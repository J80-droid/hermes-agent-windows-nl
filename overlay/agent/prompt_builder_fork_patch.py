"""Expose legal prompt_builder helpers on Tier A ``agent.prompt_builder``."""
from __future__ import annotations


def apply_prompt_builder_fork_patch() -> None:
    import agent.prompt_builder as pb

    if getattr(pb, "_fork_prompt_builder_patch_applied", False):
        return

    from overlay.agent.prompt_builder_legal import (
        augment_ephemeral_for_legal_profile,
        build_legal_runtime_paths_block,
    )

    pb.build_legal_runtime_paths_block = build_legal_runtime_paths_block  # type: ignore[attr-defined]
    pb.augment_ephemeral_for_legal_profile = augment_ephemeral_for_legal_profile  # type: ignore[attr-defined]
    pb._fork_prompt_builder_patch_applied = True  # type: ignore[attr-defined]
