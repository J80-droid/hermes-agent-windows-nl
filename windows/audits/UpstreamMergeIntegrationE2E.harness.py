#!/usr/bin/env python3
"""Isolated scenarios: upstream merge status-rule cwdReserve + profile create hooks."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _fail(msg: str, failures: list[str]) -> None:
    failures.append(msg)


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def check_source_wiring(failures: list[str]) -> None:
    app = _read("ui-tui/src/components/appChrome.tsx")
    if "const { leftWidth, rightWidth, separatorWidth } = statusRuleWidths(ruleCols, cwdLabel)" not in app:
        _fail("appChrome: statusRuleWidths vóór resolveStatusRuleLayout ontbreekt", failures)
    if "cwdReserve: rightWidth + separatorWidth" not in app:
        _fail("appChrome: cwdReserve niet doorgegeven", failures)
    widths_idx = app.find("statusRuleWidths(ruleCols, cwdLabel)")
    resolve_idx = app.find("resolveStatusRuleLayout({")
    if widths_idx < 0 or resolve_idx < 0 or widths_idx > resolve_idx:
        _fail("appChrome: statusRuleWidths moet vóór resolveStatusRuleLayout in StatusRule", failures)

    ucb = _read("ui-tui/src/domain/usageCostBar.ts")
    if "stringWidth" not in ucb or "cwdReserve" not in ucb:
        _fail("usageCostBar: stringWidth of cwdReserve ontbreekt", failures)

    prof = _read("hermes_cli/profiles.py")
    if "strip_model_block_from_profile_config(profile_dir)" not in prof:
        _fail("profiles.py: strip_model_block ontbreekt", failures)
    if "_maybe_register_gateway_service(canon)" not in prof:
        _fail("profiles.py: s6 register hook ontbreekt", failures)
    strip_idx = prof.find("strip_model_block_from_profile_config(profile_dir)")
    reg_idx = prof.find("_maybe_register_gateway_service(canon)")
    if strip_idx < 0 or reg_idx < 0 or strip_idx > reg_idx:
        _fail("profiles.py: strip_model moet vóór s6-register", failures)
    prof_norm = prof.replace("\r\n", "\n")
    if "except ImportError:" not in prof_norm or "else:\n        strip_model_block_from_profile_config" not in prof_norm:
        _fail("profiles.py: ImportError-only guard rond strip ontbreekt", failures)


def check_create_profile_strips_model(failures: list[str]) -> None:
    import os
    from unittest.mock import patch

    import yaml

    from hermes_cli.profiles import create_profile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        home = tmp_path / ".hermes"
        home.mkdir()
        (home / "config.yaml").write_text(
            "model:\n  default: openrouter/test\nagent: {}\n",
            encoding="utf-8",
        )
        os.environ["HERMES_HOME"] = str(home)
        with patch.object(Path, "home", lambda: tmp_path):
            prof = create_profile("merge_e2e_child", clone_config=True, no_alias=True)
        cfg_path = prof / "config.yaml"
        if not cfg_path.is_file():
            _fail("create_profile: geen config.yaml", failures)
            return
        raw = cfg_path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw) or {}
        if isinstance(data, dict) and "model" in data:
            _fail("create_profile: model-blok niet gestript na clone", failures)
        if "inherited from root" not in raw:
            _fail("create_profile: inheritance comment ontbreekt", failures)


def main() -> int:
    failures: list[str] = []
    check_source_wiring(failures)
    check_create_profile_strips_model(failures)
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: upstream merge integration harness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
