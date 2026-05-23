# Data Onboarding

## Doel
Dit document beschrijft hoe het `data` profiel gebruikt wordt binnen de Hermes-agent infrastructuur.

## Profiel activeren

```cmd
hermes -p data chat
```

Of via taakbalk: `SWITCH_PROFILE_AND_CHAT.bat data`

## Wanneer te gebruiken

- Database schema ontwerpen
- ETL/ELT pipelines bouwen
- Data quality checks
- Rapportages en dashboards
- Data governance

## Wanneer NIET te gebruiken

- Server configuratie → `ict`
- Security assessment → `security`
- Code ontwikkeling → `dev`
- Juridische advies → `legal`

## Tool governance

| Tool | Standaard | Wanneer inschakelen |
|------|-----------|---------------------|
| mcp | Aan | Altijd — RAG voor data docs |
| file | Aan | Altijd — schema lezen |
| terminal | Aan | Altijd — SQL/queries |
| web | Aan | Altijd — docs zoeken |
| browser | Aan | Altijd — dashboards |
| code_execution | Uit | ETL scripts testen |
| session_search | Uit | Eerdere analyses |
| todo | Uit | Migration planning |

## Belangrijke regels

- **NOOIT** schema wijzigen zonder J.-goedkeuring
- **NOOIT** productie data exporteren zonder maskering
- **ALTIJD** data lineage documenteren
- **ALTIJD** privacy checks bij PII

## Escalatie pad

1. **Data vraag** → `data` zelf
2. **Database performance** → `ict`
3. **Data breach** → `security`
4. **Pipeline code bug** → `dev`
5. **Juridische aspecten** → `legal`

## Procedures

Zie `PROCEDURES.md` voor gedetailleerde werkwijzen.
