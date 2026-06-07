# NOUS drift baseline

Generated: **2026-06-07 03:41:20**
Compare: `HEAD` vs `upstream/main`

## Summary

| Metric | Count |
|--------|------:|
| All changed paths | 1250 |
| Tier A changed (must -> upstream) | 16 |
| Tier A changed (fork-intentional allowlist) | 1 |
| Tier A extra files (fork-only in Nous dirs) | 0 |
| Tier B / excluded | 1233 |
| Transitional (planned migration) | 0 |

## Tier A changed files (must -> upstream)

- `agent/secret_sources/bitwarden.py`
- `gateway/run.py`
- `hermes_cli/doctor.py`
- `hermes_cli/main.py`
- `hermes_cli/secrets_cli.py`
- `hermes_cli/tools_config.py`
- `hermes_cli/uninstall.py`
- `tools/computer_use/cua_backend.py`
- `tools/environments/ssh.py`
- `tools/osv_check.py`
- `tools/skill_manager_tool.py`
- `tools/skills_tool.py`
- `tui_gateway/server.py`
- `website/docs/reference/cli-commands.md`
- `website/docs/user-guide/configuration.md`
- `website/docs/user-guide/desktop.md`

## Tier A changed files (fork-intentional allowlist)

- `hermes_cli/gateway_windows.py` _(fork-intentional; zie HermesNousTierPaths.ps1)_

## Tier A extra files (not in upstream)

_None._

## Regenerate

```powershell
powershell -NoProfile -File windows/scripts/Export-NousDriftBaseline.ps1
```

See [NOUS_OVERLAY_ARCHITECTURE.md](NOUS_OVERLAY_ARCHITECTURE.md).
