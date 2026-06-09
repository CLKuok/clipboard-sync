"""Clipboard access helpers."""

from __future__ import annotations

import pyperclip


class ClipboardError(RuntimeError):
    """Raised when clipboard access fails."""


def read_text() -> str:
    """Read text from the Windows clipboard."""
    try:
        text = pyperclip.paste()
    except pyperclip.PyperclipException as exc:
        raise ClipboardError(f"Could not read clipboard: {exc}") from exc

    if not isinstance(text, str):
        raise ClipboardError("Clipboard did not contain text.")

    return text


def write_text(text: str) -> None:
    """Copy text to the Windows clipboard."""
    try:
        pyperclip.copy(text)
    except pyperclip.PyperclipException as exc:
        raise ClipboardError(f"Could not write clipboard: {exc}") from exc
