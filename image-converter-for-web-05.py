"""
Image to Web-Ready JPEG Converter
Converts JPG, PNG, and HEIC images to optimized web-ready JPEGs
with drag-and-drop GUI support for files and folders.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image, ImageCms
import os
from pathlib import Path
import threading

# Register HEIC support
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    # pillow-heif not installed, HEIC files won't be supported
    pass
# Register AVIF
try:
    import pillow_avif
except ImportError:
    pass

# Register JPEG XL
try:
    import pillow_jxl
except ImportError:
    pass


class ImageConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Web-Ready JPEG Converter")
        self.root.geometry("800x600")

        # Configure style
        style = ttk.Style()
        style.theme_use("clam")

        # Main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)  # Status text gets the extra space

        # ============ TOP ROW: Drop zone and Options ============
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
        top_frame.columnconfigure(0, weight=1)
        top_frame.columnconfigure(1, weight=0)

        # Drop zone (left side)
        self.drop_frame = tk.Frame(
            top_frame,
            bg="#f0f0f0",
            relief=tk.RIDGE,
            borderwidth=2,
            width=380,
            height=280,
        )
        self.drop_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E), padx=(0, 10))
        self.drop_frame.grid_propagate(False)

        drop_label = tk.Label(
            self.drop_frame,
            text="📁 Drop images or folders here",
            bg="#f0f0f0",
            font=("Arial", 12),
            fg="#666",
        )
        drop_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Enable drag and drop
        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind("<<Drop>>", self.on_drop)

        # Options panel (right side)
        options_frame = ttk.Frame(top_frame)
        options_frame.grid(row=0, column=1, sticky=(tk.N, tk.W, tk.E))

        # Conversion options frame
        conversion_options_frame = ttk.LabelFrame(
            options_frame, text="Conversion Options", padding="10"
        )
        conversion_options_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Checkbox for keeping original dimensions
        self.keep_original_dimensions = tk.BooleanVar(value=False)
        self.dimensions_checkbox = ttk.Checkbutton(
            conversion_options_frame,
            text="Keep original dimensions\n(disable 2000px max resize)",
            variable=self.keep_original_dimensions,
        )
        self.dimensions_checkbox.grid(row=0, column=0, sticky=tk.W)

        # Output options frame
        output_options_frame = ttk.LabelFrame(
            options_frame, text="Output Options", padding="10"
        )
        output_options_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Checkbox for output to folder
        self.use_output_folder = tk.BooleanVar(value=False)
        self.output_checkbox = ttk.Checkbutton(
            output_options_frame,
            text="Output to specific folder\n(instead of alongside originals)",
            variable=self.use_output_folder,
            command=self.toggle_output_folder,
        )
        self.output_checkbox.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))

        # Output folder path
        self.default_output_folder = r"C:\Users\Jeff\Desktop\webimg"
        self.output_folder = self.default_output_folder

        self.output_entry = ttk.Entry(output_options_frame, width=30)
        self.output_entry.insert(0, self.default_output_folder)
        self.output_entry.config(state=tk.DISABLED)
        self.output_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))

        self.output_browse_button = ttk.Button(
            output_options_frame,
            text="Browse...",
            command=self.select_output_folder,
            state=tk.DISABLED,
        )
        self.output_browse_button.grid(row=2, column=0, columnspan=2, pady=(0, 5))

        # Checkbox for preserving folder structure
        self.preserve_structure = tk.BooleanVar(value=False)
        self.structure_checkbox = ttk.Checkbutton(
            output_options_frame,
            text="Preserve original folder structure",
            variable=self.preserve_structure,
            state=tk.DISABLED,
        )
        self.structure_checkbox.grid(row=3, column=0, columnspan=2, sticky=tk.W)

        output_options_frame.columnconfigure(0, weight=1)

        # Buttons frame
        button_frame = ttk.Frame(options_frame)
        button_frame.grid(row=2, column=0, pady=(0, 0))

        self.select_button = ttk.Button(
            button_frame, text="Select Files", command=self.select_files, width=15
        )
        self.select_button.grid(row=0, column=0, padx=2)

        self.select_folder_button = ttk.Button(
            button_frame, text="Select Folder", command=self.select_folder, width=15
        )
        self.select_folder_button.grid(row=0, column=1, padx=2)

        # ============ BOTTOM SECTION: Status and Output ============
        
        # Status label and progress bar
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        status_frame.columnconfigure(1, weight=1)

        ttk.Label(status_frame, text="Status:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        
        self.status_label = ttk.Label(status_frame, text="Ready", foreground="green")
        self.status_label.grid(row=0, column=1, sticky=tk.W)

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode="determinate")
        self.progress.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))

        # Status text (console output)
        output_frame = ttk.LabelFrame(main_frame, text="Console Output", padding="5")
        output_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        self.status_text = tk.Text(
            output_frame, height=10, wrap=tk.WORD, state=tk.DISABLED
        )
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Scrollbar for status text
        scrollbar = ttk.Scrollbar(output_frame, command=self.status_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.status_text.config(yscrollcommand=scrollbar.set)

        main_frame.rowconfigure(3, weight=1)

        # Store the root folder for structure preservation
        self.source_root_folder = None

    def toggle_output_folder(self):
        """Enable/disable output folder controls based on checkbox"""
        if self.use_output_folder.get():
            self.output_entry.config(state=tk.NORMAL)
            self.output_browse_button.config(state=tk.NORMAL)
            self.structure_checkbox.config(state=tk.NORMAL)
            self.output_folder = self.output_entry.get()
        else:
            self.output_entry.config(state=tk.DISABLED)
            self.output_browse_button.config(state=tk.DISABLED)
            self.structure_checkbox.config(state=tk.DISABLED)
            self.output_folder = None

    def log_status(self, message):
        """Add message to status text box"""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def select_files(self):
        """Open file dialog to select images"""
        files = filedialog.askopenfilenames(
            title="Select Images",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.heic *.HEIC *.avif *.AVIF *.jxl *.JXL *.webp *.WEBP"),
                ("All files", "*.*"),
            ],
        )
        if files:
            # For individual files, no root folder
            self.source_root_folder = None
            self.process_files(list(files))

    def select_folder(self):
        """Open folder dialog to select a folder with images"""
        folder = filedialog.askdirectory(title="Select Folder with Images")
        if folder:
            # Set the root folder for structure preservation
            self.source_root_folder = folder
            image_files = self.find_images_in_folder(folder)
            if image_files:
                self.process_files(image_files)
            else:
                messagebox.showinfo(
                    "No Images",
                    "No supported image files found in the selected folder.",
                )

    def select_output_folder(self):
        """Select output folder for converted images"""
        folder = filedialog.askdirectory(
            title="Select Output Folder", initialdir=self.output_entry.get()
        )
        if folder:
            self.output_folder = folder
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, folder)

    def find_images_in_folder(self, folder_path):
        """Recursively find all image files in a folder and its subfolders"""
        image_extensions = (
            ".AVIF",
            ".avif",
            ".heic",
            ".HEIC",
            ".jpeg",
            ".JPEG",
            ".jpg",
            ".JPG",
            ".JXL",
            ".jxl",
            ".png",
            ".PNG",
            ".webp",
            ".WEBP",
        )
        image_files = []

        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(image_extensions):
                    image_files.append(os.path.join(root, file))

        return image_files

    def on_drop(self, event):
        """Handle drag and drop event"""
        files = self.root.tk.splitlist(event.data)
        all_image_files = []

        # Determine if we're dropping a single folder or multiple items
        folders = [
            item.strip("{}") for item in files if os.path.isdir(item.strip("{}"))
        ]

        # If exactly one folder is dropped, use it as the root for structure preservation
        if len(folders) == 1 and len(files) == 1:
            self.source_root_folder = folders[0]
        else:
            # Multiple items or mixed files/folders - no structure preservation
            self.source_root_folder = None

        for item in files:
            item = item.strip("{}")  # Remove curly braces

            if os.path.isdir(item):
                # If it's a folder, find all images in it
                image_files = self.find_images_in_folder(item)
                all_image_files.extend(image_files)
            elif os.path.isfile(item) and item.lower().endswith(
                (".jpg", ".jpeg", ".png", ".heic", ".webp", ".avif", ".jxl")
            ):
                # If it's an image file, add it
                all_image_files.append(item)

        if all_image_files:
            self.process_files(all_image_files)
        else:
            messagebox.showwarning("No Images", "No supported image files found.")

    def process_files(self, files):
        """Process files in a separate thread"""
        thread = threading.Thread(target=self._convert_images, args=(files,))
        thread.daemon = True
        thread.start()

    def _convert_images(self, files):
        """Convert images to web-ready JPEGs"""
        self.select_button.config(state=tk.DISABLED)
        self.select_folder_button.config(state=tk.DISABLED)
        self.output_checkbox.config(state=tk.DISABLED)
        self.output_browse_button.config(state=tk.DISABLED)
        self.structure_checkbox.config(state=tk.DISABLED)
        self.dimensions_checkbox.config(state=tk.DISABLED)

        self.progress["value"] = 0
        self.progress["maximum"] = len(files)

        self.log_status(f"\n{'='*50}")
        self.log_status(f"Starting conversion of {len(files)} file(s)...")

        # Get output folder setting
        use_output_folder = self.use_output_folder.get()
        output_folder = self.output_entry.get() if use_output_folder else None
        preserve_structure = self.preserve_structure.get() and use_output_folder
        keep_dimensions = self.keep_original_dimensions.get()

        if use_output_folder:
            self.log_status(f"Output folder: {output_folder}")
            if preserve_structure and self.source_root_folder:
                self.log_status(
                    f"Preserving folder structure from: {self.source_root_folder}"
                )
            # Create output folder if it doesn't exist
            Path(output_folder).mkdir(parents=True, exist_ok=True)
        else:
            self.log_status(f"Output: Alongside original files")

        if keep_dimensions:
            self.log_status(f"Resize: Disabled (keeping original dimensions)")
        else:
            self.log_status(f"Resize: Max 2000px on longest side")

        self.log_status(f"{'='*50}\n")

        success_count = 0
        error_count = 0

        # Get sRGB profile
        srgb_profile = ImageCms.createProfile("sRGB")

        for idx, file_path in enumerate(files, 1):
            try:
                file_path = file_path.strip("{}")  # Remove curly braces from drag-drop
                path = Path(file_path)

                self.log_status(f"[{idx}/{len(files)}] Processing: {path.name}")

                # Open image
                img = Image.open(file_path)

                # Convert HEIC or any image to RGB
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                elif img.mode == "L":
                    img = img.convert("RGB")

                # Get original dimensions
                width, height = img.size
                original_size = f"{width}x{height}"

                # Resize if needed (max 2000px on longest side) - only if not keeping original dimensions
                if not keep_dimensions:
                    max_dimension = 2000
                    if width > max_dimension or height > max_dimension:
                        if width > height:
                            new_width = max_dimension
                            new_height = int((max_dimension / width) * height)
                        else:
                            new_height = max_dimension
                            new_width = int((max_dimension / height) * width)

                        img = img.resize(
                            (new_width, new_height), Image.Resampling.LANCZOS
                        )
                        self.log_status(
                            f"  Resized: {original_size} → {new_width}x{new_height}"
                        )
                    else:
                        self.log_status(f"  Size: {original_size} (no resize needed)")
                else:
                    self.log_status(f"  Size: {original_size} (original kept)")

                # Convert to sRGB color space
                try:
                    # Try to get the image's color profile
                    if "icc_profile" in img.info:
                        import io

                        input_profile = ImageCms.ImageCmsProfile(
                            io.BytesIO(img.info["icc_profile"])
                        )
                        img = ImageCms.profileToProfile(
                            img, input_profile, srgb_profile, outputMode="RGB"
                        )
                        self.log_status(f"  Converted to sRGB color space")
                    else:
                        # No profile, assume sRGB
                        pass
                except Exception as e:
                    self.log_status(f"  Warning: Could not convert color profile: {e}")

                # Determine output path
                if output_folder:
                    if preserve_structure and self.source_root_folder:
                        # Preserve folder structure
                        try:
                            # Get relative path from source root folder
                            relative_path = Path(file_path).relative_to(
                                self.source_root_folder
                            )
                            # Create the same structure in output folder
                            output_dir = Path(output_folder) / relative_path.parent
                            output_dir.mkdir(parents=True, exist_ok=True)
                            output_path = output_dir / f"{path.stem}_web.jpg"
                            self.log_status(f"  Folder: {relative_path.parent}")
                        except ValueError:
                            # File is not relative to source root, use flat output
                            output_path = Path(output_folder) / f"{path.stem}_web.jpg"
                    else:
                        # Flat output - all files in output folder root
                        output_path = Path(output_folder) / f"{path.stem}_web.jpg"
                else:
                    # Output alongside original
                    output_path = path.parent / f"{path.stem}_web.jpg"

                # Save as JPEG with sRGB profile embedded
                img.save(
                    output_path,
                    "JPEG",
                    quality=70,
                    optimize=True,
                    icc_profile=ImageCms.ImageCmsProfile(srgb_profile).tobytes(),
                )

                # Get file size
                file_size = output_path.stat().st_size / 1024  # KB
                self.log_status(f"  ✓ Saved: {output_path.name} ({file_size:.1f} KB)")
                success_count += 1

            except Exception as e:
                self.log_status(f"  ✗ Error: {str(e)}")
                error_count += 1

            self.progress["value"] = idx
            self.root.update_idletasks()

        # Summary
        self.log_status(f"\n{'='*50}")
        self.log_status(f"Conversion complete!")
        self.log_status(f"Success: {success_count} | Errors: {error_count}")
        self.log_status(f"{'='*50}\n")

        self.select_button.config(state=tk.NORMAL)
        self.select_folder_button.config(state=tk.NORMAL)
        self.output_checkbox.config(state=tk.NORMAL)
        self.dimensions_checkbox.config(state=tk.NORMAL)
        if self.use_output_folder.get():
            self.output_browse_button.config(state=tk.NORMAL)
            self.structure_checkbox.config(state=tk.NORMAL)


def main():
    root = TkinterDnD.Tk()
    app = ImageConverterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    # Check for required libraries
    try:
        import io

        main()
    except ImportError as e:
        print(f"Error: Missing required library - {e}")
        print("\nPlease install required packages:")
        print("pip install Pillow tkinterdnd2 pillow-heif")