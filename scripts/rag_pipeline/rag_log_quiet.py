"""Onderdruk bekende PyTorch/transformers-ruis tijdens RAG-ingest (geen functionele impact)."""

from __future__ import annotations

import logging
import os
import re
import warnings

from rag_institutional_defaults import DEFAULT_QUIET_TORCH, ENV_QUIET_TORCH

# Regels die op stderr verschijnen vóór/during embed-load (cosmetisch).
_TORCH_NOISE_RE = re.compile(
    r"KernelPreference|register_constant\(\) on Enum|torch\\utils\\_pytree",
    re.IGNORECASE,
)


def torch_ingest_quiet_enabled() -> bool:
    raw = (os.environ.get(ENV_QUIET_TORCH) or DEFAULT_QUIET_TORCH).strip().lower()
    return raw not in ("0", "false", "no", "off")


def apply_torch_ingest_quiet() -> None:
    if not torch_ingest_quiet_enabled():
        return
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    for name in ("torch", "transformers", "sentence_transformers", "lancedb"):
        logging.getLogger(name).setLevel(logging.ERROR)
    warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"torch\..*")
    warnings.filterwarnings(
        "ignore",
        message=r".*register_constant.*Enum.*",
    )
    warnings.filterwarnings(
        "ignore",
        message=r".*KernelPreference.*",
    )


def is_torch_ingest_noise_line(line: str) -> bool:
    """Filter voor console/log (PowerShell vangt torch stderr)."""
    if not torch_ingest_quiet_enabled():
        return False
    return bool(_TORCH_NOISE_RE.search(line))


apply_torch_ingest_quiet()
