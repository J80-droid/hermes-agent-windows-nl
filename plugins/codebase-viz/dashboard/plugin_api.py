"""Codebase Viz dashboard plugin — backend API routes.

Mounted at ``/api/plugins/codebase-viz/`` by the dashboard plugin system.
All data routes call ``_ensure_started()`` (lazy watchdog + WS flush loop).

Error policy: HTTP 200 with ``error`` / ``fallback: true`` for missing repo
or scan failures; WebSocket rejects invalid ``?token=`` with close 4001.
"""

from __future__ import annotations

import ast
import asyncio
import hashlib
import hmac
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import importlib.util

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

_s3_spec = importlib.util.spec_from_file_location(
    "plugin_api_sprint3",
    Path(__file__).resolve().parent / "plugin_api_sprint3.py",
)
_s3 = importlib.util.module_from_spec(_s3_spec)
assert _s3_spec.loader is not None
_s3_spec.loader.exec_module(_s3)

GIT_CACHE_TTL = float(os.environ.get("CODEBASE_VIZ_GIT_TTL", "300"))

log = logging.getLogger(__name__)
router = APIRouter()

PLUGIN_VERSION = "2.5.0"
CODEBASE_VIZ_MAX_MEMORY_MB = float(os.environ.get("CODEBASE_VIZ_MAX_MEMORY_MB", "500"))
DEFAULT_SKIP = (
    ".git,node_modules,venv,.venv,.venv.disabled*,__pycache__,dist,build,.next,.cache,"
    ".tox,.eggs,.mypy_cache,output,.hermes,backups"
)
# Gedeelde skip-lijst voor pygount, repo-handtekening en import-analyse.
# `backups/` en `.venv.disabled*` voorkomen timeouts op grote lokale mappen.
_SCAN_SKIP_DIR_NAMES = frozenset({
    ".git", "node_modules", "venv", ".venv", "__pycache__",
    "dist", "build", ".next", ".cache", ".tox", ".eggs",
    ".mypy_cache", "output", ".hermes", "backups",
})


def _scan_skip_dir_part(part: str) -> bool:
    return part in _SCAN_SKIP_DIR_NAMES or part.startswith(".venv.disabled")


def _path_has_skipped_dir(path: Path) -> bool:
    return any(_scan_skip_dir_part(part) for part in path.parts)


try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    FileSystemEventHandler = object  # type: ignore[misc, assignment]
    Observer = None  # type: ignore[misc, assignment]


def _resolve_repo_path() -> Path | None:
    env_path = os.environ.get("CODEBASE_VIZ_REPO", "").strip()
    if env_path:
        p = Path(env_path).resolve()
        return p if p.is_dir() else None

    # Bundled plugin: default naar hermes-agent repo-root
    bundled_root = Path(__file__).resolve().parents[3]
    if (bundled_root / ".git").is_dir():
        return bundled_root

    cwd = Path.cwd().resolve()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".git").is_dir():
            return parent
    return None


INSTITUTIONAL_PYGOUNT_TIMEOUT_SEC = 600
INSTITUTIONAL_PYGOUNT_CACHE_TTL_SEC = 3600.0


def _parse_pygount_timeout() -> int:
    default = str(INSTITUTIONAL_PYGOUNT_TIMEOUT_SEC)
    raw = os.environ.get("CODEBASE_VIZ_PYGOUNT_TIMEOUT", default).strip()
    try:
        value = int(raw)
    except ValueError:
        log.warning(
            "invalid CODEBASE_VIZ_PYGOUNT_TIMEOUT=%r, using %s",
            raw,
            INSTITUTIONAL_PYGOUNT_TIMEOUT_SEC,
        )
        return INSTITUTIONAL_PYGOUNT_TIMEOUT_SEC
    if value < 1:
        log.warning(
            "CODEBASE_VIZ_PYGOUNT_TIMEOUT=%s too low, using %s",
            value,
            INSTITUTIONAL_PYGOUNT_TIMEOUT_SEC,
        )
        return INSTITUTIONAL_PYGOUNT_TIMEOUT_SEC
    return value


REPO_PATH = _resolve_repo_path()
CODEBASE_VIZ_TTL = float(os.environ.get("CODEBASE_VIZ_TTL", "300"))
PYGOUNT_CACHE_TTL = float(
    os.environ.get("CODEBASE_VIZ_PYGOUNT_TTL", str(int(INSTITUTIONAL_PYGOUNT_CACHE_TTL_SEC))),
)
CODEBASE_VIZ_DEBOUNCE = float(os.environ.get("CODEBASE_VIZ_DEBOUNCE", "2.0"))
PYGOUNT_TIMEOUT = _parse_pygount_timeout()


def _parse_scan_mode() -> str:
    raw = os.environ.get("CODEBASE_VIZ_SCAN_MODE", "incremental").strip().lower()
    if raw in {"incremental", "full"}:
        return raw
    log.warning("invalid CODEBASE_VIZ_SCAN_MODE=%r, using incremental", raw)
    return "incremental"


CODEBASE_VIZ_SCAN_MODE = _parse_scan_mode()

_cache_lock = asyncio.Lock()
_cache: dict[str, tuple[float, object]] = {}
_inflight: dict[str, asyncio.Task] = {}
_scan_state: dict[str, Any] = {"phase": "idle", "detail": "", "started_at": None}

_SCAN_LABELS: dict[str, str] = {
    "pygount": "LOC tellen (pygount)",
    "import_edges": "Python-imports analyseren",
    "structure": "Directorystructuur opbouwen",
    "summary": "Metrics samenstellen",
    "dependencies": "Dependency-graaf bouwen",
    "doctor": "hermes doctor uitvoeren",
    "churn": "Git churn",
    "age-map": "Git age map",
    "complexity": "Complexity (radon)",
    "todos": "TODO/FIXME scan",
    "blame": "Git blame",
    "coverage": "Coverage inschatten",
    "history": "Git history",
    "timeline": "Timeline",
}

_initialized = False
_lazy_lock = asyncio.Lock()
_event_queue: asyncio.Queue = asyncio.Queue()
_observer: Any = None
_ws_clients: set[WebSocket] = set()
_refresh_task: asyncio.Task | None = None
_refresh_status: dict[str, Any] = {
    "running": False,
    "reason": "",
    "started_at": None,
    "last_completed_at": None,
    "last_error": "",
    "last_event_count": 0,
}
_snapshot_lock = asyncio.Lock()
_pending_changed_paths: set[str] = set()
_RECENT_EVENT_LIMIT = 200
_recent_events: list[dict[str, Any]] = []
_research_dir = Path(__file__).resolve().parents[3] / "output" / "research"
_state_paths = {
    "snapshot": (
        Path(os.environ.get("CODEBASE_VIZ_SNAPSHOT_PATH", "")).resolve()
        if os.environ.get("CODEBASE_VIZ_SNAPSHOT_PATH")
        else _research_dir / "codebase_viz_snapshot_state.json"
    ),
    "pygount_disk": (
        Path(os.environ.get("CODEBASE_VIZ_PYGOUNT_CACHE_PATH", "")).resolve()
        if os.environ.get("CODEBASE_VIZ_PYGOUNT_CACHE_PATH")
        else _research_dir / "codebase_viz_pygount_cache.json"
    ),
}
_snapshot_state: dict[str, Any] = {
    "snapshot_version": 1,
    "scan_mode": CODEBASE_VIZ_SCAN_MODE,
    "repo_signature": "",
    "last_checkpoint": "",
    "last_full_scan_at": None,
    "data_hashes": {},
    "datasets": {},
}


async def _cached(key: str, ttl: float = 60.0) -> object | None:
    async with _cache_lock:
        entry = _cache.get(key)
        if entry and time.monotonic() - entry[0] < ttl:
            return entry[1]
    return None


async def _cached_any(key: str) -> object | None:
    async with _cache_lock:
        entry = _cache.get(key)
        if entry:
            return entry[1]
    return None


async def _set_cache(key: str, data: object) -> None:
    async with _cache_lock:
        _cache[key] = (time.monotonic(), data)
    await _mark_dataset_updated(key, data)


def _snapshot_file() -> Path:
    return _state_paths["snapshot"]


def _pygount_disk_cache_file() -> Path:
    return _state_paths["pygount_disk"]


def _pygount_disk_cache_enabled() -> bool:
    return os.environ.get("CODEBASE_VIZ_PYGOUNT_DISK_CACHE", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _read_pygount_disk_cache(
    *,
    allow_stale: bool = False,
    ignore_revision: bool = False,
) -> dict[str, Any] | None:
    """Lees gepersisteerde pygount-bundle (overleeft dashboard-herstart)."""
    if not _pygount_disk_cache_enabled() or REPO_PATH is None:
        return None
    path = _pygount_disk_cache_file()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("codebase_viz_pygount_cache_load_failed: %s", exc)
        return None
    if not isinstance(data, dict):
        return None
    try:
        cached_repo = Path(str(data.get("repo_path", ""))).resolve()
        current_repo = REPO_PATH.resolve()
    except (OSError, ValueError):
        return None
    if cached_repo != current_repo:
        return None
    if not ignore_revision:
        stored_revision = str(data.get("repo_revision") or data.get("repo_signature") or "")
        if not _disk_cache_revision_matches(stored_revision, REPO_PATH):
            return None
    saved_at = data.get("saved_at")
    if not allow_stale and isinstance(saved_at, (int, float)):
        age = time.time() - float(saved_at)
        if age > PYGOUNT_CACHE_TTL:
            return None
    bundle = data.get("bundle")
    if not isinstance(bundle, dict) or bundle.get("error"):
        return None
    if not bundle.get("file_rows"):
        return None
    return dict(bundle)


def _write_pygount_disk_cache(bundle: dict[str, Any]) -> None:
    if not _pygount_disk_cache_enabled() or REPO_PATH is None or bundle.get("error"):
        return
    if not bundle.get("file_rows"):
        return
    path = _pygount_disk_cache_file()
    tmp_path: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        revision = _repo_cache_revision(REPO_PATH)
        payload = {
            "version": 1,
            "repo_path": str(REPO_PATH),
            "repo_revision": revision,
            "repo_signature": revision,
            "saved_at": int(time.time()),
            "bundle": bundle,
        }
        content = json.dumps(payload, ensure_ascii=False)
        tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(path)
    except Exception as exc:
        log.warning("codebase_viz_pygount_cache_persist_failed: %s", exc)
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass


async def _hydrate_pygount_from_disk() -> bool:
    """Vul geheugen-cache vanaf schijf zodat startup geen volledige pygount hoeft."""
    bundle = await asyncio.to_thread(_read_pygount_disk_cache, allow_stale=False)
    stale_reason: str | None = None
    if bundle is None:
        bundle = await asyncio.to_thread(
            _read_pygount_disk_cache,
            allow_stale=True,
            ignore_revision=True,
        )
        if bundle is None:
            return False
        bundle = dict(bundle)
        bundle.setdefault("warning", "disk_cache_revision_stale")
        bundle["fallback"] = True
        bundle["stale"] = True
        stale_reason = "revision_mismatch"
    async with _cache_lock:
        _cache["pygount"] = (time.monotonic(), bundle)
    signature = _repo_cache_revision(REPO_PATH)
    async with _snapshot_lock:
        _snapshot_state["repo_signature"] = signature
    await _mark_dataset_updated("pygount", bundle)
    log.info(
        "codebase_viz_pygount_disk_hydrated",
        extra={
            "files": len(bundle.get("file_rows") or []),
            "stale_reason": stale_reason,
        },
    )
    return True


def _safe_repo_file_iter(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if _path_has_skipped_dir(path):
            continue
        yield path


def _git_head_revision(repo: Path) -> str | None:
    """Huidige git commit (snel); None als geen git repo of git faalt."""
    if not (repo / ".git").is_dir():
        return None
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    rev = proc.stdout.strip()
    return rev or None


def _compute_repo_signature(repo: Path | None) -> str:
    if repo is None or not repo.is_dir():
        return ""
    digest = hashlib.sha1()
    paths = sorted(
        _safe_repo_file_iter(repo),
        key=lambda p: str(p.relative_to(repo)).replace("\\", "/"),
    )
    for path in paths:
        rel = str(path.relative_to(repo)).replace("\\", "/")
        try:
            st = path.stat()
        except OSError:
            continue
        digest.update(rel.encode("utf-8", errors="ignore"))
        digest.update(str(st.st_size).encode("ascii", errors="ignore"))
    return digest.hexdigest()


def _repo_cache_revision(repo: Path) -> str:
    """Snelle revisie voor disk-cache (git HEAD); fallback: volledige bestands-handtekening."""
    git_rev = _git_head_revision(repo)
    if git_rev:
        return git_rev
    return _compute_repo_signature(repo)


def _disk_cache_revision_matches(stored: str, repo: Path) -> bool:
    """Vergelijk opgeslagen revisie met huidige repo (git HEAD of legacy handtekening)."""
    if not stored:
        return False
    if stored == _repo_cache_revision(repo):
        return True
    # Legacy caches: volledige bestands-handtekening i.p.v. git HEAD
    return stored == _compute_repo_signature(repo)


def _disk_cache_status() -> dict[str, Any]:
    """Diagnose voor /health — waarom hydrate wel/niet slaagt."""
    path = _pygount_disk_cache_file()
    out: dict[str, Any] = {
        "enabled": _pygount_disk_cache_enabled(),
        "path": str(path),
        "exists": path.is_file(),
        "revision_matches": False,
        "current_revision": _repo_cache_revision(REPO_PATH) if REPO_PATH else None,
        "stored_revision": None,
    }
    if not path.is_file() or REPO_PATH is None:
        return out
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        out["load_error"] = str(exc)[:120]
        return out
    if isinstance(data, dict):
        out["stored_revision"] = data.get("repo_revision") or data.get("repo_signature")
        stored = str(out["stored_revision"] or "")
        out["revision_matches"] = _disk_cache_revision_matches(stored, REPO_PATH)
    return out


async def _load_snapshot_state() -> None:
    path = _snapshot_file()
    if not path.is_file():
        return
    try:
        raw = await asyncio.to_thread(path.read_text, encoding="utf-8")
        data = json.loads(raw)
    except Exception as exc:
        log.warning("codebase_viz_snapshot_load_failed: %s", exc)
        return
    if not isinstance(data, dict):
        return
    async with _snapshot_lock:
        _snapshot_state.update(data)
        _snapshot_state["scan_mode"] = CODEBASE_VIZ_SCAN_MODE


async def _persist_snapshot_state() -> None:
    path = _snapshot_file()
    try:
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        async with _snapshot_lock:
            payload = dict(_snapshot_state)
            payload["scan_mode"] = CODEBASE_VIZ_SCAN_MODE
        blob = json.dumps(payload, ensure_ascii=False, indent=2)
        await asyncio.to_thread(path.write_text, blob, encoding="utf-8")
    except Exception as exc:
        log.warning("codebase_viz_snapshot_persist_failed: %s", exc)


def _stable_data_hash(data: object) -> str:
    try:
        blob = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    except TypeError:
        blob = repr(data)
    return hashlib.sha1(blob.encode("utf-8", errors="ignore")).hexdigest()


async def _mark_dataset_updated(key: str, data: object | None = None) -> None:
    if key not in {
        "pygount", "summary", "structure", "dependencies", "import_edges",
    }:
        return
    now = int(time.time())
    async with _snapshot_lock:
        datasets = _snapshot_state.setdefault("datasets", {})
        ds = datasets.setdefault(key, {})
        ds["updated_at"] = now
        ds["has_data"] = True
        if data is not None:
            data_hashes = _snapshot_state.setdefault("data_hashes", {})
            data_hashes[key] = _stable_data_hash(data)
        if key == "pygount":
            _snapshot_state["last_full_scan_at"] = now
    await _persist_snapshot_state()


def _memory_status() -> dict[str, Any]:
    """RSS vs CODEBASE_VIZ_MAX_MEMORY_MB (default 500). Requires optional psutil."""
    max_mb = CODEBASE_VIZ_MAX_MEMORY_MB
    try:
        import psutil

        rss_mb = psutil.Process().memory_info().rss / (1024 * 1024)
        pressure = rss_mb > max_mb
        if pressure:
            log.warning(
                "codebase_viz_memory_high",
                extra={"rss_mb": round(rss_mb, 1), "max_mb": max_mb},
            )
        return {
            "rss_mb": round(rss_mb, 1),
            "max_mb": max_mb,
            "pressure": pressure,
            "psutil_available": True,
        }
    except ImportError:
        return {
            "rss_mb": None,
            "max_mb": max_mb,
            "pressure": False,
            "psutil_available": False,
        }
    except Exception as exc:
        log.debug("codebase_viz_psutil_unavailable: %s", exc)
        return {
            "rss_mb": None,
            "max_mb": max_mb,
            "pressure": False,
            "psutil_available": False,
            "error": str(exc)[:120],
        }


def _memory_ok() -> bool:
    return not _memory_status().get("pressure", False)


def _with_memory_pressure_flag(value: object) -> object:
    if isinstance(value, dict):
        out = dict(value)
        out["memory_pressure"] = True
        return out
    return value


async def _run_factory_and_store(key: str, factory) -> object:
    try:
        result = await factory()
    except Exception:
        log.exception("codebase_viz_compute_failed", extra={"cache_key": key})
        raise
    async with _cache_lock:
        _cache[key] = (time.monotonic(), result)
        _inflight.pop(key, None)
    await _mark_dataset_updated(key, result)
    return result


# Endpoints die alleen een reeds geladen pygount-bundle afleiden (geen subprocess).
_LIGHTWEIGHT_FROM_PYGOUNT_KEYS = frozenset({"structure", "summary"})


async def _get_or_compute(key: str, ttl: float, factory):
    """Cache-aside + singleflight; factory runs outside lock (safe for nested pygount)."""
    cached = await _cached(key, ttl)
    if cached is not None:
        return cached

    if not _memory_ok():
        async with _cache_lock:
            entry = _cache.get(key)
            if entry is not None:
                log.warning("codebase_viz_stale_cache", extra={"cache_key": key})
                return _with_memory_pressure_flag(entry[1])
            pygount_ready = "pygount" in _cache
        if not (key in _LIGHTWEIGHT_FROM_PYGOUNT_KEYS and pygount_ready):
            raise RuntimeError("memory_pressure")

    async with _cache_lock:
        entry = _cache.get(key)
        if entry and time.monotonic() - entry[0] < ttl:
            return entry[1]
        task = _inflight.get(key)
        if task is None:
            task = asyncio.create_task(_run_factory_and_store(key, factory))
            _inflight[key] = task

    return await task


def _empty_tree() -> dict[str, Any]:
    return {"name": "unknown", "path": "", "type": "dir", "loc": 0, "children": []}


def _empty_summary() -> dict[str, Any]:
    return {"total_files": 0, "total_code": 0, "languages": {}}


async def _api_error_payload(exc: Exception, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error": str(exc),
        "fallback": True,
        "repo_path": str(REPO_PATH) if REPO_PATH else None,
    }
    payload.update(extra)
    return payload


def _repo_scan_label() -> str:
    if REPO_PATH is None:
        return ""
    parts = REPO_PATH.parts
    if len(parts) >= 2:
        return "/".join(parts[-2:])
    return REPO_PATH.name or str(REPO_PATH)


def _attach_repo_meta(payload: dict[str, Any]) -> dict[str, Any]:
    """Zorg dat fout-/fallback-responses altijd scan-doel tonen in de UI."""
    if REPO_PATH is not None:
        payload.setdefault("repo_path", str(REPO_PATH))
        label = _repo_scan_label()
        if label:
            payload.setdefault("repo_label", label)
    return payload


async def _dataset_updated_at(key: str) -> int | None:
    async with _snapshot_lock:
        datasets = _snapshot_state.get("datasets", {})
        ds = datasets.get(key, {})
        value = ds.get("updated_at")
        return int(value) if isinstance(value, (int, float)) else None


async def _with_swr_meta(payload: dict[str, Any], *, cache_key: str, served_from_cache: bool) -> dict[str, Any]:
    out = dict(payload)
    updated_at = await _dataset_updated_at(cache_key)
    now = int(time.time())
    stale_age = (now - updated_at) if updated_at else None
    async with _snapshot_lock:
        refresh_running = bool(_refresh_status.get("running"))
    out["served_from_cache"] = served_from_cache
    out["refresh_in_background"] = refresh_running
    out["last_updated_at"] = updated_at
    out["stale_age_sec"] = stale_age
    out["scan_mode"] = CODEBASE_VIZ_SCAN_MODE
    return out


def _scan_start(phase: str, detail: str = "") -> None:
    label = _repo_scan_label()
    base = detail or _SCAN_LABELS.get(phase, phase)
    if label and phase == "pygount" and not detail:
        base = f"{base} — {label}"
    _scan_state["phase"] = phase
    _scan_state["detail"] = base
    _scan_state["started_at"] = time.monotonic()


def _scan_end() -> None:
    _scan_state["phase"] = "idle"
    _scan_state["detail"] = ""
    _scan_state["started_at"] = None


async def _async_scan_status_payload() -> dict[str, Any]:
    async with _cache_lock:
        inflight = list(_inflight.keys())
        pygount_cached = "pygount" in _cache
        import_cached = "import_edges" in _cache
    phase = _scan_state.get("phase") or "idle"
    started = _scan_state.get("started_at")
    elapsed = round(time.monotonic() - started, 1) if started else 0.0
    if phase == "idle" and inflight:
        primary = inflight[0]
        phase = primary
        detail = _SCAN_LABELS.get(primary, f"Bezig: {primary}")
    else:
        detail = _scan_state.get("detail") or ""
    busy = phase != "idle" or bool(inflight)
    # Pseudo-progress: rises with time so UI never looks frozen (cap 92% until done).
    progress = 0
    if busy:
        progress = min(92, int(12 + elapsed * 5))
    elif pygount_cached:
        progress = 100
    phase_label = _SCAN_LABELS.get(phase, phase) if phase != "idle" else ""
    repo_path_str = str(REPO_PATH) if REPO_PATH else None
    repo_label = _repo_scan_label() or None
    async with _snapshot_lock:
        refresh = dict(_refresh_status)
        pending_count = len(_pending_changed_paths)
    return {
        "busy": busy,
        "phase": phase,
        "phase_label": phase_label,
        "detail": detail,
        "elapsed_sec": elapsed,
        "progress": progress,
        "pygount_cached": pygount_cached,
        "import_edges_cached": import_cached,
        "inflight": inflight,
        "repo_path": repo_path_str,
        "repo_label": repo_label,
        "timeout_sec": PYGOUNT_TIMEOUT,
        "scan_mode": CODEBASE_VIZ_SCAN_MODE,
        "refresh": refresh,
        "pending_changed_paths": pending_count,
    }


async def _invalidate_cache() -> None:
    async with _cache_lock:
        _cache.clear()
        _inflight.clear()
    _scan_end()


def _classify_impacted_datasets(paths: set[str]) -> set[str]:
    if not paths:
        return set()
    impacted: set[str] = {"summary", "structure"}
    for p in paths:
        p_lower = p.lower()
        if p_lower.endswith(".py"):
            impacted.update({"dependencies", "import_edges", "pygount"})
        elif p_lower.endswith((".js", ".jsx", ".ts", ".tsx", ".json", ".yaml", ".yml", ".toml", ".md")):
            impacted.add("pygount")
    return impacted


async def _schedule_refresh(reason: str, changed_paths: set[str] | None = None, force_full: bool = False) -> None:
    global _refresh_task
    changed_paths = changed_paths or set()
    async with _snapshot_lock:
        _pending_changed_paths.update(changed_paths)
        _refresh_status["reason"] = reason
        _refresh_status["last_event_count"] = len(_pending_changed_paths)
    if _refresh_task and not _refresh_task.done():
        return
    _refresh_task = asyncio.create_task(_background_refresh_job(force_full=force_full))


async def _broadcast_message(msg: dict[str, Any]) -> None:
    global _ws_clients
    if not _ws_clients:
        return
    dead: set[WebSocket] = set()
    for ws in _ws_clients:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.add(ws)
    _ws_clients -= dead


async def _background_refresh_job(force_full: bool = False) -> None:
    async with _snapshot_lock:
        _refresh_status["running"] = True
        _refresh_status["started_at"] = time.time()
        _refresh_status["last_error"] = ""
        changed_paths = set(_pending_changed_paths)
        _pending_changed_paths.clear()
    await _broadcast_message({
        "type": "refresh_started",
        "scan_mode": CODEBASE_VIZ_SCAN_MODE,
        "reason": _refresh_status.get("reason", ""),
    })
    try:
        # Zelfde revisie als disk-cache/hydrate (git HEAD), niet dure bestands-handtekening.
        repo_signature = _repo_cache_revision(REPO_PATH) if REPO_PATH else ""
        async with _snapshot_lock:
            prev_signature = _snapshot_state.get("repo_signature", "")
            _snapshot_state["repo_signature"] = repo_signature
        has_delta = bool(changed_paths) or (repo_signature != prev_signature)
        if CODEBASE_VIZ_SCAN_MODE == "full" or force_full:
            impacted = {"pygount", "summary", "structure", "dependencies", "import_edges"}
        elif has_delta:
            impacted = _classify_impacted_datasets(changed_paths)
            if repo_signature != prev_signature:
                # Missed-event fallback: unknown delta -> refresh full core sets.
                impacted.update({"pygount", "summary", "structure", "dependencies", "import_edges"})
        else:
            impacted = set()

        await _broadcast_message({
            "type": "delta_detected",
            "changed_paths": sorted(changed_paths)[:200],
            "has_delta": bool(impacted),
            "impacted": sorted(impacted),
        })
        if not impacted:
            return
        async with _cache_lock:
            for key in impacted:
                _cache.pop(key, None)
        # Rebuild minimal impacted sets in dependency order.
        if "pygount" in impacted:
            await _get_pygount_bundle()
        if "import_edges" in impacted:
            await _get_import_edges()
        if "dependencies" in impacted:
            await _get_or_compute("dependencies", CODEBASE_VIZ_TTL, _build_deps)
        if "structure" in impacted:
            await _get_or_compute("structure", CODEBASE_VIZ_TTL, _build_structure)
        if "summary" in impacted:
            await _get_or_compute("summary", CODEBASE_VIZ_TTL, _build_summary)
        async with _snapshot_lock:
            _snapshot_state["last_checkpoint"] = str(int(time.time()))
        await _persist_snapshot_state()
        await _broadcast_message({
            "type": "refresh_done",
            "scan_mode": CODEBASE_VIZ_SCAN_MODE,
            "impacted": sorted(impacted),
        })
    except Exception as exc:
        log.warning("codebase_viz_refresh_failed: %s", exc)
        async with _snapshot_lock:
            _refresh_status["last_error"] = str(exc)
        await _broadcast_message({
            "type": "refresh_failed",
            "error": str(exc),
        })
    finally:
        async with _snapshot_lock:
            _refresh_status["running"] = False
            _refresh_status["last_completed_at"] = time.time()
        await _persist_snapshot_state()


def _parse_pygount_json(stdout: str) -> tuple[list[dict], list[dict]]:
    """Return (file_rows, language_rows) for pygount 3.x or legacy list format."""
    if not stdout or not stdout.strip():
        return [], []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        log.warning("pygount_json_parse_failed: %s", exc)
        return [], []
    if isinstance(data, dict):
        files = data.get("files")
        langs = data.get("languages")
        return (
            files if isinstance(files, list) else [],
            langs if isinstance(langs, list) else [],
        )
    if isinstance(data, list):
        return data, []
    return [], []


def _path_under_root(fpath: str | Path, root: Path) -> bool:
    try:
        return Path(fpath).resolve().is_relative_to(root.resolve())
    except (OSError, RuntimeError, ValueError):
        return False


def _summary_from_pygount_rows(
    file_rows: list[dict],
    lang_rows: list[dict],
) -> dict[str, Any]:
    total_code = 0
    total_files = 0
    languages: dict[str, dict[str, int]] = {}

    if lang_rows:
        for entry in lang_rows:
            lang = entry.get("language", "unknown")
            if lang.startswith("__") or entry.get("isPseudoLanguage"):
                continue
            files = entry.get("fileCount", 0) or 0
            code = entry.get("codeCount", 0) or 0
            total_files += files
            total_code += code
            languages[lang] = {"code": code, "files": files}
    else:
        for entry in file_rows:
            lang = entry.get("language", "unknown")
            if lang.startswith("__"):
                continue
            code = entry.get("codeCount", entry.get("code", 0)) or 0
            total_files += 1
            total_code += code
            if lang not in languages:
                languages[lang] = {"code": 0, "files": 0}
            languages[lang]["code"] += code
            languages[lang]["files"] += 1

    return {
        "total_files": total_files,
        "total_code": total_code,
        "languages": languages,
    }


def _tree_from_pygount_rows(file_rows: list[dict], target: str) -> dict[str, Any]:
    """Build directory tree from cached pygount file rows (no second subprocess)."""
    root = Path(target).resolve()
    tree: dict[str, Any] = {
        "name": root.name,
        "path": str(root),
        "type": "dir",
        "loc": 0,
        "children": [],
    }
    if not root.is_dir():
        return tree

    dir_map: dict[str, list] = {str(root): tree["children"]}
    for row in file_rows:
        lang = row.get("language", "")
        if lang.startswith("__"):
            continue
        fpath = row.get("path") or row.get("filename", "")
        if not fpath or not os.path.exists(fpath):
            continue
        if not _path_under_root(fpath, root):
            continue
        fpath = os.path.normpath(fpath)
        loc = row.get("codeCount", row.get("code", 0)) or 0
        rel = os.path.relpath(fpath, str(root))
        parts = rel.split(os.sep)

        current_dir = str(root)
        for part in parts[:-1]:
            parent = current_dir
            current_dir = os.path.join(current_dir, part)
            if current_dir not in dir_map:
                children: list = []
                dir_map[parent].append({
                    "name": part,
                    "path": current_dir,
                    "type": "dir",
                    "loc": 0,
                    "children": children,
                })
                dir_map[current_dir] = children

        leaf = {
            "name": parts[-1],
            "path": fpath,
            "type": "file",
            "loc": loc,
            "language": lang,
        }
        dir_map.setdefault(current_dir, []).append(leaf)
        p = current_dir
        while p and p in dir_map:
            for child in dir_map.get(os.path.dirname(p), []):
                if child["path"] == p and child["type"] == "dir":
                    child["loc"] = child.get("loc", 0) + loc
                    break
            p = os.path.dirname(p)
    return tree


def _sync_pygount_bundle(target: str) -> dict[str, Any]:
    """Single pygount run — summary + file rows for tree (shared cache key ``pygount``)."""
    cmd = [
        "pygount",
        "--format=json",
        f"--folders-to-skip={DEFAULT_SKIP}",
        target,
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=PYGOUNT_TIMEOUT,
        )
    except FileNotFoundError:
        log.warning("pygount_missing", extra={"target": target})
        return {
            "summary": {"total_files": 0, "total_code": 0, "languages": {}},
            "file_rows": [],
            "error": "pygount niet gevonden op PATH — pip install pygount",
            "fallback": True,
        }
    except subprocess.TimeoutExpired:
        log.warning("pygount_timeout", extra={"target": target, "timeout": PYGOUNT_TIMEOUT})
        return {
            "summary": {"total_files": 0, "total_code": 0, "languages": {}},
            "file_rows": [],
            "error": (
                f"pygount timeout na {PYGOUNT_TIMEOUT}s — verklein CODEBASE_VIZ_REPO "
                "of verhoog CODEBASE_VIZ_PYGOUNT_TIMEOUT"
            ),
            "fallback": True,
        }
    if proc.returncode != 0:
        return {
            "summary": {"total_files": 0, "total_code": 0, "languages": {}},
            "file_rows": [],
            "error": f"pygount failed (exit {proc.returncode}): {proc.stderr[:200]}",
            "fallback": True,
        }
    file_rows, lang_rows = _parse_pygount_json(proc.stdout)
    return {
        "summary": _summary_from_pygount_rows(file_rows, lang_rows),
        "file_rows": file_rows,
    }


def _sync_pygount_scan(target: str) -> dict[str, Any]:
    return _sync_pygount_bundle(target)["summary"]


def _sync_import_analysis(target: str) -> list[dict[str, str]]:
    root = Path(target).resolve()
    edges: list[dict[str, str]] = []
    for py_file in root.rglob("*.py"):
        if _path_has_skipped_dir(py_file):
            continue
        rel = os.path.relpath(str(py_file), str(root))
        source_mod = rel.replace(os.sep, ".").replace(".py", "").replace(".__init__", "")
        try:
            source = py_file.read_text(errors="replace")
        except OSError:
            continue
        try:
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target_mod = alias.name.split(".")[0]
                    edges.append({
                        "source": source_mod,
                        "target": target_mod,
                        "type": "import",
                    })
            elif isinstance(node, ast.ImportFrom) and node.module:
                target_mod = node.module.split(".")[0]
                edges.append({
                    "source": source_mod,
                    "target": target_mod,
                    "type": "from_import",
                })
    return edges


def _sync_directory_tree(target: str) -> dict[str, Any]:
    """Legacy path: one pygount run (prefer cached ``_get_pygount_bundle`` in async routes)."""
    root = Path(target).resolve()
    if not root.is_dir():
        return {"name": "unknown", "path": target, "type": "dir", "loc": 0, "children": []}
    try:
        bundle = _sync_pygount_bundle(target)
        return _tree_from_pygount_rows(bundle["file_rows"], target)
    except RuntimeError:
        log.warning("pygount_tree_failed", extra={"target": target})
        return {
            "name": root.name,
            "path": str(root),
            "type": "dir",
            "loc": 0,
            "children": [],
        }


async def _fetch_pygount_bundle() -> dict[str, Any]:
    if REPO_PATH is None:
        return {
            "summary": {"total_files": 0, "total_code": 0, "languages": {}},
            "file_rows": [],
        }
    if not _memory_ok():
        async with _cache_lock:
            entry = _cache.get("pygount")
        if entry is not None and isinstance(entry[1], dict):
            return entry[1]
        stale = await asyncio.to_thread(
            _read_pygount_disk_cache,
            allow_stale=True,
            ignore_revision=True,
        )
        if stale is not None:
            stale = dict(stale)
            stale.setdefault("warning", "memory_pressure_serving_disk_cache")
            stale["fallback"] = True
            stale["stale"] = True
            return stale
        raise RuntimeError("memory_pressure")
    _scan_start("pygount")
    try:
        result = await asyncio.to_thread(_sync_pygount_bundle, str(REPO_PATH))
        if result.get("error"):
            stale = await asyncio.to_thread(_read_pygount_disk_cache, allow_stale=True)
            if stale is not None:
                stale = dict(stale)
                stale["fallback"] = True
                stale["stale"] = True
                stale["warning"] = str(result["error"])
                log.warning(
                    "codebase_viz_pygount_timeout_serving_stale_cache",
                    extra={"detail": result["error"]},
                )
                async with _cache_lock:
                    _cache["pygount"] = (time.monotonic(), stale)
                return stale
        else:
            await asyncio.to_thread(_write_pygount_disk_cache, result)
        return result
    finally:
        _scan_end()


async def _fetch_import_edges() -> list[dict[str, str]]:
    if REPO_PATH is None:
        return []
    _scan_start("import_edges")
    try:
        return await asyncio.to_thread(_sync_import_analysis, str(REPO_PATH))
    finally:
        _scan_end()


async def _get_import_edges() -> list[dict[str, str]]:
    """Cached AST import scan — gedeeld door summary, dependencies, dead-imports."""
    return await _get_or_compute("import_edges", CODEBASE_VIZ_TTL, _fetch_import_edges)


async def _get_pygount_bundle() -> dict[str, Any]:
    """Cached pygount — lange TTL + disk-hydrate; één scan bedient structure + summary."""
    if not _memory_ok():
        async with _cache_lock:
            entry = _cache.get("pygount")
        if entry is not None:
            return entry[1]
        cached = await _cached("pygount", PYGOUNT_CACHE_TTL)
        if cached is not None:
            return cached
    return await _get_or_compute("pygount", PYGOUNT_CACHE_TTL, _fetch_pygount_bundle)


async def _run_pygount() -> dict[str, Any]:
    bundle = await _get_pygount_bundle()
    return bundle["summary"]


async def _run_import_analysis() -> list[dict[str, str]]:
    return await _get_import_edges()


async def _build_directory_tree() -> dict[str, Any]:
    if REPO_PATH is None:
        return {"name": "unknown", "path": "", "type": "dir", "loc": 0, "children": []}
    bundle = await _get_pygount_bundle()
    return await asyncio.to_thread(
        _tree_from_pygount_rows,
        bundle["file_rows"],
        str(REPO_PATH),
    )


async def _build_structure():
    bundle = await _get_pygount_bundle()
    tree = await asyncio.to_thread(
        _tree_from_pygount_rows,
        bundle["file_rows"],
        str(REPO_PATH),
    )
    out: dict[str, Any] = {"tree": tree, "summary": bundle["summary"]}
    if bundle.get("error"):
        out["error"] = bundle["error"]
        out["fallback"] = bool(bundle.get("fallback", True))
    elif bundle.get("warning"):
        out["error"] = bundle["warning"]
        out["fallback"] = True
        out["stale"] = bool(bundle.get("stale"))
    return _attach_repo_meta(out)


async def _build_deps():
    edges = await _get_import_edges()
    all_mods: set[str] = set()
    for e in edges:
        all_mods.add(e["source"])
        all_mods.add(e["target"])
    nodes = sorted(all_mods)
    cycles = await asyncio.to_thread(_s3.sync_dependency_cycles, edges)
    return {"nodes": nodes, "edges": edges, "cycles": cycles}


async def _build_summary():
    _scan_start("summary")
    try:
        summary = await _run_pygount()
        edges = await _get_import_edges()
        tree = await _build_directory_tree()

        all_files: list[dict] = []

        def _collect(n: dict) -> None:
            if n.get("type") == "file":
                all_files.append(n)
            for c in n.get("children", []):
                _collect(c)

        _collect(tree)

        test_code = sum(
            f.get("loc", 0) for f in all_files if "test" in f.get("name", "").lower()
        )
        prod_code = max(0, summary.get("total_code", 0) - test_code)
        top_files = sorted(all_files, key=lambda x: x.get("loc", 0), reverse=True)[:10]

        import_count: dict[str, int] = {}
        for e in edges:
            import_count[e["target"]] = import_count.get(e["target"], 0) + 1
        top_modules = sorted(import_count.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_loc": summary.get("total_code", 0),
            "total_files": summary.get("total_files", 0),
            "test_code": test_code,
            "production_code": prod_code,
            "ratio": round(prod_code / max(test_code, 1), 2),
            "languages": summary.get("languages", {}),
            "language_count": len(summary.get("languages", {})),
            "module_count": len({e["source"] for e in edges}),
            "edge_count": len(edges),
            "top_files": top_files,
            "top_modules": [{"module": m, "count": c} for m, c in top_modules],
        }
    finally:
        _scan_end()


async def _run_doctor():
    if REPO_PATH is None:
        return {"error": "No repo path configured", "sections": [], "overall": "unknown"}

    try:
        proc = await asyncio.create_subprocess_exec(
            "hermes",
            "doctor",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    except FileNotFoundError:
        return {
            "error": "hermes CLI not found on PATH",
            "sections": [],
            "summary": {"overall": "unknown", "score": 0, "ok": 0, "warnings": 0, "errors": 1, "total": 1},
            "raw": "",
        }
    except asyncio.TimeoutError:
        return {
            "error": "hermes doctor timed out after 30s",
            "sections": [],
            "summary": {"overall": "unknown", "score": 0, "ok": 0, "warnings": 0, "errors": 1, "total": 1},
            "raw": "",
        }
    output = stdout.decode("utf-8", errors="replace")

    sections: list[dict] = []
    current_section = None
    warnings = errors = ok_count = 0

    for line in output.split("\n"):
        stripped = line.strip()
        if stripped.startswith("◆"):
            if current_section:
                sections.append(current_section)
            current_section = {"name": stripped.lstrip("◆").strip(), "checks": []}
            continue
        if current_section is None:
            continue
        if "✓" in stripped:
            current_section["checks"].append({"status": "ok", "text": stripped})
            ok_count += 1
        elif "⚠" in stripped:
            current_section["checks"].append({"status": "warning", "text": stripped})
            warnings += 1
        elif "✗" in stripped:
            current_section["checks"].append({"status": "error", "text": stripped})
            errors += 1

    if current_section:
        sections.append(current_section)

    total = ok_count + warnings + errors
    score = round((ok_count / max(total, 1)) * 100)

    return {
        "sections": sections,
        "summary": {
            "ok": ok_count,
            "warnings": warnings,
            "errors": errors,
            "total": total,
            "score": score,
            "overall": (
                "healthy" if score >= 90 else ("warning" if score >= 70 else "critical")
            ),
        },
        "raw": output[:5000],
    }


if WATCHDOG_AVAILABLE:

    class CodebaseEventHandler(FileSystemEventHandler):
        SKIP_DIRS = {
            ".git", "node_modules", "venv", ".venv", "__pycache__",
            "dist", "build", ".next", ".cache", ".tox", ".eggs",
            ".mypy_cache", "output", ".hermes",
        }

        def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue):
            super().__init__()
            self._loop = loop
            self._queue = queue

        def should_ignore(self, path: str) -> bool:
            return any(s in path.replace("\\", "/").split("/") for s in self.SKIP_DIRS)

        def _enqueue(self, event_type: str, path: str, is_dir: bool) -> None:
            if self.should_ignore(path):
                return
            evt = {
                "type": event_type,
                "path": path,
                "is_directory": is_dir,
                "ts": time.time(),
            }
            self._loop.call_soon_threadsafe(self._queue.put_nowait, evt)

        def on_created(self, event):  # noqa: ANN001
            self._enqueue("created", event.src_path, event.is_directory)

        def on_modified(self, event):  # noqa: ANN001
            if not event.is_directory:
                self._enqueue("modified", event.src_path, False)

        def on_deleted(self, event):  # noqa: ANN001
            self._enqueue("deleted", event.src_path, event.is_directory)


def _start_watcher(path: str | None = None) -> Any:
    global _observer
    if not WATCHDOG_AVAILABLE or Observer is None:
        return None
    if _observer and _observer.is_alive():
        return _observer
    # Never fall back to os.getcwd() — require an explicit repo
    if REPO_PATH is None:
        log.warning("file_watcher_no_repo: cannot start watcher without CODEBASE_VIZ_REPO or .git discovery")
        return None
    target = path or str(REPO_PATH)
    loop = asyncio.get_running_loop()
    handler = CodebaseEventHandler(loop, _event_queue)
    _observer = Observer()
    _observer.schedule(handler, target, recursive=True)
    _observer.daemon = True
    _observer.start()
    log.info("file_watcher_started", extra={"path": target})
    return _observer


async def _broadcast_events(events: list[dict]) -> None:
    msg = {"type": "changes", "events": events, "count": len(events)}
    await _broadcast_message(msg)


async def _event_flush_loop() -> None:
    while True:
        await asyncio.sleep(CODEBASE_VIZ_DEBOUNCE)
        batch: list = []
        while not _event_queue.empty():
            try:
                batch.append(_event_queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        if batch:
            changed_paths = {
                str(evt.get("path", ""))
                for evt in batch
                if evt.get("path")
            }
            _recent_events.extend(batch)
            if len(_recent_events) > _RECENT_EVENT_LIMIT:
                del _recent_events[0 : len(_recent_events) - _RECENT_EVENT_LIMIT]
            await _broadcast_events(batch)
            if CODEBASE_VIZ_SCAN_MODE == "full":
                await _invalidate_cache()
            await _schedule_refresh("watchdog_events", changed_paths=changed_paths)


async def _ensure_started() -> None:
    global _initialized
    if _initialized:
        return
    async with _lazy_lock:
        if _initialized:
            return
        await _load_snapshot_state()
        await _hydrate_pygount_from_disk()
        if REPO_PATH is not None and WATCHDOG_AVAILABLE:
            try:
                _start_watcher(str(REPO_PATH))
            except Exception as exc:
                log.warning("file_watcher_start_failed: %s", exc)
        if WATCHDOG_AVAILABLE:
            asyncio.create_task(_event_flush_loop())
        await _schedule_refresh("startup", force_full=(CODEBASE_VIZ_SCAN_MODE == "full"))
        _initialized = True
        log.info("codebase_viz_lazy_started", extra={"repo": str(REPO_PATH)})


def _check_ws_token(provided: str | None) -> bool:
    if not provided:
        return False
    try:
        from hermes_cli import web_server as _ws
    except Exception:
        return True
    expected = getattr(_ws, "_SESSION_TOKEN", None)
    if not expected:
        return True
    return hmac.compare_digest(str(provided), str(expected))


@router.get("/health")
async def health():
    await _ensure_started()
    mem = _memory_status()
    async with _cache_lock:
        pygount_cached = "pygount" in _cache
        cache_keys = list(_cache.keys())
    return {
        "status": "ok" if not mem.get("pressure") else "degraded",
        "plugin": "codebase-viz",
        "version": PLUGIN_VERSION,
        "repo_path": str(REPO_PATH) if REPO_PATH else None,
        "watcher_active": bool(
            _observer is not None and getattr(_observer, "is_alive", lambda: False)(),
        ),
        "watchdog_available": WATCHDOG_AVAILABLE,
        "memory": mem,
        "cache_ttl_sec": CODEBASE_VIZ_TTL,
        "pygount_timeout_sec": PYGOUNT_TIMEOUT,
        "scan_mode": CODEBASE_VIZ_SCAN_MODE,
        "pygount_cached": pygount_cached,
        "cache_keys": cache_keys,
        "plugin_api_path": str(Path(__file__).resolve()),
        "snapshot_state_path": str(_snapshot_file()),
        "pygount_disk_cache_path": str(_pygount_disk_cache_file()),
        "pygount_disk_cache_enabled": _pygount_disk_cache_enabled(),
        "disk_cache": _disk_cache_status(),
    }


@router.get("/scan-status")
async def get_scan_status():
    """Lightweight poll endpoint for loading UI (phase, pseudo-progress, cache hits)."""
    await _ensure_started()
    return await _async_scan_status_payload()


@router.get("/structure")
async def get_structure():
    await _ensure_started()
    if REPO_PATH is None:
        return {"tree": _empty_tree(), "summary": _empty_summary(), "error": "no_repo"}
    try:
        cached = await _cached_any("structure")
        if isinstance(cached, dict):
            await _schedule_refresh("structure_poll")
            return await _with_swr_meta(cached, cache_key="structure", served_from_cache=True)
        data = await _get_or_compute("structure", CODEBASE_VIZ_TTL, _build_structure)
        if isinstance(data, dict):
            return await _with_swr_meta(data, cache_key="structure", served_from_cache=False)
        return data
    except Exception as exc:
        return await _api_error_payload(exc, tree=_empty_tree(), summary=_empty_summary())


@router.get("/dependencies")
async def get_dependencies():
    await _ensure_started()
    if REPO_PATH is None:
        return {"nodes": [], "edges": [], "error": "no_repo"}
    try:
        cached = await _cached_any("dependencies")
        if isinstance(cached, dict):
            await _schedule_refresh("dependencies_poll")
            return await _with_swr_meta(cached, cache_key="dependencies", served_from_cache=True)
        data = await _get_or_compute("dependencies", CODEBASE_VIZ_TTL, _build_deps)
        if isinstance(data, dict):
            return await _with_swr_meta(data, cache_key="dependencies", served_from_cache=False)
        return data
    except Exception as exc:
        return await _api_error_payload(exc, nodes=[], edges=[])


@router.get("/summary")
async def get_summary():
    await _ensure_started()
    if REPO_PATH is None:
        return {
            "total_loc": 0,
            "total_files": 0,
            "test_code": 0,
            "production_code": 0,
            "ratio": 0.0,
            "languages": {},
            "language_count": 0,
            "module_count": 0,
            "edge_count": 0,
            "top_files": [],
            "top_modules": [],
            "error": "no_repo",
        }
    try:
        cached = await _cached_any("summary")
        if isinstance(cached, dict):
            await _schedule_refresh("summary_poll")
            return await _with_swr_meta(cached, cache_key="summary", served_from_cache=True)
        data = await _get_or_compute("summary", CODEBASE_VIZ_TTL, _build_summary)
        if isinstance(data, dict):
            return await _with_swr_meta(data, cache_key="summary", served_from_cache=False)
        return data
    except Exception as exc:
        return await _api_error_payload(
            exc,
            total_loc=0,
            total_files=0,
            languages={},
            top_files=[],
            top_modules=[],
        )


@router.get("/doctor")
async def get_doctor():
    await _ensure_started()
    try:
        return await _get_or_compute("doctor", CODEBASE_VIZ_TTL * 5, _run_doctor)
    except Exception as exc:
        return await _api_error_payload(
            exc,
            sections=[],
            summary={"overall": "unknown", "score": 0, "ok": 0, "warnings": 0, "errors": 0, "total": 0},
        )


def _require_repo() -> Path | None:
    return REPO_PATH


@router.get("/churn")
async def get_churn():
    await _ensure_started()
    repo = _require_repo()
    if repo is None:
        return {"items": [], "error": "no_repo", "total": 0}
    try:
        return await _get_or_compute(
            "churn", GIT_CACHE_TTL,
            lambda: asyncio.to_thread(_s3.sync_churn, repo),
        )
    except Exception as exc:
        return await _api_error_payload(exc, items=[], total=0)


@router.get("/age-map")
async def get_age_map():
    await _ensure_started()
    repo = _require_repo()
    if repo is None:
        return {"items": [], "error": "no_repo", "total": 0}
    try:
        return await _get_or_compute(
            "age_map", GIT_CACHE_TTL * 2,
            lambda: asyncio.to_thread(_s3.sync_age_map, repo),
        )
    except Exception as exc:
        return await _api_error_payload(exc, items=[], total=0)


@router.get("/complexity")
async def get_complexity():
    await _ensure_started()
    repo = _require_repo()
    if repo is None:
        return {"items": [], "error": "no_repo", "total": 0}
    try:
        return await _get_or_compute(
            "complexity", GIT_CACHE_TTL,
            lambda: asyncio.to_thread(_s3.sync_complexity, repo),
        )
    except Exception as exc:
        return await _api_error_payload(exc, items=[], total=0)


@router.get("/todos")
async def get_todos():
    await _ensure_started()
    repo = _require_repo()
    if repo is None:
        return {"items": [], "error": "no_repo", "total": 0}
    try:
        return await _get_or_compute(
            "todos", CODEBASE_VIZ_TTL,
            lambda: asyncio.to_thread(_s3.sync_todos, repo),
        )
    except Exception as exc:
        return await _api_error_payload(exc, items=[], total=0)


@router.get("/blame")
async def get_blame():
    await _ensure_started()
    repo = _require_repo()
    if repo is None:
        return {"items": [], "error": "no_repo", "total": 0}
    try:
        return await _get_or_compute(
            "blame", GIT_CACHE_TTL,
            lambda: asyncio.to_thread(_s3.sync_blame, repo),
        )
    except Exception as exc:
        return await _api_error_payload(exc, items=[], total=0)


@router.get("/coverage")
async def get_coverage():
    await _ensure_started()
    repo = _require_repo()
    if repo is None:
        return {"items": [], "error": "no_repo", "total": 0, "coverage_pct": 0}
    try:
        return await _get_or_compute(
            "coverage", CODEBASE_VIZ_TTL,
            lambda: asyncio.to_thread(_s3.sync_coverage, repo),
        )
    except Exception as exc:
        return await _api_error_payload(exc, items=[], total=0, coverage_pct=0)


@router.get("/search")
async def search(q: str = Query("", min_length=0)):
    await _ensure_started()
    repo = _require_repo()
    if repo is None:
        return {"items": [], "error": "no_repo", "total": 0, "query": q}
    try:
        return await asyncio.to_thread(_s3.sync_search, repo, q)
    except Exception as exc:
        return await _api_error_payload(exc, items=[], total=0, query=q)


@router.get("/dead-imports")
async def get_dead_imports():
    await _ensure_started()
    if REPO_PATH is None:
        return {"items": [], "error": "no_repo", "total": 0}
    try:
        deps = await _get_or_compute("dependencies", CODEBASE_VIZ_TTL, _build_deps)
        return await asyncio.to_thread(
            _s3.sync_dead_imports,
            deps.get("edges", []),
            deps.get("nodes", []),
        )
    except Exception as exc:
        return await _api_error_payload(exc, items=[], total=0)


@router.get("/config-drift")
async def get_config_drift():
    await _ensure_started()
    repo = _require_repo()
    if repo is None:
        return {"items": [], "error": "no_repo", "total": 0}
    try:
        return await _get_or_compute(
            "config_drift", GIT_CACHE_TTL,
            lambda: asyncio.to_thread(_s3.sync_config_drift, repo),
        )
    except Exception as exc:
        return await _api_error_payload(exc, items=[], total=0)


@router.get("/session-stats")
async def get_session_stats():
    await _ensure_started()
    try:
        return await _get_or_compute(
            "session_stats", 30.0,
            lambda: asyncio.to_thread(_s3.sync_session_stats),
        )
    except Exception as exc:
        return await _api_error_payload(exc, items=[], total=0)


@router.get("/timeline")
async def timeline(speed: int = Query(5, ge=1, le=60)):
    await _ensure_started()
    repo = _require_repo()
    if repo is None:
        return {"frames": [], "error": "no_repo", "total": 0}
    try:
        key = f"timeline_{speed}"
        return await _get_or_compute(
            key, GIT_CACHE_TTL,
            lambda: asyncio.to_thread(_s3.sync_timeline, repo, min(speed * 20, 200)),
        )
    except Exception as exc:
        return await _api_error_payload(exc, frames=[], total=0)


@router.get("/history")
async def get_history():
    await _ensure_started()
    repo = _require_repo()
    if repo is None:
        return {"points": [], "error": "no_repo", "total": 0}
    try:
        return await _get_or_compute(
            "history", GIT_CACHE_TTL,
            lambda: asyncio.to_thread(_s3.sync_history, repo),
        )
    except Exception as exc:
        return await _api_error_payload(exc, points=[], total=0)


@router.post("/force-scan")
async def force_scan():
    await _ensure_started()
    await _invalidate_cache()
    try:
        await _schedule_refresh("force_scan", force_full=True)
        return {"status": "ok", "scan_complete": False, "refresh_started": True}
    except RuntimeError as exc:
        return {"status": "cached_invalidated", "scan_error": str(exc)}


@router.websocket("/events")
async def ws_events(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not _check_ws_token(token):
        await websocket.close(code=4001, reason="invalid token")
        return
    await _ensure_started()
    await websocket.accept()
    _ws_clients.add(websocket)
    await websocket.send_json({
        "type": "connected",
        "message": "Watching for file changes...",
        "scan_mode": CODEBASE_VIZ_SCAN_MODE,
    })
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                if isinstance(data, dict) and data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(websocket)


__all__ = ["router"]
