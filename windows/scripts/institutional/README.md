# Institutionele presentatie (legacy + archief)

## Actief (Hermes-native)

- Display: `windows\APPLY_TEAM_DISPLAY.bat` of `APPLY_INSTITUTIONAL_RUNTIME.bat` → alle profielen: `render`, `skin=default`, `assistant_render_style=institutional_rich`, `assistant_palette=demo`, `assistant_label_columns=true`, `compact=false`, `streaming=false`
- Renderer: `hermes_cli/institutional_render.py` + `hermes_cli/display_markdown.py` (`get_assistant_console_theme()`)
- Gateway: `agent/rich_output.py`; pariteit Ink/Web: `ui-tui` + `web/src/lib/institutionalMarkdown.ts`
- SOUL-sync: `windows\SYNC_SOUL_SNIPPETS.bat` (Interaction + Outputformaat)
- Docs: `docs/INSTITUTIONAL_PRESENTATION.md`; E2E: `windows\audits\RUN_INSTITUTIONAL_E2E.bat` (11 stappen)

## Legacy (niet voor dagelijks gebruik)

| Script | Rol |
|--------|-----|
| `render_colors_legacy.py` | Oud ANSI-palet (wit/blauw/groen) via klembord-pipeline |
| `watch_hermes_archive.ps1` | Archief-monitor zonder kleur-render (optioneel) |
| `show_colors_legacy.py` | Oud hardcoded kleurenpalet preview (5 Monokai-varianten) |
| `watch_hermes_legacy.ps1` | Oud live-monitor via file-polling + klembord |

Vervangen door:
- Rich markdown + globale SOUL-templates
- `scripts/diagnose_renderer.py --show-palettes` (echte renderer preview)
- `institutional_render.py` + `display_markdown.py` (live rendering)
