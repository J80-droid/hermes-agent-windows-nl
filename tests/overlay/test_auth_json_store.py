"""Unit tests for Hermes auth.json read/load hardening (BOM, corrupt guard, repair)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_repo = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_repo))


@pytest.fixture
def auth_home(tmp_path, monkeypatch):
    """Flat HERMES_HOME with root config for coherence side-effects."""
    home = tmp_path / "hermes"
    home.mkdir()
    (home / "config.yaml").write_text(
        "model:\n  provider: nous\n  default: m\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_WIN_PREFER_LOCALAPPDATA", "0")
    return home


@pytest.fixture(autouse=True)
def _reset_corrupt_guard():
    from hermes_cli import auth as auth_mod

    auth_mod._AUTH_CORRUPT_REPAIR_IN_PROGRESS = False
    yield
    auth_mod._AUTH_CORRUPT_REPAIR_IN_PROGRESS = False


class TestReadAuthJson:
    def test_missing_file_returns_empty_dict(self, tmp_path):
        from hermes_cli.auth import read_auth_json

        missing = tmp_path / "no_auth.json"
        assert read_auth_json(missing) == {}

    def test_valid_json_happy_path(self, auth_home):
        from hermes_cli.auth import read_auth_json

        path = auth_home / "auth.json"
        path.write_text(
            json.dumps({"version": 1, "active_provider": "nous", "providers": {}}),
            encoding="utf-8",
        )
        data = read_auth_json(path)
        assert data["active_provider"] == "nous"
        assert data["providers"] == {}

    def test_whitespace_only_returns_empty(self, auth_home):
        from hermes_cli.auth import read_auth_json

        path = auth_home / "auth.json"
        path.write_text("   \n\t  ", encoding="utf-8")
        assert read_auth_json(path) == {}

    def test_utf8_bom_prefix(self, auth_home):
        from hermes_cli.auth import read_auth_json

        path = auth_home / "auth.json"
        path.write_bytes(
            b"\xef\xbb\xbf"
            + b'{"version": 1, "active_provider": "openrouter", "providers": {}}'
        )
        assert read_auth_json(path)["active_provider"] == "openrouter"

    def test_non_dict_json_returns_empty(self, auth_home):
        from hermes_cli.auth import read_auth_json

        path = auth_home / "auth.json"
        path.write_text("[1, 2, 3]", encoding="utf-8")
        assert read_auth_json(path) == {}

    def test_json_string_primitive_returns_empty(self, auth_home):
        from hermes_cli.auth import read_auth_json

        path = auth_home / "auth.json"
        path.write_text('"just-a-string"', encoding="utf-8")
        assert read_auth_json(path) == {}

    def test_invalid_json_raises(self, auth_home):
        from hermes_cli.auth import read_auth_json

        path = auth_home / "auth.json"
        path.write_text("{broken", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            read_auth_json(path)


class TestLoadAuthStore:
    def test_missing_auth_file_returns_empty_providers(self, auth_home):
        from hermes_cli.auth import _load_auth_store

        path = auth_home / "auth.json"
        assert not path.exists()
        store = _load_auth_store(path)
        assert store == {"version": 1, "providers": {}}

    def test_minimal_active_provider_only(self, auth_home):
        from hermes_cli.auth import _load_auth_store

        path = auth_home / "auth.json"
        path.write_text(
            json.dumps({"active_provider": "nous"}),
            encoding="utf-8",
        )
        store = _load_auth_store(path)
        assert store["active_provider"] == "nous"
        assert store["providers"] == {}
        assert store["version"] == 1

    def test_systems_format_migration(self, auth_home):
        from hermes_cli.auth import _load_auth_store

        path = auth_home / "auth.json"
        path.write_text(
            json.dumps(
                {
                    "systems": {
                        "nous_portal": {"refresh_token": "rt", "access_token": "at"}
                    }
                }
            ),
            encoding="utf-8",
        )
        store = _load_auth_store(path)
        assert store["active_provider"] == "nous"
        assert "nous" in store["providers"]

    def test_corrupt_json_returns_empty_and_preserves_backup(self, auth_home):
        from hermes_cli import auth as auth_mod

        path = auth_home / "auth.json"
        path.write_text("not-json-at-all", encoding="utf-8")
        store = auth_mod._load_auth_store(path)
        assert store["providers"] == {}
        corrupt = path.with_suffix(".json.corrupt")
        assert corrupt.is_file()
        assert corrupt.read_text(encoding="utf-8") == "not-json-at-all"

    def test_corrupt_auth_skips_repair_when_guard_already_set(self, auth_home, monkeypatch):
        from hermes_cli import auth as auth_mod

        repair = MagicMock(return_value=["should-not-run"])
        monkeypatch.setattr(
            "hermes_cli.model_runtime_config.repair_model_provider_coherence",
            repair,
        )
        auth_mod._AUTH_CORRUPT_REPAIR_IN_PROGRESS = True
        (auth_home / "auth.json").write_text("{bad", encoding="utf-8")
        auth_mod._load_auth_store(auth_home / "auth.json")
        repair.assert_not_called()

    def test_corrupt_auth_repair_only_on_error_severity(self, auth_home, monkeypatch):
        from hermes_cli import auth as auth_mod
        from hermes_cli.model_runtime_config import CoherenceIssue

        detect = MagicMock(
            return_value=[
                CoherenceIssue(
                    code="vendor_slug_wrong_provider",
                    message="warn only",
                    severity="warn",
                )
            ]
        )
        repair = MagicMock(return_value=["fixed"])
        monkeypatch.setattr(
            "hermes_cli.model_runtime_config.detect_model_provider_incoherence",
            detect,
        )
        monkeypatch.setattr(
            "hermes_cli.model_runtime_config.repair_model_provider_coherence",
            repair,
        )
        (auth_home / "config.yaml").write_text(
            "model:\n  provider: gemini\n  default: deepseek/x\n",
            encoding="utf-8",
        )
        (auth_home / "auth.json").write_text("{invalid", encoding="utf-8")
        auth_mod._load_auth_store(auth_home / "auth.json")
        detect.assert_called_once()
        repair.assert_not_called()

    def test_corrupt_auth_calls_repair_for_error_issues(self, auth_home, monkeypatch):
        from hermes_cli import auth as auth_mod
        from hermes_cli.model_runtime_config import CoherenceIssue

        detect = MagicMock(
            return_value=[
                CoherenceIssue(
                    code="auth_config_provider_mismatch",
                    message="split brain",
                    severity="error",
                )
            ]
        )
        repair = MagicMock(return_value=["aligned config"])
        monkeypatch.setattr(
            "hermes_cli.model_runtime_config.detect_model_provider_incoherence",
            detect,
        )
        monkeypatch.setattr(
            "hermes_cli.model_runtime_config.repair_model_provider_coherence",
            repair,
        )
        (auth_home / "config.yaml").write_text(
            "model:\n  provider: gemini\n  default: m\n",
            encoding="utf-8",
        )
        (auth_home / "auth.json").write_text("{invalid", encoding="utf-8")
        store = auth_mod._load_auth_store(auth_home / "auth.json")
        assert store["providers"] == {}
        repair.assert_called_once()
        _kwargs = repair.call_args.kwargs
        assert _kwargs.get("prefer") == "auth_from_config"
        assert len(_kwargs.get("issues", [])) == 1

    def test_repair_failure_still_returns_empty_store(self, auth_home, monkeypatch):
        from hermes_cli import auth as auth_mod
        from hermes_cli.model_runtime_config import CoherenceIssue

        monkeypatch.setattr(
            "hermes_cli.model_runtime_config.detect_model_provider_incoherence",
            lambda **kw: [
                CoherenceIssue(code="auth_config_provider_mismatch", message="x", severity="error")
            ],
        )
        monkeypatch.setattr(
            "hermes_cli.model_runtime_config.repair_model_provider_coherence",
            MagicMock(side_effect=RuntimeError("repair boom")),
        )
        (auth_home / "auth.json").write_text("{bad", encoding="utf-8")
        store = auth_mod._load_auth_store(auth_home / "auth.json")
        assert store == {"version": 1, "providers": {}}
        assert auth_mod._AUTH_CORRUPT_REPAIR_IN_PROGRESS is False

    def test_empty_dict_auth_returns_empty_providers(self, auth_home):
        from hermes_cli.auth import _load_auth_store

        path = auth_home / "auth.json"
        path.write_text("{}", encoding="utf-8")
        store = _load_auth_store(path)
        assert store == {"version": 1, "providers": {}}


class TestReadSharedNousState:
    def test_missing_shared_store_returns_none(self, tmp_path, monkeypatch):
        from hermes_cli.auth import _read_shared_nous_state

        monkeypatch.setenv("HERMES_SHARED_AUTH_DIR", str(tmp_path / "empty"))
        assert _read_shared_nous_state() is None

    def test_malformed_shared_store_returns_none(self, tmp_path, monkeypatch):
        from hermes_cli.auth import NOUS_SHARED_STORE_FILENAME, _read_shared_nous_state

        shared = tmp_path / "shared"
        shared.mkdir()
        (shared / NOUS_SHARED_STORE_FILENAME).write_text("{broken", encoding="utf-8")
        monkeypatch.setenv("HERMES_SHARED_AUTH_DIR", str(shared))
        assert _read_shared_nous_state() is None

    def test_missing_tokens_returns_none(self, tmp_path, monkeypatch):
        from hermes_cli.auth import NOUS_SHARED_STORE_FILENAME, _read_shared_nous_state

        shared = tmp_path / "shared"
        shared.mkdir()
        (shared / NOUS_SHARED_STORE_FILENAME).write_text(
            '{"refresh_token": "", "access_token": "at"}', encoding="utf-8"
        )
        monkeypatch.setenv("HERMES_SHARED_AUTH_DIR", str(shared))
        assert _read_shared_nous_state() is None

    def test_bom_shared_store_happy_path(self, tmp_path, monkeypatch):
        from hermes_cli.auth import NOUS_SHARED_STORE_FILENAME, _read_shared_nous_state

        shared = tmp_path / "shared"
        shared.mkdir()
        (shared / NOUS_SHARED_STORE_FILENAME).write_bytes(
            b"\xef\xbb\xbf"
            + b'{"refresh_token": "r1", "access_token": "a1"}'
        )
        monkeypatch.setenv("HERMES_SHARED_AUTH_DIR", str(shared))
        state = _read_shared_nous_state()
        assert state["refresh_token"] == "r1"
        assert state["access_token"] == "a1"
