#!/usr/bin/env python3
import os
import shutil
import argparse
from pathlib import Path


def flatten_directory(root_path):
    """
    Move all files from subdirectories to the root directory.
    Delete empty subdirectories after moving files.

    Args:
        root_path (str or Path): Path to the root directory to flatten
    """
    root_path = Path(root_path).resolve()

    if not root_path.exists():
        print(f"Error: Directory '{root_path}' does not exist.")
        return False

    if not root_path.is_dir():
        print(f"Error: '{root_path}' is not a directory.")
        return False

    moved_files = 0
    deleted_dirs = 0

    # Walk through all subdirectories (bottom-up to handle nested structures)
    for current_dir, subdirs, files in os.walk(root_path, topdown=False):
        current_path = Path(current_dir)

        # Skip the root directory itself
        if current_path == root_path:
            continue

        # Move all files to the root directory
        for file in files:
            source_file = current_path / file
            destination_file = root_path / file

            # Handle naming conflicts by adding a number suffix
            counter = 1
            original_dest = destination_file
            while destination_file.exists():
                stem = original_dest.stem
                suffix = original_dest.suffix
                destination_file = root_path / f"{stem}_{counter}{suffix}"
                counter += 1

            try:
                shutil.move(str(source_file), str(destination_file))
                moved_files += 1
                if destination_file != original_dest:
                    print(
                        f"Moved: {source_file} → {destination_file} (renamed to avoid conflict)"
                    )
                else:
                    print(f"Moved: {source_file} → {destination_file}")
            except Exception as e:
                print(f"Error moving {source_file}: {e}")

        # Try to remove the directory if it's empty
        try:
            current_path.rmdir()  # Only removes if empty
            deleted_dirs += 1
            print(f"Deleted empty directory: {current_path}")
        except OSError:
            # Directory not empty (might contain subdirectories)
            pass

    print(f"\nOperation completed:")
    print(f"Files moved: {moved_files}")
    print(f"Empty directories deleted: {deleted_dirs}")

    return True


def get_directory_input():
    """
    Prompt the user for a directory path.

    Returns:
        str: The directory path entered by the user, or '.' if empty
    """
    while True:
        directory = input(
            "Enter the directory path to flatten (press Enter for current directory): "
        ).strip()

        # Use current directory if no input provided
        if not directory:
            directory = "."

        # Check if the directory exists
        if Path(directory).exists():
            if Path(directory).is_dir():
                return directory
            else:
                print(f"Error: '{directory}' is not a directory. Please try again.")
        else:
            print(f"Error: Directory '{directory}' does not exist. Please try again.")


def main():
    parser = argparse.ArgumentParser(
        description="Flatten directory structure by moving all files from subdirectories to the main folder."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=None,
        help="Directory to flatten (default: prompt for input)",
    )

    args = parser.parse_args()

    # If no directory provided as argument, prompt for it
    if args.directory is None:
        directory = get_directory_input()
    else:
        directory = args.directory

    print(f"Flattening directory: {Path(directory).resolve()}")
    print("-" * 50)

    success = flatten_directory(directory)

    if success:
        print("Directory flattening completed successfully!")
    else:
        print("Directory flattening failed!")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
