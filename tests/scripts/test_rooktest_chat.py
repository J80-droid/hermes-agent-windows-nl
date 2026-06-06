"""Tests for legal chat rooktest helper."""

from __future__ import annotations

from unittest.mock import patch

from scripts.rag_pipeline import _rooktest_chat as mod


def test_inference_available_with_resolved_api_key(monkeypatch):
    monkeypatch.setattr(mod, "_prepare_profile", lambda _p: None)
    monkeypatch.setattr(mod, "_model_provider_from_config", lambda: ("venice", "deepseek-v4-pro"))
    runtime = {"api_key": "sk-real", "provider": "custom", "requested_provider": "venice"}
    with patch("hermes_cli.runtime_provider.resolve_runtime_provider", return_value=runtime):
        assert mod.inference_available("legal") is True


def test_inference_unavailable_without_model(monkeypatch):
    monkeypatch.setattr(mod, "_prepare_profile", lambda _p: None)
    monkeypatch.setattr(mod, "_model_provider_from_config", lambda: ("", ""))
    assert mod.inference_available("legal") is False


def test_run_chat_skips_when_no_inference(monkeypatch):
    monkeypatch.setattr(mod, "inference_available", lambda _p=True: False)
    assert mod.run_chat_rooktest("legal") == 2
