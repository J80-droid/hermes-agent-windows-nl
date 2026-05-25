"""Unit tests for scripts/rag_pipeline/source_formats.py (collect_indexed_files)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAG_DIR = Path(__file__).resolve().parents[2] / "scripts" / "rag_pipeline"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from source_formats import (  # noqa: E402
    ALL_INDEXED_SUFFIXES,
    collect_indexed_files,
    route_for_suffix,
    supported_extension_globs,
)


class TestRouteForSuffix:
    def test_plain_md(self):
        assert route_for_suffix(".md") == "plain"

    def test_markitdown_pdf(self):
        assert route_for_suffix(".pdf") == "markitdown"

    def test_media_mp4(self):
        assert route_for_suffix(".mp4") == "media"

    def test_unknown_exe(self):
        assert route_for_suffix(".exe") == "unknown"


class TestCollectIndexedFiles:
    def test_collects_indexed_suffixes_only(self, tmp_path):
        (tmp_path / "ok.md").write_text("a", encoding="utf-8")
        (tmp_path / "skip.bin").write_bytes(b"\x00")
        sub = tmp_path / "nested"
        sub.mkdir()
        (sub / "b.txt").write_text("b", encoding="utf-8")
        files = collect_indexed_files(tmp_path)
        names = {p.name for p in files}
        assert names == {"ok.md", "b.txt"}

    def test_skips_pruned_directories(self, tmp_path):
        (tmp_path / "keep.md").write_text("x", encoding="utf-8")
        git = tmp_path / ".git"
        git.mkdir()
        (git / "secret.md").write_text("y", encoding="utf-8")
        names = {p.name for p in collect_indexed_files(tmp_path)}
        assert names == {"keep.md"}

    def test_deduplicates_same_file_via_resolve(self, tmp_path):
        f = tmp_path / "dup.md"
        f.write_text("x", encoding="utf-8")
        files = collect_indexed_files(tmp_path)
        assert len(files) == 1

    def test_nonexistent_root_returns_empty(self, tmp_path):
        missing = tmp_path / "nope"
        assert collect_indexed_files(missing) == []

    def test_sorted_case_insensitive(self, tmp_path):
        (tmp_path / "B.md").write_text("b", encoding="utf-8")
        (tmp_path / "a.md").write_text("a", encoding="utf-8")
        names = [p.name for p in collect_indexed_files(tmp_path)]
        assert names == ["a.md", "B.md"]

    def test_supported_globs_cover_all_indexed(self):
        globs = supported_extension_globs()
        assert len(globs) == len(ALL_INDEXED_SUFFIXES)
