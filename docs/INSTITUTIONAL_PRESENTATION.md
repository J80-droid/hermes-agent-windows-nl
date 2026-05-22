# Institutionele presentatie (Hermes-native)

Drie gescheiden lagen: **wat het model schrijft** (SOUL), **assistant-antwoorden** (Rich-demo renderer), en **Hermes UI** (skin goud).

## Laag A — Globale structuur (alle profielen)

| Bestand | Rol |
|---------|-----|
| [`templates/SOUL_SHARED_OUTPUT_FORMAT.md`](templates/SOUL_SHARED_OUTPUT_FORMAT.md) | Typografie, lijsten, `<institutional_check>`, standaardsecties |
| [`templates/SOUL_SHARED_INTERACTION.md`](templates/SOUL_SHARED_INTERACTION.md) | Interaction met J., landkaart |
| `windows\SYNC_SOUL_SNIPPETS.bat` | Schrijft beide blokken naar root + `profiles\*\SOUL.md` |

**Nieuwe chat verplicht** na SOUL-sync (bestaande sessies houden oude system prompt).

### Profiel-matrix

| Profiel | `<institutional_check>` | Volledige analyse-secties |
|---------|-------------------------|---------------------------|
| legal, analyst | Verplicht bij analyse | Ja |
| core, operations | Optioneel (korte Q&A) | Compact |
| overige | Typografie altijd; structuur indien nodig | Domein-SOUL bepaalt inhoud |

### Typografieregels (hard)

- Kop (`##`, `###`) op **eigen regel**; tekst op volgende regel na lege regel.
- **Lege regel vóór elke nieuwe hoofdstuk-kop** (`## Stap 2` na inhoud stap 1).
- Hoofdstukken als `##`, niet alleen `1 Stap 1:` zonder hash.
- `**Label:**` op eigen regel; waarde op volgende regel.
- Lijsten: `- item` in bron (UI toont `•`).
- Tabellen als markdown (`| kolom |`); geen `[COLOR_*]` in antwoordtekst.

Het zichtbare checklist-blok heet `<institutional_check>` (niet `<verification>` — dat gebruikt upstream interne model-guidance in `agent/prompt_builder.py`).

## Laag B — Assistant-antwoorden (Rich institutional)

Alleen **LLM-antwoorden** — niet de Hermes-banner of prompt.

| Setting | Waarde | Rol |
|---------|--------|-----|
| `display.final_response_markdown` | `render` | Rich i.p.v. strip |
| `display.assistant_render_style` | `institutional_rich` | Per-kolom tabelkoppen, demo-palet |
| `display.assistant_palette` | `demo` | cyaan/groen/magenta/geel (geen goud) |
| `display.assistant_label_columns` | `true` | `**Label:**` links, inhoud rechts |
| `display.compact` | `false` | Witruimte tussen blokken |

Code: [`hermes_cli/institutional_render.py`](../hermes_cli/institutional_render.py), [`hermes_cli/display_markdown.py`](../hermes_cli/display_markdown.py), normalizer [`markdown_output_normalize.py`](../hermes_cli/markdown_output_normalize.py).

**Pipeline:** `prepare_assistant_markdown_plain()` normaliseert één keer → `render_institutional_assistant(..., already_normalized=True)` splitst op `##`-koppen en `**Label:**`-blokken, voegt lege regels tussen Rich-`Group`-delen toe.

**Console-theme:** `get_assistant_console_theme()` (demo/legacy) — gebruikt door gateway/`format_response_ansi` én klassieke CLI `ChatConsole` bij het eindpaneel (`cli.py`). Zonder dit kreeg het antwoord-Panel nog skin-goud terwijl de gateway al demo toonde.

**Streaming:** bij `display.streaming=false` (team-default) streamt de klassieke CLI ruwe markdown; Rich-rendering alleen op het **eindpaneel**. Ink/Web/TUI-gateway: zelfde normalizer + renderer via `rich_output.py`.

Fallback: `assistant_render_style: markdown_legacy` + goud via `skin_markdown_theme()` (oude pad).

Defaults in repo: [`windows/team_display.defaults`](../windows/team_display.defaults). E2E pytest: stap **2e** in `RUN_INSTITUTIONAL_E2E.ps1` (`test_institutional_rich_render.py`).

## Laag C — Hermes UI (skin)

| Setting | Waarde |
|---------|--------|
| `display.skin` | `default` (goud/amber) — banners, status, prompt |
| `display.streaming` | `false` |

**Automatisch (aanbevolen):** `windows\APPLY_INSTITUTIONAL_RUNTIME.bat` — display op **alle** profielen, SOUL-sync, E2E-audit.

**Bij start:** `start_hermes.bat` / `launch_hermes.bat` roept `launch_institutional_runtime.ps1` aan (display + SOUL wanneer templates/defaults wijzigen; stamp in `%LOCALAPPDATA%\hermes\launch_institutional_runtime.stamp`). Geen E2E bij elke start (te traag). Overslaan: `set HERMES_SKIP_INSTITUTIONAL_RUNTIME=1`. E2E bij start: `start_hermes.bat --institutional-e2e` of `set HERMES_INSTITUTIONAL_E2E_ON_START=1`.

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

Archief: [`windows/scripts/institutional/`](../windows/scripts/institutional/README.md).

## Troubleshooting

| Symptoom | Oorzaak | Actie |
|----------|---------|-------|
| Geen gekleurde koppen | `strip` i.p.v. `render` | `APPLY_TEAM_DISPLAY.bat` |
| Antwoord nog goud | `assistant_palette: hermes` of legacy | Zet `assistant_palette: demo`; `APPLY_INSTITUTIONAL_RUNTIME.bat` |
| Eindpaneel goud, gateway wel demo | Oud `ChatConsole` zonder assistant-theme | Update fork; herstart chat |
| Geen witregel tussen hoofdstukken | Model + geen normalizer | SOUL-sync; `markdown_output_normalize` |
| Labels niet in twee kolommen | `assistant_label_columns: false` | Zet `true` in profiel-`config.yaml` |
| Magenta koppen (oude Rich) | `markdown_legacy` | `assistant_render_style: institutional_rich` |
| Blauw i.p.v. goud (UI) | Legacy cmd of `skin: slate` | Windows Terminal + `skin: default` |
| Structuur alleen bij analyst | Geen SOUL-sync | `SYNC_SOUL_SNIPPETS.bat` + nieuwe sessie |
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
