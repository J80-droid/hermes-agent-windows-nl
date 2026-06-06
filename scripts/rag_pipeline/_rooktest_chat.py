"""Chat rooktest: overlay bootstrap, profile root-inheritance, auth precheck, optional chat run."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

def _chat_timeout_sec() -> int:
    """Parse ``HERMES_ROOKTEST_CHAT_TIMEOUT``; invalid/non-positive → 600s."""
    raw = os.environ.get("HERMES_ROOKTEST_CHAT_TIMEOUT", "600")
    try:
        sec = int(str(raw).strip())
        return sec if sec > 0 else 600
    except (TypeError, ValueError):
        return 600

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
_OVERLAY_ENTRY = _REPO / "scripts" / "run_hermes_cli_with_overlay.py"


def _ensure_overlay() -> None:
    from overlay.bootstrap import install

    install()


def _prepare_profile(profile: str) -> Path:
    _ensure_overlay()
    from hermes_cli.profiles import resolve_profile_env

    home = Path(resolve_profile_env(profile))
    os.environ["HERMES_HOME"] = str(home)
    from hermes_cli import config as config_mod

    config_mod._LOAD_CONFIG_CACHE.clear()
    try:
        from hermes_cli.profile_model_inheritance import bust_config_caches

        bust_config_caches()
    except Exception:
        pass
    return home


def _chat_toolsets_arg() -> str:
    """MCP server names from profile config + file/memory (not pseudo ``mcp`` toolset)."""
    from hermes_cli.config import load_config

    try:
        cfg = load_config()
    except Exception:
        return "file,memory"
    mcp_servers = cfg.get("mcp_servers") if isinstance(cfg, dict) else None
    names: list[str] = []
    if isinstance(mcp_servers, dict):
        names = [str(k).strip() for k in mcp_servers if str(k).strip()]
    parts = names + ["file", "memory"]
    seen: set[str] = set()
    ordered: list[str] = []
    for part in parts:
        if part and part not in seen:
            seen.add(part)
            ordered.append(part)
    return ",".join(ordered) if ordered else "file,memory"


def _model_provider_from_config() -> Tuple[str, str]:
    """Resolved model/provider (profile inherits model/providers from root config)."""
    from hermes_cli.config import load_config

    model_cfg = load_config().get("model")
    if isinstance(model_cfg, dict):
        return (
            str(model_cfg.get("provider") or "").strip(),
            str(model_cfg.get("default") or "").strip(),
        )
    if isinstance(model_cfg, str):
        return "", model_cfg.strip()
    return "", ""


def inference_available(profile: str = "legal") -> bool:
    """True when chat can resolve a real API key for the rooktest profile."""
    _prepare_profile(profile)
    provider, model = _model_provider_from_config()
    if not model:
        return False

    from hermes_cli.auth import AuthError, get_auth_status, has_usable_secret
    from hermes_cli.runtime_provider import resolve_runtime_provider

    try:
        runtime = resolve_runtime_provider(
            requested=provider or None,
            target_model=model,
        )
    except AuthError:
        return False
    except Exception:
        return False

    api_key = str(runtime.get("api_key") or "").strip()
    if has_usable_secret(api_key) and api_key != "no-key-required":
        return True

    for provider_id in filter(
        None,
        {
            provider,
            str(runtime.get("provider") or ""),
            str(runtime.get("requested_provider") or ""),
            str(runtime.get("source") or "").replace("custom_provider:", ""),
        },
    ):
        if get_auth_status(provider_id).get("logged_in"):
            return True
    return False


def run_chat_rooktest(profile: str = "legal") -> int:
    """Run one-shot chat rooktest; 0 on success, 1 on failure, 2 when skipped."""
    if not inference_available(profile):
        print("[SKIP] Geen bruikbare inference-config — chat overgeslagen (geen 401)")
        print(
            "[INFO] Root model/providers worden geërfd — zorg voor VENICE_API_KEY "
            "in profiel-.env en geldige root config.yaml"
        )
        return 2

    _prepare_profile(profile)
    provider, model = _model_provider_from_config()
    toolsets = _chat_toolsets_arg()
    cmd = [
        sys.executable,
        str(_OVERLAY_ENTRY),
        "-p",
        profile,
        "chat",
        "-q",
        "Voer search_knowledge uit op actieve zorgplicht P-Direkt en citeer met [Bron: bestandsnaam].",
        "-Q",
        "--yolo",
        "--max-turns",
        "8",
        "--toolsets",
        toolsets,
    ]
    if provider:
        cmd.extend(["--provider", provider])
    if model:
        cmd.extend(["--model", model])

    os.environ.setdefault("HERMES_YOLO_MODE", "1")
    os.environ.setdefault("HERMES_NONINTERACTIVE", "1")
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(_REPO),
            env=os.environ.copy(),
            timeout=_chat_timeout_sec(),
        )
    except subprocess.TimeoutExpired:
        print(f"[WARN] Hermes chat timeout na {_chat_timeout_sec()}s")
        return 1
    if proc.returncode == 0:
        print("[OK] Hermes chat rooktest geslaagd")
        return 0
    print(f"[WARN] Hermes chat exit {proc.returncode} — controleer API-key of hermes login")
    return 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        sys.exit(0 if inference_available() else 1)
    if len(sys.argv) > 1 and sys.argv[1] == "--check-all":
        from hermes_constants import get_default_hermes_root

        profiles_root = get_default_hermes_root() / "profiles"
        if not profiles_root.is_dir():
            print(f"[ERROR] Profielenmap ontbreekt: {profiles_root}")
            sys.exit(1)
        failed = 0
        for entry in sorted(profiles_root.iterdir()):
            if entry.is_dir():
                ok = inference_available(entry.name)
                print(f"{entry.name}: {'OK' if ok else 'SKIP'}")
                if not ok:
                    failed += 1
        sys.exit(0 if failed == 0 else 1)
    profile = sys.argv[1] if len(sys.argv) > 1 else "legal"
    sys.exit(run_chat_rooktest(profile))
