
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
    def __init__(self):
        super().__init__()
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.filename = 'video.mp4'
        self.fps = 30
        self.video = cv2.VideoWriter(self.filename, fourcc, self.fps, self.screen.get_size())
        self.rate_of_slowness = 1.5  # Speed multiplier for zooming

    def run(self):

        prev_array = None
        frame_count = 0
        # Fixed time step per frame (1/fps seconds)
        fixed_dt_ms = 1000.0 / self.fps
        with tqdm(total=len(self.image_manager.images), desc="image # being processed") as pbar:
            while self.image_manager.current_index < len(self.image_manager.images) - 1:
                # Process input
                if not self.transition_manager.is_active():
                    self.zoom_controller.zoom_continuous('in', 1/(self.fps*self.rate_of_slowness))

                # Update state with fixed time step (ensures transitions advance by fixed amount per frame)
                transition_complete = self._update_state(dt_ms=fixed_dt_ms)
                
                if transition_complete:
                    pbar.update(1)
                # Render
                self._render_frame()
                
                self.video.write(
                    cv2.cvtColor(
                        np.array(pygame.surfarray.pixels3d(self.screen).swapaxes(0, 1)), 
                        cv2.COLOR_RGB2BGR
                    )
                )

        self.video.release()
        
        print(f"Prerendered video with {frame_count} unique frames")

def reverse_video(filename):
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
    r_frame_rate = stream.get('r_frame_rate', '30/1')  # Default to 30 fps
    pix_fmt = stream.get('pix_fmt', 'yuv420p')
    
    # Parse frame rate (format: "30/1")
    if '/' in r_frame_rate:
        num, den = map(int, r_frame_rate.split('/'))
        fps = num / den if den != 0 else 30
    else:
        fps = float(r_frame_rate)
    
    # Build command
    cmd = [
        "ffmpeg", "-i", filename,
        "-vf", "reverse",
        "-c:v", "mpeg4",  # Match mp4v FourCC used in run()
        "-profile:v", "0",
        "-pix_fmt", pix_fmt,
        "-r", str(int(fps)),
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
    recorder = Recorder()
    recorder.run()
    # reverse_video(recorder.filename)
    reverse_video("video.mp4")