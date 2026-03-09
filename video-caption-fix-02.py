import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
import os

# ── SRT helpers ────────────────────


def parse_time(s: str) -> float:
    """'HH:MM:SS,mmm' → seconds (float)"""
    s = s.strip().replace(".", ",")
    m = re.match(r"(\d+):(\d{2}):(\d{2})[,.](\d{3})", s)
    if not m:
        raise ValueError(f"Cannot parse time: {s!r}")
    h, mi, sc, ms = m.groups()
    return int(h) * 3600 + int(mi) * 60 + int(sc) + int(ms) / 1000


def format_time(t: float) -> str:
    """seconds (float) → 'HH:MM:SS,mmm'"""
    t = max(0.0, t)
    ms = round(t * 1000)
    h, ms = divmod(ms, 3_600_000)
    mi, ms = divmod(ms, 60_000)
    sc, ms = divmod(ms, 1000)
    return f"{int(h):02d}:{int(mi):02d}:{int(sc):02d},{int(ms):03d}"


TIMECODE_RE = re.compile(
    r"(\d+:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d+:\d{2}:\d{2}[,.]\d{3})"
)


def adjust_srt(content: str, offset_fn) -> str:
    """Apply offset_fn(original_seconds) → new_seconds to every timestamp."""
    lines = content.splitlines(keepends=True)
    out = []
    for line in lines:
        m = TIMECODE_RE.match(line)
        if m:
            t_start = parse_time(m.group(1))
            t_end = parse_time(m.group(2))
            new_start = offset_fn(t_start)
            new_end = offset_fn(t_end)
            line = f"{format_time(new_start)} --> {format_time(new_end)}\n"
        out.append(line)
    return "".join(out)


def parse_srt_entries(content: str):
    """Returns list of dicts: {start, end, text} — start/end are formatted strings."""
    entries = []
    blocks = re.split(r"\n\s*\n", content.strip())
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue
        m = TIMECODE_RE.search(block)
        if not m:
            continue
        start_str = m.group(1)
        end_str = m.group(2)
        tc_line_idx = next(
            (i for i, l in enumerate(lines) if TIMECODE_RE.search(l)), None
        )
        if tc_line_idx is None:
            continue
        text_lines = lines[tc_line_idx + 1 :]
        text = " ".join(l.strip() for l in text_lines if l.strip())
        text = re.sub(r"<[^>]+>", "", text)
        if text:
            entries.append({"start": start_str, "end": end_str, "text": text})
    return entries


# ── GUI ────────────────────────────

BG = "#1e1e2e"
SURFACE = "#313244"
ACCENT = "#89b4fa"
ACCENT2 = "#b4befe"
FG = "#cdd6f4"
FG_DIM = "#6c7086"
GREEN = "#a6e3a1"


def trunc(t, n=65):
    return t if len(t) <= n else t[:n] + "…"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SRT Timing Adjuster")
        self.resizable(True, False)
        self.configure(bg=BG, padx=20, pady=20)

        self._entries = []
        self._setup_styles()
        self._build_file_row()
        self._build_preview_strip()

        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=12)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both")

        self._build_fixed_tab()
        self._build_drift_tab()

        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=12)
        ttk.Button(self, text="Apply & Save", command=self._apply).pack()

        self.status = tk.Label(self, text="", bg=BG, fg=GREEN, font=("Segoe UI", 16))
        self.status.pack(pady=(8, 0))

    # ── Styles ────────────────────

    def _setup_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure(
            "TNotebook.Tab",
            background=SURFACE,
            foreground=FG,
            padding=[14, 6],
            font=("Segoe UI", 20),
        )
        s.map(
            "TNotebook.Tab",
            background=[("selected", ACCENT)],
            foreground=[("selected", BG)],
        )
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 18))
        s.configure(
            "Dim.TLabel", background=BG, foreground=FG_DIM, font=("Segoe UI", 16)
        )
        s.configure(
            "Head.TLabel",
            background=BG,
            foreground=ACCENT,
            font=("Segoe UI", 16, "bold"),
        )
        s.configure(
            "TEntry",
            fieldbackground=SURFACE,
            foreground=FG,
            insertcolor=FG,
            font=("Segoe UI", 18),
        )
        s.configure(
            "TButton",
            background=ACCENT,
            foreground=BG,
            font=("Segoe UI", 18, "bold"),
            padding=[10, 5],
        )
        s.map("TButton", background=[("active", ACCENT2)])

    # ── File row ──────────────────

    def _build_file_row(self):
        f = ttk.Frame(self)
        f.pack(fill="x", pady=(0, 4))
        ttk.Label(f, text="SRT file:").pack(side="left")
        self.file_var = tk.StringVar()
        self.file_var.trace_add("write", lambda *_: self._on_path_changed())
        ttk.Entry(f, textvariable=self.file_var, width=54).pack(side="left", padx=8)
        ttk.Button(f, text="Browse…", command=self._browse).pack(side="left")

    def _browse(self):
        path = filedialog.askopenfilename(
            filetypes=[("SRT files", "*.srt"), ("All files", "*.*")]
        )
        if path:
            self.file_var.set(path)

    def _on_path_changed(self):
        path = self.file_var.get().strip()
        if path and os.path.isfile(path):
            self._load_file(path)

    # ── Top preview strip (always visible) ──────────────────────────────

    def _build_preview_strip(self):
        """Two side-by-side info cards showing first & last subtitle."""
        outer = ttk.Frame(self)
        outer.pack(fill="x", pady=(8, 0))
        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=1)

        self._strip_cards = {}
        for col, which in enumerate(["first", "last"]):
            card = tk.Frame(outer, bg=SURFACE, padx=10, pady=8)
            card.grid(
                row=0, column=col, sticky="nsew", padx=(0, 6) if col == 0 else (6, 0)
            )

            icon = "▶  First subtitle" if which == "first" else "⏹  Last subtitle"
            tk.Label(
                card, text=icon, bg=SURFACE, fg=ACCENT, font=("Segoe UI", 16, "bold")
            ).pack(anchor="w")

            t_lbl = tk.Label(
                card, text="—", bg=SURFACE, fg=ACCENT2, font=("Segoe UI", 16, "bold")
            )
            t_lbl.pack(anchor="w", pady=(2, 3))

            d_lbl = tk.Label(
                card,
                text="(no file loaded)",
                bg=SURFACE,
                fg=FG,
                font=("Segoe UI", 16, "italic"),
                wraplength=270,
                justify="left",
            )
            d_lbl.pack(anchor="w", fill="x")

            self._strip_cards[which] = (t_lbl, d_lbl)

    def _update_strip(self, first, last):
        for which, entry in (("first", first), ("last", last)):
            t_lbl, d_lbl = self._strip_cards[which]
            t_lbl.config(text=entry["start"])
            d_lbl.config(text=trunc(entry["text"]))

    # ── Load file ─────────────────

    def _load_file(self, path: str):
        try:
            with open(path, encoding="utf-8-sig") as fh:
                content = fh.read()
        except Exception as e:
            messagebox.showerror("Error", f"Cannot read file:\n{e}")
            return

        entries = parse_srt_entries(content)
        if not entries:
            messagebox.showwarning("Warning", "No subtitle entries found.")
            return

        self._entries = entries
        first, last = entries[0], entries[-1]

        self._update_strip(first, last)
        self._update_fixed_tab(first, last)
        self._update_drift_tab(first, last)

        self.status.config(
            text=f"Loaded {len(entries)} subtitles  ·  {os.path.basename(path)}"
        )

    # ── Fixed-offset tab ────────────────

    def _build_fixed_tab(self):
        tab = ttk.Frame(self.nb, padding=16)
        self.nb.add(tab, text="Fixed Offset")
        tab.columnconfigure(1, weight=1)

        ttk.Label(tab, text="Shift all timestamps by a constant amount.").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        ttk.Label(tab, text="Offset (seconds):").grid(row=1, column=0, sticky="w")
        self.fixed_offset = tk.StringVar(value="0.0")
        ttk.Entry(tab, textvariable=self.fixed_offset, width=12).grid(
            row=1, column=1, sticky="w", padx=8
        )
        ttk.Label(
            tab, text="← negative = earlier  /  positive = later", style="Dim.TLabel"
        ).grid(row=1, column=2, sticky="w")

        ttk.Separator(tab, orient="horizontal").grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=14
        )

        ttk.Label(
            tab,
            text="File reference times",
            foreground=ACCENT,
            font=("Segoe UI", 16, "bold"),
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(0, 8))

        # Two cards
        card_frame = ttk.Frame(tab)
        card_frame.grid(row=4, column=0, columnspan=3, sticky="ew")
        card_frame.columnconfigure(0, weight=1)
        card_frame.columnconfigure(1, weight=1)

        self._fx_labels = {}
        for col, which in enumerate(["first", "last"]):
            card = tk.Frame(card_frame, bg=SURFACE, padx=10, pady=8)
            card.grid(
                row=0, column=col, sticky="nsew", padx=(0, 6) if col == 0 else (6, 0)
            )

            icon = "▶  First" if which == "first" else "⏹  Last"
            tk.Label(
                card, text=icon, bg=SURFACE, fg=ACCENT, font=("Segoe UI", 16, "bold")
            ).pack(anchor="w")

            t_lbl = tk.Label(
                card, text="—", bg=SURFACE, fg=ACCENT2, font=("Segoe UI", 16, "bold")
            )
            t_lbl.pack(anchor="w", pady=(2, 3))

            d_lbl = tk.Label(
                card,
                text="(no file)",
                bg=SURFACE,
                fg=FG,
                font=("Segoe UI", 16, "italic"),
                wraplength=220,
                justify="left",
            )
            d_lbl.pack(anchor="w", fill="x")

            self._fx_labels[which] = (t_lbl, d_lbl)

    def _update_fixed_tab(self, first, last):
        for which, entry in (("first", first), ("last", last)):
            t_lbl, d_lbl = self._fx_labels[which]
            t_lbl.config(text=entry["start"])
            d_lbl.config(text=trunc(entry["text"], 55))

    # ── Drift tab ─────────────────

    def _build_drift_tab(self):
        tab = ttk.Frame(self.nb, padding=16)
        self.nb.add(tab, text="Gradual Drift")

        note = (
            "Map two SRT timestamps to their true video times.\n"
            "The offset is linearly interpolated and extrapolated across the file."
        )
        ttk.Label(tab, text=note, style="Dim.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        # Column headers
        for c, h in enumerate(
            ["Sync point", "SRT time  (HH:MM:SS,mmm)", "Video time  (HH:MM:SS,mmm)"]
        ):
            ttk.Label(
                tab, text=h, foreground=ACCENT, font=("Segoe UI", 16, "bold")
            ).grid(row=1, column=c, padx=(0 if c == 0 else 8), pady=(0, 6), sticky="w")

        self.drift_vars = {}
        self._dr_labels = {}

        for row_idx, (label, which) in enumerate(
            [("Point A", "first"), ("Point B", "last")], start=2
        ):
            # Left info block
            info = tk.Frame(tab, bg=BG)
            info.grid(row=row_idx, column=0, sticky="nsw", pady=6, padx=(0, 12))

            tk.Label(
                info, text=label, bg=BG, fg=FG, font=("Segoe UI", 20, "bold")
            ).pack(anchor="w")

            t_lbl = tk.Label(
                info, text="—", bg=BG, fg=ACCENT2, font=("Segoe UI", 16, "bold")
            )
            t_lbl.pack(anchor="w")

            d_lbl = tk.Label(
                info,
                text="(no file)",
                bg=BG,
                fg=FG_DIM,
                font=("Segoe UI", 16, "italic"),
                wraplength=150,
                justify="left",
            )
            d_lbl.pack(anchor="w")

            self._dr_labels[which] = (t_lbl, d_lbl)

            # SRT + Video entries
            for col, key in enumerate(["srt", "vid"], start=1):
                var = tk.StringVar(value="00:00:00,000")
                ttk.Entry(tab, textvariable=var, width=20).grid(
                    row=row_idx, column=col, padx=8, pady=6, sticky="w"
                )
                self.drift_vars[(label, key)] = var

        ttk.Label(
            tab,
            text="Tip: set Video time to what your player shows for each line of dialogue.",
            style="Dim.TLabel",
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 0))

    def _update_drift_tab(self, first, last):
        for which, entry, label in (
            ("first", first, "Point A"),
            ("last", last, "Point B"),
        ):
            t_lbl, d_lbl = self._dr_labels[which]
            t_lbl.config(text=entry["start"])
            d_lbl.config(text=trunc(entry["text"], 45))
            # Pre-load both SRT and Video fields with the actual SRT time
            self.drift_vars[(label, "srt")].set(entry["start"])
            self.drift_vars[(label, "vid")].set(entry["start"])

    # ── Apply & Save ────────────────

    def _apply(self):
        path = self.file_var.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showerror("Error", "Please select a valid .srt file.")
            return

        try:
            with open(path, encoding="utf-8-sig") as fh:
                content = fh.read()
        except Exception as e:
            messagebox.showerror("Error", f"Cannot read file:\n{e}")
            return

        tab_idx = self.nb.index(self.nb.select())

        try:
            if tab_idx == 0:
                offset = float(self.fixed_offset.get())
                result = adjust_srt(content, lambda t, o=offset: t + o)
            else:
                srt_a = parse_time(self.drift_vars[("Point A", "srt")].get())
                vid_a = parse_time(self.drift_vars[("Point A", "vid")].get())
                srt_b = parse_time(self.drift_vars[("Point B", "srt")].get())
                vid_b = parse_time(self.drift_vars[("Point B", "vid")].get())

                if abs(srt_b - srt_a) < 0.001:
                    messagebox.showerror(
                        "Error", "Point A and Point B SRT times must differ."
                    )
                    return

                off_a = vid_a - srt_a
                off_b = vid_b - srt_b

                def drift_offset(t, sa=srt_a, sb=srt_b, oa=off_a, ob=off_b):
                    frac = (t - sa) / (sb - sa)
                    return t + oa + frac * (ob - oa)

                result = adjust_srt(content, drift_offset)

        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input:\n{e}")
            return

        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(result)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot write file:\n{e}")
            return

        self.status.config(text=f"✓ Saved: {os.path.basename(path)}")


if __name__ == "__main__":
    App().mainloop()
