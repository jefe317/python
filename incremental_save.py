import sublime
import sublime_plugin
import os
import re

class IncrementalSaveCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        current_file = self.view.file_name()
        
        if not current_file:
            # If file hasn't been saved yet, prompt for save
            self.view.window().run_command("save_as")
            return
        
        # Get directory and filename
        directory = os.path.dirname(current_file)
        filename = os.path.basename(current_file)
        name, ext = os.path.splitext(filename)
        
        # Check if filename ends with a number
        match = re.search(r'-(\d+)$', name)
        
        if match:
            # Extract the number and increment it
            current_num = int(match.group(1))
            new_num = current_num + 1
            # Replace the old number with the new one
            new_name = re.sub(r'-\d+$', f'-{new_num:02d}', name)
        else:
            # No number found, add -01
            new_name = name + '-01'
        
        new_filename = new_name + ext
        new_path = os.path.join(directory, new_filename)
        
        # Save the file with the new name
        self.view.set_scratch(False)
        self.view.retarget(new_path)
        self.view.run_command("save")
        
        sublime.status_message(f"Saved as: {new_filename}")