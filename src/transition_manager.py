"""
Transition Manager - Handles transition animations between images
"""
import pygame
import os


class TransitionManager:
    """Manages transition animations between images"""
    
    def __init__(self, config, viewport_dims, smoothing_enabled=True):
        self.config = config
        self.viewport_dims = viewport_dims
        self.smoothing_enabled = smoothing_enabled
        
        # All transitions loaded at startup (indexed by source image)
        self.transitions = []  # List of frame lists
        
        # Current position (stays in sync with ImageManager by moving ±1)
        self.transition_idx = 0
        
        # Current playback state
        self.is_transitioning = False
        self.current_transition_frames = []  # Active transition being played
        self.transition_frame_index = 0
        self.transition_start_time = None
        self.manual_elapsed_ms = 0
        self.transition_fps = 30
        self.transition_direction = None
    
    def load_all_transitions(self):
        """Load all transitions from config at startup (eager loading)"""
        print("Loading all transition animations...")
        
        for i, img_config in enumerate(self.config['images']):
            transition_folder = img_config.get('transitionFolder')
            
            if transition_folder:
                frames = self._load_transition_folder(transition_folder, i)
                self.transitions.append(frames)
            else:
                # No transition for this image - add empty list
                self.transitions.append([])
                if i < len(self.config['images']) - 1:  # Not last image
                    print(f"Warning: No transition folder for image {i}. loading empty transition.")
        
        print(f"Loaded {len(self.transitions)} transition sets")
    
    def _load_transition_folder(self, transition_folder, image_index):
        """Load transition frames from a specific folder"""
        frames = []
        
        if not os.path.exists(transition_folder):
            print(f"Warning: Transition directory not found: {transition_folder}")
            return frames
        
        # Filter for only frame_* files (e.g., frame_0001.png, frame_0002.png)
        frame_files = sorted([f for f in os.listdir(transition_folder) 
                             if f.startswith('frame_')])
        
        if not frame_files:
            print(f"Warning: No frame_* files found in {transition_folder}")
            return frames
        
        print(f"  Loading transition {image_index}: {len(frame_files)} frames from {transition_folder}")
        
        for frame_file in frame_files:
            frame_path = os.path.join(transition_folder, frame_file)
            frame = pygame.image.load(frame_path).convert_alpha()
            
            # Scale frame to fit viewport
            scale = min(self.viewport_dims[0] / frame.get_width(), 
                       self.viewport_dims[1] / frame.get_height())
            new_size = (int(frame.get_width() * scale),
                       int(frame.get_height() * scale))
            scale_fn = pygame.transform.smoothscale if self.smoothing_enabled else pygame.transform.scale
            scaled_frame = scale_fn(frame, new_size)
            
            frames.append(scaled_frame)
        
        return frames
    
    def start_transition(self, direction):
        """Start transition animation going forward or backward from current position"""
        # Determine which transition to play based on direction
        if direction == 'forward':
            idx = self.transition_idx
        else:  # 'backward'
            idx = self.transition_idx - 1
        
        # Get the transition frames

        self.current_transition_frames = self.transitions[idx]
        self.is_transitioning = True
        self.transition_frame_index = 0
        self.transition_start_time = pygame.time.get_ticks()
        self.manual_elapsed_ms = 0
        self.transition_direction = direction
    
    def update(self, dt_ms=None):
        """
        Update transition animation and return completion status
        if no transition folder exists, will complete immediately.
        """
        if not self.is_transitioning:
            return False
        
        if dt_ms is None:
            current_time = pygame.time.get_ticks()
            elapsed = current_time - self.transition_start_time
        else:
            self.manual_elapsed_ms += dt_ms
            elapsed = self.manual_elapsed_ms
        
        # Calculate which frame to show
        frame_duration = 1000 / self.transition_fps
        target_frame = int(elapsed / frame_duration)
        
        if target_frame >= len(self.current_transition_frames): # complete if done or no frames (i.e. cuurrent_transition_frames is len 0)
            # Transition complete - move position
            self.is_transitioning = False
            if self.transition_direction == 'forward':
                self.transition_idx += 1
            else:  # 'backward'
                self.transition_idx -= 1
            return True
        else:
            # Update frame index - reverse if going backward
            if self.transition_direction == 'backward':
                self.transition_frame_index = len(self.current_transition_frames) - 1 - target_frame
            else:
                self.transition_frame_index = target_frame
            return False
    
    def get_current_frame(self):
        """Get the current transition frame"""
        if self.transition_frame_index < len(self.current_transition_frames):
            return self.current_transition_frames[self.transition_frame_index]
        return None
    
    def is_active(self):
        """Check if transition is currently playing"""
        return self.is_transitioning
