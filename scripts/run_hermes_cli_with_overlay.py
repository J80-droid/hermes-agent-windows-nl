#!/usr/bin/env python3
"""Backward-compatible wrapper — delegates to ``hermes_cli_entry``."""
from __future__ import annotations

from hermes_cli_entry import main

if __name__ == "__main__":
    main()
