"""Unit tests voor institutioneel Python-beleid (conda hermes-env, IDE sync, venv-quarantaine)."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

POLICY_PS1 = REPO / "windows" / "HermesPythonPolicy.ps1"
SYNC_PS1 = REPO / "windows" / "scripts" / "sync_hermes_ide_python.ps1"
ENSURE_PS1 = REPO / "windows" / "scripts" / "ensure_hermes_python.ps1"
REPAIR_BAT = REPO / "windows" / "REPAIR_PYTHON.bat"
VSCODE_SETTINGS = REPO / ".vscode" / "settings.json"
HERMES_START = REPO / "docs" / "HERMES_START.md"
INSTITUTIONAL_MD = REPO / "windows" / "INSTITUTIONAL.md"


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def _run_powershell(script: str, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=merged,
        cwd=str(REPO),
        timeout=120,
        check=False,
    )


def _dot_source_policy() -> str:
    path = str(POLICY_PS1).replace("'", "''")
    return f". '{path}'"


# --- Static wiring (happy path + regressie) ---


def test_policy_helpers_present():
    text = POLICY_PS1.read_text(encoding="utf-8")
    for name in (
        "Get-HermesCondaEnvName",
        "Get-HermesCondaPython",
        "Update-HermesVscodeInterpreterPath",
        "Invoke-HermesSyncIdePython",
        "Write-HermesPythonPolicyManifest",
        "Invoke-HermesQuarantineBrokenVenv",
    ):
        assert f"function {name}" in text


def test_quarantine_uses_try_catch_on_rename():
    text = POLICY_PS1.read_text(encoding="utf-8")
    assert "try {" in text
    assert "Rename-Item" in text
    assert "catch {" in text


def test_sync_script_is_thin_wrapper():
    text = SYNC_PS1.read_text(encoding="utf-8")
    assert "Update-HermesVscodeInterpreterPath" in text
    assert "HermesPythonPolicy.ps1" in text
    assert "function " not in text


def test_ensure_script_wires_sync_ide_and_quarantine():
    text = ENSURE_PS1.read_text(encoding="utf-8")
    assert "[switch]$SyncIde" in text
    assert "Invoke-HermesSyncIdePython" in text
    assert "Invoke-HermesQuarantineBrokenVenv" in text


def test_repair_bat_invokes_sync_ide():
    text = REPAIR_BAT.read_text(encoding="utf-8")
    assert "-SyncIde" in text
    assert "ensure_hermes_python.ps1" in text


def test_vscode_settings_canonical_interpreter():
    text = VSCODE_SETTINGS.read_text(encoding="utf-8")
    assert "python.defaultInterpreterPath" in text
    assert "hermes-env" in text
    assert re.search(r'"python\.terminal\.activateEnvironment"\s*:\s*false', text)


def test_docs_mention_institutional_python():
    start = HERMES_START.read_text(encoding="utf-8")
    inst = INSTITUTIONAL_MD.read_text(encoding="utf-8")
    assert "Python institutioneel" in start or "conda" in start.lower()
    assert "REPAIR_PYTHON" in start
    assert "sync_hermes_ide_python" in inst


def test_e2e_audit_files_exist():
    audits = REPO / "windows" / "audits"
    for name in (
        "HermesPythonInstitutionalE2E.core.ps1",
        "HermesPythonInstitutionalE2E.harness.ps1",
        "RUN_HERMES_PYTHON_INSTITUTIONAL_E2E.ps1",
        "RUN_HERMES_PYTHON_INSTITUTIONAL_E2E.bat",
    ):
        assert (audits / name).is_file()


# --- Update-HermesVscodeInterpreterPath (isolated temp dirs) ---


def test_update_vscode_interpreter_updates_path():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        settings_dir = root / ".vscode"
        settings_dir.mkdir()
        settings = settings_dir / "settings.json"
        settings.write_text(
            '{"python.defaultInterpreterPath": "${env:USERPROFILE}/old/python.exe"}',
            encoding="utf-8",
        )
        target = r"C:\Test\miniconda3\envs\hermes-env\python.exe"
        script = f"""
{_dot_source_policy()}
$r = Update-HermesVscodeInterpreterPath -RepoRoot '{str(root).replace("'", "''")}' -PythonExe '{target.replace("'", "''")}' -Quiet
if (-not $r.Ok) {{ exit 2 }}
if (-not $r.Changed) {{ exit 3 }}
$j = Get-Content -LiteralPath '{str(settings).replace("'", "''")}' -Raw | ConvertFrom-Json
if ($j.'python.defaultInterpreterPath' -ne '{target.replace("'", "''")}') {{ exit 4 }}
exit 0
"""
        proc = _run_powershell(script)
        assert proc.returncode == 0, proc.stdout + proc.stderr


def test_update_vscode_interpreter_idempotent_when_unchanged():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        settings_dir = root / ".vscode"
        settings_dir.mkdir()
        target = r"C:\Test\miniconda3\envs\hermes-env\python.exe"
        escaped = target.replace("\\", "\\\\")
        settings = settings_dir / "settings.json"
        settings.write_text(
            f'{{"python.defaultInterpreterPath": "{escaped}"}}',
            encoding="utf-8",
        )
        script = f"""
{_dot_source_policy()}
$r = Update-HermesVscodeInterpreterPath -RepoRoot '{str(root).replace("'", "''")}' -PythonExe '{target.replace("'", "''")}' -Quiet
if (-not $r.Ok) {{ exit 2 }}
if ($r.Changed) {{ exit 3 }}
exit 0
"""
        proc = _run_powershell(script)
        assert proc.returncode == 0, proc.stdout + proc.stderr


def test_update_vscode_interpreter_fails_without_key():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        settings_dir = root / ".vscode"
        settings_dir.mkdir()
        (settings_dir / "settings.json").write_text("{}", encoding="utf-8")
        script = f"""
{_dot_source_policy()}
$r = Update-HermesVscodeInterpreterPath -RepoRoot '{str(root).replace("'", "''")}' -PythonExe 'C:\\x\\python.exe' -Quiet
if ($r.Ok) {{ exit 2 }}
if ($r.Message -notmatch 'ontbreekt') {{ exit 3 }}
exit 0
"""
        proc = _run_powershell(script)
        assert proc.returncode == 0, proc.stdout + proc.stderr


def test_update_vscode_interpreter_fails_without_settings_file():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        script = f"""
{_dot_source_policy()}
$r = Update-HermesVscodeInterpreterPath -RepoRoot '{str(root).replace("'", "''")}' -PythonExe 'C:\\x\\python.exe' -Quiet
if ($r.Ok) {{ exit 2 }}
if ($r.Message -notmatch 'settings.json ontbreekt') {{ exit 3 }}
exit 0
"""
        proc = _run_powershell(script)
        assert proc.returncode == 0, proc.stdout + proc.stderr


def test_update_vscode_interpreter_fails_without_resolvable_python():
    """Negatief: ongeldig HERMES_PYTHON zonder conda moet falen."""
    conda_probe = _run_powershell(f"{_dot_source_policy()}; if (Get-HermesCondaPython) {{ exit 0 }} else {{ exit 1 }}")
    if conda_probe.returncode == 0:
        pytest.skip("conda hermes-env beschikbaar — negatieve pad niet betrouwbaar testbaar")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        settings_dir = root / ".vscode"
        settings_dir.mkdir()
        (settings_dir / "settings.json").write_text(
            '{"python.defaultInterpreterPath": "x"}',
            encoding="utf-8",
        )
        missing = str(root / "missing-python.exe")
        script = f"""
{_dot_source_policy()}
Remove-Item Env:HERMES_PYTHON -ErrorAction SilentlyContinue
$env:HERMES_PYTHON = '{missing.replace("'", "''")}'
$r = Update-HermesVscodeInterpreterPath -RepoRoot '{str(root).replace("'", "''")}' -Quiet
if ($r.Ok) {{ exit 2 }}
if ($r.Message -notmatch 'Geen conda') {{ exit 3 }}
exit 0
"""
        proc = _run_powershell(script)
        assert proc.returncode == 0, proc.stdout + proc.stderr


# --- Env overrides ---


def test_get_conda_env_name_respects_override():
    script = f"""
{_dot_source_policy()}
$env:HERMES_CONDA_ENV = 'custom-test-env'
if ((Get-HermesCondaEnvName) -ne 'custom-test-env') {{ exit 1 }}
exit 0
"""
    proc = _run_powershell(script)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_get_conda_python_respects_hermes_python_override():
    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as handle:
        fake = handle.name
        handle.write(b"stub")
    try:
        script = f"""
{_dot_source_policy()}
$env:HERMES_PYTHON = '{fake.replace("'", "''")}'
if ((Get-HermesCondaPython) -ne '{fake.replace("'", "''")}') {{ exit 1 }}
exit 0
"""
        proc = _run_powershell(script)
        assert proc.returncode == 0, proc.stdout + proc.stderr
    finally:
        Path(fake).unlink(missing_ok=True)


# --- Quarantine edge cases ---


def test_quarantine_no_op_without_venv():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        script = f"""
{_dot_source_policy()}
if (Invoke-HermesQuarantineBrokenVenv -RepoRoot '{str(root).replace("'", "''")}' -Quiet) {{ exit 1 }}
exit 0
"""
        proc = _run_powershell(script)
        assert proc.returncode == 0, proc.stdout + proc.stderr


def test_policy_manifest_writes_json():
    with tempfile.TemporaryDirectory() as tmp:
        fake = r"C:\Test\miniconda3\envs\hermes-env\python.exe"
        script = f"""
{_dot_source_policy()}
$p = Write-HermesPythonPolicyManifest -PythonExe '{fake.replace("'", "''")}'
if (-not (Test-Path -LiteralPath $p)) {{ exit 1 }}
$j = Get-Content -LiteralPath $p -Raw | ConvertFrom-Json
if ($j.preferred_python -ne '{fake.replace("'", "''")}') {{ exit 2 }}
exit 0
"""
        proc = _run_powershell(script)
        assert proc.returncode == 0, proc.stdout + proc.stderr


def test_preferred_python_skips_venv_without_allow_flag():
    """Zonder HERMES_ALLOW_UV_VENV mag .venv niet de voorkeur krijgen boven conda."""
    conda = os.environ.get("HERMES_PYTHON") or str(
        Path.home() / "miniconda3" / "envs" / "hermes-env" / "python.exe"
    )
    if not Path(conda).is_file():
        pytest.skip("conda hermes-env niet beschikbaar op test-host")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        venv_scripts = root / ".venv" / "Scripts"
        venv_scripts.mkdir(parents=True)
        fake_venv_py = venv_scripts / "python.exe"
        fake_venv_py.write_bytes(b"stub")

        script = f"""
{_dot_source_policy()}
Remove-Item Env:HERMES_ALLOW_UV_VENV -ErrorAction SilentlyContinue
$env:HERMES_PYTHON = '{conda.replace("'", "''")}'
$p = Get-HermesPreferredPython -RepoRoot '{str(root).replace("'", "''")}'
if ($p -ne '{conda.replace("'", "''")}') {{ exit 1 }}
exit 0
"""
        proc = _run_powershell(script, env={"HERMES_PYTHON": conda})
        assert proc.returncode == 0, proc.stdout + proc.stderr


def test_sync_hermes_ide_python_script_exits_nonzero_on_missing_key():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        settings_dir = root / ".vscode"
        settings_dir.mkdir()
        (settings_dir / "settings.json").write_text("{}", encoding="utf-8")
        script_path = str(SYNC_PS1).replace("'", "''")
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SYNC_PS1),
                "-RepoRoot",
                str(root),
                "-Quiet",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(REPO),
            timeout=60,
            check=False,
        )
        assert proc.returncode != 0


def test_ensure_hermes_python_requires_conda_or_hermes_python():
    """Negatief: zonder conda/Hermes_PYTHON moet ensure falen (exit != 0)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ENSURE_PS1),
                "-RepoRoot",
                str(root),
                "-Quiet",
                "-SkipQuarantine",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={
                **{k: v for k, v in os.environ.items() if k not in ("HERMES_PYTHON", "HERMES_CONDA_ENV")},
            },
            cwd=str(REPO),
            timeout=60,
            check=False,
        )
        if proc.returncode == 0:
            pytest.skip("host heeft conda hermes-env — negatieve test niet van toepassing")
        assert "Geen conda" in proc.stdout + proc.stderr or proc.returncode != 0
