"""Tests voor institutioneel live_status (running / completed / stale)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from ingest_live_status import (
    RUN_COMPLETED,
    RUN_RUNNING,
    LiveDisplayState,
    finalize_live_status,
    interpret_live_status,
    mark_ingest_started,
    read_live_status,
    reconcile_live_status_from_summary,
    reset_live_status_clock,
    write_live_status,
)


@pytest.fixture
def ldb(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_LANCEDB_PATH", str(tmp_path))
    monkeypatch.setenv("HERMES_RAG_LIVE_STATUS", str(tmp_path / "rag_ingest_live_status.json"))
    monkeypatch.setenv("RAG_DOMAIN", "test")
    return tmp_path


def test_mark_and_finalize_completed(ldb):
    reset_live_status_clock()
    mark_ingest_started(total=5)
    live = read_live_status(ldb)
    assert live is not None
    assert live["run_state"] == RUN_RUNNING
    assert live["current_index"] == 0

    finalize_live_status(
        run_state=RUN_COMPLETED,
        exit_code=0,
        message="ok",
        current_index=5,
        total=5,
    )
    done = read_live_status(ldb)
    assert done["run_state"] == RUN_COMPLETED
    assert done["phase"] == "done"
    assert done["completed_at"]
    assert done["pid"] == 0 or done["pid"] > 0


def test_interpret_stale_when_summary_newer(ldb):
    now = datetime.now(timezone.utc)
    old = (now - timedelta(hours=1)).isoformat()
    new = now.isoformat()
    live_path = ldb / "rag_ingest_live_status.json"
    live_path.write_text(
        json.dumps(
            {
                "run_state": RUN_RUNNING,
                "phase": "index",
                "current_index": 40,
                "total": 40,
                "relative_source": "x.m4a",
                "step": "Embedden",
                "started_at": old,
                "updated_at": old,
                "pid": 999999,
                "domain": "legal",
            }
        ),
        encoding="utf-8",
    )
    (ldb / "rag_ingest_run_summary.json").write_text(
        json.dumps({"generated_at": new, "total_sources_in_index_state": 100}),
        encoding="utf-8",
    )
    interp = interpret_live_status(ldb)
    assert interp.display_state == LiveDisplayState.STALE
    assert reconcile_live_status_from_summary(ldb)
    fixed = read_live_status(ldb)
    assert fixed["run_state"] == RUN_COMPLETED


def test_started_at_stable_across_writes(ldb, monkeypatch):
    monkeypatch.setenv("HERMES_RAG_LIVE_STATUS", str(ldb / "live.json"))
    reset_live_status_clock()
    write_live_status(
        phase="index", index=1, total=10, relative_source="a.pdf", step="A"
    )
    first = json.loads((ldb / "live.json").read_text(encoding="utf-8"))
    write_live_status(
        phase="index", index=2, total=10, relative_source="b.pdf", step="B"
    )
    second = json.loads((ldb / "live.json").read_text(encoding="utf-8"))
    assert first["started_at"] == second["started_at"]
    assert first["run_state"] == RUN_RUNNING
