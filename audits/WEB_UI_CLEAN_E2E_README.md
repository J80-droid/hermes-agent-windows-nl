# Web UI clean codebase E2E

Geïsoleerde E2E voor de recente Web UI-hardening: schone `npm run lint` / `npm run build`, PTY-channel-contract, hooks/context-splits, OAuth lifecycle, team-display import.

Geen live browser of dashboard op poort 9119 (wel `npm run build`, ~1–2 min).

| ID | Scenario | Verwachting |
|----|----------|-------------|
| W1 | Repo-artefacten | `useTooltipAnchor`, `useDropUpFixedStyle`, `gatewayLine`, context-splits |
| W2 | ChatPage channel | `resume-${resumeParam}`; geen `:`; regex `^[A-Za-z0-9._-]{1,128}$` |
| W3 | institutionalMarkdown | `_headingLine` in `shouldAttemptPseudoNormalize` |
| W4 | `npm run lint` | exit 0 |
| W5 | `npm run build` | tsc + vite exit 0 |
| W6 | web_dist | `hermes_cli/web_dist/index.html` |
| W7 | apply_team_display | `utils` import via `sys.path`; geen ModuleNotFoundError |
| W8 | pytest | `tests/hermes_cli/test_web_ui_build.py` |
| W9 | pytest | `tests/windows/test_apply_team_display_root.py` |
| W10 | PluginPage | `createElement` + `useSyncExternalStore` |
| W11 | OAuthProvidersCard | unmount guard (`active`) |

```bat
audits\RUN_WEB_UI_CLEAN_E2E.bat
```

Vereisten: Node.js/npm op PATH; Python `hermes-env` (of `HERMES_AUDIT_PYTHON`).
