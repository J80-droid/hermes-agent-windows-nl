"""Institutionele runtime: per-bron timeouts, live status, bounded work."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Callable, TypeVar

from ingest_live_status import (
    STATUS_BASENAME,
    finalize_live_status,
    mark_ingest_started,
    reset_live_status_clock,
    status_path,
    write_live_status,
)

T = TypeVar("T")

__all__ = [
    "STATUS_BASENAME",
    "FileJobTimeout",
    "allow_parallel_convert",
    "file_timeout_sec",
    "finalize_live_status",
    "gc_every_n_files",
    "mark_ingest_started",
    "max_chunks_per_source",
    "reset_live_status_clock",
    "run_file_job",
    "status_path",
    "write_live_status",
]


def _env_float(name: str, default: float) -> float:
    raw = (os.environ.get(name) or str(default)).strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return default


def file_timeout_sec() -> float:
    """Max. seconden per bron (convert + chunk + embed). 0 = geen limiet."""
    return _env_float("HERMES_RAG_FILE_TIMEOUT_SEC", 1200.0)


def max_chunks_per_source() -> int:
    raw = (os.environ.get("HERMES_RAG_MAX_CHUNKS_PER_SOURCE") or "800").strip()
    try:
        v = int(raw)
    except ValueError:
        v = 800
    return max(0, v)


def gc_every_n_files() -> int:
    raw = (os.environ.get("HERMES_RAG_GC_EVERY") or "10").strip()
    try:
        v = int(raw)
    except ValueError:
        v = 10
    return max(0, v)


def allow_parallel_convert() -> bool:
    raw = (os.environ.get("HERMES_RAG_ALLOW_PARALLEL") or "0").strip().lower()
    return raw in ("1", "true", "yes", "on")


class FileJobTimeout(Exception):
    """Per-bron timeout (convert/OCR/embed)."""


def run_file_job(fn: Callable[[], T], *, timeout_sec: float | None = None) -> T:
    """Voer één bron-job uit met harde timeout (voorkomt vastlopen op stap 12/…)."""
    limit = file_timeout_sec() if timeout_sec is None else timeout_sec
    if limit <= 0:
        return fn()
    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(fn)
        try:
            return fut.result(timeout=limit)
        except FuturesTimeoutError as e:
            raise FileJobTimeout(f"timeout na {int(limit)}s") from e
