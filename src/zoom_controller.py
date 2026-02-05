"""
Zoom Controller - Manages zoom state and animations
"""
import pygame


class ZoomController:
    """Handles all zoom-related logic and animations"""
    
    def __init__(self):
        self.scale = 1.0
        self.min_scale = 1.0
        self.current_max_scale = 1.0  # Updated by viewer when image changes
        
        # Step animation properties
        self.animation_duration = 300  # milliseconds
        self.target_scale = 1.0
        self.start_scale = 1.0
        self.animation_start_time = None
        self.is_animating = False
        self.step_zoom_factor = 1.3 # 30% zoom per step
        # Continuous zoom properties
        self.continuous_zoom_rate = 2.0  # 100% scale change per second
        self.continuous_zoom_active = False  # Track if continuous zoom happened this frame
    
    def zoom_step(self, direction):
        """Initiate a discrete zoom step with animation"""
        if direction == 'in':
            new_scale = self.scale * self.step_zoom_factor
        elif direction == 'out':
            new_scale = self.scale / self.step_zoom_factor
        else:
            return
        
        self.start_zoom_animation(new_scale)
    
    def zoom_continuous(self, direction, dt):
        """Apply continuous zoom based on elapsed time"""
        zoom_factor = self.continuous_zoom_rate ** dt
        
        if direction == 'in':
            self.scale = self.scale * zoom_factor
        elif direction == 'out':
            self.scale = self.scale / zoom_factor
        
        self.continuous_zoom_active = True
    
    def update(self):
        """Update zoom state and return boundary info if exceeded"""
        boundary_info = None
        
        # Update step animation if active
        if self.is_animating:
            boundary_info = self.update_step_animation()
        # Check boundaries if continuous zoom happened this frame
        elif self.continuous_zoom_active:
            boundary_info = self._check_boundaries()
            self.continuous_zoom_active = False  # Reset for next frame
        
        return boundary_info
    
    def start_zoom_animation(self, target_scale, start_scale=None):
        """Start a zoom animation towards the target scale"""
        self.is_animating = True
        self.animation_start_time = pygame.time.get_ticks()
        self.target_scale = target_scale
        self.start_scale = start_scale if start_scale is not None else self.scale
    
    def update_step_animation(self):
        """Update step animation state and return boundary info if exceeded"""
        
        current_time = pygame.time.get_ticks()
        elapsed = current_time - self.animation_start_time
        animation_progress = min(1.0, elapsed / self.animation_duration)
        
        if animation_progress >= 1.0:
            # Animation complete
            self.is_animating = False
            self.scale = self.target_scale
            return self._check_boundaries()
        else:
            self.scale = self.start_scale + (self.target_scale - self.start_scale) * animation_progress
            swapped = self._check_boundaries()
            if swapped:
                self.is_animating = False
            return swapped
    
    def _check_boundaries(self):
        """Check if scale exceeded boundaries and return direction or None"""
        if self.scale > self.current_max_scale:
            return 'forward'
        elif self.scale < self.min_scale:
            return 'backward'
        
        return None
    
    def set_max_scale(self, max_scale):
        """Update max scale (called when image changes)"""
        self.current_max_scale = max_scale
    
    def clamp_scale(self):
        """Clamp scale to boundaries (for when max_scale changes)"""
        if self.scale > self.current_max_scale:
            self.scale = self.current_max_scale
        elif self.scale < self.min_scale:
            self.scale = self.min_scale
    
    def reset_to_min(self):
        """Reset scale to minimum (fully zoomed out)"""
        self.scale = self.min_scale
    
    def reset_to_max(self):
        """Reset scale to maximum for current image"""
        self.scale = self.current_max_scale
    
    def get_normalized_zoom(self):
        """Get zoom progress from min to max (0.0 to 1.0)"""
        return (self.scale - self.min_scale) / (self.current_max_scale - self.min_scale)
