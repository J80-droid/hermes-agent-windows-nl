#!/usr/bin/env python3
"""Verify pseudo-table normalizer (vs, Cloud/Lokaal, pipe divider, 4-col overview)."""

from __future__ import annotations

import argparse
import re
import sys

_OLLAMA_PROBE = (
    "### Vergelijking: Ollama versus LM Studio\n\n"
    "**Interface**\n"
    "Ollama: CLI _____ LM Studio: GUI\n"
    "**API Poort**\n"
    "Ollama: 11434 _____ LM Studio: 1234\n"
)

_AUX_PROBE = (
    "### Hulp taken\n\n"
    "**Vision**\n"
    "Cloud: Gemini _____ Lokaal: LLaVA\n"
    "**Web**\n"
    "Cloud: DeepSeek _____ Lokaal: Ollama\n"
)

_PIPE_PROBE = (
    "| Task | Cloud |\n"
    "| Vision | Gemini |\n"
    "| Web | DeepSeek |\n"
)

_OVERVIEW_4COL_PROBE = (
    "### Overzicht per auxiliary taak\n\n"
    "**Lokale achtergrondtaken (compression, web_extract, …)**\n"
    "Provider: custom (Ollama)\n"
    "Model: qwen2.5-coder:1.5b-instruct-q8_0\n"
    "Base URL: http://localhost:11434/v1\n\n"
    "**Visuele taken (vision)**\n"
    "Provider: gemini\n"
    "Model: gemini-2.5-flash\n"
    "Base URL: (cloud)\n"
)


def _has_divider(text: str) -> bool:
    return bool(re.search(r"^\|\s*[-:]+\s*\|", text, re.MULTILINE))


def verify_pseudo_table_normalizer() -> tuple[bool, str | None]:
    from hermes_cli.markdown_output_normalize import normalize_assistant_markdown

    ollama = normalize_assistant_markdown(_OLLAMA_PROBE)
    if "____" in ollama:
        return False, "Ollama vs-probe: underscore restant na normalize"
    if not _has_divider(ollama):
        return False, "Ollama vs-probe: geen |---| divider"
    if "| Interface |" not in ollama and "| Aspect |" not in ollama:
        return False, "Ollama vs-probe: verwachte tabelrij ontbreekt"

    aux = normalize_assistant_markdown(_AUX_PROBE)
    if "____" in aux:
        return False, "Auxiliary-probe: underscore restant na normalize"
    if "| Aspect | Cloud | Lokaal |" not in aux:
        return False, "Auxiliary-probe: Cloud/Lokaal headers ontbreken"

    pipe = normalize_assistant_markdown(_PIPE_PROBE)
    lines = [ln.strip() for ln in pipe.splitlines() if ln.strip()]
    if len(lines) < 2 or not _has_divider(pipe):
        return False, "Pipe-probe: divider niet ingevoegd"

    overview = normalize_assistant_markdown(_OVERVIEW_4COL_PROBE)
    if not _has_divider(overview):
        return False, "Overview 4-koloms probe: geen |---| divider"
    if "| Provider |" not in overview and "| Categorie | Provider |" not in overview:
        return False, "Overview 4-koloms probe: Provider-kolom ontbreekt"

    return True, None


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify pseudo-table normalizer")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Exit 0 only when all probes normalize to markdown tables",
    )
    args = parser.parse_args()

    ok, reason = verify_pseudo_table_normalizer()
    if ok:
        if args.verify:
            print("[VERIFY OK] pseudo-table normalizer (Ollama vs, auxiliary, pipe divider, overview 4col)")
        else:
            print("OK: pseudo-table normalizer probes passed")
        return 0

    msg = reason or "pseudo-table normalizer verify failed"
    print(f"[VERIFY FAIL] {msg}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
