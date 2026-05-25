"""
Trading team — Pydantic datamodellen.

Bevat de formele schema's voor inter-agent communicatie:
TradeSignal, RiskVerdict, OrderResult.

Scope: uitsluitend datavalidatie. Geen FastAPI, netwerk of agent-logica.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────


class TradeAction(str, Enum):
    """Toegestane handelsrichtingen."""

    BUY = "buy"
    SELL = "sell"


class Verdict(str, Enum):
    """Risk-goedkeuringstypes."""

    APPROVED = "approved"
    APPROVED_SCALED = "approved_scaled"
    DECLINED = "declined"


class OrderStatus(str, Enum):
    """Execution-statusmogelijkheden."""

    FILLED = "filled"
    PARTIAL = "partial"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"


# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

SIGNAL_TTL_SECONDS: int = 30
"""Maximale toegestane leeftijd van een TradeSignal in seconden."""

MAX_SLIPPAGE_BPS: int = 50
"""Maximale toegestane slippage in basispunten."""

MIN_CONFIDENCE: float = 0.0
MAX_CONFIDENCE: float = 1.0


# ──────────────────────────────────────────────
# TradeSignal
# ──────────────────────────────────────────────


class TradeSignal(BaseModel):
    """
    Analyseresultaat: koop- of verkoopsignaal gegenereerd door de Analyst agent.

    Geldigheidsduur (TTL): 30 seconden vanaf timestamp.
    """

    signal_id: str = Field(..., description="Uniek signaal-identificatienummer")
    timestamp: datetime = Field(
        ...,
        description="ISO-8601 UTC-tijdstip van signaalgeneratie",
    )
    symbol: str = Field(..., min_length=1, description="Handelspaar, bv. BTC/USDT")
    action: TradeAction = Field(..., description="Koop (buy) of verkoop (sell)")
    confidence: float = Field(
        ...,
        ge=MIN_CONFIDENCE,
        le=MAX_CONFIDENCE,
        description="Vertrouwensscore [0.0, 1.0]",
    )
    entry_price_min: Decimal = Field(
        ..., gt=Decimal("0"), description="Minimale entry-prijs (positief)"
    )
    entry_price_max: Decimal = Field(
        ..., gt=Decimal("0"), description="Maximale entry-prijs (positief)"
    )
    stop_loss: Decimal = Field(
        ..., gt=Decimal("0"), description="Stop-loss niveau (positief)"
    )
    take_profit: Decimal = Field(
        ..., gt=Decimal("0"), description="Take-profit niveau (positief)"
    )
    timeframe: str = Field(
        ..., min_length=1, description="Tijdframe van analyse, bv. 1h, 15m"
    )
    rationale: str = Field(
        ..., min_length=1, description="Menselijk leesbare onderbouwing"
    )
    sources: list[str] = Field(
        default_factory=list,
        description="Bronnen gebruikt voor signaal (exchange, sentiment, etc.)",
    )
    agent_version: str = Field(
        ..., min_length=1, description="Versie van de Analyst agent"
    )

    # ── Field validators ──────────────────────

    @field_validator("confidence")
    @classmethod
    def _confidence_bound(cls, v: float) -> float:
        """Dwingt confidence in [0.0, 1.0] af — redundant met Field(ge/le) maar expliciet."""
        if v < MIN_CONFIDENCE or v > MAX_CONFIDENCE:
            raise ValueError(
                f"confidence moet tussen {MIN_CONFIDENCE} en {MAX_CONFIDENCE} liggen, "
                f"kreeg {v}"
            )
        return v

    @field_validator("entry_price_min", "entry_price_max", "stop_loss", "take_profit")
    @classmethod
    def _prices_positive(cls, v: Decimal) -> Decimal:
        """Alle prijzen moeten strikt positief zijn."""
        if v <= Decimal("0"):
            raise ValueError(f"Prijs moet positief zijn, kreeg {v}")
        return v

    # ── Model validators ──────────────────────

    @model_validator(mode="after")
    def _enforce_ttl(self) -> TradeSignal:
        """TTL-check: signaal mag niet ouder zijn dan SIGNAL_TTL_SECONDS."""
        age = datetime.now(timezone.utc) - self.timestamp
        if age.total_seconds() > SIGNAL_TTL_SECONDS:
            raise ValueError(
                f"Signaal is {age.total_seconds():.0f}s oud — "
                f"maximaal toegestaan is {SIGNAL_TTL_SECONDS}s (TTL overschreden)"
            )
        return self

    @model_validator(mode="after")
    def _prices_logical_order(self) -> TradeSignal:
        """Controleert logische prijsrelaties op basis van action (buy/sell)."""
        if self.entry_price_min >= self.entry_price_max:
            raise ValueError(
                f"entry_price_min ({self.entry_price_min}) moet kleiner zijn dan "
                f"entry_price_max ({self.entry_price_max})"
            )

        if self.action == TradeAction.BUY:
            # Buy: stop_loss < entry_price_min < entry_price_max < take_profit
            if self.stop_loss >= self.entry_price_min:
                raise ValueError(
                    f"Bij buy moet stop_loss ({self.stop_loss}) < entry_price_min "
                    f"({self.entry_price_min})"
                )
            if self.take_profit <= self.entry_price_max:
                raise ValueError(
                    f"Bij buy moet take_profit ({self.take_profit}) > entry_price_max "
                    f"({self.entry_price_max})"
                )

        elif self.action == TradeAction.SELL:
            # Sell: take_profit < entry_price_min < entry_price_max < stop_loss
            if self.take_profit >= self.entry_price_min:
                raise ValueError(
                    f"Bij sell moet take_profit ({self.take_profit}) < entry_price_min "
                    f"({self.entry_price_min})"
                )
            if self.stop_loss <= self.entry_price_max:
                raise ValueError(
                    f"Bij sell moet stop_loss ({self.stop_loss}) > entry_price_max "
                    f"({self.entry_price_max})"
                )

        return self


# ──────────────────────────────────────────────
# RiskVerdict
# ──────────────────────────────────────────────


class RiskMetrics(BaseModel):
    """Risicometrieken meegestuurd met een RiskVerdict."""

    portfolio_var_99pct_1h: float = Field(
        ..., ge=0.0, description="Value-at-Risk (99%, 1 uur)"
    )
    current_drawdown: float = Field(
        ..., ge=0.0, le=1.0, description="Huidige drawdown fractie [0, 1]"
    )
    max_drawdown_limit: float = Field(
        ..., ge=0.0, le=1.0, description="Maximaal toegestane drawdown [0, 1]"
    )
    position_concentration_pct: float = Field(
        ..., ge=0.0, description="Positieconcentratie in % van portefeuille"
    )
    max_concentration_limit_pct: float = Field(
        ..., ge=0.0, description="Maximaal toegestane concentratie in %"
    )


class RiskVerdict(BaseModel):
    """
    Risicobeoordeling van de Risk agent op een TradeSignal.

    Bepaalt of een trade mag worden uitgevoerd, geschaald of geweigerd.
    """

    signal_id: str = Field(..., description="Verwijst naar het originele signaal-ID")
    original_signal: TradeSignal = Field(
        ..., description="Het originele TradeSignal (ter referentie)"
    )
    verdict: Verdict = Field(..., description="Goedkeuringstype")
    max_position_size_usd: Decimal = Field(
        ...,
        ge=Decimal("0"),
        description="Maximale positiegrootte in USD (0 bij DECLINED)",
    )
    max_slippage_bps: int = Field(
        ...,
        ge=1,
        le=MAX_SLIPPAGE_BPS,
        description="Maximale slippage in basispunten [1, 50]",
    )
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Risicoscore [0 = veilig, 1 = extreem risico]",
    )
    reasoning: str = Field(
        ..., min_length=1, description="Onderbouwing van de Risk-beslissing"
    )
    risk_metrics: RiskMetrics = Field(
        ..., description="Gedetailleerde risicometrieken"
    )
    agent_version: str = Field(
        ..., min_length=1, description="Versie van de Risk agent"
    )

    @model_validator(mode="after")
    def _verdict_requires_signal_id_match(self) -> RiskVerdict:
        """De signal_id moet overeenkomen met het originele signaal."""
        if self.signal_id != self.original_signal.signal_id:
            raise ValueError(
                f"signal_id ({self.signal_id}) komt niet overeen met "
                f"original_signal.signal_id ({self.original_signal.signal_id})"
            )
        return self

    @model_validator(mode="after")
    def _declined_has_no_position(self) -> RiskVerdict:
        """Een declined verdict mag geen positiegrootte > 0 hebben."""
        if self.verdict == Verdict.DECLINED and self.max_position_size_usd > Decimal("0"):
            raise ValueError(
                "Verdict is DECLINED, maar max_position_size_usd is niet 0"
            )
        return self

    @model_validator(mode="after")
    def _approved_requires_positive_size(self) -> RiskVerdict:
        """Een approved/approved_scaled verdict moet een positieve size hebben."""
        if self.verdict != Verdict.DECLINED and self.max_position_size_usd <= Decimal("0"):
            raise ValueError(
                f"Verdict is {self.verdict.value}, maar max_position_size_usd is 0"
            )
        return self


# ──────────────────────────────────────────────
# OrderResult (uitvoerder)
# ──────────────────────────────────────────────


class OrderResult(BaseModel):
    """
    Uitvoeringsresultaat van de Execution agent.

    Bevat de daadwerkelijke fill-status, prijs en eventuele fouten.
    """

    signal_id: str = Field(..., description="Verwijst naar het originele signaal-ID")
    order_id: str = Field(..., description="Uniek order-identificatienummer")
    exchange: str = Field(..., min_length=1, description="Exchange waar order is geplaatst")
    order_type: str = Field(
        ..., min_length=1, description="Order-type (limit, market, etc.)"
    )
    side: TradeAction = Field(..., description="Kant van de trade (buy/sell)")
    requested_size_usd: Decimal = Field(
        ..., gt=Decimal("0"), description="Gevraagde positiegrootte in USD"
    )
    filled_size_usd: Decimal = Field(
        ..., ge=Decimal("0"), description="Werkelijk gevulde grootte in USD"
    )
    filled_price: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0"),
        description="Gemiddelde gevulde prijs (None bij rejected/timeout)",
    )
    slippage_bps: Optional[int] = Field(
        default=None,
        ge=0,
        le=MAX_SLIPPAGE_BPS,
        description="Gerealiseerde slippage in basispunten",
    )
    status: OrderStatus = Field(..., description="Eindstatus van de order")
    duration_ms: int = Field(
        ..., ge=0, description="Orderduur in milliseconden"
    )
    error: Optional[str] = Field(
        default=None, description="Foutmelding (None bij succes)"
    )
    agent_version: str = Field(
        ..., min_length=1, description="Versie van de Execution agent"
    )

    @model_validator(mode="after")
    def _filled_requires_price(self) -> OrderResult:
        """Een filled/partial order moet een filled_price hebben."""
        if self.status in (OrderStatus.FILLED, OrderStatus.PARTIAL):
            if self.filled_price is None:
                raise ValueError(
                    f"Status is {self.status.value}, maar filled_price is None"
                )
            if self.filled_size_usd <= Decimal("0"):
                raise ValueError(
                    f"Status is {self.status.value}, maar filled_size_usd is 0"
                )
        return self

    @model_validator(mode="after")
    def _failed_has_error_message(self) -> OrderResult:
        """Een rejected/timeout/network_error order moet een error hebben."""
        if self.status in (
            OrderStatus.REJECTED,
            OrderStatus.TIMEOUT,
            OrderStatus.NETWORK_ERROR,
        ):
            if self.error is None or self.error.strip() == "":
                raise ValueError(
                    f"Status is {self.status.value}, maar error is leeg/None"
                )
        return self

    @model_validator(mode="after")
    def _filled_size_not_exceeds_requested(self) -> OrderResult:
        """Gevulde grootte mag niet groter zijn dan gevraagde grootte."""
        if self.filled_size_usd > self.requested_size_usd:
            raise ValueError(
                f"filled_size_usd ({self.filled_size_usd}) is groter dan "
                f"requested_size_usd ({self.requested_size_usd})"
            )
        return self