# Model/Provider Coherence E2E

Geïsoleerde E2E voor `persist_model_runtime`, coherence-detectie en repair. Geen live API-calls.

## Scenario's

| ID | Scenario | Verwachting |
|----|----------|-------------|
| E1 | `HERMES_HOME=profiles/core`, persist nous | Root `model.provider=nous`, profiel zonder `model:` |
| E2 | auth=nous, config=gemini | `auth_config_provider_mismatch` |
| E3 | nous + Gemini `base_url` | `base_url_provider_mismatch` |
| E4 | gemini + vendor-slug default | `vendor_slug_wrong_provider` |
| E5 | split-brain + repair | provider=nous, geen Gemini-host, coherent |
| E6 | persist openrouter | `auth.active_provider=openrouter` (niet gewist) |
| E7 | één persist-call | provider + default samen in root yaml |
| E8 | custom + `extra_model_fields` | `api_key` en `api_mode` behouden |
| E9 | minimale auth.json | mismatch nog steeds gedetecteerd |
| E10 | aligned nous config | geen issues |

## Uitvoeren

```bat
audits\RUN_MODEL_PROVIDER_COHERENCE_E2E.bat
```

Of via `RUN_AUDITS.bat -IncludeModelProviderCoherenceE2E` (windows/audits delegateert naar deze harness).

---

# Model/Provider Hardening E2E

Aanvullende E2E voor code-review hardening (geen live API).

| ID | Scenario | Verwachting |
|----|----------|-------------|
| E1 | Profiel-yaml met comment `# providers:` | Geen false-positive global blocks |
| E2 | Echte `auxiliary`/`providers` keys | Gedetecteerd + gestript |
| E3 | vendor_slug warn op gemini | Geen blocking errors (drift-gate) |
| E4 | Lege auth.json | `read_auth_json` → `{}` |
| E5 | auth.json met UTF-8 BOM | Parse OK |
| E6 | Corrupt auth.json | Lege store + guard reset |
| E7 | Nous shared store BOM | `_read_shared_nous_state` OK |
| E8 | `persist_model_runtime(azure-foundry)` | Coherent + auth sync |

```bat
audits\RUN_MODEL_PROVIDER_HARDENING_E2E.bat
```

Windows delegate: `windows\audits\RUN_MODEL_PROVIDER_HARDENING_E2E.bat`

`RUN_AUDITS.bat -IncludeModelProviderHardeningE2E` (of `-IncludeAllE2E`).
