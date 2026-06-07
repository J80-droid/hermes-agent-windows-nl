"""Fork overlay tests for GET /api/display/assistant (institutional web palette).

Kept out of tests/hermes_cli/test_web_server.py to avoid upstream merge conflicts.
SSOT: docs/FORK_MERGE_POLICY.md
"""

from __future__ import annotations

import pytest

from overlay.bootstrap import install


@pytest.fixture(autouse=True)
def _bootstrap():
    install()


class TestAssistantDisplayEndpoint:
    @pytest.fixture(autouse=True)
    def _setup_test_client(self, monkeypatch, _isolate_hermes_home):
        try:
            from starlette.testclient import TestClient
        except ImportError:
            pytest.skip("fastapi/starlette not installed")

        import hermes_state
        from hermes_constants import get_hermes_home
        from hermes_cli.web_server import app, _SESSION_HEADER_NAME, _SESSION_TOKEN

        monkeypatch.setattr(hermes_state, "DEFAULT_DB_PATH", get_hermes_home() / "state.db")

        self.client = TestClient(app)
        self.client.headers[_SESSION_HEADER_NAME] = _SESSION_TOKEN

    def test_get_assistant_display_settings(self):
        resp = self.client.get("/api/display/assistant")
        assert resp.status_code == 200
        data = resp.json()
        assert "assistant_render_style" in data
        assert "assistant_palette" in data
        assert "assistant_label_columns" in data
        assert isinstance(data["assistant_label_columns"], bool)
