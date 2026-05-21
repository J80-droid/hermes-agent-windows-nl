# RAG — institutionele omgevingsvariabelen

Deze waarden zijn **standaard** in alle officiële launchers. Je hoeft ze normaal **niet** handmatig te zetten.

Bron in code: `scripts/rag_pipeline/rag_institutional_defaults.py`  
Toepassing: `windows/scripts/rag/_rag_apply_institutional_env.bat`, `rag_institutional_env.ps1`, ingest-start in `run_domains_ingest.py`.

**Gerelateerd (geen RAG-env):** inference-model staat in `%LOCALAPPDATA%\hermes\config.yaml`, niet in profiel-yaml — zie `docs/PROFILE_MODEL_INHERITANCE.md` en `docs/README.md`.

## Aanbevolen defaults (future-proof)

| Variabele | Default | Wanneer wijzigen |
|-----------|---------|------------------|
| `HERMES_RAG_LIVE_STALE_SEC` | `120` | Alleen **verhogen** (bijv. `300`) als live status ten onrechte als “verouderd” wordt gemeld terwijl ingest nog loopt op extreem trage PDF’s. **Niet verlagen** — te kort geeft valse “stale” meldingen. |
| `HERMES_RAG_QUIET_TORCH` | `1` | Zet `0` alleen bij **debug** van PyTorch/embed (KernelPreference-waarschuwingen weer zichtbaar). Geen invloed op indexkwaliteit. |
| `HERMES_RAG_PERF_PROFILE` | `safe` | `balanced` / `fast` alleen op een machine met veel RAM/CPU en na test op één domein. |
| `HERMES_NONINTERACTIVE` | `1` (nacht/taakbalk) | Alleen in `RAG_KNOWLEDGE_UPDATE_NIGHT.bat` — geen J/N-prompt. Handmatige run zonder deze var → wel J/N-keuze. |
| `HERMES_RAG_FRESH` | `n` (nacht) | `j` alleen als je database **bewust** wilt wissen. |

Gerelateerd (geen env, wel gedrag):

| Mechanisme | Doel |
|------------|------|
| `rag_ingest_live_status.json` + `run_state` | Geen misleidende `40/40` na afloop; `completed` / `failed` |
| `ingest_live_status.py --reconcile` | Oude live_status syncen met eindrapport |
| `check_ingest_status.bat` | Status + auto-reconcile per domein |

## Waar het wordt gezet

```mermaid
flowchart TD
  A[update_knowledge.bat] --> B[update_knowledge.ps1]
  B --> C[run_domains_ingest.py]
  C --> D[_rag_apply_institutional_env.bat]
  D --> E[_rag_run_ingest_institutional.bat]
  E --> F[run_rag_ingest.ps1 + ingest.py]
  N[RAG_KNOWLEDGE_UPDATE_NIGHT.bat] --> A
```

## Handmatig overschrijven (zeldzaam)

```bat
set HERMES_RAG_LIVE_STALE_SEC=300
set HERMES_RAG_QUIET_TORCH=0
windows\scripts\update_knowledge.bat legal
```

## Zie ook

- `docs/RAG_TWEE_FASEN.md` — twee fasen index vs. chat
- `scripts/rag_pipeline/ACTIVATION.md` — technische pipeline
