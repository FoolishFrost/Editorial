"""mode_weak_modifiers.py — Identifies lazy adverbs and weak qualifiers."""

from typing import Callable
from dialogue_masker import _scan_dialogue, _is_in_dialogue
from analysis_utils import _WORD_RE

WEAK_MODIFIERS: set[str] = {
    "very", "really", "just", "suddenly", "almost",
}

ADVERB_EXCLUDE: set[str] = {
    "belly", "family", "friendly", "jelly", "likely", "lily",
    "lovely", "only", "silly", "tally", "valley",
}


def analyze_weak_modifiers(
    text: str,
    progress_callback: Callable[[int], None] | None = None,
) -> list[tuple[int, int, str]]:
    """Return weak-modifier hits as (start, end, class) tuples."""
    if not text.strip():
        if progress_callback is not None:
            progress_callback(100)
        return []

    dialogue_spans, _quote_errors = _scan_dialogue(text)

    hits: list[tuple[int, int, str]] = []
    span_idx = 0
    total_chars = max(1, len(text))
    last_progress = -1

    for match in _WORD_RE.finditer(text):
        tok_start, tok_end = match.span()

        in_dialogue, span_idx = _is_in_dialogue(tok_start, tok_end, dialogue_spans, span_idx)
        if in_dialogue:
            if progress_callback is not None:
                pct = max(1, min(100, int((tok_end / total_chars) * 100)))
                if pct != last_progress:
                    progress_callback(pct)
                    last_progress = pct
            continue

        low = match.group(0).lower().replace("\u2019", "'")
        if low in WEAK_MODIFIERS:
            hits.append((tok_start, tok_end, "orange"))
        elif low.endswith("ly") and len(low) > 3 and low not in ADVERB_EXCLUDE:
            hits.append((tok_start, tok_end, "orange"))

        if progress_callback is not None:
            pct = max(1, min(100, int((tok_end / total_chars) * 100)))
            if pct != last_progress:
                progress_callback(pct)
                last_progress = pct

    if progress_callback is not None and last_progress < 100:
        progress_callback(100)

    return hits
