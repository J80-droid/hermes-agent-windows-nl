# System patterns

## Config-scheiding (drie bestanden)

1. **Root** `%LOCALAPPDATA%\hermes\config.yaml` (Windows runtime) — globaal gedrag + **model/provider**. Legacy `%USERPROFILE%\.hermes\config.yaml` is **deprecated** (zie `docs/HERMES_HOME_WINDOWS.md`).
2. **Profiel** `%LOCALAPPDATA%\hermes\profiles\<naam>\config.yaml` — `platform_toolsets.cli`, MCP, agent; model erft van root.
3. **Toolset-manifest** `docs/domain_toolsets.yaml` — sync via `SYNC_DOMAIN_TOOLSETS.bat`; opt-in via SOUL Tool governance.
4. **RAG** `~/data/domains.yaml` — batch-indexering; geen chat-sessie.

Implementatie: `hermes_cli/profile_model_inheritance.py` + `load_config()` / `load_cli_config()`.

## Profiel → root config overerving

- `is_profile_hermes_home()` → pad onder `profiles/<naam>`.
- `resolve_model_section()` / `resolve_auxiliary_section()` / `resolve_providers_sections()` → root, tenzij `*.inherit: false`.
- `apply_profile_root_config_inheritance()` → één root YAML-read per load.
- `root_config_path()` → altijd `get_default_hermes_root()` (niet profiel-`HERMES_HOME`).
- `save_config()` / `config set` → global keys naar **root**; redirect alleen als key expliciet in save-payload.
- `bust_config_caches(root)` → leegt alle load/raw caches (profielen hangen af van root).
- `hermes profile create` / `doctor --fix` → strip stale global blocks in profielen.

## RAG-pijplijn

- Idempotente chunk-`id` (SHA-256), `merge_insert`, orphan cleanup, incrementele ingest.
- Live status: `rag_ingest_live_status.json` met `run_state` + reconciliatie na run.
- Institutionele env: `rag_institutional_defaults.py` via `_rag_apply_institutional_env.bat`.

## MCP per domein

- Servernaam `lancedb-<domein>` in profiel-config.
- `HERMES_LANCEDB_PATH` in MCP-env = zelfde pad als `lancedb_path` in `domains.yaml`.

## Memory L1 consolidatie (Windows)

- **Actief pad:** `%LOCALAPPDATA%\hermes\profiles\<naam>\memories\` — legacy `%LOCALAPPDATA%\hermes\memories\` is seed-only na `CONSOLIDATE_ROOT_MEMORIES.bat`.
- **Merge:** `HermesMemoryMergeCommon.ps1` — §-split via U+00A7 (`Get-MemorySectionDelimiterChar`); seed wint; policy-buckets dedupeerd; Hermes-config (MCP YAML, multi-profile) alleen in `profiles/core`.
- **Keten:** `sync_profile_memories.ps1` → rebalance → `restore_core_hermes_config_memory.ps1` → `invoke_deduplicate_memories.ps1` (profielen + legacy root).
- **Audit:** `Test-MemoryConsolidationLayout` in `MemoryAuditCommon.ps1`; E2E stap 17/18 in `MemoryArchitectureE2E.core.ps1`.

## Windows setup (single source)

- **Canoniek:** `scripts/windows/setup_hermes_windows.ps1` — alle setup-logica.
- **Wrapper:** `windows/setup_hermes_windows.ps1` — alleen `& $canon @PSBoundParameters` (max. 40 regels).
- **Beleid:** `windows/HermesSetupScriptPolicy.ps1`; gehandhaafd door `verify_windows_script_chain.ps1` + pytest.
- **Entrypoints:** `SETUP_HERMES.bat`, `launch_hermes.bat` → canoniek PS1 (forward slashes in `.bat`).
- **Verboden:** `Copy-Item $PSCommandPath` naar `windows/` (dubbele IDE/PSSA-lint).

## Pending trust-runtime (start-hook)

- **Stamp:** `%LOCALAPPDATA%\hermes\pending_trust_runtime.json` (`TrustRuntimePending.psm1`) — gezet door `Invoke-UpstreamPostMerge.ps1` als `SYNC_TRUST_RUNTIME.bat` faalt tijdens UPDATE.
- **Start:** `launch_hermes.bat` → `launch_pending_trust_runtime.ps1` → `Invoke-TrustRuntimeLight.ps1` (subset trust-keten; standaard `SkipProductionGate`; SOUL snippets overgeslagen binnen 120s na anatomy deploy).
- **Succes:** `Clear-PendingTrustRuntime` + `Set-InstitutionalNewChatReminder` via `Invoke-MemoryTrustPostSync.ps1`.
- **Skip:** `HERMES_SKIP_PENDING_TRUST_ON_START=1`; max 3 pogingen, daarna handmatige fallback naar `SYNC_TRUST_RUNTIME.bat`.

## Windows taakbalk-iconen

- **Bron:** `assets/Hermes_logo.png` (repo) of `%USERPROFILE%\.hermes\_local_assets\assets\Hermes_logo.png`.
- **Generator:** `windows/tools/generate_colored_hermes_icons.py` — 7 ICO-lagen (16–256); geen synthetische H-stub zonder PNG.
- **`windows\*.lnk`:** `Set-HermesShellShortcut` — `cmd.exe /c` + `IconLocation` op gekleurd `.ico` (cache onder `%LOCALAPPDATA%\Hermes\shortcut-icons\`).
- **Pins:** `User Pinned\TaskBar` via `Set-HermesTaskbarPinShortcut` (zelfde cmd-wrapper).
- **Herstel:** `FIX_TASKBAR_ICONS.bat`; verify: `verify_taskbar_shortcut_icons.ps1`.

## Institutionele presentatie (drie lagen)

1. **SOUL** — typografie/structuur (`docs/templates/SOUL_SHARED_*.md` → `SyncSoulSnippet.psm1` → alle profielen). Gebruikt centrale PowerShell-module met `--force` (altijd overschrijven) en `--verify` (check-only).
2. **Assistant** — `display.assistant_render_style=institutional_rich`; pipeline: `prepare_assistant_markdown_plain()` (één normalize, incl. `compact_institutional_check`) → `render_institutional_from_prepared()` (`TightHeadingBody`, `SectionSpacer`, `InstitutionalTableElement` met `contextvars` tabelpalet). **Finalize-only streaming:** geen volledige Rich per token; ANSI/eindpaneel via `format_response_ansi` / `message.complete`. Contract-tests: `tests/hermes_cli/test_render_pipeline_contract.py`. Theme via `get_assistant_console_theme()` (CLI `ChatConsole`, gateway `rich_output.py`). Config **live** via `load_config_readonly`.
3. **UI** — `display.skin=default` (goud); banners/prompt, niet LLM-antwoordtekst.

### SOUL Sync (centraal, niet per profiel)

- **Module:** `windows/scripts/SyncSoulSnippet.psm1`
- **Scripts:** `sync_soul_interaction_snippet.ps1`, `sync_soul_output_format_snippet.ps1`
- **Opties:** `-Force` (altijd overschrijven), `-Verify` (check zonder schrijven), `-ManifestPath` (JSON rapport)
- **Manifest:** `%LOCALAPPDATA%\hermes\soul_manifests\<datum>_<tijd>.json`
- **Logging per profiel:** `[UPDATED]`, `[FORCED]`, `[SKIPPED]`, `[VERIFY_DIFF]`, `[VERIFY_OK]`

### Paletten (YAML-driven)

- Built-in: `demo`, `hermes`, `neutral` in `_BUILTIN_PALETTES` (`institutional_render.py`)
- User-defined: `config/palettes.yaml` — loaded at runtime, overrides built-ins for same name
- **Kop vs. tabel:** sectiekoppen h1–h4 ≠ tabelkolommen; `header_palette` **cyaan-first** (`#66d9ef`, `#a6e22e`, …) zodat `##` groen ≠ kolom `ID`
- Validation: required keys (`h1`, `h2`, `h3`, `h4`, `strong`, `label`, `text`, `table_header`); optional `header_palette`
- Fallback: unknown palette → `demo` + warning
- Diagnostics: `scripts/diagnose_renderer.py --verify` (E2E 2f); score `scripts/score_institutional_render.py --verify` (E2E 2g; unit `tests/scripts/test_score_institutional_render.py`)

### Normalizer + pariteit

- **Python (canonical):** `hermes_cli/markdown_output_normalize.py` — outline, institutional_check, tighten kop–tabel, NFR prose→tabel, **pseudo-tabel** (`_needs_pseudo_table_normalize` pre-gate, `normalize_pseudo_tables_to_markdown`; `_discover_repeated_field_keys` LRU-cache); **collapsed records**; pipeline eindigt met `compact_institutional_check` (pariteit TS). Bench (lokaal): `scripts/bench_normalize_markdown.py`. TS-pariteit: `institutionalMarkdown.ts` + `pytest tests/hermes_cli/test_normalizer_ts_parity.py` (vereist `npx tsx`).
- **Web:** `web/src/lib/institutionalMarkdown.ts` + `Markdown.tsx` (`toRenderUnits` = TightHeadingBody-equivalent)
- **Ink:** re-export Web normalizer (`ui-tui/src/lib/institutionalMarkdownNormalize.ts`) + compacte Controle-regel in `markdown.tsx`

Defaults: `windows/team_display.defaults`; toepassen: `APPLY_INSTITUTIONAL_RUNTIME.bat`. Audit: `RUN_INSTITUTIONAL_E2E.ps1` (11 stappen + 2f + 2g + **2h pseudo-tabel**); dedicated overview: `RUN_CONTEXT_AWARE_PSEUDO_TABLE_E2E.bat` (10 stappen); collapsed record: `audits/RUN_COLLAPSED_RECORD_PSEUDO_TABLE_E2E.bat` (10/10); unit `tests/hermes_cli/test_collapsed_record_pseudo_table.py`.

## Windows split-home (config single-source)

- **Runtime:** `%LOCALAPPDATA%\hermes\` — enige actieve `config.yaml`; `HERMES_HOME` = root (niet `profiles\*`).
- **Root-only globals:** `model`, `auxiliary`, `providers`/`custom_providers` — profielen erven via `profile_model_inheritance.py` (load + save redirect); geen stale blocks in `profiles/*/config.yaml`.
- **Legacy hub:** `%USERPROFILE%\.hermes\` — `.env` + `_local_assets`; geen actieve config (deprecate → `config.yaml.deprecated-*` + `CONFIG_README.txt`).
- **Module:** `windows/scripts/HermesHomeCommon.ps1` (paden, drift, gateway, launch-env).
- **Poorten:** `VERIFY_HERMES_CONFIG_DRIFT.bat` (dagelijks/post-pull); `APPLY_HERMES_HOME_MIGRATION.bat` (7 stappen); `RUN_HERMES_HOME_E2E.bat` (14/14); `RUN_ROOT_CONFIG_INHERITANCE_E2E.bat` (10/10, incl. `py_compile` op `collect_env_sync_keys.py`); `SYNC_HERMES_API_ENV.bat` (incl. `VENICE_API_KEY` + dynamic `key_env`).
- **Integratie:** `POST_GIT_PULL`, `UPDATE_HERMES` (via `Invoke-UpstreamPostMerge`), `RUN_INSTITUTIONAL_E2E` stap 2i, `launch_institutional_runtime -CheckDrift`.
- **Docs:** `docs/HERMES_HOME_WINDOWS.md`; SOUL snippet `SOUL_SHARED_CONFIG_GOVERNANCE.md`; footguns `check-windows-footguns.py`.

## Profiel-uitbreiding (ICT-team)

- Nieuwe profielen volgen **legal-blauwdruk**: generieke SOUL + lenzen in RAG-submappen, zelfde toolset per profiel.
- Security = **apart profiel** (niet lens) vanwege governance-risico en tegengestelde autonomy (`mag exploiteren` vs `mag NIET exploiteren`).
- Toolset verschillen per rol: `code_execution` aan voor security/dev (PoC/scripts), uit voor ict (alleen infra); `vision` optioneel voor ict/dev/security, uit voor data.
- RAG-bronnen in `docs/09_ICT/`, `10_Security/`, `11_Development/`, `12_Data/` met submappen per lens.
- Sync volgorde: manifest → `SYNC_DOMAIN_TOOLSETS.bat --create-missing` (ontbrekend profiel) → `sync_profile_mcp_from_domains.py` → `SYNC_SOUL_SNIPPETS.bat` → E2E audit (`RUN_TOOLSET_DOMAIN_E2E`, `RUN_PROVISION_DOMAIN_E2E`).
- Provision blijft in fork-script (`windows/scripts/sync_profile_toolsets_from_manifest.py`); importeert alleen `_PROFILE_DIRS` / validatie uit upstream — geen wijziging `create_profile()`-logica.

## Codebase-audit (smoke vs release-gate)

- **Evidence E0–E3:** `docs/CODEBASE_AUDIT_EVIDENCE.md`; rapport-template `docs/templates/CODEBASE_AUDIT_REPORT.md`.
- **Smoke (E1/E2 subset):** `windows/audits/RUN_CODEBASE_SMOKE_AUDIT.bat` → `CODEBASE_SMOKE_AUDIT_REPORT_*.md` — **geen** release-ready.
- **Release (E3):** `windows/tests/RUN_PYTEST.ps1` / `scripts/run_tests.sh` of `RUN_AUDITS.bat -IncludeAllE2E`.
- **Gecombineerd:** `RUN_AUDITS.bat -IncludeCodebaseSmoke` / `-IncludeCodebaseSmokeE2E`.
- **Optioneel na pull/update:** `POST_GIT_PULL.bat` / `UPDATE_HERMES.bat` met `-IncludeCodebaseSmoke` (~32s) of `-IncludeCodebaseSmokeE2E` (~45s); helper `Invoke-PostSyncCodebaseSmoke.ps1` (standaard uit).
- **SOUL:** `SOUL_SHARED_CODEBASE_AUDIT.md` via `sync_soul_codebase_audit_snippet.ps1` (anatomy-keten); na sync `/new`.
- **Validatie claims:** `validate_soul_anatomy.py --check-codebase-audit-claims` (warn); `--strict-codebase-audit-claims` (exit 1).

## Veiligheid

- Geen ingest + zware Kanban-werk op dezelfde LanceDB tegelijk (lock-risico).
- API-keys in `.env`; model in root `config.yaml` (niet per profiel dupliceren).
