"""mode_filter_words.py — Highlights sensory filter words in narration."""

from typing import Callable
from spacy_helper import _get_nlp
from dialogue_masker import _scan_dialogue, _mask_dialogue_spans, _is_in_dialogue, _token_overlaps_ignored_phrase

FILTER_LEMMAS: list[str] = [
    "see", "look", "hear", "feel", "smell", "taste", "notice", "watch",
    "observe", "realize", "think", "know", "wonder", "decide", "note",
]

POV_PRONOUNS: list[str] = ["i", "he", "she", "we", "they"]

_FILTER_SET = set(FILTER_LEMMAS)


def analyze_filter_words(
    text: str,
    pov_character_names: set[str] | None = None,
    active_pov_pronouns: list[str] | None = None,
    progress_callback: Callable[[int], None] | None = None,
) -> list[tuple[int, int, str]]:
    """Return filter-word matches as (start, end, class) tuples."""
    if not text.strip():
        if progress_callback is not None:
            progress_callback(100)
        return []

    nlp = _get_nlp()
    dialogue_spans, _quote_errors = _scan_dialogue(text)
    masked = _mask_dialogue_spans(text, dialogue_spans)
    doc = nlp(masked)

    pov_names = {n.lower() for n in (pov_character_names or set())}
    if active_pov_pronouns is None:
        active_pov = set(POV_PRONOUNS)
    else:
        active_pov = {p.lower() for p in active_pov_pronouns}
    pov_subjects = active_pov | pov_names

    hits: list[tuple[int, int, str]] = []
    span_idx = 0
    total_chars = max(1, len(text))
    last_progress = -1

    for sent in doc.sents:
        for token in sent:
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

            lemma = token.lemma_.lower()
            if lemma not in _FILTER_SET:
                continue

            if token.pos_ not in {"VERB", "AUX"}:
                continue

            if _token_overlaps_ignored_phrase(tok_start, tok_end, sent):
                continue

            subj = next(
                (child for child in token.children if child.dep_ == "nsubj" and child.head == token),
                None,
            )

            if subj is None or subj.text.lower() not in pov_subjects:
                continue

            if lemma == "feel" and any(ch.pos_ == "ADJ" for ch in token.children):
                hits.append((tok_start, tok_end, "yellow"))
            else:
                hits.append((tok_start, tok_end, "red"))

    if progress_callback is not None and last_progress < 100:
        progress_callback(100)

    return hits
