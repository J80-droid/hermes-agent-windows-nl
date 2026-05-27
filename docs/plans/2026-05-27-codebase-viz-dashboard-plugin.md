# Codebase Viz — Hermes Dashboard Plugin v2

> **Status:** Implementatieplan · **Versie:** 2.3.0  
> **Voor Hermes:** `subagent-driven-development` skill gebruiken per taak.  
> **Schatting:** ~80 taken · **~9–10 uur** realistisch · **~12 uur** incl. debug-buffer.

### Changelog v2.3 (ten opzichte van v2.2)

- **Bundled pad primair:** `hermes-agent/plugins/codebase-viz/dashboard/` (git + CI), user override optioneel.
- **SDK:** `SDK.fetchJSON` + `usePluginFetch` — geen `useApi` (bestaat niet in `registry.ts`).
- **Icons:** CSS status-spans (`.status-ok` / `.status-warn` / `.status-err`) — geen emoji, geen `SDK.icons`.
- **Backend:** één `/health`, `_ensure_started()` op alle routes; geen `lifespan` / `_ensure_started_sync`.
- **WebSocket:** client met `?token=` + `wss:` (kanban-patroon).
- **Sprints:** MVP → core viz → fase 10 → hardening met exit-criteria.
- **Config:** `CODEBASE_VIZ_REPO` fork-runbook; verificatie MVP vs full.

**Goal:** Interactieve codebase-visualisatie als Hermes dashboard-tab — Sunburst, Force Graph, Treemap, Metrics, Health, Churn, Complexity, TODO/FIXME, Blame, Coverage Maps, Codebase Search, Dead Imports, Config Drift, Profile Diff, Session Stats, Time-lapse — met real-time file watcher voor live updates.

**Architecture:** Hermes **dashboard** plugin (geen agent-tool `plugin.yaml`). Bron in de fork-repo; Python FastAPI backend (pygount + AST import-parser + watchdog); frontend JSX → esbuild IIFE; data via **`SDK.fetchJSON`**; D3 via `/dashboard-plugins/codebase-viz/dist/d3.v7.min.js`.

**Tech Stack:** Hermes Plugin SDK (`fetchJSON`, React hooks, UI components), FastAPI, esbuild, D3.js v7, pygount 3.2, watchdog

**Prerequisites (huidige env):**
| Dependency | Status |
|------------|--------|
| fastapi 0.133.1 | ✓ beschikbaar |
| pygount 3.2.0 | ✓ beschikbaar |
| uvicorn 0.41.0 | ✓ beschikbaar |
| websockets 15.0.1 | ✓ beschikbaar |
| Node.js (voor esbuild) | ✓ beschikbaar (uit `hermes doctor`) |
| watchdog | ✗ moet geïnstalleerd worden (`pip install watchdog`) |
| radon | ✗ optioneel — voor Complexity tab (`pip install radon`) |
| psutil | ✗ optioneel — voor memory guard (`pip install psutil`) |

---

## Bron van waarheid (plugin-locatie)

| Locatie | Gebruik |
|---------|---------|
| **`hermes-agent/plugins/codebase-viz/dashboard/`** | **Primair** — git, review, `npm run build`, commit `dist/` (kanban-model) |
| `%LOCALAPPDATA%\hermes\plugins\codebase-viz\dashboard/` | Optionele **user override** (zelfde `name` → wint over bundled bij discovery) |
| Discovery | Bundled: `<repo>/plugins/<name>/dashboard/manifest.json` + user: `get_hermes_home()/plugins/` |

**Build na wijziging:** `cd hermes-agent/plugins/codebase-viz/dashboard && npm run build`  
**Dashboard herstarten** na backend- of `dist/`-wijziging.

---

## Plugin directory layout

```
hermes-agent/plugins/codebase-viz/dashboard/
├── manifest.json                        # tab-naam, icoon, positie
├── package.json                         # esbuild + npm scripts
├── esbuild.config.mjs                   # Build config (JSX → IIFE)
├── src/
│   ├── index.jsx                        # Entry point: register plugin
│   ├── App.jsx                          # Tab navigatie + data loading (12 tabs)
│   ├── SunburstChart.jsx                # D3 zoomable sunburst
│   ├── ForceGraph.jsx                   # D3 force-directed graph met search + ripple
│   ├── TreemapChart.jsx                 # D3 treemap
│   ├── MetricsTab.jsx                   # Summary cards + language tabel + history chart
│   ├── ChurnTab.jsx                     # Categorie A — meest gewijzigde files (git log)
│   ├── AgeMapTab.jsx                    # Categorie A — file-grootte vs wijzigingsdatum
│   ├── ComplexityTab.jsx                # Categorie A — cyclomatic complexity (radon)
│   ├── TodosTab.jsx                     # Categorie A — TODO/FIXME/HACK scan
│   ├── BlameTab.jsx                     # Categorie A — git blame contributor breakdown
│   ├── CoverageTab.jsx                  # Categorie A — test coverage map
│   ├── SearchTab.jsx                    # Categorie B — codebase search
│   ├── DeadImportsTab.jsx               # Categorie B — ongebruikte import detectie
│   ├── HealthTab.jsx                    # Hermes doctor visualisatie
│   ├── ConfigDriftTab.jsx               # Categorie C — profiel config verschillen
│   ├── SessionStatsTab.jsx              # Categorie C — sessie/token/model stats
│   ├── TimelineTab.jsx                  # Categorie E — time-lapse repo groei
│   ├── Inspector.jsx                    # Klik-node sidebar panel
│   ├── usePluginFetch.js                # SDK.fetchJSON + useEffect (canonical data hook)
│   ├── useFileWatcher.js                # WebSocket met sessietoken
│   └── style.css                        # Plugin CSS + .status-ok/.status-warn/.status-err
├── dist/
│   ├── index.js                         # GEBUILDED IIFE (esbuild output)
│   ├── style.css                        # Copy van src/style.css
│   └── d3.v7.min.js                     # Lokaal geserveerd (geen CDN dependency)
└── plugin_api.py                        # FastAPI router — scan, cache, watcher, WebSocket
```

**Waarom esbuild in plaats van IIFE:** Bij ~2000+ regels JSX is `createElement`-hel unmaintanable. Esbuild compileert leesbare JSX naar exact dezelfde IIFE die het Hermes SDK verwacht. Build duurt <100ms. Geen Vite/React dependency in de bundle — React komt uit het SDK.

**Plugin discovery:** De dashboard server scant `get_hermes_home() / "plugins"` (`web_server.py:4174`). Op deze Windows fork = `%LOCALAPPDATA%\hermes\plugins\`. **Niet** `~/.hermes/plugins/`.

**Plugin ontdekking:** Dashboard-only plugins worden **automatisch** ontdekt via `manifest.json` in de `dashboard/` subdirectory. Geen `plugins.enabled` nodig — dat geldt alleen voor lifecycle/tool plugins.  
Om een dashboard tab te verbergen: `dashboard.hidden_plugins` in `config.yaml`.

**Auth:** Plugin HTTP routes gaan door de dashboard sessie-token middleware — `/api/plugins/codebase-viz/*` vereist `X-Hermes-Session-Token` header (of de sessie cookie). WebSocket heeft `?token=` query parameter. Dit is automatisch geregeld door Hermes.

**Status UI (geen emoji, geen SDK-wijziging):** Gebruik `<span class="status-ok|status-warn|status-err">` met korte tekstlabels (`OK`, `Warning`, `Error`). CSS in `src/style.css` (ook naar `dist/style.css` gekopieerd).

```css
.status-ok   { color: #22c55e; font-weight: 600; }
.status-warn { color: #eab308; font-weight: 600; }
.status-err  { color: #ef4444; font-weight: 600; }
```

Doctor-backend mag CLI-output met symbolen parsen; **render** in de UI altijd via deze spans, niet via emoji of `SDK.icons` (bestaat niet in `web/src/plugins/registry.ts`).

**Beperkingen (expliciet):**

- Import-graaf `/dependencies`: alleen **Python** (`ast.parse`); geen TS/Go edges tenzij later uitgebreid.
- `REPO_PATH` wordt bij **module import** gezet — wijzig `CODEBASE_VIZ_REPO` → herstart dashboard.
- Doctor-parser is fragiel op CLI-tekst; fallback: raw expander.

---

## Configuratie (J. fork)

Standaard repo voor dagelijks werk (niet hardcoden in Python):

```powershell
# Voor dashboard-start of in gebruikersomgeving:
$env:CODEBASE_VIZ_REPO = "D:\A.I\APPS\Hermes_agent_WS\hermes-agent"
```

Of documenteer in fork-runbook / `docs/INSTITUTIONAL_OPERATIONS.md`. Zonder env: cwd `.git` walk-up (fragiel als dashboard niet vanuit repo start). `/health` toont altijd `repo_path`.

---

## Implementatievolgorde (sprints)

| Sprint | Fasen | Exit-criteria |
|--------|-------|---------------|
| **1 — MVP** | 0, 1, 9, 2, 5 (zonder history-chart), 6 | Tab zichtbaar; sunburst + metrics + health; D3 laadt; `repo_path` in `/health` |
| **2 — Core viz** | 3, 4, 7 | Force graph + treemap; WS live met token |
| **3 — Uitbreidingen** | 10a–10f | Alle endpoints in tabel hieronder; per task curl-test |
| **4 — Hardening** | 8 | pytest; thundering herd; graceful degradation |

**Niet in MVP:** fase 10 (churn, timeline, …), history-chart, profile diff UI.

---

## Endpoint-overzicht

| Method | Path | Beschrijving | Cache |
|--------|------|-------------|-------|
| GET | `/api/plugins/codebase-viz/structure` | Directory-boom met LOC per file (sunburst + treemap) | TTL 60s, asyncio.Lock |
| GET | `/api/plugins/codebase-viz/dependencies` | Import-relaties per module (force graph) | TTL 60s, asyncio.Lock |
| GET | `/api/plugins/codebase-viz/summary` | Totalen (metrics) | TTL 60s, asyncio.Lock |
| GET | `/api/plugins/codebase-viz/history` | LOC-trend over laatste N commits | TTL 300s |
| GET | `/api/plugins/codebase-viz/doctor` | Hermes doctor output (geparsed) | TTL 300s |
| GET | `/api/plugins/codebase-viz/churn` | Git churn: meest gewijzigde files | TTL 120s |
| GET | `/api/plugins/codebase-viz/age-map` | File-grootte vs laatste wijzigingsdatum | TTL 120s |
| GET | `/api/plugins/codebase-viz/complexity` | Cyclomatic complexity (radon cc) | TTL 300s |
| GET | `/api/plugins/codebase-viz/todos` | TODO/FIXME/HACK/XXX per module | TTL 60s |
| GET | `/api/plugins/codebase-viz/blame` | Contributor breakdown (git blame) | TTL 120s |
| GET | `/api/plugins/codebase-viz/coverage` | Test coverage map per module | TTL 60s |
| GET | `/api/plugins/codebase-viz/search?q=...` | Zoek door source files (grep) | Geen |
| GET | `/api/plugins/codebase-viz/dead-imports` | Ongebruikte import detectie | TTL 300s |
| GET | `/api/plugins/codebase-viz/config-drift` | Profiel config verschillen | TTL 120s |
| GET | `/api/plugins/codebase-viz/session-stats` | Sessie/token/model stats | TTL 30s |
| GET | `/api/plugins/codebase-viz/timeline?speed=5` | Time-lapse commit data | TTL 300s |
| POST | `/api/plugins/codebase-viz/force-scan` | Forceer herscan, invalidate cache | — |
| WS | `/api/plugins/codebase-viz/events` | Real-time file-change events | — |

---

## Fase 0: Project scaffolding

### Task 0.1: Plugin directory + manifest.json

**Objective:** Maak de plugin directory aan in de fork-repo (primair pad).

**Files:**
- Create: `hermes-agent/plugins/codebase-viz/dashboard/manifest.json`

**Step 1: Create directory**

```bash
# Vanaf hermes-agent/ (repo-root van de fork):
mkdir -p plugins/codebase-viz/dashboard/src
mkdir -p plugins/codebase-viz/dashboard/dist
```

**Step 2: Write manifest.json**

```json
{
  "name": "codebase-viz",
  "label": "Codebase Viz",
  "description": "Interactieve codebase-visualisatie met real-time file watcher en Hermes doctor health",
  "icon": "GitBranch",
  "version": "2.3.0",
  "tab": {
    "path": "/codebase-viz",
    "position": "after:skills"
  },
  "entry": "dist/index.js",
  "css": "dist/style.css",
  "api": "plugin_api.py"
}
```

**Step 3: Verify**

```bash
ls -la plugins/codebase-viz/dashboard/manifest.json
```

Verwacht: bestand bestaat, JSON is valide.

**Step 4: Verify dashboard discovery**

```bash
curl http://127.0.0.1:9119/api/dashboard/plugins 2>/dev/null | python -m json.tool | grep codebase-viz
# Plugin zou in de lijst moeten verschijnen (automatische discovery)

---

### Task 0.2: esbuild + package.json

**Objective:** Zet esbuild op voor JSX → IIFE compilatie.

**Files:**
- Create: `hermes-agent/plugins/codebase-viz/dashboard/package.json`
- Create: `hermes-agent/plugins/codebase-viz/dashboard/esbuild.config.mjs`

**Step 1: Write package.json**

```json
{
  "name": "codebase-viz",
  "private": true,
  "version": "2.3.0",
  "scripts": {
    "build": "node esbuild.config.mjs",
    "watch": "node esbuild.config.mjs --watch"
  },
  "devDependencies": {
    "esbuild": "^0.25.0"
  }
}
```

**Step 2: Write esbuild.config.mjs**

```javascript
import * as esbuild from 'esbuild';
import { copyFileSync, mkdirSync, existsSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const watch = args.includes('--watch');

async function build() {
  // Build JSX → dist/index.js (IIFE, React external)
  await esbuild.build({
    entryPoints: ['src/index.jsx'],
    outfile: 'dist/index.js',
    bundle: true,
    format: 'iife',
    globalName: 'CodebaseVizPlugin',
    loader: { '.jsx': 'jsx' },
    external: ['react'],
    minify: false,
    sourcemap: watch ? 'inline' : false,
    watch: watch ? { onRebuild(error) { console.log(error ? '❌ Build failed' : '✅ Rebuilt'); } } : false,
  });

  // Copy CSS
  if (existsSync('src/style.css')) {
    copyFileSync('src/style.css', 'dist/style.css');
    console.log('✅ Copied style.css');
  }

  if (!watch) {
    console.log('✅ Build complete');
  }
}

build().catch(() => process.exit(1));
```

**Step 3: Install esbuild**

```bash
cd plugins/codebase-viz/dashboard
npm install
```

**Step 4: Verify**

```bash
npx esbuild --version
```

Verwacht: versie ≥ 0.25

---

### Task 0.3: Minimale plugin_api.py + health test

**Objective:** Backend FastAPI plugin met health-endpoint.

**Files:**
- Create: `hermes-agent/plugins/codebase-viz/dashboard/plugin_api.py`

**Step 1: Write plugin_api.py**

```python
"""Codebase Viz dashboard plugin — backend API routes.

Mounted at /api/plugins/codebase-viz/ by the dashboard plugin system.
Authenticated via dashboard session token middleware (X-Hermes-Session-Token header).

Live updates arrive via the /events WebSocket, which tails file-system
changes detected by watchdog and pushes them to connected browsers.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from functools import wraps
from pathlib import Path

from fastapi import APIRouter

log = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Configuratie (env-var overridable)
# ---------------------------------------------------------------------------

def _resolve_repo_path() -> Path:
    """Resolve repo path with .git detection.

    If CODEBASE_VIZ_REPO is set, use it (even if no .git).
    If unset, detect .git in cwd or parents. If none found, return None
    (plugin shows empty state instead of scanning entire disk).
    """
    env_path = os.environ.get("CODEBASE_VIZ_REPO", "").strip()
    if env_path:
        return Path(env_path).resolve()

    cwd = Path.cwd().resolve()
    for parent in [cwd] + list(cwd.parents):
        if (parent / ".git").is_dir():
            return parent
    return None

REPO_PATH = _resolve_repo_path()
"""Resolved bij module load. Herstart Hermes na CODEBASE_VIZ_REPO wijziging."""

CODEBASE_VIZ_TTL = float(os.environ.get("CODEBASE_VIZ_TTL", "60"))
CODEBASE_VIZ_DEBOUNCE = float(os.environ.get("CODEBASE_VIZ_DEBOUNCE", "2.0"))
PYGOUNT_TIMEOUT = int(os.environ.get("CODEBASE_VIZ_PYGOUNT_TIMEOUT", "30"))
DEFAULT_SKIP = ".git,node_modules,venv,.venv,__pycache__,dist,build,.next,.cache,.tox,.eggs,.mypy_cache,output,.hermes"

# ---------------------------------------------------------------------------
# Thread-safe cache met asyncio.Lock (voorkomt thundering herd)
# ---------------------------------------------------------------------------

_cache_lock = asyncio.Lock()
_cache: dict[str, tuple[float, object]] = {}
"""TTL cache: {key: (monotonic_ts, data)}. Lock = asyncio.Lock."""


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
    """Cache-aside pattern with lock to prevent thundering herd.

    First caller to find stale/missing cache acquires the lock,
    computes fresh data, and stores it. Subsequent callers wait on
    the lock and then read the freshly cached value.
    """
    cached = await _cached(key, ttl)
    if cached is not None:
        return cached

    async with _cache_lock:
        # Double-check after acquiring lock
        entry = _cache.get(key)
        if entry and time.monotonic() - entry[0] < ttl:
            return entry[1]

        result = await factory()
        _cache[key] = (time.monotonic(), result)
        return result


async def _invalidate_cache() -> None:
    async with _cache_lock:
        _cache.clear()

# ---------------------------------------------------------------------------
# Synchronous scanning (runs in thread pool via asyncio.to_thread)
# ---------------------------------------------------------------------------

import ast
import json
import subprocess
from typing import Any


def _sync_pygount_scan(target: str) -> dict[str, Any]:
    """Run pygount --format=json. SYNCHRONOUS — runs in thread pool."""
    cmd = [
        "pygount",
        "--format=json",
        f"--folders-to-skip={DEFAULT_SKIP}",
        target,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          timeout=PYGOUNT_TIMEOUT)
    if proc.returncode != 0:
        raise RuntimeError(f"pygount failed (exit {proc.returncode}): "
                           f"{proc.stderr[:500]}")
    data = json.loads(proc.stdout)

    total_code = 0
    total_files = 0
    languages = {}

    for entry in data:
        lang = entry.get("language", "unknown")
        if lang.startswith("__"):
            continue
        count = entry.get("file_count", 0) or entry.get("count", 0)
        code = entry.get("code", 0)
        total_files += count
        total_code += code
        if lang not in languages:
            languages[lang] = {"code": 0, "files": 0}
        languages[lang]["code"] += code
        languages[lang]["files"] += count

    return {
        "total_files": total_files,
        "total_code": total_code,
        "languages": languages,
    }


def _sync_import_analysis(target: str) -> list[dict[str, str]]:
    """Parse Python imports via AST. SYNCHRONOUS — runs in thread pool."""
    root = Path(target).resolve()
    edges = []
    skip_patterns = {".git", "node_modules", "venv", ".venv", "__pycache__",
                     "dist", "build", ".next", ".cache", ".tox", ".eggs",
                     ".mypy_cache", "output", ".hermes"}

    for py_file in root.rglob("*.py"):
        if any(part in skip_patterns for part in py_file.parts):
            continue
        rel = os.path.relpath(str(py_file), str(root))
        source_mod = rel.replace(os.sep, ".").replace(".py", "").replace(".__init__", "")
        try:
            tree = ast.parse(py_file.read_text(errors="replace"), filename=str(py_file))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target_mod = alias.name.split(".")[0]
                    edges.append({"source": source_mod, "target": target_mod, "type": "import"})
            elif isinstance(node, ast.ImportFrom) and node.module:
                target_mod = node.module.split(".")[0]
                edges.append({"source": source_mod, "target": target_mod, "type": "from_import"})
    return edges


def _sync_directory_tree(target: str) -> dict[str, Any]:
    """Build hierarchical directory tree. SYNCHRONOUS — runs in thread pool."""
    root = Path(target).resolve()
    if not root.is_dir():
        return {"name": "unknown", "path": target, "type": "dir", "loc": 0, "children": []}

    tree = {"name": root.name, "path": str(root), "type": "dir", "loc": 0, "children": []}
    dir_map: dict[str, list] = {str(root): tree["children"]}

    cmd = ["pygount", "--format=json", f"--folders-to-skip={DEFAULT_SKIP}", str(root)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=PYGOUNT_TIMEOUT)
    if proc.returncode != 0:
        return tree
    rows = json.loads(proc.stdout)

    for row in rows:
        lang = row.get("language", "")
        if lang.startswith("__"):
            continue
        fpath = row.get("path") or row.get("filename", "")
        if not fpath or not os.path.exists(fpath):
            continue
        fpath = os.path.normpath(fpath)
        if not fpath.startswith(str(root)):
            continue
        loc = row.get("code", 0)
        rel = os.path.relpath(fpath, str(root))
        parts = rel.split(os.sep)

        current_dir = str(root)
        for i, part in enumerate(parts[:-1]):
            parent = current_dir
            current_dir = os.path.join(current_dir, part)
            if current_dir not in dir_map:
                children = []
                dir_map[parent].append({"name": part, "path": current_dir, "type": "dir", "loc": 0, "children": children})
                dir_map[current_dir] = children

        leaf = {"name": parts[-1], "path": fpath, "type": "file", "loc": loc, "language": lang}
        dir_map.setdefault(current_dir, []).append(leaf)
        p = current_dir
        while p and p in dir_map:
            for child in dir_map.get(os.path.dirname(p), []):
                if child["path"] == p and child["type"] == "dir":
                    child["loc"] = child.get("loc", 0) + loc
                    break
            p = os.path.dirname(p)
    return tree


# ---------------------------------------------------------------------------
# Async wrappers (offload sync work to thread pool)
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Data endpoints (alle routes: await _ensure_started() eerst)
# ---------------------------------------------------------------------------

@router.get("/structure")
async def get_structure():
    await _ensure_started()
    return await _get_or_compute("structure", CODEBASE_VIZ_TTL, _build_structure)


async def _build_structure():
    tree = await _build_directory_tree()
    summary = await _run_pygount()
    return {"tree": tree, "summary": summary}


@router.get("/dependencies")
async def get_dependencies():
    await _ensure_started()
    return await _get_or_compute("dependencies", CODEBASE_VIZ_TTL, _build_deps)


async def _build_deps():
    edges = await _run_import_analysis()
    all_mods = set()
    for e in edges:
        all_mods.add(e["source"])
        all_mods.add(e["target"])
    return {"nodes": sorted(all_mods), "edges": edges}


@router.get("/summary")
async def get_summary():
    await _ensure_started()
    return await _get_or_compute("summary", CODEBASE_VIZ_TTL, _build_summary)


async def _build_summary():
    summary = await _run_pygount()
    edges = await _run_import_analysis()
    tree = await _build_directory_tree()

    all_files = []
    def _collect(n):
        if n.get("type") == "file":
            all_files.append(n)
        for c in n.get("children", []):
            _collect(c)
    _collect(tree)

    test_code = sum(f.get("loc", 0) for f in all_files if "test" in f.get("name", "").lower())
    prod_code = max(0, summary.get("total_code", 0) - test_code)
    top_files = sorted(all_files, key=lambda x: x.get("loc", 0), reverse=True)[:10]

    import_count = {}
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
        "module_count": len(set(e["source"] for e in edges)),
        "edge_count": len(edges),
        "top_files": top_files,
        "top_modules": [{"module": m, "count": c} for m, c in top_modules],
    }


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


# ---------------------------------------------------------------------------
# Watchdog file watcher (call_soon_threadsafe + asyncio.Queue)
# ---------------------------------------------------------------------------

import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class CodebaseEventHandler(FileSystemEventHandler):
    SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__",
                 "dist", "build", ".next", ".cache", ".tox", ".eggs",
                 ".mypy_cache", "output", ".hermes"}

    def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue):
        super().__init__()
        self._loop = loop
        self._queue = queue

    def should_ignore(self, path: str) -> bool:
        return any(s in path.replace("\\", "/").split("/") for s in self.SKIP_DIRS)

    def _enqueue(self, event_type: str, path: str, is_dir: bool):
        if self.should_ignore(path):
            return
        evt = {"type": event_type, "path": path, "is_directory": is_dir, "ts": time.time()}
        self._loop.call_soon_threadsafe(lambda: self._queue.put_nowait(evt))

    def on_created(self, event): self._enqueue("created", event.src_path, event.is_directory)
    def on_modified(self, event):
        if not event.is_directory:
            self._enqueue("modified", event.src_path, False)
    def on_deleted(self, event): self._enqueue("deleted", event.src_path, event.is_directory)


_event_queue: asyncio.Queue = asyncio.Queue()
_observer: Observer | None = None


def _start_watcher(path: str = None) -> Observer:
    global _observer
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


def _stop_watcher():
    global _observer
    if _observer:
        _observer.stop()
        _observer.join(timeout=2)
        _observer = None


# ---------------------------------------------------------------------------
# WebSocket events
# ---------------------------------------------------------------------------

from fastapi import WebSocket, WebSocketDisconnect

_ws_clients: set[WebSocket] = set()


@router.websocket("/events")
async def ws_events(websocket: WebSocket, token: str = ""):
    """WebSocket endpoint — vereist `?token=` met dashboard sessie token."""
    await _ensure_started()

    # Token check (constant-time, zoals kanban plugin)
    from hermes_cli import web_server as _ws
    expected = getattr(_ws, "_SESSION_TOKEN", None)
    if expected:
        import hmac
        if not hmac.compare_digest(str(token), str(expected)):
            await websocket.close(code=4001, reason="invalid token")
            return

    await websocket.accept()
    _ws_clients.add(websocket)
    await websocket.send_json({"type": "connected", "message": "Watching for file changes..."})

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


async def _broadcast_events(events: list[dict]):
    if not _ws_clients:
        return
    msg = {"type": "changes", "events": events, "count": len(events)}
    dead = set()
    for ws in _ws_clients:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.add(ws)
    _ws_clients -= dead


async def _event_flush_loop():
    """Debounced flush: collects events from queue, broadcasts batches."""
    while True:
        await asyncio.sleep(CODEBASE_VIZ_DEBOUNCE)
        batch = []
        while not _event_queue.empty():
            try:
                batch.append(_event_queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        if batch:
            await _broadcast_events(batch)
            await _invalidate_cache()

# ---------------------------------------------------------------------------
# Hermes Doctor (/doctor endpoint)
# ---------------------------------------------------------------------------

@router.get("/doctor")
async def get_doctor():
    await _ensure_started()
    return await _get_or_compute("doctor", CODEBASE_VIZ_TTL * 5, _run_doctor)


async def _run_doctor():
    """Run 'hermes doctor' as subprocess, parse output into structured JSON."""
    if REPO_PATH is None:
        return {"error": "No repo path configured", "sections": [], "overall": "unknown"}

    proc = await asyncio.create_subprocess_exec(
        "hermes", "doctor",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    output = stdout.decode("utf-8", errors="replace")

    sections = []
    current_section = None
    warnings = 0
    errors = 0
    ok_count = 0

    for line in output.split("\n"):
        stripped = line.strip()

        # Section header (◆)
        if stripped.startswith("◆"):
            if current_section:
                sections.append(current_section)
            current_section = {"name": stripped.lstrip("◆").strip(), "checks": []}
            continue

        if current_section is None:
            continue

        # Check line: ✓ / ⚠ / ✗
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
            "overall": "healthy" if score >= 90 else ("warning" if score >= 70 else "critical"),
        },
        "raw": output[:5000],
    }

# ---------------------------------------------------------------------------
# Lazy startup — Hermes mount alleen router, niet lifespan
# ---------------------------------------------------------------------------
# Hermes include_router() negeert lifespan export. Watchdog + flush loop
# starten daarom lazy op eerste API-hit of WebSocket-connect (zoals
# hermes-achievements met _start_background_scan()).
# ---------------------------------------------------------------------------

_initialized: bool = False
_lazy_lock = asyncio.Lock()


async def _ensure_started():
    """Start watchdog + flush loop op eerste request (lazy)."""
    global _initialized
    if _initialized:
        return
    async with _lazy_lock:
        if _initialized:
            return
        if REPO_PATH is not None:
            _start_watcher(str(REPO_PATH))
        asyncio.create_task(_event_flush_loop())
        _initialized = True
        log.info("codebase_viz_lazy_started", extra={"repo": str(REPO_PATH)})


@router.get("/health")
async def health():
    await _ensure_started()
    return {
        "status": "ok",
        "plugin": "codebase-viz",
        "version": "2.3.0",
        "repo_path": str(REPO_PATH) if REPO_PATH else None,
        "watcher_active": _observer is not None and _observer.is_alive(),
    }


__all__ = ["router"]
# Geen lifespan export — Hermes negeert dat toch voor dashboard plugins.
```

**Step 2: Syntax check**

```bash
cd plugins/codebase-viz/dashboard
python -c "import ast; ast.parse(open('plugin_api.py').read()); print('OK')"
```

Verwacht: `OK`

**Step 3: Test health endpoint**

```bash
curl http://127.0.0.1:9119/api/plugins/codebase-viz/health | python -m json.tool
```

---

### Task 0.4: Minimale frontend (JSX) + build test

**Objective:** JSX entry-point die de plugin registreert, + esbuild test.

**Files:**
- Create: `hermes-agent/plugins/codebase-viz/dashboard/src\index.jsx`
- Create: `hermes-agent/plugins/codebase-viz/dashboard/src\App.jsx`
- Create: `hermes-agent/plugins/codebase-viz/dashboard/src\style.css`

**Step 1: src/index.jsx**

```jsx
/**
 * Codebase Viz — Hermes Dashboard Plugin
 * Entry point. Uses esbuild to compile JSX → dist/index.js (IIFE).
 * React comes from window.__HERMES_PLUGIN_SDK__, never bundled.
 */
import App from './App';
import './style.css';

(function () {
  'use strict';
  const SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK) return;

  if (window.__HERMES_PLUGINS__ &&
      typeof window.__HERMES_PLUGINS__.register === 'function') {
    window.__HERMES_PLUGINS__.register('codebase-viz', App);
  }
})();
```

**Step 2: src/App.jsx**

```jsx
import React from 'react';
const h = React.createElement;

const CATEGORIES = [
  {
    id: 'visuals',
    label: 'Visuals',
    tabs: [
      { id: 'sunburst', label: 'Sunburst' },
      { id: 'force-graph', label: 'Force Graph' },
      { id: 'treemap', label: 'Treemap' },
      { id: 'metrics', label: 'Metrics' },
    ],
  },
  {
    id: 'analysis',
    label: 'Analysis',
    tabs: [
      { id: 'churn', label: 'Churn' },
      { id: 'age-map', label: 'Age Map' },
      { id: 'complexity', label: 'Complexity' },
      { id: 'todos', label: 'TODO/FIXME' },
      { id: 'blame', label: 'Blame' },
      { id: 'coverage', label: 'Coverage' },
      { id: 'dependency-cycles', label: 'Dependency Cycles' },
      { id: 'dead-imports', label: 'Dead Imports' },
    ],
  },
  {
    id: 'hermes',
    label: 'Hermes',
    tabs: [
      { id: 'health', label: 'Health' },
      { id: 'config-drift', label: 'Config Drift' },
      { id: 'session-stats', label: 'Session Stats' },
    ],
  },
  {
    id: 'tools',
    label: 'Tools',
    tabs: [
      { id: 'search', label: 'Search' },
      { id: 'timeline', label: 'Timeline' },
    ],
  },
];

export default function App() {
  const [tab, setTab] = React.useState('sunburst');
  const [menuOpen, setMenuOpen] = React.useState(null);

  const currentCat = CATEGORIES.find(c => c.tabs.some(t => t.id === tab));

  return h('div', { className: 'codebase-viz-container' },
    h('div', { className: 'codebase-viz-tabs' },
      CATEGORIES.map(cat =>
        h('div', {
          key: cat.id,
          className: 'codebase-viz-category' + (menuOpen === cat.id ? ' open' : ''),
          onMouseEnter: () => setMenuOpen(cat.id),
          onMouseLeave: () => setMenuOpen(null),
        },
          h('span', { className: 'codebase-viz-category-label' },
            cat.label,
            ' \u25BE',  /* chevron — geen SDK.icons */
          ),
          menuOpen === cat.id && h('div', { className: 'codebase-viz-dropdown' },
            cat.tabs.map(t =>
              h('button', {
                key: t.id,
                className: 'codebase-viz-dropdown-item' + (tab === t.id ? ' active' : ''),
                onClick: () => { setTab(t.id); setMenuOpen(null); },
              }, t.label),
            ),
          ),
        ),
      ),
    ),
    h('div', { className: 'codebase-viz-active-label' },
      currentCat ? `${currentCat.label} › ${currentCat.tabs.find(t => t.id === tab)?.label}` : tab,
    ),
    h('div', { className: 'codebase-viz-content' },
      h('p', { className: 'text-sm text-muted-foreground' },
        'Codebase Viz geladen. Selecteer een tab.',
      ),
    ),
  );
}
```

**Step 3: src/style.css**

```css
.codebase-viz-container {
  padding: 0.5rem;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.codebase-viz-tabs {
  display: flex;
  gap: 0;
  margin-bottom: 0.25rem;
  border-bottom: 1px solid hsl(var(--border));
  position: relative;
}
.codebase-viz-category {
  position: relative;
  padding: 0.5rem 1rem;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.15s ease;
  user-select: none;
}
.codebase-viz-category:hover,
.codebase-viz-category.open {
  color: hsl(var(--foreground));
  background: hsl(var(--accent) / 0.3);
}
.codebase-viz-category-label {
  color: hsl(var(--muted-foreground));
  font-size: 0.875rem;
  white-space: nowrap;
}
.codebase-viz-category:hover .codebase-viz-category-label {
  color: hsl(var(--foreground));
}
.codebase-viz-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  background: hsl(var(--popover));
  border: 1px solid hsl(var(--border));
  border-radius: 0.5rem;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  min-width: 160px;
  z-index: 50;
  padding: 0.25rem;
  animation: fadeIn 0.1s ease;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}
.codebase-viz-dropdown-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 0.4rem 0.75rem;
  font-size: 0.8rem;
  background: transparent;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  color: hsl(var(--popover-foreground));
  transition: background 0.1s;
}
.codebase-viz-dropdown-item:hover {
  background: hsl(var(--accent));
}
.codebase-viz-dropdown-item.active {
  background: hsl(var(--accent));
  color: hsl(var(--accent-foreground));
  font-weight: 600;
}
.codebase-viz-active-label {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  padding: 0.25rem 0.25rem 0.5rem;
  border-bottom: none;
}
.codebase-viz-content { flex: 1; overflow: auto; }
.status-ok   { color: #22c55e; font-weight: 600; }
.status-warn { color: #eab308; font-weight: 600; }
.status-err  { color: #ef4444; font-weight: 600; }
.codebase-viz-error {
  padding: 1rem;
  background: hsl(var(--destructive) / 0.1);
  border: 1px solid hsl(var(--destructive) / 0.3);
  border-radius: 0.5rem;
  color: hsl(var(--destructive));
}
```

**Step 4: Build**

```bash
cd plugins/codebase-viz/dashboard
npm run build
```

Expected output: `✅ Built dist/index.js`

**Step 5: Verify in dashboard**

```bash
# Herstart dashboard / F5 in browser
# Tab "Codebase Viz" moet zichtbaar zijn na Skills
curl http://127.0.0.1:9119/api/dashboard/plugins | python -m json.tool | grep codebase-viz
```

---

### Task 0.5: Installeer D3 lokaal + watchdog

**Objective:** Geen CDN dependency — serveer D3.js lokaal vanuit dist/.

**Step 1: Download D3.js lokaal**

```bash
cd plugins/codebase-viz/dashboard
curl -sL "https://d3js.org/d3.v7.min.js" -o dist/d3.v7.min.js
echo "d3.v7.min.js gedownload ($(wc -c < dist/d3.v7.min.js) bytes)"
```

**Step 2: Installeer watchdog**

```bash
pip install watchdog
python -c "import watchdog; print(watchdog.__version__)"
```

---

## Fase 1: Backend endpoints (structure, dependencies, summary)

### Task 1.1: Implementeer /structure endpoint

**Objective:** Directory tree met LOC per file, via async thread pool.

De endpoints zijn al geschreven in Task 0.3. Deze task is: **testen en verifiëren.**

**Step 1: Test /structure**

```bash
curl http://127.0.0.1:9119/api/plugins/codebase-viz/structure | python -c "
import json, sys
d = json.load(sys.stdin)
assert 'tree' in d, 'Missing tree'
assert d['tree']['type'] == 'dir', 'Root not dir'
print(f'OK: tree root={d[\"tree\"][\"name\"]}, {len(d[\"tree\"].get(\"children\",[]))} children')
"
```

### Task 1.2: Implementeer /dependencies endpoint

**Step 1: Test /dependencies**

```bash
curl http://127.0.0.1:9119/api/plugins/codebase-viz/dependencies | python -c "
import json, sys
d = json.load(sys.stdin)
assert 'nodes' in d, 'Missing nodes'
assert 'edges' in d, 'Missing edges'
print(f'OK: {len(d[\"nodes\"])} nodes, {len(d[\"edges\"])} edges')
"
```

### Task 1.3: Implementeer /summary endpoint

**Step 1: Test /summary**

```bash
curl http://127.0.0.1:9119/api/plugins/codebase-viz/summary | python -c "
import json, sys
d = json.load(sys.stdin)
assert 'total_loc' in d, 'Missing total_loc'
assert 'languages' in d, 'Missing languages'
print(f'OK: {d[\"total_loc\"]} LOC, {d[\"total_files\"]} files, {d[\"language_count\"]} languages')
"
```

### Task 1.4: Test thundering herd protectie

**Step 1: Simuleer parallelle requests**

```bash
# Stuur 10 requests tegelijk na cache invalidatie
curl -X POST http://127.0.0.1:9119/api/plugins/codebase-viz/force-scan
for i in $(seq 1 10); do
  curl -s http://127.0.0.1:9119/api/plugins/codebase-viz/summary &
done
wait
echo "Alle 10 parallelle requests voltooid (pygount zou maar 1× gedraaid moeten zijn)"
```

### Task 1.5: Test graceful degradation zonder repo

**Step 1: Test zonder .git**

```bash
CODEBASE_VIZ_REPO=/tmp/nonexistent hermes dashboard &
sleep 3
curl http://127.0.0.1:9119/api/plugins/codebase-viz/structure | python -c "
import json, sys
d = json.load(sys.stdin)
# Moet empty tree teruggeven, geen 500
assert not d.get('error'), f'Got error: {d.get(\"error\")}'
print('OK: graceful degradation werkt')
"
```

---

## Fase 2: Sunburst tab

### Task 2.1: SunburstChart.jsx

**Objective:** D3 zoomable sunburst. Gebruikt lokaal d3 + `usePluginFetch` / tab-data uit `App.jsx`.

**File:** `src/SunburstChart.jsx`

```jsx
import React, { useEffect, useRef } from 'react';

const COLOR_MAP = {
  'Python': '#3572A5', 'TypeScript': '#3178C6', 'JavaScript': '#F7DF1E',
  'HTML': '#E34F26', 'CSS': '#563D7C', 'Shell': '#89E051',
  'Markdown': '#083FA1', 'YAML': '#CB171E', 'JSON': '#292929',
  'Dockerfile': '#384D54',
};
const COLOR_DEFAULT = '#6B7280';

// D3 wordt geladen uit lokaal bestand (window.__CODEBASE_VIZ_D3__)
function getD3() {
  return window.d3;
}

export default function SunburstChart({ data }) {
  const svgRef = useRef(null);

  useEffect(() => {
    if (!data?.tree || !svgRef.current) return;
    const d3 = getD3();
    if (!d3) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = svgRef.current.clientWidth || 800;
    const height = svgRef.current.clientHeight || 600;
    const radius = Math.min(width, height) / 2;

    // Build hierarchy
    const root = d3.hierarchy(data.tree)
      .sum(d => Math.max(d.data.loc || 0, 1));
    d3.partition().size([2 * Math.PI, radius])(root);

    const g = svg.append('g')
      .attr('transform', `translate(${width / 2},${height / 2})`);

    const arc = d3.arc()
      .startAngle(d => d.x0).endAngle(d => d.x1)
      .innerRadius(d => d.y0).outerRadius(d => d.y1);

    // Entrance animation
    const path = g.selectAll('path')
      .data(root.descendants().filter(d => d.depth > 0))
      .enter().append('path')
      .attr('d', arc)
      .attr('fill', d => COLOR_MAP[d.data.language] || COLOR_DEFAULT)
      .attr('opacity', 0)
      .attr('stroke', 'hsl(var(--background))')
      .attr('stroke-width', 1)
      .transition().duration(800)
      .attr('opacity', d => Math.min(1, (d.x1 - d.x0) * (d.y1 - d.y0) * 50 + 0.3))
      .delay(d => d.depth * 50);

    // Zoom-to-node
    let currentZoom = null;
    path.on('click', function(event, d) {
      event.stopPropagation();
      if (currentZoom === d) {
        currentZoom = null;
        g.transition().duration(750).attr('transform', `translate(${width / 2},${height / 2})`);
        path.transition().duration(750).attr('d', arc);
        return;
      }
      currentZoom = d;
      const kx = 2 * Math.PI / (d.x1 - d.x0);
      const ky = radius / (d.y1 - d.y0);
      g.transition().duration(750)
        .attr('transform', `translate(${width / 2},${height / 2}) scale(${Math.min(kx, ky)}) rotate(${-d.x0 * 180 / Math.PI})`);
      path.transition().duration(750).attr('d', n => arc(Object.assign({}, n, {
        x0: (n.x0 - d.x0) * kx, x1: (n.x1 - d.x0) * kx,
        y0: (n.y0 - d.y0) * ky, y1: (n.y1 - d.y0) * ky,
      })));
    });

    // Hover heatmap
    path.on('mouseover', function(event, d) {
      const lang = d.data.language;
      d3.select(this).attr('opacity', 0.85).attr('stroke', '#FFF').attr('stroke-width', 2);
      if (lang) path.attr('opacity', n => n.data.language === lang ? 1 : 0.2);
    }).on('mouseout', function() {
      d3.select(this).attr('opacity', 1).attr('stroke', null).attr('stroke-width', 1);
      path.attr('opacity', 1);
    });

    // Click background = reset
    svg.on('click', () => {
      currentZoom = null;
      g.transition().duration(750).attr('transform', `translate(${width / 2},${height / 2})`);
      path.transition().duration(750).attr('d', arc);
    });
  }, [data]);

  return React.createElement('svg', {
    ref: svgRef,
    style: { width: '100%', height: '100%', minHeight: '500px' },
  });
}
```

### Task 0.5: `usePluginFetch.js` (canonical data hook)

**File:** `src/usePluginFetch.js`

```jsx
import React from 'react';

const API = '/api/plugins/codebase-viz';

/**
 * Kanban-patroon: SDK.fetchJSON injecteert X-Hermes-Session-Token automatisch.
 * Geen useApi — die hook bestaat niet in __HERMES_PLUGIN_SDK__.
 */
export function usePluginFetch(path, deps = []) {
  const SDK = window.__HERMES_PLUGIN_SDK__;
  const [data, setData] = React.useState(null);
  const [error, setError] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    if (!SDK?.fetchJSON || !path) return undefined;
    const ac = new AbortController();
    setLoading(true);
    setError(null);
    SDK.fetchJSON(`${API}${path}`, { signal: ac.signal })
      .then(setData)
      .catch((err) => {
        if (err?.name !== 'AbortError') setError(err);
      })
      .finally(() => setLoading(false));
    return () => ac.abort();
  }, [path, ...deps]);

  return { data, error, loading };
}

export async function postForceScan() {
  const SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK?.fetchJSON) return;
  await SDK.fetchJSON(`${API}/force-scan`, { method: 'POST' });
}
```

---

### Task 2.2: Wire Sunburst in App.jsx (CATEGORIES + usePluginFetch)

**Navigatie:** gebruik overal **CATEGORIES** dropdowns uit Task 0.4 — geen aparte platte `TABS`-lijst.

```jsx
import React from 'react';
import SunburstChart from './SunburstChart';
import { usePluginFetch, postForceScan } from './usePluginFetch';

const h = React.createElement;

const CATEGORIES = [ /* zie Task 0.4 — volledige array */ ];

const TAB_ENDPOINTS = {
  sunburst: '/structure',
  'force-graph': '/dependencies',
  treemap: '/structure',
  metrics: '/summary',
  churn: '/churn',
  'age-map': '/age-map',
  complexity: '/complexity',
  todos: '/todos',
  blame: '/blame',
  coverage: '/coverage',
  search: '/search',
  'dead-imports': '/dead-imports',
  health: '/doctor',
  'config-drift': '/config-drift',
  'session-stats': '/session-stats',
  timeline: '/timeline',
};

function CategoryNav({ categories, tab, setTab, menuOpen, setMenuOpen }) {
  return h('div', { className: 'codebase-viz-tabs' },
    categories.map((cat) =>
      h('div', {
        key: cat.id,
        className: 'codebase-viz-category' + (menuOpen === cat.id ? ' open' : ''),
        onMouseEnter: () => setMenuOpen(cat.id),
        onMouseLeave: () => setMenuOpen(null),
      },
        h('span', { className: 'codebase-viz-category-label' }, cat.label, ' v'),
        menuOpen === cat.id && h('div', { className: 'codebase-viz-dropdown' },
          cat.tabs.map((t) =>
            h('button', {
              key: t.id,
              className: 'codebase-viz-dropdown-item' + (tab === t.id ? ' active' : ''),
              onClick: () => { setTab(t.id); setMenuOpen(null); },
            }, t.label),
          ),
        ),
      ),
    ),
  );
}

export default function App() {
  const { Card, CardHeader, CardTitle, CardContent, Button } =
    window.__HERMES_PLUGIN_SDK__.components;
  const [tab, setTab] = React.useState('sunburst');
  const [menuOpen, setMenuOpen] = React.useState(null);

  const path = TAB_ENDPOINTS[tab] || '/structure';
  const { data, error, loading } = usePluginFetch(path, [tab]);

  const shell = (content) => h('div', { className: 'codebase-viz-container' },
    h(CategoryNav, { categories: CATEGORIES, tab, setTab, menuOpen, setMenuOpen }),
    h('div', { className: 'codebase-viz-content' }, content),
  );

  if (error || data?.fallback) {
    return shell(h('div', { className: 'codebase-viz-error' },
      h('p', null, error?.message || data?.error || 'Scan mislukt'),
      h(Button, {
        variant: 'outline', size: 'sm',
        onClick: () => postForceScan().then(() => window.location.reload()),
      }, 'Opnieuw proberen'),
    ));
  }

  if (loading || !data) {
    return shell(h('p', { style: { padding: '2rem', textAlign: 'center' } }, 'Scannen...'));
  }

  if (!data.tree?.children?.length && tab === 'sunburst') {
    return shell(h('p', null,
      'Geen git-repo of lege tree. Zet CODEBASE_VIZ_REPO (zie plan — Configuratie).',
    ));
  }

  let content;
  switch (tab) {
    case 'sunburst':
      content = h(SunburstChart, { data });
      break;
    default:
      content = h(Card, null,
        h(CardHeader, null, h(CardTitle, null, 'Tab: ' + tab)),
        h(CardContent, null, h('p', null, 'Nog niet geïmplementeerd')),
      );
  }
  return shell(content);
}
```

**CSS (Task 0.4 `style.css`):** voeg `.status-ok`, `.status-warn`, `.status-err` toe (zie sectie Status UI).

---

## Fase 3: Force Graph tab

### Task 3.1: ForceGraph.jsx

**Objective:** D3 force-directed graph met drag, zoom, search, dependency ripple, inspector.

**File:** `src/ForceGraph.jsx`

```jsx
import { h } from 'react';  // Notitie: esbuild compileert JSX naar h()
```

Zie het volledige component in de appendix. Kernfunctionaliteit:
- Force simulation met collision avoidance
- Force-drag nodes
- Dependency ripple op hover (groen = outgoing, rood = incoming)
- Zoom-to-node + search met autocomplete dropdown
- Inspector sidebar bij klik (toont deps + used-by)

### Task 3.2: Search + fly-to

Zoekbalk boven de graph. SDK Input component + gefilterde autocomplete.

```jsx
const [search, setSearch] = React.useState('');
const suggestions = search.length > 1 && data?.nodes
  ? data.nodes.filter(n => n.toLowerCase().includes(search.toLowerCase())).slice(0, 10)
  : [];
```

### Task 3.3: Inspector sidebar

Klik node → rechts schuift paneel in met:
- Module naam
- Aantal incoming edges (rode pijlen)
- Aantal outgoing edges (groene pijlen)
- Top 20 van elk

```jsx
const [inspected, setInspected] = React.useState(null);
```

### Task 3.4: D3 lokaal laden in de browser

D3 wordt geladen uit `dist/d3.v7.min.js`. De Hermes dashboard server serveert statische bestanden uit de plugin `dist/` directory.

Plugin laadt D3:

```jsx
useEffect(() => {
  if (!window.d3) {
    const s = document.createElement('script');
    s.src = '/dashboard-plugins/codebase-viz/dist/d3.v7.min.js';
    // Alternatief: direct via plugin static file mount
    document.head.appendChild(s);
  }
}, []);
```

De Hermes dashboard server mount automatisch statische files uit de plugin dashboard directory. Het exacte URL-patroon is te vinden in de Hermes docs, maar lokaal laden via relatieve path werkt.

---

## Fase 4: Treemap tab

### Task 4.1: TreemapChart.jsx

**Objective:** D3 treemap — rechthoeken = files, kleur = taal, grootte = LOC.

Zie dezelfde D3 patterns als Sunburst. Entrance animation + zoom-to-directory.

---

## Fase 5: Metrics tab

### Task 5.1: MetricsTab.jsx

**Objective:** Summary cards + language breakdown table + top files + top modules + history chart.

Gebruik SDK `Card`, `CardHeader`, `CardTitle`, `CardContent` voor de layout.

**Componenten:**
- Total LOC card
- Total files card
- Language count card
- Test:Prod ratio card (kleur: groen 1:1-3, geel >3, rood <1)
- Language breakdown tabel (naam, files, LOC, %)
- Top 10 files (naam, LOC, taal)
- Top 10 modules (naam, import count)

### Task 5.2: History trend chart

**Endpoint:** `/history` (git LOC trend over laatste 30 commits)

D3 area chart: datum op x-as, LOC op y-as.

---

## Fase 6: Health tab (Hermes Doctor)

### Task 6.1: HealthTab.jsx

**Objective:** Visualiseer `hermes doctor` output als gestructureerd dashboard.

**Data:** `/api/plugins/codebase-viz/doctor` → geparst als JSON.

**Layout:**

```
┌────────────────────────────────────────────────────────────┐
│  Overall: ✓ Healthy (92%)                                  │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐              │
│  │ Python │ │ Config │ │ API    │ │ Tools  │              │
│  │ ✓ 3.11 │ │ ✓ v24  │ │ ⚠ 2/6  │ │ ✓ all  │              │
│  └────────┘ └────────┘ └────────┘ └────────┘              │
│                                                            │
│  ⚠ Warnings (3)                                            │
│  • OpenAI Codex: not logged in                             │
│  • Google Gemini OAuth: not logged in                      │
│  • xAI OAuth: not logged in                                │
│                                                            │
│  ✓ Passed (24)                                             │
│  • Python 3.11.15                                          │
│  • ~/AppData\Local\hermes\...\config.yaml exists           │
│  • git                                                     │
│  ...                                                       │
│                                                            │
│  [⟳ Refresh] [▶ Run Doctor]                                │
└────────────────────────────────────────────────────────────┘
```

**Implementatie (status-spans, geen SDK.icons):**

```jsx
import { postForceScan } from './usePluginFetch';

function StatusBadge({ status }) {
  if (status === 'error') return h('span', { className: 'status-err' }, 'Error');
  if (status === 'warning') return h('span', { className: 'status-warn' }, 'Warning');
  return h('span', { className: 'status-ok' }, 'OK');
}

export default function HealthTab({ data }) {
  if (!data?.sections) return null;
  const { summary } = data;
  const score = summary?.score || 0;
  const overallClass = score >= 90 ? 'status-ok' : score >= 70 ? 'status-warn' : 'status-err';

  return h('div', { style: { padding: '0.5rem' } },
    h('div', { style: { fontSize: '1.25rem', fontWeight: 700, marginBottom: '1rem' } },
      h('span', { className: overallClass }, `Health: ${summary.overall}`),
      ` (${score}%) — `,
      h('span', { className: 'status-ok' }, `${summary.ok} OK`), ' ',
      h('span', { className: 'status-warn' }, `${summary.warnings} warnings`), ' ',
      h('span', { className: 'status-err' }, `${summary.errors} errors`),
    ),
    h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '0.75rem' } },
      data.sections.map((section) => h(HealthSection, { key: section.name, section })),
    ),
    h('details', { style: { marginTop: '1rem' } },
      h('summary', null, 'Raw output'),
      h('pre', { style: { fontSize: '0.7rem', overflow: 'auto', maxHeight: '300px' } }, data.raw),
    ),
  );
}

function HealthSection({ section }) {
  const errors = section.checks.filter((c) => c.status === 'error');
  const warnings = section.checks.filter((c) => c.status === 'warning');

  return h('div', { style: { border: '1px solid hsl(var(--border))', borderRadius: '0.5rem', padding: '0.75rem' } },
    h('div', { style: { fontWeight: 600, marginBottom: '0.5rem' } }, section.name),
    errors.map((c) => h('div', { key: c.text, style: { fontSize: '0.8rem', padding: '0.2rem 0' } },
      h(StatusBadge, { status: 'error' }), ' ', c.text)),
    warnings.map((c) => h('div', { key: c.text, style: { fontSize: '0.8rem', padding: '0.2rem 0' } },
      h(StatusBadge, { status: 'warning' }), ' ', c.text)),
  );
}
```

### Task 6.2: Refresh-knop

```jsx
import { postForceScan } from './usePluginFetch';

h(Button, {
  variant: 'outline', size: 'sm',
  onClick: () => postForceScan().then(() => window.location.reload()),
}, 'Refresh');
```

---

## Fase 7: Real-time file watcher

### Task 7.1: WebSocket client (useFileWatcher)

**File:** `src/useFileWatcher.js`

```jsx
import { useEffect, useRef, useState } from 'react';

export default function useFileWatcher() {
  const [events, setEvents] = useState([]);
  const wsRef = useRef(null);

  useEffect(() => {
    const token = window.__HERMES_SESSION_TOKEN__ || '';
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const qs = new URLSearchParams({ token });
    const wsUrl = `${proto}//${window.location.host}/api/plugins/codebase-viz/events?${qs}`;

    function connect() {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data);
          if (data.type === 'changes') setEvents(data.events || []);
        } catch (e) { /* ignore */ }
      };
      ws.onclose = () => setTimeout(connect, 5000);
      ws.onerror = () => ws.close();
    }

    connect();
    return () => { if (wsRef.current) wsRef.current.close(); };
  }, []);

  return events;
}
```

### Task 7.2: Real-time animaties in ForceGraph

Nieuwe nodes → scale-in (r: 0 → 8 → 6), groene glow
Gewijzigde nodes → pulse (r: 6 → 10, geel, 1s)
Verwijderde nodes → shrink-out (r: 0, 500ms)

```jsx
useEffect(() => {
  if (!events?.length) return;
  const d3 = window.d3;
  if (!d3) return;

  events.forEach(evt => {
    const name = evt.path.split(/[/\\]/).pop();
    if (evt.type === 'created') {
      // Add new node + entrance animatie
    } else if (evt.type === 'modified') {
      // Pulse animatie
    } else if (evt.type === 'deleted') {
      // Shrink-out + remove
    }
  });
}, [events]);
```

---

## Fase 8: Institutional hardening

### Task 8.1: Test suite (pytest + mocks)

**File:** `tests/plugins/test_codebase_viz_plugin.py`

**Pad:** `tests/plugins/test_codebase_viz_plugin.py` importeert  
`from plugins.codebase_viz.dashboard import plugin_api` (bundled in repo).  
User override onder `%LOCALAPPDATA%\hermes\plugins\` wordt in CI niet getest.

```python
"""Tests for the codebase-viz dashboard plugin."""
from fastapi.testclient import TestClient
from fastapi import FastAPI
import pytest
import os
import tempfile

@pytest.fixture
def plugin_api():
    with patch.dict(os.environ, {"CODEBASE_VIZ_REPO": tempfile.gettempdir()}):
        from plugins.codebase_viz.dashboard import plugin_api as api
        import asyncio
        # Reset cache
        asyncio.run(api._invalidate_cache())
        yield api

class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/plugins/codebase-viz/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

class TestStructure:
    def test_graceful_degradation(self, client):
        resp = client.get("/api/plugins/codebase-viz/structure")
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.json()
            assert "tree" in data or "error" in data

class TestCacheLock:
    def test_thundering_herd_prevented(self, client):
        """Parallel requests should only trigger 1 pygount."""
        import asyncio
        async def parallel():
            tasks = [asyncio.to_thread(client.get, "/api/plugins/codebase-viz/summary") for _ in range(5)]
            results = await asyncio.gather(*tasks)
            return [r.json() for r in results]
        results = asyncio.run(parallel())
        assert all(r.get("total_loc") == results[0].get("total_loc") for r in results)

class TestDoctor:
    def test_doctor_parses_output(self, client):
        resp = client.get("/api/plugins/codebase-viz/doctor")
        assert resp.status_code == 200
        data = resp.json()
        assert "sections" in data or "error" in data
```

### Task 8.2: Memory guard

```python
import psutil
_process = psutil.Process()

async def _check_memory(max_mb=500):
    rss = _process.memory_info().rss / 1024 / 1024
    if rss > max_mb:
        log.warning("memory_high", extra={"rss_mb": round(rss, 1)})
        return False
    return True
```

### Task 8.3: Keyboard shortcuts

```jsx
useEffect(() => {
  const handler = (e) => {
    if (e.key >= '1' && e.key <= '9') setTab(['sunburst','force-graph','treemap','metrics','churn','age-map','complexity','todos','blame'][parseInt(e.key)-1]);
    if (e.key === '0') setTab('coverage');
    if (e.key === '-' || e.key === '=') {/* search / health via other keys */}
    if (e.key === 'Escape') setInspected(null);
    if (e.key === 'r' && !e.ctrlKey && !e.metaKey) {
      postForceScan();
    }
  };
  window.addEventListener('keydown', handler);
  return () => window.removeEventListener('keydown', handler);
}, []);
```

---

## Fase 9: D3.js lokaal serveer-mechanisme

De Hermes dashboard server mount statische bestanden onder:

```
/dashboard-plugins/<plugin_name>/<file_path>
```

Voor D3: `GET /dashboard-plugins/codebase-viz/dist/d3.v7.min.js`

**Niet** via `/api/plugins/...` — dat zijn alleen API-routes.  
`plugin_api.py` heeft **geen** `StaticFiles` mount nodig — Hermes dashboard server doet dat automatisch.

---

## Fase 10: Extra features met performance-garanties

Deze fase voegt alle gekozen uitbreidingen toe uit categorie A (visualisaties), B (tools), C (Hermes integraties) en E (time-lapse). **Elke feature ≤ 5s response time gegarandeerd.** Waar nodig batch processing, caching, of schatting i.p.v. exacte scan.

### ⚡ Performance design patterns (voor alle endpoints)

```python
# 1. Abort na tijd: elke git subprocess heeft een harde timeout
GIT_TIMEOUT = 15  # seconden
BATCH_SIZE = 50   # files per batch

# 2. Batch git commands i.p.v. 1 per file
# FOUT: for f in files: subprocess.run(["git", "log", "-1", "--", f])
# GOED: subprocess.run(["git", "log", "--all", "--name-only", "--format=%H|%ai", "--since=1 year ago"])

# 3. Progress endpoint — UITGESTELD (niet in v2.3 scope)
#    Gebruik cache + loading state in UI; voeg later toe indien scans >30s

# 4. Stabilized cache voor git data (TTL 600s i.p.v. 60s)
# Git history verandert alleen bij commits — 10 minuten cache is veilig.

# 5. Subprocess pool limiet: max 2 parallelle subprocesses
import asyncio
_subprocess_semaphore = asyncio.Semaphore(2)
```

### Task 10.1: Churn analysis (A)

**Endpoint:** `GET /api/plugins/codebase-viz/churn`

Backend: 1 git command, ~3-5s. ✅ Geen probleem.

```python
async def _sync_churn() -> list[dict]:
    proc = await asyncio.create_subprocess_exec(
        "git", "log", "--all", "--name-only", "--pretty=format:", "--since=1 year ago",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        cwd=REPO_PATH
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=GIT_TIMEOUT)
    counts = {}
    for line in stdout.decode().splitlines():
        line = line.strip()
        if line and not line.startswith("."):
            counts[line] = counts.get(line, 0) + 1
    top = sorted(counts.items(), key=lambda x: -x[1])[:100]
    return [{"file": f, "commits": c} for f, c in top]
```

Cache: TTL 300s (git history verandert zelden per minuut).

### Task 10.2: Codebase age map (A) — 🔴 GEFIXT

**Oude aanpak:** `git log -1` per file = 1000+ subprocess calls = **minuten**.  
**Nieuwe aanpak:** 1 git command die alle files + datums in één keer ophaalt.

```python
async def _sync_age_map() -> list[dict]:
    # ÉÉN git command i.p.v. N
    proc = await asyncio.create_subprocess_exec(
        "git", "log", "--all", "--pretty=format:%H|%ai",
        "--name-only", "--diff-filter=AMCR",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        cwd=REPO_PATH
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
    # Parse output: laatste datum per file
    last_date = {}
    current_date = None
    for line in stdout.decode().splitlines():
        if "|" in line and len(line) > 20:  # commit line
            parts = line.split("|", 1)
            current_date = parts[1].strip()
        elif line.strip() and current_date:
            last_date[line.strip()] = current_date

    # LOC per file via eenmalige git ls-tree + wc -l equivalent
    loc_proc = await asyncio.create_subprocess_exec(
        "git", "ls-tree", "-r", "HEAD", "--format=%(objectsize:bytes)\t%(path)",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        cwd=REPO_PATH
    )
    loc_stdout, _ = await asyncio.wait_for(loc_proc.communicate(), timeout=15)

    results = []
    for line in loc_stdout.decode().splitlines():
        if "\t" not in line: continue
        size_str, fpath = line.split("\t", 1)
        if not fpath or fpath.startswith("."): continue
        loc = int(size_str) if size_str.isdigit() else 0
        date = last_date.get(fpath, "unknown")
        if loc > 0:
            results.append({"file": fpath, "last_modified": date, "loc": loc})

    return results
```

**Performance:** 2 git commands totaal (~2-5s). Cache TTL 600s. ✅

### Task 10.3: Dependency cycles (A)

**Endpoint:** verrijkt `/dependencies`. DFS op bestaande graaf. ✅ Snel.

### Task 10.4: Complexity heatmap (A) — ⚠ GEFIXT

```python
async def _sync_complexity() -> list[dict]:
    try:
        proc = await asyncio.create_subprocess_exec(
            "radon", "cc", "-s", "-j", ".", "--min=A",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=REPO_PATH
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
    except asyncio.TimeoutError:
        return {"error": "radon timeout (60s)", "fallback": True}

    data = json.loads(stdout)
    results = []
    for fpath, blocks in data.items():
        avg = sum(b["complexity"] for b in blocks) / max(len(blocks), 1)
        results.append({"file": fpath, "avg_complexity": round(avg, 1), "blocks": len(blocks),
                        "max": max(b["complexity"] for b in blocks) if blocks else 0})
    return sorted(results, key=lambda x: -x["avg_complexity"])[:100]  # top 100
```

**Performance:** 1 radon command, `--min=A` filtert lage complexity, limit 100 resultaten. Cache TTL 300s.

### Task 10.5: TODO/FIXME scan (A)

Backend: `rglob` met file type filter + read_text. Performance is OK voor ≤ 2000 files. Cache TTL 60s.

### Task 10.6: Git blame heatmap (A) — 🔴 GEFIXT

**Oude aanpak:** `git blame --line-porcelain` per file = **minuten voor 1000+ files**.  
**Nieuwe aanpak:** `git shortlog -sne` geeft per-contributor line count in 1 command.

```python
async def _sync_blame() -> dict:
    proc = await asyncio.create_subprocess_exec(
        "git", "shortlog", "-sne", "HEAD",
        "--", "*.py", "*.js", "*.jsx", "*.ts", "*.tsx", "*.go", "*.rs", "*.java", "*.c", "*.cpp",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        cwd=REPO_PATH
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)

    authors = []
    for line in stdout.decode().splitlines():
        line = line.strip()
        if not line: continue
        parts = line.split("\t")
        if len(parts) < 2: continue
        count_str = parts[0].strip()
        author_email = parts[1].strip()
        count = int(count_str) if count_str.isdigit() else 0
        # Parse "Author Name <email>"
        if "<" in author_email:
            author = author_email.split("<")[0].strip()
        else:
            author = author_email
        authors.append({"author": author, "commits": count})
    return authors
```

**Performance:** 1 git command, ~1-2s. ✅

### Task 10.7: Test coverage map (A)

Backend: `rglob("*.py")` + `os.path.exists`. Snel (~1s).

### Task 10.8: Codebase search (B)

Backend: 1 grep command, result cap 200, timeout 15s. ✅

### Task 10.9: Large file warning (B)

Filter op bestaande data. ✅ Gratis.

### Task 10.10: SVG export (B)

Browser-only, geen backend. ✅

### Task 10.11: Dead import scanner (B)

Verrijkt bestaande edges. ✅ Snel.

### Task 10.12: Session stats (C)

SQLite query op state.db. ✅ Snel.

### Task 10.13 + 10.14: Config drift + Profile diff (C)

YAML reads op max 10 profielen. ✅ Snel.

### Task 10.15: Time-lapse (E) — 🔴 GEFIXT

**Oude aanpak:** 200 git commands = minuten.  
**Nieuwe aanpak:** `git log` in 1 batch + `git diff --stat` per commit batch.

```python
async def _sync_timeline(max_commits: int = 200) -> dict:
    # ÉÉN git log voor alle commits
    proc = await asyncio.create_subprocess_exec(
        "git", "log", "--reverse", f"--max-count={max_commits}",
        "--format=%H|%ai|%s",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        cwd=REPO_PATH
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
    lines = stdout.decode().strip().split("\n")
    if not lines or lines == [""]:
        return {"frames": [], "total": 0}

    frames = []
    for line in lines:
        parts = line.split("|", 2)
        if len(parts) < 3: continue
        sha, date, msg = parts
        # Gebruik git diff --stat tussen commits voor file count delta
        # In plaats van ls-tree per commit
        frames.append({"sha": sha[:7], "date": date, "message": msg[:80]})

    # Batch file count: één ls-tree voor HEAD
    ls_proc = await asyncio.create_subprocess_exec(
        "git", "ls-tree", "-r", "HEAD", "--name-only",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        cwd=REPO_PATH
    )
    ls_stdout, _ = await asyncio.wait_for(ls_proc.communicate(), timeout=15)
    head_count = len([f for f in ls_stdout.decode().splitlines() if f])
    for f in frames:
        f["files"] = head_count  # Schatting op basis van HEAD

    return {"frames": frames, "total": len(frames)}
```

**Performance:** 2 git commands + schatting. ~3-5s. ✅

### Frontend performance patches

**Patch 1: AbortController op tab-switch**

```jsx
const abortRef = useRef(null);

function switchTab(newTab) {
  // Abort vorige request
  if (abortRef.current) abortRef.current.abort();
  abortRef.current = new AbortController();
  setTab(newTab);
}

// usePluginFetch ondersteunt AbortController al via deps/tab-switch
```

**Patch 2: Force graph node cap (max 500 nodes)**

```jsx
const maxNodes = 500;
const displayNodes = data.nodes.length > maxNodes
  ? data.nodes.slice(0, maxNodes)
  : data.nodes;
const displayEdges = data.edges.filter(e =>
  displayNodes.includes(e.source) && displayNodes.includes(e.target)
);
```

**Patch 3: Virtual scroll voor grote tabellen (TODO, Coverage, Churn)**

Gebruik SDK `utils.cn()` voor CSS containment:

```css
.codebase-viz-virtual-scroll {
  overflow-y: auto;
  contain: content;
  height: 400px;
}
```

**Patch 4: Time-lapse frame skip bij veel commits**

```jsx
const MAX_FRAMES = 100;
const step = Math.ceil(frames.length / MAX_FRAMES);
const displayFrames = frames.filter((_, i) => i % step === 0);
```

---

## Samenvatting performance fixes

| Endpoint | Oude performance | Nieuwe performance | Fix |
|----------|-----------------|-------------------|-----|
| age-map | 1000+ subprocess calls → **minuten** | 2 git commands → **~2s** | `git log --all --name-only` batch |
| blame | 1000+ `git blame` → **minuten** | 1 `git shortlog` → **~1s** | shortlog -sne |
| timeline | 200 `git ls-tree` → **minuten** | 2 git commands → **~3s** | batch + schatting |
| complexity | Hele repo radon → **30-60s** | `--min=A` + top 100 → **~10s** | filter + limit |
| Frontend | Geen abort, geen cap | AbortController + 500 node cap | stabiliteit |
| Git cache | TTL 60s | TTL 300-600s voor git data | minder scans |

---

## Tijdschatting (realistisch, inclusief debug/tests)

| Fase | Tasks | Optimistisch | Realistisch |
|------|-------|-------------|-------------|
| 0 — Scaffold | 5 | ~30 min | ~45 min |
| 1 — Backend endpoints | 5 | ~30 min | ~45 min |
| 2 — Sunburst tab | 2 | ~20 min | ~30 min |
| 3 — Force graph tab | 4 | ~35 min | ~60 min |
| 4 — Treemap tab | 1 | ~15 min | ~20 min |
| 5 — Metrics tab | 2 | ~20 min | ~30 min |
| 6 — Health tab (doctor) | 2 | ~25 min | ~40 min |
| 7 — Real-time watcher | 2 | ~20 min | ~35 min |
| 8 — Hardening (tests) | 3 | ~25 min | ~45 min |
| 9 — D3 lokaal | 1 | ~10 min | ~15 min |
| 10a — Churn + Age Map + Cycles | 3 | ~25 min | ~40 min |
| 10b — Complexity + TODO + Blame + Coverage | 4 | ~30 min | ~50 min |
| 10c — Search + Dead Imports | 2 | ~20 min | ~30 min |
| 10d — Session Stats + Config Drift + Profile Diff | 3 | ~25 min | ~40 min |
| 10e — SVG Export + Large File Warning | 2 | ~15 min | ~20 min |
| 10f — Time-lapse | 1 | ~20 min | ~35 min |
| **Totaal** | **~80** | **~6 uur** | **~9-10 uur** |

**Let op:** tijden zijn exclusief debuggen van SDK-lifecycle bugs, WebSocket auth issues, en D3 integratiefouten. Reken op **2-3 extra uren** voor onvoorziene problemen. Totaal: **~12 uur.**

---

## Verificatie

### MVP gate (na sprint 1)

1. `GET /api/dashboard/plugins` bevat `codebase-viz` (niet `hermes plugins list`)
2. `hermes dashboard` → tab **Codebase Viz** na Skills
3. `GET /api/plugins/codebase-viz/health` → `repo_path`, `version` `2.3.0`
4. Sunburst rendert met data uit `/structure`
5. Metrics-tab: `/summary` totalen kloppen
6. Health-tab: doctor JSON + `.status-ok` / `.status-warn` / `.status-err` (geen emoji in UI)
7. D3: `GET /dashboard-plugins/codebase-viz/dist/d3.v7.min.js` → 200
8. `npm run build` in `plugins/codebase-viz/dashboard` → `dist/index.js` gecommit

### Full gate (na sprint 4)

1. `hermes dashboard` → http://127.0.0.1:9119/ → tab "Codebase Viz" zichtbaar
2. Sunburst: hover heatmap, zoom-to-node, entrance animation
3. Force graph: drag nodes, search+fly, dependency ripple, inspector sidebar, rode cycle edges
4. Metrics: correcte LOC/files/ratio, language breakdown table, large file warning
5. Churn: top 100 meest gewijzigde files met barchart
6. Age map: scatterplot age vs LOC
7. Complexity: barchart per module, rood > 10
8. TODO/FIXME: tabel per file met counts, totaal over repo
9. Blame: donut chart per contributor
10. Coverage: grid groen/rood per module
11. Health: doctor output parsed, score + warning/error cards
12. Codebase search: typ query → resultaten met file/lijn/context
13. Dead imports: tabel modules met 0 import count
14. Config drift: profielen tabel + highlights bij verschillen
15. Profile diff: dropdowns, side-by-side diff view
16. Session stats: cards + pie chart per model
17. Time-lapse: play knop, D3 bar chart animatie door commits
18. SVG export: knop per chart → download SVG
19. WebSocket: verander .py file → force graph pulse (live)
20. Graceful degradation: `CODEBASE_VIZ_REPO=/nonexistent` → error banner + retry
21. Thundering herd: 10 parallel requests → 1 pygount run
22. Plugin pad primair: `hermes-agent/plugins/codebase-viz/dashboard/` (bundled); discovery ook via `%LOCALAPPDATA%\hermes\plugins\` op Windows fork
23. pytest `tests/plugins/test_codebase_viz_plugin.py` passed
24. WebSocket verbindt met `?token=`; zonder token → close 4001

---

## Risico's en mitigaties

| Risico | Mitigatie |
|--------|-----------|
| Pygount timeout op grote repo | 30s timeout + graceful fallback |
| WebSocket overload bij bulk changes | 2s debounce via asyncio.Queue |
| D3.js lokaal niet gevonden | `/dashboard-plugins/codebase-viz/dist/d3.v7.min.js` (geen StaticFiles in plugin_api) |
| Event loop blocking | `asyncio.to_thread` voor rglob/ast.parse |
| Thundering herd op cache expiry | `asyncio.Lock` met double-check |
| Plugin pad fout voor Windows fork | `get_hermes_home() / "plugins"` gebruiken |
| Dashboard tab verbergen | `dashboard.hidden_plugins` in config.yaml |
| `.git` detectie faalt | CODEBASE_VIZ_REPO env var als override |
| Radon niet geïnstalleerd (complexity) | Graceful fallback: "Radon niet beschikbaar" |
| Grote blame output (hele repo) | Filter op source files, max 1000 lines |
| Time-lapse 200 commits = 200 git commands | Batch verwerking, TTL 300s cache |
| Config drift leest profiel configs buiten plugin | Read-only, geen writes |

---

## Appendix: Volledige componenten

(Zie Task 2.1 voor Sunburst, zie references/ voor ForceGraph, Treemap, Metrics, Health volledige sources.)
