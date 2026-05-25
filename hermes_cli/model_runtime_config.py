"""Atomic model/provider persistence and config/auth coherence checks.

Public API
----------
- ``persist_model_runtime`` — single write to root ``config.yaml`` + optional
  ``auth.json`` ``active_provider`` sync (never profile-local yaml).
- ``detect_model_provider_incoherence`` — split-brain, vendor-slug, stale
  ``base_url`` host checks.
- ``repair_model_provider_coherence`` — align config to auth (default) or the
  inverse via ``prefer=``.

Callers: ``hermes model`` flows via ``_commit_provider_model`` in ``main.py``,
``_update_config_for_provider`` in ``auth.py``, ``hermes doctor --fix``, setup
wizard post-checks, gateway startup WARN, ``verify_hermes_config_drift.ps1``.

Windows repair: ``windows/REPAIR_MODEL_PROVIDER.bat``. Drift: ``verify_hermes_config_drift.ps1``
(error-severity only). E2E: ``audits/RUN_MODEL_PROVIDER_COHERENCE_E2E.bat`` (10),
``audits/RUN_MODEL_PROVIDER_HARDENING_E2E.bat`` (8). Unit tests:
``tests/hermes_cli/test_model_runtime_config.py``, ``test_auth_json_store.py``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

logger = logging.getLogger(__name__)

_PREFER_MODES = frozenset({"config_from_auth", "auth_from_config"})

# Providers that accept vendor/model slugs (OpenRouter-style, Nous Portal catalog).
VENDOR_SLUG_PROVIDERS = frozenset({
    "openrouter",
    "custom",
    "auto",
    "ai-gateway",
    "kilocode",
    "opencode-zen",
    "huggingface",
    "lmstudio",
    "nous",
})

# Rough host → expected provider for stale base_url detection.
_PROVIDER_HOST_HINTS: dict[str, tuple[str, ...]] = {
    "generativelanguage.googleapis.com": ("gemini", "google-gemini-cli"),
    "openrouter.ai": ("openrouter",),
    "inference-api.nousresearch.com": ("nous",),
    "api.deepseek.com": ("deepseek",),
}


@dataclass(frozen=True)
class CoherenceIssue:
    code: str
    message: str
    severity: str = "warn"  # warn | error


@dataclass
class PersistModelRuntimeResult:
    config_path: Path
    provider: str
    default_model: str
    base_url: str
    previous_provider: str
    previous_default: str


def _read_root_yaml() -> dict[str, Any]:
    from hermes_cli.profile_model_inheritance import root_config_path

    path = root_config_path()
    if not path.is_file():
        return {}
    try:
        import yaml

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _model_section_from_config(config: dict[str, Any]) -> dict[str, Any]:
    model = config.get("model")
    if isinstance(model, dict):
        return dict(model)
    if isinstance(model, str) and model.strip():
        return {"default": model.strip()}
    return {}


def _normalize_provider_id(provider_id: str) -> str:
    return (provider_id or "").strip().lower()


def _host_from_base_url(base_url: str) -> str:
    try:
        from utils import base_url_hostname

        return (base_url_hostname(base_url) or "").lower()
    except Exception:
        return ""


def bust_all_runtime_config_caches() -> None:
    from hermes_cli.profile_model_inheritance import bust_config_caches, root_config_path

    bust_config_caches(root_config_path())


def persist_model_runtime(
    provider_id: str,
    *,
    default_model: Optional[str] = None,
    inference_base_url: str = "",
    sync_auth: bool = True,
    extra_model_fields: Optional[Dict[str, Any]] = None,
) -> PersistModelRuntimeResult:
    """Atomically persist model.provider, model.default, and base_url to root config.

    Always writes ``%LOCALAPPDATA%/hermes/config.yaml`` (via ``root_config_path()``),
    never a profile-local ``config.yaml``, so ``hermes -p <profile> model`` updates
    the effective runtime for all profiles.
    """
    from hermes_cli.profile_model_inheritance import root_config_path
    from utils import atomic_yaml_write

    provider = _normalize_provider_id(provider_id)
    if not provider:
        raise ValueError("provider_id is required")

    config_path = root_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config = _read_root_yaml()
    model_cfg = _model_section_from_config(config)
    previous_provider = str(model_cfg.get("provider") or "").strip()
    previous_default = str(model_cfg.get("default") or model_cfg.get("model") or "").strip()

    model_cfg["provider"] = provider
    if default_model is not None and str(default_model).strip():
        model_cfg["default"] = str(default_model).strip()
    elif not model_cfg.get("default"):
        cur = str(model_cfg.get("model") or "").strip()
        if cur:
            model_cfg["default"] = cur

    base = (inference_base_url or "").strip()
    if base:
        model_cfg["base_url"] = base.rstrip("/")
    else:
        model_cfg.pop("base_url", None)

    model_cfg.pop("model", None)

    if extra_model_fields is not None:
        for key, value in extra_model_fields.items():
            if value is None:
                model_cfg.pop(key, None)
            else:
                model_cfg[key] = value
    else:
        model_cfg.pop("api_key", None)
        model_cfg.pop("api_mode", None)

    config["model"] = model_cfg
    atomic_yaml_write(config_path, config, sort_keys=False)
    try:
        import os

        os.chmod(config_path, 0o600)
    except (OSError, NotImplementedError):
        pass

    if sync_auth:
        from hermes_cli.auth import _auth_store_lock, _load_auth_store, _save_auth_store

        try:
            with _auth_store_lock():
                auth_store = _load_auth_store()
                auth_store["active_provider"] = provider
                _save_auth_store(auth_store)
        except Exception as exc:
            logger.warning(
                "persist_model_runtime: config saved but auth.json sync failed "
                "(%s) — run 'hermes doctor --fix'",
                exc,
            )
            raise

    bust_all_runtime_config_caches()

    final_default = str(model_cfg.get("default") or "").strip()
    return PersistModelRuntimeResult(
        config_path=config_path,
        provider=provider,
        default_model=final_default,
        base_url=str(model_cfg.get("base_url") or "").strip(),
        previous_provider=previous_provider,
        previous_default=previous_default,
    )


def detect_model_provider_incoherence(
    config: Optional[dict[str, Any]] = None,
    auth_store: Optional[dict[str, Any]] = None,
) -> List[CoherenceIssue]:
    """Return coherence issues between auth.json and root model config."""
    issues: List[CoherenceIssue] = []

    if config is None:
        try:
            from hermes_cli.config import load_config

            config = load_config()
        except Exception:
            config = {}
    if auth_store is None:
        try:
            from hermes_cli.auth import _load_auth_store

            auth_store = _load_auth_store()
        except Exception:
            auth_store = {}

    model_cfg = _model_section_from_config(config or {})
    cfg_provider = _normalize_provider_id(str(model_cfg.get("provider") or ""))
    cfg_default = str(model_cfg.get("default") or model_cfg.get("model") or "").strip()
    cfg_base = str(model_cfg.get("base_url") or "").strip()

    auth_provider = _normalize_provider_id(str((auth_store or {}).get("active_provider") or ""))

    if auth_provider and cfg_provider and auth_provider != cfg_provider:
        issues.append(
            CoherenceIssue(
                code="auth_config_provider_mismatch",
                message=(
                    f"auth.json active_provider is '{auth_provider}' but "
                    f"config model.provider is '{cfg_provider}'. "
                    "Run 'hermes doctor --fix' to align them."
                ),
                severity="error",
            )
        )

    if cfg_default and "/" in cfg_default and cfg_provider and cfg_provider not in VENDOR_SLUG_PROVIDERS:
        issues.append(
            CoherenceIssue(
                code="vendor_slug_wrong_provider",
                message=(
                    f"model.default '{cfg_default}' uses a vendor/model slug but "
                    f"model.provider is '{cfg_provider}'. "
                    "Use an aggregator (openrouter, nous) or drop the vendor prefix."
                ),
                severity="warn",
            )
        )

    if cfg_base and cfg_provider:
        host = _host_from_base_url(cfg_base)
        expected = _PROVIDER_HOST_HINTS.get(host)
        if expected and cfg_provider not in expected:
            issues.append(
                CoherenceIssue(
                    code="base_url_provider_mismatch",
                    message=(
                        f"model.base_url host '{host}' does not match "
                        f"model.provider '{cfg_provider}'. "
                        "Run 'hermes doctor --fix' to clear stale base_url."
                    ),
                    severity="warn",
                )
            )

    return issues


def repair_model_provider_coherence(
    *,
    prefer: Literal["config_from_auth", "auth_from_config"] = "config_from_auth",
    issues: Optional[List[CoherenceIssue]] = None,
) -> List[str]:
    """Repair split-brain between auth and config. Returns human-readable actions taken."""
    from hermes_cli.auth import PROVIDER_REGISTRY, get_auth_status

    actions: List[str] = []
    if prefer not in _PREFER_MODES:
        prefer = "config_from_auth"

    if issues is None:
        try:
            from hermes_cli.config import load_config

            issues = detect_model_provider_incoherence(load_config())
        except Exception:
            issues = detect_model_provider_incoherence()
    if not issues:
        return actions

    try:
        from hermes_cli.config import load_config

        effective_cfg = load_config()
    except Exception:
        effective_cfg = _read_root_yaml()
    model_cfg = _model_section_from_config(effective_cfg)

    try:
        from hermes_cli.auth import _load_auth_store

        auth_store = _load_auth_store()
    except Exception:
        auth_store = {}

    auth_provider = _normalize_provider_id(str(auth_store.get("active_provider") or ""))
    cfg_provider = _normalize_provider_id(str(model_cfg.get("provider") or ""))

    target_provider = cfg_provider
    if prefer == "config_from_auth" and auth_provider:
        if any(
            i.code in {
                "auth_config_provider_mismatch",
                "base_url_provider_mismatch",
                "vendor_slug_wrong_provider",
            }
            for i in issues
        ):
            target_provider = auth_provider
    elif prefer == "auth_from_config" and cfg_provider:
        target_provider = cfg_provider

    if not target_provider:
        return actions

    inference_url = ""
    pconfig = PROVIDER_REGISTRY.get(target_provider)
    if pconfig and getattr(pconfig, "inference_base_url", None):
        inference_url = str(pconfig.inference_base_url or "").strip()

    if target_provider == "nous":
        try:
            from hermes_cli.auth import resolve_nous_runtime_credentials

            creds = resolve_nous_runtime_credentials(min_key_ttl_seconds=0)
            inference_url = str(creds.get("base_url") or inference_url).strip()
        except Exception:
            pass

    default_model = str(model_cfg.get("default") or model_cfg.get("model") or "").strip()
    if not default_model:
        default_model = None

    persist_model_runtime(
        target_provider,
        default_model=default_model,
        inference_base_url=inference_url,
        sync_auth=True,
    )
    actions.append(
        f"Aligned model.provider to '{target_provider}'"
        + (f" with base_url {inference_url}" if inference_url else " (cleared stale base_url)")
    )

    if auth_provider != target_provider or cfg_provider != target_provider:
        try:
            status = get_auth_status(target_provider)
            if not status.get("logged_in") and cfg_provider == target_provider:
                actions.append(
                    f"Note: auth still targets '{auth_provider or '(none)'}'; "
                    "config kept as source because auth is not logged in for target provider."
                )
        except Exception:
            pass

    return actions
