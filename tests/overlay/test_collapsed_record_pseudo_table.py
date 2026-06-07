"""Unit tests for collapsed record pseudo-table parsing (Component/Keuze/Status).

Focus: _discover_repeated_field_keys, _parse_collapsed_record_rows, eligibility,
segment splitting, dedupe, and integration via normalize_pseudo_tables_to_markdown.
"""

from __future__ import annotations

import re
from unittest.mock import MagicMock, patch

import pytest

from hermes_cli.markdown_output_normalize import (
    _MAX_COMPARISON_COLUMNS,
    _collapsed_record_layout_eligible,
    _dedupe_table_rows,
    _discover_repeated_field_keys,
    _infer_section_intent,
    _parse_collapsed_record_rows,
    _sanitize_table_cell,
    _split_record_segments,
    normalize_pseudo_tables_to_markdown,
)

EMDASH = "\u2014\u2014\u2014\u2014\u2014\u2014"


class TestDiscoverRepeatedFieldKeys:
    """Happy path and negative cases for key discovery."""

    def test_happy_path_three_keys_twice(self):
        text = (
            "Component: A Keuze: B Status: C "
            f"{EMDASH} "
            "Component: D Keuze: E Status: F"
        )
        assert _discover_repeated_field_keys(text) == ["Component", "Keuze", "Status"]

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "   ",
            "\n\n",
            None,
        ],
    )
    def test_empty_or_none_input_returns_none(self, text):
        assert _discover_repeated_field_keys(text or "") is None

    def test_single_key_repeated_not_enough_columns(self):
        assert _discover_repeated_field_keys("Status: ok Status: fail") is None

    def test_two_different_keys_each_once(self):
        assert _discover_repeated_field_keys("Component: x Keuze: y") is None

    def test_one_char_keys_ignored(self):
        """Keys shorter than 2 chars must not count (avoid false positives)."""
        assert _discover_repeated_field_keys("A: 1 A: 2 B: 3 B: 4") is None

    def test_spaced_label_inside_value_not_treated_as_key(self):
        """Regression: 'Inter-agent communicatie Keuze' must not become a key."""
        text = "Component: Inter-agent communicatie Keuze: FastAPI " * 2
        keys = _discover_repeated_field_keys(text)
        assert keys == ["Component", "Keuze"]

    def test_max_six_columns_cap(self):
        parts = []
        for i in range(8):
            parts.append(f"Field{i}: v{i} " * 2)
        keys = _discover_repeated_field_keys(" ".join(parts))
        assert keys is not None
        assert len(keys) == _MAX_COMPARISON_COLUMNS

    def test_preserves_first_seen_key_order(self):
        text = "Zebra: 1 Alpha: 2 Zebra: 3 Alpha: 4"
        assert _discover_repeated_field_keys(text) == ["Zebra", "Alpha"]


class TestCollapsedRecordLayoutEligible:
    def test_eligible_on_em_dash(self):
        chunks = ["Component: a Keuze: b Status: c"]
        full = chunks[0] + f" {EMDASH} " + "Component: d Keuze: e Status: f"
        assert _collapsed_record_layout_eligible(chunks, full) is True

    def test_eligible_three_labels_one_line(self):
        chunks = ["Component: a Keuze: b Status: c"]
        assert _collapsed_record_layout_eligible(chunks, chunks[0]) is True

    def test_eligible_multiline_without_bold_category(self):
        chunks = [
            "Component: a Keuze: b Status: c",
            "Component: d Keuze: e Status: f",
        ]
        full = " ".join(chunks)
        assert _collapsed_record_layout_eligible(chunks, full) is True

    def test_not_eligible_grouped_auxiliary_style(self):
        chunks = [
            "**Lokale taken**",
            "Provider: custom",
            "Model: qwen",
            "**Vision**",
            "Provider: gemini",
            "Model: flash",
        ]
        full = " ".join(chunks)
        assert _collapsed_record_layout_eligible(chunks, full) is False

    def test_not_eligible_single_prose_line(self):
        chunks = ["Dit is gewone tekst zonder labels."]
        assert _collapsed_record_layout_eligible(chunks, chunks[0]) is False


class TestSplitRecordSegments:
    def test_splits_on_em_dash(self):
        full = f"Component: a {EMDASH} Component: b"
        segs = _split_record_segments(full, ["Component", "Keuze"], [full])
        assert len(segs) >= 2

    def test_multiline_chunks_when_no_em_dash(self):
        chunks = [
            "Component: a Keuze: b Status: c",
            "Component: d Keuze: e Status: f",
        ]
        full = " ".join(chunks)
        segs = _split_record_segments(full, ["Component", "Keuze", "Status"], chunks)
        assert segs == chunks

    def test_anchor_key_split_single_line_two_records(self):
        full = "Component: first Keuze: x Status: y Component: second Keuze: p Status: q"
        segs = _split_record_segments(full, ["Component", "Keuze", "Status"], [full])
        assert len(segs) >= 2
        assert all("Component:" in s for s in segs)

    def test_empty_full_returns_empty_list(self):
        assert _split_record_segments("", ["Component"], []) == []


class TestDedupeTableRows:
    def test_happy_path_unique_rows(self):
        rows = [["A", "B"], ["C", "D"]]
        assert _dedupe_table_rows(rows) == rows

    def test_removes_duplicate_rows(self):
        rows = [["A", "B"], ["A", "B"], ["C", "D"]]
        assert _dedupe_table_rows(rows) == [["A", "B"], ["C", "D"]]

    def test_empty_input(self):
        assert _dedupe_table_rows([]) == []


class TestSanitizeTableCell:
    def test_strips_pipe_from_cell(self):
        assert "|" not in _sanitize_table_cell("a | b")

    def test_collapses_underscore_runs(self):
        assert _sanitize_table_cell("foo____bar") == "foo bar"


class TestParseCollapsedRecordRows:
    """Core parser: happy path, invalid input, guards."""

    _BODY_EMDASH = [
        (
            "Component: Inter-agent communicatie Keuze: FastAPI Status: operationeel "
            f"{EMDASH} "
            "Component: Datamodel Keuze: Pydantic Status: geimplementeerd"
        ),
    ]

    def test_happy_path_emdash_block(self):
        parsed = _parse_collapsed_record_rows(self._BODY_EMDASH)
        assert parsed is not None
        headers, rows = parsed
        assert headers == ["Component", "Keuze", "Status"]
        assert len(rows) == 2
        assert rows[0][0] == "Inter-agent communicatie"

    def test_happy_path_multiline_body(self):
        body = [
            "Component: A Keuze: B Status: C",
            "Component: D Keuze: E Status: F",
        ]
        parsed = _parse_collapsed_record_rows(body)
        assert parsed is not None
        assert len(parsed[1]) == 2

    def test_explicit_field_keys_bypass_discovery(self):
        body = self._BODY_EMDASH
        with patch(
            "hermes_cli.markdown_output_normalize._discover_repeated_field_keys",
            return_value=None,
        ) as mock_discover:
            parsed = _parse_collapsed_record_rows(
                body, field_keys=["Component", "Keuze", "Status"]
            )
        mock_discover.assert_not_called()
        assert parsed is not None
        assert parsed[0] == ["Component", "Keuze", "Status"]

    @pytest.mark.parametrize("body", [[], ["", "   "], ["______________"]])
    def test_empty_or_separator_only_returns_none(self, body):
        assert _parse_collapsed_record_rows(body) is None

    def test_markdown_table_row_in_body_returns_none(self):
        body = [
            "| Component | Keuze | Status |",
            "| --- | --- | --- |",
            "| A | B | C |",
        ]
        assert _parse_collapsed_record_rows(body) is None

    def test_single_record_insufficient_rows(self):
        body = ["Component: only Keuze: one Status: row"]
        assert _parse_collapsed_record_rows(body) is None

    def test_not_eligible_grouped_overview_returns_none(self):
        body = [
            "**Groep A**",
            "Provider: alpha",
            "Model: m1",
            "**Groep B**",
            "Provider: beta",
            "Model: m2",
        ]
        assert _parse_collapsed_record_rows(body) is None

    def test_discovery_fails_without_explicit_keys(self):
        body = self._BODY_EMDASH
        with patch(
            "hermes_cli.markdown_output_normalize._discover_repeated_field_keys",
            return_value=None,
        ):
            assert _parse_collapsed_record_rows(body) is None

    def test_partial_segment_skipped_needs_two_filled_fields(self):
        body = [
            f"Component: full Keuze: x Status: y {EMDASH} "
            "Component: only",
        ]
        assert _parse_collapsed_record_rows(body) is None

    def test_identical_duplicate_segments_yield_none_table(self):
        """Two identical records dedupe to one row; parser requires >=2 rows."""
        duplicate = (
            "Component: same Keuze: k Status: s "
            f"{EMDASH} "
            "Component: same Keuze: k Status: s"
        )
        assert _parse_collapsed_record_rows([duplicate]) is None
        assert _dedupe_table_rows([["same", "k", "s"], ["same", "k", "s"]]) == [
            ["same", "k", "s"]
        ]

    def test_eligibility_guard_blocks_parse(self):
        body = self._BODY_EMDASH
        with patch(
            "hermes_cli.markdown_output_normalize._collapsed_record_layout_eligible",
            return_value=False,
        ):
            assert _parse_collapsed_record_rows(body) is None

    def test_pipe_in_values_sanitized_in_output(self):
        body = [
            f"Component: a | b Keuze: K Status: ok {EMDASH} "
            "Component: c Keuze: K2 Status: ok2",
        ]
        parsed = _parse_collapsed_record_rows(body)
        assert parsed is not None
        assert "|" not in parsed[1][0][0]
        assert " / " in parsed[1][0][0]


class TestNormalizePseudoTablesIntegration:
    """End-to-end section normalization (no external I/O)."""

    def test_architecture_section_becomes_table(self):
        raw = (
            "### Architectuursamenvatting\n\n"
            "Component: A Keuze: B Status: C "
            f"{EMDASH} "
            "Component: D Keuze: E Status: F\n"
        )
        out = normalize_pseudo_tables_to_markdown(raw)
        assert "| Component | Keuze | Status |" in out
        assert re.search(r"^\|\s*[-:]+\s*\|", out, re.MULTILINE)

    def test_no_transform_without_repeated_field_gate(self):
        raw = "### Samenvatting\n\nGewone tekst zonder labels.\n"
        assert normalize_pseudo_tables_to_markdown(raw) == raw.replace("\r\n", "\n")

    def test_existing_markdown_table_unchanged(self):
        raw = (
            "### Architectuursamenvatting\n"
            "| Component | Keuze | Status |\n"
            "| --- | --- | --- |\n"
            "| A | B | C |\n"
            "| D | E | F |\n"
        )
        out = normalize_pseudo_tables_to_markdown(raw)
        dividers = [
            ln
            for ln in out.splitlines()
            if re.match(r"^\|\s*[-:]+\s*\|", ln.strip())
        ]
        assert len(dividers) == 1
        assert "| A | B | C |" in out

    def test_mock_discover_blocks_conversion_when_ineligible_text(self):
        """Isolated: if discovery returns None and layout ineligible, no table."""
        raw = "### Architectuursamenvatting\n\nComponent: once Keuze: once\n"
        with patch(
            "hermes_cli.markdown_output_normalize._parse_collapsed_record_rows",
            return_value=None,
        ) as mock_parse:
            out = normalize_pseudo_tables_to_markdown(raw)
        mock_parse.assert_called()
        assert "| Component |" not in out or "Component: once" in out


class TestUnheadedCollapsedParagraphs:
    """Regression: pseudo-blocks under **labels** without ## headings (trading screenshot)."""

    def test_laag_wat_waarom_emdash_without_heading(self):
        raw = (
            "**Doel bereikt:**\n\n"
            "Onderzoek geschreven.\n\n"
            "**Veerkrachtstrategie – beknopte samenvatting:**\n\n"
            "Drie-lagen verdediging.\n\n"
            "Laag: Fail-closed Wat: Risk crash = geen trades Waarom: Security > uptime "
            f"{EMDASH} Laag: Graceful degradatie Wat: Redis weg Waarom: Systeem blijft draaien "
            f"{EMDASH} Laag: Zelfbescherming Wat: Memory guard Waarom: Voorkomt swap-death\n"
        )
        out = normalize_pseudo_tables_to_markdown(raw)
        assert "| Laag | Wat | Waarom |" in out
        assert "Laag: Fail-closed Wat:" not in out or "| Fail-closed |" in out
        assert out.count("| --- |") >= 1

    def test_discover_laag_wat_waarom_keys(self):
        text = (
            "Laag: A Wat: B Waarom: C "
            f"{EMDASH} Laag: D Wat: E Waarom: F"
        )
        assert _discover_repeated_field_keys(text) == ["Laag", "Wat", "Waarom"]

    def test_beknopte_samenvatting_heading_not_overview_intent(self):
        intent = _infer_section_intent(
            "### Veerkrachtstrategie – beknopte samenvatting",
            [],
        )
        assert intent != "overview"


class TestNormalizeAssistantMarkdownPipeline:
    """Full pipeline hook; mock only if we need to isolate sub-steps."""

    def test_full_pipeline_includes_table(self):
        from hermes_cli.markdown_output_normalize import normalize_assistant_markdown

        raw = (
            "### Architectuursamenvatting\n\n"
            "Component: A Keuze: B Status: C "
            f"{EMDASH} "
            "Component: D Keuze: E Status: F\n"
        )
        out = normalize_assistant_markdown(raw)
        assert "| Component | Keuze | Status |" in out

    def test_crlf_input_normalized(self):
        raw = (
            "### Architectuursamenvatting\r\n\r\n"
            "Component: A Keuze: B Status: C\r\n"
            "Component: D Keuze: E Status: F\r\n"
        )
        out = normalize_pseudo_tables_to_markdown(raw)
        assert "\r" not in out
        assert "| Component |" in out


class TestNegativeAndEdgeCombinations:
    def test_http_url_does_not_pollute_keys(self):
        text = (
            "Component: see http://localhost:11434 Keuze: x Status: y "
            f"{EMDASH} "
            "Component: z Keuze: p Status: q"
        )
        keys = _discover_repeated_field_keys(text)
        assert keys == ["Component", "Keuze", "Status"]

    def test_only_one_label_colon_pair_repeated_other_once(self):
        assert (
            _discover_repeated_field_keys(
                "Component: a Component: b Keuze: only"
            )
            is None
        )

    def test_parse_with_mocked_extract_returns_sparse_rows_filtered(self):
        body = [
            f"Component: a Keuze: b Status: c {EMDASH} "
            "Component: d Keuze: e Status: f",
        ]
        mock_values = MagicMock(side_effect=[
            {"Component": "a", "Keuze": "b", "Status": "c"},
            {"Component": "d"},  # only one field -> segment skipped
        ])
        with patch(
            "hermes_cli.markdown_output_normalize._extract_field_values_from_text",
            mock_values,
        ):
            assert _parse_collapsed_record_rows(body) is None
