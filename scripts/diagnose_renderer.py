#!/usr/bin/env python3
"""Unified runtime diagnostic for the institutional Rich renderer.

Prints a plain-text report showing:
- Active renderer, palette, and settings
- Whether config is loaded live or cached
- Visual ANSI demo using the actual renderer pipeline

Usage:
    python scripts/diagnose_renderer.py
    python scripts/diagnose_renderer.py --show-palettes   # visual demo of all palettes
    python scripts/diagnose_renderer.py --verify            # exit 0 if demo palette active
"""
from __future__ import annotations

import argparse
import shutil
import sys


def _get_settings() -> dict:
    try:
        from hermes_cli.display_markdown import get_assistant_render_settings

        return get_assistant_render_settings()
    except Exception as exc:
        return {"error": str(exc)}


def _get_config_display_block() -> dict:
    try:
        from hermes_cli.config import load_config_readonly

        display = load_config_readonly().get("display") or {}
        return display if isinstance(display, dict) else {}
    except Exception as exc:
        return {"error": str(exc)}


def _get_active_profile() -> str:
    try:
        from hermes_cli.profiles import get_active_profile

        return get_active_profile() or "(none)"
    except Exception:
        return "(unknown)"


def _get_palette_preview(palette: str, cols: int = 80) -> str | None:
    """Render a test markdown table + headings through the actual pipeline."""
    try:
        from hermes_cli.display_markdown import format_response_ansi

        test_md = (
            "<institutional_check>\n- Controle hyperbolen: [Uitgevoerd]\n</institutional_check>\n\n"
            "## Projectoverzicht\n"
            "Korte intro.\n\n"
            "### Team Samenstelling\n"
            "| Naam | Rol | Status |\n|---|---|---|\n| A | Lead | Actief |\n\n"
            "### Technische stack\n"
            "- Python 3.11\n\n"
            "## Functionele requirements\n"
            "| ID | Requirement | Prioriteit |\n|---|---|---|\n| FR-001 | Test | Hoog |\n"
        )
        return format_response_ansi(test_md, cols=cols)
    except Exception as exc:
        return f"[Render error: {exc}]"


def _nfr_prose_warning(md: str) -> str | None:
    """Warn when NFR section has no pipe table (raw model output before normalize)."""
    m = re.search(
        r"^#{1,6}\s+Niet-functionele\s+requirements\s*$",
        md,
        re.MULTILINE | re.IGNORECASE,
    )
    if not m:
        return None
    tail = md[m.end() :]
    next_h = re.search(r"^#{1,6}\s+", tail, re.MULTILINE)
    body = tail[: next_h.start()] if next_h else tail
    if body.strip() and "|" not in body:
        return (
            "NFR-sectie zonder | (prose/streepjes) — draai normalizer of pas SOUL aan"
        )
    return None


def _print_color_legend(palette: str) -> None:
    try:
        from hermes_cli.institutional_render import assistant_markdown_theme, table_header_palette

        theme = assistant_markdown_theme(palette)
        headers = table_header_palette(palette)
        h2 = theme.styles.get("markdown.h2", "")
        h3 = theme.styles.get("markdown.h3", "")
        print("\n  Kleurlegenda (sectiekop ≠ tabelkolom 0):")
        print(f"    h2 (##)              : {h2}")
        print(f"    h3 (###)             : {h3}")
        for idx, style in enumerate(headers[:4]):
            print(f"    tabel kolom {idx}      : {style}")
    except Exception as exc:
        print(f"\n  Kleurlegenda: (kon niet laden: {exc})")


def _print_report() -> None:
    settings = _get_settings()
    display = _get_config_display_block()
    profile = _get_active_profile()

    width = shutil.get_terminal_size((80, 24)).columns
    line = "=" * min(width, 72)

    print(line)
    print("HERMES INSTITUTIONAL RENDERER — RUNTIME DIAGNOSE")
    print(line)

    print(f"\n  Active profile      : {profile}")

    if "error" in settings:
        print(f"\n  [FOUT] Settings konden niet geladen worden: {settings['error']}")
        sys.exit(1)

    render_style = settings.get("assistant_render_style", "(niet gezet)")
    palette = settings.get("assistant_palette", "(niet gezet)")
    label_cols = settings.get("assistant_label_columns", "(niet gezet)")

    print(f"  Renderer style      : {render_style}")
    print(f"  Active palette      : {palette}")
    print(f"  Label columns       : {label_cols}")

    _print_color_legend(palette)

    nfr_probe = (
        "### Niet-functionele requirements\n"
        "**Performantie**\nRender snel.\n"
        "Robuustheid — Stabiel — Test\n"
    )
    nfr_warn = _nfr_prose_warning(nfr_probe)
    if nfr_warn:
        print(f"\n  [LINT] {nfr_warn}")
        try:
            from hermes_cli.markdown_output_normalize import normalize_assistant_markdown

            if _nfr_prose_warning(normalize_assistant_markdown(nfr_probe)) is None:
                print("  [LINT] Na normalize_assistant_markdown: NFR-tabel OK")
        except Exception as exc:
            print(f"  [LINT] Normalizer-check mislukt: {exc}")

    print(f"\n  Config display block:")
    for key in sorted(display.keys()):
        if key.startswith("assistant") or key in {"skin", "final_response_markdown", "streaming", "compact"}:
            print(f"    {key:<30} = {display[key]}")

    # Live vs cached detection
    try:
        from hermes_cli.config import load_config_readonly
        from hermes_cli.config import _LOAD_CONFIG_CACHE

        cache_size = len(_LOAD_CONFIG_CACHE)
        print(f"\n  Config cache state  : {cache_size} entr{'y' if cache_size == 1 else 'ies'} (load_config_readonly used)")
        print("  -> Settings are read LIVE from current config, not module-level CLI_CONFIG")
    except Exception as exc:
        print(f"\n  Config cache state  : (could not inspect: {exc})")

    print(f"\n{line}")

    # Render preview
    print("VISUELE PREVIEW (actieve palette, echte pipeline):")
    print(line)
    preview = _get_palette_preview(palette, cols=min(width, 80))
    if preview:
        print(preview)
    else:
        print("[Geen preview gegenereerd — format_response_ansi returned None]")

    print(line)
    print("EINDE DIAGNOSE")
    print(line)


def _show_all_palettes() -> None:
    """Print a visual panel for every registered palette using the actual renderer."""
    try:
        from hermes_cli.institutional_render import _PALETTES, render_institutional_assistant
        from hermes_cli.display_markdown import prepare_assistant_markdown_plain
        from rich.console import Console
    except Exception as exc:
        print(f"[FOUT] Kan renderer niet importeren: {exc}")
        sys.exit(1)

    test_md = (
        "## Stap 1: Analyse\n\n"
        "| A | B | C | D |\n"
        "|---|---|---|---|\n"
        "| x | y | z | w |\n\n"
        "**Betrokken partijen:**\n\n"
        "Ministerie van Justitie.\n\n"
        "### Juridische beoordelingsruimte\n\n"
        "Feitelijke weergave en normering."
    )
    plain = prepare_assistant_markdown_plain(test_md)
    console = Console(force_terminal=True, color_system="truecolor")

    print("=" * 72)
    print("ALLE GEREGISTREERDE PALETTEN (via echte renderer)")
    print("=" * 72)

    for name in sorted(_PALETTES.keys()):
        renderable = render_institutional_assistant(plain, palette=name, already_normalized=True)
        print(f"\n--- Palette: {name} ---")
        console.print(renderable)


def main() -> int:
    parser = argparse.ArgumentParser(description="Hermes Institutional Renderer Diagnostic")
    parser.add_argument(
        "--show-palettes",
        action="store_true",
        help="Render a preview panel for every registered palette",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Exit 0 only if institutional_rich + demo palette is active",
    )
    args = parser.parse_args()

    if args.show_palettes:
        _show_all_palettes()
        return 0

    _print_report()

    if args.verify:
        settings = _get_settings()
        style = settings.get("assistant_render_style", "")
        palette = settings.get("assistant_palette", "")
        ok = style == "institutional_rich" and palette == "demo"
        if not ok:
            print(f"\n[VERIFY FAIL] style={style} palette={palette} (expected institutional_rich + demo)")
            return 1
        print("\n[VERIFY OK] institutional_rich + demo palette active")

    return 0


if __name__ == "__main__":
    sys.exit(main())
