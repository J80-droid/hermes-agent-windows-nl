# Fork test migratie backlog

SSOT: [`FORK_MERGE_POLICY.md`](FORK_MERGE_POLICY.md)

## Status 16 gewijzigde upstream-bestanden (merge-risico)

| Bestand | Status | Overlay / windows doel |
|---------|--------|------------------------|
| `test_web_server.py` | done | `tests/overlay/test_web_server_assistant_display.py`, `test_web_server_dashboard_plugins.py` |
| `test_gateway_windows.py` | done | `tests/windows/test_gateway_windows_virtual_env.py` |
| `test_apply_profile_override.py` | done | `tests/overlay/test_apply_profile_override_fork.py` |
| `test_config.py` | done | `tests/overlay/test_config_fork.py` |
| `test_doctor.py` | done | `tests/overlay/test_doctor_fork.py` |
| `test_relaunch.py` | done | `tests/overlay/test_relaunch_fork.py` |
| `test_model_validation.py` | done | `tests/overlay/test_model_validation_fork.py` |
| `test_tools_config.py` | done | `tests/overlay/test_tools_config_fork.py` |
| `test_update_check.py` | done | `tests/overlay/test_update_check_fork.py` |
| `test_curses_arrow_keys.py` | done | `tests/overlay/test_curses_arrow_keys_fork.py` |
| `test_curses_color_compat.py` | done | `tests/overlay/test_curses_color_compat_fork.py` |
| `test_runtime_provider_resolution.py` | done | `tests/overlay/test_runtime_provider_resolution_fork.py` |
| `test_setup_openclaw_migration.py` | done | `tests/overlay/test_setup_openclaw_migration_fork.py` |
| `test_skin_engine.py` | done | `tests/overlay/test_skin_engine_fork.py` |
| `test_update_concurrent_quarantine.py` | done | `tests/overlay/test_update_concurrent_quarantine_fork.py` |
| `test_model_provider_persistence.py` | done | `tests/overlay/test_model_provider_persistence_fork.py` |

Verificatie: `git diff --name-only --diff-filter=M upstream/main -- tests/hermes_cli/` → leeg.

## Fork-only bestanden (35) — deferred

Alleen migreren bij merge-conflict. Lijst: `windows/tests/fork_hermes_cli_test_exceptions.txt`.
