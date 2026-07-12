"""mode_passive_voice.py — Highlights passive voice constructions in narration."""

from typing import Callable
from spacy_helper import _get_nlp
from dialogue_masker import _scan_dialogue, _mask_dialogue_spans, _is_in_dialogue


def analyze_passive_voice(
    text: str,
    progress_callback: Callable[[int], None] | None = None,
) -> list[tuple[int, int, str]]:
    """Return passive voice matches as (start, end, class) tuples."""
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

            if token.dep_ == "auxpass" or (token.dep_ == "aux" and token.head.tag_ == "VBN" and token.lemma_ == "be"):
                aux_start = token.idx
                verb_end = token.head.idx + len(token.head.text)

                if aux_start < verb_end:
                    hits.append((aux_start, verb_end, "passive_voice_hit"))

    if progress_callback is not None and last_progress < 100:
        progress_callback(100)

    return sorted(set(hits), key=lambda x: x[0])
