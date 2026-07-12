"""mode_echo_radar.py — Unified Proximity Echo Radar algorithm for highlighting word repetition."""

import re
from typing import Callable, Any
from spacy.lang.en.stop_words import STOP_WORDS

_WORD_RE = re.compile(r"[A-Za-z]+(?:['\u2019][A-Za-z]+)?")


def analyze_echo_radar(
    content: str,
    window_words: int,
    progress_callback: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    """Scans for identical word stems occurring within a moving word window sensitivity."""
    if not content.strip():
        if progress_callback is not None:
            progress_callback(100)
        return {"ranges": [], "word_counts": {}, "token_hits": [], "groups": {}}

    filler_words = {
        "um", "uh", "hmm", "ah", "oh", "okay", "ok", "like",
        "well", "just", "really", "very", "quite", "actually",
        "basically", "literally", "perhaps", "maybe",
    }
    blocked_words = {w.replace("\u2019", "'") for w in STOP_WORDS}
    blocked_words.update(filler_words)

    tokens: list[tuple[str, int, int, int]] = []
    total_chars = max(1, len(content))
    for i, m in enumerate(_WORD_RE.finditer(content)):
        word = m.group(0).lower().replace("\u2019", "'")
        clean = word.replace("'", "")
        # Filter: length >= 4, alphabetic characters, and not a stop/filler word
        if clean.isalpha() and len(clean) >= 4 and word not in blocked_words:
            tokens.append((word, m.start(), m.end(), len(tokens)))
        if progress_callback is not None and i % 250 == 0:
            progress_callback(int((m.end() / total_chars) * 55))

    if not tokens:
        if progress_callback is not None:
            progress_callback(100)
        return {"ranges": [], "word_counts": {}, "token_hits": [], "groups": {}}

    grouped: dict[str, list[tuple[int, int, int]]] = {}
    for word, start, end, token_idx in tokens:
        grouped.setdefault(word, []).append((start, end, token_idx))

    filtered_groups: dict[str, list[tuple[int, int, int]]] = {}
    word_counts: dict[str, int] = {}
    token_hits: list[tuple[str, int, int, int]] = []
    total_words = max(1, len(grouped))

    for idx, (word, occurrences) in enumerate(grouped.items()):
        if len(occurrences) < 2:
            continue
        kept: list[tuple[int, int, int]] = []
        for i, occ in enumerate(occurrences):
            prev_gap = occ[2] - occurrences[i - 1][2] if i > 0 else 999999
            next_gap = occurrences[i + 1][2] - occ[2] if i + 1 < len(occurrences) else 999999
            if min(prev_gap, next_gap) <= window_words:
                kept.append(occ)
        if len(kept) >= 2:
            filtered_groups[word] = kept
            word_counts[word] = len(kept)
            for start, end, token_idx in kept:
                token_hits.append((word, start, end, token_idx))
        if progress_callback is not None and idx % 40 == 0:
            progress_callback(55 + int((idx / total_words) * 40))

    token_hits.sort(key=lambda item: item[1])
    ranges = [(start, end) for _word, start, end, _idx in token_hits]

    if progress_callback is not None:
        progress_callback(100)

    return {
        "ranges": ranges,
        "word_counts": word_counts,
        "token_hits": token_hits,
        "groups": filtered_groups,
    }
