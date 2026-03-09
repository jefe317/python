#!/usr/bin/env python3
"""
Recursively finds files with double extensions in a folder and removes the first
(false) extension, keeping only the true/last extension.

Example:
  "The Office S08E24.mov.mp4" -> "The Office S08E24.mp4"

# Preview changes without renaming anything (recommended first step)
python fix_double_extensions.py /path/to/folder --dry-run

# Actually rename the files
python fix_double_extensions.py /path/to/folder
"""

import os
import argparse


# Common media/file extensions to recognize as "real" extensions
KNOWN_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".webm",
    ".m4v",
    ".mp3",
    ".aac",
    ".flac",
    ".wav",
    ".ogg",
    ".m4a",
    ".wma",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tiff",
    ".webp",
    ".heic",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".zip",
    ".tar",
    ".gz",
    ".rar",
    ".7z",
    ".py",
    ".js",
    ".ts",
    ".html",
    ".css",
    ".json",
    ".xml",
    ".csv",
    ".txt",
    ".srt",
    ".sub",
    ".ass",
    ".vtt",
}


def find_double_extension_files(root_dir):
    """Yield (filepath, new_name) tuples for files with double extensions."""
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            name, ext1 = os.path.splitext(filename)
            if not ext1:
                continue
            _, ext2 = os.path.splitext(name)
            if ext2 and ext2.lower() in KNOWN_EXTENSIONS:
                # Double extension detected: ext2 is the false one, ext1 is the real one
                new_name = name[: -len(ext2)] + ext1
                filepath = os.path.join(dirpath, filename)
                yield filepath, new_name


def main():
    parser = argparse.ArgumentParser(
        description="Remove false double extensions from filenames recursively."
    )
    parser.add_argument("folder", help="Root folder to search")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be renamed without actually renaming",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.folder):
        print(f"Error: '{args.folder}' is not a valid directory.")
        return

    matches = list(find_double_extension_files(args.folder))

    if not matches:
        print("No files with double extensions found.")
        return

    print(
        f"{'DRY RUN — ' if args.dry_run else ''}Found {len(matches)} file(s) to rename:\n"
    )

    for filepath, new_name in matches:
        dirpath = os.path.dirname(filepath)
        new_path = os.path.join(dirpath, new_name)
        old_name = os.path.basename(filepath)

        print(f"  {old_name}")
        print(f"  -> {new_name}\n")

        if not args.dry_run:
            if os.path.exists(new_path):
                print(f"  [SKIPPED] Target already exists: {new_path}\n")
            else:
                os.rename(filepath, new_path)

    if args.dry_run:
        print(
            "Dry run complete. No files were renamed. Remove --dry-run to apply changes."
        )
    else:
        print("Done.")


if __name__ == "__main__":
    main()
