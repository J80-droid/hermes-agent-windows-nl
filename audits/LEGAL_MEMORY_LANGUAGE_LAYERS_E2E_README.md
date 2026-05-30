# Legal Memory Language Layers E2E

E2E voor **taal per laag** (EN trust + 3× NL legal USER triggers, SOUL precedence, geen i18n). Geen live LLM, geen SOUL repair/Pester.

## Scenario's

| Stap | Wat |
|------|-----|
| S1 | Repo-artefacten (seed, SOUL, architectuur, sync, invoke) |
| S2 | `MEMORY_CANONICAL_SEED.md` — taal-lagentabel + 3 legal fences + EN trust |
| S3 | `SOUL_LEGAL_DOMAIN.md` — USER.md EN+NL sectie, SOUL prevaleert |
| S4 | `LEGAL_DOMAIN_ARCHITECTURE.md` — § Taal- en triggerlagen |
| S5 | `sync_profile_memories.ps1` — legal-only seed routing |
| S6 | `LegalMemoryLanguageLayersE2E.core.ps1` — seed parse, char budget, runtime scheiding legal/core |
| S7 | `verify_legal_lens_parity.py` — template SOUL (na USER-tabel) |
| S8 | pytest `test_legal_memory_language_layers.py` |

## Draaien

```bat
audits\RUN_LEGAL_MEMORY_LANGUAGE_LAYERS_E2E.bat
```

## Relatie

- Breder (config repair, Pester): `RUN_LEGAL_PROACTIVE_SPARRING_E2E.bat`
- Unit (gemockt): `pytest tests/audits/test_legal_memory_language_layers_e2e_harness.py -q`
