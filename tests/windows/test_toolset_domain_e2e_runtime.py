"""Unit tests voor ``windows/scripts/toolset_domain_e2e_runtime.py``."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
RUNTIME_SCRIPT = REPO / "windows" / "scripts" / "toolset_domain_e2e_runtime.py"


def _load_runtime() -> object:
    spec = importlib.util.spec_from_file_location("toolset_domain_e2e_runtime", RUNTIME_SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def runtime_mod():
    assert RUNTIME_SCRIPT.is_file()
    return _load_runtime()


@pytest.fixture
def env_vars(tmp_path: Path) -> dict[str, str]:
    hermes = tmp_path / "hermes"
    hermes.mkdir()
    (hermes / "config.yaml").write_text(
        "platform_toolsets:\n  cli: []\n", encoding="utf-8"
    )
    return {
        "HERMES_TOOLSET_E2E_REPO": str(REPO),
        "HERMES_TOOLSET_E2E_HOME": str(hermes),
        "PYTHONPATH": str(REPO),
    }


class TestMainEnvGuard:
    def test_missing_repo_env_returns_one(self, runtime_mod, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HERMES_TOOLSET_E2E_REPO", raising=False)
        monkeypatch.delenv("HERMES_TOOLSET_E2E_HOME", raising=False)
        monkeypatch.setenv("PYTHONPATH", str(REPO))
        assert runtime_mod.main() == 1

    def test_missing_home_env_returns_one(self, runtime_mod, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HERMES_TOOLSET_E2E_REPO", str(REPO))
        monkeypatch.delenv("HERMES_TOOLSET_E2E_HOME", raising=False)
        monkeypatch.setenv("PYTHONPATH", str(REPO))
        assert runtime_mod.main() == 1


class TestMainHappyPath:
    def test_minimal_hermes_passes(self, runtime_mod, env_vars: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
        for k, v in env_vars.items():
            monkeypatch.setenv(k, v)
        hermes = Path(env_vars["HERMES_TOOLSET_E2E_HOME"])
        manifest = yaml.safe_load((REPO / "docs/domain_toolsets.yaml").read_text(encoding="utf-8"))
        for name in manifest.get("profiles", {}):
            prof = hermes / "profiles" / name
            prof.mkdir(parents=True, exist_ok=True)
            spec = manifest["profiles"][name]
            cli = (spec.get("platform_toolsets") or {}).get("cli") or []
            (prof / "config.yaml").write_text(
                yaml.safe_dump({"platform_toolsets": {"cli": list(cli)}}),
                encoding="utf-8",
            )

        mock_tools = MagicMock(return_value=[])
        mock_enabled = MagicMock(return_value=set())

        with patch("overlay.bootstrap.install", lambda: None):
            with patch("hermes_cli.tools_config._get_platform_tools", mock_enabled):
                with patch("model_tools.get_tool_definitions", mock_tools):
                    rc = runtime_mod.main()
        assert rc == 0

    def test_user_customized_profile_skipped(
        self, runtime_mod, env_vars: dict[str, str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for k, v in env_vars.items():
            monkeypatch.setenv(k, v)
        hermes = Path(env_vars["HERMES_TOOLSET_E2E_HOME"])
        prof = hermes / "profiles" / "legal"
        prof.mkdir(parents=True)
        (prof / "config.yaml").write_text(
            yaml.safe_dump(
                {
                    "platform_toolsets": {
                        "cli": ["mcp", "browser", "extra"],
                        "_user_customized": {"cli": True},
                    }
                }
            ),
            encoding="utf-8",
        )
        manifest = yaml.safe_load((REPO / "docs/domain_toolsets.yaml").read_text(encoding="utf-8"))
        for name, spec in manifest.get("profiles", {}).items():
            if name == "legal":
                continue
            pdir = hermes / "profiles" / name
            pdir.mkdir(parents=True, exist_ok=True)
            cli = (spec.get("platform_toolsets") or {}).get("cli") or []
            (pdir / "config.yaml").write_text(
                yaml.safe_dump({"platform_toolsets": {"cli": list(cli)}}),
                encoding="utf-8",
            )

        mock_tools = MagicMock(return_value=[])
        mock_enabled = MagicMock(return_value=set())

        def _is_custom(cfg: dict, platform: str) -> bool:
            pt = cfg.get("platform_toolsets") or {}
            meta = pt.get("_user_customized") or {}
            return bool(meta.get(platform)) if isinstance(meta, dict) else bool(meta)

        with patch("overlay.bootstrap.install", lambda: None):
            with patch("hermes_cli.tools_config._platform_toolsets_user_customized", side_effect=_is_custom):
                with patch("hermes_cli.tools_config._get_platform_tools", mock_enabled):
                    with patch("model_tools.get_tool_definitions", mock_tools):
                        rc = runtime_mod.main()
        assert rc == 0


class TestMainNegative:
    def test_missing_profile_config_fails(
        self, runtime_mod, env_vars: dict[str, str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        for k, v in env_vars.items():
            monkeypatch.setenv(k, v)
        with patch("overlay.bootstrap.install", lambda: None):
            rc = runtime_mod.main()
        assert rc == 1
        assert "config.yaml ontbreekt" in capsys.readouterr().out

    def test_root_cli_non_empty_fails(
        self, runtime_mod, env_vars: dict[str, str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for k, v in env_vars.items():
            monkeypatch.setenv(k, v)
        hermes = Path(env_vars["HERMES_TOOLSET_E2E_HOME"])
        (hermes / "config.yaml").write_text(
            "platform_toolsets:\n  cli: [mcp]\n", encoding="utf-8"
        )
        manifest = yaml.safe_load((REPO / "docs/domain_toolsets.yaml").read_text(encoding="utf-8"))
        for name, spec in manifest.get("profiles", {}).items():
            pdir = hermes / "profiles" / name
            pdir.mkdir(parents=True, exist_ok=True)
            cli = (spec.get("platform_toolsets") or {}).get("cli") or []
            (pdir / "config.yaml").write_text(
                yaml.safe_dump({"platform_toolsets": {"cli": list(cli)}}),
                encoding="utf-8",
            )
        mock_tools = MagicMock(return_value=[])
        mock_enabled = MagicMock(return_value=set())
        with patch("overlay.bootstrap.install", lambda: None):
            with patch("hermes_cli.tools_config._get_platform_tools", mock_enabled):
                with patch("model_tools.get_tool_definitions", mock_tools):
                    assert runtime_mod.main() == 1

    def test_restores_hermes_home_on_exit(
        self, runtime_mod, env_vars: dict[str, str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for k, v in env_vars.items():
            monkeypatch.setenv(k, v)
        monkeypatch.setenv("HERMES_HOME", "/original/home")
        with patch("overlay.bootstrap.install", lambda: None):
            runtime_mod.main()
        assert os.environ.get("HERMES_HOME") == "/original/home"

    def test_clears_hermes_home_when_unset_before(
        self, runtime_mod, env_vars: dict[str, str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for k, v in env_vars.items():
            monkeypatch.setenv(k, v)
        monkeypatch.delenv("HERMES_HOME", raising=False)
        with patch("overlay.bootstrap.install", lambda: None):
            runtime_mod.main()
        assert os.environ.get("HERMES_HOME") is None
