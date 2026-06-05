"""Single chained argparse hook for fork CLI subcommands (profile use, config get)."""
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

    def add_parser(self, name, *args, **kwargs):
        parser = _orig_add_parser(self, name, *args, **kwargs)
        dest = getattr(self, "dest", None)
        if name == "use" and dest == "profile_action":
            existing = {tuple(a.option_strings) for a in parser._actions if a.option_strings}
            for opt, kw in _PROFILE_USE_FLAGS:
                if (opt,) not in existing:
                    parser.add_argument(opt, **kw)
        elif name == "get" and dest == "config_command":
            if not any(getattr(a, "dest", None) == "config_key" for a in parser._actions):
                parser.add_argument(
                    "config_key",
                    help="Dotted key (e.g. auxiliary.vision.provider)",
                )
        return parser

    argparse._SubParsersAction.add_parser = add_parser  # type: ignore[method-assign]
    argparse._SubParsersAction._fork_argparse_patch_applied = True  # type: ignore[attr-defined]
