"""Unit tests: sync_profile_mcp_from_domains overlay bootstrap wiring."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parents[2]
RAG_DIR = REPO / "scripts" / "rag_pipeline"
SCRIPT = RAG_DIR / "sync_profile_mcp_from_domains.py"
PY = Path(os.environ.get("USERPROFILE", "")) / "miniconda3/envs/hermes-env/python.exe"
PYTHON = str(PY) if PY.is_file() else sys.executable


@pytest.fixture(scope="module")
def sync_module():
    """Load script once with repo + rag_pipeline on sys.path (real bootstrap)."""
    paths = [str(REPO), str(RAG_DIR)]
    for p in paths:
        if p not in sys.path:
            sys.path.insert(0, p)
    spec = importlib.util.spec_from_file_location("sync_profile_mcp_under_test", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_script_check_no_profile_mcp_import_error():
    env = {**os.environ, "PYTHONPATH": str(REPO)}
    proc = subprocess.run(
        [PYTHON, str(SCRIPT), "--check"],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO),
        env=env,
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    assert "ModuleNotFoundError" not in combined
    assert "profile_mcp_format" not in combined or "OK" in combined
    assert proc.returncode in (0, 1)


def test_bootstrap_failure_exits_with_message(capsys):
    install_mock = MagicMock(side_effect=RuntimeError("broken overlay"))
    fake_bootstrap = MagicMock(install=install_mock)
    spec = importlib.util.spec_from_file_location("sync_mcp_bootstrap_fail", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"overlay.bootstrap": fake_bootstrap}, clear=False):
        with pytest.raises(SystemExit) as excinfo:
            spec.loader.exec_module(mod)
    assert excinfo.value.code == 1
    install_mock.assert_called_once()
    assert "overlay bootstrap failed" in capsys.readouterr().err


def test_resolve_python_prefers_hermes_python_env(sync_module, monkeypatch, tmp_path):
    fake_py = tmp_path / "custom-python.exe"
    fake_py.write_text("", encoding="utf-8")
    monkeypatch.setenv("HERMES_PYTHON", str(fake_py))
    assert sync_module._resolve_python() == fake_py


def test_resolve_python_invalid_override_falls_back(sync_module, monkeypatch):
    monkeypatch.setenv("HERMES_PYTHON", "/nonexistent/python.exe")
    result = sync_module._resolve_python()
    assert result.name.endswith("python.exe")


def test_main_missing_domains_yaml_returns_one(sync_module, tmp_path, monkeypatch):
    missing = tmp_path / "missing.yaml"
    monkeypatch.setattr(sync_module, "default_domains_yaml", lambda: missing)
    assert sync_module.main(["--check"]) == 1


def test_main_check_empty_domain_list_returns_one(sync_module, monkeypatch, tmp_path):
    yaml_file = tmp_path / "domains.yaml"
    yaml_file.write_text("domains: []\n", encoding="utf-8")
    monkeypatch.setattr(sync_module, "default_domains_yaml", lambda: yaml_file)
    monkeypatch.setattr(sync_module, "load_domains", lambda _p: [])
    assert sync_module.main(["--check", "--domain", "nonexistent"]) == 1
