# Security Domein

> **Profiel:** `security`  
> **Toolset:** `docs/domain_toolsets.yaml` — `platform_toolsets.cli`  
> **SOUL:** `docs/templates/SOUL_SECURITY_DOMAIN.md`  
> **RAG:** `lancedb-security`  

## Lenzen (subdomeinen)

| Lens | Focus | Voorbeeld-werk |
|------|-------|----------------|
| **Pentest** | Kwetsbaarheden vinden | OWASP Top 10, network scanning, web app testing |
| **Compliance** | Beleidscontroles | ISO 27001, NIST, GDPR technisch |
| **Incident** | Breach response | Response playbook, forensische analyse, IOC hunting |
| **Forensics** | Post-incident onderzoek | Log-analyse, chain of custody, evidence preservation |

## Bronmappen

| Map | Inhoud |
|-----|--------|
| `Pentest/` | OWASP guides, testing frameworks, tool documentatie |
| `Compliance/` | ISO/NIST frameworks, audit checklists, GDPR technisch |
| `Incident/` | Response playbooks, IR procedures, communicatie templates |
| `Forensics/` | Log-analyse procedures, evidence handling, chain of custody |

## Governance

- **Impact op productie:** altijd J.-goedkeuring per actie
- **Optionele tools:** vision, session_search, todo, delegation — agent vraagt J.
- **Escalatie:** Bij actieve incidenten → J. direct
- **Chain of custody:** documenteer elke test-actie

## Procedures

Zie `ONBOARDING.md`, `PROCEDURES.md`, `ESCALATION.md` in deze map.
