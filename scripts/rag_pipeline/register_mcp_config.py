"""Verifieer en synchroniseer per-domein MCP in Hermes-profielen (domains.yaml → mcp_servers)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from domains_config import default_domains_yaml, load_domains  # noqa: E402
from sync_profile_mcp_from_domains import (  # noqa: E402
    sync_profile_config,
    validate_profile_mcp,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Controleer dat elk domein een profiel met mcp_servers heeft "
            "(CLI-formaat; geen globale monoliet-MCP)."
        )
    )
    parser.add_argument("--domains-yaml", type=Path, default=None)
    parser.add_argument("--sync", action="store_true", help="Ontbrekende/legacy configs bijwerken")
    args = parser.parse_args()

    yaml_path = args.domains_yaml or default_domains_yaml()
    if not yaml_path.is_file():
        print(f"[ERROR] domains.yaml ontbreekt: {yaml_path}", file=sys.stderr)
        return 1

    ok = True
    for spec in load_domains(yaml_path):
        if args.sync:
            _, msg = sync_profile_config(spec)
            print(f"[INFO] {msg}")
            good, vmsg = validate_profile_mcp(spec)
            print(f"[{'OK' if good else 'ERROR'}] {vmsg}")
            if not good:
                ok = False
        else:
            good, msg = validate_profile_mcp(spec)
            print(f"[{'OK' if good else 'ERROR'}] {msg}")
            if not good:
                ok = False

    if not ok:
        print(
            "[INFO] Herstel: python scripts/rag_pipeline/sync_profile_mcp_from_domains.py "
            "of windows\\scripts\\institutional_p0_p1.bat",
            file=sys.stderr,
        )
        return 1
    print(f"[OK] Alle domeinen in {yaml_path} hebben CLI-compatibele profiel-MCP.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
