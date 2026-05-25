#!/usr/bin/env python3
"""Isolated harness: performance + architecture refactor (RAG, config, runtime)."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[2]
RAG_DIR = REPO_ROOT / "scripts" / "rag_pipeline"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

FAILURES = 0


def step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES
    suffix = f" — {detail}" if detail else ""
    if ok:
        print(f"[OK] {name}{suffix}")
    else:
        print(f"[FAIL] {name}{suffix}", file=sys.stderr)
        FAILURES += 1


def test_bootstrap_path_traversal() -> None:
    from bootstrap_ingest_state import _resolve_source_file

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "ok.md").write_text("x", encoding="utf-8")
        ok_file = _resolve_source_file(root, "ok.md")
        bad = _resolve_source_file(root, "../outside.md")
        bad2 = _resolve_source_file(root, "..\\ok.md")
    step(
        "bootstrap: path traversal blocked",
        ok_file is not None and bad is None and bad2 is None,
    )


def test_collect_indexed_files_single_walk() -> None:
    from source_formats import collect_indexed_files

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a.md").write_text("a", encoding="utf-8")
        (root / "skip.exe").write_text("b", encoding="utf-8")
        sub = root / "sub"
        sub.mkdir()
        (sub / "b.txt").write_text("b", encoding="utf-8")
        files = collect_indexed_files(root)
    names = {p.name for p in files}
    step(
        "source_formats: collect_indexed_files filters suffixes",
        names == {"a.md", "b.txt"},
        f"got {names}",
    )


def test_orphan_predicate_dedup_and_batch() -> None:
    from orphan_cleanup import _orphan_predicate

    pred_small = _orphan_predicate("docs/a.md", ["id1", "id1", "id2"])
    ok_dedup = pred_small.count("'id1'") == 1
    big_ids = [f"id{i:03d}" for i in range(150)]
    pred_big = _orphan_predicate("docs/a.md", big_ids)
    ok_batch = " AND " in pred_big and pred_big.count("id NOT IN") >= 2
    step("orphan_cleanup: dedup + batched NOT IN predicate", ok_dedup and ok_batch)


def test_ingest_state_fingerprint_tuple() -> None:
    from ingest_state import IngestState

    state = IngestState()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "doc.md"
        path.write_text("hello", encoding="utf-8")
        needs, fp = state.needs_processing("doc.md", path)
        ok = needs is True and fp is None
        state.record_success("doc.md", path, chunk_count=1)
        needs2, fp2 = state.needs_processing("doc.md", path)
        ok = ok and needs2 is False and fp2 is None
    step("ingest_state: needs_processing tuple + skip unchanged", ok)


def test_mcp_ensure_resets_on_failure() -> None:
    import mcp_server

    mcp_server.close_lancedb_mcp_connection()
    backend = MagicMock()
    backend.connect.side_effect = OSError("connect failed")
    mock_repo = MagicMock()
    mock_repo.backend = backend
    with patch("mcp_server.KnowledgeRepository", return_value=mock_repo):
        try:
            mcp_server._ensure_mcp_knowledge()
            step("mcp_server: connect failure resets cache", False, "no exception")
        except OSError:
            ok = mcp_server._repo is None and mcp_server._db is None and mcp_server._table is None
            step("mcp_server: connect failure resets cache", ok)
    mcp_server.close_lancedb_mcp_connection()


def test_config_snapshot_cache() -> None:
    from hermes_cli.config_snapshot import bust_config_snapshot, get_config_snapshot

    bust_config_snapshot()
    snap1 = get_config_snapshot()
    snap2 = get_config_snapshot()
    step(
        "config_snapshot: repeated get returns same mtime cache",
        snap1 is snap2 and snap1.mtime_ns == snap2.mtime_ns,
    )


def test_whisper_model_cache() -> None:
    from hermes_cli import hardware_backend as hb

    hb.clear_faster_whisper_model_cache()

    class FakeModel:
        pass

    with patch("faster_whisper.WhisperModel", return_value=FakeModel()) as WM:
        m1 = hb.load_faster_whisper_model("tiny", preferred_device="cpu")
        m2 = hb.load_faster_whisper_model("tiny", preferred_device="cpu")
    step(
        "hardware_backend: whisper cache avoids second WhisperModel()",
        WM.call_count == 1 and m1 is m2,
        f"calls={WM.call_count}",
    )
    hb.clear_faster_whisper_model_cache()


def test_review_snapshot_none() -> None:
    from agent.review_snapshot import snapshot_messages_for_background_review

    out = snapshot_messages_for_background_review(None)
    step("review_snapshot: None -> []", out == [])


def test_document_converter_protocol() -> None:
    from document_converter import DocumentConverter, MarkItDownDocumentConverter, get_document_converter

    conv = get_document_converter()
    step(
        "document_converter: default implements protocol",
        isinstance(conv, MarkItDownDocumentConverter) and isinstance(conv, DocumentConverter),
    )


def test_schema_migrate_uses_repository() -> None:
    text = (RAG_DIR / "schema_migrate.py").read_text(encoding="utf-8")
    ok = "KnowledgeRepository" in text and "lancedb.connect" not in text
    step("schema_migrate: KnowledgeRepository (no raw lancedb.connect)", ok)


def test_process_registry_completion_queue_bounded() -> None:
    from tools.process_registry import ProcessRegistry

    reg = ProcessRegistry()
    ok = reg.completion_queue.maxsize == 256 and hasattr(reg, "_enqueue_completion_event")
    step("process_registry: bounded completion queue + enqueue helper", ok)


def main() -> int:
    print("=== Performance Architecture E2E harness ===")
    test_bootstrap_path_traversal()
    test_collect_indexed_files_single_walk()
    test_orphan_predicate_dedup_and_batch()
    test_ingest_state_fingerprint_tuple()
    test_mcp_ensure_resets_on_failure()
    test_config_snapshot_cache()
    test_whisper_model_cache()
    test_review_snapshot_none()
    test_document_converter_protocol()
    test_schema_migrate_uses_repository()
    test_process_registry_completion_queue_bounded()
    total = 11
    if FAILURES:
        print(f"=== HARNESS: FAIL ({FAILURES}/{total}) ===", file=sys.stderr)
        return 1
    print(f"=== HARNESS: PASS ({total}/{total}) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
