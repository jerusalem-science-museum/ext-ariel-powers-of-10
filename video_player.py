import pygame
import cv2
import numpy as np
import os
import subprocess
import time
import json
# Initialize Pygame
pygame.init()

# Toggle exe mode: if True, uses videos from same folder as script with native FPS
# If False, loads videos from config.json
is_exe = True

# Screen setup

screen = pygame.display.set_mode(flags=pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
pygame.display.set_caption("Video Scrubber")

# Load config and set video paths
if is_exe:
    print('Using files in same location as script')
    # Video paths in same folder as script
    video_path = "video.mp4"
    reversed_video_path = "video_reversed.mp4"
    config = {}  # Empty config for exe mode
else:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    # Video paths from config
    video_path = os.path.join('data', 'videos', config['videoPlayer']['videoPaths']['video'])
    reversed_video_path = os.path.join('data', 'videos', config['videoPlayer']['videoPaths']['reversedVideo'])

# Create reversed video if it doesn't exist
if not os.path.exists(reversed_video_path):
    print("Creating reversed video...")
    subprocess.run([
        'ffmpeg', '-i', video_path,
        '-vf', 'reverse',
        '-c:v', 'mpeg4',
        reversed_video_path
    ])
    print("Reversed video created!")

# OpenCV video setup
print("Loading videos...")

print("Using default OpenCV backend...")
cap_forward = cv2.VideoCapture(video_path)
cap_backward = cv2.VideoCapture(reversed_video_path)

caps = {'forward': cap_forward, 'backward': cap_backward}
current_dir = 'forward'
# Verify videos opened successfully
if not cap_forward.isOpened():
    print(f"ERROR: Could not open forward video: {video_path}")
    exit(1)
if not cap_backward.isOpened():
    print(f"ERROR: Could not open backward video: {reversed_video_path}")
    exit(1)

print("✓ Videos loaded successfully")

# Get video properties
fps = cap_forward.get(cv2.CAP_PROP_FPS)
total_frames = int(cap_forward.get(cv2.CAP_PROP_FRAME_COUNT))
total_frames_backward = int(cap_backward.get(cv2.CAP_PROP_FRAME_COUNT))

# Get playback FPS from config (if null or exe mode, use video's native FPS)
if is_exe:
    playback_fps = fps  # Always use native FPS in exe mode
else:
    playback_fps = config.get('videoPlayer', {}).get('playbackFPS')
    if playback_fps is None:
        playback_fps = fps
    else:
        playback_fps = float(playback_fps)

print(f"Video properties:")
print(f"  Forward: {total_frames} frames @ {fps} FPS (native)")
print(f"  Backward: {total_frames_backward} frames")
print(f"  Playback: {playback_fps} FPS")
if total_frames != total_frames_backward:
    print(f"  ⚠ WARNING: Frame count mismatch!")
if total_frames <= 0:
    print(f"  ⚠ ERROR: Invalid frame count! Video backend may not support this format.")
    exit(1)
print()

# Current playback position (in forward video frame numbers)
current_frame = 0
last_frame = None

# Read the first frame immediately so it displays on startup
cap_forward.set(cv2.CAP_PROP_POS_FRAMES, 0)
ret, first_frame = cap_forward.read()
if ret:
    last_frame = first_frame
    print("✓ First frame loaded")
else:
    print("⚠ WARNING: Could not read first frame")

# Playback state
is_playing_forward = False
is_playing_backward = False

# UI state
show_overlay = False  # Toggle with 'd' key (shows all info including instructions)

# Performance tracking
timing_log = []

# Main loop
clock = pygame.time.Clock()
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            # if event.key in [pygame.K_UP, pygame.K_DOWN]:
            if event.key == pygame.K_UP:
                # Start timing
                # action = 'forward' if event.key == pygame.K_UP else 'backward'
                t_start = time.perf_counter()
                timing = {'action': f'UP_KEY_PRESS', 'stages': {}}
                

                # Switch to forward playback
                if not is_playing_forward:
                    is_playing_forward = True
                    is_playing_backward = False
                    
                    t0 = time.perf_counter()
                    # Sync forward video to current position
                    cap_forward.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
                    t1 = time.perf_counter()
                    timing['stages']['seek'] = (t1 - t0) * 1000  # ms
                    
                    # Read first frame immediately
                    t0 = time.perf_counter()
                    ret, frame = cap_forward.read()
                    t1 = time.perf_counter()
                    timing['stages']['read_frame'] = (t1 - t0) * 1000  # ms
                    
                    if ret:
                        last_frame = frame
                        # Don't increment yet - will happen on next loop iteration
                    
                    t_end = time.perf_counter()
                    timing['total_ms'] = (t_end - t_start) * 1000
                    timing_log.append(timing)
                    
                    print(f"\n▶ UP pressed: {timing['total_ms']:.2f}ms total")
                    print(f"  - Seek to frame {current_frame}: {timing['stages']['seek']:.2f}ms")
                    print(f"  - Read frame: {timing['stages']['read_frame']:.2f}ms")
                    
            elif event.key == pygame.K_DOWN:
                # Start timing
                t_start = time.perf_counter()
                timing = {'action': 'DOWN_KEY_PRESS', 'stages': {}}
                
                # Switch to backward playback
                if not is_playing_backward:
                    is_playing_backward = True
                    is_playing_forward = False
                    
                    # Sync backward video to mirrored position
                    # Reversed video: frame 0 of reversed = frame (total-1) of forward
                    backward_frame = (total_frames - 1) - current_frame
                    
                    print(f"  DEBUG: current_frame={current_frame}, total_frames={total_frames}, backward_frame={backward_frame}")
                    
                    t0 = time.perf_counter()
                    cap_backward.set(cv2.CAP_PROP_POS_FRAMES, backward_frame)
                    t1 = time.perf_counter()
                    timing['stages']['seek'] = (t1 - t0) * 1000  # ms
                    
                    # Read first frame immediately
                    t0 = time.perf_counter()
                    ret, frame = cap_backward.read()
                    t1 = time.perf_counter()
                    timing['stages']['read_frame'] = (t1 - t0) * 1000  # ms
                    
                    if ret:
                        last_frame = frame
                        # Don't decrement yet - will happen on next loop iteration
                    
                    t_end = time.perf_counter()
                    timing['total_ms'] = (t_end - t_start) * 1000
                    timing_log.append(timing)
                    
                    print(f"\n▼ DOWN pressed: {timing['total_ms']:.2f}ms total")
                    print(f"  - Seek to backward frame {backward_frame}: {timing['stages']['seek']:.2f}ms")
                    print(f"  - Read frame: {timing['stages']['read_frame']:.2f}ms")
            elif event.key == pygame.K_d:
                # Toggle overlay display
                show_overlay = not show_overlay
                print(f"Overlay: {'ON' if show_overlay else 'OFF'}")
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_UP:
                is_playing_forward = False
            elif event.key == pygame.K_DOWN:
                is_playing_backward = False
    
    # Read frame if playing (sequential read, no seeking)
    if is_playing_forward:
        ret, frame = cap_forward.read()
        if ret:
            last_frame = frame
            current_frame = min(current_frame + 1, total_frames - 1)
        else:
            # Reached end
            is_playing_forward = False
            current_frame = total_frames - 1
    elif is_playing_backward:
        ret, frame = cap_backward.read()
        if ret:
            last_frame = frame
            current_frame = max(current_frame - 1, 0)
        else:
            # Reached beginning
            is_playing_backward = False
            current_frame = 0
    
    # Display the last frame
    if last_frame is not None:
        t0 = time.perf_counter()
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(last_frame, cv2.COLOR_BGR2RGB)
        t1 = time.perf_counter()
        
        # Convert to pygame surface (transpose for correct orientation)
        frame_surface = pygame.surfarray.make_surface(np.transpose(frame_rgb, (1, 0, 2)))
        t2 = time.perf_counter()
        
        # Scale to fit screen
        frame_surface = pygame.transform.scale(frame_surface, (WIDTH, HEIGHT))
        t3 = time.perf_counter()
        
        screen.blit(frame_surface, (0, 0))
        t4 = time.perf_counter()
        
        # Track rendering times (only log occasionally to avoid spam)
        if current_frame % 100 == 0:
            print(f"\nRender timings at frame {current_frame}:")
            print(f"  - BGR→RGB: {(t1-t0)*1000:.2f}ms")
            print(f"  - Make surface: {(t2-t1)*1000:.2f}ms")
            print(f"  - Scale: {(t3-t2)*1000:.2f}ms")
            print(f"  - Blit: {(t4-t3)*1000:.2f}ms")
    else:
        screen.fill((0, 0, 0))
    
    # Display info overlay (only if show_overlay is True)
    if show_overlay:
        font = pygame.font.Font(None, 36)
        
        current_time = current_frame / fps if fps > 0 else 0
        total_time = total_frames / fps if fps > 0 else 0
        
        # Show FPS info if playback FPS differs from native FPS
        show_fps_info = abs(playback_fps - fps) > 0.1
        
        # Calculate background height based on what we're showing
        lines_to_show = 2  # Time and Frame always shown
        if show_fps_info:
            lines_to_show += 1  # FPS line
        lines_to_show += 1  # Instructions line
        bg_height = 30 + (lines_to_show * 30)  # 10px padding top, 30px per line
        
        # Semi-transparent background for text
        info_bg = pygame.Surface((WIDTH, bg_height))
        info_bg.set_alpha(128)
        info_bg.fill((0, 0, 0))
        screen.blit(info_bg, (0, 0))
        
        info_text = font.render(f"Time: {current_time:.1f}s / {total_time:.1f}s", True, (255, 255, 255))
        frame_text = font.render(f"Frame: {current_frame}/{total_frames}", True, (255, 255, 255))
        
        y_offset = 10
        screen.blit(info_text, (10, y_offset))
        y_offset += 30
        screen.blit(frame_text, (10, y_offset))
        y_offset += 30
        
        if show_fps_info:
            fps_text = font.render(f"FPS: {fps:.1f} (native) → {playback_fps:.1f} (playback)", True, (255, 255, 255))
            screen.blit(fps_text, (10, y_offset))
            y_offset += 30
        
        controls_text = font.render("UP: Play Forward | DOWN: Play Backward (hold)", True, (255, 255, 255))
        screen.blit(controls_text, (10, y_offset))
    
    pygame.display.flip()
    clock.tick(int(playback_fps))  # Use configurable playback FPS

# Print performance summary before exit
print("\n" + "="*60)
print("PERFORMANCE SUMMARY")
print("="*60)
if timing_log:
    seek_times = [t['stages'].get('seek', 0) for t in timing_log]
    read_times = [t['stages'].get('read_frame', 0) for t in timing_log]
    total_times = [t['total_ms'] for t in timing_log]
    
    print(f"\nKey press events analyzed: {len(timing_log)}")
    print(f"\nSeek times:")
    print(f"  Min: {min(seek_times):.2f}ms")
    print(f"  Max: {max(seek_times):.2f}ms")
    print(f"  Avg: {sum(seek_times)/len(seek_times):.2f}ms")
    print(f"\nRead frame times:")
    print(f"  Min: {min(read_times):.2f}ms")
    print(f"  Max: {max(read_times):.2f}ms")
    print(f"  Avg: {sum(read_times)/len(read_times):.2f}ms")
    print(f"\nTotal key-to-frame times:")
    print(f"  Min: {min(total_times):.2f}ms")
    print(f"  Max: {max(total_times):.2f}ms")
    print(f"  Avg: {sum(total_times)/len(total_times):.2f}ms")
print("="*60 + "\n")

# Cleanup
cap_forward.release()
cap_backward.release()
pygame.quit()