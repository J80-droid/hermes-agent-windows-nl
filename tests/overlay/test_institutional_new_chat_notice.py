"""Tests for SOUL-sync new-chat reminder flag."""

from __future__ import annotations

import json

from hermes_cli import institutional_new_chat_notice as notice


def test_acknowledge_clears_notice(tmp_path, monkeypatch):
    monkeypatch.setattr(notice, "_hermes_state_dir", lambda: tmp_path)
    path = notice.notice_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"reason": "test"}), encoding="utf-8")
    assert notice.read_new_chat_notice() is not None
    assert notice.acknowledge_new_chat_notice() is True
    assert not path.is_file()
    assert notice.format_new_chat_notice_rich() is None
