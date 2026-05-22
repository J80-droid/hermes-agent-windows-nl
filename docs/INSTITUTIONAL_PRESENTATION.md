# Institutionele presentatie (Hermes-native)

Twee gescheiden lagen: **wat het model schrijft** (SOUL) en **hoe Hermes het kleurt** (Rich + skin).

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
- `**Label:**` op eigen regel; waarde op volgende regel.
- Lijsten: `- item` in bron (UI toont `•`).

Het zichtbare checklist-blok heet `<institutional_check>` (niet `<verification>` — dat gebruikt upstream interne model-guidance in `agent/prompt_builder.py`).

## Laag B — Weergave (Hermes kleuren)

| Setting | Waarde |
|---------|--------|
| `display.skin` | `default` (goud/amber) |
| `display.final_response_markdown` | `render` |
| `display.streaming` | `false` |
| `display.compact` | `false` (meer witruimte tussen blokken) |

**Automatisch (aanbevolen):** `windows\APPLY_INSTITUTIONAL_RUNTIME.bat` — display op **alle** profielen, SOUL-sync, E2E-audit.

Los: `APPLY_TEAM_DISPLAY.bat` (alle profielen; `-ActiveProfileOnly` via ps1), `SYNC_SOUL_SNIPPETS.bat`. Na `UPDATE_HERMES.bat` wordt display al toegepast.

**Config-pad:** per profiel `profiles\<naam>\config.yaml`. Root `config.yaml` blijft voor model; display per profiel. E2E stap 6/8 controleert elk profiel.

### Waar rendering gebeurt

| Oppervlak | Code |
|-----------|------|
| Klassieke CLI | [`hermes_cli/display_markdown.py`](../hermes_cli/display_markdown.py) via [`cli.py`](../cli.py) |
| TUI gateway | [`agent/rich_output.py`](../agent/rich_output.py) → zelfde Rich-theme |
| TUI Ink | [`ui-tui/src/components/markdown.tsx`](../ui-tui/src/components/markdown.tsx) (structuur; bullets `•`) |
| Web | [`web/src/components/Markdown.tsx`](../web/src/components/Markdown.tsx) |

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
| Magenta koppen | Geen skin-theme | Update fork; check `hermes_cli/display_markdown.py` |
| Blauw i.p.v. goud | Legacy cmd of `skin: slate` | Windows Terminal + `skin: default` |
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
