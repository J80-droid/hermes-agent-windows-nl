"""Attach fork-only ``read_auth_json`` to Tier A ``hermes_cli.auth`` (overlay; no Tier A edits)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


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
    import json
    from typing import Any, Dict, Optional

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


def apply_auth_fork_patch() -> None:
    import hermes_cli.auth as auth

    if getattr(auth, "_fork_read_auth_json_patch_applied", False):
        return
    auth.read_auth_json = read_auth_json  # type: ignore[attr-defined]
    auth.sync_root_active_provider = sync_root_active_provider  # type: ignore[attr-defined]
    auth._read_shared_nous_state = read_shared_nous_state_bom_tolerant  # type: ignore[assignment]
    if not hasattr(auth, "_AUTH_CORRUPT_REPAIR_IN_PROGRESS"):
        auth._AUTH_CORRUPT_REPAIR_IN_PROGRESS = False  # type: ignore[attr-defined]
    auth._fork_read_auth_json_patch_applied = True  # type: ignore[attr-defined]
