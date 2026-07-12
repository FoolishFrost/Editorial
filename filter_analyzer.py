"""SpaCy-powered contextual filter-word analysis for fiction manuscripts.
This file serves as a facade to maintain backwards compatibility with CLI runners and test suites.
"""

from __future__ import annotations

import argparse
from typing import Callable, Any

# Import from the newly extracted files
from spacy_helper import _get_nlp
from analysis_utils import load_or_create_list, _WORD_RE
from dialogue_masker import (
    _scan_dialogue,
    _mask_dialogue_spans,
    _mask_dialogue,
    _find_dialogue_spans,
    find_quote_issues,
    _is_in_dialogue,
    _token_overlaps_ignored_phrase,
)

from mode_filter_words import analyze_filter_words, FILTER_LEMMAS, POV_PRONOUNS
from mode_weak_modifiers import analyze_weak_modifiers, WEAK_MODIFIERS, ADVERB_EXCLUDE
from mode_punctuation import analyze_dialogue_mechanics
from mode_dialogue_tags import analyze_dialogue_tags
from mode_emotion_catcher import analyze_emotion_words, EMOTION_WORDS
from mode_rhythm_pacing import analyze_sentence_pacing
from mode_cliches import analyze_cliches, reload_cliches, CLICHES_LIST
from mode_redundancies import analyze_redundancies, reload_redundancies, REDUNDANCIES_LIST
from mode_passive_voice import analyze_passive_voice
from mode_sentence_architecture import analyze_sentence_architecture


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
