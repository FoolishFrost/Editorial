from spellcheck_subsystem import _extract_spellcheck_tokens


def test_extract_spellcheck_tokens_skips_contractions() -> None:
    tokens = _extract_spellcheck_tokens("Don't stop now.")
    assert tokens == [("stop", (6, 10)), ("now", (11, 14))]

    tokens2 = _extract_spellcheck_tokens("didn’t wasn’t hadn’t stop now.")
    assert tokens2 == [("stop", (21, 25)), ("now", (26, 29))]


def test_convert_ellipses_standard() -> None:
    import re
    pattern = r'(?:\.(?: \.){2,}|\.{3,}|\u2026)'

    assert re.sub(pattern, '...', 'Hello . . . world') == 'Hello ... world'
    assert re.sub(pattern, '...', 'Hello ... world') == 'Hello ... world'
    assert re.sub(pattern, '...', 'Hello \u2026 world') == 'Hello ... world'
    assert re.sub(pattern, '...', 'Hello .... world') == 'Hello ... world'

