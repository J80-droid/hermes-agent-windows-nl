# Development Escalation

## Escalation Matrix

| Probleem | Eerste lijn | Escalatie naar | Wanneer |
|----------|-------------|----------------|---------|
| Security bug in code | `dev` | `security` | Onmiddellijk |
| Performance issue | `dev` | `ict` | Na profiling |
| Database schema conflict | `dev` | `data` | Na analyse |
| Build pipeline down | `dev` | `ict` | Onmiddellijk |
| Juridische compliance code | `dev` | `legal` | Binnen 4 uur |
| Onbekende scope | `dev` | `core` | Na 15 min |

## Contact Procedures

1. **`security` profiel:** Bij security issues in code
2. **`ict` profiel:** Bij infra/deployment issues
3. **`data` profiel:** Bij database schema issues
4. **`legal` profiel:** Bij compliance in code
5. **J. direct:** Bij productie incidents

## Documentatie

- Alle bugs gelogd in incident log
- Root cause analysis bij P1
- Lessons learned bij sprint review
