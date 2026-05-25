#!/usr/bin/env python3
"""E2E: collapsed record pseudo-tables (Component/Keuze/Status + em-dash).

Dedicated audit for _parse_collapsed_record_rows / eligibility guards / review hardening.
No live Hermes runtime — normalizer + verify + optional TS parity only.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

FAILURES = 0
STEP = 0

_ARCHITECTURE_EMDASH = (
    "### Architectuursamenvatting\n\n"
    "Component: Inter-agent communicatie Keuze: FastAPI Status: operationeel "
    "\u2014\u2014\u2014\u2014\u2014\u2014 "
    "Component: Datamodel Keuze: Pydantic Status: geimplementeerd\n"
)

_ARCHITECTURE_MULTILINE = (
    "### Architectuursamenvatting\n\n"
    "Component: Inter-agent communicatie Keuze: FastAPI Status: operationeel\n"
    "Component: Datamodel Keuze: Pydantic Status: geimplementeerd\n"
)

_GROUPED_AUXILIARY = (
    "### Overzicht per auxiliary taak\n\n"
    "**Lokale achtergrondtaken (compression)**\n"
    "Provider: custom (Ollama)\n"
    "Model: qwen2.5-coder:1.5b\n"
    "Base URL: http://localhost:11434/v1\n\n"
    "**Visuele taken (vision)**\n"
    "Provider: gemini\n"
    "Model: gemini-2.5-flash\n"
    "Base URL: (cloud)\n"
)


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" — {detail}" if detail else ""
    if ok:
        print(f"[OK] E{STEP} {name}{suffix}")
    else:
        print(f"[FAIL] E{STEP} {name}{suffix}", file=sys.stderr)
        FAILURES += 1


def _has_divider(text: str) -> bool:
    return bool(re.search(r"^\|\s*[-:]+\s*\|", text, re.MULTILINE))


def test_e1_emdash_single_line_to_table() -> None:
    from hermes_cli.markdown_output_normalize import normalize_pseudo_tables_to_markdown

    out = normalize_pseudo_tables_to_markdown(_ARCHITECTURE_EMDASH)
    ok = (
        _has_divider(out)
        and "| Component | Keuze | Status |" in out
        and "| Inter-agent communicatie | FastAPI | operationeel |" in out
        and "| Datamodel | Pydantic | geimplementeerd |" in out
        and "\u2014\u2014\u2014" not in out
    )
    _step("em-dash enkele regel → 3-koloms markdown-tabel", ok)


def test_e2_multiline_without_emdash() -> None:
    from hermes_cli.markdown_output_normalize import normalize_pseudo_tables_to_markdown

    out = normalize_pseudo_tables_to_markdown(_ARCHITECTURE_MULTILINE)
    ok = _has_divider(out) and "| Datamodel | Pydantic | geimplementeerd |" in out
    _step("multi-line zonder em-dash → tabel (anchor-key split)", ok)


def test_e3_overview_intent_and_parse_section() -> None:
    from hermes_cli.markdown_output_normalize import (
        _infer_section_intent,
        _parse_section_to_table,
    )

    body = _ARCHITECTURE_EMDASH.splitlines()[2:]
    heading = "### Architectuursamenvatting"
    intent_ok = _infer_section_intent(heading, body) == "overview"
    parsed = _parse_section_to_table(heading, body)
    parse_ok = (
        parsed is not None
        and parsed[0] == ["Component", "Keuze", "Status"]
        and len(parsed[1]) >= 2
    )
    _step("Architectuursamenvatting → overview intent + parse", intent_ok and parse_ok)


def test_e4_eligibility_blocks_grouped_auxiliary() -> None:
    from hermes_cli.markdown_output_normalize import (
        _collapsed_record_layout_eligible,
        normalize_pseudo_tables_to_markdown,
    )

    body = _GROUPED_AUXILIARY.splitlines()[2:]
    chunks = [ln.strip() for ln in body if ln.strip()]
    full = " ".join(chunks)
    eligible = _collapsed_record_layout_eligible(chunks, full)
    out = normalize_pseudo_tables_to_markdown(_GROUPED_AUXILIARY)
    ok = (not eligible) and "| Categorie | Provider | Model | Base URL |" in out
    _step("**Groep**-overzicht: geen record-parser false positive", ok)


def test_e5_pipe_in_cell_sanitized() -> None:
    from hermes_cli.markdown_output_normalize import (
        _sanitize_table_cell,
        normalize_pseudo_tables_to_markdown,
    )

    raw = (
        "### Architectuursamenvatting\n\n"
        "Component: foo | bar Keuze: A Status: ok "
        "\u2014\u2014\u2014\u2014 "
        "Component: baz Keuze: B Status: ok2\n"
    )
    out = normalize_pseudo_tables_to_markdown(raw)
    direct = "|" not in _sanitize_table_cell("foo | bar")
    table_ok = _has_divider(out) and "| foo / bar |" in out
    _step("pipe in celwaarde → / en geldige tabel", direct and table_ok)


def test_e6_valid_markdown_table_idempotent() -> None:
    from hermes_cli.markdown_output_normalize import normalize_pseudo_tables_to_markdown

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
    ok = len(dividers) == 1 and "| A | B | C |" in out and "| D | E | F |" in out
    _step("bestaande markdown-tabel blijft idempotent", ok)


def test_e7_verify_script_architecture_probe() -> None:
    try:
        from scripts.verify_pseudo_table_normalizer import verify_pseudo_table_normalizer

        ok, reason = verify_pseudo_table_normalizer()
        _step("verify_pseudo_table_normalizer --verify (incl. architectuur)", ok, reason or "")
    except Exception as exc:
        _step("verify_pseudo_table_normalizer --verify (incl. architectuur)", False, str(exc))


def test_e8_discover_and_dedupe_helpers() -> None:
    from hermes_cli.markdown_output_normalize import (
        _dedupe_table_rows,
        _discover_repeated_field_keys,
    )

    line = "Component: A Keuze: B Status: C \u2014\u2014 Component: A Keuze: B Status: C"
    keys = _discover_repeated_field_keys(line)
    keys_ok = keys == ["Component", "Keuze", "Status"]
    dedupe_ok = _dedupe_table_rows([["A", "B"], ["A", "B"], ["C", "D"]]) == [
        ["A", "B"],
        ["C", "D"],
    ]
    _step("_discover_repeated_field_keys + _dedupe_table_rows", keys_ok and dedupe_ok)


def test_e9_full_pipeline_normalize_assistant() -> None:
    from hermes_cli.markdown_output_normalize import normalize_assistant_markdown

    out = normalize_assistant_markdown(_ARCHITECTURE_EMDASH)
    ok = "| Component | Keuze | Status |" in out and _has_divider(out)
    _step("normalize_assistant_markdown volledige pipeline", ok)


def test_e10_ts_parity_architecture_fixture() -> None:
    runner = REPO_ROOT / "scripts" / "normalize_assistant_markdown_ts_runner.ts"
    if not runner.is_file():
        _step("TS parity architecture_collapsed_emdash", False, "runner ontbreekt")
        return
    npx = shutil.which("npx")
    if not npx:
        _step("TS parity architecture_collapsed_emdash", True, "SKIP npx niet op PATH")
        return

    from hermes_cli.markdown_output_normalize import normalize_assistant_markdown

    py_out = normalize_assistant_markdown(_ARCHITECTURE_EMDASH)
    if "<institutional_check>" in _ARCHITECTURE_EMDASH.lower():
        lines = [
            ln
            for ln in py_out.splitlines()
            if ln.strip()
            and not ln.strip().lower().startswith("<institutional_check")
        ]
        py_out = "\n".join(lines)

    try:
        proc = subprocess.run(
            [npx, "--yes", "tsx", str(runner)],
            input=_ARCHITECTURE_EMDASH,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(REPO_ROOT),
            timeout=120,
            check=False,
        )
    except Exception as exc:
        _step("TS parity architecture_collapsed_emdash", False, str(exc))
        return

    if proc.returncode != 0:
        _step(
            "TS parity architecture_collapsed_emdash",
            False,
            (proc.stderr or proc.stdout or "")[:200],
        )
        return

    ts_out = proc.stdout or ""
    ok = py_out.strip() == ts_out.strip()
    _step("TS parity architecture_collapsed_emdash", ok)


def main() -> int:
    print("=== CollapsedRecordPseudoTable E2E ===")
    test_e1_emdash_single_line_to_table()
    test_e2_multiline_without_emdash()
    test_e3_overview_intent_and_parse_section()
    test_e4_eligibility_blocks_grouped_auxiliary()
    test_e5_pipe_in_cell_sanitized()
    test_e6_valid_markdown_table_idempotent()
    test_e7_verify_script_architecture_probe()
    test_e8_discover_and_dedupe_helpers()
    test_e9_full_pipeline_normalize_assistant()
    test_e10_ts_parity_architecture_fixture()
    if FAILURES:
        print(f"=== HARNESS: FAIL ({FAILURES}) ===", file=sys.stderr)
        return 1
    print(f"=== HARNESS: PASS ({STEP}/{STEP}) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
