# Institutionele markdown — porting-gids

Porteer het Hermes institutionele presentatiesysteem naar een ander project. Voor **dagelijks Hermes-gebruik** zie [INSTITUTIONAL_PRESENTATION.md](INSTITUTIONAL_PRESENTATION.md). Voor **visuele rooktest** zie [INSTITUTIONAL_RENDERER_TEST_PROMPT.md](templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md).

---

## 1. Architectuur in één oogopslag

| Laag | Doel | Niet mengen met |
|------|------|-----------------|
| **A — SOUL / system prompt** | Wat het model schrijft (structuur, tabellen, labels) | UI-kleuren |
| **B — Assistant-renderer** | Hoe antwoorden getoond worden (kleur, spacing, labels) | App-chrome / banner |
| **C — App UI** | Shell, navigatie, prompt (bijv. goud skin) | Assistant-antwoordkleuren |

```
Laag A: typografieregels in system prompt
    → ruwe markdown van LLM
Laag B: normalizeAssistantMarkdown → Renderer + palet
    → CLI ANSI / Web HTML / TUI
Laag C: app theme (banner, prompt)
```

**Kernprincipe:** assistant-antwoorden gebruiken een demo/Monokai-palet (cyaan/groen/magenta), niet de app-skin.

---

## 2. Configuratie (single source of truth)

### 2.1 Config-keys

```yaml
display:
  final_response_markdown: render      # render | strip | raw
  assistant_render_style: institutional_rich   # institutional_rich | markdown_legacy
  assistant_palette: demo              # demo, monokai, dracula, …
  assistant_label_columns: true        # legacy naam; layout is ALTIJD verticaal
  compact: false
  streaming: false                     # true = ruwe markdown tijdens stream
```

| Key | Effect |
|-----|--------|
| `assistant_render_style: institutional_rich` | Per-kolom tabelkleuren, labels verticaal, sectie-spacing |
| `assistant_palette` | Kleurenschema alleen voor assistant-output |
| `final_response_markdown: render` | Zonder dit zie je geen Rich-kleuren |

### 2.2 Settings-functie

Port `get_assistant_render_settings()` uit [`hermes_cli/display_markdown.py`](../hermes_cli/display_markdown.py):

- Valideer `assistant_render_style` ∈ `{institutional_rich, markdown_legacy}`
- Valideer `assistant_palette` tegen bekende paletten; fallback `demo` + warning
- **Lees config live** bij elke render (niet cache-en op module-load)

---

## 3. Bestanden om te porten (prioriteit)

### 3.1 Must-have

| Hermes-bestand | Rol | Port naar |
|----------------|-----|-----------|
| `hermes_cli/markdown_output_normalize.py` | Pre-processing vóór render | Backend + frontend normalizer |
| `hermes_cli/institutional_render.py` | CLI Rich-renderer | Python terminal, of eigen renderer |
| `web/src/lib/institutionalMarkdown.ts` | TS-kopie normalizer | Frontend |
| `web/src/lib/institutionalWebPalette.ts` | Kleuren per palet | Frontend CSS/Tailwind |
| `web/src/components/Markdown.tsx` | Block-parser + kleuren | Frontend |
| `config/palettes.yaml` | User-editable paletten | Config-map project root |

### 3.2 Integratie-laag

| Hermes-bestand | Rol |
|----------------|-----|
| `hermes_cli/display_markdown.py` | Orchestratie: normalize → render → ANSI |
| `hermes_cli/web_server.py` → `GET /api/display/assistant` | Live config naar Web |
| `web/src/contexts/AssistantDisplayProvider.tsx` | React context + fetch |
| `web/src/lib/assistantDisplayEvents.ts` | Event na config-save → refetch |

### 3.3 Prompt-laag

| Bestand | Rol |
|---------|-----|
| `docs/templates/SOUL_SHARED_OUTPUT_FORMAT.md` | Typografieregels system prompt |
| `docs/templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md` | Rooktest 10/10 |

### 3.4 Optioneel (kwaliteit/CI)

| Bestand | Rol |
|---------|-----|
| `scripts/score_institutional_render.py` | 8-check score (≥ 9.0, incl. `vergelijking_tabel`) |
| `scripts/diagnose_renderer.py` | Debug + palet-preview + drift-warnings + NFR/pseudo self-test |
| `scripts/verify_pseudo_table_normalizer.py` | Probe Ollama-vs, auxiliary, pipe-divider, architectuur em-dash (`--verify`) |
| `windows/audits/RUN_PSEUDO_TABLE_NORMALIZER_E2E.bat` | 10-stappen E2E pseudo-tabel normalizer |
| `windows/audits/RUN_CONTEXT_AWARE_PSEUDO_TABLE_E2E.bat` | Context-aware overview 2–6 kolommen (10 stappen) |
| `audits/RUN_COLLAPSED_RECORD_PSEUDO_TABLE_E2E.bat` | Collapsed record Component/Keuze/Status (10 stappen) |
| `tests/hermes_cli/test_normalizer_ts_parity.py` | Python ↔ TS drift |
| `tests/hermes_cli/test_collapsed_record_pseudo_table.py` | Collapsed record parser (unit, 48 tests) |
| `tests/cli/test_institutional_rich_render.py` | Renderer unit tests |

---

## 4. Render-pipeline

```
LLM output (string)
    → [1] normalizeAssistantMarkdown()
    → [2] wrap citations (optioneel)
    → [3] realign markdown tables (optioneel, CLI)
    → [4] render_institutional_assistant() / Markdown.tsx
    → gekleurde output
```

| Oppervlak | Aanroep |
|-----------|---------|
| CLI eindpaneel | `render_final_assistant_markdown(text, mode="render")` |
| TUI/gateway ANSI | `format_response_ansi(text, cols)` |
| Web | `<Markdown content={message} />` + palet uit context |
| Config API | `GET /api/display/assistant` |

---

## 5. Normalizer — transformaties

Port **identieke** regex-logica in Python én TypeScript (pariteitstest).

| Transformatie | Voorbeeld |
|---------------|-----------|
| Heading + body splitsen | `## Titel Dit is intro.` → kop + body op aparte regels |
| Label + waarde | `**Dossierstatus:** Gereed` → label regel + waarde regel |
| Outline → koppen | `1. Projectoverzicht` → `## Projectoverzicht` |
| Spacing | `\n\n` vóór `#`-koppen; tight tussen kop en tabel/label |
| NFR-prose → tabel | Platte regels onder `### Niet-functionele requirements` → `\| Categorie \| Eis \| Meetmethode \|` |
| `<institutional_check>` | Render: compacte regel `Controle · item 1 · item 2` (geen XML in output) |

---

## 6. Renderer — visuele regels

- Split op `##`-koppen; `TightHeadingBody` (kop flush op inhoud)
- `SectionSpacer` tussen secties (1 witregel)
- Labels: `**Label:**` op eigen regel, waarde eronder (`flex-col` in Web)
- Tabellen: per-kolom kleur via `header_palette` in YAML
- **Kleurregel:** kolom 0 (cyaan) ≠ h2 (groen)

Web parser (lightweight, geen full CommonMark): heading, table, label, list, code, paragraph.

---

## 7. Palet-systeem

Zie [`config/palettes.yaml`](../config/palettes.yaml). Verplichte keys: `h1`, `h2`, `h3`, `h4`, `strong`, `label`, `text`, `table_header`. Optioneel: `header_palette`, `h5`, `h6`, `code`, `link`.

**Synchroniseer bij nieuw palet:**

1. `config/palettes.yaml` (CLI Rich)
2. `web/src/lib/institutionalWebPalette.ts` (Tailwind)
3. Optioneel TUI/Ink kleurenmap

Onbekend palet → `demo` + log warning.

---

## 8. SOUL / system prompt (Laag A)

Minimale typografieregels (volledig: `SOUL_SHARED_OUTPUT_FORMAT.md`):

- Hoofdstukken als `##` / `###` / `####`
- Kop direct op inhoud (geen lege regel tussen kop en tabel/lijst)
- `**Label:**` op eigen regel; waarde op volgende regel
- Tabellen als markdown `| kolom |`
- NFR alleen als tabel onder `### Niet-functionele requirements`
- Geen `[COLOR_*]` tokens
- `<institutional_check>` op eigen regels (analyse-antwoorden)

**Na SOUL-wijziging:** nieuwe chat/sessie verplicht.

---

## 9. Web-integratie (live config)

```python
@app.get("/api/display/assistant")
async def get_assistant_display_settings():
    return get_assistant_render_settings()
```

React: `AssistantDisplayProvider` fetch bij mount; `notifyAssistantDisplayChanged()` na config-save. Geen hardcoded `demo` in componenten.

---

## 10. Migratie-checklist (gefaseerd)

| Fase | Inhoud | Duur (indicatie ·) |
|------|--------|------------------|
| 1 | Config keys + normalizer + SOUL-regels + handmatige rooktest | 1–2 dagen |
| 2 | `palettes.yaml` + renderer (CLI Rich of Web-only) | 2–4 dagen |
| 3 | Live config API + React provider | 1 dag |
| 4 | Pariteitstests + score/diagnose | optioneel |

---

## 11. 10/10 visuele checklist

Gebruik [INSTITUTIONAL_RENDERER_TEST_PROMPT.md](templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md). Zie ook `python scripts/score_institutional_render.py --verify` (8 checks, drempel ≥ 9.0) en `windows\audits\RUN_PSEUDO_TABLE_NORMALIZER_E2E.bat`.

---

## 12. Veelvoorkomende valkuilen

| Symptoom | Oorzaak | Fix |
|----------|---------|-----|
| Alles nog goud/brand-kleur | `assistant_palette: hermes` of legacy | `demo` + `institutional_rich` |
| Geen kleuren | `final_response_markdown: strip` | `render` |
| Ruwe `##` en XML-tags zichtbaar | `streaming=true` tijdens generatie, of geen eindpaneel-render | `streaming=false`; `APPLY_INSTITUTIONAL_RUNTIME.bat` |
| Label naast waarde | Oude renderer | `_render_body_with_embedded_labels` + Web `flex-col` |
| NFR als prose | Model negeert SOUL | Normalizer + SOUL sync |
| Web ≠ CLI kleuren | TS palet niet gesynchroniseerd | Update `institutionalWebPalette.ts` |
| Config niet zichtbaar | Gecachte settings | Live read + refetch event |
| h2 = kolom 0 kleur | Geen `header_palette` | cyaan-first in `header_palette` |
| **Config drift** | Handmatige `hermes config set` | `APPLY_TEAM_DISPLAY.bat` / diagnose drift-warnings |
| **TrueColor mist** | Terminal zonder 24-bit ANSI | `export COLORTERM=truecolor` of `assistant_palette: neutral` |
| **Oude chat** | SOUL/display gewijzigd zonder `/new` | Nieuwe sessie in Hermes |

---

## 13. Minimale vs volledige port

**Minimaal (Web-only):** normalizer TS + WebPalette + Markdown.tsx + config endpoint + SOUL-regels.

**Volledig (CLI + Web + gateway):** + `institutional_render.py`, `display_markdown.py`, `format_response_ansi()`, pariteitstests.

---

## 14. Aanbevolen kopie-volgorde

1. `config/palettes.yaml`
2. `hermes_cli/markdown_output_normalize.py`
3. `web/src/lib/institutionalMarkdown.ts`
4. `web/src/lib/institutionalWebPalette.ts`
5. `web/src/components/Markdown.tsx`
6. `hermes_cli/institutional_render.py` (alleen bij CLI)
7. `hermes_cli/display_markdown.py`
8. Web context + API
9. `SOUL_SHARED_OUTPUT_FORMAT.md` + rooktest-prompt

---

## 15. Tech-stack aanpassingen

| Stack | Normalizer | Renderer | Config |
|-------|------------|----------|--------|
| Next.js + API | TS in `lib/` | React | API route |
| FastAPI + React | Python + TS (pariteit!) | Beide | FastAPI endpoint |
| Alleen CLI Python | Python | Rich | YAML |
| Electron | TS renderer | React | IPC naar main |

---

## 16. Hermes fork — operationeel

Dagelijkse workflow in **deze** repo (niet porten):

| Actie | Commando |
|-------|----------|
| Alles-in-één runtime | `windows\APPLY_INSTITUTIONAL_RUNTIME.bat` |
| Alleen display | `windows\APPLY_TEAM_DISPLAY.bat` |
| Diagnose | `python scripts/diagnose_renderer.py --verify` |
| Score | `python scripts/score_institutional_render.py --verify` |
| Pseudo-tabel verify | `python scripts/verify_pseudo_table_normalizer.py --verify` |
| Pseudo-tabel E2E | `windows\audits\RUN_PSEUDO_TABLE_NORMALIZER_E2E.bat` |
| Pre-commit guard | `python scripts/verify_institutional_guard.py` |
| E2E audit | `windows\audits\RUN_INSTITUTIONAL_E2E.bat` |
| Team defaults bron | `windows/team_display.defaults` |
| Na IDE/merge | Zie [INSTITUTIONAL_PRESENTATION.md § Na Cursor/IDE-werk](INSTITUTIONAL_PRESENTATION.md) |
| Cursor-regel | `.cursor/rules/institutional-presentatie.mdc` |
| Upstream merge | `windows\MERGE_UPSTREAM.bat` — `$keepOurs` op renderer-paden |

**Realistisch doel:** regressies binnen ~5 minuten terug via APPLY → herstart → `/new` → rooktest. Geen 100% garantie tegen handmatige config-drift of terminal-beperkingen.
