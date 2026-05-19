"""Gedeelde broncitatie-weergave (CLI markdown-chips)."""

from __future__ import annotations

import re
from pathlib import Path

_BRON_CITATION = re.compile(r"(?<!`)(\[Bron:\s*([^\]]+?)\s*\])(?!`)")


def source_basename(source: str) -> str:
    return Path(str(source).replace("\\", "/")).name or "Onbekend"


def inline_citeer_sjabloon(source: str) -> str:
    return f"[Bron: {source_basename(source)}]"


def wrap_bron_citations_for_markdown_display(text: str) -> str:
    """Zet niet-gebacktickte `[Bron: …]` tussen backticks voor inline-code chips."""
    if not text:
        return text
    return _BRON_CITATION.sub(r"`\1`", text)
