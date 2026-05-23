#!/usr/bin/env python3
"""IDE-safe Write-Host: double-quoted [TAG] -> concatenation. Skips complex bodies."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {"repair_ps1_write_host_tags.py", "Repair-HermesPs1ParseHygiene.ps1", "Fix-BrokenWriteHostConcat.ps1"}

PAT = re.compile(
    r'Write-Host\s+"(\[[^\]]+\])\s+([^"]+)"(\s+-ForegroundColor\s+\S+)?'
)


def body_to_concat(tag: str, body: str) -> str | None:
    body = body.strip()
    if not body:
        return f"Write-Host '{tag}'"
    if "$" not in body:
        esc = body.replace("'", "''")
        return f"Write-Host '{tag}{esc}'"
    # Simple: single variable or subexpression only
    if re.fullmatch(r"\$[\w:]+", body):
        return f"Write-Host ('{tag} ' + {body})"
    if re.fullmatch(r"\$\([^)]+\)", body):
        return f"Write-Host ('{tag} ' + {body})"
    # var - var / var + 'text'
    m = re.fullmatch(r"(\$[\w:]+|\$\([^)]+\))\s+-\s+(\$[\w:]+|\$\([^)]+\))", body)
    if m:
        return f"Write-Host ('{tag} ' + {m.group(1)} + ' - ' + {m.group(2)})"
    m = re.fullmatch(r"(\$[\w:]+|\$\([^)]+\))\s+->\s+(\$[\w:]+|\$\([^)]+\))", body)
    if m:
        return f"Write-Host ('{tag} ' + {m.group(1)} + ' -> ' + {m.group(2)})"
    # subexpr: rest (colon suffix)
    m = re.fullmatch(r"(\$\([^)]+\)):\s*(.+)", body)
    if m:
        tail = m.group(2).replace("'", "''")
        return f"Write-Host ('{tag} ' + {m.group(1)} + ': {tail}')"
    m = re.fullmatch(r"(\$\([^)]+\))\s+(.+)", body)
    if m and not re.search(r"[|/]", m.group(2)):
        tail = m.group(2).replace("'", "''")
        return f"Write-Host ('{tag} ' + {m.group(1)} + ' {tail}')"
    m = re.fullmatch(r"([^$][^:]*):\s*(\$[\w:]+|\$\([^)]+\))", body)
    if m:
        prefix = m.group(1).replace("'", "''")
        return f"Write-Host ('{tag} ' + '{prefix}: ' + {m.group(2)})"
    m = re.fullmatch(r"(\$[\w:]+|\$\([^)]+\))\s+(\$[\w:]+|\$\([^)]+\))\s+(.+)", body)
    if m:
        tail = m.group(3).replace("'", "''")
        return f"Write-Host ('{tag} ' + {m.group(1)} + '/' + {m.group(2)} + ' | ' + {tail}')"
    parts = re.split(r"(\$\{[^}]+\}|\$[\w:@]+|\$\([^)]+\))", body)
    if len(parts) > 1 and any(p.startswith("$") for p in parts):
        bits: list[str] = []
        for p in parts:
            if not p:
                continue
            if p.startswith("$"):
                bits.append(p)
            else:
                bits.append("'" + p.replace("'", "''") + "'")
        return f"Write-Host ('{tag} ' + {' + '.join(bits)})"
    return None


def process_file(path: Path, dry_run: bool) -> bool:
    text = path.read_text(encoding="utf-8-sig")
    changed = False

    def repl(m: re.Match[str]) -> str:
        nonlocal changed
        tag, body, col = m.group(1), m.group(2), m.group(3) or ""
        new = body_to_concat(tag, body)
        if new is None:
            return m.group(0)
        changed = True
        return new + col

    out = PAT.sub(repl, text)

    # Write-Step / Read-Host met [type]-achtige tekst in dubbele quotes (bijv. [rag], [j/N])
    pat_bracket = re.compile(
        r'(Write-(?:Step|Ok|Warn|Err|Host)|Read-Host)\s+"([^"]*\[[^"]*)"(\s+-ForegroundColor\s+\S+)?'
    )

    def repl_bracket(m: re.Match[str]) -> str:
        nonlocal changed
        cmd, body, col = m.group(1), m.group(2), m.group(3) or ""
        if "$" in body:
            return m.group(0)
        changed = True
        esc = body.replace("'", "''")
        return f"{cmd} '{esc}'{col}"

    out = pat_bracket.sub(repl_bracket, out)
    if changed and not dry_run:
        path.write_text(out, encoding="utf-8", newline="\r\n")
    return changed


def main() -> int:
    dry = "--dry-run" in sys.argv
    n = 0
    for ps1 in ROOT.rglob("*.ps1"):
        if ps1.name in SKIP or "HermesShellCommon.ps1" in ps1.name:
            continue
        if process_file(ps1, dry):
            print(ps1.relative_to(ROOT.parent))
            n += 1
    print(f"{'Would change' if dry else 'Changed'}: {n} files", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
