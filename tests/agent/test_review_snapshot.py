"""Unit tests for agent/review_snapshot.py."""

from __future__ import annotations

import pytest

from agent.review_snapshot import (
    background_review_message_limit,
    snapshot_messages_for_background_review,
)


class TestBackgroundReviewMessageLimit:
    def test_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("HERMES_BG_REVIEW_MAX_MESSAGES", raising=False)
        assert background_review_message_limit() == 40

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("HERMES_BG_REVIEW_MAX_MESSAGES", "10")
        assert background_review_message_limit() == 10

    def test_invalid_env_falls_back_to_40(self, monkeypatch):
        monkeypatch.setenv("HERMES_BG_REVIEW_MAX_MESSAGES", "not-a-number")
        assert background_review_message_limit() == 40

    def test_negative_clamped_to_zero(self, monkeypatch):
        monkeypatch.setenv("HERMES_BG_REVIEW_MAX_MESSAGES", "-5")
        assert background_review_message_limit() == 0


class TestSnapshotMessagesForBackgroundReview:
    def _msgs(self, n: int):
        return [{"role": "user", "content": str(i)} for i in range(n)]

    def test_none_returns_empty(self):
        assert snapshot_messages_for_background_review(None) == []

    def test_empty_list_returns_empty(self):
        assert snapshot_messages_for_background_review([]) == []

    def test_under_limit_returns_copy_of_all(self, monkeypatch):
        monkeypatch.setenv("HERMES_BG_REVIEW_MAX_MESSAGES", "5")
        src = self._msgs(3)
        out = snapshot_messages_for_background_review(src)
        assert out == src
        assert out is not src

    def test_over_limit_returns_tail(self, monkeypatch):
        monkeypatch.setenv("HERMES_BG_REVIEW_MAX_MESSAGES", "2")
        src = self._msgs(5)
        out = snapshot_messages_for_background_review(src)
        assert len(out) == 2
        assert out[0]["content"] == "3"
        assert out[1]["content"] == "4"

    def test_limit_zero_returns_full_list(self, monkeypatch):
        monkeypatch.setenv("HERMES_BG_REVIEW_MAX_MESSAGES", "0")
        src = self._msgs(4)
        out = snapshot_messages_for_background_review(src)
        assert len(out) == 4
