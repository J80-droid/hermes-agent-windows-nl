"""Verifieer per-domein MCP in Hermes-profiles (domains.yaml). Geen monoliet lancedb-knowledge meer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from domains_config import default_domains_yaml, load_domains, resolve_domain_paths  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Controleer dat elk domein een profiel met mcp.servers heeft (geen globale monoliet-MCP)."
    )
    parser.add_argument("--domains-yaml", type=Path, default=None)
    args = parser.parse_args()

    yaml_path = args.domains_yaml or default_domains_yaml()
    if not yaml_path.is_file():
        print(f"[ERROR] domains.yaml ontbreekt: {yaml_path}", file=sys.stderr)
        return 1

    ok = True
    for spec in load_domains(yaml_path):
        mcp = spec.resolved_mcp_name()
        _, _, profile = resolve_domain_paths(spec)
        cfg = profile / "config.yaml"
        if not cfg.is_file():
            print(f"[ERROR] {spec.name}: profiel-config ontbreekt ({cfg})", file=sys.stderr)
            ok = False
            continue
        text = cfg.read_text(encoding="utf-8")
        if mcp not in text:
            print(f"[ERROR] {spec.name}: MCP '{mcp}' niet in {cfg}", file=sys.stderr)
            ok = False
        else:
            print(f"[OK] {spec.name}: {mcp} in profiel {spec.profile_name}")

    if not ok:
        print(
            "[INFO] MCP hoort per profile in config.yaml (mcp.servers), niet in globale ~/.hermes.",
            file=sys.stderr,
        )
        return 1
    print(f"[OK] Alle domeinen in {yaml_path} hebben profiel-MCP.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
