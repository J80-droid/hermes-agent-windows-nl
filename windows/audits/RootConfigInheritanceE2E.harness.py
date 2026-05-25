#!/usr/bin/env python3
"""Isolated harness for root config inheritance E2E (profiel → root overerving)."""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FAILURES = 0


def step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES
    suffix = f" — {detail}" if detail else ""
    if ok:
        print(f"[OK] {name}{suffix}")
    else:
        print(f"[FAIL] {name}{suffix}", file=sys.stderr)
        FAILURES += 1


def _tree(base: Path) -> tuple[Path, Path]:
    root = base / "hermes_root"
    prof = root / "profiles" / "core_e2e"
    prof.mkdir(parents=True, exist_ok=True)
    return root, prof


def _env_for(root: Path, prof: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["HERMES_HOME"] = str(prof)
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


def test_root_config_path_ignores_profile_home(base: Path) -> None:
    root, prof = _tree(base)
    os.environ["HERMES_HOME"] = str(prof)
    with mock.patch("hermes_constants.get_default_hermes_root", return_value=root):
        from hermes_cli.profile_model_inheritance import root_config_path

        ok = root_config_path() == root / "config.yaml"
    step("root_config_path negeert profiel HERMES_HOME", ok, str(root / "config.yaml"))


def test_collect_env_sync_reads_root_only(base: Path) -> None:
    root, prof = _tree(base)
    (root / "config.yaml").write_text(
        "providers:\n  venice:\n    api_key_env: VENICE_API_KEY\n",
        encoding="utf-8",
    )
    (prof / "config.yaml").write_text("agent:\n  max_turns: 3\n", encoding="utf-8")
    script = REPO_ROOT / "windows" / "scripts" / "collect_env_sync_keys.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        env=_env_for(root, prof),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=False,
    )
    ok = proc.returncode == 0 and "VENICE_API_KEY" in proc.stdout
    detail = (proc.stdout or proc.stderr).strip().replace("\n", " ")[:120]
    step("collect_env_sync_keys leest root config", ok, detail or f"exit={proc.returncode}")


def test_merge_legacy_targets_root_when_profile_home(base: Path) -> None:
    root, prof = _tree(base)
    (root / "config.yaml").write_text("agent:\n  max_turns: 1\n", encoding="utf-8")
    legacy = base / "legacy"
    legacy.mkdir()
    (legacy / "config.yaml").write_text(
        "providers:\n  venice:\n    base_url: https://api.venice.ai/api/v1\n    api_key_env: VENICE_API_KEY\n",
        encoding="utf-8",
    )
    script = REPO_ROOT / "windows" / "scripts" / "merge_legacy_providers_config.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--legacy", str(legacy / "config.yaml")],
        env=_env_for(root, prof),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=False,
    )
    root_text = (root / "config.yaml").read_text(encoding="utf-8")
    prof_cfg = prof / "config.yaml"
    prof_text = prof_cfg.read_text(encoding="utf-8") if prof_cfg.is_file() else ""
    ok = proc.returncode == 0 and "venice" in root_text and "venice" not in prof_text
    detail = proc.stderr.strip() or proc.stdout.strip() or f"exit={proc.returncode}"
    step("merge_legacy → root bij HERMES_HOME=profiel", ok, detail[:200])


def test_bust_root_caches_invalidates_profile_load(base: Path) -> None:
    root, prof = _tree(base)
    (root / "config.yaml").write_text(
        "model:\n  provider: gemini\n  default: v1\n",
        encoding="utf-8",
    )
    (prof / "config.yaml").write_text("agent:\n  max_turns: 5\n", encoding="utf-8")

    from hermes_cli import config as cfg_mod
    from hermes_cli.profile_model_inheritance import bust_config_caches, root_config_path

    cfg_mod._LOAD_CONFIG_CACHE.clear()
    cfg_mod._RAW_CONFIG_CACHE.clear()

    with mock.patch.dict(os.environ, {"HERMES_HOME": str(prof)}):
        with mock.patch("hermes_constants.get_default_hermes_root", return_value=root):
            with mock.patch("hermes_cli.config.ensure_hermes_home", lambda: None):
                with mock.patch("hermes_cli.config.get_config_path", lambda: prof / "config.yaml"):
                    first = cfg_mod.load_config()
                    assert first["model"]["default"] == "v1"
                    (root / "config.yaml").write_text(
                        "model:\n  provider: gemini\n  default: v2\n",
                        encoding="utf-8",
                    )
                    second = cfg_mod.load_config()
                    cached_old = second["model"]["default"] == "v1"
                    bust_config_caches(root_config_path())
                    third = cfg_mod.load_config()
                    ok = cached_old and third["model"]["default"] == "v2"
                    step(
                        "bust root-cache ververst profiel load_config",
                        ok,
                        f"cached={cached_old} after_bust={third['model']['default']}",
                    )


def test_partial_save_preserves_root_providers(base: Path) -> None:
    root, prof = _tree(base)
    (root / "config.yaml").write_text(
        "providers:\n  venice:\n    base_url: https://api.venice.ai/api/v1\n    api_key_env: VENICE_API_KEY\n",
        encoding="utf-8",
    )
    (prof / "config.yaml").write_text("agent:\n  max_turns: 3\n", encoding="utf-8")

    from hermes_cli import config as cfg_mod

    cfg_mod._LOAD_CONFIG_CACHE.clear()
    cfg_mod._RAW_CONFIG_CACHE.clear()

    with mock.patch.dict(os.environ, {"HERMES_HOME": str(prof)}):
        with mock.patch("hermes_constants.get_default_hermes_root", return_value=root):
            with mock.patch("hermes_cli.config.ensure_hermes_home", lambda: None):
                with mock.patch("hermes_cli.config.get_config_path", lambda: prof / "config.yaml"):
                    with mock.patch("hermes_cli.config.is_managed", lambda: False):
                        cfg_mod.save_config({"agent": {"max_turns": 9}})
                        root_text = (root / "config.yaml").read_text(encoding="utf-8")
                        prof_text = (prof / "config.yaml").read_text(encoding="utf-8")
                        prof_lines = prof_text.splitlines()
                        prof_has_providers_key = any(
                            line.strip().startswith("providers:") for line in prof_lines
                        )
                        ok = (
                            "venice" in root_text
                            and "api.venice.ai" in root_text
                            and not prof_has_providers_key
                            and "max_turns: 9" in prof_text
                        )
                        step("partial profiel-save behoudt root providers", ok)


def test_explicit_providers_save_redirects_to_root(base: Path) -> None:
    root, prof = _tree(base)
    (root / "config.yaml").write_text(
        "providers:\n  venice:\n    base_url: https://old.example/v1\n",
        encoding="utf-8",
    )
    (prof / "config.yaml").write_text("agent:\n  max_turns: 1\n", encoding="utf-8")

    from hermes_cli import config as cfg_mod
    import yaml

    cfg_mod._LOAD_CONFIG_CACHE.clear()
    cfg_mod._RAW_CONFIG_CACHE.clear()

    with mock.patch.dict(os.environ, {"HERMES_HOME": str(prof)}):
        with mock.patch("hermes_constants.get_default_hermes_root", return_value=root):
            with mock.patch("hermes_cli.config.ensure_hermes_home", lambda: None):
                with mock.patch("hermes_cli.config.get_config_path", lambda: prof / "config.yaml"):
                    with mock.patch("hermes_cli.config.is_managed", lambda: False):
                        cfg_mod.save_config(
                            {
                                "providers": {
                                    "venice": {"base_url": "https://new.example/v1"},
                                }
                            }
                        )
                        data = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))
                        url = (data.get("providers") or {}).get("venice", {}).get("base_url", "")
                        ok = url == "https://new.example/v1"
                        step("providers in save → root redirect", ok, url)


def test_merge_corrupt_legacy_yaml_no_crash(base: Path) -> None:
    root, prof = _tree(base)
    (root / "config.yaml").write_text("agent:\n  max_turns: 1\n", encoding="utf-8")
    legacy = base / "legacy_bad"
    legacy.mkdir()
    (legacy / "config.yaml").write_text("providers:\n  venice: [unclosed\n", encoding="utf-8")
    script = REPO_ROOT / "windows" / "scripts" / "merge_legacy_providers_config.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--legacy", str(legacy / "config.yaml")],
        env=_env_for(root, prof),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=False,
    )
    ok = proc.returncode == 0 and "venice" not in (root / "config.yaml").read_text(encoding="utf-8")
    step("corrupt legacy YAML → graceful skip", ok, f"exit={proc.returncode}")


def test_single_root_read_in_inheritance(base: Path) -> None:
    root, prof = _tree(base)
    (root / "config.yaml").write_text(
        "model:\n  default: m\nauxiliary:\n  compression:\n    provider: custom\n"
        "providers:\n  venice:\n    base_url: x\n",
        encoding="utf-8",
    )
    (prof / "config.yaml").write_text("agent:\n  max_turns: 2\n", encoding="utf-8")
    reads: list[Path] = []

    import hermes_cli.profile_model_inheritance as inh

    real_read = inh._read_yaml

    def counting_read(path: Path):
        if path == root / "config.yaml":
            reads.append(path)
        return real_read(path)

    with mock.patch.dict(os.environ, {"HERMES_HOME": str(prof)}):
        with mock.patch("hermes_constants.get_default_hermes_root", return_value=root):
            with mock.patch.object(inh, "_read_yaml", side_effect=counting_read):
                merged = {"agent": {"max_turns": 2}}
                out = inh.apply_profile_root_config_inheritance(merged, {"agent": {"max_turns": 2}})
                ok = (
                    len(reads) == 1
                    and out["providers"].get("venice")
                    and out["auxiliary"]["compression"]["provider"] == "custom"
                )
                step("apply_profile_root_config_inheritance: 1x root read", ok, f"reads={len(reads)}")


def run_all() -> int:
    print("=== Root config inheritance harness ===")
    with tempfile.TemporaryDirectory(prefix="hermes_rci_e2e_") as td:
        base = Path(td)
        tests: list[tuple[str, Callable[[Path], None]]] = [
            ("root_config_path", test_root_config_path_ignores_profile_home),
            ("collect_env_sync", test_collect_env_sync_reads_root_only),
            ("merge_legacy", test_merge_legacy_targets_root_when_profile_home),
            ("cache_bust", test_bust_root_caches_invalidates_profile_load),
            ("partial_save", test_partial_save_preserves_root_providers),
            ("providers_redirect", test_explicit_providers_save_redirects_to_root),
            ("corrupt_yaml", test_merge_corrupt_legacy_yaml_no_crash),
            ("single_read", test_single_root_read_in_inheritance),
        ]
        for label, fn in tests:
            try:
                fn(base)
            except Exception as exc:
                step(label, False, str(exc)[:200])

    if FAILURES:
        print(f"=== HARNESS: FAIL ({FAILURES}) ===", file=sys.stderr)
        return 1
    print("=== HARNESS: PASS ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_all())
