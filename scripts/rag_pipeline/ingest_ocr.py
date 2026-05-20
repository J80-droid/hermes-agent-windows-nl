"""Fallback tekstextractie als MarkItDown leeg blijft (PDF-tekstlaag, PyMuPDF, optioneel Tesseract)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from source_formats import MARKITDOWN_SUFFIXES

_IMAGE_SUFFIXES = frozenset(
    s for s in MARKITDOWN_SUFFIXES if s in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic"}
)
_PDF_SUFFIXES = frozenset({".pdf"})


def _env_truthy(name: str, *, default: str = "1") -> bool:
    raw = (os.environ.get(name) if os.environ.get(name) is not None else default).strip()
    return raw.lower() not in ("0", "false", "no", "n", "off")


def ocr_tesseract_enabled() -> bool:
    """Tesseract-OCR (scans/beeld-PDF). Uit met HERMES_RAG_OCR=0."""
    return _env_truthy("HERMES_RAG_OCR", default="1")


def pymupdf_fallback_enabled() -> bool:
    """PyMuPDF-tekstlaag na lege MarkItDown. Uit met HERMES_RAG_PYMUPDF=0."""
    return _env_truthy("HERMES_RAG_PYMUPDF", default="1")


def pymupdf_max_pages() -> int:
    raw = (os.environ.get("HERMES_RAG_PYMUPDF_MAX_PAGES") or "80").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 80


def convert_timeout_sec() -> float:
    raw = (os.environ.get("HERMES_RAG_CONVERT_TIMEOUT_SEC") or "300").strip()
    try:
        v = float(raw)
    except ValueError:
        v = 600.0
    return max(0.0, v)


def _extract_pdf_pymupdf(path: Path) -> tuple[str, str]:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return "", "pymupdf niet geïnstalleerd (pip install pymupdf)"
    try:
        doc = fitz.open(path)
        try:
            limit = pymupdf_max_pages()
            n = min(len(doc), limit)
            parts = [doc.load_page(i).get_text("text") for i in range(n)]
            if len(doc) > n:
                parts.append(f"[… {len(doc) - n} pagina's overgeslagen (HERMES_RAG_PYMUPDF_MAX_PAGES={limit})]")
        finally:
            doc.close()
        text = "\n".join(p for p in parts if p).strip()
        if text:
            return text, "pymupdf"
        return "", "pymupdf: geen tekstlaag"
    except Exception as e:
        return "", f"pymupdf: {type(e).__name__}: {e}"


def _extract_image_tesseract(path: Path) -> tuple[str, str]:
    if not shutil.which("tesseract"):
        return "", "tesseract niet op PATH (install Tesseract OCR voor scans)"
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return "", "pytesseract/Pillow niet geïnstalleerd (pip install pytesseract pillow)"
    try:
        with Image.open(path) as im:
            text = pytesseract.image_to_string(im, lang=os.environ.get("HERMES_RAG_OCR_LANG", "nld+eng"))
        text = (text or "").strip()
        if text:
            return text, "tesseract"
        return "", "tesseract: geen tekst herkend"
    except Exception as e:
        return "", f"tesseract: {type(e).__name__}: {e}"


def _extract_pdf_tesseract(path: Path, *, max_pages: int = 25) -> tuple[str, str]:
    if not shutil.which("tesseract"):
        return "", "tesseract niet op PATH"
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError as e:
        return "", f"OCR-deps ontbreken: {e}"
    try:
        doc = fitz.open(path)
        try:
            n = min(len(doc), max_pages)
            parts: list[str] = []
            for i in range(n):
                pix = doc.load_page(i).get_pixmap(matrix=fitz.Matrix(2, 2))
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                parts.append(
                    pytesseract.image_to_string(
                        img, lang=os.environ.get("HERMES_RAG_OCR_LANG", "nld+eng")
                    )
                )
        finally:
            doc.close()
        text = "\n".join(p for p in parts if p).strip()
        if text:
            return text, f"tesseract-pdf ({n} pag.)"
        return "", "tesseract-pdf: geen tekst"
    except Exception as e:
        return "", f"tesseract-pdf: {type(e).__name__}: {e}"


def extract_fallback_text(path: Path) -> tuple[str, str | None]:
    """Probeer tekst na lege MarkItDown. Returns (text, method_or_error_detail)."""
    suf = path.suffix.lower()
    notes: list[str] = []

    if suf in _PDF_SUFFIXES and pymupdf_fallback_enabled():
        text, note = _extract_pdf_pymupdf(path)
        notes.append(note)
        if text.strip():
            return text, note

    if ocr_tesseract_enabled():
        if suf in _IMAGE_SUFFIXES:
            text, note = _extract_image_tesseract(path)
            notes.append(note)
            if text.strip():
                return text, note
        if suf in _PDF_SUFFIXES:
            text, note = _extract_pdf_tesseract(path)
            notes.append(note)
            if text.strip():
                return text, note

    return "", "; ".join(notes) if notes else "geen fallback beschikbaar"


def stub_text_from_empty_file(path: Path) -> str | None:
    """0-byte of whitespace-only .txt: indexeer bestandsnaam als verwijzing."""
    try:
        if path.stat().st_size > 0:
            raw = path.read_text(encoding="utf-8", errors="replace")
            if raw.strip():
                return None
        else:
            raw = ""
    except OSError:
        return None
    stem = path.stem.strip()
    if not stem:
        return None
    return (
        "[Stub — geen bestandsinhoud; metadata uit bestandsnaam]\n"
        f"Titel/bestandsnaam: {stem}\n"
        f"Type: {path.suffix or '(geen extensie)'}"
    )
