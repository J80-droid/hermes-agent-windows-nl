"""Unit tests voor ``audits/CreativeDomainE2E.harness.py``.

Piramide:
  - Unit (hier): helpers + scenario's met mocks (geen subprocess pytest-keten in C9)
  - Integratie: ``test_creative_domain_e2e_harness_runs`` (volledige harness via subprocess)

Conventie: zelfde importlib-laden als ``tests/windows/test_provision_profile_from_manifest.py``.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
HARNESS_PATH = REPO / "audits" / "CreativeDomainE2E.harness.py"


def _load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("creative_domain_e2e_harness", HARNESS_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def harness() -> ModuleType:
    assert HARNESS_PATH.is_file(), "CreativeDomainE2E.harness.py ontbreekt"
    return _load_harness()


@pytest.fixture(autouse=True)
def _reset_harness_counters(harness: ModuleType) -> None:
    harness.FAILURES = 0
    harness.STEP = 0
    yield
    harness.FAILURES = 0
    harness.STEP = 0


# --- _step ---


def test_step_ok_increments_step_only(harness: ModuleType) -> None:
    harness._step("naam", True, "detail")
    assert harness.STEP == 1
    assert harness.FAILURES == 0


def test_step_fail_increments_failures(harness: ModuleType) -> None:
    harness._step("naam", False, "fout")
    assert harness.STEP == 1
    assert harness.FAILURES == 1


def test_step_empty_detail(harness: ModuleType) -> None:
    harness._step("zonder-detail", True)
    assert harness.STEP == 1


# --- _creative_spec ---


def test_creative_spec_happy_path(harness: ModuleType) -> None:
    data = harness._load_manifest()
    spec = harness._creative_spec(data)
    assert spec.get("creative_lenses")
    assert "terminal" in (spec.get("platform_toolsets") or {}).get("cli", [])


def test_creative_spec_missing_profile_raises(harness: ModuleType) -> None:
    with pytest.raises(KeyError, match="profiles.creative"):
        harness._creative_spec({"profiles": {}})


def test_creative_spec_non_dict_profile_raises(harness: ModuleType) -> None:
    with pytest.raises(KeyError, match="profiles.creative"):
        harness._creative_spec({"profiles": {"creative": "geen-dict"}})


def test_creative_spec_missing_profiles_key_raises(harness: ModuleType) -> None:
    with pytest.raises(KeyError, match="profiles.creative"):
        harness._creative_spec({})


# --- _load_manifest ---


def test_load_manifest_not_mapping_raises(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(harness, "_read", lambda _rel: "[]\n")
    with pytest.raises(ValueError, match="geen mapping"):
        harness._load_manifest()


def test_load_manifest_invalid_yaml_raises(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(harness, "_read", lambda _rel: ":\n  bad: [\n")
    with pytest.raises(yaml.YAMLError):
        harness._load_manifest()


# --- _fork_paths_from_manifest ---


def test_fork_paths_parses_skills_and_optional(harness: ModuleType) -> None:
    spec = {
        "fork_creative_skills": {
            "manim": "skills/creative/manim-video/ - bundled",
            "hf": "optional-skills/creative/hyperframes/ - optional",
            "skip_int": 42,
            "skip_plain": "geen pad prefix",
            "skip_empty": "",
        }
    }
    paths = harness._fork_paths_from_manifest(spec)
    rel = {p.relative_to(REPO).as_posix() for p in paths}
    assert rel == {
        "skills/creative/manim-video",
        "optional-skills/creative/hyperframes",
    }


def test_fork_paths_empty_fork(harness: ModuleType) -> None:
    assert harness._fork_paths_from_manifest({}) == []
    assert harness._fork_paths_from_manifest({"fork_creative_skills": {}}) == []


def test_fork_paths_whitespace_prefix(harness: ModuleType) -> None:
    spec = {"fork_creative_skills": {"x": "  skills/creative/foo/  - note"}}
    paths = harness._fork_paths_from_manifest(spec)
    assert len(paths) == 1
    assert paths[0].name == "foo"


# --- _hermes_runtime_root ---


def test_hermes_runtime_root_prefers_localappdata(
    harness: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    local = tmp_path / "hermes"
    local.mkdir()
    (local / "config.yaml").write_text("x: 1\n", encoding="utf-8")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "no_home")
    assert harness._hermes_runtime_root() == local


def test_hermes_runtime_root_falls_back_to_dot_hermes(
    harness: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    hermes = home / ".hermes"
    hermes.mkdir(parents=True)
    (hermes / "config.yaml").write_text("x: 1\n", encoding="utf-8")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "empty"))
    monkeypatch.setattr(Path, "home", lambda: home)
    assert harness._hermes_runtime_root() == hermes


def test_hermes_runtime_root_none_when_missing(
    harness: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "nope"))
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "also_nope")
    assert harness._hermes_runtime_root() is None


# --- C1 repo artefacts ---


def test_c1_fails_when_artefact_missing(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    real_is_file = Path.is_file

    def _fake_is_file(self: Path) -> bool:
        if self == REPO / harness.REQUIRED_ARTEFACTS[0]:
            return False
        return real_is_file(self)

    monkeypatch.setattr(Path, "is_file", _fake_is_file)
    harness.test_c1_repo_artefacts()
    assert harness.FAILURES == 1


def test_c1_passes_when_all_present(harness: ModuleType) -> None:
    harness.test_c1_repo_artefacts()
    assert harness.FAILURES == 0
    assert harness.STEP == 1


# --- C2 manifest contract ---


def _minimal_creative_spec(*, cli: list[str] | None = None, optional: list[str] | None = None) -> dict[str, Any]:
    cli = cli or ["mcp", "file", "memory", "skills", "clarify", "web", "browser", "terminal"]
    optional = optional or ["image_gen", "vision", "code_execution"]
    return {
        "platform_toolsets": {"cli": cli},
        "optional_toolsets": optional,
        "ask_triggers": {k: "v" for k in optional},
        "creative_lenses": {
            "visual": "v",
            "motion": "m",
            "interactive": "i",
            "writing": "w",
        },
        "fork_creative_skills": {"manim_video": "x", "hyperframes": "y"},
        "max_tools": 24,
    }


def test_c2_fails_without_terminal(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    data = {
        "never_default_global": ["image_gen"],
        "profiles": {
            "creative": _minimal_creative_spec(cli=["mcp", "file", "memory", "skills", "clarify"]),
        },
    }
    monkeypatch.setattr(harness, "_load_manifest", lambda: data)
    harness.test_c2_manifest_contract()
    assert harness.FAILURES == 1


def test_c2_fails_optional_without_ask_trigger(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    spec = _minimal_creative_spec()
    spec["ask_triggers"] = {"image_gen": "only one"}
    data = {"never_default_global": [], "profiles": {"creative": spec}}
    monkeypatch.setattr(harness, "_load_manifest", lambda: data)
    harness.test_c2_manifest_contract()
    assert harness.FAILURES == 1


def test_c2_fails_cli_overlaps_never_default(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    data = {
        "never_default_global": ["image_gen"],
        "profiles": {
            "creative": _minimal_creative_spec(
                cli=["mcp", "file", "memory", "skills", "clarify", "terminal", "image_gen"],
                optional=[],
            ),
        },
    }
    monkeypatch.setattr(harness, "_load_manifest", lambda: data)
    harness.test_c2_manifest_contract()
    assert harness.FAILURES == 1


def test_c2_fails_max_tools_too_low(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    spec = _minimal_creative_spec()
    spec["max_tools"] = 2
    data = {"never_default_global": [], "profiles": {"creative": spec}}
    monkeypatch.setattr(harness, "_load_manifest", lambda: data)
    harness.test_c2_manifest_contract()
    assert harness.FAILURES == 1


def test_c2_passes_valid_contract(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    data = {"never_default_global": ["image_gen"], "profiles": {"creative": _minimal_creative_spec()}}
    monkeypatch.setattr(harness, "_load_manifest", lambda: data)
    harness.test_c2_manifest_contract()
    assert harness.FAILURES == 0


# --- C4 domains example ---


def test_c4_fails_without_creative_domain(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(harness, "_read", lambda _rel: yaml.safe_dump({"domains": [{"name": "legal"}]}))
    harness.test_c4_domains_example()
    assert harness.FAILURES == 1


def test_c4_fails_wrong_source_dir(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    body = yaml.safe_dump(
        {
            "domains": [
                {
                    "name": "creative",
                    "source_dir": "99_Wrong",
                    "mcp_name": "lancedb-creative",
                    "profile_name": "creative",
                }
            ]
        }
    )
    monkeypatch.setattr(harness, "_read", lambda _rel: body)
    harness.test_c4_domains_example()
    assert harness.FAILURES == 1


def test_c4_passes_valid_example(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    body = yaml.safe_dump(
        {
            "domains": [
                {
                    "name": "creative",
                    "source_dir": "13_Creative",
                    "mcp_name": "lancedb-creative",
                    "profile_name": "creative",
                }
            ]
        }
    )
    monkeypatch.setattr(harness, "_read", lambda _rel: body)
    harness.test_c4_domains_example()
    assert harness.FAILURES == 0


# --- C5 orchestrator ---


def test_c5_fails_missing_routing_keywords(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    def _read(rel: str) -> str:
        if "ORCHESTRATOR" in rel:
            return "geen creative hier"
        if "SOUL_CORE" in rel:
            return "| `legal` |"
        return "13_Creative en creative in blueprint"

    monkeypatch.setattr(harness, "_read", _read)
    harness.test_c5_orchestrator_routing()
    assert harness.FAILURES == 1


# --- C6 SyncSoulSnippet ---


def test_c6_fails_without_creative_in_list(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    ps1 = """
function Get-DomainSoulProfileNames {
    return @('core', 'legal')
}
"""
    monkeypatch.setattr(harness, "_read", lambda _rel: ps1)
    harness.test_c6_sync_soul_profile_list()
    assert harness.FAILURES == 1


def test_c6_fails_wrong_profile_count(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    ps1 = """
function Get-DomainSoulProfileNames {
    return @('core', 'legal', 'creative')
}
"""
    monkeypatch.setattr(harness, "_read", lambda _rel: ps1)
    harness.test_c6_sync_soul_profile_list()
    assert harness.FAILURES == 1


def test_c6_passes_fourteen_profiles(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    names = (
        "'core', 'legal', 'academics', 'operations', 'trading', 'gaming', "
        "'philosophy', 'logistics', 'ventures', 'ict', 'security', 'dev', 'data', 'creative'"
    )
    ps1 = f"function Get-DomainSoulProfileNames {{\n    return @({names})\n}}\n"
    monkeypatch.setattr(harness, "_read", lambda _rel: ps1)
    harness.test_c6_sync_soul_profile_list()
    assert harness.FAILURES == 0


# --- C7 backup ---


def test_c7_fails_missing_backup_hook(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(harness, "_read", lambda _rel: "# geen creative backup\n")
    harness.test_c7_backup_active_matters()
    assert harness.FAILURES == 1


# --- C8 SOUL template ---


def test_c8_fails_missing_lens_section(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(harness, "_read", lambda _rel: "# SOUL zonder lenzen\n")
    harness.test_c8_soul_template_gates()
    assert harness.FAILURES == 1


# --- C9 pytest subprocess (mocked) ---


def test_c9_fails_on_pytest_nonzero(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    proc = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="FAILED tests\n")
    monkeypatch.setattr(harness.subprocess, "run", lambda *a, **k: proc)
    harness.test_c9_pytest_creative_subset()
    assert harness.FAILURES == 1


def test_c9_passes_on_pytest_zero(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    proc = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="11 passed in 1.0s\n", stderr=""
    )
    monkeypatch.setattr(harness.subprocess, "run", lambda *a, **k: proc)
    harness.test_c9_pytest_creative_subset()
    assert harness.FAILURES == 0


def test_c9_uses_repo_cwd(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def _capture_run(cmd, **kwargs):
        seen["cwd"] = kwargs.get("cwd")
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ok\n", stderr="")

    monkeypatch.setattr(harness.subprocess, "run", _capture_run)
    harness.test_c9_pytest_creative_subset()
    assert seen["cwd"] == str(REPO)
    assert "test_creative_domain_docs.py" in " ".join(seen["cmd"])


# --- C10 provision (mocked sync module) ---


def test_c10_fails_when_provision_returns_false(
    harness: ModuleType, monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = MagicMock()
    mod._provision_profile.return_value = False
    mod._sync_profile.return_value = True
    mod._apply_trust_memory_limits = MagicMock(return_value=True)
    monkeypatch.setattr(harness, "_load_sync_module", lambda: mod)
    monkeypatch.setattr(harness, "_load_manifest", harness._load_manifest)
    harness.test_c10_temp_provision_sync()
    assert harness.FAILURES == 1
    mod._apply_trust_memory_limits.assert_not_called()


def test_c10_passes_with_mocked_sync_and_files(
    harness: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    spec = _minimal_creative_spec()
    cli = (spec.get("platform_toolsets") or {}).get("cli") or []

    class _FakeTempDir:
        def __enter__(self) -> str:
            root = tmp_path / "td"
            root.mkdir(exist_ok=True)
            hermes = root / "hermes"
            prof = hermes / "profiles" / "creative"
            prof.mkdir(parents=True)
            (hermes / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
            (prof / "config.yaml").write_text(
                yaml.safe_dump({"platform_toolsets": {"cli": cli}}),
                encoding="utf-8",
            )
            (prof / "SOUL.md").write_text(
                "### Creative-lenzen\nOutput conventions (institutional)\n",
                encoding="utf-8",
            )
            return str(root)

        def __exit__(self, *_args: object) -> None:
            return None

    mod = MagicMock()
    mod._provision_profile.return_value = True
    mod._sync_profile.return_value = True
    monkeypatch.setattr(harness, "_load_sync_module", lambda: mod)
    monkeypatch.setattr(harness, "_load_manifest", lambda: {"profiles": {"creative": spec}})
    monkeypatch.setattr(harness.tempfile, "TemporaryDirectory", _FakeTempDir)
    harness.test_c10_temp_provision_sync()
    assert harness.FAILURES == 0


def test_c10_fails_when_config_missing_after_sync(
    harness: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    spec = _minimal_creative_spec()

    class _EmptyTempDir:
        def __enter__(self) -> str:
            root = tmp_path / "empty"
            root.mkdir()
            (root / "hermes").mkdir()
            (root / "hermes" / "config.yaml").write_text("x: 1\n", encoding="utf-8")
            return str(root)

        def __exit__(self, *_args: object) -> None:
            return None

    mod = MagicMock()
    mod._provision_profile.return_value = True
    mod._sync_profile.return_value = True
    monkeypatch.setattr(harness, "_load_sync_module", lambda: mod)
    monkeypatch.setattr(harness, "_load_manifest", lambda: {"profiles": {"creative": spec}})
    monkeypatch.setattr(harness.tempfile, "TemporaryDirectory", _EmptyTempDir)
    harness.test_c10_temp_provision_sync()
    assert harness.FAILURES == 1


# --- C11 runtime check ---


def test_c11_skips_when_no_runtime_profile(
    harness: ModuleType, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(harness, "_hermes_runtime_root", lambda: None)
    harness.test_c11_runtime_manifest_check()
    assert harness.FAILURES == 0
    assert harness.STEP == 1


def test_c11_skips_when_config_missing(
    harness: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    hermes = tmp_path / "hermes"
    hermes.mkdir()
    (hermes / "config.yaml").write_text("x: 1\n", encoding="utf-8")
    monkeypatch.setattr(harness, "_hermes_runtime_root", lambda: hermes)
    harness.test_c11_runtime_manifest_check()
    assert harness.FAILURES == 0


def test_c11_fails_on_drift(
    harness: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    hermes = tmp_path / "hermes"
    prof = hermes / "profiles" / "creative"
    prof.mkdir(parents=True)
    (hermes / "config.yaml").write_text("x: 1\n", encoding="utf-8")
    (prof / "config.yaml").write_text("platform_toolsets:\n  cli: [mcp]\n", encoding="utf-8")
    monkeypatch.setattr(harness, "_hermes_runtime_root", lambda: hermes)
    proc = subprocess.CompletedProcess(args=[], returncode=2, stdout="drift\n", stderr="")
    monkeypatch.setattr(harness.subprocess, "run", lambda *a, **k: proc)
    harness.test_c11_runtime_manifest_check()
    assert harness.FAILURES == 1


def test_c11_passes_when_check_ok(
    harness: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    hermes = tmp_path / "hermes"
    prof = hermes / "profiles" / "creative"
    prof.mkdir(parents=True)
    (hermes / "config.yaml").write_text("x: 1\n", encoding="utf-8")
    (prof / "config.yaml").write_text("platform_toolsets:\n  cli: []\n", encoding="utf-8")
    monkeypatch.setattr(harness, "_hermes_runtime_root", lambda: hermes)
    proc = subprocess.CompletedProcess(args=[], returncode=0, stdout="OK\n", stderr="")
    monkeypatch.setattr(harness.subprocess, "run", lambda *a, **k: proc)
    harness.test_c11_runtime_manifest_check()
    assert harness.FAILURES == 0


# --- main() ---


def test_main_returns_zero_when_all_pass(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "test_c1_repo_artefacts",
        "test_c2_manifest_contract",
        "test_c3_fork_skill_paths",
        "test_c4_domains_example",
        "test_c5_orchestrator_routing",
        "test_c6_sync_soul_profile_list",
        "test_c7_backup_active_matters",
        "test_c8_soul_template_gates",
        "test_c9_pytest_creative_subset",
        "test_c10_temp_provision_sync",
        "test_c11_runtime_manifest_check",
    ):
        monkeypatch.setattr(harness, name, lambda: None)
    assert harness.main() == 0


def test_main_returns_one_when_step_fails(harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail() -> None:
        harness._step("forced", False)

    monkeypatch.setattr(harness, "test_c1_repo_artefacts", _fail)
    for name in (
        "test_c2_manifest_contract",
        "test_c3_fork_skill_paths",
        "test_c4_domains_example",
        "test_c5_orchestrator_routing",
        "test_c6_sync_soul_profile_list",
        "test_c7_backup_active_matters",
        "test_c8_soul_template_gates",
        "test_c9_pytest_creative_subset",
        "test_c10_temp_provision_sync",
        "test_c11_runtime_manifest_check",
    ):
        monkeypatch.setattr(harness, name, lambda: None)
    assert harness.main() == 1
    assert harness.FAILURES >= 1


# --- Integratie (subprocess) ---


@pytest.mark.e2e
def test_creative_domain_e2e_harness_runs() -> None:
    """Volledige audits/CreativeDomainE2E.harness.py — zelfde als RUN_CREATIVE_DOMAIN_E2E.bat."""
    proc = subprocess.run(
        [sys.executable, str(HARNESS_PATH)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert proc.returncode == 0, (proc.stderr or proc.stdout)[-4000:]
    assert "ALL PASS" in (proc.stdout or "")
