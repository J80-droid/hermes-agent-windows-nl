#!/usr/bin/env python3
"""Fork hygiene for tests/hermes_cli/ — avoid new merge conflicts.

SSOT: docs/FORK_MERGE_POLICY.md
Exceptions: windows/tests/fork_hermes_cli_test_exceptions.txt
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERMES_CLI_PREFIX = "tests/hermes_cli/"


def _repo_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return Path(__file__).resolve().parents[2]


def _norm(path: str) -> str:
    return path.replace("\\", "/").strip()


def _load_exceptions(repo: Path) -> set[str]:
    path = repo / "windows" / "tests" / "fork_hermes_cli_test_exceptions.txt"
    if not path.is_file():
        raise FileNotFoundError(f"exceptions list missing: {path}")
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.add(_norm(line))
    return out


def _git_lines(repo: Path, *args: str) -> list[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"git {' '.join(args)} failed ({proc.returncode}): {stderr}")
    return [_norm(p) for p in proc.stdout.splitlines() if p.strip()]


def _under_hermes_cli(path: str) -> bool:
    return path.startswith(HERMES_CLI_PREFIX)


def _classify(paths: list[str], exceptions: set[str]) -> dict[str, list[str]]:
    legacy: list[str] = []
    unknown: list[str] = []
    for p in paths:
        if p in exceptions:
            legacy.append(p)
        else:
            unknown.append(p)
    return {"legacy": sorted(legacy), "unknown": sorted(unknown)}


def run_pre_merge(repo: Path, upstream: str) -> dict:
    exceptions = _load_exceptions(repo)
    modified = _git_lines(repo, "diff", "--name-only", "--diff-filter=M", upstream, "--", "tests/hermes_cli/")
    added = _git_lines(repo, "diff", "--name-only", "--diff-filter=A", upstream, "--", "tests/hermes_cli/")
    merged = sorted(set(modified) | set(added))
    buckets = _classify(merged, exceptions)
    return {
        "mode": "pre-merge",
        "upstream": upstream,
        "conflict_risk_total": len(merged),
        "conflict_risk_modified": len(modified),
        "conflict_risk_added": len(added),
        "legacy_exception_paths": len(buckets["legacy"]),
        "unknown_paths": buckets["unknown"],
        "modified": sorted(modified),
        "added": sorted(added),
    }


def run_staged(repo: Path, *, suggest: bool = False) -> dict:
    exceptions = _load_exceptions(repo)
    staged_all = [
        p
        for p in _git_lines(repo, "diff", "--cached", "--name-only", "--diff-filter=ACMR")
        if _under_hermes_cli(p)
    ]
    staged_added = [
        p
        for p in _git_lines(repo, "diff", "--cached", "--name-only", "--diff-filter=A")
        if _under_hermes_cli(p)
    ]
    violations: list[str] = []
    for p in staged_added:
        if p not in exceptions:
            violations.append(p)
    return {
        "mode": "staged",
        "staged_hermes_cli": sorted(staged_all),
        "staged_added": sorted(staged_added),
        "violations": sorted(violations),
        "suggest": suggest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=None)
    parser.add_argument("--upstream", default="upstream/main")
    parser.add_argument("--pre-merge", action="store_true", help="List conflict-risk paths vs upstream")
    parser.add_argument("--staged", action="store_true", help="Fail on staged tests/hermes_cli/ outside exceptions")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--strict", action="store_true", help="With --pre-merge: fail if unknown_paths non-empty")
    parser.add_argument("--suggest", action="store_true", help="With --staged: print git restore hints for violations")
    args = parser.parse_args()

    if not args.pre_merge and not args.staged:
        parser.error("specify --pre-merge and/or --staged")

    repo = _repo_root(args.repo)
    report: dict = {"repo": str(repo)}

    exit_code = 0

    if args.pre_merge:
        pm = run_pre_merge(repo, args.upstream)
        report.update(pm)
        if pm["conflict_risk_total"]:
            print(
                f"[WARN] {pm['conflict_risk_total']} tests/hermes_cli/ pad(en) wijken af van {args.upstream} "
                f"({pm['conflict_risk_modified']} gewijzigd, {pm['conflict_risk_added']} alleen op fork).",
                file=sys.stderr,
            )
            for p in pm["modified"][:12]:
                print(f"  merge-risico (modified): {p}", file=sys.stderr)
            if len(pm["modified"]) > 12:
                print(f"  ... +{len(pm['modified']) - 12} meer", file=sys.stderr)
            print("  Zie docs/FORK_MERGE_POLICY.md - nieuwe fork-tests in tests/overlay/", file=sys.stderr)
        if pm["unknown_paths"]:
            print(
                f"[WARN] {len(pm['unknown_paths'])} pad(en) niet in exceptions-lijst (legacy debt of nieuw):",
                file=sys.stderr,
            )
            for p in pm["unknown_paths"]:
                print(f"  {p}", file=sys.stderr)
            if args.strict:
                exit_code = 1

    if args.staged:
        st = run_staged(repo, suggest=args.suggest)
        report.update(st)
        if st["violations"]:
            print(
                "[FAIL] Nieuwe staged bestanden in tests/hermes_cli/ buiten exceptions - "
                "verplaats naar tests/overlay/ of tests/windows/.",
                file=sys.stderr,
            )
            for p in st["violations"]:
                print(f"  {p}", file=sys.stderr)
                if args.suggest:
                    print(f"  hint: git restore --staged {p}", file=sys.stderr)
            print("  Zie docs/FORK_MERGE_POLICY.md", file=sys.stderr)
            exit_code = 1

    if args.as_json:
        print(json.dumps(report, indent=2))

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
