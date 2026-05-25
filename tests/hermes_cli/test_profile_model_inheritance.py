"""Profiel-model overerven van root config."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_repo = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_repo))


@pytest.fixture
def hermes_tree(tmp_path, monkeypatch):
    root = tmp_path / ".hermes"
    prof = root / "profiles" / "legal_test"
    prof.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(prof))
    monkeypatch.setattr(
        "hermes_constants.get_default_hermes_root",
        lambda: root,
    )
    return root, prof


def test_resolve_ignores_profile_model_block(hermes_tree):
    root, prof = hermes_tree
    (root / "config.yaml").write_text(
        "model:\n  provider: gemini\n  default: gemini-root\n",
        encoding="utf-8",
    )
    (prof / "config.yaml").write_text(
        "model:\n  provider: openrouter\n  default: openrouter/old\n",
        encoding="utf-8",
    )

    from hermes_cli.profile_model_inheritance import resolve_model_section
    import yaml

    profile_user = yaml.safe_load((prof / "config.yaml").read_text(encoding="utf-8"))
    model = resolve_model_section(profile_user)
    assert model["provider"] == "gemini"
    assert model["default"] == "gemini-root"


def test_load_config_applies_inheritance(hermes_tree, monkeypatch):
    root, prof = hermes_tree
    (root / "config.yaml").write_text(
        "model:\n  provider: gemini\n  default: from-root\n",
        encoding="utf-8",
    )
    (prof / "config.yaml").write_text(
        "model:\n  provider: openrouter\n  default: stale\n"
        "agent:\n  max_turns: 7\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("hermes_cli.config.get_config_path", lambda: prof / "config.yaml")
    monkeypatch.setattr("hermes_cli.config.ensure_hermes_home", lambda: None)

    from hermes_cli.config import load_config

    cfg = load_config()
    assert cfg["model"]["provider"] == "gemini"
    assert cfg["model"]["default"] == "from-root"
    assert cfg["agent"]["max_turns"] == 7


def test_inherit_false_allows_override(hermes_tree):
    root, prof = hermes_tree
    (root / "config.yaml").write_text(
        "model:\n  provider: gemini\n  default: gemini-root\n",
        encoding="utf-8",
    )
    (prof / "config.yaml").write_text(
        "model:\n  inherit: false\n  provider: openrouter\n  default: custom-only\n",
        encoding="utf-8",
    )

    from hermes_cli.profile_model_inheritance import resolve_model_section
    import yaml

    profile_user = yaml.safe_load((prof / "config.yaml").read_text(encoding="utf-8"))
    model = resolve_model_section(profile_user)
    assert model["provider"] == "openrouter"
    assert model["default"] == "custom-only"


def test_config_path_for_model_key_redirects_to_root(hermes_tree):
    _, prof = hermes_tree
    from hermes_cli.profile_model_inheritance import config_path_for_user_key

    assert config_path_for_user_key("model.default", home=prof).name == "config.yaml"
    assert config_path_for_user_key("model.default", home=prof).parent == hermes_tree[0]
    assert config_path_for_user_key("terminal.backend", home=prof) == prof / "config.yaml"


def test_load_config_inherits_without_profile_yaml(hermes_tree, monkeypatch):
    root, prof = hermes_tree
    (root / "config.yaml").write_text(
        "model:\n  provider: gemini\n  default: root-only\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("hermes_cli.config.get_config_path", lambda: prof / "config.yaml")
    monkeypatch.setattr("hermes_cli.config.ensure_hermes_home", lambda: None)

    from hermes_cli.config import load_config

    cfg = load_config()
    assert cfg["model"]["default"] == "root-only"


def test_strip_model_block(hermes_tree):
    _, prof = hermes_tree
    (prof / "config.yaml").write_text(
        "model:\n  provider: gemini\n  default: x\nagent:\n  max_turns: 1\n",
        encoding="utf-8",
    )

    from hermes_cli.profile_model_inheritance import strip_model_block_from_profile_config

    assert strip_model_block_from_profile_config(prof) is True
    text = (prof / "config.yaml").read_text(encoding="utf-8")
    assert "inherited from root" in text
    assert "model:" not in text.split("agent:")[0]


def test_resolve_ignores_profile_auxiliary_block(hermes_tree):
    root, prof = hermes_tree
    (root / "config.yaml").write_text(
        "auxiliary:\n  compression:\n    provider: custom\n    model: qwen-local\n",
        encoding="utf-8",
    )
    (prof / "config.yaml").write_text(
        "auxiliary:\n  compression:\n    provider: gemini\n    model: gemini-2.5-flash\n",
        encoding="utf-8",
    )

    from hermes_cli.profile_model_inheritance import resolve_auxiliary_section
    import yaml

    profile_user = yaml.safe_load((prof / "config.yaml").read_text(encoding="utf-8"))
    aux = resolve_auxiliary_section(profile_user)
    assert aux["compression"]["provider"] == "custom"
    assert aux["compression"]["model"] == "qwen-local"


def test_load_config_inherits_auxiliary_from_root(hermes_tree, monkeypatch):
    root, prof = hermes_tree
    (root / "config.yaml").write_text(
        "auxiliary:\n  compression:\n    provider: custom\n    model: qwen-local\n",
        encoding="utf-8",
    )
    (prof / "config.yaml").write_text(
        "auxiliary:\n  compression:\n    provider: gemini\n    model: gemini-2.5-flash\n"
        "agent:\n  max_turns: 7\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("hermes_cli.config.get_config_path", lambda: prof / "config.yaml")
    monkeypatch.setattr("hermes_cli.config.ensure_hermes_home", lambda: None)

    from hermes_cli.config import load_config

    cfg = load_config()
    assert cfg["auxiliary"]["compression"]["provider"] == "custom"
    assert cfg["agent"]["max_turns"] == 7


def test_resolve_providers_from_root(hermes_tree):
    root, prof = hermes_tree
    (root / "config.yaml").write_text(
        "providers:\n  venice:\n    base_url: https://api.venice.ai/api/v1\n",
        encoding="utf-8",
    )
    (prof / "config.yaml").write_text("providers: {}\n", encoding="utf-8")

    from hermes_cli.profile_model_inheritance import resolve_providers_sections
    import yaml

    profile_user = yaml.safe_load((prof / "config.yaml").read_text(encoding="utf-8"))
    providers, _custom = resolve_providers_sections(profile_user)
    assert "venice" in providers


def test_config_path_auxiliary_redirects_to_root(hermes_tree):
    _, prof = hermes_tree
    from hermes_cli.profile_model_inheritance import config_path_for_user_key

    assert config_path_for_user_key("auxiliary.compression.provider", home=prof).parent == hermes_tree[0]


def test_strip_global_blocks(hermes_tree):
    _, prof = hermes_tree
    (prof / "config.yaml").write_text(
        "auxiliary:\n  vision:\n    provider: gemini\n"
        "providers:\n  venice:\n    base_url: x\n"
        "agent:\n  max_turns: 1\n",
        encoding="utf-8",
    )
    from hermes_cli.profile_model_inheritance import strip_global_blocks_from_profile_config

    assert strip_global_blocks_from_profile_config(prof) is True
    text = (prof / "config.yaml").read_text(encoding="utf-8")
    assert not any(line.strip().startswith("auxiliary:") for line in text.splitlines())
    assert not any(line.strip().startswith("providers:") for line in text.splitlines())
    assert "agent:" in text


@pytest.fixture
def profiles_root_tree(tmp_path, monkeypatch):
    """Runtime root with multiple profiles for global-block list/strip tests."""
    root = tmp_path / "hermes"
    profiles = root / "profiles"
    profiles.mkdir(parents=True)
    (root / "config.yaml").write_text(
        "model:\n  provider: nous\n  default: x\n", encoding="utf-8"
    )
    monkeypatch.setenv("HERMES_HOME", str(root))
    monkeypatch.setenv("HERMES_WIN_PREFER_LOCALAPPDATA", "0")
    monkeypatch.setattr(
        "hermes_constants.get_default_hermes_root",
        lambda: root,
    )
    return root, profiles


class TestProfileGlobalConfigBlocks:
    """profile_has_global_config_blocks / list / strip_all (YAML keys, not comments)."""

    def test_profile_has_blocks_happy_path_auxiliary(self, profiles_root_tree):
        _, profiles = profiles_root_tree
        prof = profiles / "alpha"
        prof.mkdir()
        (prof / "config.yaml").write_text(
            "auxiliary:\n  vision:\n    provider: gemini\n", encoding="utf-8"
        )
        from hermes_cli.profile_model_inheritance import profile_has_global_config_blocks

        assert profile_has_global_config_blocks(prof) is True

    def test_profile_has_blocks_custom_providers_only(self, profiles_root_tree):
        _, profiles = profiles_root_tree
        prof = profiles / "beta"
        prof.mkdir()
        (prof / "config.yaml").write_text(
            "custom_providers:\n  myep:\n    base_url: https://x\n", encoding="utf-8"
        )
        from hermes_cli.profile_model_inheritance import profile_has_global_config_blocks

        assert profile_has_global_config_blocks(prof) is True

    def test_profile_has_blocks_false_when_clean(self, profiles_root_tree):
        _, profiles = profiles_root_tree
        prof = profiles / "gamma"
        prof.mkdir()
        (prof / "config.yaml").write_text("agent:\n  max_turns: 1\n", encoding="utf-8")
        from hermes_cli.profile_model_inheritance import profile_has_global_config_blocks

        assert profile_has_global_config_blocks(prof) is False

    def test_profile_has_blocks_false_comment_only(self, profiles_root_tree):
        _, profiles = profiles_root_tree
        prof = profiles / "legal"
        prof.mkdir()
        (prof / "config.yaml").write_text(
            "# auxiliary: should not match\n"
            "# providers: inherited\n"
            "agent:\n  max_turns: 2\n",
            encoding="utf-8",
        )
        from hermes_cli.profile_model_inheritance import profile_has_global_config_blocks

        assert profile_has_global_config_blocks(prof) is False

    def test_profile_has_blocks_false_nested_auxiliary_under_agent(self, profiles_root_tree):
        """Nested keys must not count — only top-level YAML blocks."""
        _, profiles = profiles_root_tree
        prof = profiles / "nested"
        prof.mkdir()
        (prof / "config.yaml").write_text(
            "agent:\n  max_turns: 1\n  auxiliary:\n    vision:\n      provider: gemini\n",
            encoding="utf-8",
        )
        from hermes_cli.profile_model_inheritance import profile_has_global_config_blocks

        assert profile_has_global_config_blocks(prof) is False

    def test_profile_has_blocks_false_missing_config_yaml(self, profiles_root_tree):
        _, profiles = profiles_root_tree
        prof = profiles / "empty_cfg"
        prof.mkdir()
        from hermes_cli.profile_model_inheritance import profile_has_global_config_blocks

        assert profile_has_global_config_blocks(prof) is False

    def test_profile_has_blocks_false_invalid_yaml(self, profiles_root_tree):
        _, profiles = profiles_root_tree
        prof = profiles / "broken"
        prof.mkdir()
        (prof / "config.yaml").write_text("model: [\n", encoding="utf-8")
        from hermes_cli.profile_model_inheritance import profile_has_global_config_blocks

        assert profile_has_global_config_blocks(prof) is False

    def test_list_profiles_sorted_and_skips_files(self, profiles_root_tree):
        _, profiles = profiles_root_tree
        for name, body in (
            ("zebra", "providers:\n  x: {}\n"),
            ("alpha", "agent:\n  max_turns: 1\n"),
            ("mango", "auxiliary:\n  a: {}\n"),
        ):
            d = profiles / name
            d.mkdir()
            (d / "config.yaml").write_text(body, encoding="utf-8")
        (profiles / "README.txt").write_text("not a profile dir", encoding="utf-8")

        from hermes_cli.profile_model_inheritance import (
            list_profiles_with_global_config_blocks,
        )

        assert list_profiles_with_global_config_blocks() == ["mango", "zebra"]

    def test_list_profiles_empty_when_profiles_root_missing(self, tmp_path, monkeypatch):
        root = tmp_path / "no_profiles"
        root.mkdir()
        monkeypatch.setattr(
            "hermes_constants.get_default_hermes_root",
            lambda: root,
        )
        from hermes_cli.profile_model_inheritance import (
            list_profiles_with_global_config_blocks,
        )

        assert list_profiles_with_global_config_blocks() == []

    def test_strip_all_returns_sorted_stripped_names(self, profiles_root_tree):
        _, profiles = profiles_root_tree
        for name in ("b_prof", "a_prof"):
            d = profiles / name
            d.mkdir()
            (d / "config.yaml").write_text(
                "providers:\n  venice:\n    api_key_env: V\n", encoding="utf-8"
            )

        from hermes_cli.profile_model_inheritance import strip_all_profile_global_blocks

        stripped = strip_all_profile_global_blocks()
        assert stripped == ["a_prof", "b_prof"]

    def test_strip_all_idempotent_second_call_empty(self, profiles_root_tree):
        _, profiles = profiles_root_tree
        prof = profiles / "once"
        prof.mkdir()
        (prof / "config.yaml").write_text("auxiliary:\n  x: {}\n", encoding="utf-8")

        from hermes_cli.profile_model_inheritance import strip_all_profile_global_blocks

        assert strip_all_profile_global_blocks() == ["once"]
        assert strip_all_profile_global_blocks() == []

    def test_strip_all_skips_clean_profiles(self, profiles_root_tree):
        _, profiles = profiles_root_tree
        clean = profiles / "clean"
        dirty = profiles / "dirty"
        clean.mkdir()
        dirty.mkdir()
        (clean / "config.yaml").write_text("agent:\n  max_turns: 1\n", encoding="utf-8")
        (dirty / "config.yaml").write_text("providers:\n  p: {}\n", encoding="utf-8")

        from hermes_cli.profile_model_inheritance import (
            list_profiles_with_global_config_blocks,
            strip_all_profile_global_blocks,
        )

        assert list_profiles_with_global_config_blocks() == ["dirty"]
        assert strip_all_profile_global_blocks() == ["dirty"]
        assert list_profiles_with_global_config_blocks() == []

    def test_strip_preserves_agent_block(self, profiles_root_tree):
        _, profiles = profiles_root_tree
        prof = profiles / "core"
        prof.mkdir()
        (prof / "config.yaml").write_text(
            "auxiliary:\n  t:\n    provider: auto\n"
            "agent:\n  max_turns: 42\n",
            encoding="utf-8",
        )
        import yaml

        from hermes_cli.profile_model_inheritance import strip_all_profile_global_blocks

        strip_all_profile_global_blocks()
        cfg = yaml.safe_load((prof / "config.yaml").read_text(encoding="utf-8"))
        assert "auxiliary" not in cfg
        assert cfg["agent"]["max_turns"] == 42
