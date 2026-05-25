"""
Risk Agent — pure berekeningslogica.

Bevat RiskEvaluator: vertaalt TradeSignal + portfolio-status naar RiskVerdict.
Scope: uitsluitend wiskundige en conditionele logica.
Geen FastAPI, Redis, SQLite of I/O.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.core.models import (
    TradeSignal,
    RiskMetrics,
    RiskVerdict,
    Verdict,
)


# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────

MAX_DRAWDOWN_LIMIT: float = 0.15
"""Maximaal toegestane virtuele drawdown-fractie (15%)."""

MAX_ALLOCATION_PER_TRADE: float = 0.02
"""Maximale portefeuille-allocatie per trade bij 100% confidence (2%)."""

MIN_VIABLE_POSITION_USD: Decimal = Decimal("10")
"""Minimale positiegrootte in USD — daaronder wordt een trade declined."""


# ──────────────────────────────────────────────
# Typed dict voor portfolio-status
# ──────────────────────────────────────────────

PORTFOLIO_REQUIRED_KEYS = frozenset({
    "portfolio_value_usd",
    "current_drawdown_pct",
    "open_position_value_usd",
})


# ──────────────────────────────────────────────
# RiskEvaluator
# ──────────────────────────────────────────────


class RiskEvaluator:
    """
    Berekent risicobeoordeling voor een TradeSignal op basis van
    portfolio-status en confidence.

    Zuivere functie: geen neveneffecten, geen I/O, geen mutable state.
    """

    def __init__(
        self,
        max_drawdown: float = MAX_DRAWDOWN_LIMIT,
        max_allocation: float = MAX_ALLOCATION_PER_TRADE,
        min_viable: Decimal = MIN_VIABLE_POSITION_USD,
    ) -> None:
        """
        Args:
            max_drawdown: Drawdown-limiet fractie (default 0.15 = 15%).
            max_allocation: Maximale allocatie fractie bij 100% confidence.
            min_viable: Minimale positie in USD; kleiner wordt declined.
        """
        if not 0.0 < max_drawdown <= 1.0:
            raise ValueError("max_drawdown moet in (0.0, 1.0] liggen")
        if not 0.0 < max_allocation <= 1.0:
            raise ValueError("max_allocation moet in (0.0, 1.0] liggen")
        if min_viable < Decimal("0"):
            raise ValueError("min_viable mag niet negatief zijn")

        self._max_drawdown = max_drawdown
        self._max_allocation = max_allocation
        self._min_viable = min_viable

    # ── Publieke methode ─────────────────────

    def evaluate(self, signal: TradeSignal, portfolio: dict[str, Any]) -> RiskVerdict:
        """
        Hoofdmethode: beoordeelt een TradeSignal en retourneert RiskVerdict.

        Args:
            signal: Het TradeSignaal van de Analyst agent.
            portfolio: Portfolio-status met minimaal:
                - portfolio_value_usd (float/Decimal): totale portefeuillewaarde.
                - current_drawdown_pct (float): huidige drawdown [0.0, 1.0].
                - open_position_value_usd (float/Decimal): waarde open posities.

        Returns:
            RiskVerdict met verdict, size en risicometrieken.
        """
        self._validate_portfolio(portfolio)

        portfolio_value = Decimal(str(portfolio["portfolio_value_usd"]))
        current_drawdown = float(portfolio["current_drawdown_pct"])
        open_position_value = Decimal(str(portfolio["open_position_value_usd"]))

        # ── Stap 1: base positiegrootte ─────
        base_size = self._compute_base_size(
            portfolio_value=portfolio_value,
            confidence=signal.confidence,
        )

        # ── Stap 1b: nulpositie = geen signaal ──
        if base_size <= Decimal("0"):
            return self._build_verdict(
                signal=signal,
                verdict=Verdict.DECLINED,
                position_size=Decimal("0"),
                current_drawdown=current_drawdown,
                portfolio_value=portfolio_value,
                new_drawdown=current_drawdown,
                risk_score=1.0,
                reasoning=(
                    f"Geweigerd: confidence {signal.confidence:.2f} resulteert in "
                    f"positiegrootte van $0. Signaal heeft geen economische substantie."
                ),
            )

        # ── Stap 2: drawdown-check ──────────
        new_drawdown = self._simulate_drawdown(
            current_drawdown=current_drawdown,
            position_size=base_size,
            portfolio_value=portfolio_value,
        )

        if new_drawdown > self._max_drawdown:
            return self._handle_drawdown_exceeded(
                signal=signal,
                current_drawdown=current_drawdown,
                portfolio_value=portfolio_value,
                base_size=base_size,
            )

        # ── Stap 3: approved (volledige size) ─
        return self._build_verdict(
            signal=signal,
            verdict=Verdict.APPROVED,
            position_size=base_size,
            current_drawdown=current_drawdown,
            portfolio_value=portfolio_value,
            new_drawdown=new_drawdown,
            risk_score=self._compute_risk_score(
                current_drawdown=current_drawdown,
                new_drawdown=new_drawdown,
            ),
            reasoning=(
                f"Goedgekeurd: confidence {signal.confidence:.2f} geeft "
                f"${base_size:,.2f} positie. Drawdown blijft op "
                f"{new_drawdown:.1%} (limiet {self._max_drawdown:.0%})."
            ),
        )

    # ── Interne rekenmethodes ────────────────

    def _compute_base_size(
        self,
        portfolio_value: Decimal,
        confidence: float,
    ) -> Decimal:
        """
        Berekent de initiële positiegrootte:
            size = portfolio_value * (confidence * max_allocation)
        """
        raw = portfolio_value * Decimal(str(confidence * self._max_allocation))
        # Afronden op 2 decimalen
        return raw.quantize(Decimal("0.01"))

    def _simulate_drawdown(
        self,
        current_drawdown: float,
        position_size: Decimal,
        portfolio_value: Decimal,
    ) -> float:
        """
        Simuleert nieuwe drawdown na toevoegen van positie.
            new_drawdown = current + (position / portfolio_value)
        """
        exposure = float(position_size / portfolio_value)
        return current_drawdown + exposure

    def _compute_risk_score(
        self,
        current_drawdown: float,
        new_drawdown: float,
    ) -> float:
        """
        Risicoscore [0, 1]: lineaire schaling op basis van drawdown-proximity
        tot de limiet.

        Score = new_drawdown / max_drawdown (afgekapt op 1.0).
        """
        score = new_drawdown / self._max_drawdown
        return min(score, 1.0)

    # ── Drawdown-overschrijding ──────────────

    def _handle_drawdown_exceeded(
        self,
        signal: TradeSignal,
        current_drawdown: float,
        portfolio_value: Decimal,
        base_size: Decimal,
    ) -> RiskVerdict:
        """
        Beslist of een overschrijding leidt tot schaling (approved_scaled)
        of weigering (declined).

        Als de drawdown-ruimte voldoende is voor min_viable positie:
        → approved_scaled met maximaal mogelijke size.
        Anders:
        → declined.
        """
        remaining_headroom = Decimal(str(self._max_drawdown)) - Decimal(str(current_drawdown))
        max_allowed = remaining_headroom * portfolio_value

        if max_allowed >= self._min_viable:
            scaled_drawdown = self._simulate_drawdown(
                current_drawdown=current_drawdown,
                position_size=max_allowed,
                portfolio_value=portfolio_value,
            )
            return self._build_verdict(
                signal=signal,
                verdict=Verdict.APPROVED_SCALED,
                position_size=max_allowed,
                current_drawdown=current_drawdown,
                portfolio_value=portfolio_value,
                new_drawdown=scaled_drawdown,
                risk_score=self._compute_risk_score(
                    current_drawdown=current_drawdown,
                    new_drawdown=scaled_drawdown,
                ),
                reasoning=(
                    f"Drawdown-overschrijding: {current_drawdown:.1%} + "
                    f"{float(base_size / portfolio_value):.1%} exposure = "
                    f"{current_drawdown + float(base_size / portfolio_value):.1%} "
                    f"(limiet {self._max_drawdown:.0%}). "
                    f"Geschaald naar ${max_allowed:,.2f} ("
                    f"{float(max_allowed / portfolio_value):.1%} exposure)."
                ),
            )

        return self._build_verdict(
            signal=signal,
            verdict=Verdict.DECLINED,
            position_size=Decimal("0"),
            current_drawdown=current_drawdown,
            portfolio_value=portfolio_value,
            new_drawdown=current_drawdown,
            risk_score=1.0,
            reasoning=(
                f"Geweigerd: base positie ${base_size:,.2f} overschrijdt "
                f"drawdown-limiet {self._max_drawdown:.0%} (huidig "
                f"{current_drawdown:.1%}). Resterende headroom "
                f"${max_allowed:,.2f} is onder minimale positie "
                f"${self._min_viable:,.2f}."
            ),
        )

    # ── Verdict builder ──────────────────────

    def _build_verdict(
        self,
        signal: TradeSignal,
        verdict: Verdict,
        position_size: Decimal,
        current_drawdown: float,
        portfolio_value: Decimal,
        new_drawdown: float,
        risk_score: float,
        reasoning: str,
    ) -> RiskVerdict:
        """Bouwt een RiskVerdict met de juiste RiskMetrics."""

        # Bepaal slippage op basis van risk_score
        slippage_bps = self._compute_slippage_budget(risk_score)

        concentration = float(position_size / portfolio_value) * 100.0

        metrics = RiskMetrics(
            portfolio_var_99pct_1h=round(new_drawdown * 0.12, 4),  # proxy
            current_drawdown=round(current_drawdown, 4),
            max_drawdown_limit=self._max_drawdown,
            position_concentration_pct=round(concentration, 2),
            max_concentration_limit_pct=round(self._max_allocation * 100.0, 2),
        )

        # Alleen signaal-specifieke velden; origineel signaal wordt bewaard
        return RiskVerdict(
            signal_id=signal.signal_id,
            original_signal=signal,
            verdict=verdict,
            max_position_size_usd=position_size,
            max_slippage_bps=slippage_bps,
            risk_score=round(risk_score, 4),
            reasoning=reasoning,
            risk_metrics=metrics,
            agent_version="risk-evaluator-v1.0",
        )

    # ── Hulpmethodes ─────────────────────────

    @staticmethod
    def _compute_slippage_budget(risk_score: float) -> int:
        """
        Slippage-budget op basis van risicoscore:
        - risk_score < 0.3: 5 bps (ruim)
        - risk_score 0.3-0.6: 3 bps (strak)
        - risk_score > 0.6: 2 bps (zeer strak)
        """
        if risk_score < 0.3:
            return 5
        elif risk_score < 0.6:
            return 3
        return 2

    @staticmethod
    def _validate_portfolio(portfolio: dict[str, Any]) -> None:
        """Valideert dat alle vereiste portfolio-sleutels aanwezig zijn."""
        missing = PORTFOLIO_REQUIRED_KEYS - set(portfolio.keys())
        if missing:
            raise ValueError(
                f"Portfolio mist vereiste sleutels: {', '.join(sorted(missing))}"
            )

        pv = portfolio.get("portfolio_value_usd", 0)
        if not isinstance(pv, (int, float, Decimal)) or pv <= 0:
            raise ValueError(
                f"portfolio_value_usd moet positief zijn, kreeg {pv!r}"
            )

        dd = portfolio.get("current_drawdown_pct", -1)
        if not isinstance(dd, (int, float)) or dd < 0 or dd > 1:
            raise ValueError(
                f"current_drawdown_pct moet in [0.0, 1.0] liggen, kreeg {dd!r}"
            )