#!/usr/bin/env python3
"""Inventariseer items: tel, categoriseer, rangschik, output genummerde landkaart (1..N)."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


def _split_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        s = re.sub(r"^[-*•]\s+", "", s)
        s = re.sub(r"^\d+[.)]\s+", "", s)
        if s:
            lines.append(s)
    return lines


def _guess_category(item: str) -> str:
    low = item.lower()
    if any(k in low for k in ("jurid", "legal", "gcr", "vso", "contract")):
        return "legal"
    if any(k in low for k in ("trade", "crypto", "portfolio", "markt")):
        return "trading"
    if any(k in low for k in ("rag", "ingest", "index", "mcp", "lancedb")):
        return "tech/rag"
    if any(k in low for k in ("windows", "script", "backup", "setup")):
        return "tech/windows"
    if any(k in low for k in ("profiel", "soul", "kanban")):
        return "hermes/profiles"
    return "overig"


def build_inventory(items: list[str], categories: dict[str, list[str]] | None = None) -> dict:
    if categories:
        grouped: dict[str, list[str]] = {k: list(v) for k, v in categories.items()}
        flat: list[str] = []
        for cat in sorted(grouped.keys()):
            flat.extend(grouped[cat])
        items = flat if flat else items
    else:
        grouped = defaultdict(list)
        for it in items:
            grouped[_guess_category(it)].append(it)
        grouped = dict(sorted(grouped.items(), key=lambda x: x[0]))

    ordered: list[str] = []
    for cat in grouped:
        ordered.extend(grouped[cat])

    return {
        "count": len(ordered),
        "categories": {k: len(v) for k, v in grouped.items()},
        "items": [{"index": i + 1, "text": t, "category": _guess_category(t)} for i, t in enumerate(ordered)],
        "grouped": grouped,
    }


def format_markdown(data: dict) -> str:
    n = data["count"]
    lines = [f"**Landkaart:** {n} item(s)", ""]
    if data.get("categories"):
        lines.append("**Categorieën:** " + ", ".join(f"{k} ({v})" for k, v in data["categories"].items()))
        lines.append("")
    for row in data["items"]:
        lines.append(f"{row['index']}. [{row['category']}] {row['text']}")
    lines.append("")
    lines.append(f"Welk item (1–{n}) wil je als eerste uitgewerkt?")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Landkaart-inventarisatie (tellen, categoriseren, 1..N)")
    ap.add_argument("file", nargs="?", help="Tekstbestand met één item per regel")
    ap.add_argument("--json", action="store_true", help="Alleen JSON naar stdout")
    ap.add_argument("--stdin-label", default="items", help="Label bij lezen van stdin")
    args = ap.parse_args()

    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        print("Geef items via stdin of als bestand.", file=sys.stderr)
        return 2

    items = _split_lines(text)
    data = build_inventory(items)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(format_markdown(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
