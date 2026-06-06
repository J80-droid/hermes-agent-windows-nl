"""Runtime tool-count check for RUN_TOOLSET_DOMAIN_E2E.ps1 (stap 5/6)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml


def main() -> int:
    try:
        repo = Path(os.environ["HERMES_TOOLSET_E2E_REPO"])
        hermes = Path(os.environ["HERMES_TOOLSET_E2E_HOME"])
    except KeyError as exc:
        print(f"[FAIL] ontbrekende env: {exc.args[0]}")
        return 1

    prev_home = os.environ.get("HERMES_HOME")
    sys.path.insert(0, str(repo))
    from overlay.bootstrap import install

    install()
    from hermes_cli.tools_config import _get_platform_tools, _platform_toolsets_user_customized
    from model_tools import get_tool_definitions

    manifest = yaml.safe_load(
        (repo / "docs/domain_toolsets.yaml").read_text(encoding="utf-8")
    )
    profiles = manifest.get("profiles") or {}
    required_base = {"mcp", "file", "memory", "skills", "clarify"}
    failures: list[str] = []
    profile_lines: list[str] = []
    try:
        for name, spec in sorted(profiles.items()):
            cfg_path = hermes / "profiles" / name / "config.yaml"
            if not cfg_path.is_file():
                failures.append(f"{name}: config.yaml ontbreekt")
                continue
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            if _platform_toolsets_user_customized(cfg, "cli"):
                profile_lines.append(f"{name}: user-customized cli (check overgeslagen)")
                continue
            cli_toolsets = set((cfg.get("platform_toolsets") or {}).get("cli") or [])
            expected = set((spec.get("platform_toolsets") or {}).get("cli") or [])
            if cli_toolsets != expected:
                failures.append(
                    f"{name}: cli mismatch {sorted(cli_toolsets)} vs {sorted(expected)}"
                )
            missing = required_base - cli_toolsets
            if missing:
                failures.append(f"{name}: mist basis toolsets {sorted(missing)}")
            never = set(spec.get("never_default") or []) | set(
                manifest.get("never_default_global") or []
            )
            overlap = cli_toolsets & never
            if overlap:
                failures.append(f"{name}: never_default in cli: {sorted(overlap)}")
            optional = set(spec.get("optional_toolsets") or [])
            bad_opt = optional & cli_toolsets
            if bad_opt:
                failures.append(f"{name}: optional_toolsets in cli: {sorted(bad_opt)}")
            if "hermes-cli" in cli_toolsets or "enabled_toolsets" in cfg:
                failures.append(f"{name}: hermes-cli of enabled_toolsets nog actief")
            max_tools = int(spec.get("max_tools") or 99)
            os.environ["HERMES_HOME"] = str(hermes / "profiles" / name)
            enabled = _get_platform_tools(cfg, "cli")
            tools = get_tool_definitions(enabled_toolsets=enabled, quiet_mode=True)
            count = len(tools)
            profile_lines.append(f"{name}: {count} tools (max {max_tools})")
            if count > max_tools:
                failures.append(f"{name}: {count} tools > max {max_tools}")
        root_cfg = hermes / "config.yaml"
        if root_cfg.is_file():
            root = yaml.safe_load(root_cfg.read_text(encoding="utf-8")) or {}
            pt = root.get("platform_toolsets") or {}
            if "cli" not in pt:
                failures.append("root: platform_toolsets.cli ontbreekt")
            root_cli = list(pt.get("cli") or [])
            if root.get("toolsets") and root.get("toolsets") != []:
                failures.append("root: toolsets moet [] zijn")
            if root_cli != []:
                failures.append(f"root: cli moet [] zijn, is {root_cli!r}")
            os.environ["HERMES_HOME"] = str(hermes)
            root_enabled = _get_platform_tools(root, "cli")
            if "hermes-cli" in root_enabled:
                failures.append("root: hermes-cli actief zonder profiel")
            root_tools = get_tool_definitions(enabled_toolsets=root_enabled, quiet_mode=True)
            if len(root_enabled) > 0 or len(root_tools) > 0:
                failures.append(
                    f"root: {len(root_enabled)} toolsets / {len(root_tools)} tools - gebruik hermes -p <domein>"
                )
            else:
                profile_lines.append("root: 0 toolsets, 0 tools")
    finally:
        if prev_home is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = prev_home

    if failures:
        for f in failures:
            print("[FAIL]", f)
        for line in profile_lines:
            print("[INFO]", line)
        return 1
    for line in profile_lines:
        print("[OK]", line)
    print("[OK] runtime tool-counts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
