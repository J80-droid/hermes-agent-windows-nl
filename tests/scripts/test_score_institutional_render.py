"""Unit tests for scripts/score_institutional_render.py.

Maps to the 10/10 checklist in docs/templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md.
Focus: per-check scoring (happy path + edge/negative), score_markdown integration,
and main() CLI (--verify / --file). External render path mocked where isolated.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import scripts.score_institutional_render as score

REPO = Path(__file__).resolve().parents[2]

# Golden rooktest body (aligned with INSTITUTIONAL_RENDERER_TEST_PROMPT.md structure)
ROOKTEST_GOLDEN = """<institutional_check>
- Controle hyperbolen: [Uitgevoerd]
- Controle stelligheden: [Uitgevoerd]
- Controle zekerheidspercentages (<100% expliciet): [Uitgevoerd]
- Controle conclusies: [Uitgevoerd]
</institutional_check>

## Projectoverzicht
Objectieve intro over Hermes Render Test.

**Dossierstatus:**
Gereed voor controle.

### Team Samenstelling
| Naam | Rol | Status |
| --- | --- | --- |
| Alex | Lead | Actief |
| Bo | Dev | Actief |
| Chris | QA | Actief |

### Technische stack
- Python 3.11
- Rich 14
- pytest
- prompt_toolkit

#### Dependencies
| Technologie | Versie | Status |
| --- | --- | --- |
| Rich | 14.3 | OK |
| pytest | 9.0 | OK |
| openai | 2.24 | OK |

## Functionele requirements
| ID | Requirement | Prioriteit |
| --- | --- | --- |
| FR-01 | Render | Hoog |
| FR-02 | Tabellen | Hoog |
| FR-03 | Labels | Midden |
| FR-04 | NFR | Hoog |

### Acceptatiecriteria
1. Checklist compact
2. Tabellen gekleurd
3. NFR als tabel

### Niet-functionele requirements
| Categorie | Eis | Meetmethode |
| --- | --- | --- |
| Performance | Snel renderen | pytest |
| Toegankelijkheid | Contrast | inspectie |
| Onderhoud | Idempotent | pytest |

### Veerkrachtstrategie
Korte intro over lagen.

| Laag | Wat | Waarom |
| --- | --- | --- |
| UI | Rich | Terminal parity |
| Normalizer | Python | Consistentie |
| Web | Ink | Zelfde palet |

## Conclusie
Dit dossier valideert de renderer. Score moet minimaal 9.0 zijn.
"""


# ---------------------------------------------------------------------------
# Template / module wiring
# ---------------------------------------------------------------------------


class TestRooktestTemplateWiring:
    def test_rooktest_path_points_at_active_template(self):
        assert score.ROOKTEST_PATH == (
            REPO / "docs" / "templates" / "INSTITUTIONAL_RENDERER_TEST_PROMPT.md"
        )
        assert score.ROOKTEST_PATH.is_file()

    def test_template_documents_score_verify_command(self):
        text = score.ROOKTEST_PATH.read_text(encoding="utf-8")
        assert "score_institutional_render.py" in text
        assert "--verify" in text

    def test_template_team_section_not_legal_agent_team(self):
        """INSTITUTIONAL_RENDERER_TEST_PROMPT: geen verwarring met legal /legal-architectuur."""
        text = score.ROOKTEST_PATH.read_text(encoding="utf-8")
        assert "/legal-architectuur" in text
        assert "geen Hermes legal-domein" in text or "legal-domein" in text.lower()


# ---------------------------------------------------------------------------
# _score_checklist_rendered
# ---------------------------------------------------------------------------


class TestRenderAnsiCached:
    @patch("hermes_cli.display_markdown.format_response_ansi")
    def test_cache_reuses_single_render_call(self, mock_fmt: MagicMock) -> None:
        cache: dict[str, str] = {}
        mock_fmt.return_value = "Controle ok"
        out1 = score._render_ansi_cached("## A\n", cache)
        out2 = score._render_ansi_cached("## B\n", cache)
        assert out1 == out2 == "Controle ok"
        mock_fmt.assert_called_once()

    @patch("hermes_cli.display_markdown.format_response_ansi", return_value="")
    def test_empty_string_cached(self, mock_fmt: MagicMock) -> None:
        cache: dict[str, str] = {}
        assert score._render_ansi_cached("", cache) == ""


class TestScoreChecklistRendered:
    def test_happy_path_compact_controle_without_xml(self):
        md = (
            "<institutional_check>\n- A: [OK]\n</institutional_check>\n\n"
            "## Projectoverzicht\nTekst."
        )
        score_val, note = score._score_checklist_rendered(md, render_cache={})
        assert score_val == 10
        assert "compact" in note.lower() or "geen xml" in note.lower()

    @patch("hermes_cli.display_markdown.format_response_ansi")
    def test_xml_tags_visible_in_render_low_score(self, mock_fmt: MagicMock):
        mock_fmt.return_value = "output with <institutional_check> still visible"
        score_val, note = score._score_checklist_rendered("ignored", render_cache={})
        assert score_val == 4
        assert "xml" in note.lower()

    @patch("hermes_cli.display_markdown.format_response_ansi")
    def test_missing_controle_line(self, mock_fmt: MagicMock):
        mock_fmt.return_value = "Rendered body without keyword"
        score_val, _ = score._score_checklist_rendered("ignored", render_cache={})
        assert score_val == 7

    @patch("hermes_cli.display_markdown.format_response_ansi")
    def test_render_exception_returns_mid_score(self, mock_fmt: MagicMock):
        mock_fmt.side_effect = RuntimeError("Rich unavailable")
        score_val, note = score._score_checklist_rendered("ignored", render_cache={})
        assert score_val == 5
        assert "renderfout" in note.lower()

    @patch("hermes_cli.display_markdown.format_response_ansi")
    def test_empty_render_output_still_has_controle_when_present(self, mock_fmt: MagicMock):
        mock_fmt.return_value = ""
        score_val, _ = score._score_checklist_rendered("ignored", render_cache={})
        assert score_val == 7


# ---------------------------------------------------------------------------
# _score_section_spacing
# ---------------------------------------------------------------------------


class TestScoreSectionSpacing:
    def test_happy_path_sections_spaced(self):
        md = (
            "| A |\n|---|---|\n| 1 |\n\n"
            "### Volgende\n"
            "- bullet\n\n"
            "## Andere\n"
        )
        score_val, note = score._score_section_spacing(md)
        assert score_val == 10
        assert "witregel" in note.lower()

    def test_table_row_directly_before_heading_fails(self):
        # Row must end with non-space + '|' before newline (scorer lookbehind).
        md = "| A |\n| B|\n## Volgende kop\n"
        score_val, note = score._score_section_spacing(md)
        assert score_val == 4
        assert "tabel" in note.lower() or "kop" in note.lower()

    def test_list_item_directly_before_heading_fails(self):
        md = "- item één\n## Volgende kop\n"
        score_val, note = score._score_section_spacing(md)
        assert score_val == 4

    def test_empty_markdown_passes(self):
        score_val, _ = score._score_section_spacing("")
        assert score_val == 10


# ---------------------------------------------------------------------------
# _score_labels
# ---------------------------------------------------------------------------


class TestScoreLabels:
    def test_no_labels_not_applicable(self):
        score_val, note = score._score_labels("## Alleen tekst\nGeen labels.")
        assert score_val == 10
        assert "n.v.t" in note.lower() or "geen labels" in note.lower()

    def test_happy_path_label_on_own_line(self):
        md = "**Dossierstatus:**\nGereed voor controle.\n"
        score_val, _ = score._score_labels(md)
        assert score_val == 10

    def test_inline_label_and_value_same_line_when_block_labels_exist(self):
        """Inline-only labels are n.v.t.; violation is scored when block labels exist too."""
        md = "**Dossierstatus:**\nGereed.\n**Inline fout:** waarde op één regel\n"
        score_val, note = score._score_labels(md)
        assert score_val == 4
        assert "zelfde regel" in note.lower()

    def test_inline_only_label_treated_as_not_applicable(self):
        md = "**Dossierstatus:** Gereed voor controle.\n"
        score_val, note = score._score_labels(md)
        assert score_val == 10
        assert "n.v.t" in note.lower() or "geen labels" in note.lower()

    def test_double_blank_between_label_and_value(self):
        md = "**Label:**\n\nWaarde\n"
        score_val, note = score._score_labels(md)
        assert score_val == 6
        assert "lege regel" in note.lower()

    def test_multiple_labels_all_valid(self):
        md = "**Eén:**\nwaarde\n**Twee:**\nook waarde\n"
        score_val, _ = score._score_labels(md)
        assert score_val == 10


# ---------------------------------------------------------------------------
# _score_heading_table_tight
# ---------------------------------------------------------------------------


class TestScoreHeadingTableTight:
    def test_heading_directly_on_table_passes(self):
        md = "### Team\n| Naam | Rol |\n|---|---|\n| A | B |\n"
        score_val, _ = score._score_heading_table_tight(md)
        assert score_val == 10

    def test_blank_line_between_heading_and_table_fails(self):
        md = "### Team\n\n| Naam | Rol |\n|---|---|\n"
        score_val, note = score._score_heading_table_tight(md)
        assert score_val == 6
        assert "lege regel" in note.lower()

    def test_h4_heading_with_blank_before_table(self):
        md = "#### Dependencies\n\n| P | V |\n|---|---|\n"
        score_val, _ = score._score_heading_table_tight(md)
        assert score_val == 6


# ---------------------------------------------------------------------------
# _score_nfr_table
# ---------------------------------------------------------------------------


class TestScoreNfrTable:
    def test_no_nfr_section_not_applicable(self):
        score_val, note = score._score_nfr_table("## Overzicht\nTekst.")
        assert score_val == 10
        assert "n.v.t" in note.lower() or "geen nfr" in note.lower()

    def test_nfr_markdown_table_passes(self):
        md = (
            "### Niet-functionele requirements\n"
            "| Categorie | Eis | Meetmethode |\n|---|---|---|\n| Perf | Snel | pytest |\n"
        )
        score_val, _ = score._score_nfr_table(md)
        assert score_val == 10

    def test_nfr_prose_with_em_dash_fails(self):
        md = (
            "### Niet-functionele requirements\n"
            "Performantie — Snel — Handmatig\n"
        )
        score_val, note = score._score_nfr_table(md)
        assert score_val == 4
        assert "prose" in note.lower() or "streepjes" in note.lower()

    def test_nfr_categorie_colon_prose_fails(self):
        md = "### Niet-functionele requirements\nCategorie: Performance Eis: snel\n"
        score_val, _ = score._score_nfr_table(md)
        assert score_val == 4

    def test_nfr_section_without_table_partial_score(self):
        md = "### Niet-functionele requirements\nAlleen platte tekst zonder tabel.\n"
        score_val, _ = score._score_nfr_table(md)
        assert score_val == 6


# ---------------------------------------------------------------------------
# _score_architectuur_tabel
# ---------------------------------------------------------------------------


class TestScoreArchitectuurTabel:
    def test_no_architecture_section_not_applicable(self):
        score_val, _ = score._score_architectuur_tabel("## Overzicht\n| A | B |\n|---|---|\n")
        assert score_val == 10

    def test_veerkrachtstrategie_with_markdown_table_passes(self):
        md = (
            "### Veerkrachtstrategie\n"
            "Intro.\n"
            "| Laag | Wat | Waarom |\n|---|---|---|\n| UI | Rich | OK |\n"
        )
        score_val, _ = score._score_architectuur_tabel(md)
        assert score_val == 10

    def test_architectuur_em_dash_pseudo_layout_fails(self):
        md = "### Architectuursamenvatting\nComponent —————— Keuze —————— Status\n"
        score_val, note = score._score_architectuur_tabel(md)
        assert score_val in (4, 5)
        assert "em-dash" in note.lower() or "pseudo" in note.lower() or "tabel" in note.lower()

    def test_component_keuze_inline_without_table_fails(self):
        md = (
            "### Architectuur\n"
            "Component: A Keuze: B Status: OK\n"
        )
        score_val, _ = score._score_architectuur_tabel(md)
        assert score_val == 5

    def test_architecture_heading_empty_body_skipped(self):
        md = "### Architectuur\n\n## Volgende\nInhoud.\n"
        score_val, _ = score._score_architectuur_tabel(md)
        assert score_val == 10


# ---------------------------------------------------------------------------
# _score_vergelijking_tabel
# ---------------------------------------------------------------------------


class TestScoreVergelijkingTabel:
    def test_no_comparison_section_not_applicable(self):
        score_val, _ = score._score_vergelijking_tabel("## Overzicht\nTekst.")
        assert score_val == 10

    def test_comparison_markdown_table_passes(self):
        md = (
            "### Vergelijking: A versus B\n"
            "| Aspect | A | B |\n|---|---|---|\n| API | REST | gRPC |\n"
        )
        score_val, _ = score._score_vergelijking_tabel(md)
        assert score_val == 10

    def test_underscore_pseudo_table_fails(self):
        md = "### Vergelijking Ollama vs LM Studio\nOllama ________ LM Studio\n"
        score_val, note = score._score_vergelijking_tabel(md)
        assert score_val in (4, 5)
        assert "underscore" in note.lower() or "tabel" in note.lower()

    def test_pipe_rows_without_divider_partial_fail(self):
        md = "### Comparison\n| A | B |\n| 1 | 2 |\n"
        score_val, _ = score._score_vergelijking_tabel(md)
        assert score_val == 5

    def test_comparison_without_any_table_fails(self):
        md = "### Vergelijk\nAlleen platte tekst.\n"
        score_val, _ = score._score_vergelijking_tabel(md)
        assert score_val == 5


# ---------------------------------------------------------------------------
# _score_heading_vs_table_color
# ---------------------------------------------------------------------------


class TestScoreHeadingVsTableColor:
    def test_demo_palette_h2_differs_from_column_zero(self):
        score_val, _ = score._score_heading_vs_table_color()
        assert score_val == 10

    @patch("hermes_cli.institutional_render.table_header_palette")
    @patch("hermes_cli.institutional_render.assistant_markdown_theme")
    def test_colliding_hex_scores_low(
        self,
        mock_theme: MagicMock,
        mock_palette: MagicMock,
    ):
        style = MagicMock()
        style.styles = {"markdown.h2": "bold #aabbcc"}
        mock_theme.return_value = style
        mock_palette.return_value = ["bold #aabbcc", "bold #ffffff"]
        score_val, note = score._score_heading_vs_table_color()
        assert score_val == 4
        assert "botsen" in note.lower() or "h2" in note.lower()

    @patch("hermes_cli.institutional_render.assistant_markdown_theme", side_effect=ImportError("no rich"))
    def test_import_error_returns_mid_score(self, _mock_theme: MagicMock):
        score_val, note = score._score_heading_vs_table_color()
        assert score_val == 7
        assert "overgeslagen" in note.lower() or "kleurcheck" in note.lower()


# ---------------------------------------------------------------------------
# _score_render_pipeline
# ---------------------------------------------------------------------------


class TestScoreRenderPipeline:
    def test_happy_path_renders_section_content(self):
        md = "## Functionele requirements\n| ID | Req |\n|---|---|\n| 1 | X |\n"
        score_val, _ = score._score_render_pipeline(md, render_cache={})
        assert score_val == 10

    @patch("hermes_cli.display_markdown.format_response_ansi")
    def test_empty_render_output(self, mock_fmt: MagicMock):
        mock_fmt.return_value = "   \n  "
        score_val, note = score._score_render_pipeline("## Functionele\nTekst.", render_cache={})
        assert score_val == 5
        assert "lege" in note.lower()

    def test_missing_section_in_output(self):
        with patch("hermes_cli.display_markdown.format_response_ansi", return_value="zonder sectie"):
            score_val, note = score._score_render_pipeline(
                "## Functionele requirements\nBody.", render_cache={}
            )
        assert score_val == 6
        assert "mist" in note.lower() or "sectie" in note.lower()

    @patch("hermes_cli.display_markdown.format_response_ansi", side_effect=OSError("terminal"))
    def test_render_exception(self, _mock_fmt: MagicMock):
        score_val, note = score._score_render_pipeline("any", render_cache={})
        assert score_val == 5
        assert "renderfout" in note.lower()


# ---------------------------------------------------------------------------
# score_markdown (integration)
# ---------------------------------------------------------------------------


class TestScoreMarkdown:
    EXPECTED_CHECKS = frozenset(
        {
            "checklist",
            "kop_op_inhoud",
            "sectie_spacing",
            "labels",
            "nfr_tabel",
            "vergelijking_tabel",
            "architectuur_tabel",
            "kleur_h2_kolom0",
            "render_pipeline",
        }
    )

    def test_returns_all_check_keys(self):
        checks = score.score_markdown(ROOKTEST_GOLDEN)
        assert set(checks.keys()) == self.EXPECTED_CHECKS
        for name, (val, note) in checks.items():
            assert 1 <= val <= 10, f"{name}: score {val} out of range"
            assert isinstance(note, str) and note.strip(), f"{name}: empty note"

    def test_golden_rooktest_average_at_least_nine(self):
        checks = score.score_markdown(ROOKTEST_GOLDEN)
        avg = sum(s for s, _ in checks.values()) / len(checks)
        assert avg >= 9.0, {k: v for k, v in checks.items()}

    def test_broken_nfr_sample_scores_below_verify_threshold(self):
        broken = (
            "### Team\n\n| Naam | Rol |\n|---|---|\n| A | B |\n\n"
            "### Niet-functionele requirements\n"
            "————————————————\n"
        )
        with patch(
            "hermes_cli.markdown_output_normalize.normalize_assistant_markdown",
            side_effect=lambda raw: raw,
        ):
            checks = score.score_markdown(broken)
        assert checks["nfr_tabel"][0] <= 4
        assert checks["kop_op_inhoud"][0] <= 6
        avg = sum(s for s, _ in checks.values()) / len(checks)
        assert avg < 9.0

    @patch("hermes_cli.markdown_output_normalize.normalize_assistant_markdown")
    def test_normalizer_invoked_before_checks(self, mock_norm: MagicMock):
        mock_norm.return_value = ROOKTEST_GOLDEN
        score.score_markdown("raw input")
        mock_norm.assert_called_once_with("raw input")

    @patch("hermes_cli.display_markdown.format_response_ansi", return_value="Controle ok")
    def test_score_markdown_reuses_single_ansi_render(self, mock_fmt: MagicMock):
        score.score_markdown(ROOKTEST_GOLDEN)
        assert mock_fmt.call_count == 1

    def test_empty_string_still_returns_full_check_map(self):
        checks = score.score_markdown("")
        assert set(checks.keys()) == self.EXPECTED_CHECKS


class TestPrintReport:
    def test_print_report_average(self, capsys: pytest.CaptureFixture[str]):
        checks = {"a": (10, "ok"), "b": (8, "note")}
        avg = score.print_report(checks)
        assert avg == 9.0
        out = capsys.readouterr().out
        assert "INSTITUTIONAL RENDER SCORE" in out
        assert "9.0/10" in out


# ---------------------------------------------------------------------------
# main() CLI
# ---------------------------------------------------------------------------


class TestMainCli:
    def test_main_default_without_verify_exits_zero(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(sys, "argv", ["score_institutional_render"])
        assert score.main() == 0

    def test_main_default_with_verify_passes_after_normalizer(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Embedded CLI sample is intentionally rough; normalizer lifts score to ≥ 9."""
        monkeypatch.setattr(sys, "argv", ["score_institutional_render", "--verify"])
        assert score.main() == 0

    def test_main_file_golden_with_verify_passes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        md_file = tmp_path / "golden.md"
        md_file.write_text(ROOKTEST_GOLDEN, encoding="utf-8")
        monkeypatch.setattr(
            sys,
            "argv",
            ["score_institutional_render", "--file", str(md_file), "--verify"],
        )
        assert score.main() == 0

    def test_main_file_broken_with_verify_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        md_file = tmp_path / "bad.md"
        md_file.write_text("# low score fixture\n", encoding="utf-8")
        forced = {name: (4, "forced low") for name in TestScoreMarkdown.EXPECTED_CHECKS}
        monkeypatch.setattr(score, "score_markdown", lambda _md: forced)
        monkeypatch.setattr(
            sys,
            "argv",
            ["score_institutional_render", "--file", str(md_file), "--verify"],
        )
        assert score.main() == 1

    def test_main_missing_file_returns_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        missing = tmp_path / "does_not_exist.md"
        monkeypatch.setattr(
            sys,
            "argv",
            ["score_institutional_render", "--file", str(missing)],
        )
        assert score.main() == 1

    def test_main_empty_file_returns_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        empty = tmp_path / "empty.md"
        empty.write_text("  \n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["score_institutional_render", "--file", str(empty)])
        assert score.main() == 1

    def test_main_verify_at_exactly_nine_passes(self, monkeypatch: pytest.MonkeyPatch):
        checks = {name: (9, "ok") for name in TestScoreMarkdown.EXPECTED_CHECKS}
        monkeypatch.setattr(score, "score_markdown", lambda _md: checks)
        monkeypatch.setattr(score, "print_report", lambda c: 9.0)
        monkeypatch.setattr(sys, "argv", ["score_institutional_render", "--verify"])
        assert score.main() == 0

    def test_main_verify_below_nine_fails(self, monkeypatch: pytest.MonkeyPatch):
        checks = {name: (8, "low") for name in TestScoreMarkdown.EXPECTED_CHECKS}
        monkeypatch.setattr(score, "score_markdown", lambda _md: checks)
        monkeypatch.setattr(score, "print_report", lambda c: 8.0)
        monkeypatch.setattr(sys, "argv", ["score_institutional_render", "--verify"])
        assert score.main() == 1
