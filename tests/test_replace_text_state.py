import pytest
import tkinter as tk
from editorial import EditorialApp

def test_replace_text_range_preserves_state():
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("Tkinter is not available in this environment")

    app = EditorialApp(root)
    app.text.insert("1.0", "Hello world\nThis is a test of formatting options.\nLine three.")
    
    # 1. Verify first-line indent is initially applied
    app._indent_first_line_var.set(True)
    app._apply_first_line_indent()
    assert "first_line_indent" in app.text.tag_names("1.0")

    # 2. Set cursor position
    app.text.mark_set(tk.INSERT, "2.5")
    initial_cursor = app.text.index(tk.INSERT)

    # Trigger clean whitespace programmatically
    app._clean_whitespace()

    # Verify first-line indent is still applied to the text
    assert "first_line_indent" in app.text.tag_names("1.0")

    # Verify cursor position is preserved
    new_cursor = app.text.index(tk.INSERT)
    assert new_cursor == initial_cursor

    root.destroy()
