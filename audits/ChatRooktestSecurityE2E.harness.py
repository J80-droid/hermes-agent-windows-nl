#!/usr/bin/env python3
"""E2E harness: chat rooktest overlay, config rebind, auth BOM, security pins (no live API).

Scenario matrix:
  E1  run_hermes_cli_with_overlay.py imports overlay (subprocess --help)
  E2  runtime_provider.load_config === patched load_config after bootstrap
  E3  profile inherits root providers.venice (isolated legal profile)
  E4  auth BOM auto-repair on _load_auth_store
  E5  repair_all_auth_json_bom scans profile auth files
  E6  inference_available with isolated VENICE_API_KEY (no chat subprocess)
  E7  overlay/requirements-security-pins.txt declares PyNaCl + setuptools<82
  E8  corrupt auth.json → empty store + .json.corrupt backup
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

FAILURES = 0
STEP = 0


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" — {detail}" if detail else ""
    if ok:
        print(f"[OK] E{STEP} {name}{suffix}")
    else:
        print(f"[FAIL] E{STEP} {name}{suffix}", file=sys.stderr)
        FAILURES += 1


@contextmanager
def _isolated_profile_tree() -> Iterator[Path]:
    import hermes_cli.profile_model_inheritance as pmi

    with tempfile.TemporaryDirectory(prefix="hermes_crs_e2e_") as tmp:
        root = Path(tmp) / "hermes"
        legal = root / "profiles" / "legal"
        legal.mkdir(parents=True)
        (root / "config.yaml").write_text(
            yaml.safe_dump(
                {
                    "model": {"default": "deepseek-v4-pro", "provider": "venice"},
                    "providers": {
                        "venice": {
                            "base_url": "https://api.venice.ai/api/v1",
                            "api_key_env": "VENICE_API_KEY",
                        }
                    },
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        (legal / "config.yaml").write_text("{}", encoding="utf-8")
        (legal / ".env").write_text("VENICE_API_KEY=sk-rooktest-e2e-key\n", encoding="utf-8")
        os.environ["HERMES_HOME"] = str(legal)
        os.environ["HERMES_WIN_PREFER_LOCALAPPDATA"] = "0"
        import hermes_constants

        hermes_constants._DEFAULT_ROOT_CACHE = None  # type: ignore[attr-defined]
        pmi.bust_config_caches(root)
        yield legal


def test_e1_overlay_entry_subprocess() -> None:
    script = REPO_ROOT / "scripts" / "run_hermes_cli_with_overlay.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=90,
    )
    blob = (proc.stdout or "") + (proc.stderr or "")
    ok = "No module named 'overlay'" not in blob
    _step("overlay_entry_subprocess", ok, blob.strip()[:160] if not ok else "")


def test_e2_runtime_provider_config_rebind() -> None:
    from overlay.bootstrap import install

    install()
    from hermes_cli import config, runtime_provider

    ok = config.load_config is runtime_provider.load_config
    _step("runtime_provider_config_rebind", ok)


def test_e3_profile_inherits_venice() -> None:
    from overlay.bootstrap import install

    install()
    with _isolated_profile_tree():
        from hermes_cli.config import load_config

        cfg = load_config()
        providers = cfg.get("providers") or {}
        model = cfg.get("model") if isinstance(cfg.get("model"), dict) else {}
        ok = "venice" in providers and model.get("provider") == "venice"
    _step("profile_inherits_venice", ok)


def test_e4_bom_auto_repair() -> None:
    from overlay.bootstrap import install
    from overlay.hermes_cli.auth_fork_patch import _load_auth_store_bom_safe

    install()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "auth.json"
        path.write_bytes(
            b"\xef\xbb\xbf"
            + b'{"version": 1, "active_provider": "venice", "providers": {}}'
        )
        store = _load_auth_store_bom_safe(path)
        ok = (
            store.get("active_provider") == "venice"
            and not path.read_bytes().startswith(b"\xef\xbb\xbf")
        )
    _step("auth_bom_auto_repair", ok)


def test_e5_repair_all_scans_profiles() -> None:
    from overlay.bootstrap import install
    from hermes_cli.auth import repair_all_auth_json_bom

    install()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "hermes"
        prof = root / "profiles" / "legal"
        prof.mkdir(parents=True)
        auth = prof / "auth.json"
        auth.write_bytes(b"\xef\xbb\xbf" + b'{"active_provider": "nous"}')
        os.environ["HERMES_HOME"] = str(prof)
        os.environ["HERMES_WIN_PREFER_LOCALAPPDATA"] = "0"
        repaired = repair_all_auth_json_bom()
        ok = any("legal" in p.replace("\\", "/") for p in repaired)
    _step("repair_all_profile_auth", ok)


def test_e6_inference_available_isolated() -> None:
    from overlay.bootstrap import install
    from scripts.rag_pipeline import _rooktest_chat as rook

    install()
    with _isolated_profile_tree():
        ok = rook.inference_available("legal")
    _step("inference_available_venice_key", ok)


def test_e7_security_pins_file() -> None:
    pins = REPO_ROOT / "overlay" / "requirements-security-pins.txt"
    text = pins.read_text(encoding="utf-8") if pins.is_file() else ""
    ok = "PyNaCl==1.6.2" in text and "setuptools" in text and "<82" in text
    _step("security_pins_manifest", ok)


def test_e8_corrupt_auth_backup() -> None:
    from overlay.bootstrap import install
    from overlay.hermes_cli.auth_fork_patch import _load_auth_store_bom_safe

    install()
    os.environ["HERMES_SUPPRESS_AUTH_CORRUPT_LOG"] = "1"
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "auth.json"
            path.write_text("{not-json", encoding="utf-8")
            store = _load_auth_store_bom_safe(path)
            corrupt = path.with_suffix(".json.corrupt")
            ok = store.get("providers") == {} and corrupt.is_file()
    finally:
        os.environ.pop("HERMES_SUPPRESS_AUTH_CORRUPT_LOG", None)
    _step("corrupt_auth_backup", ok)


def main() -> int:
    test_e1_overlay_entry_subprocess()
    test_e2_runtime_provider_config_rebind()
    test_e3_profile_inherits_venice()
    test_e4_bom_auto_repair()
    test_e5_repair_all_scans_profiles()
    test_e6_inference_available_isolated()
    test_e7_security_pins_file()
    test_e8_corrupt_auth_backup()
    if FAILURES:
        print(f"\nChatRooktestSecurityE2E: {FAILURES} failure(s)", file=sys.stderr)
        return 1
    print("\nChatRooktestSecurityE2E: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
