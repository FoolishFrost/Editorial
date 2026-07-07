import tkinter as tk
import pytest
import math
from editorial import EditorialApp, EDITOR_MODE_PACING, EDITOR_MODE_OFF

def test_pacing_slider_integration() -> None:
    try:
        root = tk.Tk()
    except Exception as e:
        pytest.skip(f"Tcl/Tk is not available/usable in this environment: {e}")

    app = EditorialApp(root)

    # Check variables are initialized
    assert hasattr(app, "_pacing_slider_var")
    assert hasattr(app, "_pacing_slider")
    assert hasattr(app, "_pacing_slider_label")
    assert app._pacing_long_words == 19
    assert app._pacing_short_words == 4   # ceil(19 * 0.2)
    assert app._pacing_average_words == 12 # ceil(19 * 0.6)
    assert app._pacing_slider_var.get() == 19

    # Change the slider value via set
    app._pacing_slider_var.set(30)
    # Trigger callback
    app._on_pacing_limit_changed(30)

    # Verify values changed in app state (with rounding up)
    assert app._pacing_long_words == 30
    assert app._pacing_short_words == 6   # ceil(30 * 0.2)
    assert app._pacing_average_words == 18 # ceil(30 * 0.6)
    assert "Pacing Limit: 30" in app._pacing_slider_label.cget("text")

    # Verify mark update is called if Pacing mode is active
    app._active_editor_mode = EDITOR_MODE_PACING
    app._pacing_active = True
    app._pacing_slider_var.set(25)
    app._on_pacing_limit_changed(25)

    assert app._pacing_long_words == 25
    assert app._pacing_short_words == 5   # ceil(25 * 0.2)
    assert app._pacing_average_words == 15 # ceil(25 * 0.6)
    assert app._pacing_update_needed is True

    # Clean up
    root.destroy()


def test_pacing_segmentation() -> None:
    from filter_analyzer import analyze_sentence_pacing

    text = "Her voice was outraged. “Ali! You…”\nI bit off my words."

    # Analyze the pacing bands
    bands = analyze_sentence_pacing(text, short_max_words=4, average_words=12, long_min_words=19)

    # We expect 4 sentences:
    # 1. "Her voice was outraged."
    # 2. "“Ali!"
    # 3. "You…”"
    # 4. "I bit off my words."

    # Verify that the newline character '\n' is NOT included in any of the bands
    for start, end, heat, wc in bands:
        span_text = text[start:end]
        assert "\n" not in span_text, f"Span text contains newline: {repr(span_text)}"

    # We should have exactly 4 bands
    assert len(bands) == 4

