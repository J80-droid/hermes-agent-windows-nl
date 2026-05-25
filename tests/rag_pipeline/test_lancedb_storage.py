"""Unit tests for scripts/rag_pipeline/lancedb_storage.py.

Covers happy paths, edge cases, invalid input, and negative scenarios.
External dependencies (lancedb, atexit, signal) are mocked.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

RAG_DIR = Path(__file__).resolve().parents[2] / "scripts" / "rag_pipeline"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

import lancedb_storage as storage  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_storage_state():
    storage.reset_lancedb_storage_state()
    yield
    storage.reset_lancedb_storage_state()


# ---------------------------------------------------------------------------
# Path resolution — happy path
# ---------------------------------------------------------------------------


class TestVectorStorePathsHappyPath:
    def test_default_root_uses_localappdata_on_windows(self, monkeypatch, tmp_path):
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
        monkeypatch.delenv("HERMES_LANCEDB_PATH", raising=False)
        root = storage.default_vector_store_root()
        assert root.is_absolute()
        assert "VectorStore" in str(root)
        assert "hermes" in str(root).lower()
        assert str(root).startswith(str(tmp_path / "LocalAppData"))

    def test_resolve_lancedb_path_uses_explicit_env(self, monkeypatch, tmp_path):
        explicit = tmp_path / "custom" / "legal"
        monkeypatch.setenv("HERMES_LANCEDB_PATH", str(explicit))
        resolved = storage.resolve_lancedb_path()
        assert resolved == str(explicit.resolve())
        assert Path(resolved).is_absolute()

    def test_resolve_lancedb_path_domain_subfolder(self, monkeypatch, tmp_path):
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
        monkeypatch.delenv("HERMES_LANCEDB_PATH", raising=False)
        resolved = storage.resolve_lancedb_path(domain="legal")
        path = Path(resolved)
        assert path.is_absolute()
        assert path.name == "legal"
        assert "VectorStore" in str(path)

    def test_resolve_relative_env_against_cwd(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        rel = Path("relative-db")
        monkeypatch.setenv("HERMES_LANCEDB_PATH", "relative-db")
        resolved = storage.resolve_lancedb_path()
        assert Path(resolved) == (tmp_path / "relative-db").resolve()

    def test_lancedb_table_dir_naming(self, tmp_path):
        store = tmp_path / "legal"
        assert storage.lancedb_table_dir(store) == store / "knowledge_base.lance"
        assert storage.lancedb_table_dir(store, "custom") == store / "custom.lance"

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix home layout")
    def test_default_root_unix_uses_home(self, monkeypatch, tmp_path):
        monkeypatch.setattr(storage.Path, "home", lambda: tmp_path / "home")
        root = storage.default_vector_store_root()
        assert ".hermes" in str(root)
        assert "VectorStore" in str(root)


# ---------------------------------------------------------------------------
# Path resolution — edge cases & invalid input
# ---------------------------------------------------------------------------


class TestVectorStorePathsEdgeCases:
    def test_empty_hermes_lancedb_path_falls_back_to_domain(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_LANCEDB_PATH", "   ")
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
        resolved = storage.resolve_lancedb_path(domain="core")
        assert Path(resolved).name == "core"

    def test_whitespace_domain_defaults_to_default_subdir(self, monkeypatch, tmp_path):
        monkeypatch.delenv("HERMES_LANCEDB_PATH", raising=False)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
        resolved = storage.resolve_lancedb_path(domain="   ")
        assert Path(resolved).name == storage.DEFAULT_DOMAIN_SUBDIR

    def test_none_domain_uses_default_subdir(self, monkeypatch, tmp_path):
        monkeypatch.delenv("HERMES_LANCEDB_PATH", raising=False)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
        resolved = storage.resolve_lancedb_path(domain=None)
        assert Path(resolved).name == storage.DEFAULT_DOMAIN_SUBDIR

    def test_windows_missing_localappdata_fallback(self, monkeypatch, tmp_path):
        if sys.platform != "win32":
            pytest.skip("Windows-only fallback")
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        monkeypatch.setattr(storage.Path, "home", lambda: tmp_path / "home")
        root = storage.default_vector_store_root()
        assert "AppData" in str(root) and "Local" in str(root)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows env expansion")
    def test_abs_path_expands_env_vars(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_TEST_ROOT", str(tmp_path))
        path = storage._abs_path("%HERMES_TEST_ROOT%\\legal")
        assert path == (tmp_path / "legal").resolve()

    def test_abs_path_raises_when_resolve_fails(self, monkeypatch):
        def failing_resolve(self):
            raise OSError("mock resolve failure")

        monkeypatch.setattr(Path, "resolve", failing_resolve)
        with pytest.raises(ValueError, match="Cannot resolve LanceDB path"):
            storage._abs_path("/some/unresolvable/path")


# ---------------------------------------------------------------------------
# Stale artifact detection
# ---------------------------------------------------------------------------


class TestStaleArtifactDetection:
    @pytest.mark.parametrize(
        "name,expected",
        [
            (".lance-lock", True),
            (".tmp", True),
            ("manifest.lance-lock", True),
            ("commit.tmp", True),
            ("COMMIT.TMP", True),
            ("data.lance", False),
            ("knowledge_base.lance", False),
            ("readme.txt", False),
        ],
    )
    def test_is_stale_artifact(self, tmp_path, name, expected):
        path = tmp_path / name
        path.write_text("x", encoding="utf-8")
        assert storage._is_stale_artifact(path) is expected

    def test_artifact_safe_to_remove_when_old_enough(self, tmp_path, monkeypatch):
        monkeypatch.setattr(storage, "_STALE_MIN_AGE_SEC", 10.0)
        path = tmp_path / "old.lance-lock"
        path.write_text("lock", encoding="utf-8")
        old = time.time() - 60
        os.utime(path, (old, old))
        assert storage._artifact_is_safe_to_remove(path) is True

    def test_artifact_not_safe_when_too_recent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(storage, "_STALE_MIN_AGE_SEC", 3600.0)
        path = tmp_path / "fresh.lance-lock"
        path.write_text("lock", encoding="utf-8")
        assert storage._artifact_is_safe_to_remove(path) is False

    def test_artifact_not_safe_when_stat_fails(self, tmp_path, monkeypatch):
        path = tmp_path / "missing.lance-lock"
        assert storage._artifact_is_safe_to_remove(path) is False


# ---------------------------------------------------------------------------
# Preflight cleanup
# ---------------------------------------------------------------------------


class TestPreflightCleanup:
    def test_removes_stale_lock_and_tmp_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(storage, "_STALE_MIN_AGE_SEC", 0.0)
        store = tmp_path / "legal"
        lance_dir = store / "knowledge_base.lance"
        lance_dir.mkdir(parents=True)
        stale_lock = lance_dir / "manifest.lance-lock"
        stale_tmp = lance_dir / "commit.tmp"
        keep = lance_dir / "data.lance"
        stale_lock.write_text("lock", encoding="utf-8")
        stale_tmp.write_text("partial", encoding="utf-8")
        keep.write_text("real", encoding="utf-8")

        removed = storage.preflight_vector_store(store, force=True)

        assert not stale_lock.exists()
        assert not stale_tmp.exists()
        assert keep.exists()
        assert len(removed) == 2

    def test_creates_missing_storage_dir(self, tmp_path):
        store = tmp_path / "new-domain"
        assert not store.exists()
        storage.preflight_vector_store(store)
        assert store.is_dir()

    def test_preflight_cache_skips_second_walk(self, tmp_path, monkeypatch):
        monkeypatch.setattr(storage, "_artifact_is_safe_to_remove", lambda _p: True)
        store = tmp_path / "cached"
        store.mkdir()
        lock = store / "a.lance-lock"
        lock.write_text("x", encoding="utf-8")

        first = storage.preflight_vector_store(store)
        lock.write_text("y", encoding="utf-8")
        second = storage.preflight_vector_store(store)

        assert len(first) == 1
        assert second == []
        assert lock.exists()

    def test_preflight_force_bypasses_cache(self, tmp_path, monkeypatch):
        monkeypatch.setattr(storage, "_STALE_MIN_AGE_SEC", 0.0)
        store = tmp_path / "forced"
        store.mkdir()
        lock = store / "b.lance-lock"
        lock.write_text("x", encoding="utf-8")
        storage.preflight_vector_store(store)
        lock.write_text("y", encoding="utf-8")
        removed = storage.preflight_vector_store(store, force=True)
        assert len(removed) == 1
        assert not lock.exists()

    def test_preflight_skips_recent_artifacts(self, tmp_path, monkeypatch):
        monkeypatch.setattr(storage, "_STALE_MIN_AGE_SEC", 99999.0)
        store = tmp_path / "active"
        store.mkdir()
        lock = store / "active.lance-lock"
        lock.write_text("active", encoding="utf-8")
        removed = storage.preflight_vector_store(store, force=True)
        assert removed == []
        assert lock.exists()

    def test_preflight_continues_after_unlink_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(storage, "_STALE_MIN_AGE_SEC", 0.0)
        store = tmp_path / "err"
        store.mkdir()
        lock = store / "fail.lance-lock"
        lock.write_text("x", encoding="utf-8")

        original_unlink = Path.unlink

        def flaky_unlink(self, missing_ok=False):  # noqa: ARG001
            if self.name == "fail.lance-lock":
                raise OSError("permission denied")
            return original_unlink(self)

        monkeypatch.setattr(Path, "unlink", flaky_unlink)
        removed = storage.preflight_vector_store(store, force=True)
        assert removed == []
        assert lock.exists()


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------


class TestConnectionLifecycle:
    def test_lancedb_session_closes_on_exit(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_LANCEDB_PATH", str(tmp_path / "db"))
        mock_db = MagicMock()
        mock_db.is_open = True
        monkeypatch.setattr(storage, "connect_lancedb", lambda *a, **k: mock_db)

        with storage.lancedb_session(str(tmp_path / "db")) as db:
            assert db is mock_db
        mock_db.close.assert_called_once()

    def test_lancedb_session_closes_on_exception(self, monkeypatch, tmp_path):
        mock_db = MagicMock()
        mock_db.is_open = True
        monkeypatch.setattr(storage, "connect_lancedb", lambda *a, **k: mock_db)

        with pytest.raises(RuntimeError, match="boom"):
            with storage.lancedb_session("/tmp/db"):
                raise RuntimeError("boom")
        mock_db.close.assert_called_once()

    def test_shutdown_all_closes_registered_connections(self):
        conn1 = MagicMock()
        conn1.is_open = True
        conn2 = MagicMock()
        conn2.is_open = True
        storage.register_lancedb_connection(conn1)
        storage.register_lancedb_connection(conn2)

        storage.shutdown_all_lancedb_connections()

        conn1.close.assert_called_once()
        conn2.close.assert_called_once()

    def test_shutdown_all_reverse_order(self):
        order: list[str] = []

        def make_conn(name: str):
            conn = MagicMock()
            conn.is_open = True
            conn.close.side_effect = lambda n=name: order.append(n)
            return conn

        c1 = make_conn("first")
        c2 = make_conn("second")
        storage.register_lancedb_connection(c1)
        storage.register_lancedb_connection(c2)
        storage.shutdown_all_lancedb_connections()
        assert order == ["second", "first"]

    def test_close_none_is_noop(self):
        storage.close_lancedb_connection(None)

    def test_close_already_closed_skips_close_call(self):
        conn = MagicMock()
        conn.is_open = False
        storage.register_lancedb_connection(conn)
        storage.close_lancedb_connection(conn)
        conn.close.assert_not_called()

    def test_close_failure_still_unregisters(self):
        conn = MagicMock()
        conn.is_open = True
        conn.close.side_effect = RuntimeError("close failed")
        storage.register_lancedb_connection(conn)
        storage.close_lancedb_connection(conn)
        storage.shutdown_all_lancedb_connections()
        conn.close.assert_called_once()

    def test_register_does_not_duplicate_connection(self):
        conn = MagicMock()
        storage.register_lancedb_connection(conn)
        storage.register_lancedb_connection(conn)
        storage.shutdown_all_lancedb_connections()
        conn.close.assert_called_once()


class TestConnectLancedb:
    def test_connect_success_registers_and_preflights(self, monkeypatch, tmp_path):
        mock_db = MagicMock()
        preflight_calls: list[Path] = []

        def fake_preflight(path: Path, *, force: bool = False):  # noqa: ARG001
            preflight_calls.append(path)
            return []

        fake_lancedb = MagicMock()
        fake_lancedb.connect.return_value = mock_db
        monkeypatch.setitem(sys.modules, "lancedb", fake_lancedb)
        monkeypatch.setattr(storage, "preflight_vector_store", fake_preflight)

        db_path = str(tmp_path / "connect-test")
        result = storage.connect_lancedb(db_path)

        assert result is mock_db
        fake_lancedb.connect.assert_called_once_with(db_path)
        assert preflight_calls == [Path(db_path)]

    def test_connect_failure_raises_runtime_error(self, monkeypatch, tmp_path):
        fake_lancedb = MagicMock()
        fake_lancedb.connect.side_effect = OSError("file in use")
        monkeypatch.setitem(sys.modules, "lancedb", fake_lancedb)
        monkeypatch.setattr(storage, "preflight_vector_store", lambda *_a, **_k: [])

        db_path = str(tmp_path / "fail-connect")
        with pytest.raises(RuntimeError, match="LanceDB connect failed"):
            storage.connect_lancedb(db_path)


class TestShutdownHooks:
    def test_register_shutdown_hooks_registers_atexit_once(self, monkeypatch):
        register = MagicMock()
        monkeypatch.setattr(storage.atexit, "register", register)

        storage.reset_lancedb_storage_state()
        storage.register_lancedb_shutdown_hooks()
        storage.register_lancedb_shutdown_hooks()

        assert register.call_count == 1

    def test_atexit_handler_runs_extra_cleanup_and_shutdown(self, monkeypatch):
        extra = MagicMock()
        shutdown = MagicMock()
        handlers: list = []
        monkeypatch.setattr(storage.atexit, "register", lambda fn: handlers.append(fn))
        monkeypatch.setattr(storage, "shutdown_all_lancedb_connections", shutdown)

        storage.reset_lancedb_storage_state()
        storage.register_lancedb_shutdown_hooks(extra_cleanup=extra)
        assert handlers
        handlers[0]()

        extra.assert_called_once()
        shutdown.assert_called_once()

    def test_extra_cleanup_failure_still_runs_shutdown(self, monkeypatch):
        extra = MagicMock(side_effect=RuntimeError("cleanup boom"))
        shutdown = MagicMock()
        handlers: list = []
        monkeypatch.setattr(storage.atexit, "register", lambda fn: handlers.append(fn))
        monkeypatch.setattr(storage, "shutdown_all_lancedb_connections", shutdown)

        storage.reset_lancedb_storage_state()
        storage.register_lancedb_shutdown_hooks(extra_cleanup=extra)
        handlers[0]()

        extra.assert_called_once()
        shutdown.assert_called_once()

    def test_signal_handler_invokes_cleanup(self, monkeypatch):
        shutdown = MagicMock()
        captured: dict = {}

        def fake_signal(sig, handler):
            captured["handler"] = handler

        import signal

        monkeypatch.setattr(storage.atexit, "register", MagicMock())
        monkeypatch.setattr(storage, "shutdown_all_lancedb_connections", shutdown)
        monkeypatch.setattr(signal, "signal", fake_signal)

        storage.reset_lancedb_storage_state()
        storage.register_lancedb_shutdown_hooks()

        if "handler" in captured:
            captured["handler"](signal.SIGTERM, None)
            shutdown.assert_called_once()
