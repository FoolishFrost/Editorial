"""mode_ignore_subsystem.py — Manages per-mode ignored words/phrases."""

import os
import json


class ModeIgnoreSubsystem:
    """Manages separate lists of ignored words/phrases for each analysis mode.
    
    Persists data to `mode_ignores.json` in the same directory as the main settings.
    """

    def __init__(self, settings_dir: str) -> None:
        self.ignores_path = os.path.join(settings_dir, "mode_ignores.json")
        # Initialize default empty sets for each supported mode
        self.ignores: dict[str, set[str]] = {
            "filter_words": set(),
            "weak_modifiers": set(),
            "cliches": set(),
            "redundancies": set(),
            "emotion_catcher": set(),
            "dialogue_tags": set(),
            "passive_voice": set(),
        }
        self.load_ignores()

    def load_ignores(self) -> None:
        """Load user ignored words/phrases from JSON file."""
        if not os.path.exists(self.ignores_path):
            return
        try:
            with open(self.ignores_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    for mode, words in data.items():
                        if mode in self.ignores and isinstance(words, list):
                            self.ignores[mode] = set(w.lower().strip() for w in words if w)
        except Exception:
            pass

    def save_ignores(self) -> None:
        """Save user ignored words/phrases to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.ignores_path), exist_ok=True)
            data = {mode: sorted(list(words)) for mode, words in self.ignores.items()}
            with open(self.ignores_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
        except Exception:
            pass

    def add_ignore(self, mode: str, word: str) -> None:
        """Add a word/phrase to the ignore list for a specific mode."""
        if mode not in self.ignores:
            return
        normalized = word.lower().strip()
        if normalized:
            self.ignores[mode].add(normalized)
            self.save_ignores()

    def remove_ignore(self, mode: str, word: str) -> None:
        """Remove a word/phrase from the ignore list for a specific mode."""
        if mode not in self.ignores:
            return
        normalized = word.lower().strip()
        if normalized in self.ignores[mode]:
            self.ignores[mode].remove(normalized)
            self.save_ignores()

    def filter_hits(self, mode: str, content: str, hits: list) -> list:
        """Filter out hits whose matched substring matches any ignored word/phrase for this mode."""
        ignored_words = self.ignores.get(mode)
        if not ignored_words or not hits:
            return hits

        filtered = []
        for hit in hits:
            ws, we = hit[0], hit[1]
            # Extract word/phrase from content
            text_span = content[ws:we].strip().lower()
            if text_span not in ignored_words:
                filtered.append(hit)
        return filtered
