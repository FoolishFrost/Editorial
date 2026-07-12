"""spacy_helper.py — Lazy SpaCy model loader singleton."""

import spacy

_NLP = None

def _get_nlp():
    global _NLP
    if _NLP is None:
        try:
            _NLP = spacy.load("en_core_web_sm")
        except OSError:
            try:
                import en_core_web_sm
                _NLP = en_core_web_sm.load()
            except Exception as exc:
                raise RuntimeError(
                    "spaCy model 'en_core_web_sm' is required. Install with: "
                    "python -m spacy download en_core_web_sm"
                ) from exc
    return _NLP
