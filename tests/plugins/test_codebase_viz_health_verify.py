"""Unit tests voor audits/verify_codebase_viz_health.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "audits"))

import verify_codebase_viz_health as verify  # noqa: E402


@pytest.fixture(autouse=True)
def _institutional_pygount_timeout_env(monkeypatch):
    monkeypatch.setenv("CODEBASE_VIZ_PYGOUNT_TIMEOUT", "600")
    monkeypatch.setattr(verify, "INSTITUTIONAL_DEFAULT_PYGOUNT_TIMEOUT_SEC", 600)


def test_extract_session_token_happy():
    html = '<script>window.__HERMES_SESSION_TOKEN__="tok-abc-123";</script>'
    assert verify.extract_session_token(html) == "tok-abc-123"


def test_extract_session_token_missing():
    assert verify.extract_session_token("<html></html>") is None
    assert verify.extract_session_token("") is None


def test_validate_health_body_ok():
    body = {"pygount_timeout_sec": 600, "plugin": "codebase-viz", "version": "2.5.0"}
    assert verify.validate_health_body(body) == []


def test_validate_health_body_respects_env(monkeypatch):
    monkeypatch.setenv("CODEBASE_VIZ_PYGOUNT_TIMEOUT", "300")
    body = {"pygount_timeout_sec": 300, "plugin": "codebase-viz"}
    assert verify.validate_health_body(body) == []


def test_validate_health_body_wrong_timeout():
    body = {"pygount_timeout_sec": 30, "plugin": "codebase-viz"}
    errs = verify.validate_health_body(body)
    assert any("pygount_timeout_sec" in e for e in errs)


def test_validate_health_body_missing_plugin():
    errs = verify.validate_health_body({"pygount_timeout_sec": 600})
    assert any("plugin" in e for e in errs)


def test_fetch_plugin_health_parses_json():
    payload = {"pygount_timeout_sec": 120, "plugin": "codebase-viz"}
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(payload).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        out = verify.fetch_plugin_health("http://127.0.0.1:9119", "tok")
    assert out["pygount_timeout_sec"] == 120


def test_main_no_token_returns_1(capsys):
    page = MagicMock()
    page.read.return_value = b"<html></html>"
    page.__enter__ = lambda s: s
    page.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=page):
        code = verify.main()
    assert code == 1
    out = capsys.readouterr().out
    assert "session token" in out.lower() or "Geen" in out


def test_main_validation_failure_returns_2(capsys):
    html = 'x __HERMES_SESSION_TOKEN__="t" y'
    health = {"pygount_timeout_sec": 30, "plugin": "codebase-viz"}
    with patch("urllib.request.urlopen") as mock_open:
        page = MagicMock()
        page.read.return_value = html.encode()
        page.__enter__ = lambda s: s
        page.__exit__ = MagicMock(return_value=False)

        health_resp = MagicMock()
        health_resp.status = 200
        health_resp.read.return_value = json.dumps(health).encode()
        health_resp.__enter__ = lambda s: s
        health_resp.__exit__ = MagicMock(return_value=False)

        mock_open.side_effect = [page, health_resp]
        code = verify.main()
    assert code == 2


def test_main_success_returns_0(capsys):
    html = 'x __HERMES_SESSION_TOKEN__="t" y'
    health = {
        "pygount_timeout_sec": 600,
        "plugin": "codebase-viz",
        "version": "2.5.0",
        "plugin_api_path": "/x/plugin_api.py",
    }
    with patch("urllib.request.urlopen") as mock_open:
        page = MagicMock()
        page.read.return_value = html.encode()
        page.__enter__ = lambda s: s
        page.__exit__ = MagicMock(return_value=False)

        health_resp = MagicMock()
        health_resp.status = 200
        health_resp.read.return_value = json.dumps(health).encode()
        health_resp.__enter__ = lambda s: s
        health_resp.__exit__ = MagicMock(return_value=False)

        mock_open.side_effect = [page, health_resp]
        code = verify.main()
    assert code == 0
    out = capsys.readouterr().out
    assert "pygount_timeout_sec=600" in out
