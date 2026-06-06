"""Register fork overlay modules and apply runtime patches (Nous Tier B).

Tier A (``cli.py``, upstream ``hermes_cli/*``, ``web/``, ``ui-tui/``) stays byte-identical
to ``upstream/main``. Fork behavior is loaded from ``overlay/hermes_cli/`` and
``overlay/agent/``, then wired via ``_apply_runtime_patches()`` (CLI cost bar, ``/cost``,
Gemini pricing, model-catalog guard).

Entry points:
  - ``PYTHONSTARTUP``: ``overlay/bootstrap_startup.py`` (see ``Invoke-HermesOverlayBootstrap.ps1``)
  - Explicit: ``python -c "from overlay.bootstrap import install; install()"``

``install()`` is idempotent. On failure, ``_installed`` stays False (no partial patch state).
Required modules: see ``_REQUIRED_HERMES_CLI``; optional gaps log a warning only.

Docs: ``docs/NOUS_OVERLAY_ARCHITECTURE.md`` · E2E: ``audits/RUN_NOUS_OVERLAY_INSTITUTIONAL_E2E.bat``
"""
from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType

logger = logging.getLogger(__name__)

_OVERLAY_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _OVERLAY_ROOT.parent
_HERMES_CLI_OVERLAY = _OVERLAY_ROOT / "hermes_cli"
_AGENT_OVERLAY = _OVERLAY_ROOT / "agent"

_OVERLAY_AGENT_MODULES_EARLY: tuple[str, ...] = (
    "venice_usage",
    "jatevo_usage",
    "review_snapshot",
)
_OVERLAY_AGENT_MODULES_LATE: tuple[str, ...] = (
    "rich_output",
)

_OVERLAY_HERMES_CLI_MODULES: tuple[str, ...] = (
    "model_runtime_config",
    "markdown_output_normalize",
    "institutional_render",
    "usage_snapshot",
    "cli_pending_queue",
    "status_bar_cost",
    "status_bar_throughput",
    "status_bar_prompt_elapsed",
    "status_bar_layout",
    "institutional_new_chat_notice",
    "legal_architecture_brief",
    "profile_model_inheritance",
    "profile_switch",
    "profile_mcp_format",
    "relaunch",
    "skills_hub_init",
    "win32_console",
    "venice_model_picker",
    "display_markdown",
    "filesystem_sandbox",
    "hardware_backend",
    "config_snapshot",
)

_REQUIRED_HERMES_CLI: frozenset[str] = frozenset(
    {
        "model_runtime_config",
        "usage_snapshot",
        "status_bar_cost",
    }
)

_installed = False


def _attach_overlay_parent(fq_name: str, mod: ModuleType) -> None:
    """Expose overlay shims on parent packages (pytest monkeypatch, tab-completion)."""
    if "." not in fq_name:
        return
    parent_name, _, stem = fq_name.partition(".")
    if not stem or "." in stem:
        return
    parent = sys.modules.get(parent_name)
    if parent is None:
        return
    setattr(parent, stem, mod)


def _load_module(fq_name: str, path: Path) -> ModuleType:
    """Load overlay source from disk; return cached ``sys.modules`` entry if present."""
    if fq_name in sys.modules:
        mod = sys.modules[fq_name]
        _attach_overlay_parent(fq_name, mod)
        return mod
    if not path.is_file():
        raise FileNotFoundError(f"overlay module missing: {path}")
    spec = importlib.util.spec_from_file_location(fq_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load spec for {fq_name}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[fq_name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        del sys.modules[fq_name]
        raise
    _attach_overlay_parent(fq_name, mod)
    return mod


def _load_overlay_modules() -> None:
    """Register overlay shims. Required ``hermes_cli`` stems raise; optional stems warn."""
    missing: list[str] = []
    for stem in _OVERLAY_AGENT_MODULES_EARLY:
        path = _AGENT_OVERLAY / f"{stem}.py"
        try:
            _load_module(f"agent.{stem}", path)
        except Exception as exc:
            logger.error("overlay agent.%s failed: %s", stem, exc)
            raise

    for stem in _OVERLAY_HERMES_CLI_MODULES:
        path = _HERMES_CLI_OVERLAY / f"{stem}.py"
        try:
            _load_module(f"hermes_cli.{stem}", path)
        except Exception as exc:
            logger.error("overlay hermes_cli.%s failed: %s", stem, exc)
            if stem in _REQUIRED_HERMES_CLI:
                raise
            missing.append(stem)

    for stem in _OVERLAY_AGENT_MODULES_LATE:
        path = _AGENT_OVERLAY / f"{stem}.py"
        try:
            _load_module(f"agent.{stem}", path)
        except Exception as exc:
            logger.error("overlay agent.%s failed: %s", stem, exc)
            raise

    if missing:
        logger.warning("optional overlay hermes_cli modules skipped: %s", ", ".join(missing))


def _apply_runtime_patches() -> None:
    """Monkey-patch Tier A classes after overlay modules are in ``sys.modules``."""
    from overlay.agent.agent_throughput_fork_patch import apply_agent_throughput_fork_patch
    from overlay.agent.pricing_fork_patch import apply_pricing_fork_patch
    from overlay.agent.prompt_builder_fork_patch import apply_prompt_builder_fork_patch
    from overlay.cli_fork_patch import apply_cli_fork_patch as apply_cli_bron_fork_patch
    from overlay.hermes_cli.argparse_fork_patch import apply_argparse_fork_patch
    from overlay.hermes_cli.auth_fork_patch import apply_auth_fork_patch
    from overlay.hermes_cli.clipboard_fork_patch import apply_clipboard_fork_patch
    from overlay.hermes_cli.cli_command_patches import apply_cli_command_patches
    from overlay.hermes_cli.cli_fork_patch import apply_cli_fork_patch
    from overlay.hermes_cli.cli_profile_fork_patch import apply_cli_profile_fork_patch
    from overlay.hermes_cli.config_fork_patch import apply_config_fork_patch
    from overlay.hermes_cli.doctor_fork_patch import apply_doctor_fork_patch
    from overlay.hermes_cli.main_fork_patch import apply_main_fork_patch
    from overlay.hermes_cli.models_fork_patch import apply_models_fork_patch
    from overlay.hermes_cli.profiles_fork_patch import apply_profiles_fork_patch
    from overlay.hermes_cli.tools_config_fork_patch import apply_tools_config_fork_patch
    from overlay.hermes_cli.web_server_fork_patch import apply_web_server_fork_patch
    from overlay.tools.file_tools_fork_patch import apply_file_tools_fork_patch
    from overlay.tools.process_registry_fork_patch import apply_process_registry_fork_patch
    from overlay.tui_gateway.gateway_config_fork_patch import apply_gateway_config_fork_patch

    apply_argparse_fork_patch()
    apply_cli_bron_fork_patch()
    apply_clipboard_fork_patch()
    apply_main_fork_patch()
    apply_profiles_fork_patch()
    apply_process_registry_fork_patch()
    apply_pricing_fork_patch()
    apply_models_fork_patch()
    apply_auth_fork_patch()
    apply_config_fork_patch()
    apply_doctor_fork_patch()
    apply_tools_config_fork_patch()
    apply_web_server_fork_patch()
    apply_prompt_builder_fork_patch()
    apply_agent_throughput_fork_patch()
    apply_cli_fork_patch()
    apply_cli_profile_fork_patch()
    apply_cli_command_patches()
    apply_gateway_config_fork_patch()
    apply_file_tools_fork_patch()


def install() -> None:
    """Register overlay shims and runtime patches (idempotent; fails loud on partial install)."""
    global _installed
    if _installed:
        return

    repo = str(_REPO_ROOT)
    if repo not in sys.path:
        sys.path.insert(0, repo)

    _load_overlay_modules()
    _apply_runtime_patches()
    try:
        from overlay.hermes_cli.config_fork_patch import _rebind_load_config_references
        import hermes_cli.config as _config_mod

        _rebind_load_config_references(_config_mod)
    except Exception:
        logger.debug("load_config rebind after patches failed", exc_info=True)
    _installed = True


def install_startup() -> None:
    """PYTHONSTARTUP entrypoint — log failures without aborting interpreter startup."""
    try:
        install()
    except Exception:
        logger.exception("overlay bootstrap failed — fork features may be unavailable")
