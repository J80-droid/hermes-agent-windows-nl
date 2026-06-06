"""Guard RAG env: verwijder diskcache/llama-cpp; houd transformers>=5."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable

_REPO = Path(__file__).resolve().parents[1]
FORBIDDEN = ("llama-cpp-python", "diskcache")
TRANSFORMERS_FLOOR = (5, 0, 0)


def _parse_version(raw: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in (raw or "").strip().split("."):
        num = ""
        for ch in piece:
            if ch.isdigit():
                num += ch
            else:
                break
        if num:
            parts.append(int(num))
    return tuple(parts)


def _pip_list_versions(python: str) -> dict[str, str]:
    proc = subprocess.run(
        [python, "-m", "pip", "list", "--format=freeze"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    versions: dict[str, str] = {}
    if proc.returncode != 0:
        return versions
    for line in proc.stdout.splitlines():
        if "==" in line:
            name, ver = line.split("==", 1)
            versions[name.lower()] = ver.strip()
    return versions


def _pip_uninstall(python: str, packages: Iterable[str]) -> list[str]:
    removed: list[str] = []
    for pkg in packages:
        proc = subprocess.run(
            [python, "-m", "pip", "uninstall", "-y", pkg],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0 and "WARNING: Skipping" not in (proc.stdout + proc.stderr):
            removed.append(pkg)
    return removed


def _ensure_transformers_floor(python: str) -> bool:
    """Re-pin transformers>=5 when RAG stack is present. Returns True if OK."""
    versions = _pip_list_versions(python)
    if "sentence-transformers" not in versions and "lancedb" not in versions:
        return True
    current = _parse_version(versions.get("transformers", ""))
    if current and current >= TRANSFORMERS_FLOOR:
        return True
    proc = subprocess.run(
        [python, "-m", "pip", "install", "transformers>=5.0.0", "--quiet"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    return proc.returncode == 0


def run_guard(
    python: str | None = None,
    *,
    fix: bool = False,
    allow_llama: bool = False,
) -> dict[str, object]:
    """Return report dict; mutates env when ``fix=True``."""
    py = python or sys.executable
    allow_llama = allow_llama or os.environ.get("HERMES_ALLOW_LLAMA_CPP") == "1"
    versions = _pip_list_versions(py)
    found_forbidden = [p for p in FORBIDDEN if p in versions]
    transformers_ver = versions.get("transformers", "")
    transformers_ok = (
        not transformers_ver
        or _parse_version(transformers_ver) >= TRANSFORMERS_FLOOR
        or "sentence-transformers" not in versions
    )
    removed: list[str] = []
    if fix and found_forbidden and not allow_llama:
        removed = _pip_uninstall(py, found_forbidden)
        versions = _pip_list_versions(py)
        found_forbidden = [p for p in FORBIDDEN if p in versions]
    if fix and not transformers_ok:
        pinned = _ensure_transformers_floor(py)
        versions = _pip_list_versions(py)
        transformers_ver = versions.get("transformers", "")
        transformers_ok = pinned or (
            not transformers_ver
            or _parse_version(transformers_ver) >= TRANSFORMERS_FLOOR
        )
    return {
        "python": py,
        "forbidden_found": found_forbidden,
        "forbidden_removed": removed,
        "transformers_version": transformers_ver,
        "transformers_ok": transformers_ok,
        "allow_llama": allow_llama,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fix", action="store_true", help="Uninstall forbidden pkgs; pin transformers>=5")
    parser.add_argument("--json", action="store_true", help="Print machine-readable report")
    args = parser.parse_args()
    report = run_guard(fix=args.fix)
    if args.json:
        import json

        print(json.dumps(report, indent=2))
    else:
        forbidden = report["forbidden_found"]
        if forbidden:
            print(f"WARN: verboden packages: {', '.join(forbidden)}")
        if report["forbidden_removed"]:
            print(f"OK: verwijderd: {', '.join(report['forbidden_removed'])}")
        if not report["transformers_ok"]:
            print(
                f"WARN: transformers {report['transformers_version'] or '?'} < 5 "
                "(RAG vereist >=5; neutts[onnx] + constraints-rag-stack)"
            )
        elif report["transformers_version"]:
            print(f"OK: transformers {report['transformers_version']}")
        if not forbidden and report["transformers_ok"]:
            print("OK: package guard groen")
    ok = not report["forbidden_found"] and report["transformers_ok"]
    return 0 if ok else (0 if args.fix else 1)


if __name__ == "__main__":
    raise SystemExit(main())
