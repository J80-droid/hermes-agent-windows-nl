# Development Procedures

## Standard Operating Procedures (SOP)

### 1. Feature Development

1. Requirements begrijpen (via `clarify` indien nodig)
2. Architecture raadplegen (`search_knowledge`)
3. Design document (bij grote features)
4. Implementatie
5. Tests schrijven
6. Code review (peer)
7. Merge naar main
8. Deploy naar staging (J.-goedkeuring voor productie)

### 2. Code Review

1. Review request ontvangen
2. Code lezen (`file`)
3. Checks: tests, documentatie, security, performance
4. Feedback geven
5. Goedkeuring of rework

### 3. Bug Fixing

1. Bug reproduceren
2. Root cause analyse
3. Fix implementeren
4. Regression test
5. Code review
6. Merge

### 4. Refactoring

1. Huidige staat analyseren
2. Doel staat definiëren
3. Impact analyse
4. Incrementele aanpak
5. Tests bijwerken
6. Documentatie bijwerken

## Quality Standards

- Min. 80% test coverage
- Alle publieke API's gedocumenteerd
- `[Bron: bestandsnaam]` bij feiten
- Geen productie deploy zonder J.-goedkeuring
