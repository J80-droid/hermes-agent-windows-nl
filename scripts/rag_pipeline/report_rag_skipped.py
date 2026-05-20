"""Genereer of verrijk overgeslagen-rapport (live ingest JSON of parse rag_ingest_run.log)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from ingest_skip_report import SkipEntry, SkipReport, default_report_path


def _default_raw_root() -> Path:
    raw = (os.getenv("HERMES_RAG_RAW_SOURCE") or "").strip()
    return Path(
        os.path.normpath(
            os.path.expanduser(os.path.expandvars(raw if raw else "~/data/raw_source_files"))
        )
    )


def _default_log_path() -> Path:
    env = (os.environ.get("HERMES_RAG_INGEST_LOG") or "").strip()
    if env:
        return Path(os.path.expanduser(os.path.expandvars(env)))
    here = Path(__file__).resolve().parent
    return here.parent.parent / "windows" / "scripts" / "rag_ingest_run.log"


def _load_existing(path: Path) -> SkipReport:
    if not path.is_file():
        return SkipReport()
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = []
    for e in data.get("entries") or []:
        entries.append(
            SkipEntry(
                relative_source=e["relative_source"],
                reason=e.get("reason", ""),
                detail=e.get("detail", ""),
                size_bytes=e.get("size_bytes"),
                ocr_attempted=bool(e.get("ocr_attempted")),
                ocr_method=e.get("ocr_method", ""),
            )
        )
    return SkipReport(entries=entries)


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG overgeslagen PDF/PNG — rapport uit log of bestaand JSON.")
    parser.add_argument("--log", type=Path, default=None, help="Pad naar rag_ingest_run.log")
    parser.add_argument("--raw-root", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None, help="JSON-uitvoer (default: naast LanceDB)")
    args = parser.parse_args()

    raw_root = args.raw_root or _default_raw_root()
    out_path = args.out or default_report_path()
    report = _load_existing(out_path)

    log_path = args.log or _default_log_path()
    added = report.merge_from_log(log_path, raw_root)
    written = report.write(out_path)
    print(f"[OK] Rapport: {written}")
    print(f"[OK] Markdown: {written.with_suffix('.md')}")
    print(f"[INFO] {added} regel(s) uit log; totaal {len(report.entries)} overgeslagen.")


if __name__ == "__main__":
    main()
