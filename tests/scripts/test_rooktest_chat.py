"""Tests for legal chat rooktest helper."""

from __future__ import annotations

import subprocess
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


def test_ensure_overlay_calls_install(monkeypatch):
    installed: list[bool] = []

    monkeypatch.setattr("overlay.bootstrap._installed", False)
    monkeypatch.setattr(
        "overlay.bootstrap.install",
        lambda: installed.append(True),
    )
    mod._ensure_overlay()
    assert installed == [True]


def test_chat_toolsets_uses_mcp_server_names(monkeypatch):
    monkeypatch.setattr(
        "hermes_cli.config.load_config",
        lambda: {"mcp_servers": {"lancedb-legal": {"command": "python"}}},
    )
    arg = mod._chat_toolsets_arg()
    assert "lancedb-legal" in arg
    assert "mcp" not in arg.split(",")
    assert "file" in arg and "memory" in arg


def test_chat_toolsets_fallback_without_mcp(monkeypatch):
    monkeypatch.setattr("hermes_cli.config.load_config", lambda: {})
    assert mod._chat_toolsets_arg() == "file,memory"


def test_chat_toolsets_on_load_config_failure(monkeypatch):
    def _boom():
        raise RuntimeError("config unavailable")

    monkeypatch.setattr("hermes_cli.config.load_config", _boom)
    assert mod._chat_toolsets_arg() == "file,memory"


def test_chat_toolsets_ignores_non_dict_mcp_servers(monkeypatch):
    monkeypatch.setattr("hermes_cli.config.load_config", lambda: {"mcp_servers": []})
    assert mod._chat_toolsets_arg() == "file,memory"


def test_chat_toolsets_dedupes_names(monkeypatch):
    monkeypatch.setattr(
        "hermes_cli.config.load_config",
        lambda: {
            "mcp_servers": {"lancedb-legal": {}, "lancedb-core": {}},
        },
    )
    arg = mod._chat_toolsets_arg()
    assert arg.count("file") == 1 and arg.count("memory") == 1


def test_chat_timeout_invalid_env_falls_back(monkeypatch):
    monkeypatch.setenv("HERMES_ROOKTEST_CHAT_TIMEOUT", "not-a-number")
    assert mod._chat_timeout_sec() == 600


def test_chat_timeout_non_positive_falls_back(monkeypatch):
    monkeypatch.setenv("HERMES_ROOKTEST_CHAT_TIMEOUT", "0")
    assert mod._chat_timeout_sec() == 600


def test_run_chat_passes_mcp_toolsets_in_cmd(monkeypatch):
    monkeypatch.setattr(mod, "inference_available", lambda _p: True)
    monkeypatch.setattr(mod, "_prepare_profile", lambda _p: None)
    monkeypatch.setattr(mod, "_model_provider_from_config", lambda: ("venice", "m"))
    monkeypatch.setattr(mod, "_chat_toolsets_arg", lambda: "lancedb-legal,file,memory")
    captured: list[list[str]] = []

    class _Proc:
        returncode = 0

    monkeypatch.setattr(
        mod.subprocess,
        "run",
        lambda cmd, **kw: captured.append(cmd) or _Proc(),
    )
    mod.run_chat_rooktest("legal")
    assert captured
    ts_idx = captured[0].index("--toolsets")
    assert captured[0][ts_idx + 1] == "lancedb-legal,file,memory"


def test_run_chat_uses_overlay_entry(monkeypatch):
    monkeypatch.setattr(mod, "inference_available", lambda _p: True)
    monkeypatch.setattr(mod, "_prepare_profile", lambda _p: None)
    monkeypatch.setattr(mod, "_model_provider_from_config", lambda: ("venice", "deepseek-v4-pro"))
    captured: list[list[str]] = []

    class _Proc:
        returncode = 0

    monkeypatch.setattr(
        mod.subprocess,
        "run",
        lambda cmd, **kw: captured.append(cmd) or _Proc(),
    )
    assert mod.run_chat_rooktest("legal") == 0
    assert captured
    assert str(mod._OVERLAY_ENTRY) in captured[0]
    assert "venice" in captured[0]
    assert "deepseek-v4-pro" in captured[0]


def test_inference_unavailable_on_auth_error(monkeypatch):
    monkeypatch.setattr(mod, "_prepare_profile", lambda _p: None)
    monkeypatch.setattr(mod, "_model_provider_from_config", lambda: ("venice", "deepseek-v4-pro"))
    from hermes_cli.auth import AuthError

    with patch(
        "hermes_cli.runtime_provider.resolve_runtime_provider",
        side_effect=AuthError("no key"),
    ):
        assert mod.inference_available("legal") is False


def test_inference_unavailable_on_resolve_exception(monkeypatch):
    monkeypatch.setattr(mod, "_prepare_profile", lambda _p: None)
    monkeypatch.setattr(mod, "_model_provider_from_config", lambda: ("venice", "m"))
    with patch(
        "hermes_cli.runtime_provider.resolve_runtime_provider",
        side_effect=RuntimeError("boom"),
    ):
        assert mod.inference_available("legal") is False


def test_inference_falls_back_to_auth_status(monkeypatch):
    monkeypatch.setattr(mod, "_prepare_profile", lambda _p: None)
    monkeypatch.setattr(mod, "_model_provider_from_config", lambda: ("venice", "m"))
    runtime = {"api_key": "", "provider": "custom", "requested_provider": "venice"}
    with (
        patch("hermes_cli.runtime_provider.resolve_runtime_provider", return_value=runtime),
        patch("hermes_cli.auth.has_usable_secret", return_value=False),
        patch("hermes_cli.auth.get_auth_status", return_value={"logged_in": True}),
    ):
        assert mod.inference_available("legal") is True


def test_run_chat_timeout_returns_1(monkeypatch):
    monkeypatch.setattr(mod, "inference_available", lambda _p: True)
    monkeypatch.setattr(mod, "_prepare_profile", lambda _p: None)
    monkeypatch.setattr(mod, "_model_provider_from_config", lambda: ("venice", "m"))

    def _timeout(*_a, **_kw):
        raise subprocess.TimeoutExpired(cmd=["chat"], timeout=1)

    monkeypatch.setattr(mod.subprocess, "run", _timeout)
    assert mod.run_chat_rooktest("legal") == 1


def test_run_chat_nonzero_exit_returns_1(monkeypatch):
    monkeypatch.setattr(mod, "inference_available", lambda _p: True)
    monkeypatch.setattr(mod, "_prepare_profile", lambda _p: None)
    monkeypatch.setattr(mod, "_model_provider_from_config", lambda: ("venice", "m"))

    class _Proc:
        returncode = 401

    monkeypatch.setattr(mod.subprocess, "run", lambda *_a, **_kw: _Proc())
    assert mod.run_chat_rooktest("legal") == 1


def test_model_provider_from_config_string_model(monkeypatch):
    monkeypatch.setattr(
        "hermes_cli.config.load_config",
        lambda: {"model": "gpt-4"},
    )
    assert mod._model_provider_from_config() == ("", "gpt-4")


def test_model_provider_from_config_invalid_returns_empty(monkeypatch):
    monkeypatch.setattr("hermes_cli.config.load_config", lambda: {"model": 42})
    assert mod._model_provider_from_config() == ("", "")


def test_check_all_missing_profiles_dir(tmp_path):
    import os
    import sys

    env = os.environ.copy()
    env["HERMES_HOME"] = str(tmp_path / "isolated")
    env["HERMES_WIN_PREFER_LOCALAPPDATA"] = "0"
    proc = subprocess.run(
        [sys.executable, str(mod.__file__), "--check-all"],
        cwd=str(mod._REPO),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 1
    assert "Profielenmap ontbreekt" in (proc.stdout + proc.stderr)
