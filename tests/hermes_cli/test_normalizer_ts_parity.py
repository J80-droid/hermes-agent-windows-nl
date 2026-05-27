"""Parity: Python normalize_assistant_markdown vs Web/Ink TypeScript normalizers."""

from __future__ import annotations

import os
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
        "nfr_prose_emdash",
        "### Niet-functionele requirements\n\n"
        "**Performantie**\nRender snel.\n"
        "Robuustheid \u2014 Stabiel \u2014 Test\n",
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
    (
        "ollama_vs_lm_studio_underscore",
        "### Vergelijking: Ollama versus LM Studio\n\n"
        "**Interface**\n"
        "Ollama: CLI-first _____ LM Studio: GUI met knoppen\n"
        "**Modelbeheer**\n"
        "Ollama: pull/list _____ LM Studio: browse catalog\n",
    ),
    (
        "auxiliary_tasks_pseudo",
        "### Hulp taken\n\n"
        "**Vision**\n"
        "Cloud: Gemini _____ Lokaal: LLaVA\n"
        "**Web**\n"
        "Cloud: DeepSeek _____ Lokaal: Ollama\n",
    ),
    (
        "pipe_rows_missing_divider",
        "| Task | Cloud |\n"
        "| Vision | Gemini |\n"
        "| Web | DeepSeek |\n",
    ),
    (
        "auxiliary_overview_4col",
        "### Overzicht per auxiliary taak\n\n"
        "**Lokale achtergrondtaken (compression, web_extract, …)**\n"
        "Provider: custom (Ollama)\n"
        "Model: qwen2.5-coder:1.5b-instruct-q8_0\n"
        "Base URL: http://localhost:11434/v1\n\n"
        "**Visuele taken (vision)**\n"
        "Provider: gemini\n"
        "Model: gemini-2.5-flash\n"
        "Base URL: (cloud)\n",
    ),
    (
        "auxiliary_overview_2col",
        "### Configuratie overzicht\n\n"
        "**Database**\n"
        "Host: localhost\n"
        "Port: 5432\n\n"
        "**Cache**\n"
        "Host: redis\n"
        "Port: 6379\n",
    ),
    (
        "architecture_collapsed_emdash",
        "### Architectuursamenvatting\n\n"
        "Component: Inter-agent communicatie Keuze: FastAPI Status: operationeel "
        "\u2014\u2014\u2014\u2014\u2014\u2014 "
        "Component: Datamodel Keuze: Pydantic Status: geimplementeerd\n",
    ),
    (
        "institutional_check_compact",
        "<institutional_check>\n- Controle hyperbolen: [Uitgevoerd]\n"
        "- Controle stelligheden: [Uitgevoerd]\n</institutional_check>\n\n"
        "## Projectoverzicht\nTekst.\n",
    ),
    (
        "resilience_laag_wat_waarom_unheaded",
        "**Veerkrachtstrategie – beknopte samenvatting:**\n\n"
        "Drie-lagen verdediging.\n\n"
        "Laag: Fail-closed Wat: Risk crash Waarom: Security "
        "\u2014\u2014\u2014\u2014\u2014\u2014 "
        "Laag: Graceful Wat: Redis weg Waarom: Systeem blijft draaien "
        "\u2014\u2014\u2014\u2014\u2014\u2014 "
        "Laag: Zelfbescherming Wat: Memory guard Waarom: Voorkomt swap-death\n",
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
        encoding="utf-8",
        errors="strict",
        cwd=REPO,
        timeout=120,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"TS runner failed ({runner.name}): {proc.stderr or proc.stdout}"
        )
    return proc.stdout


def _normalize_for_parity(text: str) -> str:
    """Python and Web/Ink share the same pipeline including compact_institutional_check."""
    return normalize_assistant_markdown(text)


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


@pytest.mark.timeout(180)
def test_web_and_ink_ts_normalizers_match_on_fixtures():
    web_runner = REPO / "scripts" / "normalize_assistant_markdown_ts_runner.ts"
    ink_runner = REPO / "scripts" / "normalize_assistant_markdown_ink_runner.ts"
    for name, text in PARITY_FIXTURES:
        web_out = _run_ts_runner(web_runner, text)
        ink_out = _run_ts_runner(ink_runner, text)
        assert web_out.strip() == ink_out.strip(), f"Web ≠ Ink on fixture {name}"
