"""Defaults voor institutionele RAG-env."""

from __future__ import annotations

import os

from rag_institutional_defaults import (
    DEFAULT_LIVE_STALE_SEC,
    DEFAULT_QUIET_TORCH,
    ENV_LIVE_STALE_SEC,
    ENV_QUIET_TORCH,
    apply_institutional_env,
)


def test_apply_sets_defaults_when_unset(monkeypatch):
    monkeypatch.delenv(ENV_LIVE_STALE_SEC, raising=False)
    monkeypatch.delenv(ENV_QUIET_TORCH, raising=False)
    snap = apply_institutional_env()
    assert snap[ENV_LIVE_STALE_SEC] == str(DEFAULT_LIVE_STALE_SEC)
    assert snap[ENV_QUIET_TORCH] == DEFAULT_QUIET_TORCH


def test_apply_respects_explicit_override(monkeypatch):
    monkeypatch.setenv(ENV_LIVE_STALE_SEC, "300")
    monkeypatch.setenv(ENV_QUIET_TORCH, "0")
    snap = apply_institutional_env()
    assert snap[ENV_LIVE_STALE_SEC] == "300"
    assert snap[ENV_QUIET_TORCH] == "0"
    assert os.environ[ENV_LIVE_STALE_SEC] == "300"
