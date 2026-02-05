import pygame
import cv2
import numpy as np
import os
import glob
import threading

# Initialize Pygame
pygame.init()

# Screen setup
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Image Sequence Player")

# Load frames directory
frames_dir = "sample transitions/non"
if not os.path.exists(frames_dir):
    print(f"Error: Frames directory '{frames_dir}' not found!")
    print("Run convert_to_frames.py first to create the image sequence.")
    pygame.quit()
    exit(1)

# Load metadata
metadata_path = os.path.join(frames_dir, "metadata.txt")
fps = 24.0  # default
total_frames = 0

if os.path.exists(metadata_path):
    with open(metadata_path, 'r') as f:
        for line in f:
            if line.startswith('fps='):
                fps = float(line.split('=')[1])
            elif line.startswith('total_frames='):
                total_frames = int(line.split('=')[1])

# Get list of frame files
frame_files = sorted(glob.glob(os.path.join(frames_dir, "frame_*.jpg")))
if not frame_files:
    print(f"Error: No frame images found in '{frames_dir}'")
    pygame.quit()
    exit(1)

total_frames = len(frame_files)
print(f"Loaded {total_frames} frames at {fps} FPS")

# Current playback state
current_frame = 0
last_displayed_frame = None
is_playing_forward = False
is_playing_backward = False

# Cache for loaded images (sliding window with predictive loading)
USE_CACHE = True
CACHE_SIZE = 200  # Keep 200 frames in memory
surface_cache = {}  # Cache pygame surfaces instead of raw images
cache_order = []  # Track order for LRU eviction
preload_lock = threading.Lock()

def load_and_convert_frame(frame_index):
    """Load a frame and convert to pygame surface"""
    if 0 <= frame_index < total_frames:
        frame = cv2.imread(frame_files[frame_index])
        if frame is not None:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Convert to pygame surface and cache the surface, not the raw image
            frame_surface = pygame.surfarray.make_surface(np.transpose(frame_rgb, (1, 0, 2)))
            # Scale once and cache the scaled version
            frame_surface = pygame.transform.scale(frame_surface, (WIDTH, HEIGHT))
            return frame_surface
    return None

def load_frame(frame_index):
    """Load a frame surface from disk or cache with LRU eviction"""
    with preload_lock:
        if frame_index in surface_cache:
            # Move to end (most recently used)
            if frame_index in cache_order:
                cache_order.remove(frame_index)
                cache_order.append(frame_index)
            return surface_cache[frame_index]
        
        surface = load_and_convert_frame(frame_index)
        if surface is not None:
            # Add to cache
            surface_cache[frame_index] = surface
            cache_order.append(frame_index)
            
            # Evict oldest if cache is full
            while len(cache_order) > CACHE_SIZE:
                oldest = cache_order.pop(0)
                if oldest in surface_cache:
                    del surface_cache[oldest]
        return surface

def preload_frames_ahead(current_frame, direction, count=60):
    """Preload frames in the direction of playback in background thread"""
    def preload_worker():
        if direction > 0:  # Forward
            for i in range(current_frame + 1, min(current_frame + count + 1, total_frames)):
                if i not in surface_cache:
                    load_frame(i)
        elif direction < 0:  # Backward
            for i in range(current_frame - 1, max(current_frame - count - 1, -1), -1):
                if i not in surface_cache:
                    load_frame(i)
    
    # Run preloading in background
    thread = threading.Thread(target=preload_worker, daemon=True)
    thread.start()

# Load initial frame and preload nearby frames
last_displayed_frame = load_frame(0)
print("Preloading initial frames...")
preload_frames_ahead(0, 1, 50)  # Preload first 50 frames
print("✓ Ready!")

# Main loop
clock = pygame.time.Clock()
running = True
last_preload_frame = 0

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                is_playing_forward = True
                is_playing_backward = False
            elif event.key == pygame.K_DOWN:
                is_playing_backward = True
                is_playing_forward = False
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_UP:
                is_playing_forward = False
            elif event.key == pygame.K_DOWN:
                is_playing_backward = False
    
    # Update frame based on playback state
    if is_playing_forward:
        current_frame = min(current_frame + 1, total_frames - 1)
        frame = load_frame(current_frame)
        if frame is not None:
            last_displayed_frame = frame
        # Preload ahead every 5 frames
        if current_frame % 5 == 0 and current_frame != last_preload_frame:
            preload_frames_ahead(current_frame, 1, 60)
            last_preload_frame = current_frame
    elif is_playing_backward:
        current_frame = max(current_frame - 1, 0)
        frame = load_frame(current_frame)
        if frame is not None:
            last_displayed_frame = frame
        # Preload ahead every 5 frames
        if current_frame % 5 == 0 and current_frame != last_preload_frame:
            preload_frames_ahead(current_frame, -1, 60)
            last_preload_frame = current_frame
    
    # Display the current frame (already a pygame surface)
    if last_displayed_frame is not None:
        screen.blit(last_displayed_frame, (0, 0))
    else:
        screen.fill((0, 0, 0))
    
    # Display info overlay
    font = pygame.font.Font(None, 36)
    
    current_time = current_frame / fps if fps > 0 else 0
    total_time = total_frames / fps if fps > 0 else 0
    
    # Semi-transparent background for text
    info_bg = pygame.Surface((WIDTH, 100))
    info_bg.set_alpha(128)
    info_bg.fill((0, 0, 0))
    screen.blit(info_bg, (0, 0))
    
    status = "Playing Forward" if is_playing_forward else ("Playing Backward" if is_playing_backward else "Paused")
    status_text = font.render(f"{status} - {current_time:.1f}s / {total_time:.1f}s", True, (255, 255, 255))
    frame_text = font.render(f"Frame: {current_frame}/{total_frames}", True, (255, 255, 255))
    controls_text = font.render("UP: Play Forward | DOWN: Play Backward (hold)", True, (255, 255, 255))
    
    screen.blit(status_text, (10, 10))
    screen.blit(frame_text, (10, 40))
    screen.blit(controls_text, (10, 70))
    
    pygame.display.flip()
    clock.tick(int(fps))

# Cleanup
pygame.quit()
