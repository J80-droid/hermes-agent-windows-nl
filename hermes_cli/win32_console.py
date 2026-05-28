"""Windows console helpers for classic Hermes CLI (prompt_toolkit).

Used from hermes_chat.cmd in the same python.exe / cmd session as the chat.
"""

from __future__ import annotations

import sys

_STD_OUTPUT_HANDLE = -11
_STD_INPUT_HANDLE = -10
_ENABLE_QUICK_EDIT_MODE = 0x0040
_ENABLE_EXTENDED_FLAGS = 0x0080
_ENABLE_MOUSE_INPUT = 0x0010


def configure_interactive_console() -> bool:
    """QuickEdit off + no mouse capture (WT scrollbar / markeermodus)."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        k32 = ctypes.windll.kernel32
        h_in = k32.GetStdHandle(_STD_INPUT_HANDLE)
        if h_in in (0, -1):
            return False
        mode = ctypes.c_uint32()
        if not k32.GetConsoleMode(h_in, ctypes.byref(mode)):
            return False
        m = int(mode.value)
        m &= ~(_ENABLE_QUICK_EDIT_MODE | _ENABLE_MOUSE_INPUT)
        m |= _ENABLE_EXTENDED_FLAGS
        k32.SetConsoleMode(h_in, m)
        return True
    except Exception:
        return False


def align_win32_viewport_to_bottom() -> bool:
    """Scroll the visible console window to the bottom of the screen buffer.

    After maximize/launcher scripts the viewport can sit mid-buffer; prompt_toolkit
    then paints at the wrong row and each keystroke appears to jump the screen up.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        class COORD(ctypes.Structure):
            _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

        class SMALL_RECT(ctypes.Structure):
            _fields_ = [
                ("Left", ctypes.c_short),
                ("Top", ctypes.c_short),
                ("Right", ctypes.c_short),
                ("Bottom", ctypes.c_short),
            ]

        class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
            _fields_ = [
                ("dwSize", COORD),
                ("dwCursorPosition", COORD),
                ("wAttributes", wintypes.WORD),
                ("srWindow", SMALL_RECT),
                ("dwMaximumWindowSize", COORD),
            ]

        k32 = ctypes.windll.kernel32
        h_out = k32.GetStdHandle(_STD_OUTPUT_HANDLE)
        if h_out in (0, -1):
            return False
        info = CONSOLE_SCREEN_BUFFER_INFO()
        if not k32.GetConsoleScreenBufferInfo(h_out, ctypes.byref(info)):
            return False
        win_h = int(info.srWindow.Bottom) - int(info.srWindow.Top) + 1
        if win_h < 1:
            return False
        buf_h = int(info.dwSize.Y)
        top = max(0, buf_h - win_h)
        rect = SMALL_RECT(
            info.srWindow.Left,
            top,
            info.srWindow.Right,
            top + win_h - 1,
        )
        if not k32.SetConsoleWindowInfo(h_out, True, ctypes.byref(rect)):
            return False
        k32.SetConsoleCursorPosition(
            h_out,
            COORD(0, min(buf_h - 1, top + win_h - 1)),
        )
        return True
    except Exception:
        return False


def release_terminal_capture() -> None:
    """Leave mouse/alt-screen modes so the window can be closed normally."""
    if sys.platform != "win32":
        return
    seq = (
        "\x1b[?1006l\x1b[?1003l\x1b[?1002l\x1b[?1000l"
        "\x1b[?1004l\x1b[?2004l\x1b[?1049l\x1b[<u\x1b[>4m\x1b[0m\x1b[?25h"
    )
    try:
        sys.stdout.write(seq)
        sys.stdout.flush()
    except Exception:
        pass
