#!/usr/bin/env python3
"""Load windows/tests/pytest_fork_gate.yaml and emit JSON for PowerShell pytest runners."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


def _repo_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return Path(__file__).resolve().parents[2]


def _manifest_path(repo: Path) -> Path:
    return repo / "windows" / "tests" / "pytest_fork_gate.yaml"


def _as_str_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"invalid manifest field {field}: expected list, got {type(value).__name__}")
    out: list[str] = []
    for i, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"invalid manifest field {field}[{i}]: expected non-empty string")
        out.append(item.strip())
    return out


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"manifest missing: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        raise ValueError(f"invalid manifest (empty): {path}")
    if not isinstance(data, dict):
        raise ValueError(f"invalid manifest (not a mapping): {path}")
    return data


def _path_for_gate_check(repo: Path, rel: str) -> Path:
    """Resolve manifest entry to a filesystem path (strip pytest nodeid suffix)."""
    file_part = rel.split("::", 1)[0]
    return repo / Path(file_part)


def _validate_gate_paths(repo: Path, paths: list[str]) -> list[str]:
    missing: list[str] = []
    for rel in paths:
        p = _path_for_gate_check(repo, rel)
        norm = rel.replace("\\", "/")
        if norm.endswith("/"):
            if not p.is_dir():
                missing.append(rel)
        elif not p.is_file():
            missing.append(rel)
    return missing


def _positive_int(value: Any, field: str, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid manifest field {field}: expected int, got {value!r}") from exc
    if parsed < 1:
        raise ValueError(f"invalid manifest field {field}: must be >= 1")
    return parsed


def build_config(repo: Path, mode: str) -> dict[str, Any]:
    if mode not in ("gate", "upstream"):
        raise ValueError(f"unsupported mode: {mode}")

    manifest = _load_manifest(_manifest_path(repo))
    ignores = _as_str_list(manifest.get("ignores"), "ignores")
    markers = manifest.get("markers")
    if markers is not None and not isinstance(markers, str):
        raise ValueError("invalid manifest field markers: expected string")

    if mode == "gate":
        paths = _as_str_list(manifest.get("paths"), "paths")
        if not paths:
            raise ValueError("invalid manifest: gate paths must not be empty")
        missing = _validate_gate_paths(repo, paths)
        if missing:
            raise FileNotFoundError(
                "gate manifest paths missing: " + ", ".join(missing)
            )
        return {
            "mode": "gate",
            "markers": markers or "",
            "paths": paths,
            "ignores": ignores,
        }

    upstream = manifest.get("upstream")
    if upstream is not None and not isinstance(upstream, dict):
        raise ValueError("invalid manifest field upstream: expected mapping")
    upstream = upstream or {}
    up_paths = _as_str_list(upstream.get("paths"), "upstream.paths") or ["tests/"]
    up_ignores = _as_str_list(upstream.get("ignores"), "upstream.ignores")
    junit = upstream.get("junit")
    if junit is not None and not isinstance(junit, str):
        raise ValueError("invalid manifest field upstream.junit: expected string")
    return {
        "mode": "upstream",
        "markers": markers or "",
        "paths": up_paths,
        "ignores": ignores + up_ignores,
        "maxfail": _positive_int(upstream.get("maxfail_default"), "upstream.maxfail_default", 50),
        "junit": str(junit or "windows/tests/pytest_upstream_junit.xml"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument(
        "--mode",
        choices=("gate", "upstream"),
        default="gate",
    )
    args = parser.parse_args()
    repo = _repo_root(args.repo_root)
    try:
        config = build_config(repo, args.mode)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    json.dump(config, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
