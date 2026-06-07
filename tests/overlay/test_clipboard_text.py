"""Windows clipboard text (paste in classic CLI)."""

import sys
from unittest.mock import MagicMock, patch

from hermes_cli.clipboard import get_clipboard_text, set_clipboard_text


def test_get_clipboard_text_non_windows():
    with patch.object(sys, "platform", "linux"):
        assert get_clipboard_text() is None


def test_set_clipboard_text_non_windows():
    with patch.object(sys, "platform", "linux"):
        assert set_clipboard_text("x") is False


def test_windows_get_text_via_ctypes():
    with patch.object(sys, "platform", "win32"):
        with patch("hermes_cli.clipboard._windows_get_text", return_value="hallo\nwereld"):
            assert get_clipboard_text() == "hallo\nwereld"
