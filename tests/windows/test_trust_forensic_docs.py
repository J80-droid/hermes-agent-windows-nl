"""Repo docs for Trust & Forensic protocol."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_trust_protocol_doc_exists():
    assert (REPO / "docs/TRUST_FORENSIC_PROTOCOL.md").is_file()


def test_shared_advisory_template_deprecated_smoke():
    """Legacy template; sync-compat only — governance lives in VALUES + TRUST_VERIFICATION."""
    path = REPO / "docs/templates/SOUL_SHARED_ADVISORY.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "Advisory" in text or "trust" in text.lower()


def test_shared_values_template():
    text = (REPO / "docs/templates/SOUL_SHARED_VALUES.md").read_text(encoding="utf-8")
    assert "Values" in text
    assert "pleaser" in text.lower()
    assert "eigen redenering" in text.lower() or "Ontbrekende informatie" in text


def test_shared_trust_verification_template():
    text = (REPO / "docs/templates/SOUL_SHARED_TRUST_VERIFICATION.md").read_text(
        encoding="utf-8"
    )
    assert "Trust & verification" in text
    assert "search_knowledge" in text or "RAG" in text
    assert "deel 1" in text.lower() or "1/N" in text


def test_legal_forensic_block():
    text = (REPO / "docs/templates/SOUL_LEGAL_DOMAIN.md").read_text(encoding="utf-8")
    assert "Forensic & trust (legal)" in text
    assert "search_knowledge" in text
    assert "geen compact modus" in text.lower()


def test_memory_canonical_seed():
    text = (REPO / "docs/templates/MEMORY_CANONICAL_SEED.md").read_text(encoding="utf-8")
    assert "Never compress" in text
    assert "Jamel el Mourif" not in text
    assert "J." in text


def test_output_format_pleaser_check():
    text = (REPO / "docs/templates/SOUL_SHARED_OUTPUT_FORMAT.md").read_text(encoding="utf-8")
    assert "pleaser-taal" in text
    assert "geen compact modus" in text.lower()


def test_trust_memory_user_snapshot_script():
    script = REPO / "windows/scripts/log_trust_memory_user_snapshot.ps1"
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert "pleaser-behavior" in text
    assert "[trust-memory]" in text
