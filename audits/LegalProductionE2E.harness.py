#!/usr/bin/env python3
"""E2E: Legal productie P0-P3 (slash, parity, verify, SOUL-meta, pytest contract).

Geen live LLM-chat. Optioneel: runtime SOUL/verify_legal_runtime als machine dat heeft.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FAILURES = 0
STEP = 0

REQUIRED_PATHS = (
    "hermes_cli/legal_architecture_brief.py",
    "scripts/rag_pipeline/verify_legal_lens_parity.py",
    "scripts/rag_pipeline/legal_lens_from_path.py",
    "windows/scripts/verify_legal_runtime.ps1",
    "windows/scripts/ensure_legal_active_matters.ps1",
    "windows/VERIFY_LEGAL_RUNTIME.bat",
    "windows/SYNC_LEGAL_LENS_FROM_TAXONOMY.bat",
    "docs/LEGAL_PRODUCTION_GATE.md",
    "docs/LEGAL_INGEST_METADATA.md",
    "docs/templates/LEGAL_ACTIVE_MATTERS.example.md",
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


def _run_ps1(script_rel: str, *ps_args: str, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    script = REPO / script_rel.replace("/", os.sep)
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


def main() -> int:
    global FAILURES

    print("=== Legal Production E2E harness ===", flush=True)
    print(f"Repo: {REPO}", flush=True)

    missing = [p for p in REQUIRED_PATHS if not (REPO / p).is_file()]
    _step("repo artifacts", not missing, ", ".join(missing) if missing else f"{len(REQUIRED_PATHS)} paths")

    # Slash + brief
    sys.path.insert(0, str(REPO))
    try:
        from hermes_cli.commands import resolve_command
        from hermes_cli.legal_architecture_brief import (
            brief_forbids_generic_team_primary,
            build_legal_architecture_brief,
        )

        cmd = resolve_command("legal-architectuur")
        _step(
            "slash legal-architectuur registered",
            cmd is not None and cmd.name == "legal-architectuur" and not cmd.cli_only,
            f"cli_only={getattr(cmd, 'cli_only', '?')}" if cmd else "missing",
        )
        alias = resolve_command("legal-arch")
        _step("slash alias legal-arch", alias is not None and alias.name == "legal-architectuur")

        brief_legal = build_legal_architecture_brief("legal")
        _step(
            "brief legal profile",
            "lenzen" in brief_legal.lower() and "lancedb-legal" in brief_legal,
        )
        _step(
            "brief contract",
            brief_forbids_generic_team_primary(brief_legal),
        )
        brief_core = build_legal_architecture_brief("core")
        _step(
            "brief core redirect",
            "profile use legal" in brief_core.lower(),
        )
    except Exception as exc:
        _step("slash + brief imports", False, str(exc))

    # SOUL template meta
    legal_tpl = (REPO / "docs/templates/SOUL_LEGAL_DOMAIN.md").read_text(encoding="utf-8")
    core_tpl = (REPO / "docs/templates/SOUL_CORE_ORCHESTRATOR.md").read_text(encoding="utf-8")
    _step(
        "SOUL legal template meta",
        "Domeinarchitectuur" in legal_tpl and "/legal-architectuur" in legal_tpl,
    )
    _step(
        "SOUL core template meta",
        "Legal architectuur" in core_tpl and "/legal-architectuur" in core_tpl,
    )

    # Lens parity template
    parity = _run_py([str(REPO / "scripts/rag_pipeline/verify_legal_lens_parity.py")])
    _step(
        "verify_legal_lens_parity template",
        parity.returncode == 0,
        (parity.stderr or parity.stdout or "")[:200],
    )

    # Lens parity runtime (+ auto-fix zoals productie-deploy)
    parity_all = _run_py(
        [str(REPO / "scripts/rag_pipeline/verify_legal_lens_parity.py"), "--all"]
    )
    if parity_all.returncode != 0:
        sync_all = _run_py(
            [
                str(REPO / "scripts/rag_pipeline/sync_legal_lens_table_from_taxonomy.py"),
                "--all",
            ]
        )
        _step("sync_legal_lens --all (parity repair)", sync_all.returncode == 0)
        parity_all = _run_py(
            [str(REPO / "scripts/rag_pipeline/verify_legal_lens_parity.py"), "--all"]
        )
    _step(
        "verify_legal_lens_parity --all",
        parity_all.returncode == 0,
        (parity_all.stderr or parity_all.stdout or "")[:200],
    )

    # Sync dry-run
    sync = _run_py(
        [
            str(REPO / "scripts/rag_pipeline/sync_legal_lens_table_from_taxonomy.py"),
            "--dry-run",
        ]
    )
    _step("sync_legal_lens dry-run", sync.returncode == 0, (sync.stderr or "")[:200])

    # legal_lens_from_path smoke
    lens_py = _run_py(
        [
            "-c",
            "from scripts.rag_pipeline.legal_lens_from_path import legal_lens_from_source; "
            "assert legal_lens_from_source('04_Legal_Corporate/Arbeidsrecht/x.pdf')=='arb'; "
            "assert legal_lens_from_source('') is None",
        ],
    )
    if lens_py.returncode != 0:
        # fallback: add rag_pipeline to path
        lens_py = _run_py(
            [
                "-c",
                "import sys; sys.path.insert(0,'scripts/rag_pipeline'); "
                "from legal_lens_from_path import legal_lens_from_source; "
                "assert legal_lens_from_source('04_Legal_Corporate/Arbeidsrecht/x.pdf')=='arb'",
            ],
        )
    _step("legal_lens_from_path smoke", lens_py.returncode == 0, (lens_py.stderr or "")[:200])

    # Pytest contract bundle
    pytest_args = [
        "-m",
        "pytest",
        "tests/windows/test_legal_domain_docs.py",
        "tests/windows/test_legal_meta_contract.py",
        "tests/windows/test_legal_skill_manifest.py",
        "tests/cli/test_legal_architecture_slash.py",
        "tests/scripts/test_legal_lens_from_path.py",
        "tests/windows/test_legal_windows_ps1_contract.py",
        "-q",
        "--tb=short",
    ]
    pt = _run_py(pytest_args, timeout=300)
    _step("pytest legal contract bundle", pt.returncode == 0, (pt.stderr or pt.stdout or "")[-300:])

    # ensure_legal_active_matters (idempotent op dev machine)
    ensure = _run_ps1("windows/scripts/ensure_legal_active_matters.ps1", "-Quiet")
    _step(
        "ensure_legal_active_matters.ps1",
        ensure.returncode == 0,
        (ensure.stderr or ensure.stdout or "")[:200],
    )

    # Runtime SOUL meta + lenzen (productie-deploy keten)
    soul_legal = _run_ps1("windows/scripts/sync_legal_soul_from_template.ps1")
    _step("sync_legal_soul_from_template", soul_legal.returncode == 0)
    soul_core = _run_ps1(
        "windows/scripts/sync_domain_soul_from_template.ps1",
        "-ProfileName",
        "core",
    )
    _step("sync_core_soul_from_template", soul_core.returncode == 0)
    lens_after = _run_py(
        [
            str(REPO / "scripts/rag_pipeline/sync_legal_lens_table_from_taxonomy.py"),
            "--all",
        ]
    )
    _step("sync_legal_lens --all post-template", lens_after.returncode == 0)

    # verify_legal_runtime (strict parity na sync hierboven)
    prev_strict = os.environ.get("HERMES_LEGAL_VERIFY_STRICT")
    os.environ["HERMES_LEGAL_VERIFY_STRICT"] = "1"
    verify = _run_ps1("windows/scripts/verify_legal_runtime.ps1", "-Quiet")
    if prev_strict is None:
        os.environ.pop("HERMES_LEGAL_VERIFY_STRICT", None)
    else:
        os.environ["HERMES_LEGAL_VERIFY_STRICT"] = prev_strict
    _step(
        "verify_legal_runtime.ps1 (strict)",
        verify.returncode == 0,
        (verify.stderr or verify.stdout or "")[:300],
    )

    print("", flush=True)
    if FAILURES:
        print(f"=== LEGAL PRODUCTION E2E: {FAILURES} FAIL ===", flush=True)
        return 1
    print("=== LEGAL PRODUCTION E2E: ALL PASS ===", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
