# ICT Domein

> **Profiel:** `ict`  
> **Toolset:** `docs/domain_toolsets.yaml` — `platform_toolsets.cli`  
> **SOUL:** `docs/templates/SOUL_ICT_DOMAIN.md`  
> **RAG:** `lancedb-ict`  

## Lenzen (subdomeinen)

| Lens | Focus | Voorbeeld-werk |
|------|-------|----------------|
| **Infra** | Servers, cloud, netwerk, containers | AWS/Azure/GCP config, Docker, Kubernetes, monitoring |
| **DevOps** | CI/CD, pipelines, IaC | GitHub Actions, Terraform, Ansible, release management |
| **Support** | Helpdesk, troubleshooting | Ticket-afhandeling, user guides, FAQ |
| **Sysadmin** | OS-beheer, backups, patching | Windows/Linux admin, Active Directory, SCCM |

## Bronmappen

| Map | Inhoud |
|-----|--------|
| `Infra/` | Server docs, runbooks, cloud configs, netwerkdiagrammen |
| `DevOps/` | CI/CD pipelines, IaC scripts, release procedures |
| `Support/` | Ticketing procedures, FAQ, troubleshooting guides |
| `Sysadmin/` | OS-beheer docs, backup procedures, patching schema |

## Governance

- **Productie wijzigingen:** altijd J.-goedkeuring
- **Standaard:** mcp, kanban (manifest + `hermes tools`-checklist)
- **Optionele tools:** vision, session_search, todo — agent vraagt J.
- **Escalatie:** Bij incidenten → `security` (indien breach) of `dev` (indien code-gerelateerd)

## Procedures

Zie `ONBOARDING.md`, `PROCEDURES.md`, `ESCALATION.md` in deze map.
