from editorial import _extract_spellcheck_tokens


def test_extract_spellcheck_tokens_skips_contractions() -> None:
    tokens = _extract_spellcheck_tokens("Don't stop now.")

    assert tokens == [("stop", (6, 10)), ("now", (11, 14))]
