import os
import json
import re
import gzip
from spellchecker import SpellChecker


def _write_spellchecker_dictionary_file(payload: bytes, destination: str) -> str:
    destination_path = os.path.abspath(destination)
    directory = os.path.dirname(destination_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(destination_path, "wb") as fh:
        fh.write(gzip.decompress(payload))
    return destination_path


def _extract_spellcheck_tokens(content: str) -> list[tuple[str, tuple[int, int]]]:
    tokens: list[tuple[str, tuple[int, int]]] = []
    for match in re.finditer(r"[A-Za-z]+(?:['\u2019][A-Za-z]+)?", content):
        word = match.group(0)
        normalized_word = word.replace("\u2019", "'")
        if "'" in normalized_word:
            continue
        tokens.append((word, match.span()))
    return tokens


class SpellcheckSubsystem:
    """Subsystem class that owns the SpellChecker engine and dictionary files."""

    def __init__(self, custom_dict_path: str, local_dict_path: str | None = None) -> None:
        self.local_dict_path = local_dict_path
        if local_dict_path and os.path.exists(local_dict_path):
            try:
                self.spellchecker = SpellChecker(language=None, local_dictionary=local_dict_path)
            except Exception:
                try:
                    self.spellchecker = SpellChecker(language="en")
                except Exception:
                    self.spellchecker = SpellChecker()
        else:
            try:
                self.spellchecker = SpellChecker(language="en")
            except Exception:
                self.spellchecker = SpellChecker()

        self.custom_dict_path = os.path.abspath(custom_dict_path)
        self.custom_dict_words: set[str] = set()
        self.ignored_words: set[str] = set()
        self.load_custom_dictionary()

    def reinit_spellchecker(self) -> None:
        """Re-initialize the spellchecker instance to discard removed words."""
        if self.local_dict_path and os.path.exists(self.local_dict_path):
            try:
                self.spellchecker = SpellChecker(language=None, local_dictionary=self.local_dict_path)
            except Exception:
                try:
                    self.spellchecker = SpellChecker(language="en")
                except Exception:
                    self.spellchecker = SpellChecker()
        else:
            try:
                self.spellchecker = SpellChecker(language="en")
            except Exception:
                self.spellchecker = SpellChecker()
        self.load_custom_dictionary()


    def load_custom_dictionary(self) -> None:
        """Load the user's custom dictionary words from file."""
        try:
            if os.path.exists(self.custom_dict_path):
                with open(self.custom_dict_path, "r", encoding="utf-8") as fh:
                    words = json.load(fh)
                    if isinstance(words, list):
                        self.custom_dict_words = set(words)
                        self.spellchecker.word_frequency.load_words(words)
        except Exception:
            pass

    def save_custom_dictionary(self) -> None:
        """Save the custom dictionary words to file."""
        try:
            directory = os.path.dirname(self.custom_dict_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.custom_dict_path, "w", encoding="utf-8") as fh:
                json.dump(list(self.custom_dict_words), fh)
        except Exception:
            pass

    def add_to_dictionary(self, word: str) -> None:
        """Add a word to the custom dictionary (case-insensitive) and trigger save."""
        word_lower = word.lower()
        self.custom_dict_words.add(word_lower)
        self.spellchecker.word_frequency.load_words([word_lower])
        self.save_custom_dictionary()

    def ignore_word(self, word: str) -> None:
        """Ignore a spelling error for the current session (case-insensitive)."""
        self.ignored_words.add(word.lower())

    def get_candidates(self, word: str) -> set[str] | None:
        """Retrieve potential spelling corrections for a given word."""
        return self.spellchecker.candidates(word)

    def check_spelling(self, content: str, pov_names: set[str] | None = None) -> list[tuple[int, int]]:
        """
        Run spelling check on content, returning lists of spans for misspelled words.
        Optimized by checking only unique lowercase words and filtering out ignored terms.
        """
        if not content.strip():
            return []

        tokens = _extract_spellcheck_tokens(content)
        if not tokens:
            return []

        words = [word for word, _ in tokens]
        spans = [span for _, span in tokens]

        # Lowercase and deduplicate spelling candidates to minimize spellchecker lookups
        pov_names_lower = {name.lower() for name in pov_names} if pov_names else set()
        unique_words = {
            w.lower() for w in words
            if w.lower() not in self.ignored_words and w.lower() not in pov_names_lower
        }

        unknown_unique = self.spellchecker.unknown(list(unique_words))

        misspelled = []
        for i, word in enumerate(words):
            if word.lower() in unknown_unique:
                misspelled.append(spans[i])

        return misspelled
