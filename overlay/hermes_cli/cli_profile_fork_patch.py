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


class CliForkProfileChatUxMixin:
    """TUI profile switch UX (sticky prompt, inline routing, confirm modal)."""

    def _slash_confirm_footer_hint(self, choice_count: int) -> str:
        return f"Kies 1–{choice_count} of Esc om te annuleren"

    def _print_slash_confirm_box(
        self,
        title: str,
        detail: str,
        choices: list[tuple[str, str, str]],
    ) -> None:
        import cli as cli_mod

        cli_mod._cprint("")
        cli_mod._cprint(f"  {cli_mod._ACCENT}{title}{cli_mod._RST}")
        for line in detail.splitlines():
            if line.strip():
                cli_mod._cprint(f"  {cli_mod._DIM}{line}{cli_mod._RST}")
        for idx, (_val, label, desc) in enumerate(choices):
            cli_mod._cprint(f"  [{idx + 1}] {label} — {cli_mod._DIM}{desc}{cli_mod._RST}")
        cli_mod._cprint(f"  {cli_mod._DIM}{self._slash_confirm_footer_hint(len(choices))}{cli_mod._RST}")
        cli_mod._cprint("")

    def _prompt_slash_confirm_stdin_fallback(
        self,
        choices: list[tuple[str, str, str]],
        *,
        timeout: float = 90,
    ) -> str | None:
        lines = ["", "  ╭─ Bevestiging ─────────────────"]
        for idx, (_val, label, desc) in enumerate(choices):
            lines.append(f"  │  [{idx + 1}] {label} — {desc}")
        lines.append(f"  │  {self._slash_confirm_footer_hint(len(choices))}")
        lines.append("  ╰──────────────────────────────")
        lines.append("> ")
        return self._prompt_text_input("\n".join(lines), timeout=timeout)

    def _prompt_profile_switch_confirm(
        self,
        *,
        title: str,
        detail: str,
        choices: list[tuple[str, str, str]],
        timeout: float = 90,
    ) -> str | None:
        if getattr(self, "_app", None):
            return self._prompt_text_input_modal(
                title=title,
                detail=detail,
                choices=choices,
                timeout=timeout,
            )
        self._print_slash_confirm_box(title, detail, choices)
        return self._prompt_slash_confirm_stdin_fallback(choices, timeout=timeout)

    def _should_handle_profile_command_inline(self, text: str, has_images: bool = False) -> bool:
        import cli as cli_mod

        if has_images or not getattr(self, "_app", None):
            return False
        if not isinstance(text, str) or not text.strip():
            return False
        if cli_mod._looks_like_slash_command(text):
            try:
                from hermes_cli.commands import resolve_command

                base = text.strip().split()[0].lower().lstrip("/")
                cmd = resolve_command(base)
                return bool(cmd and cmd.name == "profile")
            except Exception:
                return False
        return cli_mod._parse_profile_switch_intent(text) is not None

    def _get_tui_prompt_symbols(self) -> tuple[str, str]:
        try:
            from hermes_cli.skin_engine import get_active_prompt_symbol

            symbol = get_active_prompt_symbol("❯ ")
        except Exception:
            symbol = "❯ "

        symbol = (symbol or "❯ ").rstrip() + " "

        try:
            from hermes_cli.profiles import get_active_profile

            profile = get_active_profile()
            if profile not in {"default", "custom"}:
                symbol = f"{profile} {symbol}"
        except Exception:
            pass
        stripped = symbol.rstrip()
        if not stripped:
            return "❯ ", "❯ "

        parts = stripped.split()
        candidate = parts[-1] if parts else ""
        arrow_chars = ("❯", ">", "$", "#", "›", "»", "→")
        if any(ch in candidate for ch in arrow_chars):
            return symbol, candidate.rstrip() + " "

        return symbol, symbol


_PROFILE_CHAT_UX_METHODS = (
    "_slash_confirm_footer_hint",
    "_print_slash_confirm_box",
    "_prompt_slash_confirm_stdin_fallback",
    "_prompt_profile_switch_confirm",
    "_should_handle_profile_command_inline",
    "_get_tui_prompt_symbols",
)


def apply_cli_profile_fork_patch() -> None:
    import cli as cli_mod
    import hermes_cli.main as main_mod

    if getattr(main_mod, "_fork_cli_profile_patch_applied", False):
        return

    cli_mod._parse_profile_switch_intent = parse_profile_switch_intent  # type: ignore[attr-defined]

    cls = cli_mod.HermesCLI
    for name in _PROFILE_CHAT_UX_METHODS:
        setattr(cls, name, getattr(CliForkProfileChatUxMixin, name))

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
