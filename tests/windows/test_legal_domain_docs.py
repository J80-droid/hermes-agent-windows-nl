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


def test_sync_legal_lens_automation_scripts_exist():
    assert (REPO / "windows/scripts/sync_legal_lens_from_taxonomy.ps1").is_file()
    assert (REPO / "windows/SYNC_LEGAL_LENS_FROM_TAXONOMY.bat").is_file()


def test_sync_legal_lens_resolve_targets_includes_template():
    import importlib.util

    mod_path = REPO / "scripts/rag_pipeline/sync_legal_lens_table_from_taxonomy.py"
    spec = importlib.util.spec_from_file_location("sync_legal_lens", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    targets = mod.resolve_soul_targets(include_runtime=False)
    assert mod.TEMPLATE in targets


def test_soul_templates_document_legal_meta_routing():
    core = (REPO / "docs/templates/SOUL_CORE_ORCHESTRATOR.md").read_text(encoding="utf-8")
    legal = (REPO / "docs/templates/SOUL_LEGAL_DOMAIN.md").read_text(encoding="utf-8")
    assert "Legal architectuur" in core or "legal architectuur" in core.lower()
    assert "Domeinarchitectuur" in legal
    assert "geen aparte Hermes-instantie" in legal.lower() or "geen aparte hermes" in legal.lower()


def test_legal_production_scripts_exist():
    assert (REPO / "windows/scripts/verify_legal_runtime.ps1").is_file()
    assert (REPO / "windows/scripts/ensure_legal_active_matters.ps1").is_file()
    assert (REPO / "scripts/rag_pipeline/verify_legal_lens_parity.py").is_file()
    assert (REPO / "docs/LEGAL_PRODUCTION_GATE.md").is_file()


def test_sync_legal_lens_parses_five_active_rows():
    import importlib.util

    mod_path = REPO / "scripts/rag_pipeline/sync_legal_lens_table_from_taxonomy.py"
    spec = importlib.util.spec_from_file_location("sync_legal_lens", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rows = mod._parse_taxonomy_rows((REPO / "docs/LEGAL_TAXONOMY.md").read_text(encoding="utf-8"))
    assert len(rows) >= 5
    blob = " ".join(" ".join(r) for r in rows)
    assert "Klokkenluiders" in blob
    assert "Arbeidsrechtelijk" in blob
