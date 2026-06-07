"""Plain-text clipboard helpers (Tier B; upstream clipboard.py is image-only)."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _windows_get_text() -> str | None:
    try:
        import ctypes

        CF_UNICODETEXT = 13
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        if not user32.OpenClipboard(0):
            return None
        try:
            handle = user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return None
            ptr = kernel32.GlobalLock(handle)
            if not ptr:
                return None
            try:
                text = ctypes.wstring_at(ptr)
            finally:
                kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()
        if not text or not str(text).strip():
            return None
        if "\x00" in text:
            return None
        return str(text)
    except Exception as exc:
        logger.debug("Windows clipboard text read failed: %s", exc)
        return None


def _windows_set_text(text: str) -> bool:
    try:
        import ctypes

        CF_UNICODETEXT = 13
        GMEM_MOVEABLE = 0x0002
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        if not user32.OpenClipboard(0):
            return False
        try:
            if not user32.EmptyClipboard():
                return False
            blob = (text + "\x00").encode("utf-16-le")
            size = len(blob)
            handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
            if not handle:
                return False
            ptr = kernel32.GlobalLock(handle)
            if not ptr:
                return False
            try:
                ctypes.memmove(ptr, blob, size)
            finally:
                kernel32.GlobalUnlock(handle)
            if not user32.SetClipboardData(CF_UNICODETEXT, handle):
                return False
            return True
        finally:
            user32.CloseClipboard()
    except Exception as exc:
        logger.debug("Windows clipboard text write failed: %s", exc)
        return False


def get_clipboard_text() -> str | None:
    import sys

    if sys.platform == "win32":
        import hermes_cli.clipboard as cb

        reader = getattr(cb, "_windows_get_text", _windows_get_text)
        return reader()
    return None


def set_clipboard_text(text: str) -> bool:
    import sys

    if not text or sys.platform != "win32":
        return False
    return _windows_set_text(text)


def apply_clipboard_fork_patch() -> None:
    import hermes_cli.clipboard as cb

    if getattr(cb, "_fork_clipboard_text_patch_applied", False):
        return
    cb.get_clipboard_text = get_clipboard_text  # type: ignore[attr-defined]
    cb.set_clipboard_text = set_clipboard_text  # type: ignore[attr-defined]
    cb._windows_get_text = _windows_get_text  # type: ignore[attr-defined]
    cb._windows_set_text = _windows_set_text  # type: ignore[attr-defined]
    cb._fork_clipboard_text_patch_applied = True  # type: ignore[attr-defined]
