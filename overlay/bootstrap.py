"""
Register fork ``hermes_cli.*`` modules from overlay before core imports.

Loaded via PYTHONSTARTUP (see windows/scripts/Invoke-HermesOverlayBootstrap.ps1)
or explicitly: ``python -c "from overlay.bootstrap import install; install()"``.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_OVERLAY_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _OVERLAY_ROOT.parent
_HERMES_CLI_OVERLAY = _OVERLAY_ROOT / "hermes_cli"
_AGENT_OVERLAY = _OVERLAY_ROOT / "agent"

# Fork-only agent modules (not in upstream).
_OVERLAY_AGENT_MODULES_EARLY: tuple[str, ...] = (
    "venice_usage",
    "jatevo_usage",
    "review_snapshot",
)
_OVERLAY_AGENT_MODULES_LATE: tuple[str, ...] = (
    "rich_output",  # imports hermes_cli.display_markdown
)

# Fork-only modules (not in upstream hermes_cli). Order: deps first.
_OVERLAY_HERMES_CLI_MODULES: tuple[str, ...] = (
    "markdown_output_normalize",
    "institutional_render",
    "usage_snapshot",
    "status_bar_cost",
    "status_bar_throughput",
    "status_bar_prompt_elapsed",
    "status_bar_layout",
    "institutional_new_chat_notice",
    "legal_architecture_brief",
    "profile_model_inheritance",
    "profile_switch",
    "relaunch",
    "venice_model_picker",
    "display_markdown",
)

_installed = False


def _load_module(fq_name: str, path: Path) -> ModuleType | None:
    if fq_name in sys.modules:
        return sys.modules[fq_name]
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(fq_name, path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[fq_name] = mod
    spec.loader.exec_module(mod)
    return mod


def install() -> None:
    """Register overlay hermes_cli shims and ensure repo root is importable."""
    global _installed
    if _installed:
        return
    repo = str(_REPO_ROOT)
    if repo not in sys.path:
        sys.path.insert(0, repo)
    # Do not prepend overlay/ alone — overlay/hermes_cli/ must not shadow package hermes_cli.

    for stem in _OVERLAY_AGENT_MODULES_EARLY:
        _load_module(f"agent.{stem}", _AGENT_OVERLAY / f"{stem}.py")

    for stem in _OVERLAY_HERMES_CLI_MODULES:
        _load_module(f"hermes_cli.{stem}", _HERMES_CLI_OVERLAY / f"{stem}.py")

    for stem in _OVERLAY_AGENT_MODULES_LATE:
        _load_module(f"agent.{stem}", _AGENT_OVERLAY / f"{stem}.py")

    _installed = True


def install_startup() -> None:
    """PYTHONSTARTUP entrypoint."""
    try:
        install()
    except Exception:
        import traceback

        traceback.print_exc()
