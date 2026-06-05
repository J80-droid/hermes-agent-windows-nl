"""Inject fork catalog guard symbols into hermes_cli.models (Tier A unchanged)."""
from __future__ import annotations


def apply_models_fork_patch() -> None:
    import hermes_cli.models as models_mod

    if getattr(models_mod, "_fork_catalog_patch_applied", False):
        return

    from overlay.hermes_cli.model_catalog_guard import (
        model_default_passes_startup_catalog_guard,
        model_matches_provider_catalog,
    )
    models_mod.model_matches_provider_catalog = model_matches_provider_catalog
    models_mod.model_default_passes_startup_catalog_guard = model_default_passes_startup_catalog_guard
    models_mod._fork_catalog_patch_applied = True
