"""Tests voor institutionele ingest-runtime (timeouts)."""

from __future__ import annotations

import time

import pytest

from ingest_runtime import FileJobTimeout, reset_live_status_clock, run_file_job, write_live_status


def test_run_file_job_completes_within_timeout():
    assert run_file_job(lambda: 42, timeout_sec=5.0) == 42


def test_live_status_started_at_stable_across_writes(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_RAG_LIVE_STATUS", str(tmp_path / "live.json"))
    reset_live_status_clock()
    write_live_status(phase="index", index=1, total=10, relative_source="a.pdf", step="A")
    first = (tmp_path / "live.json").read_text(encoding="utf-8")
    write_live_status(phase="index", index=2, total=10, relative_source="b.pdf", step="B")
    import json

    d1 = json.loads(first)
    d2 = json.loads((tmp_path / "live.json").read_text(encoding="utf-8"))
    assert d1["started_at"] == d2["started_at"]
    assert d1["updated_at"] != d2["updated_at"]


def test_run_file_job_raises_on_timeout():
    def slow() -> None:
        time.sleep(2.0)

    with pytest.raises(FileJobTimeout):
        run_file_job(slow, timeout_sec=0.2)
