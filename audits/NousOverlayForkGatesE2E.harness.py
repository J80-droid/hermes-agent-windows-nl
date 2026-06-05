#!/usr/bin/env python3
"""E2E: Nous overlay fork gates (2026-06) — argv, config get, toolset check, legal USER.

Covers recent Tier-B fixes without live API:
- sync_profile_toolsets argv neutralization + --profile provision
- argparse/config fork ``config get`` via overlay CLI entrypoint
- toolset --check skips ``_user_customized.cli``
- legal USER stale-domain strip on trust sync
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

FAILURES = 0
STEP = 0

SYNC_SCRIPT = REPO_ROOT / "windows" / "scripts" / "sync_profile_toolsets_from_manifest.py"
OVERLAY_CLI = REPO_ROOT / "scripts" / "run_hermes_cli_with_overlay.py"
SYNC_MEMORIES_PS1 = REPO_ROOT / "windows" / "scripts" / "sync_profile_memories.ps1"


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" — {detail}" if detail else ""
    if ok:
        print(f"[OK] E{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] E{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def _load_sync_module():
    spec = importlib.util.spec_from_file_location("sync_profile_toolsets_e2e", SYNC_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_e1_repo_artefacts() -> None:
    required = [
        REPO_ROOT / "overlay" / "hermes_cli" / "argparse_fork_patch.py",
        REPO_ROOT / "overlay" / "hermes_cli" / "config_fork_patch.py",
        REPO_ROOT / "scripts" / "run_hermes_cli_with_overlay.py",
        SYNC_SCRIPT,
        SYNC_MEMORIES_PS1,
        REPO_ROOT / "windows" / "scripts" / "toolset_domain_e2e_runtime.py",
        REPO_ROOT / "tests" / "overlay" / "test_argparse_fork_patch.py",
        REPO_ROOT / "audits" / "NousOverlayForkGatesE2E.harness.py",
        REPO_ROOT / "audits" / "RUN_NOUS_OVERLAY_FORK_GATES_E2E.bat",
    ]
    missing = [str(p.relative_to(REPO_ROOT)) for p in required if not p.is_file()]
    _step("repo-artefacten fork gates", not missing, ", ".join(missing) or "OK")


def test_e2_argv_sanitizer_forms() -> None:
    mod = _load_sync_module()
    cases = [
        (["sync.py", "--profile", "legal", "--check"], ["sync.py", "--check"]),
        (["sync.py", "-p", "ict", "--dry-run"], ["sync.py", "--dry-run"]),
        (["sync.py", "--profile=core"], ["sync.py"]),
        (["sync.py", "--profile"], ["sync.py"]),
    ]
    ok = all(mod._argv_without_hermes_profile_flag(a) == b for a, b in cases)
    _step("argv sanitizer (--profile/-p/=)", ok)


def test_e3_provision_subprocess_with_profile_flag() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        hermes = Path(tmp) / "hermes"
        hermes.mkdir()
        (hermes / "config.yaml").write_text(
            "platform_toolsets:\n  cli: []\n", encoding="utf-8"
        )
        proc = subprocess.run(
            [
                sys.executable,
                str(SYNC_SCRIPT),
                "--repo-root",
                str(REPO_ROOT),
                "--hermes-root",
                str(hermes),
                "--profile",
                "ict",
                "--create-missing",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            check=False,
        )
        combined = (proc.stdout or "") + (proc.stderr or "")
        ok = (
            proc.returncode == 0
            and (hermes / "profiles" / "ict" / "config.yaml").is_file()
            and "does not exist" not in combined
        )
        _step(
            "provision --profile zonder bootstrap crash",
            ok,
            combined[-200:].strip() if not ok else "ict aangemaakt",
        )


def test_e4_config_get_overlay_entrypoint() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    proc = subprocess.run(
        [
            sys.executable,
            str(OVERLAY_CLI),
            "config",
            "get",
            "auxiliary.vision.provider",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
        env=env,
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    lines = [
        ln.strip()
        for ln in combined.splitlines()
        if ln.strip() and "usage:" not in ln.lower() and "invalid choice" not in ln.lower()
    ]
    ok = proc.returncode == 0 and len(lines) >= 1 and "get" not in lines[-1].lower()
    _step(
        "overlay CLI config get subcommand",
        ok,
        lines[-1] if lines else combined[-160:].strip(),
    )


def test_e5_toolset_check_skips_user_customized() -> None:
    mod = _load_sync_module()
    with tempfile.TemporaryDirectory() as tmp:
        hermes = Path(tmp) / "hermes"
        prof = hermes / "profiles" / "legal"
        prof.mkdir(parents=True)
        cfg = {
            "platform_toolsets": {
                "cli": ["mcp", "extra-tool"],
                "_user_customized": {"cli": True},
            }
        }
        (prof / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
        manifest = mod._load_manifest(REPO_ROOT)
        spec = manifest["profiles"]["legal"]
        ok = mod._sync_profile(
            hermes, "legal", spec, dry_run=False, check=True, force_manifest=False
        )
    _step("toolset --check slaat _user_customized over", ok)


def test_e6_argparse_config_get_no_duplicate() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/overlay/test_argparse_fork_patch.py",
            "-q",
            "--tb=line",
            "-o",
            "addopts=",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
        env=env,
    )
    tail = (proc.stdout or proc.stderr or "").strip()[-200:]
    ok = proc.returncode == 0 and "passed" in tail.lower()
    _step("pytest argparse_fork_patch", ok, tail if not ok else "")


def test_e7_legal_user_stale_domain_replaced() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        hermes = Path(tmp) / "hermes"
        legal_user = hermes / "profiles" / "legal" / "memories"
        legal_user.mkdir(parents=True)
        stale = (
            "J. demands absolute trust.\n"
            "§\n"
            "Parallelle invalshoeken. Oud blok zonder Legal proactief triggers.\n"
            "§\n"
            "SOUL prevaleert bij conflict.\n"
        )
        (legal_user / "USER.md").write_text(stale, encoding="utf-8")
        (hermes / "config.yaml").write_text(
            "platform_toolsets:\n  cli: []\n", encoding="utf-8"
        )
        env = os.environ.copy()
        env["HERMES_HOME"] = str(hermes)
        env["PYTHONPATH"] = str(REPO_ROOT)
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SYNC_MEMORIES_PS1),
                "-RepoRoot",
                str(REPO_ROOT),
                "-HermesRoot",
                str(hermes),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=180,
            check=False,
            env=env,
        )
        user_text = (legal_user / "USER.md").read_text(encoding="utf-8")
        ok = (
            proc.returncode == 0
            and "Legal proactief" in user_text
            and "Legal triggers" in user_text
            and "Parallelle invalshoeken. Oud blok" not in user_text
        )
        detail = user_text[:120].replace("\n", " ") if not ok else "canonical NL seed"
        _step("legal USER stale-domain strip + seed", ok, detail)


def test_e8_toolset_runtime_env_guard() -> None:
    env = os.environ.copy()
    env.pop("HERMES_TOOLSET_E2E_REPO", None)
    env.pop("HERMES_TOOLSET_E2E_HOME", None)
    env["PYTHONPATH"] = str(REPO_ROOT)
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "windows" / "scripts" / "toolset_domain_e2e_runtime.py")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
        env=env,
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == 1 and "ontbrekende env" in combined.lower()
    _step("toolset runtime env guard (missing env)", ok)


def main() -> int:
    print("=== Nous Overlay Fork Gates E2E ===", flush=True)
    test_e1_repo_artefacts()
    test_e2_argv_sanitizer_forms()
    test_e3_provision_subprocess_with_profile_flag()
    test_e4_config_get_overlay_entrypoint()
    test_e5_toolset_check_skips_user_customized()
    test_e6_argparse_config_get_no_duplicate()
    test_e7_legal_user_stale_domain_replaced()
    test_e8_toolset_runtime_env_guard()
    if FAILURES:
        print(f"=== HARNESS: FAIL ({FAILURES}) ===", file=sys.stderr, flush=True)
        return 1
    print(f"=== HARNESS: PASS ({STEP}/{STEP}) ===", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
