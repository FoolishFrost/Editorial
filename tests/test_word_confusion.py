import pytest
import os
import tempfile
from spellcheck_subsystem import SpellcheckSubsystem

def test_word_confusion_rules_loading_and_checking() -> None:
    # Set up a temporary custom dictionary path
    with tempfile.TemporaryDirectory() as tmpdir:
        custom_dict_path = os.path.join(tmpdir, "custom_dictionary.json")
        
        # Initialize subsystem (it will create the word_confusions.json in the base directory if missing)
        subsystem = SpellcheckSubsystem(custom_dict_path=custom_dict_path)
        
        # Verify rules loaded successfully
        assert hasattr(subsystem, "confusion_rules")
        assert len(subsystem.confusion_rules) > 0
        
        # Test Case 1: "its" vs "it's" (verb context)
        content1 = "its a nice day"
        confusions1 = subsystem.check_word_confusion(content1)
        assert len(confusions1) == 1
        start, end, suggest, explanation = confusions1[0]
        assert start == 0
        assert end == 3
        assert suggest == "it's"
        assert "contraction" in explanation
        
        # Test Case 2: "your" vs "you're" (adjective context)
        content2 = "your welcome"
        confusions2 = subsystem.check_word_confusion(content2)
        assert len(confusions2) == 1
        start, end, suggest, explanation = confusions2[0]
        assert start == 0
        assert end == 4
        assert suggest == "you're"
        
        # Test Case 3: "they're" vs "their" (noun context)
        content3 = "they're house"
        confusions3 = subsystem.check_word_confusion(content3)
        assert len(confusions3) == 1
        start, end, suggest, explanation = confusions3[0]
        assert start == 0
        assert end == 7
        assert suggest == "their" or suggest == "there" # depending on rule details, suggest is "their"
        
        # Test Case 4: "passed" vs "past" (motion verb context)
        content4 = "he ran passed me"
        confusions4 = subsystem.check_word_confusion(content4)
        assert len(confusions4) == 1
        start, end, suggest, explanation = confusions4[0]
        assert start == 7
        assert end == 13
        assert suggest == "past"
        
        # Test Case 5: Overlap resolution (earliest wins)
        # "its a loose verb" has "its a" and also "loose verb" isn't a trigger, but let's test overlapping trigger rules
        # Let's verify that resolving works
        content5 = "its a your welcome" # Trigger 1: its, Trigger 2: your
        confusions5 = subsystem.check_word_confusion(content5)
        assert len(confusions5) == 2
        assert confusions5[0][2] == "it's"
        assert confusions5[1][2] == "you're"

        # Test Case 6: Ignore confusion check
        # Ignore the first confusion and verify it's skipped
        subsystem.ignore_confusion(0, 3)
        confusions_ignored = subsystem.check_word_confusion(content5)
        # Should now only find "your welcome"
        assert len(confusions_ignored) == 1
        assert confusions_ignored[0][2] == "you're"

        # Test Case 7: "it's" vs "its" (possessive context)
        content7 = "tear it's bloody sword"
        confusions7 = subsystem.check_word_confusion(content7)
        assert len(confusions7) == 1
        start, end, suggest, explanation = confusions7[0]
        assert start == 5
        assert end == 9
        assert suggest == "its"
