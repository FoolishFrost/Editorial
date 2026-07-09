import tkinter as tk
import pytest
from editorial import EditorialApp, EDITOR_MODE_OFF, EDITOR_MODE_FILTER


def test_ngram_selection_and_highlighting() -> None:
    try:
        root = tk.Tk()
    except Exception as e:
        pytest.skip(f"Tcl/Tk is not available/usable in this environment: {e}")

    app = EditorialApp(root)

    # Put some text in the text widget
    app.text.insert("1.0", "The big red house is a big red house.")

    # Populate tree tables manually to simulate a scan
    app._single_tree.insert("", "end", values=("house", "2"))
    app._pairs_tree.insert("", "end", values=("big red", "2"))
    app._triples_tree.insert("", "end", values=("big red house", "2"))
    app._ngram_matches = {
        "house": [(8, 13), (31, 36)],
        "big red": [(4, 11), (23, 30)],
        "big red house": [(4, 17), (23, 36)],
    }

    # Verify initial state
    assert app._selected_ngram is None
    assert len(app._ngram_hit_fracs) == 0

    # Simulate selecting "big red" in pairs_tree
    pair_item = app._pairs_tree.get_children()[0]
    app._pairs_tree.selection_set(pair_item)
    
    # Manually trigger <<TreeviewSelect>> binding via event
    class DummyEvent:
        widget = app._pairs_tree
    app._on_ngram_select(DummyEvent())

    # Check selections cleared on other trees
    assert len(app._single_tree.selection()) == 0
    assert len(app._triples_tree.selection()) == 0
    assert app._pairs_tree.selection() == (pair_item,)

    # Verify state updated
    assert app._selected_ngram == "big red"
    assert app._active_editor_mode == EDITOR_MODE_OFF

    # Check tags added in the text widget
    ranges = app.text.tag_ranges("ngram_hit")
    assert len(ranges) > 0  # Should have matching ranges

    # Check density map update
    assert len(app._ngram_hit_fracs) > 0
    assert app._density_visible is True

    # Select single word "house" in single_tree
    single_item = app._single_tree.get_children()[0]
    app._single_tree.selection_set(single_item)
    DummyEvent.widget = app._single_tree
    app._on_ngram_select(DummyEvent())

    # Check selections cleared on pairs_tree
    assert len(app._pairs_tree.selection()) == 0
    assert app._single_tree.selection() == (single_item,)
    assert app._selected_ngram == "house"

    # Select another editor mode (e.g. filter)
    app._run_filter = lambda: None
    app.set_editor_mode(EDITOR_MODE_FILTER)
    
    # N-gram highlights should be cleared, selection should be cleared, but N-gram panel stays open
    assert app._selected_ngram is None
    assert len(app.text.tag_ranges("ngram_hit")) == 0
    assert len(app._single_tree.selection()) == 0

    # Clean up
    root.destroy()
