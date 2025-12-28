"""
Convert transition frames to MP4 video
Converts all frame_*.png and frame_*.jpeg files in a transition folder to a single MP4 video.
"""
import os
import sys
import glob
from pathlib import Path


def convert_transition_to_video(transition_folder, output_filename="transition.mp4", fps=24):
    """
    Convert all frame files in a transition folder to an MP4 video using ffmpeg.
    
    Args:
        transition_folder: Path to folder containing frame_*.png and frame_*.jpeg files
        output_filename: Name of output video file (default: transition.mp4)
        fps: Frames per second for the output video (default: 24)
    """
    transition_folder = Path(transition_folder)
    
    if not transition_folder.exists():
        print(f"Error: Transition folder not found: {transition_folder}")
        return False
    
    # Find all frame files (both PNG and JPEG)
    frame_patterns = [
        str(transition_folder / "frame_*.png"),
        str(transition_folder / "frame_*.jpeg"),
        str(transition_folder / "frame_*.jpg"),
    ]
    
    frame_files = []
    for pattern in frame_patterns:
        frame_files.extend(glob.glob(pattern))
    
    if not frame_files:
        print(f"Error: No frame files found in {transition_folder}")
        return False
    
    # Sort frame files by their numeric index
    def get_frame_number(filename):
        """Extract frame number from filename like frame__000000.png"""
        basename = os.path.basename(filename)
        # Extract number after frame_ or frame__
        try:
            # Handle both frame_000000.png and frame__000000.png
            # Replace frame__ first, then frame_ to handle double underscore correctly
            if basename.startswith('frame__'):
                num_str = basename.replace('frame__', '').split('.')[0]
            elif basename.startswith('frame_'):
                num_str = basename.replace('frame_', '').split('.')[0]
            else:
                return 0
            return int(num_str)
        except (ValueError, IndexError):
            return 0
    
    frame_files.sort(key=get_frame_number)
    
    # Verify sorting
    print(f"Found {len(frame_files)} frame files")
    print(f"First frame: {os.path.basename(frame_files[0])}")
    print(f"Last frame: {os.path.basename(frame_files[-1])}")
    # Check a few frames around the PNG/JPEG transition
    if len(frame_files) > 20:
        print(f"Frame 15: {os.path.basename(frame_files[15])}")
        print(f"Frame 16: {os.path.basename(frame_files[16])}")
        print(f"Frame 17: {os.path.basename(frame_files[17])}")
    
    print(f"Found {len(frame_files)} frame files")
    print(f"First frame: {os.path.basename(frame_files[0])}")
    print(f"Last frame: {os.path.basename(frame_files[-1])}")
    
    output_path = transition_folder / output_filename
    
    # Use ffmpeg to create video from image sequence
    # ffmpeg -framerate 24 -pattern_type glob -i "frame_*.png" -c:v libx264 -pix_fmt yuv420p -crf 18 output.mp4
    
    # Build ffmpeg command
    # We'll use a different approach: create a temporary file list for ffmpeg
    # This handles mixed PNG/JPEG formats better
    
    # Use ffmpeg concat demuxer to encode directly from image sequence
    # This avoids double encoding and ensures proper frame timing
    file_list_path = transition_folder / "ffmpeg_file_list.txt"
    try:
        with open(file_list_path, 'w', encoding='utf-8') as f:
            for frame_file in frame_files:
                # Use absolute path with forward slashes (Windows ffmpeg handles this)
                abs_path = os.path.abspath(frame_file).replace('\\', '/')
                # Write file path with duration for proper timing
                f.write(f"file '{abs_path}'\n")
                f.write(f"duration {1.0/fps}\n")
            # Repeat last frame to ensure proper duration
            if frame_files:
                abs_path = os.path.abspath(frame_files[-1]).replace('\\', '/')
                f.write(f"file '{abs_path}'\n")
        
        print(f"\nConverting to {output_path} at {fps} fps...")
        print(f"Found {len(frame_files)} frames to process")
        print("Encoding directly with ffmpeg...")
        
        # Encode directly with ffmpeg - single pass, proper timing
        import subprocess
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output
            '-f', 'concat',
            '-safe', '0',
            '-i', str(file_list_path),
            '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',  # Ensure dimensions divisible by 2
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-crf', '18',  # High quality
            '-preset', 'medium',
            '-r', str(fps),  # Output frame rate
            '-g', str(fps),  # GOP size (keyframe every second)
            '-bf', '2',  # B-frames
            '-movflags', '+faststart',  # Enable streaming
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error: ffmpeg encoding failed with return code {result.returncode}")
            print("stderr:", result.stderr[:2000])  # Limit output
            return False
    
        # Get video info
        video_size = output_path.stat().st_size / (1024 * 1024)  # MB
        print(f"\nForward video complete!")
        print(f"  Output: {output_path}")
        print(f"  Size: {video_size:.2f} MB")
        print(f"  Frames: {len(frame_files)}")
        print(f"  FPS: {fps}")
        
        # Create reversed video for backward playback
        reversed_filename = output_filename.replace('.mp4', '_reversed.mp4')
        reversed_path = transition_folder / reversed_filename
        print(f"\nCreating reversed video: {reversed_path}")
        
        reverse_cmd = [
            'ffmpeg',
            '-y',
            '-i', str(output_path),
            '-vf', 'reverse',
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-crf', '18',
            '-preset', 'medium',
            '-movflags', '+faststart',
            str(reversed_path)
        ]
        
        reverse_result = subprocess.run(reverse_cmd, capture_output=True, text=True)
        
        if reverse_result.returncode != 0:
            print(f"Warning: Reversed video creation failed: {reverse_result.stderr[:500]}")
            return True  # Still return success since forward video was created
        
        reversed_size = reversed_path.stat().st_size / (1024 * 1024)  # MB
        print(f"Reversed video complete!")
        print(f"  Output: {reversed_path}")
        print(f"  Size: {reversed_size:.2f} MB")
        
        return True
    finally:
        # Clean up temporary file list
        if file_list_path.exists():
            file_list_path.unlink()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_transition_to_video.py <transition_folder> [output_filename] [fps]")
        print("Example: python convert_transition_to_video.py data/transitions/6 transition.mp4 24")
        sys.exit(1)
    
    transition_folder = sys.argv[1]
    output_filename = sys.argv[2] if len(sys.argv) > 2 else "transition.mp4"
    fps = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    
    success = convert_transition_to_video(transition_folder, output_filename, fps)
    sys.exit(0 if success else 1)

