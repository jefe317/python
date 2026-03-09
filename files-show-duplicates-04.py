#!/usr/bin/env python3
"""
find_and_handle_duplicates_04.py

Added hierarchical TV‑show aware scanning:
- Scan only *season* folders inside each show.
- Compare episode identifiers only within that season folder.
"""

import os
import re
from pathlib import Path
from collections import defaultdict


def normalize_basename(name):
    """Normalize a base name by lowercasing and removing non‑alphanumeric characters."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def extract_episode_id(name):
    """
    Extract the SxxExx episode identifier from a filename, if present.
    Returns the identifier (e.g. 's01e01') or None if not found.
    Handles formats: S01E01, s01e01, S01E01E02, etc.
    """
    match = re.search(r"s\d{1,2}e\d{1,2}", name, re.IGNORECASE)
    if match:
        return match.group(0).lower()
    return None


def get_file_size_mb(filepath):
    """Get file size in MB."""
    size_bytes = os.path.getsize(filepath)
    return size_bytes / (1024 * 1024)


def find_and_handle_duplicates(folder_path):
    """Find duplicate episode files within each season folder and let user choose which to keep."""

    # Check if folder exists
    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' does not exist.")
        return

    # ------------------------------------------------------------------
    # 1️⃣ Walk the TV‑shows tree (show → season)
    for show_root, _dirs, _files in os.walk(folder_path):
        # We only care about *direct* children of `folder_path` that look like shows
        if Path(show_root).resolve() == Path(folder_path).resolve():
            continue  # skip the root itself

        # A show folder should contain sub‑folders named "Season XX" or similar.
        for season_name in os.listdir(show_root):
            season_path = os.path.join(show_root, season_name)

            if not os.path.isdir(season_path):
                continue  # ignore non‑folder items (e.g. stray files)

            # ──────────────────────  NEW  ──────────────────────
            # Walk *inside* the season folder – this is where we look for duplicates.
            files_by_key = defaultdict(list)
            key_type = {}  # key -> 'episode' or 'movie'

            for root, _dirs, files in os.walk(season_path):
                for item in files:
                    if item.lower().endswith(".srt"):
                        continue
                    filepath = os.path.join(root, item)
                    if os.path.isfile(filepath):  # sanity check – should always be true
                        basename = Path(item).stem
                        episode_id = extract_episode_id(basename)

                        if episode_id:
                            key = episode_id
                            key_type[key] = "episode"
                        else:
                            key = normalize_basename(basename)
                            key_type[key] = "movie"

                        files_by_key[key].append(filepath)
            # ──────────────────────  END NEW  ──────────────────────

            # Find and process duplicates inside this season
            duplicates_found = False
            total_deleted_mb = 0.0
            total_kept_mb = 0.0

            for key, filepaths in files_by_key.items():
                if len(filepaths) > 1:
                    duplicates_found = True
                    print(f"\n{'='*60}")

                    if key_type[key] == "episode":
                        print(
                            f"Found {len(filepaths)} files for episode: '{key.upper()}' "
                            f"in season folder: '{season_path}'"
                        )
                    else:
                        print(
                            f"Found {len(filepaths)} files with base name: '{key}' (normalized) "
                            f"in season folder: '{season_path}'"
                        )
                    print("=" * 60)

                    # Create list of (filepath, size) tuples and sort by size
                    file_info = [(fp, get_file_size_mb(fp)) for fp in filepaths]
                    file_info.sort(key=lambda x: x[1])  # Sort smallest to largest

                    # Display files with their sizes
                    for idx, (filepath, size_mb) in enumerate(file_info, 1):
                        filename = os.path.basename(filepath)
                        print(f"{idx}. {filename}")
                        print(f"   Size: {size_mb:.2f} MB")

                    # For TV episodes, offer a one-key shortcut to keep the smallest file
                    if key_type[key] == "episode":
                        print(
                            f"\n[Tip] File #1 is the smallest. Press Enter to keep it and delete the rest."
                        )

                    # Ask user which to keep
                    while True:
                        prompt = f"\nWhich file do you want to KEEP? (1-{len(file_info)}, or 's' to skip): "
                        choice = input(prompt).strip().lower()

                        # Empty Enter = keep smallest (episode shortcut)
                        if choice == "" and key_type[key] == "episode":
                            choice = "1"

                        if choice == "s":
                            print("Skipping this group.")
                            for filepath, size_mb in file_info:
                                total_kept_mb += size_mb
                            break

                        try:
                            choice_idx = int(choice) - 1
                            if 0 <= choice_idx < len(file_info):
                                kept_file = file_info[choice_idx][0]
                                kept_size = file_info[choice_idx][1]
                                total_kept_mb += kept_size
                                print(f"\nKeeping: {os.path.basename(kept_file)}")

                                for idx, (filepath, size_mb) in enumerate(file_info):
                                    if idx != choice_idx:
                                        try:
                                            os.remove(filepath)
                                            total_deleted_mb += size_mb
                                            print(
                                                f"Deleted: {os.path.basename(filepath)}"
                                            )
                                        except Exception as e:
                                            print(
                                                f"Error deleting {os.path.basename(filepath)}: {e}"
                                            )
                                break
                            else:
                                print(
                                    f"Please enter a number between 1 and {len(file_info)}."
                                )
                        except ValueError:
                            print(
                                "Invalid input. Please enter a number or 's' to skip."
                            )

            if not duplicates_found:
                print(
                    "\nNo duplicate filenames found in this season folder (ignoring extensions)."
                )

            # Print summary stats for this season
            total_original_mb = total_deleted_mb + total_kept_mb
            pct_saved = (
                (total_deleted_mb / total_original_mb * 100)
                if total_original_mb > 0
                else 0
            )
            total_space_saved_mb = total_deleted_mb - total_kept_mb

            print(f"\n{'='*60}")
            print("SUMMARY")
            print(f"Total deleted:        {total_deleted_mb:>10.2f} MB")
            print(f"Total kept/skipped:   {total_kept_mb:>10.2f} MB")
            print(
                f"Total space saved:    {total_space_saved_mb:>10.2f} MB  ({pct_saved:.1f}%)"
            )
        # ────────────────────── END PER‑SEASON LOOP ──────────────────────
    # ------------------------------------------------------------------


def main():
    folder_path = input("Enter the folder path to scan: ").strip()

    # Remove quotes if present (helpful for copy‑pasted paths)
    folder_path = folder_path.strip('"').strip("'")

    print(f"\nScanning folder: {folder_path}\n")
    find_and_handle_duplicates(folder_path)
    print("\n" + "=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
