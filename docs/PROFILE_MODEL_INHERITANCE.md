# Profiel-config — overerven van root (model, auxiliary, providers)

Domein-profielen (`legal`, `core`, `academics`, …) gebruiken **dezelfde globale inference-config** als je centrale Hermes-installatie: model, auxiliary-taken en custom providers (bijv. Venice, Jatevo). Je hoeft die **niet** per profiel te onderhouden.

## Waar regel je globale config?

| Plek | Windows-pad | Gebruik |
|------|-------------|---------|
| **Root config** | `%LOCALAPPDATA%\hermes\config.yaml` | Enige plek voor `model`, `auxiliary`, `providers` / `custom_providers` |
| **`hermes model`** | schrijft naar root | Interactieve modelwijziging via `persist_model_runtime()` |
| **`hermes config set model.*`** | schrijft naar root | CLI-key-value |
| **Auxiliary preset** | `windows\APPLY_AUXILIARY_HYBRID_PRESET.bat` | Qwen lokaal + Gemini vision (root only) |
| **Venice / Jatevo / custom providers** | root config + `SYNC_HERMES_API_ENV.bat` | Checklist: [ADDING_CUSTOM_PROVIDER.md](ADDING_CUSTOM_PROVIDER.md) · templates: `PROVIDERS_VENICE.yaml`, `PROVIDERS_JATEVO.yaml` |
| **Profiel** | `%LOCALAPPDATA%\hermes\profiles\<naam>\config.yaml` | **Geen** global blocks (alleen MCP, toolsets, agent) |

Na wijziging van root config geldt het automatisch voor:

- `hermes -p legal chat`
- `hermes -p core doctor`
- gateway/cron onder elk profiel
- klassieke CLI (`load_cli_config`)
- model picker (Venice/Jatevo zodra `providers.*` + bijbehorende `*_API_KEY` in runtime `.env` staan)

## Wat staat wél in een domein-profiel?

```yaml
# model/auxiliary/providers: inherited from root config (runtime hermes/config.yaml).
# Change model globally: hermes model
# Auxiliary: windows\APPLY_AUXILIARY_HYBRID_PRESET.bat
# MCP wordt gesynchroniseerd vanuit %USERPROFILE%\data\domains.yaml:
#   python scripts/rag_pipeline/sync_profile_mcp_from_domains.py
mcp_servers:
  lancedb-legal:
    command: C:\...\miniconda3\envs\hermes-env\python.exe
    args:
      - D:\...\hermes-agent\scripts\rag_pipeline\mcp_server.py
    env:
      HERMES_LANCEDB_PATH: C:\Users\...\data\lancedb\legal
      HERMES_REPO_ROOT: D:\...\hermes-agent
      PYTHONIOENCODING: utf-8
platform_toolsets:
  cli:
    - mcp
    - file
    - memory
    - skills
    # volledige lijst: docs/domain_toolsets.yaml + SYNC_DOMAIN_TOOLSETS.bat
agent:
  max_turns: 30
```

**Let op:** het oude nested formaat `mcp.servers` wordt door Hermes CLI/chat **genegeerd** — gebruik alleen `mcp_servers:` op root-niveau in het profiel-yaml.

## Automatisch bij `hermes profile create`

Na aanmaken van een profiel (met of zonder `--clone`):

1. **`strip_model_block_from_profile_config`** — verwijdert een gekopieerd `model:`-blok en zet een inheritance-comment in `config.yaml` (fork; zie `hermes_cli/profile_model_inheritance.py`).
2. **`_maybe_register_gateway_service`** — upstream Phase 4: in Docker/s6 registreert het een gateway-slot; op Windows/host is dit een stille no-op.

Bij `--clone` / `--clone-config` wordt `config.yaml` eerst gekopieerd en daarna gestript. Unit tests: `tests/overlay/test_profiles_create_model_strip.py`.

## Commando’s (cheatsheet)

| Actie | Commando |
|-------|----------|
| Model kiezen (alle profielen) | `hermes model` of `hermes.bat model` |
| Model in profiel-modus | `hermes -p legal model` → schrijft nog steeds naar **root** |
| Config controleren | `hermes -p legal doctor` |
| Oude `model:` / `auxiliary:` / `providers:` in profielen opruimen | `hermes doctor --fix` of `strip_profile_global_config_blocks.py` |
| Alleen root-config bewerken | `hermes config edit` (zonder `-p`) of handmatig root yaml |

## Veelgemaakte fouten

| Symptoom | Oorzaak | Oplossing |
|----------|---------|-----------|
| Doctor toont OpenRouter terwijl root Gemini is | Verouderd `model:`-blok in `profiles\legal\config.yaml` | `hermes doctor --fix` of handmatig blok verwijderen |
| Auxiliary in profiel-yaml (core) | Stale `auxiliary:` na preset | `APPLY_HERMES_HOME_MIGRATION.bat` of strip-script |
| Venice ontbreekt in model picker | `providers.venice` niet in root of key niet gesynced | `merge_legacy_providers_config.py` + `SYNC_HERMES_API_ENV.bat` |
| Jatevo ontbreekt of 401 | `providers.jatevo` / `JATEVO_API_KEY` / verkeerde host | `base_url: https://jatevo.ai/v1`; sync `.env`; `hermes model` → jatevo → Replace key |
| `search_knowledge` niet geladen in chat | `mcp.servers` i.p.v. `mcp_servers` in profiel | `sync_profile_mcp_from_domains.py` of `hermes doctor --fix` |
| Chat 401 / verkeerde provider | Profiel had eigen model; keys in root `.env` | Root model + keys in `%LOCALAPPDATA%\hermes\.env` |
| `hermes -p legal model` lijkt profiel te wijzigen | Oud gedrag vóór overerving | Update repo; model gaat naar root |
| Auth `nous`, chat nog Gemini | Split-brain auth vs `model.provider` | `hermes doctor --fix` of `windows\REPAIR_MODEL_PROVIDER.bat` |
| Gateway start met oude config | Incoherentie alleen WARN | Optioneel `HERMES_STRICT_CONFIG_COHERENCE=1` vóór gateway (weigert start tot repair) |
| Vendor-slug (`deepseek/...`) op verkeerde provider | Alleen default gezet, provider oud | `hermes model` opnieuw; doctor meldt `vendor_slug_wrong_provider` |

**API-keys:** profielen hebben eigen `.env` voor tokens; het **model** komt uit root. Bij 401: controleer provider-key voor het **effectieve** model (doctor toont inherited model).

## Bewuste uitzondering (zelden)

Alleen als één profiel **afwijkend** moet zijn van root:

```yaml
model:
  inherit: false
  provider: openrouter
  default: openrouter/anthropic/claude-sonnet-4
```

Zelfde patroon voor `auxiliary.inherit: false` of `providers.inherit: false`. Dan schrijft `save_config` wél naar **dat** profiel-config voor het betreffende blok.

## Technisch

| Onderdeel | Gedrag |
|-----------|--------|
| `hermes_cli/model_runtime_config.py` | `persist_model_runtime`, coherence detect/repair; root + auth sync |
| `hermes_cli/profile_model_inheritance.py` | Resolve model/auxiliary/providers; strip; root-save; `root_config_path()`; `bust_config_caches()` |
| `apply_profile_root_config_inheritance()` | Eén root YAML-read per load; merged model + auxiliary + providers |
| `load_config()` | Past overerving toe; ook zonder profiel-`config.yaml` |
| `load_cli_config()` | Zelfde voor klassieke CLI/chat |
| `save_config()` | Profiel: global blocks uit normalized poppen; redirect naar root **alleen** als key in meegegeven `config` dict |
| `set_config_value()` / `cli.save_config_value` | `model.*` / `auxiliary.*` / `providers.*` → root pad |
| `merge_legacy_providers_config.py` / `collect_env_sync_keys.py` | Altijd runtime root (niet profiel-`HERMES_HOME`) |
| `hermes profile create` | Stript global blocks na `--clone` / `--clone-all` |
| `hermes doctor` | Meldt inheritance + Venice/Jatevo gaps; `--fix` stript stale blokken |
| Tests | `test_profile_model_inheritance.py`, `test_model_runtime_config.py` (45), `test_doctor_model_coherence.py`, `test_merge_legacy_providers_config.py` |
| E2E | `audits/RUN_MODEL_PROVIDER_COHERENCE_E2E.bat` (**10/10**) · `RUN_ROOT_CONFIG_INHERITANCE_E2E.bat` (**10/10**) |

## Relatie met RAG

- **Indexeren** (`domains.yaml`) — geen model; batch-job.
- **Chatten** (profiel + MCP) — model uit root; MCP wijst naar LanceDB.

Zie [RAG_TWEE_FASEN.md](RAG_TWEE_FASEN.md) en [README.md](README.md).

## Zie ook

- [domains.yaml.example](domains.yaml.example) — nieuw domein + profiel zonder `model:`
- [../../HERMES_START.md](../../HERMES_START.md) — `hermes.bat` zonder conda
- [../windows/README.md](../windows/README.md) — Windows-workflow
