"""mode_sentence_architecture.py — Categorizes sentence openings and highlights structural runs."""

import re
from typing import Callable
from spacy_helper import _get_nlp


def _classify_span(span) -> str | None:
    tokens = [t for t in span if not t.is_punct and not t.is_space]
    if not tokens:
        return None

    first_token = tokens[0]

    # Fragment Detection (lacks main verb or subject, excluding imperatives)
    has_verb = any(t.pos_ in ("VERB", "AUX") for t in tokens)
    is_fragment = False
    if not has_verb:
        is_fragment = True
    else:
        roots = [t for t in span if t.dep_ == "ROOT"]
        if roots:
            root_token = roots[0]
            if root_token.pos_ in ("VERB", "AUX"):
                root_subj = [c for c in root_token.children if c.dep_ in ("nsubj", "nsubjpass")]
                if not root_subj:
                    if first_token.text.lower() in ("not", "or", "and", "but", "so") or root_token.tag_ in ("VBP", "VBD"):
                        is_fragment = True
            else:
                is_fragment = True
        else:
            is_fragment = True

    if is_fragment:
        return "arch_fragment"

    # Participial Launch (VERB VBG present participle)
    if first_token.tag_ == "VBG":
        return "arch_participial_launch"

    # Contextual Lead (ADP Preposition or npadvmod noun phrase like "The moment")
    if first_token.pos_ == "ADP":
        return "arch_contextual_lead"
    if first_token.pos_ == "DET" and len(tokens) > 1 and tokens[1].dep_ in ("npadvmod", "advmod"):
        return "arch_contextual_lead"
    if first_token.dep_ in ("npadvmod", "advmod") and first_token.pos_ in ("NOUN", "PROPN"):
        return "arch_contextual_lead"

    # Simultaneous Setup (SCONJ "as", "when", etc.)
    if first_token.pos_ == "SCONJ" or first_token.lemma_.lower() in ("as", "when", "while", "if", "after", "before", "once", "though", "although"):
        return "arch_simultaneous_setup"

    # Symmetrical Compound (Echoing Hinge)
    cconjs = [t for t in span if t.pos_ == "CCONJ" or t.dep_ == "cc"]
    if cconjs:
        conj_verbs = [t for t in span if t.dep_ == "conj" and t.pos_ in ("VERB", "AUX")]
        if conj_verbs:
            cc_idx = cconjs[0].i
            left_part = [t for t in span if t.i < cc_idx]
            right_part = [t for t in span if t.i > cc_idx]
            len_left = len([t for t in left_part if not t.is_punct])
            len_right = len([t for t in right_part if not t.is_punct])
            if len_left > 0 and len_right > 0:
                ratio = len_left / len_right
                if 0.6 <= ratio <= 1.6 or abs(len_left - len_right) <= 5:
                    return "arch_echoing_hinge"

    # Subject-First Opener (starts with subject, followed by verb)
    subj_tokens = [t for t in span if t.dep_ in ("nsubj", "nsubjpass")]
    if subj_tokens:
        subj = subj_tokens[0]
        allowed_before = True
        for t in span:
            if t.i < subj.i:
                if t.is_punct or t.is_space:
                    continue
                if t.pos_ in ("NOUN", "PROPN", "VERB", "ADP", "SCONJ"):
                    allowed_before = False
                    break
            else:
                break

        if allowed_before:
            verb = subj.head
            if verb.pos_ in ("VERB", "AUX") and verb.i > subj.i:
                has_complex_clause = False
                for t in span:
                    if t.dep_ in ("advcl", "ccomp") and t != verb:
                        t_subj = [c for c in t.children if c.dep_ in ("nsubj", "nsubjpass", "mark")]
                        if t_subj:
                            has_complex_clause = True
                            break
                if not has_complex_clause:
                    return "arch_subject_first"

    return None


def analyze_sentence_architecture(
    text: str,
    progress_callback: Callable[[int], None] | None = None,
) -> list[tuple[int, int, str]]:
    """Return sentence architecture hits as (start, end, arch_tag) tuples."""
    if not text.strip():
        if progress_callback is not None:
            progress_callback(100)
        return []

    nlp = _get_nlp()
    results: list[tuple[int, int, str]] = []
    total_chars = max(1, len(text))

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
            doc = nlp(block)
            for sent in doc.sents:
                tag = _classify_span(sent)
                if tag:
                    start_char = block_offset + sent.start_char
                    end_char = block_offset + sent.end_char
                    results.append((start_char, end_char, tag))

        if progress_callback is not None:
            pct = max(1, min(99, int((next_cursor / total_chars) * 100)))
            progress_callback(pct)

        cursor = next_cursor

    sorted_hits = sorted(results, key=lambda x: x[0])
    stacked_indices = set()
    by_tag = {}
    for idx, (_, _, tag) in enumerate(sorted_hits):
        by_tag.setdefault(tag, []).append(idx)

    for tag, indices in by_tag.items():
        if len(indices) < 3:
            continue
        n = len(indices)
        for i in range(n):
            for j in range(i + 2, n):
                idx_start = indices[i]
                idx_end = indices[j]
                char_start = sorted_hits[idx_start][0]
                char_end = sorted_hits[idx_end][1]
                span_text = text[char_start:char_end]
                word_count = len(span_text.split())
                if word_count <= 100:
                    for k in range(i, j + 1):
                        stacked_indices.add(indices[k])
                else:
                    break

    final_results = []
    for idx, (ws, we, tag) in enumerate(sorted_hits):
        if idx in stacked_indices:
            final_results.append((ws, we, tag + "_stacked"))
        else:
            final_results.append((ws, we, tag))

    if progress_callback is not None:
        progress_callback(100)

    return final_results
