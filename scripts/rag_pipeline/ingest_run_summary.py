"""Eindrapport na RAG-ingest: console + JSON."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from ingest_skip_report import SkipReport
from ingest_state import state_file_path

SUMMARY_BASENAME = "rag_ingest_run_summary.json"


def summary_path(db_path: str | Path) -> Path:
    return Path(db_path) / SUMMARY_BASENAME


def build_summary_payload(
    *,
    domain: str,
    db_path: str,
    raw_source: str,
    scan_total: int,
    queued: int,
    indexed_this_run: int,
    unchanged_skipped: int,
    removed_from_index: list[str],
    skip_report: SkipReport,
    total_sources_in_state: int,
    fresh_run: bool,
    media_policy_note: str = "",
) -> dict:
    by_reason: dict[str, int] = dict(Counter(e.reason for e in skip_report.entries))
    skipped_list = [
        {
            "path": e.relative_source,
            "reason": e.reason,
            "detail": e.detail,
            "size_mb": round(e.size_bytes / (1024 * 1024), 2) if e.size_bytes else None,
        }
        for e in skip_report.entries
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "db_path": db_path,
        "raw_source": raw_source,
        "fresh_run": fresh_run,
        "media_policy_note": media_policy_note,
        "scan_total_files": scan_total,
        "queued_for_processing": queued,
        "indexed_this_run": indexed_this_run,
        "unchanged_skipped_incremental": unchanged_skipped,
        "total_sources_in_index_state": total_sources_in_state,
        "removed_from_index": removed_from_index,
        "skipped_total": len(skip_report.entries),
        "skipped_by_reason": by_reason,
        "skipped_entries": skipped_list,
        "all_sources_indexed": len(skip_report.entries) == 0,
        "skip_report_json": str(Path(db_path) / "rag_ingest_skipped_report.json"),
        "skip_report_md": str(Path(db_path) / "rag_ingest_skipped_report.md"),
        "ingest_state_json": str(state_file_path()),
    }


def _print_summary_console(payload: dict, *, title: str = "RAG INGEST — EINDRAPPORT") -> None:
    sep = "=" * 58
    print()
    print(sep)
    print(f"  {title}")
    print(sep)
    print(f"  Domein:        {payload.get('domain', '?')}")
    print(f"  Database:      {payload.get('db_path', '')}")
    print(f"  Bronmap:       {payload.get('raw_source', '')}")
    if payload.get("media_policy_note"):
        print(f"  Media-beleid:  {payload['media_policy_note']}")
    print()
    print(f"  Gescand:              {payload.get('scan_total_files', 0)} bestand(en)")
    print(f"  Verwerkt deze run:    {payload.get('queued_for_processing', 0)}")
    print(f"  Nieuw/geupdate index: {payload.get('indexed_this_run', 0)}")
    print(f"  Ongewijzigd (incr.):  {payload.get('unchanged_skipped_incremental', 0)}")
    print(f"  Totaal in index:      {payload.get('total_sources_in_index_state', 0)} bronnen")
    removed = payload.get("removed_from_index") or []
    if removed:
        print(f"  Uit index verwijderd: {len(removed)} (bron niet meer in scan)")
        for rel in removed[:8]:
            print(f"    - {rel}")
        if len(removed) > 8:
            print(f"    ... en {len(removed) - 8} meer")
    skipped = payload.get("skipped_total", 0)
    print()
    if skipped == 0:
        print("  Overgeslagen:         0  [OK]")
    else:
        print(f"  Overgeslagen:         {skipped}  [ACTIE NODIG]")
        for reason, count in sorted((payload.get("skipped_by_reason") or {}).items()):
            print(f"    - {reason}: {count}")
        print()
        print("  Details (eerste 15):")
        for entry in (payload.get("skipped_entries") or [])[:15]:
            detail = entry.get("detail") or ""
            extra = f" — {detail[:80]}" if detail else ""
            print(f"    * {entry['path']}")
            print(f"      reden: {entry['reason']}{extra}")
        if skipped > 15:
            print(f"    ... volledig: {payload.get('skip_report_md', '')}")
    print(sep)


def write_and_print_summary(payload: dict) -> Path:
    dest = summary_path(payload["db_path"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    _print_summary_console(payload)
    print(f"  Rapport JSON:  {dest}")
    print(f"  Skip-rapport:  {payload.get('skip_report_md', '')}")
    if payload.get("skipped_total", 0) == 0:
        print("[OK] Alle bronnen in de scan zijn geindexeerd (geen skips).")
    else:
        print("[WARN] Niet alle bronnen geindexeerd — los skips op en draai opnieuw (N).")
    print("=" * 58)
    print()
    return dest


def load_and_print_summary(db_path: str | Path) -> bool:
    path = summary_path(db_path)
    if not path.is_file():
        return False
    payload = json.loads(path.read_text(encoding="utf-8"))
    _print_summary_console(payload, title="RAG INGEST — EINDRAPPORT (samenvatting)")
    return True
