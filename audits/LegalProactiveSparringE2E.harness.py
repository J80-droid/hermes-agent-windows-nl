#!/usr/bin/env python3
"""E2E: Legal proactive sparring (parallelle invalshoeken, config repair, legal USER seed).

Geen live LLM. Zie LEGAL_PROACTIVE_SPARRING_E2E_README.md.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

FAILURES = 0
STEP = 0


def _repo_root() -> Path:
    env = os.environ.get("HERMES_REPO_ROOT", "").strip().strip('"')
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


REPO = _repo_root()

REQUIRED_PATHS = (
    "docs/templates/SOUL_LEGAL_DOMAIN.md",
    "docs/templates/LEGAL_ACTIVE_MATTERS.example.md",
    "docs/templates/MEMORY_CANONICAL_SEED.md",
    "docs/templates/SOUL_SHARED_OUTPUT_FORMAT.md",
    "docs/templates/SOUL_SHARED_CONFIG_GOVERNANCE.md",
    "windows/scripts/SyncSoulSnippet.psm1",
    "windows/scripts/sync_soul_config_governance_snippet.ps1",
    "windows/scripts/sync_soul_anatomy_snippets.ps1",
    "windows/scripts/sync_profile_memories.ps1",
    "windows/scripts/HermesMemoryMergeCommon.ps1",
    "windows/tests/SoulSnippetRepair.Unit.Tests.ps1",
    "audits/LegalProactiveSparringE2E.core.ps1",
)


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] S{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] S{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def _audit_python() -> str:
    if os.environ.get("HERMES_AUDIT_PYTHON") and Path(os.environ["HERMES_AUDIT_PYTHON"]).is_file():
        return os.environ["HERMES_AUDIT_PYTHON"]
    for c in (
        Path(os.environ.get("USERPROFILE", "")) / "miniconda3/envs/hermes-env/python.exe",
        Path(sys.executable),
    ):
        if c.is_file():
            return str(c)
    return sys.executable


def _run_py(args: list[str], *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    py = _audit_python()
    return subprocess.run(
        [py, *args],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _run_py_safe(args: list[str], *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    try:
        return _run_py(args, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            args=exc.cmd or [],
            returncode=1,
            stdout="",
            stderr=f"timeout after {exc.timeout}s",
        )
    except OSError as exc:
        return subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr=str(exc),
        )


def _run_ps1(script_rel: str, *ps_args: str, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    script = REPO / script_rel.replace("/", os.sep)
    if not script.is_file():
        return subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr=f"script ontbreekt: {script}",
        )
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        *ps_args,
    ]
    return subprocess.run(
        cmd,
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=os.environ.copy(),
    )


def _run_ps1_safe(script_rel: str, *ps_args: str, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    try:
        return _run_ps1(script_rel, *ps_args, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            args=exc.cmd or [],
            returncode=1,
            stdout="",
            stderr=f"timeout after {exc.timeout}s",
        )
    except OSError as exc:
        return subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr=str(exc),
        )


def _read(rel: str) -> str | None:
    path = REPO / rel
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def main() -> int:
    global FAILURES

    print("=== Legal Proactive Sparring E2E ===", flush=True)
    print(f"Repo: {REPO}", flush=True)

    missing = [p for p in REQUIRED_PATHS if not (REPO / p).is_file()]
    _step("repo artifacts", not missing, ", ".join(missing) if missing else f"{len(REQUIRED_PATHS)} paths")

    legal_tpl = _read("docs/templates/SOUL_LEGAL_DOMAIN.md")
    _step(
        "SOUL legal parallelle invalshoeken sectie",
        legal_tpl is not None
        and "Parallelle invalshoeken" in legal_tpl
        and "Proactief meedenken" in legal_tpl,
    )
    _step(
        "SOUL legal pushback parallelle tabel",
        legal_tpl is not None
        and "parallelle invalshoeken" in legal_tpl.lower()
        and "Pushback" in legal_tpl,
    )
    _step(
        "SOUL legal example mandaat/disciplinair",
        legal_tpl is not None
        and "mandaat" in legal_tpl.lower()
        and "disciplinair" in legal_tpl.lower(),
    )

    matters_ex = _read("docs/templates/LEGAL_ACTIVE_MATTERS.example.md")
    _step(
        "MATTERS example GCR + Adjacent checks",
        matters_ex is not None
        and "GCR 2024-00145" in matters_ex
        and "Adjacent checks" in matters_ex,
    )

    seed = _read("docs/templates/MEMORY_CANONICAL_SEED.md")
    _step(
        "MEMORY seed legal USER section",
        seed is not None
        and "## legal USER.md entries" in seed
        and "Legal proactief" in seed,
    )
    _step(
        "MEMORY seed legal triggers voorbeeldvragen",
        seed is not None
        and "Legal triggers" in seed
        and "voorbeeldvragen" in seed
        and "disciplinaire maatregel" in seed,
    )
    _step(
        "MEMORY seed taallaag + SOUL prevaleert",
        seed is not None and "Legal taallaag" in seed and "SOUL prevaleert" in seed,
    )
    _step(
        "MEMORY seed taal-triggerlagen doc",
        seed is not None and "Taal- en triggerlagen" in seed and "Geen i18n" in seed,
    )
    _step(
        "SOUL USER.md trust EN + triggers NL sectie",
        legal_tpl is not None
        and "USER.md (trust EN + legal triggers NL)" in legal_tpl
        and "SOUL prevaleert" in legal_tpl,
    )
    arch = _read("docs/LEGAL_DOMAIN_ARCHITECTURE.md")
    _step(
        "LEGAL_DOMAIN_ARCHITECTURE taal-triggerlagen",
        arch is not None and "Taal- en triggerlagen" in arch and "SOUL prevaleert" in arch,
    )

    out_fmt = _read("docs/templates/SOUL_SHARED_OUTPUT_FORMAT.md")
    _step(
        "OUTPUT_FORMAT legal parallelle regel",
        out_fmt is not None
        and "Parallelle invalshoeken" in out_fmt
        and "SOUL_LEGAL_DOMAIN" in out_fmt,
    )

    psm1 = _read("windows/scripts/SyncSoulSnippet.psm1")
    _step(
        "SyncSoulSnippet export config repair",
        psm1 is not None
        and "Repair-SoulDuplicateConfigGovernanceBlocks" in psm1
        and "Export-ModuleMember" in psm1,
    )
    _step(
        "SyncSoulSnippet anatomy cfg count check",
        psm1 is not None and "verwacht 1 Config governance-blok" in psm1,
    )

    sync_mem = _read("windows/scripts/sync_profile_memories.ps1")
    _step(
        "sync_profile_memories legal SeedEntries",
        sync_mem is not None
        and "Test-IsLegalProfileMemoryUserPath" in sync_mem
        and "legal USER.md" in sync_mem
        and "ExtraExisting" not in sync_mem,
    )

    merge = _read("windows/scripts/HermesMemoryMergeCommon.ps1")
    _step(
        "HermesMemoryMergeCommon Optional + legal path",
        merge is not None
        and "[switch]$Optional" in merge
        and "Test-IsLegalProfileMemoryUserPath" in merge,
    )

    pt = _run_py_safe(
        [
            "-m",
            "pytest",
            "tests/windows/test_legal_meta_contract.py",
            "tests/windows/test_legal_memory_language_layers.py",
            "-q",
            "--tb=short",
        ],
        timeout=120,
    )
    _step(
        "pytest legal memory contracts",
        pt.returncode == 0,
        (pt.stderr or pt.stdout or "")[-400:],
    )

    pester = _run_ps1_safe("audits/Invoke-LegalProactiveSparringPester.ps1", timeout=120)
    _step(
        "Pester SoulSnippetRepair.Unit.Tests",
        pester.returncode == 0,
        (pester.stderr or pester.stdout or "")[-400:],
    )

    core = _run_ps1_safe("audits/LegalProactiveSparringE2E.core.ps1", "-RepoRoot", str(REPO))
    _step(
        "LegalProactiveSparringE2E.core.ps1",
        core.returncode == 0,
        (core.stderr or core.stdout or "")[-500:],
    )

    print("", flush=True)
    if FAILURES:
        print(f"=== LEGAL PROACTIVE SPARRING E2E: {FAILURES} FAIL ===", flush=True)
        return 1
    print("=== LEGAL PROACTIVE SPARRING E2E: ALL PASS ===", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
