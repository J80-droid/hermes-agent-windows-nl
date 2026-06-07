"""Fork setup helpers (model coherence guard + profile .env reads)."""
from __future__ import annotations

from typing import Optional


def _model_section_is_coherent(config: dict) -> bool:
    """False when auth.json and config model.provider disagree."""
    try:
        from hermes_cli.model_runtime_config import detect_model_provider_incoherence

        return len(detect_model_provider_incoherence(config)) == 0
    except Exception:
        return False


def apply_setup_fork_patch() -> None:
    import hermes_cli.setup as setup_mod

    if getattr(setup_mod, "_fork_setup_patch_applied", False):
        return

    from hermes_cli.config import get_env_value

    setup_mod.get_env_value = get_env_value  # type: ignore[attr-defined]
    setup_mod._model_section_is_coherent = _model_section_is_coherent  # type: ignore[attr-defined]

    _orig_skip = setup_mod._skip_configured_section

    def _skip_configured_section(config: dict, section_key: str, label: str) -> bool:
        summary = setup_mod._get_section_config_summary(config, section_key)
        if not summary:
            return False
        if section_key == "model" and not _model_section_is_coherent(config):
            setup_mod.print_warning(
                f"  {label}: credentials present but auth.json and config model.provider "
                "disagree — reconfigure required."
            )
            try:
                from hermes_cli.model_runtime_config import detect_model_provider_incoherence

                for ci in detect_model_provider_incoherence(config):
                    setup_mod.print_warning(f"    {ci.message}")
            except Exception:
                pass
            setup_mod.print_info("  Run 'hermes doctor --fix' after setup, or reconfigure now.")
            return False
        return _orig_skip(config, section_key, label)

    setup_mod._skip_configured_section = _skip_configured_section  # type: ignore[assignment]
    setup_mod._fork_setup_patch_applied = True  # type: ignore[attr-defined]
