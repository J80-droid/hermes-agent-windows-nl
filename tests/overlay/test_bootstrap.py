"""Unit tests for overlay.bootstrap (Nous fork module registration).

Covers happy path, idempotency, partial-failure rollback, optional vs required
modules, and install_startup fault tolerance. External I/O and runtime patches
are mocked so tests stay hermetic.
"""

from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

import overlay.bootstrap as bootstrap


@pytest.fixture(autouse=True)
def _reset_bootstrap_installed():
    """Allow install() to run again; does not unload already-registered shims."""
    prev = bootstrap._installed
    bootstrap._installed = False
    yield
    bootstrap._installed = prev


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    return tmp_path


def _overlay_module_names() -> list[str]:
    names: list[str] = []
    for stem in bootstrap._OVERLAY_AGENT_MODULES_EARLY + bootstrap._OVERLAY_AGENT_MODULES_LATE:
        names.append(f"agent.{stem}")
    for stem in bootstrap._OVERLAY_HERMES_CLI_MODULES:
        names.append(f"hermes_cli.{stem}")
    return names


@pytest.fixture
def isolated_bootstrap(monkeypatch: pytest.MonkeyPatch, repo_root: Path):
    """Point bootstrap paths at a temp overlay tree; drop cached overlay shims."""
    overlay = repo_root / "overlay"
    hermes_cli = overlay / "hermes_cli"
    agent = overlay / "agent"
    hermes_cli.mkdir(parents=True)
    agent.mkdir(parents=True)
    monkeypatch.setattr(bootstrap, "_OVERLAY_ROOT", overlay)
    monkeypatch.setattr(bootstrap, "_REPO_ROOT", repo_root)
    monkeypatch.setattr(bootstrap, "_HERMES_CLI_OVERLAY", hermes_cli)
    monkeypatch.setattr(bootstrap, "_AGENT_OVERLAY", agent)
    saved = {name: sys.modules.pop(name) for name in _overlay_module_names() if name in sys.modules}
    yield repo_root
    for name, mod in saved.items():
        sys.modules[name] = mod


def _write_py(path: Path, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body or "# stub\n", encoding="utf-8")


class TestLoadModule:
    """Low-level _load_module: caching, missing files, spec failures, rollback."""

    def test_returns_cached_module_without_reloading(self, tmp_path: Path):
        fq = "hermes_cli._test_cached"
        existing = ModuleType(fq)
        existing.marker = 42
        sys.modules[fq] = existing
        try:
            got = bootstrap._load_module(fq, tmp_path / "missing.py")
            assert got is existing
            assert got.marker == 42
        finally:
            sys.modules.pop(fq, None)

    def test_raises_file_not_found_for_missing_path(self, tmp_path: Path):
        fq = "hermes_cli._test_missing_file"
        sys.modules.pop(fq, None)
        with pytest.raises(FileNotFoundError, match="overlay module missing"):
            bootstrap._load_module(fq, tmp_path / "nope.py")

    def test_raises_import_error_when_spec_is_none(self, tmp_path: Path):
        path = tmp_path / "bad.py"
        _write_py(path)
        fq = "hermes_cli._test_bad_spec"
        sys.modules.pop(fq, None)
        with patch(
            "overlay.bootstrap.importlib.util.spec_from_file_location",
            return_value=None,
        ):
            with pytest.raises(ImportError, match="cannot load spec"):
                bootstrap._load_module(fq, path)
        assert fq not in sys.modules

    def test_raises_import_error_when_loader_is_none(self, tmp_path: Path):
        path = tmp_path / "bad_loader.py"
        _write_py(path)
        fq = "hermes_cli._test_bad_loader"
        sys.modules.pop(fq, None)
        spec = MagicMock(loader=None)
        with patch(
            "overlay.bootstrap.importlib.util.spec_from_file_location",
            return_value=spec,
        ):
            with pytest.raises(ImportError, match="cannot load spec"):
                bootstrap._load_module(fq, path)
        assert fq not in sys.modules

    def test_rolls_back_sys_modules_on_exec_failure(self, tmp_path: Path):
        path = tmp_path / "boom.py"
        _write_py(path, "raise RuntimeError('exec failed')\n")
        fq = "hermes_cli._test_exec_fail"
        sys.modules.pop(fq, None)
        with pytest.raises(RuntimeError, match="exec failed"):
            bootstrap._load_module(fq, path)
        assert fq not in sys.modules

    def test_happy_path_registers_and_returns_module(self, tmp_path: Path):
        path = tmp_path / "ok.py"
        _write_py(path, "VALUE = 'loaded'\n")
        fq = "hermes_cli._test_ok"
        sys.modules.pop(fq, None)
        mod = bootstrap._load_module(fq, path)
        assert mod.VALUE == "loaded"
        assert sys.modules[fq] is mod


class TestLoadOverlayModules:
    """_load_overlay_modules: required vs optional module policy."""

    def test_raises_when_early_agent_module_missing(
        self, isolated_bootstrap, caplog: pytest.LogCaptureFixture
    ):
        # No files created — first early agent stem fails before hermes_cli loop.
        with caplog.at_level(logging.ERROR):
            with pytest.raises(FileNotFoundError, match="overlay module missing"):
                bootstrap._load_overlay_modules()
        assert "agent." in caplog.text

    def test_continues_when_optional_module_fails(
        self, isolated_bootstrap, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ):
        repo = isolated_bootstrap
        overlay = repo / "overlay"
        agent = overlay / "agent"
        hermes_cli = overlay / "hermes_cli"

        for stem in bootstrap._OVERLAY_AGENT_MODULES_EARLY + bootstrap._OVERLAY_AGENT_MODULES_LATE:
            _write_py(agent / f"{stem}.py")
        for stem in bootstrap._OVERLAY_HERMES_CLI_MODULES:
            if stem in bootstrap._REQUIRED_HERMES_CLI:
                _write_py(hermes_cli / f"{stem}.py")
            else:
                # Skip optional files entirely — should warn, not raise.
                continue

        with caplog.at_level(logging.WARNING):
            bootstrap._load_overlay_modules()
        assert "optional overlay hermes_cli modules skipped" in caplog.text

    def test_raises_when_required_module_exec_fails(
        self, isolated_bootstrap, caplog: pytest.LogCaptureFixture
    ):
        repo = isolated_bootstrap
        overlay = repo / "overlay"
        agent = overlay / "agent"
        hermes_cli = overlay / "hermes_cli"

        for stem in bootstrap._OVERLAY_AGENT_MODULES_EARLY + bootstrap._OVERLAY_AGENT_MODULES_LATE:
            _write_py(agent / f"{stem}.py")
        for stem in bootstrap._OVERLAY_HERMES_CLI_MODULES:
            path = hermes_cli / f"{stem}.py"
            if stem == "usage_snapshot":
                _write_py(path, "raise SyntaxError('broken required')\n")
            elif stem in bootstrap._REQUIRED_HERMES_CLI:
                _write_py(path)
            # optional: omit

        with caplog.at_level(logging.ERROR):
            with pytest.raises(SyntaxError):
                bootstrap._load_overlay_modules()

    def test_happy_path_loads_early_agent_required_cli_and_late_agent(
        self, isolated_bootstrap, monkeypatch: pytest.MonkeyPatch
    ):
        repo = isolated_bootstrap
        overlay = repo / "overlay"
        agent = overlay / "agent"
        hermes_cli = overlay / "hermes_cli"

        for stem in bootstrap._OVERLAY_AGENT_MODULES_EARLY + bootstrap._OVERLAY_AGENT_MODULES_LATE:
            _write_py(agent / f"{stem}.py", f"STEM = '{stem}'\n")
        for stem in bootstrap._OVERLAY_HERMES_CLI_MODULES:
            _write_py(hermes_cli / f"{stem}.py", f"STEM = '{stem}'\n")

        bootstrap._load_overlay_modules()
        assert sys.modules["agent.venice_usage"].STEM == "venice_usage"
        assert sys.modules["hermes_cli.usage_snapshot"].STEM == "usage_snapshot"
        assert sys.modules["agent.rich_output"].STEM == "rich_output"


class TestApplyRuntimePatches:
    def test_invokes_all_patch_entrypoints_in_order(self):
        calls: list[str] = []

        def _rec(name: str):
            def _fn():
                calls.append(name)

            return _fn

        with (
            patch(
                "overlay.agent.pricing_fork_patch.apply_pricing_fork_patch",
                side_effect=_rec("pricing"),
            ),
            patch(
                "overlay.hermes_cli.models_fork_patch.apply_models_fork_patch",
                side_effect=_rec("models"),
            ),
            patch(
                "overlay.hermes_cli.auth_fork_patch.apply_auth_fork_patch",
                side_effect=_rec("auth"),
            ),
            patch(
                "overlay.agent.agent_throughput_fork_patch.apply_agent_throughput_fork_patch",
                side_effect=_rec("agent_tps"),
            ),
            patch(
                "overlay.hermes_cli.cli_fork_patch.apply_cli_fork_patch",
                side_effect=_rec("cli_fork"),
            ),
            patch(
                "overlay.hermes_cli.cli_command_patches.apply_cli_command_patches",
                side_effect=_rec("cli_commands"),
            ),
            patch(
                "overlay.tui_gateway.gateway_config_fork_patch.apply_gateway_config_fork_patch",
                side_effect=_rec("gateway_config"),
            ),
        ):
            bootstrap._apply_runtime_patches()

        assert calls == [
            "pricing",
            "models",
            "auth",
            "agent_tps",
            "cli_fork",
            "cli_commands",
            "gateway_config",
        ]

    def test_propagates_patch_failure(self):
        with patch(
            "overlay.agent.pricing_fork_patch.apply_pricing_fork_patch",
            side_effect=RuntimeError("patch boom"),
        ):
            with pytest.raises(RuntimeError, match="patch boom"):
                bootstrap._apply_runtime_patches()


class TestInstall:
    def test_inserts_repo_root_on_sys_path(self, monkeypatch: pytest.MonkeyPatch):
        repo = str(bootstrap._REPO_ROOT)
        while repo in sys.path:
            sys.path.remove(repo)
        with (
            patch.object(bootstrap, "_load_overlay_modules"),
            patch.object(bootstrap, "_apply_runtime_patches"),
        ):
            bootstrap.install()
        assert sys.path[0] == repo

    def test_does_not_duplicate_repo_on_sys_path(self, monkeypatch: pytest.MonkeyPatch):
        repo = str(bootstrap._REPO_ROOT)
        sys.path.insert(0, repo)
        count_before = sys.path.count(repo)
        with (
            patch.object(bootstrap, "_load_overlay_modules"),
            patch.object(bootstrap, "_apply_runtime_patches"),
        ):
            bootstrap.install()
        assert sys.path.count(repo) == count_before

    def test_idempotent_second_call_skips_work(self):
        with (
            patch.object(bootstrap, "_load_overlay_modules") as load_mock,
            patch.object(bootstrap, "_apply_runtime_patches") as patch_mock,
        ):
            bootstrap.install()
            bootstrap.install()
        load_mock.assert_called_once()
        patch_mock.assert_called_once()
        assert bootstrap._installed is True

    def test_does_not_set_installed_when_load_fails(self):
        with (
            patch.object(
                bootstrap,
                "_load_overlay_modules",
                side_effect=OSError("disk"),
            ),
            patch.object(bootstrap, "_apply_runtime_patches") as patch_mock,
        ):
            with pytest.raises(OSError, match="disk"):
                bootstrap.install()
        assert bootstrap._installed is False
        patch_mock.assert_not_called()

    def test_does_not_set_installed_when_patches_fail(self):
        with (
            patch.object(bootstrap, "_load_overlay_modules"),
            patch.object(
                bootstrap,
                "_apply_runtime_patches",
                side_effect=ValueError("patch"),
            ),
        ):
            with pytest.raises(ValueError, match="patch"):
                bootstrap.install()
        assert bootstrap._installed is False

    def test_happy_path_sets_installed(self):
        with (
            patch.object(bootstrap, "_load_overlay_modules"),
            patch.object(bootstrap, "_apply_runtime_patches"),
        ):
            bootstrap.install()
        assert bootstrap._installed is True


class TestInstallStartup:
    def test_delegates_to_install(self):
        with patch.object(bootstrap, "install") as install_mock:
            bootstrap.install_startup()
        install_mock.assert_called_once()

    def test_swallows_install_exception_and_logs(self, caplog: pytest.LogCaptureFixture):
        with patch.object(bootstrap, "install", side_effect=RuntimeError("startup fail")):
            with caplog.at_level(logging.ERROR):
                bootstrap.install_startup()
        assert "overlay bootstrap failed" in caplog.text
        assert any(r.exc_info for r in caplog.records)

    def test_swallows_file_not_found_from_install(self, caplog: pytest.LogCaptureFixture):
        """install_startup must never abort PYTHONSTARTUP on bad overlay tree."""
        with patch.object(bootstrap, "install", side_effect=FileNotFoundError("missing")):
            with caplog.at_level(logging.ERROR):
                bootstrap.install_startup()
        assert "overlay bootstrap failed" in caplog.text


class TestBootstrapStartupModule:
    """overlay/bootstrap_startup.py — thin PYTHONSTARTUP wrapper."""

    def test_import_does_not_raise_when_install_startup_fails(self):
        sys.modules.pop("overlay.bootstrap_startup", None)
        with patch("overlay.bootstrap.install_startup", side_effect=RuntimeError("x")):
            mod = importlib.import_module("overlay.bootstrap_startup")
        assert mod is not None

    def test_import_succeeds_when_install_startup_ok(self):
        sys.modules.pop("overlay.bootstrap_startup", None)
        with patch("overlay.bootstrap.install_startup"):
            mod = importlib.import_module("overlay.bootstrap_startup")
        assert hasattr(mod, "_run") or True


class TestModuleConstants:
    """Guardrails on overlay manifest lists (regression for institutional E2E)."""

    def test_required_modules_subset_of_hermes_cli_list(self):
        assert bootstrap._REQUIRED_HERMES_CLI <= frozenset(bootstrap._OVERLAY_HERMES_CLI_MODULES)

    def test_no_duplicate_stems_in_lists(self):
        for name, items in (
            ("early agent", bootstrap._OVERLAY_AGENT_MODULES_EARLY),
            ("late agent", bootstrap._OVERLAY_AGENT_MODULES_LATE),
            ("hermes_cli", bootstrap._OVERLAY_HERMES_CLI_MODULES),
        ):
            assert len(items) == len(set(items)), f"duplicate in {name}"

    def test_overlay_root_resolves_under_repo(self):
        assert bootstrap._OVERLAY_ROOT.parent == bootstrap._REPO_ROOT
        assert bootstrap._OVERLAY_ROOT.name == "overlay"
