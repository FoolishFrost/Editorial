from spellcheck_subsystem import _extract_spellcheck_tokens


def test_extract_spellcheck_tokens_splits_contractions() -> None:
    # Contractions are now returned as single tokens
    tokens = _extract_spellcheck_tokens("Don't stop now.")
    words = [w for w, _ in tokens]
    assert "Don't" in words
    assert "stop" in words
    assert "now" in words
    assert "Don" not in words
    assert "t" not in words

    tokens2 = _extract_spellcheck_tokens("didn't wasn't hadn't stop now.")
    words2 = [w for w, _ in tokens2]
    assert "didn't" in words2
    assert "wasn't" in words2
    assert "hadn't" in words2
    assert "stop" in words2
    assert "now" in words2

    tokens3 = _extract_spellcheck_tokens("he's here.")
    words3 = [w for w, _ in tokens3]
    assert "he's" in words3
    assert "here" in words3


def test_extract_spellcheck_tokens_catches_invalid_suffix() -> None:
    # "ca'nnt" is tokenised as the entire contraction word
    tokens = _extract_spellcheck_tokens("ca'nnt")
    words = [w for w, _ in tokens]
    assert "ca'nnt" in words
    assert "ca" not in words
    assert "nnt" not in words


def test_spellchecker_contraction_validation() -> None:
    from spellcheck_subsystem import SpellcheckSubsystem
    import tempfile
    import os
    with tempfile.TemporaryDirectory() as tmpdir:
        custom_dict_path = os.path.join(tmpdir, "custom_dictionary.json")
        subsystem = SpellcheckSubsystem(custom_dict_path=custom_dict_path)
        
        # Valid negation contraction -> not flagged
        assert len(subsystem.check_spelling("didn't")) == 0
        assert len(subsystem.check_spelling("wouldn't")) == 0
        
        # Invalid negation contraction -> flagged!
        assert len(subsystem.check_spelling("did'nt")) == 1
        assert len(subsystem.check_spelling("would'nt")) == 1
        assert len(subsystem.check_spelling("done't")) == 1
        
        # Valid possessive of standard word -> not flagged
        assert len(subsystem.check_spelling("writer's")) == 0
        
        # Valid possessive of POV name -> not flagged
        assert len(subsystem.check_spelling("Kindra's", pov_names={"Kindra"})) == 0
        
        # Invalid possessive -> flagged!
        assert len(subsystem.check_spelling("Kindraa's", pov_names={"Kindra"})) == 1


def test_convert_ellipses_standard() -> None:
    import re
    pattern = r'(?:\.(?: \.){2,}|\.{3,}|\u2026)'

    assert re.sub(pattern, '...', 'Hello . . . world') == 'Hello ... world'
    assert re.sub(pattern, '...', 'Hello ... world') == 'Hello ... world'
    assert re.sub(pattern, '...', 'Hello \u2026 world') == 'Hello ... world'
    assert re.sub(pattern, '...', 'Hello .... world') == 'Hello ... world'

