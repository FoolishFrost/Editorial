"""mode_emotion_catcher.py — Spots abstract tell-not-show emotional keywords in narration."""

from typing import Callable
from spacy_helper import _get_nlp
from dialogue_masker import _scan_dialogue, _mask_dialogue_spans, _is_in_dialogue

EMOTION_WORDS: set[str] = {
    "angry", "anger", "furious", "irate", "mad", "rage", "enraged",
    "sad", "sorrow", "depressed", "miserable", "gloomy", "heartbroken",
    "terrified", "afraid", "fearful", "scared", "panic", "anxious",
    "happy", "joyful", "glad", "delighted", "elated", "cheerful",
    "jealous", "envy", "envious", "resentful",
}


def analyze_emotion_words(
    text: str,
    progress_callback: Callable[[int], None] | None = None,
) -> list[tuple[int, int, str]]:
    """Return explicit emotion-word hits as (start, end, class) tuples."""
    if not text.strip():
        if progress_callback is not None:
            progress_callback(100)
        return []

    nlp = _get_nlp()
    dialogue_spans, _quote_errors = _scan_dialogue(text)
    masked = _mask_dialogue_spans(text, dialogue_spans)
    doc = nlp(masked)

    hits: list[tuple[int, int, str]] = []
    span_idx = 0

    total_chars = max(1, len(text))
    last_progress = -1

    for token in doc:
        tok_start = token.idx
        tok_end = token.idx + len(token.text)
        if progress_callback is not None:
            pct = max(1, min(100, int((tok_end / total_chars) * 100)))
            if pct != last_progress:
                progress_callback(pct)
                last_progress = pct
        in_dialogue, span_idx = _is_in_dialogue(tok_start, tok_end, dialogue_spans, span_idx)
        if in_dialogue:
            continue
        if token.lemma_.lower() in EMOTION_WORDS:
            hits.append((tok_start, tok_end, "red"))

    if progress_callback is not None and last_progress < 100:
        progress_callback(100)

    return hits
