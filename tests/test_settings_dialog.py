import tkinter as tk
import pytest
import os
import json
from editorial import EditorialApp

def test_settings_dialog_integration() -> None:
    try:
        root = tk.Tk()
    except Exception as e:
        pytest.skip(f"Tcl/Tk is not available/usable in this environment: {e}")

    app = EditorialApp(root)

    # 1. Verify show_settings_dialog opens the window
    assert not hasattr(app, "_settings_dialog") or app._settings_dialog is None
    app.show_settings_dialog()
    assert app._settings_dialog is not None
    assert app._settings_dialog.winfo_exists()
    assert app._settings_notebook is not None

    # Check that initial tab was selected
    assert app._settings_notebook.index("current") == 0

    # Clean up settings dialog
    app._settings_dialog.destroy()
    app._settings_dialog = None

    # 2. Verify redirect from show_pov_names_dialog opens Settings at tab index 2
    app.show_pov_names_dialog()
    assert app._settings_dialog is not None
    assert app._settings_dialog.winfo_exists()
    assert app._settings_notebook.index("current") == 2

    # Clean up settings dialog
    app._settings_dialog.destroy()
    app._settings_dialog = None

    # 3. Test settings persistence (saving and loading)
    # Clear settings path first
    if os.path.exists(app._settings_path):
        try:
            os.remove(app._settings_path)
        except Exception:
            pass

    # Change settings
    app._pov_names_var.set("RAULD, DETECTIVE")
    app._spellcheck_active = False
    app._pov_choice.set("First Person (I/We)")
    app._echo_focus_window_words = 50
    app._pacing_long_words = 25
    app._arch_ignore_dialogue_var.set(True)

    app._save_user_settings()

    # Check JSON contains our saved values
    assert os.path.exists(app._settings_path)
    with open(app._settings_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
        assert data["pov_names"] == "RAULD, DETECTIVE"
        assert data["spelling_checker_enabled"] is False
        assert data["pov_choice"] == "First Person (I/We)"
        assert data["echo_range"] == 50
        assert data["pacing_limit"] == 25
        assert data["arch_ignore_dialogue"] is True

    # Reset and reload
    app._pov_names_var.set("")
    app._spellcheck_active = True
    app._pov_choice.set("All Pronouns (Broad Scan)")
    app._echo_focus_window_words = 80
    app._pacing_long_words = 19
    app._arch_ignore_dialogue_var.set(False)

    app._load_user_settings()

    # Verify settings are correctly loaded back
    assert app._pov_names_var.get() == "RAULD, DETECTIVE"
    assert app._spellcheck_active is False
    assert app._pov_choice.get() == "First Person (I/We)"
    assert app._echo_focus_window_words == 50
    assert app._pacing_long_words == 25
    assert app._arch_ignore_dialogue_var.get() is True

    # 4. Test that names in the POV names list are ignored by spelling checker
    # "Rauld" should be unknown/misspelled by default (it's not a standard English dictionary word)
    app._pov_names_var.set("") # Clear POV names
    misspelled_before = app._spellcheck_subsystem.check_spelling("Rauld", pov_names=app._get_all_pov_names())
    # Should find "Rauld" misspelled
    assert len(misspelled_before) == 1

    # Add "Rauld" to POV Names list
    app._add_to_pov_names("Rauld")
    assert "Rauld" in app._get_all_pov_names()

    # Verify spellchecker now ignores "Rauld"
    misspelled_after = app._spellcheck_subsystem.check_spelling("Rauld", pov_names=app._get_all_pov_names())
    assert len(misspelled_after) == 0

    # Clean up settings file
    if os.path.exists(app._settings_path):
        try:
            os.remove(app._settings_path)
        except Exception:
            pass

    root.destroy()
