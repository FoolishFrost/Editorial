"""formatting_subsystem.py — Pure string processing functions for quotes, ellipses, and whitespace."""

import re


def smarten_straight_quotes(text: str) -> str:
    """Convert straight quotes to curly (smart) quotes contextually."""
    # First normalize smart quotes to straight quotes so conversion is deterministic.
    src = text.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    out: list[str] = []
    open_double = True
    open_single = True

    for idx, ch in enumerate(src):
        prev_ch = src[idx - 1] if idx > 0 else ""
        next_ch = src[idx + 1] if idx + 1 < len(src) else ""

        if ch == '"':
            if open_double:
                out.append("\u201c")
            else:
                out.append("\u201d")
            open_double = not open_double
            continue

        if ch == "'":
            # Apostrophe in words: don't treat as quote pair delimiter.
            if prev_ch.isalpha() and next_ch.isalpha():
                out.append("\u2019")
                continue

            if open_single:
                out.append("\u2018")
            else:
                out.append("\u2019")
            open_single = not open_single
            continue

        out.append(ch)

    return "".join(out)


def convert_to_smart_quotes(text: str) -> str:
    """Wrapper function to smarten text quotes."""
    return smarten_straight_quotes(text)


def convert_to_straight_quotes(text: str) -> str:
    """Convert smart quotes to straight quotes."""
    return text.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")


def convert_ellipses_spaced(text: str) -> str:
    """Convert all ellipsis formats to standard unspaced three-dots (i.e. '...')."""
    return re.sub(r'(?:\.(?: \.){2,}|\.{3,}|\u2026)', '...', text)


def convert_ellipses_char(text: str) -> str:
    """Convert all ellipsis formats to standard single-character ellipsis (i.e. '…')."""
    return re.sub(r'(?:\.(?: \.){2,}|\.{3,}|\u2026)', '\u2026', text)


def clean_whitespace(text: str) -> str:
    """Remove trailing spaces, collapse multiple spaces into one."""
    # Remove trailing spaces
    new_text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)
    # Collapse multiple spaces into one
    return re.sub(r'[ \t]{2,}', ' ', new_text)
