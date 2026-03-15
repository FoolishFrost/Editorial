"""SpaCy-powered contextual filter-word analysis for fiction manuscripts."""

from __future__ import annotations

import argparse
import re
from typing import Callable

import spacy


FILTER_LEMMAS: list[str] = [
    "see", "look", "hear", "feel", "smell", "taste", "notice", "watch",
    "observe", "realize", "think", "know", "wonder", "decide", "note",
]

IGNORE_PHRASES: list[str] = [
    "look like", "looks like", "looking like", "feel free", "make sense",
    "you see", "looked like",
]

POV_PRONOUNS: list[str] = ["i", "he", "she", "we", "they"]

WEAK_MODIFIERS: set[str] = {
    "very", "really", "just", "suddenly", "almost",
}

ADVERB_EXCLUDE: set[str] = {
    "belly", "family", "friendly", "jelly", "likely", "lily",
    "lovely", "only", "silly", "tally", "valley",
}


# Match quote characters used for dialogue boundaries.
_DIALOGUE_RE = re.compile(r'["\u201c\u201d]')
_FILTER_SET = set(FILTER_LEMMAS)
_IGNORE_PHRASE_REGEXES = [re.compile(re.escape(phrase)) for phrase in IGNORE_PHRASES]
_WORD_RE = re.compile(r"[A-Za-z]+(?:['\u2019][A-Za-z]+)?")
_DASH_RE = re.compile(r"--|\s—|—\s|\s-\s")
_ELLIPSIS_RE = re.compile(r"(?<!\.)\.{2}(?!\.)|(?<!\.)\.{4,}")
_LOUD_PUNCT_RE = re.compile(r"!!+|\?!|!\?")

_NLP = None


def _get_nlp():
    global _NLP
    if _NLP is None:
        try:
            _NLP = spacy.load("en_core_web_sm")
        except OSError:
            # In packaged apps, direct module loading is often more reliable
            # than model-name lookup via entry points.
            try:
                import en_core_web_sm

                _NLP = en_core_web_sm.load()
            except Exception as exc:
                raise RuntimeError(
                    "spaCy model 'en_core_web_sm' is required. Install with: "
                    "python -m spacy download en_core_web_sm"
                ) from exc
    return _NLP


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
    """
    Replace dialogue with spaces so sentence/char offsets are preserved while
    ensuring words inside quotes are never flagged.
    """

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


def analyze_filter_words(
    text: str,
    pov_character_names: set[str] | None = None,
    active_pov_pronouns: list[str] | None = None,
    progress_callback: Callable[[int], None] | None = None,
) -> list[tuple[int, int, str]]:
    """
    Return filter-word matches as (start, end, class) tuples.

    Classes:
      - "red"    -> Standard Filter Word
            - "yellow" -> Emotional Tell (felt + adjective)

    Notes:
      - Dialogue is masked and never flagged.
    """
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

    hits.sort(key=lambda item: item[0])
    return hits


def build_console_report(
    text: str,
    pov_character_names: set[str] | None = None,
    active_pov_pronouns: list[str] | None = None,
) -> list[str]:
    """Build report lines formatted as requested for console output."""
    if not text.strip():
        return []

    nlp = _get_nlp()
    dialogue_spans, _quote_errors = _scan_dialogue(text)
    masked = _mask_dialogue_spans(text, dialogue_spans)
    doc = nlp(masked)
    hits = analyze_filter_words(text, pov_character_names, active_pov_pronouns)

    index_to_hits: dict[int, list[tuple[int, int, str]]] = {}
    for start, end, cls in hits:
        index_to_hits.setdefault(start, []).append((start, end, cls))

    lines: list[str] = []
    sent_no = 0
    for sent in doc.sents:
        sent_no += 1
        for token in sent:
            tok_start = token.idx
            if tok_start not in index_to_hits:
                continue
            tok_end = tok_start + len(token.text)
            for _s, _e, cls in index_to_hits[tok_start]:
                rule = "Emotional Tell" if cls == "yellow" else "Standard Filter Word"
                rel_start = tok_start - sent.start_char
                rel_end = tok_end - sent.start_char
                marked = sent.text[:rel_start] + "**" + sent.text[rel_start:rel_end] + "**" + sent.text[rel_end:]
                lines.append(f"[{sent_no}] - [{rule}]: \"{marked.strip()}\"")
    return lines


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


def print_report_for_file(
    file_path: str,
    pov_character_names: set[str] | None = None,
    active_pov_pronouns: list[str] | None = None,
) -> None:
    with open(file_path, "r", encoding="utf-8") as fh:
        text = fh.read()

    report_lines = build_console_report(text, pov_character_names, active_pov_pronouns)
    if not report_lines:
        print("No filter words found.")
        return

    print("Filter Word Report")
    print("------------------")
    for line in report_lines:
        print(line)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Context-aware filter-word analyzer")
    p.add_argument("input_file", help="Path to input .txt manuscript")
    p.add_argument(
        "--pov-names",
        default="",
        help="Comma-separated POV names (example: David,Sarah)",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    names = {n.strip() for n in args.pov_names.split(",") if n.strip()}
    print_report_for_file(args.input_file, names)


if __name__ == "__main__":
    main()
