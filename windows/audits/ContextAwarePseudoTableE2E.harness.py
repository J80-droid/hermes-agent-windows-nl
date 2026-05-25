#!/usr/bin/env python3
"""Isolated harness: context-aware pseudo-tabel normalizer (2-6 kolommen, overview intent)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FAILURES = 0


def step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES
    suffix = f" — {detail}" if detail else ""
    if ok:
        print(f"[OK] {name}{suffix}")
    else:
        print(f"[FAIL] {name}{suffix}", file=sys.stderr)
        FAILURES += 1


def _has_divider(text: str) -> bool:
    return bool(re.search(r"^\|\s*[-:]+\s*\|", text, re.MULTILINE))


def _body_data_rows(text: str) -> list[str]:
    """Pipe data rows after the |---| divider (excludes header + divider)."""
    past_divider = False
    rows: list[str] = []
    for ln in text.splitlines():
        stripped = ln.strip()
        if not stripped.startswith("|"):
            continue
        if re.match(r"^\|\s*[-:]+\s*\|", stripped):
            past_divider = True
            continue
        if past_divider:
            rows.append(stripped)
    return rows


def test_4col_grouped_overview() -> None:
    from hermes_cli.markdown_output_normalize import normalize_pseudo_tables_to_markdown

    raw = (
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
    out = normalize_pseudo_tables_to_markdown(raw)
    ok = (
        _has_divider(out)
        and "| Categorie | Provider | Model | Base URL |" in out
        and "| Lokale achtergrondtaken (compression) | custom (Ollama) |" in out
        and "| Visuele taken (vision) | gemini |" in out
        and "**Lokale" not in out
    )
    step("4-koloms grouped auxiliary-overzicht → markdown-tabel", ok)


def test_4col_collapsed_inline() -> None:
    from hermes_cli.markdown_output_normalize import normalize_pseudo_tables_to_markdown

    raw = (
        "### Overzicht per auxiliary taak\n\n"
        "Category | Provider | Model | Base URL "
        "**Lokale achtergrondtaken** Provider: custom Model: qwen "
        "Base URL: http://localhost **Visuele taken** Provider: gemini "
        "Model: flash Base URL: (cloud)\n"
    )
    out = normalize_pseudo_tables_to_markdown(raw)
    ok = (
        _has_divider(out)
        and "| Category | Provider | Model | Base URL |" in out
        and "| Lokale achtergrondtaken | custom | qwen | http://localhost |" in out
        and "| Visuele taken | gemini | flash | (cloud) |" in out
    )
    step("4-koloms collapsed inline pseudo → markdown-tabel", ok)


def test_2col_config_overview() -> None:
    from hermes_cli.markdown_output_normalize import normalize_pseudo_tables_to_markdown

    raw = (
        "### Configuratie overzicht\n\n"
        "**Database**\n"
        "Host: localhost\n"
        "Port: 5432\n\n"
        "**Cache**\n"
        "Host: redis\n"
        "Port: 6379\n"
    )
    out = normalize_pseudo_tables_to_markdown(raw)
    ok = (
        _has_divider(out)
        and "| Categorie | Host | Port |" in out
        and "| Database | localhost | 5432 |" in out
        and "| Cache | redis | 6379 |" in out
    )
    step("2-koloms configuratie-overzicht (context=2)", ok)


def test_vs_comparison_regression() -> None:
    from hermes_cli.markdown_output_normalize import normalize_pseudo_tables_to_markdown

    raw = (
        "### Vergelijking: Ollama versus LM Studio\n\n"
        "**Interface**\n"
        "Ollama: CLI-first _____ LM Studio: GUI\n"
        "**Modelbeheer**\n"
        "Ollama: pull _____ LM Studio: browse\n"
    )
    out = normalize_pseudo_tables_to_markdown(raw)
    ok = (
        _has_divider(out)
        and "| Interface |" in out
        and "____" not in out
        and len(_body_data_rows(out)) >= 2
    )
    step("3-koloms vs-vergelijking regressie", ok)


def test_cloud_lokaal_regression() -> None:
    from hermes_cli.markdown_output_normalize import normalize_assistant_markdown

    raw = (
        "### Hulp taken\n\n"
        "**Vision**\n"
        "Cloud: Gemini _____ Lokaal: LLaVA\n"
        "**Web**\n"
        "Cloud: DeepSeek _____ Lokaal: Ollama\n"
    )
    out = normalize_assistant_markdown(raw)
    ok = (
        _has_divider(out)
        and "| Aspect | Cloud | Lokaal |" in out
        and "____" not in out
    )
    step("Cloud/Lokaal vergelijking (geen overview-intent false positive)", ok)


def test_separator_no_duplicate_rows() -> None:
    from hermes_cli.markdown_output_normalize import normalize_pseudo_tables_to_markdown

    raw = (
        "### Overzicht per auxiliary taak\n\n"
        "**Groep A**\n"
        "Provider: alpha\n"
        "Model: m1\n"
        "______________\n"
        "**Groep B**\n"
        "Provider: beta\n"
        "Model: m2\n"
    )
    out = normalize_pseudo_tables_to_markdown(raw)
    data = _body_data_rows(out)
    ok = (
        len(data) == 2
        and "| Groep A | alpha | m1 |" in out
        and "| Groep B | beta | m2 |" in out
    )
    step("Scheiding tussen groepen: geen dubbele rijen", ok, f"data_rows={len(data)}")


def test_valid_4col_table_idempotent() -> None:
    from hermes_cli.markdown_output_normalize import normalize_pseudo_tables_to_markdown

    raw = (
        "### Overzicht per auxiliary taak\n"
        "| Categorie | Provider | Model | Base URL |\n"
        "| --- | --- | --- | --- |\n"
        "| Lokale | Ollama | qwen | http://localhost |\n"
        "| Vision | gemini | flash | (cloud) |\n"
    )
    out = normalize_pseudo_tables_to_markdown(raw)
    dividers = [
        ln for ln in out.splitlines() if re.match(r"^\|\s*[-:]+\s*\|", ln.strip())
    ]
    ok = len(dividers) == 1 and "| Lokale | Ollama |" in out
    step("Geldige 4-koloms tabel blijft idempotent", ok)


def test_generic_provider_model_fallback() -> None:
    from hermes_cli.markdown_output_normalize import normalize_pseudo_tables_to_markdown

    raw = (
        "### Stack details\n\n"
        "**Backend**\n"
        "Provider: postgres\n"
        "Port: 5432\n\n"
        "**Frontend**\n"
        "Provider: nginx\n"
        "Port: 443\n"
    )
    out = normalize_pseudo_tables_to_markdown(raw)
    ok = _has_divider(out) and "| Backend | postgres |" in out and "| Frontend | nginx |" in out
    step("Generic intent: Provider/Port overview fallback", ok)


def test_crlf_windows_line_endings() -> None:
    from hermes_cli.markdown_output_normalize import normalize_pseudo_tables_to_markdown

    raw = (
        "### Overzicht per auxiliary taak\r\n\r\n"
        "**Groep A**\r\n"
        "Provider: alpha\r\n"
        "Model: m1\r\n\r\n"
        "**Groep B**\r\n"
        "Provider: beta\r\n"
        "Model: m2\r\n"
    )
    out = normalize_pseudo_tables_to_markdown(raw)
    ok = _has_divider(out) and "| Groep A | alpha | m1 |" in out and "\r" not in out
    step("CRLF input (Windows) normaliseert naar markdown-tabel", ok)


def main() -> int:
    print("=== Context-aware pseudo-tabel harness ===")
    test_4col_grouped_overview()
    test_4col_collapsed_inline()
    test_2col_config_overview()
    test_vs_comparison_regression()
    test_cloud_lokaal_regression()
    test_separator_no_duplicate_rows()
    test_valid_4col_table_idempotent()
    test_generic_provider_model_fallback()
    test_crlf_windows_line_endings()
    if FAILURES:
        print(f"=== HARNESS: FAIL ({FAILURES}) ===", file=sys.stderr)
        return 1
    print("=== HARNESS: PASS (9/9) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
