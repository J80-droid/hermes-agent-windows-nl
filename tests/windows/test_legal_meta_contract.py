"""Contract tests: legal meta-routing templates and brief (no LLM)."""

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def test_legal_soul_template_meta_triggers():
    text = (REPO / "docs/templates/SOUL_LEGAL_DOMAIN.md").read_text(encoding="utf-8")
    assert "Domeinarchitectuur" in text
    assert "team van agents" in text.lower() or "team van agents" in text
    assert "/legal-architectuur" in text
    assert "geen aparte Hermes-instantie" in text or "geen aparte hermes" in text.lower()


def test_core_soul_legal_meta_section():
    text = (REPO / "docs/templates/SOUL_CORE_ORCHESTRATOR.md").read_text(encoding="utf-8")
    assert "Legal architectuur" in text
    assert "/legal-architectuur" in text
    assert "legal" in text.lower()


def test_orchestrator_routing_mentions_legal_profile():
    text = (REPO / "docs/ORCHESTRATOR_ROUTING.md").read_text(encoding="utf-8")
    assert "legal" in text.lower()


def test_verify_lens_parity_template_only():
    import subprocess
    import sys

    script = REPO / "scripts/rag_pipeline/verify_legal_lens_parity.py"
    r = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr or r.stdout


def test_legal_architecture_brief_has_lens_model():
    from hermes_cli.legal_architecture_brief import (
        brief_forbids_generic_team_primary,
        build_legal_architecture_brief,
    )

    brief = build_legal_architecture_brief("legal")
    assert "lenzen" in brief.lower() or "Lenzen" in brief
    assert "lancedb-legal" in brief
    assert brief_forbids_generic_team_primary(brief)


def test_legal_runtime_paths_block_no_percent_localappdata():
    from agent.prompt_builder import build_legal_runtime_paths_block

    block = build_legal_runtime_paths_block()
    if block:
        assert "%LOCALAPPDATA%" not in block
        assert "LEGAL_ACTIVE_MATTERS" in block


def test_legal_active_matters_example_exists():
    assert (REPO / "docs/templates/LEGAL_ACTIVE_MATTERS.example.md").is_file()


def test_verify_legal_runtime_scripts_exist():
    assert (REPO / "windows/scripts/verify_legal_runtime.ps1").is_file()
    assert (REPO / "windows/VERIFY_LEGAL_RUNTIME.bat").is_file()


def test_backup_manifest_includes_legal_active_matters():
    text = (REPO / "windows/scripts/HermesBackupCommon.ps1").read_text(encoding="utf-8")
    assert "LEGAL_ACTIVE_MATTERS.md" in text
