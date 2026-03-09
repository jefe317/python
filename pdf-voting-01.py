import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import requests
import pdf2image
import io
import csv
import threading
import queue
import time
import os

# --- Configuration ---
INPUT_FILE = "pdf-urls.txt"
OUTPUT_CSV = "pdf-urls-results.csv"
MAX_DIMENSION = 500
ANIMATION_DURATION_MS = 2000  # 2 seconds total loop
MAX_PAGES = 10
PRELOAD_BUFFER = 10  # How many PDFs to process in advance


class PDFProcessor(threading.Thread):
    """Background thread to download and process PDFs."""

    def __init__(self, url_queue, result_queue):
        super().__init__()
        self.url_queue = url_queue
        self.result_queue = result_queue
        self.daemon = True  # Kill thread when main app closes

    def run(self):
        while True:
            try:
                url = self.url_queue.get()
                if url is None:
                    break  # Sentinel to stop

                print(f"Processing: {url}")

                # 1. Download PDF
                try:
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    pdf_bytes = response.content
                except Exception as e:
                    print(f"Error downloading {url}: {e}")
                    self.result_queue.put(("error", url, str(e)))
                    continue

                # 2. Convert to Images (First 10 pages)
                try:
                    # poppler_path=r'C:\Program Files\poppler-xx\bin' # UNCOMMENT AND SET IF WINDOWS PATH ISSUES
                    images = pdf2image.convert_from_bytes(
                        pdf_bytes, first_page=1, last_page=MAX_PAGES, fmt="jpeg"
                    )
                except Exception as e:
                    print(f"Error converting PDF {url}: {e}")
                    self.result_queue.put(("error", url, "PDF Conversion Failed"))
                    continue

                # 3. Resize Images (Thumbnailing)
                processed_frames = []
                for img in images:
                    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
                    processed_frames.append(img)

                # 4. Put ready data into queue
                self.result_queue.put(("success", url, processed_frames))

            except Exception as e:
                print(f"Unexpected error: {e}")


class TriageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Triage Tool")
        self.root.geometry("600x700")

        # Data Structures
        self.url_queue = queue.Queue()
        self.ready_queue = queue.Queue(maxsize=PRELOAD_BUFFER)

        self.current_url = None
        self.current_frames = []
        self.animation_running = False
        self.frame_index = 0

        # Load URLs
        self.load_urls()

        # GUI Components
        self.setup_ui()

        # Start Worker Thread
        self.worker = PDFProcessor(self.url_queue, self.ready_queue)
        self.worker.start()

        # Start Polling for Content
        self.check_queue()

    def load_urls(self):
        try:
            with open(INPUT_FILE, "r") as f:
                urls = [line.strip() for line in f if line.strip()]

            # Check which are already done
            done_urls = set()
            if os.path.exists(OUTPUT_CSV):
                with open(OUTPUT_CSV, "r") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if row:
                            done_urls.add(row[0])

            count = 0
            for u in urls:
                if u not in done_urls:
                    self.url_queue.put(u)
                    count += 1

            print(f"Queued {count} URLs for processing.")

        except FileNotFoundError:
            messagebox.showerror("Error", f"Could not find {INPUT_FILE}")

    def setup_ui(self):
        # 1. Info Frame
        self.info_frame = tk.Frame(self.root, pady=10)
        self.info_frame.pack(fill=tk.X)

        self.lbl_url = tk.Label(
            self.info_frame,
            text="Waiting for worker...",
            wraplength=550,
            font=("Arial", 10),
        )
        self.lbl_url.pack()

        # 2. Image Display Area
        self.img_container = tk.Frame(self.root, width=500, height=500, bg="#e0e0e0")
        self.img_container.pack(pady=10)
        self.img_container.pack_propagate(False)  # Don't shrink

        self.lbl_image = tk.Label(self.img_container, bg="#e0e0e0")
        self.lbl_image.pack(expand=True)

        # 3. Controls Frame
        self.btn_frame = tk.Frame(self.root, pady=20)
        self.btn_frame.pack(fill=tk.X)
        self.btn_frame.columnconfigure(0, weight=1)
        self.btn_frame.columnconfigure(1, weight=1)
        self.btn_frame.columnconfigure(2, weight=1)

        # Buttons
        self.btn_del = tk.Button(
            self.btn_frame,
            text="Delete (D)",
            bg="#ffcccc",
            fg="red",
            command=lambda: self.vote("Delete"),
            height=2,
        )
        self.btn_del.grid(row=0, column=0, sticky="ew", padx=5)

        self.btn_web = tk.Button(
            self.btn_frame,
            text="Webize (J)",
            bg="#ccffcc",
            fg="green",
            command=lambda: self.vote("Webize"),
            height=2,
        )
        self.btn_web.grid(row=0, column=1, sticky="ew", padx=5)

        self.btn_fix = tk.Button(
            self.btn_frame,
            text="Fix (F)",
            bg="#ffeebb",
            fg="#cc6600",
            command=lambda: self.vote("Fix"),
            height=2,
        )
        self.btn_fix.grid(row=0, column=2, sticky="ew", padx=5)

        # Keyboard Shortcuts
        self.root.bind("<d>", lambda e: self.vote("Delete"))
        self.root.bind("<j>", lambda e: self.vote("Webize"))
        self.root.bind("<f>", lambda e: self.vote("Fix"))

    def check_queue(self):
        """Polls the ready queue to see if the next PDF is ready."""
        if self.current_url is None:
            try:
                # Non-blocking get
                status, url, data = self.ready_queue.get_nowait()

                if status == "error":
                    # Skip errors, log them, maybe save to CSV as 'Error', and recurse
                    self.log_to_csv(url, f"Error: {data}")
                    self.check_queue()
                else:
                    self.load_new_content(url, data)
            except queue.Empty:
                if self.url_queue.empty() and self.ready_queue.empty():
                    self.lbl_url.config(text="All Done! No more URLs.")
                    self.lbl_image.config(image="", text="Done")
                else:
                    self.lbl_url.config(text="Loading next PDF...")
                    self.root.after(500, self.check_queue)
        else:
            # We have content, no need to check queue
            pass

    def load_new_content(self, url, frames):
        self.current_url = url
        self.current_frames = frames
        self.lbl_url.config(text=url)
        self.frame_index = 0

        if frames:
            # Calculate speed: 2000ms / number of frames
            self.delay = int(ANIMATION_DURATION_MS / len(frames))
            self.animation_running = True
            self.animate()
        else:
            self.lbl_image.config(text="Empty PDF or No Images")

    def animate(self):
        if not self.animation_running or not self.current_frames:
            return

        # Prepare image for Tkinter
        pil_img = self.current_frames[self.frame_index]
        tk_img = ImageTk.PhotoImage(pil_img)

        # Update Label
        self.lbl_image.configure(image=tk_img)
        self.lbl_image.image = tk_img  # Keep reference to prevent GC

        # Increment index
        self.frame_index = (self.frame_index + 1) % len(self.current_frames)

        # Schedule next frame
        self.root.after(self.delay, self.animate)

    def vote(self, choice):
        if not self.current_url:
            return

        # Save Result
        self.log_to_csv(self.current_url, choice)

        # Reset State
        self.animation_running = False
        self.current_url = None
        self.current_frames = []
        self.lbl_image.config(image="")

        # Get next
        self.check_queue()

    def log_to_csv(self, url, choice):
        try:
            with open(OUTPUT_CSV, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([url, choice])
        except Exception as e:
            messagebox.showerror("Error", f"Could not save to CSV: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = TriageApp(root)
    root.mainloop()
