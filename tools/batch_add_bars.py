"""
Batch Add Black Bars or Crop Images
Select multiple images and either add black bars or crop to match a target aspect ratio
"""
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from PIL import Image
from pathlib import Path
import sys
import json

config = json.load(open('config.json','r'))
dims = config['setup']['viewportDims']
def add_bars_to_match_aspect(img: Image.Image, target_ratio: float, bg=(0, 0, 0)) -> Image.Image:
    """Add black bars to image to match target aspect ratio"""
    w, h = img.size
    src_ratio = w / h

    # If already matches, return copy
    if abs(src_ratio - target_ratio) < 1e-6:
        return img.copy()

    if src_ratio > target_ratio:
        # Image is wider than target → add bars top/bottom
        canvas_w = w
        canvas_h = round(w / target_ratio)
    else:
        # Image is taller/narrower than target → add bars left/right
        canvas_h = h
        canvas_w = round(h * target_ratio)

    canvas = Image.new("RGB", (canvas_w, canvas_h), bg)
    offset_x = (canvas_w - w) // 2
    offset_y = (canvas_h - h) // 2
    canvas.paste(img, (offset_x, offset_y))
    return canvas


def crop_to_match_aspect(img: Image.Image, target_ratio: float) -> Image.Image:
    """Crop image to match target aspect ratio (centered cropping)"""
    w, h = img.size
    src_ratio = w / h

    # If already matches, return copy
    if abs(src_ratio - target_ratio) < 1e-6:
        return img.copy()

    if src_ratio > target_ratio:
        # Image is wider than target → crop left/right (equidistant)
        new_w = round(h * target_ratio)
        left = (w - new_w) // 2
        return img.crop((left, 0, left + new_w, h))
    else:
        # Image is taller/narrower than target → crop top/bottom (equidistant)
        new_h = round(w / target_ratio)
        top = (h - new_h) // 2
        return img.crop((0, top, w, top + new_h))


def select_images():
    """Open file dialog to select multiple images"""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    
    files = filedialog.askopenfilenames(
        title="Select Images to Process",
        filetypes=[
            ("Image files", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"),
            ("All files", "*.*")
        ]
    )
    
    root.destroy()
    return list(files) if files else None


def get_target_aspect_ratio():
    """Get target aspect ratio from user"""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    
    # Ask for width and height
    width = dims[0]
    
    if width is None:
        root.destroy()
        return None
    
    height = dims[1]
    
    root.destroy()
    
    if height is None or height <= 0:
        return None
    
    return width / height


def select_output_folder():
    """Select output folder for processed images"""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    
    folder = filedialog.askdirectory(
        title="Select Output Folder (Cancel to save in same folder as originals)",
        mustexist=False
    )
    
    root.destroy()
    return folder if folder else None


def choose_mode():
    """Ask user to choose between adding bars or cropping"""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    
    choice = messagebox.askyesno(
        "Processing Mode",
        "Choose processing mode:\n\n"
        "YES = Add black bars (preserves full image)\n"
        "NO = Crop to aspect ratio (centered, equidistant)\n\n"
        "Click YES for bars, NO for crop"
    )
    
    root.destroy()
    return "bars" if choice else "crop"


def process_images(image_paths, target_ratio, mode="bars", output_folder=None, bg=(0, 0, 0)):
    """Process all selected images"""
    if not image_paths:
        print("No images selected!")
        return
    
    if output_folder:
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = None
    
    processed = 0
    skipped = 0
    mode_suffix = "_bars" if mode == "bars" else "_cropped"
    
    for img_path in image_paths:
        try:
            img_path_obj = Path(img_path)
            
            # Load image
            img = Image.open(img_path).convert("RGB")
            
            # Process based on mode
            if mode == "bars":
                out_img = add_bars_to_match_aspect(img, target_ratio, bg=bg)
            else:  # mode == "crop"
                out_img = crop_to_match_aspect(img, target_ratio)
            
            # Determine output path
            if output_path:
                out_file = output_path / img_path_obj.name
            else:
                # Save in same folder with appropriate suffix
                stem = img_path_obj.stem
                suffix = img_path_obj.suffix
                out_file = img_path_obj.parent / f"{stem}{mode_suffix}{suffix}"
            
            # Save
            out_img.save(out_file, quality=95)
            print(f"✓ Processed: {img_path_obj.name} → {out_file.name}")
            processed += 1
            
        except Exception as e:
            print(f"✗ Error processing {img_path_obj.name}: {e}")
            skipped += 1
    
    print(f"\n{'='*60}")
    print(f"Processing complete!")
    print(f"Mode: {mode.upper()}")
    print(f"Processed: {processed}")
    print(f"Skipped: {skipped}")
    print(f"{'='*60}")


def main():
    print("="*60)
    print("BATCH PROCESS IMAGES - ADD BARS OR CROP")
    print("="*60)
    
    # Select images
    print("\nStep 1: Select images...")
    image_paths = select_images()
    
    if not image_paths:
        print("No images selected. Exiting.")
        sys.exit(0)
    
    print(f"Selected {len(image_paths)} image(s)")
    
    # Get target aspect ratio
    print("\nStep 2: Enter target aspect ratio...")
    target_ratio = get_target_aspect_ratio()
    
    if target_ratio is None:
        print("No target ratio specified. Exiting.")
        sys.exit(0)
    
    print(f"Target aspect ratio: {target_ratio:.4f}")
    
    # Choose processing mode
    print("\nStep 3: Choose processing mode...")
    mode = choose_mode()
    print(f"Mode: {mode.upper()}")
    
    # Select output folder (optional)
    print("\nStep 4: Select output folder (optional)...")
    output_folder = select_output_folder()
    
    if output_folder:
        print(f"Output folder: {output_folder}")
    else:
        suffix = "_bars" if mode == "bars" else "_cropped"
        print(f"Saving in same folder as originals (with '{suffix}' suffix)")
    
    # Process images
    print("\nProcessing images...")
    print("-"*60)
    process_images(image_paths, target_ratio, mode, output_folder)
    
    # Show completion message
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    messagebox.showinfo("Complete", f"Processed {len(image_paths)} image(s)!")
    root.destroy()


if __name__ == "__main__":
    main()

