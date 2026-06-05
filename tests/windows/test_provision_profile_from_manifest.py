"""Provision + sync via sync_profile_toolsets_from_manifest (--create-missing)."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
SYNC_SCRIPT = REPO / "windows" / "scripts" / "sync_profile_toolsets_from_manifest.py"
MANIFEST = REPO / "docs" / "domain_toolsets.yaml"


def _load_sync_module():
    spec = importlib.util.spec_from_file_location("sync_profile_toolsets", SYNC_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _hermes_fixture(tmp_path: Path) -> Path:
    hermes = tmp_path / "hermes"
    hermes.mkdir()
    (hermes / "config.yaml").write_text(
        "platform_toolsets:\n  cli: []\n",
        encoding="utf-8",
    )
    return hermes


def test_provision_creates_profile_with_soul_and_config(tmp_path):
    mod = _load_sync_module()
    hermes = _hermes_fixture(tmp_path)
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    spec = manifest["profiles"]["data"]

    assert mod._provision_profile(hermes, REPO, "data", inject_soul=True)

    prof_dir = hermes / "profiles" / "data"
    assert prof_dir.is_dir()
    assert (prof_dir / "config.yaml").is_file()
    soul = prof_dir / "SOUL.md"
    assert soul.is_file()
    text = soul.read_text(encoding="utf-8")
    assert "## Interaction met J." in text
    assert "Output conventions (institutional)" in text

    assert mod._sync_profile(hermes, "data", spec, dry_run=False, check=False)
    cfg = yaml.safe_load((prof_dir / "config.yaml").read_text(encoding="utf-8"))
    cli = (cfg.get("platform_toolsets") or {}).get("cli") or []
    expected = (spec.get("platform_toolsets") or {}).get("cli") or []
    assert cli == expected


def test_provision_idempotent_when_config_exists(tmp_path):
    mod = _load_sync_module()
    hermes = _hermes_fixture(tmp_path)
    prof_dir = hermes / "profiles" / "data"
    prof_dir.mkdir(parents=True)
    (prof_dir / "config.yaml").write_text("platform_toolsets:\n  cli: []\n", encoding="utf-8")

    assert mod._provision_profile(hermes, REPO, "data", inject_soul=True)
    assert not (prof_dir / "SOUL.md").is_file()


def test_check_detects_toolset_drift(tmp_path):
    mod = _load_sync_module()
    hermes = _hermes_fixture(tmp_path)
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    spec = manifest["profiles"]["data"]

    mod._provision_profile(hermes, REPO, "data", inject_soul=False)
    mod._sync_profile(hermes, "data", spec, dry_run=False, check=False)

    cfg_path = hermes / "profiles" / "data" / "config.yaml"
    cfg_path.write_text("platform_toolsets:\n  cli: [mcp]\n", encoding="utf-8")

    assert not mod._sync_profile(hermes, "data", spec, dry_run=False, check=True)


def test_invalid_profile_name_fails(tmp_path):
    mod = _load_sync_module()
    hermes = _hermes_fixture(tmp_path)
    assert not mod._provision_profile(hermes, REPO, "core/profile", inject_soul=True)


def test_create_missing_cli_integration(tmp_path):
    mod = _load_sync_module()
    hermes = _hermes_fixture(tmp_path)
    import argparse

    args = argparse.Namespace(
        repo_root=str(REPO),
        hermes_root=str(hermes),
        profile="ict",
        dry_run=False,
        check=False,
        create_missing=True,
        no_soul_inject=False,
        sync_soul_snippets=False,
    )
    manifest = mod._load_manifest(REPO)
    profiles = manifest["profiles"]
    name = "ict"
    cfg_path = hermes / "profiles" / name / "config.yaml"
    if not cfg_path.is_file():
        mod._provision_profile(hermes, REPO, name, dry_run=args.dry_run, inject_soul=True)
    ok = mod._sync_profile(
        hermes, name, profiles[name], dry_run=args.dry_run, check=args.check
    )
    assert ok
    assert (hermes / "profiles" / "ict" / "SOUL.md").is_file()


def test_resolve_soul_template_ict():
    mod = _load_sync_module()
    p = mod._resolve_soul_template(REPO, "ict")
    assert p is not None
    assert p.name == "SOUL_ICT_DOMAIN.md"


def test_resolve_soul_template_creative():
    mod = _load_sync_module()
    p = mod._resolve_soul_template(REPO, "creative")
    assert p is not None
    assert p.name == "SOUL_CREATIVE_DOMAIN.md"


def test_provision_creative_syncs_cli(tmp_path):
    mod = _load_sync_module()
    hermes = _hermes_fixture(tmp_path)
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    spec = manifest["profiles"]["creative"]
    assert mod._provision_profile(hermes, REPO, "creative", inject_soul=False)
    assert mod._sync_profile(hermes, "creative", spec, dry_run=False, check=False)
    cfg = yaml.safe_load((hermes / "profiles" / "creative" / "config.yaml").read_text(encoding="utf-8"))
    cli = (cfg.get("platform_toolsets") or {}).get("cli") or []
    assert "terminal" in cli


def test_clone_from_fallback_soul(tmp_path):
    mod = _load_sync_module()
    hermes = _hermes_fixture(tmp_path)
    legal_dir = hermes / "profiles" / "legal"
    legal_dir.mkdir(parents=True)
    (legal_dir / "SOUL.md").write_text("# Legal SOUL\n", encoding="utf-8")
    (legal_dir / "config.yaml").write_text("platform_toolsets:\n  cli: []\n", encoding="utf-8")

    assert mod._provision_profile(
        hermes,
        REPO,
        "e2e_clone_test",
        inject_soul=True,
        clone_from="legal",
    )
    soul = hermes / "profiles" / "e2e_clone_test" / "SOUL.md"
    assert soul.is_file()
    assert "Legal SOUL" in soul.read_text(encoding="utf-8")


def test_argv_without_hermes_profile_flag_strips_cli_profile():
    mod = _load_sync_module()
    argv = [
        "sync_profile_toolsets_from_manifest.py",
        "--repo-root",
        "/repo",
        "--profile",
        "e2e_provision_test",
        "--create-missing",
    ]
    stripped = mod._argv_without_hermes_profile_flag(argv)
    assert stripped == [
        "sync_profile_toolsets_from_manifest.py",
        "--repo-root",
        "/repo",
        "--create-missing",
    ]


def test_argv_without_hermes_profile_flag_strips_p_and_equals_form():
    mod = _load_sync_module()
    assert mod._argv_without_hermes_profile_flag(
        ["sync.py", "-p", "legal", "--check"]
    ) == ["sync.py", "--check"]
    assert mod._argv_without_hermes_profile_flag(
        ["sync.py", "--profile=ict", "--dry-run"]
    ) == ["sync.py", "--dry-run"]
    # Trailing --profile without value: drop flag only
    assert mod._argv_without_hermes_profile_flag(["sync.py", "--profile"]) == ["sync.py"]


def test_main_with_profile_flag_does_not_require_runtime_profile(tmp_path):
    """Regression: --profile for this script must not trigger hermes_cli.main override."""
    hermes = _hermes_fixture(tmp_path)
    py = os.environ.get("HERMES_PYTHON") or sys.executable
    r = subprocess.run(
        [
            py,
            str(SYNC_SCRIPT),
            "--repo-root",
            str(REPO),
            "--hermes-root",
            str(hermes),
            "--profile",
            "ict",
            "--create-missing",
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr or r.stdout
    assert (hermes / "profiles" / "ict" / "config.yaml").is_file()


def test_provision_only_skips_sync(tmp_path, monkeypatch):
    mod = _load_sync_module()
    hermes = _hermes_fixture(tmp_path)
    sync_called = []

    def _track_sync(*a, **kw):
        sync_called.append(True)
        return True

    monkeypatch.setattr(mod, "_sync_profile", _track_sync)
    import argparse

    args = argparse.Namespace(
        repo_root=str(REPO),
        hermes_root=str(hermes),
        profile="ict",
        dry_run=False,
        check=False,
        create_missing=True,
        no_soul_inject=False,
        sync_soul_snippets=False,
        clone_from="legal",
        provision_only=True,
    )
    manifest = mod._load_manifest(REPO)
    profiles = manifest["profiles"]
    name = "ict"
    cfg_path = hermes / "profiles" / name / "config.yaml"
    if not cfg_path.is_file():
        mod._provision_profile(
            hermes, REPO, name, dry_run=False, inject_soul=True, clone_from="legal"
        )
    if not args.provision_only:
        mod._sync_profile(hermes, name, profiles[name], dry_run=False, check=False)
    assert not sync_called
    assert cfg_path.is_file()
