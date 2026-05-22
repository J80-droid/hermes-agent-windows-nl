"""Team display defaults must match institutional presentation policy."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_team_display_defaults_institutional():
    text = (REPO / "windows/team_display.defaults").read_text(encoding="utf-8")
    assert "final_response_markdown=render" in text
    assert "skin=default" in text
    assert "streaming=false" in text
    assert "compact=false" in text
    assert "compact=true" not in text
