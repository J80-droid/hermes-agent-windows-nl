"""Verify codebase-viz /health after dashboard start (uses session token from HTML)."""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE = "http://127.0.0.1:9119"
SESSION_TOKEN_RE = re.compile(r'__HERMES_SESSION_TOKEN__="([^"]+)"')
INSTITUTIONAL_DEFAULT_PYGOUNT_TIMEOUT_SEC = 240


def expected_pygount_timeout_sec() -> int:
    raw = os.environ.get("CODEBASE_VIZ_PYGOUNT_TIMEOUT", "").strip()
    if raw.isdigit():
        return int(raw)
    return INSTITUTIONAL_DEFAULT_PYGOUNT_TIMEOUT_SEC


def extract_session_token(html: str) -> str | None:
    match = SESSION_TOKEN_RE.search(html or "")
    return match.group(1) if match else None


def fetch_plugin_health(
    base: str,
    token: str,
    *,
    timeout: float = 10.0,
) -> dict[str, Any]:
    url = f"{base.rstrip('/')}/api/plugins/codebase-viz/health"
    req = urllib.request.Request(
        url,
        headers={"X-Hermes-Session-Token": token},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise urllib.error.HTTPError(url, resp.status, resp.reason, resp.headers, None)
        return json.loads(resp.read().decode())


def validate_health_body(body: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = expected_pygount_timeout_sec()
    if body.get("pygount_timeout_sec") != expected:
        errors.append(
            f"pygount_timeout_sec={body.get('pygount_timeout_sec')!r}, "
            f"verwacht {expected}",
        )
    if not body.get("plugin"):
        errors.append("ontbrekend veld: plugin")
    return errors


def main() -> int:
    base = DEFAULT_BASE
    try:
        html = urllib.request.urlopen(f"{base}/codebase-viz", timeout=10).read().decode(
            "utf-8", "replace",
        )
    except urllib.error.URLError as exc:
        print(f"Dashboard niet bereikbaar op {base}: {exc}")
        return 1

    token = extract_session_token(html)
    if not token:
        print("Geen session token in dashboard HTML")
        return 1

    try:
        body = fetch_plugin_health(base, token)
    except urllib.error.HTTPError as exc:
        print(f"/health HTTP {exc.code}: {exc.reason}")
        return 1
    except urllib.error.URLError as exc:
        print(f"/health mislukt: {exc}")
        return 1
    except json.JSONDecodeError as exc:
        print(f"/health geen JSON: {exc}")
        return 1

    print(f"version={body.get('version')}")
    print(f"pygount_timeout_sec={body.get('pygount_timeout_sec')}")
    print(f"plugin_api_path={body.get('plugin_api_path', '')}")

    errors = validate_health_body(body)
    if errors:
        for err in errors:
            print(err)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
