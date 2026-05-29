"""Regressie: codebase smoke audit runner + report emitter (smoke vs release-gate)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_repo_codebase_smoke_runner_wired():
    ps1 = REPO / "windows" / "audits" / "RUN_CODEBASE_SMOKE_AUDIT.ps1"
    bat = REPO / "windows" / "audits" / "RUN_CODEBASE_SMOKE_AUDIT.bat"
    e2e = REPO / "windows" / "audits" / "RUN_CODEBASE_SMOKE_E2E.ps1"
    e2e_bat = REPO / "windows" / "audits" / "RUN_CODEBASE_SMOKE_E2E.bat"
    assert ps1.is_file() and bat.is_file() and e2e.is_file() and e2e_bat.is_file()
    text = ps1.read_text(encoding="utf-8")
    assert "verify_windows_script_chain.ps1" in text
    assert "emit_codebase_smoke_report.py" in text
    assert "test_tui_gateway_server.py" in text
    assert "IncludeTuiGatewayPytest" in text
    e2e_text = e2e.read_text(encoding="utf-8")
    assert "RUN_CODEBASE_SMOKE_AUDIT.ps1" in e2e_text
    assert "CODEBASE_SMOKE_E2E_REPORT_" in e2e_text
    audits = (REPO / "windows" / "audits" / "RUN_AUDITS.ps1").read_text(encoding="utf-8")
    assert "IncludeCodebaseSmoke" in audits
    assert "IncludeCodebaseSmokeE2E" in audits


def test_repo_codebase_audit_docs_exist():
    assert (REPO / "docs/CODEBASE_AUDIT_EVIDENCE.md").is_file()
    assert (REPO / "docs/templates/CODEBASE_AUDIT_REPORT.md").is_file()
    assert (REPO / "docs/templates/CODEBASE_AUDIT_SMOKE_PROMPT.md").is_file()
    assert (REPO / "docs/templates/SOUL_SHARED_CODEBASE_AUDIT.md").is_file()
    assert (REPO / "scripts/emit_codebase_smoke_report.py").is_file()
    assert (REPO / "windows/scripts/sync_soul_codebase_audit_snippet.ps1").is_file()
    anatomy = (REPO / "windows/scripts/sync_soul_anatomy_snippets.ps1").read_text(encoding="utf-8")
    assert "sync_soul_codebase_audit_snippet.ps1" in anatomy


def test_post_git_pull_and_update_optional_smoke_flags():
    helper = REPO / "windows/scripts/Invoke-PostSyncCodebaseSmoke.ps1"
    assert helper.is_file()
    post_git = (REPO / "windows/POST_GIT_PULL.bat").read_text(encoding="utf-8")
    assert "-IncludeCodebaseSmokeE2E" in post_git
    assert "-IncludeCodebaseSmoke" in post_git
    assert "Invoke-PostSyncCodebaseSmoke.ps1" in post_git
    assert "VERIFY_WINDOWS_CHAIN.bat" not in post_git
    upstream = (REPO / "windows/upstream_sync.ps1").read_text(encoding="utf-8")
    post = (REPO / "windows/scripts/Invoke-UpstreamPostMerge.ps1").read_text(encoding="utf-8")
    assert "verify_windows_script_chain.ps1" in post
    assert "IncludeCodebaseSmokeE2E" in upstream
    assert "IncludeCodebaseSmoke" in upstream
    assert "Invoke-UpstreamPostMerge.ps1" in upstream
    assert "Invoke-PostSyncCodebaseSmoke.ps1" in post
    assert "Register-PendingTrustRuntimeRequired" in post
    assert "Clear-PendingTrustRuntime" in post
    update = (REPO / "windows/UPDATE_HERMES.bat").read_text(encoding="utf-8")
    assert "-IncludeCodebaseSmokeE2E" in update
    assert "-IncludeCodebaseSmoke" in update


def test_emit_codebase_smoke_report_minimal():
    emitter = REPO / "scripts" / "emit_codebase_smoke_report.py"
    payload = {
        "started": "2026-05-24T12:00:00",
        "release_gate_run": False,
        "steps": [
            {
                "timestamp": "12:00:01",
                "name": "pytest_windows_critical",
                "tier": "E2",
                "source": "tests/windows/test_critical_windows_scripts.py",
                "exit": 0,
                "detail": "8 passed",
                "skipped": False,
            }
        ],
        "warnings": [],
    }
    log = REPO / "windows" / "audits" / "_pytest_codebase_smoke_steplog.json"
    out = REPO / "windows" / "audits" / "_pytest_codebase_smoke_report.md"
    try:
        log.write_text(json.dumps(payload), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(emitter), str(log), "-o", str(out)],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr or proc.stdout
        text = out.read_text(encoding="utf-8")
        assert "Release-gate in deze run:" in text
        assert "geen E3" in text.lower() or "Nee" in text
        assert "[E2]" in text
    finally:
        log.unlink(missing_ok=True)
        out.unlink(missing_ok=True)
