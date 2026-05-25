"""Bouw .hermes_rag_ingest_state.json uit bestaande LanceDB + bronbestanden op schijf.

Geen re-embed: alleen mtime/size/hash zodat incrementele ingest (N) snel wordt.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from ingest_state import IngestState, state_file_path
from kb_schema import DB_PATH, TABLE_NAME, list_all_table_names
from knowledge_repository import KnowledgeRepository

try:
    import pyarrow.compute as pc
except ImportError as e:
    print(f"[ERROR] Vereist pyarrow: {e}", file=sys.stderr)
    sys.exit(1)

logger = logging.getLogger(__name__)


def _default_raw_root() -> Path:
    raw = (os.getenv("HERMES_RAG_RAW_SOURCE") or "").strip()
    return Path(
        os.path.normpath(
            os.path.expanduser(os.path.expandvars(raw if raw else "~/data/raw_source_files"))
        )
    )


def _normalize_db_source_value(val) -> str | None:
    if val is None:
        return None
    normalized = str(val).replace("\\", "/")
    return normalized or None


def _collect_sources_from_scan(table) -> list[str] | None:
    """Column-scan zonder volledige tabel in RAM; None = gebruik arrow-fallback."""
    sources: set[str] = set()
    try:
        dataset = table.to_lance()
        for batch in dataset.scan(columns=["source"]).to_batches():
            col = batch.column("source")
            for i in range(batch.num_rows):
                normalized = _normalize_db_source_value(col[i].as_py())
                if normalized:
                    sources.add(normalized)
        return sorted(sources)
    except Exception as exc:
        logger.debug("Column scan for source failed, falling back to to_arrow: %s", exc)
        return None


def _collect_sources_from_arrow(table) -> list[str]:
    try:
        arrow = table.to_arrow()
    except Exception as arrow_exc:
        logger.warning("Could not read LanceDB sources: %s", arrow_exc)
        return []
    if "source" not in arrow.column_names:
        return []

    out: list[str] = []
    for s in pc.unique(arrow["source"]):
        normalized = _normalize_db_source_value(s.as_py())
        if normalized:
            out.append(normalized)
    return sorted(out)


def _unique_sources_from_table(table) -> list[str]:
    """Collect distinct ``source`` values without loading the full table into RAM."""
    scanned = _collect_sources_from_scan(table)
    if scanned is not None:
        return scanned
    return _collect_sources_from_arrow(table)


def _is_safe_relative_key(rel_key: str) -> bool:
    rel_key = str(rel_key).replace("\\", "/").strip()
    if not rel_key or rel_key.startswith("/"):
        return False
    return ".." not in Path(rel_key).parts


def _resolve_source_file(raw_root: Path, rel_key: str) -> Path | None:
    """Map DB ``source`` to a file under ``raw_root``; reject path traversal."""
    if not _is_safe_relative_key(rel_key):
        return None

    rel_key = str(rel_key).replace("\\", "/").strip()
    root = raw_root.resolve()
    try:
        candidate = (root / Path(rel_key)).resolve()
        candidate.relative_to(root)
    except (OSError, ValueError):
        return None
    return candidate if candidate.is_file() else None


def _load_sources_from_knowledge_table() -> list[str]:
    repo = KnowledgeRepository(db_path=str(DB_PATH))
    with repo.session() as db:
        if TABLE_NAME not in list_all_table_names(db):
            return []
        table = db.open_table(TABLE_NAME)
        return _unique_sources_from_table(table)


def _match_sources_on_disk(state: IngestState, raw_root: Path, sources: list[str]) -> int:
    matched = 0
    for rel_key in sources:
        file_path = _resolve_source_file(raw_root, rel_key)
        if file_path is None:
            continue
        if state.bootstrap_entry(rel_key, file_path):
            matched += 1
    return matched


def bootstrap_from_lancedb(raw_root: Path, *, dry_run: bool = False) -> tuple[int, int, int]:
    """Return (unieke bronnen in DB, bestanden op schijf gematcht, state-entries)."""
    sources = _load_sources_from_knowledge_table()
    state = IngestState.load()
    matched = _match_sources_on_disk(state, raw_root, sources)
    entry_count = len(state.entries)

    if dry_run:
        return len(sources), matched, entry_count

    if matched:
        state.save()
    return len(sources), matched, entry_count


def _print_bootstrap_summary(
    *,
    in_db: int,
    matched: int,
    entries: int,
    dry_run: bool,
) -> None:
    dest = state_file_path()
    print(f"[INFO] LanceDB: {DB_PATH}")
    print(f"[INFO] Bronnen in tabel (uniek): {in_db}")
    print(f"[INFO] Gematcht op schijf: {matched}")
    if dry_run:
        print(f"[INFO] Dry-run: zou {entries} entries schrijven naar {dest}")
        return
    if matched:
        print(f"[OK] Ingest-staat geschreven: {dest} ({entries} bronnen)")
        return
    print("[WARN] Geen entries geschreven (geen overlap DB ↔ bronmap?).", file=sys.stderr)
    sys.exit(1)


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
    _print_bootstrap_summary(in_db=in_db, matched=matched, entries=entries, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
