"""Unit tests for overlay.hermes_cli.auth_fork_patch."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from overlay.hermes_cli import auth_fork_patch


@pytest.fixture(autouse=True)
def _ensure_patch_applied():
    auth_fork_patch.apply_auth_fork_patch()
    yield


class TestReadAuthJson:
    def test_missing_file_returns_empty_dict(self, tmp_path: Path):
        missing = tmp_path / "no_auth.json"
        assert auth_fork_patch.read_auth_json(missing) == {}

    def test_empty_file_returns_empty_dict(self, tmp_path: Path):
        path = tmp_path / "auth.json"
        path.write_text("   \n", encoding="utf-8")
        assert auth_fork_patch.read_auth_json(path) == {}

    def test_utf8_bom_tolerant(self, tmp_path: Path):
        path = tmp_path / "auth.json"
        payload = {"active_provider": "openrouter"}
        path.write_text("\ufeff" + json.dumps(payload), encoding="utf-8")
        assert auth_fork_patch.read_auth_json(path) == payload

    def test_non_dict_json_returns_empty_dict(self, tmp_path: Path):
        path = tmp_path / "auth.json"
        path.write_text("[1, 2]", encoding="utf-8")
        assert auth_fork_patch.read_auth_json(path) == {}


class TestApplyAuthForkPatch:
    def test_idempotent(self):
        import hermes_cli.auth as auth

        auth_fork_patch.apply_auth_fork_patch()
        first = auth.read_auth_json
        auth_fork_patch.apply_auth_fork_patch()
        assert auth.read_auth_json is first

    def test_attaches_to_hermes_cli_auth(self):
        import hermes_cli.auth as auth

        assert auth.read_auth_json is auth_fork_patch.read_auth_json
        assert auth.sync_root_active_provider is auth_fork_patch.sync_root_active_provider
        assert auth._load_auth_store is auth_fork_patch._load_auth_store_bom_safe
        assert getattr(auth, "_fork_read_auth_json_patch_applied", False) is True


class TestRepairAuthJsonBom:
    def test_repair_strips_bom(self, tmp_path: Path):
        path = tmp_path / "auth.json"
        payload = {"version": 1, "active_provider": "venice", "providers": {}}
        path.write_bytes(b"\xef\xbb\xbf" + json.dumps(payload).encode("utf-8"))
        assert auth_fork_patch.repair_auth_json_bom(path) is True
        assert not path.read_bytes().startswith(b"\xef\xbb\xbf")
        assert json.loads(path.read_text(encoding="utf-8"))["active_provider"] == "venice"

    def test_repair_noop_without_bom(self, tmp_path: Path):
        path = tmp_path / "auth.json"
        path.write_text('{"active_provider": "nous"}', encoding="utf-8")
        assert auth_fork_patch.repair_auth_json_bom(path) is False

    def test_load_auth_store_auto_repairs_bom(self, tmp_path: Path):
        path = tmp_path / "auth.json"
        path.write_bytes(
            b"\xef\xbb\xbf"
            + b'{"version": 1, "active_provider": "venice", "providers": {}}'
        )
        store = auth_fork_patch._load_auth_store_bom_safe(path)
        assert store.get("active_provider") == "venice"
        assert not path.read_bytes().startswith(b"\xef\xbb\xbf")

    def test_repair_bom_on_empty_dict(self, tmp_path: Path):
        path = tmp_path / "auth.json"
        path.write_bytes(b"\xef\xbb\xbf" + b"{}")
        assert auth_fork_patch.repair_auth_json_bom(path) is True
        assert not path.read_bytes().startswith(b"\xef\xbb\xbf")

    def test_repair_invalid_json_returns_false(self, tmp_path: Path):
        path = tmp_path / "auth.json"
        path.write_bytes(b"\xef\xbb\xbf" + b"{bad")
        assert auth_fork_patch.repair_auth_json_bom(path) is False


class TestRepairAllAuthJsonBom:
    def test_scans_root_and_profiles(self, tmp_path: Path, monkeypatch):
        root = tmp_path / "hermes"
        prof = root / "profiles" / "legal"
        prof.mkdir(parents=True)
        root_auth = root / "auth.json"
        prof_auth = prof / "auth.json"
        root_auth.write_bytes(b"\xef\xbb\xbf" + b'{"active_provider": "nous"}')
        prof_auth.write_bytes(b"\xef\xbb\xbf" + b'{"active_provider": "venice"}')
        monkeypatch.setenv("HERMES_HOME", str(prof))
        monkeypatch.setenv("HERMES_WIN_PREFER_LOCALAPPDATA", "0")
        repaired = auth_fork_patch.repair_all_auth_json_bom()
        paths = {p.replace("\\", "/") for p in repaired}
        assert any("profiles/legal/auth.json" in p for p in paths)
        assert not root_auth.read_bytes().startswith(b"\xef\xbb\xbf")


class TestLoadAuthStoreCorrupt:
    def test_corrupt_json_creates_backup(self, tmp_path: Path, monkeypatch):
        path = tmp_path / "auth.json"
        path.write_text("{not-json", encoding="utf-8")
        monkeypatch.setenv("HERMES_SUPPRESS_AUTH_CORRUPT_LOG", "1")
        store = auth_fork_patch._load_auth_store_bom_safe(path)
        assert store.get("providers") == {}
        assert path.with_suffix(".json.corrupt").is_file()

    def test_missing_file_returns_empty_providers(self, tmp_path: Path):
        path = tmp_path / "missing.json"
        store = auth_fork_patch._load_auth_store_bom_safe(path)
        assert store.get("providers") == {}
