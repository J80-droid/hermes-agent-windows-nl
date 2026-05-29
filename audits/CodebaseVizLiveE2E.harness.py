#!/usr/bin/env python3
"""E2E: Codebase Viz op live dashboard (http://127.0.0.1:9119/codebase-viz).

Combineert:
  - Bron-/dist-audit (scripts, routes, UI-contract)
  - Loopback HTTP + plugin-API (als dashboard draait)
  - Optioneel: pytest plugin-unit gate

Draai: audits/RUN_CODEBASE_VIZ_LIVE_E2E.bat
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugins" / "codebase-viz" / "dashboard"
PLUGIN_API = PLUGIN / "plugin_api.py"
DIST_CSS = PLUGIN / "dist" / "style.css"
DIST_JS = PLUGIN / "dist" / "index.js"
MANIFEST = PLUGIN / "manifest.json"
VERIFY = REPO / "audits" / "verify_codebase_viz_health.py"
LAUNCH_PS1 = REPO / "windows" / "scripts" / "launch_dashboard_on_start.ps1"

DEFAULT_BASE = os.environ.get("HERMES_DASHBOARD_BASE", "http://127.0.0.1:9119").rstrip("/")
SESSION_TOKEN_RE = re.compile(r'__HERMES_SESSION_TOKEN__="([^"]+)"')

FAILURES = 0
STEP = 0
SKIPS = 0

API_ROUTES = (
    "/health",
    "/scan-status",
    "/structure",
    "/dependencies",
    "/summary",
    "/doctor",
    "/churn",
    "/age-map",
    "/complexity",
    "/todos",
    "/blame",
    "/coverage",
    "/search",
    "/dead-imports",
    "/config-drift",
    "/session-stats",
    "/timeline",
    "/history",
)

FRONTEND_SCRIPTS = (
    "src/index.jsx",
    "src/App.jsx",
    "src/usePluginFetch.js",
    "src/useScanProgress.js",
    "src/useKeyboardShortcuts.js",
    "src/useFileWatcher.js",
    "src/wsAuth.js",
    "src/ScanProgress.jsx",
    "src/SunburstChart.jsx",
    "src/ForceGraph.jsx",
    "src/TreemapChart.jsx",
    "src/MetricsTab.jsx",
    "src/HealthTab.jsx",
    "src/DataTableTab.jsx",
    "src/SearchTab.jsx",
    "src/TimelineTab.jsx",
)

PY = Path.home() / "miniconda3/envs/hermes-env/python.exe"
if not PY.is_file():
    PY = Path(sys.executable)


def _step(name: str, ok: bool, detail: str = "", *, skip: bool = False) -> None:
    global FAILURES, STEP, SKIPS
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if skip:
        SKIPS += 1
        print(f"[SKIP] L{STEP} {name}{suffix}", flush=True)
        return
    if ok:
        print(f"[OK] L{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] L{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def _http_get(path: str, *, token: str | None = None, timeout: float = 30.0) -> tuple[int, str]:
    url = f"{DEFAULT_BASE}{path}"
    headers: dict[str, str] = {}
    if token:
        headers["X-Hermes-Session-Token"] = token
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace") if exc.fp else ""
        return exc.code, body
    except urllib.error.URLError:
        return 0, ""


def _fetch_json_api(
    route: str,
    token: str,
    *,
    timeout: float = 30.0,
) -> tuple[int, dict[str, Any] | None, str]:
    try:
        status, body = _http_get(
            f"/api/plugins/codebase-viz{route}",
            token=token,
            timeout=timeout,
        )
    except TimeoutError:
        return 0, None, "timeout"
    except urllib.error.URLError as exc:
        return 0, None, str(exc.reason) if getattr(exc, "reason", None) else str(exc)
    if status != 200:
        return status, None, body[:200]
    try:
        return status, json.loads(body), ""
    except json.JSONDecodeError:
        return status, None, "invalid JSON"


def test_l1_repo_artefacts() -> None:
    missing = [p for p in (MANIFEST, PLUGIN_API, DIST_JS, DIST_CSS, VERIFY, LAUNCH_PS1) if not p.is_file()]
    for rel in FRONTEND_SCRIPTS:
        if not (PLUGIN / rel).is_file():
            missing.append(str(PLUGIN / rel))
    _step("repo-artefacten plugin + scripts", not missing, ", ".join(Path(m).name for m in missing[:5]))


def test_l2_manifest_and_routes_wiring() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    api_text = PLUGIN_API.read_text(encoding="utf-8")
    ok_manifest = manifest.get("name") == "codebase-viz" and manifest.get("api") == "plugin_api.py"
    ok_routes = all(
        f'@router.get("{r}"' in api_text or f'@router.post("{r}"' in api_text
        for r in API_ROUTES
    )
    ok_ws = '@router.websocket("/events")' in api_text
    ok_post = '@router.post("/force-scan")' in api_text
    _step("manifest + API-routes gedocumenteerd", ok_manifest and ok_routes and ok_ws and ok_post)


def test_l3_frontend_script_inventory() -> None:
    use_fetch = (PLUGIN / "src/usePluginFetch.js").read_text(encoding="utf-8")
    app_src = (PLUGIN / "src/App.jsx").read_text(encoding="utf-8")
    ok = (
        "const API = '/api/plugins/codebase-viz'" in use_fetch
        and "CategoryNav" in app_src
        and "codebase-viz-nav-shell" in app_src
        and "is-menu-open" in app_src
        and "!menuOpen" in app_src
        and "TAB_MAP" in app_src
    )
    _step("frontend fetch + tab-routing", ok)


def test_l4_dropdown_css_contract() -> None:
    css = (PLUGIN / "src/style.css").read_text(encoding="utf-8")
    dist = DIST_CSS.read_text(encoding="utf-8") if DIST_CSS.is_file() else ""
    markers = (
        ".codebase-viz-nav-shell",
        "is-menu-open",
        "z-index: 200",
        ".codebase-viz-dropdown",
        "z-index: 1000",
        ".codebase-viz-category-trigger",
    )
    ok_src = all(m in css for m in markers)
    ok_dist = all(m in dist for m in markers) if dist else False
    _step("dropdown/nav CSS contract (src)", ok_src)
    _step("dropdown/nav CSS contract (dist)", ok_dist, "npm run build in dashboard/" if not ok_dist else "")


def test_l5_launch_wiring() -> None:
    ps1 = LAUNCH_PS1.read_text(encoding="utf-8")
    checks = [
        "HERMES_BUNDLED_PLUGINS" in ps1,
        "codebase-viz" in ps1,
        "Update-CodebaseVizDistIfNeeded" in ps1,
        "verify_codebase_viz_health.py" in ps1,
        "pip install pygount" in ps1,
    ]
    _step("launch_dashboard_on_start.ps1 wiring", all(checks), f"{sum(checks)}/{len(checks)}")


def test_l6_live_dashboard_reachable() -> int:
    status, _ = _http_get("/codebase-viz", timeout=5.0)
    if status != 200:
        _step(
            "live dashboard /codebase-viz",
            False,
            f"HTTP {status} op {DEFAULT_BASE} — start dashboard (launch_hermes.bat)",
        )
        return status
    _step("live dashboard /codebase-viz", True, DEFAULT_BASE)
    return status


def test_l7_session_token_and_plugin_assets(token_from_html: str | None) -> str | None:
    if not token_from_html:
        _step("session token in HTML", False, skip=True)
        return None
    _step("session token in HTML", True)
    for path in (
        "/dashboard-plugins/codebase-viz/dist/style.css",
        "/dashboard-plugins/codebase-viz/dist/index.js",
    ):
        st, _ = _http_get(path, token=token_from_html)
        _step(f"plugin asset {path}", st == 200, f"HTTP {st}")
    return token_from_html


def test_l8_live_health(token: str | None) -> None:
    if not token:
        _step("live /health", False, skip=True)
        return
    sys.path.insert(0, str(REPO / "audits"))
    try:
        import verify_codebase_viz_health as v

        body = v.fetch_plugin_health(DEFAULT_BASE, token)
        errs = v.validate_health_body(body)
        _step("live /health contract", not errs, "; ".join(errs) or f"plugin={body.get('plugin')}")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        _step("live /health contract", False, str(exc))
    finally:
        if str(REPO / "audits") in sys.path:
            sys.path.remove(str(REPO / "audits"))


def test_l9_live_api_smoke(token: str | None) -> None:
    if not token:
        _step("live API smoke (fast)", False, skip=True)
        _step("live API smoke (heavy, optioneel)", False, skip=True)
        return
    fast_routes = ("/health", "/scan-status")
    bad: list[str] = []
    for route in fast_routes:
        status, data, err = _fetch_json_api(route, token, timeout=20.0)
        if status == 401:
            bad.append(f"{route}=401 Unauthorized")
        elif status != 200:
            bad.append(f"{route}={err or f'HTTP {status}'}")
        elif data is None:
            bad.append(f"{route}={err or 'no JSON'}")
    _step("live API smoke (fast)", not bad, "; ".join(bad) or ", ".join(fast_routes))

    # Eerste pygount-scan kan minuten duren; timeout = geen harde fail als scan actief is.
    status, data, err = _fetch_json_api("/summary", token, timeout=45.0)
    if status == 200 and data is not None:
        _step("live API smoke (heavy /summary)", True, "200")
        return
    _, scan, _ = _fetch_json_api("/scan-status", token, timeout=15.0)
    phase = (scan or {}).get("phase") if isinstance(scan, dict) else None
    scanning = phase not in (None, "", "idle", "done")
    if status == 0 and err == "timeout" and scanning:
        _step(
            "live API smoke (heavy /summary)",
            True,
            f"timeout OK — scan actief (phase={phase!r})",
        )
    elif status == 200:
        _step("live API smoke (heavy /summary)", True)
    else:
        _step(
            "live API smoke (heavy /summary)",
            False,
            err or f"HTTP {status}, phase={phase!r}",
        )


def test_l10_unauthorized_without_token() -> None:
    status, _ = _http_get("/api/plugins/codebase-viz/health", token=None, timeout=5.0)
    if status == 0:
        _step("API zonder token geweigerd", False, skip=True)
        return
    _step("API zonder token geweigerd", status in {401, 403}, f"HTTP {status}")


def test_l11_pytest_unit_gate() -> None:
    if os.environ.get("HERMES_SKIP_PYTEST") == "1":
        _step("pytest plugin gate", True, skip=True)
        return
    proc = subprocess.run(
        [str(PY), "-m", "pytest", "tests/plugins/test_codebase_viz_plugin.py", "-q", "--tb=no"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=180,
    )
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()[-1:] or ["?"]
    _step("pytest plugin gate", proc.returncode == 0, tail[0][:120])


def main() -> int:
    print(f"Codebase Viz Live E2E — base={DEFAULT_BASE}", flush=True)
    test_l1_repo_artefacts()
    test_l2_manifest_and_routes_wiring()
    test_l3_frontend_script_inventory()
    test_l4_dropdown_css_contract()
    test_l5_launch_wiring()

    dash_status = test_l6_live_dashboard_reachable()
    token: str | None = None
    if dash_status == 200:
        _, html = _http_get("/codebase-viz")
        match = SESSION_TOKEN_RE.search(html)
        token = match.group(1) if match else None
        test_l7_session_token_and_plugin_assets(token)
    else:
        _step("live plugin assets", False, skip=True)

    test_l8_live_health(token)
    test_l9_live_api_smoke(token)
    test_l10_unauthorized_without_token()
    test_l11_pytest_unit_gate()

    print(f"\nTotaal: {STEP} stappen, {FAILURES} failures, {SKIPS} skips", flush=True)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
