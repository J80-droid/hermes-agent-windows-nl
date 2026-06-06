#!/usr/bin/env python3
"""Remove model/auxiliary/providers blocks from all profile config.yaml files."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from overlay.bootstrap import install

install()


def main() -> int:
    try:
        from hermes_cli.profile_model_inheritance import strip_all_profile_global_blocks
    except ImportError as exc:
        print(f"[FAIL] profile_model_inheritance niet beschikbaar: {exc}", file=sys.stderr)
        return 1

    stripped = strip_all_profile_global_blocks()
    if stripped:
        print("[OK] Stripped global blocks from profiles:", ", ".join(stripped))
    else:
        print("[OK] No profile global blocks to strip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
