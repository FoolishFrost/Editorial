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
import gzip
import json
import os
import sys
import threading
import time
import math
import re
import subprocess
import webbrowser
from urllib import error as urlerror
from urllib import request as urlrequest
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import font as tkfont
from tkinter import ttk

# Keep local module imports stable when launched from outside workspace root.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR and _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from editorial_indicators import IndicatorSubsystem
from editorial_modes import ModeSubsystem
from filter_analyzer import (
    analyze_dialogue_mechanics,
    analyze_dialogue_tags,
    analyze_emotion_words,
    analyze_filter_words,
    analyze_sentence_pacing,
    analyze_weak_modifiers,
)

from editorial_export import collect_export_ranges, build_tagged_export, build_rtf_export

from spellcheck_subsystem import SpellcheckSubsystem
from search_subsystem import SearchSubsystem
from ngram_subsystem import calculate_ngrams
import formatting_subsystem
from mode_echo_radar import analyze_echo_radar




from editorial_config import (
    APP_NAME,
    APP_VERSION,
    COMPANY_NAME,
    CREATOR_NAME,
    SUPPORT_EMAIL,
    GITHUB_REPO,
    WIKI_URL,
    RELEASES_URL,
    LATEST_RELEASE_API,
    BG,
    BG_SURFACE,
    BG_OVERLAY,
    TEXT,
    TEXT_SUBTLE,
    ACCENT,
    RED_FG,
    RED_BG,
    GREEN_FG,
    GREEN_BG,
    PURPLE_FG,
    PURPLE_BG,
    ORANGE_FG,
    ORANGE_BG,
    BLUE_FG,
    BLUE_BG,
    WHITE_FG,
    WHITE_BG,
    FIND_BG,
    PACING_SHORT_WORDS,
    PACING_AVERAGE_WORDS,
    PACING_LONG_WORDS,
    PACING_TAG_STYLES,
    PACING_EXPORT_LABELS,
    POV_PRONOUN_MAP,
    EDITOR_MODE_OFF,
    EDITOR_MODE_FILTER,
    EDITOR_MODE_WEAK,
    EDITOR_MODE_PUNCT,
    EDITOR_MODE_DTAG,
    EDITOR_MODE_EMOTION,
    EDITOR_MODE_ECHO,
    EDITOR_MODE_PACING,
    EDITOR_MODE_CLICHE,
    EDITOR_MODE_REDUNDANCY,
    EDITOR_MODE_PASSIVE,
    EDITOR_MODE_ARCH,
    EDITOR_MODES,
    ARCH_TAG_STYLES,
    ARCH_EXPORT_LABELS,
    ARCH_FRIENDLY_LABELS,
)



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
        self._dialogue_tag_update_needed: bool = False
        self._emotion_update_needed: bool = False
        self._echo_update_needed: bool = False
        self._pacing_update_needed: bool = False
        self._weak_mod_active: bool = False
        self._weak_mod_processing: bool = False
        self._weak_mod_run_seq: int = 0
        self._punct_active: bool = False
        self._punct_processing: bool = False
        self._punct_run_seq: int = 0
        self._dialogue_tag_active: bool = False
        self._mode_wrapper_processing: bool = False
        self._mode_wrapper_run_seq: int = 0
        self._emotion_active: bool = False
        self._echo_active: bool = False
        self._pacing_active: bool = False
        self._arch_active: bool = False
        self._arch_update_needed: bool = False
        self._arch_visible = {
            "arch_subject_first": True,
            "arch_participial_launch": True,
            "arch_contextual_lead": True,
            "arch_echoing_hinge": True,
            "arch_simultaneous_setup": True,
            "arch_fragment": True,
        }
        self._arch_counts: dict[str, int] = {}
        self._active_editor_mode: str = EDITOR_MODE_OFF
        self._editor_mode_var = tk.StringVar(value=EDITOR_MODE_OFF)
        self._editor_mode_label_var = tk.StringVar(value="Editor Off")
        self._arch_ignore_dialogue_var = tk.BooleanVar(value=False)
        self._mode_to_label = {value: label for label, value in EDITOR_MODES}
        self._label_to_mode = {label: value for label, value in EDITOR_MODES}
        self._weak_mod_hits: list[tuple[int, int]] = []
        self._weak_hit_fracs: list[float] = []
        self._emotion_hits: list[tuple[int, int]] = []
        self._emotion_hit_fracs: list[float] = []
        self._echo_hits: list[tuple[int, int]] = []
        self._echo_hit_fracs: list[float] = []
        self._echo_groups: dict[str, list[tuple[int, int, int]]] = {}
        self._echo_token_hits: list[tuple[str, int, int, int]] = []
        self._echo_token_starts: list[int] = []
        self._echo_focus_word: str = ""
        self._echo_focus_refresh_job: str | None = None
        self._echo_focus_window_words: int = 80
        self._echo_slider_var = tk.IntVar(value=80)
        self._pacing_long_words: int = 19
        self._pacing_short_words: int = 4
        self._pacing_average_words: int = 12
        self._pacing_slider_var = tk.IntVar(value=19)
        self._dialogue_tag_hits: list[tuple[int, int]] = []
        self._dialogue_tag_hit_fracs: list[float] = []
        self._typography_hits: list[tuple[int, int]] = []
        self._typography_hit_fracs: list[float] = []
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
        self._selected_ngram: str | None = None
        self._ngram_hit_fracs: list[float] = []
        self._ngram_matches: dict[str, list[tuple[int, int]]] = {}
        self._ngram_run_seq: int = 0
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
        self._pacing_lane_visible: bool = False
        self._pacing_heat_spans: list[tuple[float, float, float]] = []
        self._pacing_viewport_id: int | None = None
        self._arch_hits: list[tuple[int, int, str]] = []
        self._arch_hit_fracs: list[tuple[float, str]] = []
        self._search_subsystem = SearchSubsystem(self)
        self._pov_choice = tk.StringVar(value="All Pronouns (Broad Scan)")
        self._pov_names_var = tk.StringVar()
        self._pov_names_dialog: tk.Toplevel | None = None
        self._pov_names_edit_var = tk.StringVar()
        self._spellcheck_active: bool = True
        self._spellcheck_run_seq: int = 0
        self._spellcheck_job: str | None = None
        self._spellcheck_toggle_var = tk.BooleanVar(value=True)
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
        self._update_word_char_count()

    # ------------------------------------------------------------------ menu

    def _build_menu(self) -> None:
        cfg = dict(bg=BG_SURFACE, fg=TEXT,
                   activebackground=ACCENT, activeforeground=BG,
                   selectcolor=TEXT,
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
        self._export_menu = exm
        fm.add_separator()
        fm.add_command(label="Settings…", command=self.show_settings_dialog)
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

        # Punctuation --------------------------------------------------------
        pm = tk.Menu(bar, **cfg)
        pm.add_command(label="Convert to Smart Quotes", command=self._convert_to_smart_quotes)
        pm.add_command(label="Convert to Straight Quotes", command=self._convert_to_straight_quotes)
        pm.add_separator()
        pm.add_command(label="Convert Ellipses to Standard", command=self._convert_ellipses_spaced)
        pm.add_command(label="Convert Ellipses to Character", command=self._convert_ellipses_char)
        pm.add_separator()
        pm.add_command(label="Clean Whitespace", command=self._clean_whitespace)
        bar.add_cascade(label="Punctuation", menu=pm)

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
            label="Punctuation",
            variable=self._editor_mode_var,
            value=EDITOR_MODE_PUNCT,
            command=self._on_tools_mode_selected,
            accelerator="Ctrl+Shift+P",
        )
        self._tools_mode_entries.append((int(tm.index("end")), "Punctuation", EDITOR_MODE_PUNCT))
        tm.add_radiobutton(
            label="Dialogue Tags",
            variable=self._editor_mode_var,
            value=EDITOR_MODE_DTAG,
            command=self._on_tools_mode_selected,
            accelerator="Ctrl+Shift+D",
        )
        self._tools_mode_entries.append((int(tm.index("end")), "Dialogue Tags", EDITOR_MODE_DTAG))
        tm.add_radiobutton(
            label="Emotion Catcher",
            variable=self._editor_mode_var,
            value=EDITOR_MODE_EMOTION,
            command=self._on_tools_mode_selected,
            accelerator="Ctrl+Shift+E",
        )
        self._tools_mode_entries.append((int(tm.index("end")), "Emotion Catcher", EDITOR_MODE_EMOTION))
        tm.add_radiobutton(
            label="Proximity Echo Radar",
            variable=self._editor_mode_var,
            value=EDITOR_MODE_ECHO,
            command=self._on_tools_mode_selected,
            accelerator="Ctrl+Shift+R",
        )
        self._tools_mode_entries.append((int(tm.index("end")), "Proximity Echo Radar", EDITOR_MODE_ECHO))
        tm.add_radiobutton(
            label="Rhythm & Pacing",
            variable=self._editor_mode_var,
            value=EDITOR_MODE_PACING,
            command=self._on_tools_mode_selected,
            accelerator="Ctrl+Shift+M",
        )
        self._tools_mode_entries.append((int(tm.index("end")), "Rhythm & Pacing", EDITOR_MODE_PACING))
        tm.add_radiobutton(
            label="Cliches",
            variable=self._editor_mode_var,
            value=EDITOR_MODE_CLICHE,
            command=self._on_tools_mode_selected,
        )
        self._tools_mode_entries.append((int(tm.index("end")), "Cliches", EDITOR_MODE_CLICHE))
        tm.add_radiobutton(
            label="Redundancies",
            variable=self._editor_mode_var,
            value=EDITOR_MODE_REDUNDANCY,
            command=self._on_tools_mode_selected,
        )
        self._tools_mode_entries.append((int(tm.index("end")), "Redundancies", EDITOR_MODE_REDUNDANCY))
        tm.add_radiobutton(
            label="Passive Voice",
            variable=self._editor_mode_var,
            value=EDITOR_MODE_PASSIVE,
            command=self._on_tools_mode_selected,
        )
        self._tools_mode_entries.append((int(tm.index("end")), "Passive Voice", EDITOR_MODE_PASSIVE))
        tm.add_radiobutton(
            label="Sentence Architecture",
            variable=self._editor_mode_var,
            value=EDITOR_MODE_ARCH,
            command=self._on_tools_mode_selected,
        )
        self._tools_mode_entries.append((int(tm.index("end")), "Sentence Architecture", EDITOR_MODE_ARCH))
        tm.add_separator()
        tm.add_checkbutton(
            label="Spelling Checker",
            variable=self._spellcheck_toggle_var,
            command=self._toggle_spellcheck,
        )
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
        ref_menu = tk.Menu(hm, **cfg)
        ref_menu.add_command(label="File Menu Reference", command=lambda: self.open_local_help("file-menu"))
        ref_menu.add_command(label="Edit Menu Reference", command=lambda: self.open_local_help("edit-menu"))
        ref_menu.add_command(label="View Menu Reference", command=lambda: self.open_local_help("view-menu"))
        ref_menu.add_command(label="Punctuation Menu Reference", command=lambda: self.open_local_help("punctuation-menu"))
        ref_menu.add_command(label="Tools Menu Reference", command=lambda: self.open_local_help("tools-menu"))
        ref_menu.add_command(label="Help Menu Reference", command=lambda: self.open_local_help("help-menu"))
        hm.add_cascade(label="Menu Reference", menu=ref_menu)
        hm.add_command(label="Check for Updates", command=self.check_for_updates)
        hm.add_separator()
        hm.add_command(label="About Editorial", command=self.show_about_dialog)
        bar.add_cascade(label="Help", menu=hm)

        self._menus: list[tk.Menu] = [fm, em, vm, pm, tm, hm]
        self._tools_menu = tm

        self.root.config(menu=bar)

        local_dict_path = "dictionary.json"
        exe_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else None

        if exe_dir:
            possible_path = os.path.join(exe_dir, local_dict_path)
            if not os.path.exists(possible_path):
                try:
                    payload = pkgutil.get_data("spellchecker", "resources/en.json.gz")
                    if payload:
                        local_dict_path = _write_spellchecker_dictionary_file(payload, possible_path)
                except Exception:
                    local_dict_path = "dictionary.json"

        self._custom_dict_path = os.path.join(os.path.dirname(self._settings_path), "custom_dictionary.json")
        self._spellcheck_subsystem = SpellcheckSubsystem(
            custom_dict_path=self._custom_dict_path,
            local_dict_path=local_dict_path
        )

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
        self._mode_combo.pack(side=tk.LEFT, padx=(0, 4))
        self._mode_combo.bind("<<ComboboxSelected>>", self._on_mode_combo_selected)

        self._mode_help_btn = tk.Button(
            self._toolbar,
            text="ⓘ",
            command=self._on_context_help_clicked,
            bg=BG_SURFACE,
            fg=ACCENT,
            activebackground=BG_SURFACE,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            padx=2,
            pady=2,
            cursor="hand2",
            font=("Segoe UI", 11, "bold"),
        )
        self._mode_help_btn.pack(side=tk.LEFT, padx=(0, 8))
        ToolTip(self._mode_help_btn, "Open manual for the active mode")

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

        self._echo_slider_label = tk.Label(
            self._toolbar,
            text=f"Echo Range: {self._echo_focus_window_words}",
            bg=BG_SURFACE,
            fg=TEXT_SUBTLE,
            font=("Segoe UI", 9),
        )

        self._echo_slider = ttk.Scale(
            self._toolbar,
            from_=1,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self._echo_slider_var,
            length=120,
            command=self._on_echo_range_changed,
            style="Horizontal.TScale",
        )

        self._pacing_slider_label = tk.Label(
            self._toolbar,
            text=f"Pacing Limit: {self._pacing_long_words}",
            bg=BG_SURFACE,
            fg=TEXT_SUBTLE,
            font=("Segoe UI", 9),
        )

        self._pacing_slider = ttk.Scale(
            self._toolbar,
            from_=5,
            to=50,
            orient=tk.HORIZONTAL,
            variable=self._pacing_slider_var,
            length=120,
            command=self._on_pacing_limit_changed,
            style="Horizontal.TScale",
        )

        self._arch_ignore_dialogue_check = tk.Checkbutton(
            self._toolbar,
            text="Ignore Dialogue",
            variable=self._arch_ignore_dialogue_var,
            command=self._on_arch_ignore_dialogue_changed,
            bg=BG_SURFACE,
            fg=TEXT,
            selectcolor=BG_SURFACE,
            activebackground=BG_SURFACE,
            activeforeground=TEXT,
            font=("Segoe UI", 9),
            bd=0,
            highlightthickness=0,
        )

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
        header_frame = tk.Frame(self._analysis_panel, bg=BG_SURFACE)
        header_frame.pack(fill=tk.X)

        self._analysis_title = tk.Label(
            header_frame,
            text="Overused Combinations",
            bg=BG_SURFACE,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            padx=10,
            pady=8,
        )
        self._analysis_title.pack(side=tk.LEFT)

        self._ngram_help_btn = tk.Button(
            header_frame,
            text="ⓘ",
            command=lambda: self.open_local_help("n-gram-scan"),
            bg=BG_SURFACE,
            fg=ACCENT,
            activebackground=BG_SURFACE,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            padx=4,
            pady=4,
            cursor="hand2",
            font=("Segoe UI", 11, "bold"),
        )
        self._ngram_help_btn.pack(side=tk.LEFT, padx=2)
        ToolTip(self._ngram_help_btn, "Open manual for N-gram Scan")
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
            "Horizontal.TScale",
            troughcolor=BG_OVERLAY,
            background=BG_SURFACE,
            sliderthickness=12,
            borderwidth=0,
        )
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

        self._single_tree.bind("<<TreeviewSelect>>", self._on_ngram_select)
        self._pairs_tree.bind("<<TreeviewSelect>>", self._on_ngram_select)
        self._triples_tree.bind("<<TreeviewSelect>>", self._on_ngram_select)
        self._analysis_visible = False

        # Density mini-map canvas (red filter hits)
        self._density = tk.Canvas(
            container, bg=BG_SURFACE, width=30, highlightthickness=0,
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

        # Rhythm pacing lane (sentence heat map)
        self._pacing_lane = tk.Canvas(
            container, bg=BG_SURFACE, width=30, highlightthickness=0,
            cursor="hand2",
        )
        self._pacing_lane.bind("<Button-1>", self._on_pacing_lane_click)
        self._pacing_lane.bind("<B1-Motion>", self._on_pacing_lane_click)
        self._pacing_lane.bind("<Configure>", lambda _e: self._redraw_pacing_lane())

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
        self.text.tag_configure(
            "cliche_hit",
            background="#004d40", # Dark cyan/teal bg
            foreground="#80cbc4", # Cyan/teal fg
        )
        self.text.tag_configure(
            "redundancy_hit",
            background="#4d4d00", # Dark yellow bg
            foreground="#ffee58", # Yellow fg
        )
        self.text.tag_configure(
            "passive_voice_hit",
            background="#4a0024", # Dark magenta/pink bg
            foreground="#f06292", # Magenta/pink fg
        )
        self.text.tag_configure(
            "echo_hit",
            background="#3b4f6f",
            foreground="#eef6ff",
            underline=0,
        )
        self.text.tag_configure(
            "echo_focus",
            background="#35567f",
            foreground="#e6f3ff",
            underline=1,
        )
        self.text.tag_configure(
            "echo_focus_cursor",
            background="#4d79ad",
            foreground="#ffffff",
            underline=1,
        )
        self.text.tag_configure(
            "misspelled",
            underline=1,
            foreground=RED_FG,
        )
        self.text.tag_configure(
            "dialogue_tag",
            background=ORANGE_BG,
            foreground=ORANGE_FG,
            underline=1,
        )
        self.text.tag_configure(
            "emotion_hit",
            background=RED_BG,
            foreground=RED_FG,
        )
        self.text.tag_configure(
            "typography_hit",
            background=BLUE_BG,
            foreground=BLUE_FG,
            underline=1,
        )
        for tag_name, fg, bg in PACING_TAG_STYLES:
            self.text.tag_configure(
                tag_name,
                background=bg,
                foreground=fg,
            )
        for tag_tuple in ARCH_TAG_STYLES:
            tag_name, bg, fg = tag_tuple[:3]
            self.text.tag_configure(
                tag_name,
                background=bg,
                foreground=fg,
            )
            if len(tag_tuple) > 3 and tag_tuple[3]:
                self.text.tag_configure(
                    tag_name,
                    relief="solid",
                    borderwidth=1,
                )
        self.text.tag_configure("find_match",
                    background=FIND_BG, foreground=TEXT)
        self.text.tag_configure("ngram_hit",
                    background="#3e445e", foreground="#89b4fa", underline=1)
        self.text.tag_configure("first_line_indent", lmargin1=0, lmargin2=0)
        self._apply_first_line_indent()

        # Event bindings
        self.text.bind("<KeyRelease>",    self._on_key_release)
        self.text.bind("<ButtonRelease>", self._on_cursor_move)
        self.text.bind("<Configure>", self._on_text_configure)
        self.text.bind("<<Copy>>", self._on_copy_event)
        self.text.bind("<Control-MouseWheel>", self._on_ctrl_mousewheel)

        # Context menu bindings
        if self.root.tk.call("tk", "windowingsystem") == "aqua":
            self.text.bind("<Button-2>", self._show_context_menu)
            self.text.bind("<Control-Button-1>", self._show_context_menu)
        else:
            self.text.bind("<Button-3>", self._show_context_menu)

        # Defer first line-number draw until widget is fully rendered
        self.root.after(120, self._redraw_lineno)

        # Initial spellcheck
        self._schedule_spellcheck()

    def _toggle_spellcheck(self) -> None:
        self._spellcheck_active = bool(self._spellcheck_toggle_var.get())
        self.text.tag_remove("misspelled", "1.0", tk.END)
        if self._spellcheck_active:
            self._schedule_spellcheck()
        else:
            if self._spellcheck_job is not None:
                self.root.after_cancel(self._spellcheck_job)
                self._spellcheck_job = None

    def _schedule_spellcheck(self) -> None:
        if not self._spellcheck_active:
            return
        if self._spellcheck_job is not None:
            self.root.after_cancel(self._spellcheck_job)
        self._spellcheck_job = self.root.after(1000, self._run_spellchecker)

    def _run_spellchecker(self) -> None:
        self._spellcheck_job = None
        if not self._spellcheck_active:
            return

        self._spellcheck_run_seq += 1
        run_id = self._spellcheck_run_seq
        content = self.text.get("1.0", "end-1c")

        def analyze_worker() -> None:
            try:
                misspelled = self._spellcheck_subsystem.check_spelling(content)
                self.root.after(0, lambda: apply_worker(misspelled))
            except Exception:
                self.root.after(0, lambda: apply_worker([]))

        def apply_worker(ranges: list[tuple[int, int]]) -> None:
            if run_id != self._spellcheck_run_seq:
                return

            self.text.tag_remove("misspelled", "1.0", tk.END)

            if not ranges:
                return

            # Apply tags in chunks
            total = len(ranges)
            idx = 0
            step = 600

            def run_chunk() -> None:
                nonlocal idx
                if run_id != self._spellcheck_run_seq:
                    return
                end = min(total, idx + step)
                flat_args = []
                for ws, we in ranges[idx:end]:
                    if we > ws:
                        flat_args.append(f"1.0 + {ws}c")
                        flat_args.append(f"1.0 + {we}c")
                if flat_args:
                    self.text.tk.call(self.text._w, "tag", "add", "misspelled", *flat_args)
                idx = end
                if idx < total:
                    self.root.after(1, run_chunk)

            run_chunk()

        threading.Thread(target=analyze_worker, daemon=True).start()

    def _show_context_menu(self, event) -> None:
        try:
            index = self.text.index(f"@{event.x},{event.y}")
            tags = self.text.tag_names(index)
        except tk.TclError:
            return

        if "misspelled" not in tags:
            return

        # Get the word span
        # Use tag ranges to accurately capture the word including apostrophes
        prev_range = self.text.tag_prevrange("misspelled", f"{index} wordend")
        if not prev_range:
            return

        word_start, word_end = prev_range
        # Double check the click is within the tag bounds
        if self.text.compare(index, "<", word_start) or self.text.compare(index, ">=", word_end):
            return

        word = self.text.get(word_start, word_end)

        # If it's empty or doesn't match our regex, maybe it's punctuation.
        if not re.match(r"^[A-Za-z]+(?:'[A-Za-z]+)?$", word):
            return

        menu = tk.Menu(self.root, tearoff=0, bg=BG_SURFACE, fg=TEXT, activebackground=ACCENT, activeforeground=BG)

        # Get suggestions
        suggestions = self._spellcheck_subsystem.get_candidates(word)
        if suggestions:
            # pyspellchecker returns None if no suggestions, or a set
            for i, suggestion in enumerate(sorted(list(suggestions))[:5]):
                # Match capitalization
                if word.istitle():
                    suggestion = suggestion.title()
                elif word.isupper():
                    suggestion = suggestion.upper()

                menu.add_command(
                    label=suggestion,
                    command=lambda s=suggestion: self._apply_suggestion(word_start, word_end, s)
                )
            menu.add_separator()
        else:
            menu.add_command(label="(No spelling suggestions)", state="disabled")
            menu.add_separator()

        menu.add_command(
            label="Add to dictionary",
            command=lambda w=word: self._add_to_dictionary(w)
        )
        menu.add_command(
            label="Ignore",
            command=lambda w=word: self._ignore_word(w)
        )

        menu.tk_popup(event.x_root, event.y_root)

    def _add_to_dictionary(self, word: str) -> None:
        self._spellcheck_subsystem.add_to_dictionary(word)
        self._run_spellchecker()

    def _ignore_word(self, word: str) -> None:
        self._spellcheck_subsystem.ignore_word(word)
        self._run_spellchecker()

    def _apply_suggestion(self, start: str, end: str, new_text: str) -> None:
        try:
            self.text.delete(start, end)
            self.text.insert(start, new_text)
            self._mark_active_mode_needs_update()
            self._update_status()
            self._update_word_char_count()
            self._apply_first_line_indent()
            self._schedule_spellcheck()
        except tk.TclError:
            pass

    def _show_analysis_panel(self) -> None:
        if self._analysis_visible:
            return
        self._analysis_panel.pack(side=tk.RIGHT, fill=tk.Y, before=self._scrollbar)
        self._analysis_visible = True

    def _hide_analysis_panel(self) -> None:
        if not self._analysis_visible:
            return
        self._select_ngram(None)
        self._analysis_panel.pack_forget()
        self._analysis_visible = False

    def _populate_ngram_table(self, table: ttk.Treeview, items: list[tuple[str, int]]) -> None:
        table.delete(*table.get_children())
        if not items:
            table.insert("", tk.END, values=("(none)", "-"))
            return
        for gram, count in items:
            table.insert("", tk.END, values=(gram, str(count)))

    def _on_ngram_select(self, event) -> None:
        # Update UI visually immediately before doing any heavy operations
        self.root.update_idletasks()

        tree = event.widget
        sel = tree.selection()
        if not sel:
            return

        # Clear selection on other trees
        for other_tree in (self._single_tree, self._pairs_tree, self._triples_tree):
            if other_tree is not tree:
                try:
                    if other_tree.selection():
                        other_tree.selection_set(())
                except tk.TclError:
                    pass

        # Get selected phrase
        item_id = sel[0]
        values = tree.item(item_id, "values")
        if values:
            gram = values[0]
            if gram == "(none)":
                self._select_ngram(None)
            else:
                self._select_ngram(gram)
        else:
            self._select_ngram(None)

    def _select_ngram(self, phrase: str | None) -> None:
        self._ngram_run_seq += 1
        run_id = self._ngram_run_seq

        self.text.tag_remove("ngram_hit", "1.0", "end")
        self._selected_ngram = phrase
        self._ngram_hit_fracs = []

        if not phrase:
            self._ngram_matches = {}
            # Clear selection in all treeviews to sync UI
            for tree in (self._single_tree, self._pairs_tree, self._triples_tree):
                try:
                    if tree.selection():
                        tree.selection_set(())
                except tk.TclError:
                    pass
            self._set_editor_progress(None, "")
            if not self._mode_uses_density_band():
                self._hide_density_band()
            else:
                self._request_density_redraw()
            return

        # Ensure active editor mode is OFF to prevent interference
        if self._active_editor_mode != EDITOR_MODE_OFF:
            self.set_editor_mode(EDITOR_MODE_OFF)

        self._selected_ngram = phrase

        # Retrieve precomputed match ranges
        ranges = self._ngram_matches.get(phrase, [])
        if not ranges:
            self._show_density_band()
            self._request_density_redraw()
            return

        # Compute midpoint fractions instantly using character offsets (avoiding heavy Tkinter displayline counting)
        self._ngram_hit_fracs = self._compute_midpoint_fracs(ranges)
        self._show_density_band()
        self._request_density_redraw()

        # Perform progressive/asynchronous tagging to keep UI responsive
        total = len(ranges)
        idx = 0
        step = 100

        import time

        def run_chunk() -> None:
            nonlocal idx, step
            if run_id != self._ngram_run_seq:
                # Cancel if another scan/selection was triggered
                return

            t0 = time.perf_counter()
            end = min(total, idx + step)
            flat_args: list[str] = []
            for ws, we in ranges[idx:end]:
                if we <= ws:
                    continue
                flat_args.append(f"1.0 + {ws}c")
                flat_args.append(f"1.0 + {we}c")
            if flat_args:
                self.text.tk.call(self.text._w, "tag", "add", "ngram_hit", *flat_args)
            idx = end

            elapsed_ms = (time.perf_counter() - t0) * 1000
            if elapsed_ms > 0.5:
                # Scale step based on execution speed, keeping layout rendering responsive
                step = max(20, min(1000, int(step * 8.0 / elapsed_ms)))

            pct = int((idx / total) * 100)
            self._set_editor_progress(pct, f"Highlighting '{phrase}'")

            if idx < total:
                self.root.after(1, run_chunk)
            else:
                # Finished progressive tagging
                self._set_editor_progress(None, "")

        run_chunk()

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
        root.bind("<Control-Shift-D>", lambda _e: self._toggle_editor_mode_shortcut(EDITOR_MODE_DTAG))
        root.bind("<Control-Shift-E>", lambda _e: self._toggle_editor_mode_shortcut(EDITOR_MODE_EMOTION))
        root.bind("<Control-Shift-R>", lambda _e: self._toggle_editor_mode_shortcut(EDITOR_MODE_ECHO))
        root.bind("<Control-Shift-M>", lambda _e: self._toggle_editor_mode_shortcut(EDITOR_MODE_PACING))
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
        self._update_pacing_viewport()

    def _on_text_scroll(self, first: str, last: str) -> None:
        """Called when the text widget scrolls for any reason."""
        self._scrollbar.set(first, last)
        self._redraw_lineno()
        self._update_density_viewport()
        self._update_pacing_viewport()

    # -------------------------------------------------------------- file I/O

    def new_file(self) -> None:
        if not self._confirm_discard():
            return
        self.text.delete("1.0", tk.END)
        self._clear_pacing_highlights()
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
        self._clear_pacing_highlights()
        self._apply_first_line_indent()
        self.text.edit_reset()
        self.current_file = path
        self._set_title(os.path.basename(path))
        self._update_status()
        self._update_word_char_count()
        self._redraw_lineno()
        if self._weak_mod_active:
            self.refresh_weak_modifiers()
        if self.filter_active:
            self._clear_filter()
            self._mark_filter_needs_update()
        if self._punct_active:
            self._clear_dialogue_mechanics()
            self._mark_punct_needs_update()
        if self._emotion_active:
            self._clear_emotion_highlights()
            self._mark_emotion_needs_update()
        if self._echo_active:
            self._clear_echo_highlights()
            self._mark_echo_needs_update()
        if self._pacing_active:
            self._clear_pacing_highlights()
            self._mark_pacing_needs_update()
        if self._dialogue_tag_active:
            self._clear_dialogue_tag_highlights()
            self._mark_dialogue_tags_needs_update()

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
        pass

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
        return (
            self._filter_processing
            or self._weak_mod_processing
            or self._punct_processing
            or self._mode_wrapper_processing
        )

    def _mode_uses_density_band(self) -> bool:
        return (
            self.filter_active
            or self._weak_mod_active
            or self._dialogue_tag_active
            or self._emotion_active
            or self._echo_active
            or getattr(self, "_cliche_active", False)
            or getattr(self, "_redundancy_active", False)
            or getattr(self, "_passive_voice_active", False)
            or getattr(self, "_arch_active", False)
            or (self._analysis_visible and getattr(self, "_selected_ngram", None) is not None)
        )

    def _mode_uses_quote_band(self) -> bool:
        return self.filter_active or self._punct_active

    def _sync_editor_mode_ui(self) -> None:
        mode = self._active_editor_mode or EDITOR_MODE_OFF
        self._editor_mode_var.set(mode)
        self._editor_mode_label_var.set(self._mode_to_label.get(mode, "Editor Off"))
        self._update_status_legend()
        self._refresh_tools_mode_markers()
        self._apply_first_line_indent()

        if self._tools_menu is not None and self._tools_refresh_index is not None:
            refresh_state = "disabled" if mode == EDITOR_MODE_OFF else "normal"
            try:
                self._tools_menu.entryconfig(self._tools_refresh_index, state=refresh_state)
            except Exception:
                pass

        if hasattr(self, "_export_menu"):
            try:
                if mode == EDITOR_MODE_OFF:
                    self._export_menu.entryconfig(0, state="disabled")
                    self._export_menu.entryconfig(1, state="disabled")
                elif mode == EDITOR_MODE_PACING:
                    self._export_menu.entryconfig(0, state="normal")
                    self._export_menu.entryconfig(1, state="disabled")
                else:
                    self._export_menu.entryconfig(0, state="normal")
                    self._export_menu.entryconfig(1, state="normal")
            except Exception:
                pass

        if mode == EDITOR_MODE_FILTER:
            if not self._pov_label.winfo_manager():
                self._pov_label.pack(side=tk.LEFT, padx=(8, 6), after=self._mode_combo)
            if not self._pov_combo.winfo_manager():
                self._pov_combo.pack(side=tk.LEFT, padx=(0, 6), after=self._pov_label)
        else:
            if self._pov_combo.winfo_manager():
                self._pov_combo.pack_forget()
            if self._pov_label.winfo_manager():
                self._pov_label.pack_forget()

        if mode == EDITOR_MODE_ECHO:
            if not self._echo_slider_label.winfo_manager():
                self._echo_slider_label.pack(side=tk.LEFT, padx=(8, 6), after=self._mode_combo)
            if not self._echo_slider.winfo_manager():
                self._echo_slider.pack(side=tk.LEFT, padx=(0, 6), after=self._echo_slider_label)
        else:
            if self._echo_slider.winfo_manager():
                self._echo_slider.pack_forget()
            if self._echo_slider_label.winfo_manager():
                self._echo_slider_label.pack_forget()

        if mode == EDITOR_MODE_PACING:
            if not self._pacing_slider_label.winfo_manager():
                self._pacing_slider_label.pack(side=tk.LEFT, padx=(8, 6), after=self._mode_combo)
            if not self._pacing_slider.winfo_manager():
                self._pacing_slider.pack(side=tk.LEFT, padx=(0, 6), after=self._pacing_slider_label)
        else:
            if self._pacing_slider.winfo_manager():
                self._pacing_slider.pack_forget()
            if self._pacing_slider_label.winfo_manager():
                self._pacing_slider_label.pack_forget()

        if mode == EDITOR_MODE_ARCH:
            if not self._arch_ignore_dialogue_check.winfo_manager():
                self._arch_ignore_dialogue_check.pack(side=tk.LEFT, padx=(8, 6), after=self._mode_combo)
        else:
            if self._arch_ignore_dialogue_check.winfo_manager():
                self._arch_ignore_dialogue_check.pack_forget()

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
        self._dialogue_tag_update_needed = False
        self._emotion_update_needed = False
        self._echo_update_needed = False
        self._pacing_update_needed = False
        self._cliche_update_needed = False
        self._redundancy_update_needed = False
        self._passive_voice_update_needed = False
        self._arch_update_needed = False
        self._hide_filter_refresh_button()

        self.filter_active = False
        self._weak_mod_active = False
        self._punct_active = False
        self._dialogue_tag_active = False
        self._emotion_active = False
        self._echo_active = False
        self._pacing_active = False
        self._cliche_active = False
        self._redundancy_active = False
        self._passive_voice_active = False
        self._arch_active = False

        self._clear_filter()
        self._clear_weak_modifiers()
        self._clear_dialogue_mechanics()
        self._clear_dialogue_tag_highlights()
        self._clear_emotion_highlights()
        self._clear_echo_highlights()
        self._clear_pacing_highlights()
        self._clear_cliche_highlights()
        self._clear_redundancy_highlights()
        self._clear_passive_voice_highlights()
        self._clear_arch_highlights()
        self._hide_quote_band()
        if mode != EDITOR_MODE_OFF:
            self.text.tag_remove("ngram_hit", "1.0", "end")
            self._selected_ngram = None
            self._ngram_hit_fracs = []
            self._ngram_matches = {}
            for tree in (self._single_tree, self._pairs_tree, self._triples_tree):
                try:
                    if tree.selection():
                        tree.selection_set(())
                except tk.TclError:
                    pass
        self._hide_density_band()

        if mode == EDITOR_MODE_OFF:
            self._set_editor_progress(None, "")
            self._lbl_filter.config(text="")
            return

        if mode == EDITOR_MODE_FILTER:
            self.filter_active = True
            self._show_density_band()
            self._run_filter()
            return

        if mode == EDITOR_MODE_WEAK:
            self._show_density_band()
            self._weak_mod_active = True
            self._run_weak_modifiers()
            return

        if mode == EDITOR_MODE_PUNCT:
            self._show_quote_band()
            self._punct_active = True
            self._run_dialogue_mechanics()
            return

        if mode == EDITOR_MODE_DTAG:
            self._show_density_band()
            self._dialogue_tag_active = True
            self._run_dialogue_tags_mode()
            return

        if mode == EDITOR_MODE_EMOTION:
            self._show_density_band()
            self._emotion_active = True
            self._run_emotion_catcher_mode()
            return

        if mode == EDITOR_MODE_ECHO:
            self._show_density_band()
            self._echo_active = True
            self._run_echo_radar_mode()
            return

        if mode == EDITOR_MODE_PACING:
            self._pacing_active = True
            self._run_pacing_scan_mode()
            return

        if mode == EDITOR_MODE_CLICHE:
            self._show_density_band()
            self._cliche_active = True
            self._run_cliche_mode()
            return

        if mode == EDITOR_MODE_REDUNDANCY:
            self._show_density_band()
            self._redundancy_active = True
            self._run_redundancy_mode()
            return

        if mode == EDITOR_MODE_PASSIVE:
            self._show_density_band()
            self._passive_voice_active = True
            self._run_passive_voice_mode()
            return

        if mode == EDITOR_MODE_ARCH:
            self._show_density_band()
            self._arch_active = True
            self._run_arch_mode()
            return

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
            ranges = collect_export_ranges(self, mode, text, active_pov, pov_names)
            rtf = build_rtf_export(text, ranges)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(rtf)

        self._run_task_with_progress("Exporting RTF...", task, "RTF export complete.")

    def _mark_arch_needs_update(self) -> None:
        if not getattr(self, "_arch_active", False):
            return
        self._arch_update_needed = True
        self._show_filter_refresh_button()
        self._lbl_filter.config(text="Sentence Architecture - changes pending (click Refresh)")

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
            ranges = collect_export_ranges(self, mode, text, active_pov, pov_names)
            label_map: dict[str, str] | None = None
            if mode == EDITOR_MODE_PUNCT:
                label_map = {"quote": "QUOTE", "dash": "DASH", "ellipsis": "ELLIPSIS", "loud": "LOUD"}
            elif mode == EDITOR_MODE_DTAG:
                label_map = {"dialogue_tag": "DTAG"}
            elif mode == EDITOR_MODE_EMOTION:
                label_map = {"emotion": "EMOTION"}
            elif mode == EDITOR_MODE_ECHO:
                label_map = {"echo": "ECHO"}
            elif mode == EDITOR_MODE_PACING:
                label_map = dict(PACING_EXPORT_LABELS)
            elif mode == EDITOR_MODE_CLICHE:
                label_map = {"cliche_hit": "CLICHE"}
            elif mode == EDITOR_MODE_REDUNDANCY:
                label_map = {"redundancy_hit": "REDUNDANCY"}
            elif mode == EDITOR_MODE_PASSIVE:
                label_map = {"passive_voice_hit": "PASSIVE_VOICE"}
            elif mode == EDITOR_MODE_ARCH:
                label_map = dict(ARCH_EXPORT_LABELS)
            tagged = build_tagged_export(text, ranges, label_map)
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

        self._select_ngram(None)
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

        def set_progress(val: int) -> None:
            p = max(0, min(100, int(val)))
            pb["value"] = p
            pct_var.set(f"{p}%")

        def render_results(result: dict[str, list[tuple[str, int]]]) -> None:
            self._populate_ngram_table(self._single_tree, result["single"])
            self._populate_ngram_table(self._pairs_tree, result["pairs"])
            self._populate_ngram_table(self._triples_tree, result["triples"])
            self._show_analysis_panel()

        def finish(error: Exception | None, result: dict[str, Any] | None) -> None:
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
                self._ngram_matches = result.get("matches", {})
                render_results(result)

        def worker() -> None:
            try:
                result = calculate_ngrams(text, lambda p: self.root.after(0, lambda: set_progress(p)))
                self.root.after(0, lambda: finish(None, result))
            except Exception as exc:
                self.root.after(0, lambda: finish(exc, None))

        threading.Thread(target=worker, daemon=True).start()

    def _text_char_length(self) -> int:
        try:
            return int(self.text.count("1.0", "end-1c", "chars")[0])
        except Exception:
            return len(self.text.get("1.0", "end-1c"))

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

    def standardize_typography(self) -> None:
        messagebox.showinfo("Typography", "Typography mode is disabled for now.")

    def _standardize_typography_text(self, text: str) -> tuple[str, int]:
        working = text
        total_changes = 0

        # Normalize common draft dash patterns to an unspaced em dash.
        working, n = re.subn(r"--+", "\u2014", working)
        total_changes += n
        working, n = re.subn(r"\s+[\u2014-]\s+", "\u2014", working)
        total_changes += n

        # Normalize sloppy ellipses to the single ellipsis character.
        working, n = re.subn(r"(?<!\.)\.\.\.(?!\.)", "\u2026", working)
        total_changes += n
        working, n = re.subn(r"(?<!\.)\.{2}(?!\.)|(?<!\.)\.{4,}", "\u2026", working)
        total_changes += n

        smart = self._smarten_straight_quotes(working)
        if smart != working:
            total_changes += 1
        return smart, total_changes

    def _get_text_range(self) -> tuple[str, str, str]:
        """Returns (start_index, end_index, selected_text) based on selection or whole document."""
        try:
            sel_start = self.text.index(tk.SEL_FIRST)
            sel_end = self.text.index(tk.SEL_LAST)
            return sel_start, sel_end, self.text.get(sel_start, sel_end)
        except tk.TclError:
            # No selection, use entire document
            return "1.0", "end-1c", self.text.get("1.0", "end-1c")

    def _replace_text_range(self, start: str, end: str, new_text: str) -> None:
        """Replaces text in the given range and selects the new text if it was originally selected."""
        try:
            had_sel = bool(self.text.tag_ranges(tk.SEL))
        except tk.TclError:
            had_sel = False

        # Save cursor position and vertical scroll state
        cursor_pos = self.text.index(tk.INSERT)
        y_scroll = self.text.yview()[0]

        self.text.delete(start, end)
        self.text.insert(start, new_text)

        if had_sel:
            new_end = f"{start}+{len(new_text)}c"
            self.text.tag_add(tk.SEL, start, new_end)
            self.text.mark_set(tk.INSERT, new_end)
        else:
            self.text.mark_set(tk.INSERT, cursor_pos)

        self.text.yview_moveto(y_scroll)

        self._update_status()
        self._mark_active_mode_needs_update()
        self._apply_first_line_indent()
        self._schedule_spellcheck()

    def _convert_to_smart_quotes(self) -> None:
        start, end, text = self._get_text_range()
        new_text = formatting_subsystem.convert_to_smart_quotes(text)
        if new_text != text:
            self._replace_text_range(start, end, new_text)

    def _convert_to_straight_quotes(self) -> None:
        start, end, text = self._get_text_range()
        new_text = formatting_subsystem.convert_to_straight_quotes(text)
        if new_text != text:
            self._replace_text_range(start, end, new_text)

    def _convert_ellipses_spaced(self) -> None:
        """Convert all ellipsis formats to standard unspaced three-dots (i.e. '...')."""
        start, end, text = self._get_text_range()
        new_text = formatting_subsystem.convert_ellipses_spaced(text)
        if new_text != text:
            self._replace_text_range(start, end, new_text)

    def _convert_ellipses_char(self) -> None:
        start, end, text = self._get_text_range()
        new_text = formatting_subsystem.convert_ellipses_char(text)
        if new_text != text:
            self._replace_text_range(start, end, new_text)

    def _clean_whitespace(self) -> None:
        start, end, text = self._get_text_range()
        new_text = formatting_subsystem.clean_whitespace(text)
        if new_text != text:
            self._replace_text_range(start, end, new_text)

    def _clear_emotion_highlights(self) -> None:
        self.text.tag_remove("emotion_hit", "1.0", tk.END)
        self._emotion_hits = []
        self._emotion_hit_fracs = []

    def _clear_cliche_highlights(self) -> None:
        self.text.tag_remove("cliche_hit", "1.0", tk.END)
        self._cliche_hits = []
        self._cliche_hit_fracs = []

    def _clear_redundancy_highlights(self) -> None:
        self.text.tag_remove("redundancy_hit", "1.0", tk.END)
        self._redundancy_hits = []
        self._redundancy_hit_fracs = []

    def _clear_passive_voice_highlights(self) -> None:
        self.text.tag_remove("passive_voice_hit", "1.0", tk.END)
        self._passive_voice_hits = []
        self._passive_voice_hit_fracs = []

    def _clear_typography_highlights(self) -> None:
        self.text.tag_remove("typography_hit", "1.0", tk.END)
        self._typography_hits = []
        self._typography_hit_fracs = []

    def _clear_dialogue_tag_highlights(self) -> None:
        self.text.tag_remove("dialogue_tag", "1.0", tk.END)
        self._dialogue_tag_hits = []
        self._dialogue_tag_hit_fracs = []

    def _reset_arch_tag_styles(self) -> None:
        self._arch_visible = {
            "arch_subject_first": True,
            "arch_participial_launch": True,
            "arch_contextual_lead": True,
            "arch_echoing_hinge": True,
            "arch_simultaneous_setup": True,
            "arch_fragment": True,
        }
        for tag_tuple in ARCH_TAG_STYLES:
            tag_name, bg, fg = tag_tuple[:3]
            self.text.tag_configure(
                tag_name,
                background=bg,
                foreground=fg,
                relief="flat",
                borderwidth=0,
            )
            if len(tag_tuple) > 3 and tag_tuple[3]:
                self.text.tag_configure(
                    tag_name,
                    relief="solid",
                    borderwidth=1,
                )

    def _toggle_arch_tag(self, base_tag: str) -> None:
        self._arch_visible[base_tag] = not self._arch_visible[base_tag]
        
        # Reconfigure tag colors in Tkinter text widget
        # Find colors from ARCH_TAG_STYLES
        normal_bg = ""
        normal_fg = ""
        stacked_bg = ""
        stacked_fg = ""
        
        for name, bg, fg, stacked in ARCH_TAG_STYLES:
            if name == base_tag:
                normal_bg = bg
                normal_fg = fg
            elif name == base_tag + "_stacked":
                stacked_bg = bg
                stacked_fg = fg
                
        is_visible = self._arch_visible[base_tag]
        if is_visible:
            self.text.tag_configure(base_tag, background=normal_bg, foreground=normal_fg, relief="flat", borderwidth=0)
            self.text.tag_configure(base_tag + "_stacked", background=stacked_bg, foreground=stacked_fg, relief="solid", borderwidth=1)
        else:
            self.text.tag_configure(base_tag, background="", foreground="", relief="flat", borderwidth=0)
            self.text.tag_configure(base_tag + "_stacked", background="", foreground="", relief="flat", borderwidth=0)
            
        self._update_status_legend()

    def _clear_arch_highlights(self) -> None:
        for tag_tuple in ARCH_TAG_STYLES:
            self.text.tag_remove(tag_tuple[0], "1.0", tk.END)
        self._arch_hits = []
        self._arch_hit_fracs = []

    def _run_arch_mode(self) -> None:
        self._reset_arch_tag_styles()
        self._arch_counts = {}

        def analyze_worker(content: str, progress_cb):
            if not content.strip():
                progress_cb(100)
                return []
            if getattr(self, "_arch_ignore_dialogue_var", None) and self._arch_ignore_dialogue_var.get():
                content = self._mask_dialogue_text(content)
            from filter_analyzer import analyze_sentence_architecture
            return analyze_sentence_architecture(content, progress_callback=progress_cb)

        def apply_worker(run_id: int, hits: list[tuple[int, int, str]], done) -> None:
            current_text = self.text.get("1.0", "end-1c")
            processed_hits = []
            for ws, we, tag in hits:
                norm = self._normalize_span(current_text, ws, we)
                if norm is None:
                    continue
                ws, we = norm
                if getattr(self, "_arch_ignore_dialogue_var", None) and self._arch_ignore_dialogue_var.get():
                    ws, we = self._trim_dialogue_from_span(current_text, ws, we)
                if we > ws:
                    processed_hits.append((ws, we, tag))

            self._arch_hits = processed_hits
            total = len(processed_hits)
            if total == 0:
                done("Sentence Architecture - no clauses found")
                self._arch_counts = {}
                self._update_status_legend()
                return

            idx = 0
            step = 400

            def run_chunk() -> None:
                nonlocal idx, step
                if run_id != self._mode_wrapper_run_seq:
                    return
                t0 = time.perf_counter()
                end = min(total, idx + step)
                for ws, we, tag in processed_hits[idx:end]:
                    self.text.tag_add(tag, f"1.0 + {ws}c", f"1.0 + {we}c")
                idx = end
                elapsed_ms = (time.perf_counter() - t0) * 1000
                if elapsed_ms > 0.5:
                    step = max(60, min(2000, int(step * 8.0 / elapsed_ms)))
                pct = 56 + int((idx / total) * 42)
                self._set_editor_progress(pct, "Architecture")
                if idx < total:
                    self.root.after(1, run_chunk)
                else:
                    # Build density fracs as (frac, tag) pairs for all sentence structures
                    total_chars = max(1, self._text_char_length())
                    fracs: list[tuple[float, str]] = []
                    for ws, we, tag in processed_hits:
                        mid = (ws + we) // 2
                        fracs.append((max(0.0, min(0.999999, mid / total_chars)), tag))
                    self._arch_hit_fracs = fracs

                    counts: dict[str, int] = {}
                    for _, _, tag in processed_hits:
                        base_tag = tag.replace("_stacked", "")
                        counts[base_tag] = counts.get(base_tag, 0) + 1

                    self._arch_counts = counts
                    done("Sentence Architecture")
                    self._update_status_legend()

            run_chunk()

        self._arch_update_needed = False
        self._hide_filter_refresh_button()
        self._run_wrapped_mode_scan(
            mode_label="Architecture",
            active_check=lambda: getattr(self, "_arch_active", False),
            clear_before=self._clear_arch_highlights,
            analyze_worker=analyze_worker,
            apply_worker=apply_worker,
            error_title="Sentence Architecture Error",
        )

    def _apply_tag_ranges_progressive(
        self,
        run_id: int,
        mode_label: str,
        ranges: list[tuple[int, int]],
        tag_name: str,
        on_done,
    ) -> None:
        total = len(ranges)
        if total == 0:
            self._set_editor_progress(100, mode_label)
            self.root.after(1, on_done)
            return

        idx = 0
        step = 600

        def run_chunk() -> None:
            nonlocal idx, step
            if run_id != self._mode_wrapper_run_seq:
                return
            t0 = time.perf_counter()
            end = min(total, idx + step)
            flat_args: list[str] = []
            for ws, we in ranges[idx:end]:
                if we <= ws:
                    continue
                flat_args.append(f"1.0 + {ws}c")
                flat_args.append(f"1.0 + {we}c")
            if flat_args:
                self.text.tk.call(self.text._w, "tag", "add", tag_name, *flat_args)
            idx = end
            elapsed_ms = (time.perf_counter() - t0) * 1000
            if elapsed_ms > 0.5:
                step = max(60, min(2000, int(step * 8.0 / elapsed_ms)))
            pct = 56 + int((idx / total) * 42)
            self._set_editor_progress(pct, mode_label)
            if idx < total:
                self.root.after(1, run_chunk)
            else:
                on_done()

        run_chunk()

    def _build_displayline_midpoint_fracs_async(
        self,
        run_id: int,
        ranges: list[tuple[int, int]],
        on_done,
    ) -> None:
        fracs = self._compute_midpoint_fracs(ranges)
        def run_callback() -> None:
            if run_id == self._mode_wrapper_run_seq:
                on_done(fracs)
        self.root.after(1, run_callback)

    def _normalize_span(self, text: str, start: int, end: int) -> tuple[int, int] | None:
        s = max(0, start)
        e = min(len(text), end)
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if e <= s:
            return None
        return s, e

    def _normalize_ranges(self, text: str, ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
        out: list[tuple[int, int]] = []
        for start, end in ranges:
            norm = self._normalize_span(text, start, end)
            if norm is not None:
                out.append(norm)
        return out

    def _start_mode_bootstrap_progress(self, run_id: int, mode_label: str) -> None:
        def tick() -> None:
            if run_id != self._mode_wrapper_run_seq or not self._mode_wrapper_processing:
                return
            cur = self._editor_progress_pct or 2
            if cur < 35:
                self._set_editor_progress(cur + 1, mode_label)
            self.root.after(90, tick)

        self.root.after(120, tick)

    def _compute_midpoint_fracs(self, ranges: list[tuple[int, int]]) -> list[float]:
        total_chars = max(1, self._text_char_length())
        fracs: list[float] = []
        for ws, we in ranges:
            if we <= ws:
                continue
            mid = (ws + we) // 2
            fracs.append(max(0.0, min(0.999999, mid / total_chars)))
        return fracs

    def _compute_tag_midpoint_fracs(self, tag_name: str) -> list[float]:
        ranges = self.text.tag_ranges(tag_name)
        if not ranges:
            return []
        total_chars = max(1, self._text_char_length())
        fracs: list[float] = []
        for i in range(0, len(ranges), 2):
            try:
                ws = int(self.text.count("1.0", ranges[i], "chars")[0])
                we = int(self.text.count("1.0", ranges[i + 1], "chars")[0])
            except Exception:
                continue
            if we <= ws:
                continue
            mid = (ws + we) // 2
            fracs.append(max(0.0, min(0.999999, mid / total_chars)))
        return fracs

    def _compute_displayline_midpoint_fracs(self, ranges: list[tuple[int, int]]) -> list[float]:
        if not ranges:
            return []
        try:
            total_display_lines = int(self.text.count("1.0", "end-1c", "displaylines")[0])
        except Exception:
            return self._compute_midpoint_fracs(ranges)
        total_display_lines = max(1, total_display_lines)
        out: list[float] = []
        for ws, we in ranges:
            if we <= ws:
                continue
            mid = (ws + we) // 2
            try:
                idx_str = self.text.index(f"1.0 + {mid}c")
                disp = int(self.text.count("1.0", idx_str, "displaylines")[0])
            except Exception:
                continue
            out.append(max(0.0, min(0.999999, disp / total_display_lines)))
        return out

    def _compute_tag_displayline_midpoint_fracs(self, tag_name: str) -> list[float]:
        ranges = self.text.tag_ranges(tag_name)
        if not ranges:
            return []
        packed: list[tuple[int, int]] = []
        for i in range(0, len(ranges), 2):
            try:
                ws = int(self.text.count("1.0", ranges[i], "chars")[0])
                we = int(self.text.count("1.0", ranges[i + 1], "chars")[0])
            except Exception:
                continue
            if we > ws:
                packed.append((ws, we))
        return self._compute_displayline_midpoint_fracs(packed)

    def _run_wrapped_mode_scan(
        self,
        mode_label: str,
        active_check,
        clear_before,
        analyze_worker,
        apply_worker,
        error_title: str,
    ) -> None:
        if not active_check() or self._mode_wrapper_processing:
            return

        self._mode_wrapper_processing = True
        self._mode_wrapper_run_seq += 1
        run_id = self._mode_wrapper_run_seq
        self._acquire_ui_lock()
        self._set_editor_progress(2, mode_label)
        self._start_mode_bootstrap_progress(run_id, mode_label)
        self._lbl_filter.config(text=f"{mode_label} - analyzing...")
        clear_before()
        content = self.text.get("1.0", "end-1c")

        def finish(summary: str) -> None:
            if run_id != self._mode_wrapper_run_seq:
                return
            self._mode_wrapper_processing = False
            self._set_editor_progress(100, mode_label)
            self._lbl_filter.config(text=summary)
            if self._mode_uses_density_band():
                self._request_density_redraw()
            self._update_density_viewport()
            self._update_pacing_viewport()
            self.root.after(120, lambda: self._set_editor_progress(None, ""))
            self._release_ui_lock()

        def complete(result, error: Exception | None) -> None:
            if run_id != self._mode_wrapper_run_seq:
                return
            if error is not None:
                self._mode_wrapper_processing = False
                self._set_editor_progress(None, "")
                self._release_ui_lock()
                self._lbl_filter.config(text="")
                self.set_editor_mode(EDITOR_MODE_OFF)
                messagebox.showerror(error_title, str(error))
                return
            self._set_editor_progress(56, mode_label)
            apply_worker(run_id, result, finish)

        def worker() -> None:
            try:
                last_progress = -1

                def on_scan_progress(raw_pct: int) -> None:
                    nonlocal last_progress
                    pct = 2 + int((max(0, min(100, raw_pct)) / 100) * 52)
                    if pct == last_progress:
                        return
                    last_progress = pct
                    self.root.after(0, lambda p=pct: self._set_editor_progress(p, mode_label))

                result = analyze_worker(content, on_scan_progress)
                self.root.after(0, lambda r=result: complete(r, None))
            except Exception as exc:
                self.root.after(0, lambda e=exc: complete(None, e))

        threading.Thread(target=worker, daemon=True).start()

    def _mark_emotion_needs_update(self) -> None:
        if not self._emotion_active:
            return
        self._emotion_update_needed = True
        self._show_filter_refresh_button()
        self._lbl_filter.config(text="Emotion catcher - changes pending (click Refresh)")

    def _mark_dialogue_tags_needs_update(self) -> None:
        if not self._dialogue_tag_active:
            return
        self._dialogue_tag_update_needed = True
        self._show_filter_refresh_button()
        self._lbl_filter.config(text="Dialogue tags - changes pending (click Refresh)")

    def _mark_echo_needs_update(self) -> None:
        if not self._echo_active:
            return
        self._echo_update_needed = True
        self._show_filter_refresh_button()
        self._lbl_filter.config(text="Echo radar - changes pending (click Refresh)")

    def _mark_pacing_needs_update(self) -> None:
        if not self._pacing_active:
            return
        self._pacing_update_needed = True
        self._show_filter_refresh_button()
        self._lbl_filter.config(text="Rhythm/pacing - changes pending (click Refresh)")

    def _mark_typography_needs_update(self) -> None:
        return

    def _run_cliche_mode(self) -> None:
        def analyze_worker(content: str, progress_cb):
            if not content.strip():
                progress_cb(100)
                return []
            from filter_analyzer import analyze_cliches
            hits = analyze_cliches(content, progress_callback=progress_cb)
            raw_ranges = [(ws, we) for ws, we, _cls in hits]
            return self._normalize_ranges(content, raw_ranges)

        def apply_worker(run_id: int, ranges: list[tuple[int, int]], done) -> None:
            self._cliche_hits = ranges

            def wrapped_done() -> None:
                if ranges and not self.text.tag_ranges("cliche_hit"):
                    for ws, we in ranges:
                        if we > ws:
                            self.text.tag_add("cliche_hit", f"1.0 + {ws}c", f"1.0 + {we}c")
                def finish_fracs(fracs: list[float]) -> None:
                    if run_id != self._mode_wrapper_run_seq:
                        return
                    self._cliche_hit_fracs = fracs
                    if ranges:
                        done(f"Cliches - {len(ranges)} hit(s)")
                    else:
                        done("Cliches - no cliches found")

                self._build_displayline_midpoint_fracs_async(run_id, ranges, finish_fracs)

            self._apply_tag_ranges_progressive(run_id, "Cliches", ranges, "cliche_hit", wrapped_done)

        self._cliche_update_needed = False
        self._hide_filter_refresh_button()
        self._run_wrapped_mode_scan(
            mode_label="Cliches",
            active_check=lambda: getattr(self, "_cliche_active", False),
            clear_before=self._clear_cliche_highlights,
            analyze_worker=analyze_worker,
            apply_worker=apply_worker,
            error_title="Cliches Error",
        )

    def _run_redundancy_mode(self) -> None:
        def analyze_worker(content: str, progress_cb):
            if not content.strip():
                progress_cb(100)
                return []
            from filter_analyzer import analyze_redundancies
            hits = analyze_redundancies(content, progress_callback=progress_cb)
            raw_ranges = [(ws, we) for ws, we, _cls in hits]
            return self._normalize_ranges(content, raw_ranges)

        def apply_worker(run_id: int, ranges: list[tuple[int, int]], done) -> None:
            self._redundancy_hits = ranges

            def wrapped_done() -> None:
                if ranges and not self.text.tag_ranges("redundancy_hit"):
                    for ws, we in ranges:
                        if we > ws:
                            self.text.tag_add("redundancy_hit", f"1.0 + {ws}c", f"1.0 + {we}c")
                def finish_fracs(fracs: list[float]) -> None:
                    if run_id != self._mode_wrapper_run_seq:
                        return
                    self._redundancy_hit_fracs = fracs
                    if ranges:
                        done(f"Redundancies - {len(ranges)} hit(s)")
                    else:
                        done("Redundancies - no redundancies found")

                self._build_displayline_midpoint_fracs_async(run_id, ranges, finish_fracs)

            self._apply_tag_ranges_progressive(run_id, "Redundancies", ranges, "redundancy_hit", wrapped_done)

        self._redundancy_update_needed = False
        self._hide_filter_refresh_button()
        self._run_wrapped_mode_scan(
            mode_label="Redundancies",
            active_check=lambda: getattr(self, "_redundancy_active", False),
            clear_before=self._clear_redundancy_highlights,
            analyze_worker=analyze_worker,
            apply_worker=apply_worker,
            error_title="Redundancies Error",
        )

    def _run_passive_voice_mode(self) -> None:
        def analyze_worker(content: str, progress_cb):
            if not content.strip():
                progress_cb(100)
                return []
            from filter_analyzer import analyze_passive_voice
            hits = analyze_passive_voice(content, progress_callback=progress_cb)
            raw_ranges = [(ws, we) for ws, we, _cls in hits]
            return self._normalize_ranges(content, raw_ranges)

        def apply_worker(run_id: int, ranges: list[tuple[int, int]], done) -> None:
            self._passive_voice_hits = ranges

            def wrapped_done() -> None:
                if ranges and not self.text.tag_ranges("passive_voice_hit"):
                    for ws, we in ranges:
                        if we > ws:
                            self.text.tag_add("passive_voice_hit", f"1.0 + {ws}c", f"1.0 + {we}c")
                def finish_fracs(fracs: list[float]) -> None:
                    if run_id != self._mode_wrapper_run_seq:
                        return
                    self._passive_voice_hit_fracs = fracs
                    if ranges:
                        done(f"Passive Voice - {len(ranges)} hit(s)")
                    else:
                        done("Passive Voice - no passive voice found")

                self._build_displayline_midpoint_fracs_async(run_id, ranges, finish_fracs)

            self._apply_tag_ranges_progressive(run_id, "Passive Voice", ranges, "passive_voice_hit", wrapped_done)

        self._passive_voice_update_needed = False
        self._hide_filter_refresh_button()
        self._run_wrapped_mode_scan(
            mode_label="Passive Voice",
            active_check=lambda: getattr(self, "_passive_voice_active", False),
            clear_before=self._clear_passive_voice_highlights,
            analyze_worker=analyze_worker,
            apply_worker=apply_worker,
            error_title="Passive Voice Error",
        )

    def _run_emotion_catcher_mode(self) -> None:
        def analyze_worker(content: str, progress_cb):
            if not content.strip():
                progress_cb(100)
                return []
            hits = analyze_emotion_words(content, progress_callback=progress_cb)
            raw_ranges = [(ws, we) for ws, we, _cls in hits]
            return self._normalize_ranges(content, raw_ranges)

        def apply_worker(run_id: int, ranges: list[tuple[int, int]], done) -> None:
            self._emotion_hits = ranges

            def wrapped_done() -> None:
                # Keep emotion density markers synced to what is actually tagged
                # in the editor text widget.
                if ranges and not self.text.tag_ranges("emotion_hit"):
                    for ws, we in ranges:
                        if we > ws:
                            self.text.tag_add("emotion_hit", f"1.0 + {ws}c", f"1.0 + {we}c")
                def finish_fracs(fracs: list[float]) -> None:
                    if run_id != self._mode_wrapper_run_seq:
                        return
                    self._emotion_hit_fracs = fracs
                    if ranges:
                        done(f"Emotion catcher - {len(ranges)} hit(s)")
                    else:
                        done("Emotion catcher - no explicit emotion words")

                self._build_displayline_midpoint_fracs_async(run_id, ranges, finish_fracs)

            self._apply_tag_ranges_progressive(run_id, "Emotion", ranges, "emotion_hit", wrapped_done)

        self._emotion_update_needed = False
        self._hide_filter_refresh_button()
        self._run_wrapped_mode_scan(
            mode_label="Emotion",
            active_check=lambda: self._emotion_active,
            clear_before=self._clear_emotion_highlights,
            analyze_worker=analyze_worker,
            apply_worker=apply_worker,
            error_title="Emotion Catcher Error",
        )

    def _run_dialogue_tags_mode(self) -> None:
        def analyze_worker(content: str, progress_cb):
            if not content.strip():
                progress_cb(100)
                return []
            hits = analyze_dialogue_tags(content)
            progress_cb(100)
            ranges = [(ws, we) for ws, we, _cls in hits]
            return self._normalize_ranges(content, ranges)

        def apply_worker(run_id: int, ranges: list[tuple[int, int]], done) -> None:
            self._dialogue_tag_hits = ranges

            def wrapped_done() -> None:
                def finish_fracs(fracs: list[float]) -> None:
                    if run_id != self._mode_wrapper_run_seq:
                        return
                    self._dialogue_tag_hit_fracs = fracs
                    if ranges:
                        done(f"Dialogue tags - {len(ranges)} lint hit(s)")
                    else:
                        done("Dialogue tags - no lint hits")

                self._build_displayline_midpoint_fracs_async(run_id, ranges, finish_fracs)

            self._apply_tag_ranges_progressive(run_id, "DialogueTags", ranges, "dialogue_tag", wrapped_done)

        self._dialogue_tag_update_needed = False
        self._hide_filter_refresh_button()
        self._run_wrapped_mode_scan(
            mode_label="DialogueTags",
            active_check=lambda: self._dialogue_tag_active,
            clear_before=self._clear_dialogue_tag_highlights,
            analyze_worker=analyze_worker,
            apply_worker=apply_worker,
            error_title="Dialogue Tags Error",
        )

    def _run_typography_scan_mode(self) -> None:
        self._lbl_filter.config(text="Typography mode is disabled")

    def _clear_echo_highlights(self) -> None:
        self.text.tag_remove("echo_hit", "1.0", tk.END)
        self.text.tag_remove("echo_focus", "1.0", tk.END)
        self.text.tag_remove("echo_focus_cursor", "1.0", tk.END)
        self._echo_hits = []
        self._echo_hit_fracs = []
        self._echo_groups = {}
        self._echo_token_hits = []
        self._echo_token_starts = []
        self._echo_focus_word = ""
        if self._echo_focus_refresh_job is not None:
            try:
                self.root.after_cancel(self._echo_focus_refresh_job)
            except Exception:
                pass
            self._echo_focus_refresh_job = None

    def _clear_pacing_highlights(self) -> None:
        for tag_name, _fg, _bg in PACING_TAG_STYLES:
            self.text.tag_remove(tag_name, "1.0", tk.END)
        self._pacing_heat_spans = []
        self._hide_pacing_lane()

    def run_pacing_scan(self) -> None:
        if self._active_editor_mode != EDITOR_MODE_PACING:
            self.set_editor_mode(EDITOR_MODE_PACING)
            return
        self._run_pacing_scan_mode()

    def _run_pacing_scan_mode(self) -> None:
        def analyze_worker(content: str, progress_cb):
            if not content.strip():
                progress_cb(100)
                return []
            bands = analyze_sentence_pacing(
                content,
                short_max_words=self._pacing_short_words,
                average_words=self._pacing_average_words,
                long_min_words=self._pacing_long_words,
                progress_callback=progress_cb,
            )
            return bands

        def apply_worker(run_id: int, bands: list[tuple[int, int, float, int]], done) -> None:
            total = len(bands)
            if total == 0:
                done("Rhythm & pacing - no sentences mapped")
                return

            idx = 0
            step = 320
            very_short_count = 0
            long_count = 0
            total_chars = max(1, self._text_char_length())
            current_text = self.text.get("1.0", "end-1c")

            def run_chunk() -> None:
                nonlocal idx, very_short_count, long_count
                if run_id != self._mode_wrapper_run_seq:
                    return
                end = min(total, idx + step)
                for start, stop, heat, wc in bands[idx:end]:
                    norm = self._normalize_span(current_text, start, stop)
                    if norm is None:
                        continue
                    start, stop = norm
                    tag = self._pacing_tag_from_heat(heat)
                    self.text.tag_add(tag, f"1.0 + {start}c", f"1.0 + {stop}c")
                    if wc <= self._pacing_short_words:
                        very_short_count += 1
                    elif wc >= self._pacing_long_words:
                        long_count += 1
                    start_frac = max(0.0, min(0.999999, start / total_chars))
                    stop_frac = max(start_frac, min(0.999999, stop / total_chars))
                    self._pacing_heat_spans.append((start_frac, stop_frac, heat))
                idx = end
                pct = 56 + int((idx / total) * 42)
                self._set_editor_progress(pct, "Pacing")
                if idx < total:
                    self.root.after(1, run_chunk)
                    return
                if self._pacing_heat_spans:
                    self._show_pacing_lane()
                self._redraw_pacing_lane()
                done(
                    f"Rhythm & Pacing: {very_short_count:,} short (<= {self._pacing_short_words} words) | "
                    f"{long_count:,} long (>= {self._pacing_long_words} words)"
                )

            run_chunk()

        self._pacing_update_needed = False
        self._hide_filter_refresh_button()
        self._run_wrapped_mode_scan(
            mode_label="Pacing",
            active_check=lambda: self._pacing_active,
            clear_before=self._clear_pacing_highlights,
            analyze_worker=analyze_worker,
            apply_worker=apply_worker,
            error_title="Rhythm & Pacing Error",
        )

    def _show_pacing_lane(self) -> None:
        if self._pacing_lane_visible:
            return
        self._pacing_lane.pack(side=tk.LEFT, fill=tk.Y, before=self._lineno)
        self._pacing_lane_visible = True

    def _hide_pacing_lane(self) -> None:
        if not self._pacing_lane_visible:
            return
        self._pacing_lane.pack_forget()
        self._pacing_lane_visible = False
        self._pacing_viewport_id = None
        self._pacing_lane.delete("all")

    def _on_pacing_lane_click(self, event) -> None:
        if not self._pacing_lane_visible:
            return
        h = max(2, self._pacing_lane.winfo_height())
        frac = max(0.0, min(1.0, event.y / (h - 1)))
        self.text.yview_moveto(frac)
        self._redraw_lineno()
        self._update_density_viewport()
        self._update_pacing_viewport()

    def _redraw_pacing_lane(self) -> None:
        if not self._pacing_lane_visible:
            return
        self._pacing_lane.delete("all")
        self._pacing_viewport_id = None
        w = max(8, self._pacing_lane.winfo_width())
        h = max(20, self._pacing_lane.winfo_height())
        row_scores = [0.0] * h
        row_weights = [0] * h
        row_min = [0.0] * h
        row_max = [0.0] * h
        for start_frac, stop_frac, heat in self._pacing_heat_spans:
            y1 = max(0, min(h - 1, int(start_frac * (h - 1))))
            y2 = max(y1, min(h - 1, int(math.ceil(stop_frac * (h - 1)))))
            for y in range(y1, y2 + 1):
                row_scores[y] += heat
                row_weights[y] += 1
                row_min[y] = min(row_min[y], heat)
                row_max[y] = max(row_max[y], heat)
        weights = (1, 2, 3, 2, 1)
        row_heat = [0.0] * h
        for y in range(h):
            score_total = 0.0
            weight_total = 0
            extreme_total = 0.0
            extreme_weight_total = 0
            for offset, weight in zip(range(-2, 3), weights):
                yy = y + offset
                if yy < 0 or yy >= h or row_weights[yy] == 0:
                    continue
                avg_heat = row_scores[yy] / row_weights[yy]
                strongest = row_max[yy] if abs(row_max[yy]) >= abs(row_min[yy]) else row_min[yy]
                score_total += avg_heat * weight
                weight_total += weight
                extreme_total += strongest * weight
                extreme_weight_total += weight
            if weight_total == 0 or extreme_weight_total == 0:
                row_heat[y] = 0.0
                continue
            smoothed_avg = score_total / weight_total
            smoothed_extreme = extreme_total / extreme_weight_total
            row_heat[y] = (smoothed_avg * 0.58) + (smoothed_extreme * 0.42)

        peak_positive = max((value for value in row_heat if value > 0.0), default=0.0)
        peak_negative = max((-value for value in row_heat if value < 0.0), default=0.0)

        for y in range(h):
            heat = row_heat[y]
            if heat > 0.0 and peak_positive > 0.0:
                normalized = heat / peak_positive
            elif heat < 0.0 and peak_negative > 0.0:
                normalized = heat / peak_negative
            else:
                normalized = 0.0
            normalized = math.copysign(abs(normalized) ** 0.82, normalized)
            self._pacing_lane.create_line(
                1,
                y,
                w - 2,
                y,
                fill=self._pacing_heat_color(normalized),
            )
        self._update_pacing_viewport()

    def _pacing_tag_from_heat(self, heat: float) -> str:
        if heat <= -0.7:
            return "pacing_cool_3"
        if heat <= -0.35:
            return "pacing_cool_2"
        if heat < -0.1:
            return "pacing_cool_1"
        if heat < 0.15:
            return "pacing_neutral"
        if heat < 0.5:
            return "pacing_warm_1"
        if heat < 0.85:
            return "pacing_warm_2"
        return "pacing_hot"

    def _blend_hex_color(self, left: str, right: str, amount: float) -> str:
        amount = max(0.0, min(1.0, amount))
        left_rgb = tuple(int(left[i:i + 2], 16) for i in (1, 3, 5))
        right_rgb = tuple(int(right[i:i + 2], 16) for i in (1, 3, 5))
        blended = tuple(
            round(lv + ((rv - lv) * amount)) for lv, rv in zip(left_rgb, right_rgb)
        )
        return f"#{blended[0]:02x}{blended[1]:02x}{blended[2]:02x}"

    def _pacing_heat_color(self, heat: float) -> str:
        if heat <= 0.0:
            return self._blend_hex_color("#4ea4ff", "#58d68d", heat + 1.0)
        return self._blend_hex_color("#58d68d", "#ff6b6b", heat)

    def _update_pacing_viewport(self) -> None:
        if not self._pacing_lane_visible:
            return
        w = max(8, self._pacing_lane.winfo_width())
        h = max(20, self._pacing_lane.winfo_height())
        first, last = self.text.yview()
        y1 = int(first * h)
        y2 = max(y1 + 6, int(last * h))
        if self._pacing_viewport_id is None:
            self._pacing_viewport_id = self._pacing_lane.create_rectangle(
                0, y1, w - 1, y2, outline=ACCENT, width=1
            )
        else:
            self._pacing_lane.coords(self._pacing_viewport_id, 0, y1, w - 1, y2)
            self._pacing_lane.tag_raise(self._pacing_viewport_id)

    def run_echo_radar(self) -> None:
        if self._active_editor_mode != EDITOR_MODE_ECHO:
            self.set_editor_mode(EDITOR_MODE_ECHO)
            return
        self._run_echo_radar_mode()

    def _run_echo_radar_mode(self) -> None:
        def analyze_worker(content: str, progress_cb):
            result = analyze_echo_radar(content, self._echo_focus_window_words, progress_cb)
            result["ranges"] = self._normalize_ranges(content, result["ranges"])
            return result

        def apply_worker(run_id: int, result: dict[str, object], done) -> None:
            ranges = list(result.get("ranges", []))
            word_counts = dict(result.get("word_counts", {}))
            token_hits = list(result.get("token_hits", []))
            groups = dict(result.get("groups", {}))
            self._echo_hits = ranges
            self._echo_hit_fracs = self._compute_midpoint_fracs(ranges)
            self._echo_token_hits = token_hits
            self._echo_groups = groups
            self._echo_token_starts = [start for _word, start, _end, _token_idx in token_hits]

            def wrapped_done() -> None:
                self._refresh_echo_focus_highlights(force=True)
                if word_counts:
                    done(
                        f"Echo radar - tracking {len(ranges)} local echo hit(s) "
                        f"across {len(word_counts)} word(s)"
                    )
                else:
                    done("Echo radar - no nearby repeats with current sensitivity")

                def finish_fracs(fracs: list[float]) -> None:
                    if run_id != self._mode_wrapper_run_seq:
                        return
                    self._echo_hit_fracs = fracs
                    if self._density_visible:
                        self._request_density_redraw()

                self.root.after(
                    1,
                    lambda: self._build_displayline_midpoint_fracs_async(run_id, ranges, finish_fracs),
                )

            self._apply_tag_ranges_progressive(run_id, "Echo", ranges, "echo_hit", wrapped_done)

        self._echo_update_needed = False
        self._hide_filter_refresh_button()
        self._run_wrapped_mode_scan(
            mode_label="Echo",
            active_check=lambda: self._echo_active,
            clear_before=self._clear_echo_highlights,
            analyze_worker=analyze_worker,
            apply_worker=apply_worker,
            error_title="Echo Radar Error",
        )

    def _schedule_echo_focus_refresh(self) -> None:
        if not self._echo_active or self._mode_wrapper_processing:
            return
        if self._echo_focus_refresh_job is not None:
            try:
                self.root.after_cancel(self._echo_focus_refresh_job)
            except Exception:
                pass
        self._echo_focus_refresh_job = self.root.after(24, self._refresh_echo_focus_highlights)

    def _refresh_echo_focus_highlights(self, force: bool = False) -> None:
        self._echo_focus_refresh_job = None
        if not self._echo_active:
            return

        self.text.tag_remove("echo_focus", "1.0", tk.END)
        self.text.tag_remove("echo_focus_cursor", "1.0", tk.END)

        if not self._echo_token_hits:
            return

        try:
            caret = int(self.text.count("1.0", "insert", "chars")[0])
        except Exception:
            caret = 0

        idx = bisect.bisect_right(self._echo_token_starts, caret) - 1
        candidate_indexes = [idx, idx + 1]
        active_token: tuple[str, int, int, int] | None = None
        for cand in candidate_indexes:
            if cand < 0 or cand >= len(self._echo_token_hits):
                continue
            word, start, end, token_idx = self._echo_token_hits[cand]
            if start - 1 <= caret <= end + 1:
                active_token = (word, start, end, token_idx)
                break

        if active_token is None:
            if force:
                self._lbl_filter.config(
                    text=f"Echo radar - tracking {len(self._echo_hits)} local hit(s); place cursor on a highlighted word"
                )
            return

        word, start, end, token_idx = active_token
        self._echo_focus_word = word

        candidates = self._echo_groups.get(word, [])
        window = self._echo_focus_window_words
        nearby: list[tuple[int, int]] = []
        for ws, we, widx in candidates:
            if abs(widx - token_idx) <= window:
                nearby.append((ws, we))

        for ws, we in nearby:
            self.text.tag_add("echo_focus", f"1.0 + {ws}c", f"1.0 + {we}c")
        self.text.tag_remove("echo_focus", f"1.0 + {start}c", f"1.0 + {end}c")
        self.text.tag_add("echo_focus_cursor", f"1.0 + {start}c", f"1.0 + {end}c")

        self._lbl_filter.config(
            text=(
                f"Echo radar - \"{word}\" nearby echoes: {len(nearby)} "
                f"(window {window} words)"
            )
        )

    def select_all(self) -> None:
        self.text.tag_add(tk.SEL, "1.0", tk.END)
        self.text.mark_set(tk.INSERT, "end-1c")

    def show_find_dialog(self, show_replace: bool = False) -> None:
        self._search_subsystem.show_find_dialog(show_replace)

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

        spellcheck_enabled = data.get("spelling_checker_enabled", True)
        self._spellcheck_active = bool(spellcheck_enabled)
        self._spellcheck_toggle_var.set(self._spellcheck_active)

        pov_choice = data.get("pov_choice", "All Pronouns (Broad Scan)")
        if isinstance(pov_choice, str) and pov_choice in POV_PRONOUN_MAP:
            self._pov_choice.set(pov_choice)

        echo_range = data.get("echo_range", 80)
        if isinstance(echo_range, (int, float)):
            int_echo = int(echo_range)
            self._echo_focus_window_words = int_echo
            self._echo_slider_var.set(int_echo)
            if hasattr(self, "_echo_slider_label") and self._echo_slider_label:
                self._echo_slider_label.config(text=f"Echo Range: {int_echo}")

        pacing_limit = data.get("pacing_limit", 19)
        if isinstance(pacing_limit, (int, float)):
            int_pacing = int(pacing_limit)
            self._pacing_long_words = int_pacing
            self._pacing_short_words = math.ceil(int_pacing * 0.2)
            self._pacing_average_words = math.ceil(int_pacing * 0.6)
            self._pacing_slider_var.set(int_pacing)
            if hasattr(self, "_pacing_slider_label") and self._pacing_slider_label:
                self._pacing_slider_label.config(text=f"Pacing Limit: {int_pacing}")

        arch_ignore = data.get("arch_ignore_dialogue", False)
        self._arch_ignore_dialogue_var.set(bool(arch_ignore))

    def _save_user_settings(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._settings_path), exist_ok=True)
            data = {
                "pov_names": self._pov_names_var.get().strip(),
                "spelling_checker_enabled": bool(self._spellcheck_active),
                "pov_choice": self._pov_choice.get(),
                "echo_range": int(self._echo_focus_window_words),
                "pacing_limit": int(self._pacing_long_words),
                "arch_ignore_dialogue": bool(self._arch_ignore_dialogue_var.get()),
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

    def _on_echo_range_changed(self, val) -> None:
        int_val = int(float(val))
        self._echo_slider_label.config(text=f"Echo Range: {int_val}")
        if int_val != self._echo_focus_window_words:
            self._echo_focus_window_words = int_val
            self._mark_echo_needs_update()

    def _on_pacing_limit_changed(self, val) -> None:
        int_val = int(float(val))
        self._pacing_slider_label.config(text=f"Pacing Limit: {int_val}")
        if int_val != self._pacing_long_words:
            self._pacing_long_words = int_val
            self._pacing_short_words = math.ceil(int_val * 0.2)
            self._pacing_average_words = math.ceil(int_val * 0.6)
            self._update_status_legend()
            self._mark_pacing_needs_update()

    def _on_arch_ignore_dialogue_changed(self) -> None:
        if getattr(self, "_arch_active", False):
            self._arch_update_needed = True
            self._run_arch_mode()

    def _mask_dialogue_text(self, text: str) -> str:
        chars = list(text)
        in_quote = False
        quote_start = -1
        for i, c in enumerate(chars):
            if c in ('\r', '\n'):
                if in_quote and quote_start != -1:
                    for j in range(quote_start + 1, i):
                        chars[j] = ' '
                in_quote = False
                quote_start = -1
                continue
            if c in ('"', '“', '”'):
                if not in_quote:
                    in_quote = True
                    quote_start = i
                else:
                    for j in range(quote_start + 1, i):
                        chars[j] = ' '
                    in_quote = False
                    quote_start = -1
        if in_quote and quote_start != -1:
            for j in range(quote_start + 1, len(chars)):
                chars[j] = ' '
        return "".join(chars)

    def _trim_dialogue_from_span(self, text: str, start: int, end: int) -> tuple[int, int]:
        end = min(end, len(text))
        # Trim leading dialogue
        while True:
            while start < end and text[start].isspace():
                start += 1
            if start >= end:
                break
            if text[start] in ('"', '“'):
                close_idx = -1
                for idx in range(start + 1, end):
                    if text[idx] in ('"', '”'):
                        close_idx = idx
                        break
                if close_idx != -1:
                    start = close_idx + 1
                    continue
            break

        # Trim trailing dialogue
        while True:
            while end > start and text[end - 1].isspace():
                end -= 1
            if end <= start:
                break
            if text[end - 1] in ('"', '”'):
                open_idx = -1
                for idx in range(end - 2, start - 1, -1):
                    if text[idx] in ('"', '“'):
                        open_idx = idx
                        break
                if open_idx != -1:
                    end = open_idx
                    continue
            break
            
        return start, end



    def show_settings_dialog(self, initial_tab: int = 0) -> None:
        if hasattr(self, "_settings_dialog") and self._settings_dialog and self._settings_dialog.winfo_exists():
            self._settings_dialog.deiconify()
            self._settings_dialog.lift()
            self._settings_dialog.focus_force()
            if hasattr(self, "_settings_notebook") and self._settings_notebook:
                self._settings_notebook.select(initial_tab)
            return

        dlg = tk.Toplevel(self.root)
        dlg.withdraw()
        dlg.title("Settings")
        dlg.configure(bg=BG_SURFACE)
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        self._settings_dialog = dlg

        # Temporary variables for spellingchecker, mode settings, and POV names
        temp_spellcheck_active = tk.BooleanVar(value=self._spellcheck_active)
        temp_custom_words = sorted(list(self._spellcheck_subsystem.custom_dict_words))
        temp_pov_choice = tk.StringVar(value=self._pov_choice.get())
        temp_echo_range = tk.IntVar(value=self._echo_focus_window_words)
        temp_pacing_limit = tk.IntVar(value=self._pacing_long_words)
        temp_arch_ignore_dialogue = tk.BooleanVar(value=self._arch_ignore_dialogue_var.get())
        temp_pov_names = tk.StringVar(value=self._pov_names_var.get())

        # Configure style for TNotebook to match the dark Catppuccin theme
        style = ttk.Style(self.root)
        style.configure("Settings.TNotebook", background=BG_SURFACE, borderwidth=0)
        style.configure(
            "Settings.TNotebook.Tab",
            background=BG_OVERLAY,
            foreground=TEXT,
            borderwidth=0,
            padding=[12, 6],
            font=("Segoe UI", 9, "bold")
        )
        style.map(
            "Settings.TNotebook.Tab",
            background=[("selected", BG_SURFACE)],
            foreground=[("selected", ACCENT)]
        )

        notebook = ttk.Notebook(dlg, style="Settings.TNotebook")
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self._settings_notebook = notebook

        # ------------------------------------------------------------- Tab 1: Spelling Checker
        tab_spell = tk.Frame(notebook, bg=BG_SURFACE)
        notebook.add(tab_spell, text="Spelling Checker")

        chk_spell = tk.Checkbutton(
            tab_spell,
            text="Spelling Checker Enabled",
            variable=temp_spellcheck_active,
            bg=BG_SURFACE,
            fg=TEXT,
            selectcolor=BG_SURFACE,
            activebackground=BG_SURFACE,
            activeforeground=TEXT,
            font=("Segoe UI", 9, "bold"),
            bd=0,
            highlightthickness=0,
        )
        chk_spell.pack(anchor="w", padx=15, pady=(15, 10))

        words_frame = tk.Frame(tab_spell, bg=BG_SURFACE)
        words_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        lbl_words = tk.Label(
            words_frame,
            text="Added User Words:",
            bg=BG_SURFACE,
            fg=TEXT_SUBTLE,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )
        lbl_words.pack(fill=tk.X, pady=(0, 4))

        list_container = tk.Frame(words_frame, bg=BG_SURFACE)
        list_container.pack(fill=tk.BOTH, expand=True)

        list_frame = tk.Frame(list_container, bg=BG)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(
            list_frame, bg=BG_SURFACE, troughcolor=BG,
            activebackground=ACCENT, width=12, relief="flat", bd=0,
        )
        listbox = tk.Listbox(
            list_frame,
            bg=BG,
            fg=TEXT,
            selectbackground=BG_OVERLAY,
            selectforeground=ACCENT,
            highlightcolor=ACCENT,
            highlightbackground=BG_OVERLAY,
            relief="flat",
            bd=0,
            font=("Segoe UI", 9),
            yscrollcommand=scrollbar.set,
            width=28,
            height=10,
        )
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def update_listbox():
            listbox.delete(0, tk.END)
            for w in temp_custom_words:
                listbox.insert(tk.END, w)

        update_listbox()

        actions_frame = tk.Frame(list_container, bg=BG_SURFACE, padx=10)
        actions_frame.pack(side=tk.LEFT, fill=tk.Y)

        lbl_new_word = tk.Label(
            actions_frame,
            text="New Word:",
            bg=BG_SURFACE,
            fg=TEXT_SUBTLE,
            font=("Segoe UI", 9),
            anchor="w",
        )
        lbl_new_word.pack(fill=tk.X, pady=(0, 2))

        add_word_entry = tk.Entry(
            actions_frame,
            bg=BG,
            fg=TEXT,
            insertbackground=ACCENT,
            relief="flat",
            font=("Segoe UI", 9),
            width=18,
        )
        add_word_entry.pack(fill=tk.X, pady=(0, 8))

        def add_word_action():
            word = add_word_entry.get().strip().lower()
            if not word:
                return
            if " " in word:
                messagebox.showerror("Invalid Word", "User words cannot contain spaces.", parent=dlg)
                return
            if word in temp_custom_words:
                messagebox.showinfo("Duplicate Word", f"'{word}' is already in the custom dictionary.", parent=dlg)
                return
            temp_custom_words.append(word)
            temp_custom_words.sort()
            update_listbox()
            add_word_entry.delete(0, tk.END)

        add_word_entry.bind("<Return>", lambda _e: add_word_action())

        btn_add = tk.Button(
            actions_frame,
            text="Add Word",
            command=add_word_action,
            bg=BG_OVERLAY,
            fg=TEXT,
            activebackground=ACCENT,
            activeforeground=BG,
            relief="flat",
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )
        btn_add.pack(fill=tk.X, pady=(0, 10))

        def remove_word_action():
            selected = listbox.curselection()
            if not selected:
                return
            index = selected[0]
            word = listbox.get(index)
            if word in temp_custom_words:
                temp_custom_words.remove(word)
                update_listbox()
                new_size = len(temp_custom_words)
                if new_size > 0:
                    new_idx = min(index, new_size - 1)
                    listbox.select_set(new_idx)
                    listbox.activate(new_idx)

        btn_remove = tk.Button(
            actions_frame,
            text="Remove Selected",
            command=remove_word_action,
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
        btn_remove.pack(fill=tk.X)

        # ------------------------------------------------------------- Tab 2: Mode Settings
        tab_modes = tk.Frame(notebook, bg=BG_SURFACE)
        notebook.add(tab_modes, text="Mode Settings")

        # Layout modes as vertical stack with descriptive labels
        modes_container = tk.Frame(tab_modes, bg=BG_SURFACE, padx=10, pady=10)
        modes_container.pack(fill=tk.BOTH, expand=True)

        # POV Pronoun Filter Settings
        sec_pov = tk.Frame(modes_container, bg=BG_SURFACE, pady=6)
        sec_pov.pack(fill=tk.X)
        tk.Label(
            sec_pov,
            text="Filter Words: POV Setting",
            bg=BG_SURFACE,
            fg=ACCENT,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill=tk.X)
        combo_pov = ttk.Combobox(
            sec_pov,
            state="readonly",
            values=list(POV_PRONOUN_MAP.keys()),
            textvariable=temp_pov_choice,
            width=28,
        )
        combo_pov.pack(anchor="w", pady=(4, 0))

        # Echo Radar Range Slider
        sec_echo = tk.Frame(modes_container, bg=BG_SURFACE, pady=6)
        sec_echo.pack(fill=tk.X)
        lbl_echo_hdr = tk.Frame(sec_echo, bg=BG_SURFACE)
        lbl_echo_hdr.pack(fill=tk.X)
        tk.Label(
            lbl_echo_hdr,
            text="Echo Radar: Focus Window Range (Words)",
            bg=BG_SURFACE,
            fg=ACCENT,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(side=tk.LEFT)
        lbl_echo_val = tk.Label(
            lbl_echo_hdr,
            text=str(temp_echo_range.get()),
            bg=BG_SURFACE,
            fg=TEXT,
            font=("Segoe UI", 9, "bold"),
        )
        lbl_echo_val.pack(side=tk.RIGHT, padx=5)

        def on_temp_echo_change(val):
            int_val = int(float(val))
            lbl_echo_val.config(text=str(int_val))
            temp_echo_range.set(int_val)

        scale_echo = ttk.Scale(
            sec_echo,
            from_=1,
            to=100,
            orient=tk.HORIZONTAL,
            variable=temp_echo_range,
            command=on_temp_echo_change,
            style="Horizontal.TScale",
        )
        scale_echo.pack(fill=tk.X, pady=(4, 0))

        # Rhythm & Pacing Limit Slider
        sec_pacing = tk.Frame(modes_container, bg=BG_SURFACE, pady=6)
        sec_pacing.pack(fill=tk.X)
        lbl_pacing_hdr = tk.Frame(sec_pacing, bg=BG_SURFACE)
        lbl_pacing_hdr.pack(fill=tk.X)
        tk.Label(
            lbl_pacing_hdr,
            text="Rhythm & Pacing: Long Sentence Limit (Words)",
            bg=BG_SURFACE,
            fg=ACCENT,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(side=tk.LEFT)
        lbl_pacing_val = tk.Label(
            lbl_pacing_hdr,
            text=str(temp_pacing_limit.get()),
            bg=BG_SURFACE,
            fg=TEXT,
            font=("Segoe UI", 9, "bold"),
        )
        lbl_pacing_val.pack(side=tk.RIGHT, padx=5)

        def on_temp_pacing_change(val):
            int_val = int(float(val))
            lbl_pacing_val.config(text=str(int_val))
            temp_pacing_limit.set(int_val)

        scale_pacing = ttk.Scale(
            sec_pacing,
            from_=5,
            to=50,
            orient=tk.HORIZONTAL,
            variable=temp_pacing_limit,
            command=on_temp_pacing_change,
            style="Horizontal.TScale",
        )
        scale_pacing.pack(fill=tk.X, pady=(4, 0))

        # Sentence Architecture Ignore Dialogue Checkbox
        sec_arch = tk.Frame(modes_container, bg=BG_SURFACE, pady=6)
        sec_arch.pack(fill=tk.X)
        chk_arch = tk.Checkbutton(
            sec_arch,
            text="Sentence Architecture: Ignore Dialogue text during analysis",
            variable=temp_arch_ignore_dialogue,
            bg=BG_SURFACE,
            fg=TEXT,
            selectcolor=BG_SURFACE,
            activebackground=BG_SURFACE,
            activeforeground=TEXT,
            font=("Segoe UI", 9),
            bd=0,
            highlightthickness=0,
        )
        chk_arch.pack(anchor="w")

        # ------------------------------------------------------------- Tab 3: POV Names
        tab_pov = tk.Frame(notebook, bg=BG_SURFACE)
        notebook.add(tab_pov, text="POV Names")

        pov_panel = tk.Frame(tab_pov, bg=BG_SURFACE, padx=12, pady=12)
        pov_panel.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            pov_panel,
            text="POV Character Names (comma-separated)",
            bg=BG_SURFACE,
            fg=TEXT,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill=tk.X)

        tk.Label(
            pov_panel,
            text="Example: Nalls, Rauld, Detective",
            bg=BG_SURFACE,
            fg=TEXT_SUBTLE,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill=tk.X, pady=(2, 8))

        entry_pov_names = tk.Entry(
            pov_panel,
            textvariable=temp_pov_names,
            bg=BG,
            fg=TEXT,
            insertbackground=ACCENT,
            relief="flat",
            font=("Segoe UI", 9),
            width=42,
        )
        entry_pov_names.pack(fill=tk.X)

        # ------------------------------------------------------------- Dialog Action Buttons (Save/Cancel)
        btn_row = tk.Frame(dlg, bg=BG_SURFACE, padx=10, pady=0)
        btn_row.pack(fill=tk.X, side=tk.BOTTOM, pady=(0, 10))

        bkw = dict(
            bg=BG_OVERLAY,
            fg=TEXT,
            activebackground=ACCENT,
            activeforeground=BG,
            relief="flat",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )

        def cancel_action():
            dlg.grab_release()
            dlg.destroy()
            self._settings_dialog = None

        def save_action():
            # 1. Apply Spellchecker
            self._spellcheck_subsystem.custom_dict_words = set(temp_custom_words)
            self._spellcheck_subsystem.save_custom_dictionary()
            self._spellcheck_subsystem.reinit_spellchecker()

            # Enable spelling check if changed
            self._spellcheck_active = bool(temp_spellcheck_active.get())
            self._spellcheck_toggle_var.set(self._spellcheck_active)
            self._toggle_spellcheck()

            # 2. Apply POV choice
            new_pov = temp_pov_choice.get()
            self._pov_choice.set(new_pov)
            self._on_pov_changed()

            # 3. Apply Echo range
            new_echo = temp_echo_range.get()
            self._on_echo_range_changed(new_echo)
            self._echo_slider_var.set(new_echo)

            # 4. Apply Pacing limit
            new_pacing = temp_pacing_limit.get()
            self._on_pacing_limit_changed(new_pacing)
            self._pacing_slider_var.set(new_pacing)

            # 5. Apply Sentence Architecture ignore dialogue
            new_arch_ignore = temp_arch_ignore_dialogue.get()
            self._arch_ignore_dialogue_var.set(new_arch_ignore)
            self._on_arch_ignore_dialogue_changed()

            # 6. Apply POV names
            self._pov_names_var.set(temp_pov_names.get().strip())

            # Save to configuration JSON
            self._save_user_settings()

            cancel_action()

        tk.Button(btn_row, text="Cancel", command=cancel_action, **bkw).pack(side=tk.RIGHT)
        tk.Button(btn_row, text="Save and Close", command=save_action, **bkw).pack(side=tk.RIGHT, padx=(0, 8))

        notebook.select(initial_tab)
        entry_pov_names.bind("<Return>", lambda _e: save_action())
        dlg.bind("<Escape>", lambda _e: cancel_action())
        dlg.protocol("WM_DELETE_WINDOW", cancel_action)

        self._center_popup(dlg)

    def show_pov_names_dialog(self) -> None:
        self.show_settings_dialog(initial_tab=2)


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


    def _on_text_configure(self, _event=None) -> None:
        if self._resize_in_progress:
            return
        if self.filter_active or self._weak_mod_active or self._punct_active:
            self._request_density_redraw()
        if self._pacing_lane_visible:
            self._redraw_pacing_lane()

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
            if self._pacing_lane_visible:
                self._redraw_pacing_lane()

        # Redraw bars/dots after resize settles, but avoid expensive cache rebuilds.
        self._resize_settle_job = self.root.after(280, settle)

    def _schedule_layout_refresh(self) -> None:
        if (not self._mode_uses_density_band() and not self._punct_active) or self._is_editor_processing():
            return
        if self._layout_refresh_job is not None:
            self.root.after_cancel(self._layout_refresh_job)

        def run() -> None:
            self._layout_refresh_job = None
            if (not self._mode_uses_density_band() and not self._punct_active) or self._is_editor_processing():
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
            self.text.tag_configure("first_line_indent", lmargin1=0, lmargin2=0)

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
        try:
            row, col = self.text.index(tk.INSERT).split(".")
            self._lbl_pos.config(text=f"Ln {row}, Col {int(col) + 1}")
        except Exception:
            pass

    def _update_word_char_count(self) -> None:
        content = self.text.get("1.0", "end-1c")
        words = len(content.split()) if content.strip() else 0
        chars = len(content)
        self._lbl_words.config(text=f"Words: {words}")
        self._lbl_chars.config(text=f"Chars: {chars}")

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
            EDITOR_MODE_DTAG: [(ORANGE_FG, "Tag Lint")],
            EDITOR_MODE_EMOTION: [(RED_FG, "Emotion Word")],
            EDITOR_MODE_ECHO: [(ACCENT, "Echo Repeat")],
            EDITOR_MODE_PACING: [
                ("#4ea4ff", f"Short (<= {self._pacing_short_words})"),
                (GREEN_FG, f"Balanced (~{self._pacing_average_words})"),
                (RED_FG, f"Long (>= {self._pacing_long_words})"),
            ],
            EDITOR_MODE_CLICHE: [("#80cbc4", "Cliche")],
            EDITOR_MODE_REDUNDANCY: [("#ffee58", "Redundancy")],
            EDITOR_MODE_PASSIVE: [("#f06292", "Passive Voice")],
        }
        if self._active_editor_mode == EDITOR_MODE_ARCH:
            items = [
                ("arch_subject_first",          "#253a52", "#c6e0ff"),
                ("arch_participial_launch",     "#4f3e1a", "#ffebaf"),
                ("arch_contextual_lead",        "#3c2a57", "#e3d1ff"),
                ("arch_echoing_hinge",          "#542817", "#ffd4c0"),
                ("arch_simultaneous_setup",     "#23422a", "#d3ffd9"),
                ("arch_fragment",               "#303040", "#c0c0d8"),
            ]
            tk.Label(
                self._legend_frame,
                text="Key:",
                bg="#11111b",
                fg=TEXT_SUBTLE,
                font=("Segoe UI", 9),
                padx=4,
            ).pack(side=tk.LEFT)

            for base_tag, default_bg, default_fg in items:
                friendly = ARCH_FRIENDLY_LABELS.get(base_tag, base_tag)
                count = self._arch_counts.get(base_tag, 0)
                is_visible = self._arch_visible.get(base_tag, True)
                
                if is_visible:
                    bg_color = default_bg
                    fg_color = default_fg
                else:
                    bg_color = "#313244"
                    fg_color = "#7f849c"
                
                lbl = tk.Label(
                    self._legend_frame,
                    text=f"  {friendly} ({count})  ",
                    bg=bg_color,
                    fg=fg_color,
                    font=("Segoe UI", 8, "bold"),
                    padx=4,
                    pady=1,
                    cursor="hand2",
                    relief="solid",
                    borderwidth=1,
                )
                lbl.pack(side=tk.LEFT, padx=(4, 0))
                lbl.bind("<Button-1>", lambda event, tag=base_tag: self._toggle_arch_tag(tag))
            return

        legend_map = {
            EDITOR_MODE_FILTER: [(RED_FG, "Filter Words")],
            EDITOR_MODE_WEAK: [(ORANGE_FG, "Weak / -ly")],
            EDITOR_MODE_PUNCT: [
                (PURPLE_BG, "Quote"),
                (BLUE_FG, "Dash"),
                (WHITE_FG, "Ellipsis"),
                (RED_FG, "Loud"),
            ],
            EDITOR_MODE_DTAG: [(ORANGE_FG, "Tag Lint")],
            EDITOR_MODE_EMOTION: [(RED_FG, "Emotion Word")],
            EDITOR_MODE_ECHO: [(ACCENT, "Echo Repeat")],
            EDITOR_MODE_PACING: [
                ("#4ea4ff", f"Short (<= {self._pacing_short_words})"),
                (GREEN_FG, f"Balanced (~{self._pacing_average_words})"),
                (RED_FG, f"Long (>= {self._pacing_long_words})"),
            ],
            EDITOR_MODE_CLICHE: [("#80cbc4", "Cliche")],
            EDITOR_MODE_REDUNDANCY: [("#ffee58", "Redundancy")],
            EDITOR_MODE_PASSIVE: [("#f06292", "Passive Voice")],
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

    def open_local_help(self, anchor: str = "") -> None:
        import os
        import sys
        import webbrowser
        from pathlib import Path

        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        filename_map = {
            "": "index.html",
            "filter-words": "filter_words.html",
            "weak-modifiers": "weak_modifiers.html",
            "punctuation-mode": "punctuation_mode.html",
            "dialogue-tags": "dialogue_tags.html",
            "emotion-catcher": "emotion_catcher.html",
            "proximity-echo-radar": "proximity_echo_radar.html",
            "rhythm-and-pacing": "rhythm_and_pacing.html",
            "cliches": "cliches.html",
            "redundancies": "redundancies.html",
            "passive-voice": "passive_voice.html",
            "sentence-architecture": "sentence_architecture.html",
            "spell-checking": "spell_checking.html",
            "n-gram-scan": "n_gram_scan.html",
            "file-menu": "file_menu.html",
            "edit-menu": "edit_menu.html",
            "view-menu": "view_menu.html",
            "punctuation-menu": "punctuation_menu.html",
            "tools-menu": "tools_menu.html",
            "help-menu": "help_menu.html",
        }
        filename = filename_map.get(anchor, "index.html")
        help_path = os.path.join(base_dir, "help", filename)
        if not os.path.exists(help_path):
            self._open_url(WIKI_URL)
            return

        help_uri = Path(help_path).as_uri()
        webbrowser.open(help_uri)

    def _on_context_help_clicked(self) -> None:
        mode = self._active_editor_mode or EDITOR_MODE_OFF
        anchor_map = {
            EDITOR_MODE_OFF: "",
            EDITOR_MODE_FILTER: "filter-words",
            EDITOR_MODE_WEAK: "weak-modifiers",
            EDITOR_MODE_PUNCT: "punctuation-mode",
            EDITOR_MODE_DTAG: "dialogue-tags",
            EDITOR_MODE_EMOTION: "emotion-catcher",
            EDITOR_MODE_ECHO: "proximity-echo-radar",
            EDITOR_MODE_PACING: "rhythm-and-pacing",
            EDITOR_MODE_CLICHE: "cliches",
            EDITOR_MODE_REDUNDANCY: "redundancies",
            EDITOR_MODE_PASSIVE: "passive-voice",
            EDITOR_MODE_ARCH: "sentence-architecture",
        }
        anchor = anchor_map.get(mode, "")
        self.open_local_help(anchor)

    def open_docs(self) -> None:
        self.open_local_help("")

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
        self._redraw_lineno()

        # Schedule spellchecker
        self._schedule_spellcheck()

        if self._echo_active and not self._mode_wrapper_processing:
            self._schedule_echo_focus_refresh()
        if self._skip_filter_schedule_once:
            self._skip_filter_schedule_once = False
            return
        if self._should_schedule_filter_for_key(_event):
            self._update_word_char_count()
            self._apply_first_line_indent()
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
        if self._echo_active and not self._mode_wrapper_processing:
            self._schedule_echo_focus_refresh()


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#313244", foreground="#cdd6f4",
                         relief=tk.SOLID, borderwidth=1,
                         font=("Segoe UI", 9))
        label.pack(ipadx=4, ipady=2)

    def hide_tip(self, event=None):
        tw = self.tip
        self.tip = None
        if tw:
            tw.destroy()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    root = tk.Tk()
    EditorialApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
