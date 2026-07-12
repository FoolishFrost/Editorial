"""mode_rhythm_pacing.py — Analyzes and calculates sentence length heatmaps for pacing."""

import re
from typing import Callable
from analysis_utils import _WORD_RE

_OPEN_SENTENCE_PUNCT = '"\'\u201c\u2018({['
_CLOSE_SENTENCE_PUNCT = '")]}\u201d\u2019\'!?.,;:\u2026'
_SENTENCE_END_CHARS = ".!?\u2026"
_COMMON_ABBREVIATIONS = {
    "mr.", "mrs.", "ms.", "dr.", "prof.", "sr.", "jr.", "st.",
    "vs.", "etc.", "e.g.", "i.e.", "a.m.", "p.m.",
}


def is_sentence_break(block: str, idx: int) -> bool:
    ch = block[idx]
    if ch not in _SENTENCE_END_CHARS:
        return False

    # Ellipsis terminal checks
    is_ellipsis = (ch == "\u2026")
    if ch == ".":
        prev_ch = block[idx - 1] if idx > 0 else ""
        next_ch = block[idx + 1] if idx + 1 < len(block) else ""
        if prev_ch == "." or next_ch == ".":
            is_ellipsis = True

    if is_ellipsis:
        run_end = idx
        if ch == ".":
            while run_end + 1 < len(block) and block[run_end + 1] == ".":
                run_end += 1

        if ch == "." and idx != run_end:
            return False

        tail = run_end + 1
        while tail < len(block) and block[tail] in '"\'”’\u201d\u2019)]}!?,;:':
            tail += 1

        saw_linebreak = False
        while tail < len(block) and block[tail].isspace():
            if block[tail] in "\r\n":
                saw_linebreak = True
            tail += 1

        is_terminal = saw_linebreak or tail >= len(block)
        if not is_terminal and tail < len(block):
            if block[tail].isupper():
                is_terminal = True
        return is_terminal

    if ch == ".":
        prev_ch = block[idx - 1] if idx > 0 else ""
        next_ch = block[idx + 1] if idx + 1 < len(block) else ""
        if prev_ch.isdigit() and next_ch.isdigit():
            return False

        j = idx - 1
        while j >= 0 and block[j].isspace():
            j -= 1
        k = j
        while k >= 0 and (block[k].isalpha() or block[k] in {"'", "\u2019", "-"}):
            k -= 1
        token = block[k + 1:j + 1].lower()
        if token and f"{token}." in _COMMON_ABBREVIATIONS:
            return False
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

    bands: list[tuple[int, int, float, int]] = []
    total_chars = max(1, len(text))
    last_progress = -1

    cursor = 0
    while cursor < len(text):
        match = re.search(r"\r?\n+", text[cursor:])
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
