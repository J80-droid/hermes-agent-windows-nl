"""Unit tests for IngestState.needs_processing (tuple + content_hash)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

RAG_DIR = Path(__file__).resolve().parents[2] / "scripts" / "rag_pipeline"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from ingest_state import IngestState, normalize_relative_source  # noqa: E402


@pytest.fixture
def state():
    return IngestState()


class TestNeedsProcessing:
    def test_no_prior_entry_always_process(self, state, tmp_path):
        f = tmp_path / "new.md"
        f.write_text("hello", encoding="utf-8")
        need, h = state.needs_processing("new.md", f)
        assert need is True
        assert h is None

    def test_incremental_disabled_always_process(self, state, tmp_path, monkeypatch):
        monkeypatch.setenv("HERMES_RAG_FORCE_FULL", "1")
        f = tmp_path / "a.md"
        f.write_text("x", encoding="utf-8")
        st = f.stat()
        state.entries["a.md"] = {
            "mtime_ns": st.st_mtime_ns,
            "size": st.st_size,
            "content_hash": "same",
        }
        need, h = state.needs_processing("a.md", f)
        assert need is True
        assert h is None

    def test_unchanged_mtime_and_size_skips(self, state, tmp_path, monkeypatch):
        monkeypatch.setenv("HERMES_RAG_FORCE_FULL", "0")
        monkeypatch.setenv("HERMES_RAG_INCREMENTAL", "1")
        f = tmp_path / "stable.md"
        f.write_text("unchanged", encoding="utf-8")
        st = f.stat()
        state.entries["stable.md"] = {
            "mtime_ns": st.st_mtime_ns,
            "size": st.st_size,
            "content_hash": "abc",
        }
        need, h = state.needs_processing("stable.md", f)
        assert need is False
        assert h is None

    def test_mtime_change_recomputes_hash(self, state, tmp_path, monkeypatch):
        monkeypatch.setenv("HERMES_RAG_FORCE_FULL", "0")
        f = tmp_path / "chg.md"
        f.write_text("v1", encoding="utf-8")
        st = f.stat()
        state.entries["chg.md"] = {
            "mtime_ns": st.st_mtime_ns - 1,
            "size": st.st_size,
            "content_hash": "old",
        }
        with patch("ingest_state.file_content_fingerprint", return_value="newfp"):
            need, h = state.needs_processing("chg.md", f)
        assert need is True
        assert h == "newfp"

    def test_same_hash_after_mtime_change_skips(self, state, tmp_path, monkeypatch):
        monkeypatch.setenv("HERMES_RAG_FORCE_FULL", "0")
        f = tmp_path / "same.md"
        f.write_text("data", encoding="utf-8")
        st = f.stat()
        state.entries["same.md"] = {
            "mtime_ns": st.st_mtime_ns - 999,
            "size": st.st_size,
            "content_hash": "fp123",
        }
        with patch("ingest_state.file_content_fingerprint", return_value="fp123"):
            need, h = state.needs_processing("same.md", f)
        assert need is False
        assert h == "fp123"

    def test_missing_file_on_disk_still_processes(self, state, tmp_path, monkeypatch):
        monkeypatch.setenv("HERMES_RAG_FORCE_FULL", "0")
        missing = tmp_path / "gone.md"
        state.entries["gone.md"] = {"mtime_ns": 1, "size": 1, "content_hash": "x"}
        need, h = state.needs_processing("gone.md", missing)
        assert need is True
        assert h is None

    def test_normalizes_backslash_key(self, state, tmp_path, monkeypatch):
        monkeypatch.setenv("HERMES_RAG_FORCE_FULL", "0")
        f = tmp_path / "sub" / "doc.md"
        f.parent.mkdir()
        f.write_text("z", encoding="utf-8")
        st = f.stat()
        state.entries[normalize_relative_source("sub/doc.md")] = {
            "mtime_ns": st.st_mtime_ns,
            "size": st.st_size,
            "content_hash": "h",
        }
        need, _ = state.needs_processing(r"sub\doc.md", f)
        assert need is False
