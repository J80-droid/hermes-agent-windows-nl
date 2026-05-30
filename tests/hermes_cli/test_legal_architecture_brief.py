"""Unit tests voor hermes_cli/legal_architecture_brief.py."""

from __future__ import annotations

import pytest

from hermes_cli.legal_architecture_brief import (
    brief_forbids_generic_team_primary,
    build_legal_architecture_brief,
)


class TestBuildLegalArchitectureBrief:
    def test_legal_profile_full_body(self) -> None:
        brief = build_legal_architecture_brief("legal")
        assert "## Legal domein" in brief
        assert "lancedb-legal" in brief
        assert "rechtsgebied-lenzen" in brief.lower() or "lenzen" in brief.lower()
        assert "/legal-architectuur" in brief
        assert "profile use legal" not in brief.lower()

    def test_core_profile_redirect(self) -> None:
        brief = build_legal_architecture_brief("core")
        assert "profile use legal" in brief.lower()
        assert "core" in brief.lower()

    def test_other_profile_header(self) -> None:
        brief = build_legal_architecture_brief("trading")
        assert "trading" in brief
        assert "## Legal domein" in brief

    def test_none_profile_no_core_redirect(self) -> None:
        brief = build_legal_architecture_brief(None)
        assert "profile use legal" not in brief.lower()
        assert "Legal domein" in brief

    def test_empty_string_treated_as_default_header(self) -> None:
        brief = build_legal_architecture_brief("")
        assert brief.startswith("## Legal domein")

    def test_whitespace_profile_stripped(self) -> None:
        brief = build_legal_architecture_brief("  LEGAL  ")
        assert "profile use legal" not in brief.lower()

    def test_invalid_profile_name_still_returns_body(self) -> None:
        brief = build_legal_architecture_brief("not-a-valid-name!!!")
        assert "Legal domein" in brief

    def test_lists_all_five_lens_subfolders(self) -> None:
        brief = build_legal_architecture_brief("legal")
        for folder in (
            "Arbeidsrecht",
            "Bestuursrecht",
            "Aansprakelijkheid_Letselschade",
            "Klokkenluiders",
            "Corporate",
        ):
            assert folder in brief


class TestBriefForbidsGenericTeamPrimary:
    def test_legal_brief_passes_contract(self) -> None:
        assert brief_forbids_generic_team_primary(build_legal_architecture_brief("legal"))

    def test_delegate_only_text_fails(self) -> None:
        assert not brief_forbids_generic_team_primary("Use delegate_task and Kanban only.")

    def test_lenzen_without_lancedb_fails(self) -> None:
        assert not brief_forbids_generic_team_primary("We use lenzen in this answer.")

    def test_empty_string_fails(self) -> None:
        assert not brief_forbids_generic_team_primary("")

    @pytest.mark.parametrize(
        "text",
        [
            "rechtsgebied-lenzen en lancedb-legal bucket",
            "LENZEN model met lancedb-legal",
        ],
    )
    def test_case_insensitive_pass(self, text: str) -> None:
        assert brief_forbids_generic_team_primary(text)
