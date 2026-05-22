# Institutioneel E2E-audit — 22 mei 2026

**Script:** `windows/audits/RUN_INSTITUTIONAL_E2E.ps1`  
**Log:** `windows/audits/INSTITUTIONAL_E2E_LAST_RUN.log`  
**Resultaat:** **PASS** (8/8 stappen)

## Uitgevoerd in deze sessie

| Stap | Onderdeel | Status |
|------|-----------|--------|
| 1/8 | Repo-artefacten (25 bestanden incl. presentatie) | OK |
| 2/8 | pytest landkaart/orchestrator | 4 passed |
| 2b/8 | pytest presentatie (markdown, rich_output, normalize) | 22 passed |
| 2c/8 | `team_display.defaults` (render, skin, streaming=false, compact=false) | OK |
| 3/8 | landkaart CLI smoke | OK |
| 4/8 | `backup_soul_profiles` | OK (13 bestanden) |
| 5/8 | Runtime SOUL Interaction + landkaart | OK |
| 5b/8 | Runtime SOUL Outputformaat + `institutional_check` | OK (na `SYNC_SOUL_SNIPPETS.bat`) |
| 6/8 | Display config actief profiel (`core`) | OK (na `apply_team_display.ps1`) |
| 7/8 | rich_output smoke (pytest) | OK |
| 8/8 | RESTORE / UPDATE regressie | OK |

## Runtime-acties (lokaal uitgevoerd)

1. `windows\SYNC_SOUL_SNIPPETS.bat` — Outputformaat naar 10 SOUL-bestanden  
2. `windows\apply_team_display.ps1` — display-keys op profiel `core`

## Scriptfixes (repo)

- PowerShell-parserfouten in stap 6 (`$label - APPLY` → string-concatenatie)  
- Stap 6 controleert nu **profiel-config** (`profiles\<active>\config.yaml`), niet alleen root  
- `apply_team_display.ps1`: `HERMES_HOME` via `conda run --env-vars` naar actief profiel  
- Dubbele `else` en kapotte here-string in stap 7 verwijderd  

## Productie-gereedheid (institutioneel)

| Laag | Beoordeling |
|------|-------------|
| **Code & tests** | Ja — E2E + 26 pytest presentatie/landkaart groen |
| **Repo-documentatie** | Ja — `docs/INSTITUTIONAL_PRESENTATION.md`, templates, audits |
| **Runtime (deze machine)** | Ja — SOUL + profiel-display gesynchroniseerd |
| **Nieuwe chat vereist** | Ja — na SOUL-sync voor model-gedrag Outputformaat |
| **Overige profielen** | Let op — `legal` e.d. hebben eigen `compact: true` in profiel-config; alleen `core` is geaudit als actief profiel |

**Conclusie:** De app is **klaar voor institutioneel productieniveau** voor het **core-orchestrator**-pad, mits je na elke deploy opnieuw `SYNC_SOUL_SNIPPETS.bat` + `APPLY_TEAM_DISPLAY.bat` draait en een **nieuwe chat** start. Voor andere profielen: display per profiel toepassen of root `display.compact` harmoniseren.

## Herhaal audit

```bat
windows\audits\RUN_INSTITUTIONAL_E2E.bat
```

Of volledige keten: `windows\audits\RUN_AUDITS.bat -IncludeInstitutionalE2E`
