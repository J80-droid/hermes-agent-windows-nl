"""Conversie-handlers: MarkItDown met optionele pandoc-fallback voor Office/OpenDocument."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path

from markitdown import MarkItDown

from ingest_ocr import convert_timeout_sec, extract_fallback_text

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


def _convert_document_impl(path: Path) -> tuple[str, str | None, str]:
    """Returns (text, error, ocr_method)."""
    try:
        from ingest_live_progress import set_step

        set_step("MarkItDown")
    except ImportError:
        pass
    text, err = convert_markitdown_one(path)
    if err is None and text.strip():
        return text, None, ""
    suf = path.suffix.lower()
    if suf in PANDOC_FALLBACK_SUFFIXES:
        ptext, perr = _pandoc_to_markdown(path)
        if perr is None and ptext.strip():
            return ptext, None, ""
        combined = err or ""
        if perr:
            combined = f"{combined}; pandoc: {perr}" if combined else f"pandoc: {perr}"
        text = text or ptext
        err = combined or err
    if text.strip():
        return text, None, ""

    try:
        from ingest_live_progress import set_step

        set_step("OCR/PyMuPDF")
    except ImportError:
        pass
    fallback, ocr_note = extract_fallback_text(path)
    if fallback.strip():
        return fallback, None, ocr_note or "fallback"
    combined = err or ""
    if ocr_note:
        combined = f"{combined}; {ocr_note}" if combined else ocr_note
    return text or "", combined or "lege conversie", ocr_note or ""


def convert_document(path: Path) -> tuple[str, str | None, str]:
    """MarkItDown → pandoc (Office) → PyMuPDF/Tesseract. Returns (text, err, ocr_method)."""
    timeout = convert_timeout_sec()
    if timeout <= 0:
        t, e, m = _convert_document_impl(path)
        return t, e, m
    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(_convert_document_impl, path)
        try:
            t, e, m = fut.result(timeout=timeout)
            return t, e, m
        except FuturesTimeoutError:
            return "", f"timeout na {int(timeout)}s", ""
