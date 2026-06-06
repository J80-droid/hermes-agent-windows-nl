"""Single chained argparse hook for fork CLI subcommands (profile use, config get, tools post-setup).

Upstream ``hermes_cli.main`` has no ``config get`` subparser; this patch injects
``get`` on the ``config_command`` subparser group (once), adds ``profile use``
fork flags, and registers ``hermes tools post-setup``. Skips duplicate registration
when upstream already defines equivalent parsers.
"""
from __future__ import annotations

import sys

_PROFILE_USE_FLAGS = (
    ("--fix-hermes-home", {"action": "store_true", "help": "Normalize User HERMES_HOME"}),
    ("--no-sync-env", {"action": "store_true", "help": "Skip API env sync"}),
    ("--sync-env", {"action": "store_true", "help": "Force API env sync"}),
    ("--no-restart-gateway", {"action": "store_true", "help": "Do not restart gateway"}),
    ("--restart-gateway", {"action": "store_true", "help": "Restart gateway if it was running"}),
    ("--restart-chat", {"action": "store_true", "help": "Relaunch chat after switch"}),
)


def _wrap_cmd_tools_handler(func):
    if getattr(func, "_fork_cmd_tools_wrapped", False):
        return func

    def cmd_tools(args):
        action = getattr(args, "tools_action", None)
        if action == "post-setup":
            from hermes_cli.tools_config import run_post_setup_command

            sys.exit(run_post_setup_command(args))
        return func(args)

    cmd_tools.__name__ = getattr(func, "__name__", "cmd_tools")
    cmd_tools._fork_cmd_tools_wrapped = True  # type: ignore[attr-defined]
    return cmd_tools


def apply_argparse_fork_patch() -> None:
    import argparse

    if getattr(argparse._SubParsersAction, "_fork_argparse_patch_applied", False):
        return

    _orig_add_parser = argparse._SubParsersAction.add_parser
    _orig_set_defaults = argparse.ArgumentParser.set_defaults

    def _tools_subparser_has_post_setup(subparsers_action) -> bool:
        choices = getattr(subparsers_action, "choices", None)
        if isinstance(choices, dict) and "post-setup" in choices:
            return True
        name_map = getattr(subparsers_action, "_name_parser_map", None)
        return isinstance(name_map, dict) and "post-setup" in name_map

    def _ensure_tools_post_setup_parser(subparsers_action) -> None:
        if getattr(subparsers_action, "_fork_tools_post_setup_registered", False):
            return
        if getattr(subparsers_action, "dest", None) != "tools_action":
            return
        if _tools_subparser_has_post_setup(subparsers_action):
            subparsers_action._fork_tools_post_setup_registered = True  # type: ignore[attr-defined]
            return
        post_p = _orig_add_parser(
            subparsers_action,
            "post-setup",
            help="Run a provider's post-setup install hook (npm/pip/binary)",
            description=(
                "Run the install/bootstrap hook a tool backend declares — the\n"
                "same step `hermes tools` runs after you pick a provider that\n"
                "needs extra dependencies (browser Chromium, Camofox, cua-driver,\n"
                "KittenTTS/Piper, ddgs, Spotify, Langfuse, xAI). Stable,\n"
                "non-interactive target the dashboard spawns to drive backend\n"
                "setup."
            ),
        )
        post_p.add_argument(
            "post_setup_key",
            metavar="KEY",
            help="Post-setup hook key (e.g. agent_browser, camofox, kittentts)",
        )
        subparsers_action._fork_tools_post_setup_registered = True  # type: ignore[attr-defined]

    def _inject_tools_post_setup_late(parser: argparse.ArgumentParser) -> None:
        """Register post-setup after upstream tools subparsers (avoids duplicate with Nous Tier A)."""
        for action in parser._actions:
            if not isinstance(action, argparse._SubParsersAction):
                continue
            if getattr(action, "dest", None) != "tools_action":
                continue
            if _tools_subparser_has_post_setup(action):
                return
            _ensure_tools_post_setup_parser(action)

    def set_defaults(self, **kwargs):
        func = kwargs.get("func")
        if callable(func) and func.__name__ == "cmd_tools":
            kwargs = dict(kwargs)
            kwargs["func"] = _wrap_cmd_tools_handler(func)
            _inject_tools_post_setup_late(self)
        return _orig_set_defaults(self, **kwargs)

    def _config_subparser_has_get(subparsers_action) -> bool:
        choices = getattr(subparsers_action, "choices", None)
        if isinstance(choices, dict) and "get" in choices:
            return True
        name_map = getattr(subparsers_action, "_name_parser_map", None)
        return isinstance(name_map, dict) and "get" in name_map

    def _ensure_config_get_parser(subparsers_action) -> None:
        """Upstream has no ``config get``; register it on the config subparser group."""
        if getattr(subparsers_action, "_fork_config_get_registered", False):
            return
        if _config_subparser_has_get(subparsers_action):
            subparsers_action._fork_config_get_registered = True  # type: ignore[attr-defined]
            return
        get_p = _orig_add_parser(
            subparsers_action,
            "get",
            help="Get a configuration value (dotted key)",
        )
        get_p.add_argument(
            "config_key",
            help="Dotted key (e.g. auxiliary.vision.provider)",
        )
        subparsers_action._fork_config_get_registered = True  # type: ignore[attr-defined]

    def add_parser(self, name, *args, **kwargs):
        parser = _orig_add_parser(self, name, *args, **kwargs)
        dest = getattr(self, "dest", None)
        if name == "use" and dest == "profile_action":
            existing = {tuple(a.option_strings) for a in parser._actions if a.option_strings}
            for opt, kw in _PROFILE_USE_FLAGS:
                if (opt,) not in existing:
                    parser.add_argument(opt, **kw)
        elif dest == "config_command":
            if name == "get":
                if not any(getattr(a, "dest", None) == "config_key" for a in parser._actions):
                    parser.add_argument(
                        "config_key",
                        help="Dotted key (e.g. auxiliary.vision.provider)",
                    )
            else:
                _ensure_config_get_parser(self)
        elif dest == "tools_action" and name == "post-setup":
            if not any(
                getattr(a, "dest", None) == "post_setup_key" for a in parser._actions
            ):
                parser.add_argument(
                    "post_setup_key",
                    metavar="KEY",
                    help="Post-setup hook key (e.g. agent_browser, camofox, kittentts)",
                )
        return parser

    argparse._SubParsersAction.add_parser = add_parser  # type: ignore[method-assign]
    argparse.ArgumentParser.set_defaults = set_defaults  # type: ignore[method-assign]
    argparse._SubParsersAction._fork_argparse_patch_applied = True  # type: ignore[attr-defined]
