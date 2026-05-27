"""Codebase Viz dashboard plugin — backend API routes.

Mounted at ``/api/plugins/codebase-viz/`` by the dashboard plugin system.
All data routes call ``_ensure_started()`` (lazy watchdog + WS flush loop).

Error policy: HTTP 200 with ``error`` / ``fallback: true`` for missing repo
or scan failures; WebSocket rejects invalid ``?token=`` with close 4001.
"""

from __future__ import annotations

import ast
import asyncio
import hmac
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

log = logging.getLogger(__name__)
router = APIRouter()

PLUGIN_VERSION = "2.3.0"
DEFAULT_SKIP = (
    ".git,node_modules,venv,.venv,__pycache__,dist,build,.next,.cache,"
    ".tox,.eggs,.mypy_cache,output,.hermes"
)

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


REPO_PATH = _resolve_repo_path()
CODEBASE_VIZ_TTL = float(os.environ.get("CODEBASE_VIZ_TTL", "60"))
CODEBASE_VIZ_DEBOUNCE = float(os.environ.get("CODEBASE_VIZ_DEBOUNCE", "2.0"))
PYGOUNT_TIMEOUT = int(os.environ.get("CODEBASE_VIZ_PYGOUNT_TIMEOUT", "30"))

_cache_lock = asyncio.Lock()
_cache: dict[str, tuple[float, object]] = {}

_initialized = False
_lazy_lock = asyncio.Lock()
_event_queue: asyncio.Queue = asyncio.Queue()
_observer: Any = None
_ws_clients: set[WebSocket] = set()


async def _cached(key: str, ttl: float = 60.0) -> object | None:
    async with _cache_lock:
        entry = _cache.get(key)
        if entry and time.monotonic() - entry[0] < ttl:
            return entry[1]
    return None


async def _set_cache(key: str, data: object) -> None:
    async with _cache_lock:
        _cache[key] = (time.monotonic(), data)


async def _get_or_compute(key: str, ttl: float, factory):
    cached = await _cached(key, ttl)
    if cached is not None:
        return cached

    async with _cache_lock:
        entry = _cache.get(key)
        if entry and time.monotonic() - entry[0] < ttl:
            return entry[1]
        try:
            result = await factory()
        except Exception:
            log.exception("codebase_viz_compute_failed", extra={"cache_key": key})
            raise
        _cache[key] = (time.monotonic(), result)
        return result


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


async def _invalidate_cache() -> None:
    async with _cache_lock:
        _cache.clear()


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


def _sync_pygount_scan(target: str) -> dict[str, Any]:
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
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"pygount timed out after {PYGOUNT_TIMEOUT}s",
        ) from exc
    if proc.returncode != 0:
        raise RuntimeError(
            f"pygount failed (exit {proc.returncode}): {proc.stderr[:500]}",
        )
    file_rows, lang_rows = _parse_pygount_json(proc.stdout)
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


def _sync_import_analysis(target: str) -> list[dict[str, str]]:
    root = Path(target).resolve()
    edges: list[dict[str, str]] = []
    skip = {
        ".git", "node_modules", "venv", ".venv", "__pycache__",
        "dist", "build", ".next", ".cache", ".tox", ".eggs",
        ".mypy_cache", "output", ".hermes",
    }
    for py_file in root.rglob("*.py"):
        if any(part in skip for part in py_file.parts):
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
    root = Path(target).resolve()
    if not root.is_dir():
        return {"name": "unknown", "path": target, "type": "dir", "loc": 0, "children": []}

    tree: dict[str, Any] = {
        "name": root.name,
        "path": str(root),
        "type": "dir",
        "loc": 0,
        "children": [],
    }
    dir_map: dict[str, list] = {str(root): tree["children"]}

    cmd = ["pygount", "--format=json", f"--folders-to-skip={DEFAULT_SKIP}", str(root)]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=PYGOUNT_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        log.warning("pygount_tree_timeout", extra={"target": target})
        return tree
    if proc.returncode != 0:
        return tree
    file_rows, _lang_rows = _parse_pygount_json(proc.stdout)

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


async def _run_pygount() -> dict[str, Any]:
    if REPO_PATH is None:
        return {"total_files": 0, "total_code": 0, "languages": {}}
    return await asyncio.to_thread(_sync_pygount_scan, str(REPO_PATH))


async def _run_import_analysis() -> list[dict[str, str]]:
    if REPO_PATH is None:
        return []
    return await asyncio.to_thread(_sync_import_analysis, str(REPO_PATH))


async def _build_directory_tree() -> dict[str, Any]:
    if REPO_PATH is None:
        return {"name": "unknown", "path": "", "type": "dir", "loc": 0, "children": []}
    return await asyncio.to_thread(_sync_directory_tree, str(REPO_PATH))


async def _build_structure():
    tree = await _build_directory_tree()
    summary = await _run_pygount()
    return {"tree": tree, "summary": summary}


async def _build_deps():
    edges = await _run_import_analysis()
    all_mods: set[str] = set()
    for e in edges:
        all_mods.add(e["source"])
        all_mods.add(e["target"])
    return {"nodes": sorted(all_mods), "edges": edges}


async def _build_summary():
    summary = await _run_pygount()
    edges = await _run_import_analysis()
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
    target = path or (str(REPO_PATH) if REPO_PATH else os.getcwd())
    loop = asyncio.get_running_loop()
    handler = CodebaseEventHandler(loop, _event_queue)
    _observer = Observer()
    _observer.schedule(handler, target, recursive=True)
    _observer.daemon = True
    _observer.start()
    log.info("file_watcher_started", extra={"path": target})
    return _observer


async def _broadcast_events(events: list[dict]) -> None:
    if not _ws_clients:
        return
    msg = {"type": "changes", "events": events, "count": len(events)}
    dead: set[WebSocket] = set()
    for ws in _ws_clients:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.add(ws)
    _ws_clients -= dead


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
            await _broadcast_events(batch)
            await _invalidate_cache()


async def _ensure_started() -> None:
    global _initialized
    if _initialized:
        return
    async with _lazy_lock:
        if _initialized:
            return
        if REPO_PATH is not None and WATCHDOG_AVAILABLE:
            try:
                _start_watcher(str(REPO_PATH))
            except Exception as exc:
                log.warning("file_watcher_start_failed: %s", exc)
        if WATCHDOG_AVAILABLE:
            asyncio.create_task(_event_flush_loop())
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
    return {
        "status": "ok",
        "plugin": "codebase-viz",
        "version": PLUGIN_VERSION,
        "repo_path": str(REPO_PATH) if REPO_PATH else None,
        "watcher_active": bool(
            _observer is not None and getattr(_observer, "is_alive", lambda: False)(),
        ),
        "watchdog_available": WATCHDOG_AVAILABLE,
    }


@router.get("/structure")
async def get_structure():
    await _ensure_started()
    if REPO_PATH is None:
        return {"tree": _empty_tree(), "summary": _empty_summary(), "error": "no_repo"}
    try:
        return await _get_or_compute("structure", CODEBASE_VIZ_TTL, _build_structure)
    except Exception as exc:
        return await _api_error_payload(exc, tree=_empty_tree(), summary=_empty_summary())


@router.get("/dependencies")
async def get_dependencies():
    await _ensure_started()
    if REPO_PATH is None:
        return {"nodes": [], "edges": [], "error": "no_repo"}
    try:
        return await _get_or_compute("dependencies", CODEBASE_VIZ_TTL, _build_deps)
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
        return await _get_or_compute("summary", CODEBASE_VIZ_TTL, _build_summary)
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


@router.post("/force-scan")
async def force_scan():
    await _ensure_started()
    await _invalidate_cache()
    try:
        summary = await _run_pygount()
        await _set_cache("summary", summary)
        return {"status": "ok", "scan_complete": True}
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
