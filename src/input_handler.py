"""
Input Handler - Processes user input
"""
import pygame


class InputHandler:
    """Handles keyboard input and timing"""
    
    def __init__(self):
        self.last_key_time = {}
        self.key_delay = 200  # Milliseconds before continuous zoom starts
    
    def process_events(self, transition_active, dt):
        """Process all input (events + continuous) and return actions"""
        actions = []
        current_time = pygame.time.get_ticks()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                actions.append(('quit', None))
            
            # Ignore input during transition
            elif not transition_active:
                if event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_UP, pygame.K_DOWN]:
                        self.last_key_time[event.key] = current_time
                        
                        if event.key == pygame.K_UP:
                            actions.append(('zoom_step', 'in'))
                        elif event.key == pygame.K_DOWN:
                            actions.append(('zoom_step', 'out'))
                    
                    elif event.key == pygame.K_d:
                        actions.append(('toggle_debug', None))
                
                elif event.type == pygame.KEYUP:
                    if event.key in self.last_key_time:
                        del self.last_key_time[event.key]
        
        # Check for continuous zoom
        if not transition_active:
            keys = pygame.key.get_pressed()
            
            for key in [pygame.K_UP, pygame.K_DOWN]:
                if (key in self.last_key_time and 
                    current_time - self.last_key_time[key] > self.key_delay and 
                    keys[key]):
                    
                    direction = 'in' if key == pygame.K_UP else 'out'
                    actions.append(('zoom_continuous', direction, dt))
                    break  # Only one continuous zoom at a time
        
        return actions
