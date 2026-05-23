# Development Onboarding

## Doel
Dit document beschrijft hoe het `dev` profiel gebruikt wordt binnen de Hermes-agent infrastructuur.

## Profiel activeren

```cmd
hermes -p dev chat
```

Of via taakbalk: `SWITCH_PROFILE_AND_CHAT.bat dev`

## Wanneer te gebruiken

- Code schrijven of refactoren
- API design
- Database schema ontwerpen
- Testing en coverage
- Code review

## Wanneer NIET te gebruiken

- Server configuratie → `ict`
- Security assessment → `security`
- Data analyse → `data`
- Juridische advies → `legal`

## Tool governance

| Tool | Standaard | Wanneer inschakelen |
|------|-----------|---------------------|
| mcp | Aan | Altijd — RAG voor patterns |
| file | Aan | Altijd — code lezen |
| terminal | Aan | Altijd — build/test |
| web | Aan | Altijd — docs zoeken |
| browser | Aan | Altijd — UI testing |
| code_execution | Aan | Altijd — scripts/tests |
| vision | Uit | UI screenshots |
| session_search | Uit | Eerdere debug sessies |
| todo | Uit | Sprint planning |
| kanban | Uit | Ticket board |

## Belangrijke regels

- **NOOIT** direct deploy naar productie
- **ALTIJD** tests schrijven voor nieuwe features
- **ALTIJD** code review vóór merge
- **ALTIJD** documentatie bij public API's

## Escalatie pad

1. **Code vraag** → `dev` zelf
2. **Security issue in code** → `security`
3. **Infra deployment** → `ict`
4. **Database schema** → `data`
5. **Juridische aspecten** → `legal`

## Procedures

Zie `PROCEDURES.md` voor gedetailleerde werkwijzen.
