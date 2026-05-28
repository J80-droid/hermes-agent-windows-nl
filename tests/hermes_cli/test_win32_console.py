"""Windows console helpers."""

import sys
from unittest.mock import patch

from hermes_cli import win32_console as wc


def test_configure_skips_non_windows():
    with patch.object(sys, "platform", "linux"):
        assert wc.configure_interactive_console() is False


def test_release_terminal_capture_noop_off_windows():
    with patch.object(sys, "platform", "linux"):
        wc.release_terminal_capture()


def test_align_viewport_skips_non_windows():
    with patch.object(sys, "platform", "linux"):
        assert wc.align_win32_viewport_to_bottom() is False


def test_finalize_console_after_chat_noop_off_windows():
    with patch.object(sys, "platform", "linux"):
        wc.finalize_console_after_chat(object())


def test_clear_for_exit_noop_off_windows():
    with patch.object(sys, "platform", "linux"):
        wc.clear_win32_console_for_exit()
