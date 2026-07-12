"""analysis_utils.py — Shared helper utilities and regex patterns."""

import os
import sys
import re

_WORD_RE = re.compile(r"[A-Za-z]+(?:['\u2019][A-Za-z]+)?")

def _get_base_dir() -> str:
    """Get the base directory for loading/saving data files."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def load_or_create_list(filename: str, default_items: list[str]) -> list[str]:
    """Load items from a file, creating it with defaults if it doesn't exist."""
    path = os.path.join(_get_base_dir(), filename)
    try:
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as fh:
                for item in default_items:
                    fh.write(f"{item}\n")
            return list(default_items)

        with open(path, "r", encoding="utf-8") as fh:
            lines = [line.strip() for line in fh.readlines()]
            return [line for line in lines if line and not line.startswith("#")]
    except Exception:
        # Fallback to defaults if file operations fail
        return list(default_items)
