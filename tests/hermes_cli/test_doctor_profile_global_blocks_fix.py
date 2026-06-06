"""Doctor --fix strips auxiliary/providers from domain profile configs."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_repo = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_repo))


@pytest.fixture
def profile_with_global_blocks(tmp_path, monkeypatch):
    root = tmp_path / "hermes"
    prof = root / "profiles" / "core"
    prof.mkdir(parents=True)
    (root / "config.yaml").write_text(
        "model:\n  provider: openrouter\n  default: x\n",
        encoding="utf-8",
    )
    (prof / "config.yaml").write_text(
        "agent:\n  max_turns: 30\n"
        "auxiliary:\n"
        "  profile_describer:\n"
        "    provider: auto\n"
        "providers:\n"
        "  venice:\n"
        "    api_key_env: VENICE_API_KEY\n",
        encoding="utf-8",
    )
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


def test_strip_all_profile_global_blocks_removes_auxiliary(profile_with_global_blocks):
    root, prof = profile_with_global_blocks
    from hermes_cli.profile_model_inheritance import strip_all_profile_global_blocks

    stripped = strip_all_profile_global_blocks()
    assert "core" in stripped
    text = (prof / "config.yaml").read_text(encoding="utf-8")
    assert not re.search(r"(?m)^auxiliary:\s*", text)
    assert not re.search(r"(?m)^providers:\s*", text)
    assert "agent:" in text


def test_comment_only_providers_not_detected_as_global_block(tmp_path, monkeypatch):
    """Comments mentioning providers: must not trigger false-positive detection."""
    root = tmp_path / "hermes"
    prof = root / "profiles" / "legal"
    prof.mkdir(parents=True)
    (root / "config.yaml").write_text("model:\n  provider: nous\n", encoding="utf-8")
    (prof / "config.yaml").write_text(
        "# providers/custom_providers: inherited from root config.\n"
        "agent:\n  max_turns: 30\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(prof))
    monkeypatch.setenv("HERMES_WIN_PREFER_LOCALAPPDATA", "0")
    monkeypatch.setattr(
        "hermes_constants.get_default_hermes_root",
        lambda: root,
    )
    from hermes_cli.profile_model_inheritance import (
        list_profiles_with_global_config_blocks,
        profile_has_global_config_blocks,
    )

    assert not profile_has_global_config_blocks(prof)
    assert list_profiles_with_global_config_blocks() == []


def test_doctor_fix_strips_global_blocks_via_inheritance(profile_with_global_blocks):
    from hermes_cli.profile_model_inheritance import strip_all_profile_global_blocks

    _, prof = profile_with_global_blocks
    before = (prof / "config.yaml").read_text(encoding="utf-8")
    assert re.search(r"(?m)^auxiliary:\s*", before)
    stripped = strip_all_profile_global_blocks()
    assert stripped == ["core"]


def test_doctor_fix_strips_global_blocks_via_doctor_command(profile_with_global_blocks):
    from argparse import Namespace

    from overlay.bootstrap import install
    from overlay.hermes_cli.doctor_fork_patch import _run_fork_doctor_checks

    install()

    _, prof = profile_with_global_blocks
    before = (prof / "config.yaml").read_text(encoding="utf-8")
    assert re.search(r"(?m)^auxiliary:\s*", before)

    _run_fork_doctor_checks(Namespace(fix=True))

    after = (prof / "config.yaml").read_text(encoding="utf-8")
    assert not re.search(r"(?m)^auxiliary:\s*", after)
    assert not re.search(r"(?m)^providers:\s*", after)
    assert "agent:" in after
