import subprocess
import json
import os

def get_video_bitrate_and_resolution(file_path):
    """
    Extract video bitrate and resolution using ffprobe
    """
    try:
        # Run ffprobe to get video stream information in JSON format
        result = subprocess.run([
            'ffprobe', 
            '-v', 'quiet', 
            '-print_format', 'json', 
            '-show_streams', 
            '-select_streams', 'v:0', 
            file_path
        ], capture_output=True, text=True)
        
        # Parse the JSON output
        probe_data = json.loads(result.stdout)
        
        # Extract bitrate and resolution
        video_stream = probe_data['streams'][0]
        bitrate = int(video_stream.get('bit_rate', 0)) / 1000  # Convert to kbps
        width = int(video_stream.get('width', 0))
        height = int(video_stream.get('height', 0))
        
        return bitrate, width, height
    
    except Exception as e:
        print(f"Error analyzing video: {e}")
        return None, None, None

def categorize_bitrate(bitrate, width, height):
    """
    Categorize bitrate based on resolution and bitrate
    """
    # Categorization based on resolution and typical bitrate recommendations
    if width <= 0 or height <= 0:
        return "Unable to determine resolution"
    
    # Calculate pixels
    pixels = width * height
    
    # Bitrate categories for different resolutions
    categories = {
        # 4K (3840x2160)
        (3840 * 2160, float('inf')): {
            'low': (10000, 'Low bitrate for 4K'),
            'medium': (20000, 'Medium bitrate for 4K'),
            'high': (float('inf'), 'High bitrate for 4K')
        },
        # 1080p (1920x1080)
        (1920 * 1080, 3840 * 2160): {
            'low': (5000, 'Low bitrate for 1080p'),
            'medium': (10000, 'Medium bitrate for 1080p'),
            'high': (float('inf'), 'High bitrate for 1080p')
        },
        # 720p (1280x720)
        (1280 * 720, 1920 * 1080): {
            'low': (2500, 'Low bitrate for 720p'),
            'medium': (5000, 'Medium bitrate for 720p'),
            'high': (float('inf'), 'High bitrate for 720p')
        },
        # SD (640x480 or lower)
        (0, 1280 * 720): {
            'low': (1000, 'Low bitrate for SD'),
            'medium': (2500, 'Medium bitrate for SD'),
            'high': (float('inf'), 'High bitrate for SD')
        }
    }
    
    # Find the right resolution category
    for (min_pixels, max_pixels), thresholds in categories.items():
        if min_pixels < pixels <= max_pixels:
            for category, (threshold, description) in thresholds.items():
                if bitrate <= threshold:
                    return f"{category.capitalize()} Bitrate ({description})"
    
    return "Unable to categorize"

def main():
    # Prompt for file path
    file_path = input("Enter the full path to the video file: ").strip('"')
    
    # Validate file exists
    if not os.path.exists(file_path):
        print("File does not exist. Please check the path and try again.")
        return
    
    # Get bitrate and resolution
    bitrate, width, height = get_video_bitrate_and_resolution(file_path)
    
    # Check if analysis was successful
    if bitrate is None:
        print("Could not analyze the video file. Ensure ffprobe is installed and the file is a valid video.")
        return
    
    # Print detailed information
    print(f"\nVideo Analysis:")
    print(f"Resolution: {width}x{height}")
    print(f"Bitrate: {bitrate:.2f} kbps")
    
    # Categorize bitrate
    category = categorize_bitrate(bitrate, width, height)
    print(f"Bitrate Category: {category}")

if __name__ == "__main__":
    main()