"""Unit tests for overlay model catalog guard patch."""

from __future__ import annotations

import hermes_cli.models as models_mod
from overlay.hermes_cli.models_fork_patch import apply_models_fork_patch


def test_models_patch_injects_guard_symbols():
    apply_models_fork_patch()
    assert hasattr(models_mod, "model_matches_provider_catalog")
    assert hasattr(models_mod, "model_default_passes_startup_catalog_guard")
    assert getattr(models_mod, "_fork_catalog_patch_applied", False)


def test_models_patch_idempotent():
    apply_models_fork_patch()
    first_match = models_mod.model_matches_provider_catalog
    apply_models_fork_patch()
    assert models_mod.model_matches_provider_catalog is first_match
