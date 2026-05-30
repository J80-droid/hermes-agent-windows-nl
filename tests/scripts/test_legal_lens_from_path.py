"""Tests for legal_lens_from_path (fase 2b.1)."""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "rag_pipeline"))

from legal_lens_from_path import legal_lens_from_source  # noqa: E402


def test_arbeidsrecht_lens():
    assert legal_lens_from_source("04_Legal_Corporate/Arbeidsrecht/doc.pdf") == "arb"


def test_klokkenluiders_lens():
    assert legal_lens_from_source("data/raw_source_files/04_Legal_Corporate/Klokkenluiders/x.md") == "klok"


def test_outside_legal_returns_none():
    assert legal_lens_from_source("01_Core/readme.md") is None
