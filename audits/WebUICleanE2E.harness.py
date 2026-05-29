#!/usr/bin/env python3
"""E2E: schone Web UI (build, lint, channel-contract, hooks, team-display import).

Valideert de recente web-frontend hardening zonder live dashboard op 9119.
Draai: audits/RUN_WEB_UI_CLEAN_E2E.bat
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WEB = REPO / "web"
FAILURES = 0
STEP = 0

CHANNEL_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
APPLY_SCRIPT = REPO / "windows/scripts/apply_team_display_profiles.py"


def _audit_python() -> str:
    env_py = os.environ.get("HERMES_AUDIT_PYTHON", "").strip()
    if env_py and Path(env_py).is_file():
        return env_py
    conda = Path.home() / "miniconda3/envs/hermes-env/python.exe"
    if conda.is_file():
        return str(conda)
    return sys.executable


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] W{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] W{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8", errors="replace")


def test_w1_repo_artefacts() -> None:
    paths = [
        WEB / "src/hooks/useTooltipAnchor.ts",
        WEB / "src/hooks/useDropUpFixedStyle.ts",
        WEB / "src/components/gatewayLine.ts",
        WEB / "src/i18n/i18n-context.ts",
        WEB / "src/i18n/useI18n.ts",
        WEB / "src/themes/theme-context.ts",
        WEB / "src/themes/useTheme.ts",
        WEB / "src/lib/institutionalMarkdown.ts",
    ]
    ok = all(p.is_file() for p in paths)
    _step("repo-artefacten (hooks + context splits)", ok, f"{sum(p.is_file() for p in paths)}/{len(paths)}")


def test_w2_chat_channel_contract() -> None:
    src = _read("web/src/pages/ChatPage.tsx")
    has_valid_pattern = "resume-${resumeParam}" in src or "resume-`${resumeParam}`" in src
    has_invalid_colon = "resume:${resumeParam}" in src or "resume:${resumeParam}" in src
    sample_ok = bool(CHANNEL_RE.match("resume-test-session-id-01"))
    ok = has_valid_pattern and not has_invalid_colon and sample_ok
    _step("ChatPage PTY channel (geen dubbele-punt)", ok)


def test_w3_institutional_markdown_param() -> None:
    src = _read("web/src/lib/institutionalMarkdown.ts")
    ok = "_headingLine:" in src and "function shouldAttemptPseudoNormalize" in src
    bad = re.search(r"function shouldAttemptPseudoNormalize\(\s*headingLine:", src) is not None
    _step("institutionalMarkdown ongebruikte param", ok and not bad)


def test_w4_npm_lint() -> None:
    npm = shutil.which("npm")
    if not npm:
        _step("npm run lint", False, "npm niet op PATH")
        return
    proc = subprocess.run(
        [npm, "run", "lint"],
        cwd=str(WEB),
        capture_output=True,
        text=True,
        timeout=180,
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == 0 and "error" not in combined.lower().split("✖")[-1:] if "✖" in combined else proc.returncode == 0
    ok = proc.returncode == 0
    tail = combined.strip().splitlines()[-1] if combined.strip() else f"exit={proc.returncode}"
    _step("npm run lint (0 errors)", ok, tail[:120])


def test_w5_npm_build() -> None:
    npm = shutil.which("npm")
    if not npm:
        _step("npm run build", False, "npm niet op PATH")
        return
    proc = subprocess.run(
        [npm, "run", "build"],
        cwd=str(WEB),
        capture_output=True,
        text=True,
        timeout=300,
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == 0 and "error TS" not in combined
    detail = "built" if ok else (combined.strip().splitlines()[-1][:120] if combined.strip() else f"exit={proc.returncode}")
    _step("npm run build (tsc + vite)", ok, detail)


def test_w6_web_dist_output() -> None:
    dist = REPO / "hermes_cli/web_dist/index.html"
    manifest = REPO / "hermes_cli/web_dist/.vite/manifest.json"
    ok = dist.is_file() and (manifest.is_file() or (REPO / "hermes_cli/web_dist/assets").is_dir())
    _step("hermes_cli/web_dist aanwezig", ok, str(dist.parent))


def test_w7_apply_team_display_import() -> None:
    src = APPLY_SCRIPT.read_text(encoding="utf-8")
    ok = "sys.path.insert" in src and "from utils import atomic_yaml_write" in src
    py = _audit_python()
    proc = subprocess.run(
        [py, str(APPLY_SCRIPT), "--check-drift"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    # drift may be 1 on real machines; import/startup must not traceback
    no_trace = "ModuleNotFoundError" not in (proc.stdout or "") + (proc.stderr or "")
    ok = ok and no_trace and proc.returncode in (0, 1)
    _step("apply_team_display_profiles utils-import", ok, f"exit={proc.returncode}")


def test_w8_pytest_web_ui_build() -> None:
    py = _audit_python()
    proc = subprocess.run(
        [py, "-m", "pytest", "tests/hermes_cli/test_web_ui_build.py", "-q", "--tb=short"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=120,
    )
    ok = proc.returncode == 0
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    _step("pytest test_web_ui_build", ok, tail[-1] if tail else f"exit={proc.returncode}")


def test_w9_pytest_apply_team_display() -> None:
    py = _audit_python()
    proc = subprocess.run(
        [py, "-m", "pytest", "tests/windows/test_apply_team_display_root.py", "-q", "--tb=short"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=120,
    )
    ok = proc.returncode == 0
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    _step("pytest test_apply_team_display_root", ok, tail[-1] if tail else f"exit={proc.returncode}")


def test_w10_plugin_page_dynamic_render() -> None:
    src = _read("web/src/plugins/PluginPage.tsx")
    ok = "createElement" in src and "useSyncExternalStore" in src
    _step("PluginPage createElement + external store", ok)


def test_w11_oauth_fetch_lifecycle() -> None:
    src = _read("web/src/components/OAuthProvidersCard.tsx")
    ok = "let active = true" in src and "fetchProviders" in src
    _step("OAuthProvidersCard unmount guard", ok)


def main() -> int:
    print("=" * 60, flush=True)
    print("  Web UI clean codebase E2E - Audit", flush=True)
    print("=" * 60, flush=True)
    print(flush=True)

    test_w1_repo_artefacts()
    test_w2_chat_channel_contract()
    test_w3_institutional_markdown_param()
    test_w4_npm_lint()
    test_w5_npm_build()
    test_w6_web_dist_output()
    test_w7_apply_team_display_import()
    test_w8_pytest_web_ui_build()
    test_w9_pytest_apply_team_display()
    test_w10_plugin_page_dynamic_render()
    test_w11_oauth_fetch_lifecycle()

    print(flush=True)
    print("=" * 60, flush=True)
    if FAILURES == 0:
        print(f"  ALL PASS ({STEP}/{STEP})", flush=True)
    else:
        print(f"  FAILURES: {FAILURES}/{STEP}", file=sys.stderr, flush=True)
    print("=" * 60, flush=True)
    return 1 if FAILURES > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
