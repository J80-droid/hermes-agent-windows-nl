"""Post-ingest MCP-verificatie per domein (domains.yaml → profile mcp.servers)."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from domains_config import DomainSpec, resolve_domain_paths


@dataclass
class McpVerifyResult:
    domain: str
    mcp_name: str
    ok: bool
    detail: str
    tool_count: int = 0


def _env_truthy(name: str, *, default: str = "0") -> bool:
    raw = (os.environ.get(name) if os.environ.get(name) is not None else default).strip()
    return raw.lower() in ("1", "true", "yes", "j", "on")


def mcp_verify_enabled() -> bool:
    return not _env_truthy("HERMES_RAG_SKIP_MCP_VERIFY")


def mcp_verify_strict() -> bool:
    return _env_truthy("HERMES_RAG_MCP_VERIFY_STRICT")


def _profile_config_path(spec: DomainSpec) -> Path:
    _, _, profile = resolve_domain_paths(spec)
    return profile / "config.yaml"


def _load_mcp_server_config(profile_cfg: dict, mcp_name: str) -> dict[str, Any] | None:
    if not isinstance(profile_cfg, dict):
        return None
    servers = profile_cfg.get("mcp_servers")
    if isinstance(servers, dict) and mcp_name in servers:
        entry = servers[mcp_name]
        return dict(entry) if isinstance(entry, dict) else None
    mcp = profile_cfg.get("mcp")
    if isinstance(mcp, dict):
        nested = mcp.get("servers")
        if isinstance(nested, dict) and mcp_name in nested:
            entry = nested[mcp_name]
            return dict(entry) if isinstance(entry, dict) else None
    return None


def _lancedb_has_index(ldb_path: Path) -> tuple[bool, str]:
    table = ldb_path / "knowledge_base.lance"
    if not table.is_dir():
        return False, f"geen knowledge_base.lance in {ldb_path}"
    data_dir = table / "data"
    if data_dir.is_dir() and any(data_dir.iterdir()):
        return True, "LanceDB-data aanwezig"
    return False, "knowledge_base.lance bestaat maar lijkt leeg"


def verify_domain_mcp(spec: DomainSpec, *, repo_root: Path | None = None) -> McpVerifyResult:
    mcp_name = spec.resolved_mcp_name()
    ldb, _, profile = resolve_domain_paths(spec)

    ldb_ok, ldb_note = _lancedb_has_index(ldb)
    if not ldb_ok:
        return McpVerifyResult(spec.name, mcp_name, False, ldb_note)

    cfg_path = _profile_config_path(spec)
    if not cfg_path.is_file():
        return McpVerifyResult(
            spec.name,
            mcp_name,
            False,
            f"profiel-config ontbreekt: {cfg_path}",
        )

    try:
        profile_cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        return McpVerifyResult(spec.name, mcp_name, False, f"config.yaml lezen mislukt: {e}")

    server_cfg = _load_mcp_server_config(profile_cfg, mcp_name)
    if not server_cfg:
        return McpVerifyResult(
            spec.name,
            mcp_name,
            False,
            f"MCP '{mcp_name}' niet in profiel {spec.profile_name} (mcp.servers / mcp_servers)",
        )

    # Zorg dat ingest-pad in server-env overeenkomt met dit domein
    env_block = server_cfg.setdefault("env", {})
    if isinstance(env_block, dict):
        env_block.setdefault("HERMES_LANCEDB_PATH", str(ldb))

    root = repo_root or Path(__file__).resolve().parent.parent.parent
    prev_cwd = Path.cwd()
    try:
        os.chdir(root)
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from hermes_cli.config import _expand_env_vars
        from hermes_cli.mcp_config import _probe_single_server

        expanded = _expand_env_vars(server_cfg)
        if not isinstance(expanded, dict):
            return McpVerifyResult(spec.name, mcp_name, False, "serverconfig ongeldig na env-expand")

        tools = _probe_single_server(mcp_name, expanded)
        n = len(tools)
        if n < 1:
            return McpVerifyResult(
                spec.name,
                mcp_name,
                False,
                f"verbonden maar 0 tools ({ldb_note})",
            )
        return McpVerifyResult(
            spec.name,
            mcp_name,
            True,
            f"OK — {n} tool(s), {ldb_note}",
            tool_count=n,
        )
    except Exception as e:
        return McpVerifyResult(
            spec.name,
            mcp_name,
            False,
            f"MCP-probe mislukt: {type(e).__name__}: {e}",
        )
    finally:
        os.chdir(prev_cwd)


def print_verify_result(result: McpVerifyResult) -> None:
    tag = "[OK]" if result.ok else "[WARN]"
    if mcp_verify_strict() and not result.ok:
        tag = "[ERROR]"
    print(f"{tag} MCP {result.mcp_name} ({result.domain}): {result.detail}")


def verify_domains(
    specs: list[DomainSpec],
    *,
    repo_root: Path | None = None,
) -> int:
    """Verifieer alle domeinen; return exitcode (0=ok, 1=fail bij strict)."""
    if not mcp_verify_enabled():
        print("[INFO] MCP post-verify uit (HERMES_RAG_SKIP_MCP_VERIFY=1)")
        return 0

    print()
    print("-- Post-verify MCP (per domein uit domains.yaml) --")
    any_fail = False
    for spec in specs:
        result = verify_domain_mcp(spec, repo_root=repo_root)
        print_verify_result(result)
        if not result.ok:
            any_fail = True

    if any_fail and mcp_verify_strict():
        print("[ERROR] MCP-verificatie mislukt (HERMES_RAG_MCP_VERIFY_STRICT=1)")
        return 1
    if any_fail:
        print("[WARN] MCP-verificatie had waarschuwingen (niet strict — ingest blijft OK)")
    else:
        print("[OK] Alle MCP-servers bereikbaar")
    return 0
