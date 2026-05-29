#!/usr/bin/env python3
"""E2E harness: model/provider hardening (code-review follow-up, no live API).

Scenario matrix:
  E1  comment-only profile yaml → no false-positive global blocks
  E2  real auxiliary/providers keys → detected + strip_all_profile_global_blocks
  E3  coherence gate: warn-only issues do not block (error-only, like drift PS1)
  E4  read_auth_json empty file → {}
  E5  read_auth_json UTF-8 BOM → parsed dict
  E6  corrupt auth.json → empty store + repair guard reset (no re-entry hang)
  E7  _read_shared_nous_state tolerates UTF-8 BOM
  E8  azure-foundry persist + aligned auth.active_provider
"""

from __future__ import annotations

import json
import os
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


def _coherence_blocking_errors(config: dict | None = None) -> list:
    """Mirror windows/scripts/HermesHomeCommon.ps1 drift gate (errors only)."""
    from hermes_cli.model_runtime_config import detect_model_provider_incoherence

    if config is None:
        from hermes_cli.config import load_config

        config = load_config()
    issues = detect_model_provider_incoherence(config)
    return [i for i in issues if getattr(i, "severity", "warn") == "error"]


@contextmanager
def _isolated_hermes(
    *,
    root_yaml: str,
    auth_payload: dict | None = None,
) -> Iterator[Path]:
    import hermes_cli.profile_model_inheritance as pmi

    with tempfile.TemporaryDirectory(prefix="hermes_mph_e2e_") as tmp:
        root = Path(tmp) / "hermes"
        root.mkdir()
        (root / "config.yaml").write_text(root_yaml, encoding="utf-8")
        if auth_payload is not None:
            (root / "auth.json").write_text(
                json.dumps(auth_payload), encoding="utf-8"
            )
        os.environ["HERMES_HOME"] = str(root)
        os.environ["HERMES_WIN_PREFER_LOCALAPPDATA"] = "0"
        import hermes_constants

        hermes_constants._profile_fallback_warned = True
        real_root_fn = pmi.root_config_path

        def _root_path() -> Path:
            return root / "config.yaml"

        real_default_root = hermes_constants.get_default_hermes_root

        def _default_root() -> Path:
            return root

        pmi.root_config_path = _root_path  # type: ignore[method-assign]
        hermes_constants.get_default_hermes_root = _default_root  # type: ignore[assignment]
        try:
            yield root
        finally:
            pmi.root_config_path = real_root_fn  # type: ignore[method-assign]
            hermes_constants.get_default_hermes_root = real_default_root  # type: ignore[assignment]


@contextmanager
def _isolated_profiles_tree() -> Iterator[Path]:
    import hermes_cli.profile_model_inheritance as pmi

    with tempfile.TemporaryDirectory(prefix="hermes_mph_prof_e2e_") as tmp:
        root = Path(tmp) / "hermes"
        profiles = root / "profiles"
        profiles.mkdir(parents=True)
        (root / "config.yaml").write_text(
            "model:\n  provider: nous\n  default: x\n", encoding="utf-8"
        )
        os.environ["HERMES_HOME"] = str(root)
        os.environ["HERMES_WIN_PREFER_LOCALAPPDATA"] = "0"
        import hermes_constants

        hermes_constants._profile_fallback_warned = True
        real_default_root = hermes_constants.get_default_hermes_root

        def _default_root() -> Path:
            return root

        hermes_constants.get_default_hermes_root = _default_root  # type: ignore[assignment]
        try:
            yield profiles
        finally:
            hermes_constants.get_default_hermes_root = real_default_root  # type: ignore[assignment]


def test_e1_comment_only_not_global_block() -> None:
    with _isolated_profiles_tree() as profiles:
        legal = profiles / "legal"
        legal.mkdir()
        (legal / "config.yaml").write_text(
            "# providers/custom_providers: inherited from root config.\n"
            "agent:\n  max_turns: 30\n",
            encoding="utf-8",
        )
        from hermes_cli.profile_model_inheritance import (
            list_profiles_with_global_config_blocks,
            profile_has_global_config_blocks,
        )

        ok = (
            not profile_has_global_config_blocks(legal)
            and list_profiles_with_global_config_blocks() == []
        )
        _step("comment_only_not_global_block", ok)


def test_e2_strip_real_global_blocks() -> None:
    with _isolated_profiles_tree() as profiles:
        core = profiles / "core"
        core.mkdir()
        (core / "config.yaml").write_text(
            "auxiliary:\n  profile_describer:\n    provider: auto\n"
            "providers:\n  venice:\n    api_key_env: VENICE_API_KEY\n"
            "agent:\n  max_turns: 30\n",
            encoding="utf-8",
        )
        from hermes_cli.profile_model_inheritance import (
            list_profiles_with_global_config_blocks,
            strip_all_profile_global_blocks,
        )

        listed = list_profiles_with_global_config_blocks()
        stripped = strip_all_profile_global_blocks()
        cfg = yaml.safe_load((core / "config.yaml").read_text(encoding="utf-8"))
        ok = (
            listed == ["core"]
            and stripped == ["core"]
            and "auxiliary" not in cfg
            and "providers" not in cfg
            and cfg.get("agent", {}).get("max_turns") == 30
        )
        _step("strip_real_global_blocks", ok, str({"listed": listed, "stripped": stripped}))


def test_e3_warn_only_does_not_block_drift_gate() -> None:
    with _isolated_hermes(
        root_yaml="model:\n  provider: gemini\n  default: deepseek/deepseek-v4\n",
        auth_payload={"version": 1, "active_provider": "gemini", "providers": {}},
    ):
        from hermes_cli.config import load_config
        from hermes_cli.model_runtime_config import detect_model_provider_incoherence

        cfg = load_config()
        all_issues = detect_model_provider_incoherence(cfg)
        blocking = _coherence_blocking_errors(cfg)
        ok = (
            any(i.code == "vendor_slug_wrong_provider" for i in all_issues)
            and len(blocking) == 0
        )
        _step("warn_only_not_blocking", ok, str([i.code for i in all_issues]))


def test_e4_read_auth_json_empty() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "auth.json"
        path.write_text("", encoding="utf-8")
        from hermes_cli.auth import read_auth_json

        ok = read_auth_json(path) == {}
        _step("read_auth_json_empty", ok)


def test_e5_read_auth_json_bom() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "auth.json"
        path.write_bytes(
            b"\xef\xbb\xbf"
            + b'{"version": 1, "active_provider": "nous", "providers": {}}'
        )
        from hermes_cli.auth import read_auth_json

        data = read_auth_json(path)
        ok = data.get("active_provider") == "nous"
        _step("read_auth_json_bom", ok, str(data.get("active_provider")))


def test_e6_corrupt_auth_guard_reset() -> None:
    with _isolated_hermes(
        root_yaml="model:\n  provider: gemini\n  default: m\n",
        auth_payload=None,
    ) as root:
        from hermes_cli import auth as auth_mod

        (root / "auth.json").write_text("{not-json", encoding="utf-8")
        auth_mod._AUTH_CORRUPT_REPAIR_IN_PROGRESS = False
        # Expected corrupt-auth recovery logs to stderr; keep harness output clean for PS audits.
        os.environ["HERMES_SUPPRESS_AUTH_CORRUPT_LOG"] = "1"
        try:
            store = auth_mod._load_auth_store(root / "auth.json")
        finally:
            os.environ.pop("HERMES_SUPPRESS_AUTH_CORRUPT_LOG", None)
        ok = (
            store.get("providers") == {}
            and auth_mod._AUTH_CORRUPT_REPAIR_IN_PROGRESS is False
        )
        _step("corrupt_auth_guard_reset", ok)


def test_e7_shared_nous_store_bom() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        shared = Path(tmp) / "shared"
        shared.mkdir()
        from hermes_cli.auth import NOUS_SHARED_STORE_FILENAME, _read_shared_nous_state

        store_path = shared / NOUS_SHARED_STORE_FILENAME
        store_path.write_bytes(
            b"\xef\xbb\xbf"
            + b'{"refresh_token": "rt-e2e", "access_token": "at-e2e"}'
        )
        os.environ["HERMES_SHARED_AUTH_DIR"] = str(shared)
        try:
            state = _read_shared_nous_state()
            ok = (
                state is not None
                and state.get("refresh_token") == "rt-e2e"
                and state.get("access_token") == "at-e2e"
            )
        finally:
            os.environ.pop("HERMES_SHARED_AUTH_DIR", None)
        _step("shared_nous_store_bom", ok)


def test_e8_azure_foundry_persist_coherent() -> None:
    with _isolated_hermes(
        root_yaml="model:\n  provider: gemini\n  default: old\n",
        auth_payload={"version": 1, "active_provider": "gemini", "providers": {}},
    ) as root:
        from hermes_cli.auth import _load_auth_store
        from hermes_cli.model_runtime_config import (
            detect_model_provider_incoherence,
            persist_model_runtime,
        )

        persist_model_runtime(
            "azure-foundry",
            default_model="gpt-4.1",
            inference_base_url="https://myfoundry.openai.azure.com/openai/v1",
        )
        cfg = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))
        auth = _load_auth_store()
        issues = detect_model_provider_incoherence(cfg, auth)
        ok = (
            cfg["model"]["provider"] == "azure-foundry"
            and auth.get("active_provider") == "azure-foundry"
            and len(_coherence_blocking_errors(cfg)) == 0
            and len(issues) == 0
        )
        _step("azure_foundry_persist_coherent", ok, str(cfg.get("model")))


def run_all() -> int:
    print("=== Model/Provider Hardening E2E ===")
    print(f"Repo: {REPO_ROOT}")
    tests = [
        test_e1_comment_only_not_global_block,
        test_e2_strip_real_global_blocks,
        test_e3_warn_only_does_not_block_drift_gate,
        test_e4_read_auth_json_empty,
        test_e5_read_auth_json_bom,
        test_e6_corrupt_auth_guard_reset,
        test_e7_shared_nous_store_bom,
        test_e8_azure_foundry_persist_coherent,
    ]
    for fn in tests:
        try:
            fn()
        except Exception as exc:
            _step(fn.__name__, False, str(exc)[:200])

    print()
    if FAILURES:
        print(f"=== HARNESS: FAIL ({FAILURES}/{len(tests)}) ===", file=sys.stderr)
        return 1
    print(f"=== HARNESS: PASS ({len(tests)}/{len(tests)}) ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_all())
