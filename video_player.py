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
idle_timeout_ms = config['videoPlayer'].get('idleTimeoutSeconds', 60) * 1000
last_frame_hold_ms = config['videoPlayer'].get('lastFrameSeconds', 2) * 1000

# Load audio cues sidecar (optional). Cue frame indices are in forward-video coordinates;
# the player's current_frame is also forward-video coordinates in both play directions.
cues_by_frame = {}
cues_path = 'video_audio_cues.json'
if os.path.exists(cues_path):
    with open(cues_path, 'r', encoding='utf-8') as f:
        cues_data = json.load(f)
    for cue in cues_data.get('cues', []):
        audio = cue.get('audio')
        if audio:
            cues_by_frame[cue['frame']] = audio
    print(f"Loaded {len(cues_by_frame)} narration cues from {cues_path}")
else:
    print(f"No {cues_path} found - narration disabled")

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
pygame.mixer.init()
screen = pygame.display.set_mode((1920,1080), pygame.FULLSCREEN | pygame.SCALED)
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

# Idle auto-zoom state
last_activity_time = pygame.time.get_ticks()
idle_auto_playing = False
idle_hold_until = 0  # when > 0, holding on end/start frame until this time (ms)
idle_enabled = True  # when False, idle autoplay will not start

# Narration playback state
narration_channel = None
narration_playing = False
last_cue_frame = None
narration_sound_cache = {}

def stop_narration():
    global narration_playing, narration_channel, last_cue_frame
    if narration_channel is not None:
        narration_channel.stop()
    narration_channel = None
    narration_playing = False
    last_cue_frame = None

def maybe_trigger_narration():
    """If autoplaying and current_frame matches a cue, pause playback and play narration."""
    global narration_playing, narration_channel, last_cue_frame, is_playing
    if not idle_auto_playing or narration_playing:
        return
    audio_path = cues_by_frame.get(current_frame)
    if audio_path is None or current_frame == last_cue_frame:
        return
    if audio_path not in narration_sound_cache:
        if not os.path.exists(audio_path):
            print(f"Narration file missing: {audio_path}")
            last_cue_frame = current_frame
            return
        narration_sound_cache[audio_path] = pygame.mixer.Sound(audio_path)
    last_cue_frame = current_frame
    is_playing = False
    narration_channel = narration_sound_cache[audio_path].play()
    narration_playing = True

# Main loop
clock = pygame.time.Clock()
running = True

while running:
    now_ms = pygame.time.get_ticks()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_ESCAPE) and narration_playing:
                stop_narration()
            if event.key == pygame.K_UP:
                # While key is held, disable idle autoplay from starting
                idle_enabled = False
                # Exit auto-zoom if active
                if idle_auto_playing:
                    idle_auto_playing = False
                    idle_hold_until = 0
                # Always switch to forward, even if already playing forward
                current_video = 'forward'
                cap_forward.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
                ret, frame = cap_forward.read()
                if ret:
                    last_frame = frame
                is_playing = True
                just_switched = True
            elif event.key == pygame.K_DOWN:
                # While key is held, disable idle autoplay from starting
                idle_enabled = False
                # Exit auto-zoom if active
                if idle_auto_playing:
                    idle_auto_playing = False
                    idle_hold_until = 0
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
            
            # When the user releases UP or DOWN, treat that as the end of activity
            if event.key in (pygame.K_UP, pygame.K_DOWN):
                idle_enabled = True
                last_activity_time = pygame.time.get_ticks()
                if idle_auto_playing:
                    idle_auto_playing = False
                idle_hold_until = 0
    
    # Check for idle timeout and start auto-zoom
    if idle_enabled and not idle_auto_playing and idle_hold_until == 0 and (pygame.time.get_ticks() - last_activity_time) >= idle_timeout_ms:
        idle_auto_playing = True
        last_cue_frame = None
        current_video = 'forward'
        cap_forward.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        ret, frame = cap_forward.read()
        if ret:
            last_frame = frame
        is_playing = True
        just_switched = True
    
    # If we're holding on end/start frame, wait until hold time elapses then switch direction
    if idle_hold_until > 0 and now_ms >= idle_hold_until:
        idle_hold_until = 0
        last_cue_frame = None
        if current_video == 'forward':
            current_video = 'backward'
            cap_backward.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap_backward.read()
            if ret:
                last_frame = frame
            is_playing = True
            just_switched = True
        else:
            current_video = 'forward'
            cap_forward.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap_forward.read()
            if ret:
                last_frame = frame
            is_playing = True
            just_switched = True
    
    # If narration finished, resume playback
    if narration_playing and (narration_channel is None or not narration_channel.get_busy()):
        narration_playing = False
        narration_channel = None
        if idle_auto_playing:
            is_playing = True

    # Read frame if playing
    if is_playing and not just_switched and idle_hold_until == 0 and not narration_playing:
        if current_video == 'forward':
            ret, frame = cap_forward.read()
            if ret:
                last_frame = frame
                current_frame = min(current_frame + 1, total_frames - 1)
                maybe_trigger_narration()
                # Ping-pong: if we reached the end during auto-zoom, hold then switch to backward
                if idle_auto_playing and current_frame == total_frames - 1:
                    idle_hold_until = now_ms + last_frame_hold_ms
                    is_playing = False
                    just_switched = True
            else:
                if idle_auto_playing:
                    current_frame = total_frames - 1
                    idle_hold_until = now_ms + last_frame_hold_ms
                    is_playing = False
                    just_switched = True
                else:
                    is_playing = False
                    current_frame = total_frames - 1
        else:
            ret, frame = cap_backward.read()
            if ret:
                last_frame = frame
                current_frame = max(current_frame - 1, 0)
                maybe_trigger_narration()
                # Ping-pong: if we reached the start during auto-zoom, hold then switch to forward
                if idle_auto_playing and current_frame == 0:
                    idle_hold_until = now_ms + last_frame_hold_ms
                    is_playing = False
                    just_switched = True
            else:
                if idle_auto_playing:
                    current_frame = 0
                    idle_hold_until = now_ms + last_frame_hold_ms
                    is_playing = False
                    just_switched = True
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
