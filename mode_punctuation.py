"""mode_punctuation.py — Finds punctuation errors, spaced ellipses, long dashes, and loud marks."""

import re
from dialogue_masker import find_quote_issues

_DASH_RE = re.compile(r"--|\s—|—\s|\s-\s")
_ELLIPSIS_RE = re.compile(r"(?<!\.)\.{2}(?!\.)|(?<!\.)\.{4,}")
_LOUD_PUNCT_RE = re.compile(r"!!+|\?!|!\?")


def analyze_dialogue_mechanics(text: str) -> list[tuple[int, int, str]]:
    """Return punctuation/dialogue hits as (start, end, class) tuples."""
    if not text.strip():
        return []

    hits: list[tuple[int, int, str]] = []

    for start, end in find_quote_issues(text):
        hits.append((start, end, "quote"))

    for match in _DASH_RE.finditer(text):
        hits.append((match.start(), match.end(), "dash"))

    for match in _ELLIPSIS_RE.finditer(text):
        hits.append((match.start(), match.end(), "ellipsis"))

    for match in _LOUD_PUNCT_RE.finditer(text):
        hits.append((match.start(), match.end(), "loud"))

    unique_hits = sorted(set(hits), key=lambda item: item[0])
    return unique_hits
