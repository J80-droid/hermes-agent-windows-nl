#!/usr/bin/env python3
"""Harness: PSES-safe logging + git redirect patterns in fork-kritieke windows scripts."""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

CRITICAL_PS1 = [
    "windows/HermesShellCommon.ps1",
    "windows/upstream_sync.ps1",
    "windows/apply_hermes_home_migration.ps1",
    "windows/HermesPythonPolicy.ps1",
    "windows/sync_hermes_api_env.ps1",
    "windows/scripts/HermesHomeCommon.ps1",
    "windows/scripts/check_hermes_rag_after_repair.ps1",
]

FORBIDDEN = [
    (re.compile(r'2>\$null'), "stderr redirect 2>$null (PSES tokenizer)"),
    (re.compile(r'2>&1'), "stderr redirect 2>&1 (PSES tokenizer)"),
    (re.compile(r'"\[(?:INFO|OK|WARN|FAIL|ERROR|SKIP)\]'), "bracket tag in double-quoted string"),
    (re.compile(r'"\$[A-Za-z_][A-Za-z0-9_]*/\$'), "division-like $var/$var in double quotes"),
]


def _fail(msg: str, failures: list[str]) -> None:
    failures.append(msg)


def _code_lines_only(text: str) -> list[tuple[int, str]]:
    """Strip <# block comments #> and # line comments; return (1-based line, code)."""
    stripped = re.sub(r"<#.*?#>", "", text, flags=re.DOTALL)
    out: list[tuple[int, str]] = []
    for i, line in enumerate(stripped.splitlines(), start=1):
        if line.strip().startswith("#"):
            continue
        out.append((i, line))
    return out


def check_pses_safe_sources(failures: list[str]) -> None:
    for rel in CRITICAL_PS1:
        path = REPO / rel
        if not path.is_file():
            _fail(f"missing: {rel}", failures)
            continue
        text = path.read_text(encoding="utf-8")
        for pat, desc in FORBIDDEN:
            for i, line in _code_lines_only(text):
                if pat.search(line):
                    _fail(f"{rel}:{i}: {desc} -> {line.strip()[:80]}", failures)


def check_shell_common_api(failures: list[str]) -> None:
    common = (REPO / "windows/HermesShellCommon.ps1").read_text(encoding="utf-8")
    required = [
        "function Write-HermesInfo",
        "function Format-HermesStepLabel",
        "function Invoke-GitCommand",
        "function Test-NativeCommandFailed",
        "'INFO: '",
        "'OK: '",
        "ValidateRange(1, [int]::MaxValue)",
    ]
    for needle in required:
        if needle not in common:
            _fail(f"HermesShellCommon.ps1 mist: {needle!r}", failures)


def main() -> int:
    failures: list[str] = []
    check_shell_common_api(failures)
    check_pses_safe_sources(failures)
    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1
    print("OK: HermesShellCommon PSES harness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
