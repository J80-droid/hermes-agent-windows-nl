"""Bundled fork plugin: legal brief, profile helpers (via overlay bootstrap)."""
from __future__ import annotations

from typing import Any


def register(ctx: Any) -> None:
    try:
        from overlay.bootstrap import install

        install()
    except Exception:
        pass

    try:
        from hermes_cli.legal_architecture_brief import build_legal_architecture_brief

        def _legal_architecture_handler(**_kwargs: Any) -> str:
            return build_legal_architecture_brief()

        ctx.register_command(
            "legal-architectuur",
            _legal_architecture_handler,
            description="Fork legal domain architecture brief (deterministic).",
        )
    except ImportError:
        pass
