"""Unit tests: pending trust-runtime stamp + start-hook (geïsoleerd, geen live sync/API)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PSM1 = REPO / "windows/scripts/TrustRuntimePending.psm1"
LAUNCHER = REPO / "windows/scripts/launch_pending_trust_runtime.ps1"
LIGHT = REPO / "windows/scripts/Invoke-TrustRuntimeLight.ps1"


def _run_pending_ps(cmd: str, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Voer PowerShell-modulecommando's uit tegen geïsoleerde LOCALAPPDATA."""
    script = f"""
$ErrorActionPreference = 'Stop'
Import-Module '{PSM1}' -Force
{cmd}
"""
    run_env = None
    if env is not None:
        import os

        run_env = os.environ.copy()
        run_env.update(env)
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=run_env,
    )


def _run_launcher_ps(
    args: str = "",
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Launcher zonder echte memory/trust-keten (dry-run of geen pending)."""
    script = f"""
$ErrorActionPreference = 'Stop'
& '{LAUNCHER}' -RepoRoot '{REPO}' {args}
"""
    run_env = None
    if env is not None:
        import os

        run_env = os.environ.copy()
        run_env.update(env)
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env=run_env,
    )


def _stamp_file(localappdata: Path) -> Path:
    return localappdata / "hermes" / "pending_trust_runtime.json"


def _read_stamp(localappdata: Path) -> dict | None:
    path = _stamp_file(localappdata)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def isolated_localappdata(tmp_path, monkeypatch):
    """Mock runtime-home: geen echte %LOCALAPPDATA%\\hermes."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    return tmp_path


# --- TrustRuntimePending.psm1 (module) ---


class TestTrustRuntimePendingHappyPath:
    def test_set_clear_roundtrip(self, isolated_localappdata):
        r = _run_pending_ps(
            "Register-PendingTrustRuntimeRequired -Source 'UPDATE_HERMES' -Reason 'unit'; "
            "if (-not (Test-PendingTrustRuntime)) { exit 2 }; "
            "Clear-PendingTrustRuntime; "
            "if (Test-PendingTrustRuntime) { exit 3 }"
        )
        assert r.returncode == 0, r.stderr or r.stdout

    def test_stamp_payload_fields(self, isolated_localappdata):
        repo = r"D:\fake\repo"
        _run_pending_ps(
            f"Register-PendingTrustRuntimeRequired -Source 'POST_GIT_PULL' -Reason 'trust fail' -RepoRoot '{repo}'"
        )
        data = _read_stamp(isolated_localappdata)
        assert data is not None
        assert data["status"] == "required"
        assert data["source"] == "POST_GIT_PULL"
        assert data["reason"] == "trust fail"
        assert data["repo_root"] == repo
        assert data["attempts"] == 0
        assert data["created_at"]

    def test_preserves_created_at_on_refresh(self, isolated_localappdata):
        r = _run_pending_ps(
            "Register-PendingTrustRuntimeRequired -Source 'UPDATE_HERMES' -Reason 'first'; "
            "$t1 = (Get-PendingTrustRuntime).created_at; "
            "Start-Sleep -Milliseconds 50; "
            "Register-PendingTrustRuntimeRequired -Source 'UPDATE_HERMES' -Reason 'second'; "
            "$t2 = (Get-PendingTrustRuntime).created_at; "
            "if (-not $t1 -or $t1 -ne $t2) { exit 7 }"
        )
        assert r.returncode == 0, r.stderr or r.stdout

    def test_register_increments_and_max_threshold(self, isolated_localappdata):
        r = _run_pending_ps(
            "Register-PendingTrustRuntimeRequired -Source 'UPDATE_HERMES' -Reason 'test'; "
            "$a = Register-PendingTrustRuntimeAttempt; "
            "$b = Register-PendingTrustRuntimeAttempt; "
            "$c = Register-PendingTrustRuntimeAttempt; "
            "if ($a -ne 1 -or $b -ne 2 -or $c -ne 3) { exit 4 }; "
            "if (-not (Test-PendingTrustRuntimeMaxAttemptsReached)) { exit 5 }"
        )
        assert r.returncode == 0, r.stderr or r.stdout

    def test_creates_hermes_directory_when_missing(self, isolated_localappdata):
        assert not (isolated_localappdata / "hermes").exists()
        r = _run_pending_ps("Register-PendingTrustRuntimeRequired -Reason 'mkdir test'")
        assert r.returncode == 0, r.stderr or r.stdout
        assert _stamp_file(isolated_localappdata).is_file()


class TestTrustRuntimePendingEdgeCases:
    def test_no_stamp_means_not_pending(self, isolated_localappdata):
        r = _run_pending_ps(
            "if (Test-PendingTrustRuntime) { exit 1 }; "
            "if (Get-PendingTrustRuntime) { exit 2 }"
        )
        assert r.returncode == 0, r.stderr or r.stdout

    def test_wrong_status_not_pending(self, isolated_localappdata):
        _stamp_file(isolated_localappdata).parent.mkdir(parents=True, exist_ok=True)
        _stamp_file(isolated_localappdata).write_text(
            json.dumps({"status": "done", "attempts": 0}), encoding="utf-8"
        )
        r = _run_pending_ps("if (Test-PendingTrustRuntime) { exit 3 }")
        assert r.returncode == 0, r.stderr or r.stdout

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "   ",
            "{not-json",
            "[]",
            '{"status":"unknown"}',
        ],
    )
    def test_invalid_stamp_content_not_pending(self, isolated_localappdata, raw: str):
        path = _stamp_file(isolated_localappdata)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw, encoding="utf-8")
        r = _run_pending_ps("if (Test-PendingTrustRuntime) { exit 4 }")
        assert r.returncode == 0, r.stderr or r.stdout

    def test_minimal_required_json_is_pending(self, isolated_localappdata):
        _stamp_file(isolated_localappdata).parent.mkdir(parents=True, exist_ok=True)
        _stamp_file(isolated_localappdata).write_text('{"status":"required"}', encoding="utf-8")
        r = _run_pending_ps(
            "if (-not (Test-PendingTrustRuntime)) { exit 12 }; "
            "$n = (Get-PendingTrustRuntime).attempts; if ($n -ne 0) { exit 13 }"
        )
        assert r.returncode == 0, r.stderr or r.stdout

    @pytest.mark.parametrize(
        ("attempts_raw", "expected"),
        [
            ("abc", 0),
            ("", 0),
            (-1, 0),
            ("2", 2),
            (99, 99),
        ],
    )
    def test_attempts_coercion(self, isolated_localappdata, attempts_raw, expected: int):
        _stamp_file(isolated_localappdata).parent.mkdir(parents=True, exist_ok=True)
        _stamp_file(isolated_localappdata).write_text(
            json.dumps({"status": "required", "attempts": attempts_raw}),
            encoding="utf-8",
        )
        r = _run_pending_ps(
            "$n = (Get-PendingTrustRuntime).attempts; "
            f"if ($n -ne {expected}) {{ exit 5 }}"
        )
        assert r.returncode == 0, r.stderr or r.stdout

    def test_max_attempts_false_below_threshold(self, isolated_localappdata):
        _run_pending_ps("Register-PendingTrustRuntimeRequired -Reason 'low attempts'")
        _run_pending_ps("Register-PendingTrustRuntimeAttempt | Out-Null")
        r = _run_pending_ps(
            "if (Test-PendingTrustRuntimeMaxAttemptsReached) { exit 6 }"
        )
        assert r.returncode == 0, r.stderr or r.stdout

    def test_register_without_pending_returns_zero(self, isolated_localappdata):
        r = _run_pending_ps(
            "$n = Register-PendingTrustRuntimeAttempt; if ($n -ne 0) { exit 7 }"
        )
        assert r.returncode == 0, r.stderr or r.stdout

    def test_register_preserves_source_and_reason(self, isolated_localappdata):
        _run_pending_ps(
            "Register-PendingTrustRuntimeRequired -Source 'UPDATE_HERMES' -Reason 'keep me' -RepoRoot 'C:\\r'"
        )
        _run_pending_ps("Register-PendingTrustRuntimeAttempt -RepoRoot 'C:\\r2' | Out-Null")
        data = _read_stamp(isolated_localappdata)
        assert data["source"] == "UPDATE_HERMES"
        assert data["reason"] == "keep me"
        assert data["repo_root"] == "C:\\r2"
        assert data["attempts"] == 1

    def test_clear_stale_removes_non_required(self, isolated_localappdata):
        _stamp_file(isolated_localappdata).parent.mkdir(parents=True, exist_ok=True)
        _stamp_file(isolated_localappdata).write_text(
            '{"status":"done","attempts":0}', encoding="utf-8"
        )
        r = _run_pending_ps(
            "Clear-StalePendingTrustRuntimeFile; "
            "if (Test-Path -LiteralPath (Get-PendingTrustRuntimePath)) { exit 8 }"
        )
        assert r.returncode == 0, r.stderr or r.stdout

    def test_clear_stale_keeps_valid_required(self, isolated_localappdata):
        _run_pending_ps("Register-PendingTrustRuntimeRequired -Reason 'valid'")
        r = _run_pending_ps(
            "Clear-StalePendingTrustRuntimeFile; "
            "if (-not (Test-PendingTrustRuntime)) { exit 9 }"
        )
        assert r.returncode == 0, r.stderr or r.stdout

    def test_clear_idempotent_when_missing(self, isolated_localappdata):
        r = _run_pending_ps(
            "Clear-PendingTrustRuntime; Clear-PendingTrustRuntime; "
            "if (Test-Path -LiteralPath (Get-PendingTrustRuntimePath)) { exit 10 }"
        )
        assert r.returncode == 0, r.stderr or r.stdout

    def test_path_under_isolated_localappdata(self, isolated_localappdata):
        r = _run_pending_ps(
            f"$p = Get-PendingTrustRuntimePath; "
            f"if ($p -notlike '*{isolated_localappdata.name}*') {{ exit 11 }}"
        )
        assert r.returncode == 0, r.stderr or r.stdout


class TestLaunchPendingTrustRuntime:
    """Launcher: mock via geïsoleerde LOCALAPPDATA + E2E dry-run (geen SYNC_TRUST_RUNTIME)."""

    def test_exit_zero_without_pending(self, isolated_localappdata):
        r = _run_launcher_ps(env={"LOCALAPPDATA": str(isolated_localappdata)})
        assert r.returncode == 0, r.stderr or r.stdout
        assert _stamp_file(isolated_localappdata).exists() is False

    def test_skip_flag_keeps_pending(self, isolated_localappdata):
        _run_pending_ps(
            "Register-PendingTrustRuntimeRequired -Reason 'skip test'",
            env={"LOCALAPPDATA": str(isolated_localappdata)},
        )
        r = _run_launcher_ps(
            env={
                "LOCALAPPDATA": str(isolated_localappdata),
                "HERMES_SKIP_PENDING_TRUST_ON_START": "1",
            }
        )
        assert r.returncode == 0, r.stderr or r.stdout
        assert _read_stamp(isolated_localappdata) is not None
        assert _read_stamp(isolated_localappdata)["attempts"] == 0

    def test_dry_run_clears_pending_without_light_chain(self, isolated_localappdata):
        _run_pending_ps(
            "Register-PendingTrustRuntimeRequired -Reason 'dry'",
            env={"LOCALAPPDATA": str(isolated_localappdata)},
        )
        r = _run_launcher_ps(
            env={
                "LOCALAPPDATA": str(isolated_localappdata),
                "HERMES_PENDING_TRUST_E2E_DRY_RUN": "1",
                "HERMES_REPO_ROOT": str(REPO),
            }
        )
        assert r.returncode == 0, r.stderr or r.stdout
        assert _read_stamp(isolated_localappdata) is None

    def test_max_attempts_does_not_increment_fourth_launch(self, isolated_localappdata):
        env = {"LOCALAPPDATA": str(isolated_localappdata), "HERMES_REPO_ROOT": str(REPO)}
        _run_pending_ps(
            "Register-PendingTrustRuntimeRequired -Reason 'max'; "
            "Register-PendingTrustRuntimeAttempt | Out-Null; "
            "Register-PendingTrustRuntimeAttempt | Out-Null; "
            "Register-PendingTrustRuntimeAttempt | Out-Null",
            env=env,
        )
        before = _read_stamp(isolated_localappdata)["attempts"]
        r = _run_launcher_ps(env=env)
        after = _read_stamp(isolated_localappdata)
        assert r.returncode == 0, r.stderr or r.stdout
        assert before == 3
        assert after is not None
        assert after["attempts"] == 3

    def test_stale_file_removed_before_pending_check(self, isolated_localappdata):
        path = _stamp_file(isolated_localappdata)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"status":"obsolete"}', encoding="utf-8")
        r = _run_launcher_ps(env={"LOCALAPPDATA": str(isolated_localappdata)})
        assert r.returncode == 0, r.stderr or r.stdout
        assert not path.exists()


class TestLaunchPendingTrustRuntimeNegative:
    def test_missing_light_script_exits_nonzero(self, isolated_localappdata, tmp_path, monkeypatch):
        """Simuleer ontbrekende Invoke-TrustRuntimeLight zonder repo te muteren."""
        fake_scripts = tmp_path / "scripts"
        fake_scripts.mkdir()
        fake_launcher = fake_scripts / "launch_pending_trust_runtime.ps1"
        fake_module = fake_scripts / "TrustRuntimePending.psm1"
        fake_module.write_text(PSM1.read_text(encoding="utf-8"), encoding="utf-8")
        fake_launcher.write_text(
            (REPO / "windows/scripts/launch_pending_trust_runtime.ps1")
            .read_text(encoding="utf-8")
            .replace(
                "Join-Path $PSScriptRoot 'Invoke-TrustRuntimeLight.ps1'",
                "Join-Path $PSScriptRoot 'MISSING_Invoke-TrustRuntimeLight.ps1'",
            ),
            encoding="utf-8",
        )
        _run_pending_ps(
            "Register-PendingTrustRuntimeRequired -Reason 'neg'",
            env={"LOCALAPPDATA": str(isolated_localappdata)},
        )
        script = f"""
$ErrorActionPreference = 'Stop'
& '{fake_launcher}' -RepoRoot '{REPO}'
"""
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
            env={**__import__("os").environ, "LOCALAPPDATA": str(isolated_localappdata)},
        )
        assert proc.returncode == 1, proc.stderr or proc.stdout


# --- Repo wiring (statisch, geen runtime) ---


class TestPendingTrustRepoWiring:
    def test_upstream_post_merge_wires_pending_trust(self):
        text = (REPO / "windows/scripts/Invoke-UpstreamPostMerge.ps1").read_text(
            encoding="utf-8"
        )
        assert "TrustRuntimePending.psm1" in text
        assert "Register-PendingTrustRuntimeRequired" in text
        assert "Clear-PendingTrustRuntime" in text

    def test_launch_hermes_wires_pending_trust_runtime(self):
        launch = (REPO / "windows/launch_hermes.bat").read_text(encoding="utf-8")
        launch_ps1 = (REPO / "windows/scripts/launch_hermes.ps1").read_text(encoding="utf-8")
        orch = (REPO / "windows/scripts/launch_pre_chat_orchestrator.ps1").read_text(
            encoding="utf-8"
        )
        assert "launch_hermes.ps1" in launch
        assert "launch_pre_chat_orchestrator.ps1" in launch_ps1
        assert "launch_trust_runtime_sync.ps1" in orch
        assert "launch_pending_trust_runtime.ps1" in orch
        assert "HERMES_SKIP_PENDING_TRUST_ON_START" in orch
        assert orch.index("launch_institutional_runtime.ps1") < orch.index(
            "launch_pending_trust_runtime.ps1"
        )

    def test_trust_runtime_light_scripts_exist(self):
        assert LIGHT.is_file()
        assert LAUNCHER.is_file()
        light = LIGHT.read_text(encoding="utf-8")
        assert "Invoke-MemoryTrustPostSync.ps1" in light
        assert "Clear-PendingTrustRuntime" in light
        assert "SkipProductionGate" in light

    def test_launcher_has_dry_run_hook(self):
        text = LAUNCHER.read_text(encoding="utf-8")
        assert "HERMES_PENDING_TRUST_E2E_DRY_RUN" in text

    def test_e2e_runner_exists(self):
        assert (REPO / "windows/audits/RUN_PENDING_TRUST_START_E2E.ps1").is_file()
        assert (REPO / "windows/audits/PendingTrustStartE2E.core.ps1").is_file()
