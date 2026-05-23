# Upstream update + institutioneel E2E — 23 mei 2026

**Keten:** upstream merge (58 Nous-commits) → `UPDATE_HERMES.bat` → institutional E2E → push  
**Repo:** `D:\A.I\APPS\Hermes_agent_WS\hermes-agent`  
**Remote:** `origin/main` @ `e445d1cca` (fork `hermes-agent-windows-nl`)

---

## Samenvatting

| Onderdeel | Status | Bewijs |
|-----------|--------|--------|
| Upstream merge | PASS | `dd44205dd` — 1 conflict (`.github/workflows/tests.yml`: matrix + RAG-job) |
| `UPDATE_HERMES.bat` | PASS | ~4 min; exit 0 |
| Post-merge institutional runtime | PASS | `apply_institutional_runtime.ps1 -SkipE2E -NoPause` in keten |
| Pytest subset | PASS | 29 passed (rich, web API, normalizer pariteit) |
| Render score | PASS | 10.0/10 |
| `RUN_INSTITUTIONAL_E2E.bat` | PASS | 11/11 stappen |
| `git push origin main` | PASS | sync met remote |
| `MERGE_UPSTREAM.bat` conflict-flow | PARTIAL | Handmatige merge; `-PromptOnly` getest (0 conflicts na merge) |
| IDE-prompt met echte snippets | DEFER | Volgende upstream-merge; script aanwezig |

---

## Upstream merge (23 mei 2026)

- **Vóór merge:** 139 ahead / 58 behind upstream/main  
- **Conflict:** alleen `.github/workflows/tests.yml`  
- **Oplossing:** upstream matrix-slicing + duration-cache **én** fork RAG-job gecombineerd  
- **Na merge:** 0 behind upstream/main  

Alternatief voor volgende merge: `windows\MERGE_UPSTREAM.bat` (IDE-guided prompt, geen blind auto-resolve).

---

## UPDATE_HERMES.bat — post-merge keten

Uitgevoerd na merge; preflight meldde *Al gelijk met upstream/main* (merge al klaar).

| Stap | Resultaat |
|------|-----------|
| hermes update (deps/skills) | OK |
| RAG extras | OK — 14 domeinen |
| Trust runtime | OK |
| Domein-toolsets | OK |
| **Institutioneel runtime** | OK — display 14 profielen + SOUL forced sync |
| verify_windows_script_chain | FAIL → gefixt (zie hieronder) |
| Taakbalk-iconen | OK |

**Institutional runtime in keten sinds:** commit `e445d1cca` (`upstream_sync.ps1`).

---

## Institutional E2E (11 stappen)

```
windows\audits\RUN_INSTITUTIONAL_E2E.bat
=== INSTITUTIONAL E2E: PASS ===
```

Inclusief: rich renderer 2e, score 2g (≥9.0), display alle profielen, profielwissel 9–11.

---

## MERGE_UPSTREAM.bat — validatiestatus

| Modus | Getest | Opmerking |
|-------|--------|-----------|
| `-PromptOnly` | Ja | Na merge: *Al gelijk met upstream/main* |
| Volledige merge + IDE-prompt | Nee | Geen open conflicten meer |
| `-AutoResolve` | Nee | Opt-in; niet aanbevolen voor fork |
| `-FinalizeOnly` | Nee | Volgende merge |

Prompt-output: `%LOCALAPPDATA%\hermes\merge_prompts\UPSTREAM_MERGE_PROMPT_*.md`

---

## Verify-fix (zelfde sessie)

- **Probleem:** `verify_windows_script_chain.ps1` — `\s` in `RUN_PROVISION_DOMAIN_E2E.ps1:61`  
- **Fix:** pad-literal → forward slashes (`windows/scripts/...`)

---

## Na update (gebruiker)

1. Hermes herstarten indien open  
2. `/new` — SOUL/display bijgewerkt  
3. Optioneel: `docs/templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md`

---

## Herhaal audit

```cmd
cd D:\A.I\APPS\Hermes_agent_WS\hermes-agent
windows\UPDATE_HERMES.bat
windows\audits\RUN_INSTITUTIONAL_E2E.bat
pytest tests/cli/test_institutional_rich_render.py tests/hermes_cli/test_web_server.py -q
python scripts/score_institutional_render.py --verify
```

Volgende upstream-merge:

```cmd
windows\MERGE_UPSTREAM.bat -PromptOnly
windows\MERGE_UPSTREAM.bat
```
