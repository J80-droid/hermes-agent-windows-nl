"""Legal chat rooktest: profile env, provider/model fallback, auth precheck, optional chat run."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

_REPO = Path(__file__).resolve().parents[2]


def _prepare_profile(profile: str) -> Path:
    from hermes_cli.profiles import resolve_profile_env

    home = Path(resolve_profile_env(profile))
    os.environ["HERMES_HOME"] = str(home)
    from hermes_cli import config as config_mod

    config_mod._LOAD_CONFIG_CACHE.clear()
    return home


def _model_provider_from_config() -> Tuple[str, str]:
    from hermes_cli.config import load_config

    model_cfg = load_config().get("model")
    if isinstance(model_cfg, dict):
        model = str(model_cfg.get("default") or "").strip()
        provider = str(model_cfg.get("provider") or "").strip()
        if model:
            return provider, model

    from hermes_constants import get_default_hermes_root

    core_path = get_default_hermes_root() / "config.yaml"
    if not core_path.is_file():
        return "", ""
    import yaml

    core_cfg = yaml.safe_load(core_path.read_text(encoding="utf-8")) or {}
    core_model = core_cfg.get("model")
    if isinstance(core_model, dict):
        return (
            str(core_model.get("provider") or "").strip(),
            str(core_model.get("default") or "").strip(),
        )
    if isinstance(core_model, str):
        return "", core_model.strip()
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
    """Run one-shot legal chat rooktest; 0 on success, 1 on failure, 2 when skipped."""
    if not inference_available(profile):
        print("[SKIP] Geen bruikbare inference-config — chat overgeslagen (geen 401)")
        print("[INFO] Zet model/provider in profiel-config of core config + API-key in profiel-.env")
        return 2

    provider, model = _model_provider_from_config()
    cmd = [
        sys.executable,
        "-m",
        "hermes_cli.main",
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
        "mcp,file,memory",
    ]
    if provider:
        cmd.extend(["--provider", provider])
    if model:
        cmd.extend(["--model", model])

    os.environ.setdefault("HERMES_YOLO_MODE", "1")
    os.environ.setdefault("HERMES_NONINTERACTIVE", "1")
    proc = subprocess.run(cmd, cwd=str(_REPO))
    if proc.returncode == 0:
        print("[OK] Hermes chat rooktest geslaagd")
        return 0
    print(f"[WARN] Hermes chat exit {proc.returncode} — controleer API-key of hermes login")
    return 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        sys.exit(0 if inference_available() else 1)
    sys.exit(run_chat_rooktest())
