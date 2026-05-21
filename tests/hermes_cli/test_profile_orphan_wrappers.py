"""Orphan profile wrapper detection and removal."""

from pathlib import Path

from hermes_cli.profiles import (
    iter_orphan_profile_wrappers,
    remove_orphan_profile_wrappers,
)


def test_orphan_wrapper_detected_and_removed(tmp_path: Path, monkeypatch):
    profiles_root = tmp_path / "profiles"
    profiles_root.mkdir()
    (profiles_root / "legal").mkdir()

    wrapper_dir = tmp_path / "bin"
    wrapper_dir.mkdir()
    orphan = wrapper_dir / "analyst"
    orphan.write_text('#!/bin/sh\nexec hermes -p analyst "$@"\n', encoding="utf-8")

    monkeypatch.setattr(
        "hermes_cli.profiles._get_profiles_root",
        lambda: profiles_root,
    )
    monkeypatch.setattr(
        "hermes_cli.profiles._get_default_hermes_home",
        lambda: tmp_path / "hermes",
    )
    monkeypatch.setattr(
        "hermes_cli.profiles._get_wrapper_dir",
        lambda: wrapper_dir,
    )

    found = iter_orphan_profile_wrappers(wrapper_dir)
    assert len(found) == 1
    assert found[0] == ("analyst", "analyst")

    removed = remove_orphan_profile_wrappers(wrapper_dir)
    assert removed == ["analyst"]
    assert not orphan.exists()
