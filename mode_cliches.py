"""mode_cliches.py — Detects clichés using spaCy Matcher patterns."""

from typing import Callable
from spacy_helper import _get_nlp
from analysis_utils import load_or_create_list

_DEFAULT_CLICHES = [
    "avoid like the plague", "fit as a fiddle", "at the end of the day",
    "piece of cake", "barking up the wrong tree", "bite the bullet",
    "break the ice", "call it a day", "cut corners", "get out of hand",
    "hang in there", "hit the sack", "let the cat out of the bag",
    "make a long story short", "miss the boat", "no pain, no gain",
    "on the ball", "pull someone's leg", "so far so good",
    "speak of the devil", "that's the last straw", "the best of both worlds",
    "time flies", "under the weather", "wrap my head around", "elephant in the room",
    "better late than never", "add insult to injury", "bite off more than you can chew",
    "burning the midnight oil", "cost an arm and a leg", "cutting edge", "dime a dozen",
    "don't judge a book by its cover", "every cloud has a silver lining", "ignorance is bliss",
    "it takes two to tango", "jump on the bandwagon", "leave no stone unturned",
    "once in a blue moon", "play devil's advocate", "spill the beans", "take with a grain of salt",
    "the early bird catches the worm", "the writing on the wall", "throw caution to the wind"
]

CLICHES_LIST = load_or_create_list("cliches.txt", _DEFAULT_CLICHES)

_CLICHES_MATCHER_PATTERNS = None
_LAST_CLICHES_LIST = None


def _get_cliches_matcher_patterns(nlp):
    global _CLICHES_MATCHER_PATTERNS, _LAST_CLICHES_LIST
    if _CLICHES_MATCHER_PATTERNS is None or _LAST_CLICHES_LIST != CLICHES_LIST:
        _LAST_CLICHES_LIST = list(CLICHES_LIST)
        _CLICHES_MATCHER_PATTERNS = []
        for phrase in CLICHES_LIST:
            phrase_clean = phrase.strip().lower()
            if not phrase_clean:
                continue
            phrase_doc = nlp(phrase_clean)
            lemmas = [token.lemma_ for token in phrase_doc]
            if not lemmas:
                continue

            pattern = [{"LEMMA": lemmas[0].lower()}]
            if len(lemmas) > 1:
                for _ in range(3):
                    pattern.append({"OP": "?", "IS_PUNCT": False, "IS_SPACE": False})
                for lemma in lemmas[1:]:
                    for _ in range(2):
                        pattern.append({"OP": "?", "IS_PUNCT": False, "IS_SPACE": False})
                    pattern.append({"LEMMA": lemma.lower()})
            _CLICHES_MATCHER_PATTERNS.append((phrase_clean, pattern))
    return _CLICHES_MATCHER_PATTERNS


def reload_cliches() -> None:
    global CLICHES_LIST, _CLICHES_MATCHER_PATTERNS, _LAST_CLICHES_LIST
    CLICHES_LIST = load_or_create_list("cliches.txt", _DEFAULT_CLICHES)
    _CLICHES_MATCHER_PATTERNS = None
    _LAST_CLICHES_LIST = None


def analyze_cliches(
    text: str,
    progress_callback: Callable[[int], None] | None = None,
) -> list[tuple[int, int, str]]:
    """Return cliche matches as (start, end, class) tuples."""
    if not text.strip():
        if progress_callback is not None:
            progress_callback(100)
        return []

    nlp = _get_nlp()
    doc = nlp(text)

    from spacy.matcher import Matcher
    matcher = Matcher(nlp.vocab)

    patterns = _get_cliches_matcher_patterns(nlp)
    for phrase, pattern in patterns:
        matcher.add(phrase, [pattern])

    hits: list[tuple[int, int, str]] = []
    matches = matcher(doc)

    for match_id, start_idx, end_idx in matches:
        start_char = doc[start_idx].idx
        end_char = doc[end_idx - 1].idx + len(doc[end_idx - 1].text)
        hits.append((start_char, end_char, "cliche_hit"))

    if progress_callback is not None:
        progress_callback(100)

    return sorted(set(hits), key=lambda x: x[0])
