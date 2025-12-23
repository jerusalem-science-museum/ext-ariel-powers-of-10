
import pygame
import numpy as np
import cv2
from src.viewer import ZoomViewer
from tqdm import tqdm
import subprocess
import json

class Recorder(ZoomViewer):
    """
    Runs the viewer and records the full zoom-in with transitions to a video file.
    """
    def __init__(self, target_fps=24, output_filename='video.mp4', rate_of_slowness=1.5, disable_antialias=True):
        smoothing_enabled = not disable_antialias
        super().__init__(smoothing_enabled=smoothing_enabled)
        self.filename = output_filename
        self.fps = float(target_fps)
        self.rate_of_slowness = rate_of_slowness  # Speed multiplier for zooming

        self.transition_manager.transition_fps = self.fps

        # Pipe frames directly to ffmpeg for H.264 encoding (no intermediate file)
        width, height = self.screen.get_size()
        self.ffmpeg_process = self._create_ffmpeg_pipe(self.filename, self.fps, width, height)

    def _create_ffmpeg_pipe(self, filename, fps, width, height):
        """Create an ffmpeg process that accepts raw video frames via stdin"""
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{width}x{height}',
            '-pix_fmt', 'bgr24',
            '-r', str(fps),
            '-i', '-',  # Read from stdin
            '-an',  # No audio
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '18',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            filename
        ]
        
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print(f"Encoding directly to H.264 ({filename}) at {fps} fps")
        return process

    def run(self):

        prev_array = None
        frame_count = 0
        width, height = self.screen.get_size()
        with tqdm(total=len(self.image_manager.images), desc="image # being processed") as pbar:
            while True:
                # Fixed time step ensures constant motion regardless of render speed
                dt_seconds = 1.0 / (self.fps * self.rate_of_slowness)
                dt_ms = 1000.0 / self.fps

                # Advance zoom while not in transition
                if not self.transition_manager.is_active():
                    self.zoom_controller.zoom_continuous('in', dt_seconds)

                # Update state
                transition_complete = self._update_state(dt_ms=dt_ms)
                
                if transition_complete:
                    pbar.update(1)
                # Render
                self._render_frame()
                
                # Convert screen to BGR numpy array and write to ffmpeg stdin
                frame_bgr = cv2.cvtColor(
                    np.array(pygame.surfarray.pixels3d(self.screen).swapaxes(0, 1)), 
                    cv2.COLOR_RGB2BGR
                )
                self.ffmpeg_process.stdin.write(frame_bgr.tobytes())
                frame_count += 1
                
                # Exit when we've reached the last image (after completing transition to it)
                if self.image_manager.current_index >= len(self.image_manager.images) - 1:
                    break

        # Close stdin and wait for ffmpeg to finish
        self.ffmpeg_process.stdin.close()
        self.ffmpeg_process.wait()
        
        if self.ffmpeg_process.returncode != 0:
            stderr = self.ffmpeg_process.stderr.read().decode()
            raise RuntimeError(f"ffmpeg encoding failed: {stderr}")
        
        print(f"Prerendered video with {frame_count} frames: {self.filename}")

def reverse_video(filename, fps):
    output_file = "video_reversed.mp4"
    
    # Get original video properties using ffprobe
    probe_cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=bit_rate,width,height,r_frame_rate,pix_fmt",
        "-of", "json", filename
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    probe_data = json.loads(result.stdout)
    stream = probe_data['streams'][0]
    
    # Extract properties
    bitrate = stream.get('bit_rate', None)
    width = stream.get('width')
    height = stream.get('height')
    pix_fmt = stream.get('pix_fmt', 'yuv420p')
    
    # Build command
    cmd = [
        "ffmpeg", "-i", filename,
        "-vf", "reverse",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", pix_fmt,
        "-r", str(int(fps)),
        "-movflags", "+faststart",
    ]
    
    # Add bitrate if available
    if bitrate:
        cmd.extend(["-b:v", bitrate])
    
    # Add resolution
    if width and height:
        cmd.extend(["-s", f"{width}x{height}"])
    
    # Add output file
    cmd.append("-y")  # Overwrite output
    cmd.append(output_file)
    
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    recorder = Recorder(target_fps=24, output_filename='video.mp4', rate_of_slowness=1.5, disable_antialias=False)
    recorder.run()
    reverse_video(recorder.filename, fps=recorder.fps)
    # reverse_video("video.mp4", fps=24)