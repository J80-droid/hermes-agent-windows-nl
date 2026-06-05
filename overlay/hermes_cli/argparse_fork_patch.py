"""Single chained argparse hook for fork CLI subcommands (profile use, config get).

Upstream ``hermes_cli.main`` has no ``config get`` subparser; this patch injects
``get`` on the ``config_command`` subparser group (once), and adds ``profile use``
fork flags. Skips duplicate registration when upstream already defines ``get``.
"""
from __future__ import annotations

_PROFILE_USE_FLAGS = (
    ("--fix-hermes-home", {"action": "store_true", "help": "Normalize User HERMES_HOME"}),
    ("--no-sync-env", {"action": "store_true", "help": "Skip API env sync"}),
    ("--sync-env", {"action": "store_true", "help": "Force API env sync"}),
    ("--no-restart-gateway", {"action": "store_true", "help": "Do not restart gateway"}),
    ("--restart-gateway", {"action": "store_true", "help": "Restart gateway if it was running"}),
    ("--restart-chat", {"action": "store_true", "help": "Relaunch chat after switch"}),
)


def apply_argparse_fork_patch() -> None:
    import argparse

    if getattr(argparse._SubParsersAction, "_fork_argparse_patch_applied", False):
        return

    _orig_add_parser = argparse._SubParsersAction.add_parser

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
        return parser

    argparse._SubParsersAction.add_parser = add_parser  # type: ignore[method-assign]
    argparse._SubParsersAction._fork_argparse_patch_applied = True  # type: ignore[attr-defined]
