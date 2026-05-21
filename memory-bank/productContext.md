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

Domeinprofielen verschillen in **MCP, SOUL, toolsets** — niet in inference-model. Het model staat centraal in `%LOCALAPPDATA%\hermes\config.yaml`, zodat een toekomstige wissel (bijv. ander Gemini/OpenRouter-model) **één keer** volstaat voor legal, core en alle andere profielen.

Zie `docs/PROFILE_MODEL_INHERITANCE.md`.

## Gebruikerservaring

- Windows-first: `.bat`-starters, taakbalk, geen conda in PATH vereist voor `hermes.bat`.
- `domains.yaml` en LanceDB buiten de repo (geen secrets, geen bulk-data in git).
- Live ingest-status en eindrapporten voor vertrouwen (“is legal klaar?”).
