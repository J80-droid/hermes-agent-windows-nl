#!/usr/bin/env python3
"""E2E: post-pull automatisering (PULL_HERMES, POST_GIT_PULL, relaunch, trust, CLI notice).

Geen live Windows Terminal-start, geen git pull, geen kill van actieve Hermes-sessies.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FAILURES = 0
STEP = 0

PS1_SCRIPTS = (
    "windows/scripts/Invoke-HermesPostPullRelaunch.ps1",
    "windows/scripts/Invoke-PostGitPullTrustOutcome.ps1",
    "windows/scripts/Invoke-PostGitPullInstitutionalVerify.ps1",
    "windows/stop_other_hermes_processes.ps1",
)


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] P{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] P{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8", errors="replace")


def _audit_python() -> str:
    if os.environ.get("HERMES_AUDIT_PYTHON") and Path(os.environ["HERMES_AUDIT_PYTHON"]).is_file():
        return os.environ["HERMES_AUDIT_PYTHON"]
    candidates = [
        Path(os.environ.get("USERPROFILE", "")) / "miniconda3/envs/hermes-env/python.exe",
        Path(sys.executable),
    ]
    for c in candidates:
        if c and c.is_file():
            return str(c)
    return sys.executable


def _powershell_file(script: Path, *args: str, env: dict[str, str] | None = None, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), *args]
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.run(
        cmd,
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=run_env,
    )


def _parse_ps1(path: Path) -> bool:
    esc = str(path).replace("'", "''")
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                f"$e=$null; $null=[System.Management.Automation.Language.Parser]::ParseFile('{esc}', "
                "[ref]$null, [ref]$e); if ($e) {{ $e | Out-String; exit 1 }} else {{ exit 0 }}"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO),
    )
    return proc.returncode == 0


def test_p1_repo_artifacts() -> None:
    required = [
        "PULL_HERMES.bat",
        "windows/POST_GIT_PULL.bat",
        "windows/RAG_PIPELINE.bat",
        "windows/scripts/Invoke-HermesPostPullRelaunch.ps1",
        "windows/scripts/Invoke-PostGitPullTrustOutcome.ps1",
        "windows/scripts/Invoke-PostGitPullInstitutionalVerify.ps1",
        "windows/scripts/Get-RagSourceReadiness.ps1",
        "windows/stop_other_hermes_processes.ps1",
        "windows/scripts/Invoke-UpstreamPostMerge.ps1",
        "cli.py",
        "tests/windows/test_post_git_pull_args.py",
        "tests/hermes_cli/test_cli_post_sync_new_chat.py",
        "audits/PostGitPullAutomationE2E.harness.py",
        "audits/RUN_POST_GIT_PULL_AUTOMATION_E2E.bat",
    ]
    missing = [r for r in required if not (REPO / r).is_file()]
    _step("repo-artefacten post-pull keten", not missing, ", ".join(missing) or "OK")


def test_p2_post_git_pull_wiring() -> None:
    bat = _read("windows/POST_GIT_PULL.bat")
    checks = [
        "-SkipRelaunch" in bat,
        "-RelaunchHermes" in bat,
        "-Full" in bat,
        "-IncludeInstitutionalVerify" in bat,
        "-IncludeRagPipeline" in bat,
        "MERGE_HEAD" in bat,
        "Invoke-HermesPostPullRelaunch.ps1" in bat,
        "Invoke-PostGitPullTrustOutcome.ps1" in bat,
        "apply_institutional_runtime.ps1" in bat,
        "-KeepPid $PID" in bat,
        "geen relaunch" in bat.lower() or "geen relaunch" in bat,
    ]
    _step("POST_GIT_PULL.bat flags en relaunch/trust wiring", all(checks))


def test_p3_pull_hermes_chain() -> None:
    pull = _read("PULL_HERMES.bat")
    ok = (
        "git pull" in pull
        and "POST_GIT_PULL.bat" in pull
        and "which_hermes_repo.ps1" in pull
    )
    _step("PULL_HERMES.bat keten", ok)


def test_p4_relaunch_script_contract() -> None:
    ps1 = _read("windows/scripts/Invoke-HermesPostPullRelaunch.ps1")
    checks = [
        "Invoke-HermesPipEditableInstall" in ps1,
        "LASTEXITCODE -ne 0" in ps1,
        "Clear-HermesUpdateCheckCache" in ps1,
        "HERMES_AUTO_NEW_AFTER_SYNC" in ps1,
        "HERMES_SKIP_RELAUNCH_AFTER_PULL" in ps1,
        "try {" in ps1 and "Resolve-Path" in ps1,
        "KeepPid.Count -eq 0" in ps1,
        "Invoke-HermesLaunchInWindowsTerminal" in ps1,
    ]
    _step("Invoke-HermesPostPullRelaunch.ps1 contract", all(checks))


def test_p5_stop_script_contract() -> None:
    stop = _read("windows/stop_other_hermes_processes.ps1")
    checks = [
        "hermes_cli\\.main" in stop,
        "Name = 'python.exe' OR Name = 'pythonw.exe'" in stop,
        "KeepPid" in stop,
        "KeepPid.Count -eq 0" in stop,
        "$PID" in stop,
        "$keepId" in stop,
    ]
    _step("stop_other_hermes_processes.ps1 WMI + KeepPid", all(checks))


def test_p6_upstream_post_merge_relaunch() -> None:
    merge = _read("windows/scripts/Invoke-UpstreamPostMerge.ps1")
    ok = (
        "Invoke-HermesPostPullRelaunch.ps1" in merge
        and "-KeepPid $PID" in merge
        and "$LASTEXITCODE -ne 0" in merge
    )
    _step("Invoke-UpstreamPostMerge relaunch + exitcode", ok)


def test_p7_powershell_parse() -> None:
    bad: list[str] = []
    for rel in PS1_SCRIPTS:
        path = REPO / rel
        if not _parse_ps1(path):
            bad.append(rel)
    _step("PowerShell parse post-pull scripts", not bad, ", ".join(bad) or "OK")


def test_p8_skip_relaunch_env() -> None:
    relaunch = REPO / "windows/scripts/Invoke-HermesPostPullRelaunch.ps1"
    proc = _powershell_file(
        relaunch,
        "-RepoRoot",
        str(REPO),
        env={"HERMES_SKIP_RELAUNCH_AFTER_PULL": "1"},
        timeout=90,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == 0 and "overgeslagen" in out.lower()
    _step("skip relaunch via HERMES_SKIP_RELAUNCH_AFTER_PULL", ok, f"exit={proc.returncode}")


def test_p9_invalid_repo_root() -> None:
    relaunch = REPO / "windows/scripts/Invoke-HermesPostPullRelaunch.ps1"
    missing = str(REPO / "_e2e_post_pull_bogus_nested" / "no_such_dir")
    env = os.environ.copy()
    env["HERMES_SKIP_RELAUNCH_AFTER_PULL"] = "0"
    proc = _powershell_file(
        relaunch,
        "-RepoRoot",
        missing,
        "-Quiet",
        env=env,
        timeout=60,
    )
    ok = proc.returncode != 0
    _step("ongeldig RepoRoot (Resolve-Path) exit non-zero", ok, f"exit={proc.returncode}")


def test_p10_trust_outcome_success() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        la = Path(tmp) / "LocalAppData"
        la.mkdir()
        pending = la / "hermes" / "pending_trust_runtime.json"
        pending.parent.mkdir(parents=True)
        pending.write_text(
            json.dumps({"status": "required", "source": "TEST"}),
            encoding="utf-8",
        )
        trust_ps1 = REPO / "windows/scripts/Invoke-PostGitPullTrustOutcome.ps1"
        proc = _powershell_file(
            trust_ps1,
            "-TrustExitCode",
            "0",
            "-RepoRoot",
            str(REPO),
            env={"LOCALAPPDATA": str(la)},
            timeout=60,
        )
        ok = proc.returncode == 0 and not pending.exists()
    _step("trust outcome success wist pending", ok, f"exit={proc.returncode}")


def test_p11_trust_outcome_failure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        la = Path(tmp) / "LocalAppData"
        la.mkdir()
        pending = la / "hermes" / "pending_trust_runtime.json"
        trust_ps1 = REPO / "windows/scripts/Invoke-PostGitPullTrustOutcome.ps1"
        proc = _powershell_file(
            trust_ps1,
            "-TrustExitCode",
            "5",
            "-RepoRoot",
            str(REPO),
            env={"LOCALAPPDATA": str(la)},
            timeout=60,
        )
        data = {}
        if pending.is_file():
            data = json.loads(pending.read_text(encoding="utf-8"))
        ok = (
            proc.returncode == 5
            and data.get("status") == "required"
            and data.get("source") == "POST_GIT_PULL"
        )
    _step("trust outcome failure registreert pending", ok, f"exit={proc.returncode}")


def test_p12_rag_readiness_empty() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        rag_ps1 = REPO / "windows/scripts/Get-RagSourceReadiness.ps1"
        proc = _powershell_file(
            rag_ps1,
            "-RepoRoot",
            str(REPO),
            env={"USERPROFILE": tmp},
            timeout=60,
        )
        ok = proc.returncode == 2
    _step("RAG readiness zonder raw_source_files exit 2", ok, f"exit={proc.returncode}")


def test_p13_pytest_subset() -> None:
    py = _audit_python()
    proc = subprocess.run(
        [
            py,
            "-m",
            "pytest",
            "tests/windows/test_post_git_pull_args.py",
            "tests/windows/test_stop_hermes_cli_processes.py",
            "tests/hermes_cli/test_cli_post_sync_new_chat.py",
            "-q",
            "--tb=line",
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip(), file=sys.stderr)
    _step("pytest subset post-pull", proc.returncode == 0, f"exit={proc.returncode}")


def test_p14_cli_init_hook() -> None:
    cli = _read("cli.py")
    ok = "_apply_post_sync_new_chat_notice" in cli and "self._apply_post_sync_new_chat_notice()" in cli
    _step("cli _init_agent roept post-sync notice aan", ok)


def main() -> int:
    print("=== Post-git-pull automatisering E2E ===", flush=True)
    test_p1_repo_artifacts()
    test_p2_post_git_pull_wiring()
    test_p3_pull_hermes_chain()
    test_p4_relaunch_script_contract()
    test_p5_stop_script_contract()
    test_p6_upstream_post_merge_relaunch()
    test_p7_powershell_parse()
    test_p8_skip_relaunch_env()
    test_p9_invalid_repo_root()
    test_p10_trust_outcome_success()
    test_p11_trust_outcome_failure()
    test_p12_rag_readiness_empty()
    test_p13_pytest_subset()
    test_p14_cli_init_hook()

    if FAILURES:
        print(f"\n{FAILURES} failure(s)", file=sys.stderr, flush=True)
        return 1
    print("\nALL PASS", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
