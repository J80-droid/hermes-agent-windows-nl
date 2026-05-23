# Data Escalation

## Escalation Matrix

| Probleem | Eerste lijn | Escalatie naar | Wanneer |
|----------|-------------|----------------|---------|
| Data breach | `data` | `security` + J. | Onmiddellijk |
| Database performance | `data` | `ict` | Na analyse |
| Pipeline failure | `data` | `dev` + `ict` | Onmiddellijk |
| Schema conflict | `data` | `dev` | Na analyse |
| Privacy compliance | `data` | `legal` + J. | Binnen 4 uur |
| Onbekende scope | `data` | `core` | Na 15 min |

## Contact Procedures

1. **`security` profiel:** Bij data breaches of exposure
2. **`ict` profiel:** Bij infra/database performance
3. **`dev` profiel:** Bij pipeline code bugs
4. **`legal` profiel:** Bij privacy of compliance issues
5. **J. direct:** Bij productie data incidents

## Documentatie

- Alle data incidents gelogd
- Root cause analysis bij P1
- Data impact assessment bij breaches
