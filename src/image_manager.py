"""
Image Manager - Handles loading and managing images with their metadata
"""
from dataclasses import dataclass
import pygame
import os


@dataclass
class RectData:
    """Lightweight rectangle structure that retains floating point precision"""
    x: float
    y: float
    width: float
    height: float

    def scaled(self, factor: float) -> "RectData":
        return RectData(
            self.x * factor,
            self.y * factor,
            self.width * factor,
            self.height * factor,
        )


class ImageData:
    """Encapsulates all data for a single image"""
    def __init__(self, config, original, surface, scale, bg, max_scale):
        self.config = config
        self.original = original  # High-res original
        self.surface = surface    # Pre-scaled to fit viewport
        self.scale = scale        # Scale factor used to create surface
        self.bg = bg             # Background image
        self.max_scale = max_scale  # Maximum zoom level for this image


class ImageManager:
    """Manages loading and accessing images"""
    
    def __init__(self, config, viewport_dims):
        self.config = config
        self.viewport_dims = viewport_dims
        self.images = []
        self.current_index = 0
        
    def load_images(self):
        """Load all images from config"""
        for img_config in self.config['images']:
            # Load image from file
            image_path = img_config['src']
            image_path_bg = img_config.get('bg')
            
            original = pygame.image.load(image_path).convert_alpha()
            bg = pygame.image.load(image_path_bg).convert_alpha()
            
            # Calculate scaling to fit viewport while maintaining aspect ratio
            scale = min(self.viewport_dims[0] / original.get_width(), 
                       self.viewport_dims[1] / original.get_height())
            
            new_size = (int(original.get_width() * scale),
                       int(original.get_height() * scale))
            
            scaled = pygame.transform.smoothscale(original, new_size)
            
            # Calculate max scale based on rectangle dimensions
            original_size = (original.get_width(), original.get_height())
            max_scale = self._calculate_max_scale(img_config, original_size, scale)
            
            image_data = ImageData(img_config, original, scaled, scale, bg, max_scale)
            self.images.append(image_data)
    
    def _calculate_max_scale(self, img_config, original_size, scale_factor):
        """Calculate maximum zoom level based on rect dimensions"""
        rect = self._get_rect(img_config, original_size, scale_factor, space='surface')
        max_scale = 1.0
        
        if rect:
            # Calculate max scale so rect fills viewport
            width_scale = self.viewport_dims[0] / rect.width
            height_scale = self.viewport_dims[1] / rect.height
            max_scale = min(width_scale, height_scale)
        
        return max_scale
    
    def _get_rect(self, img_config, original_size, scale_factor, space='surface'):
        """Get rect from config and convert to requested coordinate space"""
        rect_data = None

        # Check for pixel coordinates first (original image space)
        pixel_rect = img_config.get('nextPixelRect')
        if pixel_rect and len(pixel_rect) == 4:
            rect_data = RectData(*(float(value) for value in pixel_rect))
        else:
            rect = img_config.get('nextRect')
            if rect and len(rect) == 4:
                orig_w, orig_h = original_size
                rect_data = RectData(
                    orig_w * float(rect[0]),
                    orig_h * float(rect[1]),
                    orig_w * float(rect[2]),
                    orig_h * float(rect[3])
                )

        if rect_data and space == 'surface':
            return rect_data.scaled(scale_factor)

        return rect_data
    
    def get_current_image(self):
        """Get the current image data"""
        return self.images[self.current_index]
    
    def get_rect(self, image_data, space='surface'):
        """Get rect for a specific image in the requested space"""
        original_size = (image_data.original.get_width(), image_data.original.get_height())
        return self._get_rect(image_data.config, original_size, image_data.scale, space)
    
    def set_image(self, index):
        """Set current image to specific index"""
        if 0 <= index < len(self.images):
            self.current_index = index
    
    def try_next(self):
        """Try to move to next image. Returns True if successful."""
        if self.can_go_next():
            self.current_index += 1
            return True
        return False
    
    def try_previous(self):
        """Try to move to previous image. Returns True if successful."""
        if self.can_go_previous():
            self.current_index -= 1
            return True
        return False
    
    def next_image(self):
        """Move to next image if available"""
        if self.can_go_next():
            self.current_index += 1
    
    def previous_image(self):
        """Move to previous image if available"""
        if self.can_go_previous():
            self.current_index -= 1
    
    def can_go_next(self):
        """Check if can move to next image"""
        return self.current_index < len(self.images) - 1
    
    def can_go_previous(self):
        """Check if can move to previous image"""
        return self.current_index > 0
