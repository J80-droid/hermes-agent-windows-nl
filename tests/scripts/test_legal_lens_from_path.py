"""Tests for legal_lens_from_path (fase 2b.1)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "rag_pipeline"))

from legal_lens_from_path import (  # noqa: E402
    SUBMAP_TO_LENS,
    legal_lens_from_source,
    normalize_rel_path,
)


class TestNormalizeRelPath:
    def test_backslashes_to_forward(self) -> None:
        assert normalize_rel_path("A\\B\\C") == "a/b/c"

    def test_lowercase(self) -> None:
        assert "legal_corporate" in normalize_rel_path("04_Legal_Corporate")


class TestLegalLensFromSourceHappyPath:
    @pytest.mark.parametrize(
        "source,expected",
        [
            ("04_Legal_Corporate/Arbeidsrecht/doc.pdf", "arb"),
            ("data/raw_source_files/04_Legal_Corporate/Klokkenluiders/x.md", "klok"),
            ("04_Legal_Corporate/Bestuursrecht/", "bbk"),
            ("04_Legal_Corporate/Aansprakelijkheid_Letselschade/a.pdf", "aanspr"),
            ("04_Legal_Corporate/Corporate/contract.docx", "corp"),
        ],
    )
    def test_all_canonical_submaps(self, source: str, expected: str) -> None:
        assert legal_lens_from_source(source) == expected

    def test_first_matching_lens_wins(self) -> None:
        # Pad met twee lens-mappen: eerste in Path.parts volgorde wint
        path = "04_Legal_Corporate/Arbeidsrecht/Bestuursrecht/doc.pdf"
        assert legal_lens_from_source(path) == "arb"


class TestLegalLensFromSourceNegative:
    def test_outside_legal_returns_none(self) -> None:
        assert legal_lens_from_source("01_Core/readme.md") is None

    def test_empty_source_returns_none(self) -> None:
        assert legal_lens_from_source("") is None
        assert legal_lens_from_source("   ") is None

    def test_none_like_string_empty(self) -> None:
        assert legal_lens_from_source("\n\t") is None

    def test_legal_corporate_without_lens_subfolder(self) -> None:
        assert legal_lens_from_source("04_Legal_Corporate/_Taxonomy/README.md") is None

    def test_case_folder_only_under_legal(self) -> None:
        assert legal_lens_from_source("04_Legal_Corporate/Geschillencommissie Rijk/zaak.pdf") is None

    def test_wrong_number_prefix(self) -> None:
        assert legal_lens_from_source("03_Other/Arbeidsrecht/x") is None

    def test_unknown_subfolder_returns_none(self) -> None:
        assert legal_lens_from_source("04_Legal_Corporate/OnbekendRecht/x.pdf") is None


class TestSubmapToLensMap:
    def test_map_has_five_entries(self) -> None:
        assert len(SUBMAP_TO_LENS) == 5

    def test_values_unique(self) -> None:
        assert len(set(SUBMAP_TO_LENS.values())) == 5
