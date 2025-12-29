
import pygame
import numpy as np
import cv2
from src.viewer import ZoomViewer
from tqdm import tqdm
import subprocess
import json
import os

class Recorder(ZoomViewer):
    """
    Runs the viewer and records the full zoom-in with transitions to a video file.
    Uses H.264 with simple settings for fast seeking (~20ms) and good quality.
    """
    def __init__(self, crf=18):
        """
        Initialize recorder with H.264 encoding for fast seeking and good quality.
        
        Args:
            crf: Constant Rate Factor (15-23, lower = better quality, larger file)
                 15-18 = high quality, 20 = good quality, 23 = balanced
        """
        super().__init__()
        self.filename = 'video.mp4'
        self.fps = 30
        self.rate_of_slowness = 1.6  # Speed multiplier for zooming
        
        # Get screen dimensions
        width, height = self.screen.get_size()
        
        # Create ffmpeg process for H.264 encoding
        self.ffmpeg_process = self._create_ffmpeg_encoder(width, height, crf)
        
    def _create_ffmpeg_encoder(self, width, height, crf):
        """Create ffmpeg process that accepts raw video frames via stdin - H.264 with simple settings for fast seeking"""
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{width}x{height}',
            '-pix_fmt', 'bgr24',  # OpenCV uses BGR
            '-r', str(self.fps),
            '-i', '-',  # Read from stdin
            '-an',  # No audio
            '-c:v', 'libx264',  # H.264 codec
            '-preset', 'slow',  # Fast preset for reasonable encoding speed
            '-crf', str(crf),  # Quality setting (lower = better quality)
            '-profile:v', 'high422',  # High422 profile (required for yuv422p - better color resolution)
            '-pix_fmt', 'yuv422p',  # 4:2:2 chroma (better color resolution, reduces red flickering)
            '-g', '1',  # GOP size of 1 = every frame is a keyframe for instant seeking
            '-bf', '0',  # No B-frames (required for GOP=1)
            '-movflags', '+faststart',  # Enable fast start for web playback
            self.filename
        ]
        
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0  # Unbuffered for immediate error detection
        )
        
        print(f"Encoding video with H.264 (CRF {crf}, every frame keyframe) - fast seeking with good quality")
        print(f"Output: {self.filename} ({width}x{height} @ {self.fps} fps)")
        
        return process

    def run(self):
        # Fixed time step per frame (1/fps seconds) - ensures transitions advance independently of rendering speed
        fixed_dt_ms = 1000.0 / self.fps
        
        with tqdm(total=len(self.image_manager.images), desc="image # being processed") as pbar:
            while self.image_manager.current_index < len(self.image_manager.images) - 1:
                # Process input
                if not self.transition_manager.is_active():
                    self.zoom_controller.zoom_continuous('in', 1/(self.fps*self.rate_of_slowness))

                # Update state with fixed time step (transitions advance by fixed amount per frame)
                transition_complete = self._update_state(dt_ms=fixed_dt_ms)
                
                if transition_complete:
                    pbar.update(1)
                    
                # Render
                self._render_frame()
                
                # Write frame to video (convert RGB to BGR for OpenCV/ffmpeg)
                frame_bgr = cv2.cvtColor(
                    np.array(pygame.surfarray.pixels3d(self.screen).swapaxes(0, 1)), 
                    cv2.COLOR_RGB2BGR
                )
                
                # Write raw frame data to ffmpeg stdin
                try:
                    self.ffmpeg_process.stdin.write(frame_bgr.tobytes())
                except BrokenPipeError:
                    # ffmpeg exited early - get error message
                    stdout, stderr = self.ffmpeg_process.communicate()
                    error_msg = stderr.decode('utf-8', errors='ignore')
                    print(f"Error: ffmpeg exited early with code {self.ffmpeg_process.returncode}")
                    print("ffmpeg error output:")
                    print(error_msg)
                    raise

        # Close stdin to signal end of input
        self.ffmpeg_process.stdin.close()
        
        # Wait for ffmpeg to finish encoding
        stdout, stderr = self.ffmpeg_process.communicate()
        
        if self.ffmpeg_process.returncode != 0:
            print(f"Warning: ffmpeg exited with code {self.ffmpeg_process.returncode}")
            print("Error output:", stderr.decode('utf-8', errors='ignore'))
        else:
            # Get file size for user info
            file_size_mb = os.path.getsize(self.filename) / (1024 * 1024)
            print(f"Video recording complete: {self.filename} ({file_size_mb:.2f} MB)")

def reverse_video(filename):
    output_file = "video_reversed.mp4"
    
    # Check if input file exists
    if not os.path.exists(filename):
        print(f"Error: Video file '{filename}' not found.")
        print("Please run the recorder first to create the video file.")
        return
    
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
    r_frame_rate = stream.get('r_frame_rate', '30/1')  # Default to 30 fps
    pix_fmt = stream.get('pix_fmt', 'yuv420p')
    
    # Parse frame rate (format: "30/1")
    if '/' in r_frame_rate:
        num, den = map(int, r_frame_rate.split('/'))
        fps = num / den if den != 0 else 30
    else:
        fps = float(r_frame_rate)
    
    # Build command - use same H.264 encoding as recording
    cmd = [
        "ffmpeg", "-i", filename,
        "-vf", "reverse",
        "-c:v", "libx264",  # H.264 codec
        "-preset", "slow",  # slow.
        "-crf", "18",  # High quality (match recording quality)
        "-profile:v", "high422",  # High422 profile (required for yuv422p - better color resolution)
        "-pix_fmt", "yuv422p",  # 4:2:2 chroma (better color resolution, reduces red flickering)
        "-g", "1",  # GOP size of 1 = every frame is a keyframe for instant seeking
        "-bf", "0",  # No B-frames (required for GOP=1)
        "-movflags", "+faststart",  # Enable fast start
        "-y",  # Overwrite output
        output_file
    ]
    
    print(f"Reversing video with H.264 encoding (every frame keyframe)...")
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    
    if os.path.exists(output_file):
        file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
        print(f"Reversed video created: {output_file} ({file_size_mb:.2f} MB)")
    else:
        print("Warning: Reversed video file was not created")


if __name__ == "__main__":
    recorder = Recorder()
    recorder.run()
    reverse_video(recorder.filename)