#!/usr/bin/env python3
"""E2E: Codebase Viz pygount disk-cache + pre-warm (geen volledige repo-scan).

Scenario's:
  - Wiring: warm script, launch PS1 Ensure-CodebaseVizPygountCache, skip-lijst, timeout 600
  - Disk-cache: atomic write, repo_revision, backups skip
  - Functioneel: tiny-repo warm roundtrip + --check-only exit codes
  - Unit gate: pytest subset pygount cache

Draai: audits/RUN_CODEBASE_VIZ_PYGOUNT_CACHE_E2E.bat
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FAILURES = 0
STEP = 0

WARM_SCRIPT = REPO / "scripts" / "warm_codebase_viz_pygount_cache.py"
PLUGIN_API = REPO / "plugins" / "codebase-viz" / "dashboard" / "plugin_api.py"
PS1 = REPO / "windows" / "scripts" / "launch_dashboard_on_start.ps1"
VERIFY = REPO / "audits" / "verify_codebase_viz_health.py"

PY = Path.home() / "miniconda3/envs/hermes-env/python.exe"


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] W{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] W{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def _python_exe() -> Path:
    if PY.is_file():
        return PY
    return Path(sys.executable)


def _load_plugin_module(repo_path: Path, cache_path: Path):
    os.environ["CODEBASE_VIZ_REPO"] = str(repo_path)
    os.environ["CODEBASE_VIZ_PYGOUNT_CACHE_PATH"] = str(cache_path)
    os.environ["CODEBASE_VIZ_PYGOUNT_DISK_CACHE"] = "1"
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    spec = importlib.util.spec_from_file_location("cv_pygount_e2e_plugin", PLUGIN_API)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_tiny_repo(root: Path) -> Path:
    (root / ".git").mkdir()
    (root / "pkg").mkdir()
    (root / "pkg" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (root / "backups").mkdir()
    (root / "backups" / "old.py").write_text("# skip\n", encoding="utf-8")
    disabled = root / ".venv.disabled-test"
    disabled.mkdir()
    (disabled / "lib.py").write_text("y = 2\n", encoding="utf-8")
    cache_dir = root / "output" / "research"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return root


def test_w1_warm_script_contract() -> None:
    text = WARM_SCRIPT.read_text(encoding="utf-8")
    ok = (
        WARM_SCRIPT.is_file()
        and "--check-only" in text
        and "--force" in text
        and "_try_install_bundled_seed" in text
        and ("return 2" in text or "exit 2" in text.lower())
    )
    _step("warm_codebase_viz_pygount_cache.py contract", ok)


def test_w2_plugin_skip_and_revision() -> None:
    text = PLUGIN_API.read_text(encoding="utf-8")
    checks = [
        "backups" in text and ".venv.disabled*" in text,
        "_SCAN_SKIP_DIR_NAMES" in text,
        "_path_has_skipped_dir" in text,
        "_repo_cache_revision" in text,
        "_disk_cache_revision_matches" in text,
        "_git_head_revision" in text,
        ".tmp" in text and "tmp_path.replace(path)" in text,
        "FileNotFoundError" in text,
    ]
    _step("plugin_api skip + disk-cache + atomic write", all(checks), f"{sum(checks)}/{len(checks)}")


def test_w3_launch_ps1_prewarm_wiring() -> None:
    ps1 = PS1.read_text(encoding="utf-8")
    checks = [
        "Ensure-CodebaseVizPygountCache" in ps1,
        "warm_codebase_viz_pygount_cache.py" in ps1,
        "'600'" in ps1 or '"600"' in ps1,
        "CODEBASE_VIZ_REPO" in ps1,
        "HERMES_CODEBASE_VIZ_PREGOUNT_CACHE" in ps1,
        "schijfcache actueel" in ps1,
    ]
    _step("launch PS1 pre-warm wiring", all(checks), f"{sum(checks)}/{len(checks)}")


def test_w4_verify_default_timeout_600() -> None:
    saved = os.environ.pop("CODEBASE_VIZ_PYGOUNT_TIMEOUT", None)
    sys.path.insert(0, str(REPO / "audits"))
    try:
        if "verify_codebase_viz_health" in sys.modules:
            del sys.modules["verify_codebase_viz_health"]
        import verify_codebase_viz_health as v

        ok = (
            v.INSTITUTIONAL_DEFAULT_PYGOUNT_TIMEOUT_SEC == 600
            and v.expected_pygount_timeout_sec() == 600
            and v.validate_health_body({"pygount_timeout_sec": 600, "plugin": "codebase-viz"}) == []
            and v.validate_health_body({"pygount_timeout_sec": 240, "plugin": "codebase-viz"}) != []
        )
        _step("verify_codebase_viz_health default 600", ok)
    finally:
        sys.path.pop(0)
        if saved is not None:
            os.environ["CODEBASE_VIZ_PYGOUNT_TIMEOUT"] = saved


def test_w5_scan_skip_backups_and_disabled_venv() -> None:
    with tempfile.TemporaryDirectory() as td:
        repo = _make_tiny_repo(Path(td))
        cache = repo / "output" / "research" / "codebase_viz_pygount_cache.json"
        mod = _load_plugin_module(repo, cache)
        names = {p.name for p in mod._safe_repo_file_iter(repo)}
        ok = "a.py" in names and "old.py" not in names and "lib.py" not in names
        _step("skip backups + .venv.disabled*", ok, f"seen={sorted(names)}")


def test_w6_disk_cache_write_read_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as td:
        repo = _make_tiny_repo(Path(td))
        cache = repo / "output" / "research" / "codebase_viz_pygount_cache.json"
        mod = _load_plugin_module(repo, cache)
        bundle = {
            "summary": {"total_files": 1, "total_code": 1, "languages": {}},
            "file_rows": [{"path": "pkg/a.py", "language": "Python", "code": 1}],
        }
        mod._write_pygount_disk_cache(bundle)
        loaded = mod._read_pygount_disk_cache(allow_stale=False)
        ok = (
            cache.is_file()
            and loaded is not None
            and loaded["file_rows"][0]["path"] == "pkg/a.py"
        )
        _step("disk cache write/read roundtrip", ok)


def test_w7_warm_script_check_only_and_force() -> None:
    if not WARM_SCRIPT.is_file():
        _step("warm script tiny-repo roundtrip", False, "script ontbreekt")
        return
    py = _python_exe()
    with tempfile.TemporaryDirectory() as td:
        repo = _make_tiny_repo(Path(td))
        cache = repo / "output" / "research" / "codebase_viz_pygount_cache.json"
        base_env = {
            **os.environ,
            "CODEBASE_VIZ_REPO": str(repo),
            "CODEBASE_VIZ_PYGOUNT_CACHE_PATH": str(cache),
            "CODEBASE_VIZ_PYGOUNT_DISK_CACHE": "1",
            "CODEBASE_VIZ_PYGOUNT_TIMEOUT": "120",
        }
        before = subprocess.run(
            [str(py), str(WARM_SCRIPT), "--check-only"],
            cwd=str(REPO),
            env=base_env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        warm = subprocess.run(
            [str(py), str(WARM_SCRIPT), "--force"],
            cwd=str(REPO),
            env=base_env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        after = subprocess.run(
            [str(py), str(WARM_SCRIPT), "--check-only"],
            cwd=str(REPO),
            env=base_env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        ok = (
            before.returncode == 2
            and warm.returncode == 0
            and after.returncode == 0
            and cache.is_file()
            and cache.stat().st_size > 100
        )
        detail = (
            f"before={before.returncode} warm={warm.returncode} after={after.returncode} "
            f"bytes={cache.stat().st_size if cache.is_file() else 0}"
        )
        if not ok and warm.stderr:
            detail += f" err={warm.stderr.strip()[:120]}"
        _step("warm script check-only + force roundtrip", ok, detail)


def test_w8_pytest_pygount_cache_unit_gate() -> None:
    py = _python_exe()
    proc = subprocess.run(
        [
            str(py),
            "-m",
            "pytest",
            "tests/plugins/test_codebase_viz_plugin.py",
            "-q",
            "--tb=line",
            "-k",
            "pygount_disk or warm_pygount or scan_skip_backups",
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=180,
    )
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    detail = tail[-1] if tail else f"exit={proc.returncode}"
    _step("pytest pygount-cache unit gate", proc.returncode == 0, detail)


def main() -> int:
    print("=" * 60, flush=True)
    print("  Codebase Viz pygount disk-cache E2E", flush=True)
    print("=" * 60, flush=True)
    print(flush=True)

    test_w1_warm_script_contract()
    test_w2_plugin_skip_and_revision()
    test_w3_launch_ps1_prewarm_wiring()
    test_w4_verify_default_timeout_600()
    test_w5_scan_skip_backups_and_disabled_venv()
    test_w6_disk_cache_write_read_roundtrip()
    test_w7_warm_script_check_only_and_force()
    test_w8_pytest_pygount_cache_unit_gate()

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
