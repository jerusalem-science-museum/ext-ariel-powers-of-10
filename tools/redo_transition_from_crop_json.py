"""
Redo GMIC morph transition frames from an existing transition folder.

This tool:
- Lets you choose an existing transition folder via a folder dialog
- Expects that folder to contain:
  - crop_data.json
  - cropped_output.png
  - zoomed_reference.png
- Deletes any existing frame_*.png files and the original_scale/ subfolder
- Prompts for the number of frames
- Regenerates the GMIC morph sequence
- Rescales frames to the viewport dimensions from config.json (if available)
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pygame

from .crop_alignment_tool import select_num_frames
from .precompute_transitions import process_transition_folder


def select_transition_folder() -> str | None:
    """Open folder dialog to select an existing transition directory."""
    try:
        from tkinter import Tk, filedialog
    except ImportError:
        print("Error: tkinter not available for folder dialog")
        return None

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    print("Select the existing transition folder (with crop_data.json, cropped_output.png, zoomed_reference.png)...")
    folder = filedialog.askdirectory(
        title="Select Existing Transition Folder",
        mustexist=True,
    )

    root.destroy()

    if not folder:
        print("No folder selected. Exiting.")
        return None

    return folder


def validate_transition_folder(folder: Path) -> bool:
    """Ensure required files exist in the transition folder."""
    required_files = [
        "crop_data.json",
        "cropped_output.png",
        "zoomed_reference.png",
    ]

    missing = [name for name in required_files if not (folder / name).exists()]
    if missing:
        print("\n❌ Transition folder is missing required files:")
        for name in missing:
            print(f"  - {name}")
        print("\nExpected files in the selected folder:")
        for name in required_files:
            print(f"  - {name}")
        return False

    return True


def cleanup_transition_folder(folder: Path) -> None:
    """Remove existing frames and original_scale directory."""
    print("\nCleaning up existing frames in transition folder...")

    # Delete frame_*.png / frame_*.jpg / frame_*.jpeg in the root transition folder
    patterns = ["frame_*.png", "frame_*.jpg", "frame_*.jpeg"]
    removed = 0
    for pattern in patterns:
        for path in folder.glob(pattern):
            try:
                path.unlink()
                removed += 1
            except OSError as e:
                print(f"  Warning: Could not delete {path}: {e}")

    print(f"  Removed {removed} existing frame files.")

    # Delete original_scale subdirectory if present
    original_dir = folder / "original_scale"
    if original_dir.exists() and original_dir.is_dir():
        try:
            shutil.rmtree(original_dir)
            print(f"  Removed existing original_scale directory: {original_dir}")
        except OSError as e:
            print(f"  Warning: Could not remove original_scale directory {original_dir}: {e}")


def load_crop_info(folder: Path) -> None:
    """
    Load crop_data.json and print a short summary, purely for user feedback.

    The actual morph is driven by cropped_output.png and zoomed_reference.png;
    we don't need the crop rect numerically here, but it's nice to show it.
    """
    crop_path = folder / "crop_data.json"
    try:
        with crop_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"\nWarning: Could not read crop_data.json: {e}")
        return

    try:
        if isinstance(data, dict) and "nextPixelRect" in data:
            x, y, w, h = data["nextPixelRect"]
            print("\nExisting crop data:")
            print(f"  Crop region: ({x}, {y}) {w}x{h}")
        else:
            print("\nExisting crop_data.json loaded (non-standard format).")
    except Exception as e:
        print(f"\nWarning: Could not interpret crop_data.json contents: {e}")


def find_gmic_executable() -> str | None:
    """Locate the GMIC executable, mirroring the logic from crop_alignment_tool."""
    import shutil as _shutil

    # First, try system PATH
    gmic_exe = _shutil.which("gmic")

    # Then, common Windows locations (same as crop_alignment_tool)
    if not gmic_exe:
        common_paths = [
            r"./gmic.exe",
            r"C:\Program Files\gmic\gmic.exe",
            r"C:\Program Files (x86)\gmic\gmic.exe",
            os.path.expanduser(r"~\AppData\Local\gmic\gmic.exe"),
            r"C:\gmic\gmic.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                gmic_exe = path
                break

    if not gmic_exe:
        print("\n❌ GMIC not found!")
        print("Searched in:")
        print("  - System PATH")
        print("  - C:\\Program Files\\gmic\\")
        print("  - C:\\Program Files (x86)\\gmic\\")
        print("  - %USERPROFILE%\\AppData\\Local\\gmic\\")
        print("  - Current directory (./gmic.exe)")
        print("\nPlease install GMIC from: https://gmic.eu/")
        print()
        return None

    return gmic_exe


def generate_morph_sequence(
    cropped_filename: str,
    zoomed_filename: str,
    output_folder: str,
    num_frames: int,
) -> None:
    """Generate morph sequence using GMIC with an explicit frame count."""
    os.makedirs(output_folder, exist_ok=True)

    print("\n" + "=" * 60)
    print("REGENERATING MORPH SEQUENCE WITH GMIC")
    print("=" * 60)
    print(f"From: {cropped_filename}")
    print(f"To:   {zoomed_filename}")
    print(f"Output folder: {output_folder}/")
    print(f"Frames: {num_frames}")

    gmic_exe = find_gmic_executable()
    if not gmic_exe:
        return

    print(f"\nUsing GMIC: {gmic_exe}\n")

    gmic_command = [
        gmic_exe,
        cropped_filename,
        zoomed_filename,
        "-x_morph",
        str(num_frames),
        "-output",
        f"{output_folder}/frame_.png",
    ]

    try:
        result = subprocess.run(
            gmic_command,
            capture_output=True,
            text=True,
            check=True,
        )

        print(f"\n✅ Morph sequence generated successfully!")
        print(f"Output: {output_folder}/")
        if result.stdout:
            print(f"\nGMIC output:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ GMIC command failed!")
        print(f"Error: {e}")
        if e.stderr:
            print(f"GMIC error output:\n{e.stderr}")
        print("\nCommand that was run:")
        print(" ".join(gmic_command))
    except FileNotFoundError:
        print(f"\n❌ GMIC not found!")
        print("Please install GMIC and ensure it's in your PATH")
        print("Download from: https://gmic.eu/")
    finally:
        print("=" * 60 + "\n")


def load_viewport_dims(config_path: str = "config.json") -> tuple[int, int] | None:
    """Load viewport dimensions from config.json if available."""
    if not os.path.exists(config_path):
        print("Warning: config.json not found, skipping frame rescaling.")
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        viewport = config["setup"]["viewportDims"]
        if isinstance(viewport, (list, tuple)) and len(viewport) == 2:
            return int(viewport[0]), int(viewport[1])
        print("Warning: Invalid viewportDims format in config.json, skipping frame rescaling.")
        return None
    except Exception as e:
        print(f"Warning: Could not load config.json: {e}, skipping frame rescaling.")
        return None


def rescale_frames_to_viewport(folder: Path, viewport: tuple[int, int]) -> None:
    """Rescale all frames in the transition folder to the viewport dimensions."""
    print("Rescaling transition frames to viewport dimensions...")

    # Minimal display to enable image operations (mirrors crop_alignment_tool logic)
    pygame.init()
    try:
        pygame.display.set_mode((1, 1))
    except pygame.error:
        # Fallback: use dummy driver if necessary
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.display.set_mode((1, 1))

    process_transition_folder(str(folder), viewport, force=True)
    pygame.quit()


def redo_transition_for_folder(folder: Path) -> None:
    """Main logic: clean up, pick frame count, regenerate morph, rescale."""
    print("\n" + "=" * 60)
    print("REDO TRANSITION FROM EXISTING CROP")
    print("=" * 60)
    print(f"Transition folder: {folder}")

    if not validate_transition_folder(folder):
        return

    load_crop_info(folder)
    cleanup_transition_folder(folder)

    # Get paths to cropped and zoomed images
    cropped_path = folder / "cropped_output.png"
    zoomed_path = folder / "zoomed_reference.png"

    # Ask user for number of frames (reuse same dialog as crop tool)
    num_frames = select_num_frames(default=16)
    print(f"\nUsing {num_frames} frames for regenerated morph sequence.\n")

    generate_morph_sequence(str(cropped_path), str(zoomed_path), str(folder), num_frames)

    viewport = load_viewport_dims("config.json")
    if viewport:
        rescale_frames_to_viewport(folder, viewport)
    else:
        print("Skipping rescaling step due to missing/invalid viewport configuration.")

    print("\nDone. Transition frames have been regenerated.")


def main() -> int:
    # If a folder was provided as a CLI argument, use it; otherwise open dialog.
    if len(sys.argv) >= 2:
        folder = Path(sys.argv[1])
    else:
        selected = select_transition_folder()
        if not selected:
            return 1
        folder = Path(selected)

    if not folder.exists() or not folder.is_dir():
        print(f"Error: Transition folder not found: {folder}")
        return 1

    redo_transition_for_folder(folder)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

