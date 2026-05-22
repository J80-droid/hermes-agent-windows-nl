"""Repo-docs voor legal domein architectuur."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_legal_taxonomy_exists():
    assert (REPO / "docs/LEGAL_TAXONOMY.md").is_file()


def test_legal_architecture_exists():
    assert (REPO / "docs/LEGAL_DOMAIN_ARCHITECTURE.md").is_file()


def test_soul_legal_template_has_lenses():
    text = (REPO / "docs/templates/SOUL_LEGAL_DOMAIN.md").read_text(encoding="utf-8")
    assert "## Juridische lenzen" in text
    assert "Klokkenluiders" in text
    assert "GCR 2024-00145" not in text.split("## Identity")[1].split("## Mission")[0]


def test_migrate_legal_script_exists():
    assert (REPO / "windows/scripts/migrate_legal_source_layout.ps1").is_file()


def test_sync_legal_lens_script_exists():
    assert (REPO / "scripts/rag_pipeline/sync_legal_lens_table_from_taxonomy.py").is_file()
