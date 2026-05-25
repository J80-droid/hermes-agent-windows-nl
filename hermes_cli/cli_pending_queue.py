"""Classic CLI ``_pending_input`` queue — display, FIFO management, hint/status UI.

Used by ``HermesCLI`` (``cli.py``) for follow-up prompts while the agent runs.
Storage remains ``queue.Queue`` on ``self._pending_input``; this module only peeks
(``list(q.queue)``) or mutates via ``get_nowait`` (pop/clear) — never changes FIFO
semantics of ``process_loop``.

Payload shapes:
  - ``str``: user text or slash command (shown as ``[cmd] /…`` when applicable)
  - ``(text, [Path, ...])``: text plus attached images (``[N images]`` suffix)

Public API:
  - ``normalize_pending_entry``, ``snapshot_pending_queue``, ``pending_queue_depth``
  - ``render_queue_lines`` (hint max 2 rows; list max 8 + overflow hint)
  - ``pop_pending_head``, ``clear_pending_queue``
  - ``queue_status_fragment``, ``enqueue_ack_message``
  - ``hint_panel_height``, ``hint_panel_fragments``, ``format_removed_preview``

Tests: ``tests/hermes_cli/test_cli_pending_queue.py`` (88+ cases).
E2E: ``audits/RUN_CLI_PENDING_QUEUE_E2E.bat`` (17 scenarios, no live API).
"""

from __future__ import annotations

import re
from queue import Empty, Queue
from typing import Any, List, Optional, Sequence, Tuple

_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1a\x1c-\x1f\x7f]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text).replace("\r", "").replace("\n", " ")


def _looks_like_slash_command(text: str) -> bool:
    if not text or not text.startswith("/"):
        return False
    first_word = text.split()[0]
    return "/" not in first_word[1:]


def normalize_pending_entry(entry: Any) -> str:
    """Turn a queue payload into a single-line label for display."""
    if isinstance(entry, tuple):
        if not entry:
            return "(empty)"
        text = str(entry[0] or "").strip()
        images = entry[1] if len(entry) > 1 else None
        if images is not None and not isinstance(images, (str, bytes)):
            try:
                count = len(images)  # type: ignore[arg-type]
            except TypeError:
                count = 1
            suffix = f" [{count} image{'s' if count != 1 else ''}]"
            text = (text + suffix).strip() if text else suffix.strip()
    else:
        text = str(entry or "").strip()
    if not text:
        return "(empty)"
    if _looks_like_slash_command(text):
        return f"[cmd] {text}"
    return text


def snapshot_pending_queue(q: Optional[Queue]) -> List[str]:
    """Peek FIFO order without consuming."""
    if q is None:
        return []
    try:
        raw = list(q.queue)
    except Exception:
        return []
    return [normalize_pending_entry(item) for item in raw]


def pending_queue_depth(q: Optional[Queue]) -> int:
    if q is None:
        return 0
    try:
        return q.qsize()
    except Exception:
        try:
            return len(q.queue)
        except Exception:
            return 0


def format_queue_preview(text: str, width: int) -> str:
    """Single-line preview with ellipsis."""
    width = max(8, width)
    clean = _CONTROL_RE.sub("", _strip_ansi(text)).strip()
    if not clean:
        return ""
    if len(clean) <= width:
        return clean
    if width <= 1:
        return "…"
    return clean[: width - 1] + "…"


def render_queue_lines(
    entries: Sequence[str],
    *,
    width: int,
    max_visible: int = 2,
    list_mode: bool = False,
) -> List[str]:
    """Compact numbered lines for hint panel or /queue list."""
    if not entries:
        return ["  (queue empty)"]

    preview_width = min(72, max(16, width - 12))
    lines: List[str] = []
    cap = 8 if list_mode else max(1, max_visible)
    show = entries[: min(len(entries), cap)]

    lines.append(f"  queued ({len(entries)})")
    if not list_mode and width < 60:
        lines.append("  /queue list")
        return lines

    for idx, entry in enumerate(show, start=1):
        preview = format_queue_preview(entry, preview_width)
        lines.append(f"  {idx}. {preview}")

    remaining = len(entries) - len(show)
    if remaining > 0:
        suffix = " · /queue list" if not list_mode else " (use /queue pop)"
        lines.append(f"  …and {remaining} more{suffix}")

    return lines


def pop_pending_head(q: Optional[Queue]) -> Optional[str]:
    """Remove FIFO head without blocking (no depth pre-check — avoids qsize races)."""
    if q is None:
        return None
    try:
        raw = q.get_nowait()
    except Empty:
        return None
    return normalize_pending_entry(raw)


def clear_pending_queue(q: Optional[Queue]) -> int:
    """Drain queue; return count removed."""
    if q is None:
        return 0
    removed = 0
    while True:
        try:
            q.get_nowait()
            removed += 1
        except Empty:
            break
    return removed


def queue_status_fragment(depth: int) -> Optional[str]:
    if depth <= 0:
        return None
    return f"queue:{depth}"


def enqueue_ack_message(
    payload: Any,
    *,
    depth: int,
    agent_running: bool,
) -> str:
    """Format user-facing ack after enqueue."""
    label = normalize_pending_entry(payload)
    preview = format_queue_preview(label, 72)
    when = "next turn" if agent_running else "when idle"
    return f"[{depth}] Queued for {when}: {preview}"


def hint_panel_height(depth: int, terminal_width: int) -> int:
    if depth <= 0:
        return 0
    if terminal_width < 60:
        # Matches render_queue_lines narrow layout: header + "/queue list"
        return 2
    visible = min(2, depth)
    extra = 1 if depth > visible else 0
    return 1 + visible + extra


def format_removed_preview(label: str, *, max_len: int = 80) -> str:
    """Truncate pop/clear feedback without breaking multibyte or ANSI edge cases."""
    clean = _CONTROL_RE.sub("", _strip_ansi(label)).strip()
    if len(clean) <= max_len:
        return clean
    return format_queue_preview(clean, max_len)


def hint_panel_fragments(
    entries: Sequence[str],
    *,
    terminal_width: int,
) -> List[Tuple[str, str]]:
    """Formatted-text tuples for prompt_toolkit hint window."""
    lines = render_queue_lines(entries, width=terminal_width, max_visible=2, list_mode=False)
    return [("class:hint", line) for line in lines]
