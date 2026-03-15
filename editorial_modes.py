from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING

from filter_analyzer import analyze_dialogue_mechanics, analyze_filter_words, analyze_weak_modifiers

if TYPE_CHECKING:
    from editorial import EditorialApp


class ModeSubsystem:
    """Mode-processing subsystem extracted from EditorialApp."""

    EXPORTED_METHODS = [
        "_clear_weak_modifiers",
        "refresh_weak_modifiers",
        "_run_weak_modifiers",
        "_complete_weak_mod_analysis",
        "_apply_weak_modifiers_progressive",
        "_finish_weak_mod_processing",
        "_build_weak_density_cache_async",
        "_finalize_weak_mod_processing",
        "_clear_dialogue_mechanics",
        "refresh_dialogue_mechanics",
        "_run_dialogue_mechanics",
        "_complete_dialogue_mechanics",
        "_apply_dialogue_mechanics_progressive",
        "_build_dialogue_dot_cache_async",
        "_finalize_dialogue_mechanics",
        "toggle_weak_modifiers",
        "toggle_filter",
        "_set_filter_processing",
        "_update_filter_btn",
        "_clear_filter",
        "_show_filter_refresh_button",
        "_hide_filter_refresh_button",
        "_mark_filter_needs_update",
        "_mark_weak_needs_update",
        "_mark_punct_needs_update",
        "_mark_active_mode_needs_update",
        "_on_filter_refresh_clicked",
        "_finish_filter_processing",
        "_finalize_filter_processing",
        "_acquire_ui_lock",
        "_release_ui_lock",
        "_apply_visible_levels_progressive",
        "_run_filter",
        "_start_filter_analysis_async",
        "_complete_filter_analysis",
        "_rebuild_filter_line_cache_async",
    ]

    def __init__(self, app: "EditorialApp") -> None:
        object.__setattr__(self, "app", app)

    def __getattr__(self, name: str):
        return getattr(self.app, name)

    def __setattr__(self, name: str, value) -> None:
        if name == "app":
            object.__setattr__(self, name, value)
        else:
            setattr(self.app, name, value)

    def _clear_weak_modifiers(self) -> None:
        self.text.tag_remove("filter_orange", "1.0", tk.END)
        self._weak_mod_hits = []
        self._weak_hit_fracs = []

    def refresh_weak_modifiers(self) -> None:
        if not self._weak_mod_active or self._weak_mod_processing:
            return
        self._run_weak_modifiers()

    def _run_weak_modifiers(self) -> None:
        if not self._weak_mod_active or self._weak_mod_processing:
            return

        self._weak_mod_processing = True
        self._weak_mod_run_seq += 1
        run_id = self._weak_mod_run_seq
        self._acquire_ui_lock()
        self._set_editor_progress(2, "Weak")
        self._lbl_filter.config(text="Weak modifiers - analyzing...")

        content = self.text.get("1.0", "end-1c")
        self._clear_weak_modifiers()

        def worker() -> None:
            try:
                def on_scan_progress(raw_pct: int) -> None:
                    ui_pct = 2 + int((max(0, min(100, raw_pct)) / 100) * 52)
                    self.root.after(0, lambda p=ui_pct: self._set_editor_progress(p, "Weak"))

                hits = analyze_weak_modifiers(content, progress_callback=on_scan_progress)
                self.root.after(0, lambda: self._complete_weak_mod_analysis(run_id, hits, None))
            except Exception as exc:
                self.root.after(0, lambda: self._complete_weak_mod_analysis(run_id, None, exc))

        threading.Thread(target=worker, daemon=True).start()

    def _complete_weak_mod_analysis(
        self,
        run_id: int,
        hits: list[tuple[int, int, str]] | None,
        error: Exception | None,
    ) -> None:
        if run_id != self._weak_mod_run_seq:
            return

        if error is not None:
            self._weak_mod_processing = False
            self._weak_mod_active = False
            self._set_editor_progress(None, "")
            self._release_ui_lock()
            self._lbl_filter.config(text="")
            self.set_editor_mode("off")
            messagebox.showerror("Weak Modifier Error", str(error))
            return

        resolved_hits = hits or []
        self._set_editor_progress(55, "Weak")
        self._apply_weak_modifiers_progressive(run_id, resolved_hits)

    def _apply_weak_modifiers_progressive(
        self,
        run_id: int,
        hits: list[tuple[int, int, str]],
    ) -> None:
        total = len(hits)
        if total == 0:
            self._weak_mod_hits = []
            self._finish_weak_mod_processing(run_id)
            return

        self._weak_mod_hits = []
        step = 500
        idx = 0

        def run_chunk() -> None:
            nonlocal idx
            if run_id != self._weak_mod_run_seq:
                return

            end = min(idx + step, total)
            for ws, we, _cls in hits[idx:end]:
                self.text.tag_add("filter_orange", f"1.0 + {ws}c", f"1.0 + {we}c")
                self._weak_mod_hits.append((ws, we))
            idx = end

            pct = 55 + int((idx / total) * 43)
            self._set_editor_progress(pct, "Weak")
            if idx < total:
                self.root.after(1, run_chunk)
            else:
                self._finish_weak_mod_processing(run_id)

        run_chunk()

    def _finish_weak_mod_processing(self, run_id: int) -> None:
        self._build_weak_density_cache_async(run_id, lambda: self._finalize_weak_mod_processing(run_id))

    def _build_weak_density_cache_async(self, run_id: int, done_callback) -> None:
        total = len(self._weak_mod_hits)
        self._weak_hit_fracs = []
        if total == 0:
            self._set_editor_progress(100, "Weak")
            self.root.after(1, done_callback)
            return

        total_chars = max(1, self._text_char_length())
        idx = 0
        step = 400

        def run_chunk() -> None:
            nonlocal idx
            if run_id != self._weak_mod_run_seq:
                return
            end = min(total, idx + step)
            for ws, we in self._weak_mod_hits[idx:end]:
                mid = (ws + we) // 2
                self._weak_hit_fracs.append(max(0.0, min(0.999999, mid / total_chars)))
            idx = end
            pct = 85 + int((idx / total) * 15)
            self._set_editor_progress(pct, "Weak")
            if self._density_visible:
                self._request_density_redraw()
            if idx < total:
                self.root.after(1, run_chunk)
            else:
                done_callback()

        run_chunk()

    def _finalize_weak_mod_processing(self, run_id: int) -> None:
        if run_id != self._weak_mod_run_seq:
            return
        self._weak_mod_processing = False
        self._set_editor_progress(100, "Weak")
        self._lbl_filter.config(text=f"Weak modifiers - {len(self._weak_mod_hits)} highlighted")
        self._request_density_redraw()
        self.root.after(120, lambda: self._set_editor_progress(None, ""))
        self._release_ui_lock()

    def _clear_dialogue_mechanics(self) -> None:
        for tag in ("punct_quote", "punct_dash", "punct_ellipsis", "punct_loud"):
            self.text.tag_remove(tag, "1.0", tk.END)
        for key in self._punct_hits:
            self._punct_hits[key] = []
            self._punct_dot_fracs[key] = []

    def refresh_dialogue_mechanics(self) -> None:
        if not self._punct_active or self._punct_processing:
            return
        self._run_dialogue_mechanics()

    def _run_dialogue_mechanics(self) -> None:
        if not self._punct_active or self._punct_processing:
            return

        self._punct_processing = True
        self._punct_run_seq += 1
        run_id = self._punct_run_seq
        self._acquire_ui_lock()
        self._set_editor_progress(2, "Punct")
        self._lbl_filter.config(text="Punctuation/dialogue - analyzing...")
        content = self.text.get("1.0", "end-1c")
        self._clear_dialogue_mechanics()

        def worker() -> None:
            try:
                hits = analyze_dialogue_mechanics(content)
                self.root.after(0, lambda: self._complete_dialogue_mechanics(run_id, hits, None))
            except Exception as exc:
                self.root.after(0, lambda: self._complete_dialogue_mechanics(run_id, None, exc))

        threading.Thread(target=worker, daemon=True).start()

    def _complete_dialogue_mechanics(
        self,
        run_id: int,
        hits: list[tuple[int, int, str]] | None,
        error: Exception | None,
    ) -> None:
        if run_id != self._punct_run_seq:
            return

        if error is not None:
            self._punct_processing = False
            self._punct_active = False
            self._set_editor_progress(None, "")
            self._release_ui_lock()
            self._lbl_filter.config(text="")
            self.set_editor_mode("off")
            messagebox.showerror("Punctuation/Dialogue Error", str(error))
            return

        grouped: dict[str, list[tuple[int, int]]] = {
            "quote": [],
            "dash": [],
            "ellipsis": [],
            "loud": [],
        }
        for ws, we, cls in hits or []:
            if cls in grouped:
                grouped[cls].append((ws, we))
        self._punct_hits = grouped
        self._set_editor_progress(55, "Punct")
        self._apply_dialogue_mechanics_progressive(run_id)

    def _apply_dialogue_mechanics_progressive(self, run_id: int) -> None:
        ops: list[tuple[str, int, int]] = []
        tag_map = {
            "quote": "punct_quote",
            "dash": "punct_dash",
            "ellipsis": "punct_ellipsis",
            "loud": "punct_loud",
        }
        for cls, ranges in self._punct_hits.items():
            for ws, we in ranges:
                ops.append((tag_map[cls], ws, we))
        total = len(ops)
        if total == 0:
            self._build_dialogue_dot_cache_async(run_id, lambda: self._finalize_dialogue_mechanics(run_id))
            return

        idx = 0
        step = 400

        def run_chunk() -> None:
            nonlocal idx
            if run_id != self._punct_run_seq:
                return
            end = min(total, idx + step)
            for tag, ws, we in ops[idx:end]:
                self.text.tag_add(tag, f"1.0 + {ws}c", f"1.0 + {we}c")
            idx = end
            pct = 55 + int((idx / total) * 30)
            self._set_editor_progress(pct, "Punct")
            if idx < total:
                self.root.after(1, run_chunk)
            else:
                self._build_dialogue_dot_cache_async(run_id, lambda: self._finalize_dialogue_mechanics(run_id))

        run_chunk()

    def _build_dialogue_dot_cache_async(self, run_id: int, done_callback) -> None:
        all_hits = sum((len(ranges) for ranges in self._punct_hits.values()), 0)
        if all_hits == 0:
            self.root.after(1, done_callback)
            return

        try:
            total_display_lines = int(self.text.count("1.0", "end-1c", "displaylines")[0])
        except Exception:
            total_display_lines = 1
        total_display_lines = max(1, total_display_lines)

        for key in self._punct_dot_fracs:
            self._punct_dot_fracs[key] = []

        ops: list[tuple[str, int, int]] = []
        for cls, ranges in self._punct_hits.items():
            for ws, we in ranges:
                ops.append((cls, ws, we))
        ops.sort(key=lambda x: (x[1] + x[2]) // 2)

        idx = 0
        step = 400
        total = len(ops)
        prev_idx_str = "1.0"
        prev_disp = 0

        def run_chunk() -> None:
            nonlocal idx, prev_idx_str, prev_disp
            if run_id != self._punct_run_seq:
                return
            end = min(total, idx + step)
            for cls, ws, we in ops[idx:end]:
                mid = (ws + we) // 2
                try:
                    idx_str = self.text.index(f"1.0 + {mid}c")
                    delta = int(self.text.count(prev_idx_str, idx_str, "displaylines")[0])
                    disp = prev_disp + max(0, delta)
                except Exception:
                    try:
                        idx_str = self.text.index(f"1.0 + {mid}c")
                        disp = int(self.text.count("1.0", idx_str, "displaylines")[0])
                    except Exception:
                        continue

                prev_idx_str = idx_str
                prev_disp = disp
                frac = max(0.0, min(0.999999, disp / total_display_lines))
                self._punct_dot_fracs[cls].append(frac)
            idx = end
            pct = 86 + int((idx / total) * 14)
            self._set_editor_progress(pct, "Punct")
            self._request_density_redraw()
            if idx < total:
                self.root.after(1, run_chunk)
            else:
                done_callback()

        run_chunk()

    def _finalize_dialogue_mechanics(self, run_id: int) -> None:
        if run_id != self._punct_run_seq:
            return
        self._punct_processing = False
        total = sum((len(v) for v in self._punct_hits.values()), 0)
        self._set_editor_progress(100, "Punct")
        self._lbl_filter.config(text=f"Punctuation/dialogue - {total} highlighted")
        self._request_density_redraw()
        self.root.after(120, lambda: self._set_editor_progress(None, ""))
        self._release_ui_lock()

    def toggle_weak_modifiers(self) -> None:
        next_mode = "off" if self._active_editor_mode == "weak_modifiers" else "weak_modifiers"
        self.set_editor_mode(next_mode)

    def toggle_filter(self) -> None:
        next_mode = "off" if self._active_editor_mode == "filter_words" else "filter_words"
        self.set_editor_mode(next_mode)

    def _set_filter_processing(self, percent: int) -> None:
        pct = max(0, min(100, int(percent)))
        if self._filter_processing and self._editor_progress_pct is not None and pct < self._editor_progress_pct:
            pct = self._editor_progress_pct
        self._set_editor_progress(pct, "Filter")

    def _update_filter_btn(self) -> None:
        self._sync_editor_mode_ui()

    def _clear_filter(self) -> None:
        for tag in ("filter_red", "filter_purple"):
            self.text.tag_remove(tag, "1.0", tk.END)
        self._filter_hits = {"red": [], "purple": []}
        self._filter_hits_lines = {"red": [], "purple": []}
        self._filter_hit_fracs = {"red": [], "purple": []}
        if hasattr(self, "_quote_dots"):
            self._quote_dots.delete("all")

    def _show_filter_refresh_button(self) -> None:
        if self._active_editor_mode == "off":
            return
        if self._filter_refresh_btn.winfo_manager():
            return
        self._filter_refresh_btn.pack(side=tk.LEFT, padx=(2, 8), after=self._mode_combo)

    def _hide_filter_refresh_button(self) -> None:
        if self._filter_refresh_btn.winfo_manager():
            self._filter_refresh_btn.pack_forget()

    def _mark_filter_needs_update(self) -> None:
        if not self.filter_active:
            return
        self._filter_update_needed = True
        self._show_filter_refresh_button()
        self._lbl_filter.config(text="Filter - changes pending (click Refresh)")

    def _mark_weak_needs_update(self) -> None:
        if not self._weak_mod_active:
            return
        self._weak_update_needed = True
        self._show_filter_refresh_button()
        self._lbl_filter.config(text="Weak modifiers - changes pending (click Refresh)")

    def _mark_punct_needs_update(self) -> None:
        if not self._punct_active:
            return
        self._punct_update_needed = True
        self._show_filter_refresh_button()
        self._lbl_filter.config(text="Punctuation/dialogue - changes pending (click Refresh)")

    def _mark_active_mode_needs_update(self) -> None:
        if self.filter_active:
            self._mark_filter_needs_update()
        elif self._weak_mod_active:
            self._mark_weak_needs_update()
        elif self._punct_active:
            self._mark_punct_needs_update()

    def _on_filter_refresh_clicked(self) -> None:
        if self._is_editor_processing():
            return
        self._hide_filter_refresh_button()
        if self.filter_active:
            self._filter_update_needed = False
            self._run_filter()
            return
        if self._weak_mod_active:
            self._weak_update_needed = False
            self._run_weak_modifiers()
            return
        if self._punct_active:
            self._punct_update_needed = False
            self._run_dialogue_mechanics()

    def _finish_filter_processing(self) -> None:
        if self._needs_cache_rebuild:
            self._set_filter_processing(85)
            self._rebuild_filter_line_cache_async(self._finalize_filter_processing, show_progress=True)
            return
        self._finalize_filter_processing()

    def _finalize_filter_processing(self) -> None:
        self._filter_processing = False
        self._needs_cache_rebuild = False
        if self.filter_active:
            self._update_filter_btn()
        self._set_filter_processing(100)
        self._request_density_redraw()
        self.root.after(120, lambda: self._set_editor_progress(None, ""))
        self._release_ui_lock()

    def _acquire_ui_lock(self) -> None:
        self._ui_lock_count += 1
        if self._ui_lock_count > 1:
            return

        self._ui_locked_controls.clear()
        controls: list[tk.Widget] = [
            self._mode_combo,
            self._filter_refresh_btn,
            self._pov_combo,
            self._ngram_btn,
            self._analysis_close,
        ]
        for widget in controls:
            try:
                state = str(widget.cget("state"))
                self._ui_locked_controls.append((widget, state))
                widget.config(state="disabled")
            except Exception:
                continue

        try:
            self._text_locked_prev_state = str(self.text.cget("state"))
            self.text.config(state="disabled")
        except Exception:
            self._text_locked_prev_state = "normal"

        if not self._ui_menu_locked:
            for menu in getattr(self, "_menus", []):
                try:
                    end = menu.index("end")
                    if end is None:
                        continue
                    for idx in range(end + 1):
                        menu.entryconfig(idx, state="disabled")
                except Exception:
                    continue
            self._ui_menu_locked = True

    def _release_ui_lock(self) -> None:
        if self._ui_lock_count <= 0:
            self._ui_lock_count = 0
            return

        self._ui_lock_count -= 1
        if self._ui_lock_count > 0:
            return

        for widget, state in self._ui_locked_controls:
            try:
                widget.config(state=state)
            except Exception:
                continue
        self._ui_locked_controls.clear()

        try:
            self.text.config(state=self._text_locked_prev_state)
        except Exception:
            pass

        if self._ui_menu_locked:
            for menu in getattr(self, "_menus", []):
                try:
                    end = menu.index("end")
                    if end is None:
                        continue
                    for idx in range(end + 1):
                        menu.entryconfig(idx, state="normal")
                except Exception:
                    continue
            self._ui_menu_locked = False

    def _apply_visible_levels_progressive(self, done_callback) -> None:
        ops: list[tuple[str, int, int]] = []
        for level, ranges in self._filter_hits.items():
            for ws, we in ranges:
                ops.append((f"filter_{level}", ws, we))

        total = len(ops)
        if total == 0:
            self._set_filter_processing(100)
            self.root.after(1, done_callback)
            return

        step = 250
        idx = 0

        def run_chunk() -> None:
            nonlocal idx
            end = min(idx + step, total)
            for tag, ws, we in ops[idx:end]:
                self.text.tag_add(tag, f"1.0 + {ws}c", f"1.0 + {we}c")
            idx = end
            pct = 56 + int((idx / total) * 28)
            self._set_filter_processing(pct)
            if self._density_visible:
                self._request_density_redraw()
            if idx < total:
                self.root.after(1, run_chunk)
            else:
                done_callback()

        run_chunk()

    def _run_filter(self) -> None:
        if not self.filter_active:
            return
        if self._filter_processing:
            return

        self._filter_update_needed = False
        self._hide_filter_refresh_button()
        self._acquire_ui_lock()
        self._filter_processing = True
        self._needs_cache_rebuild = True
        self._filter_run_seq += 1
        run_id = self._filter_run_seq
        self._set_filter_processing(2)
        self._lbl_filter.config(text="Filter - analyzing...")
        self._start_filter_bootstrap_progress(run_id)
        self._clear_filter()
        content = self.text.get("1.0", tk.END)
        active_pov = self._get_active_pov_pronouns()
        pov_names = self._get_active_pov_names()
        self._start_filter_analysis_async(run_id, content, active_pov, pov_names)

    def _start_filter_analysis_async(
        self,
        run_id: int,
        content: str,
        active_pov: list[str],
        pov_names: set[str],
    ) -> None:
        def worker() -> None:
            try:
                def on_scan_progress(raw_pct: int) -> None:
                    ui_pct = 2 + int((max(0, min(100, raw_pct)) / 100) * 52)
                    self.root.after(0, lambda p=ui_pct: self._set_filter_processing(p))

                raw_hits = analyze_filter_words(
                    content,
                    pov_character_names=pov_names,
                    active_pov_pronouns=active_pov,
                    progress_callback=on_scan_progress,
                )
                grouped: dict[str, list[tuple[int, int]]] = {"red": [], "purple": []}
                for ws, we, cls in raw_hits:
                    if cls == "yellow":
                        cls = "red"
                    if cls in grouped:
                        grouped[cls].append((ws, we))
                counts = {
                    "red": len(grouped["red"]),
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
            self.filter_active = False
            self._hide_filter_refresh_button()
            self._hide_quote_band()
            self._hide_density_band()
            self.set_editor_mode("off")
            self._set_editor_progress(None, "")
            self._lbl_filter.config(text="")
            self._release_ui_lock()
            messagebox.showerror("Filter Analyzer Error", str(error))
            return

        self._filter_hits = grouped
        self._set_filter_processing(55)

        self._lbl_filter.config(
            text=(
                f"Filter -  ● {counts['red']} Filter Words"
            )
        )
        self._apply_visible_levels_progressive(self._finish_filter_processing)

    def _rebuild_filter_line_cache_async(self, done_callback, show_progress: bool = False) -> None:
        self._cache_build_seq += 1
        build_seq = self._cache_build_seq

        levels = ["red", "purple"]
        self._filter_hits_lines = {"red": [], "purple": []}
        self._filter_hit_fracs = {"red": [], "purple": []}

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
        step = 200
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
                pct = 86 + int((idx / total) * 12)
                self._set_filter_processing(pct)
            if self._density_visible:
                self._request_density_redraw()
            if idx < total:
                self.root.after(1, run_chunk)
            else:
                done_callback()

        run_chunk()
