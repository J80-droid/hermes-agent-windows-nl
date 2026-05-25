"""Bounded message snapshots for background memory/skill review."""

from __future__ import annotations

import os
from typing import Any


def background_review_message_limit() -> int:
    raw = (os.environ.get("HERMES_BG_REVIEW_MAX_MESSAGES") or "40").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 40


def snapshot_messages_for_background_review(
    messages: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Return a shallow copy of the tail of ``messages`` for review threads."""
    if not messages:
        return []
    limit = background_review_message_limit()
    if limit <= 0 or len(messages) <= limit:
        return list(messages)
    return list(messages[-limit:])
