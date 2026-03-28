# python
Python scripts

- **[imdb-playlist-to-plex-07.py](https://github.com/jefe317/python/blob/main/imdb-playlist-to-plex-07.py)** Create a Plex Movie Collection based on an IMDB list, like https://www.imdb.com/list/ls002272292/, which needs to be exported to CSV (which IMDB lets you do). This script will remember your Plex URL and token, and loads your existing movie collections if you want to update an existing group of films. Uses fuzzy matching to maximize success, and generates reports to show which films were added, skipped, don't exist or failed. Has command line parameters as well.
- **[color-contrast-07.py](https://github.com/jefe317/python/blob/main/color-contrast-07.py)** Generate a HTML file with text over background colors based on the input in the file. Also shows WCAG 2.1 color contrast ratios and if it passes or fails for all categories.
- **[show-bitrate-02.py](https://github.com/jefe317/python/blob/main/show-bitrate-02.py)** Shows the bitrate of a file, which is helpful for looking into video file information.
- **[show-bitrate-folder-02.py](https://github.com/jefe317/python/blob/main/show-bitrate-folder-02.py)** Shows the bitrate of a whole folder, which is helpful for looking into video file information.
- **[remove-unneeded-extensions-01.py](https://github.com/jefe317/python/blob/main/files-remove-unneeded-extensions-01.py)** Recursively finds files with double extensions in a folder and removes the first (false) extension, keeping only the true/last extension.
- **[pdf-voting-01.py](https://github.com/jefe317/python/blob/main/pdf-voting-01.py)** - Shows 2s animation of first 10 pages to help categorize PDFs. I created this to sort 750 PDFs in 45 minutes.
- **[files-show-duplicates-04.py](https://github.com/jefe317/python/blob/main/files-show-duplicates-04.py)** - Find TV and movie media files with ~same name, ask to keep only the smallest.
- **[files-sort-organize-03.py](https://github.com/jefe317/python/blob/main/files-sort-organize-03.py)** - GUI to sort files into folders based on filetype, used to auto clean up my downloads folder.
- **[folder-flatten-02.py](https://github.com/jefe317/python/blob/main/folder-flatten-02.py)** - Puts all sub folders and files into the current directory.
- **[image-converter-for-web-05.py](https://github.com/jefe317/python/blob/main/image-converter-for-web-05.py)** - Used to convert images to web safe jpg, faster than loading photoshop, used to save filesize as well to avoid huge images.
- **[pdf-scan-words-01.py](https://github.com/jefe317/python/blob/main/pdf-scan-words-01.py)** - Scan PDF files for keywords, copy to folder for manual review, report pages keywords were found on. Used to find text in lots of long PDFs quickly.
- **[timelapse_detector-01.py](https://github.com/jefe317/python/blob/main/timelapse_detector-01.py)** - Find timelapse photo sequences and organize into subfolders.
- **[video-caption-fix-02.py](https://github.com/jefe317/python/blob/main/video-caption-fix-02.py)** - GUI to fix .srt caption timings by constant or drifting amount.

# Sublime Text
Sublime Text Add-ons
- **[incremental\_save.py](https://github.com/jefe317/python/blob/main/incremental_save.py)** - Saves your current file with an incremented version number (e.g., `document.txt` → `document-01.txt` → `document-02.txt`), useful for maintaining version history without overwriting.
- **[quote\_replacer.py](https://github.com/jefe317/python/blob/main/quote_replacer.py)** - Converts straight quotes to HTML entities (curly quotes like `&ldquo;` and `&rdquo;`) while intelligently preserving quotes within HTML tags, CSS, and JavaScript, and handles apostrophes in contractions.

## Installation

1.  Open Sublime Text and go to **Preferences → Browse Packages...**
2.  Create a new **User** folder in the opened directory if it doesn't exist already
3.  Save each `.py` file into that folder

## Usage

Run the commands via the Command Palette (**Ctrl+Shift+P** or **Cmd+Shift+P** on Mac):

*   Type "Incremental Save" to run the version saver
*   Type "Smart Quote Replacer" to convert quotes

## Adding Keyboard Shortcuts

1.  Go to **Preferences → Key Bindings**
2.  Add to your user key bindings file:

\[  
 {  
 "keys": \["ctrl+alt+s"\],  
 "command": "incremental\_save"  
 },  
 {  
 "keys": \["ctrl+alt+q"\],  
 "command": "smart\_quote\_replacer"  
 }  
\]

Replace the key combinations with your preferred shortcuts. On Mac, use `"super"` instead of `"ctrl"`.
