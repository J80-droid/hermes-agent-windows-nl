"""Non-interactieve registratie van lancedb-knowledge in ~/.hermes/config.yaml."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Registreer lancedb-knowledge MCP (stdio, absoluut pad).")
    parser.add_argument("--repo-root", required=True, help="Hermes repo-root (met scripts/rag_pipeline/).")
    parser.add_argument("--python", required=True, help="Volledig pad naar python.exe (hermes-env).")
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    script = repo / "scripts" / "rag_pipeline" / "mcp_server.py"
    if not script.is_file():
        print(f"[ERROR] MCP-script ontbreekt: {script}", file=sys.stderr)
        return 1

    py = Path(args.python).resolve()
    if not py.is_file():
        print(f"[ERROR] Python ontbreekt: {py}", file=sys.stderr)
        return 1

    repo_str = str(repo)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)

    from hermes_cli.mcp_config import _save_mcp_server
    from hermes_constants import get_hermes_home

    ldb = (os.environ.get("HERMES_LANCEDB_PATH") or "").strip()
    if not ldb:
        ldb = str(Path.home() / "data" / "my_lancedb")

    _save_mcp_server(
        "lancedb-knowledge",
        {
            "command": str(py),
            "args": [str(script)],
            "env": {
                "HERMES_REPO_ROOT": repo_str,
                "HERMES_LANCEDB_PATH": ldb,
                "PYTHONIOENCODING": "utf-8",
            },
        },
    )
    cfg = get_hermes_home() / "config.yaml"
    print(f"[OK] lancedb-knowledge in {cfg} (absoluut pad + env).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
