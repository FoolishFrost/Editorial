"""search_subsystem.py — Encapsulates the Find / Replace dialog UI and search replacement logic."""

import re
import tkinter as tk
from tkinter import messagebox


class SearchSubsystem:
    """Manages Find/Replace window state and Tkinter text search operations."""

    def __init__(self, app) -> None:
        self.app = app
        self.dialog: tk.Toplevel | None = None
        self._find_var = tk.StringVar()
        self._replace_var = tk.StringVar()
        self._case_sensitive_var = tk.BooleanVar(value=False)
        self._regex_var = tk.BooleanVar(value=False)
        self._find_index = "1.0"
        self._last_find_term = ""

    def show_find_dialog(self, show_replace: bool = False) -> None:
        """Construct or focus the Find/Replace TopLevel popup."""
        from editorial_config import BG, BG_SURFACE, BG_OVERLAY, TEXT, ACCENT

        if self.dialog and self.dialog.winfo_exists():
            self.dialog.deiconify()
            self.dialog.lift()
            self.dialog.focus_force()
            self._set_replace_visibility(show_replace)
            return

        dlg = tk.Toplevel(self.app.root)
        dlg.withdraw()
        dlg.title("Find / Replace")
        dlg.configure(bg=BG_SURFACE)
        dlg.resizable(False, False)
        dlg.transient(self.app.root)
        self.dialog = dlg

        panel = tk.Frame(dlg, bg=BG_SURFACE, padx=10, pady=10)
        panel.pack(fill=tk.BOTH, expand=True)

        lkw = dict(bg=BG_SURFACE, fg=TEXT, font=("Segoe UI", 9))
        ekw = dict(bg=BG, fg=TEXT, insertbackground=ACCENT, relief="flat", width=34, font=("Segoe UI", 9))
        bkw = dict(bg=BG_OVERLAY, fg=TEXT, activebackground=ACCENT, activeforeground=BG, relief="flat", bd=0, padx=10, pady=4, cursor="hand2", font=("Segoe UI", 9))
        ckw = dict(bg=BG_SURFACE, fg=TEXT, activebackground=BG_SURFACE, activeforeground=ACCENT,
                   selectcolor=BG_OVERLAY, relief="flat", bd=0, font=("Segoe UI", 9), cursor="hand2")

        # Row 0 — Find entry
        tk.Label(panel, text="Find", **lkw).grid(row=0, column=0, sticky="w", pady=(0, 6))
        find_entry = tk.Entry(panel, textvariable=self._find_var, **ekw)
        find_entry.grid(row=0, column=1, columnspan=3, sticky="ew", padx=(8, 0), pady=(0, 6))

        # Row 1 — Options (case-sensitive + regex)
        opts_frame = tk.Frame(panel, bg=BG_SURFACE)
        opts_frame.grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 6))
        tk.Checkbutton(
            opts_frame, text="Case sensitive", variable=self._case_sensitive_var,
            command=self._reset_find_position, **ckw,
        ).pack(side=tk.LEFT, padx=(0, 12))
        tk.Checkbutton(
            opts_frame, text="Regex", variable=self._regex_var,
            command=self._reset_find_position, **ckw,
        ).pack(side=tk.LEFT)

        # Row 2 — Replace entry (hidden when show_replace=False)
        self._replace_row = tk.Frame(panel, bg=BG_SURFACE)
        self._replace_row.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(0, 8))
        tk.Label(self._replace_row, text="Replace", **lkw).grid(row=0, column=0, sticky="w")
        replace_entry = tk.Entry(self._replace_row, textvariable=self._replace_var, **ekw)
        replace_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self._replace_row.grid_columnconfigure(1, weight=1)

        # Row 3 — Buttons
        self._btn_find_next = tk.Button(panel, text="Find Next", command=self._find_next, **bkw)
        self._btn_find_next.grid(row=3, column=0, sticky="ew", pady=(0, 2))
        self._btn_replace = tk.Button(panel, text="Replace", command=self._replace_next, **bkw)
        self._btn_replace.grid(row=3, column=1, sticky="ew", padx=(6, 0), pady=(0, 2))
        self._btn_replace_all = tk.Button(panel, text="Replace All", command=self._replace_all, **bkw)
        self._btn_replace_all.grid(row=3, column=2, sticky="ew", padx=(6, 0), pady=(0, 2))
        tk.Button(panel, text="Close", command=self._close_find_dialog, **bkw).grid(
            row=3, column=3, sticky="ew", padx=(6, 0), pady=(0, 2)
        )

        panel.grid_columnconfigure(3, weight=1)

        find_entry.bind("<Return>", lambda _e: self._find_next())
        replace_entry.bind("<Return>", lambda _e: self._replace_next())
        dlg.bind("<Escape>", lambda _e: self._close_find_dialog())
        dlg.protocol("WM_DELETE_WINDOW", self._close_find_dialog)

        self._set_replace_visibility(show_replace)
        self.app._center_popup(dlg)
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
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.destroy()
        self.dialog = None

    def _clear_find_tag(self) -> None:
        self.app.text.tag_remove("find_match", "1.0", tk.END)

    def _reset_find_position(self) -> None:
        """Reset the sequential search position when search options change."""
        self._last_find_term = ""
        self._find_index = "1.0"

    # ------------------------------------------------------------------
    # Internal helpers: plain-text vs. regex search
    # ------------------------------------------------------------------

    def _search_next(self, needle: str, start_index: str) -> tuple[str, int] | None:
        """Return (tk_index, match_length) for the next occurrence of *needle*
        starting from *start_index*, respecting the case-sensitive and regex
        mode flags.  Returns None if no match is found.
        """
        use_regex = self._regex_var.get()
        case_sensitive = self._case_sensitive_var.get()

        if use_regex:
            # Regex search: fetch all text and use Python's re module.
            all_text = self.app.text.get("1.0", tk.END)
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                pattern = re.compile(needle, flags)
            except re.error:
                return None

            # Convert start_index to a character offset.
            try:
                start_offset = int(self.app.text.count("1.0", start_index, "chars")[0])
            except Exception:
                start_offset = 0

            m = pattern.search(all_text, start_offset)
            if m is None:
                return None

            # Convert character offset back to Tkinter index.
            tk_index = self.app.text.index(f"1.0 + {m.start()}c")
            return (tk_index, len(m.group(0)))
        else:
            # Plain-text search: delegate to Tkinter's fast built-in.
            nocase = not case_sensitive
            idx = self.app.text.search(needle, start_index, stopindex=tk.END, nocase=nocase)
            if not idx:
                return None
            return (idx, len(needle))

    def _search_wrap(self, needle: str, start_index: str) -> tuple[str, int] | None:
        """Like _search_next but wraps around to the beginning if no match is
        found past *start_index*.  Returns None only if there is no match in
        the entire document.
        """
        result = self._search_next(needle, start_index)
        if result is not None:
            return result
        # Wrap around from the beginning.
        return self._search_next(needle, "1.0")

    # ------------------------------------------------------------------
    # Public commands
    # ------------------------------------------------------------------

    def _find_next(self) -> None:
        needle = self._find_var.get()
        if not needle:
            return

        start = self._find_index if needle == self._last_find_term else self.app.text.index(tk.INSERT)
        result = self._search_wrap(needle, start)
        if result is None:
            self.app.root.bell()
            return

        idx, match_len = result
        end = f"{idx}+{match_len}c"
        self._clear_find_tag()
        self.app.text.tag_remove(tk.SEL, "1.0", tk.END)
        self.app.text.tag_add("find_match", idx, end)
        self.app.text.tag_add(tk.SEL, idx, end)
        self.app.text.mark_set(tk.INSERT, end)
        self.app.text.see(idx)
        self._last_find_term = needle
        self._find_index = end

    def _replace_next(self) -> None:
        needle = self._find_var.get()
        if not needle:
            return

        replaced = False
        try:
            sel_start = self.app.text.index(tk.SEL_FIRST)
            sel_end = self.app.text.index(tk.SEL_LAST)
            selected = self.app.text.get(sel_start, sel_end)
            case_sensitive = self._case_sensitive_var.get()
            matches = selected == needle if case_sensitive else selected.lower() == needle.lower()
            if matches:
                replacement = self._replace_var.get()
                self.app.text.delete(sel_start, sel_end)
                self.app.text.insert(sel_start, replacement)
                new_end = f"{sel_start}+{len(replacement)}c"
                self.app.text.tag_add(tk.SEL, sel_start, new_end)
                self.app.text.mark_set(tk.INSERT, new_end)
                self._find_index = new_end
                replaced = True
        except tk.TclError:
            pass

        if not replaced:
            self._find_next()
            return

        self.app._update_status()
        self.app._update_word_char_count()
        self.app._mark_active_mode_needs_update()
        self.app._apply_first_line_indent()
        self.app._schedule_spellcheck()
        self._find_next()

    def _replace_all(self) -> None:
        needle = self._find_var.get()
        if not needle:
            return

        replacement = self._replace_var.get()
        use_regex = self._regex_var.get()
        case_sensitive = self._case_sensitive_var.get()
        count = 0

        if use_regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                pattern = re.compile(needle, flags)
            except re.error as exc:
                messagebox.showerror("Regex Error", f"Invalid regular expression:\n{exc}")
                return
            all_text = self.app.text.get("1.0", tk.END)
            new_text, count = pattern.subn(replacement, all_text)
            if count:
                self.app.text.delete("1.0", tk.END)
                self.app.text.insert("1.0", new_text)
        else:
            start = "1.0"
            while True:
                idx = self.app.text.search(needle, start, stopindex=tk.END, nocase=not case_sensitive)
                if not idx:
                    break
                end = f"{idx}+{len(needle)}c"
                self.app.text.delete(idx, end)
                self.app.text.insert(idx, replacement)
                start = f"{idx}+{len(replacement)}c"
                count += 1

        self._clear_find_tag()
        self._find_index = "1.0"
        self._last_find_term = ""
        self.app._update_status()
        self.app._update_word_char_count()
        self.app._mark_active_mode_needs_update()
        self.app._apply_first_line_indent()
        self.app._schedule_spellcheck()
        messagebox.showinfo("Replace All", f"Replaced {count} occurrence(s).")


