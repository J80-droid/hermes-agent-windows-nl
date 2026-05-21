"""
Institutionele RAG-defaults (env) — enige bron van waarheid voor aanbevolen waarden.

Wordt toegepast bij start van ingest (bat/ps1/run_domains_ingest) zodat nachtruns,
taakbalk en CLI hetzelfde gedrag hebben zonder handmatig set-commando's.
"""

from __future__ import annotations

import os
from typing import Final

# --- Aanbevolen defaults (documenteer in docs/RAG_INSTITUTIONAL_ENV.md) ---
DEFAULT_LIVE_STALE_SEC: Final[int] = 120
DEFAULT_QUIET_TORCH: Final[str] = "1"
DEFAULT_PERF_PROFILE: Final[str] = "safe"
DEFAULT_NONINTERACTIVE: Final[str] = "1"  # alleen nacht/taakbalk-launchers

ENV_LIVE_STALE_SEC = "HERMES_RAG_LIVE_STALE_SEC"
ENV_QUIET_TORCH = "HERMES_RAG_QUIET_TORCH"
ENV_PERF_PROFILE = "HERMES_RAG_PERF_PROFILE"
ENV_NONINTERACTIVE = "HERMES_NONINTERACTIVE"


def _setdefault(name: str, value: str) -> None:
    if not (os.environ.get(name) or "").strip():
        os.environ[name] = value


def apply_institutional_env(
    *,
    noninteractive: bool = False,
    quiet_torch: bool = True,
) -> dict[str, str]:
    """
    Zet ontbrekende env-vars op institutionele defaults (bestaande waarden blijven).

    Returns dict met effectieve waarden (voor logging).
    """
    _setdefault(ENV_LIVE_STALE_SEC, str(DEFAULT_LIVE_STALE_SEC))
    if quiet_torch:
        _setdefault(ENV_QUIET_TORCH, DEFAULT_QUIET_TORCH)
        _setdefault("TRANSFORMERS_VERBOSITY", "error")
        _setdefault("TOKENIZERS_PARALLELISM", "false")
    _setdefault(ENV_PERF_PROFILE, DEFAULT_PERF_PROFILE)
    if noninteractive:
        _setdefault(ENV_NONINTERACTIVE, DEFAULT_NONINTERACTIVE)
    return institutional_env_snapshot()


def institutional_env_snapshot() -> dict[str, str]:
    return {
        ENV_LIVE_STALE_SEC: os.environ.get(ENV_LIVE_STALE_SEC, str(DEFAULT_LIVE_STALE_SEC)),
        ENV_QUIET_TORCH: os.environ.get(ENV_QUIET_TORCH, DEFAULT_QUIET_TORCH),
        ENV_PERF_PROFILE: os.environ.get(ENV_PERF_PROFILE, DEFAULT_PERF_PROFILE),
        ENV_NONINTERACTIVE: os.environ.get(ENV_NONINTERACTIVE, ""),
    }
