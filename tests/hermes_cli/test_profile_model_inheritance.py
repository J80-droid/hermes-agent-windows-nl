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
