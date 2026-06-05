"""Windows split-home doctor check (Tier B overlay)."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _env_has_non_empty_key(env_path: Path, key: str) -> bool:
    if not env_path.is_file():
        return False
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith(f"{key}="):
                val = stripped.split("=", 1)[1].strip().strip('"').strip("'")
                return bool(val)
    except OSError:
        return False
    return False


def check_windows_split_home_config(issues: list, *, should_fix: bool = False) -> None:
    """Warn when legacy ~/.hermes/config.yaml coexists with Windows runtime config."""
    if sys.platform != "win32":
        return

    localappdata = os.environ.get("LOCALAPPDATA", "")
    if not localappdata:
        return

    from hermes_cli.doctor import check_warn

    runtime_root = Path(localappdata) / "hermes"
    runtime_cfg = runtime_root / "config.yaml"
    legacy_root = Path.home() / ".hermes"
    legacy_cfg = legacy_root / "config.yaml"

    if runtime_cfg.is_file() and legacy_cfg.is_file():
        check_warn(
            "Windows split-home: legacy ~/.hermes/config.yaml exists alongside runtime config",
            f"Canoniek: {runtime_cfg}. Run windows\\DEPRECATE_LEGACY_CONFIG.bat",
        )
        issues.append(
            "Deprecate legacy ~/.hermes/config.yaml (windows\\APPLY_HERMES_HOME_MIGRATION.bat)"
        )

    legacy_env = legacy_root / ".env"
    runtime_env = runtime_root / ".env"
    if _env_has_non_empty_key(legacy_env, "GOOGLE_API_KEY") and not _env_has_non_empty_key(
        runtime_env, "GOOGLE_API_KEY"
    ):
        check_warn(
            "GOOGLE_API_KEY only in legacy ~/.hermes/.env",
            "Run windows\\SYNC_HERMES_API_ENV.bat",
        )
        issues.append("Sync API keys (SYNC_HERMES_API_ENV.bat)")

    if should_fix:
        try:
            from hermes_cli.profile_switch import normalize_user_hermes_home
            from hermes_cli.doctor import check_ok

            normalized, msg = normalize_user_hermes_home(fix=True)
            if msg:
                if normalized:
                    check_ok("HERMES_HOME normalized", msg)
                else:
                    check_warn("HERMES_HOME", msg)
        except Exception:
            pass


def apply_doctor_fork_patch() -> None:
    import hermes_cli.doctor as doctor_mod

    if getattr(doctor_mod, "_fork_doctor_patch_applied", False):
        return
    doctor_mod._check_windows_split_home_config = check_windows_split_home_config  # type: ignore[attr-defined]
    doctor_mod._fork_doctor_patch_applied = True  # type: ignore[attr-defined]
