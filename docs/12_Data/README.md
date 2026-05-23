# Data Domein

> **Profiel:** `data`  
> **Toolset:** `docs/domain_toolsets.yaml` — `platform_toolsets.cli`  
> **SOUL:** `docs/templates/SOUL_DATA_DOMAIN.md`  
> **RAG:** `lancedb-data`  

## Lenzen (subdomeinen)

| Lens | Focus | Voorbeeld-werk |
|------|-------|----------------|
| **Database** | Schema design, admin | SQL, optimalisatie, migrations, DB admin |
| **Analytics** | BI, dashboards | Reporting, visualisatie, data storytelling |
| **Pipeline** | ETL/ELT, orchestration | Data quality, lineage, scheduling |
| **Governance** | Classification, privacy | Retention, compliance, data catalog |

## Bronmappen

| Map | Inhoud |
|-----|--------|
| `Database/` | Schema docs, query optimalisatie, migration scripts |
| `Analytics/` | BI standards, dashboard designs, reporting procedures |
| `Pipeline/` | ETL documentatie, data quality checks, lineage docs |
| `Governance/` | Data classification, privacy procedures, retention policies |

## Governance

- **Schema wijzigingen / exports:** altijd J.-goedkeuring
- **Optionele tools:** code_execution, session_search, todo — agent vraagt J.
- **Escalatie:** Bij privacy issues → `security`; bij performance issues → `ict`

## Procedures

Zie `ONBOARDING.md`, `PROCEDURES.md`, `ESCALATION.md` in deze map.
