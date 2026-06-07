"""Doctor auth.json UTF-8 BOM detection and --fix repair."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_repo = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_repo))


@pytest.fixture
def hermes_tree_with_bom_auth(tmp_path, monkeypatch):
    root = tmp_path / "hermes"
    prof = root / "profiles" / "legal"
    prof.mkdir(parents=True)
    auth = prof / "auth.json"
    auth.write_bytes(
        b"\xef\xbb\xbf" + json.dumps({"active_provider": "venice"}).encode("utf-8")
    )
    monkeypatch.setenv("HERMES_HOME", str(prof))
    monkeypatch.setenv("HERMES_WIN_PREFER_LOCALAPPDATA", "0")
    monkeypatch.setattr("hermes_constants.get_default_hermes_root", lambda: root)
    return root, auth


def test_auth_json_files_with_bom_detects_profile(hermes_tree_with_bom_auth):
    _root, auth = hermes_tree_with_bom_auth
    from hermes_cli.doctor import _auth_json_files_with_bom

    found = _auth_json_files_with_bom()
    assert auth in found


def test_auth_json_files_with_bom_includes_root(tmp_path, monkeypatch):
    root = tmp_path / "hermes"
    root.mkdir()
    auth = root / "auth.json"
    auth.write_bytes(b"\xef\xbb\xbf" + b"{}")
    monkeypatch.setenv("HERMES_HOME", str(root))
    monkeypatch.setenv("HERMES_WIN_PREFER_LOCALAPPDATA", "0")
    monkeypatch.setattr("hermes_constants.get_default_hermes_root", lambda: root)
    from hermes_cli.doctor import _auth_json_files_with_bom

    assert auth in _auth_json_files_with_bom()


def test_auth_json_files_with_bom_skips_unreadable(tmp_path, monkeypatch):
    root = tmp_path / "hermes"
    prof = root / "profiles" / "legal"
    prof.mkdir(parents=True)
    auth = prof / "auth.json"
    auth.write_bytes(b"\xef\xbb\xbf" + b"{}")
    monkeypatch.setenv("HERMES_HOME", str(prof))
    monkeypatch.setenv("HERMES_WIN_PREFER_LOCALAPPDATA", "0")
    monkeypatch.setattr("hermes_constants.get_default_hermes_root", lambda: root)
    from hermes_cli.doctor import _auth_json_files_with_bom

    with patch.object(Path, "read_bytes", side_effect=OSError("denied")):
        assert _auth_json_files_with_bom() == []


def test_repair_auth_json_bom_all_strips_bom(hermes_tree_with_bom_auth):
    _root, auth = hermes_tree_with_bom_auth
    from overlay.bootstrap import install
    from hermes_cli.doctor import _auth_json_files_with_bom, _repair_auth_json_bom_all

    install()
    repaired = _repair_auth_json_bom_all()
    assert repaired
    assert not auth.read_bytes().startswith(b"\xef\xbb\xbf")
    assert _auth_json_files_with_bom() == []


def test_repair_auth_json_bom_all_returns_empty_when_repair_raises(
    hermes_tree_with_bom_auth, monkeypatch
):
    from overlay.bootstrap import install
    from hermes_cli.doctor import _repair_auth_json_bom_all

    install()

    def _boom() -> list[str]:
        raise RuntimeError("repair failed")

    monkeypatch.setattr("hermes_cli.auth.repair_all_auth_json_bom", _boom)
    assert _repair_auth_json_bom_all() == []


def test_doctor_reports_no_bom_when_clean(tmp_path, monkeypatch):
    root = tmp_path / "hermes"
    prof = root / "profiles" / "core"
    prof.mkdir(parents=True)
    (prof / "auth.json").write_text('{"active_provider": "nous"}', encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(prof))
    monkeypatch.setenv("HERMES_WIN_PREFER_LOCALAPPDATA", "0")
    monkeypatch.setattr("hermes_constants.get_default_hermes_root", lambda: root)
    from hermes_cli.doctor import _auth_json_files_with_bom

    assert _auth_json_files_with_bom() == []
