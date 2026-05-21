# Profiel-model — overerven van root config

Domein-profielen (`legal`, `core`, `academics`, …) gebruiken **hetzelfde inference-model** als je centrale Hermes-installatie. Je hoeft het model **niet** per profiel te onderhouden.

## Waar regel je het model?

| Plek | Windows-pad | Gebruik |
|------|-------------|---------|
| **Root config** | `%LOCALAPPDATA%\hermes\config.yaml` | Enige plek voor standaard `model` + `provider` |
| **`hermes model`** | schrijft naar root | Interactieve wijziging |
| **`hermes config set model.*`** | schrijft naar root | CLI-key-value |
| **Profiel** | `%LOCALAPPDATA%\hermes\profiles\<naam>\config.yaml` | **Geen** `model:` (alleen MCP, toolsets, agent) |

Na `hermes model` of een edit van root config geldt het nieuwe model **automatisch** voor:

- `hermes -p legal chat`
- `hermes -p core doctor`
- gateway/cron onder elk profiel
- klassieke CLI (`load_cli_config`)

## Wat staat wél in een domein-profiel?

```yaml
# model/provider: inherited from root config (~/.hermes/config.yaml).
# Change model globally: hermes model
mcp:
  servers:
    lancedb-legal:
      command: ...
      args: [.../mcp_server.py]
      env:
        HERMES_LANCEDB_PATH: C:\Users\...\data\lancedb\legal
enabled_toolsets:
  - mcp
  - file
agent:
  max_turns: 30
```

## Commando’s (cheatsheet)

| Actie | Commando |
|-------|----------|
| Model kiezen (alle profielen) | `hermes model` of `hermes.bat model` |
| Model in profiel-modus | `hermes -p legal model` → schrijft nog steeds naar **root** |
| Config controleren | `hermes -p legal doctor` |
| Oude `model:` in profielen opruimen | `hermes doctor --fix` |
| Alleen root-config bewerken | `hermes config edit` (zonder `-p`) of handmatig root yaml |

## Veelgemaakte fouten

| Symptoom | Oorzaak | Oplossing |
|----------|---------|-----------|
| Doctor toont OpenRouter terwijl root Gemini is | Verouderd `model:`-blok in `profiles\legal\config.yaml` | `hermes doctor --fix` of handmatig `model:` verwijderen |
| Chat 401 / verkeerde provider | Profiel had eigen model; keys in root `.env` | Root model + keys in `%LOCALAPPDATA%\hermes\.env` |
| `hermes -p legal model` lijkt profiel te wijzigen | Oud gedrag vóór overerving | Update repo; model gaat naar root |

**API-keys:** profielen hebben eigen `.env` voor tokens; het **model** komt uit root. Bij 401: controleer provider-key voor het **effectieve** model (doctor toont inherited model).

## Bewuste uitzondering (zelden)

Alleen als één profiel een **ander** model moet dan de rest:

```yaml
model:
  inherit: false
  provider: openrouter
  default: openrouter/anthropic/claude-sonnet-4
```

Dan schrijft `hermes model` / `save_config` wél naar **dat** profiel-config.

## Technisch

| Onderdeel | Gedrag |
|-----------|--------|
| `hermes_cli/profile_model_inheritance.py` | Resolve, strip, root-save helpers |
| `load_config()` | Past overerving toe; ook zonder profiel-`config.yaml` |
| `load_cli_config()` | Zelfde voor klassieke CLI/chat |
| `save_config()` | Profiel: model naar root; rest naar profiel-yaml |
| `set_config_value()` / `cli.save_config_value` | `model.*` → root pad |
| `hermes profile create` | Stript `model:` na `--clone` / `--clone-all` |
| `hermes doctor` | Meldt inheritance; `--fix` stript stale blokken |
| Tests | `tests/hermes_cli/test_profile_model_inheritance.py` |

## Relatie met RAG

- **Indexeren** (`domains.yaml`) — geen model; batch-job.
- **Chatten** (profiel + MCP) — model uit root; MCP wijst naar LanceDB.

Zie [RAG_TWEE_FASEN.md](RAG_TWEE_FASEN.md) en [README.md](README.md).

## Zie ook

- [domains.yaml.example](domains.yaml.example) — nieuw domein + profiel zonder `model:`
- [../../HERMES_START.md](../../HERMES_START.md) — `hermes.bat` zonder conda
- [../windows/README.md](../windows/README.md) — Windows-workflow
