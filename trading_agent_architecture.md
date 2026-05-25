# Multi-Agent Trading Team — Technische Architectuur

> **Status:** Vooronderzoek (proof-of-concept fase)
> **Datum:** 2026-05-25

---

## 1. Visie & Doel

Een multi-agent systeem dat marktanalyse, risicobeheer en orderuitvoering ontkoppelt in gespecialiseerde, asynchrone agents die via een gestandaardiseerd berichtenprotocol samenwerken. Elk agent heeft een eigen verantwoordelijkheid, model-context en toolset — geen monolithische handelslogica.

**Principes:**

- **Separation of Concerns** — elk agent doet exact één ding
- **Fail-isolated** — een crash in de analyst-agent brengt risk-agent niet omver
- **Verifieerbare berichten** — ieder inter-agent signaal heeft timestamp, schema en TTL
- **Geen exchange-afhankelijkheid in kern** — exchange-adapters zijn pluggable

---

## 2. Agent-Rollen

| Rol | Verantwoordelijkheid | Taal/Framework | Communicatie |
|-----|---------------------|----------------|--------------|
| **Analyst Agent** | Genereert koop/verkoop-signaal obv technische indicatoren of ML-model | Python, FastAPI-client | HTTP POST naar Risk Agent |
| **Risk Agent** | Valideert signaal (TTL, max exposure, drawdown-limiet) | Python, FastAPI-server | HTTP POST naar Execution Agent |
| **Execution Agent** | Plaatst order obv gevalideerd signaal | Python (exchange-agnostisch) | Gateway → Exchange-adapter |
| **Market Data Agent** | Stroomt real-time data (ohlc, orderbook) | WebSocket / gRPC stream | Publish/Subscribe |
| **Portfolio Agent** | Houdt positie-, PnL- en marge-administratie bij | Python, SQLite/Postgres | Periodic sync + events |
| **Orchestrator Agent** | Coördineert agents, heartbeat, health-checks, circuit-breaker | Hermes Kanban / cron | Interne message bus |

---

## 3. Tech Stack — Gemotiveerde Keuzes

### 3.1 Communicatielaag

| Component | Keuze | Waarom |
|-----------|-------|--------|
| Inter-agent API | **FastAPI** (async, Pydantic-validatie) | Laagste latency voor HTTP, ingebouwde schema-validatie, OpenAPI-docs |
| Service discovery | **Static mapping** (config.yaml) / optioneel Consul | In dit stadium vaste localhost-ports; later Service Discovery |
| Berichtformaat | **JSON** via Pydantic-modellen | Schema-afdwingbaar, leesbaar, universeel combineerbaar |
| Async transport | **httpx.AsyncClient** (analyst→risk) + uvicorn (risk-server) | non-blocking, hoge throughput |

### 3.2 Datamodellen

Alle inter-agent berichten gebruiken Pydantic BaseModel:

```python
class TradeSignal(BaseModel):
    timestamp_ms: int           # Unix milliseconden (generatie)
    asset_ticker: str           # "BTC/USD", "AAPL", etc.
    action: str                 # "buy" | "sell" | "hold"
    confidence_score: float     # 0.0 – 1.0
    ttl_ms: int = 200           # default 200ms — signaal is anders stale
    metadata: dict = {}         # extensieveld voor domeinspecifieke data
```

### 3.3 Agent Framework

| Aspect | Keuze |
|--------|-------|
| Runtime | Python 3.13+ (async/await) |
| HTTP-server | uvicorn + FastAPI |
| HTTP-client | httpx (AsyncClient) |
| Config | pydantic-settings / YAML |
| Logging | structlog of stdlib logging (JSON-formatted) |
| Testen | pytest + httpx TestClient |

### 3.4 Deployment (toekomst)

- Containerization: Docker (per agent een container)
- Orchestratie: docker-compose (dev) / Kubernetes (prod)
- Health-check: /health endpoint per agent
- Monitoring: Prometheus metrics + Grafana dashboards

---

## 4. Communicatieflow

```
┌──────────────┐     POST /signal     ┌──────────────┐     POST /execute     ┌──────────────────┐
│              │  {timestamp_ms,      │              │  {validated_signal}  │                  │
│  Market Data ├─────────────────────►│    Risk      ├──────────────────────►│   Execution      │
│   Agent      │   asset_ticker,      │    Agent     │                       │    Agent         │
│              │   action, score}     │              │                       │                  │
└──────────────┘                     └──────┬───────┘                       └──────────────────┘
                                            │
                                    TTL-check │ Exposure-check
                                    (<200ms)  │ (max pos. size)
                                            │
                                   Reject ➔ log + event
```

**Stappen:**

1. Analyst genereert signaal → POST met `TradeSignal` naar Risk Agent (`:8001/signal`)
2. Risk Agent valideert:
   - TTL: `now - timestamp_ms < 200ms`
   - Schema: Pydantic dwingt veldtypes af
   - Exposure: (toekomst) max open posities
3. Bij accept: POST naar Execution Agent (`:8002/execute`)
4. Bij reject: log + event naar Orchestrator

---

## 5. Foutafhandeling & Resilientie

| Scenario | Gedrag |
|----------|--------|
| Risk Agent niet bereikbaar | Analyst retry 3× (exponential backoff), daarna circuit-breaker (30s) |
| TTL overschreden | Signaal wordt stil verworpen + logging (dit is **expected behavior** bij oude data) |
| Ongeldig schema | Risk Agent retourneert 422 + detail; Analyst logt fout |
| Time-out | httpx timeout=1s, daarna fast-fail |

---

## 6. Waarom HTTP (FastAPI) en niet Message Queue?

In de PoC-fase is HTTP de juiste keuze:

| Criterium | HTTP (FastAPI) | Message Queue (Kafka/RabbitMQ) |
|-----------|---------------|-------------------------------|
| Opstarttijd | Seconden (uvicorn) | Minuten (ZK + broker) |
| Debugbaar | curl / browser / Swagger | Extra tooling nodig |
| Schema-validatie | Pydantic out-of-the-box | Schema Registry nodig |
| latency (localhost) | ~0.5–2ms | ~2–10ms |
| Complexiteit | Laag | Hoog |

**Evolutiepad:** HTTP → gRPC (voor high-frequency) → NATS / RabbitMQ (voor broadcasting).

---

## 7. Beveiliging (toekomst)

- Inter-agent API-key authenticatie (X-API-Key header)
- mTLS tussen agents (binnen Kubernetes)
- Rate-limiting per agent
- Input-validatie obv Pydantic (standaard)

---

## 8. Directorystructuur (voorgesteld)

```
trading_agents/
├── agents/
│   ├── analyst/
│   │   ├── main.py
│   │   └── strategies/
│   ├── risk/
│   │   ├── main.py
│   │   └── rules/
│   └── execution/
│       ├── main.py
│       └── exchanges/
├── schemas/
│   ├── trade_signal.py        # Pydantic-modellen
│   └── __init__.py
├── poc_communicatie/          # Huidige PoC
│   ├── mock_analyst.py
│   ├── mock_risk.py
│   └── test_communicatie.sh
├── docker-compose.yml
├── trading_agent_architecture.md
└── README.md
```

---

## 9. Openstaande Vragen / Volgende Stappen

| Vraag | Actie |
|-------|-------|
| Welke exchange(s) als eerste target? | Kiezen obv liquiditeit + API-kwaliteit (bv. Binance REST + WS) |
| ML-model voor analyst? | LSTM / XGBoost / eigen indicator? |
| Database voor portfolio-agent? | SQLite (dev) → TimescaleDB (prod)? |
| Orchestrator: Hermes Kanban of eigen? | Afhankelijk van gewenste autonomie |
| Welke latency-eis? | sub-100ms (scalping) of seconden (swing)? |