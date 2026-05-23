# Security Escalation

## Escalation Matrix

| Probleem | Eerste lijn | Escalatie naar | Wanneer |
|----------|-------------|----------------|---------|
| Actief security incident | `security` | J. direct + `ict` | Onmiddellijk |
| Data breach | `security` | J. direct + `data` | Onmiddellijk |
| Critical CVE | `security` | J. direct | Binnen 1 uur |
| Compliance failure | `security` | `legal` + J. | Binnen 4 uur |
| Code kwetsbaarheid | `security` | `dev` | Na assessment |
| Onbekende scope | `security` | `core` | Na 15 min |

## Crisis Procedures

1. **Stop** — analyseer impact
2. **Escaleer** — J. direct
3. **Contain** — beperk schade
4. **Document** — chain of custody
5. **Communicate** — status updates

## Contact Procedures

1. **J. direct:** Bij alle security incidents
2. **`ict` profiel:** Bij infrastructurele impact
3. **`dev` profiel:** Bij code kwetsbaarheden
4. **`data` profiel:** Bij data exposure
5. **`legal` profiel:** Bij compliance of juridische aspecten

## Documentatie

- Alle security-acties gelogd
- Incident timeline binnen 1 uur
- Post-incident review binnen 24 uur
