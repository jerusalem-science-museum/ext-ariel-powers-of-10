import cv2
import os
import sys

def convert_video_to_frames(video_path, output_dir="frames", quality=95):
    """Convert video to image sequence"""
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return False
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Converting video: {video_path}")
    print(f"FPS: {fps}, Total frames: {total_frames}")
    
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Save frame as JPG
        frame_path = os.path.join(output_dir, f"frame_{frame_count:06d}.jpg")
        cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        
        frame_count += 1
        if frame_count % 100 == 0:
            print(f"Processed {frame_count}/{total_frames} frames...")
    
    cap.release()
    
    # Save metadata
    metadata_path = os.path.join(output_dir, "metadata.txt")
    with open(metadata_path, 'w') as f:
        f.write(f"fps={fps}\n")
        f.write(f"total_frames={frame_count}\n")
    
    print(f"✓ Conversion complete! {frame_count} frames saved to {output_dir}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_to_frames.py <video_file> [output_dir] [quality]")
        print("Example: python convert_to_frames.py video.mp4 frames 95")
        sys.exit(1)
    
    video_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "frames"
    quality = int(sys.argv[3]) if len(sys.argv) > 3 else 95
    
    convert_video_to_frames(video_path, output_dir, quality)
