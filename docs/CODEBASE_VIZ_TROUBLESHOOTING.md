# Codebase Viz — troubleshooting

## Symptoom: `memory_pressure` in Sunburst

De UI toont `memory_pressure` en "Scan afgebroken of geen resultaat." De console logt `fetch ok` met `{ fallback: true, error: 'memory_pressure' }` — dat is een **API-fallback**, geen netwerkfout.

### Oorzaken

1. **Verouderde pygount-schijfcache** — `repo_revision` in `output/research/codebase_viz_pygount_cache.json` komt niet overeen met `git rev-parse HEAD` (bijv. na `git pull`).
2. **RSS boven drempel** — standaard `CODEBASE_VIZ_MAX_MEMORY_MB=500`; zware Hermes-sessie blokkeert nieuwe pygount-scans.
3. **Valse cache-invalidatie (opgelost v2.5.0+)** — background refresh vergeleek git HEAD met een bestands-handtekening en wiste bij elke start de in-memory cache.

### Snel herstel

```bat
windows\FIX_CODEBASE_VIZ_CACHE.bat
```

Daarna **dashboard herstarten** en `/codebase-viz` hard refreshen (Ctrl+Shift+R).

Handmatig (repo-root):

```powershell
python scripts/warm_codebase_viz_pygount_cache.py --check-only   # exit 0 = cache geldig
python scripts/warm_codebase_viz_pygount_cache.py --force        # opnieuw scannen
```

Optioneel hogere geheugenlimiet vóór dashboard-start:

```powershell
$env:CODEBASE_VIZ_MAX_MEMORY_MB = "1024"
```

### Diagnose (met sessietoken)

Open `/codebase-viz` en in DevTools-console:

```javascript
await fetch('/api/plugins/codebase-viz/health', {
  headers: { 'X-Hermes-Session-Token': window.__HERMES_SESSION_TOKEN__ }
}).then(r => r.json()).then(h => ({
  memory: h.memory,
  pygount_cached: h.pygount_cached,
  cache_keys: h.cache_keys,
  disk_cache: h.disk_cache,
}))
```

| Veld | Betekenis |
|------|-----------|
| `memory.pressure` | `true` = geen nieuwe zware scan |
| `disk_cache.revision_matches` | `false` = schijfcache ouder dan HEAD → repair-script |
| `pygount_cached` | `true` = pygount-bundle in geheugen |
| `cache_keys` | bevat `structure` na eerste succesvolle Sunburst-load |

**Let op:** `/api/...` in de adresbalk zonder token geeft `401 Unauthorized` — gebruik de fetch hierboven of `audits/verify_codebase_viz_health.py`.

## Plugin-README

Zie [`plugins/codebase-viz/dashboard/README.md`](../plugins/codebase-viz/dashboard/README.md) voor env-variabelen en endpoints.
