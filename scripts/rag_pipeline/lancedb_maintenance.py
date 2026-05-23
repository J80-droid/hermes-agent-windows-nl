#!/usr/bin/env python3
"""Multi-domain LanceDB maintenance: list, schema inspect, compact, query benchmark."""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import lancedb
import pyarrow as pa

from domains_config import DomainSpec, default_domains_yaml, load_domains, resolve_domain_paths
from kb_schema import TABLE_NAME, list_all_table_names

RAG_DIR = Path(__file__).resolve().parent
REPO_ROOT = RAG_DIR.parents[1]


@dataclass
class DomainReport:
    name: str
    lancedb_path: Path
    exists: bool
    has_table: bool
    row_count: int | None
    schema_ok: bool | None
    schema_note: str
    compact_note: str = ""
    benchmark_p50_ms: float | None = None
    benchmark_p95_ms: float | None = None
    benchmark_error: str = ""


def _schema_has_id(schema: pa.Schema) -> bool:
    return "id" in schema.names


def _dir_size_bytes(path: Path) -> int:
    if not path.is_dir():
        return 0
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                pass
    return total


def _ingest_running() -> bool:
    try:
        import subprocess

        out = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "windows" / "scripts" / "check_rag_ingest_running.ps1"),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return out.returncode != 0
    except Exception:
        return False


def inspect_domain(spec: DomainSpec) -> DomainReport:
    ldb_path, _raw, _profile = resolve_domain_paths(spec)
    rep = DomainReport(
        name=spec.name,
        lancedb_path=ldb_path,
        exists=ldb_path.is_dir(),
        has_table=False,
        row_count=None,
        schema_ok=None,
        schema_note="",
    )
    if not rep.exists:
        rep.schema_note = "pad ontbreekt"
        return rep

    try:
        db = lancedb.connect(str(ldb_path))
        names = list_all_table_names(db)
        if TABLE_NAME not in names:
            rep.schema_note = f"geen tabel '{TABLE_NAME}'"
            return rep
        rep.has_table = True
        table = db.open_table(TABLE_NAME)
        rep.row_count = table.count_rows()
        if _schema_has_id(table.schema):
            rep.schema_ok = True
            rep.schema_note = "id-kolom aanwezig (upsert-schema)"
        else:
            rep.schema_ok = False
            rep.schema_note = "oud schema zonder id — schema_migrate.py of fresh ingest"
    except Exception as exc:
        rep.schema_note = f"fout: {exc}"
    return rep


def compact_domain(spec: DomainSpec, *, dry_run: bool) -> str:
    rep = inspect_domain(spec)
    if not rep.has_table:
        return rep.schema_note or "geen tabel"
    if dry_run:
        return "dry-run: zou compact_files() aanroepen"
    try:
        db = lancedb.connect(str(rep.lancedb_path))
        table = db.open_table(TABLE_NAME)
        table.compact_files()
        try:
            table.optimize()
            return "compact_files + optimize OK"
        except Exception as opt_exc:
            return f"compact_files OK; optimize overgeslagen: {opt_exc}"
    except Exception as exc:
        return f"compact mislukt: {exc}"


def benchmark_domain(spec: DomainSpec, *, queries: int, query_text: str) -> tuple[float | None, float | None, str]:
    rep = inspect_domain(spec)
    if not rep.has_table or not rep.row_count:
        return None, None, rep.schema_note or "lege of ontbrekende tabel"
    try:
        db = lancedb.connect(str(rep.lancedb_path))
        table = db.open_table(TABLE_NAME)
        samples: list[float] = []
        for _ in range(max(1, queries)):
            t0 = time.perf_counter()
            table.search(query_text).limit(5).to_list()
            samples.append((time.perf_counter() - t0) * 1000.0)
        if not samples:
            return None, None, "geen samples"
        p50 = statistics.median(samples)
        p95 = sorted(samples)[min(len(samples) - 1, int(len(samples) * 0.95))]
        return p50, p95, ""
    except Exception as exc:
        return None, None, str(exc)


def _format_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n //= 1024
    return f"{n:.0f} TB"


def run_list(domains: list[DomainSpec]) -> int:
    print(f"domains.yaml: {default_domains_yaml()}")
    print(f"Domeinen: {len(domains)}")
    print("-" * 72)
    for spec in domains:
        rep = inspect_domain(spec)
        size = _format_bytes(_dir_size_bytes(rep.lancedb_path)) if rep.exists else "—"
        rows = str(rep.row_count) if rep.row_count is not None else "—"
        print(f"  {rep.name:<14} rows={rows:<8} size={size:<10} {rep.lancedb_path}")
    return 0


def run_inspect(domains: list[DomainSpec], *, report_path: Path | None) -> int:
    lines: list[str] = [
        f"# LanceDB schema audit — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"Bron: `{default_domains_yaml()}`",
        "",
        "| Domein | Pad | Tabel | Rijen | Schema | Notitie |",
        "|--------|-----|-------|-------|--------|---------|",
    ]
    exit_code = 0
    for spec in domains:
        rep = inspect_domain(spec)
        status = "OK" if rep.schema_ok else ("ACTIE" if rep.schema_ok is False else "—")
        if rep.schema_ok is False:
            exit_code = 1
        lines.append(
            f"| {rep.name} | `{rep.lancedb_path}` | "
            f"{'ja' if rep.has_table else 'nee'} | {rep.row_count or '—'} | {status} | {rep.schema_note} |"
        )
        print(f"[{status}] {rep.name}: {rep.schema_note}")

    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nRapport: {report_path}")
    return exit_code


def run_compact(domains: list[DomainSpec], *, dry_run: bool, domain_filter: str | None) -> int:
    if _ingest_running():
        print("[ERROR] RAG-ingest actief — stop ingest vóór compact.", file=sys.stderr)
        return 2
    targets = domains
    if domain_filter:
        targets = [d for d in domains if d.name.lower() == domain_filter.lower()]
        if not targets:
            print(f"[ERROR] Onbekend domein: {domain_filter}", file=sys.stderr)
            return 1
    for spec in targets:
        note = compact_domain(spec, dry_run=dry_run)
        print(f"  {spec.name}: {note}")
    return 0


def run_benchmark(
    domains: list[DomainSpec],
    *,
    queries: int,
    query_text: str,
    max_ms: float | None,
    domain_filter: str | None,
) -> int:
    targets = domains
    if domain_filter:
        targets = [d for d in domains if d.name.lower() == domain_filter.lower()]
    exit_code = 0
    print(f"Query: {query_text!r}  (n={queries})")
    print("-" * 72)
    for spec in targets:
        p50, p95, err = benchmark_domain(spec, queries=queries, query_text=query_text)
        if err:
            print(f"  {spec.name:<14} SKIP — {err}")
            continue
        over = ""
        if max_ms is not None and p95 is not None and p95 > max_ms:
            exit_code = 1
            over = f"  [FAIL > {max_ms}ms]"
        print(f"  {spec.name:<14} p50={p50:.1f}ms  p95={p95:.1f}ms{over}")
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="LanceDB multi-domain maintenance")
    parser.add_argument("--domains-yaml", type=Path, help="Override domains.yaml pad")
    parser.add_argument("--domain", help="Alleen dit domein (naam)")
    parser.add_argument("--dry-run", action="store_true", help="Geen schrijfacties (compact)")
    parser.add_argument("--list", action="store_true", help="Toon domeinen + paden")
    parser.add_argument("--inspect", action="store_true", help="Schema-audit per domein")
    parser.add_argument(
        "--report",
        type=Path,
        help="Markdown-rapport bij --inspect (default: windows/audits/LANCEDB_SCHEMA_AUDIT_<datum>.md)",
    )
    parser.add_argument("--compact", action="store_true", help="compact_files per tabel")
    parser.add_argument("--benchmark", action="store_true", help="Zoek-latency per domein")
    parser.add_argument("--queries", type=int, default=5, help="Queries per domein (benchmark)")
    parser.add_argument("--query", default="test", help="Zoektekst (benchmark)")
    parser.add_argument("--max-ms", type=float, default=None, help="Fail benchmark als p95 > drempel")
    args = parser.parse_args()

    yaml_path = args.domains_yaml or default_domains_yaml()
    if not yaml_path.is_file():
        print(f"[ERROR] domains.yaml niet gevonden: {yaml_path}", file=sys.stderr)
        return 1

    domains = load_domains(yaml_path)
    if not (args.list or args.inspect or args.compact or args.benchmark):
        parser.print_help()
        return 0

    code = 0
    if args.list:
        code = max(code, run_list(domains))
    if args.inspect:
        repo = RAG_DIR.parents[1]
        default_report = (
            repo
            / "windows"
            / "audits"
            / f"LANCEDB_SCHEMA_AUDIT_{datetime.now().strftime('%Y-%m-%d')}.md"
        )
        code = max(code, run_inspect(domains, report_path=args.report or default_report))
    if args.compact:
        code = max(code, run_compact(domains, dry_run=args.dry_run, domain_filter=args.domain))
    if args.benchmark:
        code = max(code, run_benchmark(
            domains,
            queries=args.queries,
            query_text=args.query,
            max_ms=args.max_ms,
            domain_filter=args.domain,
        ))
    return code


if __name__ == "__main__":
    sys.exit(main())
