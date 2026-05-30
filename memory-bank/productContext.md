# Productcontext

## Probleem

Juridische en corporate bronnen staan verspreid over duizenden bestanden. De agent moet:

1. Die bronnen **doorzoekbaar** maken (LanceDB + embeddings).
2. In chat **betrouwbaar citeren** (`[Bron: bestandsnaam]`).
3. Per domein (legal, core, …) de **juiste** kennisbank gebruiken zonder verwarring.

## Oplossing (twee fasen)

| Fase | Wie | Wat |
|------|-----|-----|
| 1 — Bibliotheek | `update_knowledge.bat` + `domains.yaml` | Index bouwen in `lancedb/<domein>` |
| 2 — Balie | Hermes-profiel + MCP | Chat met `search_knowledge` op die index |

Zonder fase 1 is de index leeg. Zonder fase 2 weet de agent niet welke LanceDB bij de sessie hoort.

## Eén model voor alle balies

Domeinprofielen verschillen in **MCP, SOUL, `platform_toolsets.cli`** (minimaal per domein, opt-in via agent) — niet in inference-model. Het model staat centraal in `%LOCALAPPDATA%\hermes\config.yaml`, zodat een toekomstige wissel (bijv. ander Gemini/OpenRouter-model) **één keer** volstaat voor legal, core en alle andere profielen.

Zie `docs/PROFILE_MODEL_INHERITANCE.md`.

## Gebruikerservaring

- Windows-first: `.bat`-starters, taakbalk, geen conda in PATH vereist voor `hermes.bat`.
- **Windows Terminal:** minimize/maximize/sluiten op de WT-titelbalk moet werken; bij vastlopen: `windows\FIX_MOUSE_BLOCKED.bat` of `RESET_TERMINAL.bat` → alle tabs dicht → `start_hermes.bat` (klik op WT-chrome, niet het zwarte chatvlak). Zie `windows/MOUSE_OVERLAY_FIX.md`.
- `domains.yaml` en LanceDB buiten de repo (geen secrets, geen bulk-data in git).
- Live ingest-status en eindrapporten voor vertrouwen ("is legal klaar?").

## Team (14 profielen)

| Team | Profielen |
|------|-----------|
| Leadership | `core` |
| Legal | `legal` (arb, bbk, klok, aanspr, corp) |
| ICT | `ict` (infra, devops, support, sysadmin) |
| Security | `security` (pentest, compliance, incident, forensics) |
| Development | `dev` (backend, frontend, architecture, quality) |
| Data | `data` (database, analytics, pipeline, governance) |
| Creative | `creative` (visual, motion, interactive, writing) |
| Business | `operations`, `logistics`, `trading`, `ventures` |
| Kennis | `academics`, `philosophy`, `gaming` |

Alle profielen delen **één** inference-model (root `config.yaml`); verschillen in MCP, SOUL, `platform_toolsets.cli`.
