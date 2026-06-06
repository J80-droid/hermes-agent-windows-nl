"""Print gateway PIDs (one per line) for Windows install/status scripts."""
from __future__ import annotations

import sys

from hermes_cli.gateway import find_gateway_pids


def main() -> int:
    # all_profiles: Scheduled Task / pythonw kan buiten actieve HERMES_PROFILE vallen.
    pids = find_gateway_pids(all_profiles=True)
    for pid in pids:
        print(pid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
