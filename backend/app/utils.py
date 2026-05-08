"""Generic utility functions."""

import re


def clean_text(text: str) -> str:
    """Normalize whitespace in any block of text.

    - Strips leading/trailing whitespace.
    - Collapses runs of spaces/tabs to a single space within each line.
    - Collapses 3+ consecutive blank lines down to 2 (one visual gap).

    Returns the cleaned text.
    """
    # Collapse horizontal whitespace (spaces/tabs) within each line
    text = re.sub(r"[^\S\n]+", " ", text)

    # Collapse 3+ blank lines to a single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def validate_minimum_text_length(
    text: str, label: str, min_chars: int = 50
) -> None:
    """Raise ValueError if *text* is shorter than *min_chars*."""
    if len(text) < min_chars:
        raise ValueError(
            f"{label} is too short ({len(text)} chars). "
            f"Please provide at least {min_chars} characters."
        )
