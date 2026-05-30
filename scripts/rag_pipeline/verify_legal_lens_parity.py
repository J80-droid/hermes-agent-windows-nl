"""Verify ## Juridische lenzen table matches docs/LEGAL_TAXONOMY.md active rows.

CLI: ``--soul PATH`` | ``--all`` (template + runtime SOUL) | ``--fix`` (sync script bij mismatch).
Exit 0 = parity OK; 1 = ontbrekende taxonomie, geen rijen, geen SOULs, of mismatch.
Unit tests: ``tests/scripts/test_verify_legal_lens_parity.py``.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_RAG_DIR = Path(__file__).resolve().parent
if str(_RAG_DIR) not in sys.path:
    sys.path.insert(0, str(_RAG_DIR))

TAXONOMY = REPO / "docs" / "LEGAL_TAXONOMY.md"
LENS_HEADER = "## Juridische lenzen"

from sync_legal_lens_table_from_taxonomy import (  # noqa: E402
    TEMPLATE,
    _parse_taxonomy_rows,
    resolve_soul_targets,
)


def _parse_soul_lens_rows(text: str) -> list[tuple[str, str, str]]:
    """Return (signals, lens, submap) from the Juridische lenzen table only (ignore other markdown tables)."""
    rows: list[tuple[str, str, str]] = []
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if not in_table:
            if stripped.startswith("| Signaal"):
                in_table = True
            continue
        if not stripped:
            continue
        if not stripped.startswith("|"):
            break
        if stripped.startswith("|----") or stripped.startswith("|------"):
            continue
        parts = [p.strip() for p in stripped.split("|")[1:-1]]
        if len(parts) < 3:
            break
        signals, lens, submap = parts[0], parts[1], parts[2].strip("`").strip()
        # Lens rows always have a Bron-submap folder; other tables (USER.md, parallelle) do not.
        if "/" not in submap:
            break
        rows.append((signals, lens, submap))
    return rows


def _normalize_rows(rows: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    return [
        (s.strip(), lens.strip(), submap.strip().strip("`").strip("/"))
        for s, lens, submap in rows
    ]


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
    for i, (exp, got) in enumerate(zip(expected, soul_rows)):
        if exp != got:
            print(f"  rij {i + 1}: verwacht {exp!r} vs SOUL {got!r}", file=sys.stderr)
            break
    else:
        if len(expected) != len(soul_rows):
            print("  (verschil in aantal rijen)", file=sys.stderr)
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
    checked = 0
    for soul in souls:
        if not soul.is_file():
            print(f"[WARN] Overgeslagen (ontbreekt): {soul}", file=sys.stderr)
            continue
        checked += 1
        ok = check_parity(soul, taxonomy_rows)
        if not ok and args.fix:
            sync = REPO / "scripts" / "rag_pipeline" / "sync_legal_lens_table_from_taxonomy.py"
            cmd = [sys.executable, str(sync), "--soul", str(soul)]
            fix_run = subprocess.run(cmd, cwd=str(REPO), check=False)
            if fix_run.returncode != 0:
                print(f"[ERROR] Sync mislukt (exit {fix_run.returncode}): {soul}", file=sys.stderr)
                ok_all = False
                continue
            ok = check_parity(soul, taxonomy_rows)
        ok_all = ok_all and ok

    if checked == 0:
        print("[ERROR] Geen SOUL-bestanden om te controleren", file=sys.stderr)
        return 1

    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
