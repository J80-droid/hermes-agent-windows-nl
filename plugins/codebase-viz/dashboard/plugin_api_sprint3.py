"""Sprint 3 (fase 10) sync scanners — imported by plugin_api.py."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

GIT_TIMEOUT = int(os.environ.get("CODEBASE_VIZ_GIT_TIMEOUT", "15"))
GIT_LONG_TIMEOUT = int(os.environ.get("CODEBASE_VIZ_GIT_LONG_TIMEOUT", "30"))
RADON_TIMEOUT = int(os.environ.get("CODEBASE_VIZ_RADON_TIMEOUT", "60"))
SEARCH_TIMEOUT = int(os.environ.get("CODEBASE_VIZ_SEARCH_TIMEOUT", "15"))
TODO_PATTERN = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)

SKIP_PARTS = {
    ".git", "node_modules", "venv", ".venv", "__pycache__",
    "dist", "build", ".next", ".cache", ".tox", ".eggs",
    ".mypy_cache", "output", ".hermes",
}

SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".c", ".cpp", ".md"}


def _should_skip(path: Path) -> bool:
    return any(part in SKIP_PARTS for part in path.parts)


def _run_git(repo: Path, *args: str, timeout: int = GIT_TIMEOUT) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git failed ({proc.returncode}): {proc.stderr[:300]}")
    return proc.stdout


def sync_churn(repo: Path) -> dict[str, Any]:
    out = _run_git(
        repo,
        "log", "--all", "--name-only", "--pretty=format:", "--since=1 year ago",
        timeout=GIT_LONG_TIMEOUT,
    )
    counts: Counter[str] = Counter()
    for line in out.splitlines():
        line = line.strip()
        if line and not line.startswith("."):
            counts[line] += 1
    items = [{"file": f, "commits": c} for f, c in counts.most_common(100)]
    return {"items": items, "total": len(items)}


def sync_age_map(repo: Path) -> dict[str, Any]:
    log_out = _run_git(
        repo,
        "log", "--all", "--pretty=format:%H|%ai", "--name-only", "--diff-filter=AMCR",
        timeout=GIT_LONG_TIMEOUT,
    )
    last_date: dict[str, str] = {}
    current_date: str | None = None
    for line in log_out.splitlines():
        if "|" in line and len(line) > 20:
            current_date = line.split("|", 1)[1].strip()
        elif line.strip() and current_date:
            last_date[line.strip()] = current_date

    try:
        tree_out = _run_git(
            repo,
            "ls-tree", "-r", "HEAD", "--format=%(objectsize:bytes)\t%(path)",
        )
    except RuntimeError:
        tree_out = ""

    items: list[dict[str, Any]] = []
    for line in tree_out.splitlines():
        if "\t" not in line:
            continue
        size_str, fpath = line.split("\t", 1)
        if not fpath or fpath.startswith("."):
            continue
        loc = int(size_str) if size_str.isdigit() else 0
        if loc > 0:
            items.append({
                "file": fpath,
                "last_modified": last_date.get(fpath, "unknown"),
                "loc": loc,
            })
    items.sort(key=lambda x: x["loc"], reverse=True)
    return {"items": items[:200], "total": len(items)}


def sync_complexity(repo: Path) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            ["radon", "cc", "-s", "-j", ".", "--min=A"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=RADON_TIMEOUT,
        )
    except FileNotFoundError:
        return {"items": [], "error": "radon not installed", "total": 0}
    except subprocess.TimeoutExpired:
        return {"items": [], "error": "radon timed out", "total": 0}

    if proc.returncode != 0:
        return {"items": [], "error": proc.stderr[:200] or "radon failed", "total": 0}

    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"items": [], "error": "invalid radon json", "total": 0}

    items: list[dict[str, Any]] = []
    for fpath, blocks in data.items():
        if not isinstance(blocks, list) or not blocks:
            continue
        complexities = [b.get("complexity", 0) for b in blocks if isinstance(b, dict)]
        if not complexities:
            continue
        items.append({
            "file": fpath,
            "avg_complexity": round(sum(complexities) / len(complexities), 1),
            "max": max(complexities),
            "blocks": len(complexities),
        })
    items.sort(key=lambda x: x["avg_complexity"], reverse=True)
    items = items[:100]
    return {"items": items, "total": len(items)}


def sync_todos(repo: Path) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for path in repo.rglob("*"):
        if not path.is_file() or _should_skip(path):
            continue
        if path.suffix.lower() not in {".py", ".js", ".jsx", ".ts", ".tsx", ".md", ".yaml", ".yml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        counts: Counter[str] = Counter()
        for i, line in enumerate(text.splitlines(), 1):
            m = TODO_PATTERN.search(line)
            if m:
                counts[m.group(1).upper()] += 1
        if counts:
            rel = os.path.relpath(str(path), str(repo))
            items.append({
                "file": rel,
                "todo": counts.get("TODO", 0),
                "fixme": counts.get("FIXME", 0),
                "hack": counts.get("HACK", 0),
                "xxx": counts.get("XXX", 0),
                "total": sum(counts.values()),
            })
    items.sort(key=lambda x: x["total"], reverse=True)
    return {"items": items[:200], "total": len(items)}


def sync_blame(repo: Path) -> dict[str, Any]:
    globs = ["*.py", "*.js", "*.jsx", "*.ts", "*.tsx"]
    out = _run_git(repo, "shortlog", "-sne", "HEAD", "--", *globs, timeout=GIT_TIMEOUT)
    items: list[dict[str, Any]] = []
    for line in out.splitlines():
        line = line.strip()
        if not line or "\t" not in line:
            continue
        count_str, author_raw = line.split("\t", 1)
        count = int(count_str.strip()) if count_str.strip().isdigit() else 0
        author = author_raw.split("<")[0].strip() if "<" in author_raw else author_raw.strip()
        items.append({"author": author, "commits": count})
    return {"items": items, "total": len(items)}


def sync_coverage(repo: Path) -> dict[str, Any]:
    modules: dict[str, dict[str, Any]] = {}
    for py in repo.rglob("*.py"):
        if _should_skip(py) or "test" in py.name.lower():
            continue
        rel = os.path.relpath(str(py), str(repo)).replace(os.sep, ".")
        mod = rel.replace(".py", "").replace(".__init__", "")
        test_candidates = [
            repo / "tests" / f"test_{py.name}",
            repo / "tests" / f"test_{py.stem}.py",
            py.parent / f"test_{py.name}",
        ]
        has_test = any(t.is_file() for t in test_candidates)
        modules[mod] = {"module": mod, "has_test": has_test, "path": os.path.relpath(str(py), str(repo))}

    items = list(modules.values())
    covered = sum(1 for m in items if m["has_test"])
    return {
        "items": sorted(items, key=lambda x: x["module"])[:300],
        "total": len(items),
        "covered": covered,
        "coverage_pct": round(100 * covered / max(len(items), 1), 1),
    }


def sync_search(repo: Path, query: str) -> dict[str, Any]:
    q = (query or "").strip()
    if len(q) < 2:
        return {"items": [], "total": 0, "query": q}

    try:
        proc = subprocess.run(
            [
                "git", "grep", "-n", "-i", "--full-name", q,
                "--", "*.py", "*.js", "*.jsx", "*.ts", "*.tsx", "*.md", "*.yaml",
            ],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=SEARCH_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"items": [], "total": 0, "query": q, "error": "search timed out"}
    except FileNotFoundError:
        return _sync_search_walk(repo, q)

    if proc.returncode not in (0, 1):
        return {"items": [], "total": 0, "query": q, "error": proc.stderr[:200]}

    items: list[dict[str, Any]] = []
    for line in (proc.stdout or "").splitlines()[:200]:
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        items.append({"file": parts[0], "line": int(parts[1]) if parts[1].isdigit() else 0, "text": parts[2][:200]})
    return {"items": items, "total": len(items), "query": q}


def _sync_search_walk(repo: Path, query: str) -> dict[str, Any]:
    q_lower = query.lower()
    items: list[dict[str, Any]] = []
    for path in repo.rglob("*"):
        if not path.is_file() or _should_skip(path):
            continue
        if path.suffix.lower() not in {".py", ".js", ".jsx", ".ts", ".tsx", ".md"}:
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        rel = os.path.relpath(str(path), str(repo))
        for i, line in enumerate(lines, 1):
            if q_lower in line.lower():
                items.append({"file": rel, "line": i, "text": line.strip()[:200]})
                if len(items) >= 200:
                    return {"items": items, "total": len(items), "query": query}
    return {"items": items, "total": len(items), "query": query}


def sync_dead_imports(edges: list[dict[str, str]], nodes: list[str]) -> dict[str, Any]:
    incoming: Counter[str] = Counter()
    for e in edges:
        incoming[e["target"]] += 1
    stdlib_like = {"os", "sys", "json", "re", "pathlib", "typing", "asyncio", "logging"}
    items = []
    for mod in nodes:
        if incoming.get(mod, 0) == 0 and mod not in stdlib_like:
            items.append({"module": mod, "incoming": 0})
    items.sort(key=lambda x: x["module"])
    return {"items": items[:200], "total": len(items)}


def sync_config_drift(repo: Path) -> dict[str, Any]:
    try:
        from hermes_constants import get_hermes_home
    except ImportError:
        return {"items": [], "error": "hermes_constants unavailable", "total": 0}

    home = get_hermes_home()
    cfg = home / "config.yaml"
    example = repo / "docs" / "domains.yaml.example"
    items = []
    if cfg.is_file():
        items.append({"path": str(cfg), "exists": True, "size": cfg.stat().st_size})
    if example.is_file():
        items.append({"path": str(example), "exists": True, "size": example.stat().st_size})
    return {"items": items, "total": len(items), "hermes_home": str(home)}


def sync_session_stats() -> dict[str, Any]:
    try:
        from hermes_constants import get_hermes_home
    except ImportError:
        return {"items": [], "error": "hermes_constants unavailable", "total": 0}

    db_path = get_hermes_home() / "state.db"
    if not db_path.is_file():
        return {"items": [], "error": "state.db not found", "total": 0}

    items: list[dict[str, Any]] = []
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
        )
        tables = [r[0] for r in cur.fetchall()]
        for table in tables[:5]:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
                items.append({"table": table, "rows": count})
            except sqlite3.Error:
                continue
        conn.close()
    except sqlite3.Error as exc:
        return {"items": [], "error": str(exc), "total": 0}
    return {"items": items, "total": len(items)}


def sync_timeline(repo: Path, max_commits: int = 100) -> dict[str, Any]:
    out = _run_git(
        repo,
        "log", "--reverse", f"--max-count={max_commits}", "--format=%H|%ai|%s",
        timeout=GIT_LONG_TIMEOUT,
    )
    frames = []
    for line in out.splitlines():
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        sha, date, msg = parts
        frames.append({"sha": sha[:7], "date": date, "message": msg[:80]})
    return {"frames": frames, "total": len(frames)}


def sync_history(repo: Path, max_commits: int = 30) -> dict[str, Any]:
    out = _run_git(
        repo,
        "log", f"--max-count={max_commits}", "--format=%H|%ai", "--numstat",
        timeout=GIT_LONG_TIMEOUT,
    )
    points: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    loc_total = 0
    for line in out.splitlines():
        if "|" in line and not line[0].isdigit() and "\t" not in line[:3]:
            if current:
                current["loc"] = loc_total
                points.append(current)
            sha, date = line.split("|", 1)
            current = {"sha": sha[:7], "date": date.strip(), "loc": loc_total}
        elif current and "\t" in line:
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                loc_total += int(parts[0]) + int(parts[1])
    if current:
        current["loc"] = loc_total
        points.append(current)
    points.reverse()
    return {"points": points, "total": len(points)}


def sync_dependency_cycles(edges: list[dict[str, str]]) -> list[list[str]]:
    graph: dict[str, list[str]] = {}
    for e in edges:
        graph.setdefault(e["source"], []).append(e["target"])

    cycles: list[list[str]] = []
    path: list[str] = []
    visited: set[str] = set()

    def dfs(node: str) -> None:
        if node in path:
            idx = path.index(node)
            cycle = path[idx:] + [node]
            if len(cycle) <= 12:
                cycles.append(cycle)
            return
        if node in visited:
            return
        visited.add(node)
        path.append(node)
        for nxt in graph.get(node, []):
            dfs(nxt)
        path.pop()

    for n in list(graph.keys())[:200]:
        dfs(n)
    return cycles[:20]
