"""Institutioneel E2E: profielwissel in chat (CLI-intent + prompt + SOUL-tekst).

Geen live LLM: we testen code en runtime SOUL, niet of Gemini de regel volgt.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from cli import HermesCLI, _parse_profile_switch_intent

REPO = Path(__file__).resolve().parents[2]


class TestParseProfileSwitchIntent:
    @pytest.mark.parametrize(
        "phrase,expected",
        [
            ("verander profiel naar core", "core"),
            ("schakel naar core", "core"),
            ("wissel naar legal", "legal"),
            ("profile core", "core"),
            ("profiel legal", "legal"),
            ("switch to trading", "trading"),
        ],
    )
    def test_recognizes_switch_phrases(self, phrase, expected, monkeypatch):
        def _exists(name: str) -> bool:
            return name in {
                "core",
                "legal",
                "trading",
                "academics",
                "gaming",
                "logistics",
                "operations",
                "philosophy",
                "ventures",
                "default",
            }

        monkeypatch.setattr(
            "hermes_cli.profiles.profile_exists",
            _exists,
        )
        assert _parse_profile_switch_intent(phrase) == expected

    @pytest.mark.parametrize(
        "phrase",
        [
            "wat is core orchestrator",
            "leg uit het legal profiel uit",
            "/profile use core",
            "",
        ],
    )
    def test_no_false_positive(self, phrase):
        assert _parse_profile_switch_intent(phrase) is None


class TestSoulProfileSwitchGuidance:
    def test_shared_interaction_template_documents_slash_command(self):
        text = (REPO / "docs/templates/SOUL_SHARED_INTERACTION.md").read_text(
            encoding="utf-8"
        )
        assert "/profile use" in text
        assert "/profile <naam>" in text or "/profile use <naam>" in text
        assert "nooit" in text.lower() or "Nooit" in text
        assert "buiten de sessie" in text

    def test_runtime_legal_soul_has_profile_switch_rule(self):
        legal_soul = (
            Path.home() / "AppData/Local/hermes/profiles/legal/SOUL.md"
        )
        if not legal_soul.is_file():
            pytest.skip("Geen runtime legal SOUL op deze machine")
        text = legal_soul.read_text(encoding="utf-8")
        assert "/profile use" in text
        assert "Profiel wisselen" in text or "profiel wisselen" in text.lower()


class TestTuiPromptUsesStickyProfile:
    def _make_cli_stub(self):
        cli = HermesCLI.__new__(HermesCLI)
        cli._sudo_state = None
        cli._secret_state = None
        cli._approval_state = None
        cli._clarify_state = None
        cli._slash_confirm_state = None
        cli._clarify_freetext = False
        cli._command_running = False
        cli._agent_running = False
        cli._voice_recording = False
        cli._voice_processing = False
        cli._voice_mode = False
        cli._command_spinner_frame = lambda: "⟳"
        return cli

    @pytest.mark.parametrize("sticky", ["core", "legal"])
    def test_prompt_shows_sticky_not_hermes_home_path(self, sticky):
        cli = self._make_cli_stub()
        with patch("hermes_cli.profiles.get_active_profile", return_value=sticky):
            with patch("hermes_cli.skin_engine.get_active_prompt_symbol", return_value="❯ "):
                normal, _suffix = cli._get_tui_prompt_symbols()
        assert normal.startswith(f"{sticky} ")
        assert "❯" in normal


class TestLaunchIntegration:
    def test_launch_hermes_wires_institutional_runtime(self):
        text = (REPO / "windows/launch_hermes.bat").read_text(encoding="utf-8")
        assert "launch_institutional_runtime.ps1" in text

    def test_launch_hermes_wires_soul_deploy_before_institutional(self):
        text = (REPO / "windows/launch_hermes.bat").read_text(encoding="utf-8")
        assert "launch_soul_anatomy_deploy.ps1" in text
        assert "HERMES_SKIP_SOUL_DEPLOY_ON_START" in text
        assert text.index("launch_soul_anatomy_deploy.ps1") < text.index(
            "launch_institutional_runtime.ps1"
        )

    def test_post_git_pull_uses_soul_deploy_force(self):
        text = (REPO / "windows/POST_GIT_PULL.bat").read_text(encoding="utf-8")
        assert "launch_soul_anatomy_deploy.ps1" in text
        assert "-Force" in text

    def test_soul_deploy_start_e2e_runner_exists(self):
        assert (REPO / "windows/audits/RUN_SOUL_DEPLOY_START_E2E.ps1").is_file()

    def test_cli_defines_profile_intent_parser(self):
        import cli as cli_mod

        assert callable(getattr(cli_mod, "_parse_profile_switch_intent", None))
