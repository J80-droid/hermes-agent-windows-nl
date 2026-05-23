# Institutionele presentatie (Hermes-native)

Drie gescheiden lagen: **wat het model schrijft** (SOUL), **assistant-antwoorden** (Rich-demo renderer), en **Hermes UI** (skin goud).

## Laag A — Globale structuur (alle profielen)

| Bestand | Rol |
|---------|-----|
| [`SOUL_ANATOMY_SPEC.md`](SOUL_ANATOMY_SPEC.md) | Canonieke SOUL-sectievolgorde (10 anatomy-blokken) |
| [`templates/SOUL_SHARED_VALUES.md`](templates/SOUL_SHARED_VALUES.md) | Values & Principles |
| [`templates/SOUL_SHARED_TRUST_VERIFICATION.md`](templates/SOUL_SHARED_TRUST_VERIFICATION.md) | Trust onder Hard Limits |
| [`templates/SOUL_SHARED_OUTPUT_FORMAT.md`](templates/SOUL_SHARED_OUTPUT_FORMAT.md) | `### Output conventions (institutional)` |
| [`templates/SOUL_SHARED_INTERACTION.md`](templates/SOUL_SHARED_INTERACTION.md) | `### Interaction met J.` |
| [`templates/SOUL_SHARED_WORKFLOW.md`](templates/SOUL_SHARED_WORKFLOW.md) | Workflow (Assess→Deliver) |
| [`templates/SOUL_SHARED_TOOL_GOVERNANCE.md`](templates/SOUL_SHARED_TOOL_GOVERNANCE.md) | `## Tool Usage` |
| [`templates/SOUL_SHARED_MEMORY_POLICY.md`](templates/SOUL_SHARED_MEMORY_POLICY.md) | Memory Policy |
| `windows\SYNC_SOUL_SNIPPETS.bat` | Values → Interaction → Output → Trust → Workflow → Tool → Memory |
| `windows\SYNC_TRUST_RUNTIME.bat` | + legal template, trust/values, memory seed (geen scrub) |

**Sync-methode:** Centrale PowerShell-module `SyncSoulSnippet.psm1` (in `windows/scripts/`). Deze module:
- Leest templates uit `docs/templates/`
- Schrijft naar **alle** profiel-SOUL's + root SOUL.md
- Ondersteunt `--force` (altijd overschrijven) en `--verify` (alleen check, niet schrijven)
- Genereert JSON-manifest per sync-run (`%LOCALAPPDATA%\hermes\soul_manifests\`)
- Toont per profiel: `[UPDATED]`, `[FORCED]`, `[SKIPPED]` of `[VERIFY_DIFF]`

Voor dagelijks gebruik: `APPLY_INSTITUTIONAL_RUNTIME.bat` gebruikt automatisch `--force`, zodat alle profielen gegarandeerd identiek zijn aan de centrale templates.

**Nieuwe chat verplicht** na SOUL-sync (bestaande sessies houden oude system prompt).

### Profiel-matrix

| Profiel | `<institutional_check>` | Volledige analyse-secties |
|---------|-------------------------|---------------------------|
| legal (dossier) | Verplicht bij analyse | Ja |
| core, operations | Optioneel (korte Q&A) | Compact |
| overige | Typografie altijd; structuur indien nodig | Domein-SOUL bepaalt inhoud |

### Typografieregels (hard)

- Kop (`##`, `###`) op **eigen regel**; inhoud op de **volgende regel** (geen lege regel tussen kop en tabel/lijst in markdown — renderer zet ze visueel flush).
- **Tussen secties:** renderer voegt één subtiele witregel toe (`SectionSpacer`).
- Hoofdstukken als `##`, niet alleen `1 Stap 1:` zonder hash (normalizer vangt outline af).
- `**Label:**` op eigen regel; waarde op de **volgende regel** (visueel eronder, niet ernaast). Normalizer splitst inline `**Label:** waarde`; renderer pelt labels ook uit heading-body (bijv. `**Dossierstatus:**` onder `## Projectoverzicht`).
- Tabellen als markdown (`| kolom |`); NFR **alleen** als tabel onder `### Niet-functionele requirements`.
- Lijsten: `- item` in bron (UI toont `•`).
- Geen `[COLOR_*]` in antwoordtekst.

Het zichtbare checklist-blok heet `<institutional_check>` (niet `<verification>` — dat gebruikt upstream interne model-guidance in `agent/prompt_builder.py`).

## Laag B — Assistant-antwoorden (Rich institutional)

Alleen **LLM-antwoorden** — niet de Hermes-banner of prompt.

| Setting | Waarde | Rol |
|---------|--------|-----|
| `display.final_response_markdown` | `render` | Rich i.p.v. strip |
| `display.assistant_render_style` | `institutional_rich` | Per-kolom tabelkoppen, demo-palet |
| `display.assistant_palette` | `demo` | cyaan/groen/magenta/geel (geen goud) |
| `display.assistant_label_columns` | `true` | Legacy config-naam; layout is **altijd verticaal** (label boven waarde) |
| `display.compact` | `false` | Witruimte tussen blokken |

Code: [`hermes_cli/institutional_render.py`](../hermes_cli/institutional_render.py), [`hermes_cli/display_markdown.py`](../hermes_cli/display_markdown.py), normalizer [`markdown_output_normalize.py`](../hermes_cli/markdown_output_normalize.py).

**Pipeline:** `prepare_assistant_markdown_plain()` normaliseert één keer → `render_institutional_assistant(..., already_normalized=True)` splitst op `##`-koppen en `**Label:**`-blokken, voegt lege regels tussen Rich-`Group`-delen toe. Labels in sectie-body worden expliciet gepeeld (`_render_body_with_embedded_labels`) zodat ze niet via markdown op één regel vallen.

**`<institutional_check>`:** tags worden in de renderer niet getoond; checklist op één compacte regel (`Controle  · item · item`).

**Kop + inhoud:** elke `#`–`######` via `TightHeadingBody` **flush** op tabel/lijst/proza. **Labels:** roze/oranje kopregel, waarde op regel eronder (`TightHeadingBody`, geen kolom-layout). **Tussen** secties één subtiele lege regel (`SectionSpacer`). Tabellen: `leading=0`, minimale cel-padding; celinhoud erft kolomkleur (CLI + Web `tableCellClass`).

**Pariteit:** CLI/TUI-gateway = volledige Python-renderer. Web/Ink = zelfde normalizer + compacte layout. Web assistant-kleuren: [`web/src/lib/institutionalWebPalette.ts`](../web/src/lib/institutionalWebPalette.ts) (alle YAML-paletten). **Live config:** `GET /api/display/assistant` → `AssistantDisplayProvider` → `Markdown` (zelfde bron als CLI `get_assistant_render_settings()`; geen hardcoded `demo`). Na Config-save triggert `notifyAssistantDisplayChanged()` een refetch. **Drift-test:** `pytest tests/hermes_cli/test_normalizer_ts_parity.py` (Python ↔ Web/Ink via `npx tsx`).

**Kleuren:** sectiekoppen (h1–h4) = niveau-gebaseerd; tabelkolommen = apart palet (`header_palette` op alle YAML-paletten, **cyaan-first** zodat `##` groen ≠ kolom `ID` cyaan).

**Score (7 checks):** checklist, kop-op-inhoud, sectie-spacing, labels, NFR-tabel, kleur h2≠kolom0, render-pipeline — `python scripts/score_institutional_render.py --verify` (E2E stap 2g, drempel ≥ 9.0).

**Normalizer (fallback):** zet platte outline om naar `##`/`###`; `N Stap N:` → `## Stap N:`; inline `**Label:** waarde` → label + waarde op aparte regels; platte `Categorie: … Eis: …` en **NFR-prose** (streepjes, `**Performantie**`-blokken) → markdown-tabel; `<institutional_check>` op eigen regels.

**Rooktest-prompt:** [`templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md`](templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md) — plak in nieuwe chat na SOUL-sync; gebruik **dezelfde** prompt om runs te vergelijken.

**Nieuwe chat (geautomatiseerd):** na SOUL-sync schrijft `SyncSoulSnippet.psm1` / `APPLY_INSTITUTIONAL_RUNTIME.bat` een vlag `%LOCALAPPDATA%\hermes\institutional_new_chat_required.json`. Hermes toont bij start een gele banner; `/new` wist de vlag. Hermes hoeft niet herstart te worden voor de banner — wel **nieuwe sessie** voor de system prompt.

**Console-theme:** `get_assistant_console_theme()` (demo/legacy) — gebruikt door gateway/`format_response_ansi` én klassieke CLI `ChatConsole` bij het eindpaneel (`cli.py`). Zonder dit kreeg het antwoord-Panel nog skin-goud terwijl de gateway al demo toonde.

**Live config:** `get_assistant_render_settings()` leest de actieve profiel-config bij elke aanroep (niet gecachet). Dit garandeert dat na een profielwissel (`/profile use <naam>`) direct het juiste palet wordt gebruikt zonder Hermes te herstarten.

**Streaming:** bij `display.streaming=true` streamt de klassieke CLI **ruwe markdown** (zichtbare `##`, `<institutional_check>`-tags) **tijdens** generatie; Rich-rendering komt pas op het **eindpaneel**. Bij `display.streaming=false` (team-default) is er **geen** token-stream — alleen het Rich-eindpaneel. Hermes dwingt `streaming=false` af wanneer `final_response_markdown=render` (zie `_normalize_display_markdown_streaming` in `config.py`). Ink/Web/TUI-gateway: zelfde normalizer + renderer via `rich_output.py`.

Fallback: `assistant_render_style: markdown_legacy` + goud via `skin_markdown_theme()` (oude pad).

Defaults in repo: [`windows/team_display.defaults`](../windows/team_display.defaults).

E2E pytest: stap **2e** (`test_institutional_rich_render.py`).
E2E diagnose: stap **2f** (`scripts/diagnose_renderer.py --verify`).
E2E score: stap **2g** (`scripts/score_institutional_render.py --verify`, drempel ≥ 9.0).

### Runtime verifiëren

```bat
python scripts/diagnose_renderer.py
python scripts/score_institutional_render.py
python scripts/score_institutional_render.py --verify
```

Toont:
- Actief profiel, renderer-stijl, palet, label-kolommen (config; layout altijd verticaal)
- Kleurlegenda h2 vs tabelkolom 0
- NFR normalizer self-test (prose→tabel; `[OK]` in diagnose, `[WARN]` alleen bij falende pipeline)
- Config cache state (live vs gecachet)
- Visuele preview via de echte `format_response_ansi()` pipeline

```bat
python scripts/diagnose_renderer.py --show-palettes
```

Toont alle geregistreerde paletten (built-in + YAML) met een test-tabel + koppen.

### Nieuwe paletten toevoegen (geen code-edit)

1. Open [`config/palettes.yaml`](../config/palettes.yaml)
2. Kopieer een bestaand palet en pas kleuren aan (Rich style strings: hex `#RRGGBB` of Rich kleurnamen zoals `bright_cyan`)
3. Vereiste keys: `h1`, `h2`, `h3`, `h4`, `strong`, `label`, `text`, `table_header`
4. Optioneel: `header_palette` (komma-gescheiden Rich-stijlen; kolom 0 bij voorkeur **niet** dezelfde hex als `h2`)
5. `display.assistant_palette: <jouw_naam>` in profiel-config

Bij onbekend palet: automatische fallback naar `demo` + warning in log.

## Laag C — Hermes UI (skin)

| Setting | Waarde |
|---------|--------|
| `display.skin` | `default` (goud/amber) — banners, status, prompt |
| `display.streaming` | `false` |

**Automatisch (aanbevolen):** `windows\APPLY_INSTITUTIONAL_RUNTIME.bat` — display op **alle** profielen, SOUL-sync, E2E-audit.

**Bij start:** `launch_hermes.bat` roept eerst `launch_soul_anatomy_deploy.ps1` aan (13 domein-templates + snippets wanneer repo-SOUL nieuwer dan `%LOCALAPPDATA%\hermes\soul_anatomy_deploy.stamp`), daarna `launch_institutional_runtime.ps1` (team display; snippets overgeslagen als anatomy net liep). Geen E2E bij elke start. Overslaan: `set HERMES_SKIP_SOUL_DEPLOY_ON_START=1` en/of `set HERMES_SKIP_INSTITUTIONAL_RUNTIME=1`. Geforceerd: `set HERMES_FORCE_SOUL_DEPLOY=1`. E2E bij start: `start_hermes.bat --institutional-e2e` of `set HERMES_INSTITUTIONAL_E2E_ON_START=1`.

Los: `APPLY_TEAM_DISPLAY.bat`, `SYNC_SOUL_SNIPPETS.bat`. Na `UPDATE_HERMES.bat` wordt display al toegepast.

**Config-pad:** per profiel `profiles\<naam>\config.yaml`. Root `config.yaml` blijft voor model; display per profiel. E2E stap 6/8 controleert elk profiel.

### Waar rendering gebeurt

| Oppervlak | Code |
|-----------|------|
| Klassieke CLI (eindpaneel) | `ChatConsole(theme=get_assistant_console_theme())` → `institutional_render` → ANSI |
| TUI gateway | [`agent/rich_output.py`](../agent/rich_output.py) + `get_assistant_console_theme()` |
| TUI Ink | [`ui-tui/src/components/markdown.tsx`](../ui-tui/src/components/markdown.tsx) + [`institutionalColors.ts`](../ui-tui/src/lib/institutionalColors.ts) |
| Web | [`web/src/components/Markdown.tsx`](../web/src/components/Markdown.tsx) + [`institutionalMarkdown.ts`](../web/src/lib/institutionalMarkdown.ts) |

Start: `windows\start_hermes.bat` of VS Code **Hermes Matrix Cockpit** (`.vscode/tasks.json`).

### `display.tui_compact`

Onafhankelijk van `display.compact`. Toggle in TUI via `/compact`. Alleen TUI-witruimte.

## Legacy (niet dagelijks)

| Oud | Vervanging |
|-----|------------|
| `render_colors.py` (ANSI wit/blauw/groen) | Rich `render` + skin |
| `watch-hermes` + klembord | Matrix Cockpit / `start_hermes.bat` |
| `[COLOR_*]` tokens in SOUL | Normale markdown `##` / `**` |
| `show_colors.py` (hardcoded preview) | `scripts/diagnose_renderer.py --show-palettes` |
| SOUL met `[COLOR_*]` tokens | `SYNC_SOUL_SNIPPETS.bat` + `scripts/migrate_soul_tokens.py` |

Archief: [`windows/scripts/institutional/`](../windows/scripts/institutional/README.md).

## Na Cursor/IDE-werk

Na wijzigingen via Cursor, upstream-merge of handmatige config-edits:

1. `windows\APPLY_INSTITUTIONAL_RUNTIME.bat` — display op alle profielen + SOUL-sync + E2E
2. Hermes **herstarten** (lopen sessie laadt oude config)
3. In Hermes: **`/new`** — nieuwe system prompt + display-effect
4. Verifiëren:
   ```bat
   set HERMES_HOME=%LOCALAPPDATA%\hermes\profiles\core
   python scripts\diagnose_renderer.py --verify
   python scripts\score_institutional_render.py --verify
   ```
5. Visuele rooktest: [`templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md`](templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md)
6. Optioneel vóór commit bij renderer-wijzigingen: `python scripts/verify_institutional_guard.py`

**Niet blind wijzigen:** renderer-bestanden (`institutional_render.py`, `Markdown.tsx`, …) — zie `.cursor/rules/institutional-presentatie.mdc`.

## Troubleshooting

| Symptoom | Oorzaak | Actie |
|----------|---------|-------|
| Geen gekleurde koppen | `strip` i.p.v. `render` | `APPLY_TEAM_DISPLAY.bat` |
| Antwoord nog goud | `assistant_palette: hermes` of legacy | Zet `assistant_palette: demo`; `APPLY_INSTITUTIONAL_RUNTIME.bat` |
| Eindpaneel goud, gateway wel demo | Oud `ChatConsole` zonder assistant-theme | Update fork; herstart chat |
| Geen witregel tussen hoofdstukken | Model + geen normalizer | SOUL-sync; `markdown_output_normalize` |
| Label en waarde op één regel | Inline markdown in heading-body (oud) | Pull/update fork; renderer pelt labels; normalizer splitst inline |
| NFR prose i.p.v. tabel | Model negeert SOUL | Normalizer herstelt prose→tabel; `diagnose_renderer --verify` faalt als pipeline kapot; SOUL-sync + `/new` |
| Magenta koppen (oude Rich) | `markdown_legacy` | `assistant_render_style: institutional_rich` |
| Blauw i.p.v. goud (UI) | Legacy cmd of `skin: slate` | Windows Terminal + `skin: default` |
| Geen institutioneel format | Geen SOUL-sync | `SYNC_SOUL_SNIPPETS.bat` + nieuwe sessie (`/new`) |
| Ruwe `##` / `<institutional_check>` zichtbaar | Config drift of `streaming=true` | `APPLY_INSTITUTIONAL_RUNTIME.bat`; diagnose drift-warnings |
| Kleuren plat (structuur OK) | Geen TrueColor in terminal | `COLORTERM=truecolor` of `assistant_palette: neutral` |
| TUI andere kleuren dan CLI | Normaal vóór rich_output | Zorg dat `agent/rich_output.py` aanwezig is |

## Legal SOUL opnieuw deployen

`windows\scripts\sync_legal_soul_from_template.ps1` kopieert `SOUL_LEGAL_DOMAIN.md` en injecteert **volledige** shared Interaction + Outputformaat (niet alleen stub-tekst).

## Rooktest na upstream-merge

Zie [`windows/UPSTREAM_SYNC.md`](../windows/UPSTREAM_SYNC.md): display/skin + `SYNC_SOUL_SNIPPETS.bat` + `RUN_INSTITUTIONAL_E2E.bat`.

```cmd
windows\APPLY_INSTITUTIONAL_RUNTIME.bat
rem of alleen audit na handmatige sync:
windows\audits\RUN_INSTITUTIONAL_E2E.bat -ApplyRuntime
```

Rapport (na audit): `windows/audits/INSTITUTIONAL_E2E_REPORT_2026-05-22.md` (log: `INSTITUTIONAL_E2E_LAST_RUN.log`, gitignored).
