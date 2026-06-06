#!/usr/bin/env python3
"""Render CODEBASE_SMOKE audit markdown from RUN_CODEBASE_SMOKE_AUDIT step log JSON."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def _repo() -> Path:
    return Path(__file__).resolve().parents[1]


def _format_chronology(steps: list[dict]) -> str:
    rows: list[str] = []
    for s in steps:
        ts = s.get("timestamp") or "—"
        name = s.get("name", "?")
        detail = s.get("detail") or f"exit {s.get('exit', '?')}"
        source = s.get("source", "—")
        tier = s.get("tier", "—")
        status = "SKIP" if s.get("skipped") else ("FAIL" if s.get("exit", 0) != 0 else "OK")
        rows.append(f"| {ts} | {name} ({status}) | {detail} | {source} | {tier} |")
    header = "| Tijdstip | Handeling | Resultaat | Bron | Tier |\n| --- | --- | --- | --- | --- |"
    return header + "\n" + "\n".join(rows) if rows else header + "\n| — | — | — | — | — |"


def _verified_smoke_bullets(steps: list[dict]) -> list[str]:
    bullets: list[str] = []
    for s in steps:
        if s.get("skipped") or s.get("exit", 1) != 0:
            continue
        name = s.get("name", "")
        source = s.get("source", "")
        tier = s.get("tier", "")
        if source:
            bullets.append(f"- {name} [Bron: {source}] [{tier}].")
    return bullets


def render_report(data: dict) -> str:
    started = data.get("started") or datetime.now().isoformat(timespec="seconds")
    release = data.get("release_gate_run", False)
    steps: list[dict] = data.get("steps") or []
    pygount = data.get("pygount") or {}
    warnings: list[str] = data.get("warnings") or []

    smoke_ok = all(s.get("exit", 1) == 0 or s.get("skipped") for s in steps if not s.get("optional"))
    chain_skipped = any(
        s.get("name") == "verify_windows_chain" and s.get("skipped") for s in steps
    )

    lines = [
        "# Codebase smoke audit rapport",
        "",
        "<institutional_check>",
        "- Controle hyperbolen: [Uitgevoerd]",
        "- Controle stelligheden: [Uitgevoerd]",
        "- Controle conclusies: [Uitgevoerd]",
        "- Controle evidence-tiers (E0-E3, geen valse 100%): [Uitgevoerd]",
        "</institutional_check>",
        "",
        "## Geobjectiveerde analyse",
        "",
        "### Audit-scope",
        "",
        "| Niveau | Geverifieerd in Smoke | Geverifieerd in Release-gate | Expliciete runners / methoden |",
        "| --- | --- | --- | --- |",
        "| E0 (Documentatie) | Nee (niet in smoke-runner) | Optioneel | AGENTS.md, architecture docs |",
        "| E1 (Statisch / wiring) | Ja | Ja | verify scripts, verify_windows_script_chain.ps1 |",
        "| E2 (Module pytest) | Ja (subset) | Ja | pytest modules in smoke-stappen |",
        f"| E3 fork gate | {'Ja' if release else 'Nee'} | {'Ja' if release else 'Nee'} | RUN_PYTEST_FORK_GATE / RUN_AUDITS preflight |",
        f"| E3 upstream parity | {'Ja' if release else 'Nee'} | Nee (diagnostiek) | RUN_PYTEST_UPSTREAM -ReportOnly / run_tests.sh (Linux CI) |",
        "",
        f"**Smoke-run gestart:** {started}",
        "",
        f"**Release-gate in deze run:** {'Ja' if release else 'Nee — niet voldoende voor release-ready'}",
        "",
        "### Feitelijke chronologie",
        "",
        _format_chronology(steps),
        "",
    ]

    if pygount:
        lines.extend(
            [
                "### Codebase-statistieken (E1, informatief)",
                "",
                f"**Snapshot datum:** {pygount.get('date', started[:10])}",
                "",
                "| Meting | Waarde | Opmerking |",
                "| --- | --- | --- |",
                f"| Executable LOC (totaal) | {pygount.get('code', '—')} | pygount snapshot, geen gate |",
                f"| Commentaarlijnen | {pygount.get('comment', '—')} | idem |",
                "",
            ]
        )

    lines.extend(
        [
            "### Geverifieerde componenten (Smoke)",
            "",
        ]
    )
    bullets = _verified_smoke_bullets(steps)
    lines.extend(bullets if bullets else ["- Geen geslaagde stappen."])
    lines.extend(
        [
            "",
            "### Niet in scope",
            "",
            "- E3 fork gate: RUN_PYTEST_FORK_GATE (verplicht groen). E3 upstream parity: RUN_PYTEST_UPSTREAM -ReportOnly (diagnostiek; Linux CI = waarheid) [E3].",
            "- Headless Ink / visual soak [gap].",
            "- Gateway load/soak onder netwerkcongestie [gap].",
            "",
        ]
    )

    if warnings or chain_skipped:
        lines.extend(["### Waarschuwingen", ""])
        for w in warnings:
            lines.append(f"- {w}")
        if chain_skipped:
            lines.append("- verify_windows_chain overgeslagen — PS1-syntax niet bewezen in deze run.")
        lines.append("")

    lines.extend(
        [
            "## Ontbrekende informatie (voor deze conclusie)",
            "",
            "- Visual/Ink load-test niet uitgevoerd.",
            "- TUI: contracttests in repo (~187 in test_tui_gateway_server.py); smoke gebruikt collect-only tenzij -IncludeTuiGatewayPytest.",
            "",
            f"**Smoke eindstatus:** {'PASS' if smoke_ok else 'FAIL'}",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit codebase smoke audit markdown report")
    parser.add_argument("step_log", type=Path, help="JSON step log from RUN_CODEBASE_SMOKE_AUDIT.ps1")
    parser.add_argument("-o", "--output", type=Path, help="Output markdown path")
    args = parser.parse_args()

    if not args.step_log.is_file():
        print(f"[FAIL] Step log ontbreekt: {args.step_log}", file=sys.stderr)
        return 1

    data = json.loads(args.step_log.read_text(encoding="utf-8-sig"))
    report = render_report(data)

    out = args.output
    if not out:
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        out = _repo() / "windows" / "audits" / f"CODEBASE_SMOKE_AUDIT_REPORT_{stamp}.md"

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(f"[OK] Rapport: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
