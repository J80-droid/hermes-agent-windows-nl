"""Profile switch CLI + natural-language intent (Tier B overlay; no Tier A edits)."""
from __future__ import annotations

import re
import sys
from typing import Optional


def parse_profile_switch_intent(text: str) -> Optional[str]:
    """Recognize NL/EN profile-switch phrases and map to a profile id."""
    if not text or not isinstance(text, str):
        return None
    t = text.strip()
    if not t or t.startswith("/"):
        return None
    try:
        from hermes_cli.profiles import normalize_profile_name, profile_exists
    except Exception:
        return None

    patterns = (
        re.compile(
            r"(?i)^(?:verander|wissel|schakel|switch|zet|set|ga|go)"
            r"(?:\s+(?:mijn|het|naar|to|to\s+the))?\s+"
            r"(?:profiel\s+|profile\s+)?([a-z][a-z0-9_-]{0,63})(?:\s+(?:profiel|profile))?\s*[.!?]*$"
        ),
        re.compile(
            r"(?i)^(?:verander|wissel|schakel|switch)\s+"
            r"(?:profiel|profile)\s+(?:naar|to)\s+([a-z][a-z0-9_-]{0,63})\s*[.!?]*$"
        ),
        re.compile(r"(?i)^(?:profiel|profile)\s+([a-z][a-z0-9_-]{0,63})\s*[.!?]*$"),
        re.compile(
            r"(?i)^(?:naar|to)\s+([a-z][a-z0-9_-]{0,63})(?:\s+(?:profiel|profile))?\s*[.!?]*$"
        ),
    )
    for pat in patterns:
        m = pat.match(t)
        if not m:
            continue
        try:
            canon = normalize_profile_name(m.group(1))
        except ValueError:
            continue
        if canon == "default" or profile_exists(canon):
            return canon
    return None


def _profile_use_execute(args) -> None:
    from hermes_cli.profile_switch import execute_profile_switch, print_switch_messages
    from hermes_cli.profiles import get_active_profile

    name = args.profile_name
    sync_env = None
    if getattr(args, "no_sync_env", False):
        sync_env = False
    elif getattr(args, "sync_env", None):
        sync_env = True

    restart_gateway = None
    if getattr(args, "no_restart_gateway", False):
        restart_gateway = False
    elif getattr(args, "restart_gateway", None):
        restart_gateway = True

    try:
        result = execute_profile_switch(
            name,
            old_profile=get_active_profile(),
            sync_env=sync_env,
            restart_gateway=restart_gateway,
            fix_hermes_home=getattr(args, "fix_hermes_home", False),
        )
        print_switch_messages(result)
        if name == "default":
            print("Switched to: default (~/.hermes)")
        else:
            print(f"Switched to: {name}")
        if getattr(args, "restart_chat", False):
            from hermes_cli.relaunch import relaunch_chat_after_profile_switch

            relaunch_chat_after_profile_switch(name)
    except (ValueError, FileNotFoundError) as exc:
        print(f"Error: {exc}")
        sys.exit(1)


def apply_cli_profile_fork_patch() -> None:
    import cli as cli_mod
    import hermes_cli.main as main_mod

    if getattr(main_mod, "_fork_cli_profile_patch_applied", False):
        return

    cli_mod._parse_profile_switch_intent = parse_profile_switch_intent  # type: ignore[attr-defined]

    _orig_cmd_profile = main_mod.cmd_profile

    def cmd_profile(args):
        action = getattr(args, "profile_action", None)
        if action == "use" and (
            getattr(args, "fix_hermes_home", False)
            or getattr(args, "no_sync_env", False)
            or getattr(args, "no_restart_gateway", False)
            or getattr(args, "sync_env", False)
            or getattr(args, "restart_gateway", False)
            or getattr(args, "restart_chat", False)
        ):
            _profile_use_execute(args)
            return
        return _orig_cmd_profile(args)

    main_mod.cmd_profile = cmd_profile  # type: ignore[assignment]
    main_mod._fork_cli_profile_patch_applied = True  # type: ignore[attr-defined]
