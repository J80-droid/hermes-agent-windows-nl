import os

from ingest_config import max_file_bytes


def test_max_file_bytes_default_unlimited(monkeypatch):
    monkeypatch.delenv("HERMES_RAG_MAX_FILE_MB", raising=False)
    assert max_file_bytes() is None


def test_max_file_bytes_explicit_limit(monkeypatch):
    monkeypatch.setenv("HERMES_RAG_MAX_FILE_MB", "100")
    assert max_file_bytes() == 100 * 1024 * 1024
