"""
Transition Manager - Handles transition animations between images
"""
import pygame
import os
import cv2
import numpy as np


class TransitionManager:
    """Manages transition animations between images"""
    
    def __init__(self, config, viewport_dims, smoothing_enabled=True):
        self.config = config
        self.viewport_dims = viewport_dims
        self.smoothing_enabled = smoothing_enabled
        
        # All transitions loaded at startup (indexed by source image)
        # Each entry is either:
        # - List of pygame surfaces (PNG-based transitions)
        # - Dict with 'video_path', 'frame_count', 'fps' (video-based transitions)
        self.transitions = []
        
        # Current position (stays in sync with ImageManager by moving ±1)
        self.transition_idx = 0
        
        # Current playback state
        self.is_transitioning = False
        self.current_transition_data = None  # Active transition data (frames list or video dict)
        self.current_transition_frames = []  # For PNG-based transitions
        self.current_video_cap = None  # For video-based transitions
        self.current_cached_frame = None  # Cached pygame surface for current video frame
        self.video_ended = False  # Track if video has ended (for video transitions)
        self.transition_frame_index = 0  # Only used for PNG-based transitions
        self.current_video_frame_index = 0  # Track current frame number for video transitions
        self.target_video_frame_index = None  # Target frame position for time-based video seeking
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
        """Load transition from a specific folder. Checks for video first, falls back to PNG frames."""
        if not os.path.exists(transition_folder):
            print(f"Warning: Transition directory not found: {transition_folder}")
            return []
        
        # Check for video file first
        video_path = os.path.join(transition_folder, "transition.mp4")
        if os.path.exists(video_path):
            return self._load_transition_video(video_path, image_index)
        
        # Fall back to PNG/JPEG frames
        return self._load_transition_frames(transition_folder, image_index)
    
    def _load_transition_video(self, video_path, image_index):
        """Load transition metadata from video file"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Warning: Could not open video {video_path}, falling back to frames")
            return self._load_transition_frames(os.path.dirname(video_path), image_index)
        
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        # Check for reversed video
        video_dir = os.path.dirname(video_path)
        video_basename = os.path.basename(video_path)
        reversed_path = os.path.join(video_dir, video_basename.replace('.mp4', '_reversed.mp4'))
        has_reversed = os.path.exists(reversed_path)
        
        print(f"  Loading transition {image_index}: Video with {frame_count} frames @ {fps:.1f} fps from {video_path}")
        if has_reversed:
            print(f"    Found reversed video: {reversed_path}")
        
        # Return dict with video metadata (will be loaded on-demand)
        return {
            'type': 'video',
            'video_path': video_path,
            'reversed_path': reversed_path if has_reversed else None,
            'frame_count': frame_count,
            'fps': fps,
            'width': width,
            'height': height
        }
    
    def _load_transition_frames(self, transition_folder, image_index):
        """Load transition frames from PNG/JPEG files"""
        frames = []
        
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
        
        # Get the transition data
        self.current_transition_data = self.transitions[idx]
        
        # Close any existing video capture
        if self.current_video_cap is not None:
            self.current_video_cap.release()
            self.current_video_cap = None
        
        # Initialize based on transition type
        if isinstance(self.current_transition_data, dict) and self.current_transition_data.get('type') == 'video':
            # Video-based transition - play as continuous stream
            self.current_transition_frames = []  # Not used for video
            
            # Use reversed video for backward playback if available
            if direction == 'backward' and self.current_transition_data.get('reversed_path'):
                video_path = self.current_transition_data['reversed_path']
            else:
                video_path = self.current_transition_data['video_path']
            
            self.current_video_cap = cv2.VideoCapture(video_path)
            if not self.current_video_cap.isOpened():
                print(f"Error: Could not open video {video_path}")
                self.is_transitioning = False
                return
            
            self.video_ended = False
        else:
            # PNG-based transition
            self.current_transition_frames = self.current_transition_data
            self.current_video_cap = None
            self.video_ended = False
        
        self.current_cached_frame = None
        self.is_transitioning = True
        self.transition_frame_index = 0
        self.current_video_frame_index = 0
        self.target_video_frame_index = None
        self.transition_start_time = pygame.time.get_ticks()
        self.manual_elapsed_ms = 0
        self.transition_direction = direction
    
    def update(self, dt_ms=None):
        """
        Update transition animation and return completion status
        For video transitions:
        - If dt_ms is provided: uses time-based frame calculation and seeking
        - If dt_ms is None: uses real-time sequential frame reading
        Completion is determined by video_ended flag or calculated frame exceeding frame count.
        For PNG transitions, completion is determined by frame count.
        """
        if not self.is_transitioning:
            return False
        
        # For video transitions
        if isinstance(self.current_transition_data, dict) and self.current_transition_data.get('type') == 'video':
            if self.video_ended:
                # Transition complete - move position
                self.is_transitioning = False
                if self.current_video_cap is not None:
                    self.current_video_cap.release()
                    self.current_video_cap = None
                self.current_cached_frame = None
                if self.transition_direction == 'forward':
                    self.transition_idx += 1
                else:  # 'backward'
                    self.transition_idx -= 1
                return True
            
            # Time-based video playback (when dt_ms is provided)
            if dt_ms is not None:
                # Track elapsed time
                self.manual_elapsed_ms += dt_ms
                elapsed_seconds = self.manual_elapsed_ms / 1000.0
                
                # Calculate target frame position based on video fps
                video_fps = self.current_transition_data.get('fps', 30)
                target_frame = int(elapsed_seconds * video_fps)
                frame_count = self.current_transition_data.get('frame_count', 0)
                
                # Clamp to valid range
                if target_frame >= frame_count:
                    # Transition complete - mark as ended
                    self.video_ended = True
                    self.is_transitioning = False
                    if self.current_video_cap is not None:
                        self.current_video_cap.release()
                        self.current_video_cap = None
                    self.current_cached_frame = None
                    if self.transition_direction == 'forward':
                        self.transition_idx += 1
                    else:  # 'backward'
                        self.transition_idx -= 1
                    return True
                
                # Set target frame index (will be used by get_current_frame to seek)
                # For reversed videos, we're already playing a reversed video file, so frame index is forward
                self.target_video_frame_index = target_frame
                self.current_video_frame_index = target_frame  # Update immediately for background changes
                
                # Invalidate cache so get_current_frame will seek to the new position
                self.current_cached_frame = None
            else:
                # Real-time playback (no dt_ms provided) - invalidate cache to read next frame
                self.current_cached_frame = None
            
            return False
        
        # For PNG-based transitions, use frame index calculation
        if dt_ms is None:
            current_time = pygame.time.get_ticks()
            elapsed = current_time - self.transition_start_time
        else:
            self.manual_elapsed_ms += dt_ms
            elapsed = self.manual_elapsed_ms
        
        # Calculate which frame to show
        frame_duration = 1000 / self.transition_fps
        target_frame = int(elapsed / frame_duration)
        frame_count = len(self.current_transition_frames) if self.current_transition_frames else 0
        
        if target_frame >= frame_count or frame_count == 0:
            # Transition complete - move position
            self.is_transitioning = False
            self.current_cached_frame = None
            if self.transition_direction == 'forward':
                self.transition_idx += 1
            else:  # 'backward'
                self.transition_idx -= 1
            return True
        else:
            # Update frame index - reverse if going backward
            if self.transition_direction == 'backward':
                self.transition_frame_index = frame_count - 1 - target_frame
            else:
                self.transition_frame_index = target_frame
            return False
    
    def get_current_frame(self):
        """Get the current transition frame (pygame surface)
        For video transitions:
        - If time-based (dt_ms provided in update()): seeks to calculated frame position
        - If real-time (no dt_ms): reads frames sequentially from video stream
        For PNG transitions, returns frame by index.
        """
        if not self.is_transitioning or self.current_transition_data is None:
            return None
        
        # Handle video-based transitions
        if isinstance(self.current_transition_data, dict) and self.current_transition_data.get('type') == 'video':
            if self.current_video_cap is None or self.video_ended:
                return None
            
            # Use cached frame if available (only read new frame when needed)
            if self.current_cached_frame is not None:
                return self.current_cached_frame
            
            # Time-based seeking (when target_video_frame_index is set)
            if self.target_video_frame_index is not None:
                # Seek to the target frame position
                self.current_video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.target_video_frame_index)
                ret, frame_bgr = self.current_video_cap.read()
                
                if not ret:
                    # Video has ended or frame doesn't exist
                    self.video_ended = True
                    return None
                
                # Clear target (already seeked)
                self.target_video_frame_index = None
            else:
                # Real-time sequential playback (no dt_ms provided)
                # Read next frame from video stream (sequential read, no seeking needed)
                # If using reversed video, it's already reversed so just read forward
                ret, frame_bgr = self.current_video_cap.read()
                
                if not ret:
                    # Video has ended
                    self.video_ended = True
                    return None
                
                # Increment video frame index for sequential playback
                self.current_video_frame_index += 1
            
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            
            # Convert to pygame surface
            frame_surface = pygame.surfarray.make_surface(np.transpose(frame_rgb, (1, 0, 2)))
            
            # Scale frame to fit viewport (matching PNG scaling behavior)
            scale = min(self.viewport_dims[0] / frame_surface.get_width(), 
                       self.viewport_dims[1] / frame_surface.get_height())
            new_size = (int(frame_surface.get_width() * scale),
                       int(frame_surface.get_height() * scale))
            scale_fn = pygame.transform.smoothscale if self.smoothing_enabled else pygame.transform.scale
            scaled_frame = scale_fn(frame_surface, new_size)
            
            # Cache the frame (will be invalidated when we need a new frame)
            self.current_cached_frame = scaled_frame
            return scaled_frame
        
        # Handle PNG-based transitions
        if self.transition_frame_index < len(self.current_transition_frames):
            return self.current_transition_frames[self.transition_frame_index]
        
        return None
    
    def is_active(self):
        """Check if transition is currently playing"""
        return self.is_transitioning
    
    def get_active_bg_path(self):
        """Return the bg path active during the current transition frame, or None if no
        transitionBackgroundChanges entry currently applies."""
        if not self.is_transitioning:
            return None

        if self.transition_direction == 'forward':
            img_idx = self.transition_idx
        else:
            img_idx = self.transition_idx - 1

        bg_changes = self.config['images'][img_idx].get('transitionBackgroundChanges')
        if not bg_changes:
            return None

        if isinstance(self.current_transition_data, dict) and self.current_transition_data.get('type') == 'video':
            current_frame = self.current_video_frame_index
        else:
            current_frame = self.transition_frame_index
            if self.transition_direction == 'backward':
                frame_count = len(self.current_transition_frames) if self.current_transition_frames else 0
                current_frame = frame_count - 1 - current_frame

        active_frame = -1
        active_bg = None
        for change in bg_changes:
            if change['frame'] <= current_frame and change['frame'] > active_frame:
                active_frame = change['frame']
                active_bg = change['bg']
        return active_bg

    def get_current_background(self, current_img_bg):
        """Get background for current transition frame, loading on-demand from config"""
        bg_path = self.get_active_bg_path()
        if bg_path and os.path.exists(bg_path):
            return pygame.image.load(bg_path).convert_alpha()
        return current_img_bg
