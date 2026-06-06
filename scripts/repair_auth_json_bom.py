"""Remove UTF-8 BOM from root and profile auth.json files (fork overlay)."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from overlay.bootstrap import install

install()

from hermes_cli.auth import repair_all_auth_json_bom  # noqa: E402


def main() -> int:
    repaired = repair_all_auth_json_bom()
    if repaired:
        print("OK: BOM verwijderd uit:")
        for path in repaired:
            print(f"  {path}")
    else:
        print("OK: Geen auth.json met UTF-8 BOM gevonden")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
