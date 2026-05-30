"""Tests for /legal-architectuur slash command."""

from hermes_cli.commands import resolve_command
from hermes_cli.legal_architecture_brief import build_legal_architecture_brief


def test_legal_architectuur_command_registered():
    cmd = resolve_command("legal-architectuur")
    assert cmd is not None
    assert cmd.name == "legal-architectuur"
    assert cmd.cli_only is False


def test_legal_arch_alias():
    cmd = resolve_command("legal-arch")
    assert cmd is not None
    assert cmd.name == "legal-architectuur"


def test_brief_core_redirect():
    brief = build_legal_architecture_brief("core")
    assert "profile use legal" in brief.lower() or "/profile use legal" in brief
    assert "lenzen" in brief.lower()


def test_brief_explains_lens_not_six_profiles():
    brief = build_legal_architecture_brief("legal")
    assert "geen aparte hermes-profielen" in brief.lower() or "geen aparte Hermes-profielen" in brief
    assert "lenzen" in brief.lower()
