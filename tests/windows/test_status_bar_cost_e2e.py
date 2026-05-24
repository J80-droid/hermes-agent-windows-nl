"""E2E smoke for TUI status-bar session cost (show_cost + gateway usage payload)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]


def test_repo_team_display_defaults_enable_show_cost():
    text = (REPO / "windows" / "team_display.defaults").read_text(encoding="utf-8")
    assert "show_cost=true" in text
    assert "cost_bar_mode=rich" in text


def test_repo_usage_snapshot_module_exists():
    path = REPO / "hermes_cli" / "usage_snapshot.py"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "def build_session_usage_snapshot" in text
    assert "cost_breakdown_pct" in text
    assert "_seed_agent_session_cost" in text


def test_repo_google_gemini_cache_pricing_catalog():
    text = (REPO / "agent" / "usage_pricing.py").read_text(encoding="utf-8")
    assert "_GOOGLE_GEMINI_PRICING" in text
    assert '"gemini-3.5-flash"' in text
    assert "cache_read_cost_per_million" in text
    assert "google-gemini-cli" in text


def test_repo_usage_cost_bar_formatter_exists():
    path = REPO / "ui-tui" / "src" / "domain" / "usageCostBar.ts"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "export function formatStatusBarCostRich" in text
    assert "formatUsdCompact" in text


def test_repo_classic_cli_status_bar_cost_module():
    path = REPO / "hermes_cli" / "status_bar_cost.py"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "def format_status_bar_cost_rich" in text
    assert "def resolve_status_bar_cost_label" in text


def test_repo_classic_cli_cost_hooks():
    cli = (REPO / "cli.py").read_text(encoding="utf-8")
    assert "_handle_cost_command" in cli
    assert "_append_status_bar_cost_fragments" in cli
    assert 'canonical == "cost"' in cli


def test_repo_cost_command_registered():
    commands = (REPO / "hermes_cli" / "commands.py").read_text(encoding="utf-8")
    assert 'CommandDef("cost"' in commands


def test_repo_classic_cli_smoke_script_exists():
    path = REPO / "scripts" / "status_bar_cost_classic_cli_smoke.py"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "classic cli status bar cost smoke ok" in text


def test_repo_classic_cli_live_smoke_script_exists():
    path = REPO / "scripts" / "status_bar_cost_classic_cli_live_smoke.py"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "classic cli live status bar cost smoke ok" in text
    assert "post-turn" in text.lower() or "post_turn" in text
    assert "smoke_gemini_35_flash_cache_cost_not_na" in text


def test_repo_gateway_delegates_to_usage_snapshot():
    gateway = (REPO / "tui_gateway" / "server.py").read_text(encoding="utf-8")
    assert "build_session_usage_snapshot" in gateway


def test_repo_verify_usage_cost_bar_script_exists():
    assert (REPO / "scripts" / "verify_usage_cost_bar.py").is_file()


def test_repo_ui_usage_helpers_export_cost_formatters():
    usage_ts = (REPO / "ui-tui" / "src" / "domain" / "usage.ts").read_text(encoding="utf-8")
    assert "export function mergeUsage" in usage_ts
    assert "export function formatStatusBarCost" in usage_ts
    assert "export function shouldShowStatusBarCost" in usage_ts
    assert "value !== undefined" in usage_ts


def test_repo_status_rule_uses_cost_helpers():
    chrome = (REPO / "ui-tui" / "src" / "components" / "appChrome.tsx").read_text(
        encoding="utf-8"
    )
    assert "resolveStatusRuleLayout" in chrome


def test_repo_gateway_and_slash_cost_toggle():
    gateway = (REPO / "tui_gateway" / "server.py").read_text(encoding="utf-8")
    assert 'if key == "cost":' in gateway
    assert 'display.show_cost' in gateway
    core = (REPO / "ui-tui" / "src" / "app" / "slash" / "commands" / "core.ts").read_text(
        encoding="utf-8"
    )
    assert "name: 'cost'" in core


def test_repo_gateway_smoke_script_exists():
    path = REPO / "scripts" / "status_bar_cost_gateway_smoke.py"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "_smoke_cost_breakdown" in text
    assert "cost_breakdown_pct" in text


def test_diagnose_renderer_drift_checks_show_cost():
    diag = (REPO / "scripts" / "diagnose_renderer.py").read_text(encoding="utf-8")
    assertive = '"show_cost"' in diag or "'show_cost'" in diag
    assert assertive


def test_institutional_e2e_script_checks_show_cost():
    e2e = (REPO / "windows" / "audits" / "RUN_INSTITUTIONAL_E2E.ps1").read_text(
        encoding="utf-8"
    )
    assert "show_cost=true" in e2e


def test_get_usage_includes_cost_breakdown_when_pricing_available():
    from agent.usage_pricing import CostResult, PricingEntry
    from tui_gateway import server

    agent = SimpleNamespace(
        model="anthropic/claude-opus-4-7",
        provider="anthropic",
        base_url="https://api.anthropic.com",
        session_input_tokens=1000,
        session_output_tokens=500,
        session_cache_read_tokens=100,
        session_cache_write_tokens=200,
        session_prompt_tokens=1300,
        session_completion_tokens=500,
        session_total_tokens=1800,
        session_api_calls=2,
        context_compressor=None,
    )
    entry = PricingEntry(
        input_cost_per_million=Decimal("5"),
        output_cost_per_million=Decimal("25"),
        cache_read_cost_per_million=Decimal("0.5"),
        cache_write_cost_per_million=Decimal("6.25"),
        source="official_docs_snapshot",
    )
    cost = CostResult(
        amount_usd=Decimal("0.023"),
        status="estimated",
        source="official_docs_snapshot",
        label="test",
    )
    with patch("agent.usage_pricing.estimate_usage_cost", return_value=cost), patch(
        "agent.usage_pricing.get_pricing_entry", return_value=entry
    ):
        usage = server._get_usage(agent)

    assert usage["cost_usd"] == pytest.approx(0.023)
    assert "cost_breakdown_usd" in usage
    assert "cost_breakdown_pct" in usage


def test_get_usage_includes_cost_usd_when_pricing_returns_amount():
    from agent.usage_pricing import CostResult
    from tui_gateway import server

    agent = SimpleNamespace(
        model="openai/gpt-4o-mini",
        provider="openai",
        base_url="https://api.openai.com/v1",
        session_input_tokens=1000,
        session_output_tokens=500,
        session_cache_read_tokens=0,
        session_cache_write_tokens=0,
        session_prompt_tokens=1000,
        session_completion_tokens=500,
        session_total_tokens=1500,
        session_api_calls=2,
        context_compressor=None,
    )
    cost = CostResult(
        amount_usd=Decimal("0.0042"),
        status="estimated",
        source="provider_models_api",
        label="test",
    )
    with patch("agent.usage_pricing.estimate_usage_cost", return_value=cost):
        usage = server._get_usage(agent)

    assert usage["cost_usd"] == pytest.approx(0.0042)
    assert usage["cost_status"] == "estimated"
    assert usage["calls"] == 2


def test_get_usage_omits_cost_usd_when_pricing_unknown():
    from agent.usage_pricing import CostResult
    from tui_gateway import server

    agent = SimpleNamespace(
        model="local/unknown-model",
        provider="local",
        base_url="",
        session_input_tokens=100,
        session_output_tokens=50,
        session_cache_read_tokens=0,
        session_cache_write_tokens=0,
        session_prompt_tokens=100,
        session_completion_tokens=50,
        session_total_tokens=150,
        session_api_calls=1,
        context_compressor=None,
    )
    cost = CostResult(
        amount_usd=None,
        status="unknown",
        source="none",
        label="unknown",
    )
    with patch("agent.usage_pricing.estimate_usage_cost", return_value=cost):
        usage = server._get_usage(agent)

    assert "cost_usd" not in usage
    assert usage["cost_status"] == "unknown"


def test_runtime_profiles_show_cost_true_when_hermes_home_available():
    """Skip when no local Hermes home (CI); fail when home exists but drifted."""
    local = Path.home() / "AppData" / "Local" / "hermes"
    legacy = Path.home() / ".hermes"
    root = local if (local / "config.yaml").is_file() else legacy
    if not (root / "config.yaml").is_file():
        pytest.skip("no local Hermes home")

    profiles = root / "profiles"
    missing: list[str] = []
    for prof_dir in sorted(profiles.iterdir()) if profiles.is_dir() else []:
        if not prof_dir.is_dir():
            continue
        cfg_path = prof_dir / "config.yaml"
        if not cfg_path.is_file():
            missing.append(f"{prof_dir.name}: geen config.yaml")
            continue
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        display = cfg.get("display") if isinstance(cfg.get("display"), dict) else {}
        if display.get("show_cost") is not True:
            missing.append(f"{prof_dir.name}: show_cost != true")
        if display.get("cost_bar_mode") != "rich":
            missing.append(f"{prof_dir.name}: cost_bar_mode != rich")

    root_cfg = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8")) or {}
    root_display = root_cfg.get("display") if isinstance(root_cfg.get("display"), dict) else {}
    if root_display.get("show_cost") is not True:
        missing.append("root: show_cost != true")
    if root_display.get("cost_bar_mode") != "rich":
        missing.append("root: cost_bar_mode != rich")

    assert not missing, "display drift: " + "; ".join(missing)
