"""Unit tests for scripts/deduplicate_memories.py (§-dedup + preamble/mojibake)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from deduplicate_memories import deduplicate_content  # noqa: E402


TRUST_BLOCK = (
    "J. demands absolute trust, zero babysitting, and no pleaser-behavior. "
    "Provide complete forensic and legal details."
)


def test_deduplicate_removes_preamble_duplicate_before_first_section():
    raw = f"{TRUST_BLOCK}\nÂ\n§\n{TRUST_BLOCK}\n§\nExtra preference line.\n"
    out = deduplicate_content(raw)
    assert out.count(TRUST_BLOCK) == 1
    assert "Extra preference line." in out
    assert "Â" not in out


def test_deduplicate_collapses_repeated_sections():
    raw = f"§\n{TRUST_BLOCK}\n§\n{TRUST_BLOCK}\n§\nOnly once.\n"
    out = deduplicate_content(raw)
    assert out.count(TRUST_BLOCK) == 1
    assert "Only once." in out


def test_deduplicate_strips_mojibake_only_lines():
    raw = f"{TRUST_BLOCK}\nÂ\n§\nTail note.\n"
    out = deduplicate_content(raw)
    assert "Â" not in out
    assert "Tail note." in out
