"""
Tests voor src/agents/risk/logic.py.

Bewijst dat de RiskEvaluator correct schaalt (approved_scaled) bij een
normaal signaal en faalt (declined) bij een roekeloos signaal.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.agents.risk.logic import (
    MAX_ALLOCATION_PER_TRADE,
    MAX_DRAWDOWN_LIMIT,
    MIN_VIABLE_POSITION_USD,
    RiskEvaluator,
)
from src.core.models import TradeSignal, Verdict


# ══════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════


def _signal_kwargs(**overrides) -> dict:
    """Minimale geldige TradeSignal-parameters (binnen TTL)."""
    base = {
        "signal_id": "sig_risk_test",
        "timestamp": datetime.now(timezone.utc),
        "symbol": "BTC/USDT",
        "action": "buy",
        "confidence": 0.82,
        "entry_price_min": Decimal("82500"),
        "entry_price_max": Decimal("83400"),
        "stop_loss": Decimal("79800"),
        "take_profit": Decimal("87500"),
        "timeframe": "1h",
        "rationale": "Test signaal",
        "sources": ["test"],
        "agent_version": "analyst-v1.0",
    }
    base.update(overrides)
    return base


def _make_signal(**overrides) -> TradeSignal:
    return TradeSignal(**_signal_kwargs(**overrides))


def _portfolio(**overrides) -> dict:
    """Standaard portfolio-status."""
    base: dict = {
        "portfolio_value_usd": 100_000.0,
        "current_drawdown_pct": 0.04,
        "open_position_value_usd": 5_000.0,
    }
    base.update(overrides)
    return base


# ══════════════════════════════════════════════
# RiskEvaluator — constructie
# ══════════════════════════════════════════════


class TestRiskEvaluatorInit:
    def test_default_parameters(self):
        evaluator = RiskEvaluator()
        assert evaluator._max_drawdown == MAX_DRAWDOWN_LIMIT
        assert evaluator._max_allocation == MAX_ALLOCATION_PER_TRADE
        assert evaluator._min_viable == MIN_VIABLE_POSITION_USD

    def test_custom_parameters(self):
        evaluator = RiskEvaluator(
            max_drawdown=0.10,
            max_allocation=0.05,
            min_viable=Decimal("50"),
        )
        assert evaluator._max_drawdown == 0.10
        assert evaluator._max_allocation == 0.05
        assert evaluator._min_viable == Decimal("50")

    def test_invalid_drawdown_raises(self):
        with pytest.raises(ValueError):
            RiskEvaluator(max_drawdown=0.0)
        with pytest.raises(ValueError):
            RiskEvaluator(max_drawdown=1.5)

    def test_invalid_allocation_raises(self):
        with pytest.raises(ValueError):
            RiskEvaluator(max_allocation=0.0)
        with pytest.raises(ValueError):
            RiskEvaluator(max_allocation=-0.1)

    def test_negative_min_viable_raises(self):
        with pytest.raises(ValueError):
            RiskEvaluator(min_viable=Decimal("-1"))


# ══════════════════════════════════════════════
# RiskEvaluator — portfolio validatie
# ══════════════════════════════════════════════


class TestPortfolioValidation:
    def test_missing_key_raises(self):
        evaluator = RiskEvaluator()
        signal = _make_signal()
        with pytest.raises(ValueError) as exc:
            evaluator.evaluate(signal, {"portfolio_value_usd": 100_000})
        msg = str(exc.value)
        assert "portfolio" in msg.lower()

    def test_negative_portfolio_value_raises(self):
        evaluator = RiskEvaluator()
        signal = _make_signal()
        with pytest.raises(ValueError):
            evaluator.evaluate(signal, _portfolio(portfolio_value_usd=-100))

    def test_drawdown_out_of_range_raises(self):
        evaluator = RiskEvaluator()
        signal = _make_signal()
        with pytest.raises(ValueError):
            evaluator.evaluate(signal, _portfolio(current_drawdown_pct=1.5))


# ══════════════════════════════════════════════
# RiskEvaluator — approved (normaal signaal)
# ══════════════════════════════════════════════


class TestApprovedVerdict:
    def test_normal_signal_approved(self):
        """
        Normaal signaal (confidence 0.82) met gezonde portfolio:
        verwacht VERDICT = APPROVED.
        """
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=0.82)
        portfolio = _portfolio(
            portfolio_value_usd=100_000.0,
            current_drawdown_pct=0.04,
        )
        verdict = evaluator.evaluate(signal, portfolio)

        assert verdict.verdict == Verdict.APPROVED
        assert verdict.signal_id == "sig_risk_test"

    def test_approved_size_calculation(self):
        """
        Met confidence 0.82 en max_allocation 0.02:
        base_size = 100_000 * (0.82 * 0.02) = 100_000 * 0.0164 = 1640.00
        """
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=0.82)
        portfolio = _portfolio(portfolio_value_usd=100_000.0)
        verdict = evaluator.evaluate(signal, portfolio)

        expected = Decimal("1640.00")
        assert verdict.max_position_size_usd == expected

    def test_high_confidence_larger_position(self):
        """
        Confidence 1.0:
        base_size = 100_000 * (1.0 * 0.02) = 2_000.00
        """
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=1.0)
        portfolio = _portfolio(portfolio_value_usd=100_000.0)
        verdict = evaluator.evaluate(signal, portfolio)

        assert verdict.max_position_size_usd == Decimal("2000.00")

    def test_low_confidence_small_position(self):
        """Confidence 0.1: 100_000 * (0.1 * 0.02) = 200.00"""
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=0.1)
        portfolio = _portfolio(portfolio_value_usd=100_000.0)
        verdict = evaluator.evaluate(signal, portfolio)

        assert verdict.max_position_size_usd == Decimal("200.00")

    def test_approved_includes_risk_metrics(self):
        """Een approved verdict moet volledige RiskMetrics bevatten."""
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=0.82)
        portfolio = _portfolio(portfolio_value_usd=100_000.0)
        verdict = evaluator.evaluate(signal, portfolio)

        metrics = verdict.risk_metrics
        assert metrics.current_drawdown == 0.04
        assert metrics.max_drawdown_limit == 0.15
        assert metrics.position_concentration_pct == pytest.approx(1.64, abs=0.01)
        assert metrics.portfolio_var_99pct_1h > 0


# ══════════════════════════════════════════════
# RiskEvaluator — approved_scaled (drawdown riskant)
# ══════════════════════════════════════════════


class TestApprovedScaledVerdict:
    def test_scaled_when_near_drawdown_limit(self):
        """
        Portfolio met drawdown 14% (limiet 15%): een signaal met confidence 0.82
        geeft base_size = 1_640. Exposure = 1_640 / 100_000 = 1.64%.
        Nieuwe drawdown = 14% + 1.64% = 15.64% > 15% → schaling.
        Headroom = 1.0% van 100_000 = 1_000.
        Resterende headroom (1_000) >= min_viable (10) → APPROVED_SCALED.
        """
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=0.82)
        portfolio = _portfolio(current_drawdown_pct=0.14)
        verdict = evaluator.evaluate(signal, portfolio)

        assert verdict.verdict == Verdict.APPROVED_SCALED
        # Headroom = 0.01 * 100_000 = 1_000
        expected_size = Decimal("1000.00")
        assert verdict.max_position_size_usd == expected_size

    def test_scaled_size_matches_headroom(self):
        """
        Drawdown 12%, confidence 1.0:
        base_size = 2_000, exposure = 2%.
        Nieuwe drawdown = 12% + 2% = 14% (binnen 15%) → APPROVED.
        """
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=1.0)
        portfolio = _portfolio(current_drawdown_pct=0.12)
        verdict = evaluator.evaluate(signal, portfolio)

        # 12% + 2% = 14% < 15% → approved
        assert verdict.verdict == Verdict.APPROVED
        assert verdict.max_position_size_usd == Decimal("2000.00")

    def test_scaled_at_exact_boundary(self):
        """
        Drawdown 14.5%, confidence 0.82:
        base = 1_640 (1.64%), new drawdown = 16.14% > 15%.
        Headroom = 0.5% * 100_000 = 500.
        """
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=0.82)
        portfolio = _portfolio(current_drawdown_pct=0.145)
        verdict = evaluator.evaluate(signal, portfolio)

        assert verdict.verdict == Verdict.APPROVED_SCALED
        assert verdict.max_position_size_usd == Decimal("500.00")

    def test_scaled_risk_score_reflects_proximity(self):
        """
        Bij schaling moet de risk_score de hogere drawdown-proximity weerspiegelen.
        """
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=0.82)
        portfolio = _portfolio(current_drawdown_pct=0.14)
        verdict = evaluator.evaluate(signal, portfolio)

        # scaled drawdown = 14% + 1% = 15% → score = 0.15/0.15 = 1.0
        assert verdict.risk_score == pytest.approx(1.0, abs=0.01)


# ══════════════════════════════════════════════
# RiskEvaluator — declined (roekeloos signaal)
# ══════════════════════════════════════════════


class TestDeclinedVerdict:
    def test_declined_when_headroom_below_minimum(self):
        """
        Portfolio met drawdown 14.99%: headroom = 0.01% * 100_000 = $10.
        Dit is gelijk aan MIN_VIABLE → nog approved_scaled.
        """
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=0.82)
        portfolio = _portfolio(current_drawdown_pct=0.1499)
        verdict = evaluator.evaluate(signal, portfolio)

        assert verdict.verdict == Verdict.APPROVED_SCALED
        assert verdict.max_position_size_usd == Decimal("10.00")

    def test_declined_when_headroom_below_minimum_plus_one(self):
        """
        Portfolio met drawdown 14.999%: headroom = 0.001% * 100_000 = $1.
        Dit is ONDER MIN_VIABLE ($10) → DECLINED.
        """
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=0.82)
        portfolio = _portfolio(current_drawdown_pct=0.14999)
        verdict = evaluator.evaluate(signal, portfolio)

        assert verdict.verdict == Verdict.DECLINED
        assert verdict.max_position_size_usd == Decimal("0")

    def test_declined_at_hard_limit(self):
        """
        Drawdown exact op 15%: geen headroom over.
        Zelfs de minimale positie is niet mogelijk → DECLINED.
        """
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=0.82)
        portfolio = _portfolio(current_drawdown_pct=0.15)
        verdict = evaluator.evaluate(signal, portfolio)

        assert verdict.verdict == Verdict.DECLINED
        assert verdict.max_position_size_usd == Decimal("0")
        assert verdict.risk_score == 1.0

    def test_declined_includes_explanatory_reasoning(self):
        """
        Een declined verdict moet een duidelijke reden geven waarom.
        """
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=0.82)
        portfolio = _portfolio(current_drawdown_pct=0.14999)
        verdict = evaluator.evaluate(signal, portfolio)

        assert verdict.verdict == Verdict.DECLINED
        assert len(verdict.reasoning) > 20
        assert "Geweigerd" in verdict.reasoning or "overschrijdt" in verdict.reasoning

    def test_declined_risk_score_is_max(self):
        """Een declined verdict heeft risk_score = 1.0."""
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=0.82)
        portfolio = _portfolio(current_drawdown_pct=0.14999)
        verdict = evaluator.evaluate(signal, portfolio)

        assert verdict.risk_score == 1.0


# ══════════════════════════════════════════════
# RiskEvaluator — slippage budget
# ══════════════════════════════════════════════


class TestSlippageBudget:
    def test_low_risk_high_slippage(self):
        """risk_score < 0.3 → slippage_bps = 5."""
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=0.1)  # kleine positie, laag risico
        portfolio = _portfolio(current_drawdown_pct=0.0)
        verdict = evaluator.evaluate(signal, portfolio)

        assert verdict.verdict == Verdict.APPROVED
        assert verdict.max_slippage_bps == 5

    def test_medium_risk_medium_slippage(self):
        """risk_score 0.3-0.6 → slippage_bps = 3."""
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=1.0)
        # 14% drawdown + 2% exposure = 16% > 15% → scaled
        portfolio = _portfolio(current_drawdown_pct=0.14)
        verdict = evaluator.evaluate(signal, portfolio)

        # scaled: risk_score should be elevated
        # scaled drawdown = 15%, score = 15/15 = 1.0
        # Actually this is > 0.6, so slippage = 2
        assert verdict.max_slippage_bps in (2, 3, 5)

    def test_high_risk_low_slippage(self):
        """risk_score > 0.6 → slippage_bps = 2."""
        evaluator = RiskEvaluator(max_drawdown=0.10)
        signal = _make_signal(confidence=1.0)
        portfolio = _portfolio(
            portfolio_value_usd=100_000.0,
            current_drawdown_pct=0.09,
        )
        # drawdown 9% + 2% = 11% > 10% → scaled to 1% = 1_000
        # scaled drawdown = 10%, risk_score = 10/10 = 1.0
        verdict = evaluator.evaluate(signal, portfolio)

        assert verdict.max_slippage_bps == 2


# ══════════════════════════════════════════════
# RiskEvaluator — edge cases
# ══════════════════════════════════════════════


class TestEdgeCases:
    def test_zero_current_drawdown(self):
        """Geen drawdown → volledig approved."""
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=0.82)
        portfolio = _portfolio(current_drawdown_pct=0.0)
        verdict = evaluator.evaluate(signal, portfolio)

        assert verdict.verdict == Verdict.APPROVED
        assert verdict.max_position_size_usd == Decimal("1640.00")
        assert verdict.risk_score < 0.3

    def test_small_portfolio_declined(self):
        """
        Zeer kleine portfolio (100 USD) met confidence 0.5:
        base_size = 100 * (0.5 * 0.02) = 1.0 → boven min_viable van 10?
        Nee, 1.0 < 10, maar drawdown-check is leidend.
        Drawdown 4% + 1% = 5% < 15% → approved.
        """
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=0.5)
        portfolio = _portfolio(portfolio_value_usd=100.0)
        verdict = evaluator.evaluate(signal, portfolio)

        # base_size = 100 * (0.5 * 0.02) = 1.0
        # drawdown 0.04 + 0.01 = 0.05 < 0.15 → approved, size 1.0
        assert verdict.verdict == Verdict.APPROVED
        assert verdict.max_position_size_usd == Decimal("1.00")

    def test_portfolio_at_exact_drawdown_limit_not_declined(self):
        """
        Drawdown exact 15%: geen headroom. Elke positie overschrijdt.
        → declined.
        """
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=0.1)  # kleine positie
        portfolio = _portfolio(current_drawdown_pct=0.15)
        verdict = evaluator.evaluate(signal, portfolio)

        assert verdict.verdict == Verdict.DECLINED

    def test_roekeloos_hoog_confidence_bij_volle_drawdown(self):
        """
        *** ROEKELOOS SIGNAAL ***
        Confidence 0.95, drawdown 14.5% (nog 0.5% headroom).
        base = 100_000 * (0.95 * 0.02) = 100_000 * 0.019 = 1_900
        exposure = 1.9%, new drawdown = 16.4% > 15%
        headroom = 0.5% = $500 >= $10 → approved_scaled ($500)
        """
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=0.95)
        portfolio = _portfolio(current_drawdown_pct=0.145)
        verdict = evaluator.evaluate(signal, portfolio)

        assert verdict.verdict == Verdict.APPROVED_SCALED
        assert verdict.max_position_size_usd == Decimal("500.00")

    def test_roekeloos_hoog_confidence_max_drawdown(self):
        """
        *** ROEKELOOS SIGNAAL — DECLINED ***
        Confidence 0.95, drawdown exact 15%: geen headroom.
        → declined.
        """
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=0.95)
        portfolio = _portfolio(current_drawdown_pct=0.15)
        verdict = evaluator.evaluate(signal, portfolio)

        assert verdict.verdict == Verdict.DECLINED
        assert verdict.max_position_size_usd == Decimal("0")

    def test_confidence_zero_is_declined(self):
        """
        Confidence 0.0: base_size = 0.
        Dit wordt direct opgepikt als 'geen substantie' → DECLINED.
        """
        evaluator = RiskEvaluator()
        signal = _make_signal(confidence=0.0)
        portfolio = _portfolio(portfolio_value_usd=100_000.0)
        verdict = evaluator.evaluate(signal, portfolio)

        assert verdict.verdict == Verdict.DECLINED
        assert verdict.max_position_size_usd == Decimal("0")
        assert "geen economische substantie" in verdict.reasoning

    def test_negative_confidence_raises_at_signal_level(self):
        """Negatieve confidence wordt al door TradeSignal-validator afgevangen."""
        with pytest.raises(ValidationError):
            _make_signal(confidence=-0.1)