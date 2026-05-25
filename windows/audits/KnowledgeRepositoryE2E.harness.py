#!/usr/bin/env python3
"""Isolated harness: KnowledgeRepository layer + caller wiring (edge cases)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

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


def test_search_empty_query_skips_table() -> None:
    from knowledge_repository import KnowledgeRepository

    mock_table = MagicMock()
    repo = KnowledgeRepository()
    hits = repo.search("   ", table=mock_table)
    ok = hits == [] and not mock_table.search.called
    step("KnowledgeRepository: empty search returns [] without table.search", ok)


def test_search_invalid_limit_fallback() -> None:
    from knowledge_repository import KnowledgeRepository

    mock_table = MagicMock()
    mock_table.search.return_value.limit.return_value.to_list.return_value = []
    repo = KnowledgeRepository()
    repo.search("term", limit="not-a-number", table=mock_table)  # type: ignore[arg-type]
    ok = mock_table.search.return_value.limit.call_args[0][0] == 5
    step("KnowledgeRepository: invalid limit falls back to 5", ok)


def test_upsert_requires_id_column() -> None:
    from knowledge_repository import KnowledgeRepository

    mock_table = MagicMock()
    repo = KnowledgeRepository()
    try:
        repo.upsert_chunks(mock_table, [{"text": "missing id"}])
        step("KnowledgeRepository: upsert rejects rows without id", False, "no ValueError")
    except ValueError as exc:
        ok = "id" in str(exc).lower() and not mock_table.merge_insert.called
        step("KnowledgeRepository: upsert rejects rows without id", ok, str(exc))


def test_merge_insert_wraps_runtime_error() -> None:
    from knowledge_repository import KnowledgeRepository

    mock_table = MagicMock()
    chain = mock_table.merge_insert.return_value
    chain.when_matched_update_all.return_value = chain
    chain.when_not_matched_insert_all.return_value = chain
    chain.execute.side_effect = OSError("disk full")

    try:
        KnowledgeRepository._merge_rows(mock_table, [{"id": "1"}])
        step("KnowledgeRepository: merge_insert failure wrapped", False, "no RuntimeError")
    except RuntimeError as exc:
        ok = "merge_insert failed" in str(exc).lower() and exc.__cause__ is not None
        step("KnowledgeRepository: merge_insert failure wrapped", ok)


def test_session_closes_on_success() -> None:
    from knowledge_repository import KnowledgeRepository

    backend = MagicMock()
    mock_db = MagicMock()
    backend.connect.return_value = mock_db
    repo = KnowledgeRepository(db_path="/tmp/kb", backend=backend)
    with repo.session() as db:
        assert db is mock_db
    ok = backend.close.call_count == 1 and backend.close.call_args[0][0] is mock_db
    step("KnowledgeRepository: session closes connection on success", ok)


def test_session_closes_on_exception() -> None:
    from knowledge_repository import KnowledgeRepository

    backend = MagicMock()
    mock_db = MagicMock()
    backend.connect.return_value = mock_db
    repo = KnowledgeRepository(backend=backend)
    try:
        with repo.session():
            raise RuntimeError("simulated ingest failure")
    except RuntimeError:
        pass
    ok = backend.close.call_count == 1
    step("KnowledgeRepository: session closes connection on exception", ok)


def test_ensure_table_rejects_legacy_schema() -> None:
    from knowledge_repository import KnowledgeRepository

    mock_table = MagicMock()
    mock_table.schema.names = ["text", "source"]
    mock_db = MagicMock()
    page = MagicMock()
    page.tables = ["knowledge_base"]
    page.page_token = None
    mock_db.list_tables.return_value = page
    mock_db.open_table.return_value = mock_table

    repo = KnowledgeRepository()
    try:
        repo.ensure_table(mock_db)
        step("KnowledgeRepository: legacy schema without id rejected", False, "no RuntimeError")
    except RuntimeError as exc:
        ok = "id" in str(exc).lower()
        step("KnowledgeRepository: legacy schema without id rejected", ok)


def test_ingest_upsert_uses_passed_repo() -> None:
    import ingest

    mock_table = MagicMock()
    mock_repo = MagicMock()
    rows = [{"id": "abc", "text": "chunk", "source": "doc.md"}]
    ingest._upsert_chunk_rows(mock_table, rows, repo=mock_repo)
    ok = mock_repo.upsert_chunks.call_count == 1
    args = mock_repo.upsert_chunks.call_args
    ok = ok and args[0][0] is mock_table and args[0][1] == rows
    step("ingest: _upsert_chunk_rows delegates to injected repo", ok)


def main() -> int:
    print("=== KnowledgeRepository E2E harness ===")
    test_search_empty_query_skips_table()
    test_search_invalid_limit_fallback()
    test_upsert_requires_id_column()
    test_merge_insert_wraps_runtime_error()
    test_session_closes_on_success()
    test_session_closes_on_exception()
    test_ensure_table_rejects_legacy_schema()
    test_ingest_upsert_uses_passed_repo()
    total = 8
    if FAILURES:
        print(f"=== HARNESS: FAIL ({FAILURES}) ===", file=sys.stderr)
        return 1
    print(f"=== HARNESS: PASS ({total}/{total}) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
