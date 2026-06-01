"""Sync script must not overwrite platform_toolsets.cli after hermes tools save."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import yaml

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO / "windows" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from sync_profile_toolsets_from_manifest import (  # noqa: E402
    _load_manifest,
    _sync_profile,
)


def test_sync_profile_skips_when_cli_user_customized(tmp_path):
    hermes = tmp_path / "hermes"
    profile_dir = hermes / "profiles" / "legal"
    profile_dir.mkdir(parents=True)
    cfg = {
        "platform_toolsets": {
            "_user_customized": {"cli": True},
            "cli": ["web", "terminal", "mcp"],
        }
    }
    (profile_dir / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    manifest = _load_manifest(_REPO)
    spec = manifest["profiles"]["legal"]
    ok = _sync_profile(hermes, "legal", spec, dry_run=False, check=False, force_manifest=False)
    assert ok
    saved = yaml.safe_load((profile_dir / "config.yaml").read_text(encoding="utf-8"))
    assert saved["platform_toolsets"]["cli"] == ["web", "terminal", "mcp"]


def test_sync_profile_force_manifest_overwrites_user_customized(tmp_path):
    hermes = tmp_path / "hermes"
    profile_dir = hermes / "profiles" / "legal"
    profile_dir.mkdir(parents=True)
    cfg = {
        "platform_toolsets": {
            "_user_customized": {"cli": True},
            "cli": ["web", "terminal"],
        }
    }
    (profile_dir / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    manifest = _load_manifest(_REPO)
    spec = manifest["profiles"]["legal"]
    with patch("sync_profile_toolsets_from_manifest._write_yaml") as write_yaml:
        ok = _sync_profile(
            hermes,
            "legal",
            spec,
            dry_run=False,
            check=False,
            force_manifest=True,
        )
    assert ok
    assert write_yaml.called
