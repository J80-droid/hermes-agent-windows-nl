"""Parity: Python normalize_assistant_markdown vs Web/Ink TypeScript normalizers."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from hermes_cli.markdown_output_normalize import normalize_assistant_markdown

REPO = Path(__file__).resolve().parents[2]

PARITY_FIXTURES: list[tuple[str, str]] = [
    (
        "outline_h1",
        "1. Projectoverzicht\n\nTekst.\n1.1 Team\n\n| A | B |",
    ),
    (
        "nfr_prose",
        "### Niet-functionele requirements\n\n"
        "**Performantie**\nRender snel.\n"
        "Robuustheid - Stabiel - Test\n",
    ),
    (
        "nfr_inline",
        "Categorie: Performance Eis: Snel Meetmethode: Benchmark\n",
    ),
    (
        "heading_table_tight",
        "## Functionele requirements\n| ID | Req |\n|---|---|\n| FR-1 | X |",
    ),
    (
        "numbered_step",
        "1 Stap 1: Analyse\nBody.",
    ),
]


def _run_ts_runner(runner: Path, text: str) -> str:
    npx = shutil.which("npx")
    if not npx:
        pytest.skip("npx not on PATH")
    cmd = [
        npx,
        "--yes",
        "tsx",
        str(runner),
    ]
    proc = subprocess.run(
        cmd,
        input=text,
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"TS runner failed ({runner.name}): {proc.stderr or proc.stdout}"
        )
    return proc.stdout


def _normalize_for_parity(text: str) -> str:
    """Align Python with TS: TS compacts institutional_check; strip for compare."""
    out = normalize_assistant_markdown(text)
    if "<institutional_check>" in text.lower():
        # TS compacts tags; Python keeps block layout — compare without tag lines
        lines = [
            ln
            for ln in out.splitlines()
            if ln.strip()
            and not ln.strip().lower().startswith("<institutional_check")
            and not ln.strip().lower().startswith("</institutional_check")
        ]
        return "\n".join(lines)
    return out


@pytest.mark.parametrize("name,text", PARITY_FIXTURES, ids=[n for n, _ in PARITY_FIXTURES])
def test_web_ts_normalizer_matches_python(name: str, text: str):
    del name
    runner = REPO / "scripts" / "normalize_assistant_markdown_ts_runner.ts"
    if not runner.is_file():
        pytest.skip("web TS runner missing")
    py_out = _normalize_for_parity(text)
    ts_out = _run_ts_runner(runner, text)
    assert py_out.strip() == ts_out.strip(), (
        f"Web TS ≠ Python\n--- Python ---\n{py_out}\n--- TS ---\n{ts_out}"
    )


@pytest.mark.parametrize("name,text", PARITY_FIXTURES, ids=[n for n, _ in PARITY_FIXTURES])
def test_ink_ts_normalizer_matches_python(name: str, text: str):
    del name
    runner = REPO / "scripts" / "normalize_assistant_markdown_ink_runner.ts"
    if not runner.is_file():
        pytest.skip("ink TS runner missing")
    py_out = _normalize_for_parity(text)
    ts_out = _run_ts_runner(runner, text)
    assert py_out.strip() == ts_out.strip(), (
        f"Ink TS ≠ Python\n--- Python ---\n{py_out}\n--- TS ---\n{ts_out}"
    )


def test_web_and_ink_ts_normalizers_match_on_fixtures():
    web_runner = REPO / "scripts" / "normalize_assistant_markdown_ts_runner.ts"
    ink_runner = REPO / "scripts" / "normalize_assistant_markdown_ink_runner.ts"
    for name, text in PARITY_FIXTURES:
        web_out = _run_ts_runner(web_runner, text)
        ink_out = _run_ts_runner(ink_runner, text)
        assert web_out.strip() == ink_out.strip(), f"Web ≠ Ink on fixture {name}"
