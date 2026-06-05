"""Unit tests for scripts/deduplicate_memories.py (§-dedup + preamble/mojibake)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from deduplicate_memories import deduplicate_content, deduplicate_file  # noqa: E402


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


def test_deduplicate_file_writes_deduplicated_content(tmp_path: Path):
    path = tmp_path / "MEMORY.md"
    raw = f"§\n{TRUST_BLOCK}\n§\n{TRUST_BLOCK}\n"
    path.write_text(raw, encoding="utf-8")
    assert deduplicate_file(path) is True
    out = path.read_text(encoding="utf-8")
    assert out.count(TRUST_BLOCK) == 1


def test_deduplicate_preserves_seven_runtime_sections():
  """Core-shaped MEMORY: seed x3 + 4 runtime sections stays 7 after dedup."""
  seed = "Never compress, average out, or omit micro-details."
  runtime = [
      "Hermes Windows Native quirks: terminal.backend local.",
      "canonical Python interpreter on this Windows host",
      "OBSIDIAN_VAULT_PATH = Hermes Knowledge",
      "Core profile: checkpoints.enabled=True",
  ]
  parts = [seed, "Rule for facts: NEVER guess.", "Trust protocol: GCR, BZ, VSO."]
  parts.extend(runtime)
  raw = "\n§\n".join(parts) + "\n"
  out = deduplicate_content(raw)
  assert out.count("Hermes Windows Native quirks") == 1
  assert out.count("OBSIDIAN_VAULT_PATH") == 1
  assert out.count("Never compress") == 1
  assert out.count("§") == 6  # 7 sections => 6 delimiters


def test_deduplicate_keeps_distinct_tool_failure_variants():
    short = "Rule for facts: NEVER guess when tools fail."
    long = (
        "Rule for facts & tool failures: NEVER guess, extrapolate, or use conceptual "
        "blueprints when verification tools fail."
    )
    raw = f"§\n{short}\n§\n{long}\n"
    out = deduplicate_content(raw)
    assert short in out
    assert long in out


def test_deduplicate_preserves_inline_section_sign_in_prose():
    """Inline § in legal seed mag sectie niet splitsen — alleen regel-§."""
    block_a = "Legal proactief (NL): SOUL § Parallelle invalshoeken. SOUL prevaleert."
    block_b = "Legal triggers — voorbeeldvragen J. (NL): disciplinaire maatregel."
    block_c = "Legal taallaag (NL): Deze § = NL triggers only."
    raw = f"{block_a}\n§\n{block_b}\n§\n{block_c}\n"
    out = deduplicate_content(raw)
    assert "Legal proactief" in out
    assert "Legal triggers" in out
    assert "Legal taallaag" in out
    assert out.count("§") == 4  # 2 inline in prose + 2 regel-delimiters


def test_deduplicate_empty_input_returns_empty():
    assert deduplicate_content("") == ""
    assert deduplicate_content("   \n\n  ") == ""


def test_deduplicate_file_missing_returns_false(tmp_path: Path):
    assert deduplicate_file(tmp_path / "missing.md") is False


def test_deduplicate_file_read_error_returns_false():
    from unittest.mock import MagicMock

    path = MagicMock(spec=Path)
    path.is_file.return_value = True
    path.read_text.side_effect = OSError("denied")
    assert deduplicate_file(path) is False


def test_main_deduplicates_legacy_root_memories(tmp_path: Path, monkeypatch):
    """main() must process hermes/memories/ as well as profiles/*/memories/."""
    import deduplicate_memories as dm

    hermes = tmp_path / "hermes"
    hermes.mkdir(parents=True)
    (hermes / "config.yaml").write_text("profiles: {}\n", encoding="utf-8")
    root_mem = hermes / "memories" / "MEMORY.md"
    root_mem.parent.mkdir(parents=True)
    dup = "Never compress, average out, or omit micro-details."
    root_mem.write_text(f"§\n{dup}\n§\n{dup}\n", encoding="utf-8")

    prof = hermes / "profiles" / "core" / "memories"
    prof.mkdir(parents=True)
    prof_file = prof / "MEMORY.md"
    prof_file.write_text("§\nCore only once.\n", encoding="utf-8")

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert dm.main() == 0
    assert root_mem.read_text(encoding="utf-8").count(dup) == 1
