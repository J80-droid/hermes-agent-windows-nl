# Data Procedures

## Standard Operating Procedures (SOP)

### 1. Schema Design

1. Requirements verzamelen
2. Normalisatie (3NF standaard)
3. Indexing strategie
4. Constraints definieren
5. Documentatie
6. J.-review vóór implementatie

### 2. ETL Pipeline

1. Source analyse
2. Transformatie regels
3. Data quality checks
4. Error handling
5. Monitoring
6. Documentatie

### 3. Data Quality

1. Profiling (uniqueness, completeness)
2. Validatie regels
3. Anomaly detection
4. Cleansing
5. Monitoring dashboard

### 4. Reporting

1. Requirements verzamelen
2. Data sources identificeren
3. Aggregatie logica
4. Visualisatie ontwerp
5. Performance optimalisatie
6. Documentatie

## Quality Standards

- Alle schema changes in version control
- Data lineage gedocumenteerd
- PII altijd gemaskeerd in non-prod
- `[Bron: bestandsnaam]` bij feiten
- Geen productie schema changes zonder J.-goedkeuring
