#!/usr/bin/env python3
"""Verify OpenRouter Pareto Code router wiring (model-gated min_coding_score)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _repo() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Pareto Code router wiring")
    parser.add_argument("--verify", action="store_true", help="Exit 1 on drift")
    args = parser.parse_args()

    repo = _repo()
    errors: list[str] = []

    plugin = repo / "plugins" / "model-providers" / "openrouter" / "__init__.py"
    if not plugin.is_file():
        errors.append("openrouter provider plugin ontbreekt")
    else:
        text = plugin.read_text(encoding="utf-8")
        if "openrouter/pareto-code" not in text:
            errors.append("openrouter plugin mist pareto-code model gate")
        if "pareto-router" not in text:
            errors.append("openrouter plugin mist pareto-router plugin id")

    transport = (repo / "agent" / "transports" / "chat_completions.py").read_text(encoding="utf-8")
    if "openrouter/pareto-code" not in transport or "pareto-router" not in transport:
        errors.append("chat_completions.py mist pareto-router emission")

    helpers = (repo / "agent" / "chat_completion_helpers.py").read_text(encoding="utf-8")
    if "openrouter/pareto-code" not in helpers or "pareto-router" not in helpers:
        errors.append("chat_completion_helpers.py mist pareto summary path")

    config = (repo / "hermes_cli" / "config.py").read_text(encoding="utf-8")
    if "min_coding_score" not in config or "openrouter/pareto-code" not in config:
        errors.append("hermes_cli/config.py documenteert min_coding_score niet")

    models = (repo / "hermes_cli" / "models.py").read_text(encoding="utf-8")
    if "openrouter/pareto-code" not in models:
        errors.append("hermes_cli/models.py mist openrouter/pareto-code catalog entry")

    if errors:
        for err in errors:
            print(f"[FAIL] {err}")
        return 1

    print("[OK] Pareto Code router wiring")
    return 0


if __name__ == "__main__":
    sys.exit(main())
