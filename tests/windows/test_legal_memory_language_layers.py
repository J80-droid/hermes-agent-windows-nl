"""Contract: legal memory taal- en triggerlagen (EN trust + NL triggers, geen i18n)."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def test_memory_seed_has_three_legal_user_entries():
    text = _read("docs/templates/MEMORY_CANONICAL_SEED.md")
    section = text.split("## legal USER.md entries", 1)[1].split("## MEMORY.md entries", 1)[0]
    fences = section.count("```")
    assert fences >= 6  # 3 open + 3 close
    assert "Legal proactief (NL):" in section
    assert "Legal triggers — voorbeeldvragen J. (NL):" in section
    assert "Legal taallaag (NL):" in section
    assert "SOUL prevaleert" in section
    assert "disciplinaire maatregel" in section


def test_memory_seed_documents_language_layers():
    text = _read("docs/templates/MEMORY_CANONICAL_SEED.md")
    assert "Taal- en triggerlagen" in text
    assert "Geen i18n" in text


def test_soul_legal_user_memory_precedence():
    text = _read("docs/templates/SOUL_LEGAL_DOMAIN.md")
    assert "USER.md (trust EN + legal triggers NL)" in text
    assert "SOUL prevaleert" in text


def test_legal_domain_architecture_language_layers():
    text = _read("docs/LEGAL_DOMAIN_ARCHITECTURE.md")
    assert "## Taal- en triggerlagen" in text
    assert "SOUL prevaleert" in text
    assert "USER.nl.md" in text
    assert "geen i18n" in text.lower() or "Geen i18n" in text


def test_legal_seed_entries_under_char_budget():
    """NL legal seeds alleen; trust EN komt uit aparte USER.md sectie."""
    section = _read("docs/templates/MEMORY_CANONICAL_SEED.md")
    part = section.split("## legal USER.md entries", 1)[1].split("## MEMORY.md entries", 1)[0]
    body = "".join(
        line
        for line in part.splitlines()
        if not line.strip().startswith("```") and line.strip()
    )
    assert len(body) < 1200, f"legal seed body {len(body)} chars — te groot voor USER-budget"


def test_deduplicate_preserves_inline_section_sign_in_legal_seed():
    """§ in legal seed-proza mag niet splitsen (regel-§ alleen)."""
    from scripts.deduplicate_memories import deduplicate_content

    seed = _read("docs/templates/MEMORY_CANONICAL_SEED.md")
    part = seed.split("## legal USER.md entries", 1)[1].split("## MEMORY.md entries", 1)[0]
    blocks: list[str] = []
    in_fence = False
    for line in part.splitlines():
        if line.strip() == "```":
            in_fence = not in_fence
            continue
        if in_fence and line.strip():
            blocks.append(line.strip())
    assert len(blocks) == 3
    merged = "\n§\n".join(blocks) + "\n"
    out = deduplicate_content(merged)
    assert "Legal proactief (NL):" in out
    assert "Legal triggers" in out
    assert "Legal taallaag (NL):" in out
    assert "SOUL prevaleert" in out
    assert out.count("§") >= 3  # inline § in proza + sectie-scheidingen
