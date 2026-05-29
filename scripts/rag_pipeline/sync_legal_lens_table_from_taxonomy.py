"""Patch ## Juridische lenzen table in legal SOUL from docs/LEGAL_TAXONOMY.md (review verplicht)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TAXONOMY = REPO / "docs" / "LEGAL_TAXONOMY.md"
TEMPLATE = REPO / "docs" / "templates" / "SOUL_LEGAL_DOMAIN.md"
LENS_HEADER = "## Juridische lenzen"
MULTI_HEADER = "### Multi-lens"


def _parse_taxonomy_rows(text: str) -> list[tuple[str, str, str]]:
    """Return (signals, lens, submap) from active lenses table."""
    rows: list[tuple[str, str, str]] = []
    in_table = False
    for line in text.splitlines():
        if line.startswith("| id |"):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|") or line.startswith("|----"):
            if in_table and rows:
                break
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) < 5:
            continue
        _id, lens, signals, submap, _tag, status = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
        if status.strip() != "active":
            continue
        rows.append((signals, lens, submap.strip("`")))
    return rows


def build_lens_section(rows: list[tuple[str, str, str]]) -> str:
    lines = [
        LENS_HEADER,
        "Canonieke taxonomie: repo `docs/LEGAL_TAXONOMY.md`. Samenvatting:",
        "",
        "| Signaal (indicatief) | Lens | Bron-submap |",
        "|----------------------|------|-------------|",
    ]
    for signals, lens, submap in rows:
        lines.append(f"| {signals} | {lens} | `{submap}` |")
    lines.append("")
    return "\n".join(lines)


def patch_soul(soul_path: Path, lens_block: str, dry_run: bool) -> bool:
    text = soul_path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"(?ms)^{re.escape(LENS_HEADER)}.*?(?=^{re.escape(MULTI_HEADER)})"
    )
    if not pattern.search(text):
        print(f"[ERROR] Sectie {LENS_HEADER} niet gevonden in {soul_path}", file=sys.stderr)
        return False
    new_text = pattern.sub(lens_block + "\n", text, count=1)
    if new_text == text:
        print("[INFO] Geen wijziging nodig")
        return True
    if dry_run:
        print(f"[DRY-RUN] Zou patchen: {soul_path}")
        return True
    soul_path.write_text(new_text, encoding="utf-8")
    print(f"[OK] Bijgewerkt: {soul_path}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--soul", type=Path, help="Pad naar legal SOUL.md (default: template)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not TAXONOMY.is_file():
        print(f"[ERROR] Ontbreekt: {TAXONOMY}", file=sys.stderr)
        return 1

    rows = _parse_taxonomy_rows(TAXONOMY.read_text(encoding="utf-8"))
    if not rows:
        print("[ERROR] Geen active rijen in taxonomie", file=sys.stderr)
        return 1

    lens_block = build_lens_section(rows)
    soul = args.soul or TEMPLATE
    if not soul.is_file():
        print(f"[ERROR] SOUL niet gevonden: {soul}", file=sys.stderr)
        return 1

    ok = patch_soul(soul, lens_block, args.dry_run)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
