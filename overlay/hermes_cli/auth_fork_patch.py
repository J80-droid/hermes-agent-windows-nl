"""Attach fork-only ``read_auth_json`` to Tier A ``hermes_cli.auth`` (overlay; no Tier A edits)."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def sync_root_active_provider(provider_id: str) -> Path:
    """Set ``active_provider`` on root ``auth.json`` (matches root ``config.yaml`` model)."""
    from hermes_constants import get_default_hermes_root

    import hermes_cli.auth as auth

    root_auth = get_default_hermes_root() / "auth.json"
    root_lock = root_auth.with_suffix(".lock")
    with auth._file_lock(
        root_lock,
        auth._auth_lock_holder,
        auth.AUTH_LOCK_TIMEOUT_SECONDS,
        "Timed out waiting for root auth store lock",
    ):
        auth_store = read_auth_json(root_auth)
        if not auth_store:
            auth_store = {"version": auth.AUTH_STORE_VERSION, "providers": {}}
        auth_store["active_provider"] = str(provider_id or "").strip()
        real_path_fn = auth._auth_file_path
        try:
            auth._auth_file_path = lambda: root_auth  # type: ignore[method-assign, assignment]
            return auth._save_auth_store(auth_store)
        finally:
            auth._auth_file_path = real_path_fn  # type: ignore[method-assign, assignment]


def read_shared_nous_state_bom_tolerant():
    """Load shared Nous OAuth store with UTF-8 BOM tolerance."""
    import hermes_cli.auth as auth

    try:
        path = auth._nous_shared_store_path()
    except RuntimeError:
        return None
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    refresh_token = payload.get("refresh_token")
    access_token = payload.get("access_token")
    if not (isinstance(refresh_token, str) and refresh_token.strip()):
        return None
    if not (isinstance(access_token, str) and access_token.strip()):
        return None
    return payload


def read_auth_json(auth_file: Optional[Path] = None) -> Dict[str, Any]:
    """Load Hermes ``auth.json`` with UTF-8 BOM tolerance."""
    from hermes_cli.auth import _auth_file_path

    path = auth_file or _auth_file_path()
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        return {}
    raw = json.loads(text)
    return raw if isinstance(raw, dict) else {}


def repair_auth_json_bom(auth_file: Optional[Path] = None) -> bool:
    """Rewrite ``auth.json`` without UTF-8 BOM when JSON is valid."""
    from hermes_cli.auth import _auth_file_path

    path = auth_file or _auth_file_path()
    if not path.is_file():
        return False
    raw_bytes = path.read_bytes()
    if not raw_bytes.startswith(b"\xef\xbb\xbf"):
        return False
    try:
        data = json.loads(raw_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    logger.info("auth: removed UTF-8 BOM from %s", path)
    return True


def repair_all_auth_json_bom() -> list[str]:
    """Repair root + profile ``auth.json`` files that carry a UTF-8 BOM."""
    from hermes_constants import get_default_hermes_root

    repaired: list[str] = []
    root = get_default_hermes_root()
    candidates = [root / "auth.json"]
    profiles_root = root / "profiles"
    if profiles_root.is_dir():
        candidates.extend(profiles_root.glob("*/auth.json"))
    for path in candidates:
        if repair_auth_json_bom(path):
            repaired.append(str(path))
    return repaired


def _attempt_corrupt_auth_coherence_repair() -> None:
    """Try model/provider repair after corrupt auth.json (guarded against re-entry)."""
    import os

    import hermes_cli.auth as auth

    if getattr(auth, "_AUTH_CORRUPT_REPAIR_IN_PROGRESS", False):
        return
    try:
        from hermes_cli.model_runtime_config import (
            detect_model_provider_incoherence,
            repair_model_provider_coherence,
        )

        issues = detect_model_provider_incoherence()
        error_issues = [
            issue
            for issue in issues
            if getattr(issue, "severity", None) == "error"
        ]
        if not error_issues:
            return
        auth._AUTH_CORRUPT_REPAIR_IN_PROGRESS = True  # type: ignore[attr-defined]
        try:
            repair_model_provider_coherence(
                prefer="auth_from_config",
                issues=error_issues,
            )
        finally:
            auth._AUTH_CORRUPT_REPAIR_IN_PROGRESS = False  # type: ignore[attr-defined]
    except Exception:
        auth._AUTH_CORRUPT_REPAIR_IN_PROGRESS = False  # type: ignore[attr-defined]
        if not os.environ.get("HERMES_SUPPRESS_AUTH_CORRUPT_LOG"):
            logger.debug("auth: corrupt-auth coherence repair failed", exc_info=True)


def _normalize_auth_store_raw(raw: Any) -> Dict[str, Any]:
    from hermes_cli.auth import AUTH_STORE_VERSION

    if isinstance(raw, dict) and (
        isinstance(raw.get("providers"), dict)
        or isinstance(raw.get("credential_pool"), dict)
    ):
        raw.setdefault("providers", {})
        return raw

    if isinstance(raw, dict) and raw.get("active_provider") is not None:
        return {
            "version": AUTH_STORE_VERSION,
            "active_provider": raw.get("active_provider"),
            "providers": {},
        }

    if isinstance(raw, dict) and isinstance(raw.get("systems"), dict):
        systems = raw["systems"]
        providers = {}
        if "nous_portal" in systems:
            providers["nous"] = systems["nous_portal"]
        return {
            "version": AUTH_STORE_VERSION,
            "providers": providers,
            "active_provider": "nous" if providers else None,
        }

    return {"version": AUTH_STORE_VERSION, "providers": {}}


def _load_auth_store_bom_safe(auth_file: Optional[Path] = None) -> Dict[str, Any]:
    """BOM-tolerant ``_load_auth_store`` for root and all profile auth files."""
    import shutil

    import hermes_cli.auth as auth

    auth_file = auth_file or auth._auth_file_path()
    if not auth_file.exists():
        return {"version": auth.AUTH_STORE_VERSION, "providers": {}}

    try:
        had_bom = auth_file.read_bytes().startswith(b"\xef\xbb\xbf")
        raw = read_auth_json(auth_file)
        if had_bom:
            repair_auth_json_bom(auth_file)
    except json.JSONDecodeError as exc:
        corrupt_path = auth_file.with_suffix(".json.corrupt")
        try:
            shutil.copy2(auth_file, corrupt_path)
        except Exception:
            pass
        if not os.environ.get("HERMES_SUPPRESS_AUTH_CORRUPT_LOG"):
            logger.warning(
                "auth: failed to parse %s (%s) — starting with empty store. "
                "Corrupt file preserved at %s",
                auth_file,
                exc,
                corrupt_path,
            )
        _attempt_corrupt_auth_coherence_repair()
        return {"version": auth.AUTH_STORE_VERSION, "providers": {}}
    except Exception as exc:
        corrupt_path = auth_file.with_suffix(".json.corrupt")
        try:
            shutil.copy2(auth_file, corrupt_path)
        except Exception:
            pass
        if not os.environ.get("HERMES_SUPPRESS_AUTH_CORRUPT_LOG"):
            logger.warning(
                "auth: failed to parse %s (%s) — starting with empty store. "
                "Corrupt file preserved at %s",
                auth_file,
                exc,
                corrupt_path,
            )
        _attempt_corrupt_auth_coherence_repair()
        return {"version": auth.AUTH_STORE_VERSION, "providers": {}}

    return _normalize_auth_store_raw(raw)


def _reset_config_provider_root() -> Path:
    """Reset root ``config.yaml`` provider to auto after logout (profile-aware)."""
    from hermes_cli.profile_model_inheritance import root_config_path
    from hermes_constants import OPENROUTER_BASE_URL
    from utils import atomic_yaml_write
    import yaml

    config_path = root_config_path()
    if not config_path.exists():
        return config_path

    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except OSError:
        return config_path
    if not isinstance(config, dict):
        return config_path

    model = config.get("model")
    if isinstance(model, dict):
        model["provider"] = "auto"
        if "base_url" in model:
            model["base_url"] = OPENROUTER_BASE_URL
        config["model"] = model
        atomic_yaml_write(config_path, config, sort_keys=False)
    return config_path


def apply_auth_fork_patch() -> None:
    import hermes_cli.auth as auth

    if getattr(auth, "_fork_read_auth_json_patch_applied", False):
        return
    auth.read_auth_json = read_auth_json  # type: ignore[attr-defined]
    auth.sync_root_active_provider = sync_root_active_provider  # type: ignore[attr-defined]
    auth.repair_auth_json_bom = repair_auth_json_bom  # type: ignore[attr-defined]
    auth.repair_all_auth_json_bom = repair_all_auth_json_bom  # type: ignore[attr-defined]
    auth._read_shared_nous_state = read_shared_nous_state_bom_tolerant  # type: ignore[assignment]
    auth._load_auth_store = _load_auth_store_bom_safe  # type: ignore[assignment]
    auth._reset_config_provider = _reset_config_provider_root  # type: ignore[assignment]
    if not hasattr(auth, "_AUTH_CORRUPT_REPAIR_IN_PROGRESS"):
        auth._AUTH_CORRUPT_REPAIR_IN_PROGRESS = False  # type: ignore[attr-defined]
    auth._fork_read_auth_json_patch_applied = True  # type: ignore[attr-defined]
