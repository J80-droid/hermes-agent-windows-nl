"""Gedeelde broncitatie-weergave (CLI markdown-chips, optionele file-links)."""

from __future__ import annotations

import os
import re
from pathlib import Path
_BRON_CITATION = re.compile(r"(?<!`)(\[Bron:\s*([^\]]+?)\s*\])(?!`)")


def source_basename(source: str) -> str:
    return Path(str(source).replace("\\", "/")).name or "Onbekend"


def _raw_source_root() -> Path | None:
    raw = (os.environ.get("HERMES_RAG_RAW_SOURCE") or "").strip()
    if not raw:
        return None
    return Path(os.path.expanduser(os.path.expandvars(raw)))


def bron_source_path(source: str) -> Path | None:
    root = _raw_source_root()
    if root is None:
        return None
    rel = str(source).replace("\\", "/").lstrip("/")
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def bron_file_uri(source: str) -> str | None:
    path = bron_source_path(source)
    if path is None:
        return None
    return Path(path).as_uri()


def inline_citeer_sjabloon(source: str) -> str:
    if _env_truthy("HERMES_RAG_BRON_FILE_LINKS"):
        uri = bron_file_uri(source)
        if uri:
            name = source_basename(source)
            return f"[Bron: {name}]({uri})"
    return f"[Bron: {source_basename(source)}]"


def _env_truthy(name: str) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    return raw in ("1", "true", "yes", "y", "on")


def wrap_bron_citations_for_markdown_display(text: str) -> str:
    """Zet niet-gebacktickte `[Bron: …]` tussen backticks voor inline-code chips."""
    if not text:
        return text
    return _BRON_CITATION.sub(r"`\1`", text)
