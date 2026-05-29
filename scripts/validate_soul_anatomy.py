#!/usr/bin/env python3
"""Validate SOUL.md files against SOUL_ANATOMY_SPEC section list."""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

REQUIRED_SECTIONS = [
    r"^# SOUL\.md - ",
    r"^## Identity\s",
    r"^## Values & Principles\s",
    r"^## Communication Style\s",
    r"^### Interaction met J\.\s",
    r"^### Output conventions \(institutional\)\s",
    r"^## Expertise & Knowledge\s",
    r"^## Hard Limits\s",
    r"^## Workflow\s",
    r"^## Tool Usage\s",
    r"^## Memory Policy\s",
    r"^## Example Interaction\s",
]

LEGACY_FORBIDDEN = [
    r"^## Advisory & trust\s",
    r"^## Outputformaat \(institutioneel\)\s",
    r"^## Tool governance \(domein-minimum\)\s",
    r"^## Interaction met J\.\s",
    r"^# SOUL: ",
]

LEGACY_ALLOWED_WITH_WARNING = [
    r"^## Tone\s",
    r"^## Mission\s",
]

GOVERNANCE_MARKERS = [
    (r"Zekerheid:\s*NN%", "zekerheidspercentage (Zekerheid: NN%)"),
    (r"Ontbrekende informatie \(voor deze conclusie\)", "gap-blok per strategie"),
    (r"ga door", "1/N ga-door gate"),
    (r"max\.\s*1\s*x", "tool retry-limiet"),
    (r"herproberen", "tool retry-context"),
]

LEGACY_GOVERNANCE_FORBIDDEN = [
    (r"bij twijfel:\s*zeg het", "oude twijfel-formulering"),
    (r"bij zwakke strategie,\s*ontbrekende feiten", "oude gap-trigger alleen bij zwakke strategie"),
    (r"voortzetting in volgende turn", "automatische 1/N-voortzetting"),
    (r"config succesvol overschreven", "onbewezen config-success claim"),
    (r"100%\s*\[Feit uit bron\].*config", "valse 100% config claim"),
]

CODEBASE_AUDIT_SECTION_HEADERS = (
    r"^##\s+Geobjectiveerde analyse\s",
    r"^###\s+Geverifieerde componenten",
    r"^###\s+Architectuur\s",
    r"^##\s+Beoordeling van",
)

CODEBASE_AUDIT_DENY_PATTERNS: list[tuple[str, str]] = [
    (r"100%\s+(codebase|suite|getest)", "valse 100% codebase/suite claim"),
    (r"zonder\s+syntax.*test_critical_windows", "PS1-syntax claim op critical-windows pytest alleen"),
    (r"routeert\s+betrouwbaar.*pareto", "runtime pareto-routing op static verify"),
]

CODEBASE_AUDIT_DENY_EXCEPTION = re.compile(
    r"(verboden|niet|geen|denylist|incorrect|juiste bron|max:|alleen op basis)",
    re.IGNORECASE,
)


def hermes_home() -> Path:
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
    if (local / "config.yaml").exists():
        return local
    home = Path.home() / ".hermes"
    if (home / "config.yaml").exists():
        return home
    return local


def find_souls(home: Path, *, profiles_only: bool = False) -> list[Path]:
    souls: list[Path] = []
    if not profiles_only:
        root_soul = home / "SOUL.md"
        if root_soul.exists():
            souls.append(root_soul)
    profiles = home / "profiles"
    if profiles.is_dir():
        for d in sorted(profiles.iterdir()):
            p = d / "SOUL.md"
            if p.is_file():
                souls.append(p)
    return souls


def _section_order_issues(text: str) -> list[str]:
    issues: list[str] = []
    comm = re.search(r"^## Communication Style\s", text, re.MULTILINE)
    out = re.search(r"^### Output conventions \(institutional\)\s", text, re.MULTILINE)
    exp = re.search(r"^## Expertise & Knowledge\s", text, re.MULTILINE)
    if comm and out and exp and not (comm.start() < out.start() < exp.start()):
        issues.append("Output conventions not between Communication Style and Expertise")
    out_count = len(re.findall(r"^### Output conventions \(institutional\)\s", text, re.MULTILINE))
    if out_count != 1:
        issues.append(f"expected 1 Output conventions block, found {out_count}")
    if not re.search(r"^### Trust & verification", text, re.MULTILINE):
        issues.append("missing ### Trust & verification")
    return issues


def _codebase_audit_sections(text: str) -> list[str]:
    lines = text.splitlines()
    sections: list[str] = []
    in_section = False
    buf: list[str] = []
    for line in lines:
        if any(re.match(pat, line) for pat in CODEBASE_AUDIT_SECTION_HEADERS):
            if buf:
                sections.append("\n".join(buf))
            buf = [line]
            in_section = True
            continue
        if in_section:
            if re.match(r"^##\s+", line) and buf and not any(
                re.match(pat, line) for pat in CODEBASE_AUDIT_SECTION_HEADERS
            ):
                sections.append("\n".join(buf))
                buf = []
                in_section = False
            elif in_section:
                buf.append(line)
    if buf:
        sections.append("\n".join(buf))
    return sections if sections else [text]


def _codebase_audit_claim_issues(text: str, *, strict_tiers: bool = False) -> list[str]:
    issues: list[str] = []
    for block in _codebase_audit_sections(text):
        for pat, label in CODEBASE_AUDIT_DENY_PATTERNS:
            for match in re.finditer(pat, block, re.IGNORECASE):
                line_start = block.rfind("\n", 0, match.start()) + 1
                line_end = block.find("\n", match.start())
                line = block[line_start : line_end if line_end != -1 else len(block)]
                if line.strip().startswith("|"):
                    continue  # claim-woordenboek / tabellen: voorbeeld van verboden claim
                if CODEBASE_AUDIT_DENY_EXCEPTION.search(line):
                    continue  # documenteert denylist (zelfde regel)
                start = max(0, match.start() - 80)
                context = block[start : match.start()]
                if CODEBASE_AUDIT_DENY_EXCEPTION.search(context):
                    continue
                issues.append(f"codebase_audit_deny:{label}")
        if strict_tiers and not re.search(r"\[E[0-3]\]", block):
            issues.append("codebase_audit_missing:geen [E0]-[E3] tier in audit-sectie")
    return issues


def _normalize_governance_text(text: str) -> str:
    return text.replace("\u00d7", "x").replace("×", "x")


def _governance_issues(text: str) -> list[str]:
    norm = _normalize_governance_text(text)
    issues: list[str] = []
    for pat, label in LEGACY_GOVERNANCE_FORBIDDEN:
        if re.search(pat, norm, re.IGNORECASE):
            issues.append(f"governance_legacy:{label}")
    for pat, label in GOVERNANCE_MARKERS:
        if not re.search(pat, norm, re.IGNORECASE):
            issues.append(f"governance_missing:{label}")
    return issues


def validate_file(path: Path, *, check_governance: bool = False) -> tuple[list[str], list[str]]:
    text = path.read_text(encoding="utf-8-sig")
    missing = [pat for pat in REQUIRED_SECTIONS if not re.search(pat, text, re.MULTILINE)]
    legacy = [pat for pat in LEGACY_FORBIDDEN if re.search(pat, text, re.MULTILINE)]
    warnings = [pat for pat in LEGACY_ALLOWED_WITH_WARNING if re.search(pat, text, re.MULTILINE)]
    order_issues = _section_order_issues(text)
    governance = _governance_issues(text) if check_governance else []
    return missing, legacy + order_issues + governance + [f"warn:{w}" for w in warnings]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate SOUL.md anatomy sections")
    parser.add_argument("path", nargs="?", help="Single SOUL.md file")
    parser.add_argument("--all-profiles", action="store_true", help="Validate all runtime SOUL files")
    parser.add_argument("--repo-templates", action="store_true", help="Validate docs/templates/SOUL_*")
    parser.add_argument(
        "--check-governance",
        action="store_true",
        help="Require trust/values governance markers; fail on legacy twijfel/1/N wording",
    )
    parser.add_argument(
        "--check-codebase-audit-claims",
        action="store_true",
        help="Warn on forbidden codebase-audit phrasing in audit sections (exit 0 unless --strict)",
    )
    parser.add_argument(
        "--strict-codebase-audit-claims",
        action="store_true",
        help="Exit 1 on codebase-audit denylist matches (use with --check-codebase-audit-claims)",
    )
    args = parser.parse_args()

    paths: list[Path] = []
    if args.path:
        paths.append(Path(args.path))
    elif args.all_profiles:
        paths = find_souls(hermes_home(), profiles_only=True)
    elif args.repo_templates:
        repo = Path(__file__).resolve().parents[1]
        templates = repo / "docs" / "templates"
        paths = sorted(templates.glob("SOUL_*_DOMAIN.md")) + [templates / "SOUL_CORE_ORCHESTRATOR.md"]
    else:
        parser.print_help()
        return 2

    if not paths:
        print("[WARN] Geen SOUL.md bestanden gevonden.", file=sys.stderr)
        return 0

    codebase_only = args.check_codebase_audit_claims and not (
        args.check_governance or args.all_profiles or args.repo_templates
    )
    if args.strict_codebase_audit_claims and not args.check_codebase_audit_claims:
        args.check_codebase_audit_claims = True

    failed = 0
    warned = 0
    for p in paths:
        if not p.exists():
            print(f"[SKIP] {p} (ontbreekt)")
            continue

        if codebase_only or (args.check_codebase_audit_claims and p.suffix.lower() in {".md", ".txt"}):
            text = p.read_text(encoding="utf-8-sig")
            ca_issues = _codebase_audit_claim_issues(
                text, strict_tiers=args.strict_codebase_audit_claims
            )
            if ca_issues:
                if args.strict_codebase_audit_claims:
                    failed += 1
                    print(f"[FAIL] {p}")
                    for i in ca_issues:
                        print(f"  codebase_audit: {i}")
                else:
                    warned += 1
                    print(f"[WARN] {p}")
                    for i in ca_issues:
                        print(f"  codebase_audit: {i}")
            else:
                print(f"[OK] {p}")
            if codebase_only:
                continue

        missing, issues = validate_file(p, check_governance=args.check_governance)
        if missing or [i for i in issues if not i.startswith("warn:")]:
            failed += 1
            print(f"[FAIL] {p}")
            for m in missing:
                print(f"  mist: {m}")
            for i in issues:
                if not i.startswith("warn:"):
                    label = "governance" if i.startswith("governance_") else "legacy"
                    print(f"  {label}: {i}")
        else:
            print(f"[OK] {p}")
            for w in issues:
                if w.startswith("warn:"):
                    print(f"  {w} (draai migrate + SYNC_SOUL_SNIPPETS)")

        if args.check_codebase_audit_claims and not codebase_only:
            text = p.read_text(encoding="utf-8-sig")
            ca_issues = _codebase_audit_claim_issues(
                text, strict_tiers=args.strict_codebase_audit_claims
            )
            for i in ca_issues:
                if args.strict_codebase_audit_claims:
                    if failed == 0:
                        failed += 1
                        print(f"[FAIL] {p} (codebase-audit)")
                    print(f"  codebase_audit: {i}")
                else:
                    print(f"[WARN] {p} codebase_audit: {i}")
                    warned += 1

    if warned and not failed:
        print(f"[OK] {warned} waarschuwing(en), geen harde failures.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
