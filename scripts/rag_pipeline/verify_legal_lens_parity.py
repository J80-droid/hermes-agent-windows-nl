"""Verify ## Juridische lenzen table matches docs/LEGAL_TAXONOMY.md active rows."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TAXONOMY = REPO / "docs" / "LEGAL_TAXONOMY.md"
TEMPLATE = REPO / "docs" / "templates" / "SOUL_LEGAL_DOMAIN.md"
LENS_HEADER = "## Juridische lenzen"

# Shared with sync_legal_lens_table_from_taxonomy.py
from sync_legal_lens_table_from_taxonomy import (  # noqa: E402
    _parse_taxonomy_rows,
    resolve_soul_targets,
)


def _parse_soul_lens_rows(text: str) -> list[tuple[str, str, str]]:
    """Return (signals, lens, submap) from SOUL lens table (skip header)."""
    rows: list[tuple[str, str, str]] = []
    in_table = False
    for line in text.splitlines():
        if line.startswith("| Signaal"):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|") or line.startswith("|----"):
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) < 3:
            continue
        signals, lens, submap = parts[0], parts[1], parts[2].strip("`")
        rows.append((signals, lens, submap))
    return rows


def _normalize_rows(rows: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    return [(s.strip(), l.strip(), m.strip()) for s, l, m in rows]


def check_parity(soul_path: Path, taxonomy_rows: list[tuple[str, str, str]]) -> bool:
    if not soul_path.is_file():
        print(f"[ERROR] SOUL niet gevonden: {soul_path}", file=sys.stderr)
        return False
    text = soul_path.read_text(encoding="utf-8")
    if LENS_HEADER not in text:
        print(f"[ERROR] {LENS_HEADER} ontbreekt in {soul_path}", file=sys.stderr)
        return False
    soul_rows = _normalize_rows(_parse_soul_lens_rows(text))
    expected = _normalize_rows(taxonomy_rows)
    if soul_rows == expected:
        print(f"[OK] Parity: {soul_path.name} ({len(expected)} lenzen)")
        return True
    print(f"[FAIL] Parity mismatch: {soul_path}", file=sys.stderr)
    print(f"  taxonomie: {len(expected)} rijen, SOUL: {len(soul_rows)} rijen", file=sys.stderr)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Check template + runtime SOUL")
    parser.add_argument("--soul", type=Path, help="Single SOUL path")
    parser.add_argument("--fix", action="store_true", help="Run sync script on mismatch")
    args = parser.parse_args()

    if not TAXONOMY.is_file():
        print(f"[ERROR] Ontbreekt: {TAXONOMY}", file=sys.stderr)
        return 1

    taxonomy_rows = _parse_taxonomy_rows(TAXONOMY.read_text(encoding="utf-8"))
    if not taxonomy_rows:
        print("[ERROR] Geen active rijen in taxonomie", file=sys.stderr)
        return 1

    if args.all:
        souls = resolve_soul_targets(include_runtime=True)
    elif args.soul:
        souls = [args.soul]
    else:
        souls = [TEMPLATE]

    ok_all = True
    for soul in souls:
        if not soul.is_file():
            print(f"[WARN] Overgeslagen (ontbreekt): {soul}", file=sys.stderr)
            continue
        ok = check_parity(soul, taxonomy_rows)
        if not ok and args.fix:
            sync = REPO / "scripts" / "rag_pipeline" / "sync_legal_lens_table_from_taxonomy.py"
            cmd = [sys.executable, str(sync), "--soul", str(soul)]
            subprocess.run(cmd, check=False)
            ok = check_parity(soul, taxonomy_rows)
        ok_all = ok_all and ok

    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
