#!/usr/bin/env python3
"""Scan Hermes fork skills/docs for CLI paths and flags that may have drifted."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Patterns that should exist in the codebase (update when CLI changes).
CANONICAL = {
    "MERGE_UPSTREAM.bat": REPO / "windows" / "MERGE_UPSTREAM.bat",
    "VERIFY_WINDOWS_CHAIN.bat": REPO / "windows" / "VERIFY_WINDOWS_CHAIN.bat",
    "UPDATE_HERMES.bat": REPO / "windows" / "UPDATE_HERMES.bat",
    "LANCEDB_MAINTENANCE.bat": REPO / "windows" / "LANCEDB_MAINTENANCE.bat",
    "cli.py": REPO / "cli.py",
    "run_agent.py": REPO / "run_agent.py",
    "hermes_cli/main.py": REPO / "hermes_cli" / "main.py",
    "lancedb_maintenance.py": REPO / "scripts" / "rag_pipeline" / "lancedb_maintenance.py",
}

# Deprecated references to flag in skills.
DEPRECATED_PATTERNS: list[tuple[str, str]] = [
    (r"python\s+run_agent\.py\s+--no-isolate", "Gebruik pytest via RUN_PYTEST.ps1 / run_tests.sh"),
    (r"(?<!geen )(?<!niet )hermes-cli\s+preset", "platform_toolsets.cli gebruikt expliciet [] — geen hermes-cli preset"),
    (r"windows\\\\setup_hermes_windows\.ps1", "Pad-literal: gebruik scripts/windows/setup_hermes_windows.ps1"),
]

SCAN_GLOBS = (
    "skills/productivity/**/*.md",
    "skills/autonomous-ai-agents/hermes-agent/**/*.md",
    "optional-skills/**/SKILL.md",
    "docs/**/*.md",
    "memory-bank/**/*.md",
)

CODE_CMD_RE = re.compile(
    r"^(?:```[^\n]*\n)?\s*(?:python|pytest|hermes|windows\\|windows/|\./)[^\n`]+",
    re.MULTILINE | re.IGNORECASE,
)


def _iter_files() -> list[Path]:
    out: list[Path] = []
    for pattern in SCAN_GLOBS:
        out.extend(REPO.glob(pattern))
    return sorted({p.resolve() for p in out if p.is_file()})


def audit_file(path: Path) -> list[str]:
    issues: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"kan niet lezen: {exc}"]

    rel = path.relative_to(REPO).as_posix()
    for pattern, hint in DEPRECATED_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            line_no = text[: m.start()].count("\n") + 1
            line_text = text.splitlines()[line_no - 1] if line_no else ""
            if "referentie" in line_text.lower() or "geen hermes-cli" in line_text.lower():
                continue
            issues.append(f"L{line_no}: deprecated patroon — {hint}")

    for m in CODE_CMD_RE.finditer(text):
        snippet = m.group(0).strip()
        for token, canon_path in CANONICAL.items():
            if token in snippet and not canon_path.is_file():
                line = text[: m.start()].count("\n") + 1
                issues.append(f"L{line}: verwijst naar {token} maar bestand ontbreekt in repo")

    domain_yaml = REPO / "docs" / "domain_toolsets.yaml"
    canonical_domains = 14
    if domain_yaml.is_file():
        import re as _re

        profile_keys = _re.findall(r"^  ([a-z_]+):\s*$", domain_yaml.read_text(encoding="utf-8"), _re.MULTILINE)
        profile_keys = [k for k in profile_keys if k not in ("platform_toolsets", "toolsets", "note")]
        if profile_keys:
            canonical_domains = len(profile_keys)
    if "landkaart" in rel or "memory-bank" in rel:
        count_re = re.compile(
            r"\b(\d{1,2})\s*(?:domein(?:en|profielen)?|profiel(?:en)?)\b", re.IGNORECASE
        )
        for i, line_text in enumerate(text.splitlines(), 1):
            for m in count_re.finditer(line_text):
                stated = int(m.group(1))
                if stated != canonical_domains:
                    issues.append(
                        f"L{i}: vermeld '{stated}' domeinen/profielen — canoniek zijn er "
                        f"{canonical_domains} (zie docs/domain_toolsets.yaml)"
                    )
                    break

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit skill/docs drift vs Hermes fork")
    parser.add_argument(
        "--report",
        type=Path,
        help="Markdown output (default: windows/audits/SKILL_DRIFT_AUDIT_<date>.md)",
    )
    args = parser.parse_args()

    findings: dict[str, list[str]] = {}
    for path in _iter_files():
        hits = audit_file(path)
        if hits:
            findings[path.relative_to(REPO).as_posix()] = hits

    lines = [
        f"# Skill / docs drift audit — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"Bestanden gescand: {len(list(_iter_files()))}",
        f"Met bevindingen: {len(findings)}",
        "",
    ]
    if not findings:
        lines.append("Geen drift-bevindingen in fork-scope.")
        print("[OK] Geen drift-bevindingen.")
    else:
        for rel, hits in sorted(findings.items()):
            lines.append(f"## `{rel}`")
            lines.append("")
            for h in hits:
                lines.append(f"- {h}")
            lines.append("")
            print(f"[WARN] {rel}: {len(hits)} bevinding(en)")

    report = args.report or (
        REPO / "windows" / "audits" / f"SKILL_DRIFT_AUDIT_{datetime.now().strftime('%Y-%m-%d')}.md"
    )
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Rapport: {report}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
