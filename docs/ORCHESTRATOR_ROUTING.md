# Orchestrator routing (core-profiel)

Canonieke matrix voor `profiles/core/SOUL.md`. Domeinnamen komen uit [`domains.yaml.example`](domains.yaml.example).

## Wanneer welk profiel

| Signaal / onderwerp | Profiel | MCP (RAG) |
|---------------------|---------|-----------|
| Juridisch (GCR, arbeidsrecht, VSO, BZ, klokkenluiders, bestuursrecht, letselschade, …) | `legal` | `lancedb-legal` |
| Crypto, portfolio, marktdata, trading | `trading` | `lancedb-trading` |
| Curriculum, papers, onderwijs, wetenschap | `academics` | `lancedb-academics` |
| Processen, workflows, KPI, operations | `operations` | `lancedb-operations` |
| Planning, agenda, persoonlijke logistiek | `logistics` | `lancedb-logistics` |
| Startups, business model, incubatie | `ventures` | `lancedb-ventures` |
| Games, performance, specs | `gaming` | `lancedb-gaming` |
| Filosofie, psychologie, reflectie | `philosophy` | `lancedb-philosophy` |
| Infra, cloud, netwerk, servers, containers | `ict` | `lancedb-ict` |
| Kwetsbaarheden, compliance, incident, forensics | `security` | `lancedb-security` |
| Code, build, test, deploy, architecture | `dev` | `lancedb-dev` |
| Database, ETL, BI, analytics, data governance | `data` | `lancedb-data` |
| Personal Brain, cross-domein, onduidelijk domein | `core` | `lancedb-core` (+ Kanban naar specialist) |

## Multi-domein

1. Label per domein welke bron/DB is geraadpleegd.
2. Geen bindend juridisch of financieel advies in core-synthese — citeer specialist of routeer.
3. Bij conflict tussen domeinen: expliciet benoemen, niet verhullen.

## Acties

| Actie | Hoe |
|-------|-----|
| Profiel wisselen | `/profile use <naam>` of `windows\SWITCH_PROFILE.bat <naam>` |
| Taak naar specialist | Kanban + `hermes -p <profiel> chat` |
| Volledige inventarisatie | `/landkaart` of skill `landkaart` |

**Legal:** core routeert naar profiel `legal` alleen — geen subprofielen (`legal-arb`, …). Binnen-routering via rechtsgebied-lenzen: [LEGAL_DOMAIN_ARCHITECTURE.md](LEGAL_DOMAIN_ARCHITECTURE.md), [LEGAL_TAXONOMY.md](LEGAL_TAXONOMY.md).

Zie ook [PROFILE_SWITCH.md](PROFILE_SWITCH.md) en [PROFILE_SOUL.md](PROFILE_SOUL.md).
