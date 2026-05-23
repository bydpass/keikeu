from __future__ import annotations

from typing import Any


def copy_to_clipboard(root: Any, text: str) -> None:
    """Copy `text` to the system clipboard using Tk's built-in mechanism.

    `root` should be any Tk/CTk widget — typically the app's root window.
    """
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()
