"""Unit tests for the Sentence Architecture/Prose Structure analyser."""

from __future__ import annotations

import pytest

from filter_analyzer import analyze_sentence_architecture


def _tags_for(text: str) -> list[str]:
    """Return the list of archetype tags produced for the given text."""
    hits = analyze_sentence_architecture(text)
    return [tag for _, _, tag in hits]


def _contains_tag(text: str, expected_tag: str) -> bool:
    return expected_tag in _tags_for(text)


class TestSubjectFirstOpener:
    def test_pronoun_drone(self):
        assert _contains_tag("She grabbed the sword.", "arch_subject_first")
        assert _contains_tag("She lunged forward.", "arch_subject_first")
        assert _contains_tag("Ali missed the beast.", "arch_subject_first")
        assert _contains_tag("He ran.", "arch_subject_first")

    def test_non_subject_first_ignored(self):
        # Setting-first or front-loaded sentences are not "Subject-First Opener"
        assert not _contains_tag("Through the thick gray fog, Ali crawled.", "arch_subject_first")


class TestParticipialLaunch:
    def test_ing_launch(self):
        assert _contains_tag(
            "Sprinting toward the clearing, she drew her blade.",
            "arch_participial_launch"
        )
        assert _contains_tag(
            "Glancing over her shoulder, Kindra prepared a spell.",
            "arch_participial_launch"
        )


class TestContextualLead:
    def test_preposition_first(self):
        assert _contains_tag("Through the thick gray fog, Ali crawled.", "arch_contextual_lead")
        assert _contains_tag("Near the edge of the fire, the beast waited.", "arch_contextual_lead")


class TestEchoingHinge:
    def test_symmetrical_compound(self):
        assert _contains_tag(
            "The fire engulfed the creature instantly, but the blast did no damage.",
            "arch_echoing_hinge"
        )
        assert _contains_tag(
            "The blade struck the furred neck, and a shock of pain ran up her arm.",
            "arch_echoing_hinge"
        )


class TestSimultaneousSetup:
    def test_as_when_trap(self):
        assert _contains_tag("As the beast turned, Ali struck.", "arch_simultaneous_setup")
        assert _contains_tag("When the smoke cleared, Kindra gasped.", "arch_simultaneous_setup")


class TestSyntaxStack:
    def test_stack_detection(self):
        # If the exact same structural archetype appears 3+ times in a 100-word window,
        # it gets marked with '_stacked'
        text = (
            "She grabbed the sword. "
            "She lunged forward. "
            "Ali missed the beast. "
            "This is normal text to pad it out."
        )
        tags = _tags_for(text)
        assert tags.count("arch_subject_first_stacked") == 4

    def test_large_document_performance(self):
        import time
        # Generate 400 Subject-First sentences to ensure a large 'n'
        # without the O(N^2) optimization, this would take a very long time.
        # With the optimization, it completes in a few milliseconds.
        text = " ".join(["She grabbed the sword. She lunged forward."] * 200)
        t0 = time.perf_counter()
        hits = analyze_sentence_architecture(text)
        elapsed = time.perf_counter() - t0
        # Assert it runs very quickly (typically < 0.2 seconds even with spaCy startup included)
        assert elapsed < 1.0
        assert len(hits) > 0


class TestDialogueMasking:
    def test_mask_dialogue_text_straight_quotes(self):
        import tkinter as tk
        try:
            root = tk.Tk()
        except Exception:
            pytest.skip("Tkinter is not available in this environment")

        from editorial import EditorialApp
        app = EditorialApp(root)
        
        # Test basic straight quote masking
        text = 'She said, "I am here," and then she walked.'
        masked = app._mask_dialogue_text(text)
        assert masked == 'She said, "          " and then she walked.'
        root.destroy()

    def test_mask_dialogue_text_smart_quotes(self):
        import tkinter as tk
        try:
            root = tk.Tk()
        except Exception:
            pytest.skip("Tkinter is not available in this environment")

        from editorial import EditorialApp
        app = EditorialApp(root)

        # Test smart quote masking
        text = 'She said, “Yes, indeed,” and then she left.'
        masked = app._mask_dialogue_text(text)
        assert masked == 'She said, “            ” and then she left.'
        root.destroy()

    def test_mask_dialogue_multiline_reset(self):
        import tkinter as tk
        try:
            root = tk.Tk()
        except Exception:
            pytest.skip("Tkinter is not available in this environment")

        from editorial import EditorialApp
        app = EditorialApp(root)

        # Test that unclosed quote doesn't bleed across hard paragraph lines
        text = 'She said, "I am going.\nHe stayed.'
        masked = app._mask_dialogue_text(text)
        assert masked == 'She said, "           \nHe stayed.'
        root.destroy()
