# ICT Escalation

## Escalation Matrix

| Probleem | Eerste lijn | Escalatie naar | Wanneer |
|----------|-------------|----------------|---------|
| Server down | `ict` | J. direct | Onmiddellijk |
| Security incident | `ict` | `security` | Binnen 5 minuten |
| Data loss | `ict` | `data` + J. | Onmiddellijk |
| Code bug in productie | `ict` | `dev` | Na isolatie |
| Juridische compliance | `ict` | `legal` | Binnen 1 uur |
| Onbekende scope | `ict` | `core` | Na 15 min onderzoek |

## Contact Procedures

1. **J. direct:** Bij P1 incidenten (system down, data breach)
2. **`security` profiel:** Bij verdachte activiteit, CVE's, compliance issues
3. **`dev` profiel:** Bij code-gerelateerde problemen
4. **`data` profiel:** Bij database/pipeline issues
5. **`legal` profiel:** Bij compliance of juridische aspecten

## Documentatie

- Alle escalaties documenteren in incident log
- Root cause analysis binnen 24 uur
- Lessons learned binnen 1 week
