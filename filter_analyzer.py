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

EMOTION_WORDS: set[str] = {
    "angry", "anger", "furious", "irate", "mad", "rage", "enraged",
    "sad", "sorrow", "depressed", "miserable", "gloomy", "heartbroken",
    "terrified", "afraid", "fearful", "scared", "panic", "anxious",
    "happy", "joyful", "glad", "delighted", "elated", "cheerful",
    "jealous", "envy", "envious", "resentful",
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
_DIALOGUE_TAG_VERBS = (
    "said|asked|replied|murmured|whispered|shouted|yelled|cried|called|"
    "muttered|snapped|growled|hissed|added|continued|answered|insisted|"
    "explained|admitted|sighed|laughed|breathed"
)
_MISSING_TAG_PUNCT_RE = re.compile(
    rf"[A-Za-z0-9](?P<quote>[\"\u201d])\s+(?:[a-z][A-Za-z'\u2019-]*\s+){{0,2}}(?:{_DIALOGUE_TAG_VERBS})\b"
)
_UPPER_TAG_PRONOUN_RE = re.compile(
    rf"[.!?\u2026][\"\u201d]\s+(?P<pronoun>He|She|They|We|You|It|I)\s+(?:{_DIALOGUE_TAG_VERBS})\b"
)
_TAG_CHAIN_RE = re.compile(
    rf"(?P<prepunct>[,.!?\u2026])(?P<quote>[\"\u201d])\s+"
    rf"(?P<subject>He|She|They|We|You|It|I|he|she|they|we|you|it|i|[A-Z][a-z]+|[a-z][a-z]+)\s+"
    rf"(?P<verb>{_DIALOGUE_TAG_VERBS})\b"
)
_UPPER_PRONOUNS = {"He", "She", "They", "We", "You", "It", "I"}
_STANDARD_TAG_VERBS = {"said", "asked"}
_OPEN_SENTENCE_PUNCT = '"([{\u201c'
_CLOSE_SENTENCE_PUNCT = '")]}\u201d!?.,;:\u2026'
_SENTENCE_END_CHARS = ".!?"
_COMMON_ABBREVIATIONS = {
    "mr.", "mrs.", "ms.", "dr.", "prof.", "sr.", "jr.", "st.",
    "vs.", "etc.", "e.g.", "i.e.", "a.m.", "p.m.",
}

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


def analyze_emotion_words(
    text: str,
    progress_callback: Callable[[int], None] | None = None,
) -> list[tuple[int, int, str]]:
    """Return explicit emotion-word hits as (start, end, class) tuples.

    This scan masks dialogue and only flags narration for tell-vs-show terms.
    """
    if not text.strip():
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


def analyze_dialogue_tags(text: str) -> list[tuple[int, int, str]]:
    """Return dialogue-tag lint hits as (start, end, class) tuples."""
    if not text.strip():
        return []

    hits: list[tuple[int, int, str]] = []

    # "I am going" he said. -> missing punctuation before closing quote.
    for match in _MISSING_TAG_PUNCT_RE.finditer(text):
        q = match.start("quote")
        hits.append((q, q + 1, "tag"))

    # "Stop!" He yelled. -> uppercase pronoun often indicates tag capitalization issue.
    for match in _UPPER_TAG_PRONOUN_RE.finditer(text):
        s, e = match.span("pronoun")
        hits.append((s, e, "tag"))

    # Additional dialogue-tag lint checks.
    for match in _TAG_CHAIN_RE.finditer(text):
        prepunct = match.group("prepunct")
        subject = match.group("subject")
        verb = match.group("verb").lower()

        if prepunct == ".":
            p = match.start("prepunct")
            hits.append((p, p + 1, "tag"))

        if subject in _UPPER_PRONOUNS:
            s, e = match.span("subject")
            hits.append((s, e, "tag"))

        if verb not in _STANDARD_TAG_VERBS:
            s, e = match.span("verb")
            hits.append((s, e, "tag"))

    return sorted(set(hits), key=lambda item: item[0])


def analyze_sentence_pacing(
    text: str,
    short_max_words: int = 3,
    average_words: int = 12,
    long_min_words: int = 19,
    progress_callback: Callable[[int], None] | None = None,
) -> list[tuple[int, int, float, int]]:
    """Return sentence pacing bands as (start, end, heat, word_count)."""
    if not text.strip():
        return []

    def is_sentence_break(block: str, idx: int) -> bool:
        ch = block[idx]
        if ch not in _SENTENCE_END_CHARS:
            return False
        if ch == ".":
            prev_ch = block[idx - 1] if idx > 0 else ""
            next_ch = block[idx + 1] if idx + 1 < len(block) else ""

            # Ellipsis is treated as a pacing pause, not a sentence break.
            if prev_ch == "." or next_ch == ".":
                return False

            # Don't split decimals.
            if prev_ch.isdigit() and next_ch.isdigit():
                return False

            # Suppress common abbreviations from breaking sentences.
            j = idx - 1
            while j >= 0 and block[j].isspace():
                j -= 1
            k = j
            while k >= 0 and (block[k].isalpha() or block[k] in {"'", "\u2019", "-"}):
                k -= 1
            token = block[k + 1:j + 1].lower()
            if token and f"{token}." in _COMMON_ABBREVIATIONS:
                return False
            # Initials like "A. Smith" should not hard-split.
            if len(token) == 1 and token.isalpha() and idx + 2 < len(block) and block[idx + 2].isupper():
                return False
        return True

    def iter_sentence_spans(block: str):
        start = 0
        i = 0
        while i < len(block):
            if is_sentence_break(block, i):
                end = i + 1
                while end < len(block) and block[end] in _CLOSE_SENTENCE_PUNCT:
                    end += 1
                yield (start, end)
                start = end
                i = end
                continue
            i += 1
        if start < len(block):
            yield (start, len(block))

    bands: list[tuple[int, int, float, int]] = []
    total_chars = max(1, len(text))
    last_progress = -1

    # Analyze non-empty paragraph blocks independently so scene breaks and blank
    # lines can never merge into phantom long "sentences".
    cursor = 0
    while cursor < len(text):
        match = re.search(r"\n[ \t]*\n+", text[cursor:])
        if match is None:
            block_end = len(text)
            next_cursor = len(text)
        else:
            block_end = cursor + match.start()
            next_cursor = cursor + match.end()
        block = text[cursor:block_end]
        block_offset = cursor

        if block.strip():
            for sent_start, sent_end in iter_sentence_spans(block):
                global_end = block_offset + sent_end
                if progress_callback is not None:
                    pct = max(1, min(100, int((global_end / total_chars) * 100)))
                    if pct != last_progress:
                        progress_callback(pct)
                        last_progress = pct

                sent_text = block[sent_start:sent_end]
                words = list(_WORD_RE.finditer(sent_text))
                wc = len(words)
                if wc == 0:
                    continue

                start_char = sent_start + words[0].start()
                while start_char > sent_start and block[start_char - 1] in _OPEN_SENTENCE_PUNCT:
                    start_char -= 1

                end_char = sent_start + words[-1].end()
                # Include possessive/contraction suffixes attached to the last
                # alpha token (e.g. Nalls's, don't, he'll) so apostrophes do
                # not truncate the detected sentence span.
                while (
                    end_char + 1 < sent_end
                    and block[end_char] in {"'", "\u2019"}
                    and block[end_char + 1].isalpha()
                ):
                    end_char += 1
                    while end_char < sent_end and block[end_char].isalpha():
                        end_char += 1
                while end_char < sent_end and block[end_char] in _CLOSE_SENTENCE_PUNCT:
                    end_char += 1

                if wc <= short_max_words:
                    heat = -1.0
                elif wc < average_words:
                    heat = -1.0 + ((wc - short_max_words) / max(1, average_words - short_max_words))
                elif wc >= long_min_words:
                    heat = 1.0
                else:
                    heat = (wc - average_words) / max(1, long_min_words - average_words)

                bands.append(
                    (
                        block_offset + start_char,
                        block_offset + end_char,
                        max(-1.0, min(1.0, heat)),
                        wc,
                    )
                )

        cursor = next_cursor

    if progress_callback is not None and last_progress < 100:
        progress_callback(100)

    return bands


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
