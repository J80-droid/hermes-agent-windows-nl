"""Unit tests: TrustRuntimeSync.psm1 (stamp/drift; geïsoleerd, geen live sync/API)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PSM1 = REPO / "windows/scripts/TrustRuntimeSync.psm1"
UNIT_PS1 = REPO / "windows/tests/TrustRuntimeSync.Unit.Tests.ps1"


def _run_sync_ps(cmd: str, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Voer TrustRuntimeSync-modulecommando's uit tegen geïsoleerde LOCALAPPDATA."""
    script = f"""
$ErrorActionPreference = 'Stop'
Import-Module '{PSM1}' -Force
{cmd}
"""
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
        env=run_env,
    )


@pytest.fixture
def isolated_localappdata(tmp_path, monkeypatch):
    """Mock runtime-home: geen echte %LOCALAPPDATA%\\hermes."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    return tmp_path


class TestTrustRuntimeSyncHappyPath:
    def test_stamp_roundtrip_custom_path(self, isolated_localappdata):
        stamp = isolated_localappdata / "hermes" / "custom.stamp"
        r = _run_sync_ps(
            f"$p = '{stamp}'; "
            "New-Item -ItemType Directory -Path (Split-Path $p) -Force | Out-Null; "
            "Set-Content -LiteralPath (Join-Path (Split-Path $p) 'config.yaml') -Value 'x'; "
            "Set-TrustRuntimeSyncStamp -StampPath $p; "
            "if (-not (Test-Path -LiteralPath $p)) { exit 2 }; "
            "if (-not ((Get-Content -LiteralPath $p -Raw).Trim())) { exit 3 }"
        )
        assert r.returncode == 0, r.stderr or r.stdout
        assert stamp.is_file()

    def test_watch_paths_include_enforce_script(self, isolated_localappdata):
        r = _run_sync_ps(
            f"$w = Get-TrustRuntimeWatchPaths -RepoRoot '{REPO}'; "
            "if (-not ($w | Where-Object { $_ -match 'enforce_profile_memory_char_limits' })) { exit 2 }"
        )
        assert r.returncode == 0, r.stderr or r.stdout

    def test_profile_complete_all_domains(self, isolated_localappdata):
        profiles = (
            "core", "legal", "academics", "operations", "trading", "gaming",
            "philosophy", "logistics", "ventures", "ict", "security", "dev", "data", "creative",
        )
        setup = isolated_localappdata / "hermes"
        (setup / "profiles").mkdir(parents=True, exist_ok=True)
        (setup / "config.yaml").write_text("model: test\n", encoding="utf-8")
        for name in profiles:
            mem = setup / "profiles" / name / "memories"
            mem.mkdir(parents=True, exist_ok=True)
            (setup / "profiles" / name / "config.yaml").write_text(
                "memory:\n  memory_char_limit: 4000\n  user_char_limit: 1800\n",
                encoding="utf-8",
            )
            (mem / "MEMORY.md").write_text("## stub\nok\n", encoding="utf-8")
            (mem / "USER.md").write_text("## user\nok\n", encoding="utf-8")
        r = _run_sync_ps(
            f"if (-not (Test-TrustRuntimeProfileMemoriesComplete -HermesRoot '{setup}')) {{ exit 2 }}"
        )
        assert r.returncode == 0, r.stderr or r.stdout


class TestTrustRuntimeSyncEdgeCases:
    def test_force_and_env_override(self, isolated_localappdata):
        r = _run_sync_ps(
            f"if (-not (Test-TrustRuntimeSyncNeeded -RepoRoot '{REPO}' -Force)) {{ exit 2 }}; "
            "$env:HERMES_FORCE_TRUST_SYNC='1'; "
            f"if (-not (Test-TrustRuntimeSyncNeeded -RepoRoot '{REPO}')) {{ exit 3 }}"
        )
        assert r.returncode == 0, r.stderr or r.stdout

    def test_incomplete_profiles_need_sync(self, isolated_localappdata):
        root = isolated_localappdata / "hermes"
        root.mkdir()
        (root / "config.yaml").write_text("model: x\n", encoding="utf-8")
        r = _run_sync_ps(
            f"if (-not (Test-TrustRuntimeSyncNeeded -RepoRoot '{REPO}')) {{ exit 2 }}; "
            f"if (Test-TrustRuntimeProfileMemoriesComplete -HermesRoot '{root}') {{ exit 3 }}"
        )
        assert r.returncode == 0, r.stderr or r.stdout

    def test_over_memory_not_clean(self, isolated_localappdata):
        root = isolated_localappdata / "hermes"
        mem_dir = root / "profiles" / "core" / "memories"
        mem_dir.mkdir(parents=True)
        (root / "config.yaml").write_text("model: x\n", encoding="utf-8")
        (root / "profiles" / "core" / "config.yaml").write_text(
            "memory:\n  memory_char_limit: 100\n  user_char_limit: 1800\n",
            encoding="utf-8",
        )
        (mem_dir / "MEMORY.md").write_text("x" * 500, encoding="utf-8")
        (mem_dir / "USER.md").write_text("ok\n", encoding="utf-8")
        r = _run_sync_ps(
            f"if (Test-TrustRuntimeMemoryAuditClean -HermesRoot '{root}') {{ exit 2 }}"
        )
        assert r.returncode == 0, r.stderr or r.stdout

    def test_missing_stamp_needs_sync(self, isolated_localappdata):
        root = isolated_localappdata / "hermes"
        root.mkdir()
        (root / "config.yaml").write_text("model: x\n", encoding="utf-8")
        stamp = root / "trust_runtime_sync.stamp"
        r = _run_sync_ps(
            f"$stamp = '{stamp}'; "
            f"if (-not (Test-TrustRuntimeSyncNeeded -RepoRoot '{REPO}' -StampPath $stamp)) {{ exit 2 }}"
        )
        assert r.returncode == 0, r.stderr or r.stdout

    def test_invalid_repo_root_raises(self, isolated_localappdata):
        r = _run_sync_ps(
            "try { "
            "[void](Get-TrustRuntimeWatchPaths -RepoRoot 'Z:\\__hermes_no_such_repo__'); "
            "exit 2 "
            "} catch { exit 0 }"
        )
        assert r.returncode == 0, r.stderr or r.stdout


def test_powershell_unit_runner_passes():
    """Volledige PS1-suite (mock filesystem, drift-stamp)."""
    if os.name != "nt":
        pytest.skip("TrustRuntimeSync unit tests require Windows PowerShell")
    if not UNIT_PS1.is_file():
        pytest.skip("TrustRuntimeSync.Unit.Tests.ps1 ontbreekt")
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(UNIT_PS1),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
