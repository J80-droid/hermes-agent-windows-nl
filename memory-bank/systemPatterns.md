# System patterns

## Config-scheiding (drie bestanden)

1. **Root** `~/.hermes/config.yaml` — globaal gedrag + **model/provider**.
2. **Profiel** `~/.hermes/profiles/<naam>/config.yaml` — `platform_toolsets.cli`, MCP, agent; model erft van root.
3. **Toolset-manifest** `docs/domain_toolsets.yaml` — sync via `SYNC_DOMAIN_TOOLSETS.bat`; opt-in via SOUL Tool governance.
4. **RAG** `~/data/domains.yaml` — batch-indexering; geen chat-sessie.

Implementatie: `hermes_cli/profile_model_inheritance.py` + `load_config()` / `load_cli_config()`.

## Profiel-model overerving

- `is_profile_hermes_home()` → pad onder `profiles/<naam>`.
- `resolve_model_section()` → root-model, tenzij `model.inherit: false`.
- `save_config()` / `config set model.*` → schrijven naar **root**, niet naar profiel-yaml.
- `hermes profile create` → `strip_model_block_from_profile_config()` na clone.
- `hermes doctor --fix` → verwijdert verouderde `model:`-blokken in alle profielen.

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

## Windows taakbalk-iconen

- **Bron:** `assets/Hermes_logo.png` (repo) of `%USERPROFILE%\.hermes\_local_assets\assets\Hermes_logo.png`.
- **Generator:** `windows/tools/generate_colored_hermes_icons.py` — 7 ICO-lagen (16–256); geen synthetische H-stub zonder PNG.
- **`windows\*.lnk`:** `Set-HermesShellShortcut` — `cmd.exe /c` + `IconLocation` op gekleurd `.ico` (cache onder `%LOCALAPPDATA%\Hermes\shortcut-icons\`).
- **Pins:** `User Pinned\TaskBar` via `Set-HermesTaskbarPinShortcut` (zelfde cmd-wrapper).
- **Herstel:** `FIX_TASKBAR_ICONS.bat`; verify: `verify_taskbar_shortcut_icons.ps1`.

## Institutionele presentatie (drie lagen)

1. **SOUL** — typografie/structuur (`docs/templates/SOUL_SHARED_*.md` → `SyncSoulSnippet.psm1` → alle profielen). Gebruikt centrale PowerShell-module met `--force` (altijd overschrijven) en `--verify` (check-only).
2. **Assistant** — `display.assistant_render_style=institutional_rich`; pipeline: `markdown_output_normalize.py` → `institutional_render.py` (`TightHeadingBody`, `SectionSpacer`, `InstitutionalTableElement`). Theme via `get_assistant_console_theme()` (CLI `ChatConsole`, gateway `rich_output.py`). Config **live** via `load_config_readonly`.
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
- Diagnostics: `scripts/diagnose_renderer.py --verify` (E2E 2f); score `scripts/score_institutional_render.py --verify` (E2E 2g)

### Normalizer + pariteit

- **Python (canonical):** `hermes_cli/markdown_output_normalize.py` — outline, institutional_check, tighten kop–tabel, NFR prose→tabel, **pseudo-tabel/underscore vs→markdown** (`ensure_markdown_table_dividers`, `normalize_pseudo_tables_to_markdown`)
- **Web:** `web/src/lib/institutionalMarkdown.ts` + `Markdown.tsx` (`toRenderUnits` = TightHeadingBody-equivalent)
- **Ink:** re-export Web normalizer (`ui-tui/src/lib/institutionalMarkdownNormalize.ts`) + compacte Controle-regel in `markdown.tsx`

Defaults: `windows/team_display.defaults`; toepassen: `APPLY_INSTITUTIONAL_RUNTIME.bat`. Audit: `RUN_INSTITUTIONAL_E2E.ps1` (11 stappen + 2f + 2g + **2h pseudo-tabel**).

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
