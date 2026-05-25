"""Conversie-handlers: MarkItDown met optionele pandoc-fallback voor Office/OpenDocument.

Pijplijn (early return): grote PDF → OCR → MarkItDown → pandoc (Office) → OCR/PyMuPDF → HTML-parser.
Publieke entry: ``convert_document``; timeout per bron via ``ingest_runtime.run_file_job``.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path

from markitdown import MarkItDown

from ingest_ocr import extract_fallback_text

_markitdown_converter: MarkItDown | None = None


def get_markitdown_converter() -> MarkItDown:
    """Herbruikbare MarkItDown-instantie per ingest-run (proces)."""
    global _markitdown_converter
    if _markitdown_converter is None:
        _markitdown_converter = MarkItDown()
    return _markitdown_converter


def reset_markitdown_converter() -> None:
    """Tests: reset gedeelde converter."""
    global _markitdown_converter
    _markitdown_converter = None


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

_HTML_SUFFIXES = frozenset({".html", ".htm", ".xhtml"})


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data and data.strip():
            self._parts.append(data.strip())

    def text(self) -> str:
        return "\n".join(self._parts)


def _notify_conversion_step(step: str) -> None:
    try:
        from ingest_live_progress import set_step

        set_step(step)
    except ImportError:
        pass


def _combine_conversion_errors(*parts: str | None) -> str:
    combined = ""
    for part in parts:
        if not part:
            continue
        combined = f"{combined}; {part}" if combined else part
    return combined


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
    """Eén MarkItDown-conversie (gedeelde instantie; ingest is sequentieel per bron)."""
    try:
        result = get_markitdown_converter().convert(str(path))
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
    _notify_conversion_step("OCR/PyMuPDF")
    fallback, ocr_note = extract_fallback_text(path)
    if fallback.strip():
        return fallback, None, ocr_note or "fallback"
    return "", ocr_note or "lege fallback", ocr_note or ""


def _try_pymupdf_first_path(path: Path) -> tuple[str, str | None, str] | None:
    """Grote PDF's eerst via OCR; None = door naar MarkItDown-keten."""
    if not _should_pymupdf_first(path):
        return None
    text, _err, method = _try_fallback(path)
    if not text.strip():
        return None
    return text, None, method


def _apply_pandoc_office_fallback(path: Path, text: str, err: str | None) -> tuple[str, str | None]:
    """Werk text/err bij na pandoc-poging (Office/OpenDocument-suffixen)."""
    if path.suffix.lower() not in PANDOC_FALLBACK_SUFFIXES:
        return text, err

    ptext, perr = _pandoc_to_markdown(path)
    if perr is None and ptext.strip():
        return ptext, None

    combined = err or ""
    if perr:
        combined = f"{combined}; pandoc: {perr}" if combined else f"pandoc: {perr}"
    return text or ptext, combined or err


def _try_html_parser_fallback(path: Path) -> tuple[str, str | None, str] | None:
    if path.suffix.lower() not in _HTML_SUFFIXES:
        return None
    html_text, html_err = _html_to_text(path)
    if not html_text.strip():
        return None
    return html_text, None, "html-parser"


def _convert_document_impl(path: Path) -> tuple[str, str | None, str]:
    """Returns (text, error, ocr_method)."""
    fast_path = _try_pymupdf_first_path(path)
    if fast_path is not None:
        return fast_path

    _notify_conversion_step("MarkItDown")
    text, err = convert_markitdown_one(path)
    if err is None and text.strip():
        return text, None, ""

    text, err = _apply_pandoc_office_fallback(path, text, err)
    if text.strip():
        return text, None, ""

    fallback, fb_err, ocr_note = _try_fallback(path)
    if fallback.strip():
        return fallback, None, ocr_note or "fallback"

    html_result = _try_html_parser_fallback(path)
    if html_result is not None:
        return html_result

    combined = _combine_conversion_errors(err, fb_err)
    return text or "", combined or "lege conversie", ocr_note or ""


def convert_document(path: Path) -> tuple[str, str | None, str]:
    """MarkItDown → pandoc (Office) → PyMuPDF/Tesseract. Returns (text, err, ocr_method).

    Timeout wordt afgedwongen door ``ingest_runtime.run_file_job`` (één executor-laag).
    """
    return _convert_document_impl(path)
