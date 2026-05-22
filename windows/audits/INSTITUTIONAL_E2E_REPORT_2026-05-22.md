# Institutioneel E2E-audit — 22 mei 2026

**Script:** `windows/audits/RUN_INSTITUTIONAL_E2E.ps1`  
**Log:** `windows/audits/INSTITUTIONAL_E2E_LAST_RUN.log`  
**Stappen:** **11** (was 8)

## Resultaat

**Resultaat:** **PASS** (11/11) — laatste run na regex-fix `verander profiel naar <naam>` en stap-11 one-liner smoke.

## Stappenoverzicht

| Stap | Onderdeel |
|------|-----------|
| 1/11 | Repo-artefacten |
| 2/11 | pytest landkaart/orchestrator |
| 2b/11 | pytest presentatie (markdown, rich_output) |
| 2c/11 | `team_display.defaults` |
| **2d/11** | **Profiel-chat-UX** (`test_institutional_profile_chat_ux.py`) |
| **2e/11** | **pytest institutional Rich renderer** (demo-palet, per-kolom tabellen, label-kolommen) |
| 3/11 | landkaart CLI smoke |
| 4/11 | `backup_soul_profiles` |
| 5/11 | Runtime SOUL Interaction |
| 5b/11 | Runtime SOUL Outputformaat |
| **5c/11** | **SOUL profielwissel-regel (alle profielen)** |
| 6/11 | Display config alle profielen (`assistant_render_style`, `assistant_palette`, `assistant_label_columns`) |
| 7/11 | rich_output smoke |
| 8/11 | RESTORE / UPDATE regressie |
| **9/11** | **pytest profielwissel-subset** |
| **10/11** | **SWITCH legal → core** |
| **11/11** | **CLI intent smoke** (geen LLM) |

## Wat de E2E níet deed (en nu deels wel)

| Oorspronkelijke gap | Status in audit |
|--------------------|-----------------|
| Chat: “schakel naar core” → model zegt `/profile use core` | **Niet** geautomatiseerd (geen LLM). CLI-intent wisselt sticky profiel vóór agent (2d, 11). |
| Prompt direct `core ❯` na natuurlijke taal | **Deels:** 2d test `get_active_profile` in prompt; geen live TUI na zin in lopende sessie. |
| Volledige profielwissel-E2E in deze keten | **Deels:** 9–10; volledig blijft `RUN_PROFILE_SWITCH_E2E.bat`. |
| SOUL-regels gevolgd in lange sessie | **Niet:** 5c = tekst op schijf; nieuwe chat vereist voor model-gedrag. |
| Rich-demo per-kolom tabellen + label-kolommen | **Ja** (CLI/gateway/Ink/Web) via `assistant_render_style=institutional_rich` |

## Handmatige acceptatie (Rich renderer)

- ACTIEPLAN: witregel tussen `## Stap 1` en `## Stap 2`
- Tabel: verschillende kleuren per kolomkop (niet één gouden accent)
- Antwoordtekst: demo-palet; Hermes-banner blijft skin-goud

## Herhaal audit

```bat
windows\audits\RUN_INSTITUTIONAL_E2E.bat
```

Of: `windows\APPLY_INSTITUTIONAL_RUNTIME.bat` (display + SOUL + E2E).
