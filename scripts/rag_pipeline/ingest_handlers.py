"""Conversie-handlers: MarkItDown met optionele pandoc-fallback voor Office/OpenDocument."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from html.parser import HTMLParser
from pathlib import Path

from markitdown import MarkItDown

from ingest_ocr import convert_timeout_sec, extract_fallback_text


def _pdf_pymupdf_first_mb() -> float:
    """PDF's groter dan dit (MB) eerst via PyMuPDF/OCR — voorkomt MarkItDown-hang (FontBBox)."""
    raw = (os.environ.get("HERMES_RAG_PDF_PYMUPDF_FIRST_MB") or "8").strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 8.0


def _should_pymupdf_first(path: Path) -> bool:
    if path.suffix.lower() != ".pdf":
        return False
    limit_mb = _pdf_pymupdf_first_mb()
    if limit_mb <= 0:
        return False
    try:
        size_mb = path.stat().st_size / (1024 * 1024)
    except OSError:
        return False
    return size_mb >= limit_mb

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


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data and data.strip():
            self._parts.append(data.strip())

    def text(self) -> str:
        return "\n".join(self._parts)


def _html_to_text(path: Path) -> tuple[str, str | None]:
    """Eenvoudige HTML-tekstextractie als MarkItDown faalt (mindmaps, export)."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return "", f"{type(e).__name__}: {e}"
    parser = _HTMLTextExtractor()
    try:
        parser.feed(raw)
        parser.close()
    except Exception as e:
        return "", f"{type(e).__name__}: {e}"
    text = re.sub(r"\n{3,}", "\n\n", parser.text()).strip()
    if len(text) < 20:
        return "", "te weinig tekst na HTML-parse"
    return text, None


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


def _try_fallback(path: Path) -> tuple[str, str | None, str]:
    try:
        from ingest_live_progress import set_step

        set_step("OCR/PyMuPDF")
    except ImportError:
        pass
    fallback, ocr_note = extract_fallback_text(path)
    if fallback.strip():
        return fallback, None, ocr_note or "fallback"
    return "", ocr_note or "lege fallback", ocr_note or ""


def _convert_document_impl(path: Path) -> tuple[str, str | None, str]:
    """Returns (text, error, ocr_method)."""
    if _should_pymupdf_first(path):
        text, err, method = _try_fallback(path)
        if text.strip():
            return text, None, method
        # Kleine rest via MarkItDown als fallback leeg blijft
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

    fallback, fb_err, ocr_note = _try_fallback(path)
    if fallback.strip():
        return fallback, None, ocr_note or "fallback"
    if path.suffix.lower() in (".html", ".htm", ".xhtml"):
        html_text, html_err = _html_to_text(path)
        if html_text.strip():
            return html_text, None, "html-parser"
    combined = err or ""
    if fb_err:
        combined = f"{combined}; {fb_err}" if combined else fb_err
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
            text, fb_err, method = _try_fallback(path)
            if text.strip():
                return text, None, method
            return "", f"timeout na {int(timeout)}s; {fb_err or 'geen OCR-tekst'}", method
