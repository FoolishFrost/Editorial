import tkinter as tk
import pytest
from editorial import EditorialApp, EDITOR_MODE_ECHO, EDITOR_MODE_OFF


def test_echo_slider_integration() -> None:
    try:
        root = tk.Tk()
    except Exception as e:
        pytest.skip(f"Tcl/Tk is not available/usable in this environment: {e}")

    app = EditorialApp(root)

    # Check variables are initialized
    assert hasattr(app, "_echo_slider_var")
    assert hasattr(app, "_echo_slider")
    assert hasattr(app, "_echo_slider_label")
    assert app._echo_focus_window_words == 80
    assert app._echo_slider_var.get() == 80

    # Change the slider value via set
    app._echo_slider_var.set(30)
    # Trigger callback
    app._on_echo_range_changed(30)

    # Verify value changed in app state
    assert app._echo_focus_window_words == 30
    assert "Echo Range: 30" in app._echo_slider_label.cget("text")

    # Verify mark update is called if Echo mode is active
    app._active_editor_mode = EDITOR_MODE_ECHO
    app._echo_active = True
    app._echo_slider_var.set(15)
    app._on_echo_range_changed(15)

    assert app._echo_focus_window_words == 15
    assert app._echo_update_needed is True

    # Clean up
    root.destroy()
