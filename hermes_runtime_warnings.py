"""Cosmetic runtime warning filters (startup, pytest, ingest)."""

from __future__ import annotations

import logging
import os
import warnings


def apply_runtime_warning_filters() -> None:
    """Call early in CLI/gateway entrypoints before heavy imports."""
    if os.environ.get("HERMES_NO_WARNING_FILTERS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return

    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message=r".*audioop.*",
    )
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module=r"discord\..*",
    )
    try:
        from scripts.rag_pipeline.rag_log_quiet import apply_torch_ingest_quiet

        apply_torch_ingest_quiet()
    except Exception:
        for name in ("torch", "transformers", "sentence_transformers"):
            logging.getLogger(name).setLevel(logging.ERROR)
