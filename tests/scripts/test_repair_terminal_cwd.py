"""Unit tests for scripts/repair_terminal_cwd.py (happy path + edge cases)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def hermes_profile_home(tmp_path):
    home = tmp_path / "profiles" / "core"
    home.mkdir(parents=True)
    (home / "config.yaml").write_text(
        yaml.safe_dump({"terminal": {"backend": "local", "cwd": "."}}, sort_keys=False),
        encoding="utf-8",
    )
    return home


def _import_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "repair_terminal_cwd",
        REPO / "scripts" / "repair_terminal_cwd.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_normalize_path_rejects_empty():
    mod = _import_module()
    with pytest.raises(ValueError, match="empty"):
        mod._normalize_path("   ")


def test_normalize_path_rejects_missing_directory(tmp_path):
    mod = _import_module()
    missing = tmp_path / "does-not-exist"
    with pytest.raises(ValueError, match="not a directory"):
        mod._normalize_path(str(missing))


def test_normalize_path_returns_posix(tmp_path):
    mod = _import_module()
    ws = tmp_path / "workspace"
    ws.mkdir()
    assert mod._normalize_path(str(ws)) == ws.resolve().as_posix()


def test_read_env_cwd_ignores_comments_and_placeholders(tmp_path):
    mod = _import_module()
    env = tmp_path / ".env"
    env.write_text(
        "\n".join(
            [
                "# TERMINAL_CWD=.",
                "TERMINAL_CWD=.",
                "TERMINAL_CWD=",
                "MESSAGING_CWD=auto",
                "TERMINAL_CWD=/real/path",
            ]
        ),
        encoding="utf-8",
    )
    terminal, messaging = mod._read_env_cwd(env)
    assert terminal == "/real/path"
    assert messaging is None


def test_read_env_cwd_prefers_terminal_over_messaging(tmp_path):
    mod = _import_module()
    env = tmp_path / ".env"
    env.write_text(
        "MESSAGING_CWD=/msg\nTERMINAL_CWD=/term\n",
        encoding="utf-8",
    )
    terminal, messaging = mod._read_env_cwd(env)
    assert terminal == "/term"
    assert messaging == "/msg"


def test_strip_env_cwd_lines_keeps_comments_and_placeholders(tmp_path):
    mod = _import_module()
    env = tmp_path / ".env"
    env.write_text(
        "# TERMINAL_CWD=legacy\nTERMINAL_CWD=.\nTERMINAL_CWD=/remove/me\nKEEP=1\n",
        encoding="utf-8",
    )
    assert mod._strip_env_cwd_lines(env) is True
    text = env.read_text(encoding="utf-8")
    assert "TERMINAL_CWD=/remove/me" not in text
    assert "# TERMINAL_CWD=legacy" in text
    assert "TERMINAL_CWD=." in text
    assert "KEEP=1" in text


def test_config_cwd_is_placeholder_edge_cases():
    mod = _import_module()
    assert mod._config_cwd_is_placeholder({}) is True
    assert mod._config_cwd_is_placeholder({"terminal": "bad"}) is True
    assert mod._config_cwd_is_placeholder({"terminal": {"cwd": "auto"}}) is True
    assert mod._config_cwd_is_placeholder({"terminal": {"cwd": "/abs"}}) is False


def test_migrate_from_env_sets_config_and_strips_env(hermes_profile_home, tmp_path):
    mod = _import_module()
    workspace = tmp_path / "project"
    workspace.mkdir()
    env = hermes_profile_home / ".env"
    env.write_text(f"TERMINAL_CWD={workspace}\n", encoding="utf-8")
    cfg_path = hermes_profile_home / "config.yaml"
    config = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    written: list[tuple[str, str]] = []

    def _set(key: str, value: str) -> None:
        written.append((key, value))

    rc = mod.migrate_terminal_cwd(
        config_path=cfg_path,
        config=config,
        workspace=None,
        set_config_value_fn=_set,
    )
    assert rc == 0
    assert written == [("terminal.cwd", workspace.resolve().as_posix())]
    assert "TERMINAL_CWD=" not in env.read_text(encoding="utf-8")


def test_migrate_uses_workspace_when_env_clean(hermes_profile_home, tmp_path):
    mod = _import_module()
    workspace = tmp_path / "repo"
    workspace.mkdir()
    cfg_path = hermes_profile_home / "config.yaml"
    config = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    written: list[tuple[str, str]] = []

    rc = mod.migrate_terminal_cwd(
        config_path=cfg_path,
        config=config,
        workspace=workspace,
        set_config_value_fn=lambda k, v: written.append((k, v)),
    )
    assert rc == 0
    assert written == [("terminal.cwd", workspace.resolve().as_posix())]


def test_migrate_idempotent_when_config_explicit(hermes_profile_home, tmp_path):
    mod = _import_module()
    workspace = tmp_path / "repo"
    workspace.mkdir()
    cfg_path = hermes_profile_home / "config.yaml"
    explicit = workspace.resolve().as_posix()
    cfg_path.write_text(
        yaml.safe_dump({"terminal": {"cwd": explicit}}, sort_keys=False),
        encoding="utf-8",
    )
    env = hermes_profile_home / ".env"
    env.write_text(f"TERMINAL_CWD={workspace}\n", encoding="utf-8")
    config = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    setter = MagicMock()

    rc = mod.migrate_terminal_cwd(
        config_path=cfg_path,
        config=config,
        workspace=workspace,
        set_config_value_fn=setter,
    )
    assert rc == 0
    setter.assert_not_called()
    assert "TERMINAL_CWD=" not in env.read_text(encoding="utf-8")


def test_migrate_dry_run_does_not_mutate(hermes_profile_home, tmp_path):
    mod = _import_module()
    workspace = tmp_path / "repo"
    workspace.mkdir()
    env = hermes_profile_home / ".env"
    env.write_text(f"TERMINAL_CWD={workspace}\n", encoding="utf-8")
    cfg_path = hermes_profile_home / "config.yaml"
    before_cfg = cfg_path.read_text(encoding="utf-8")
    before_env = env.read_text(encoding="utf-8")
    config = yaml.safe_load(before_cfg)

    rc = mod.migrate_terminal_cwd(
        config_path=cfg_path,
        config=config,
        workspace=workspace,
        dry_run=True,
        set_config_value_fn=MagicMock(),
    )
    assert rc == 0
    assert cfg_path.read_text(encoding="utf-8") == before_cfg
    assert env.read_text(encoding="utf-8") == before_env


def test_migrate_invalid_path_returns_error(hermes_profile_home, tmp_path):
    mod = _import_module()
    cfg_path = hermes_profile_home / "config.yaml"
    config = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    rc = mod.migrate_terminal_cwd(
        config_path=cfg_path,
        config=config,
        workspace=tmp_path / "missing-dir",
        set_config_value_fn=MagicMock(),
    )
    assert rc == 1


def test_migrate_noop_without_sources(hermes_profile_home):
    mod = _import_module()
    cfg_path = hermes_profile_home / "config.yaml"
    config = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    rc = mod.migrate_terminal_cwd(
        config_path=cfg_path,
        config=config,
        set_config_value_fn=MagicMock(),
    )
    assert rc == 0


def test_main_cli_on_isolated_home(hermes_profile_home, tmp_path, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(hermes_profile_home))
    monkeypatch.setenv("HERMES_WIN_PREFER_LOCALAPPDATA", "0")
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts" / "repair_terminal_cwd.py"),
            "--workspace",
            str(workspace),
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = proc.stdout + proc.stderr
    assert "terminal.cwd" in out.lower() or "[OK]" in out
