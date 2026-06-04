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

_TERMINAL_MODE_RESET_SEQ = (
    "\x1b[?1006l\x1b[?1003l\x1b[?1002l\x1b[?1000l"
    "\x1b[?1004l\x1b[?2004l\x1b[?1049l\x1b[<u\x1b[>4m\x1b[0m\x1b[?25h"
)


def _console_screen_info():
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
        return None, None, None
    info = CONSOLE_SCREEN_BUFFER_INFO()
    if not k32.GetConsoleScreenBufferInfo(h_out, ctypes.byref(info)):
        return None, None, None
    return k32, h_out, info


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
    """Scroll the visible console window to the bottom of the screen buffer."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        k32, h_out, info = _console_screen_info()
        if not k32:
            return False
        win_h = int(info.srWindow.Bottom) - int(info.srWindow.Top) + 1
        if win_h < 1:
            return False
        buf_h = int(info.dwSize.Y)
        top = max(0, buf_h - win_h)

        class SMALL_RECT(ctypes.Structure):
            _fields_ = [
                ("Left", ctypes.c_short),
                ("Top", ctypes.c_short),
                ("Right", ctypes.c_short),
                ("Bottom", ctypes.c_short),
            ]

        class COORD(ctypes.Structure):
            _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

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


def clear_win32_console_for_exit() -> None:
    """Full screen + scrollback reset (alleen RESET_TERMINAL / noodherstel)."""
    try:
        sys.stdout.write("\x1b[2J\x1b[3J\x1b[H")
        sys.stdout.flush()
    except Exception:
        pass


def _reset_modes_via_prompt_toolkit_output(app) -> None:
    """VT reset via Win32Output (geen zichtbare ?[... garbage op stdout)."""
    if app is None:
        return
    try:
        output = app.renderer.output
        if hasattr(output, "write_raw"):
            output.write_raw(_TERMINAL_MODE_RESET_SEQ)
            output.flush()
        elif hasattr(output, "write"):
            output.write(_TERMINAL_MODE_RESET_SEQ)
            output.flush()
    except Exception:
        pass


def release_terminal_capture() -> None:
    """Leave mouse/alt-screen modes so the window can be closed normally."""
    if sys.platform == "win32":
        configure_interactive_console()
        return
    try:
        sys.stdout.write(_TERMINAL_MODE_RESET_SEQ)
        sys.stdout.flush()
    except Exception:
        pass


def finalize_console_after_chat(app=None, *, preserve_scrollback: bool = True) -> None:
    """Tear down prompt_toolkit; keep chat scrollback; position cursor for exit footer."""
    if sys.platform != "win32":
        return
    if app is not None:
        _reset_modes_via_prompt_toolkit_output(app)
        try:
            app.renderer.reset(leave_alternate_screen=False)
        except Exception:
            pass
    configure_interactive_console()
    if not preserve_scrollback:
        clear_win32_console_for_exit()
    elif app is not None:
        align_win32_viewport_to_bottom()
