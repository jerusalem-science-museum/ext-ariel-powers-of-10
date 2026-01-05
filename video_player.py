import pygame
import cv2
import numpy as np
import os
import json

# Load config and set video paths
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
#video_path = os.path.join('data', 'videos', config['videoPlayer']['videoPaths']['video'])
#reversed_video_path = os.path.join('data', 'videos', config['videoPlayer']['videoPaths']['reversedVideo'])
video_path = config['videoPlayer']['videoPaths']['video']
reversed_video_path = config['videoPlayer']['videoPaths']['reversedVideo']
# OpenCV video setup
cap_forward = cv2.VideoCapture(video_path)
cap_backward = cv2.VideoCapture(reversed_video_path)

if not cap_forward.isOpened() or not cap_backward.isOpened():
    print("ERROR: Could not open videos")
    exit(1)

# Get video properties
fps = cap_forward.get(cv2.CAP_PROP_FPS)
total_frames = int(cap_forward.get(cv2.CAP_PROP_FRAME_COUNT))

if total_frames <= 0:
    print("ERROR: Invalid frame count!")
    exit(1)

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode(flags=pygame.FULLSCREEN | pygame.DOUBLEBUF)
WIDTH, HEIGHT = screen.get_size()
pygame.display.set_caption("Video Scrubber")

# Current playback position
current_frame = 0
last_frame = None

# Read first frame
cap_forward.set(cv2.CAP_PROP_POS_FRAMES, 0)
ret, first_frame = cap_forward.read()
if ret:
    last_frame = first_frame

# Playback state
is_playing = False
current_video = 'forward'
just_switched = False

# Main loop
clock = pygame.time.Clock()
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                # Always switch to forward, even if already playing forward
                current_video = 'forward'
                cap_forward.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
                ret, frame = cap_forward.read()
                if ret:
                    last_frame = frame
                is_playing = True
                just_switched = True
            elif event.key == pygame.K_DOWN:
                # Always switch to backward, even if already playing backward
                current_video = 'backward'
                backward_frame = (total_frames - 1) - current_frame
                cap_backward.set(cv2.CAP_PROP_POS_FRAMES, backward_frame)
                ret, frame = cap_backward.read()
                if ret:
                    last_frame = frame
                is_playing = True
                just_switched = True
            elif event.key == pygame.K_ESCAPE:
                running = False
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_UP:
                # Only stop if we're still playing forward
                if current_video == 'forward':
                    is_playing = False
            elif event.key == pygame.K_DOWN:
                # Only stop if we're still playing backward
                if current_video == 'backward':
                    is_playing = False
    
    # Read frame if playing
    if is_playing and not just_switched:
        if current_video == 'forward':
            ret, frame = cap_forward.read()
            if ret:
                last_frame = frame
                current_frame = min(current_frame + 1, total_frames - 1)
            else:
                is_playing = False
                current_frame = total_frames - 1
        else:
            ret, frame = cap_backward.read()
            if ret:
                last_frame = frame
                current_frame = max(current_frame - 1, 0)
            else:
                is_playing = False
                current_frame = 0
    
    just_switched = False
    
    # Display the last frame
    if last_frame is not None:
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(last_frame, cv2.COLOR_BGR2RGB)
        
        # Convert to pygame surface (transpose for correct orientation)
        frame_surface = pygame.surfarray.make_surface(np.transpose(frame_rgb, (1, 0, 2)))
        
        # Scale to fit screen
        frame_surface = pygame.transform.scale(frame_surface, (WIDTH, HEIGHT))
        
        screen.blit(frame_surface, (0, 0))
    else:
        screen.fill((0, 0, 0))
    
    pygame.display.flip()
    clock.tick(int(fps) if fps > 0 else 30)

# Cleanup
cap_forward.release()
cap_backward.release()
pygame.quit()
