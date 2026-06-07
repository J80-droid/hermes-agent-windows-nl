"""Doctor coherence detection and --fix for model/provider split-brain."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_repo = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_repo))


@pytest.fixture
def split_brain_home(tmp_path, monkeypatch):
    home = tmp_path / "hermes"
    home.mkdir()
    (home / "config.yaml").write_text(
        "model:\n"
        "  provider: gemini\n"
        "  default: deepseek/deepseek-v4-flash:free\n"
        "  base_url: https://generativelanguage.googleapis.com/v1beta\n",
        encoding="utf-8",
    )
    (home / "auth.json").write_text(
        json.dumps({"version": 1, "active_provider": "nous", "providers": {}}),
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


def test_doctor_fix_repairs_split_brain(split_brain_home, monkeypatch):
    monkeypatch.setattr(
        "hermes_cli.doctor.PROJECT_ROOT",
        _repo,
    )
    monkeypatch.setattr(
        "hermes_cli.doctor.HERMES_HOME",
        split_brain_home,
    )

    from hermes_cli.model_runtime_config import detect_model_provider_incoherence
    from hermes_cli.config import load_config

    assert detect_model_provider_incoherence(load_config())

    from hermes_cli.model_runtime_config import repair_model_provider_coherence

    actions = repair_model_provider_coherence()
    assert actions, "repair should apply fixes for split-brain fixture"
    import yaml

    cfg_disk = yaml.safe_load((split_brain_home / "config.yaml").read_text(encoding="utf-8"))
    assert cfg_disk["model"]["provider"] == "nous"
    cfg = load_config()
    assert cfg["model"]["provider"] == "nous"
    assert not detect_model_provider_incoherence(cfg)
