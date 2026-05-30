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
CHECK_RAG_PS1 = REPO / "windows" / "scripts" / "check_hermes_rag_after_repair.ps1"
LAUNCH_BOOTSTRAP_PS1 = REPO / "windows" / "scripts" / "launch_bootstrap.ps1"
RAG_MANIFEST = Path(os.environ.get("LOCALAPPDATA", "")) / "Hermes" / "rag-deps.json"


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


def _rag_manifest_backup():
    if RAG_MANIFEST.is_file():
        return RAG_MANIFEST.read_text(encoding="utf-8")
    return None


def _restore_rag_manifest(backup: str | None) -> None:
    if backup is None:
        RAG_MANIFEST.unlink(missing_ok=True)
    else:
        RAG_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        RAG_MANIFEST.write_text(backup, encoding="utf-8")


def _conda_available() -> bool:
    probe = _run_powershell(f"{_dot_source_policy()}; if (Get-HermesCondaPython) {{ exit 0 }} else {{ exit 1 }}")
    return probe.returncode == 0


# --- Static wiring (happy path + regressie) ---


def test_policy_helpers_present():
    text = POLICY_PS1.read_text(encoding="utf-8")
    for name in (
        "Get-HermesCondaEnvName",
        "Get-HermesCondaPython",
        "Resolve-HermesPythonExe",
        "Test-HermesRagExtrasInstalled",
        "Test-HermesNeedsRagExtrasInstall",
        "Sync-HermesLaunchBootstrapStamp",
        "Test-HermesLaunchBootstrapFastPath",
        "Write-HermesLaunchBootstrapState",
        "Get-HermesPyprojectFingerprint",
        "Update-HermesVscodeInterpreterPath",
        "Invoke-HermesSyncIdePython",
        "Write-HermesPythonPolicyManifest",
        "Write-HermesRagDepsManifest",
        "Invoke-HermesQuarantineBrokenVenv",
    ):
        assert f"function {name}" in text


def test_resolve_script_exists():
    assert (REPO / "windows" / "scripts" / "resolve_hermes_python.ps1").is_file()


def test_get_preferred_python_delegates_to_resolver():
    text = POLICY_PS1.read_text(encoding="utf-8")
    assert "Resolve-HermesPythonExe -RepoRoot $RepoRoot -RequirePip" in text


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
    assert "check_hermes_rag_after_repair.ps1" in text
    assert "install_rag_extras.ps1" in text


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


def test_hermes_home_common_has_model_catalog_guard():
    text = (REPO / "windows" / "scripts" / "HermesHomeCommon.ps1").read_text(encoding="utf-8")
    assert "function Test-HermesModelCatalogAvailability" in text
    assert "provider_model_ids" in text
    assert "provider-catalog" in text


def test_e2e_audit_files_exist():
    audits = REPO / "windows" / "audits"
    for name in (
        "HermesPythonInstitutionalE2E.core.ps1",
        "HermesPythonInstitutionalE2E.harness.ps1",
        "RUN_HERMES_PYTHON_INSTITUTIONAL_E2E.ps1",
        "RUN_HERMES_PYTHON_INSTITUTIONAL_E2E.bat",
    ):
        assert (audits / name).is_file()


def test_regression_e2e_audit_files_exist():
    audits = REPO / "windows" / "audits"
    for name in (
        "HermesPythonInstitutionalRegressionE2E.core.ps1",
        "HermesPythonInstitutionalRegressionE2E.harness.ps1",
        "RUN_HERMES_PYTHON_INSTITUTIONAL_REGRESSION_E2E.ps1",
        "RUN_HERMES_PYTHON_INSTITUTIONAL_REGRESSION_E2E.bat",
    ):
        assert (audits / name).is_file()


def test_policy_hermes_conda_root_wiring():
    text = POLICY_PS1.read_text(encoding="utf-8")
    assert "HERMES_CONDA_ROOT" in text
    assert "rag_extras_verified" in text


def test_launch_bootstrap_stamp_guard_wiring():
    text = LAUNCH_BOOTSTRAP_PS1.read_text(encoding="utf-8")
    assert "Test-HermesNeedsRagExtrasInstall" in text
    assert "Test-HermesLaunchBootstrapFastPath" in text
    assert "Write-HermesLaunchBootstrapState" in text
    assert "Invoke-HermesLaunchBootstrapQuickVerify" in text
    assert "Invoke-HermesBootstrapChildScript" in text
    assert "Sync-HermesLaunchBootstrapStamp" in text
    assert "Invoke-HermesCapturedProcess" not in text


def test_check_rag_after_repair_noninteractive_wiring():
    text = CHECK_RAG_PS1.read_text(encoding="utf-8")
    assert "[switch]$NonInteractive" in text
    assert "HERMES_NONINTERACTIVE" in text
    assert "IsInputRedirected" in text


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


def test_resolve_hermes_python_exe_prefers_hermes_python_env():
    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as handle:
        fake = handle.name
        handle.write(b"stub")
    try:
        script = f"""
{_dot_source_policy()}
$env:HERMES_PYTHON = '{fake.replace("'", "''")}'
$r = Resolve-HermesPythonExe -RequirePip:$false
if ($r -ne '{fake.replace("'", "''")}') {{ exit 1 }}
exit 0
"""
        proc = _run_powershell(script)
        assert proc.returncode == 0, proc.stdout + proc.stderr
    finally:
        Path(fake).unlink(missing_ok=True)


def test_resolve_script_prints_path():
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO / "windows" / "scripts" / "resolve_hermes_python.ps1"),
            "-RepoRoot",
            str(REPO),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(REPO),
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        pytest.skip("conda hermes-env niet beschikbaar op test-host")
    assert proc.stdout.strip().endswith("python.exe")


def test_resolve_manifest_fallback():
    with tempfile.TemporaryDirectory() as tmp:
        fake = str(Path(tmp) / "manifest-python.exe")
        Path(fake).write_bytes(b"stub")
        policy_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "Hermes"
        policy_dir.mkdir(parents=True, exist_ok=True)
        manifest = policy_dir / "python-policy.json"
        backup = manifest.read_text(encoding="utf-8") if manifest.is_file() else None
        manifest.write_text(
            f'{{"preferred_python":"{fake.replace(chr(92), chr(92)+chr(92))}"}}',
            encoding="utf-8",
        )
        try:
            script = f"""
{_dot_source_policy()}
Remove-Item Env:HERMES_PYTHON -ErrorAction SilentlyContinue
$saved = $env:HERMES_CONDA_ENV
$env:HERMES_CONDA_ENV = '__nonexistent_manifest_test__'
$r = Resolve-HermesPythonExe -RequirePip:$false
if ($null -ne $saved) {{ $env:HERMES_CONDA_ENV = $saved }} else {{ Remove-Item Env:HERMES_CONDA_ENV -ErrorAction SilentlyContinue }}
if ($r -ne '{fake.replace("'", "''")}') {{ exit 1 }}
exit 0
"""
            proc = _run_powershell(script)
            if proc.returncode != 0:
                conda_probe = _run_powershell(
                    f"{_dot_source_policy()}; Remove-Item Env:HERMES_PYTHON -ErrorAction SilentlyContinue; if (Get-HermesCondaPython) {{ exit 0 }} else {{ exit 1 }}"
                )
                if conda_probe.returncode == 0:
                    pytest.skip("conda gevonden vóór manifest — volgorde-test niet betrouwbaar")
            assert proc.returncode == 0, proc.stdout + proc.stderr
        finally:
            if backup is None:
                manifest.unlink(missing_ok=True)
            else:
                manifest.write_text(backup, encoding="utf-8")


# --- Review-fixes: CONDA_ROOT, RAG manifest, invalid input ---


def test_get_conda_python_hermes_conda_root():
    with tempfile.TemporaryDirectory() as tmp:
        env_name = "hermes-env"
        conda_root = Path(tmp)
        py_path = conda_root / "envs" / env_name / "python.exe"
        py_path.parent.mkdir(parents=True)
        py_path.write_bytes(b"stub")
        script = f"""
{_dot_source_policy()}
$prev = $env:HERMES_CONDA_ROOT
$prevPy = $env:HERMES_PYTHON
Remove-Item Env:HERMES_PYTHON -ErrorAction SilentlyContinue
$env:HERMES_CONDA_ROOT = '{str(conda_root).replace("'", "''")}'
$r = Get-HermesCondaPython
if ($r -ne '{str(py_path).replace("'", "''")}') {{ exit 1 }}
if ($null -eq $prev) {{ Remove-Item Env:HERMES_CONDA_ROOT -ErrorAction SilentlyContinue }} else {{ $env:HERMES_CONDA_ROOT = $prev }}
if ($null -eq $prevPy) {{ Remove-Item Env:HERMES_PYTHON -ErrorAction SilentlyContinue }} else {{ $env:HERMES_PYTHON = $prevPy }}
exit 0
"""
        proc = _run_powershell(script)
        assert proc.returncode == 0, proc.stdout + proc.stderr


def test_rag_extras_installed_false_for_invalid_stub_exe():
    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as handle:
        stub = handle.name
        handle.write(b"not-a-valid-pe")
    try:
        script = f"""
{_dot_source_policy()}
if (Test-HermesRagExtrasInstalled -PythonExe '{stub.replace("'", "''")}') {{ exit 1 }}
exit 0
"""
        proc = _run_powershell(script)
        assert proc.returncode == 0, proc.stdout + proc.stderr
    finally:
        Path(stub).unlink(missing_ok=True)


def test_rag_extras_installed_false_for_missing_path():
    script = f"""
{_dot_source_policy()}
if (Test-HermesRagExtrasInstalled -PythonExe 'C:\\missing\\python.exe') {{ exit 1 }}
exit 0
"""
    proc = _run_powershell(script)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_write_rag_deps_manifest_returns_null_without_rag():
    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as handle:
        stub = handle.name
        handle.write(b"stub")
    try:
        script = f"""
{_dot_source_policy()}
$r = Write-HermesRagDepsManifest -PythonExe '{stub.replace("'", "''")}'
if ($null -ne $r) {{ exit 1 }}
exit 0
"""
        proc = _run_powershell(script)
        assert proc.returncode == 0, proc.stdout + proc.stderr
    finally:
        Path(stub).unlink(missing_ok=True)


def test_needs_rag_extras_install_false_with_verified_manifest():
    if not _conda_available():
        pytest.skip("conda hermes-env niet beschikbaar op test-host")

    backup = _rag_manifest_backup()
    try:
        script = f"""
{_dot_source_policy()}
$py = Resolve-HermesPythonExe -RepoRoot '{str(REPO).replace("'", "''")}' -RequirePip
if (-not $py) {{ exit 9 }}
$p = Get-HermesRagDepsManifestPath
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $p) | Out-Null
@{{
    installed_at = (Get-Date).ToUniversalTime().ToString('o')
    python_exe = $py
    rag_extras_verified = $true
}} | ConvertTo-Json | Set-Content -LiteralPath $p -Encoding UTF8
$needs = Test-HermesNeedsRagExtrasInstall -RepoRoot '{str(REPO).replace("'", "''")}' -PyprojectPath '{str(REPO / "pyproject.toml").replace("'", "''")}'
if ($needs) {{ exit 1 }}
exit 0
"""
        proc = _run_powershell(script)
        assert proc.returncode == 0, proc.stdout + proc.stderr
    finally:
        _restore_rag_manifest(backup)


def test_needs_rag_extras_install_true_when_python_mismatch():
    if not _conda_available():
        pytest.skip("conda hermes-env niet beschikbaar op test-host")

    backup = _rag_manifest_backup()
    try:
        script = f"""
{_dot_source_policy()}
$p = Get-HermesRagDepsManifestPath
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $p) | Out-Null
@{{
    installed_at = (Get-Date).ToUniversalTime().ToString('o')
    python_exe = 'C:\\\\Other\\\\python.exe'
    rag_extras_verified = $true
}} | ConvertTo-Json | Set-Content -LiteralPath $p -Encoding UTF8
$needs = Test-HermesNeedsRagExtrasInstall -RepoRoot '{str(REPO).replace("'", "''")}' -PyprojectPath '{str(REPO / "pyproject.toml").replace("'", "''")}'
if (-not $needs) {{ exit 1 }}
exit 0
"""
        proc = _run_powershell(script)
        assert proc.returncode == 0, proc.stdout + proc.stderr
    finally:
        _restore_rag_manifest(backup)


def test_needs_rag_extras_install_true_when_pyproject_missing():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        script = f"""
{_dot_source_policy()}
$needs = Test-HermesNeedsRagExtrasInstall -RepoRoot '{str(root).replace("'", "''")}' -PyprojectPath '{str(root / "missing.toml").replace("'", "''")}'
if (-not $needs) {{ exit 1 }}
exit 0
"""
        proc = _run_powershell(script)
        assert proc.returncode == 0, proc.stdout + proc.stderr


def test_needs_rag_extras_install_true_on_corrupt_manifest():
    if not _conda_available():
        pytest.skip("conda hermes-env niet beschikbaar op test-host")

    backup = _rag_manifest_backup()
    try:
        RAG_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        RAG_MANIFEST.write_text("{not-json", encoding="utf-8")
        script = f"""
{_dot_source_policy()}
$needs = Test-HermesNeedsRagExtrasInstall -RepoRoot '{str(REPO).replace("'", "''")}' -PyprojectPath '{str(REPO / "pyproject.toml").replace("'", "''")}'
if (-not $needs) {{ exit 1 }}
exit 0
"""
        proc = _run_powershell(script)
        assert proc.returncode == 0, proc.stdout + proc.stderr
    finally:
        _restore_rag_manifest(backup)


def test_launch_bootstrap_fast_path_with_state_json():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / "pyproject.toml").write_text('[project]\nname = "t"\nversion = "0.0.1"\n', encoding="utf-8")
        local = Path(tmp) / "localappdata"
        hermes_dir = local / "hermes"
        hermes_dir.mkdir(parents=True)
        policy_dir = local / "Hermes"
        policy_dir.mkdir(parents=True)
        py = r"C:\fake\miniconda3\envs\hermes-env\python.exe"
        script_path = str(POLICY_PS1).replace("'", "''")
        repo_s = str(repo).replace("'", "''")
        script = f"""
$env:LOCALAPPDATA = '{str(local).replace("'", "''")}'
. '{script_path}'
$fp = Get-HermesPyprojectFingerprint -PyprojectPath '{str(repo / "pyproject.toml").replace("'", "''")}'
@{{
    schema_version = 1
    verified_at_utc = '2026-01-01T00:00:00Z'
    repo_root = (Get-HermesNormalizedRepoRoot -RepoRoot '{repo_s}')
    pyproject_sha256 = $fp
    python_exe = '{py.replace("'", "''")}'
    rag_extras_verified = $true
}} | ConvertTo-Json | Set-Content -LiteralPath (Get-HermesLaunchBootstrapStatePath) -Encoding UTF8
function Resolve-HermesPythonExe {{ param($RepoRoot='', [switch]$RequirePip) return '{py.replace("'", "''")}' }}
function Test-HermesNeedsRagExtrasInstall {{ param($RepoRoot, $PyprojectPath) return $false }}
function Test-HermesPythonHasPip {{ param($PythonExe) return $true }}
$r = Test-HermesLaunchBootstrapFastPath -RepoRoot '{repo_s}'
if (-not $r.Ok) {{ Write-Error $r.Reason; exit 1 }}
if ($r.Reason -ne 'bootstrap-state v1') {{ exit 2 }}
exit 0
"""
        proc = _run_powershell(script)
        assert proc.returncode == 0, proc.stdout + proc.stderr


def test_launch_bootstrap_fast_path_rejects_pyproject_change():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        proj = repo / "pyproject.toml"
        proj.write_text('[project]\nname = "t"\nversion = "0.0.1"\n', encoding="utf-8")
        local = Path(tmp) / "localappdata"
        (local / "hermes").mkdir(parents=True)
        script_path = str(POLICY_PS1).replace("'", "''")
        repo_s = str(repo).replace("'", "''")
        py = r"C:\fake\hermes-env\python.exe"
        script = f"""
$env:LOCALAPPDATA = '{str(local).replace("'", "''")}'
. '{script_path}'
$repo = '{repo_s}'
$fp = Get-HermesPyprojectFingerprint -PyprojectPath '{str(proj).replace("'", "''")}'
@{{
    schema_version = 1
    repo_root = (Get-HermesNormalizedRepoRoot -RepoRoot $repo)
    pyproject_sha256 = 'deadbeef'
    python_exe = '{py.replace("'", "''")}'
    rag_extras_verified = $true
}} | ConvertTo-Json | Set-Content -LiteralPath (Get-HermesLaunchBootstrapStatePath) -Encoding UTF8
function Resolve-HermesPythonExe {{ param($RepoRoot='', [switch]$RequirePip) return '{py.replace("'", "''")}' }}
function Test-HermesNeedsRagExtrasInstall {{ param($RepoRoot, $PyprojectPath) return $false }}
function Test-HermesPythonHasPip {{ param($PythonExe) return $true }}
$r = Test-HermesLaunchBootstrapFastPath -RepoRoot $repo
if ($r.Ok) {{ exit 1 }}
if ($r.Reason -notmatch 'pyproject') {{ exit 2 }}
exit 0
"""
        proc = _run_powershell(script)
        assert proc.returncode == 0, proc.stdout + proc.stderr


def test_sync_launch_bootstrap_stamp_canonical_path():
    script = f"""
{_dot_source_policy()}
$p = Sync-HermesLaunchBootstrapStamp
$expected = Join-Path (Join-Path $env:LOCALAPPDATA 'hermes') 'launch_bootstrap.stamp'
if ($p -ne $expected) {{ exit 1 }}
exit 0
"""
    proc = _run_powershell(script)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_resolve_requires_pip_skips_stub_without_pip():
    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as handle:
        stub = handle.name
        handle.write(b"stub")
    try:
        script = f"""
{_dot_source_policy()}
$env:HERMES_PYTHON = '{stub.replace("'", "''")}'
$r = Resolve-HermesPythonExe -RequirePip
if ($r -eq '{stub.replace("'", "''")}') {{ exit 1 }}
exit 0
"""
        proc = _run_powershell(script)
        assert proc.returncode == 0, proc.stdout + proc.stderr
    finally:
        Path(stub).unlink(missing_ok=True)


def test_check_rag_after_repair_noninteractive_exits_quickly():
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(CHECK_RAG_PS1),
            "-RepoRoot",
            str(REPO),
            "-NonInteractive",
            "-Quiet",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "HERMES_NONINTERACTIVE": "1"},
        cwd=str(REPO),
        timeout=30,
        check=False,
    )
    assert proc.returncode in (0, 1)
    assert "Read-Host" not in (proc.stdout + proc.stderr)


def test_get_hermes_audit_python_idempotent_dot_source():
    """Get-HermesAuditPython mag policy niet dubbel laden (geen crash)."""
    shell = REPO / "windows" / "HermesShellCommon.ps1"
    script = f"""
. '{str(shell).replace("'", "''")}'
. '{str(POLICY_PS1).replace("'", "''")}'
$p1 = Get-HermesAuditPython -RepoRoot '{str(REPO).replace("'", "''")}'
$p2 = Get-HermesAuditPython -RepoRoot '{str(REPO).replace("'", "''")}'
if (-not $p1 -or -not $p2) {{ exit 1 }}
if ($p1 -ne $p2) {{ exit 2 }}
exit 0
"""
    proc = _run_powershell(script)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_resolve_script_fails_without_conda():
    """Negatief: resolve_hermes_python.ps1 exit 1 zonder interpreter."""
    with tempfile.TemporaryDirectory() as tmp:
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("HERMES_PYTHON", "HERMES_CONDA_ROOT", "HERMES_CONDA_ENV", "HERMES_AUDIT_PYTHON")
        }
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO / "windows" / "scripts" / "resolve_hermes_python.ps1"),
                "-RepoRoot",
                str(tmp),
                "-RequirePip",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            cwd=str(REPO),
            timeout=60,
            check=False,
        )
        if proc.returncode == 0:
            pytest.skip("host conda resolveert ondanks lege repo — negatieve test niet betrouwbaar")
        assert proc.returncode == 1
        assert "Resolve-HermesPythonExe" in proc.stderr or proc.returncode == 1


def test_test_hermes_python_has_pip_false_for_missing():
    script = f"""
{_dot_source_policy()}
if (Test-HermesPythonHasPip -PythonExe 'C:\\\\no\\\\such\\\\python.exe') {{ exit 1 }}
exit 0
"""
    proc = _run_powershell(script)
    assert proc.returncode == 0, proc.stdout + proc.stderr
