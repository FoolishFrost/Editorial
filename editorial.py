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
    Yellow = likely damaged quote / missing quote closer
"""

from __future__ import annotations
import json
import os
import threading
import math
import re
import ctypes
import subprocess
import webbrowser
from collections import Counter
from urllib import error as urlerror
from urllib import request as urlrequest
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import font as tkfont
from tkinter import ttk
from spacy.lang.en.stop_words import STOP_WORDS

from editorial_indicators import IndicatorSubsystem
from editorial_modes import ModeSubsystem
from filter_analyzer import analyze_dialogue_mechanics, analyze_filter_words, analyze_weak_modifiers

APP_NAME = "Editorial"
APP_VERSION = "1.1.0"
COMPANY_NAME = "Foolish Designs"
CREATOR_NAME = "John Bowden"
SUPPORT_EMAIL = "johnbowden@foolishdesigns.com"
GITHUB_REPO = "FoolishFrost/Editorial"
WIKI_URL = "https://github.com/FoolishFrost/Editorial/wiki"
RELEASES_URL = "https://github.com/FoolishFrost/Editorial/releases"
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

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
GREEN_FG  = "#a6e3a1"
GREEN_BG  = "#1a2e1e"
PURPLE_FG = "#1e1e2e"
PURPLE_BG = "#f9e2af"
ORANGE_FG = "#f2cd96"
ORANGE_BG = "#4a3320"
BLUE_FG   = "#89b4fa"
BLUE_BG   = "#1f2b40"
WHITE_FG  = "#f5f5f5"
WHITE_BG  = "#3a3a3a"
FIND_BG   = "#45475a"

POV_PRONOUN_MAP: dict[str, list[str]] = {
    "First Person (I/We)": ["i", "we", "me", "us"],
    "Third Person Male (He)": ["he", "him"],
    "Third Person Female (She)": ["she", "her"],
    "Third Person Plural (They)": ["they", "them"],
    "All Pronouns (Broad Scan)": ["i", "we", "he", "she", "they", "me", "us", "him", "her", "them"],
}

EDITOR_MODE_OFF = "off"
EDITOR_MODE_FILTER = "filter_words"
EDITOR_MODE_WEAK = "weak_modifiers"
EDITOR_MODE_PUNCT = "dialogue_punctuation"

EDITOR_MODES: list[tuple[str, str]] = [
    ("Editor Off", EDITOR_MODE_OFF),
    ("Filter Words", EDITOR_MODE_FILTER),
    ("Weak Modifiers", EDITOR_MODE_WEAK),
    ("Punctuation & Dialogue", EDITOR_MODE_PUNCT),
]


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class EditorialApp:
    """Main application window."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1280x820")
        self.root.minsize(800, 520)
        self.root.configure(bg=BG)

        self.current_file: str | None = None
        self.filter_active: bool = False
        self._filter_processing: bool = False
        self._filter_update_needed: bool = False
        self._weak_update_needed: bool = False
        self._punct_update_needed: bool = False
        self._weak_mod_active: bool = False
        self._weak_mod_processing: bool = False
        self._weak_mod_run_seq: int = 0
        self._punct_active: bool = False
        self._punct_processing: bool = False
        self._punct_run_seq: int = 0
        self._active_editor_mode: str = EDITOR_MODE_OFF
        self._editor_mode_var = tk.StringVar(value=EDITOR_MODE_OFF)
        self._editor_mode_label_var = tk.StringVar(value="Editor Off")
        self._mode_to_label = {value: label for label, value in EDITOR_MODES}
        self._label_to_mode = {label: value for label, value in EDITOR_MODES}
        self._weak_mod_hits: list[tuple[int, int]] = []
        self._weak_hit_fracs: list[float] = []
        self._punct_hits: dict[str, list[tuple[int, int]]] = {
            "quote": [],
            "dash": [],
            "ellipsis": [],
            "loud": [],
        }
        self._punct_dot_fracs: dict[str, list[float]] = {
            "quote": [],
            "dash": [],
            "ellipsis": [],
            "loud": [],
        }
        self._filter_hits: dict[str, list[tuple[int, int]]] = {
            "red": [], "purple": []
        }
        self._density_visible: bool = False
        self._quote_band_visible: bool = False
        self._filter_hits_lines: dict[str, list[int]] = {"red": [], "purple": []}
        self._filter_hit_fracs: dict[str, list[float]] = {"red": [], "purple": []}
        self._filter_run_seq: int = 0
        self._analysis_in_progress: bool = False
        self._progress_pulse_job: str | None = None
        self._progress_pulse_value: int = 1
        self._progress_pulse_dir: int = 1
        self._needs_cache_rebuild: bool = False
        self._density_static_dirty: bool = True
        self._density_viewport_id: int | None = None
        self._density_viewport_canvas: tk.Canvas | None = None
        self._density_viewport_pending: bool = False
        self._density_draw_pending: bool = False
        self._layout_refresh_job: str | None = None
        self._resize_settle_job: str | None = None
        self._resize_in_progress: bool = False
        self._cache_build_seq: int = 0
        self._skip_filter_schedule_once: bool = False
        self._ui_lock_count: int = 0
        self._ui_menu_locked: bool = False
        self._ui_locked_controls: list[tuple[tk.Widget, str]] = []
        self._text_locked_prev_state: str = "normal"
        self._editor_progress_pct: int | None = None
        self._tools_mode_entries: list[tuple[int, str, str]] = []
        self._tools_refresh_index: int | None = None
        self._find_dialog: tk.Toplevel | None = None
        self._find_var = tk.StringVar()
        self._replace_var = tk.StringVar()
        self._last_find_term = ""
        self._find_index = "1.0"
        self._pov_choice = tk.StringVar(value="All Pronouns (Broad Scan)")
        self._pov_names_var = tk.StringVar()
        self._pov_names_dialog: tk.Toplevel | None = None
        self._pov_names_edit_var = tk.StringVar()
        self._settings_path = self._get_settings_path()
        self._load_user_settings()
        self._modes = ModeSubsystem(self)
        for method_name in ModeSubsystem.EXPORTED_METHODS:
            setattr(self, method_name, getattr(self._modes, method_name))
        self._indicators = IndicatorSubsystem(
            self,
            {
                "ACCENT": ACCENT,
                "BG_OVERLAY": BG_OVERLAY,
                "PURPLE_BG": PURPLE_BG,
                "BLUE_FG": BLUE_FG,
                "WHITE_FG": WHITE_FG,
                "RED_FG": RED_FG,
                "ORANGE_FG": ORANGE_FG,
            },
        )

        self._build_menu()
        self._build_toolbar()
        self._build_statusbar()
        self._build_editor()
        self._bind_shortcuts()
        self.root.bind("<Configure>", self._on_root_configure)
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
        exm = tk.Menu(fm, **cfg)
        exm.add_command(label="Highlighted RTF…", command=self.export_highlighted_rtf)
        exm.add_command(label="Tagged Text…", command=self.export_tagged_text)
        fm.add_cascade(label="Export", menu=exm)
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
        self._indent_first_line_var = tk.BooleanVar(value=True)
        vm.add_checkbutton(label="Line Numbers",
                           variable=self._show_lines_var,
                           command=self._toggle_line_numbers)
        vm.add_checkbutton(label="Indent First Line",
                   variable=self._indent_first_line_var,
                   command=self._toggle_first_line_indent)
        vm.add_separator()
        vm.add_command(label="Zoom In",  command=self._zoom_in,  accelerator="Ctrl+=")
        vm.add_command(label="Zoom Out", command=self._zoom_out, accelerator="Ctrl+-")
        bar.add_cascade(label="View", menu=vm)

        # Tools --------------------------------------------------------------
        tm = tk.Menu(bar, **cfg)
        tm.add_radiobutton(
            label="Editor Off",
            variable=self._editor_mode_var,
            value=EDITOR_MODE_OFF,
            command=self._on_tools_mode_selected,
        )
        self._tools_mode_entries.append((int(tm.index("end")), "Editor Off", EDITOR_MODE_OFF))
        tm.add_radiobutton(
            label="Filter Words",
            variable=self._editor_mode_var,
            value=EDITOR_MODE_FILTER,
            command=self._on_tools_mode_selected,
            accelerator="Ctrl+Shift+F",
        )
        self._tools_mode_entries.append((int(tm.index("end")), "Filter Words", EDITOR_MODE_FILTER))
        tm.add_radiobutton(
            label="Weak Modifiers",
            variable=self._editor_mode_var,
            value=EDITOR_MODE_WEAK,
            command=self._on_tools_mode_selected,
            accelerator="Ctrl+Shift+W",
        )
        self._tools_mode_entries.append((int(tm.index("end")), "Weak Modifiers", EDITOR_MODE_WEAK))
        tm.add_radiobutton(
            label="Punctuation & Dialogue",
            variable=self._editor_mode_var,
            value=EDITOR_MODE_PUNCT,
            command=self._on_tools_mode_selected,
            accelerator="Ctrl+Shift+P",
        )
        self._tools_mode_entries.append((int(tm.index("end")), "Punctuation & Dialogue", EDITOR_MODE_PUNCT))
        tm.add_separator()
        tm.add_command(label="Refresh", command=self._on_filter_refresh_clicked)
        self._tools_refresh_index = int(tm.index("end"))
        tm.add_command(label="Set POV Names…", command=self.show_pov_names_dialog)
        tm.add_separator()
        tm.add_command(label="Word Count…", command=self._word_count_dialog)
        bar.add_cascade(label="Tools", menu=tm)

        # Help ---------------------------------------------------------------
        hm = tk.Menu(bar, **cfg)
        hm.add_command(label="Docs", command=self.open_docs)
        hm.add_command(label="Check for Updates", command=self.check_for_updates)
        hm.add_separator()
        hm.add_command(label="About Editorial", command=self.show_about_dialog)
        bar.add_cascade(label="Help", menu=hm)

        self._menus: list[tk.Menu] = [fm, em, vm, tm, hm]
        self._tools_menu = tm

        self.root.config(menu=bar)

    # --------------------------------------------------------------- toolbar

    def _build_toolbar(self) -> None:
        self._toolbar = tk.Frame(self.root, bg=BG_SURFACE, pady=3)
        self._toolbar.pack(side=tk.TOP, fill=tk.X)

        tk.Label(
            self._toolbar,
            text="Editorial Mode:",
            bg=BG_SURFACE,
            fg=TEXT_SUBTLE,
            font=("Segoe UI", 9),
        ).pack(side=tk.LEFT, padx=(8, 6))

        self._mode_combo = ttk.Combobox(
            self._toolbar,
            state="readonly",
            values=[label for label, _ in EDITOR_MODES],
            textvariable=self._editor_mode_label_var,
            width=24,
        )
        self._mode_combo.pack(side=tk.LEFT, padx=(0, 8))
        self._mode_combo.bind("<<ComboboxSelected>>", self._on_mode_combo_selected)

        self._mode_progress_label = tk.Label(
            self._toolbar,
            text="",
            bg=BG_SURFACE,
            fg=ACCENT,
            font=("Segoe UI", 9, "bold"),
            padx=6,
        )
        self._mode_progress_label.pack(side=tk.LEFT)

        self._pov_label = tk.Label(
            self._toolbar,
            text="POV Setting:",
            bg=BG_SURFACE,
            fg=TEXT_SUBTLE,
            font=("Segoe UI", 9),
        )

        self._pov_combo = ttk.Combobox(
            self._toolbar,
            state="readonly",
            values=list(POV_PRONOUN_MAP.keys()),
            textvariable=self._pov_choice,
            width=28,
        )
        self._pov_combo.bind("<<ComboboxSelected>>", self._on_pov_changed)

        self._ngram_btn = tk.Button(
            self._toolbar,
            text="N-gram Scan",
            command=self.run_ngram_scan,
            bg=BG_OVERLAY,
            fg=TEXT,
            activebackground=ACCENT,
            activeforeground=BG,
            relief="flat",
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )
        self._ngram_btn.pack(side=tk.RIGHT, padx=(6, 8))

        self._filter_refresh_btn = tk.Button(
            self._toolbar,
            text="Refresh",
            command=self._on_filter_refresh_clicked,
            bg=BG_OVERLAY,
            fg=TEXT,
            activebackground=ACCENT,
            activeforeground=BG,
            relief="flat",
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )

        self._sync_editor_mode_ui()

    # --------------------------------------------------------------- editor

    def _build_editor(self) -> None:
        container = tk.Frame(self.root, bg=BG)
        container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self._editor_container = container

        self._editor_font = tkfont.Font(family="Consolas", size=13)

        # Scrollbar
        self._scrollbar = tk.Scrollbar(
            container, bg=BG_SURFACE, troughcolor=BG,
            activebackground=ACCENT, width=12, relief="flat", bd=0,
        )
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Right analysis panel (shown on demand)
        self._analysis_panel = tk.Frame(container, bg=BG_SURFACE, width=380)
        self._analysis_panel.pack_propagate(False)
        self._analysis_title = tk.Label(
            self._analysis_panel,
            text="Overused Combinations",
            bg=BG_SURFACE,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            padx=10,
            pady=8,
        )
        self._analysis_title.pack(fill=tk.X)
        self._analysis_close = tk.Button(
            self._analysis_panel,
            text="Close",
            command=self._hide_analysis_panel,
            bg=BG_OVERLAY,
            fg=TEXT,
            activebackground=ACCENT,
            activeforeground=BG,
            relief="flat",
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )
        self._analysis_close.pack(anchor="e", padx=8, pady=(0, 4))

        self._ngram_style = ttk.Style(self.root)
        try:
            if self._ngram_style.theme_use() != "clam":
                self._ngram_style.theme_use("clam")
        except tk.TclError:
            pass
        self._ngram_style.configure(
            "Ngram.Treeview",
            background=BG,
            fieldbackground=BG,
            foreground=TEXT,
            rowheight=22,
            borderwidth=0,
            font=("Segoe UI", 9),
        )
        self._ngram_style.configure(
            "Ngram.Treeview.Heading",
            background=BG_OVERLAY,
            foreground=TEXT,
            relief="flat",
            font=("Segoe UI", 9, "bold"),
        )
        self._ngram_style.map(
            "Ngram.Treeview",
            background=[("selected", ACCENT)],
            foreground=[("selected", BG)],
        )

        self._analysis_tables_host = tk.Frame(self._analysis_panel, bg=BG_SURFACE)
        self._analysis_tables_host.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        def make_section(title: str) -> ttk.Treeview:
            frame = tk.LabelFrame(
                self._analysis_tables_host,
                text=title,
                bg=BG_SURFACE,
                fg=TEXT,
                padx=6,
                pady=6,
                font=("Segoe UI", 9, "bold"),
                relief="groove",
                bd=1,
            )
            frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
            tree = ttk.Treeview(
                frame,
                columns=("gram", "count"),
                show="",
                style="Ngram.Treeview",
                selectmode="browse",
                height=5,
            )
            tree.column("gram", width=240, anchor="w", stretch=True)
            tree.column("count", width=80, anchor="e", stretch=False)

            header = tk.Frame(frame, bg=BG_OVERLAY)
            header.pack(fill=tk.X, pady=(0, 4))
            tk.Label(
                header,
                text="Phrase",
                bg=BG_OVERLAY,
                fg=TEXT,
                font=("Segoe UI", 9, "bold"),
                anchor="w",
            ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0), pady=4)
            tk.Label(
                header,
                text="Count",
                bg=BG_OVERLAY,
                fg=TEXT,
                font=("Segoe UI", 9, "bold"),
                anchor="e",
                width=8,
            ).pack(side=tk.RIGHT, padx=(0, 6), pady=4)

            yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=yscroll.set)
            yscroll.pack(side=tk.RIGHT, fill=tk.Y)
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            return tree

        self._single_tree = make_section("Top Single Words")
        self._pairs_tree = make_section("Top Word Pairs")
        self._triples_tree = make_section("Top Word Triples")
        self._analysis_visible = False

        # Density mini-map canvas (red filter hits)
        self._density = tk.Canvas(
            container, bg=BG_SURFACE, width=28, highlightthickness=0,
            cursor="hand2",
        )
        self._density.bind("<Button-1>", self._on_density_click)
        self._density.bind("<B1-Motion>", self._on_density_drag)
        self._density.bind("<Configure>", self._on_density_configure)

        # Quote-warning dot band (yellow dots)
        self._quote_dots = tk.Canvas(
            container, bg=BG_SURFACE, width=30, highlightthickness=0,
            cursor="hand2",
        )
        self._quote_dots.bind("<Button-1>", self._on_quote_band_click)
        self._quote_dots.bind("<B1-Motion>", self._on_quote_band_drag)
        self._quote_dots.bind("<Configure>", self._on_density_configure)

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
        self.text.tag_configure(
            "filter_purple",
            background=PURPLE_BG,
            foreground=PURPLE_FG,
            underline=1,
        )
        self.text.tag_configure(
            "filter_orange",
            background=ORANGE_BG,
            foreground=ORANGE_FG,
        )
        self.text.tag_configure(
            "filter_blue",
            background=BLUE_BG,
            foreground=BLUE_FG,
        )
        self.text.tag_configure(
            "filter_white",
            background=WHITE_BG,
            foreground=WHITE_FG,
        )
        self.text.tag_configure(
            "punct_quote",
            background=PURPLE_BG,
            foreground=PURPLE_FG,
            underline=1,
        )
        self.text.tag_configure(
            "punct_dash",
            background=BLUE_BG,
            foreground=BLUE_FG,
            underline=1,
        )
        self.text.tag_configure(
            "punct_ellipsis",
            background=WHITE_BG,
            foreground=WHITE_FG,
            underline=1,
        )
        self.text.tag_configure(
            "punct_loud",
            background=RED_BG,
            foreground=RED_FG,
            underline=1,
        )
        self.text.tag_configure("find_match",
                    background=FIND_BG, foreground=TEXT)
        self.text.tag_configure("first_line_indent", lmargin1=0, lmargin2=0)
        self._apply_first_line_indent()

        # Event bindings
        self.text.bind("<KeyRelease>",    self._on_key_release)
        self.text.bind("<ButtonRelease>", self._on_cursor_move)
        self.text.bind("<Configure>", self._on_text_configure)
        self.text.bind("<<Copy>>", self._on_copy_event)
        self.text.bind("<Control-MouseWheel>", self._on_ctrl_mousewheel)

        # Defer first line-number draw until widget is fully rendered
        self.root.after(120, self._redraw_lineno)

    def _show_analysis_panel(self) -> None:
        if self._analysis_visible:
            return
        self._analysis_panel.pack(side=tk.RIGHT, fill=tk.Y, before=self._scrollbar)
        self._analysis_visible = True

    def _hide_analysis_panel(self) -> None:
        if not self._analysis_visible:
            return
        self._analysis_panel.pack_forget()
        self._analysis_visible = False

    def _populate_ngram_table(self, table: ttk.Treeview, items: list[tuple[str, int]]) -> None:
        table.delete(*table.get_children())
        if not items:
            table.insert("", tk.END, values=("(none)", "-"))
            return
        for gram, count in items:
            table.insert("", tk.END, values=(gram, str(count)))

    # ----------------------------------------------------------- status bar

    def _build_statusbar(self) -> None:
        bar_h = 30
        bar = tk.Frame(self.root, bg="#11111b", height=bar_h)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        bar.pack_propagate(False)
        self._statusbar = bar
        self._statusbar_h = bar_h

        lkw = dict(bg="#11111b", fg=TEXT_SUBTLE, font=("Segoe UI", 9),
                   padx=10, pady=0)

        self._lbl_words    = tk.Label(bar, text="Words: 0",   **lkw)
        self._lbl_chars    = tk.Label(bar, text="Chars: 0",   **lkw)
        self._lbl_pos      = tk.Label(bar, text="Ln 1, Col 1",**lkw)
        self._lbl_filter   = tk.Label(bar, text="",
                                      bg="#11111b", fg=ACCENT,
                                      font=("Segoe UI", 9), padx=10, pady=3)
        self._legend_frame = tk.Frame(bar, bg="#11111b")

        self._lbl_words.pack(side=tk.LEFT)
        self._lbl_chars.pack(side=tk.LEFT)
        self._lbl_pos.pack(side=tk.LEFT)
        self._lbl_filter.pack(side=tk.LEFT, padx=22)
        self._legend_frame.pack(side=tk.LEFT, padx=(8, 0))

        # Reserve a full-height square at the bottom-right for easy resize grip targeting.
        self._grip_slot = tk.Frame(bar, bg="#11111b", width=bar_h, height=bar_h)
        self._grip_slot.pack(side=tk.RIGHT, fill=tk.Y)
        self._grip_slot.pack_propagate(False)

        self._sizegrip = ttk.Sizegrip(self._grip_slot)
        self._sizegrip.place(relx=1.0, rely=1.0, relwidth=1.0, relheight=1.0, anchor="se")
        self._update_status_legend()

    # ------------------------------------------------------------ shortcuts

    def _bind_shortcuts(self) -> None:
        root = self.root
        root.bind("<Control-n>",       lambda _e: self.new_file())
        root.bind("<Control-o>",       lambda _e: self.open_file())
        root.bind("<Control-s>",       lambda _e: self.save_file())
        root.bind("<Control-S>",       lambda _e: self.save_file_as())
        root.bind("<Control-Shift-s>", lambda _e: self.save_file_as())
        root.bind("<Control-Shift-F>", lambda _e: self._toggle_editor_mode_shortcut(EDITOR_MODE_FILTER))
        root.bind("<Control-Shift-W>", lambda _e: self._toggle_editor_mode_shortcut(EDITOR_MODE_WEAK))
        root.bind("<Control-Shift-P>", lambda _e: self._toggle_editor_mode_shortcut(EDITOR_MODE_PUNCT))
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
        self._apply_first_line_indent()
        self.text.edit_reset()
        self.current_file = None
        self._set_title("Untitled")
        self.set_editor_mode(EDITOR_MODE_OFF)

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
        self._apply_first_line_indent()
        self.text.edit_reset()
        self.current_file = path
        self._set_title(os.path.basename(path))
        self._update_status()
        self._redraw_lineno()
        if self._weak_mod_active:
            self.refresh_weak_modifiers()
        if self.filter_active:
            self._clear_filter()
            self._mark_filter_needs_update()

    def _toggle_editor_mode_shortcut(self, mode: str) -> None:
        current = self._active_editor_mode
        if current == mode:
            self.set_editor_mode(EDITOR_MODE_OFF)
            return
        self.set_editor_mode(mode)

    def _on_mode_combo_selected(self, _event=None) -> None:
        selected = self._editor_mode_label_var.get().strip()
        self.set_editor_mode(self._label_to_mode.get(selected, EDITOR_MODE_OFF))

    def _on_tools_mode_selected(self) -> None:
        self.set_editor_mode(self._editor_mode_var.get())

    def _set_editor_progress(self, percent: int | None, prefix: str) -> None:
        if percent is None:
            self._editor_progress_pct = None
            self._mode_progress_label.config(text="")
            return
        pct = max(0, min(100, int(percent)))
        self._editor_progress_pct = pct
        self._mode_progress_label.config(text=f"Processing {pct}%")

    def _refresh_tools_mode_markers(self) -> None:
        menu = getattr(self, "_tools_menu", None)
        if menu is None:
            return
        active = self._active_editor_mode
        for idx, base_label, mode in self._tools_mode_entries:
            mark = "● " if mode == active else "  "
            try:
                menu.entryconfig(idx, label=f"{mark}{base_label}")
            except Exception:
                continue

    def _start_filter_bootstrap_progress(self, run_id: int) -> None:
        def tick() -> None:
            if run_id != self._filter_run_seq or not self._filter_processing:
                return
            cur = self._editor_progress_pct or 2
            if cur < 35:
                self._set_filter_processing(cur + 1)
                self.root.after(90, tick)

        self.root.after(120, tick)

    def _is_editor_processing(self) -> bool:
        return self._filter_processing or self._weak_mod_processing or self._punct_processing

    def _sync_editor_mode_ui(self) -> None:
        mode = self._active_editor_mode or EDITOR_MODE_OFF
        self._editor_mode_var.set(mode)
        self._editor_mode_label_var.set(self._mode_to_label.get(mode, "Editor Off"))
        self._update_status_legend()
        self._refresh_tools_mode_markers()

        if self._tools_menu is not None and self._tools_refresh_index is not None:
            refresh_state = "disabled" if mode == EDITOR_MODE_OFF else "normal"
            try:
                self._tools_menu.entryconfig(self._tools_refresh_index, state=refresh_state)
            except Exception:
                pass

        if mode == EDITOR_MODE_FILTER:
            if not self._pov_label.winfo_manager():
                self._pov_label.pack(side=tk.LEFT, padx=(8, 6))
            if not self._pov_combo.winfo_manager():
                self._pov_combo.pack(side=tk.LEFT, padx=(0, 6))
        else:
            if self._pov_combo.winfo_manager():
                self._pov_combo.pack_forget()
            if self._pov_label.winfo_manager():
                self._pov_label.pack_forget()

    def set_editor_mode(self, mode: str) -> None:
        if mode not in self._mode_to_label:
            mode = EDITOR_MODE_OFF

        if self._is_editor_processing() and mode != self._active_editor_mode:
            self.root.bell()
            return

        current = self._active_editor_mode
        self._active_editor_mode = mode
        self._sync_editor_mode_ui()

        if mode == current:
            return

        self._filter_update_needed = False
        self._weak_update_needed = False
        self._punct_update_needed = False
        self._hide_filter_refresh_button()

        if mode == EDITOR_MODE_OFF:
            if self.filter_active:
                self.filter_active = False
                self._clear_filter()
            if self._weak_mod_active:
                self._weak_mod_active = False
                self._clear_weak_modifiers()
            if self._punct_active:
                self._punct_active = False
                self._clear_dialogue_mechanics()
            self._set_editor_progress(None, "")
            self._lbl_filter.config(text="")
            self._hide_quote_band()
            self._hide_density_band()
            return

        if mode == EDITOR_MODE_FILTER:
            if self._weak_mod_active:
                self._weak_mod_active = False
                self._clear_weak_modifiers()
            if self._punct_active:
                self._punct_active = False
                self._clear_dialogue_mechanics()
            self.filter_active = True
            self._show_density_band()
            self._hide_quote_band()
            self._run_filter()
            return

        if mode == EDITOR_MODE_WEAK:
            if self.filter_active:
                self.filter_active = False
                self._clear_filter()
            if self._punct_active:
                self._punct_active = False
                self._clear_dialogue_mechanics()
            self._filter_update_needed = False
            self._hide_filter_refresh_button()
            self._hide_quote_band()
            self._show_density_band()
            self._weak_mod_active = True
            self._run_weak_modifiers()
            return

        if mode == EDITOR_MODE_PUNCT:
            if self.filter_active:
                self.filter_active = False
                self._clear_filter()
            if self._weak_mod_active:
                self._weak_mod_active = False
                self._clear_weak_modifiers()
            self._filter_update_needed = False
            self._hide_filter_refresh_button()
            self._hide_density_band()
            self._show_quote_band()
            self._punct_active = True
            self._run_dialogue_mechanics()

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
        pov_names = self._get_active_pov_names()
        mode = self._active_editor_mode

        def task() -> None:
            ranges = self._collect_export_ranges(mode, text, active_pov, pov_names)
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
        pov_names = self._get_active_pov_names()
        mode = self._active_editor_mode

        def task() -> None:
            ranges = self._collect_export_ranges(mode, text, active_pov, pov_names)
            label_map: dict[str, str] | None = None
            if mode == EDITOR_MODE_PUNCT:
                label_map = {"quote": "QUOTE", "dash": "DASH", "ellipsis": "ELLIPSIS", "loud": "LOUD"}
            tagged = self._build_tagged_export(text, ranges, label_map)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(tagged)

        self._run_task_with_progress("Exporting tagged text...", task, "Tagged text export complete.")

    def _run_task_with_progress(self, title: str, task, success_message: str) -> None:
        self._acquire_ui_lock()
        dlg = tk.Toplevel(self.root)
        dlg.withdraw()
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
        self._center_popup(dlg)

        def finish(error: Exception | None) -> None:
            try:
                pb.stop()
                dlg.grab_release()
                dlg.destroy()
            except Exception:
                pass
            self._release_ui_lock()
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

    def run_ngram_scan(self) -> None:
        if self._ui_lock_count > 0:
            return

        text = self.text.get("1.0", "end-1c")
        if not text.strip():
            messagebox.showinfo("N-gram Scan", "No text to analyze.")
            return

        self._acquire_ui_lock()
        dlg = tk.Toplevel(self.root)
        dlg.withdraw()
        dlg.title("Scanning Overused Combinations")
        dlg.transient(self.root)
        dlg.resizable(False, False)
        dlg.configure(bg=BG_SURFACE)
        dlg.grab_set()

        panel = tk.Frame(dlg, bg=BG_SURFACE, padx=14, pady=12)
        panel.pack(fill=tk.BOTH, expand=True)
        tk.Label(panel, text="Analyzing text...", bg=BG_SURFACE, fg=TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        pct_var = tk.StringVar(value="0%")
        tk.Label(panel, textvariable=pct_var, bg=BG_SURFACE, fg=TEXT_SUBTLE, font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 6))
        pb = ttk.Progressbar(panel, mode="determinate", maximum=100, length=300)
        pb.pack(fill=tk.X)
        self._center_popup(dlg)

        token_re = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

        # Standard NLP practice: remove function/stop words and short fillers
        # so frequency outputs emphasize semantically meaningful terms.
        filler_words = {
            "um", "uh", "hmm", "ah", "oh", "okay", "ok", "like",
            "well", "just", "really", "very", "quite", "actually",
            "basically", "literally", "perhaps", "maybe",
        }
        blocked_words = {w.replace("\u2019", "'") for w in STOP_WORDS}
        blocked_words.update(filler_words)

        def set_progress(val: int) -> None:
            p = max(0, min(100, int(val)))
            pb["value"] = p
            pct_var.set(f"{p}%")

        def render_results(result: dict[str, list[tuple[str, int]]]) -> None:
            self._populate_ngram_table(self._single_tree, result["single"])
            self._populate_ngram_table(self._pairs_tree, result["pairs"])
            self._populate_ngram_table(self._triples_tree, result["triples"])
            self._show_analysis_panel()

        def finish(error: Exception | None, result: dict[str, list[tuple[str, int]]] | None) -> None:
            try:
                dlg.grab_release()
                dlg.destroy()
            except Exception:
                pass
            self._release_ui_lock()
            if error is not None:
                messagebox.showerror("N-gram Scan", str(error))
                return
            if result is not None:
                render_results(result)

        def worker() -> None:
            try:
                # Normalize smart apostrophes so contractions stay intact.
                ngram_text = text.lower().replace("\u2019", "'")
                raw_tokens = [m.group(0) for m in token_re.finditer(ngram_text)]
                tokens = [
                    tok for tok in raw_tokens
                    if tok.replace("'", "").isalpha() and len(tok) > 1 and tok not in blocked_words
                ]
                total = len(tokens)
                if total == 0:
                    self.root.after(0, lambda: finish(None, {"single": [], "pairs": [], "triples": []}))
                    return

                self.root.after(0, lambda: set_progress(10))
                uni: Counter[str] = Counter(tokens)

                self.root.after(0, lambda: set_progress(45))
                bi: Counter[tuple[str, str]] = Counter(zip(tokens, tokens[1:]))

                self.root.after(0, lambda: set_progress(75))
                tri: Counter[tuple[str, str, str]] = Counter(zip(tokens, tokens[1:], tokens[2:]))

                top_single = [(w, c) for w, c in uni.most_common(10)]
                top_pairs = [(" ".join(k), c) for k, c in bi.most_common(10)]
                top_triples = [(" ".join(k), c) for k, c in tri.most_common(10)]

                result = {
                    "single": top_single,
                    "pairs": top_pairs,
                    "triples": top_triples,
                }
                self.root.after(0, lambda: set_progress(100))
                self.root.after(0, lambda: finish(None, result))
            except Exception as exc:
                self.root.after(0, lambda: finish(exc, None))

        threading.Thread(target=worker, daemon=True).start()

    def _collect_export_ranges(
        self,
        mode: str,
        text: str,
        active_pov: list[str],
        pov_names: set[str] | None = None,
    ) -> list[tuple[int, int, str]]:
        if mode == EDITOR_MODE_WEAK:
            if not self._weak_update_needed and self._weak_mod_hits:
                return sorted(
                    [(ws, we, "orange") for ws, we in self._weak_mod_hits],
                    key=lambda x: x[0],
                )
            hits_raw = analyze_weak_modifiers(text)
            return sorted(
                [(ws, we, "orange") for ws, we, _cls in hits_raw],
                key=lambda x: x[0],
            )
        if mode == EDITOR_MODE_PUNCT:
            ranges: list[tuple[int, int, str]] = []
            if not self._punct_update_needed and any(self._punct_hits.values()):
                for cls, hits in self._punct_hits.items():
                    for ws, we in hits:
                        ranges.append((ws, we, cls))
                return sorted(ranges, key=lambda x: x[0])
            for ws, we, cls in analyze_dialogue_mechanics(text):
                ranges.append((ws, we, cls))
            return sorted(ranges, key=lambda x: x[0])
        if mode == EDITOR_MODE_FILTER:
            if not self._filter_update_needed and any(self._filter_hits.values()):
                ranges = []
                for level in ("red", "purple"):
                    for ws, we in self._filter_hits.get(level, []):
                        ranges.append((ws, we, level))
                return sorted(ranges, key=lambda x: x[0])
            hits_raw = analyze_filter_words(
                text,
                pov_character_names=pov_names,
                active_pov_pronouns=active_pov,
            )
            return sorted(
                [(ws, we, "red" if cls == "yellow" else cls) for ws, we, cls in hits_raw],
                key=lambda x: x[0],
            )
        return []

    def _build_tagged_export(
        self,
        text: str,
        ranges: list[tuple[int, int, str]],
        label_map: dict[str, str] | None = None,
    ) -> str:
        if not ranges:
            return text

        out: list[str] = []
        pos = 0

        for start, end, level in ranges:
            if start < pos:
                continue
            out.append(text[pos:start])
            word = text[start:end]
            if label_map and level in label_map:
                out.append(f"[{label_map[level]}:{word}]")
            else:
                out.append(f"[{word}]")
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
        # Color table entries mirror the exact hex pairs used by in-app text tags.
        # Index 0 is the implicit "auto" entry (before first semicolon).
        # cf = foreground index, highlight = background index — same values as app constants.
        #
        # Color table:
        #  1 RED_FG   #f38ba8  \red243\green139\blue168
        #  2 RED_BG   #3d1520  \red61\green21\blue32
        #  3 ORANGE_FG #f2cd96 \red242\green205\blue150
        #  4 ORANGE_BG #4a3320 \red74\green51\blue32
        #  5 PURPLE_FG #1e1e2e \red30\green30\blue46
        #  6 PURPLE_BG #f9e2af \red249\green226\blue175
        #  7 BLUE_FG  #89b4fa  \red137\green180\blue250
        #  8 BLUE_BG  #1f2b40  \red31\green43\blue64
        #  9 WHITE_FG #f5f5f5  \red245\green245\blue245
        # 10 WHITE_BG #3a3a3a  \red58\green58\blue58
        level_colors: dict[str, tuple[int, int, bool]] = {
            "red":      (1, 2),   # filter words:     RED_FG on RED_BG
            "orange":   (3, 4),   # weak modifiers:   ORANGE_FG on ORANGE_BG
            "quote":    (5, 6),   # quote issues:     PURPLE_FG on PURPLE_BG
            "dash":     (7, 8),   # dashes:           BLUE_FG on BLUE_BG
            "ellipsis": (9, 10),  # ellipsis:         WHITE_FG on WHITE_BG
            "loud":     (1, 2),   # loud punctuation: RED_FG on RED_BG
            "purple":   (5, 6),   # legacy quote:     PURPLE_FG on PURPLE_BG
        }

        chunks: list[str] = []
        pos = 0
        for start, end, level in ranges:
            if start < pos:
                continue
            if start > pos:
                chunks.append(self._rtf_escape(text[pos:start]))
            word = self._rtf_escape(text[start:end])
            cf, highlight = level_colors.get(level, (1, 2))
            underline = level in {"quote", "dash", "ellipsis", "loud"}
            prefix = r"{\cf" + str(cf) + r"\highlight" + str(highlight) + " "
            if underline:
                prefix += r"\ul "
            suffix = r"\ul0\highlight0\cf0 }" if underline else r"\highlight0\cf0 }"
            chunks.append(prefix + word + suffix)
            pos = end
        chunks.append(self._rtf_escape(text[pos:]))

        color_table = (
            r"{\colortbl ;"
            r"\red243\green139\blue168;"   #  1 RED_FG   #f38ba8
            r"\red61\green21\blue32;"      #  2 RED_BG   #3d1520
            r"\red242\green205\blue150;"   #  3 ORANGE_FG #f2cd96
            r"\red74\green51\blue32;"      #  4 ORANGE_BG #4a3320
            r"\red30\green30\blue46;"      #  5 PURPLE_FG #1e1e2e
            r"\red249\green226\blue175;"   #  6 PURPLE_BG #f9e2af
            r"\red137\green180\blue250;"   #  7 BLUE_FG  #89b4fa
            r"\red31\green43\blue64;"      #  8 BLUE_BG  #1f2b40
            r"\red245\green245\blue245;"   #  9 WHITE_FG #f5f5f5
            r"\red58\green58\blue58;"      # 10 WHITE_BG #3a3a3a
            r"}"
        )
        header = (
            r"{\rtf1\ansi\deff0"
            r"{\fonttbl{\f0 Consolas;}}"
            + color_table +
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

    def cut(self) -> None:
        self.text.event_generate("<<Cut>>")
        self._mark_active_mode_needs_update()

    def copy(self) -> None:
        self.text.event_generate("<<Copy>>")

    def paste(self) -> None:
        self.text.event_generate("<<Paste>>")
        self._mark_active_mode_needs_update()
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
        dlg.withdraw()
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
        self._center_popup(dlg)
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
        self._mark_active_mode_needs_update()
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
        self._mark_active_mode_needs_update()
        messagebox.showinfo("Replace All", f"Replaced {count} occurrence(s).")

    def _get_active_pov_pronouns(self) -> list[str]:
        return POV_PRONOUN_MAP.get(self._pov_choice.get(), POV_PRONOUN_MAP["All Pronouns (Broad Scan)"])

    def _get_settings_path(self) -> str:
        base = os.getenv("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, COMPANY_NAME, APP_NAME, "settings.json")

    def _get_legacy_settings_path(self) -> str:
        base = os.getenv("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "Editorial", "settings.json")

    def _load_user_settings(self) -> None:
        data: dict[str, object] | None = None
        try:
            with open(self._settings_path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
                if isinstance(loaded, dict):
                    data = loaded
        except Exception:
            pass

        if data is None:
            legacy = self._get_legacy_settings_path()
            try:
                with open(legacy, "r", encoding="utf-8") as fh:
                    loaded = json.load(fh)
                    if isinstance(loaded, dict):
                        data = loaded
            except Exception:
                return

        names = data.get("pov_names", "")
        if isinstance(names, str):
            self._pov_names_var.set(names)

    def _save_user_settings(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._settings_path), exist_ok=True)
            data = {
                "pov_names": self._pov_names_var.get().strip(),
            }
            with open(self._settings_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
        except Exception:
            pass

    def _get_active_pov_names(self) -> set[str]:
        if self._pov_choice.get() == "First Person (I/We)":
            return set()
        raw = self._pov_names_var.get().strip()
        if not raw:
            return set()
        return {name.strip() for name in raw.split(",") if name.strip()}

    def _rerun_filter_for_pov_change(self) -> None:
        if not self.filter_active:
            return
        if self._filter_processing:
            self._mark_filter_needs_update()
            return
        self._filter_update_needed = False
        self._hide_filter_refresh_button()
        self._run_filter()

    def _on_pov_changed(self, _event=None) -> None:
        self._rerun_filter_for_pov_change()

    def show_pov_names_dialog(self) -> None:
        if self._pov_names_dialog and self._pov_names_dialog.winfo_exists():
            self._pov_names_dialog.deiconify()
            self._pov_names_dialog.lift()
            self._pov_names_dialog.focus_force()
            return

        dlg = tk.Toplevel(self.root)
        dlg.withdraw()
        dlg.title("POV Names")
        dlg.configure(bg=BG_SURFACE)
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        self._pov_names_dialog = dlg

        panel = tk.Frame(dlg, bg=BG_SURFACE, padx=12, pady=12)
        panel.pack(fill=tk.BOTH, expand=True)

        self._pov_names_edit_var.set(self._pov_names_var.get())

        tk.Label(
            panel,
            text="POV Character Names (comma-separated)",
            bg=BG_SURFACE,
            fg=TEXT,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill=tk.X)

        tk.Label(
            panel,
            text="Example: Nalls, Rauld, Detective",
            bg=BG_SURFACE,
            fg=TEXT_SUBTLE,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill=tk.X, pady=(2, 8))

        entry = tk.Entry(
            panel,
            textvariable=self._pov_names_edit_var,
            bg=BG,
            fg=TEXT,
            insertbackground=ACCENT,
            relief="flat",
            font=("Segoe UI", 9),
            width=42,
        )
        entry.pack(fill=tk.X)

        btn_row = tk.Frame(panel, bg=BG_SURFACE)
        btn_row.pack(fill=tk.X, pady=(10, 0))

        bkw = dict(
            bg=BG_OVERLAY,
            fg=TEXT,
            activebackground=ACCENT,
            activeforeground=BG,
            relief="flat",
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            font=("Segoe UI", 9),
        )

        tk.Button(btn_row, text="Cancel", command=self._cancel_pov_names_dialog, **bkw).pack(side=tk.RIGHT)
        tk.Button(btn_row, text="Save and Close", command=self._apply_and_close_pov_names_dialog, **bkw).pack(side=tk.RIGHT, padx=(0, 8))

        entry.bind("<Return>", lambda _e: self._apply_and_close_pov_names_dialog())
        dlg.bind("<Escape>", lambda _e: self._cancel_pov_names_dialog())
        dlg.protocol("WM_DELETE_WINDOW", self._apply_and_close_pov_names_dialog)
        self._center_popup(dlg)
        entry.focus_set()

    def _center_popup(self, dlg: tk.Toplevel) -> None:
        dlg.update_idletasks()
        w = dlg.winfo_reqwidth()
        h = dlg.winfo_reqheight()
        rx = self.root.winfo_rootx()
        ry = self.root.winfo_rooty()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        x = rx + max(0, (rw - w) // 2)
        y = ry + max(0, (rh - h) // 2)
        dlg.geometry(f"+{x}+{y}")
        dlg.deiconify()
        dlg.lift()

    def _apply_and_close_pov_names_dialog(self) -> None:
        new_value = self._pov_names_edit_var.get().strip()
        self._pov_names_var.set(new_value)
        self._save_user_settings()

        if self._pov_names_dialog and self._pov_names_dialog.winfo_exists():
            self._pov_names_dialog.grab_release()
            self._pov_names_dialog.destroy()
        self._pov_names_dialog = None

        # Apply POV name changes once on close, avoiding per-keystroke reruns.
        self._rerun_filter_for_pov_change()

    def _cancel_pov_names_dialog(self) -> None:
        if self._pov_names_dialog and self._pov_names_dialog.winfo_exists():
            self._pov_names_dialog.grab_release()
            self._pov_names_dialog.destroy()
        self._pov_names_dialog = None

    def _on_text_configure(self, _event=None) -> None:
        if self._resize_in_progress:
            return
        if self.filter_active or self._weak_mod_active or self._punct_active:
            self._request_density_redraw()

    def _on_root_configure(self, event) -> None:
        if event.widget is not self.root:
            return

        try:
            self._statusbar.config(height=self._statusbar_h)
            self._statusbar.pack_configure(side=tk.BOTTOM, fill=tk.X)
            self._statusbar.lift()
            self._grip_slot.config(width=self._statusbar_h, height=self._statusbar_h)
            self._sizegrip.place(relx=1.0, rely=1.0, relwidth=1.0, relheight=1.0, anchor="se")
        except Exception:
            pass

        self._resize_in_progress = True
        if self._resize_settle_job is not None:
            self.root.after_cancel(self._resize_settle_job)

        def _is_left_mouse_down() -> bool:
            # On Windows, non-client resize drags happen outside Tk widgets.
            # Querying the global button state avoids running heavy refresh work
            # while the user still holds the resize grip/corner.
            if os.name != "nt":
                return False
            try:
                return bool(ctypes.windll.user32.GetKeyState(0x01) & 0x8000)
            except Exception:
                return False

        def settle() -> None:
            if _is_left_mouse_down():
                self._resize_settle_job = self.root.after(120, settle)
                return
            self._resize_settle_job = None
            self._resize_in_progress = False
            if self.filter_active or self._weak_mod_active or self._punct_active:
                self._request_density_redraw()

        # Redraw bars/dots after resize settles, but avoid expensive cache rebuilds.
        self._resize_settle_job = self.root.after(280, settle)

    def _schedule_layout_refresh(self) -> None:
        if (not self.filter_active and not self._weak_mod_active and not self._punct_active) or self._is_editor_processing() or self._filter_update_needed:
            return
        if self._layout_refresh_job is not None:
            self.root.after_cancel(self._layout_refresh_job)

        def run() -> None:
            self._layout_refresh_job = None
            if (not self.filter_active and not self._weak_mod_active and not self._punct_active) or self._is_editor_processing():
                return
            self._request_density_redraw()

        self._layout_refresh_job = self.root.after(220, run)

    # ------------------------------------------------------- view / display

    def _zoom_in(self) -> None:
        self._editor_font.config(size=self._editor_font.cget("size") + 1)
        self._apply_first_line_indent()
        self.root.after(20, self._redraw_lineno)
        self._schedule_layout_refresh()

    def _zoom_out(self) -> None:
        s = self._editor_font.cget("size")
        if s > 7:
            self._editor_font.config(size=s - 1)
            self._apply_first_line_indent()
            self.root.after(20, self._redraw_lineno)
            self._schedule_layout_refresh()

    def _indent_pixels(self) -> int:
        # Approximate two visible spaces for the active editor font.
        return max(2, self._editor_font.measure("  "))

    def _apply_first_line_indent(self) -> None:
        if not hasattr(self, "text"):
            return
        if self._indent_first_line_var.get():
            px = self._indent_pixels()
            # First-line indent only: wrapped continuation lines stay unindented.
            self.text.tag_configure("first_line_indent", lmargin1=px, lmargin2=0)
            self.text.tag_add("first_line_indent", "1.0", "end")
        else:
            self.text.tag_remove("first_line_indent", "1.0", "end")

    def _toggle_first_line_indent(self) -> None:
        self._apply_first_line_indent()

    def _toggle_line_numbers(self) -> None:
        if self._show_lines_var.get():
            self._lineno.pack(side=tk.LEFT, fill=tk.Y, before=self.text)
            self._redraw_lineno()
        else:
            self._lineno.pack_forget()

    def _on_ctrl_mousewheel(self, event) -> str:
        if getattr(event, "delta", 0) > 0:
            self._zoom_in()
        elif getattr(event, "delta", 0) < 0:
            self._zoom_out()
        return "break"

    def _show_density_band(self) -> None:
        self._indicators.show_density_band()

    def _hide_density_band(self) -> None:
        self._indicators.hide_density_band()

    def _on_density_configure(self, _event=None) -> None:
        self._indicators.on_density_configure(_event)

    def _on_density_click(self, event) -> None:
        self._indicators.on_density_click(event)

    def _on_density_drag(self, event) -> None:
        self._indicators.on_density_drag(event)

    def _show_quote_band(self) -> None:
        self._indicators.show_quote_band()

    def _hide_quote_band(self) -> None:
        self._indicators.hide_quote_band()

    def _on_quote_band_click(self, event) -> None:
        self._indicators.on_quote_band_click(event)

    def _on_quote_band_drag(self, event) -> None:
        self._indicators.on_quote_band_drag(event)

    def _center_text_on_fraction(self, frac: float) -> None:
        self._indicators.center_text_on_fraction(frac)

    def _request_density_redraw(self) -> None:
        self._indicators.request_density_redraw()

    def _update_density_viewport(self) -> None:
        self._indicators.update_density_viewport()

    def _redraw_density_band_static(self) -> None:
        self._indicators.redraw_density_band_static()

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
        self.root.title(f"{APP_NAME} \u2014 {name}")

    def _update_status_legend(self) -> None:
        if not hasattr(self, "_legend_frame"):
            return

        for child in self._legend_frame.winfo_children():
            child.destroy()

        legend_map = {
            EDITOR_MODE_FILTER: [(RED_FG, "Filter Words")],
            EDITOR_MODE_WEAK: [(ORANGE_FG, "Weak / -ly")],
            EDITOR_MODE_PUNCT: [
                (PURPLE_BG, "Quote"),
                (BLUE_FG, "Dash"),
                (WHITE_FG, "Ellipsis"),
                (RED_FG, "Loud"),
            ],
        }

        items = legend_map.get(self._active_editor_mode, [])
        if not items:
            return

        tk.Label(
            self._legend_frame,
            text="Key:",
            bg="#11111b",
            fg=TEXT_SUBTLE,
            font=("Segoe UI", 9),
            padx=4,
        ).pack(side=tk.LEFT)

        for color, label in items:
            tk.Label(
                self._legend_frame,
                text=f"  {label}  ",
                bg=color,
                fg=BG if color != WHITE_FG else BG,
                font=("Segoe UI", 8, "bold"),
                padx=4,
                pady=1,
            ).pack(side=tk.LEFT, padx=(4, 0))

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

    def open_docs(self) -> None:
        self._open_url(WIKI_URL)

    def check_for_updates(self) -> None:
        dlg = tk.Toplevel(self.root)
        dlg.withdraw()
        dlg.title("Check for Updates")
        dlg.transient(self.root)
        dlg.resizable(False, False)
        dlg.configure(bg=BG_SURFACE)
        dlg.grab_set()

        panel = tk.Frame(dlg, bg=BG_SURFACE, padx=14, pady=12)
        panel.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            panel,
            text="Checking GitHub releases...",
            bg=BG_SURFACE,
            fg=TEXT,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")
        pb = ttk.Progressbar(panel, mode="indeterminate", length=300)
        pb.pack(fill=tk.X, pady=(10, 0))
        pb.start(14)
        self._center_popup(dlg)

        def finish(error: Exception | None, info: dict[str, object] | None) -> None:
            try:
                pb.stop()
                dlg.grab_release()
                dlg.destroy()
            except Exception:
                pass

            if error is not None:
                messagebox.showerror("Update Check", str(error))
                return
            if info is not None:
                self._show_update_dialog(info)

        def worker() -> None:
            try:
                info = self._fetch_latest_release_info()
                self.root.after(0, lambda: finish(None, info))
            except Exception as exc:
                self.root.after(0, lambda: finish(exc, None))

        threading.Thread(target=worker, daemon=True).start()

    def _fetch_latest_release_info(self) -> dict[str, object]:
        req = urlrequest.Request(
            LATEST_RELEASE_API,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"{APP_NAME}/{APP_VERSION}",
            },
        )
        try:
            with urlrequest.urlopen(req, timeout=12) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urlerror.URLError as exc:
            raise RuntimeError("Unable to contact GitHub. Check your internet connection and try again.") from exc

        if not isinstance(payload, dict):
            raise RuntimeError("Unexpected response from GitHub releases API.")

        assets: list[dict[str, object]] = []
        raw_assets = payload.get("assets", [])
        if isinstance(raw_assets, list):
            for item in raw_assets:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", ""))
                url = str(item.get("browser_download_url", ""))
                size = int(item.get("size", 0) or 0)
                if name and url:
                    assets.append({"name": name, "url": url, "size": size})

        return {
            "tag": str(payload.get("tag_name", "")).strip(),
            "title": str(payload.get("name", "")).strip(),
            "published": str(payload.get("published_at", "")).strip(),
            "url": str(payload.get("html_url", RELEASES_URL)).strip() or RELEASES_URL,
            "assets": assets,
        }

    def _show_update_dialog(self, info: dict[str, object]) -> None:
        latest_tag = str(info.get("tag", "")).strip()
        latest_version = latest_tag.lstrip("vV")
        has_update = self._is_newer_version(APP_VERSION, latest_version)

        dlg = tk.Toplevel(self.root)
        dlg.withdraw()
        dlg.title("Editorial Updates")
        dlg.transient(self.root)
        dlg.resizable(False, False)
        dlg.configure(bg=BG_SURFACE)
        dlg.grab_set()

        panel = tk.Frame(dlg, bg=BG_SURFACE, padx=14, pady=12)
        panel.pack(fill=tk.BOTH, expand=True)

        status_text = "Update available" if has_update else "You are up to date"
        status_color = GREEN_FG if has_update else ACCENT
        tk.Label(panel, text=status_text, bg=BG_SURFACE, fg=status_color, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(panel, text=f"Current version: {APP_VERSION}", bg=BG_SURFACE, fg=TEXT_SUBTLE, font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 0))
        tk.Label(panel, text=f"Latest release: {latest_tag or 'Unknown'}", bg=BG_SURFACE, fg=TEXT_SUBTLE, font=("Segoe UI", 9)).pack(anchor="w")

        title = str(info.get("title", "")).strip()
        published = str(info.get("published", "")).strip()
        if title:
            tk.Label(panel, text=f"Release: {title}", bg=BG_SURFACE, fg=TEXT_SUBTLE, font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))
        if published:
            tk.Label(panel, text=f"Published: {published[:10]}", bg=BG_SURFACE, fg=TEXT_SUBTLE, font=("Segoe UI", 9)).pack(anchor="w")

        tk.Label(panel, text="Available binaries:", bg=BG_SURFACE, fg=TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 4))

        assets_frame = tk.Frame(panel, bg=BG_SURFACE)
        assets_frame.pack(fill=tk.X)

        bkw = dict(
            bg=BG_OVERLAY,
            fg=TEXT,
            activebackground=ACCENT,
            activeforeground=BG,
            relief="flat",
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            font=("Segoe UI", 9),
        )

        assets = info.get("assets", [])
        if isinstance(assets, list) and assets:
            for item in assets:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", ""))
                url = str(item.get("url", ""))
                size = int(item.get("size", 0) or 0)
                if not name or not url:
                    continue

                row = tk.Frame(assets_frame, bg=BG_SURFACE)
                row.pack(fill=tk.X, pady=2)
                tk.Label(
                    row,
                    text=f"{name} ({self._format_bytes(size)})",
                    bg=BG_SURFACE,
                    fg=TEXT,
                    font=("Segoe UI", 9),
                    anchor="w",
                ).pack(side=tk.LEFT, fill=tk.X, expand=True)
                tk.Button(row, text="Open", command=lambda target=url: self._open_url(target), **bkw).pack(side=tk.RIGHT)
        else:
            tk.Label(assets_frame, text="No binaries were listed for the latest release.", bg=BG_SURFACE, fg=TEXT_SUBTLE, font=("Segoe UI", 9)).pack(anchor="w")

        actions = tk.Frame(panel, bg=BG_SURFACE)
        actions.pack(fill=tk.X, pady=(12, 0))
        release_url = str(info.get("url", RELEASES_URL)) or RELEASES_URL
        tk.Button(actions, text="Open Release Page", command=lambda: self._open_url(release_url), **bkw).pack(side=tk.LEFT)
        tk.Button(actions, text="Close", command=lambda: self._close_dialog(dlg), **bkw).pack(side=tk.RIGHT)
        self._center_popup(dlg)

    def _close_dialog(self, dlg: tk.Toplevel) -> None:
        try:
            dlg.grab_release()
            dlg.destroy()
        except Exception:
            pass

    def _open_url(self, url: str) -> None:
        try:
            webbrowser.open_new_tab(url)
        except Exception as exc:
            messagebox.showerror("Open Link", str(exc))

    def _format_bytes(self, size: int) -> str:
        value = float(max(0, size))
        units = ["B", "KB", "MB", "GB"]
        idx = 0
        while value >= 1024 and idx < len(units) - 1:
            value /= 1024.0
            idx += 1
        if idx == 0:
            return f"{int(value)} {units[idx]}"
        return f"{value:.1f} {units[idx]}"

    def _parse_version_tuple(self, version: str) -> tuple[int, ...]:
        parts = re.findall(r"\d+", version)
        if not parts:
            return ()
        return tuple(int(p) for p in parts[:3])

    def _is_newer_version(self, current: str, latest: str) -> bool:
        cur = self._parse_version_tuple(current)
        lat = self._parse_version_tuple(latest)
        if not cur or not lat:
            return False
        n = max(len(cur), len(lat))
        cur = cur + (0,) * (n - len(cur))
        lat = lat + (0,) * (n - len(lat))
        return lat > cur

    def _get_git_metadata(self) -> tuple[str | None, str | None]:
        repo_dir = os.path.dirname(os.path.abspath(__file__))
        if not os.path.isdir(os.path.join(repo_dir, ".git")):
            return None, None

        commit: str | None = None
        tag: str | None = None

        try:
            commit = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=repo_dir,
                stderr=subprocess.DEVNULL,
                timeout=2,
                text=True,
            ).strip()
        except Exception:
            commit = None

        try:
            tag = subprocess.check_output(
                ["git", "describe", "--tags", "--exact-match"],
                cwd=repo_dir,
                stderr=subprocess.DEVNULL,
                timeout=2,
                text=True,
            ).strip()
        except Exception:
            tag = None

        return commit or None, tag or None

    def show_about_dialog(self) -> None:
        commit, tag = self._get_git_metadata()
        git_lines = ""
        if commit:
            git_lines += f"\nGit commit: {commit}"
        if tag:
            git_lines += f"\nGit tag: {tag}"

        messagebox.showinfo(
            f"About {APP_NAME}",
            f"{APP_NAME} {APP_VERSION}\n"
            f"Created by {COMPANY_NAME}\n\n"
            f"Creator: {CREATOR_NAME}\n"
            f"Contact: {SUPPORT_EMAIL}{git_lines}",
        )

    # -------------------------------------------------------- event handlers

    def _on_key_release(self, _event=None) -> None:
        self._update_status()
        self._apply_first_line_indent()
        self._redraw_lineno()
        if self._skip_filter_schedule_once:
            self._skip_filter_schedule_once = False
            return
        if self._should_schedule_filter_for_key(_event):
            self._mark_active_mode_needs_update()

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
