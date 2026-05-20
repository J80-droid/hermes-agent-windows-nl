"""Live voortgang per bron: gebruiker ziet of ingest loopt of vastzit."""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path

from ingest_runtime import write_live_status

_active: "FileActivityTracker | None" = None


def _env_float(name: str, default: float) -> float:
    raw = (os.environ.get(name) or str(default)).strip()
    try:
        return max(0.5, float(raw))
    except ValueError:
        return default


def live_tick_sec() -> float:
    """Interval voor postfix + [LIVE]-regel (seconden)."""
    return _env_float("HERMES_RAG_LIVE_TICK_SEC", 3.0)


def live_log_ticks_enabled() -> bool:
    raw = os.environ.get("HERMES_RAG_LIVE_LOG", "1")
    return str(raw).strip().lower() not in ("0", "false", "no", "off")


def set_active_tracker(tracker: "FileActivityTracker | None") -> None:
    global _active
    _active = tracker


def set_step(step: str) -> None:
    if _active is not None:
        _active.set_step(step)


class FileActivityTracker:
    """Achtergrond-heartbeat: postfix + [LIVE]-regels + live_status.json tijdens zware PDF's."""

    def __init__(self, pbar: object, *, interval: float | None = None, log_ticks: bool | None = None) -> None:
        self._pbar = pbar
        self._interval = live_tick_sec() if interval is None else interval
        self._log_ticks = live_log_ticks_enabled() if log_ticks is None else log_ticks
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._step = ""
        self._short = ""
        self._rel = ""
        self._idx = 0
        self._total = 0
        self._t0 = 0.0
        self._size_mb: float | None = None

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._heartbeat_loop, name="rag-live-progress", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval + 2.0)
            self._thread = None

    def begin_file(
        self,
        index: int,
        total: int,
        file_path: Path,
        relative_source: str,
    ) -> None:
        try:
            size_b = file_path.stat().st_size
            size_mb = round(size_b / (1024 * 1024), 1)
        except OSError:
            size_mb = None
        with self._lock:
            self._idx = index
            self._total = total
            self._short = file_path.name
            self._rel = relative_source
            self._t0 = time.monotonic()
            self._step = "start"
            self._size_mb = size_mb
        self._render(log_line=True)

    def set_step(self, step: str) -> None:
        with self._lock:
            self._step = step
        self._render(log_line=False)

    def end_file(self) -> None:
        with self._lock:
            self._t0 = 0.0
            self._step = ""

    def _heartbeat_loop(self) -> None:
        while not self._stop.wait(self._interval):
            self._render(log_line=True)

    def _snapshot(self) -> tuple[int, int, float, str, str, str, float | None]:
        with self._lock:
            if self._t0 <= 0:
                return 0, 0, 0.0, "", "", "", None
            elapsed = time.monotonic() - self._t0
            return (
                self._idx,
                self._total,
                elapsed,
                self._step,
                self._short,
                self._rel,
                self._size_mb,
            )

    def _render(self, *, log_line: bool) -> None:
        idx, total, elapsed, step, short, rel, size_mb = self._snapshot()
        if idx <= 0 or not step:
            return

        from ingest_ui import format_elapsed, set_progress_activity, write_live_tick

        set_progress_activity(
            self._pbar,
            elapsed_sec=elapsed,
            step=step,
            filename=short,
            index=idx,
            total=total,
            size_mb=size_mb,
        )
        write_live_status(
            phase="index",
            index=idx,
            total=total,
            relative_source=rel,
            step=step,
            extra=f"{format_elapsed(elapsed)} | {step} | {short}",
        )
        if log_line:
            write_live_tick(
                self._pbar,
                index=idx,
                total=total,
                elapsed_sec=elapsed,
                step=step,
                filename=short,
                size_mb=size_mb,
            )
