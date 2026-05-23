# ICT Onboarding

## Doel
Dit document beschrijft hoe het `ict` profiel gebruikt wordt binnen de Hermes-agent infrastructuur.

## Profiel activeren

```cmd
hermes -p ict chat
```

Of via taakbalk: `SWITCH_PROFILE_AND_CHAT.bat ict`

## Wanneer te gebruiken

- Server configuratie wijzigingen
- Netwerk troubleshooting
- CI/CD pipeline problemen
- Helpdesk ticket escalatie
- Backup/monitoring controles

## Wanneer NIET te gebruiken

- Juridische vragen → `legal`
- Security incidenten → `security`
- Code ontwikkeling → `dev`
- Data analyse → `data`

## Tool governance

| Tool | Standaard | Wanneer inschakelen |
|------|-----------|---------------------|
| mcp | Aan | Altijd — RAG voor runbooks |
| file | Aan | Altijd — config lezen |
| terminal | Aan | Altijd — server commands |
| web | Aan | Altijd — docs zoeken |
| browser | Aan | Altijd — dashboards |
| vision | Uit | Screenshots van errors |
| session_search | Uit | Eerdere troubleshooting |
| todo | Uit | Incident planning |
| kanban | Uit | ITIL/change processen |

## Escalatie pad

1. **Lokaal probleem** → `ict` zelf
2. **Security impact** → `security`
3. **Code bug** → `dev`
4. **Data issue** → `data`
5. **Juridische aspecten** → `legal`
6. **Onbekend** → `core` (router)

## Procedures

Zie `PROCEDURES.md` voor gedetailleerde werkwijzen.
