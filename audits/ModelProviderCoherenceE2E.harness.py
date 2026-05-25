#!/usr/bin/env python3
"""E2E harness: model/provider atomic persist + coherence (no live API).

Scenario matrix (institutional):
  E1  persist from profile HERMES_HOME → root config.yaml only
  E2  detect auth_config_provider_mismatch (split-brain)
  E3  detect base_url_provider_mismatch (stale Gemini host)
  E4  detect vendor_slug_wrong_provider
  E5  repair aligns config to auth (nous + inference base_url)
  E6  persist keeps auth.active_provider (no post-persist clear)
  E7  atomic persist sets provider + default in one write
  E8  custom provider preserves api_key via extra_model_fields
  E9  minimal auth.json (active_provider only) still detected
  E10 coherent aligned config → zero issues
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


@contextmanager
def _isolated_hermes(
    *,
    root_yaml: str,
    auth_payload: dict | None = None,
    profile_yaml: str = "agent:\n  max_turns: 1\n",
    use_profile_home: bool = False,
) -> Iterator[tuple[Path, Path | None]]:
    """Yield (root_dir, profile_dir|None) with HERMES_HOME configured."""
    import hermes_cli.profile_model_inheritance as pmi

    with tempfile.TemporaryDirectory(prefix="hermes_mpc_e2e_") as tmp:
        root = Path(tmp) / "hermes"
        root.mkdir()
        (root / "config.yaml").write_text(root_yaml, encoding="utf-8")
        if auth_payload is not None:
            (root / "auth.json").write_text(
                json.dumps(auth_payload), encoding="utf-8"
            )

        prof: Path | None = None
        if use_profile_home:
            prof = root / "profiles" / "core"
            prof.mkdir(parents=True)
            (prof / "config.yaml").write_text(profile_yaml, encoding="utf-8")
            if auth_payload is not None:
                (prof / "auth.json").write_text(
                    json.dumps(auth_payload), encoding="utf-8"
                )
            os.environ["HERMES_HOME"] = str(prof)
        else:
            os.environ["HERMES_HOME"] = str(root)

        os.environ["HERMES_WIN_PREFER_LOCALAPPDATA"] = "0"
        import hermes_constants

        hermes_constants._profile_fallback_warned = True

        real_root_fn = pmi.root_config_path

        def _root_path() -> Path:
            return root / "config.yaml"

        pmi.root_config_path = _root_path  # type: ignore[method-assign]
        try:
            yield root, prof
        finally:
            pmi.root_config_path = real_root_fn  # type: ignore[method-assign]


def test_e1_persist_profile_to_root() -> None:
    with _isolated_hermes(
        root_yaml="model:\n  provider: gemini\n  default: old\n",
        auth_payload={"version": 1, "active_provider": "gemini", "providers": {}},
        use_profile_home=True,
    ) as (root, prof):
        from hermes_cli.model_runtime_config import persist_model_runtime

        persist_model_runtime(
            "nous",
            default_model="deepseek/deepseek-v4-flash:free",
            inference_base_url="https://inference-api.nousresearch.com/v1",
        )
        root_text = (root / "config.yaml").read_text(encoding="utf-8")
        prof_text = (prof / "config.yaml").read_text(encoding="utf-8") if prof else ""
        ok = (
            "provider: nous" in root_text
            and "provider: gemini" not in root_text
            and "model:" not in prof_text
        )
        _step("persist_profile_to_root", ok, root_text.splitlines()[0] if not ok else "")


def test_e2_detect_auth_config_mismatch() -> None:
    with _isolated_hermes(
        root_yaml="model:\n  provider: gemini\n  default: x/y\n",
        auth_payload={"version": 1, "active_provider": "nous", "providers": {}},
    ) as (root, _):
        from hermes_cli.config import load_config
        from hermes_cli.model_runtime_config import detect_model_provider_incoherence

        codes = {i.code for i in detect_model_provider_incoherence(load_config())}
        _step(
            "detect_auth_config_mismatch",
            "auth_config_provider_mismatch" in codes,
            str(codes),
        )


def test_e3_detect_base_url_mismatch() -> None:
    with _isolated_hermes(
        root_yaml=(
            "model:\n  provider: nous\n  default: m\n"
            "  base_url: https://generativelanguage.googleapis.com/v1beta\n"
        ),
        auth_payload={"version": 1, "active_provider": "nous", "providers": {}},
    ) as (_root, _):
        from hermes_cli.config import load_config
        from hermes_cli.model_runtime_config import detect_model_provider_incoherence

        codes = {i.code for i in detect_model_provider_incoherence(load_config())}
        _step(
            "detect_base_url_mismatch",
            "base_url_provider_mismatch" in codes,
            str(codes),
        )


def test_e4_detect_vendor_slug_wrong_provider() -> None:
    with _isolated_hermes(
        root_yaml="model:\n  provider: gemini\n  default: deepseek/deepseek-v4\n",
        auth_payload={"version": 1, "active_provider": "gemini", "providers": {}},
    ) as (_root, _):
        from hermes_cli.config import load_config
        from hermes_cli.model_runtime_config import detect_model_provider_incoherence

        codes = {i.code for i in detect_model_provider_incoherence(load_config())}
        _step(
            "detect_vendor_slug_wrong_provider",
            "vendor_slug_wrong_provider" in codes,
            str(codes),
        )


def test_e5_repair_aligns_to_auth() -> None:
    with _isolated_hermes(
        root_yaml=(
            "model:\n  provider: gemini\n  default: deepseek/deepseek-v4-flash:free\n"
            "  base_url: https://generativelanguage.googleapis.com/v1beta\n"
        ),
        auth_payload={"version": 1, "active_provider": "nous", "providers": {}},
    ) as (root, _):
        from hermes_cli.config import load_config
        from hermes_cli.model_runtime_config import (
            detect_model_provider_incoherence,
            repair_model_provider_coherence,
        )

        actions = repair_model_provider_coherence()
        cfg = load_config()
        root_text = (root / "config.yaml").read_text(encoding="utf-8")
        ok = (
            bool(actions)
            and cfg.get("model", {}).get("provider") == "nous"
            and not detect_model_provider_incoherence(cfg)
            and "generativelanguage" not in root_text
        )
        _step("repair_aligns_to_auth", ok, str(actions))


def test_e6_auth_sync_after_persist() -> None:
    with _isolated_hermes(
        root_yaml="model:\n  provider: gemini\n  default: old\n",
        auth_payload={"version": 1, "active_provider": "gemini", "providers": {}},
    ) as (_root, _):
        from hermes_cli.auth import _load_auth_store
        from hermes_cli.model_runtime_config import persist_model_runtime

        persist_model_runtime(
            "openrouter",
            default_model="openai/gpt-4o-mini",
            inference_base_url="https://openrouter.ai/api/v1",
        )
        auth = _load_auth_store()
        _step(
            "auth_sync_after_persist",
            auth.get("active_provider") == "openrouter",
            str(auth.get("active_provider")),
        )


def test_e7_atomic_provider_and_default() -> None:
    with _isolated_hermes(
        root_yaml="model:\n  provider: gemini\n  default: only-old\n",
        auth_payload={"version": 1, "active_provider": "gemini", "providers": {}},
    ) as (root, _):
        from hermes_cli.model_runtime_config import persist_model_runtime

        persist_model_runtime(
            "nous",
            default_model="deepseek/deepseek-v4-flash:free",
            inference_base_url="https://inference-api.nousresearch.com/v1",
        )
        data = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))
        model = data.get("model") or {}
        ok = (
            model.get("provider") == "nous"
            and model.get("default") == "deepseek/deepseek-v4-flash:free"
            and "only-old" not in str(model.get("default", ""))
        )
        _step("atomic_provider_and_default", ok, str(model))


def test_e8_custom_api_key_preserved() -> None:
    with _isolated_hermes(
        root_yaml="model:\n  provider: gemini\n  default: x\n",
        auth_payload={"version": 1, "active_provider": "gemini", "providers": {}},
    ) as (root, _):
        from hermes_cli.model_runtime_config import persist_model_runtime

        persist_model_runtime(
            "custom",
            default_model="llama-3",
            inference_base_url="https://llm.example.com/v1",
            extra_model_fields={"api_key": "sk-test-key", "api_mode": "chat_completions"},
        )
        model = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8")).get(
            "model", {}
        )
        ok = (
            model.get("provider") == "custom"
            and model.get("api_key") == "sk-test-key"
            and model.get("api_mode") == "chat_completions"
        )
        _step("custom_api_key_preserved", ok, str({k: model.get(k) for k in ("provider", "api_key")}))


def test_e9_minimal_auth_store_detected() -> None:
    with _isolated_hermes(
        root_yaml="model:\n  provider: gemini\n  default: m\n",
        auth_payload={"version": 1, "active_provider": "nous"},
    ) as (_root, _):
        from hermes_cli.config import load_config
        from hermes_cli.model_runtime_config import detect_model_provider_incoherence

        codes = {i.code for i in detect_model_provider_incoherence(load_config())}
        _step(
            "minimal_auth_store_detected",
            "auth_config_provider_mismatch" in codes,
            str(codes),
        )


def test_e10_coherent_config_clean() -> None:
    with _isolated_hermes(
        root_yaml=(
            "model:\n  provider: nous\n  default: deepseek/deepseek-v4-flash:free\n"
            "  base_url: https://inference-api.nousresearch.com/v1\n"
        ),
        auth_payload={"version": 1, "active_provider": "nous", "providers": {}},
    ) as (_root, _):
        from hermes_cli.config import load_config
        from hermes_cli.model_runtime_config import detect_model_provider_incoherence

        issues = detect_model_provider_incoherence(load_config())
        _step("coherent_config_clean", len(issues) == 0, str([i.code for i in issues]))


def run_all() -> int:
    print("=== Model/Provider Coherence E2E ===")
    print(f"Repo: {REPO_ROOT}")
    tests = [
        test_e1_persist_profile_to_root,
        test_e2_detect_auth_config_mismatch,
        test_e3_detect_base_url_mismatch,
        test_e4_detect_vendor_slug_wrong_provider,
        test_e5_repair_aligns_to_auth,
        test_e6_auth_sync_after_persist,
        test_e7_atomic_provider_and_default,
        test_e8_custom_api_key_preserved,
        test_e9_minimal_auth_store_detected,
        test_e10_coherent_config_clean,
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
