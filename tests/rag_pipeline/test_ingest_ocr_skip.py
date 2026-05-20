"""Tests voor OCR-fallback stubs en skip-rapport."""

from __future__ import annotations

from pathlib import Path

from ingest_ocr import stub_text_from_empty_file
from ingest_skip_report import SkipReport


def test_stub_text_from_empty_file(tmp_path: Path):
    p = tmp_path / "Productie 10 - Zie DEEL F.txt"
    p.write_bytes(b"")
    stub = stub_text_from_empty_file(p)
    assert stub is not None
    assert "Productie 10" in stub
    assert "Stub" in stub


def test_stub_none_when_file_has_content(tmp_path: Path):
    p = tmp_path / "note.txt"
    p.write_text("echte inhoud", encoding="utf-8")
    assert stub_text_from_empty_file(p) is None


def test_skip_report_write(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HERMES_LANCEDB_PATH", str(tmp_path / "ldb"))
    root = tmp_path / "raw"
    root.mkdir()
    fp = root / "doc.pdf"
    fp.write_bytes(b"%PDF")
    report = SkipReport()
    report.add(fp, root, reason="empty_after_convert", detail="pymupdf: geen tekst")
    out = report.write()
    assert out.is_file()
    md = out.with_suffix(".md")
    assert md.is_file()
    assert "doc.pdf" in md.read_text(encoding="utf-8")
