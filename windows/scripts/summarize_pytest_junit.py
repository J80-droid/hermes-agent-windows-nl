#!/usr/bin/env python3
"""Summarize pytest JUnit XML for upstream parity reporting."""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


def _canonical_nodeid(nodeid: str) -> str:
    """Normalize path-style vs dot-style pytest nodeids for comparison."""
    nodeid = nodeid.strip().replace("\\", "/")
    if "::" in nodeid:
        file_part, rest = nodeid.split("::", 1)
    else:
        file_part, rest = nodeid, ""
    file_part = file_part.strip()
    if file_part.endswith(".py"):
        module = file_part[:-3].replace("/", ".")
    elif "/" in file_part:
        module = file_part.replace("/", ".")
    else:
        module = file_part
    return f"{module}::{rest}" if rest else module


def _load_known_fails(path: Path | None) -> set[str]:
    if not path or not path.is_file():
        return set()
    known: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        known.add(_canonical_nodeid(line))
    return known


def _module_from_nodeid(nodeid: str) -> str:
    if "::" in nodeid:
        return nodeid.split("::", 1)[0]
    return nodeid


def _nodeid_from_case(case: ET.Element) -> str:
    file_attr = case.get("file")
    name = case.get("name", "")
    if file_attr:
        return file_attr.replace("\\", "/") + "::" + name
    classname = case.get("classname", "")
    return classname + "::" + name if classname else name


def summarize(junit_path: Path, known_fails: set[str] | None = None) -> dict:
    if known_fails is None:
        known_fails = set()
    else:
        known_fails = {_canonical_nodeid(k) for k in known_fails}
    try:
        tree = ET.parse(junit_path)
    except ET.ParseError as exc:
        raise ValueError(f"invalid junit xml: {junit_path}: {exc}") from exc

    root = tree.getroot()
    passed = failed = skipped = errors = 0
    failed_nodeids: list[str] = []
    module_counter: Counter[str] = Counter()

    for case in root.iter("testcase"):
        nodeid = _nodeid_from_case(case)
        if case.find("skipped") is not None:
            skipped += 1
            continue
        if case.find("failure") is not None:
            failed += 1
            failed_nodeids.append(nodeid)
            module_counter[_module_from_nodeid(nodeid)] += 1
            continue
        if case.find("error") is not None:
            errors += 1
            failed_nodeids.append(nodeid)
            module_counter[_module_from_nodeid(nodeid)] += 1
            continue
        passed += 1

    new_fails = [n for n in failed_nodeids if _canonical_nodeid(n) not in known_fails]
    known_only = [n for n in failed_nodeids if _canonical_nodeid(n) in known_fails]

    top_modules = [
        {"module": mod, "failures": count}
        for mod, count in module_counter.most_common(20)
    ]

    return {
        "junit": str(junit_path),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "errors": errors,
        "failed_nodeids_count": len(failed_nodeids),
        "new_failures": new_fails[:50],
        "new_failures_count": len(new_fails),
        "known_failures_count": len(known_only),
        "top_failure_modules": top_modules,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--known-fails", type=Path, default=None)
    args = parser.parse_args()

    if not args.junit.is_file():
        print(f"junit missing: {args.junit}", file=sys.stderr)
        return 1

    known = _load_known_fails(args.known_fails)
    try:
        payload = summarize(args.junit, known)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output} ({payload['failed']} failed, {payload['new_failures_count']} new)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
