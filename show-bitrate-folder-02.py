import subprocess
import json
import os
from collections import defaultdict
from pathlib import Path

# Common video file extensions
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'}

def get_video_info(file_path):
    """
    Extract video bitrate and resolution using ffprobe with modified bitrate calculation
    """
    try:
        # First command to get stream information
        result = subprocess.run([
            'ffprobe', 
            '-v', 'quiet', 
            '-print_format', 'json', 
            '-show_streams', 
            '-select_streams', 'v:0', 
            file_path
        ], capture_output=True, text=True)
        
        # Second command specifically for bitrate using -count_packets
        bitrate_result = subprocess.run([
            'ffprobe',
            '-v', 'quiet',
            '-select_streams', 'v:0',
            '-show_entries', 'format=duration,size',
            '-print_format', 'json',
            file_path
        ], capture_output=True, text=True)
        
        probe_data = json.loads(result.stdout)
        bitrate_data = json.loads(bitrate_result.stdout)
        
        video_stream = probe_data['streams'][0]
        width = int(video_stream.get('width', 0))
        height = int(video_stream.get('height', 0))
        
        # Calculate bitrate from file size and duration
        try:
            duration = float(bitrate_data['format']['duration'])
            size_bits = float(bitrate_data['format']['size']) * 8
            bitrate = (size_bits / duration) / 1000  # Convert to kbps
        except (KeyError, ZeroDivisionError):
            # Fallback method using direct bit_rate if available
            bitrate = float(video_stream.get('bit_rate', 0)) / 1000
            if bitrate == 0:
                # Second fallback: try format bitrate
                format_result = subprocess.run([
                    'ffprobe',
                    '-v', 'quiet',
                    '-print_format', 'json',
                    '-show_format',
                    file_path
                ], capture_output=True, text=True)
                format_data = json.loads(format_result.stdout)
                bitrate = float(format_data['format'].get('bit_rate', 0)) / 1000
        
        return {
            'bitrate': bitrate,
            'width': width,
            'height': height,
            'path': file_path,
            'filename': os.path.basename(file_path),
            'size_mb': os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB
        }
    
    except Exception as e:
        print(f"\nError analyzing video {file_path}: {e}")
        return None

def categorize_bitrate(video_info):
    """
    Categorize bitrate based on resolution and bitrate
    """
    width = video_info['width']
    height = video_info['height']
    bitrate = video_info['bitrate']
    pixels = width * height
    
    # Resolution categories and their bitrate thresholds
    categories = {
        '4K': {
            'pixels': (3840 * 2160, float('inf')),
            'thresholds': {
                'Low': (0, 10000),
                'Medium': (10000, 20000),
                'High': (20000, float('inf'))
            }
        },
        '1080p': {
            'pixels': (1920 * 1080, 3840 * 2160),
            'thresholds': {
                'Low': (0, 5000),
                'Medium': (5000, 10000),
                'High': (10000, float('inf'))
            }
        },
        '720p': {
            'pixels': (1280 * 720, 1920 * 1080),
            'thresholds': {
                'Low': (0, 2500),
                'Medium': (2500, 5000),
                'High': (5000, float('inf'))
            }
        },
        'SD': {
            'pixels': (0, 1280 * 720),
            'thresholds': {
                'Low': (0, 1000),
                'Medium': (1000, 2500),
                'High': (2500, float('inf'))
            }
        }
    }
    
    # Find resolution category
    resolution_category = None
    for res_name, res_info in categories.items():
        min_pixels, max_pixels = res_info['pixels']
        if min_pixels < pixels <= max_pixels:
            resolution_category = res_name
            break
    
    if not resolution_category:
        return None
    
    # Find bitrate category
    for bitrate_category, (min_rate, max_rate) in categories[resolution_category]['thresholds'].items():
        if min_rate <= bitrate < max_rate:
            return f"{resolution_category} - {bitrate_category}"
    
    return None

def find_video_files(folder_path):
    """
    Recursively find all video files in the given folder
    """
    video_files = []
    for path in Path(folder_path).rglob('*'):
        if path.suffix.lower() in VIDEO_EXTENSIONS:
            video_files.append(str(path))
    return video_files

def analyze_folder(folder_path):
    """
    Analyze all videos in a folder and return categorized results
    """
    print(f"Scanning folder: {folder_path}")
    
    # Find all video files
    video_files = find_video_files(folder_path)
    total_files = len(video_files)
    print(f"Found {total_files} video files")
    
    # Analyze each video
    categorized_videos = defaultdict(list)
    for i, file_path in enumerate(video_files, 1):
        print(f"\rAnalyzing video {i}/{total_files}: {os.path.basename(file_path)}", end='')
        
        video_info = get_video_info(file_path)
        if video_info:
            category = categorize_bitrate(video_info)
            if category:
                categorized_videos[category].append(video_info)
    
    print("\nAnalysis complete!")
    return categorized_videos

def display_results(categorized_videos):
    """
    Display categorized videos sorted by bitrate
    """
    print("\nVideo Analysis Results:")
    print("=" * 100)
    
    # Sort categories in order: 4K, 1080p, 720p, SD, each with High, Medium, Low
    category_order = []
    for res in ['4K', '1080p', '720p', 'SD']:
        for quality in ['High', 'Medium', 'Low']:
            category_order.append(f"{res} - {quality}")
    
    # Display results for each category
    for category in category_order:
        if category in categorized_videos:
            videos = categorized_videos[category]
            # Sort videos by bitrate (highest to lowest)
            videos.sort(key=lambda x: x['bitrate'], reverse=True)
            
            print(f"\n{category} Quality Videos:")
            print("-" * 100)
            print(f"{'Filename':<50} {'Resolution':<15} {'Bitrate':>10} {'Size':>10}")
            print("-" * 100)
            
            for video in videos:
                filename = video['filename']
                if len(filename) > 47:
                    filename = filename[:44] + "..."
                print(f"{filename:<50} {video['width']}x{video['height']:<15} {video['bitrate']:>8.0f}k {video['size_mb']:>8.1f}MB")

def main():
    # Prompt for folder path
    folder_path = input("Enter the folder path to analyze: ").strip('"')
    
    # Validate folder exists
    if not os.path.isdir(folder_path):
        print("Folder does not exist. Please check the path and try again.")
        return
    
    # Analyze videos
    categorized_videos = analyze_folder(folder_path)
    
    # Display results
    display_results(categorized_videos)

if __name__ == "__main__":
    main()