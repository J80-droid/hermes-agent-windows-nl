"""Unit tests voor scripts/rag_pipeline/verify_legal_lens_parity.py."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parents[2]
RAG = REPO / "scripts" / "rag_pipeline"
PARITY_PATH = RAG / "verify_legal_lens_parity.py"
SYNC_PATH = RAG / "sync_legal_lens_table_from_taxonomy.py"
TAXONOMY = REPO / "docs" / "LEGAL_TAXONOMY.md"
TEMPLATE = REPO / "docs" / "templates" / "SOUL_LEGAL_DOMAIN.md"


def _load_parity() -> ModuleType:
    if str(RAG) not in sys.path:
        sys.path.insert(0, str(RAG))
    spec = importlib.util.spec_from_file_location("verify_legal_lens_parity", PARITY_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def parity() -> ModuleType:
    return _load_parity()


SAMPLE_TAXONOMY = """| id | lens | signals | submap | tag | status |
|----|------|---------|--------|-----|--------|
| arb | Arbeidsrechtelijk | arbeidsrecht | `Arbeidsrecht/` | x | active |
| klok | Klokkenluiders | wbk | `Klokkenluiders/` | x | active |
"""

SAMPLE_SOUL = """## Juridische lenzen
Canonieke taxonomie: repo `docs/LEGAL_TAXONOMY.md`. Samenvatting:

| Signaal (indicatief) | Lens | Bron-submap |
|----------------------|------|-------------|
| arbeidsrecht | Arbeidsrechtelijk | `Arbeidsrecht/` |
| wbk | Klokkenluiders | `Klokkenluiders/` |

### Multi-lens
text
"""


class TestParseSoulLensRows:
    def test_parses_table_rows(self, parity: ModuleType) -> None:
        rows = parity._parse_soul_lens_rows(SAMPLE_SOUL)
        assert len(rows) == 2
        assert rows[0][1] == "Arbeidsrechtelijk"

    def test_no_table_returns_empty(self, parity: ModuleType) -> None:
        assert parity._parse_soul_lens_rows("## Juridische lenzen\ngeen tabel") == []

    def test_skips_separator_row(self, parity: ModuleType) -> None:
        md = (
            "| Signaal (indicatief) | Lens | Bron-submap |\n"
            "|----------------------|------|-------------|\n"
            "|----|----|----|\n"
            "| a | b | `c/` |\n"
        )
        rows = parity._parse_soul_lens_rows(md)
        assert len(rows) == 1


class TestNormalizeRows:
    def test_strips_backticks_and_slashes(self, parity: ModuleType) -> None:
        rows = [("  sig ", " Lens ", "`Arbeidsrecht/`")]
        norm = parity._normalize_rows(rows)
        assert norm[0] == ("sig", "Lens", "Arbeidsrecht")


class TestCheckParity:
    def test_happy_path(self, parity: ModuleType, tmp_path: Path) -> None:
        soul = tmp_path / "SOUL.md"
        soul.write_text(SAMPLE_SOUL, encoding="utf-8")
        tax_rows = parity._parse_taxonomy_rows(SAMPLE_TAXONOMY)
        assert parity.check_parity(soul, tax_rows) is True

    def test_missing_soul_file(self, parity: ModuleType, tmp_path: Path) -> None:
        missing = tmp_path / "nope.md"
        tax_rows = parity._parse_taxonomy_rows(SAMPLE_TAXONOMY)
        assert parity.check_parity(missing, tax_rows) is False

    def test_missing_lens_header(self, parity: ModuleType, tmp_path: Path) -> None:
        soul = tmp_path / "SOUL.md"
        soul.write_text("## Identity\ngeen lenzen\n", encoding="utf-8")
        assert parity.check_parity(soul, parity._parse_taxonomy_rows(SAMPLE_TAXONOMY)) is False

    def test_row_mismatch(self, parity: ModuleType, tmp_path: Path) -> None:
        bad = SAMPLE_SOUL.replace("Klokkenluiders", "Corporate")
        soul = tmp_path / "SOUL.md"
        soul.write_text(bad, encoding="utf-8")
        assert parity.check_parity(soul, parity._parse_taxonomy_rows(SAMPLE_TAXONOMY)) is False


class TestMainCli:
    def test_missing_taxonomy_returns_one(
        self, parity: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(parity, "TAXONOMY", tmp_path / "missing.md")
        monkeypatch.setattr(sys, "argv", ["verify_legal_lens_parity"])
        assert parity.main() == 1

    def test_empty_taxonomy_rows_returns_one(
        self, parity: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        tax = tmp_path / "LEGAL_TAXONOMY.md"
        tax.write_text("| id | lens | signals | submap | tag | status |\n|----|\n", encoding="utf-8")
        monkeypatch.setattr(parity, "TAXONOMY", tax)
        monkeypatch.setattr(sys, "argv", ["verify_legal_lens_parity"])
        assert parity.main() == 1

    def test_single_soul_arg(
        self, parity: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tax = tmp_path / "LEGAL_TAXONOMY.md"
        tax.write_text(SAMPLE_TAXONOMY, encoding="utf-8")
        monkeypatch.setattr(parity, "TAXONOMY", tax)
        soul = tmp_path / "SOUL.md"
        soul.write_text(SAMPLE_SOUL, encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["verify_legal_lens_parity", "--soul", str(soul)])
        assert parity.main() == 0

    def test_fix_invokes_sync_on_mismatch(
        self, parity: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        soul = tmp_path / "SOUL.md"
        soul.write_text("## Juridische lenzen\n| Signaal | Lens | Bron |\n|---|---|---|\n| x | wrong | `y/` |\n\n### Multi-lens\n", encoding="utf-8")
        tax = tmp_path / "tax.md"
        tax.write_text(SAMPLE_TAXONOMY, encoding="utf-8")
        monkeypatch.setattr(parity, "TAXONOMY", tax)
        monkeypatch.setattr(parity, "TEMPLATE", soul)
        monkeypatch.setattr(
            sys, "argv", ["verify_legal_lens_parity", "--soul", str(soul), "--fix"]
        )

        with patch("subprocess.run") as run:
            run.return_value = MagicMock(returncode=0)
            code = parity.main()
        assert run.called
        assert code in (0, 1)

    def test_all_skipped_when_no_souls(
        self, parity: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        tax = tmp_path / "LEGAL_TAXONOMY.md"
        tax.write_text(SAMPLE_TAXONOMY, encoding="utf-8")
        monkeypatch.setattr(parity, "TAXONOMY", tax)
        monkeypatch.setattr(parity, "resolve_soul_targets", lambda **kw: [tmp_path / "ghost.md"])
        monkeypatch.setattr(sys, "argv", ["verify_legal_lens_parity", "--all"])
        assert parity.main() == 1

    def test_template_parity_against_repo_taxonomy(
        self, parity: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Integratie: repo-template moet matchen met LEGAL_TAXONOMY.md."""
        monkeypatch.setattr(sys, "argv", ["verify_legal_lens_parity"])
        assert parity.main() == 0
