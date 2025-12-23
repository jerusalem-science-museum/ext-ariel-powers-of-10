"""
Powers of Ten Viewer - Refactored version with proper separation of concerns
Main application that coordinates all components
"""
import pygame
import json
from .image_manager import ImageManager
from .zoom_controller import ZoomController
from .transition_manager import TransitionManager
from .renderer import Renderer
from .input_handler import InputHandler


class ZoomViewer:
    """Main application coordinator"""
    
    def __init__(self, smoothing_enabled=True):
        pygame.init()
        
        # Display setup
        flags = pygame.FULLSCREEN
        self.screen = pygame.display.set_mode(flags=flags)
        pygame.display.set_caption("Powers of Ten Viewer")

        # Load configuration
        with open('config.json', 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.viewport_dims = self.config['setup']['viewportDims']
        self.viewport_rect = pygame.Rect(*self.config['setup']['viewportTL'], *self.viewport_dims)
        
        # Font setup
        self.font = pygame.font.SysFont('Arial', 16)

        
        # Initialize components
        self.image_manager = ImageManager(self.config, self.viewport_dims)
        self.image_manager.load_images()
        
        self.zoom_controller = ZoomController()
        # Set initial max scale
        self.zoom_controller.set_max_scale(
            self.image_manager.get_current_image().max_scale
        )
        
        self.transition_manager = TransitionManager(self.config, self.viewport_dims, smoothing_enabled=smoothing_enabled)
        self.transition_manager.load_all_transitions()
        
        self.renderer = Renderer(self.screen, self.viewport_dims, self.viewport_rect, self.font, smoothing_enabled=smoothing_enabled)
        
        self.input_handler = InputHandler()
        
        # Clock for frame rate control
        self.clock = pygame.time.Clock()
        self.FPS = 60
        
    
    def _handle_input(self, dt):
        """Process input events and handle actions"""
        actions = self.input_handler.process_events(self.transition_manager.is_active(), dt)
        
        for action in actions:
            if action[0] == 'quit':
                return False  # Signal to stop running
            elif action[0] == 'zoom_step':
                self.zoom_controller.zoom_step(action[1])
            elif action[0] == 'zoom_continuous':
                self.zoom_controller.zoom_continuous(action[1], action[2])  # direction, dt
            elif action[0] == 'toggle_debug':
                self.debug_mode = not self.debug_mode 
                print(f"Debug mode: {'ON' if self.debug_mode else 'OFF'}")
        
        return True  # Continue running
    
    def _handle_boundary_transition(self, boundary_direction):
        """Handle zoom boundary crossing and image transitions"""
        # Check if we can navigate in the boundary direction
        if boundary_direction == 'forward':
            next_image_exists = self.image_manager.can_go_next()
        else:  # 'backward'
            next_image_exists = self.image_manager.can_go_previous()
        
        if next_image_exists:
            # Start the transition animation
            self.transition_manager.start_transition(boundary_direction)
        else:
            # Can't transition - clamp scale to boundaries
            self.zoom_controller.clamp_scale()
    
    def _update_state(self, dt_ms=None):
        """Update zoom and transition state"""
        
        # Update zoom state and check boundaries
        boundary_direction = self.zoom_controller.update()
        if boundary_direction:
            self._handle_boundary_transition(boundary_direction)
        
        # Update transition animation
        transition_complete = self.transition_manager.update(dt_ms=dt_ms)
        if transition_complete:
            # Transition just finished - sync image manager to match transition manager position
            self.image_manager.set_image(self.transition_manager.transition_idx)
            
            # Update max scale for new image
            self.zoom_controller.set_max_scale(
                self.image_manager.get_current_image().max_scale
            )
            
            # Reset zoom to appropriate level based on direction
            if self.transition_manager.transition_direction == 'backward':
                self.zoom_controller.reset_to_max()
            else:
                self.zoom_controller.reset_to_min()
        
        return transition_complete
    
    def _render_frame(self):
        """Render current frame"""
        self.renderer.draw_frame(self.image_manager, self.zoom_controller, self.transition_manager)
        
    def run(self):
        """Main game loop"""
        running = True
        
        while running:
            frame_start = pygame.time.get_ticks()
            dt = self.clock.get_time() / 1000.0
            
            # Process input
            running = self._handle_input(dt)
            if not running:
                break
            
            # Update state
            self._update_state()
            
            # Render
            self._render_frame()
            
            # Control frame rate
            self.clock.tick(self.FPS)
        
        pygame.quit()


if __name__ == "__main__":
    viewer = ZoomViewer()
    viewer.run()
