import os
import sys
from datetime import datetime, timedelta
from PIL import Image
from PIL.ExifTags import TAGS
import shutil


def get_image_datetime(image_path):
    """Extract datetime from image metadata"""
    try:
        img = Image.open(image_path)
        exif = img._getexif()
        if exif:
            for tag, value in exif.items():
                if TAGS.get(tag) == "DateTimeOriginal":
                    return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
    except (AttributeError, KeyError, ValueError, TypeError):
        pass
    return None


def find_sequences(files_with_dates, min_sequence_length=50):
    """Find sequences of photos taken at regular intervals"""
    if not files_with_dates:
        return []

    # Sort files by datetime
    sorted_files = sorted(files_with_dates, key=lambda x: x[1])
    sequences = []
    current_sequence = [sorted_files[0]]

    for i in range(1, len(sorted_files)):
        prev_file, prev_time = sorted_files[i - 1]
        curr_file, curr_time = sorted_files[i]
        time_diff = curr_time - prev_time

        if not current_sequence:
            current_sequence.append((curr_file, curr_time))
            continue

        # Check if this photo continues the sequence
        if len(current_sequence) == 1:
            # First interval - can't determine pattern yet
            current_sequence.append((curr_file, curr_time))
            continue

        # Calculate expected time based on established interval
        first, second = current_sequence[0][1], current_sequence[1][1]
        interval = second - first
        expected_time = current_sequence[-1][1] + interval
        tolerance = timedelta(seconds=interval.total_seconds() * 0.1)  # 10% tolerance

        if abs(curr_time - expected_time) <= tolerance:
            current_sequence.append((curr_file, curr_time))
        else:
            # Sequence broken
            if len(current_sequence) >= min_sequence_length:
                sequences.append(current_sequence)
            current_sequence = [(curr_file, curr_time)]

    # Add the last sequence if it's long enough
    if len(current_sequence) >= min_sequence_length:
        sequences.append(current_sequence)

    return sequences


def scan_directory(root_dir):
    """Scan directory recursively for image files"""
    image_extensions = {".jpg", ".jpeg", ".png", ".tiff", ".nef", ".cr2", ".arw"}
    files_with_dates = []

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            ext = os.path.splitext(filename.lower())[1]
            if ext in image_extensions:
                filepath = os.path.join(dirpath, filename)
                try:
                    dt = get_image_datetime(filepath)
                    if dt:
                        files_with_dates.append((filepath, dt))
                except Image.DecompressionBombError:
                    print(f"Skipping large image file: {filepath}")
                    continue

    return files_with_dates


def format_sequence_info(sequence):
    """Format sequence information for display"""
    first_file = sequence[0][0]
    last_file = sequence[-1][0]
    count = len(sequence)
    interval = sequence[1][1] - sequence[0][1]

    dirname = os.path.dirname(first_file)
    first_filename = os.path.basename(first_file)
    last_filename = os.path.basename(last_file)

    return {
        "count": count,
        "directory": dirname,
        "first": first_filename,
        "last": last_filename,
        "interval": interval,
    }


def move_sequence(sequence, base_dir):
    """Move sequence to its own folder"""
    if not sequence:
        return

    first_file = sequence[0][0]
    dirname = os.path.dirname(first_file)
    seq_start = sequence[0][1].strftime("%Y%m%d_%H%M%S")
    seq_end = sequence[-1][1].strftime("%H%M%S")
    new_dirname = os.path.join(base_dir, f"timelapse_{seq_start}-{seq_end}")

    os.makedirs(new_dirname, exist_ok=True)

    for filepath, _ in sequence:
        filename = os.path.basename(filepath)
        new_path = os.path.join(new_dirname, filename)
        shutil.move(filepath, new_path)

    return new_dirname


def main():
    if len(sys.argv) < 2:
        print("Usage: python timelapse_detector.py <directory>")
        return

    root_dir = sys.argv[1]
    print(f"Scanning {root_dir} for timelapse sequences...")

    files_with_dates = scan_directory(root_dir)
    sequences = find_sequences(files_with_dates)

    if not sequences:
        print("No timelapse sequences found.")
        return

    print(f"\nFound {len(sequences)} timelapse sequences:")
    sequence_info = []
    for i, seq in enumerate(sequences, 1):
        info = format_sequence_info(seq)
        sequence_info.append(info)
        print(f"\nSequence {i}:")
        print(f"  Photos: {info['count']}")
        print(f"  Directory: {info['directory']}")
        print(f"  First file: {info['first']}")
        print(f"  Last file: {info['last']}")
        print(
            f"  Interval: ~{info['interval'].total_seconds():.1f} seconds between photos"
        )

    response = (
        input("\nWould you like to move these sequences to their own folders? (y/n): ")
        .strip()
        .lower()
    )
    if response == "y":
        base_dir = os.path.abspath(root_dir)
        for i, seq in enumerate(sequences, 1):
            new_dir = move_sequence(seq, base_dir)
            print(f"Moved sequence {i} to {new_dir}")
        print("\nDone moving sequences.")
    else:
        print("No files were moved.")


if __name__ == "__main__":
    main()
