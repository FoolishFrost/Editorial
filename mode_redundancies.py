"""mode_redundancies.py — Highlights common semantic redundancies."""

import re
from typing import Callable
from analysis_utils import load_or_create_list

_DEFAULT_REDUNDANCIES = [
    "shrugged his shoulders", "nodded her head", "whispered softly", "sudden crisis",
    "past history", "added bonus", "advance warning", "basic fundamentals",
    "close proximity", "completely finish", "consensus of opinion", "end result",
    "exactly identical", "fall down", "final outcome", "first and foremost",
    "free gift", "future plans", "join together", "kneel down", "major breakthrough",
    "new beginning", "new innovation", "past experience", "postpone until later",
    "revert back", "safe haven", "shrugged her shoulders", "nodded his head",
    "smile on his face", "smile on her face", "stand up", "sit down",
    "totally unique", "true fact", "unexpected surprise", "unintended mistake",
    "shook his head", "shook her head"
]

REDUNDANCIES_LIST = load_or_create_list("redundancies.txt", _DEFAULT_REDUNDANCIES)
_REDUNDANCIES_REGEXES = [re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE) for phrase in REDUNDANCIES_LIST]


def reload_redundancies() -> None:
    global REDUNDANCIES_LIST, _REDUNDANCIES_REGEXES
    REDUNDANCIES_LIST = load_or_create_list("redundancies.txt", _DEFAULT_REDUNDANCIES)
    _REDUNDANCIES_REGEXES = [re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE) for phrase in REDUNDANCIES_LIST]


def analyze_redundancies(
    text: str,
    progress_callback: Callable[[int], None] | None = None,
) -> list[tuple[int, int, str]]:
    """Return redundancy matches as (start, end, class) tuples."""
    if not text.strip():
        if progress_callback is not None:
            progress_callback(100)
        return []

    hits: list[tuple[int, int, str]] = []

    total_chars = max(1, len(text))
    last_progress = -1

    for i, regex in enumerate(_REDUNDANCIES_REGEXES):
        for match in regex.finditer(text):
            hits.append((match.start(), match.end(), "redundancy_hit"))
        if progress_callback is not None:
            pct = max(1, min(100, int((i / len(_REDUNDANCIES_REGEXES)) * 100)))
            if pct != last_progress:
                progress_callback(pct)
                last_progress = pct

    if progress_callback is not None and last_progress < 100:
        progress_callback(100)

    return sorted(set(hits), key=lambda x: x[0])
