"""Conversie-handlers: MarkItDown met optionele pandoc-fallback voor Office/OpenDocument."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from markitdown import MarkItDown

# Als MarkItDown faalt, probeer pandoc (indien op PATH)
PANDOC_FALLBACK_SUFFIXES: frozenset[str] = frozenset(
    {
        ".doc",
        ".rtf",
        ".odt",
        ".ods",
        ".odp",
        ".ppt",
        ".xls",
    }
)


def convert_markitdown_one(path: Path) -> tuple[str, str | None]:
    """Eén MarkItDown-conversie (thread-safe: eigen instantie per aanroep)."""
    try:
        mc = MarkItDown()
        result = mc.convert(str(path))
        raw_text = getattr(result, "text_content", None)
        text = raw_text if isinstance(raw_text, str) else ""
        return (text, None)
    except Exception as e:
        return ("", f"{type(e).__name__}: {e}")


def _pandoc_to_markdown(path: Path) -> tuple[str, str | None]:
    pandoc = shutil.which("pandoc")
    if pandoc is None:
        return ("", "pandoc niet op PATH")
    with tempfile.TemporaryDirectory() as tmp:
        out_md = Path(tmp) / "out.md"
        cmd = [pandoc, str(path), "-t", "markdown", "-o", str(out_md)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "pandoc mislukt")[:500]
            return ("", err)
        if not out_md.is_file():
            return ("", "pandoc produceerde geen output")
        return (out_md.read_text(encoding="utf-8", errors="replace"), None)


def convert_document(path: Path) -> tuple[str, str | None]:
    """MarkItDown eerst; bij falen optioneel pandoc voor legacy Office/OpenDocument."""
    text, err = convert_markitdown_one(path)
    if err is None and text.strip():
        return text, None
    suf = path.suffix.lower()
    if suf not in PANDOC_FALLBACK_SUFFIXES:
        return text, err
    ptext, perr = _pandoc_to_markdown(path)
    if perr is None and ptext.strip():
        return ptext, None
    combined = err or ""
    if perr:
        combined = f"{combined}; pandoc: {perr}" if combined else f"pandoc: {perr}"
    return text or ptext, combined or "lege conversie"
