"""Hulp bij oude LanceDB-tabellen zonder kolom `id` (handmatige migratie)."""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

import lancedb
import pyarrow as pa

from kb_schema import DB_PATH, TABLE_NAME, get_knowledge_schema, list_all_table_names


def _schema_has_id(schema: pa.Schema) -> bool:
    return "id" in schema.names


def inspect() -> int:
    db = lancedb.connect(DB_PATH)
    if TABLE_NAME not in list_all_table_names(db):
        print(f"[OK] Geen tabel '{TABLE_NAME}' — verse installatie of nog niet geïndexeerd.")
        return 0
    table = db.open_table(TABLE_NAME)
    if _schema_has_id(table.schema):
        print(f"[OK] Tabel '{TABLE_NAME}' heeft kolom 'id' (upsert-schema).")
        return 0
    print(
        f"[ACTIE] Tabel '{TABLE_NAME}' mist kolom 'id' (oud schema).\n"
        f"  Database: {DB_PATH}\n"
        f"  Opties:\n"
        f"    1) Volledige herbouw: update_knowledge.bat met J / HERMES_RAG_FRESH=1\n"
        f"    2) Backup + leeg: python scripts/rag_pipeline/schema_migrate.py --backup-and-reset\n"
        f"  Sluit Hermes/MCP af vóór wissen (LanceDB-lock)."
    )
    return 1


def backup_and_reset() -> int:
    root = Path(DB_PATH)
    if TABLE_NAME not in list_all_table_names(lancedb.connect(DB_PATH)):
        print(f"[INFO] Geen tabel '{TABLE_NAME}' — niets te migreren.")
        return 0
    table = lancedb.connect(DB_PATH).open_table(TABLE_NAME)
    if _schema_has_id(table.schema):
        print("[OK] Schema al actueel — geen migratie nodig.")
        return 0
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = root.parent / f"{root.name}.pre-id-migration.{stamp}"
    if root.exists():
        shutil.copytree(root, backup)
        print(f"[OK] Backup: {backup}")
        shutil.rmtree(root)
        print(f"[OK] Verwijderd: {root}")
    db = lancedb.connect(DB_PATH)
    db.create_table(TABLE_NAME, schema=get_knowledge_schema())
    print(f"[OK] Lege tabel '{TABLE_NAME}' met KnowledgeSchema aangemaakt. Draai daarna ingest.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="LanceDB schema-check / migratie (id-kolom).")
    parser.add_argument(
        "--backup-and-reset",
        action="store_true",
        help="Backup DB-map, wis, maak lege knowledge_base met id-schema.",
    )
    args = parser.parse_args()
    if args.backup_and_reset:
        return backup_and_reset()
    return inspect()


if __name__ == "__main__":
    sys.exit(main())
