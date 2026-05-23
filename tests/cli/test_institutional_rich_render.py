"""Institutional Rich renderer: demo palette, per-column table headers."""

import re

from hermes_cli.display_markdown import format_response_ansi, get_assistant_render_settings
from hermes_cli.institutional_render import assistant_markdown_theme, render_institutional_assistant
from hermes_cli.markdown_output_normalize import normalize_assistant_markdown


def test_assistant_markdown_theme_demo_not_gold():
    theme = assistant_markdown_theme("demo")
    h1 = str(theme.styles["markdown.h1"]).lower()
    assert "ffd700" not in h1
    assert "cyan" in h1 or "66d9ef" in h1


def test_heading_h2_distinct_from_table_column_zero():
    from hermes_cli.institutional_render import table_header_palette

    theme = assistant_markdown_theme("demo")
    h2_style = str(theme.styles["markdown.h2"])
    col0 = table_header_palette("demo")[0]

    def _hexes(style: str) -> set[str]:
        return set(re.findall(r"#[0-9a-fA-F]{6}", style.lower()))

    assert _hexes(h2_style) != _hexes(col0), (
        f"h2 ({h2_style}) must differ from table column 0 ({col0})"
    )


def test_table_render_produces_multiple_header_styles():
    md = (
        "## Overzicht\n\n"
        "| Datum | Titel | Budget |\n"
        "|---|---|---|\n"
        "| 2024 | A | 1 |\n"
    )
    out = format_response_ansi(md, cols=100) or ""
    codes = set(re.findall(r"\x1b\[[0-9;]*m", out))
    assert len(codes) >= 2


def test_dossierstatus_label_on_separate_line_from_value():
    """Checklist #5: label roze/oranje, waarde op regel eronder (niet inline)."""
    md = (
        "## Projectoverzicht\n"
        "Intro.\n\n"
        "**Dossierstatus:**\n"
        "Gereed voor controle.\n"
    )
    out = format_response_ansi(normalize_assistant_markdown(md), cols=100) or ""
    for line in out.splitlines():
        if "Dossierstatus" in line:
            assert "Gereed" not in line, f"label en waarde opzelfde regel: {line!r}"


def test_dossierstatus_inline_split_by_normalizer_and_renderer():
    md = "## Projectoverzicht\nIntro.\n**Dossierstatus:** Gereed voor controle.\n"
    out = format_response_ansi(md, cols=100) or ""
    for line in out.splitlines():
        if "Dossierstatus" in line:
            assert "Gereed" not in line


def test_render_institutional_assistant_label_block():
    md = "**Stap:**\n\nInhoud van het blok."
    renderable = render_institutional_assistant(md, label_columns=True)
    assert renderable is not None


def test_get_assistant_render_settings_defaults():
    s = get_assistant_render_settings()
    assert s["assistant_render_style"] in {"institutional_rich", "markdown_legacy"}
    assert s["assistant_palette"] in {"demo", "hermes", "neutral"}


def test_render_institutional_assistant_splits_headings():
    md = "## Eerste\n\ntekst\n## Tweede\n\nmeer"
    renderable = render_institutional_assistant(md, already_normalized=True)
    from rich.console import Group

    assert isinstance(renderable, Group)
    assert len(renderable._renderables) >= 3


def test_heading_table_renders_as_tight_pair():
    from hermes_cli.institutional_render import TightHeadingBody

    md = "### Team\n| Naam | Rol |\n|---|---|\n| A | B |"
    renderable = render_institutional_assistant(md, already_normalized=True)
    assert isinstance(renderable, TightHeadingBody)


def test_tight_heading_body_skips_blank_line_between_title_and_table():
    from io import StringIO

    from rich.console import Console

    from rich.text import Text as RichText

    from hermes_cli.institutional_render import InstitutionalMarkdown, TightHeadingBody

    pair = TightHeadingBody(
        RichText("Team", style="bold"),
        InstitutionalMarkdown("| A |\n|---|\n| 1 |"),
    )
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80, legacy_windows=False)
    console.print(pair)
    raw_lines = buf.getvalue().splitlines()
    team_idx = next(i for i, ln in enumerate(raw_lines) if "Team" in ln)
    next_idx = team_idx + 1
    assert next_idx < len(raw_lines)
    assert raw_lines[next_idx].strip(), "geen lege regel tussen titel en tabel"


def test_section_spacer_inserts_blank_line_between_blocks():
    from io import StringIO

    from rich.console import Console

    from hermes_cli.institutional_render import SectionSpacer, TightHeadingBody, _assemble_with_section_spacing
    from rich.text import Text as RichText

    blocks = [
        TightHeadingBody(RichText("Een"), RichText("inhoud")),
        TightHeadingBody(RichText("Twee"), RichText("meer")),
    ]
    group = _assemble_with_section_spacing(blocks)  # default gap=2 between body sections
    buf = StringIO()
    Console(file=buf, force_terminal=True, width=80, legacy_windows=False).print(group)
    raw = buf.getvalue().splitlines()
    tweede = next(i for i, ln in enumerate(raw) if "Twee" in ln)
    assert tweede >= 2
    assert raw[tweede - 1].strip() == ""


def test_single_blank_line_after_checklist_not_double():
    md = (
        "<institutional_check>\n- A: [OK]\n</institutional_check>\n\n"
        "## Projectoverzicht\nIntro."
    )
    out = format_response_ansi(md, cols=100) or ""
    lines = out.splitlines()
    ctrl = next(i for i, ln in enumerate(lines) if "Controle" in ln)
    empty_run = 0
    for ln in lines[ctrl + 1 :]:
        if not ln.strip():
            empty_run += 1
        else:
            break
    assert empty_run == 1, f"verwacht 1 witregel na checklist, kreeg {empty_run}"


def test_full_document_section_spacing_and_tight_headings():
    md = (
        "<institutional_check>\n- Controle hyperbolen: [Uitgevoerd]\n</institutional_check>\n\n"
        "## Projectoverzicht\n"
        "Intro tekst.\n\n"
        "### Team Samenstelling\n"
        "| Naam | Rol |\n|---|---|\n| A | B |\n\n"
        "### Technische stack\n"
        "- Python\n"
    )
    out = format_response_ansi(md, cols=100) or ""
    lines = out.splitlines()
    team_i = next(i for i, ln in enumerate(lines) if "Team" in ln)
    assert lines[team_i + 1].strip(), "kop moet direct op tabel"
    tech_i = next(i for i, ln in enumerate(lines) if "Technische" in ln)
    assert tech_i > team_i + 2
    assert any(not lines[j].strip() for j in range(team_i + 1, tech_i)), "witregel tussen secties"


def test_heading_list_and_prose_tight():
    from rich.console import Group

    from hermes_cli.institutional_render import TightHeadingBody

    md = (
        "## Projectoverzicht\n"
        "Korte intro.\n\n"
        "### Technische stack\n"
        "- Python\n"
        "- Rich\n\n"
        "### Dependencies\n"
        "| P | V |\n|---|---|\n| Rich | 13 |"
    )
    renderable = render_institutional_assistant(md, already_normalized=True)
    assert isinstance(renderable, Group)
    assert any(isinstance(p, TightHeadingBody) for p in renderable._renderables)


def test_institutional_check_renders_compact_without_xml_tags():
    md = (
        "<institutional_check>\n"
        "- Controle hyperbolen: [Uitgevoerd]\n"
        "- Controle stelligheden: [Uitgevoerd]\n"
        "</institutional_check>\n\n"
        "## Projectoverzicht\n\nTekst."
    )
    out = format_response_ansi(md, cols=120) or ""
    assert "<institutional_check>" not in out
    assert "Controle hyperbolen" in out
    assert "stelligheden" in out
