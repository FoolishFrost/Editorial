"""ngram_subsystem.py — Logic for scanning and extracting single, pair, and triple n-grams."""

import re
from collections import Counter
from typing import Callable, Any
from spacy.lang.en.stop_words import STOP_WORDS


def calculate_ngrams(
    text: str,
    set_progress_callback: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    """Calculate top 10 single, pair, and triple word ngrams and build matches map."""
    token_re = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

    # Standard NLP practice: remove function/stop words and short fillers
    filler_words = {
        "um", "uh", "hmm", "ah", "oh", "okay", "ok", "like",
        "well", "just", "really", "very", "quite", "actually",
        "basically", "literally", "perhaps", "maybe",
    }
    blocked_words = {w.replace("\u2019", "'") for w in STOP_WORDS}
    blocked_words.update(filler_words)

    # Normalize smart apostrophes so contractions stay intact.
    ngram_text = text.lower().replace("\u2019", "'")
    raw_tokens = [m.group(0) for m in token_re.finditer(ngram_text)]
    tokens = [
        tok for tok in raw_tokens
        if tok.replace("'", "").isalpha() and len(tok) > 1 and tok not in blocked_words
    ]
    total = len(tokens)
    if total == 0:
        if set_progress_callback is not None:
            set_progress_callback(100)
        return {"single": [], "pairs": [], "triples": [], "matches": {}}

    if set_progress_callback is not None:
        set_progress_callback(10)

    uni: Counter[str] = Counter(tokens)

    if set_progress_callback is not None:
        set_progress_callback(45)

    bi: Counter[tuple[str, str]] = Counter(zip(tokens, tokens[1:]))

    if set_progress_callback is not None:
        set_progress_callback(75)

    tri: Counter[tuple[str, str, str]] = Counter(zip(tokens, tokens[1:], tokens[2:]))

    top_single = [(w, c) for w, c in uni.most_common(10)]
    top_pairs = [(" ".join(k), c) for k, c in bi.most_common(10)]
    top_triples = [(" ".join(k), c) for k, c in tri.most_common(10)]

    # Pre-collect match objects to map tokens to spans
    filtered_matches = [
        m for m in token_re.finditer(ngram_text)
        if (tok := m.group(0)).replace("'", "").isalpha() and len(tok) > 1 and tok not in blocked_words
    ]

    # Build matches map for top 30
    matches_map: dict[str, list[tuple[int, int]]] = {}

    # Single words
    top_single_set = {w for w, _ in top_single}
    for w in top_single_set:
        matches_map[w] = []
    for i, m in enumerate(filtered_matches):
        w = tokens[i]
        if w in top_single_set:
            matches_map[w].append((m.start(), m.end()))

    # Word pairs
    top_pairs_keys = {k for k, _ in bi.most_common(10)}
    for k in top_pairs_keys:
        matches_map[" ".join(k)] = []
    for i in range(len(tokens) - 1):
        k = (tokens[i], tokens[i+1])
        if k in top_pairs_keys:
            matches_map[" ".join(k)].append((filtered_matches[i].start(), filtered_matches[i+1].end()))

    # Word triples
    top_triples_keys = {k for k, _ in tri.most_common(10)}
    for k in top_triples_keys:
        matches_map[" ".join(k)] = []
    for i in range(len(tokens) - 2):
        k = (tokens[i], tokens[i+1], tokens[i+2])
        if k in top_triples_keys:
            matches_map[" ".join(k)].append((filtered_matches[i].start(), filtered_matches[i+2].end()))

    if set_progress_callback is not None:
        set_progress_callback(100)

    return {
        "single": top_single,
        "pairs": top_pairs,
        "triples": top_triples,
        "matches": matches_map,
    }
