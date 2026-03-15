from __future__ import annotations

import math
from typing import Any


class IndicatorSubsystem:
    """Owns indicator band rendering/interaction for the editor UI."""

    def __init__(self, app: Any, colors: dict[str, str]) -> None:
        self.app = app
        self.colors = colors

    def show_density_band(self) -> None:
        if self.app._density_visible:
            return
        anchor = self.app._quote_dots if self.app._quote_band_visible else self.app._lineno
        self.app._density.pack(side="left", fill="y", before=anchor)
        self.app._density_visible = True
        self.request_density_redraw()

    def hide_density_band(self) -> None:
        if not self.app._density_visible:
            return
        self.app._density.pack_forget()
        self.app._density_visible = False
        self.app._density_viewport_id = None
        self.app._density_viewport_canvas = None

    def on_density_configure(self, _event=None) -> None:
        self.request_density_redraw()

    def on_density_click(self, event) -> None:
        if not (self.app.filter_active or self.app._weak_mod_active):
            return
        h = max(2, self.app._density.winfo_height())
        frac = max(0.0, min(1.0, event.y / (h - 1)))
        self.center_text_on_fraction(frac)
        self.app._redraw_lineno()
        self.update_density_viewport()

    def on_density_drag(self, event) -> None:
        if not (self.app.filter_active or self.app._weak_mod_active):
            return
        h = max(2, self.app._density.winfo_height())
        frac = max(0.0, min(1.0, event.y / (h - 1)))
        self.scroll_text_to_fraction(frac)
        self.app._redraw_lineno()
        self.update_density_viewport()

    def show_quote_band(self) -> None:
        if self.app._quote_band_visible:
            return
        self.app._quote_dots.pack(side="left", fill="y", before=self.app._lineno)
        self.app._quote_band_visible = True
        if self.app._density_visible:
            self.app._density.pack_forget()
            self.app._density.pack(side="left", fill="y", before=self.app._quote_dots)
        self.request_density_redraw()

    def hide_quote_band(self) -> None:
        if not self.app._quote_band_visible:
            return
        self.app._quote_dots.pack_forget()
        self.app._quote_band_visible = False
        self.app._quote_dots.delete("all")
        self.app._density_viewport_id = None
        self.app._density_viewport_canvas = None

    def on_quote_band_click(self, event) -> None:
        if not (self.app.filter_active or self.app._punct_active):
            return
        h = max(2, self.app._quote_dots.winfo_height())
        frac = max(0.0, min(1.0, event.y / (h - 1)))
        self.center_text_on_fraction(frac)
        self.app._redraw_lineno()
        self.update_density_viewport()

    def on_quote_band_drag(self, event) -> None:
        if not (self.app.filter_active or self.app._punct_active):
            return
        h = max(2, self.app._quote_dots.winfo_height())
        frac = max(0.0, min(1.0, event.y / (h - 1)))
        self.scroll_text_to_fraction(frac)
        self.app._redraw_lineno()
        self.update_density_viewport()

    def center_text_on_fraction(self, frac: float) -> None:
        first, last = self.app.text.yview()
        span = max(0.01, last - first)
        top = max(0.0, min(1.0 - span, frac - (span / 2)))
        self.app.text.yview_moveto(top)

    def scroll_text_to_fraction(self, frac: float) -> None:
        self.app.text.yview_moveto(max(0.0, min(1.0, frac)))

    def request_density_redraw(self) -> None:
        self.app._density_static_dirty = True
        if self.app._density_draw_pending:
            return
        self.app._density_draw_pending = True

        def go() -> None:
            self.app._density_draw_pending = False
            self.redraw_density_band_static()
            self.update_density_viewport()

        self.app.root.after(16, go)

    def update_density_viewport(self) -> None:
        if not (self.app.filter_active or self.app._weak_mod_active or self.app._punct_active):
            return
        if self.app._density_viewport_pending:
            return
        self.app._density_viewport_pending = True

        def go() -> None:
            self.app._density_viewport_pending = False
            if self.app._density_visible:
                canvas = self.app._density
            elif self.app._quote_band_visible:
                canvas = self.app._quote_dots
            else:
                return

            width = max(8, canvas.winfo_width())
            height = max(20, canvas.winfo_height())
            first, last = self.app.text.yview()
            y1 = int(first * height)
            y2 = max(y1 + 6, int(last * height))
            if self.app._density_viewport_canvas is not canvas:
                self.app._density_viewport_id = None
                self.app._density_viewport_canvas = canvas
            if self.app._density_viewport_id is None:
                self.app._density_viewport_id = canvas.create_rectangle(
                    0, y1, width - 1, y2, outline=self.colors["ACCENT"], width=1
                )
            else:
                canvas.coords(self.app._density_viewport_id, 0, y1, width - 1, y2)
                canvas.tag_raise(self.app._density_viewport_id)

        self.app.root.after(16, go)

    def redraw_density_band_static(self) -> None:
        if not self.app._density_static_dirty:
            return
        self.app._density_static_dirty = False
        self.app._density.delete("all")
        self.app._density_viewport_id = None
        self.app._density_viewport_canvas = None
        self.app._quote_dots.delete("all")
        if not (self.app.filter_active or self.app._weak_mod_active or self.app._punct_active):
            return

        if self.app._density_visible:
            width = max(20, self.app._density.winfo_width())
            height = max(20, self.app._density.winfo_height())

            first, last = self.app.text.yview()
            span = max(0.01, last - first)
            pages = max(1, int(math.ceil(1.0 / span)))

            mode_key = "red" if self.app.filter_active else "orange"
            page_counts: list[dict[str, int]] = [{mode_key: 0} for _ in range(pages)]

            if self.app.filter_active:
                if not any(self.app._filter_hit_fracs.values()) and any(self.app._filter_hits.values()):
                    total_chars = max(1, self.app._text_char_length())
                    for level in ("red", "purple"):
                        fracs: list[float] = []
                        for ws, we in self.app._filter_hits.get(level, []):
                            mid = (ws + we) // 2
                            fracs.append(max(0.0, min(0.999999, mid / total_chars)))
                        self.app._filter_hit_fracs[level] = fracs

                for frac in self.app._filter_hit_fracs.get("red", []):
                    page_idx = min(pages - 1, max(0, int(frac * pages)))
                    page_counts[page_idx]["red"] += 1
            else:
                for frac in self.app._weak_hit_fracs:
                    page_idx = min(pages - 1, max(0, int(frac * pages)))
                    page_counts[page_idx]["orange"] += 1

            max_total = max((sum(p.values()) for p in page_counts), default=0)
            avail_w = max(1, width - 2)

            for i, counts in enumerate(page_counts):
                y1 = int((i * height) / pages)
                y2 = max(y1 + 1, int(((i + 1) * height) / pages))

                total = counts[mode_key]
                if total <= 0 or max_total <= 0:
                    continue

                row_w = max(1, int((total / max_total) * avail_w))
                fill_color = self.colors["RED_FG"] if self.app.filter_active else self.colors["ORANGE_FG"]
                self.app._density.create_rectangle(1, y1, 1 + row_w, y2, fill=fill_color, outline="")

        if self.app._quote_band_visible:
            qwidth = max(8, self.app._quote_dots.winfo_width())
            qheight = max(20, self.app._quote_dots.winfo_height())
            radius = max(2, min(3, qwidth // 3))
            cx = qwidth // 2

            if self.app.filter_active:
                for frac in self.app._filter_hit_fracs.get("purple", []):
                    cy = max(radius, min(qheight - radius, int(frac * qheight)))
                    self.app._quote_dots.create_oval(
                        cx - radius,
                        cy - radius,
                        cx + radius,
                        cy + radius,
                        fill=self.colors["PURPLE_BG"],
                        outline="",
                    )
            elif self.app._punct_active:
                punct_colors = {
                    "quote": self.colors["PURPLE_BG"],
                    "dash": self.colors["BLUE_FG"],
                    "ellipsis": self.colors["WHITE_FG"],
                    "loud": self.colors["RED_FG"],
                }
                punct_columns = ["quote", "dash", "ellipsis", "loud"]
                usable_width = max(8, qwidth - 2)
                for idx, cls in enumerate(punct_columns):
                    left = 1 + int((idx * usable_width) / len(punct_columns))
                    right = 1 + int(((idx + 1) * usable_width) / len(punct_columns))
                    col_center = max(radius + 1, min(qwidth - radius - 1, (left + right) // 2))
                    if idx > 0:
                        self.app._quote_dots.create_line(left, 0, left, qheight, fill=self.colors["BG_OVERLAY"])
                    color = punct_colors.get(cls, self.colors["ACCENT"])
                    for frac in self.app._punct_dot_fracs.get(cls, []):
                        cy = max(radius, min(qheight - radius, int(frac * qheight)))
                        self.app._quote_dots.create_oval(
                            col_center - radius,
                            cy - radius,
                            col_center + radius,
                            cy + radius,
                            fill=color,
                            outline="",
                        )
