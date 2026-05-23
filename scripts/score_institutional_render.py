#!/usr/bin/env python3
"""Score institutional renderer output against the 10/10 rooktest checklist."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOKTEST_PATH = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "templates"
    / "INSTITUTIONAL_RENDERER_TEST_PROMPT.md"
)


def _score_checklist_rendered(md: str) -> tuple[int, str]:
    try:
        from hermes_cli.display_markdown import format_response_ansi

        out = format_response_ansi(md, cols=100) or ""
        if "institutional_check" in out.lower():
            return 4, "XML-tags zichtbaar in render"
        if "Controle" not in out:
            return 7, "Geen compacte Controle-regel in render"
        return 10, "Checklist compact, geen XML in render"
    except Exception as exc:
        return 5, f"Checklist renderfout: {exc}"


def _score_heading_table_tight(md: str) -> tuple[int, str]:
    if re.search(r"^#{1,6}\s+.+\n\n+\|", md, re.MULTILINE):
        return 6, "Lege regel tussen kop en tabel in markdown"
    return 10, "Kop direct op tabel/lijst"


def _score_nfr_table(md: str) -> tuple[int, str]:
    m = re.search(
        r"^#{1,6}\s+Niet-functionele\s+requirements\s*$",
        md,
        re.MULTILINE | re.IGNORECASE,
    )
    if not m:
        return 10, "Geen NFR-sectie (n.v.t.)"
    tail = md[m.end() :]
    next_h = re.search(r"^#{1,6}\s+", tail, re.MULTILINE)
    body = tail[: next_h.start()] if next_h else tail
    if "| Categorie |" in body or re.search(r"^\|[^|\n]+\|", body, re.MULTILINE):
        return 10, "NFR als markdown-tabel"
    if "Categorie:" in body or "—" in body or "————————" in body:
        return 4, "NFR prose/streepjes i.p.v. tabel"
    return 6, "NFR-sectie zonder tabel"


def _score_heading_vs_table_color() -> tuple[int, str]:
    try:
        from hermes_cli.institutional_render import assistant_markdown_theme, table_header_palette

        theme = assistant_markdown_theme("demo")
        h2 = str(theme.styles.get("markdown.h2", ""))
        col0 = table_header_palette("demo")[0]

        def hexes(s: str) -> set[str]:
            return set(re.findall(r"#[0-9a-fA-F]{6}", s.lower()))

        if hexes(h2) == hexes(col0):
            return 4, f"h2 en tabelkolom 0 botsen ({h2} vs {col0})"
        return 10, "Sectiekop h2 ≠ tabelkolom 0"
    except Exception as exc:
        return 7, f"Kleurcheck overgeslagen: {exc}"


def _score_render_pipeline(md: str) -> tuple[int, str]:
    try:
        from hermes_cli.display_markdown import format_response_ansi

        out = format_response_ansi(md, cols=100) or ""
        if not out.strip():
            return 5, "Renderer produceerde lege output"
        if "Functionele" in md and "Functionele" not in out:
            return 6, "Renderer mist sectie-inhoud"
        return 10, "Rich-pipeline rendert succesvol"
    except Exception as exc:
        return 5, f"Renderfout: {exc}"


def score_markdown(md: str) -> dict[str, tuple[int, str]]:
    from hermes_cli.markdown_output_normalize import normalize_assistant_markdown

    normalized = normalize_assistant_markdown(md)
    checks = {
        "checklist": _score_checklist_rendered(normalized),
        "kop_op_inhoud": _score_heading_table_tight(normalized),
        "nfr_tabel": _score_nfr_table(normalized),
        "kleur_h2_kolom0": _score_heading_vs_table_color(),
        "render_pipeline": _score_render_pipeline(normalized),
    }
    return checks


def print_report(checks: dict[str, tuple[int, str]]) -> float:
    print("=" * 60)
    print("INSTITUTIONAL RENDER SCORE")
    print("=" * 60)
    total = 0.0
    for name, (score, note) in checks.items():
        print(f"  {name:<20} {score:>4}/10  — {note}")
        total += score
    avg = total / len(checks) if checks else 0.0
    print("-" * 60)
    print(f"  TOTAAL               {avg:>4.1f}/10")
    print("=" * 60)
    return avg


def main() -> int:
    parser = argparse.ArgumentParser(description="Score institutional render quality")
    parser.add_argument(
        "--file",
        type=Path,
        help="Markdown file to score (default: embedded rooktest sample)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Exit 0 only if average score >= 9.0",
    )
    args = parser.parse_args()

    if args.file:
        md = args.file.read_text(encoding="utf-8")
    else:
        md = (
            "<institutional_check>\n- Controle hyperbolen: [Uitgevoerd]\n</institutional_check>\n\n"
            "## Projectoverzicht\n"
            "Intro.\n\n"
            "### Team Samenstelling\n"
            "| Naam | Rol | Status |\n|---|---|---|\n| A | Lead | Actief |\n\n"
            "## Functionele requirements\n"
            "| ID | Requirement | Prioriteit |\n|---|---|---|\n| FR-001 | Test | Hoog |\n\n"
            "### Niet-functionele requirements\n"
            "**Performantie**\nRender snel.\n"
            "Robuustheid — Stabiel — Test\n"
        )

    avg = print_report(score_markdown(md))
    if args.verify and avg < 9.0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
