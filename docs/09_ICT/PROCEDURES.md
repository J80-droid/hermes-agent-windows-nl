# ICT Procedures

## Standard Operating Procedures (SOP)

### 1. Incident Response

1. Identificeer scope (welke systemen, gebruikers, data)
2. Raadpleeg `search_knowledge` voor runbooks
3. Documenteer in `todo` (indien ingeschakeld)
4. Escaleer naar `security` bij breach-verdachte activiteit
5. Communiceer status naar J.

### 2. Change Management

1. Impact analyse via `search_knowledge`
2. Test in non-prod (via `terminal`)
3. Rollback plan documenteren
4. J.-goedkeuring voor productie
5. Uitvoeren met monitoring
6. Post-change review

### 3. Monitoring & Alerting

1. Dashboard check (`browser`)
2. Log analyse (`terminal` + `file`)
3. Threshold evaluatie
4. Alert tuning indien nodig
5. Documentatie updaten

### 4. Backup & Recovery

1. Backup status verifiëren (`terminal`)
2. Recovery procedures raadplegen (`search_knowledge`)
3. Test restore (scheduled)
4. Documentatie bijwerken

## Quality Standards

- Alle configs in version control
- Documentatie bij elke wijziging
- `[Bron: bestandsnaam]` bij feiten
- Geen productie wijzigingen zonder J.-goedkeuring
