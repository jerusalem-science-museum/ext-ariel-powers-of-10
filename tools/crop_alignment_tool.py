"""
Crop Alignment Tool
Interactive tool to align crop regions with zoomed-in reference images
"""
import pygame
import sys
import json
import os
from .precompute_transitions import process_transition_folder
from tkinter import Tk, simpledialog, filedialog

class CropAlignmentTool:
    """Interactive crop selection and alignment tool"""
    
    def __init__(self, base_image_path, zoomed_image_path, config_path="config.json"):
        pygame.init()
        self.config = json.load(open(config_path, 'r', encoding='utf-8'))
        
        # Store image paths
        self.base_image_path = base_image_path
        self.zoomed_image_path = zoomed_image_path
        
        # Window setup
        self.screen = pygame.display.set_mode(self.config['setup']['viewportDims'])
        pygame.display.set_caption("Crop Alignment Tool")
        
        # Load images
        self.base_image = pygame.image.load(base_image_path).convert()
        self.zoomed_image = pygame.image.load(zoomed_image_path).convert_alpha()
        
        # Calculate aspect ratio from zoomed image
        self.aspect_ratio = self.zoomed_image.get_width() / self.zoomed_image.get_height()
        
        # Fonts
        self.font = pygame.font.SysFont('Arial', 14)
        self.title_font = pygame.font.SysFont('Arial', 16, bold=True)
        
        # View state
        self.zoom_level = 1.0
        self.pan_offset = [0, 0]
        self.dragging_view = False
        self.drag_start = None
        
        # Crop selection
        self.crop_rect = None
        self.is_selecting = False
        self.selection_start = None
        self.dragging_crop = False
        self.resizing_crop = False
        self.resize_handle = None  # 'tl', 'tr', 'bl', 'br', 'top', 'bottom', 'left', 'right'
        self.drag_offset = [0, 0]
        
        # Overlay
        self.show_overlay = True
        self.overlay_alpha = 128
        
        # Handle size for resize
        self.handle_size = 10
        
        # Clock
        self.clock = pygame.time.Clock()
        
        
    def screen_to_image(self, screen_pos):
        """Convert screen coordinates to image coordinates"""
        x = (screen_pos[0] - self.pan_offset[0]) / self.zoom_level
        y = (screen_pos[1] - self.pan_offset[1]) / self.zoom_level
        return (x, y)
    
    def image_to_screen(self, image_pos):
        """Convert image coordinates to screen coordinates"""
        x = image_pos[0] * self.zoom_level + self.pan_offset[0]
        y = image_pos[1] * self.zoom_level + self.pan_offset[1]
        return (x, y)
    
    def get_resize_handle(self, mouse_pos):
        """Check if mouse is over a resize handle"""
        if not self.crop_rect:
            return None
        
        # Get screen coordinates of crop rect
        screen_rect = pygame.Rect(
            self.crop_rect.x * self.zoom_level + self.pan_offset[0],
            self.crop_rect.y * self.zoom_level + self.pan_offset[1],
            self.crop_rect.width * self.zoom_level,
            self.crop_rect.height * self.zoom_level
        )
        
        mx, my = mouse_pos
        tolerance = self.handle_size
        
        # Check corners first
        if abs(mx - screen_rect.left) < tolerance and abs(my - screen_rect.top) < tolerance:
            return 'tl'
        if abs(mx - screen_rect.right) < tolerance and abs(my - screen_rect.top) < tolerance:
            return 'tr'
        if abs(mx - screen_rect.left) < tolerance and abs(my - screen_rect.bottom) < tolerance:
            return 'bl'
        if abs(mx - screen_rect.right) < tolerance and abs(my - screen_rect.bottom) < tolerance:
            return 'br'
        
        # Check edges
        if abs(my - screen_rect.top) < tolerance and screen_rect.left < mx < screen_rect.right:
            return 'top'
        if abs(my - screen_rect.bottom) < tolerance and screen_rect.left < mx < screen_rect.right:
            return 'bottom'
        if abs(mx - screen_rect.left) < tolerance and screen_rect.top < my < screen_rect.bottom:
            return 'left'
        if abs(mx - screen_rect.right) < tolerance and screen_rect.top < my < screen_rect.bottom:
            return 'right'
        
        return None
    
    def is_inside_crop(self, mouse_pos):
        """Check if mouse is inside crop rectangle"""
        if not self.crop_rect:
            return False
        
        img_pos = self.screen_to_image(mouse_pos)
        return self.crop_rect.collidepoint(img_pos)
    
    def resize_crop_rect(self, mouse_pos, handle):
        """Resize crop rectangle while maintaining aspect ratio"""
        img_pos = self.screen_to_image(mouse_pos)
        
        if handle in ['tl', 'tr', 'bl', 'br']:
            # Corner resize - maintain aspect ratio from opposite corner
            if handle == 'tl':
                anchor_x = self.crop_rect.right
                anchor_y = self.crop_rect.bottom
                new_width = anchor_x - img_pos[0]
                new_height = new_width / self.aspect_ratio
                self.crop_rect.topleft = (anchor_x - new_width, anchor_y - new_height)
                self.crop_rect.width = new_width
                self.crop_rect.height = new_height
            elif handle == 'tr':
                anchor_x = self.crop_rect.left
                anchor_y = self.crop_rect.bottom
                new_width = img_pos[0] - anchor_x
                new_height = new_width / self.aspect_ratio
                self.crop_rect.topleft = (anchor_x, anchor_y - new_height)
                self.crop_rect.width = new_width
                self.crop_rect.height = new_height
            elif handle == 'bl':
                anchor_x = self.crop_rect.right
                anchor_y = self.crop_rect.top
                new_width = anchor_x - img_pos[0]
                new_height = new_width / self.aspect_ratio
                self.crop_rect.topleft = (anchor_x - new_width, anchor_y)
                self.crop_rect.width = new_width
                self.crop_rect.height = new_height
            elif handle == 'br':
                anchor_x = self.crop_rect.left
                anchor_y = self.crop_rect.top
                new_width = img_pos[0] - anchor_x
                new_height = new_width / self.aspect_ratio
                self.crop_rect.topleft = (anchor_x, anchor_y)
                self.crop_rect.width = new_width
                self.crop_rect.height = new_height
        
        elif handle in ['top', 'bottom']:
            # Edge resize - maintain aspect ratio
            center_x = self.crop_rect.centerx
            if handle == 'top':
                new_height = self.crop_rect.bottom - img_pos[1]
                new_width = new_height * self.aspect_ratio
                self.crop_rect.height = new_height
                self.crop_rect.width = new_width
                self.crop_rect.centerx = center_x
                self.crop_rect.bottom = self.crop_rect.bottom
            else:  # bottom
                new_height = img_pos[1] - self.crop_rect.top
                new_width = new_height * self.aspect_ratio
                self.crop_rect.height = new_height
                self.crop_rect.width = new_width
                self.crop_rect.centerx = center_x
        
        elif handle in ['left', 'right']:
            # Edge resize - maintain aspect ratio
            center_y = self.crop_rect.centery
            if handle == 'left':
                new_width = self.crop_rect.right - img_pos[0]
                new_height = new_width / self.aspect_ratio
                self.crop_rect.width = new_width
                self.crop_rect.height = new_height
                self.crop_rect.centery = center_y
                self.crop_rect.right = self.crop_rect.right
            else:  # right
                new_width = img_pos[0] - self.crop_rect.left
                new_height = new_width / self.aspect_ratio
                self.crop_rect.width = new_width
                self.crop_rect.height = new_height
                self.crop_rect.centery = center_y
        
        # Clamp to image bounds
        self.crop_rect.left = max(0, self.crop_rect.left)
        self.crop_rect.top = max(0, self.crop_rect.top)
        self.crop_rect.right = min(self.base_image.get_width(), self.crop_rect.right)
        self.crop_rect.bottom = min(self.base_image.get_height(), self.crop_rect.bottom)
    
    def handle_events(self):
        """Handle user input"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_SPACE:
                    self.show_overlay = not self.show_overlay
                elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    self.save_crop()
                    # Exit after saving (save_crop quits pygame)
                    return False
                elif event.key == pygame.K_c:
                    self.crop_rect = None
                elif event.key == pygame.K_UP:
                    self.overlay_alpha = min(255, self.overlay_alpha + 16)
                elif event.key == pygame.K_DOWN:
                    self.overlay_alpha = max(0, self.overlay_alpha - 16)
            
            elif event.type == pygame.MOUSEWHEEL:
                # Zoom
                mouse_pos = pygame.mouse.get_pos()
                old_zoom = self.zoom_level
                
                if event.y > 0:  # Scroll up - zoom in
                    self.zoom_level *= 1.1
                else:  # Scroll down - zoom out
                    self.zoom_level /= 1.1
                
                self.zoom_level = max(0.1, min(10.0, self.zoom_level))
                
                # Adjust pan to zoom towards mouse
                zoom_factor = self.zoom_level / old_zoom
                self.pan_offset[0] = mouse_pos[0] - (mouse_pos[0] - self.pan_offset[0]) * zoom_factor
                self.pan_offset[1] = mouse_pos[1] - (mouse_pos[1] - self.pan_offset[1]) * zoom_factor
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    mouse_pos = pygame.mouse.get_pos()
                    
                    # Check for resize handle
                    handle = self.get_resize_handle(mouse_pos)
                    if handle:
                        self.resizing_crop = True
                        self.resize_handle = handle
                    # Check if clicking inside crop
                    elif self.is_inside_crop(mouse_pos):
                        self.dragging_crop = True
                        img_pos = self.screen_to_image(mouse_pos)
                        self.drag_offset = [img_pos[0] - self.crop_rect.x, img_pos[1] - self.crop_rect.y]
                    # Start new selection
                    else:
                        self.is_selecting = True
                        self.selection_start = self.screen_to_image(mouse_pos)
                
                elif event.button == 3:  # Right click - pan view
                    self.dragging_view = True
                    self.drag_start = pygame.mouse.get_pos()
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Left click
                    if self.is_selecting:
                        self.is_selecting = False
                        # Finalize selection
                        if self.crop_rect and (self.crop_rect.width < 10 or self.crop_rect.height < 10):
                            self.crop_rect = None
                    self.dragging_crop = False
                    self.resizing_crop = False
                    self.resize_handle = None
                
                elif event.button == 3:  # Right click
                    self.dragging_view = False
                    self.drag_start = None
            
            elif event.type == pygame.MOUSEMOTION:
                mouse_pos = pygame.mouse.get_pos()
                
                if self.dragging_view and self.drag_start:
                    # Pan view
                    dx = mouse_pos[0] - self.drag_start[0]
                    dy = mouse_pos[1] - self.drag_start[1]
                    self.pan_offset[0] += dx
                    self.pan_offset[1] += dy
                    self.drag_start = mouse_pos
                
                elif self.is_selecting:
                    # Update selection rectangle
                    img_pos = self.screen_to_image(mouse_pos)
                    start_x = min(self.selection_start[0], img_pos[0])
                    start_y = min(self.selection_start[1], img_pos[1])
                    width = abs(img_pos[0] - self.selection_start[0])
                    height = width / self.aspect_ratio
                    
                    self.crop_rect = pygame.Rect(start_x, start_y, width, height)
                
                elif self.dragging_crop and self.crop_rect:
                    # Move crop rectangle
                    img_pos = self.screen_to_image(mouse_pos)
                    new_x = img_pos[0] - self.drag_offset[0]
                    new_y = img_pos[1] - self.drag_offset[1]
                    
                    # Clamp to image bounds
                    new_x = max(0, min(self.base_image.get_width() - self.crop_rect.width, new_x))
                    new_y = max(0, min(self.base_image.get_height() - self.crop_rect.height, new_y))
                    
                    self.crop_rect.x = new_x
                    self.crop_rect.y = new_y
                
                elif self.resizing_crop and self.resize_handle:
                    # Resize crop rectangle
                    self.resize_crop_rect(mouse_pos, self.resize_handle)
        
        return True
    
    def draw(self):
        """Draw everything"""
        self.screen.fill((30, 30, 30))
        
        # Create scaled/panned view of base image
        scaled_width = int(self.base_image.get_width() * self.zoom_level)
        scaled_height = int(self.base_image.get_height() * self.zoom_level)
        
        if scaled_width > 0 and scaled_height > 0:
            scaled_base = pygame.transform.scale(self.base_image, (scaled_width, scaled_height))
            self.screen.blit(scaled_base, self.pan_offset)
        
        # Draw crop rectangle
        if self.crop_rect:
            screen_rect = pygame.Rect(
                int(self.crop_rect.x * self.zoom_level + self.pan_offset[0]),
                int(self.crop_rect.y * self.zoom_level + self.pan_offset[1]),
                int(self.crop_rect.width * self.zoom_level),
                int(self.crop_rect.height * self.zoom_level)
            )
            
            # Draw crop outline
            pygame.draw.rect(self.screen, (0, 255, 0), screen_rect, 2)
            
            # Draw overlay if enabled
            if self.show_overlay and screen_rect.width > 0 and screen_rect.height > 0:
                try:
                    overlay_scaled = pygame.transform.scale(self.zoomed_image, 
                                                           (screen_rect.width, screen_rect.height))
                    overlay_scaled.set_alpha(self.overlay_alpha)
                    self.screen.blit(overlay_scaled, screen_rect.topleft)
                except:
                    pass
            
            # Draw resize handles
            handle_rects = self.draw_resize_handles(screen_rect)
        
        # Draw UI
        self.draw_ui()
        
        pygame.display.flip()
    
    def draw_resize_handles(self, screen_rect):
        """Draw resize handles on crop rectangle"""
        handle_color = (255, 255, 0)
        handle_size = self.handle_size
        
        handles = {
            'tl': (screen_rect.left, screen_rect.top),
            'tr': (screen_rect.right, screen_rect.top),
            'bl': (screen_rect.left, screen_rect.bottom),
            'br': (screen_rect.right, screen_rect.bottom),
            'top': (screen_rect.centerx, screen_rect.top),
            'bottom': (screen_rect.centerx, screen_rect.bottom),
            'left': (screen_rect.left, screen_rect.centery),
            'right': (screen_rect.right, screen_rect.centery)
        }
        
        for pos in handles.values():
            pygame.draw.circle(self.screen, handle_color, pos, handle_size // 2)
            pygame.draw.circle(self.screen, (0, 0, 0), pos, handle_size // 2, 1)
    
    def draw_ui(self):
        """Draw UI overlay"""
        y = 10
        padding = 8
        
        # Instructions panel
        instructions = [
            "CROP ALIGNMENT TOOL",
            "",
            "Mouse Wheel: Zoom in/out",
            "Right Click + Drag: Pan view",
            "Left Click + Drag: Create crop selection",
            "Drag handles: Resize crop (maintains aspect ratio)",
            "Drag center: Move crop",
            "SPACE: Toggle overlay",
            "↑/↓: Adjust overlay opacity",
            "C: Clear selection",
            "ENTER: Save crop",
            "ESC: Exit"
        ]
        
        if self.crop_rect:
            instructions.append("")
            instructions.append(f"Crop: ({int(self.crop_rect.x)}, {int(self.crop_rect.y)}) "
                              f"{int(self.crop_rect.width)}x{int(self.crop_rect.height)}")
        
        instructions.append(f"Zoom: {self.zoom_level:.2f}x")
        instructions.append(f"Overlay Alpha: {self.overlay_alpha}")
        
        # Calculate panel size
        max_width = max(self.font.size(text)[0] for text in instructions)
        panel_width = max_width + padding * 2
        panel_height = len(instructions) * 20 + padding * 2
        
        # Draw semi-transparent background
        panel_surface = pygame.Surface((panel_width, panel_height))
        panel_surface.set_alpha(200)
        panel_surface.fill((20, 20, 20))
        self.screen.blit(panel_surface, (10, y))
        
        # Draw text
        y += padding
        for i, text in enumerate(instructions):
            if i == 0:  # Title
                surface = self.title_font.render(text, True, (100, 200, 255))
            elif text == "":
                continue
            else:
                color = (200, 200, 200) if not text.startswith("Crop:") else (100, 255, 100)
                surface = self.font.render(text, True, color)
            
            self.screen.blit(surface, (10 + padding, y))
            y += 20
    
    def save_crop(self):
        """Save crop information"""
        if not self.crop_rect:
            print("No crop selected!")
            return
        
        # Close pygame window before selecting output folder
        pygame.quit()
        
        # Select output folder for transition frames
        print("\nSelect output folder for transition frames...")
        output_folder = select_output_folder()
        
        # Re-initialize pygame for saving images
        pygame.init()
        
        # Create output data in config.json format
        # Convert output_folder to relative path if possible
        try:
            rel_output_folder = os.path.relpath(output_folder, os.getcwd())
        except ValueError:
            rel_output_folder = output_folder
        
        try:
            rel_base_image = os.path.relpath(self.base_image_path, os.getcwd())
        except ValueError:
            rel_base_image = self.base_image_path
        
        output = {
            "nextPixelRect": [
                int(self.crop_rect.x),
                int(self.crop_rect.y),
                int(self.crop_rect.width),
                int(self.crop_rect.height)
            ],
            "transitionFolder": rel_output_folder.replace("\\", "/"),  # Use forward slashes for JSON
            "src": rel_base_image.replace("\\", "/"),  # Use forward slashes for JSON
            # Additional fields to fill in manually:
            # "id": "imgX",
            # "caption": "Description for Image X",
            # "bg": "data/bg/bgX.png",
            # "outlineColor": "#00ff88"
        }
        
        # Create output folder
        os.makedirs(output_folder, exist_ok=True)
        
        # Save individual crop JSON in output folder
        output_file = os.path.join(output_folder, "crop_data.json")
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)
        
        print("\n" + "="*60)
        print("CROP SAVED!")
        print("="*60)
        print(f"Output file: {output_file}")
        print(f"Crop region: ({output['nextPixelRect'][0]}, {output['nextPixelRect'][1]}) {output['nextPixelRect'][2]}x{output['nextPixelRect'][3]}")
        print(f"Transition folder: {output['transitionFolder']}")
        print(f"Source image: {output['src']}")
        print("\nThis JSON can be copied directly into config.json images array!")
        print("="*60 + "\n")
        
        # Save the cropped image
        cropped_surface = self.base_image.subsurface(self.crop_rect)
        cropped_filename = os.path.join(output_folder, "cropped_output.png")
        pygame.image.save(cropped_surface, cropped_filename)
        print(f"Cropped image saved: {cropped_filename}\n")
        
        # Save zoomed image in output folder
        zoomed_filename = os.path.join(output_folder, "zoomed_reference.png")
        pygame.image.save(self.zoomed_image, zoomed_filename)
        print(f"Zoomed reference saved: {zoomed_filename}\n")
        
        # Clean up pygame
        pygame.quit()
        
        # Generate morph sequence using GMIC
        generate_morph_sequence_standalone(cropped_filename, zoomed_filename, output_folder)

        # rescale transition frames to viewport dimensions
        print("Rescaling transition frames to viewport dimensions...")
        pygame.init()
        pygame.display.set_mode((1,1))  # Minimal display to enable image operations
        process_transition_folder(output_folder,
                                  self.config['setup']['viewportDims'],
                                  force=False)
        
        # Clean up pygame after processing
        pygame.quit()
    
    def run(self):
        """Main loop"""
        running = True
        
        while running:
            running = self.handle_events()
            if running:
                self.draw()
                self.clock.tick(60)
        
        # Only quit if we didn't save (save_crop calls pygame.quit())
        if pygame.get_init():
            pygame.quit()


def select_files_with_dialog():
    """Open file dialogs to select images"""
    try:
        from tkinter import Tk, filedialog
        
        # Hide the main tkinter window
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        print("Select the base image (the one to crop)...")
        base_image = filedialog.askopenfilename(
            title="Select Base Image (to crop)",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("All files", "*.*")
            ]
        )
        
        if not base_image:
            print("No base image selected. Exiting.")
            return None, None
        
        print("Select the zoomed-in reference image...")
        zoomed_image = filedialog.askopenfilename(
            title="Select Zoomed-In Reference Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("All files", "*.*")
            ]
        )
        
        if not zoomed_image:
            print("No zoomed image selected. Exiting.")
            return None, None
        
        root.destroy()
        return base_image, zoomed_image
        
    except ImportError:
        print("Error: tkinter not available for file dialogs")
        print("Please provide images as command line arguments")
        return None, None


def select_output_folder():
    """Open folder dialog to select output directory for frames"""
    try:
        from tkinter import Tk, filedialog
        
        # Hide the main tkinter window
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        print("Select the output folder for rendered frames...")
        output_folder = filedialog.askdirectory(
            title="Select Output Folder for Rendered Frames",
            mustexist=False
        )
        
        root.destroy()
        
        if not output_folder:
            print("No folder selected. Using default 'morph_sequence' folder.")
            return "morph_sequence"
        
        return output_folder
        
    except ImportError:
        print("Error: tkinter not available for folder dialog")
        print("Using default 'morph_sequence' folder")
        return "morph_sequence"


def select_num_frames(default=16):
    """Open dialog to select number of frames for morph sequence"""
    try:
        
        
        # Hide the main tkinter window
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        print("Select number of frames for morph sequence...")
        num_frames = simpledialog.askinteger(
            title="Number of Frames",
            prompt="Enter the number of frames for the morph sequence:",
            initialvalue=default,
            minvalue=1,
            maxvalue=1000
        )
        
        root.destroy()
        
        if num_frames is None:
            print(f"No value entered. Using default: {default} frames.")
            return default
        
        return num_frames
        
    except ImportError:
        print("Error: tkinter not available for dialog")
        print(f"Using default: {default} frames")
        return default



def apply_existing_crop(base_image_path, zoomed_image_path, crop_json_path):
    """Apply existing crop from JSON and proceed to GMIC stage"""
    
    # Load crop data
    try:
        with open(crop_json_path, 'r') as f:
            crop_data = json.load(f)
        
        # Support multiple formats:
        # 1. Old format: [x, y, w, h]
        # 2. Old format: {"crop_region": {...}}
        # 3. New config.json format: {"nextPixelRect": [x, y, w, h], ...}
        if isinstance(crop_data, list):
            x, y, width, height = crop_data
        elif isinstance(crop_data, dict):
            if "nextPixelRect" in crop_data:
                # New config.json format
                x, y, width, height = crop_data["nextPixelRect"]
            elif "crop_region" in crop_data:
                # Old dict format
                cr = crop_data["crop_region"]
                x, y, width, height = cr["x"], cr["y"], cr["width"], cr["height"]
            else:
                print("Error: Invalid JSON format - expected 'nextPixelRect' or 'crop_region'")
                return False
        else:
            print("Error: Invalid JSON format")
            return False
        
        print("\n" + "="*60)
        print("APPLYING EXISTING CROP")
        print("="*60)
        print(f"Crop JSON: {crop_json_path}")
        print(f"Crop region: ({x}, {y}) {width}x{height}")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"Error loading crop JSON: {e}")
        return False
    
    # Select output folder first
    output_folder = select_output_folder()
    
    # Initialize pygame just for image loading and cropping
    import pygame
    pygame.init()
    
    try:
        # Load images
        base_image = pygame.image.load(base_image_path).convert()
        zoomed_image = pygame.image.load(zoomed_image_path).convert_alpha()
        
        # Create crop rect
        crop_rect = pygame.Rect(x, y, width, height)
        
        # Validate crop is within bounds
        if (crop_rect.right > base_image.get_width() or 
            crop_rect.bottom > base_image.get_height() or
            crop_rect.left < 0 or crop_rect.top < 0):
            print("Error: Crop region is outside image bounds!")
            pygame.quit()
            return False
        
        # Create output folder
        os.makedirs(output_folder, exist_ok=True)
        
        # Save the cropped image in output folder
        cropped_surface = base_image.subsurface(crop_rect)
        cropped_filename = os.path.join(output_folder, "cropped_output.png")
        pygame.image.save(cropped_surface, cropped_filename)
        print(f"Cropped image saved: {cropped_filename}\n")
        
        # Save zoomed image in output folder
        zoomed_filename = os.path.join(output_folder, "zoomed_reference.png")
        pygame.image.save(zoomed_image, zoomed_filename)
        print(f"Zoomed reference saved: {zoomed_filename}\n")
        
        # Clean up pygame
        pygame.quit()
        
        # Generate morph sequence directly
        generate_morph_sequence_standalone(cropped_filename, zoomed_filename, output_folder)
        
        # Rescale transition frames to viewport dimensions
        print("Rescaling transition frames to viewport dimensions...")
        # Load config for viewport dimensions
        try:
            config_path = "config.json"
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                viewport_dims = config['setup']['viewportDims']
            else:
                print("Warning: config.json not found, skipping frame rescaling")
                return True
        except Exception as e:
            print(f"Warning: Could not load config.json: {e}, skipping frame rescaling")
            return True
        
        # Re-initialize pygame for image operations
        pygame.init()
        pygame.display.set_mode((1, 1))  # Minimal display to enable image operations
        process_transition_folder(output_folder, viewport_dims, force=False)
        
        return True
        
    except Exception as e:
        print(f"Error processing crop: {e}")
        pygame.quit()
        return False


def generate_morph_sequence_standalone(cropped_filename, zoomed_filename, output_folder):
    """Generate morph sequence using GMIC (standalone version)"""
    import subprocess
    import shutil
    
    # Create output folder
    os.makedirs(output_folder, exist_ok=True)
    
    print("="*60)
    print("GENERATING MORPH SEQUENCE WITH GMIC")
    print("="*60)
    print(f"From: {cropped_filename}")
    print(f"To:   {zoomed_filename}")
    print(f"Output folder: {output_folder}/")
    
    # Try to find GMIC executable
    gmic_exe = None
    
    # Check if gmic is in PATH
    gmic_exe = shutil.which("gmic")
    
    # Check common Windows installation locations
    if not gmic_exe:
        common_paths = [
            r"./gmic.exe",
            r"C:\Program Files\gmic\gmic.exe",
            r"C:\Program Files (x86)\gmic\gmic.exe",
            os.path.expanduser(r"~\AppData\Local\gmic\gmic.exe"),
            r"C:\gmic\gmic.exe"

        ]
        for path in common_paths:
            if os.path.exists(path):
                gmic_exe = path
                break
    
    if not gmic_exe:
        print(f"\n❌ GMIC not found!")
        print("Searched in:")
        print("  - System PATH")
        print("  - C:\\Program Files\\gmic\\")
        print("  - C:\\Program Files (x86)\\gmic\\")
        print("  - %USERPROFILE%\\AppData\\Local\\gmic\\")
        print("\nPlease install GMIC from: https://gmic.eu/")
        print("="*60 + "\n")
        return
    
    print(f"Using GMIC: {gmic_exe}\n")
    
    # GMIC command to create morph sequence
    num_frames = select_num_frames(default=16)
    
    gmic_command = [
        gmic_exe,
        cropped_filename,
        zoomed_filename,
        "-x_morph",
        str(num_frames),
        "-output",
        f"{output_folder}/frame_.png"
    ]
    
    try:
        result = subprocess.run(
            gmic_command,
            capture_output=True,
            text=True,
            check=True
        )
        
        print(f"\n✅ Morph sequence generated successfully!")
        print(f"Output: {output_folder}/")
        print(f"Frames: {num_frames}")
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
    
    print("="*60 + "\n")


def main():
    base_image_path = None
    zoomed_image_path = None
    
    if len(sys.argv) >= 3:
        # Command line arguments provided
        base_image_path = sys.argv[1]
        zoomed_image_path = sys.argv[2]
    else:
        # No arguments - show file dialog
        print("\nNo images specified. Opening file dialogs...\n")
        base_image_path, zoomed_image_path = select_files_with_dialog()
        
        if not base_image_path or not zoomed_image_path:
            sys.exit(1)
    
    # Validate files exist
    if not os.path.exists(base_image_path):
        print(f"Error: Base image not found: {base_image_path}")
        sys.exit(1)
    
    if not os.path.exists(zoomed_image_path):
        print(f"Error: Zoomed image not found: {zoomed_image_path}")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("CROP ALIGNMENT TOOL")
    print("="*60)
    print(f"Base image:   {base_image_path}")
    print(f"Zoomed image: {zoomed_image_path}")
    print("="*60 + "\n")
    tool = CropAlignmentTool(base_image_path, zoomed_image_path)
    tool.run()


if __name__ == "__main__":
    main()
