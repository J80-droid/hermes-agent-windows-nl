# Security Onboarding

## Doel
Dit document beschrijft hoe het `security` profiel gebruikt wordt binnen de Hermes-agent infrastructuur.

## Profiel activeren

```cmd
hermes -p security chat
```

Of via taakbalk: `SWITCH_PROFILE_AND_CHAT.bat security`

## Wanneer te gebruiken

- Kwetsbaarheid assessments
- Pentest planning en uitvoering
- Compliance audits (ISO 27001, NIST, GDPR)
- Incident response
- Forensische analyse

## Wanneer NIET te gebruiken

- Algemene IT vragen → `ict`
- Code review → `dev`
- Data analyse → `data`
- Juridische advies → `legal`

## Tool governance

| Tool | Standaard | Wanneer inschakelen |
|------|-----------|---------------------|
| mcp | Aan | Altijd — RAG voor CVE/compliance |
| file | Aan | Altijd — log analyse |
| terminal | Aan | Altijd — scanning/commands |
| web | Aan | Altijd — threat intelligence |
| browser | Aan | Altijd — web app testing |
| code_execution | Aan | Altijd — PoC scripts |
| vision | Uit | CVE dashboard screenshots |
| session_search | Uit | Eerdere pentest sessies |
| todo | Uit | Audit checklist |
| delegation | Uit | Crisis-response |

## Belangrijke regels

- **NOOIT** exploitatie op productie zonder expliciete J.-goedkeuring
- **ALTIJD** chain of custody documenteren bij forensics
- **ALTIJD** scope definieren vóór pentest
- **ALTIJD** test-omgeving gebruiken voor PoC

## Escalatie pad

1. **Scanning/assessment** → `security` zelf
2. **Actief incident** → J. direct + `ict`
3. **Data breach** → J. direct + `data`
4. **Code kwetsbaarheid** → `dev`
5. **Juridische aspecten** → `legal`

## Procedures

Zie `PROCEDURES.md` voor gedetailleerde werkwijzen.
