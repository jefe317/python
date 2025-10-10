# python
Python scripts

- **imdb-playlist-to-plex-07.py** Create a Plex Movie Collection based on an IMDB list, like https://www.imdb.com/list/ls002272292/, which needs to be exported to CSV (which IMDB lets you do). This script will remember your Plex URL and token, and loads your existing movie collections if you want to update an existing group of films. Uses fuzzy matching to maximize success, and generates reports to show which films were added, skipped, don't exist or failed. Has command line parameters as well.
- **color-contrast-07.py** Generate a HTML file with text over background colors based on the input in the file. Also shows WCAG 2.1 color contrast ratios and if it passes or fails for all categories.
- **show-bitrate-02.py** Shows the bitrate of a file, which is helpful for looking into video file information.
- **show-bitrate-folder-02.py** Shows the bitrate of a whole folder, which is helpful for looking into video file information.

# Sublime Text
Sublime Text Add-ons
- **incremental\_save.py** - Saves your current file with an incremented version number (e.g., `document.txt` → `document-01.txt` → `document-02.txt`), useful for maintaining version history without overwriting.
- **quote\_replacer.py** - Converts straight quotes to HTML entities (curly quotes like `&ldquo;` and `&rdquo;`) while intelligently preserving quotes within HTML tags, CSS, and JavaScript, and handles apostrophes in contractions.

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
