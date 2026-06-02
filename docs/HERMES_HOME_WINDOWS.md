# Hermes home op Windows (split-home runbook)

Deze fork gebruikt **twee bewuste locaties** — geen symlink, geen blind overschrijven.

| Pad | Rol |
| --- | --- |
| `%LOCALAPPDATA%\hermes\` | **Runtime / canoniek** — `config.yaml`, sessions, auth, SOUL, profielen |
| `%USERPROFILE%\.hermes\` | **Legacy hub** — vooral `.env` (API-keys bron) + `_local_assets`; **geen actieve `config.yaml`** |

**Submappen onder runtime (fork):**

| Submap | Rol |
| --- | --- |
| `VectorStore\<domein>\` | Default LanceDB-pad wanneer `HERMES_LANCEDB_PATH` niet gezet is (`lancedb_storage.py`) |
| `workspace\` | Default agent file-tool sandbox wanneer `workspace.root` leeg is |

Zie [WINDOWS_PLATFORM_HARDENING.md](WINDOWS_PLATFORM_HARDENING.md).

## Productie-poorten (fork)

| Poort | Commando | Wanneer |
| --- | --- | --- |
| Dagelijks | `windows\POST_GIT_PULL.bat` | Na `git pull` |
| Start | **`start_hermes.bat`** (repo-root; WT) | Elke sessie |
| Wekelijks | `windows\audits\RUN_AUDITS.bat` | Kwaliteit |
| Release | `windows\audits\RUN_AUDITS.bat -IncludeAllE2E` | Vóór grote wijziging |
| Config wijziging | `APPLY_AUXILIARY_HYBRID_PRESET.bat` + `hermes config get auxiliary` | Eenmalig / na model pull |
| **Split-home migratie (eenmalig)** | `APPLY_HERMES_HOME_MIGRATION.bat` | Backup → deprecate → preset → Venice merge → strip → env sync → E2E |

## Twee checkouts (footgun)

| Wat | Pad |
| --- | --- |
| **Dev-repo (start hier)** | `start_hermes.bat` in je fork (bijv. `Hermes_agent_WS\hermes-agent`; intern `windows\launch_hermes.bat`) |
| Nous clone (optioneel) | `%LOCALAPPDATA%\hermes\hermes-agent` — **niet** mengen met fork/RAG zonder keuze |
| Config leeft in | `%LOCALAPPDATA%\hermes\` — **niet** in de repo |

Diagnose: `windows\scripts\which_hermes_repo.ps1`

## WSL-coexistentie

Native Windows Hermes gebruikt `%LOCALAPPDATA%\hermes`. WSL-sessies kunnen parallel `~/.hermes` hebben — dat zijn **gescheiden** runtimes. Wijzig nooit Windows-config vanuit WSL-paden tenzij je bewust in WSL-Hermes werkt.

## Dagelijks

| Actie | Commando |
| --- | --- |
| Start Hermes | **`start_hermes.bat`** (repo-root; Windows Terminal) |
| Dagelijks | **`start_hermes.bat`** — pull+sync+relaunch alleen als nodig; anders direct start |
| Forceer pull | `start_hermes.bat --pull` of `PULL_HERMES.bat` |
| Na handmatige pull | `start_hermes.bat --sync` of `windows\POST_GIT_PULL.bat` |
| Relaunch uit | `-SkipRelaunch` / `HERMES_SKIP_RELAUNCH_AFTER_PULL=1` · auto-pull uit: `HERMES_SKIP_AUTO_PULL_ON_START=1` |
| Volledige preset na pull | `POST_GIT_PULL.bat -Full` (= AutoRepair + InstitutionalVerify + relaunch) |
| Nous upstream | `UPDATE_HERMES.bat` (zelfde relaunch na post-merge) |
| Wekelijkse kwaliteit | `windows\audits\RUN_AUDITS.bat` |
| Config drift check | `windows\VERIFY_HERMES_CONFIG_DRIFT.bat` |

## Config wijzigen (altijd runtime)

- **CLI:** `hermes config set …`, `hermes model`, `hermes doctor`
- **Niet:** `write_file` / handmatig yaml in `~/.hermes\config.yaml`
- **Verify:** `hermes config get auxiliary` of `hermes config get auxiliary.vision.provider`

Canoniek bestand: `%LOCALAPPDATA%\hermes\config.yaml`

## API-keys (secrets)

1. Bron vaak: `%USERPROFILE%\.hermes\.env`
2. Sync naar runtime + profielen: `windows\SYNC_HERMES_API_ENV.bat`
3. Na sync: `hermes doctor` — geen "key only in legacy" WARN

## Model/provider split-brain (auth vs config)

Symptoom: `auth.json` heeft `active_provider: nous` maar chat gebruikt nog **Gemini** (`model.provider: gemini` in root config, soms met verkeerde `base_url`).

| Stap | Actie |
|------|--------|
| 1 | `windows\REPAIR_MODEL_PROVIDER.bat` of `hermes doctor --fix` |
| 2 | `hermes config get model.provider` → verwacht jouw gekozen provider (bijv. `nous`) |
| 3 | Automatisch via `PULL_HERMES.bat` / `POST_GIT_PULL.bat` (relaunch + verse SOUL); TUI: auto `/new`; klassieke CLI: notice bij start |

**Checklist na code-deploy (operationeel):** `PULL_HERMES.bat` of `git pull` + `POST_GIT_PULL.bat -Full` → Hermes opent in nieuw WT-tabblad → `hermes config get model.provider` → eerste bericht: juiste provider (geen `generativelanguage` in routing). Geautomatiseerde check: `audits\RUN_POST_GIT_PULL_AUTOMATION_E2E.bat`.

**Optionele git-hook (lokaal, niet in repo):** `post-merge` → `windows\POST_GIT_PULL.bat`

**Architectuur (repo):** `hermes_cli/model_runtime_config.py` · `hermes_cli/auth.read_auth_json()` (UTF-8 BOM-safe)

- `persist_model_runtime()` — atomisch `model.provider`, `model.default`, `base_url` naar **root** + sync `auth.active_provider`
- `detect_model_provider_incoherence()` — auth/config-mismatch, vendor-slug vs provider, stale host in `base_url`
- `repair_model_provider_coherence()` — herstel (default: config volgt auth)

**Oorzaak (opgelost):** oude flows schreven alleen `model.default` vóór `model.provider`, naar profiel-yaml i.p.v. root, of wisten `active_provider` na persist via `deactivate_provider()`. Gebruik `hermes model` / setup; intern via `_commit_provider_model()`.

**Validatie:** `audits\RUN_MODEL_PROVIDER_COHERENCE_E2E.bat` (10) · `audits\RUN_MODEL_PROVIDER_HARDENING_E2E.bat` (8: BOM, corrupt auth, global blocks, drift error-gate) · `RUN_AUDITS.bat -IncludeModelProviderCoherenceE2E` / `-IncludeModelProviderHardeningE2E` · `verify_hermes_config_drift.ps1` (coherence, error-severity) · pytest `tests/hermes_cli/test_model_runtime_config.py`, `test_auth_json_store.py`, `test_profile_model_inheritance.py`

**POST_GIT_PULL opt-in:** `POST_GIT_PULL.bat -AutoRepairModelProvider` — bij drift-check éénmalig `repair_model_provider_coherence.ps1` vóór fail (standaard uit).

**Gateway strict (optioneel):** `set HERMES_STRICT_CONFIG_COHERENCE=1` vóór gateway-start weigert start bij model/provider-incoherentie (standaard alleen WARN in logs).

## Gemini / auth.json (HTTP 400)

Symptoom: keys gesynced maar vision/Gemini faalt met HTTP 400.

1. `hermes doctor` — auth.json health
2. `windows\FIX_GEMINI_CREDENTIAL_POOL.bat`
3. `verify_hermes_home.ps1` (repareert corrupt auth.json indien nodig)

## Kanban & subprocessen

Kanban-workers krijgen `HERMES_HOME` geïnjecteerd (`hermes_cli/kanban_db.py`). **Root moet** `%LOCALAPPDATA%\hermes` zijn (niet `profiles\<naam>`). Launch-keten zet proces-env vóór `conda run`.

## Eenmalig: split-home migratie (aanbevolen)

**Eén commando** (backup → deprecate → auxiliary preset → Venice merge → strip profielen → env sync → E2E):

```bat
windows\APPLY_HERMES_HOME_MIGRATION.bat
```

Keten (7 stappen): backup → deprecate → auxiliary preset → merge legacy providers (Venice) → strip profile global blocks → sync API env → HermesHome E2E (14 checks).

Hermes/gateway moet **volledig gestopt** zijn vóór start. Her-run na eerdere backup:

```bat
windows\APPLY_HERMES_HOME_MIGRATION.bat -SkipBackup -NoPause
```

### Handmatig (losse stappen)

```bat
windows\MANAGE_BACKUPS.bat
windows\DEPRECATE_LEGACY_CONFIG.bat
windows\APPLY_AUXILIARY_HYBRID_PRESET.bat
windows\scripts\merge_legacy_providers_config.py
windows\SYNC_HERMES_API_ENV.bat
windows\audits\RUN_HERMES_HOME_E2E.bat
windows\audits\RUN_ROOT_CONFIG_INHERITANCE_E2E.bat
```

Optioneel alleen ontbrekende auxiliary keys kopiëren bij deprecate:

```powershell
powershell -File windows\scripts\deprecate_legacy_config.ps1 -CopyAuxiliaryOnly
```

## Auxiliary preset (Qwen lokaal + Gemini vision)

Preset dekt **8 tekst-taken** + vision. **Niet** in preset (blijven `auto`/main): `kanban_decomposer`, `profile_describer`, `goal_judge`. `session_search` auxiliary slot is legacy (genegeerd door code).

```bat
windows\APPLY_AUXILIARY_HYBRID_PRESET.bat
hermes config get auxiliary.vision.provider
```

Preflight: Ollama op `http://localhost:11434/v1`, `GOOGLE_API_KEY` in runtime `.env`. Na apply: `/new` in TUI (reminder via `institutional_new_chat_required.json`).

## Global config (root only)

Deze keys horen **alleen** in `%LOCALAPPDATA%\hermes\config.yaml` (root), niet in `profiles\<naam>\config.yaml`:

| Blok | Beheer |
| --- | --- |
| `model:` | `hermes model` / root config |
| `auxiliary:` | `APPLY_AUXILIARY_HYBRID_PRESET.bat` |
| `providers:` / `custom_providers:` | Model picker; templates: `docs/templates/PROVIDERS_VENICE.yaml`, `docs/templates/PROVIDERS_JATEVO.yaml` |

Profiel-modus (`active_profile=core`) erft deze blokken automatisch van root via `profile_model_inheritance.py`. Stale profiel-blokken: `strip_profile_global_config_blocks.py` of migratie-keten. Partial profiel-save (bijv. alleen `agent.max_turns`) overschrijft root `providers` **niet**.

## Venice, Jatevo + custom providers

Legacy `providers.venice` / `providers.jatevo` worden gemerged via migratie-keten. API-keys: `SYNC_HERMES_API_ENV.bat` (incl. `VENICE_API_KEY`, `JATEVO_API_KEY`). Model picker toont custom providers zodra root config + runtime `.env` kloppen. Nieuwe provider: [ADDING_CUSTOM_PROVIDER.md](ADDING_CUSTOM_PROVIDER.md).

**Venice DIEM** (`agent/venice_usage.py`, template `docs/templates/PROVIDERS_VENICE.yaml`):
- Statusbalk **`VN 90/100`** of **`VN 9.5 DIEM`** — alleen `GET /billing/balance` + `GET /api_keys/rate_limits` (90s cache).
- **`/vquota`** en **`/usage`** — extended APIs parallel: [billing/usage](https://docs.venice.ai/api-reference/endpoint/billing/usage), [usage-analytics](https://docs.venice.ai/api-reference/endpoint/billing/usage-analytics) (beta), [rate_limits/log](https://docs.venice.ai/api-reference/endpoint/api_keys/rate_limit_logs), [models/traits](https://docs.venice.ai/api-reference/endpoint/models/traits), [compatibility_mapping](https://docs.venice.ai/api-reference/endpoint/models/compatibility_mapping). Bij gedeeltelijke HTTP-fouten: regels in `extended_errors`.
- **`hermes model` / setup → Venice:** trait-filter + OpenAI-mapping; setup vraagt optioneel `extra_body.venice_parameters` (web search, `character_slug`).
- **Telegram `/model` → Venice:** helper-menu (`vf:all`, `vf:t:N`, `vf:o:N`) vóór de modellenlijst; vereist `VENICE_API_KEY` in runtime `.env`.
- **Typed `/model` (alle platforms):** `gpt-4o --provider venice` wordt via `compatibility_mapping` naar Venice-model-id vertaald.
- Chat-opties in config: `providers.venice.extra_body.venice_parameters`. Bij **429** → hint naar `/vquota`.

**Jatevo:** `hermes model` → key-stap → live `/v1/models`; base URL **`https://jatevo.ai/v1`**; **`/jquota`**, statusbalk **`JV 0/562`** (`GET /v1/usage`, 90s cache); **429** → `/jquota`. Code: `agent/jatevo_usage.py`.

## Drift / diagnose

| Symptoom | Fix |
| --- | --- |
| Agent schrijft config op verkeerd pad | `DEPRECATE_LEGACY_CONFIG.bat`; SOUL governance snippet sync |
| Twee verschillende auxiliary-blokken | `VERIFY_HERMES_CONFIG_DRIFT.bat` → migratie |
| Auxiliary in profiel-yaml (core) | `APPLY_HERMES_HOME_MIGRATION.bat` (strip + preset) |
| Venice/Jatevo ontbreekt in picker | `merge_legacy_providers_config.py` + `SYNC_HERMES_API_ENV.bat` |
| Tekst-aux nog op `provider: auto` | `APPLY_AUXILIARY_HYBRID_PRESET.bat` |
| `HERMES_HOME=profiles\…` | `hermes profile use <naam> --fix-hermes-home` |
| Gateway verkeerde home | `VERIFY_GATEWAY_HOME.bat` → `REPAIR_GATEWAY_HOME.bat` |
| Na restore backup | Automatisch: `Ensure-UserHermesHomeRoot` + sync; deprecate opnieuw indien stub terug |

## Inventaris & E2E

```bat
windows\INVENTORY_HERMES_HOME.bat
windows\audits\RUN_HERMES_HOME_E2E.bat
windows\audits\RUN_ROOT_CONFIG_INHERITANCE_E2E.bat
windows\audits\RUN_AUDITS.bat -IncludeHermesHomeE2E
```

**Root-inheritance E2E** (`RUN_ROOT_CONFIG_INHERITANCE_E2E.bat`): **10/10 PASS** — pytest inheritance/merge, isolated harness (8 scenario's), `py_compile`-guard op env-sync script, runtime Venice + profiel auxiliary inheritance.

**HermesHome E2E** (`RUN_HERMES_HOME_E2E.bat`): **16/16 PASS** — split-home drift, Venice/Jatevo env, auxiliary inheritance live checks.

## Feature flag (Python fallback)

`HERMES_WIN_PREFER_LOCALAPPDATA=1` (default): als `HERMES_HOME` unset is en runtime `config.yaml` bestaat, gebruikt Python `%LOCALAPPDATA%\hermes`. Uitzetten: `HERMES_WIN_PREFER_LOCALAPPDATA=0`.

Zie ook: `windows\INSTITUTIONAL.md` §5c, `docs\USER_DATA_OPERATIONS.md`.
