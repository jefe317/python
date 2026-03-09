"""
file_sorter.py — GUI file organizer with optional headless CLI mode.

Usage:
  python file_sorter.py            # open GUI
  python file_sorter.py --sort     # headless: sort using saved config, then exit
  python file_sorter.py --help     # show CLI help
"""

import sys
import json
import shutil
import argparse
from pathlib import Path

CONFIG_FILE = Path.home() / ".file_sorter_config.json"


BG = "#1a1a2e"
PANEL = "#16213e"
ACCENT = "#0f3460"
HIGHLIGHT = "#e94560"
TEXT = "#eaeaea"
SUBTEXT = "#888"
SUCCESS = "#4caf50"
ENTRY_BG = "#0d1b2a"

ROW_HEIGHT = 26  # px — must match Treeview rowheight


def load_config() -> dict:
    """Return {"sources": [...], "rules": [...]} from disk, or defaults."""
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
            # back-compat: old format was a plain list of rules
            if isinstance(data, list):
                return {"sources": [], "rules": data}
            # back-compat: old format had a single "source" string
            if "source" in data and "sources" not in data:
                src = data.pop("source").strip()
                data["sources"] = [src] if src else []
            data.setdefault("sources", [])
            return data
        except Exception:
            pass
    return {"sources": [], "rules": []}


def save_config(config: dict):
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def run_sort(sources: list, rules: list) -> tuple:
    """
    Move files from each folder in *sources* according to *rules*.
    Returns (moved, skipped, errors).
    """
    ext_map: dict = {}
    for r in rules:
        for e in r["extensions"]:
            if e not in ext_map:
                ext_map[e] = r["destination"]

    total_moved, total_skipped, all_errors = 0, 0, []

    for source in sources:
        src = Path(source)
        if not src.is_dir():
            all_errors.append(f"[{source}] Source folder not found — skipped.")
            continue

        for entry in src.iterdir():
            if not entry.is_file():
                continue
            ext = entry.suffix.lstrip(".").lower()
            if ext in ext_map:
                dest_dir = Path(ext_map[ext])
                try:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    target = dest_dir / entry.name
                    counter = 1
                    while target.exists():
                        target = dest_dir / f"{entry.stem}_{counter}{entry.suffix}"
                        counter += 1
                    shutil.move(str(entry), str(target))
                    total_moved += 1
                except Exception as exc:
                    all_errors.append(f"[{source}] {entry.name}: {exc}")
            else:
                total_skipped += 1

    return total_moved, total_skipped, all_errors


def headless_sort():
    config = load_config()
    sources = [s.strip() for s in config.get("sources", []) if s.strip()]
    rules = config.get("rules", [])

    if not sources:
        print(
            "ERROR: No source folders saved in config. Open the GUI and set at least one first."
        )
        sys.exit(1)
    if not rules:
        print(
            "ERROR: No sorting rules saved in config. Open the GUI and add some first."
        )
        sys.exit(1)

    print(f"Sorting files in {len(sources)} source folder(s):")
    for s in sources:
        print(f"  • {s}")
    print(f"Using {len(rules)} rule(s) from {CONFIG_FILE}")

    moved, skipped, errors = run_sort(sources, rules)

    print(f"Done — {moved} moved, {skipped} skipped (no matching rule).", end="")
    if errors:
        print(f"  {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
    else:
        print()


def launch_gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    class FileSorterApp(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("File Sorter")
            self.configure(bg=BG)
            self.resizable(True, True)

            self._config = load_config()
            self.rules = self._config.get("rules", [])
            self.sources = self._config.get("sources", [])

            self._build_ui()
            self._refresh_sources()
            self._refresh_rules()

            # let geometry settle then lock minimum size
            self.update_idletasks()
            self.minsize(680, self.winfo_height())

        def _persist(self, *_):
            self._config["rules"] = self.rules
            self._config["sources"] = self.sources
            save_config(self._config)

        def _build_ui(self):
            # accent strip
            tk.Frame(self, bg=HIGHLIGHT, height=4).pack(fill="x")

            # title
            title_bar = tk.Frame(self, bg=BG, pady=12)
            title_bar.pack(fill="x", padx=20)
            tk.Label(
                title_bar,
                text="📂 File Sorter",
                font=("Courier New", 20, "bold"),
                bg=BG,
                fg=TEXT,
            ).pack(side="left")
            tk.Label(
                title_bar,
                text="Automate your folder hygiene",
                font=("Courier New", 10),
                bg=BG,
                fg=SUBTEXT,
            ).pack(side="left", padx=16)

            # ── Source Folders panel ──────
            src_frame = tk.Frame(self, bg=PANEL, pady=10, padx=16)
            src_frame.pack(fill="x", padx=20, pady=(0, 4))
            tk.Label(
                src_frame,
                text="SOURCE FOLDERS",
                font=("Courier New", 9, "bold"),
                bg=PANEL,
                fg=HIGHLIGHT,
            ).pack(anchor="w")

            list_row = tk.Frame(src_frame, bg=PANEL)
            list_row.pack(fill="x", pady=(4, 0))

            # listbox + scrollbar
            lb_frame = tk.Frame(list_row, bg=PANEL)
            lb_frame.pack(side="left", fill="x", expand=True)
            sb = tk.Scrollbar(lb_frame, orient="vertical")
            self.src_listbox = tk.Listbox(
                lb_frame,
                bg=ENTRY_BG,
                fg=TEXT,
                selectbackground=HIGHLIGHT,
                selectforeground=TEXT,
                relief="flat",
                font=("Courier New", 10),
                height=4,
                yscrollcommand=sb.set,
                activestyle="none",
            )
            sb.config(command=self.src_listbox.yview)
            sb.pack(side="right", fill="y")
            self.src_listbox.pack(side="left", fill="x", expand=True)

            # buttons
            src_btn_col = tk.Frame(list_row, bg=PANEL)
            src_btn_col.pack(side="left", padx=(8, 0), anchor="n")
            self._btn(src_btn_col, "+ Add", self._add_source, color=SUCCESS).pack(
                fill="x", pady=(0, 4)
            )
            self._btn(src_btn_col, "Remove", self._remove_source, color="#c0392b").pack(
                fill="x"
            )

            # ── Add / Edit Rule panel ──────
            add_frame = tk.LabelFrame(
                self,
                text=" Add / Edit Rule ",
                font=("Courier New", 9),
                bg=PANEL,
                fg=SUBTEXT,
                bd=1,
                padx=14,
                pady=10,
            )
            add_frame.pack(fill="x", padx=20, pady=6)

            ext_row = tk.Frame(add_frame, bg=PANEL)
            ext_row.pack(fill="x", pady=(0, 6))
            tk.Label(
                ext_row,
                text="Extensions (comma-separated, e.g. jpg, png, gif):",
                font=("Courier New", 9),
                bg=PANEL,
                fg=TEXT,
            ).pack(anchor="w")
            self.ext_var = tk.StringVar()
            tk.Entry(
                ext_row,
                textvariable=self.ext_var,
                bg=ENTRY_BG,
                fg=TEXT,
                insertbackground=TEXT,
                relief="flat",
                font=("Courier New", 11),
                bd=6,
            ).pack(fill="x")

            dst_row = tk.Frame(add_frame, bg=PANEL)
            dst_row.pack(fill="x", pady=(0, 6))
            tk.Label(
                dst_row,
                text="Destination folder:",
                font=("Courier New", 9),
                bg=PANEL,
                fg=TEXT,
            ).pack(anchor="w")
            dest_inp = tk.Frame(dst_row, bg=PANEL)
            dest_inp.pack(fill="x")
            self.dst_var = tk.StringVar()
            tk.Entry(
                dest_inp,
                textvariable=self.dst_var,
                bg=ENTRY_BG,
                fg=TEXT,
                insertbackground=TEXT,
                relief="flat",
                font=("Courier New", 11),
                bd=6,
            ).pack(side="left", fill="x", expand=True)
            self._btn(dest_inp, "Browse", self._browse_dest).pack(
                side="left", padx=(8, 0)
            )

            btn_row = tk.Frame(add_frame, bg=PANEL)
            btn_row.pack(fill="x", pady=(4, 0))
            self._btn(btn_row, "+ Add Rule", self._add_rule, color=SUCCESS).pack(
                side="left"
            )
            self._btn(btn_row, "Edit Selected", self._update_rule).pack(
                side="left", padx=8
            )
            self._btn(
                btn_row, "Delete Selected", self._delete_rule, color="#c0392b"
            ).pack(side="left")

            # ── Rules table ──────
            tbl_frame = tk.Frame(self, bg=BG)
            tbl_frame.pack(fill="x", padx=20, pady=(0, 4))
            tk.Label(
                tbl_frame,
                text="RULES",
                font=("Courier New", 9, "bold"),
                bg=BG,
                fg=HIGHLIGHT,
            ).pack(anchor="w", pady=(4, 2))

            style = ttk.Style()
            style.theme_use("clam")
            style.configure(
                "Treeview",
                background=ENTRY_BG,
                foreground=TEXT,
                fieldbackground=ENTRY_BG,
                rowheight=ROW_HEIGHT,
                font=("Courier New", 10),
            )
            style.configure(
                "Treeview.Heading",
                background=ACCENT,
                foreground=TEXT,
                font=("Courier New", 10, "bold"),
                relief="flat",
            )
            style.map("Treeview", background=[("selected", HIGHLIGHT)])

            cols = ("extensions", "destination")
            self.tree = ttk.Treeview(
                tbl_frame,
                columns=cols,
                show="headings",
                selectmode="browse",
                style="Treeview",
                height=0,
            )
            self.tree.heading("extensions", text="Extensions")
            self.tree.heading("destination", text="Destination Folder")
            self.tree.column("extensions", width=200, minwidth=120)
            self.tree.column("destination", width=520, minwidth=200)
            self.tree.pack(fill="x")
            self.tree.bind("<<TreeviewSelect>>", self._on_select)

            # ── Bottom bar ──────
            bar = tk.Frame(self, bg=BG, pady=10)
            bar.pack(fill="x", padx=20)
            self.status_var = tk.StringVar(value="Ready.")
            tk.Label(
                bar,
                textvariable=self.status_var,
                font=("Courier New", 9),
                bg=BG,
                fg=SUBTEXT,
            ).pack(side="left")
            self._btn(
                bar, "Sort Now", self._sort_files, color=HIGHLIGHT, font_size=12
            ).pack(side="right")

        def _btn(self, parent, text, cmd, color=ACCENT, font_size=10):
            return tk.Button(
                parent,
                text=text,
                command=cmd,
                bg=color,
                fg=TEXT,
                activebackground=HIGHLIGHT,
                activeforeground=TEXT,
                relief="flat",
                cursor="hand2",
                font=("Courier New", font_size, "bold"),
                padx=10,
                pady=4,
            )

        # ── Source folder helpers ──────

        def _refresh_sources(self):
            self.src_listbox.delete(0, "end")
            for s in self.sources:
                self.src_listbox.insert("end", s)

        def _add_source(self):
            d = filedialog.askdirectory(title="Select source folder")
            if d and d not in self.sources:
                self.sources.append(d)
                self._persist()
                self._refresh_sources()
                self.status_var.set(f"Source added: {d}")

        def _remove_source(self):
            sel = self.src_listbox.curselection()
            if not sel:
                return
            removed = self.sources.pop(sel[0])
            self._persist()
            self._refresh_sources()
            self.status_var.set(f"Source removed: {removed}")

        # ── Destination browse ──────

        def _browse_dest(self):
            d = filedialog.askdirectory(title="Select destination folder")
            if d:
                self.dst_var.set(d)

        # ── Rule helpers ──────

        def _parse_exts(self, raw: str) -> list:
            return [e.strip().lstrip(".").lower() for e in raw.split(",") if e.strip()]

        def _refresh_rules(self):
            self.tree.delete(*self.tree.get_children())
            for i, r in enumerate(self.rules):
                self.tree.insert(
                    "",
                    "end",
                    iid=str(i),
                    values=(", ".join(r["extensions"]), r["destination"]),
                )
            self.tree.configure(height=len(self.rules))
            self.update_idletasks()

        def _on_select(self, _=None):
            sel = self.tree.selection()
            if not sel:
                return
            r = self.rules[int(sel[0])]
            self.ext_var.set(", ".join(r["extensions"]))
            self.dst_var.set(r["destination"])

        def _add_rule(self):
            exts = self._parse_exts(self.ext_var.get())
            dst = self.dst_var.get().strip()
            if not exts or not dst:
                messagebox.showwarning(
                    "Missing info",
                    "Please enter at least one extension and a destination folder.",
                )
                return
            self.rules.append({"extensions": exts, "destination": dst})
            self._persist()
            self._refresh_rules()
            self.ext_var.set("")
            self.dst_var.set("")
            self.status_var.set(f"Rule added: {', '.join(exts)} -> {dst}")

        def _update_rule(self):
            sel = self.tree.selection()
            if not sel:
                messagebox.showinfo("No selection", "Select a rule to update.")
                return
            exts = self._parse_exts(self.ext_var.get())
            dst = self.dst_var.get().strip()
            if not exts or not dst:
                messagebox.showwarning(
                    "Missing info", "Please fill in extensions and destination."
                )
                return
            self.rules[int(sel[0])] = {"extensions": exts, "destination": dst}
            self._persist()
            self._refresh_rules()
            self.status_var.set("Rule updated.")

        def _delete_rule(self):
            sel = self.tree.selection()
            if not sel:
                messagebox.showinfo("No selection", "Select a rule to delete.")
                return
            removed = self.rules.pop(int(sel[0]))
            self._persist()
            self._refresh_rules()
            self.status_var.set(f"Deleted rule for: {', '.join(removed['extensions'])}")

        def _sort_files(self):
            if not self.sources:
                messagebox.showwarning(
                    "No sources", "Please add at least one source folder."
                )
                return
            if not self.rules:
                messagebox.showinfo(
                    "No rules", "Add at least one sorting rule before sorting."
                )
                return
            self._persist()
            moved, skipped, errors = run_sort(self.sources, self.rules)

            summary = f"{moved} file(s) moved, {skipped} skipped (no matching rule)."
            if errors:
                summary += f"  {len(errors)} error(s)."
                messagebox.showwarning(
                    "Sort complete with errors",
                    summary + "\n\n" + "\n".join(errors[:10]),
                )
            else:
                messagebox.showinfo("Sort complete", summary)
            self.status_var.set(summary)

    FileSorterApp().mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="File Sorter — GUI organizer with headless mode.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python file_sorter.py            open the GUI
  python file_sorter.py --sort     sort files silently using saved config, then exit
        """,
    )
    parser.add_argument(
        "--sort",
        action="store_true",
        help="Headless mode: sort files using the saved source folders and rules, then exit.",
    )
    args = parser.parse_args()

    if args.sort:
        headless_sort()
    else:
        launch_gui()
