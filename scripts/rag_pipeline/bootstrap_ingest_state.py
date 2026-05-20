"""Bouw .hermes_rag_ingest_state.json uit bestaande LanceDB + bronbestanden op schijf.

Geen re-embed: alleen mtime/size/hash zodat incrementele ingest (N) snel wordt.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from ingest_state import IngestState, state_file_path
from kb_schema import DB_PATH, TABLE_NAME, list_all_table_names

try:
    import lancedb
    import pyarrow.compute as pc
except ImportError as e:
    print(f"[ERROR] Vereist lancedb/pyarrow: {e}", file=sys.stderr)
    sys.exit(1)


def _default_raw_root() -> Path:
    raw = (os.getenv("HERMES_RAG_RAW_SOURCE") or "").strip()
    return Path(
        os.path.normpath(
            os.path.expanduser(os.path.expandvars(raw if raw else "~/data/raw_source_files"))
        )
    )


def bootstrap_from_lancedb(raw_root: Path, *, dry_run: bool = False) -> tuple[int, int, int]:
    """Return (unieke bronnen in DB, bestanden op schijf gematcht, state-entries)."""
    db = lancedb.connect(DB_PATH)
    if TABLE_NAME not in list_all_table_names(db):
        return 0, 0, 0

    table = db.open_table(TABLE_NAME)
    arrow = table.to_arrow()
    if "source" not in arrow.column_names:
        return 0, 0, 0
    unique = pc.unique(arrow["source"])
    sources = sorted(s.as_py() for s in unique if s.as_py())

    state = IngestState.load()
    matched = 0
    for rel in sources:
        rel_key = str(rel).replace("\\", "/")
        fp = raw_root / Path(rel_key)
        if not fp.is_file():
            continue
        if state.bootstrap_entry(rel_key, fp):
            matched += 1

    if dry_run:
        return len(sources), matched, len(state.entries)

    if matched:
        state.save()
    return len(sources), matched, len(state.entries)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Maak/herstel .hermes_rag_ingest_state.json vanuit LanceDB (geen re-index)."
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=None,
        help="Bronmap (default: HERMES_RAG_RAW_SOURCE of ~/data/raw_source_files)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Tel alleen, schrijf niet.")
    args = parser.parse_args()
    raw_root = args.raw_root or _default_raw_root()
    if not raw_root.is_dir():
        print(f"[ERROR] Bronmap niet gevonden: {raw_root}", file=sys.stderr)
        sys.exit(1)

    in_db, matched, entries = bootstrap_from_lancedb(raw_root, dry_run=args.dry_run)
    dest = state_file_path()
    print(f"[INFO] LanceDB: {DB_PATH}")
    print(f"[INFO] Bronnen in tabel (uniek): {in_db}")
    print(f"[INFO] Gematcht op schijf: {matched}")
    if args.dry_run:
        print(f"[INFO] Dry-run: zou {entries} entries schrijven naar {dest}")
        return
    if matched:
        print(f"[OK] Ingest-staat geschreven: {dest} ({entries} bronnen)")
    else:
        print("[WARN] Geen entries geschreven (geen overlap DB ↔ bronmap?).", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
