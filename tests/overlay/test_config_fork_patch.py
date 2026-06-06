"""Unit tests for overlay.hermes_cli.config_fork_patch."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest
import yaml

from overlay.bootstrap import install
from overlay.hermes_cli import config_fork_patch as cfp


@pytest.fixture(autouse=True)
def _bootstrap():
    install()
    yield


class TestRebindLoadConfigReferences:
    def test_rebinds_stale_module_binding(self):
        import hermes_cli.config as config_mod

        stale = MagicMock(name="stale_load_config")
        fake_mod = types.ModuleType("hermes_test_stale_load_config")
        fake_mod.load_config = stale
        fake_mod.load_config_readonly = MagicMock(name="stale_ro")
        sys.modules["hermes_test_stale_load_config"] = fake_mod
        try:
            cfp._rebind_load_config_references(config_mod)
            assert fake_mod.load_config is config_mod.load_config
            assert fake_mod.load_config_readonly is config_mod.load_config_readonly
        finally:
            sys.modules.pop("hermes_test_stale_load_config", None)

    def test_skips_modules_without_load_config(self):
        import hermes_cli.config as config_mod

        bare = types.ModuleType("hermes_test_bare_module")
        sys.modules["hermes_test_bare_module"] = bare
        try:
            cfp._rebind_load_config_references(config_mod)
        finally:
            sys.modules.pop("hermes_test_bare_module", None)


class TestApplyProfileInheritance:
    def test_non_profile_home_returns_unchanged(self, monkeypatch):
        monkeypatch.setattr(
            "hermes_cli.profile_model_inheritance.is_profile_hermes_home",
            lambda: False,
        )
        cfg = {"model": {"provider": "nous"}}
        assert cfp._apply_profile_inheritance(cfg) is cfg

    def test_profile_inherits_root_providers(self, tmp_path, monkeypatch):
        root = tmp_path / "hermes"
        legal = root / "profiles" / "legal"
        legal.mkdir(parents=True)
        (root / "config.yaml").write_text(
            yaml.safe_dump(
                {
                    "model": {"default": "deepseek-v4-pro", "provider": "venice"},
                    "providers": {"venice": {"api_key_env": "VENICE_API_KEY"}},
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        (legal / "config.yaml").write_text("{}", encoding="utf-8")
        monkeypatch.setenv("HERMES_HOME", str(legal))
        monkeypatch.setenv("HERMES_WIN_PREFER_LOCALAPPDATA", "0")

        import hermes_cli.profile_model_inheritance as pmi

        pmi.bust_config_caches(root)
        from hermes_cli.config import load_config

        cfg = load_config()
        assert cfg.get("providers", {}).get("venice")
        assert cfg.get("model", {}).get("provider") == "venice"


class TestGetConfigValue:
    def test_empty_key_prints_nothing(self, capsys):
        cfp.get_config_value("")
        assert capsys.readouterr().out == ""

    def test_missing_nested_key_prints_nothing(self, monkeypatch, capsys):
        monkeypatch.setattr(
            "hermes_cli.config.load_config",
            lambda: {"auxiliary": {}},
        )
        cfp.get_config_value("auxiliary.vision.provider")
        assert capsys.readouterr().out == ""

    def test_invalid_list_index_prints_nothing(self, monkeypatch, capsys):
        monkeypatch.setattr(
            "hermes_cli.config.load_config",
            lambda: {"items": ["a"]},
        )
        cfp.get_config_value("items.notanint")
        assert capsys.readouterr().out == ""


class TestApplyConfigForkPatch:
    def test_idempotent(self):
        import hermes_cli.config as config_mod

        first = config_mod.load_config
        cfp.apply_config_fork_patch()
        second = config_mod.load_config
        assert first is second
