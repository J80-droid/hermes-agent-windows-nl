"""
Tests voor src/core/models.py.

Bewijst dat ongeldige data onmiddellijk een pydantic.ValidationError opwerpt.
Geen FastAPI, netwerk of agent-logica.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.core.models import (
    MAX_CONFIDENCE,
    MIN_CONFIDENCE,
    SIGNAL_TTL_SECONDS,
    OrderResult,
    OrderStatus,
    RiskMetrics,
    RiskVerdict,
    TradeAction,
    TradeSignal,
    Verdict,
)


# ══════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════


def _valid_signal_kwargs(**overrides) -> dict:
    """Bare-minimum geldige TradeSignal-parameters — TTL-respecting timestamp (nu)."""
    base = {
        "signal_id": "sig_test_001",
        "timestamp": datetime.now(timezone.utc),
        "symbol": "BTC/USDT",
        "action": "buy",
        "confidence": 0.82,
        "entry_price_min": Decimal("82500.0"),
        "entry_price_max": Decimal("83400.0"),
        "stop_loss": Decimal("79800.0"),
        "take_profit": Decimal("87500.0"),
        "timeframe": "1h",
        "rationale": "Bullish pennant breakout",
        "sources": ["binance"],
        "agent_version": "analyst-v1.2",
    }
    base.update(overrides)
    return base


def _valid_risk_metrics(**overrides) -> dict:
    base = {
        "portfolio_var_99pct_1h": 0.018,
        "current_drawdown": 0.04,
        "max_drawdown_limit": 0.15,
        "position_concentration_pct": 4.1,
        "max_concentration_limit_pct": 12.0,
    }
    base.update(overrides)
    return base


def _valid_signal() -> TradeSignal:
    """Factory voor een geldig TradeSignal (binnen TTL)."""
    return TradeSignal(**_valid_signal_kwargs())


def _valid_risk_verdict(**overrides) -> dict:
    signal = _valid_signal()
    base = {
        "signal_id": signal.signal_id,
        "original_signal": signal,
        "verdict": "approved",
        "max_position_size_usd": Decimal("1250.0"),
        "max_slippage_bps": 5,
        "risk_score": 0.31,
        "reasoning": "VaR binnen limieten",
        "risk_metrics": RiskMetrics(**_valid_risk_metrics()),
        "agent_version": "risk-v1.1",
    }
    base.update(overrides)
    return base


def _valid_order_result(**overrides) -> dict:
    base = {
        "signal_id": "sig_test_001",
        "order_id": "exec_test_001",
        "exchange": "binance",
        "order_type": "limit",
        "side": "buy",
        "requested_size_usd": Decimal("1250.0"),
        "filled_size_usd": Decimal("1248.30"),
        "filled_price": Decimal("83120.50"),
        "slippage_bps": 1,
        "status": "filled",
        "duration_ms": 342,
        "error": None,
        "agent_version": "execution-v1.0",
    }
    base.update(overrides)
    return base


# ══════════════════════════════════════════════
# TradeSignal — confidence validatie
# ══════════════════════════════════════════════


class TestTradeSignalConfidence:
    def test_below_minimum_raises(self):
        kwargs = _valid_signal_kwargs(confidence=-0.01)
        with pytest.raises(ValidationError) as exc:
            TradeSignal(**kwargs)
        msg = str(exc.value)
        assert "confidence" in msg.lower() or "0.0" in msg

    def test_above_maximum_raises(self):
        kwargs = _valid_signal_kwargs(confidence=1.5)
        with pytest.raises(ValidationError) as exc:
            TradeSignal(**kwargs)
        msg = str(exc.value)
        assert "confidence" in msg.lower() or "1.0" in msg

    def test_boundary_zero_ok(self):
        kwargs = _valid_signal_kwargs(confidence=MIN_CONFIDENCE)
        s = TradeSignal(**kwargs)
        assert s.confidence == 0.0

    def test_boundary_one_ok(self):
        kwargs = _valid_signal_kwargs(confidence=MAX_CONFIDENCE)
        s = TradeSignal(**kwargs)
        assert s.confidence == 1.0


# ══════════════════════════════════════════════
# TradeSignal — prijs validatie
# ══════════════════════════════════════════════


class TestTradeSignalPrices:
    def test_negative_entry_price_min_raises(self):
        kwargs = _valid_signal_kwargs(entry_price_min=Decimal("-100"))
        with pytest.raises(ValidationError):
            TradeSignal(**kwargs)

    def test_zero_stop_loss_raises(self):
        kwargs = _valid_signal_kwargs(stop_loss=Decimal("0"))
        with pytest.raises(ValidationError):
            TradeSignal(**kwargs)

    def test_entry_min_gt_entry_max_raises(self):
        kwargs = _valid_signal_kwargs(
            entry_price_min=Decimal("84000"),
            entry_price_max=Decimal("82000"),
        )
        with pytest.raises(ValidationError):
            TradeSignal(**kwargs)

    def test_buy_stop_loss_above_entry_min_raises(self):
        kwargs = _valid_signal_kwargs(
            action="buy",
            stop_loss=Decimal("83000"),  # >= entry_price_min (82500)
        )
        with pytest.raises(ValidationError):
            TradeSignal(**kwargs)

    def test_buy_take_profit_below_entry_max_raises(self):
        kwargs = _valid_signal_kwargs(
            action="buy",
            take_profit=Decimal("83000"),  # <= entry_price_max (83400)
        )
        with pytest.raises(ValidationError):
            TradeSignal(**kwargs)

    def test_sell_stop_loss_above_entry_max_ok(self):
        """Sell: stop_loss moet > entry_price_max zijn."""
        kwargs = _valid_signal_kwargs(
            action="sell",
            entry_price_min=Decimal("82000"),
            entry_price_max=Decimal("83000"),
            stop_loss=Decimal("86000"),
            take_profit=Decimal("80000"),
        )
        s = TradeSignal(**kwargs)
        assert s.action == TradeAction.SELL

    def test_sell_take_profit_below_entry_min_ok(self):
        """Sell: take_profit moet < entry_price_min zijn."""
        kwargs = _valid_signal_kwargs(
            action="sell",
            entry_price_min=Decimal("82000"),
            entry_price_max=Decimal("83000"),
            stop_loss=Decimal("86000"),
            take_profit=Decimal("80000"),
        )
        s = TradeSignal(**kwargs)
        assert s.take_profit == Decimal("80000")

    def test_sell_wrong_stop_loss_raises(self):
        """Sell: stop_loss moet > entry_price_max; als het eronder zit, faalt het."""
        kwargs = _valid_signal_kwargs(
            action="sell",
            entry_price_min=Decimal("82000"),
            entry_price_max=Decimal("83000"),
            stop_loss=Decimal("82500"),  # < entry_price_max — fout
            take_profit=Decimal("80000"),
        )
        with pytest.raises(ValidationError):
            TradeSignal(**kwargs)


# ══════════════════════════════════════════════
# TradeSignal — TTL validatie
# ══════════════════════════════════════════════


class TestTradeSignalTTL:
    def test_ttl_barely_within_limit_ok(self):
        """Timestamp exact SIGNAL_TTL_SECONDS geleden — mag nog net."""
        ts = datetime.now(timezone.utc) - timedelta(seconds=SIGNAL_TTL_SECONDS)
        kwargs = _valid_signal_kwargs(timestamp=ts)
        s = TradeSignal(**kwargs)
        assert s.timestamp == ts

    def test_ttl_45_seconds_old_raises(self):
        """
        TradeSignal met een leeftijd van 45 seconden moet een ValidationError geven
        (TTL is 30 seconden).
        """
        age = 45
        ts = datetime.now(timezone.utc) - timedelta(seconds=age)
        kwargs = _valid_signal_kwargs(timestamp=ts)
        with pytest.raises(ValidationError) as exc:
            TradeSignal(**kwargs)
        msg = str(exc.value).lower()
        assert "ttl" in msg or str(SIGNAL_TTL_SECONDS) in msg

    def test_ttl_one_second_past_limit_raises(self):
        """Signaal exact 1 seconde over TTL moet falen."""
        ts = datetime.now(timezone.utc) - timedelta(seconds=SIGNAL_TTL_SECONDS + 1)
        kwargs = _valid_signal_kwargs(timestamp=ts)
        with pytest.raises(ValidationError):
            TradeSignal(**kwargs)


# ══════════════════════════════════════════════
# RiskVerdict validatie
# ══════════════════════════════════════════════


class TestRiskVerdict:
    def test_valid_approved_risk_verdict(self):
        """Een volledig correct RiskVerdict mag geen fout geven."""
        verdict = RiskVerdict(**_valid_risk_verdict())
        assert verdict.verdict == Verdict.APPROVED
        assert verdict.signal_id == "sig_test_001"

    def test_signal_id_mismatch_raises(self):
        """Mismatch tussen signal_id en original_signal.signal_id moet falen."""
        kwargs = _valid_risk_verdict(signal_id="sig_wrong")
        with pytest.raises(ValidationError) as exc:
            RiskVerdict(**kwargs)
        msg = str(exc.value).lower()
        assert "signal_id" in msg

    def test_declined_with_positive_size_raises(self):
        """DECLINED verdict mag geen max_position_size_usd > 0 hebben."""
        kwargs = _valid_risk_verdict(
            verdict="declined",
            max_position_size_usd=Decimal("100"),
        )
        with pytest.raises(ValidationError):
            RiskVerdict(**kwargs)

    def test_declined_with_zero_size_ok(self):
        """DECLINED verdict met size=0 is nu geldig (model accepteert ge=0)."""
        kwargs = _valid_risk_verdict(
            verdict="declined",
            max_position_size_usd=Decimal("0"),
        )
        verdict = RiskVerdict(**kwargs)
        assert verdict.verdict == Verdict.DECLINED
        assert verdict.max_position_size_usd == Decimal("0")

    def test_risk_score_out_of_range_raises(self):
        kwargs = _valid_risk_verdict(risk_score=1.5)
        with pytest.raises(ValidationError):
            RiskVerdict(**kwargs)

    def test_negative_max_position_size_raises(self):
        kwargs = _valid_risk_verdict(max_position_size_usd=Decimal("-100"))
        with pytest.raises(ValidationError):
            RiskVerdict(**kwargs)


# ══════════════════════════════════════════════
# OrderResult validatie
# ══════════════════════════════════════════════


class TestOrderResult:
    def test_valid_filled_order(self):
        """Een correct gevulde order mag geen fout geven."""
        result = OrderResult(**_valid_order_result())
        assert result.status == OrderStatus.FILLED
        assert result.filled_price == Decimal("83120.50")

    def test_filled_without_price_raises(self):
        """Een filled order zonder filled_price moet falen."""
        kwargs = _valid_order_result(filled_price=None)
        with pytest.raises(ValidationError) as exc:
            OrderResult(**kwargs)
        msg = str(exc.value).lower()
        assert "filled_price" in msg

    def test_filled_with_zero_size_raises(self):
        """Een filled order met filled_size_usd=0 moet falen."""
        kwargs = _valid_order_result(filled_size_usd=Decimal("0"))
        with pytest.raises(ValidationError):
            OrderResult(**kwargs)

    def test_rejected_without_error_raises(self):
        """Een rejected order zonder error-message moet falen."""
        kwargs = _valid_order_result(
            status="rejected",
            filled_size_usd=Decimal("0"),
            filled_price=None,
            slippage_bps=None,
            error="",
        )
        with pytest.raises(ValidationError) as exc:
            OrderResult(**kwargs)
        msg = str(exc.value).lower()
        assert "error" in msg

    def test_network_error_without_error_raises(self):
        """Een network_error zonder foutmelding moet falen."""
        kwargs = _valid_order_result(
            status="network_error",
            filled_size_usd=Decimal("0"),
            filled_price=None,
            slippage_bps=None,
            error=None,
        )
        with pytest.raises(ValidationError):
            OrderResult(**kwargs)

    def test_timeout_requires_error(self):
        """Timeout-status moet een error-veld hebben."""
        kwargs = _valid_order_result(
            status="timeout",
            filled_size_usd=Decimal("0"),
            filled_price=None,
            slippage_bps=None,
            error="Order niet gevuld binnen 30s time-window",
        )
        result = OrderResult(**kwargs)
        assert result.status == OrderStatus.TIMEOUT
        assert "time-window" in result.error

    def test_filled_size_exceeds_requested_raises(self):
        """filled_size_usd > requested_size_usd moet falen."""
        kwargs = _valid_order_result(
            filled_size_usd=Decimal("2000"),
            requested_size_usd=Decimal("1000"),
        )
        with pytest.raises(ValidationError):
            OrderResult(**kwargs)

    def test_partial_status_allows_half_fill(self):
        """Een partial fill met de juiste prijs en size is geldig."""
        kwargs = _valid_order_result(
            status="partial",
            filled_size_usd=Decimal("625.0"),
            filled_price=Decimal("83100.0"),
            slippage_bps=2,
        )
        result = OrderResult(**kwargs)
        assert result.status == OrderStatus.PARTIAL
        assert result.filled_size_usd < result.requested_size_usd

    def test_slippage_exceeds_max_raises(self):
        """Slippage > 50 bps moet falen."""
        kwargs = _valid_order_result(slippage_bps=100)
        with pytest.raises(ValidationError):
            OrderResult(**kwargs)


# ══════════════════════════════════════════════
# Integratietest: volledige dataflow (geen code)
# ══════════════════════════════════════════════


class TestFullDataFlow:
    """Simuleert de volledige inter-agent dataflow zonder logica — alleen validatie."""

    def test_analyst_to_risk_to_execution(self):
        """TradeSignal → RiskVerdict → OrderResult; alle valide stappen."""
        # Analist
        signal = _valid_signal()
        assert isinstance(signal, TradeSignal)
        assert signal.action == TradeAction.BUY

        # Risk
        verdict = RiskVerdict(
            signal_id=signal.signal_id,
            original_signal=signal,
            verdict="approved_scaled",
            max_position_size_usd=Decimal("1250.0"),
            max_slippage_bps=5,
            risk_score=0.31,
            reasoning="Binnen VaR-limiet.",
            risk_metrics=RiskMetrics(
                portfolio_var_99pct_1h=0.018,
                current_drawdown=0.04,
                max_drawdown_limit=0.15,
                position_concentration_pct=4.1,
                max_concentration_limit_pct=12.0,
            ),
            agent_version="risk-v1.1",
        )
        assert verdict.verdict == Verdict.APPROVED_SCALED
        assert verdict.signal_id == signal.signal_id

        # Execution
        result = OrderResult(
            signal_id=verdict.signal_id,
            order_id="exec_int_001",
            exchange="binance",
            order_type="limit",
            side="buy",
            requested_size_usd=verdict.max_position_size_usd,
            filled_size_usd=Decimal("1248.30"),
            filled_price=Decimal("83120.50"),
            slippage_bps=1,
            status="filled",
            duration_ms=342,
            error=None,
            agent_version="execution-v1.0",
        )
        assert result.status == OrderStatus.FILLED
        assert result.filled_size_usd <= result.requested_size_usd

    def test_stale_signal_rejected_in_risk_verdict(self):
        """
        Bewijst dat een oud signaal (45s) niet eens door de Risk-validator komt
        doordat TradeSignal zelf al faalt op TTL.
        """
        stale_ts = datetime.now(timezone.utc) - timedelta(seconds=45)
        kwargs = _valid_signal_kwargs(timestamp=stale_ts)
        with pytest.raises(ValidationError) as exc:
            TradeSignal(**kwargs)
        assert "TTL" in str(exc.value) or str(SIGNAL_TTL_SECONDS) in str(exc.value)

    def test_negative_stop_loss_rejected_at_model_level(self):
        """
        Bewijst dat een negatieve stop-loss onmiddellijk een ValidationError geeft
        — nog voordat Risk of Execution het ziet.
        """
        kwargs = _valid_signal_kwargs(stop_loss=Decimal("-500"))
        with pytest.raises(ValidationError):
            TradeSignal(**kwargs)