# Multi-Agent Trading Team — Architectuurvooronderzoek (Windows/WSL2)

**Status:** Vooronderzoek (pre-implementatie)
**Doel:** Volledige documentatie van tech stack, agent-rollen, datastromen, Windows-haalbaarheid en resilience-strategie voor een lokaal draaiend trading-team bestaande uit Analyst-, Risk- en Execution-agents.
**Scope:** Alleen analyse en ontwerp — geen uitvoerbare code, testscripts of mocks.

---

## 1. Aanbevolen Tech Stack

### 1.1 Overzicht kernelcomponenten

| Laag | Keuze | Rationale |
| --- | --- | --- |
| Inter-agent communicatie | FastAPI (HTTP/JSON) + Redis (pub/sub status) | Zie §1.2 voor vergelijking |
| Agent runtime | Python 3.11+ (conda hermes-env) | Bestaande infra; geen Node.js dependency |
| LLM orchestration | Hermes Agent (multi-profile) | Herbruikbare session/state/tool-laag |
| Async task queue | Redis + Celery (optioneel) of asyncio.queue | Alleen bij hoge frequentie; start met asyncio |
| State persistence | SQLite via Hermes SessionDB | Geen PostgreSQL overhead; lokale focus |
| Marktdata feed | WebSocket (REST fallback) via CCXT of Polygon.io | Realtime + historisch in één lib |
| Config management | YAML + Hermes config set | Consistent met bestaande Hermes-werkwijze |
| Secret management | %USERPROFILE%\.hermes\.env | API keys buiten git; sync met SYNC_HERMES_API_ENV.bat |

### 1.2 Vergelijking: Redis vs FastAPI als primair communicatieprotocol

| Criterium | Redis (pub/sub + streams) | FastAPI (HTTP/JSON + WebSocket) |
| --- | --- | --- |
| **Koppeling** | Los — agents lezen/schrijven naar streams zonder directe kennis van elkaar | Semi-los — elke agent exposeert endpoints; caller kent URL |
| **Latency** | Sub-milliseconden (in-memory) | 1-5 ms per HTTP-call (lokaal); hoger bij serialisatie |
| **Doorvoer** | 100k+ msg/sec | 10k-50k req/sec (lokaal, 1 core) |
| **Message persistence** | Ja (streams met consumer groups) | Nee (HTTP is request-response; WebSocket is stateful) |
| **Ordering garantie** | Per stream: FIFO per consumer group | HTTP: geen (parallelle calls); WebSocket: sequentieel per connectie |
| **Herstart-tolerantie** | Consumer groups onthouden offsets; geen berichtverlies | HTTP: retry nodig; WebSocket: reconnect met state recovery |
| **Complexiteit** | Medium — consumer groups, ACK-mechanisme, dead-letter | Laag — REST semantics, iedereen kent HTTP |
| **Debugbaarheid** | Moeilijk (binary protocol, aparte CLI) | Hoog (curl, browser, Swagger docs) |
| **WSL2 compatibiliteit** | Uitstekend (docker of native Linux binary) | Uitstekend (Python-native, geen Docker nodig) |
| **Windows native optie** | Redis via WSL2 of Memurai (Windows port) | FastAPI draait native Windows; geen WSL2 nodig |
| **Resource footprint** | ~5 MB RAM idle; CPU light | ~50-100 MB per FastAPI worker (uvicorn) |

**Conclusie:** **FastAPI (HTTP/JSON)** als primair protocol voor inter-agent communicatie, met Redis als **secundair status-kanaal** voor:
- Heartbeat/detection (agent X is alive)
- Broadcast van marktdata (1 writer, N readers)
- Event-log voor audit trail (append-only stream)

FastAPI wint op eenvoud, debugbaarheid en Windows-native support. Redis wordt alleen ingezet waar pub/sub of persistente streams een duidelijke meerwaarde hebben.

### 1.3 Specifieke pakketten

| Pakket | Versie (min) | Doel |
| --- | --- | --- |
| uvicorn | 0.30+ | ASGI server voor FastAPI |
| fastapi | 0.115+ | REST endpoints, WebSocket support |
| redis-py | 5.0+ | Redis pub/sub + streams (optioneel) |
| ccxt | 4.3+ | Unified exchange API (marktdata + orders) |
| pydantic | 2.5+ | Datavalidatie en JSON-schema generatie |
| httpx | 0.27+ | Async HTTP client (inter-agent calls) |
| pandas | 2.1+ | Tijdreeksanalyse (Analyst agent) |
| numpy | 1.26+ | Numerieke berekeningen (risk metrics) |
| structlog | 24.1+ | Gestructureerde logging per agent |

### 1.4 Aanbevolen netwerktopologie (lokaal)

```
WSL2 Linux (Ubuntu 24.04)
├── Redis-server (port 6379) — status/pub-sub kanaal
│
Windows host (conda hermes-env)
├── FastAPI Gateway (port 8000) — orchestrator/router
├── Analyst Agent  (port 8001) — analyse-marktdata
├── Risk Agent     (port 8002) — risico-check
└── Execution Agent(port 8003) — order-executie
```

**Waarom WSL2 voor Redis, Windows native voor agents:**
- Redis presteert het best op Linux (geen Windows port-problemen; Memurai is niet feature-parity)
- Agent-code draait in conda `hermes-env` (bestaande Hermes-infra, native Windows)
- FastAPI is cross-platform, geen WSL2 nodig voor de agent-processen
- Windows-TCP/IP communiceert met WSL2 via `localhost` (WSL2 forwardt default)

### 1.5 Hermes-integratie

Elke agent draait als een **Hermes profiel**:
```
hermes -p trading-analyst
hermes -p trading-risk
hermes -p trading-execution
```

Profiel-config per agent via `%LOCALAPPDATA%\hermes\profiles\trading-*/config.yaml`.  
Gedeelde secrets: `%USERPROFILE%\.hermes\.env`.

---

## 2. Agent Team-Architectuur

### 2.1 Agentrollen en verantwoordelijkheden

| Agent | Primaire taak | Input | Output | LLM-rol |
| --- | --- | --- | --- | --- |
| **Analyst** | Marktanalyse en signaalgeneratie | OHLCV-data, nieuws-feed, on-chain metrics | TradeSignal (koop/verkoop met rationale) | Specialist: patroonherkenning, macro-analyse |
| **Risk** | Risicobeoordeling, positielimieten | TradeSignal, portfoliostaat, volatility | RiskVerdict (approved/declined/scaled, max_size) | Specialist: VaR, drawdown, correlatie |
| **Execution** | Orderuitvoering, Slippage-minimalisatie | RiskVerdict, orderboek, liquiditeit | OrderResult (filled/partial/failed, avg_price) | Specialist: TWAP/VWAP, gas-pricing, exchange routing |

### 2.2 JSON-datastromen

#### 2.2.1 Analyst → Risk: TradeSignal

```json
{
  "signal_id": "sig_20260525_001",
  "timestamp": "2026-05-25T14:30:00Z",
  "symbol": "BTC/USDT",
  "action": "buy",
  "confidence": 0.82,
  "entry_price_min": 82500.0,
  "entry_price_max": 83400.0,
  "stop_loss": 79800.0,
  "take_profit": 87500.0,
  "timeframe": "1h",
  "rationale": "Bullish pennant breakout op 1h, RSI 58, volume 2.3x avg, weerstand $83.5k gebroken met retest",
  "sources": ["binance_ohlcv", "coinglass_liquidation", "twitter_sentiment"],
  "agent_version": "analyst-v1.2"
}
```

**Validatieregels (Risk):**
- `timestamp` ≤ 30 seconden oud (anders stale signal)
- `confidence` ∈ [0.0, 1.0]
- `stop_loss` < `entry_price_min` bij buy, > `entry_price_max` bij sell
- `take_profit` > `entry_price_max` bij buy, < `entry_price_min` bij sell
- `symbol` in goedgekeurde lijst

#### 2.2.2 Risk → Execution: RiskVerdict

```json
{
  "signal_id": "sig_20260525_001",
  "original_signal": { "action": "buy", "confidence": 0.82, "entry_price_max": 83400.0 },
  "verdict": "approved_scaled",
  "max_position_size_usd": 1250.0,
  "max_slippage_bps": 5,
  "risk_score": 0.31,
  "reasoning": "VaR(99%)=1.8% portefeuille, huidige drawdown 4% (drempel 15%), correlatie BTC/ETH laag (0.32), liquiditeit voldoende. Schaling: 62.5% van gevraagde size wegens trailing-drawdown limiet (binnen 3% van max)",
  "risk_metrics": {
    "portfolio_var_99pct_1h": 0.018,
    "current_drawdown": 0.04,
    "max_drawdown_limit": 0.15,
    "position_concentration_pct": 4.1,
    "max_concentration_limit_pct": 12.0
  },
  "agent_version": "risk-v1.1"
}
```

**Validatieregels (Execution):**
- `verdict` is `approved`, `approved_scaled`, of `declined`
- `max_position_size_usd` ≤ portfolio-limiet (vanuit Risk state)
- `max_slippage_bps` ∈ [1, 50]

#### 2.2.3 Execution → Analyst/Risk: OrderResult (feedback loop)

```json
{
  "signal_id": "sig_20260525_001",
  "order_id": "exec_20260525_001",
  "exchange": "binance",
  "order_type": "limit",
  "side": "buy",
  "requested_size_usd": 1250.0,
  "filled_size_usd": 1248.30,
  "filled_price": 83120.50,
  "slippage_bps": 1.2,
  "status": "filled",
  "duration_ms": 342,
  "error": null,
  "agent_version": "execution-v1.0"
}
```

**Foutgevallen in `status`-veld:**
- `filled` — volledig uitgevoerd
- `partial` — deels gevuld (reden: illiquiditeit of prijsverschuiving)
- `rejected` — exchange weigerde (reden: insufficient balance, trading disabled)
- `timeout` — niet gevuld binnen time-window (30s default)
- `network_error` — connectie verloren tijdens poging (automatische retry max 3x)

### 2.3 Sequencediagram (normale flow)

```
Analyst                    Risk                    Execution              Exchange
  │                         │                         │                      │
  │-- TradeSignal JSON ---->│                         │                      │
  │                         │  VaR + port check       │                      │
  │                         │-- RiskVerdict JSON ---->│                      │
  │                         │                         │-- POST order ------->│
  │                         │                         │<-- order status -----│
  │                         │<-- OrderResult JSON ----│                      │
  │<-- OrderResult JSON ----│                         │                      │
  │                         │                         │                      │
```

**Async variant:** Analyst stuurt signaal, Risk returned direct, Execution returned pas na exchange-response. Analyst kan in de tussentijd nieuwe signalen genereren (rate-limited per Risk's `max_concurrent_signals`).

### 2.4 State management per agent

| Agent | Persistentie | Sleutel | Voorbeeld |
| --- | --- | --- | --- |
| Analyst | SQLite via SessionDB | `signals_{session_id}` | Laatste 1000 signalen + prestaties per signaal-type |
| Risk | SQLite via SessionDB | `portfolio_state`, `risk_limits` | Huidige posities, VaR-historie, drawdown-tracking |
| Execution | SQLite via SessionDB | `orders_{session_id}` | Open orders, fill-history, exchange status |

Elke agent heeft een **in-memory cache** (Python dict + TTL) voor hot data: actuele posities, laatste 5 signalen, exchange latency.

---

## 3. Haalbaarheidsanalyse voor de Windows-omgeving

### 3.1 Beperkingen en risico's

| Risico | Impact | Mitigatie |
| --- | --- | --- |
| **WSL2 netwerkinstabiliteit** | Verbinding tussen Windows agents en WSL2 Redis kan wegvallen bij WSL2 herstart/suspend | Agent-side reconnect loop (exponential backoff, max 5s interval); Health endpoint op Redis-proxy |
| **WSL2 vs Windows clock skew** | Tijdsverschil tussen WSL2 en Windows leidt tot stale signal-validatie | NTP-sync afdwingen in WSL2 (`wsl --sync` of `sudo hwclock -s`); alle timestamps in UTC |
| **Geen Linux kernel features** | Geen eBPF, io_uring of cgroups voor resource-isolatie | Niet nodig voor 3-4 agent-processen; Windows Job Objects als alternatief voor CPU/RAM limits |
| **RAM beperking (8 GB)** | 3 LLM-agents + Redis kan leiden tot swapping | Zie §3.3 resource budget; lokale LLM's uit, cloud-only via OpenRouter/Google |
| **Windows Defender / firewall** | Redis-poorten of FastAPI endpoints kunnen geblokkeerd worden | Expliciete firewall rules: `New-NetFirewallRule -DisplayName "Trading Agents" -Direction Inbound -Protocol TCP -LocalPort 8000-8003,6379 -Action Allow` |
| **Geen native Redis op Windows** | Memurai is niet 100% compatible; WSL2 addt complexity | Accepteer WSL2 voor Redis; documenteer start-volgorde (eerst WSL2 Redis, dan Windows agents) |

### 3.2 Hardware- en software-eisen

| Component | Eis | Opmerking |
| --- | --- | --- |
| OS | Windows 11 Pro (24H2+) | WSL2 vereist Hyper-V-features |
| CPU | 4+ cores (AMD Ryzen 5 5625U voldoet) | Analyst agent profiteert van parallelle LLM-calls |
| RAM | minimaal 8 GB (12+ aanbevolen) | Zie §3.3; bij 8 GB sluit alle apps behalve Hermes |
| Opslag | 20 GB vrij (SSD) | Redis AOF, SQLite databases, logs |
| WSL2 | Ubuntu 24.04 LTS | `wsl --install -d Ubuntu-24.04` |
| Redis | 7.2+ (in WSL2) | `sudo apt install redis` + `sudo systemctl enable redis` |
| Python | 3.11+ (conda hermes-env) | Bestaande Hermes-python; geen aparte venv |
| LLM API keys | OpenRouter / Google Gemini | Geen lokale LLM's — RAM-budget ontoereikend voor 3 agents |

### 3.3 Resource budget (8 GB RAM scenario)

| Proces | RAM (idle) | RAM (piek) | CPU (idle) | CPU (piek) |
| --- | --- | --- | --- | --- |
| Hermes CLI (core) | 120 MB | 250 MB | 0% | 15% |
| Analyst agent (FastAPI) | 80 MB | 200 MB | 0% | 25% (LLM call) |
| Risk agent (FastAPI) | 80 MB | 180 MB | 0% | 20% (LLM call) |
| Execution agent (FastAPI) | 80 MB | 160 MB | 0% | 10% (order routing) |
| Redis (WSL2) | 15 MB | 50 MB | 0% | 5% |
| WSL2 kernel + overhead | 500 MB | 700 MB | 0-2% | 5% |
| **Totaal agents** | **875 MB** | **1.54 GB** | **0-2%** | **~70% (kort)** |

**Conclusie:** Binnen 8 GB RAM is 1.5-2 GB voor de agents acceptabel (18-25% van totaal). Windows + browser + andere apps gebruiken ~3-4 GB, blijft 2-3 GB buffer. Geen swapping risico zolang lokale LLM's worden vermeden.

### 3.4 Aanbevolen opstartprocedure

```
Stap 1: wsl -- start Redis (systemctl start redis)
         → Verify: redis-cli ping
Stap 2: Start Execution Agent (uvicorn ... 8003)
Stap 3: Start Risk Agent (uvicorn ... 8002)
Stap 4: Start Analyst Agent (uvicorn ... 8001)
Stap 5: Start Gateway / Orchestrator (uvicorn ... 8000)
Stap 6: hermes -p trading-core  (monitoring dashboard)
```

**Waarom omgekeerde volgorde (Execution eerst):**
- Execution heeft geen dependency op Risk of Analyst (ontvangt pas berichten nadat Risk heeft goedgekeurd)
- Risk heeft Execution nodig om OrderResult te kunnen ontvangen (feedback loop)
- Analyst heeft beide nodig voor complete signaal-feedback cyclus
- Orchestrator als laatste om te voorkomen dat signalen worden gestuurd naar agents die nog niet klaar zijn

---

## 4. Failure Mode & Resilience Matrix

### 4.1 Foutscenario's en mitigaties

| Failure Mode | Detectie | Impact | Mitigatie | Recovery Time | Opmerking |
| --- | --- | --- | --- | --- | --- |
| **Risk Agent crash** | Heartbeat time-out (2x interval = 10s) | Geen nieuwe trades; openstaande posities blijven (uitvoerbare order niet gecanceld) | **Circuit breaker:** Analyst schakelt naar `risk_bypass=false`, stopt signaal-generatie tot Risk herstart. **State recovery:** Risk leest portfolio_state uit SQLite bij opstart | < 15s (autorestart via Hermes supervisor) | Geen trade-executie zonder Risk-approval; dit is een bewuste "fail-closed" ontwerpkeuze |
| **Execution Agent crash** | Heartbeat time-out | Open orders onbevestigd; geen nieuwe order-executie | **Idempotency:** alle OrderResult hebben een `signal_id`; Execution herstart en pollt exchange voor open orders. **Queue drain:** Redis stream bewaart onbevestigde RiskVerdicts | < 10s | Execution is het enige agens met exchange API keys; bij herstart moeten secrets opnieuw geladen worden uit `.env` |
| **Analyst Agent crash** | Heartbeat time-out | Geen nieuwe signalen | **Laatste signaal vastleggen:** SQLite slaat laatste 5 signalen per symbool op; Analyst herstart en hervat op laatste consistent state. **Risk blijft actief** met trade-monitoring | < 10s | Analyst is stateless; TradeSignal wordt pas impactvol als Risk het approveert |
| **WSL2 Redis disconnect** | Redis connection error in agent-log | Status/pub-sub onbeschikbaar; inter-agent communicatie via FastAPI blijft werken | **Degraded mode:** agents schakelen Redis uit en vallen terug op FastAPI-only. **Reconnect:** exponential backoff tot 30s; na 3 minuten Redis-alert. **Fallback:** agents blijven functioneren zonder Redis (geen heartbeats, geen broadcast) | 0-30s (transparant) | Redis is een secundair kanaal; primaire communicatie verloopt via FastAPI |
| **Exchange API down/timeout** | HTTP error/timeout van exchange | Order kan niet worden geplaatst of gevuld | **Retry policy:** Execution retry max 3x (exponential backoff: 1s, 3s, 9s). **Fallback exchange:** indien geconfigureerd en market available. **Order timeout:** 30s time-window, daarna `status: "timeout"` | 30-60s (incl. retries) | Een timeout geen fatale fout; OrderResult bevat `error`-veld voor Risk om te analyseren |
| **LLM provider timeout** | LLM-call timeout (15s default) | Analyst/Risk kan geen signaal/verdict genereren | **Graceful degradation:** Agent returned `LLM_TIMEOUT` status; Orchestrator kan besluiten eerder signaal te hergebruiken (max 5 min oud). **Dedicated fallback model:** `gemini-2.5-flash` als backup voor `deepseek-v4-flash` | 15-20s | Gebruik `httpx` met `timeout=15` per LLM call; separaat timeout per agent |
| **Clock skew (WSL2 vs Windows)** | Timestamp mismatch > 5s bij signaalvalidatie | Stale-signal detectie kan vals positief/negatief zijn | **NTP-sync:** `wsl --sync` of cronjob elke 15 min. **Window-based validatie:** Risk accepteert signalen ≤ 60s oud (niet ≤ 30s) als `confidence` ≥ 0.9 | Continue (drift-correctie) | Monitoring-metric in Risk: `max_clock_drift_seconds` |
| **RAM uitputting / swap** | Pagination file usage > 50% of RAM < 1 GB beschikbaar | Alles vertraagt; LLM-calls kunnen OOM krijgen | **Memory guard:** elke agent monitort `psutil.virtual_memory().percent` ≥ 90%; initieert graceful shutdown van zichzelf (laatste State persisted). **Agent priority:** Risk > Execution > Analyst voor resource-toewijzing bij memory pressure | N.V.T. (preventief shutdown) | Graceful shutdown schrijft laatste portfoliostaat, cancelt pending orders, logt "MEMORY_CRITICAL_SHUTDOWN" |
| **Poortconflict** | FastAPI start niet (address already in use) | Agent niet beschikbaar | **Poortscan bij startup:** agents proberen defined port, fallback naar `defined_port + random(1,100)`. **Poortregistratie:** Redis key `agent:{name}:port` of `agent_port_map.yaml` bij Orchestrator | < 2s (autofallback) | Alleen relevant bij ontwikkelen/testen op zelfde machine |
| **Oneindige loop / hangende agent** | Heartbeat stopt (geen exception, gewoon geen response) | Agent "zombie" — geen output, geen processing | **Watchdog:** Hermes supervisor stuurt health-check elke 5s naar `/health`; 3x missed → kill + restart. **Health endpoint:** `GET /health` retourneert `{"status": "ok", "last_signal_ts": "...", "uptime_s": 123}` | 20-30s (detectie 15s + restart 5-15s) | Health-check bevat `last_signal_ts` om "stil maar alive" zombie te detecteren |

### 4.2 Resilience matrix (overzicht)

| Laag | Mechanisme | Type |
| --- | --- | --- |
| **Detectie** | Heartbeat (pub/sub + health endpoint) | Push/pull hybrid |
| **Detectie** | Timeout monitoring per LLM call | Per-call guard |
| **Detectie** | Memory guard (psutil) | Proactief |
| **Recovery** | Stateful restart (SQLite) | Cold start met herstel |
| **Recovery** | Idempotent order dispatch (signal_id) | Duplicate-safe |
| **Recovery** | Exponential backoff retry | Netwerkfouten |
| **Degradatie** | Redis fallback → FastAPI-only | Graceful |
| **Degradatie** | Risk bypass lock (circuit breaker) | Fail-closed |
| **Degradatie** | LLM timeout → signaal hergebruik (5 min TTL) | Graceful |
| **Transfer** | Order polling bij crash (exchange API) | Dead-agent recovery |

### 4.3 Ontwerpprincipes voor resilience

1. **Fail closed, niet fail open.** Geen trade zonder Risk-approval. Een crash van Risk stopt alle nieuwe trades tot herstel.
2. **Heavyweight protocol = degradatiekanaal.** Redis is optioneel; alle agents blijven functioneren via FastAPI-only.
3. **Idempotentie voorkomt dubbele orders.** `signal_id` is de unique key; als Execution een crash herstart, pollt het de exchange voor orders met dat ID voordat het een nieuwe plaatst.
4. **Elk agens is verantwoordelijk voor eigen state persistence.** Geen shared database voor portfolio_state; Risk schrijft zelf en leest zelf.
5. **Orchestrator is een monitor, geen controller.** De orchestrator (poort 8000) observeert health en routed signalen, maar grijpt niet direct in in de Risk-approval of Execution-flow. Dit voorkomt een single point of failure.

### 4.4 Scenario: Risk Agent crash tijdens actieve trade

```
T=0s: Analyst stuurt TradeSignal naar Risk
T=1s: Risk start verificatie, maar crash mid-process (portfolio_state opgeslagen)
T=3s: Heartbeat timeout — Orchestrator detecteert Risk offline
T=3s: Orchestrator activeert circuit breaker: alle signalen worden in Redis queue bewaard
T=5s: Orchestrator start Risk Agent (autorestart)
T=6s: Risk start: laadt portfolio_state uit SQLite → detecteert "mid-flight" signal_id via logs
T=7s: Risk leest onbevestigd signaal uit Redis dead-letter stream
T=8s: Risk verwerkt signaal alsnog; stuurt RiskVerdict
T=9s: Execution ontvangt verdict (via FastAPI direct)
T=10s: Normale flow hervat
```

**Totale impact:** 7 seconden vertraging op één trade-signaal. Geen verloren data, geen double-spend.

---
*Einde document. Alle vier secties zijn volledig uitgewerkt: Tech Stack (§1), Agent Architectuur (§2), Windows Haalbaarheid (§3), Failure Mode & Resilience (§4).*