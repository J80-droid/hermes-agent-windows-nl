#!/usr/bin/env python3
"""E2E: creative domein (14e profiel) — manifest, docs, SOUL, provision, pytest.

Geen live API, geen netwerk.

Operators:
  audits/RUN_CREATIVE_DOMAIN_E2E.bat

Tests (unit + mocks, geen nested pytest in C9):
  pytest tests/audits/test_creative_domain_e2e_harness.py -q
  pytest tests/audits/test_creative_domain_e2e_harness.py -m e2e -q  # volledige harness

C10 gebruikt een tijdelijke HERMES_HOME en patcht ``_apply_trust_memory_limits``
zodat de echte ``%LOCALAPPDATA%\\hermes`` niet wordt aangepast.
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[1]
FAILURES = 0
STEP = 0

PY = Path.home() / "miniconda3/envs/hermes-env/python.exe"
if not PY.is_file():
    PY = Path(sys.executable)

REQUIRED_ARTEFACTS = (
    "docs/domain_toolsets.yaml",
    "docs/domains.yaml.example",
    "docs/DOMAIN_BLUEPRINT.md",
    "docs/ORCHESTRATOR_ROUTING.md",
    "docs/templates/SOUL_CREATIVE_DOMAIN.md",
    "docs/13_Creative/README.md",
    "docs/13_Creative/ONBOARDING.md",
    "docs/13_Creative/PROCEDURES.md",
    "docs/13_Creative/ESCALATION.md",
    "docs/13_Creative/CREATIVE_ACTIVE_MATTERS.md",
    "docs/13_Creative/Visual/README.md",
    "docs/13_Creative/Motion/README.md",
    "docs/13_Creative/Interactive/README.md",
    "docs/13_Creative/Writing/README.md",
    "windows/scripts/sync_profile_toolsets_from_manifest.py",
    "windows/SYNC_DOMAIN_TOOLSETS.bat",
    "tests/windows/test_creative_domain_docs.py",
)

FORK_SKILL_PATHS = (
    "skills/creative/manim-video",
    "optional-skills/creative/hyperframes",
    "skills/creative/comfyui",
    "skills/creative/touchdesigner-mcp",
    "skills/creative/excalidraw",
    "skills/creative/baoyu-article-illustrator",
    "skills/creative/creative-ideation",
)


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] C{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] C{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8", errors="replace")


def _load_manifest() -> dict[str, Any]:
    data = yaml.safe_load(_read("docs/domain_toolsets.yaml"))
    if not isinstance(data, dict):
        raise ValueError("domain_toolsets.yaml is geen mapping")
    return data


def _creative_spec(data: dict[str, Any]) -> dict[str, Any]:
    profiles = data.get("profiles") or {}
    spec = profiles.get("creative")
    if not isinstance(spec, dict):
        raise KeyError("profiles.creative ontbreekt")
    return spec


def _fork_paths_from_manifest(spec: dict[str, Any]) -> list[Path]:
    fork = spec.get("fork_creative_skills") or {}
    paths: list[Path] = []
    for value in fork.values():
        if not isinstance(value, str):
            continue
        m = re.match(r"^\s*((?:skills|optional-skills)/\S+)", value)
        if m:
            paths.append(REPO / m.group(1).rstrip("/"))
    return paths


def _load_sync_module():
    path = REPO / "windows/scripts/sync_profile_toolsets_from_manifest.py"
    spec = importlib.util.spec_from_file_location("sync_profile_toolsets_e2e", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Kan module niet laden: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _hermes_runtime_root() -> Path | None:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
    if (local_root / "config.yaml").is_file():
        return local_root
    home_root = Path.home() / ".hermes"
    if (home_root / "config.yaml").is_file():
        return home_root
    return None


def test_c1_repo_artefacts() -> None:
    missing = [rel for rel in REQUIRED_ARTEFACTS if not (REPO / rel).is_file()]
    ok = not missing
    detail = f"{len(REQUIRED_ARTEFACTS) - len(missing)}/{len(REQUIRED_ARTEFACTS)} bestanden"
    if missing:
        detail += f"; ontbrekend: {', '.join(missing[:3])}"
        if len(missing) > 3:
            detail += f" (+{len(missing) - 3})"
    _step("repo-artefacten creative", ok, detail)


def test_c2_manifest_contract() -> None:
    data = _load_manifest()
    spec = _creative_spec(data)
    cli = set((spec.get("platform_toolsets") or {}).get("cli") or [])
    optional = set(spec.get("optional_toolsets") or [])
    triggers = set((spec.get("ask_triggers") or {}).keys())
    lenses = spec.get("creative_lenses") or {}
    checks = [
        "terminal" in cli,
        {"visual", "motion", "interactive", "writing"} <= set(lenses.keys()),
        "fork_creative_skills" in spec,
        "manim_video" in (spec.get("fork_creative_skills") or {}),
        "hyperframes" in (spec.get("fork_creative_skills") or {}),
        optional <= triggers,
        int(spec.get("max_tools") or 0) >= len(cli) + len(optional),
        not (cli & set(data.get("never_default_global") or [])),
    ]
    ok = all(checks)
    _step("manifest creative contract", ok, f"{sum(checks)}/{len(checks)} checks")


def test_c3_fork_skill_paths() -> None:
    data = _load_manifest()
    spec = _creative_spec(data)
    paths = _fork_paths_from_manifest(spec)
    missing = [p for p in paths if not p.is_dir()]
    ok = not missing and len(paths) >= len(FORK_SKILL_PATHS)
    detail = f"{len(paths) - len(missing)}/{len(paths)} mappen"
    if missing:
        detail += f"; ontbrekend: {missing[0].relative_to(REPO)}"
    hf_skill = REPO / "optional-skills/creative/hyperframes/SKILL.md"
    if ok and not hf_skill.is_file():
        ok = False
        detail = "hyperframes/SKILL.md ontbreekt"
    _step("fork_creative_skills op schijf", ok, detail)


def test_c4_domains_example() -> None:
    data = yaml.safe_load(_read("docs/domains.yaml.example"))
    domains = data.get("domains") or []
    creative = next((d for d in domains if isinstance(d, dict) and d.get("name") == "creative"), None)
    ok = (
        creative is not None
        and creative.get("source_dir") == "13_Creative"
        and creative.get("mcp_name") == "lancedb-creative"
        and creative.get("profile_name") == "creative"
    )
    _step("domains.yaml.example creative", ok, "13_Creative + lancedb-creative")


def test_c5_orchestrator_routing() -> None:
    routing = _read("docs/ORCHESTRATOR_ROUTING.md")
    core = _read("docs/templates/SOUL_CORE_ORCHESTRATOR.md")
    blueprint = _read("docs/DOMAIN_BLUEPRINT.md")
    checks = [
        "creative" in routing and "lancedb-creative" in routing,
        "`creative`" in core or "| `creative`" in core,
        "creative" in blueprint and "13_Creative" in blueprint,
    ]
    ok = all(checks)
    _step("orchestrator + blueprint routing", ok, f"{sum(checks)}/3")


def test_c6_sync_soul_profile_list() -> None:
    ps1 = _read("windows/scripts/SyncSoulSnippet.psm1")
    m = re.search(
        r"function Get-DomainSoulProfileNames\s*\{[^}]*return\s*@\(([^)]+)\)",
        ps1,
        re.DOTALL,
    )
    ok = m is not None and "'creative'" in m.group(1)
    if ok:
        names = re.findall(r"'([^']+)'", m.group(1))
        ok = "creative" in names and len(names) == 14
    detail = "14 profielen incl. creative" if ok else "Get-DomainSoulProfileNames mist creative"
    _step("SyncSoulSnippet profiellijst", ok, detail)


def test_c7_backup_active_matters() -> None:
    ps1 = _read("windows/scripts/HermesBackupCommon.ps1")
    ok = "CREATIVE_ACTIVE_MATTERS.md" in ps1 and "$name -eq 'creative'" in ps1
    _step("HermesBackupCommon CREATIVE_ACTIVE_MATTERS", ok)


def test_c8_soul_template_gates() -> None:
    soul = _read("docs/templates/SOUL_CREATIVE_DOMAIN.md")
    checks = [
        "### Creative-lenzen" in soul,
        "hyperframes" in soul.lower(),
        "manim-video" in soul,
        "Forensic & trust" in soul or "forensic" in soul.lower(),
        "CREATIVE_ACTIVE_MATTERS" in soul,
        "lancedb-creative" in soul,
        "image_gen" in soul,
    ]
    ok = all(checks)
    _step("SOUL_CREATIVE_DOMAIN gates", ok, f"{sum(checks)}/{len(checks)}")


def test_c9_pytest_creative_subset() -> None:
    cmd = [
        str(PY),
        "-m",
        "pytest",
        "tests/windows/test_domain_toolsets_manifest.py",
        "-k",
        "creative",
        "tests/windows/test_creative_domain_docs.py",
        "tests/windows/test_provision_profile_from_manifest.py",
        "-k",
        "creative or resolve_soul_template_creative",
        "-q",
        "--tb=short",
    ]
    proc = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True, timeout=120)
    ok = proc.returncode == 0
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    detail = tail[-1] if tail else f"exit={proc.returncode}"
    if not ok and proc.stderr:
        detail = proc.stderr.strip().splitlines()[-1][:120]
    _step("pytest creative subset", ok, detail)


def test_c10_temp_provision_sync() -> None:
    mod = _load_sync_module()
    data = _load_manifest()
    spec = _creative_spec(data)

    def _skip_trust_memory_limits(_repo: Path, *, dry_run: bool = False) -> bool:
        return True

    with tempfile.TemporaryDirectory() as tmp:
        hermes = Path(tmp) / "hermes"
        hermes.mkdir(exist_ok=True)
        (hermes / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
        prev_apply = mod._apply_trust_memory_limits
        mod._apply_trust_memory_limits = _skip_trust_memory_limits  # type: ignore[method-assign]
        try:
            ok_prov = mod._provision_profile(hermes, REPO, "creative", inject_soul=True)
        finally:
            mod._apply_trust_memory_limits = prev_apply  # type: ignore[method-assign]
        ok_sync = mod._sync_profile(hermes, "creative", spec, dry_run=False, check=False)
        if not (ok_prov and ok_sync):
            ok = False
        else:
            cfg_path = hermes / "profiles" / "creative" / "config.yaml"
            soul_path = hermes / "profiles" / "creative" / "SOUL.md"
            if not cfg_path.is_file() or not soul_path.is_file():
                ok = False
            else:
                cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
                cli = (cfg.get("platform_toolsets") or {}).get("cli") or []
                expected_cli = (spec.get("platform_toolsets") or {}).get("cli") or []
                soul = soul_path.read_text(encoding="utf-8")
                ok = (
                    cli == expected_cli
                    and "terminal" in cli
                    and "### Creative-lenzen" in soul
                    and "Output conventions (institutional)" in soul
                )
    _step("temp provision + sync creative", ok, "terminal + SOUL template")


def test_c11_runtime_manifest_check() -> None:
    hermes = _hermes_runtime_root()
    cfg = hermes / "profiles" / "creative" / "config.yaml" if hermes else None
    if cfg is None or not cfg.is_file():
        _step("runtime manifest drift (optioneel)", True, "overgeslagen — geen runtime profiel creative")
        return
    sync_py = REPO / "windows/scripts/sync_profile_toolsets_from_manifest.py"
    env = {**os.environ, "HERMES_HOME": str(hermes)}
    proc = subprocess.run(
        [
            str(PY),
            str(sync_py),
            "--repo-root",
            str(REPO),
            "--hermes-root",
            str(hermes),
            "--profile",
            "creative",
            "--check",
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=90,
        env=env,
    )
    ok = proc.returncode == 0
    detail = "cli matcht manifest" if ok else (proc.stdout or proc.stderr or "")[-200:]
    _step("runtime manifest drift (optioneel)", ok, detail.strip()[:80])


def main() -> int:
    print("=" * 60, flush=True)
    print("  Creative domain E2E - Audit", flush=True)
    print("=" * 60, flush=True)
    print(flush=True)

    test_c1_repo_artefacts()
    test_c2_manifest_contract()
    test_c3_fork_skill_paths()
    test_c4_domains_example()
    test_c5_orchestrator_routing()
    test_c6_sync_soul_profile_list()
    test_c7_backup_active_matters()
    test_c8_soul_template_gates()
    test_c9_pytest_creative_subset()
    test_c10_temp_provision_sync()
    test_c11_runtime_manifest_check()

    print(flush=True)
    print("=" * 60, flush=True)
    if FAILURES == 0:
        print(f"  ALL PASS ({STEP}/{STEP})", flush=True)
    else:
        print(f"  FAILURES: {FAILURES}/{STEP}", file=sys.stderr, flush=True)
    print("=" * 60, flush=True)
    return 1 if FAILURES > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
