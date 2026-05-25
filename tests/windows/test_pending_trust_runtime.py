"""Regressie: pending trust-runtime stamp + start-hook wiring."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PSM1 = REPO / "windows/scripts/TrustRuntimePending.psm1"


def _run_pending_ps(cmd: str) -> subprocess.CompletedProcess[str]:
    script = f"""
$ErrorActionPreference = 'Stop'
Import-Module '{PSM1}' -Force
{cmd}
"""
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_pending_trust_runtime_set_clear_test(tmp_path, monkeypatch):
    stamp_dir = tmp_path / "hermes"
    stamp_dir.mkdir()
    stamp = stamp_dir / "pending_trust_runtime.json"
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert PSM1.is_file()
    r = _run_pending_ps(
        "Set-PendingTrustRuntime -Source 'UPDATE_HERMES' -Reason 'test'; "
        "if (-not (Test-PendingTrustRuntime)) { exit 2 }; "
        "Clear-PendingTrustRuntime; "
        "if (Test-PendingTrustRuntime) { exit 3 }"
    )
    assert r.returncode == 0, r.stderr or r.stdout


def test_pending_trust_runtime_preserves_created_at(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    r = _run_pending_ps(
        "Set-PendingTrustRuntime -Source 'UPDATE_HERMES' -Reason 'first'; "
        "$t1 = (Get-PendingTrustRuntime).created_at; "
        "Start-Sleep -Milliseconds 50; "
        "Set-PendingTrustRuntime -Source 'UPDATE_HERMES' -Reason 'second'; "
        "$t2 = (Get-PendingTrustRuntime).created_at; "
        "if (-not $t1 -or $t1 -ne $t2) { exit 7 }"
    )
    assert r.returncode == 0, r.stderr or r.stdout


def test_pending_trust_runtime_attempt_counter(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    r = _run_pending_ps(
        "Set-PendingTrustRuntime -Source 'UPDATE_HERMES' -Reason 'test'; "
        "$a = Register-PendingTrustRuntimeAttempt; "
        "$b = Register-PendingTrustRuntimeAttempt; "
        "$c = Register-PendingTrustRuntimeAttempt; "
        "if ($a -ne 1 -or $b -ne 2 -or $c -ne 3) { exit 4 }; "
        "if (-not (Test-PendingTrustRuntimeMaxAttemptsReached)) { exit 5 }"
    )
    assert r.returncode == 0, r.stderr or r.stdout


def test_upstream_post_merge_wires_pending_trust():
    text = (REPO / "windows/scripts/Invoke-UpstreamPostMerge.ps1").read_text(encoding="utf-8")
    assert "TrustRuntimePending.psm1" in text
    assert "Set-PendingTrustRuntime" in text
    assert "Clear-PendingTrustRuntime" in text


def test_launch_hermes_wires_pending_trust_runtime():
    text = (REPO / "windows/launch_hermes.bat").read_text(encoding="utf-8")
    assert "launch_pending_trust_runtime.ps1" in text
    assert "HERMES_SKIP_PENDING_TRUST_ON_START" in text
    assert text.index("launch_institutional_runtime.ps1") < text.index(
        "launch_pending_trust_runtime.ps1"
    )


def test_clear_stale_pending_trust_runtime_file(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    stamp = tmp_path / "hermes" / "pending_trust_runtime.json"
    stamp.parent.mkdir(parents=True)
    stamp.write_text('{"status":"done","attempts":0}', encoding="utf-8")
    r = _run_pending_ps(
        "if (Test-PendingTrustRuntime) { exit 8 }; "
        "Clear-StalePendingTrustRuntimeFile; "
        "if (Test-Path -LiteralPath (Get-PendingTrustRuntimePath)) { exit 9 }"
    )
    assert r.returncode == 0, r.stderr or r.stdout


def test_trust_runtime_light_scripts_exist():
    assert (REPO / "windows/scripts/Invoke-TrustRuntimeLight.ps1").is_file()
    assert (REPO / "windows/scripts/launch_pending_trust_runtime.ps1").is_file()
    light = (REPO / "windows/scripts/Invoke-TrustRuntimeLight.ps1").read_text(encoding="utf-8")
    assert "Invoke-MemoryTrustPostSync.ps1" in light
    assert "Clear-PendingTrustRuntime" in light
