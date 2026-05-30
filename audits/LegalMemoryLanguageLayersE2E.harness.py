#!/usr/bin/env python3
"""E2E: Legal memory taal-lagen (EN trust + NL triggers, geen i18n).

Geen live LLM. Respecteert HERMES_REPO_ROOT. Subprocess: verify_legal_lens_parity,
pytest test_legal_memory_language_layers, LegalMemoryLanguageLayersE2E.core.ps1.

Zie LEGAL_MEMORY_LANGUAGE_LAYERS_E2E_README.md.
Unit tests: tests/audits/test_legal_memory_language_layers_e2e_harness.py
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
    "docs/templates/MEMORY_CANONICAL_SEED.md",
    "docs/templates/SOUL_LEGAL_DOMAIN.md",
    "docs/LEGAL_DOMAIN_ARCHITECTURE.md",
    "windows/scripts/sync_profile_memories.ps1",
    "windows/scripts/HermesMemoryMergeCommon.ps1",
    "windows/scripts/Invoke-LegalProactiveSparringE2E.ps1",
    "audits/LegalMemoryLanguageLayersE2E.core.ps1",
    "tests/windows/test_legal_memory_language_layers.py",
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


def _run_py(args: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_audit_python(), *args],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _run_py_safe(args: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
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
        return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=str(exc))


def _run_ps1_safe(script_rel: str, *ps_args: str, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    script = REPO / script_rel.replace("/", os.sep)
    if not script.is_file():
        return subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr=f"script ontbreekt: {script}"
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
    try:
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
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            args=exc.cmd or [],
            returncode=1,
            stdout="",
            stderr=f"timeout after {exc.timeout}s",
        )
    except OSError as exc:
        return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=str(exc))


def _read(rel: str) -> str | None:
    path = REPO / rel
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def main() -> int:
    print("=== Legal Memory Language Layers E2E ===", flush=True)
    print(f"Repo: {REPO}", flush=True)

    missing = [p for p in REQUIRED_PATHS if not (REPO / p).is_file()]
    _step("repo artifacts", not missing, ", ".join(missing) if missing else f"{len(REQUIRED_PATHS)} paths")

    seed = _read("docs/templates/MEMORY_CANONICAL_SEED.md")
    _step(
        "seed taal-lagentabel + geen i18n",
        seed is not None
        and "Taal- en triggerlagen" in seed
        and "Geen i18n" in seed
        and "| Trust |" in seed
        and "| Legal triggers |" in seed,
    )
    if seed is not None:
        legal_block = seed.split("## legal USER.md entries", 1)[-1].split("## MEMORY.md entries", 1)[0]
        fence_count = legal_block.count("```")
        _step(
            "seed 3 legal USER fences",
            fence_count >= 6 and legal_block.count("Legal proactief (NL):") == 1,
            f"fences={fence_count}",
        )
    else:
        _step("seed 3 legal USER fences", False)

    _step(
        "seed EN trust separate section",
        seed is not None
        and "## USER.md entries" in seed
        and "J. demands absolute trust" in seed,
    )

    soul = _read("docs/templates/SOUL_LEGAL_DOMAIN.md")
    _step(
        "SOUL USER trust EN + triggers NL",
        soul is not None
        and "USER.md (trust EN + legal triggers NL)" in soul
        and "SOUL prevaleert" in soul,
    )

    arch = _read("docs/LEGAL_DOMAIN_ARCHITECTURE.md")
    _step(
        "architecture taal-triggerlagen 100%",
        arch is not None
        and "## Taal- en triggerlagen" in arch
        and "SOUL prevaleert" in arch
        and "USER.nl.md" in arch,
    )

    parity = _run_py_safe(
        [
            str(REPO / "scripts/rag_pipeline/verify_legal_lens_parity.py"),
            "--soul",
            "docs/templates/SOUL_LEGAL_DOMAIN.md",
        ],
        timeout=60,
    )
    _step(
        "lens parity template SOUL",
        parity.returncode == 0,
        (parity.stderr or parity.stdout or "")[-300:],
    )

    pt = _run_py_safe(
        [
            "-m",
            "pytest",
            "tests/windows/test_legal_memory_language_layers.py",
            "-q",
            "--tb=short",
        ],
        timeout=120,
    )
    _step(
        "pytest test_legal_memory_language_layers",
        pt.returncode == 0,
        (pt.stderr or pt.stdout or "")[-400:],
    )

    core = _run_ps1_safe(
        "audits/LegalMemoryLanguageLayersE2E.core.ps1",
        "-RepoRoot",
        str(REPO),
    )
    _step(
        "LegalMemoryLanguageLayersE2E.core.ps1",
        core.returncode == 0,
        (core.stderr or core.stdout or "")[-500:],
    )

    print("", flush=True)
    if FAILURES:
        print(f"=== LEGAL MEMORY LANGUAGE LAYERS E2E: {FAILURES} FAIL ===", flush=True)
        return 1
    print("=== LEGAL MEMORY LANGUAGE LAYERS E2E: ALL PASS ===", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
