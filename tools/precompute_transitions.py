"""Precompute transition frames to match the current viewport dimensions.

This script scans all transition folders declared in config.json and ensures that
scaled copies of every frame exist at the viewport size. Original frames are
preserved inside an "original_scale" subdirectory.
"""
import argparse
import json
import os
import shutil
import sys
from typing import Dict, Tuple

import pygame

ORIGINAL_DIR_NAME = "original_scale"
FRAME_PREFIX = "frame_"
FRAME_SUFFIX = ".png"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Precompute scaled transition frames")
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to the configuration file describing transition folders (default: config.json)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=720,
        help="Viewport width to scale frames to (default: 720)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=720,
        help="Viewport height to scale frames to (default: 720)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild scaled copies even if they already match the viewport size",
    )
    return parser.parse_args()


def init_pygame_headless() -> None:
    """Initialize pygame with a hidden display so convert_alpha works."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    try:
        pygame.display.set_mode((1, 1), flags=pygame.HIDDEN)
    except pygame.error:
        # Fallback: create a tiny visible window if the dummy driver is unavailable
        pygame.display.set_mode((1, 1))


def calculate_target_size(width: int, height: int, viewport: Tuple[int, int]) -> Tuple[int, int]:
    if width == 0 or height == 0:
        return viewport
    scale = min(viewport[0] / width, viewport[1] / height)
    new_width = max(1, int(round(width * scale)))
    new_height = max(1, int(round(height * scale)))
    return new_width, new_height


def list_frame_names(folder: str) -> Tuple[str, ...]:
    names = set()
    for directory in (folder, os.path.join(folder, ORIGINAL_DIR_NAME)):
        if not os.path.isdir(directory):
            continue
        for filename in os.listdir(directory):
            if filename.startswith(FRAME_PREFIX) and filename.endswith(FRAME_SUFFIX):
                names.add(filename)
    return tuple(sorted(names))


def ensure_scaled_frame(
    folder: str,
    frame_name: str,
    viewport: Tuple[int, int],
    force: bool,
) -> Dict[str, bool]:
    """Ensure a scaled copy exists; return operation flags."""
    summary = {"moved_original": False, "rescaled": False, "skipped": False}

    scaled_path = os.path.join(folder, frame_name)
    original_dir = os.path.join(folder, ORIGINAL_DIR_NAME)
    original_path = os.path.join(original_dir, frame_name)

    # Prefer original file if available; otherwise use whatever exists at root
    source_path = original_path if os.path.exists(original_path) else scaled_path
    if not os.path.exists(source_path):
        print(f"  Warning: Missing frame {frame_name} in {folder}; skipping")
        summary["skipped"] = True
        return summary

    # Move the source into original_scale if needed so we retain a pristine copy
    if source_path == scaled_path and not os.path.exists(original_path):
        os.makedirs(original_dir, exist_ok=True)
        shutil.move(scaled_path, original_path)
        source_path = original_path
        summary["moved_original"] = True

    # Load surfaces
    source_surface = pygame.image.load(source_path).convert_alpha()
    target_size = calculate_target_size(source_surface.get_width(), source_surface.get_height(), viewport)

    scaled_surface = None
    if os.path.exists(scaled_path):
        scaled_surface = pygame.image.load(scaled_path).convert_alpha()

    if not force and scaled_surface and scaled_surface.get_size() == target_size:
        summary["skipped"] = True
        return summary

    scaled_surface = pygame.transform.smoothscale(source_surface, target_size)
    pygame.image.save(scaled_surface, scaled_path)
    summary["rescaled"] = True
    return summary


def process_transition_folder(
    folder: str,
    viewport: Tuple[int, int],
    force: bool,
    index: int = 0,
) -> Dict[str, int]:
    stats = {"frames": 0, "rescaled": 0, "skipped": 0, "moved": 0}

    if not os.path.exists(folder):
        print(f"Warning: Transition folder not found: {folder}")
        return stats

    frame_names = list_frame_names(folder)
    if not frame_names:
        print(f"Warning: No frame_*.png files found in {folder}")
        return stats

    print(f"Processing transition {index}: {len(frame_names)} frames")

    for name in frame_names:
        result = ensure_scaled_frame(folder, name, viewport, force)
        stats["frames"] += 1
        if result["rescaled"]:
            stats["rescaled"] += 1
        if result["skipped"]:
            stats["skipped"] += 1
        if result["moved_original"]:
            stats["moved"] += 1

    return stats


def main() -> int:
    args = parse_args()
    viewport = (args.width, args.height)

    if args.width <= 0 or args.height <= 0:
        print("Viewport dimensions must be positive integers")
        return 1

    if not os.path.exists(args.config):
        print(f"Config file not found: {args.config}")
        return 1

    with open(args.config, "r", encoding="utf-8") as fh:
        config = json.load(fh)

    init_pygame_headless()

    total_stats = {"folders": 0, "frames": 0, "rescaled": 0, "skipped": 0, "moved": 0}

    for idx, image_cfg in enumerate(config.get("images", [])):
        folder = image_cfg.get("transitionFolder")
        if not folder:
            continue
        stats = process_transition_folder(folder, viewport, args.force, idx)
        total_stats["folders"] += 1
        total_stats["frames"] += stats["frames"]
        total_stats["rescaled"] += stats["rescaled"]
        total_stats["skipped"] += stats["skipped"]
        total_stats["moved"] += stats["moved"]

    print("\nDone.")
    print(
        "Processed {folders} folders / {frames} frames => {rescaled} rescaled, {skipped} already up-to-date, {moved} originals archived".format(
            **total_stats
        )
    )
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
