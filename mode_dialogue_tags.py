"""mode_dialogue_tags.py — Identifies incorrect dialogue tag formatting and capitalization."""

import re

_DIALOGUE_TAG_VERBS = (
    "said|asked|replied|murmured|whispered|shouted|yelled|cried|called|"
    "muttered|snapped|growled|hissed|added|continued|answered|insisted|"
    "explained|admitted|sighed|laughed|breathed"
)
_MISSING_TAG_PUNCT_RE = re.compile(
    rf"[A-Za-z0-9](?P<quote>[\"\u201d])[ \t]+(?:[a-z][A-Za-z'\u2019-]*[ \t]+){{0,2}}(?:{_DIALOGUE_TAG_VERBS})\b"
)
_UPPER_TAG_PRONOUN_RE = re.compile(
    rf"[.!?\u2026][\"\u201d][ \t]+(?P<pronoun>He|She|They|We|You|It|I)[ \t]+(?:{_DIALOGUE_TAG_VERBS})\b"
)
_TAG_CHAIN_RE = re.compile(
    rf"(?P<prepunct>[,.!?\u2026])(?P<quote>[\"\u201d])[ \t]+"
    rf"(?P<subject>He|She|They|We|You|It|I|he|she|they|we|you|it|i|[A-Z][a-z]+|[a-z][a-z]+)[ \t]+"
    rf"(?P<verb>{_DIALOGUE_TAG_VERBS})\b"
)
_UPPER_PRONOUNS = {"He", "She", "They", "We", "You", "It", "I"}
_STANDARD_TAG_VERBS = {"said", "asked"}


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
