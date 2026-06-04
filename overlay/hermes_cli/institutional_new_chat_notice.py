"""Reminder na SOUL-sync: start een nieuwe chat (system prompt vernieuwen)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_NOTICE_BASENAME = "institutional_new_chat_required.json"


def _hermes_state_dir() -> Path:
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
    if local.is_dir() or not (Path.home() / ".hermes").is_dir():
        return local
    return Path.home() / ".hermes"


def notice_path() -> Path:
    return _hermes_state_dir() / _NOTICE_BASENAME


def read_new_chat_notice() -> dict[str, Any] | None:
    path = notice_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def acknowledge_new_chat_notice() -> bool:
    """Clear reminder after /new or explicit ack. Returns True if a file was removed."""
    path = notice_path()
    if not path.is_file():
        return False
    try:
        path.unlink()
    except OSError:
        return False
    return True


def format_new_chat_notice_rich() -> str | None:
    """One-line Rich markup for CLI banner, or None if no reminder pending."""
    data = read_new_chat_notice()
    if not data:
        return None
    reason = str(data.get("reason") or "SOUL/presentatie gewijzigd").strip()
    smoke = str(
        data.get("smoke_test_prompt") or "docs/templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md"
    ).strip()
    return (
        "[bold #FFBF00]⚠ Nieuwe chat vereist[/] "
        f"({reason}). "
        "Bestaande sessies laden de oude system prompt. "
        "Gebruik [cyan]/new[/] of start een nieuwe sessie. "
        f"Rooktest: [dim]{smoke}[/]"
    )
