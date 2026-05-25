"""Pytest wiring for upstream merge integration E2E (profile create + s6 hooks)."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def profile_env(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    default_home = tmp_path / ".hermes"
    default_home.mkdir(exist_ok=True)
    monkeypatch.setenv("HERMES_HOME", str(default_home))
    return default_home


def test_create_profile_strips_cloned_model_block(profile_env):
    """Na upstream-merge: clone_config + strip verwijdert model uit profiel-config."""
    from hermes_cli.profiles import create_profile

    (profile_env / "config.yaml").write_text(
        "model:\n  default: openrouter/test-model\nagent: {}\n",
        encoding="utf-8",
    )
    prof = create_profile("upstream_merge_strip", clone_config=True, no_alias=True)
    raw = (prof / "config.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    assert not (isinstance(data, dict) and "model" in data)
    assert "inherited from root" in raw


def test_profiles_create_calls_register_after_strip():
    """create_profile bevat strip vóór s6-register (regressie upstream merge)."""
    from pathlib import Path

    text = (Path(__file__).resolve().parents[2] / "hermes_cli" / "profiles.py").read_text(
        encoding="utf-8"
    )
    strip_idx = text.find("strip_model_block_from_profile_config(profile_dir)")
    reg_idx = text.find("_maybe_register_gateway_service(canon)")
    assert strip_idx >= 0 and reg_idx >= 0
    assert strip_idx < reg_idx
