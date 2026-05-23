"""E2E smoke for OpenRouter Pareto Code router (model-gated min_coding_score)."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_repo_pareto_audit_script_exists():
    path = REPO / "windows" / "audits" / "RUN_PARETO_E2E.ps1"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "verify_pareto_router" in text


def test_repo_openrouter_plugin_model_gates_pareto():
    text = (
        REPO / "plugins" / "model-providers" / "openrouter" / "__init__.py"
    ).read_text(encoding="utf-8")
    assert 'model == "openrouter/pareto-code"' in text
    assert '"pareto-router"' in text or "'pareto-router'" in text
    assert "min_coding_score" in text


def test_repo_chat_completions_pareto_emission():
    text = (REPO / "agent" / "transports" / "chat_completions.py").read_text(encoding="utf-8")
    assert "openrouter/pareto-code" in text
    assert "pareto-router" in text


def test_repo_chat_completion_helpers_summary_pareto():
    text = (REPO / "agent" / "chat_completion_helpers.py").read_text(encoding="utf-8")
    assert "openrouter/pareto-code" in text
    assert "pareto-router" in text


def test_repo_config_documents_min_coding_score():
    text = (REPO / "hermes_cli" / "config.py").read_text(encoding="utf-8")
    assert "min_coding_score" in text
    assert "openrouter/pareto-code" in text


def test_repo_models_catalog_lists_pareto_code():
    text = (REPO / "hermes_cli" / "models.py").read_text(encoding="utf-8")
    assert "openrouter/pareto-code" in text


def test_repo_docs_mention_pareto_router():
    providers = (REPO / "website" / "docs" / "integrations" / "providers.md").read_text(
        encoding="utf-8"
    )
    config = (REPO / "website" / "docs" / "user-guide" / "configuration.md").read_text(
        encoding="utf-8"
    )
    assert "Pareto" in providers
    assert "pareto-code" in providers
    assert "pareto-router" in config or "Pareto" in config


def test_repo_verify_pareto_router_script():
    path = REPO / "scripts" / "verify_pareto_router.py"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "pareto-router" in text
