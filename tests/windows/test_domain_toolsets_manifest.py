"""Validate docs/domain_toolsets.yaml structure (alle 14 profielen incl. creative).

Creative-specifiek: ``test_creative_*``; volledige E2E-poort: ``audits/RUN_CREATIVE_DOMAIN_E2E.bat``.
"""
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "docs" / "domain_toolsets.yaml"
_MANIFEST_CACHE: dict | None = None

REQUIRED_PROFILES = {
    "core",
    "legal",
    "academics",
    "trading",
    "operations",
    "logistics",
    "philosophy",
    "gaming",
    "ventures",
    "ict",
    "security",
    "dev",
    "data",
    "creative",
}

REQUIRED_BASE = {"mcp", "file", "memory", "skills", "clarify"}


def _load():
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is None:
        data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        _MANIFEST_CACHE = data
    return _MANIFEST_CACHE


def test_manifest_exists():
    assert MANIFEST.is_file()


def test_all_domain_profiles_present():
    data = _load()
    profiles = data.get("profiles") or {}
    assert REQUIRED_PROFILES <= set(profiles.keys())


def test_cli_excludes_never_default():
    data = _load()
    global_never = set(data.get("never_default_global") or [])
    for name, spec in (data.get("profiles") or {}).items():
        cli = set((spec.get("platform_toolsets") or {}).get("cli") or [])
        never = set(spec.get("never_default") or []) | global_never
        assert not (cli & never), f"{name}: cli overlaps never_default"
        optional = set(spec.get("optional_toolsets") or [])
        assert not (optional & cli), f"{name}: optional in cli"


def test_required_base_toolsets():
    data = _load()
    for name, spec in (data.get("profiles") or {}).items():
        cli = set((spec.get("platform_toolsets") or {}).get("cli") or [])
        missing = REQUIRED_BASE - cli
        assert not missing, f"{name}: missing base {missing}"


def test_root_empty_cli():
    data = _load()
    root_cli = (data.get("root") or {}).get("platform_toolsets", {}).get("cli")
    assert root_cli == []


def test_legal_has_lenses_doc():
    data = _load()
    legal = (data.get("profiles") or {}).get("legal") or {}
    lenses = legal.get("legal_lenses") or {}
    assert "arb" in lenses
    assert "klok" in lenses


def test_ict_has_lenses():
    data = _load()
    ict = (data.get("profiles") or {}).get("ict") or {}
    lenses = ict.get("ict_lenses") or {}
    assert "infra" in lenses
    assert "support" in lenses


def test_security_has_lenses():
    data = _load()
    sec = (data.get("profiles") or {}).get("security") or {}
    lenses = sec.get("security_lenses") or {}
    assert "pentest" in lenses
    assert "incident" in lenses


def test_dev_has_lenses():
    data = _load()
    dev = (data.get("profiles") or {}).get("dev") or {}
    lenses = dev.get("dev_lenses") or {}
    assert "backend" in lenses
    assert "quality" in lenses


def test_data_has_lenses():
    data = _load()
    data_prof = (data.get("profiles") or {}).get("data") or {}
    lenses = data_prof.get("data_lenses") or {}
    assert "database" in lenses
    assert "pipeline" in lenses


def test_creative_has_lenses():
    data = _load()
    creative = (data.get("profiles") or {}).get("creative") or {}
    lenses = creative.get("creative_lenses") or {}
    assert "visual" in lenses
    assert "motion" in lenses
    assert "interactive" in lenses
    assert "writing" in lenses


def test_creative_fork_skills():
    data = _load()
    creative = (data.get("profiles") or {}).get("creative") or {}
    skills = creative.get("fork_creative_skills") or {}
    assert "manim_video" in skills
    assert "hyperframes" in skills


def test_creative_ask_triggers_cover_optional():
    data = _load()
    creative = (data.get("profiles") or {}).get("creative") or {}
    optional = set(creative.get("optional_toolsets") or [])
    triggers = set((creative.get("ask_triggers") or {}).keys())
    missing = optional - triggers
    assert not missing, f"creative: optional zonder ask_trigger: {missing}"


def test_creative_cli_includes_terminal_for_hyperframes():
    data = _load()
    creative = (data.get("profiles") or {}).get("creative") or {}
    cli = set((creative.get("platform_toolsets") or {}).get("cli") or [])
    assert "terminal" in cli


def test_creative_max_tools_covers_worst_case():
    """cli + alle optional mag binnen max_tools blijven (geen stille truncation)."""
    data = _load()
    creative = (data.get("profiles") or {}).get("creative") or {}
    cli = (creative.get("platform_toolsets") or {}).get("cli") or []
    optional = creative.get("optional_toolsets") or []
    max_tools = int(creative.get("max_tools") or 0)
    assert max_tools >= len(cli) + len(optional)


def test_soul_templates_exist():
    assert (REPO / "docs/templates/SOUL_ICT_DOMAIN.md").is_file()
    assert (REPO / "docs/templates/SOUL_SECURITY_DOMAIN.md").is_file()
    assert (REPO / "docs/templates/SOUL_DEV_DOMAIN.md").is_file()
    assert (REPO / "docs/templates/SOUL_DATA_DOMAIN.md").is_file()
    assert (REPO / "docs/templates/SOUL_CREATIVE_DOMAIN.md").is_file()


def test_sync_scripts_exist():
    assert (REPO / "windows/scripts/sync_profile_toolsets_from_manifest.py").is_file()
    assert (REPO / "windows/SYNC_DOMAIN_TOOLSETS.bat").is_file()
    assert (REPO / "docs/templates/SOUL_SHARED_TOOL_GOVERNANCE.md").is_file()
