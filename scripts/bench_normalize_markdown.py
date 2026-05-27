#!/usr/bin/env python3
"""Benchmark normalize_assistant_markdown (local profiling; not a CI gate).

Usage:
  python scripts/bench_normalize_markdown.py
  python scripts/bench_normalize_markdown.py --file path/to/sample.md --iterations 100
"""

from __future__ import annotations

import argparse
import statistics
import time
from pathlib import Path

from hermes_cli.markdown_output_normalize import normalize_assistant_markdown

REPO = Path(__file__).resolve().parent.parent
ROOKTEST = (
    "<institutional_check>\n- Controle hyperbolen: [Uitgevoerd]\n</institutional_check>\n\n"
    "## Projectoverzicht\nIntro.\n\n"
    "### Team Samenstelling\n| Naam | Rol | Status |\n|---|---|---|\n| A | Lead | Actief |\n\n"
    "### Niet-functionele requirements\n"
    "**Performantie**\nRender snel.\nRobuustheid — Stabiel — Test\n"
)
ARCHITECTURE = (
    "### Architectuursamenvatting\n\n"
    "Component: API Keuze: REST Status: live —————— "
    "Component: DB Keuze: Postgres Status: prod\n"
)


def _bench(label: str, text: str, *, iterations: int) -> None:
    normalize_assistant_markdown(text)  # warmup
    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        normalize_assistant_markdown(text)
        times.append(time.perf_counter() - start)
    print(f"{label}: p50={statistics.median(times)*1000:.2f}ms "
          f"p95={sorted(times)[int(0.95 * len(times)) - 1]*1000:.2f}ms "
          f"n={iterations}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark institutional normalizer")
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--file", type=Path, help="Optional markdown file to bench")
    args = parser.parse_args()

    _bench("rooktest", ROOKTEST, iterations=args.iterations)
    _bench("architecture_collapsed", ARCHITECTURE, iterations=args.iterations)
    if args.file and args.file.is_file():
        sample = args.file.read_text(encoding="utf-8")
        _bench(args.file.name, sample, iterations=args.iterations)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
