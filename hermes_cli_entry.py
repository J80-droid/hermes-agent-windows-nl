#!/usr/bin/env python3
"""Canonical Hermes CLI entry (fork overlay bootstrap + ``hermes_cli.main``).

Use this module instead of ``python -m hermes_cli.main`` so profile-root
config inheritance, Venice/Jatevo providers, status-bar forks, and setup
patches are always active.

Entry points:
  - Console script ``hermes`` (``pyproject.toml``)
  - ``python -m hermes_cli_entry``
  - ``scripts/run_hermes_cli_with_overlay.py`` (thin wrapper)
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main() -> None:
    from overlay.bootstrap import install

    install()
    from hermes_cli.main import main as hermes_main

    hermes_main()


if __name__ == "__main__":
    main()
