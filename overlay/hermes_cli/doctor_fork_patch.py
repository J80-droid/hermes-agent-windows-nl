"""Windows split-home + profile global-blocks doctor checks (Tier B overlay)."""
from __future__ import annotations

import logging
import os
import sys
from functools import wraps
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


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
            logger.debug("HERMES_HOME normalize during doctor --fix failed", exc_info=True)


def check_profile_global_config_blocks(issues: list, *, should_fix: bool = False) -> None:
    """Warn when domain profiles still define auxiliary/providers locally."""
    try:
        from hermes_cli.doctor import check_ok, check_warn
        from hermes_cli.profile_model_inheritance import (
            list_profiles_with_global_config_blocks,
            strip_all_profile_global_blocks,
        )

        profiles = list_profiles_with_global_config_blocks()
        if profiles:
            names = ", ".join(profiles)
            check_warn(
                f"Profile(s) with local auxiliary/providers blocks: {names}",
                "Global blocks belong in root config — run windows\\scripts\\strip_profile_global_config_blocks.py",
            )
            for name in profiles:
                issues.append(f"Strip global config blocks from profile '{name}'")

        if should_fix and profiles:
            stripped = strip_all_profile_global_blocks()
            if stripped:
                check_ok("Stripped global blocks from profiles", ", ".join(stripped))
                issues[:] = [
                    issue
                    for issue in issues
                    if not issue.startswith("Strip global config blocks from profile ")
                ]
    except ImportError:
        logger.debug("profile_model_inheritance unavailable for global-blocks check")
    except Exception:
        logger.warning("profile global-blocks check failed", exc_info=True)


def _run_fork_doctor_checks(args: Any) -> None:
    should_fix = bool(getattr(args, "fix", False))
    fork_issues: list = []
    check_windows_split_home_config(fork_issues, should_fix=should_fix)
    check_profile_global_config_blocks(fork_issues, should_fix=should_fix)


def apply_doctor_fork_patch() -> None:
    import hermes_cli.doctor as doctor_mod

    if getattr(doctor_mod, "_fork_doctor_patch_applied", False):
        return

    doctor_mod._check_windows_split_home_config = check_windows_split_home_config  # type: ignore[attr-defined]
    doctor_mod._check_profile_global_config_blocks = check_profile_global_config_blocks  # type: ignore[attr-defined]

    _orig_run_doctor = doctor_mod.run_doctor

    @wraps(_orig_run_doctor)
    def run_doctor_patched(args):
        _run_fork_doctor_checks(args)
        return _orig_run_doctor(args)

    doctor_mod.run_doctor = run_doctor_patched  # type: ignore[assignment]
    doctor_mod._fork_doctor_patch_applied = True  # type: ignore[attr-defined]
