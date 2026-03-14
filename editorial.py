#!/usr/bin/env python3
"""
editorial.py — Editorial: a smart text editor for fiction writers.

Features
--------
* Full-featured text editing  — New / Open / Save / Save As
* Standard clipboard          — Cut / Copy / Paste / Select All
* Unlimited Undo / Redo
* Line numbers
* Zoom (font size) in / out
* Word & character count
* Filter Words mode (toggle)  — highlights analysis results by context:
    Red    = obvious filter word in narration (POV subject present)
    Yellow = questionable (filter word in narration, context unclear)
    Purple = likely damaged quote / missing quote closer
"""

from __future__ import annotations
import os
import threading
import math
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import font as tkfont
from tkinter import ttk

from filter_analyzer import analyze_filter_words, find_quote_issues

# ---------------------------------------------------------------------------
# Colour palette  (Catppuccin Mocha-inspired dark theme)
# ---------------------------------------------------------------------------
BG          = "#1e1e2e"   # base background
BG_SURFACE  = "#181825"   # toolbar / panel background
BG_OVERLAY  = "#313244"   # hover / selection overlay
TEXT        = "#cdd6f4"   # primary text
TEXT_SUBTLE = "#6c7086"   # muted labels
ACCENT      = "#89b4fa"   # blue accent (cursor, scrollbar)

# Filter highlight colours
RED_FG    = "#f38ba8"
RED_BG    = "#3d1520"
YELLOW_FG = "#f9e2af"
YELLOW_BG = "#3d3210"
GREEN_FG  = "#a6e3a1"
GREEN_BG  = "#1a2e1e"
PURPLE_FG = "#1e1e2e"
PURPLE_BG = "#f5a6ff"
FIND_BG   = "#45475a"

POV_PRONOUN_MAP: dict[str, list[str]] = {
    "First Person (I/We)": ["i", "we", "me", "us"],
    "Third Person Male (He)": ["he", "him"],
    "Third Person Female (She)": ["she", "her"],
    "Third Person Plural (They)": ["they", "them"],
    "All Pronouns (Broad Scan)": ["i", "we", "he", "she", "they", "me", "us", "him", "her", "them"],
}


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class EditorialApp:
    """Main application window."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Editorial")
        self.root.geometry("1280x820")
        self.root.minsize(800, 520)
        self.root.configure(bg=BG)

        self.current_file: str | None = None
        self.filter_active: bool = False
        self._filter_job: str | None = None   # after() handle for debounce
        self._filter_processing: bool = False
        self._filter_rerun_requested: bool = False
        self._filter_hits: dict[str, list[tuple[int, int]]] = {
            "red": [], "yellow": [], "purple": []
        }
        self._enabled_filter_levels: set[str] = {"red", "yellow", "purple"}
        self._density_visible: bool = False
        self._filter_hits_lines: dict[str, list[int]] = {
            "red": [], "yellow": [], "purple": []
        }
        self._filter_hit_fracs: dict[str, list[float]] = {
            "red": [], "yellow": [], "purple": []
        }
        self._filter_run_seq: int = 0
        self._analysis_in_progress: bool = False
        self._progress_pulse_job: str | None = None
        self._progress_pulse_value: int = 1
        self._progress_pulse_dir: int = 1
        self._needs_cache_rebuild: bool = False
        self._density_static_dirty: bool = True
        self._density_viewport_id: int | None = None
        self._density_viewport_pending: bool = False
        self._density_draw_pending: bool = False
        self._layout_refresh_job: str | None = None
        self._cache_build_seq: int = 0
        self._skip_filter_schedule_once: bool = False
        self._find_dialog: tk.Toplevel | None = None
        self._find_var = tk.StringVar()
        self._replace_var = tk.StringVar()
        self._last_find_term = ""
        self._find_index = "1.0"
        self._pov_choice = tk.StringVar(value="All Pronouns (Broad Scan)")

        self._build_menu()
        self._build_toolbar()
        self._build_editor()
        self._build_statusbar()
        self._bind_shortcuts()
        self._update_status()

    # ------------------------------------------------------------------ menu

    def _build_menu(self) -> None:
        cfg = dict(bg=BG_SURFACE, fg=TEXT,
                   activebackground=ACCENT, activeforeground=BG,
                   tearoff=False)
        bar = tk.Menu(self.root, **cfg)

        # File ---------------------------------------------------------------
        fm = tk.Menu(bar, **cfg)
        fm.add_command(label="New",       command=self.new_file,     accelerator="Ctrl+N")
        fm.add_command(label="Open…",     command=self.open_file,    accelerator="Ctrl+O")
        fm.add_command(label="Save",      command=self.save_file,    accelerator="Ctrl+S")
        fm.add_command(label="Save As…",  command=self.save_file_as, accelerator="Ctrl+Shift+S")
        fm.add_separator()
        fm.add_command(label="Export Highlighted RTF…", command=self.export_highlighted_rtf)
        fm.add_command(label="Export Tagged Text…", command=self.export_tagged_text)
        fm.add_separator()
        fm.add_command(label="Exit",      command=self.quit_app)
        bar.add_cascade(label="File", menu=fm)

        # Edit ---------------------------------------------------------------
        em = tk.Menu(bar, **cfg)
        em.add_command(label="Undo",       command=self._undo,      accelerator="Ctrl+Z")
        em.add_command(label="Redo",       command=self._redo,      accelerator="Ctrl+Y")
        em.add_separator()
        em.add_command(label="Cut",        command=self.cut,        accelerator="Ctrl+X")
        em.add_command(label="Copy",       command=self.copy,       accelerator="Ctrl+C")
        em.add_command(label="Paste",      command=self.paste,      accelerator="Ctrl+V")
        em.add_separator()
        em.add_command(label="Select All", command=self.select_all, accelerator="Ctrl+A")
        em.add_separator()
        em.add_command(label="Find…",      command=self.show_find_dialog, accelerator="Ctrl+F")
        em.add_command(label="Replace…",   command=lambda: self.show_find_dialog(show_replace=True),
                   accelerator="Ctrl+H")
        bar.add_cascade(label="Edit", menu=em)

        # View ---------------------------------------------------------------
        vm = tk.Menu(bar, **cfg)
        self._show_lines_var = tk.BooleanVar(value=True)
        vm.add_checkbutton(label="Line Numbers",
                           variable=self._show_lines_var,
                           command=self._toggle_line_numbers)
        vm.add_separator()
        vm.add_command(label="Zoom In",  command=self._zoom_in,  accelerator="Ctrl+=")
        vm.add_command(label="Zoom Out", command=self._zoom_out, accelerator="Ctrl+-")
        bar.add_cascade(label="View", menu=vm)

        # Tools --------------------------------------------------------------
        tm = tk.Menu(bar, **cfg)
        tm.add_command(label="Toggle Filter Words",
                       command=self.toggle_filter, accelerator="Ctrl+Shift+F")
        tm.add_separator()
        tm.add_command(label="Word Count…", command=self._word_count_dialog)
        bar.add_cascade(label="Tools", menu=tm)

        self.root.config(menu=bar)

    # --------------------------------------------------------------- toolbar

    def _build_toolbar(self) -> None:
        self._toolbar = tk.Frame(self.root, bg=BG_SURFACE, pady=3)
        self._toolbar.pack(side=tk.TOP, fill=tk.X)

        # Filter Words toggle button
        self._filter_btn = tk.Button(
            self._toolbar, text="\u29c6  Filter Words: OFF",
            command=self.toggle_filter,
            bg=BG_SURFACE, fg=TEXT_SUBTLE,
            activebackground=BG_OVERLAY, activeforeground=TEXT,
            relief="flat", bd=0, padx=12, pady=5,
            cursor="hand2", font=("Segoe UI", 9, "bold"),
        )
        self._filter_btn.pack(side=tk.LEFT, padx=6)

        tk.Label(
            self._toolbar,
            text="POV Setting:",
            bg=BG_SURFACE,
            fg=TEXT_SUBTLE,
            font=("Segoe UI", 9),
        ).pack(side=tk.LEFT, padx=(10, 6))

        self._pov_combo = ttk.Combobox(
            self._toolbar,
            state="readonly",
            values=list(POV_PRONOUN_MAP.keys()),
            textvariable=self._pov_choice,
            width=28,
        )
        self._pov_combo.pack(side=tk.LEFT, padx=(0, 6))
        self._pov_combo.bind("<<ComboboxSelected>>", self._on_pov_changed)

        # Color-level controls (right-aligned, visible only when filter is ON)
        self._legend = tk.Frame(self._toolbar, bg=BG_SURFACE)

        bkw = dict(
            activebackground=BG_OVERLAY,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )

        self._red_btn = tk.Button(
            self._legend,
            text="\u25cf Obvious",
            command=lambda: self._toggle_filter_level("red"),
            **bkw,
        )
        self._yellow_btn = tk.Button(
            self._legend,
            text="\u25cf Questionable",
            command=lambda: self._toggle_filter_level("yellow"),
            **bkw,
        )
        self._purple_btn = tk.Button(
            self._legend,
            text="\u25cf Quote Errors",
            command=lambda: self._toggle_filter_level("purple"),
            **bkw,
        )

        self._red_btn.pack(side=tk.LEFT, padx=2)
        self._yellow_btn.pack(side=tk.LEFT, padx=2)
        self._purple_btn.pack(side=tk.LEFT, padx=2)
        self._update_level_buttons()

    # --------------------------------------------------------------- editor

    def _build_editor(self) -> None:
        container = tk.Frame(self.root, bg=BG)
        container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self._editor_font = tkfont.Font(family="Consolas", size=13)

        # Scrollbar
        self._scrollbar = tk.Scrollbar(
            container, bg=BG_SURFACE, troughcolor=BG,
            activebackground=ACCENT, width=12, relief="flat", bd=0,
        )
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Line-number canvas
        self._density = tk.Canvas(
            container, bg=BG_SURFACE, width=28, highlightthickness=0,
            cursor="hand2",
        )
        self._density.bind("<Button-1>", self._on_density_click)
        self._density.bind("<B1-Motion>", self._on_density_click)
        self._density.bind("<Configure>", self._on_density_configure)

        # Line-number canvas
        self._lineno = tk.Canvas(
            container, bg=BG_SURFACE, width=54, highlightthickness=0,
        )
        self._lineno.pack(side=tk.LEFT, fill=tk.Y)

        # Main text widget
        self.text = tk.Text(
            container,
            bg=BG, fg=TEXT,
            insertbackground=ACCENT,
            selectbackground=ACCENT, selectforeground=BG,
            font=self._editor_font,
            undo=True, maxundo=-1,
            wrap=tk.WORD,
            padx=22, pady=14,
            relief="flat", bd=0,
            highlightthickness=0,
            spacing1=3, spacing3=3,
            yscrollcommand=self._on_text_scroll,
        )
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._scrollbar.config(command=self._on_scrollbar_move)

        # Tag styles for each filter category
        self.text.tag_configure("filter_red",
                                background=RED_BG, foreground=RED_FG)
        self.text.tag_configure("filter_yellow",
                                background=YELLOW_BG, foreground=YELLOW_FG)
        self.text.tag_configure(
            "filter_purple",
            background=PURPLE_BG,
            foreground=PURPLE_FG,
            underline=1,
        )
        self.text.tag_configure("find_match",
                    background=FIND_BG, foreground=TEXT)

        # Event bindings
        self.text.bind("<KeyRelease>",    self._on_key_release)
        self.text.bind("<ButtonRelease>", self._on_cursor_move)
        self.text.bind("<Configure>", self._on_text_configure)
        self.text.bind("<<Copy>>", self._on_copy_event)

        # Defer first line-number draw until widget is fully rendered
        self.root.after(120, self._redraw_lineno)

    # ----------------------------------------------------------- status bar

    def _build_statusbar(self) -> None:
        bar = tk.Frame(self.root, bg="#11111b", height=26)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        bar.pack_propagate(False)

        lkw = dict(bg="#11111b", fg=TEXT_SUBTLE, font=("Segoe UI", 9),
                   padx=10, pady=3)

        self._lbl_words    = tk.Label(bar, text="Words: 0",   **lkw)
        self._lbl_chars    = tk.Label(bar, text="Chars: 0",   **lkw)
        self._lbl_pos      = tk.Label(bar, text="Ln 1, Col 1",**lkw)
        self._lbl_filter   = tk.Label(bar, text="",
                                      bg="#11111b", fg=ACCENT,
                                      font=("Segoe UI", 9), padx=10, pady=3)
        self._lbl_filename = tk.Label(bar, text="Untitled",   **lkw)

        self._lbl_words.pack(side=tk.LEFT)
        self._lbl_chars.pack(side=tk.LEFT)
        self._lbl_pos.pack(side=tk.LEFT)
        self._lbl_filter.pack(side=tk.RIGHT)
        self._lbl_filename.pack(side=tk.RIGHT)

    # ------------------------------------------------------------ shortcuts

    def _bind_shortcuts(self) -> None:
        root = self.root
        root.bind("<Control-n>",       lambda _e: self.new_file())
        root.bind("<Control-o>",       lambda _e: self.open_file())
        root.bind("<Control-s>",       lambda _e: self.save_file())
        root.bind("<Control-S>",       lambda _e: self.save_file_as())
        root.bind("<Control-Shift-s>", lambda _e: self.save_file_as())
        root.bind("<Control-Shift-F>", lambda _e: self.toggle_filter())
        root.bind("<Control-f>",       lambda _e: self.show_find_dialog())
        root.bind("<Control-h>",       lambda _e: self.show_find_dialog(show_replace=True))
        root.bind("<Control-equal>",   lambda _e: self._zoom_in())
        root.bind("<Control-minus>",   lambda _e: self._zoom_out())
        root.protocol("WM_DELETE_WINDOW", self.quit_app)

    # -------------------------------------------------------- scroll helpers

    def _on_scrollbar_move(self, *args) -> None:
        """Called when the user drags/clicks the scrollbar."""
        self.text.yview(*args)
        self._redraw_lineno()
        self._update_density_viewport()

    def _on_text_scroll(self, first: str, last: str) -> None:
        """Called when the text widget scrolls for any reason."""
        self._scrollbar.set(first, last)
        self._redraw_lineno()
        self._update_density_viewport()

    # -------------------------------------------------------------- file I/O

    def new_file(self) -> None:
        if not self._confirm_discard():
            return
        self.text.delete("1.0", tk.END)
        self.text.edit_reset()
        self.current_file = None
        self._set_title("Untitled")
        self._update_status()
        if self.filter_active:
            self.filter_active = False
            self._update_filter_btn()
            self._lbl_filter.config(text="")
            self._legend.pack_forget()
            self._hide_density_band()

    def open_file(self) -> None:
        if not self._confirm_discard():
            return
        path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"),
                       ("Markdown",   "*.md"),
                       ("All files",  "*.*")])
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
        except OSError as exc:
            messagebox.showerror("Open Error", str(exc))
            return
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", content)
        self.text.edit_reset()
        self.current_file = path
        self._set_title(os.path.basename(path))
        self._update_status()
        self._redraw_lineno()
        if self.filter_active:
            self._run_filter()

    def save_file(self) -> None:
        if self.current_file:
            self._write(self.current_file)
        else:
            self.save_file_as()

    def save_file_as(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"),
                       ("Markdown",   "*.md"),
                       ("All files",  "*.*")])
        if path:
            self._write(path)
            self.current_file = path
            self._set_title(os.path.basename(path))

    def export_highlighted_rtf(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".rtf",
            filetypes=[("Rich Text Format", "*.rtf"), ("All files", "*.*")],
        )
        if not path:
            return
        text = self.text.get("1.0", "end-1c")
        active_pov = list(self._get_active_pov_pronouns())

        def task():
            ranges = self._compute_export_ranges(text, active_pov)
            rtf = self._build_rtf_export(text, ranges)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(rtf)

        self._run_task_with_progress("Exporting RTF...", task, "RTF export complete.")

    def export_tagged_text(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        text = self.text.get("1.0", "end-1c")
        active_pov = list(self._get_active_pov_pronouns())

        def task():
            ranges = self._compute_export_ranges(text, active_pov)
            tagged = self._build_tagged_export(text, ranges)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(tagged)

        self._run_task_with_progress("Exporting tagged text...", task, "Tagged text export complete.")

    def _run_task_with_progress(self, title: str, task, success_message: str) -> None:
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.transient(self.root)
        dlg.resizable(False, False)
        dlg.configure(bg=BG_SURFACE)
        dlg.grab_set()

        panel = tk.Frame(dlg, bg=BG_SURFACE, padx=14, pady=12)
        panel.pack(fill=tk.BOTH, expand=True)
        tk.Label(panel, text=title, bg=BG_SURFACE, fg=TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        pb = ttk.Progressbar(panel, mode="indeterminate", length=280)
        pb.pack(fill=tk.X, pady=(10, 2))
        pb.start(12)

        def finish(error: Exception | None) -> None:
            try:
                pb.stop()
                dlg.grab_release()
                dlg.destroy()
            except Exception:
                pass
            if error is not None:
                messagebox.showerror("Export Error", str(error))
            else:
                messagebox.showinfo("Export", success_message)

        def worker() -> None:
            try:
                task()
                self.root.after(0, lambda: finish(None))
            except Exception as exc:
                self.root.after(0, lambda: finish(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _get_cached_export_ranges(self) -> list[tuple[int, int, str]] | None:
        if not (self.filter_active and any(self._filter_hits.values())):
            return None
        ranges: list[tuple[int, int, str]] = []
        for level in ("red", "yellow", "purple"):
            if level not in self._enabled_filter_levels:
                continue
            for ws, we in self._filter_hits.get(level, []):
                ranges.append((ws, we, level))
        return sorted(ranges, key=lambda x: x[0])

    def _compute_export_ranges(self, text: str, active_pov: list[str]) -> list[tuple[int, int, str]]:
        hits = analyze_filter_words(text, active_pov_pronouns=active_pov)
        hits.extend((start, end, "purple") for start, end in find_quote_issues(text))
        ranges = [(ws, we, cls) for ws, we, cls in hits if cls in self._enabled_filter_levels]
        return sorted(ranges, key=lambda x: x[0])

    def _build_tagged_export(self, text: str, ranges: list[tuple[int, int, str]]) -> str:
        if not ranges:
            return text

        id_map = {"red": "r", "yellow": "y", "purple": "p"}
        out: list[str] = []
        pos = 0

        for start, end, level in ranges:
            if start < pos:
                continue
            out.append(text[pos:start])
            word = text[start:end]
            out.append(f"[{id_map[level]}~{word}]")
            pos = end

        out.append(text[pos:])
        return "".join(out)

    def _rtf_escape(self, s: str) -> str:
        s = s.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        return s.replace("\n", r"\par " + "\n")

    def _text_char_length(self) -> int:
        try:
            return int(self.text.count("1.0", "end-1c", "chars")[0])
        except Exception:
            return len(self.text.get("1.0", "end-1c"))

    def _build_rtf_export(self, text: str, ranges: list[tuple[int, int, str]]) -> str:
        color_idx = {"red": 1, "yellow": 2, "purple": 3}

        chunks: list[str] = []
        pos = 0
        for start, end, level in ranges:
            if start < pos:
                continue
            if start > pos:
                chunks.append(self._rtf_escape(text[pos:start]))
            word = self._rtf_escape(text[start:end])
            chunks.append(r"{\cf" + str(color_idx[level]) + " " + word + r"\cf0 }")
            pos = end
        chunks.append(self._rtf_escape(text[pos:]))

        header = (
            r"{\rtf1\ansi\deff0"
            r"{\fonttbl{\f0 Consolas;}}"
            r"{\colortbl ;\red243\green139\blue168;\red249\green226\blue175;\red203\green166\blue247;}"
            r"\viewkind4\uc1\pard\f0\fs22 "
        )
        return header + "".join(chunks) + r"}"

    def _write(self, path: str) -> None:
        try:
            content = self.text.get("1.0", "end-1c")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            self.text.edit_modified(False)
        except OSError as exc:
            messagebox.showerror("Save Error", str(exc))

    def _confirm_discard(self) -> bool:
        """Return True if it is safe to discard the current document."""
        if not self.text.edit_modified():
            return True
        choice = messagebox.askyesnocancel(
            "Unsaved Changes",
            "Save changes before continuing?")
        if choice is None:
            return False
        if choice:
            self.save_file()
        return True

    def quit_app(self) -> None:
        if self._confirm_discard():
            self.root.destroy()

    # ---------------------------------------------------------- edit actions

    def _undo(self) -> None:
        try:
            self.text.edit_undo()
        except tk.TclError:
            pass

    def _redo(self) -> None:
        try:
            self.text.edit_redo()
        except tk.TclError:
            pass

    def cut(self)        -> None: self.text.event_generate("<<Cut>>")
    def copy(self)       -> None: self.text.event_generate("<<Copy>>")
    def paste(self)      -> None: self.text.event_generate("<<Paste>>")
    def select_all(self) -> None:
        self.text.tag_add(tk.SEL, "1.0", tk.END)
        self.text.mark_set(tk.INSERT, "end-1c")

    def show_find_dialog(self, show_replace: bool = False) -> None:
        if self._find_dialog and self._find_dialog.winfo_exists():
            self._find_dialog.deiconify()
            self._find_dialog.lift()
            self._find_dialog.focus_force()
            self._set_replace_visibility(show_replace)
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("Find / Replace")
        dlg.configure(bg=BG_SURFACE)
        dlg.resizable(False, False)
        dlg.transient(self.root)
        self._find_dialog = dlg

        panel = tk.Frame(dlg, bg=BG_SURFACE, padx=10, pady=10)
        panel.pack(fill=tk.BOTH, expand=True)

        lkw = dict(bg=BG_SURFACE, fg=TEXT, font=("Segoe UI", 9))
        ekw = dict(bg=BG, fg=TEXT, insertbackground=ACCENT,
                   relief="flat", width=34, font=("Segoe UI", 9))
        bkw = dict(bg=BG_OVERLAY, fg=TEXT,
                   activebackground=ACCENT, activeforeground=BG,
                   relief="flat", bd=0, padx=10, pady=4,
                   cursor="hand2", font=("Segoe UI", 9))

        tk.Label(panel, text="Find", **lkw).grid(row=0, column=0, sticky="w", pady=(0, 6))
        find_entry = tk.Entry(panel, textvariable=self._find_var, **ekw)
        find_entry.grid(row=0, column=1, columnspan=3, sticky="ew", padx=(8, 0), pady=(0, 6))

        self._replace_row = tk.Frame(panel, bg=BG_SURFACE)
        self._replace_row.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(0, 8))
        tk.Label(self._replace_row, text="Replace", **lkw).grid(row=0, column=0, sticky="w")
        replace_entry = tk.Entry(self._replace_row, textvariable=self._replace_var, **ekw)
        replace_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self._replace_row.grid_columnconfigure(1, weight=1)

        self._btn_find_next = tk.Button(panel, text="Find Next", command=self._find_next, **bkw)
        self._btn_find_next.grid(row=2, column=0, sticky="ew", pady=(0, 2))
        self._btn_replace = tk.Button(panel, text="Replace", command=self._replace_next, **bkw)
        self._btn_replace.grid(row=2, column=1, sticky="ew", padx=(6, 0), pady=(0, 2))
        self._btn_replace_all = tk.Button(panel, text="Replace All", command=self._replace_all, **bkw)
        self._btn_replace_all.grid(row=2, column=2, sticky="ew", padx=(6, 0), pady=(0, 2))
        tk.Button(panel, text="Close", command=self._close_find_dialog, **bkw).grid(
            row=2, column=3, sticky="ew", padx=(6, 0), pady=(0, 2)
        )

        panel.grid_columnconfigure(3, weight=1)

        find_entry.bind("<Return>", lambda _e: self._find_next())
        replace_entry.bind("<Return>", lambda _e: self._replace_next())
        dlg.bind("<Escape>", lambda _e: self._close_find_dialog())
        dlg.protocol("WM_DELETE_WINDOW", self._close_find_dialog)

        self._set_replace_visibility(show_replace)
        find_entry.focus_set()

    def _set_replace_visibility(self, show_replace: bool) -> None:
        if show_replace:
            self._replace_row.grid()
            self._btn_replace.grid()
            self._btn_replace_all.grid()
        else:
            self._replace_row.grid_remove()
            self._btn_replace.grid_remove()
            self._btn_replace_all.grid_remove()

    def _close_find_dialog(self) -> None:
        self._clear_find_tag()
        if self._find_dialog and self._find_dialog.winfo_exists():
            self._find_dialog.destroy()
        self._find_dialog = None

    def _clear_find_tag(self) -> None:
        self.text.tag_remove("find_match", "1.0", tk.END)

    def _find_next(self) -> None:
        needle = self._find_var.get()
        if not needle:
            return

        start = self._find_index if needle == self._last_find_term else self.text.index(tk.INSERT)
        idx = self.text.search(needle, start, stopindex=tk.END, nocase=True)
        if not idx:
            idx = self.text.search(needle, "1.0", stopindex=start, nocase=True)
        if not idx:
            self.root.bell()
            return

        end = f"{idx}+{len(needle)}c"
        self._clear_find_tag()
        self.text.tag_remove(tk.SEL, "1.0", tk.END)
        self.text.tag_add("find_match", idx, end)
        self.text.tag_add(tk.SEL, idx, end)
        self.text.mark_set(tk.INSERT, end)
        self.text.see(idx)
        self._last_find_term = needle
        self._find_index = end

    def _replace_next(self) -> None:
        needle = self._find_var.get()
        if not needle:
            return

        replaced = False
        try:
            sel_start = self.text.index(tk.SEL_FIRST)
            sel_end = self.text.index(tk.SEL_LAST)
            selected = self.text.get(sel_start, sel_end)
            if selected.lower() == needle.lower():
                replacement = self._replace_var.get()
                self.text.delete(sel_start, sel_end)
                self.text.insert(sel_start, replacement)
                new_end = f"{sel_start}+{len(replacement)}c"
                self.text.tag_add(tk.SEL, sel_start, new_end)
                self.text.mark_set(tk.INSERT, new_end)
                self._find_index = new_end
                replaced = True
        except tk.TclError:
            pass

        if not replaced:
            self._find_next()
            return

        self._update_status()
        if self.filter_active:
            self._schedule_filter()
        self._find_next()

    def _replace_all(self) -> None:
        needle = self._find_var.get()
        if not needle:
            return

        replacement = self._replace_var.get()
        start = "1.0"
        count = 0

        while True:
            idx = self.text.search(needle, start, stopindex=tk.END, nocase=True)
            if not idx:
                break
            end = f"{idx}+{len(needle)}c"
            self.text.delete(idx, end)
            self.text.insert(idx, replacement)
            start = f"{idx}+{len(replacement)}c"
            count += 1

        self._clear_find_tag()
        self._find_index = "1.0"
        self._update_status()
        if self.filter_active:
            self._schedule_filter()
        messagebox.showinfo("Replace All", f"Replaced {count} occurrence(s).")

    # ------------------------------------------------------- filter feature

    def toggle_filter(self) -> None:
        if self._filter_processing:
            self._filter_rerun_requested = True
            return

        self.filter_active = not self.filter_active
        self._update_filter_btn()
        if self.filter_active:
            self._legend.pack(side=tk.RIGHT, padx=14)
            self._show_density_band()
            self._run_filter()
        else:
            self._clear_filter()
            self._lbl_filter.config(text="")
            self._legend.pack_forget()
            self._hide_density_band()

    def _set_filter_processing(self, percent: int) -> None:
        pct = max(1, min(100, int(percent)))
        self._filter_btn.config(
            text=f"\u29c6  Processing {pct}%",
            fg=ACCENT,
            bg=BG_OVERLAY,
        )

    def _update_filter_btn(self) -> None:
        if self.filter_active:
            self._filter_btn.config(
                text="\u29c6  Filter Words: ON",
                fg=GREEN_FG, bg=GREEN_BG,
            )
        else:
            self._filter_btn.config(
                text="\u29c6  Filter Words: OFF",
                fg=TEXT_SUBTLE, bg=BG_SURFACE,
            )

    def _clear_filter(self) -> None:
        for tag in ("filter_red", "filter_yellow", "filter_purple"):
            self.text.tag_remove(tag, "1.0", tk.END)
        self._filter_hits_lines = {"red": [], "yellow": [], "purple": []}
        self._filter_hit_fracs = {"red": [], "yellow": [], "purple": []}

    def _update_level_buttons(self) -> None:
        styles = {
            "red": (self._red_btn, RED_FG, RED_BG),
            "yellow": (self._yellow_btn, YELLOW_FG, YELLOW_BG),
            "purple": (self._purple_btn, PURPLE_FG, PURPLE_BG),
        }
        for level, (btn, fg, bg) in styles.items():
            active = level in self._enabled_filter_levels
            if active:
                btn.config(fg=fg, bg=bg)
            else:
                btn.config(fg=TEXT_SUBTLE, bg=BG_SURFACE)

    def _toggle_filter_level(self, level: str) -> None:
        if not self.filter_active or self._filter_processing:
            return

        if level in self._enabled_filter_levels:
            self._enabled_filter_levels.remove(level)
            add_mode = False
        else:
            self._enabled_filter_levels.add(level)
            add_mode = True

        self._update_level_buttons()
        ranges = self._filter_hits.get(level, [])
        if not ranges:
            return

        self._filter_processing = True
        self._needs_cache_rebuild = False
        self._apply_ranges_progressive(level, ranges, add_mode, self._finish_filter_processing)

    def _finish_filter_processing(self) -> None:
        self._analysis_in_progress = False
        if self._progress_pulse_job is not None:
            self.root.after_cancel(self._progress_pulse_job)
            self._progress_pulse_job = None
        if self._needs_cache_rebuild:
            self._set_filter_processing(95)
            self._rebuild_filter_line_cache_async(self._finalize_filter_processing, show_progress=True)
            return
        self._finalize_filter_processing()

    def _finalize_filter_processing(self) -> None:
        self._filter_processing = False
        self._needs_cache_rebuild = False
        if self.filter_active:
            self._update_filter_btn()
        self._update_level_buttons()
        self._request_density_redraw()
        if self._filter_rerun_requested and self.filter_active:
            self._filter_rerun_requested = False
            self._run_filter()

    def _apply_ranges_progressive(
        self,
        level: str,
        ranges: list[tuple[int, int]],
        add_mode: bool,
        done_callback,
    ) -> None:
        tag = f"filter_{level}"
        total = len(ranges)
        if total == 0:
            self._set_filter_processing(100)
            self.root.after(1, done_callback)
            return

        step = 400
        idx = 0

        def run_chunk() -> None:
            nonlocal idx
            end = min(idx + step, total)
            for ws, we in ranges[idx:end]:
                s = f"1.0 + {ws}c"
                e = f"1.0 + {we}c"
                if add_mode:
                    self.text.tag_add(tag, s, e)
                else:
                    self.text.tag_remove(tag, s, e)
            idx = end
            pct = int((idx / total) * 100)
            self._set_filter_processing(pct)
            if idx < total:
                self.root.after(1, run_chunk)
            else:
                done_callback()

        run_chunk()

    def _apply_visible_levels_progressive(self, done_callback) -> None:
        ops: list[tuple[str, int, int]] = []
        for level, ranges in self._filter_hits.items():
            if level not in self._enabled_filter_levels:
                continue
            for ws, we in ranges:
                ops.append((f"filter_{level}", ws, we))

        total = len(ops)
        if total == 0:
            self._set_filter_processing(100)
            self.root.after(1, done_callback)
            return

        step = 500
        idx = 0

        def run_chunk() -> None:
            nonlocal idx
            end = min(idx + step, total)
            for tag, ws, we in ops[idx:end]:
                self.text.tag_add(tag, f"1.0 + {ws}c", f"1.0 + {we}c")
            idx = end
            pct = 86 + int((idx / total) * 9)
            self._set_filter_processing(pct)
            if idx < total:
                self.root.after(1, run_chunk)
            else:
                done_callback()

        run_chunk()

    def _run_filter(self) -> None:
        if not self.filter_active:
            return
        if self._filter_processing:
            self._filter_rerun_requested = True
            return

        self._filter_processing = True
        self._analysis_in_progress = True
        self._needs_cache_rebuild = True
        self._filter_run_seq += 1
        run_id = self._filter_run_seq
        self._progress_pulse_value = 2
        self._set_filter_processing(1)
        self._clear_filter()
        content = self.text.get("1.0", tk.END)
        active_pov = self._get_active_pov_pronouns()
        self._start_progress_pulse()
        self._start_filter_analysis_async(run_id, content, active_pov)

    def _start_progress_pulse(self) -> None:
        if self._progress_pulse_job is not None:
            self.root.after_cancel(self._progress_pulse_job)

        self._progress_pulse_value = 5

        def tick() -> None:
            if not self._analysis_in_progress:
                self._progress_pulse_job = None
                return

            self._progress_pulse_value = min(85, self._progress_pulse_value + 2)

            self._set_filter_processing(self._progress_pulse_value)
            self._progress_pulse_job = self.root.after(80, tick)

        self._progress_pulse_job = self.root.after(80, tick)

    def _start_filter_analysis_async(self, run_id: int, content: str, active_pov: list[str]) -> None:
        def worker() -> None:
            try:
                raw_hits = analyze_filter_words(content, active_pov_pronouns=active_pov)
                raw_hits.extend((start, end, "purple") for start, end in find_quote_issues(content))
                grouped: dict[str, list[tuple[int, int]]] = {"red": [], "yellow": [], "purple": []}
                for ws, we, cls in raw_hits:
                    if cls in grouped:
                        grouped[cls].append((ws, we))
                counts = {
                    "red": len(grouped["red"]),
                    "yellow": len(grouped["yellow"]),
                    "purple": len(grouped["purple"]),
                }
                self.root.after(0, lambda: self._complete_filter_analysis(run_id, grouped, counts, None))
            except Exception as exc:
                self.root.after(0, lambda: self._complete_filter_analysis(run_id, None, None, exc))

        threading.Thread(target=worker, daemon=True).start()

    def _complete_filter_analysis(self, run_id: int, grouped, counts, error: Exception | None) -> None:
        if run_id != self._filter_run_seq:
            return

        if error is not None:
            self._filter_processing = False
            self._analysis_in_progress = False
            if self._progress_pulse_job is not None:
                self.root.after_cancel(self._progress_pulse_job)
                self._progress_pulse_job = None
            self.filter_active = False
            self._legend.pack_forget()
            self._hide_density_band()
            self._update_filter_btn()
            self._lbl_filter.config(text="")
            messagebox.showerror("Filter Analyzer Error", str(error))
            return

        self._analysis_in_progress = False
        if self._progress_pulse_job is not None:
            self.root.after_cancel(self._progress_pulse_job)
            self._progress_pulse_job = None

        self._filter_hits = grouped
        self._set_filter_processing(86)

        self._lbl_filter.config(
            text=(f"Filter \u2014  "
                  f"\u25cf {counts['red']} obvious   "
                  f"\u25cf {counts['yellow']} questionable   "
                  f"\u25cf {counts['purple']} quote issues")
        )
        self._apply_visible_levels_progressive(self._finish_filter_processing)

    def _rebuild_filter_line_cache_async(self, done_callback, show_progress: bool = False) -> None:
        self._cache_build_seq += 1
        build_seq = self._cache_build_seq

        levels = ["red", "yellow", "purple"]
        self._filter_hits_lines = {"red": [], "yellow": [], "purple": []}
        self._filter_hit_fracs = {"red": [], "yellow": [], "purple": []}

        try:
            total_display_lines = int(self.text.count("1.0", "end-1c", "displaylines")[0])
        except Exception:
            total_display_lines = 1
        total_display_lines = max(1, total_display_lines)

        ops: list[tuple[str, int]] = []
        for lvl in levels:
            for ws, we in self._filter_hits.get(lvl, []):
                ops.append((lvl, (ws + we) // 2))

        # Sort by position so the density band fills top-to-bottom during progressive draws
        ops.sort(key=lambda x: x[1])

        total = len(ops)
        if total == 0:
            self.root.after(1, done_callback)
            return

        idx = 0
        step = 300
        prev_idx_str = "1.0"
        prev_disp = 0

        def run_chunk() -> None:
            nonlocal idx, prev_idx_str, prev_disp
            if build_seq != self._cache_build_seq:
                return

            end = min(total, idx + step)
            for lvl, mid in ops[idx:end]:
                try:
                    idx_str = self.text.index(f"1.0 + {mid}c")
                    line = int(idx_str.split(".")[0])
                    delta = int(self.text.count(prev_idx_str, idx_str, "displaylines")[0])
                    disp = prev_disp + max(0, delta)
                except Exception:
                    try:
                        idx_str = self.text.index(f"1.0 + {mid}c")
                        line = int(idx_str.split(".")[0])
                        disp = int(self.text.count("1.0", idx_str, "displaylines")[0])
                    except Exception:
                        continue

                prev_idx_str = idx_str
                prev_disp = disp

                frac = max(0.0, min(0.999999, disp / total_display_lines))
                self._filter_hits_lines[lvl].append(line)
                self._filter_hit_fracs[lvl].append(frac)

            idx = end
            if show_progress:
                pct = 96 + int((idx / total) * 4)
                self._set_filter_processing(pct)
            # Draw whatever we have so far — band fills top-to-bottom progressively
            if self._density_visible:
                self._request_density_redraw()
            if idx < total:
                self.root.after(1, run_chunk)
            else:
                done_callback()

        run_chunk()

    def _schedule_filter(self) -> None:
        """Debounce: re-analyse 700 ms after the last keystroke."""
        if not self.filter_active:
            return
        if self._filter_job is not None:
            self.root.after_cancel(self._filter_job)
        self._filter_job = self.root.after(700, self._run_filter)

    def _get_active_pov_pronouns(self) -> list[str]:
        return POV_PRONOUN_MAP.get(self._pov_choice.get(), POV_PRONOUN_MAP["All Pronouns (Broad Scan)"])

    def _on_pov_changed(self, _event=None) -> None:
        if self.filter_active:
            self._schedule_filter()

    def _on_text_configure(self, _event=None) -> None:
        self._schedule_layout_refresh()

    def _schedule_layout_refresh(self) -> None:
        if not self.filter_active or self._filter_processing:
            return
        if self._layout_refresh_job is not None:
            self.root.after_cancel(self._layout_refresh_job)

        def run() -> None:
            self._layout_refresh_job = None
            if not self.filter_active or self._filter_processing:
                return
            self._rebuild_filter_line_cache_async(self._request_density_redraw, show_progress=False)

        self._layout_refresh_job = self.root.after(220, run)

    # ------------------------------------------------------- view / display

    def _zoom_in(self) -> None:
        self._editor_font.config(size=self._editor_font.cget("size") + 1)
        self.root.after(20, self._redraw_lineno)
        self._schedule_layout_refresh()

    def _zoom_out(self) -> None:
        s = self._editor_font.cget("size")
        if s > 7:
            self._editor_font.config(size=s - 1)
            self.root.after(20, self._redraw_lineno)
            self._schedule_layout_refresh()

    def _toggle_line_numbers(self) -> None:
        if self._show_lines_var.get():
            self._lineno.pack(side=tk.LEFT, fill=tk.Y, before=self.text)
            self._redraw_lineno()
        else:
            self._lineno.pack_forget()

    def _show_density_band(self) -> None:
        if self._density_visible:
            return
        self._density.pack(side=tk.LEFT, fill=tk.Y, before=self._lineno)
        self._density_visible = True
        self._request_density_redraw()

    def _hide_density_band(self) -> None:
        if not self._density_visible:
            return
        self._density.pack_forget()
        self._density_visible = False
        self._density_viewport_id = None

    def _on_density_configure(self, _event=None) -> None:
        self._request_density_redraw()

    def _on_density_click(self, event) -> None:
        if not self.filter_active:
            return
        h = max(1, self._density.winfo_height())
        frac = max(0.0, min(1.0, event.y / h))
        self.text.yview_moveto(frac)
        self._redraw_lineno()
        self._update_density_viewport()

    def _request_density_redraw(self) -> None:
        self._density_static_dirty = True
        if self._density_draw_pending:
            return
        self._density_draw_pending = True

        def go() -> None:
            self._density_draw_pending = False
            self._redraw_density_band_static()
            self._update_density_viewport()

        self.root.after(16, go)

    def _update_density_viewport(self) -> None:
        if not self.filter_active or not self._density_visible:
            return
        if self._density_viewport_pending:
            return
        self._density_viewport_pending = True

        def go() -> None:
            self._density_viewport_pending = False
            width = max(20, self._density.winfo_width())
            height = max(20, self._density.winfo_height())
            first, last = self.text.yview()
            y1 = int(first * height)
            y2 = max(y1 + 6, int(last * height))
            if self._density_viewport_id is None:
                self._density_viewport_id = self._density.create_rectangle(
                    0, y1, width - 1, y2, outline=ACCENT, width=1
                )
            else:
                self._density.coords(self._density_viewport_id, 0, y1, width - 1, y2)
                self._density.tag_raise(self._density_viewport_id)

        self.root.after(16, go)

    def _redraw_density_band_static(self) -> None:
        if not self._density_static_dirty:
            return
        self._density_static_dirty = False
        self._density.delete("all")
        self._density_viewport_id = None
        if not self.filter_active or not self._density_visible:
            return

        width = max(20, self._density.winfo_width())
        height = max(20, self._density.winfo_height())

        first, last = self.text.yview()
        span = max(0.01, last - first)
        pages = max(1, int(math.ceil(1.0 / span)))

        page_counts: list[dict[str, int]] = [
            {"red": 0, "yellow": 0, "purple": 0} for _ in range(pages)
        ]

        # Fallback: if display-line cache is empty but highlights exist, use
        # cheap char-offset fractions so the sidebar never appears blank.
        if not any(self._filter_hit_fracs.values()) and any(self._filter_hits.values()):
            total_chars = max(1, self._text_char_length())
            for level in ("red", "yellow", "purple"):
                fracs: list[float] = []
                for ws, we in self._filter_hits.get(level, []):
                    mid = (ws + we) // 2
                    fracs.append(max(0.0, min(0.999999, mid / total_chars)))
                self._filter_hit_fracs[level] = fracs

        for level in ("red", "yellow", "purple"):
            if level not in self._enabled_filter_levels:
                continue
            for frac in self._filter_hit_fracs.get(level, []):
                page_idx = min(pages - 1, max(0, int(frac * pages)))
                page_counts[page_idx][level] += 1

        max_total = max((sum(p.values()) for p in page_counts), default=0)
        avail_w = max(1, width - 2)

        for i, counts in enumerate(page_counts):
            y1 = int((i * height) / pages)
            y2 = max(y1 + 1, int(((i + 1) * height) / pages))

            total = counts["red"] + counts["yellow"] + counts["purple"]
            if total <= 0 or max_total <= 0:
                continue

            row_w = max(1, int((total / max_total) * avail_w))
            red_w = int(row_w * (counts["red"] / total))
            yellow_w = int(row_w * (counts["yellow"] / total))
            purple_w = row_w - red_w - yellow_w

            x = 1
            if red_w > 0:
                self._density.create_rectangle(x, y1, x + red_w, y2, fill=RED_FG, outline="")
                x += red_w
            if yellow_w > 0:
                self._density.create_rectangle(x, y1, x + yellow_w, y2, fill=YELLOW_FG, outline="")
                x += yellow_w
            if purple_w > 0:
                self._density.create_rectangle(x, y1, x + purple_w, y2, fill=PURPLE_FG, outline="")

    def _redraw_lineno(self, *_args) -> None:
        """Repaint the line-number gutter to match the current scroll position."""
        self._lineno.delete("all")

        # Keep gutter wide enough for the highest visible/logical line number.
        try:
            max_line = int(self.text.index("end-1c").split(".")[0])
        except Exception:
            max_line = 1
        digits = max(2, len(str(max_line)))
        needed = self._editor_font.measure("9" * digits) + 16
        cur_w = int(self._lineno.cget("width"))
        if needed != cur_w:
            self._lineno.config(width=needed)

        x = int(self._lineno.cget("width")) - 6
        i = self.text.index("@0,0")
        last_linenum: str | None = None
        while True:
            dline = self.text.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            linenum = i.split(".")[0]
            if linenum != last_linenum:
                self._lineno.create_text(
                    x, y + 2, anchor="ne",
                    text=linenum,
                    fill=TEXT_SUBTLE,
                    font=self._editor_font,
                )
                last_linenum = linenum
            nxt = self.text.index(f"{i}+1line")
            if nxt == i:
                break
            i = nxt

    # ---------------------------------------------------------- status bar

    def _update_status(self) -> None:
        content = self.text.get("1.0", "end-1c")
        words = len(content.split()) if content.strip() else 0
        chars = len(content)
        self._lbl_words.config(text=f"Words: {words}")
        self._lbl_chars.config(text=f"Chars: {chars}")
        try:
            row, col = self.text.index(tk.INSERT).split(".")
            self._lbl_pos.config(text=f"Ln {row}, Col {int(col) + 1}")
        except Exception:
            pass

    def _set_title(self, name: str) -> None:
        self._lbl_filename.config(text=name)
        self.root.title(f"Editorial \u2014 {name}")

    def _word_count_dialog(self) -> None:
        content = self.text.get("1.0", "end-1c")
        words = len(content.split()) if content.strip() else 0
        chars = len(content)
        paras = len([p for p in content.split("\n\n") if p.strip()])
        sents = sum(content.count(c) for c in ".!?")
        messagebox.showinfo(
            "Word Count",
            f"Words:       {words}\n"
            f"Characters:  {chars}\n"
            f"Sentences:   {sents}\n"
            f"Paragraphs:  {paras}",
        )

    # -------------------------------------------------------- event handlers

    def _on_key_release(self, _event=None) -> None:
        self._update_status()
        self._redraw_lineno()
        if self._skip_filter_schedule_once:
            self._skip_filter_schedule_once = False
            return
        if self.filter_active and self._should_schedule_filter_for_key(_event):
            self._schedule_filter()

    def _on_copy_event(self, _event=None) -> None:
        self._skip_filter_schedule_once = True

    def _should_schedule_filter_for_key(self, event) -> bool:
        if event is None:
            return True
        keysym = getattr(event, "keysym", "")
        if keysym in {
            "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R",
            "Caps_Lock", "Escape", "Left", "Right", "Up", "Down",
            "Prior", "Next", "Home", "End",
        }:
            return False

        # Ignore common non-editing Ctrl shortcuts. Keep Ctrl+V editable.
        state = int(getattr(event, "state", 0))
        if (state & 0x4) and keysym.lower() in {"c", "a", "f", "h", "s", "o", "n", "z", "y"}:
            return False
        return True

    def _on_cursor_move(self, _event=None) -> None:
        self._update_status()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    root = tk.Tk()
    EditorialApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
