"""Classic CLI status-bar per-prompt elapsed formatting (fork-owned for upstream-safe merges).

Fork default: time only (``26s``, ``1m 3s``) — no U+23F1/U+23F2 prefix. Enable emoji via
``display.show_prompt_timer_emoji`` or ``/timer-emoji`` for upstream parity.

``cli.py`` must delegate ``_format_prompt_elapsed`` here (never inline emoji) so
``scripts/verify_fork_status_bar_display.py`` passes after upstream merges.
"""

from __future__ import annotations

import math
import time
from typing import Any, Optional

# Width-1 timer glyphs (no variation selectors) — upstream parity when emoji enabled.
_EMOJI_LIVE = "\u23f1"
_EMOJI_FROZEN = "\u23f2"
_TIMER_EMOJI_CHARS = frozenset({_EMOJI_LIVE, _EMOJI_FROZEN})


def prompt_elapsed_contains_emoji(text: str) -> bool:
    """True if text includes status-bar timer emoji (U+23F1/U+23F2)."""
    return any(ch in _TIMER_EMOJI_CHARS for ch in (text or ""))


def _coerce_epoch_seconds(value: Any) -> Optional[float]:
    """Parse wall-clock epoch seconds; reject bool, non-numeric, and non-finite values."""
    if type(value) not in (int, float):  # bool is a subclass of int — exclude explicitly
        return None
    seconds = float(value)
    if not math.isfinite(seconds):
        return None
    return seconds


def _coerce_non_negative_seconds(value: Any) -> float:
    """Map duration inputs to a finite, non-negative second count (invalid → 0)."""
    if type(value) not in (int, float):
        return 0.0
    seconds = float(value)
    if not math.isfinite(seconds):
        return 0.0
    return max(0.0, seconds)


def _format_time_str(elapsed: float) -> str:
    elapsed = _coerce_non_negative_seconds(elapsed)
    days = int(elapsed // 86400)
    remaining = elapsed % 86400
    hours = int(remaining // 3600)
    remaining = remaining % 3600
    minutes = int(remaining // 60)
    seconds = int(remaining % 60)

    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s" if seconds else f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m {seconds}s" if seconds else f"{minutes}m"
    return f"{int(elapsed)}s"


def format_prompt_elapsed_status_bar(
    prompt_start_time: Optional[float],
    prompt_duration: float,
    *,
    live: bool = False,
    show_emoji: bool = False,
    now: Optional[float] = None,
) -> str:
    """Format per-prompt elapsed time for the status bar.

    Always returns a string. When ``show_emoji`` is False (fork default), returns
    only the time segment (e.g. ``26s``, ``1m 3s``) without leading emoji.

    Live elapsed uses ``now`` when finite; otherwise ``time.time()``. Non-finite
    ``prompt_start_time`` falls back to ``prompt_duration``. Negative elapsed is
    clamped via ``_format_time_str``.
    """
    duration_sec = _coerce_non_negative_seconds(prompt_duration)
    started_at = _coerce_epoch_seconds(prompt_start_time)

    if started_at is None and duration_sec <= 0.0:
        time_str = "0s"
        if show_emoji:
            return f"{_EMOJI_FROZEN} {time_str}"
        return time_str

    clock = _coerce_epoch_seconds(now) if now is not None else None
    if clock is None:
        clock = time.time()
    elapsed = (clock - started_at) if started_at is not None else duration_sec
    time_str = _format_time_str(elapsed)

    if not show_emoji:
        return time_str

    emoji = _EMOJI_LIVE if live else _EMOJI_FROZEN
    return f"{emoji} {time_str}"


def should_show_prompt_timer_emoji(show_emoji: Any) -> bool:
    """Return whether timer emoji prefix is enabled.

    Expects a bool from ``cli.py`` after ``is_truthy_value``; non-bool values are off.
    """
    return show_emoji is True
