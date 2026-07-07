import pytest
from filter_analyzer import analyze_cliches, reload_cliches

def test_cliches_variation() -> None:
    reload_cliches()

    text = (
        "You should avoid like the plague. "
        "He avoided John like the plague. "
        "She was avoiding him completely like the plague. "
        "I avoided the subject like the proverbial plague. "
        "They avoided the very terrible plague."
    )

    hits = analyze_cliches(text)

    # We expect exactly 4 matches:
    # 1. "avoid like the plague"
    # 2. "avoided John like the plague"
    # 3. "avoiding him completely like the plague"
    # 4. "I avoided the subject like the proverbial plague." (matched span)

    assert len(hits) == 4

    matched_strings = [text[start:end] for start, end, _ in hits]
    assert "avoid like the plague" in matched_strings
    assert "avoided John like the plague" in matched_strings
    assert "avoiding him completely like the plague" in matched_strings
    assert "avoided the subject like the proverbial plague" in matched_strings
    assert "avoided the very terrible plague" not in matched_strings
