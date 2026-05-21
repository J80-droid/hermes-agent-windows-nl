"""Institutioneel live-statusbestand per LanceDB-domein (running / completed / failed + stale-detectie)."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from kb_schema import DB_PATH
from rag_institutional_defaults import DEFAULT_LIVE_STALE_SEC, ENV_LIVE_STALE_SEC

STATUS_BASENAME = "rag_ingest_live_status.json"
SUMMARY_BASENAME = "rag_ingest_run_summary.json"

RUN_RUNNING = "running"
RUN_COMPLETED = "completed"
RUN_FAILED = "failed"

_run_started_at: str | None = None


class LiveDisplayState(str, Enum):
    MISSING = "missing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STALE = "stale"  # verouderd midden in 'running', proces weg
    STALE_RECONCILED = "stale_reconciled"


@dataclass
class LiveStatusPayload:
    run_state: str
    phase: str
    current_index: int
    total: int
    relative_source: str
    step: str
    started_at: str
    updated_at: str
    pid: int
    domain: str = ""
    extra: str = ""
    completed_at: str | None = None
    exit_code: int | None = None
    message: str = ""
    schema_version: int = 1

    def write(self, path: Path | None = None) -> Path:
        dest = path or status_path()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return dest


@dataclass
class LiveStatusInterpretation:
    display_state: LiveDisplayState
    human: str
    live: dict[str, Any] | None = None
    reconciled: bool = False
    pid_alive: bool = False


def status_path(db_path: str | Path | None = None) -> Path:
    override = (os.environ.get("HERMES_RAG_LIVE_STATUS") or "").strip()
    if override:
        return Path(os.path.expanduser(os.path.expandvars(override)))
    base = Path(db_path) if db_path else Path(DB_PATH)
    return base / STATUS_BASENAME


def summary_path_for_db(db_path: str | Path) -> Path:
    return Path(db_path) / SUMMARY_BASENAME


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def stale_after_sec() -> float:
    raw = (os.environ.get(ENV_LIVE_STALE_SEC) or str(DEFAULT_LIVE_STALE_SEC)).strip()
    try:
        return max(30.0, float(raw))
    except ValueError:
        return 120.0


def is_process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


def reset_live_status_clock() -> None:
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
    run_state: str = RUN_RUNNING,
) -> None:
    global _run_started_at
    now = datetime.now(timezone.utc).isoformat()
    if _run_started_at is None:
        _run_started_at = now
    LiveStatusPayload(
        run_state=run_state,
        phase=phase,
        current_index=index,
        total=total,
        relative_source=relative_source,
        step=step,
        started_at=_run_started_at,
        updated_at=now,
        pid=os.getpid(),
        domain=(os.environ.get("RAG_DOMAIN") or "").strip(),
        extra=extra,
    ).write()


def mark_ingest_started(*, total: int) -> None:
    """Schrijf expliciet 'running' bij start index-fase (geen verouderde 40/40 van vorige run)."""
    reset_live_status_clock()
    write_live_status(
        phase="index",
        index=0,
        total=total,
        relative_source="",
        step="Gestart",
        extra="index-fase gestart",
        run_state=RUN_RUNNING,
    )


def finalize_live_status(
    *,
    run_state: str,
    exit_code: int = 0,
    message: str = "",
    phase: str = "done",
    current_index: int | None = None,
    total: int | None = None,
) -> Path:
    """Altijd aanroepen in ingest-finally: sluit live_status netjes af."""
    now = datetime.now(timezone.utc).isoformat()
    path = status_path()
    prev: dict[str, Any] = {}
    if path.is_file():
        try:
            prev = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            prev = {}

    idx = current_index if current_index is not None else int(prev.get("current_index") or 0)
    tot = total if total is not None else int(prev.get("total") or 0)
    started = prev.get("started_at") or _run_started_at or now

    payload = LiveStatusPayload(
        run_state=run_state,
        phase=phase,
        current_index=idx,
        total=tot,
        relative_source=str(prev.get("relative_source") or ""),
        step="Afgerond" if run_state == RUN_COMPLETED else str(prev.get("step") or "Gestopt"),
        started_at=str(started),
        updated_at=now,
        pid=os.getpid(),
        domain=(os.environ.get("RAG_DOMAIN") or prev.get("domain") or "").strip(),
        extra=str(prev.get("extra") or ""),
        completed_at=now if run_state in (RUN_COMPLETED, RUN_FAILED) else None,
        exit_code=exit_code,
        message=message,
    )
    return payload.write(path)


def read_live_status(db_path: str | Path | None = None) -> dict[str, Any] | None:
    path = status_path(db_path)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def read_summary(db_path: str | Path) -> dict[str, Any] | None:
    path = summary_path_for_db(db_path)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _legacy_run_state(live: dict[str, Any]) -> str:
    return str(live.get("run_state") or RUN_RUNNING).strip().lower()


def interpret_live_status(
    db_path: str | Path,
    *,
    summary: dict[str, Any] | None = None,
) -> LiveStatusInterpretation:
    live = read_live_status(db_path)
    if summary is None:
        summary = read_summary(db_path)

    if live is None:
        if summary:
            return LiveStatusInterpretation(
                display_state=LiveDisplayState.COMPLETED,
                human="Geen live_status; wel eindrapport (ingest eerder afgerond).",
                live=None,
            )
        return LiveStatusInterpretation(
            display_state=LiveDisplayState.MISSING,
            human="Geen live_status (nog geen index-run of bestand verwijderd).",
        )

    state = _legacy_run_state(live)
    pid = int(live.get("pid") or 0)
    alive = is_process_alive(pid)
    updated = _parse_iso(str(live.get("updated_at") or ""))
    summary_at = _parse_iso(str((summary or {}).get("generated_at") or ""))

    if state == RUN_COMPLETED:
        return LiveStatusInterpretation(
            display_state=LiveDisplayState.COMPLETED,
            human=_format_completed_line(live),
            live=live,
            pid_alive=alive,
        )
    if state == RUN_FAILED:
        return LiveStatusInterpretation(
            display_state=LiveDisplayState.FAILED,
            human=f"Ingest mislukt: {live.get('message') or 'onbekend'}",
            live=live,
            pid_alive=alive,
        )

    if alive:
        return LiveStatusInterpretation(
            display_state=LiveDisplayState.RUNNING,
            human=_format_running_line(live),
            live=live,
            pid_alive=True,
        )

    # Proces weg, run_state nog running (legacy of crash)
    if summary and summary_at and updated and summary_at >= updated:
        return LiveStatusInterpretation(
            display_state=LiveDisplayState.STALE,
            human=(
                "Live status verouderd (proces weg; eindrapport is nieuwer). "
                "Reconciliatie aanbevolen."
            ),
            live=live,
            pid_alive=False,
        )

    age_sec = (
        (datetime.now(timezone.utc) - updated).total_seconds()
        if updated
        else stale_after_sec() + 1
    )
    if age_sec > stale_after_sec():
        return LiveStatusInterpretation(
            display_state=LiveDisplayState.STALE,
            human=(
                f"Live status verouderd ({int(age_sec)}s geleden, pid {pid} niet actief). "
                "Mogelijk crash of afgebroken run."
            ),
            live=live,
            pid_alive=False,
        )

    return LiveStatusInterpretation(
        display_state=LiveDisplayState.STALE,
        human=f"Pid {pid} niet actief; recente update — mogelijk net gestopt.",
        live=live,
        pid_alive=False,
    )


def reconcile_live_status_from_summary(db_path: str | Path) -> bool:
    """Zet verouderde 'running' live_status op completed als eindrapport nieuwer is."""
    db_path = Path(db_path)
    live = read_live_status(db_path)
    summary = read_summary(db_path)
    if not live or not summary:
        return False

    interp = interpret_live_status(db_path, summary=summary)
    if interp.display_state not in (LiveDisplayState.STALE, LiveDisplayState.RUNNING):
        if _legacy_run_state(live) == RUN_COMPLETED:
            return False
        # running but pid alive — don't reconcile
        if interp.display_state == LiveDisplayState.RUNNING:
            return False

    if _legacy_run_state(live) == RUN_COMPLETED:
        return False

    summary_at = str(summary.get("generated_at") or "")
    now = datetime.now(timezone.utc).isoformat()
    payload = LiveStatusPayload(
        run_state=RUN_COMPLETED,
        phase="done",
        current_index=int(summary.get("total_sources_in_index_state") or live.get("total") or 0),
        total=int(summary.get("scan_total_files") or live.get("total") or 0),
        relative_source="",
        step="Afgerond",
        started_at=str(live.get("started_at") or summary_at or now),
        updated_at=summary_at or now,
        pid=0,
        domain=str(summary.get("domain") or live.get("domain") or ""),
        extra="live_status gesynchroniseerd met eindrapport",
        completed_at=summary_at or now,
        exit_code=0,
        message=(
            f"Gesynchroniseerd met eindrapport "
            f"({summary.get('total_sources_in_index_state', '?')} bronnen in index)"
        ),
    )
    payload.write(status_path(db_path))
    return True


def _format_running_line(live: dict[str, Any]) -> str:
    return (
        f"Bezig: {live.get('current_index')}/{live.get('total')} | "
        f"{live.get('step')} | {live.get('relative_source') or '-'}"
    )


def _format_completed_line(live: dict[str, Any]) -> str:
    msg = live.get("message") or ""
    at = live.get("completed_at") or live.get("updated_at") or "?"
    base = f"Afgerond ({at})"
    return f"{base} — {msg}" if msg else base


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="RAG live_status — lezen / reconciliëren")
    parser.add_argument("--db-path", required=True, help="Pad naar lancedb/<domein>")
    parser.add_argument("--reconcile", action="store_true", help="Verouderde live_status fixen")
    parser.add_argument("--json", action="store_true", help="Machine-leesbare output")
    args = parser.parse_args(argv)

    db = Path(args.db_path)
    reconciled = reconcile_live_status_from_summary(db) if args.reconcile else False
    interp = interpret_live_status(db)

    if args.json:
        out = {
            "display_state": interp.display_state.value,
            "human": interp.human,
            "reconciled": reconciled,
            "pid_alive": interp.pid_alive,
            "live": interp.live,
        }
        print(json.dumps(out, ensure_ascii=False))
    else:
        tag = "[OK]" if interp.display_state == LiveDisplayState.COMPLETED else "[INFO]"
        if interp.display_state in (LiveDisplayState.STALE, LiveDisplayState.FAILED):
            tag = "[WARN]"
        if reconciled:
            print("[OK] live_status gesynchroniseerd met eindrapport")
        print(f"{tag} {interp.human}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
