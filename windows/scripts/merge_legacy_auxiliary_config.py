#!/usr/bin/env python3
"""Selectief auxiliary-blok van legacy config naar runtime mergen (alleen auto/leeg)."""
from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required", file=sys.stderr)
    sys.exit(1)

TEXT_AUX_TASKS = (
    "compression",
    "web_extract",
    "mcp",
    "approval",
    "title_generation",
    "skills_hub",
    "triage_specifier",
    "curator",
)


def _load(path: Path) -> dict:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def _is_empty_or_auto(slot: dict) -> bool:
    if not isinstance(slot, dict):
        return True
    provider = str(slot.get("provider") or "auto").strip().lower()
    model = str(slot.get("model") or "").strip()
    base_url = str(slot.get("base_url") or "").strip()
    return provider in ("", "auto") and not model and not base_url


def merge_auxiliary(*, legacy: dict, runtime: dict) -> tuple[dict, list[str]]:
    runtime = copy.deepcopy(runtime)
    aux_rt = runtime.setdefault("auxiliary", {})
    if not isinstance(aux_rt, dict):
        aux_rt = {}
        runtime["auxiliary"] = aux_rt
    aux_lg = legacy.get("auxiliary") if isinstance(legacy.get("auxiliary"), dict) else {}
    merged: list[str] = []

    for task in TEXT_AUX_TASKS + ("vision",):
        lg_slot = aux_lg.get(task)
        if not isinstance(lg_slot, dict):
            continue
        rt_slot = aux_rt.get(task)
        if not isinstance(rt_slot, dict):
            rt_slot = {}
        if _is_empty_or_auto(rt_slot) and lg_slot:
            aux_rt[task] = copy.deepcopy(lg_slot)
            merged.append(task)
        elif isinstance(rt_slot, dict):
            aux_rt[task] = rt_slot

    return runtime, merged


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    args = parser.parse_args()

    legacy_cfg = _load(args.legacy)
    runtime_cfg = _load(args.runtime)
    if not runtime_cfg:
        print(f"Runtime config missing or empty: {args.runtime}", file=sys.stderr)
        return 1

    merged_cfg, tasks = merge_auxiliary(legacy=legacy_cfg, runtime=runtime_cfg)
    if not tasks:
        print("No auxiliary slots merged (runtime already explicit).")
        return 0

    with args.runtime.open("w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(merged_cfg, f, sort_keys=False, allow_unicode=True)

    print(f"Merged auxiliary tasks: {', '.join(tasks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
