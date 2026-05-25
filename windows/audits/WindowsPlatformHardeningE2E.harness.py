#!/usr/bin/env python3
"""Isolated harness: Windows platform hardening (filesystem sandbox, hardware backend, LanceDB storage)."""
from __future__ import annotations

import os
import sys
import tempfile
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


def test_filesystem_sandbox_default_root_absolute() -> None:
    from hermes_cli import filesystem_sandbox as fs

    fs.reset_workspace_cache()
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["LOCALAPPDATA"] = tmp
        os.environ.pop("HERMES_WORKSPACE_ROOT", None)
        os.environ.pop("TERMINAL_CWD", None)
        fs.reset_workspace_cache()
        root = fs.default_workspace_root()
        ok = root.is_absolute() and root.exists()
        if sys.platform == "win32":
            ok = ok and str(root).lower().startswith(str(Path(tmp).resolve()).lower())
        step("Filesystem sandbox: default root is absolute (LOCALAPPDATA)", ok)


def test_filesystem_sandbox_blocks_traversal() -> None:
    from hermes_cli import filesystem_sandbox as fs

    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        (workspace / "inside.txt").write_text("ok", encoding="utf-8")
        fs.reset_workspace_cache()
        err = fs.check_filesystem_sandbox(
            "../outside.txt",
            sandbox_root=workspace,
            resolution_base=workspace,
        )
        step("Filesystem sandbox: blocks ../ traversal", err is not None, err or "")


def test_filesystem_sandbox_blocks_windows_absolute_escape() -> None:
    from hermes_cli import filesystem_sandbox as fs

    if sys.platform != "win32":
        step("Filesystem sandbox: blocks C:\\Windows absolute path", True, "skipped (non-Windows)")
        return
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        err = fs.check_filesystem_sandbox(
            r"C:\Windows\System32\drivers\etc\hosts",
            sandbox_root=workspace,
            resolution_base=workspace,
        )
        step("Filesystem sandbox: blocks C:\\Windows absolute path", err is not None)


def test_filesystem_sandbox_allows_in_workspace() -> None:
    from hermes_cli import filesystem_sandbox as fs

    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        (workspace / "readme.md").write_text("# ok", encoding="utf-8")
        resolved, err = fs.validate_agent_path_for_task(
            "readme.md",
            resolution_base=workspace,
            sandbox_root=workspace,
        )
        step(
            "Filesystem sandbox: allows in-workspace relative path",
            err is None and resolved == (workspace / "readme.md").resolve(),
        )


def test_read_file_tool_blocks_escape() -> None:
    from hermes_cli import filesystem_sandbox as fs

    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        os.environ["HERMES_WORKSPACE_ROOT"] = str(workspace)
        os.environ["HERMES_ENFORCE_FILE_SANDBOX"] = "1"
        os.environ["TERMINAL_CWD"] = str(workspace)
        fs.reset_workspace_cache()

        import json
        from tools.file_tools import read_file_tool

        result = json.loads(read_file_tool("../outside.txt"))
        step("read_file_tool blocks path traversal", "error" in result)


def test_hardware_onnx_provider_order() -> None:
    from hermes_cli import hardware_backend as hb

    hb._onnx_providers_cache = None

    def fake_providers() -> list[str]:
        return ["CPUExecutionProvider", "DmlExecutionProvider", "CUDAExecutionProvider"]

    original = hb.get_onnxruntime_available_providers
    hb.get_onnxruntime_available_providers = fake_providers  # type: ignore[method-assign]
    try:
        attempts = hb.build_onnx_provider_attempts()
        names = [name for name, _ in attempts]
        ok = names == [hb.BackendName.CUDA, hb.BackendName.DIRECTML, hb.BackendName.CPU]
    finally:
        hb.get_onnxruntime_available_providers = original  # type: ignore[method-assign]
        hb._onnx_providers_cache = None
    step("Hardware backend: ONNX provider order CUDA->DirectML->CPU", ok)


def test_hardware_cuda_error_heuristic() -> None:
    from hermes_cli.hardware_backend import looks_like_cuda_lib_error

    ok = looks_like_cuda_lib_error(RuntimeError("Library libcublas.so.12 is not found"))
    ok = ok and not looks_like_cuda_lib_error(RuntimeError("CUDA out of memory"))
    step("Hardware backend: CUDA lib error heuristic", ok)


def test_hardware_startup_probe_lines() -> None:
    from hermes_cli.hardware_backend import probe_startup_backends

    lines = probe_startup_backends()
    joined = "\n".join(lines)
    ok = "faster-whisper" in joined and "ONNX (Piper TTS)" in joined
    step("Hardware backend: startup probe lines present", ok)


def test_lancedb_resolve_absolute_path() -> None:
    import lancedb_storage as storage

    storage.reset_lancedb_storage_state()
    with tempfile.TemporaryDirectory() as tmp:
        explicit = Path(tmp) / "legal"
        os.environ["HERMES_LANCEDB_PATH"] = str(explicit)
        resolved = storage.resolve_lancedb_path()
        ok = Path(resolved).is_absolute() and Path(resolved) == explicit.resolve()
        step("LanceDB storage: HERMES_LANCEDB_PATH resolves absolute", ok)


def test_lancedb_default_vectorstore_localappdata() -> None:
    import lancedb_storage as storage

    storage.reset_lancedb_storage_state()
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["LOCALAPPDATA"] = str(Path(tmp) / "LocalAppData")
        os.environ.pop("HERMES_LANCEDB_PATH", None)
        root = storage.default_vector_store_root()
        ok = root.is_absolute() and "VectorStore" in str(root)
        if sys.platform == "win32":
            ok = ok and "LocalAppData" in str(root)
        step("LanceDB storage: default VectorStore under LOCALAPPDATA", ok)


def test_lancedb_preflight_removes_stale_lock() -> None:
    import lancedb_storage as storage
    import vector_store_lifecycle as lifecycle

    storage.reset_lancedb_storage_state()
    lifecycle._STALE_MIN_AGE_SEC = 0.0
    try:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "legal"
            lance_dir = store / "knowledge_base.lance"
            lance_dir.mkdir(parents=True)
            lock = lance_dir / "manifest.lance-lock"
            lock.write_text("stale", encoding="utf-8")
            removed = storage.preflight_vector_store(store, force=True)
            ok = not lock.exists() and len(removed) >= 1
            step("LanceDB storage: preflight removes stale .lance-lock", ok)
    finally:
        lifecycle._STALE_MIN_AGE_SEC = 30.0


def test_lancedb_session_closes_connection() -> None:
    import lancedb_storage as storage

    storage.reset_lancedb_storage_state()
    mock_db = MagicMock()
    mock_db.is_open = True
    storage.connect_lancedb = lambda *a, **k: mock_db  # type: ignore[method-assign]
    storage.preflight_vector_store = lambda *a, **k: []  # type: ignore[method-assign]

    with storage.lancedb_session("/tmp/test-db") as db:
        assert db is mock_db
    mock_db.close.assert_called_once()
    step("LanceDB storage: lancedb_session closes on exit", True)


def main() -> int:
    print("=== Windows platform hardening harness ===")
    test_filesystem_sandbox_default_root_absolute()
    test_filesystem_sandbox_blocks_traversal()
    test_filesystem_sandbox_blocks_windows_absolute_escape()
    test_filesystem_sandbox_allows_in_workspace()
    test_read_file_tool_blocks_escape()
    test_hardware_onnx_provider_order()
    test_hardware_cuda_error_heuristic()
    test_hardware_startup_probe_lines()
    test_lancedb_resolve_absolute_path()
    test_lancedb_default_vectorstore_localappdata()
    test_lancedb_preflight_removes_stale_lock()
    test_lancedb_session_closes_connection()
    total = 12
    if FAILURES:
        print(f"=== HARNESS: FAIL ({FAILURES}) ===", file=sys.stderr)
        return 1
    print(f"=== HARNESS: PASS ({total}/{total}) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
