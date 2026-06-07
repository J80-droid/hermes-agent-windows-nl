"""CLI auto-handling of institutional_new_chat_required.json after sync."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from overlay.bootstrap import install


@pytest.fixture(autouse=True)
def _bootstrap():
    install()


@pytest.fixture
def notice_file(tmp_path, monkeypatch):
    hermes_dir = tmp_path / "hermes"
    hermes_dir.mkdir()
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    path = hermes_dir / "institutional_new_chat_required.json"
    path.write_text(
        json.dumps({"reason": "test sync", "smoke_test_prompt": "docs/x.md"}),
        encoding="utf-8",
    )
    return path


def test_apply_post_sync_acknowledges_when_empty_history(notice_file, monkeypatch):
    monkeypatch.delenv("HERMES_SKIP_AUTO_NEW_AFTER_SYNC", raising=False)
    from cli import HermesCLI

    cli = HermesCLI.__new__(HermesCLI)
    cli.conversation_history = []
    cli.new_session = MagicMock()

    cli._apply_post_sync_new_chat_notice()

    assert not notice_file.exists()
    cli.new_session.assert_not_called()


def test_apply_post_sync_new_session_when_history(notice_file, monkeypatch):
    monkeypatch.delenv("HERMES_SKIP_AUTO_NEW_AFTER_SYNC", raising=False)
    from cli import HermesCLI

    cli = HermesCLI.__new__(HermesCLI)
    cli.conversation_history = [{"role": "user", "content": "hi"}]
    cli.new_session = MagicMock()

    cli._apply_post_sync_new_chat_notice()

    cli.new_session.assert_called_once_with(silent=True)


def test_apply_post_sync_acknowledges_when_history_attr_missing(notice_file, monkeypatch):
    monkeypatch.delenv("HERMES_SKIP_AUTO_NEW_AFTER_SYNC", raising=False)
    from cli import HermesCLI

    cli = HermesCLI.__new__(HermesCLI)
    cli.new_session = MagicMock()

    cli._apply_post_sync_new_chat_notice()

    assert not notice_file.exists()
    cli.new_session.assert_not_called()


def test_apply_post_sync_survives_new_session_failure(notice_file, monkeypatch):
    monkeypatch.delenv("HERMES_SKIP_AUTO_NEW_AFTER_SYNC", raising=False)
    from cli import HermesCLI

    cli = HermesCLI.__new__(HermesCLI)
    cli.conversation_history = [{"role": "user", "content": "hi"}]
    cli.new_session = MagicMock(side_effect=RuntimeError("boom"))

    cli._apply_post_sync_new_chat_notice()  # must not raise
