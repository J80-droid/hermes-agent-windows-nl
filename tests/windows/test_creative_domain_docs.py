"""Repo-docs en paden voor creative domein."""

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "docs" / "domain_toolsets.yaml"
DOMAINS_EXAMPLE = REPO / "docs" / "domains.yaml.example"
CREATIVE_DOCS = REPO / "docs" / "13_Creative"


def test_creative_docs_tree_exists():
    for name in (
        "README.md",
        "ONBOARDING.md",
        "PROCEDURES.md",
        "ESCALATION.md",
        "CREATIVE_ACTIVE_MATTERS.md",
    ):
        assert (CREATIVE_DOCS / name).is_file(), f"missing {name}"
    for lens in ("Visual", "Motion", "Interactive", "Writing"):
        assert (CREATIVE_DOCS / lens / "README.md").is_file(), f"missing lens {lens}"


def test_soul_creative_template_has_lenses():
    text = (REPO / "docs/templates/SOUL_CREATIVE_DOMAIN.md").read_text(encoding="utf-8")
    assert "### Creative-lenzen" in text
    assert "hyperframes" in text.lower()
    assert "manim-video" in text


def test_domains_example_creative_block():
    data = yaml.safe_load(DOMAINS_EXAMPLE.read_text(encoding="utf-8"))
    domains = data.get("domains") or []
    names = [d.get("name") for d in domains if isinstance(d, dict)]
    assert "creative" in names
    creative = next(d for d in domains if d.get("name") == "creative")
    assert creative.get("source_dir") == "13_Creative"
    assert creative.get("profile_name") == "creative"
    assert creative.get("mcp_name") == "lancedb-creative"


def _fork_skill_paths(fork_map: dict) -> list[Path]:
    paths: list[Path] = []
    for value in fork_map.values():
        if not isinstance(value, str):
            continue
        m = re.match(r"^\s*((?:skills|optional-skills)/\S+)", value)
        if m:
            paths.append(REPO / m.group(1).rstrip("/"))
    return paths


def test_creative_fork_skill_paths_on_disk():
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    creative = (data.get("profiles") or {}).get("creative") or {}
    fork = creative.get("fork_creative_skills") or {}
    assert fork, "fork_creative_skills leeg"
    missing = [p for p in _fork_skill_paths(fork) if not p.is_dir()]
    assert not missing, f"ontbrekende skill-mappen: {missing}"
