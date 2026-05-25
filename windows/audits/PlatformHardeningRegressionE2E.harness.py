#!/usr/bin/env python3
"""Isolated harness: platform hardening regression (code-review fixes + wiring)."""
from __future__ import annotations

import json
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


def test_sandbox_blocks_env_var_traversal() -> None:
    from hermes_cli import filesystem_sandbox as fs

    fs.reset_workspace_cache()
    prev = os.environ.get("HERMES_ESCAPE")
    os.environ["HERMES_ESCAPE"] = "../outside"
    try:
        err = fs.has_forbidden_path_content("%HERMES_ESCAPE%/secret.txt")
        step("Sandbox: blocks env-var path traversal", err is not None, err or "")
    finally:
        if prev is None:
            os.environ.pop("HERMES_ESCAPE", None)
        else:
            os.environ["HERMES_ESCAPE"] = prev


def test_sandbox_device_prefix_case_insensitive() -> None:
    from hermes_cli import filesystem_sandbox as fs

    if sys.platform != "win32":
        step("Sandbox: case-insensitive device prefix", True, "skipped (non-Windows)")
        return
    err = fs.has_forbidden_path_content(r"\\?\c:\Windows")
    step("Sandbox: case-insensitive device prefix", err is not None)


def test_patch_tool_blocks_sandbox_escape() -> None:
    from hermes_cli import filesystem_sandbox as fs

    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        os.environ["HERMES_WORKSPACE_ROOT"] = str(workspace)
        os.environ["HERMES_ENFORCE_FILE_SANDBOX"] = "1"
        os.environ["TERMINAL_CWD"] = str(workspace)
        fs.reset_workspace_cache()

        from tools.file_tools import patch_tool

        raw = patch_tool(
            mode="replace",
            path="../outside.txt",
            old_string="a",
            new_string="b",
        )
        payload = json.loads(raw)
        msg = str(payload.get("error", "")).lower()
        ok = bool(msg) and (
            "traversal" in msg or "outside" in msg or "escapes" in msg or "sandbox" in msg
        )
        step("patch_tool blocks sandbox escape", ok, msg or "no error")


def test_patch_tool_permission_error_propagates() -> None:
    from hermes_cli import filesystem_sandbox as fs

    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        target = workspace / "locked.txt"
        target.write_text("original", encoding="utf-8")
        os.environ["HERMES_WORKSPACE_ROOT"] = str(workspace)
        os.environ["HERMES_ENFORCE_FILE_SANDBOX"] = "1"
        os.environ["TERMINAL_CWD"] = str(workspace)
        fs.reset_workspace_cache()

        from tools import file_tools

        with patch.object(
            file_tools,
            "_resolve_path_for_task",
            side_effect=PermissionError("sandbox denied"),
        ):
            try:
                file_tools.patch_tool(
                    mode="replace",
                    path="locked.txt",
                    old_string="original",
                    new_string="changed",
                )
                step("patch_tool PermissionError propagates", False, "no exception raised")
            except PermissionError:
                step("patch_tool PermissionError propagates", True)


def test_hardware_cuda_device_fallback() -> None:
    from hermes_cli import hardware_backend as hb

    original = hb.probe_torch_cuda
    hb.probe_torch_cuda = lambda: False  # type: ignore[method-assign]
    try:
        device, backend = hb.select_torch_device("cuda")
        ok = device == "cpu" and backend == hb.BackendName.CPU
    finally:
        hb.probe_torch_cuda = original  # type: ignore[method-assign]
    step("Hardware: explicit cuda falls back to CPU when unavailable", ok)


def test_whisper_auto_cpu_fallback() -> None:
    from hermes_cli import hardware_backend as hb

    class FakeWhisper:
        def __init__(self, model_name, device, compute_type):
            self.model_name = model_name
            self.device = device
            self.compute_type = compute_type

    calls: list[tuple[str, str, str]] = []

    def fake_ctor(model_name, device, compute_type):
        calls.append((model_name, device, compute_type))
        if device in {"cuda", "auto"} and len(calls) == 1:
            raise RuntimeError("cannot be loaded")
        return FakeWhisper(model_name, device, compute_type)

    hb._selections.clear()
    try:
        import faster_whisper
    except ImportError:
        step("Hardware: faster-whisper auto falls back to CPU", True, "skipped (faster_whisper not installed)")
        return

    original = faster_whisper.WhisperModel
    faster_whisper.WhisperModel = fake_ctor  # type: ignore[misc]
    try:
        model = hb.load_faster_whisper_model("tiny", preferred_device="auto")
        ok = model.device == "cpu" and len(calls) == 2
    finally:
        faster_whisper.WhisperModel = original  # type: ignore[misc]
    step("Hardware: faster-whisper auto falls back to CPU", ok)


def test_lancedb_extra_cleanup_after_connect() -> None:
    import vector_store_lifecycle as lifecycle

    lifecycle.reset_lancedb_storage_state()
    calls: list[str] = []

    def extra() -> None:
        calls.append("extra")

    shutdown_mock = MagicMock()
    original_shutdown = lifecycle.shutdown_all_lancedb_connections
    lifecycle.shutdown_all_lancedb_connections = shutdown_mock  # type: ignore[method-assign]
    try:
        lifecycle.register_lancedb_connection(object())
        lifecycle.register_lancedb_shutdown_hooks(extra_cleanup=extra)
        lifecycle._run_shutdown_hooks()
        ok = calls == ["extra"] and shutdown_mock.call_count == 1
    finally:
        lifecycle.shutdown_all_lancedb_connections = original_shutdown  # type: ignore[method-assign]
        lifecycle.reset_lancedb_storage_state()
    step("LanceDB: extra_cleanup runs after connect-first registration", ok)


def test_lancedb_single_atexit_handler() -> None:
    import vector_store_lifecycle as lifecycle

    lifecycle.reset_lancedb_storage_state()
    handlers: list = []
    original_register = lifecycle.atexit.register
    lifecycle.atexit.register = lambda fn: handlers.append(fn)  # type: ignore[method-assign]
    try:
        lifecycle.register_lancedb_connection(object())
        lifecycle.register_lancedb_shutdown_hooks(extra_cleanup=lambda: None)
        ok = len(handlers) == 1
    finally:
        lifecycle.atexit.register = original_register  # type: ignore[method-assign]
        lifecycle.reset_lancedb_storage_state()
    step("LanceDB: single atexit shutdown handler", ok)


def test_terminal_tool_documents_git_bash() -> None:
    text = (REPO_ROOT / "tools" / "terminal_tool.py").read_text(encoding="utf-8")
    ok = "Git Bash" in text and "HERMES_GIT_BASH_PATH" in text
    step("terminal_tool documents Git Bash on Windows", ok)


def test_knowledge_repository_mock_backend() -> None:
    from knowledge_repository import KnowledgeRepository

    mock_table = MagicMock()
    mock_table.schema.names = ["id", "text"]
    mock_table.search.return_value.limit.return_value.to_list.return_value = [{"text": "hit"}]
    mock_db = MagicMock()
    page = MagicMock()
    page.tables = ["knowledge_base"]
    page.page_token = None
    mock_db.list_tables.return_value = page
    mock_db.open_table.return_value = mock_table

    backend = MagicMock()
    backend.connect.return_value = mock_db

    repo = KnowledgeRepository(db_path="/tmp/kb", backend=backend)
    with repo.session() as db:
        table = repo.ensure_table(db)
        hits = repo.search("query", limit=2, table=table)
        repo.upsert_chunks(table, [{"id": "1", "text": "a", "source": "s"}])
    backend.close.assert_called_once()
    ok = hits == [{"text": "hit"}] and mock_table.merge_insert.called
    step("KnowledgeRepository: session/search/upsert via DI backend", ok)


def main() -> int:
    print("=== Platform hardening regression harness ===")
    test_sandbox_blocks_env_var_traversal()
    test_sandbox_device_prefix_case_insensitive()
    test_patch_tool_blocks_sandbox_escape()
    test_patch_tool_permission_error_propagates()
    test_hardware_cuda_device_fallback()
    test_whisper_auto_cpu_fallback()
    test_lancedb_extra_cleanup_after_connect()
    test_lancedb_single_atexit_handler()
    test_terminal_tool_documents_git_bash()
    test_knowledge_repository_mock_backend()
    total = 10
    if FAILURES:
        print(f"=== HARNESS: FAIL ({FAILURES}) ===", file=sys.stderr)
        return 1
    print(f"=== HARNESS: PASS ({total}/{total}) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
