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
| Start | `windows\launch_hermes.bat` | Elke sessie |
| Wekelijks | `windows\audits\RUN_AUDITS.bat` | Kwaliteit |
| Release | `windows\audits\RUN_AUDITS.bat -IncludeAllE2E` | Vóór grote wijziging |
| Config wijziging | `APPLY_AUXILIARY_HYBRID_PRESET.bat` + `hermes config get auxiliary` | Eenmalig / na model pull |
| **Split-home migratie (eenmalig)** | `APPLY_HERMES_HOME_MIGRATION.bat` | Backup → deprecate → preset → Venice merge → strip → env sync → E2E |

## Twee checkouts (footgun)

| Wat | Pad |
| --- | --- |
| **Dev-repo (start hier)** | `windows\launch_hermes.bat` in je fork (bijv. `Hermes_agent_WS\hermes-agent`) |
| Nous clone (optioneel) | `%LOCALAPPDATA%\hermes\hermes-agent` — **niet** mengen met fork/RAG zonder keuze |
| Config leeft in | `%LOCALAPPDATA%\hermes\` — **niet** in de repo |

Diagnose: `windows\scripts\which_hermes_repo.ps1`

## WSL-coexistentie

Native Windows Hermes gebruikt `%LOCALAPPDATA%\hermes`. WSL-sessies kunnen parallel `~/.hermes` hebben — dat zijn **gescheiden** runtimes. Wijzig nooit Windows-config vanuit WSL-paden tenzij je bewust in WSL-Hermes werkt.

## Dagelijks

| Actie | Commando |
| --- | --- |
| Start Hermes | `windows\launch_hermes.bat` |
| Na `git pull` / update | `POST_GIT_PULL.bat` of `UPDATE_HERMES.bat` |
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
| `providers:` / `custom_providers:` | Model picker; Venice: `docs/templates/PROVIDERS_VENICE.yaml` |

Profiel-modus (`active_profile=core`) erft deze blokken automatisch van root via `profile_model_inheritance.py`. Stale profiel-blokken: `strip_profile_global_config_blocks.py` of migratie-keten. Partial profiel-save (bijv. alleen `agent.max_turns`) overschrijft root `providers` **niet**.

## Venice + custom providers

Legacy `providers.venice` wordt gemerged via migratie-keten. API-key: `SYNC_HERMES_API_ENV.bat` (incl. `VENICE_API_KEY`). Model picker toont Venice zodra config + runtime `.env` kloppen.

## Drift / diagnose

| Symptoom | Fix |
| --- | --- |
| Agent schrijft config op verkeerd pad | `DEPRECATE_LEGACY_CONFIG.bat`; SOUL governance snippet sync |
| Twee verschillende auxiliary-blokken | `VERIFY_HERMES_CONFIG_DRIFT.bat` → migratie |
| Auxiliary in profiel-yaml (core) | `APPLY_HERMES_HOME_MIGRATION.bat` (strip + preset) |
| Venice ontbreekt in picker | `merge_legacy_providers_config.py` + `SYNC_HERMES_API_ENV.bat` |
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

**HermesHome E2E** (`RUN_HERMES_HOME_E2E.bat`): **14/14 PASS** — split-home drift, Venice env, auxiliary inheritance live checks.

## Feature flag (Python fallback)

`HERMES_WIN_PREFER_LOCALAPPDATA=1` (default): als `HERMES_HOME` unset is en runtime `config.yaml` bestaat, gebruikt Python `%LOCALAPPDATA%\hermes`. Uitzetten: `HERMES_WIN_PREFER_LOCALAPPDATA=0`.

Zie ook: `windows\INSTITUTIONAL.md` §5c, `docs\USER_DATA_OPERATIONS.md`.
