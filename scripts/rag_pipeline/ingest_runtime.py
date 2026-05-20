"""Institutionele runtime: per-bron timeouts, live status, bounded work."""

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, TypeVar

from kb_schema import DB_PATH

T = TypeVar("T")

STATUS_BASENAME = "rag_ingest_live_status.json"
_run_started_at: str | None = None


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


def status_path() -> Path:
    override = (os.environ.get("HERMES_RAG_LIVE_STATUS") or "").strip()
    if override:
        return Path(os.path.expanduser(os.path.expandvars(override)))
    return Path(DB_PATH) / STATUS_BASENAME


@dataclass
class LiveStatus:
    phase: str
    current_index: int
    total: int
    relative_source: str
    step: str
    started_at: str
    updated_at: str
    pid: int
    extra: str = ""

    def write(self) -> None:
        p = status_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(self)
        p.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


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


def reset_live_status_clock() -> None:
    """Reset run-start voor live_status.json (aanroepen bij start index-fase)."""
    global _run_started_at
    _run_started_at = None


def write_live_status(
    *,
    phase: str,
    index: int,
    total: int,
    relative_source: str,
    step: str,
    extra: str = "",
) -> None:
    global _run_started_at
    now = datetime.now(timezone.utc).isoformat()
    if _run_started_at is None:
        _run_started_at = now
    LiveStatus(
        phase=phase,
        current_index=index,
        total=total,
        relative_source=relative_source,
        step=step,
        started_at=_run_started_at,
        updated_at=now,
        pid=os.getpid(),
        extra=extra,
    ).write()
