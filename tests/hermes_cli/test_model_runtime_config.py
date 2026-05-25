"""Unit tests for hermes_cli.model_runtime_config.

Covers atomic persist, coherence detection, and repair. Mocks external I/O
(auth store, load_config, atomic_yaml_write, Nous credential resolution).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import yaml

_repo = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_repo))


@pytest.fixture
def hermes_tree(tmp_path, monkeypatch):
    """Profile HERMES_HOME with root config + auth (split-brain fixture)."""
    root = tmp_path / ".hermes"
    prof = root / "profiles" / "core"
    prof.mkdir(parents=True)
    (root / "config.yaml").write_text(
        "model:\n  provider: gemini\n  default: gemini-flash\n"
        "  base_url: https://generativelanguage.googleapis.com/v1beta\n",
        encoding="utf-8",
    )
    (prof / "config.yaml").write_text("agent:\n  max_turns: 30\n", encoding="utf-8")
    auth_payload = json.dumps({"version": 1, "active_provider": "nous", "providers": {}})
    (root / "auth.json").write_text(auth_payload, encoding="utf-8")
    (prof / "auth.json").write_text(auth_payload, encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(prof))
    monkeypatch.setenv("HERMES_WIN_PREFER_LOCALAPPDATA", "0")
    monkeypatch.setattr(
        "hermes_constants.get_default_hermes_root",
        lambda: root,
    )
    monkeypatch.setattr(
        "hermes_cli.profile_model_inheritance.root_config_path",
        lambda: root / "config.yaml",
    )
    return root, prof


@pytest.fixture
def flat_home(tmp_path, monkeypatch):
    """Flat HERMES_HOME (no profile subdir)."""
    home = tmp_path / "hermes"
    home.mkdir()
    (home / "config.yaml").write_text("model: legacy-string-model\n", encoding="utf-8")
    (home / "auth.json").write_text(
        json.dumps({"version": 1, "active_provider": "openrouter", "providers": {}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_WIN_PREFER_LOCALAPPDATA", "0")
    monkeypatch.setattr(
        "hermes_constants.get_default_hermes_root",
        lambda: home,
    )
    monkeypatch.setattr(
        "hermes_cli.profile_model_inheritance.root_config_path",
        lambda: home / "config.yaml",
    )
    return home


# ---------------------------------------------------------------------------
# Helpers (private functions)
# ---------------------------------------------------------------------------


class TestModelSectionFromConfig:
    def test_dict_model_passthrough(self):
        from hermes_cli.model_runtime_config import _model_section_from_config

        cfg = {"model": {"provider": "nous", "default": "x"}}
        assert _model_section_from_config(cfg) == {"provider": "nous", "default": "x"}

    def test_string_model_becomes_default_key(self):
        from hermes_cli.model_runtime_config import _model_section_from_config

        assert _model_section_from_config({"model": "  kimi-k2.5  "}) == {
            "default": "kimi-k2.5"
        }

    def test_empty_and_invalid_model(self):
        from hermes_cli.model_runtime_config import _model_section_from_config

        assert _model_section_from_config({}) == {}
        assert _model_section_from_config({"model": ""}) == {}
        assert _model_section_from_config({"model": 42}) == {}
        assert _model_section_from_config({"model": None}) == {}


class TestNormalizeProviderId:
    def test_strips_and_lowercases(self):
        from hermes_cli.model_runtime_config import _normalize_provider_id

        assert _normalize_provider_id("  OpenRouter  ") == "openrouter"
        assert _normalize_provider_id("") == ""
        assert _normalize_provider_id(None) == ""  # type: ignore[arg-type]


class TestReadRootYaml:
    def test_missing_file_returns_empty(self, flat_home):
        from hermes_cli.model_runtime_config import _read_root_yaml

        (flat_home / "config.yaml").unlink()
        assert _read_root_yaml() == {}

    def test_invalid_yaml_returns_empty(self, flat_home):
        from hermes_cli.model_runtime_config import _read_root_yaml

        (flat_home / "config.yaml").write_text("model: [\n", encoding="utf-8")
        assert _read_root_yaml() == {}

    def test_non_dict_root_returns_empty(self, flat_home):
        from hermes_cli.model_runtime_config import _read_root_yaml

        (flat_home / "config.yaml").write_text("just-a-string\n", encoding="utf-8")
        assert _read_root_yaml() == {}


class TestHostFromBaseUrl:
    def test_delegates_to_utils(self):
        from hermes_cli.model_runtime_config import _host_from_base_url

        with patch(
            "utils.base_url_hostname",
            return_value="inference-api.nousresearch.com",
        ):
            assert _host_from_base_url("https://inference-api.nousresearch.com/v1") == (
                "inference-api.nousresearch.com"
            )

    def test_returns_empty_on_utils_failure(self):
        from hermes_cli.model_runtime_config import _host_from_base_url

        with patch("utils.base_url_hostname", side_effect=ValueError("bad url")):
            assert _host_from_base_url("not-a-url") == ""


# ---------------------------------------------------------------------------
# persist_model_runtime
# ---------------------------------------------------------------------------


class TestPersistModelRuntimeHappyPath:
    def test_persist_writes_root_not_profile(self, hermes_tree):
        root, prof = hermes_tree
        from hermes_cli.model_runtime_config import persist_model_runtime

        result = persist_model_runtime(
            "nous",
            default_model="deepseek/deepseek-v4-flash:free",
            inference_base_url="https://inference-api.nousresearch.com/v1",
        )

        root_cfg = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))
        prof_cfg = yaml.safe_load((prof / "config.yaml").read_text(encoding="utf-8"))

        assert result.provider == "nous"
        assert result.config_path == root / "config.yaml"
        assert result.previous_provider == "gemini"
        assert root_cfg["model"]["provider"] == "nous"
        assert root_cfg["model"]["default"] == "deepseek/deepseek-v4-flash:free"
        assert root_cfg["model"]["base_url"] == "https://inference-api.nousresearch.com/v1"
        assert "generativelanguage" not in root_cfg["model"].get("base_url", "")
        assert "model" not in prof_cfg
        assert "api_key" not in root_cfg["model"]

    def test_persist_sync_auth_keeps_active_provider(self, hermes_tree):
        root, _prof = hermes_tree
        from hermes_cli.auth import _load_auth_store
        from hermes_cli.model_runtime_config import persist_model_runtime

        persist_model_runtime(
            "nous",
            default_model="deepseek/deepseek-v4-flash:free",
            inference_base_url="https://inference-api.nousresearch.com/v1",
        )
        auth = _load_auth_store()
        assert auth.get("active_provider") == "nous"
        disk = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))
        assert disk["model"]["provider"] == "nous"

    def test_provider_id_normalized(self, flat_home):
        from hermes_cli.model_runtime_config import persist_model_runtime

        persist_model_runtime("  NOUS ", default_model="m")
        cfg = yaml.safe_load((flat_home / "config.yaml").read_text(encoding="utf-8"))
        assert cfg["model"]["provider"] == "nous"


class TestPersistModelRuntimeEdgeCases:
    def test_preserves_existing_default_when_default_model_none(self, flat_home):
        from hermes_cli.model_runtime_config import persist_model_runtime

        (flat_home / "config.yaml").write_text(
            "model:\n  provider: gemini\n  default: keep-me\n",
            encoding="utf-8",
        )
        persist_model_runtime("openrouter", default_model=None)
        cfg = yaml.safe_load((flat_home / "config.yaml").read_text(encoding="utf-8"))
        assert cfg["model"]["default"] == "keep-me"
        assert cfg["model"]["provider"] == "openrouter"

    def test_migrates_legacy_model_key_to_default(self, flat_home):
        from hermes_cli.model_runtime_config import persist_model_runtime

        (flat_home / "config.yaml").write_text(
            "model:\n  provider: gemini\n  model: legacy-id\n",
            encoding="utf-8",
        )
        persist_model_runtime("nous", default_model=None)
        cfg = yaml.safe_load((flat_home / "config.yaml").read_text(encoding="utf-8"))
        assert cfg["model"]["default"] == "legacy-id"
        assert "model" not in cfg["model"]

    def test_clears_base_url_when_inference_empty(self, hermes_tree):
        root, _ = hermes_tree
        from hermes_cli.model_runtime_config import persist_model_runtime

        persist_model_runtime("nous", default_model="m", inference_base_url="")
        cfg = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))
        assert "base_url" not in cfg["model"]

    def test_strips_trailing_slash_from_base_url(self, flat_home):
        from hermes_cli.model_runtime_config import persist_model_runtime

        persist_model_runtime(
            "openrouter",
            default_model="m",
            inference_base_url="https://openrouter.ai/api/v1/",
        )
        cfg = yaml.safe_load((flat_home / "config.yaml").read_text(encoding="utf-8"))
        assert cfg["model"]["base_url"] == "https://openrouter.ai/api/v1"

    def test_sync_auth_false_skips_auth_write(self, flat_home):
        from hermes_cli.model_runtime_config import persist_model_runtime

        persist_model_runtime("nous", default_model="m", sync_auth=False)
        auth = json.loads((flat_home / "auth.json").read_text(encoding="utf-8"))
        assert auth["active_provider"] == "openrouter"

    def test_extra_model_fields_none_strips_secrets(self, flat_home):
        from hermes_cli.model_runtime_config import persist_model_runtime

        (flat_home / "config.yaml").write_text(
            "model:\n  provider: custom\n  api_key: old\n  api_mode: old\n",
            encoding="utf-8",
        )
        persist_model_runtime("openrouter", default_model="m", extra_model_fields=None)
        cfg = yaml.safe_load((flat_home / "config.yaml").read_text(encoding="utf-8"))
        assert "api_key" not in cfg["model"]
        assert "api_mode" not in cfg["model"]

    def test_extra_model_fields_empty_dict_does_not_strip(self, flat_home):
        """``{}`` is not None — must not trigger builtin secret stripping."""
        from hermes_cli.model_runtime_config import persist_model_runtime

        (flat_home / "config.yaml").write_text(
            "model:\n  provider: custom\n  api_key: keep\n",
            encoding="utf-8",
        )
        persist_model_runtime("custom", default_model="m", extra_model_fields={})
        cfg = yaml.safe_load((flat_home / "config.yaml").read_text(encoding="utf-8"))
        assert cfg["model"]["api_key"] == "keep"

    def test_extra_model_fields_null_removes_key(self, flat_home):
        from hermes_cli.model_runtime_config import persist_model_runtime

        (flat_home / "config.yaml").write_text(
            "model:\n  provider: custom\n  api_mode: stale\n",
            encoding="utf-8",
        )
        persist_model_runtime(
            "custom",
            default_model="m",
            extra_model_fields={"api_mode": None, "api_key": "sk-x"},
        )
        cfg = yaml.safe_load((flat_home / "config.yaml").read_text(encoding="utf-8"))
        assert "api_mode" not in cfg["model"]
        assert cfg["model"]["api_key"] == "sk-x"

    def test_string_model_format_upgraded_on_persist(self, flat_home):
        from hermes_cli.model_runtime_config import persist_model_runtime

        persist_model_runtime("nous", default_model="new-default")
        cfg = yaml.safe_load((flat_home / "config.yaml").read_text(encoding="utf-8"))
        assert isinstance(cfg["model"], dict)
        assert cfg["model"]["default"] == "new-default"


class TestPersistModelRuntimeNegative:
    def test_raises_on_empty_provider_id(self, flat_home):
        from hermes_cli.model_runtime_config import persist_model_runtime

        with pytest.raises(ValueError, match="provider_id is required"):
            persist_model_runtime("")
        with pytest.raises(ValueError, match="provider_id is required"):
            persist_model_runtime("   ")

    def test_auth_sync_failure_raises_after_config_write(self, flat_home, monkeypatch):
        from hermes_cli.model_runtime_config import persist_model_runtime

        original = (flat_home / "config.yaml").read_text(encoding="utf-8")

        def _fail_save(_store):
            raise OSError("disk full")

        monkeypatch.setattr(
            "hermes_cli.auth._save_auth_store",
            _fail_save,
        )
        with pytest.raises(OSError, match="disk full"):
            persist_model_runtime("nous", default_model="m", sync_auth=True)

        # Config may have been written before auth failed — document current behavior.
        after = (flat_home / "config.yaml").read_text(encoding="utf-8")
        assert after != original or "nous" in after

    def test_atomic_write_failure_propagates(self, flat_home, monkeypatch):
        from hermes_cli.model_runtime_config import persist_model_runtime

        original = (flat_home / "config.yaml").read_text(encoding="utf-8")

        def _boom(_path, _data, **kwargs):
            raise OSError("simulated atomic write failure")

        monkeypatch.setattr("utils.atomic_yaml_write", _boom)
        with pytest.raises(OSError, match="simulated atomic write failure"):
            persist_model_runtime("nous", default_model="m")

        assert (flat_home / "config.yaml").read_text(encoding="utf-8") == original

    def test_bust_caches_called_after_success(self, flat_home, monkeypatch):
        from hermes_cli.model_runtime_config import persist_model_runtime

        calls: list[Path] = []

        def _track_bust(*paths):
            calls.extend(paths)

        monkeypatch.setattr(
            "hermes_cli.profile_model_inheritance.bust_config_caches",
            _track_bust,
        )
        persist_model_runtime("nous", default_model="m")
        assert len(calls) == 1
        assert calls[0] == flat_home / "config.yaml"


# ---------------------------------------------------------------------------
# detect_model_provider_incoherence
# ---------------------------------------------------------------------------


class TestDetectModelProviderIncoherence:
    def test_split_brain_error(self, hermes_tree):
        from hermes_cli.config import load_config
        from hermes_cli.model_runtime_config import detect_model_provider_incoherence

        issues = detect_model_provider_incoherence(load_config())
        codes = {i.code for i in issues}
        assert "auth_config_provider_mismatch" in codes
        mismatch = next(i for i in issues if i.code == "auth_config_provider_mismatch")
        assert mismatch.severity == "error"

    def test_vendor_slug_warn_for_gemini(self):
        from hermes_cli.model_runtime_config import detect_model_provider_incoherence

        cfg = {
            "model": {
                "provider": "gemini",
                "default": "deepseek/deepseek-v4-flash:free",
            }
        }
        auth = {"active_provider": "gemini"}
        codes = {i.code for i in detect_model_provider_incoherence(cfg, auth)}
        assert "vendor_slug_wrong_provider" in codes

    def test_no_vendor_slug_warn_for_nous(self):
        from hermes_cli.model_runtime_config import detect_model_provider_incoherence

        cfg = {
            "model": {
                "provider": "nous",
                "default": "deepseek/deepseek-v4-flash:free",
            }
        }
        issues = detect_model_provider_incoherence(cfg, {"active_provider": "nous"})
        assert not any(i.code == "vendor_slug_wrong_provider" for i in issues)

    def test_base_url_host_mismatch(self):
        from hermes_cli.model_runtime_config import detect_model_provider_incoherence

        cfg = {
            "model": {
                "provider": "nous",
                "default": "m",
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
            }
        }
        with patch(
            "utils.base_url_hostname",
            return_value="generativelanguage.googleapis.com",
        ):
            issues = detect_model_provider_incoherence(cfg, {"active_provider": "nous"})
        assert any(i.code == "base_url_provider_mismatch" for i in issues)

    def test_coherent_config_returns_empty(self):
        from hermes_cli.model_runtime_config import detect_model_provider_incoherence

        cfg = {
            "model": {
                "provider": "nous",
                "default": "deepseek/x",
                "base_url": "https://inference-api.nousresearch.com/v1",
            }
        }
        with patch(
            "utils.base_url_hostname",
            return_value="inference-api.nousresearch.com",
        ):
            assert detect_model_provider_incoherence(cfg, {"active_provider": "nous"}) == []

    def test_missing_auth_or_config_provider_skips_mismatch(self):
        from hermes_cli.model_runtime_config import detect_model_provider_incoherence

        assert not detect_model_provider_incoherence(
            {"model": {"provider": "gemini"}},
            {},
        )
        assert not detect_model_provider_incoherence(
            {"model": {"default": "x"}},
            {"active_provider": "nous"},
        )

    def test_string_model_format_detected(self):
        from hermes_cli.model_runtime_config import detect_model_provider_incoherence

        cfg = {"model": "openai/gpt-4", "model_meta": {"provider": "gemini"}}
        # provider must be in dict branch — string-only has no provider
        issues = detect_model_provider_incoherence(
            {"model": "vendor/slug-only"},
            {"active_provider": "nous"},
        )
        assert not any(i.code == "auth_config_provider_mismatch" for i in issues)

    def test_load_config_failure_returns_empty_issues(self, monkeypatch):
        from hermes_cli.model_runtime_config import detect_model_provider_incoherence

        def _boom():
            raise RuntimeError("no config")

        monkeypatch.setattr(
            "hermes_cli.config.load_config",
            _boom,
        )
        monkeypatch.setattr(
            "hermes_cli.auth._load_auth_store",
            lambda: {"active_provider": "nous"},
        )
        # config load fails → {}; no provider in config → no mismatch error
        assert detect_model_provider_incoherence() == []

    def test_load_auth_failure_still_checks_config(self, monkeypatch):
        from hermes_cli.model_runtime_config import detect_model_provider_incoherence

        monkeypatch.setattr(
            "hermes_cli.auth._load_auth_store",
            MagicMock(side_effect=OSError("auth missing")),
        )
        cfg = {
            "model": {
                "provider": "gemini",
                "default": "deepseek/x",
            }
        }
        issues = detect_model_provider_incoherence(cfg)
        assert any(i.code == "vendor_slug_wrong_provider" for i in issues)

    def test_unknown_host_skips_base_url_check(self):
        from hermes_cli.model_runtime_config import detect_model_provider_incoherence

        cfg = {
            "model": {
                "provider": "custom",
                "default": "m",
                "base_url": "https://unknown.example/v1",
            }
        }
        with patch("utils.base_url_hostname", return_value="unknown.example"):
            issues = detect_model_provider_incoherence(cfg, {"active_provider": "custom"})
        assert not any(i.code == "base_url_provider_mismatch" for i in issues)


# ---------------------------------------------------------------------------
# repair_model_provider_coherence
# ---------------------------------------------------------------------------


class TestRepairModelProviderCoherence:
    def test_repair_aligns_config_to_auth(self, hermes_tree):
        from hermes_cli.config import load_config
        from hermes_cli.model_runtime_config import (
            detect_model_provider_incoherence,
            repair_model_provider_coherence,
        )

        actions = repair_model_provider_coherence()
        assert actions
        assert "nous" in actions[0]

        cfg = load_config()
        assert cfg["model"]["provider"] == "nous"
        assert not detect_model_provider_incoherence(cfg)

    def test_no_issues_returns_empty_actions(self, flat_home):
        from hermes_cli.model_runtime_config import repair_model_provider_coherence

        (flat_home / "config.yaml").write_text(
            "model:\n  provider: openrouter\n  default: x\n",
            encoding="utf-8",
        )
        (flat_home / "auth.json").write_text(
            json.dumps({"version": 1, "active_provider": "openrouter", "providers": {}}),
            encoding="utf-8",
        )
        assert repair_model_provider_coherence() == []

    def test_invalid_prefer_falls_back_to_config_from_auth(self, hermes_tree, monkeypatch):
        from hermes_cli.model_runtime_config import repair_model_provider_coherence

        captured: dict = {}

        def _fake_persist(provider_id, **kwargs):
            captured["provider"] = provider_id

        monkeypatch.setattr(
            "hermes_cli.model_runtime_config.persist_model_runtime",
            _fake_persist,
        )
        repair_model_provider_coherence(prefer="invalid-mode")  # type: ignore[arg-type]
        assert captured["provider"] == "nous"

    def test_auth_from_config_prefers_config_provider(self, hermes_tree, monkeypatch):
        from hermes_cli.model_runtime_config import repair_model_provider_coherence

        captured: dict = {}

        def _fake_persist(provider_id, **kwargs):
            captured["provider"] = provider_id

        monkeypatch.setattr(
            "hermes_cli.model_runtime_config.persist_model_runtime",
            _fake_persist,
        )
        repair_model_provider_coherence(prefer="auth_from_config")
        assert captured["provider"] == "gemini"

    def test_passed_issues_avoids_reload_detect(self, monkeypatch):
        from hermes_cli.model_runtime_config import (
            CoherenceIssue,
            repair_model_provider_coherence,
        )

        load_config = MagicMock(side_effect=AssertionError("should not load for detect"))
        monkeypatch.setattr("hermes_cli.config.load_config", load_config)

        issues = [
            CoherenceIssue(
                code="auth_config_provider_mismatch",
                message="x",
                severity="error",
            )
        ]
        monkeypatch.setattr(
            "hermes_cli.model_runtime_config.persist_model_runtime",
            lambda *a, **k: None,
        )
        monkeypatch.setattr(
            "hermes_cli.auth._load_auth_store",
            lambda: {"active_provider": "nous"},
        )
        # First load_config for effective_cfg still runs
        load_config.side_effect = [
            {"model": {"provider": "gemini", "default": "m"}},
        ]
        actions = repair_model_provider_coherence(issues=issues)
        assert actions

    def test_no_target_provider_returns_empty(self, monkeypatch):
        from hermes_cli.model_runtime_config import (
            CoherenceIssue,
            repair_model_provider_coherence,
        )

        issues = [
            CoherenceIssue(code="vendor_slug_wrong_provider", message="w", severity="warn")
        ]
        monkeypatch.setattr(
            "hermes_cli.config.load_config",
            lambda: {"model": {}},
        )
        monkeypatch.setattr(
            "hermes_cli.auth._load_auth_store",
            lambda: {},
        )
        assert repair_model_provider_coherence(issues=issues) == []

    def test_nous_uses_resolve_credentials_base_url(self, hermes_tree, monkeypatch):
        from hermes_cli.model_runtime_config import repair_model_provider_coherence

        captured: dict = {}

        def _fake_persist(provider_id, **kwargs):
            captured.update(kwargs)
            captured["provider"] = provider_id

        monkeypatch.setattr(
            "hermes_cli.model_runtime_config.persist_model_runtime",
            _fake_persist,
        )
        monkeypatch.setattr(
            "hermes_cli.auth.resolve_nous_runtime_credentials",
            lambda **kw: {"base_url": "https://inference-api.nousresearch.com/v1"},
        )
        repair_model_provider_coherence()
        assert captured["provider"] == "nous"
        assert captured["inference_base_url"] == "https://inference-api.nousresearch.com/v1"

    def test_nous_resolve_failure_uses_registry_url(self, hermes_tree, monkeypatch):
        from hermes_cli.auth import PROVIDER_REGISTRY
        from hermes_cli.model_runtime_config import repair_model_provider_coherence

        captured: dict = {}

        def _fake_persist(provider_id, **kwargs):
            captured.update(kwargs)

        monkeypatch.setattr(
            "hermes_cli.model_runtime_config.persist_model_runtime",
            _fake_persist,
        )
        monkeypatch.setattr(
            "hermes_cli.auth.resolve_nous_runtime_credentials",
            MagicMock(side_effect=RuntimeError("no portal")),
        )
        registry_url = PROVIDER_REGISTRY["nous"].inference_base_url
        repair_model_provider_coherence()
        assert captured["inference_base_url"] == registry_url

    def test_auth_status_note_when_not_logged_in(self, hermes_tree, monkeypatch):
        from hermes_cli.model_runtime_config import repair_model_provider_coherence

        monkeypatch.setattr(
            "hermes_cli.model_runtime_config.persist_model_runtime",
            lambda *a, **k: None,
        )
        monkeypatch.setattr(
            "hermes_cli.auth.get_auth_status",
            lambda _p: {"logged_in": False},
        )
        # auth_from_config keeps config provider; note when auth not logged in for it.
        actions = repair_model_provider_coherence(prefer="auth_from_config")
        assert any("Note:" in a for a in actions)


class TestBustAllRuntimeConfigCaches:
    def test_delegates_to_profile_bust(self, flat_home, monkeypatch):
        from hermes_cli.model_runtime_config import bust_all_runtime_config_caches

        seen: list[Path] = []

        def _bust(*paths):
            seen.extend(paths)

        monkeypatch.setattr(
            "hermes_cli.profile_model_inheritance.bust_config_caches",
            _bust,
        )
        bust_all_runtime_config_caches()
        assert seen == [flat_home / "config.yaml"]
