#!/usr/bin/env python3
"""``hermes_cli.main`` entrypoint after ``overlay.bootstrap.install()``."""
from __future__ import annotations


def main() -> None:
    from overlay.bootstrap import install

    install()
    from hermes_cli.main import main as hermes_main

    hermes_main()


if __name__ == "__main__":
    main()
