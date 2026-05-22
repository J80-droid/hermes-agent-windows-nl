"""Validate docs/domain_toolsets.yaml structure."""
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "docs" / "domain_toolsets.yaml"

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
}

REQUIRED_BASE = {"mcp", "file", "memory", "skills", "clarify"}


def _load():
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


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


def test_sync_scripts_exist():
    assert (REPO / "windows/scripts/sync_profile_toolsets_from_manifest.py").is_file()
    assert (REPO / "windows/SYNC_DOMAIN_TOOLSETS.bat").is_file()
    assert (REPO / "docs/templates/SOUL_SHARED_TOOL_GOVERNANCE.md").is_file()
