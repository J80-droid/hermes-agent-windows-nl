"""Fork helpers on top-level ``cli`` module (Tier B)."""
from __future__ import annotations


def apply_cli_fork_patch() -> None:
    import cli

    if getattr(cli, "_fork_cli_bron_patch_applied", False):
        return
    if hasattr(cli, "_wrap_bron_citations_for_display"):
        cli._fork_cli_bron_patch_applied = True  # type: ignore[attr-defined]
        return
    from hermes_cli.display_markdown import _wrap_bron_citations_for_display

    cli._wrap_bron_citations_for_display = _wrap_bron_citations_for_display  # type: ignore[attr-defined]
    cli._fork_cli_bron_patch_applied = True  # type: ignore[attr-defined]
