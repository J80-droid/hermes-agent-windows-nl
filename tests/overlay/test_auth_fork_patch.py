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
        assert getattr(auth, "_fork_read_auth_json_patch_applied", False) is True
