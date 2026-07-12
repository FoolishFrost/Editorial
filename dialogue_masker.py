"""dialogue_masker.py — Scanning, masking, and exclusion detection for dialogue spans."""

import re

_DIALOGUE_RE = re.compile(r'["\u201c\u201d]')

IGNORE_PHRASES: list[str] = [
    "look like", "looks like", "looking like", "feel free", "make sense",
    "you see", "looked like",
]
_IGNORE_PHRASE_REGEXES = [re.compile(re.escape(phrase)) for phrase in IGNORE_PHRASES]


def _prev_non_space(text: str, pos: int) -> str:
    i = pos - 1
    while i >= 0 and text[i] in " \t\r\n":
        i -= 1
    return text[i] if i >= 0 else ""


def _next_non_space(text: str, pos: int) -> str:
    i = pos + 1
    while i < len(text) and text[i] in " \t\r\n":
        i += 1
    return text[i] if i < len(text) else ""


def _is_paragraph_start(text: str, pos: int) -> bool:
    i = pos - 1
    while i >= 0 and text[i] in " \t\r":
        i -= 1
    return i < 0 or text[i] == "\n"


def _looks_like_open_quote(text: str, pos: int) -> bool:
    quote_ch = text[pos]
    prev_ch = _prev_non_space(text, pos)
    prev_raw = text[pos - 1] if pos > 0 else ""
    next_ch = _next_non_space(text, pos)
    if quote_ch == "\u201c":
        return True
    if quote_ch != '"':
        return False
    if next_ch == "" or next_ch in '"\u201d':
        return False
    return prev_raw in {"", " ", "\t", "\r", "\n", "(", "[", "{", "<", "-"} or prev_ch in ":;"


def _scan_dialogue(text: str) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Return dialogue spans and quote-error spans from regex-identified quote chars."""
    spans: list[tuple[int, int]] = []
    errors: list[tuple[int, int]] = []
    open_start: int | None = None

    for m in _DIALOGUE_RE.finditer(text):
        pos = m.start()

        if open_start is None:
            open_start = pos
            continue

        if _is_paragraph_start(text, pos):
            # Multi-paragraph dialogue convention: new paragraph starts with a
            # fresh quote marker while the earlier quote remains logically open.
            continue

        if _looks_like_open_quote(text, pos):
            # A likely new opener while an older quote is still open usually
            # means the previous quote was damaged or missing its closer.
            spans.append((open_start, pos))
            errors.append((open_start, min(open_start + 1, len(text))))
            open_start = pos
            continue

        spans.append((open_start, pos + 1))
        open_start = None

    if open_start is not None:
        spans.append((open_start, len(text)))
        errors.append((open_start, min(open_start + 1, len(text))))

    return spans, errors


def _mask_dialogue_spans(text: str, dialogue_spans: list[tuple[int, int]]) -> str:
    """Replace dialogue with spaces so sentence/char offsets are preserved."""
    chars = list(text)
    for start, end in dialogue_spans:
        for i in range(start, end):
            if chars[i] != "\n":
                chars[i] = " "
    return "".join(chars)


def _mask_dialogue(text: str) -> str:
    dialogue_spans, _quote_errors = _scan_dialogue(text)
    return _mask_dialogue_spans(text, dialogue_spans)


def _find_dialogue_spans(text: str) -> list[tuple[int, int]]:
    """Return half-open dialogue spans built from regex-identified quote chars."""
    spans, _errors = _scan_dialogue(text)
    return spans


def find_quote_issues(text: str) -> list[tuple[int, int]]:
    """Return spans that mark likely quote damage, such as missing closers."""
    _spans, errors = _scan_dialogue(text)
    return errors


def _is_in_dialogue(
    token_start: int,
    token_end: int,
    dialogue_spans: list[tuple[int, int]],
    start_idx: int,
) -> tuple[bool, int]:
    """Return whether token overlaps a dialogue span and updated cursor index."""
    idx = start_idx
    while idx < len(dialogue_spans) and token_start >= dialogue_spans[idx][1]:
        idx += 1
    if idx < len(dialogue_spans):
        s, e = dialogue_spans[idx]
        if token_start < e and token_end > s:
            return True, idx
    return False, idx


def _token_overlaps_ignored_phrase(token_start: int, token_end: int, sent) -> bool:
    sent_lower = sent.text.lower()
    rel_start = token_start - sent.start_char
    rel_end = token_end - sent.start_char

    for phrase_re in _IGNORE_PHRASE_REGEXES:
        for m in phrase_re.finditer(sent_lower):
            if rel_start < m.end() and rel_end > m.start():
                return True
    return False
