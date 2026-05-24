"""Tests for institutional markdown layout normalization."""

import re

from hermes_cli.markdown_output_normalize import (
    coalesce_heading_content_chunks,
    ensure_heading_line_breaks,
    ensure_institutional_check_block,
    ensure_institutional_check_spacing,
    ensure_markdown_table_dividers,
    ensure_section_breaks,
    normalize_assistant_markdown,
    normalize_numbered_headings,
    normalize_plain_nfr_rows_to_table,
    normalize_nfr_prose_section_to_table,
    normalize_plain_outline_headings,
    normalize_pseudo_tables_to_markdown,
    tighten_heading_and_label_spacing,
)


def test_splits_inline_heading_body():
    raw = "## Geobjectiveerde Analyse Dit is de tekst."
    out = ensure_heading_line_breaks(raw)
    assert "## Geobjectiveerde Analyse\n\n" in out
    assert "Dit is de tekst." in out


def test_splits_bold_label_on_same_line():
    raw = "**Betrokken partijen:** Partij A en B"
    out = ensure_heading_line_breaks(raw)
    assert "**Betrokken partijen:**\n\n" in out
    assert "Partij A en B" in out


def test_section_break_before_second_heading():
    raw = "Einde stap één.\n## Stap 2: Volgende"
    out = ensure_section_breaks(raw)
    assert "Einde stap één.\n\n## Stap 2" in out


def test_normalize_numbered_step_to_markdown_heading():
    raw = "1 Stap 1: De acceptatie\nTekst.\n2 Stap 2: Opening"
    out = normalize_numbered_headings(raw)
    assert "## Stap 1: De acceptatie" in out
    assert "## Stap 2: Opening" in out


def test_normalize_assistant_markdown_adds_section_breaks():
    raw = "Intro.\n## Hoofdstuk\n\nBody.\n## Tweede"
    out = normalize_assistant_markdown(raw)
    assert "Body.\n\n## Tweede" in out


def test_normalize_assistant_markdown_idempotent_on_clean_input():
    raw = "## Titel\nTekst hier."
    assert normalize_assistant_markdown(raw) == raw


def test_plain_outline_h1_becomes_markdown_heading():
    raw = "1. Projectoverzicht\n\nTekst."
    out = normalize_plain_outline_headings(raw)
    assert "## Projectoverzicht" in out
    assert "1. Projectoverzicht" not in out


def test_dotted_outline_becomes_subheadings():
    raw = "1.1 Team Samenstelling\n\n| Naam | Rol |\n"
    out = normalize_plain_outline_headings(raw)
    assert "### Team Samenstelling" in out


def test_deep_dotted_outline_becomes_h4():
    raw = "1.2.1 Dependencies\n\nTekst."
    out = normalize_plain_outline_headings(raw)
    assert "#### Dependencies" in out


def test_numbered_list_item_not_converted_to_heading():
    raw = "1. Open het configuratiebestand\n2. Sla op"
    out = normalize_plain_outline_headings(raw)
    assert "## Open" not in out
    assert "1. Open het configuratiebestand" in out


def test_bold_plain_outline_h1():
    raw = "**1. Projectoverzicht**\n\nTekst."
    out = normalize_plain_outline_headings(raw)
    assert "## Projectoverzicht" in out
    assert "**1." not in out


def test_bold_dotted_outline():
    raw = "**1.1 Team Samenstelling**\n\n| A | B |"
    out = normalize_plain_outline_headings(raw)
    assert "### Team Samenstelling" in out


def test_chapter_num_without_dot():
    raw = "2 Functionele Requirements\n\n| ID | Req |"
    out = normalize_plain_outline_headings(raw)
    assert "## Functionele Requirements" in out


def test_bold_chapter_with_dot():
    raw = "**2. Functionele Requirements**"
    out = normalize_plain_outline_headings(raw)
    assert "## Functionele Requirements" in out


def test_institutional_check_inline_expands_to_block():
    raw = "<institutional_check> - Controle: [OK] </institutional_check>"
    out = ensure_institutional_check_block(raw)
    assert out.startswith("<institutional_check>\n")
    assert "\n</institutional_check>" in out


def test_institutional_check_spacing_before_body():
    raw = "Intro.\n<institutional_check>\n- x\n</institutional_check>\n## Titel"
    out = ensure_institutional_check_spacing(raw)
    assert "Intro.\n\n<institutional_check>" in out
    assert "</institutional_check>\n\n## Titel" in out


def test_coalesce_heading_only_chunk_with_table():
    chunks = ["### Team Samenstelling", "| Naam | Rol |\n|---|---|"]
    out = coalesce_heading_content_chunks(chunks)
    assert len(out) == 1
    assert out[0].startswith("### Team Samenstelling\n| Naam |")


def test_coalesce_heading_with_bullet_list():
    chunks = ["### Technische stack", "- Python\n- Rich"]
    out = coalesce_heading_content_chunks(chunks)
    assert len(out) == 1
    assert "- Python" in out[0]


def test_coalesce_heading_with_prose():
    chunks = ["## Projectoverzicht", "Dit is de tekst."]
    out = coalesce_heading_content_chunks(chunks)
    assert len(out) == 1
    assert "Dit is de tekst" in out[0]


def test_tighten_heading_to_table_or_list():
    raw = "### Dependencies\n\n| A | B |\n|---|---|\n"
    out = tighten_heading_and_label_spacing(raw)
    assert "### Dependencies\n| A | B |" in out
    assert "### Dependencies\n\n|" not in out


def test_tighten_preserves_break_before_next_chapter():
    raw = "## Eerste\n\nTekst.\n\n## Tweede\n\n| A |"
    out = tighten_heading_and_label_spacing(raw)
    assert "Tekst.\n\n## Tweede" in out
    assert "## Tweede\n| A |" in out


def test_tighten_label_to_value():
    raw = "**Status:**\n\nActief"
    out = tighten_heading_and_label_spacing(raw)
    assert "**Status:**\nActief" in out


def test_normalize_plain_nfr_rows_to_table():
    raw = (
        "Categorie: Performance Eis: Snel Meetmethode: Benchmark\n"
        "---\n"
        "Categorie: Robuustheid Eis: Geen crash Meetmethode: Fuzz\n"
    )
    out = normalize_plain_nfr_rows_to_table(raw)
    assert "| Categorie | Eis | Meetmethode |" in out
    assert "| Performance | Snel | Benchmark |" in out


def test_normalize_nfr_prose_section_to_table():
    raw = (
        "### Niet-functionele requirements\n\n"
        "**Performantie**\n"
        "Render binnen 50ms bij normale payloads.\n"
        "————————\n"
        "Robuustheid — Geen crash bij lege input — Fuzz-test\n"
        "Portabiliteit: Windows + Linux compatibel\n"
        "\n"
        "## Conclusie\n"
        "Klaar."
    )
    out = normalize_nfr_prose_section_to_table(raw)
    assert "| Categorie | Eis | Meetmethode |" in out
    assert "| Performantie |" in out
    assert "| Robuustheid | Geen crash bij lege input | Fuzz-test |" in out
    assert "| Portabiliteit | Windows + Linux compatibel | - |" in out
    assert "## Conclusie" in out


def test_normalize_assistant_markdown_converts_nfr_prose():
    raw = (
        "### Niet-functionele requirements\n\n"
        "Performantie — Snel — Benchmark\n"
        "Robuustheid — Stabiel — Test\n"
    )
    out = normalize_assistant_markdown(raw)
    assert "| Performantie | Snel | Benchmark |" in out


def test_normalize_assistant_markdown_converts_outline_and_check():
    raw = (
        "1. Projectoverzicht\n"
        "Tekst.\n"
        "1.1 Team\n"
        "Meer.\n"
        "<institutional_check> - A: [OK] </institutional_check>\n"
        "## Tweede"
    )
    out = normalize_assistant_markdown(raw)
    assert "## Projectoverzicht" in out
    assert "### Team" in out
    assert "<institutional_check>\n" in out


def test_ensure_markdown_table_dividers_inserts_separator():
    raw = (
        "| Task | Cloud |\n"
        "| Vision | Gemini |\n"
        "| Web | DeepSeek |\n"
    )
    out = ensure_markdown_table_dividers(raw)
    lines = out.splitlines()
    assert lines[1].strip().startswith("| ---")
    assert "| Vision | Gemini |" in out


def test_ensure_markdown_table_dividers_idempotent_on_valid_table():
    raw = (
        "| A | B |\n"
        "| --- | --- |\n"
        "| 1 | 2 |\n"
    )
    assert ensure_markdown_table_dividers(raw).strip() == raw.strip()


def test_normalize_pseudo_ollama_vs_lm_studio():
    raw = (
        "### Vergelijking: Ollama versus LM Studio\n\n"
        "**Interface**\n"
        "Ollama: CLI-first _____ LM Studio: GUI met knoppen\n"
        "**Modelbeheer**\n"
        "Ollama: pull/list _____ LM Studio: browse catalog\n"
    )
    out = normalize_pseudo_tables_to_markdown(raw)
    assert "| --- |" in out
    assert "| Interface |" in out
    assert "CLI-first" in out
    assert "GUI met knoppen" in out
    assert "____" not in out


def test_normalize_pseudo_inline_bold_dual_values():
    raw = (
        "### Vergelijking: Foo versus Bar\n\n"
        "**Speed** Foo fast _____ Bar slow\n"
        "**Cost** Foo cheap _____ Bar pricey\n"
    )
    out = normalize_pseudo_tables_to_markdown(raw)
    assert "| Speed |" in out
    assert "| Cost |" in out
    assert "____" not in out


def test_normalize_assistant_markdown_ollama_vs_full_pipeline():
    raw = (
        "### Vergelijking: Ollama versus LM Studio\n\n"
        "**Interface**\n"
        "Ollama: CLI _____ LM Studio: GUI\n"
        "**API Poort**\n"
        "Ollama: 11434 _____ LM Studio: 1234\n"
    )
    out = normalize_assistant_markdown(raw)
    assert "| --- |" in out
    assert "| Interface | Ollama | LM Studio |" in out or "| Interface |" in out
    assert "____" not in out


def test_normalize_pseudo_skips_numbered_list_section():
    raw = (
        "### Stappen\n\n"
        "1. Open het configuratiebestand\n"
        "2. Sla de wijzigingen op\n"
    )
    out = normalize_pseudo_tables_to_markdown(raw)
    assert "1. Open het configuratiebestand" in out
    assert "| --- |" not in out


def test_normalize_auxiliary_tasks_infers_cloud_lokaal_headers():
    raw = (
        "### Hulp taken\n\n"
        "**Vision**\n"
        "Cloud: Gemini _____ Lokaal: LLaVA\n"
        "**Web**\n"
        "Cloud: DeepSeek _____ Lokaal: Ollama\n"
    )
    out = normalize_assistant_markdown(raw)
    assert "| Aspect | Cloud | Lokaal |" in out
    assert "| Vision | Gemini | LLaVA |" in out


def test_normalize_assistant_markdown_pipe_rows_missing_divider():
    raw = (
        "| Task | Cloud |\n"
        "| Vision | Gemini |\n"
        "| Web | DeepSeek |\n"
    )
    out = normalize_assistant_markdown(raw)
    lines = out.splitlines()
    assert lines[1].strip().startswith("| ---")


def test_normalize_pseudo_idempotent_on_valid_comparison_table():
    raw = (
        "### Vergelijking: Foo versus Bar\n"
        "| Aspect | Foo | Bar |\n"
        "| --- | --- | --- |\n"
        "| Speed | fast | slow |\n"
    )
    out = normalize_pseudo_tables_to_markdown(raw)
    dividers = [
        ln
        for ln in out.splitlines()
        if re.match(r"^\|\s*[-:]+\s*\|", ln.strip())
    ]
    assert len(dividers) == 1
    assert "| Speed | fast | slow |" in out
