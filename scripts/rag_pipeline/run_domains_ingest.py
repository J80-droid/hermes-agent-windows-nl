#!/usr/bin/env python3
"""RAG-ingest voor één of alle domeinen uit domains.yaml."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from domains_config import (
    DomainSpec,
    default_domains_yaml,
    get_domain,
    load_domains,
    resolve_domain_paths,
)
from rag_mcp_verify import (
    mcp_verify_enabled,
    mcp_verify_strict,
    print_verify_result,
    verify_domain_mcp,
)
from ingest_run_summary import summary_path
from source_layout import apply_media_policy_env, restore_quarantine_files


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _rag_scripts_dir() -> Path:
    return _repo_root() / "windows" / "scripts" / "rag"


def _apply_env_for_domain(spec: DomainSpec, *, media_only: bool = False) -> Path:
    ldb, raw, profile = resolve_domain_paths(spec)
    os.environ["RAG_DOMAIN"] = spec.name
    os.environ["HERMES_LANCEDB_PATH"] = str(ldb)
    os.environ["HERMES_RAG_RAW_SOURCE"] = str(raw)
    os.environ["HERMES_HOME"] = str(profile)
    if not os.environ.get("HERMES_REPO"):
        os.environ["HERMES_REPO"] = str(_repo_root())
    for key, value in spec.ingest_env.items():
        os.environ[key] = value
    if media_only:
        os.environ["HERMES_RAG_MEDIA_ONLY"] = "1"
        apply_media_policy_env("whisper_when_missing", spec.media_ingest_env)
    else:
        os.environ.pop("HERMES_RAG_MEDIA_ONLY", None)
        apply_media_policy_env(spec.media_policy, spec.media_ingest_env)
    return raw


def _preflight_source_layout(spec: DomainSpec, raw: Path) -> None:
    if not spec.quarantine_restore:
        return
    moves = restore_quarantine_files(raw, spec.quarantine_restore)
    if not moves:
        return
    print(f"[INFO] Quarantaine -> canonieke paden ({len(moves)} bestand(en)):")
    for src, dst in moves:
        print(f"  {src} -> {dst}")


def _run_cmd_bat(bat: Path) -> int:
    if not bat.is_file():
        print(f"[ERROR] Ontbreekt: {bat}", file=sys.stderr)
        return 1
    result = subprocess.run(["cmd", "/c", str(bat)], env=os.environ.copy())
    return int(result.returncode or 0)


def ingest_domain(spec: DomainSpec, *, fresh: bool, media_only: bool = False) -> int:
    raw = _apply_env_for_domain(spec, media_only=media_only)
    _preflight_source_layout(spec, raw)
    rag_scripts = _rag_scripts_dir()
    if fresh:
        code = _run_cmd_bat(rag_scripts / "_rag_apply_fresh.bat")
        if code != 0:
            return code
    return _run_cmd_bat(rag_scripts / "_rag_run_ingest_institutional.bat")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RAG-ingest uit domains.yaml")
    parser.add_argument(
        "--domains-yaml",
        type=Path,
        default=None,
        help="Pad naar domains.yaml (default: %%USERPROFILE%%/data/domains.yaml)",
    )
    parser.add_argument("--list", action="store_true", help="Toon domeinen en stop")
    parser.add_argument("--all", action="store_true", help="Alle domeinen uit yaml")
    parser.add_argument(
        "--domain",
        action="append",
        dest="domains",
        metavar="NAME",
        help="Alleen dit domein (herhaalbaar)",
    )
    parser.add_argument(
        "--skip-mcp-verify",
        action="store_true",
        help="Geen MCP post-verify na ingest",
    )
    parser.add_argument(
        "--mcp-verify-only",
        action="store_true",
        help="Alleen MCP testen (geen ingest)",
    )
    parser.add_argument(
        "--media-only",
        action="store_true",
        help="Alleen audio/video zonder sidecar (Whisper); gebruikt media_ingest_env uit yaml",
    )
    args = parser.parse_args(argv)

    if args.skip_mcp_verify:
        os.environ["HERMES_RAG_SKIP_MCP_VERIFY"] = "1"

    yaml_path = args.domains_yaml or default_domains_yaml()

    if args.list:
        for spec in load_domains(yaml_path):
            desc = f" — {spec.description}" if spec.description else ""
            mcp = spec.resolved_mcp_name()
            print(f"{spec.name}: {spec.source_dir} [MCP: {mcp}]{desc}")
        return 0

    if args.all:
        specs = load_domains(yaml_path)
    elif args.domains:
        specs = [get_domain(n, yaml_path) for n in args.domains]
    else:
        parser.error("Geef --all, --domain NAME, of --list")

    repo = _repo_root()

    if args.mcp_verify_only:
        verify_results = [verify_domain_mcp(s, repo_root=repo) for s in specs]
        for r in verify_results:
            print_verify_result(r)
        if mcp_verify_strict() and any(not r.ok for r in verify_results):
            return 1
        return 0

    fresh = os.environ.get("HERMES_RAG_FRESH", "").strip().lower() in (
        "1",
        "j",
        "yes",
        "true",
    )

    verify_results = []
    for spec in specs:
        print()
        print("=" * 52)
        print(f"  Domein: {spec.name}")
        print("=" * 52)
        code = ingest_domain(spec, fresh=fresh, media_only=args.media_only)
        ldb, _, _ = resolve_domain_paths(spec)
        if code != 0:
            print(f"[ERROR] {spec.name} ingest mislukt (exit {code})", file=sys.stderr)
            return code
        summary_path = ldb / "rag_ingest_run_summary.json"
        if summary_path.is_file():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            if summary.get("skipped_total", 0) > 0:
                print(
                    f"[WARN] {spec.name}: {summary['skipped_total']} bron(nen) overgeslagen — "
                    f"zie eindrapport hierboven.",
                    file=sys.stderr,
                )
        if mcp_verify_enabled():
            print()
            print(f"-- Post-verify MCP: {spec.resolved_mcp_name()} --")
            result = verify_domain_mcp(spec, repo_root=repo)
            print_verify_result(result)
            verify_results.append(result)

    print()
    print(f"[OK] {len(specs)} domein(en) verwerkt.")
    if mcp_verify_enabled() and mcp_verify_strict() and any(not r.ok for r in verify_results):
        print("[ERROR] Eén of meer MCP-verificaties mislukt (HERMES_RAG_MCP_VERIFY_STRICT=1)")
        return 1
    if mcp_verify_enabled() and verify_results and all(r.ok for r in verify_results):
        print("[OK] Alle MCP-servers bereikbaar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
