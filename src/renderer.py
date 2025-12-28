"""
Renderer - Handles all drawing operations
"""
import pygame


class Renderer:
    """Responsible for rendering images, transitions, and UI"""
    
    def __init__(self, screen, viewport_dims, viewport_rect, font, smoothing_enabled=True):
        self.screen = screen
        self.viewport_dims = viewport_dims
        self.viewport_rect = viewport_rect
        self.viewport = pygame.Surface(viewport_dims)
        self.font = font
        self.small_font = pygame.font.SysFont('Consolas', 12)
        self.smoothing_enabled = smoothing_enabled
    
    def draw_frame(self, image_manager, zoom_controller, transition_manager):
        """Draw the complete frame"""
        current_img = image_manager.get_current_image()
        
        # Get background (may change during transitions)
        bg = transition_manager.get_current_background(current_img.bg)
        
        # Fill background
        self.screen.fill((17, 17, 17))
        self.screen.blit(bg, (0, 0))
        
        # Draw either transition or normal image
        if transition_manager.is_active():
            frame_drawn = self._draw_transition(transition_manager)
            # Fall back to normal image if transition has no frame available
            if not frame_drawn:
                rect = image_manager.get_rect(current_img)
                if rect:
                    self._draw_zoomed_image(current_img, rect, zoom_controller)
                else:
                    self._draw_centered_image(current_img)
        else:
            rect = image_manager.get_rect(current_img)
            if rect:
                self._draw_zoomed_image(current_img, rect, zoom_controller)
            else:
                self._draw_centered_image(current_img)
        
        # Blit viewport to main screen
        self.screen.blit(self.viewport, self.viewport_rect)
        
        # Draw instructions
        # self._draw_instructions()
        
        # Update display
        pygame.display.flip()
    
    def _draw_transition(self, transition_manager):
        """Draw transition frame. Returns True if frame was drawn, False otherwise."""
        self.viewport.fill((0, 0, 0))
        frame = transition_manager.get_current_frame()
        if frame:
            x = (self.viewport_dims[0] - frame.get_width()) / 2
            y = (self.viewport_dims[1] - frame.get_height()) / 2
            self.viewport.blit(frame, (x, y))
            return True
        return False
    
    def _draw_centered_image(self, image_data):
        """Draw image centered in viewport"""
        img_width = image_data.surface.get_width()
        img_height = image_data.surface.get_height()
        x = self.viewport_dims[0] / 2 - img_width / 2
        y = self.viewport_dims[1] / 2 - img_height / 2
        
        self.viewport.fill((0, 0, 0))
        self.viewport.blit(image_data.surface, (x, y))
    
    def _draw_zoomed_image(self, image_data, rect, zoom_controller):
        """Draw zoomed image with rectangle"""
        img_surface = image_data.surface
        scale = zoom_controller.scale
        normalized_zoom = zoom_controller.get_normalized_zoom()
        
        # Calculate rect's relative position
        rect_center_x = rect.x + rect.width / 2
        rect_center_y = rect.y + rect.height / 2
        relative_x = rect_center_x / img_surface.get_width()
        relative_y = rect_center_y / img_surface.get_height()
        
        # Calculate anchor points
        img_point_x = img_surface.get_width() * relative_x
        img_point_y = img_surface.get_height() * relative_y
        
        rect_local_x = rect.width * relative_x
        rect_local_y = rect.height * relative_y
        rect_point_x = rect.x + rect_local_x
        rect_point_y = rect.y + rect_local_y
        
        viewport_anchor_x = self.viewport_dims[0] * relative_x
        viewport_anchor_y = self.viewport_dims[1] * relative_y
        
        # Interpolate focus point
        focus_x = img_point_x + (rect_point_x - img_point_x) * normalized_zoom
        focus_y = img_point_y + (rect_point_y - img_point_y) * normalized_zoom
        
        # Position image
        image_pos_x = viewport_anchor_x - focus_x * scale
        image_pos_y = viewport_anchor_y - focus_y * scale
        
        # Scale image (with crop optimization for high zoom)
        image_scaled, adjusted_pos_x, adjusted_pos_y = self._scale_image_optimized(
            image_data, scale, image_pos_x, image_pos_y, img_surface
        )
        
        # Calculate rect position in viewport
        rect_viewport_x = rect.x * scale + image_pos_x
        rect_viewport_y = rect.y * scale + image_pos_y
        rect_viewport_w = rect.width * scale
        rect_viewport_h = rect.height * scale
        
        # Draw
        self.viewport.fill((0, 0, 0))
        self.viewport.blit(image_scaled, (adjusted_pos_x, adjusted_pos_y))
        outline_rect = pygame.Rect(
            round(rect_viewport_x),
            round(rect_viewport_y),
            round(rect_viewport_w),
            round(rect_viewport_h)
        )
        pygame.draw.rect(self.viewport, 'red', outline_rect, 2)
    
    def _scale_image_optimized(self, image_data, scale, image_pos_x, image_pos_y, img_surface):
        """Scale image with crop optimization at high zoom levels"""
        CROP_THRESHOLD = 1.5
        
        if scale < CROP_THRESHOLD:
            # Low zoom: simple scaling
            target_width = max(1, int(img_surface.get_width() * scale))
            target_height = max(1, int(img_surface.get_height() * scale))
            scale_fn = pygame.transform.smoothscale if self.smoothing_enabled else pygame.transform.scale
            image_scaled = scale_fn(img_surface, (target_width, target_height))
            return image_scaled, image_pos_x, image_pos_y
        else:
            # High zoom: crop then scale for performance
            visible_left = max(0, -image_pos_x)
            visible_top = max(0, -image_pos_y)
            visible_right = min(img_surface.get_width() * scale, 
                               self.viewport_dims[0] - image_pos_x)
            visible_bottom = min(img_surface.get_height() * scale,
                                self.viewport_dims[1] - image_pos_y)
            
            original_scale_factor = image_data.scale
            margin = 2
            
            crop_left = (visible_left / scale / original_scale_factor) - margin
            crop_top = (visible_top / scale / original_scale_factor) - margin
            crop_right = (visible_right / scale / original_scale_factor) + margin
            crop_bottom = (visible_bottom / scale / original_scale_factor) + margin
            
            original = image_data.original
            crop_left = max(0, min(int(crop_left), original.get_width()))
            crop_top = max(0, min(int(crop_top), original.get_height()))
            crop_right = max(0, min(int(crop_right), original.get_width()))
            crop_bottom = max(0, min(int(crop_bottom), original.get_height()))
            
            crop_width = crop_right - crop_left
            crop_height = crop_bottom - crop_top
            
            if crop_width > 0 and crop_height > 0:
                cropped = original.subsurface((crop_left, crop_top, crop_width, crop_height))
                final_width = int(crop_width * original_scale_factor * scale)
                final_height = int(crop_height * original_scale_factor * scale)
                
                if final_width > 0 and final_height > 0:
                    scale_fn = pygame.transform.smoothscale if self.smoothing_enabled else pygame.transform.scale
                    image_scaled = scale_fn(cropped, (final_width, final_height))
                    adjusted_pos_x = image_pos_x + (crop_left * original_scale_factor * scale)
                    adjusted_pos_y = image_pos_y + (crop_top * original_scale_factor * scale)
                    return image_scaled, adjusted_pos_x, adjusted_pos_y
            
            # Fallback
            target_width = max(1, int(img_surface.get_width() * scale))
            target_height = max(1, int(img_surface.get_height() * scale))
            scale_fn = pygame.transform.smoothscale if self.smoothing_enabled else pygame.transform.scale
            image_scaled = scale_fn(img_surface, (target_width, target_height))
            return image_scaled, image_pos_x, image_pos_y
    
    def _draw_instructions(self):
        """Draw on-screen instructions"""
        instructions = "⬆ Zoom In    ⬇ Zoom Out    D: Debug"
        instr_surface = self.font.render(instructions, True, (153, 153, 153))
        instr_x = (self.screen.get_width() - instr_surface.get_width()) / 2
        self.screen.blit(instr_surface, (instr_x, self.screen.get_height() - 20))
    
    def _draw_fps(self, fps, debug_mode, perf_stats, avg_frame_time):
        """Draw FPS counter and performance stats"""
        # Color code FPS based on performance
        if fps >= 55:
            color = (0, 255, 0)  # Green - excellent
        elif fps >= 45:
            color = (255, 255, 0)  # Yellow - good
        elif fps >= 30:
            color = (255, 165, 0)  # Orange - acceptable
        else:
            color = (255, 0, 0)  # Red - poor
        
        fps_text = f"FPS: {fps:.1f}"
        fps_surface = self.font.render(fps_text, True, color)
        self.screen.blit(fps_surface, (10, 10))
        
        if debug_mode and perf_stats:
            y_offset = 35
            line_height = 18
            
            # Frame time
            frame_text = f"Frame: {avg_frame_time:.1f}ms"
            frame_surface = self.small_font.render(frame_text, True, (200, 200, 200))
            self.screen.blit(frame_surface, (10, y_offset))
            y_offset += line_height
            
            # Component breakdown
            input_text = f"Input:  {perf_stats['input']:.1f}ms"
            update_text = f"Update: {perf_stats['update']:.1f}ms"
            render_text = f"Render: {perf_stats['render']:.1f}ms"
            
            input_surface = self.small_font.render(input_text, True, (150, 150, 150))
            update_surface = self.small_font.render(update_text, True, (150, 150, 150))
            render_surface = self.small_font.render(render_text, True, (150, 150, 150))
            
            self.screen.blit(input_surface, (10, y_offset))
            y_offset += line_height
            self.screen.blit(update_surface, (10, y_offset))
            y_offset += line_height
            self.screen.blit(render_surface, (10, y_offset))
            y_offset += line_height
            
            # Performance tips for RPi
            target_frame_time = 1000 / 60  # 16.67ms for 60 FPS
            if avg_frame_time > target_frame_time:
                tip = "Tip: Consider lowering resolution"
                if perf_stats['render'] > 12:
                    tip = "Tip: Render bottleneck - reduce viewport"
                tip_surface = self.small_font.render(tip, True, (255, 100, 100))
                self.screen.blit(tip_surface, (10, y_offset))
