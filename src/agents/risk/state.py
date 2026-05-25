"""
Risk Agent — Append-Only Ledger (Event Sourcing).

Elke financiële mutatie of statuswijziging wordt uitsluitend opgeslagen
via INSERT statements als onveranderlijke events. UPDATE of DELETE zijn
in deze module verboden — actuele state wordt gereconstrueerd door
runtime-aggregatie van chronologische events.

Scope: uitsluitend SQLite. Geen FastAPI, netwerk of I/O buiten sqlite3.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


# ──────────────────────────────────────────────
# Event types (constants)
# ──────────────────────────────────────────────

EVENT_PORTFOLIO_INIT = "portfolio_init"
"""Eerste event: initiële portfolio-status bij opstarten van de Risk Agent."""

EVENT_SIGNAL_EVALUATED = "signal_evaluated"
"""
Event na elke RiskEvaluator.evaluate()-aanroep.
Bevat de nieuwe portfolio-state ná het verwerken van het signaal.
"""

EVENT_PORTFOLIO_REVALUE = "portfolio_revalue"
"""Externe herwaardering van de portefeuille (P&L, deposit, withdrawal)."""


# ──────────────────────────────────────────────
# Ledger schema (SQL)
# ──────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS risk_ledger (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sequence    INTEGER NOT NULL,
    event_type  TEXT    NOT NULL,

    -- Signal-specific fields (alleen voor signal_evaluated)
    signal_id          TEXT,
    verdict            TEXT,
    position_size_usd  REAL,
    confidence         REAL,

    -- Portfolio state NA dit event
    portfolio_value_usd     REAL NOT NULL,
    drawdown_pct            REAL NOT NULL,
    open_position_value_usd REAL NOT NULL,

    -- Extra metadata (JSON)
    metadata TEXT,

    -- Timestamp (UTC ISO-8601)
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ledger_sequence
    ON risk_ledger(sequence);
"""


# ──────────────────────────────────────────────
# RiskLedger
# ──────────────────────────────────────────────


class RiskLedger:
    """
    Append-only event ledger voor Risk Agent state.

    Gebruik:
        ledger = RiskLedger("path/to/risk.db")
        ledger.append_portfolio_init(portfolio_value=100_000)
        ledger.append_signal_event(signal, verdict, portfolio_before)

        state = ledger.reconstruct_state()
        # → {"portfolio_value_usd": ..., "current_drawdown_pct": ...}
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(SCHEMA_SQL)
        self._conn.commit()

    # ── Event writers (alleen INSERT) ─────────

    def append_portfolio_init(
        self,
        portfolio_value_usd: float | Decimal,
        open_position_value_usd: float | Decimal = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """
        Schrijft een portfolio_init event.
        Drawdown start op 0.0.

        Returns:
            Het id (rowid) van het aangemaakte event.
        """
        return self._insert_event(
            event_type=EVENT_PORTFOLIO_INIT,
            portfolio_value_usd=float(portfolio_value_usd),
            drawdown_pct=0.0,
            open_position_value_usd=float(open_position_value_usd),
            signal_id=None,
            verdict=None,
            position_size_usd=None,
            confidence=None,
            metadata=metadata,
        )

    def append_signal_event(
        self,
        signal_id: str,
        verdict: str,
        position_size_usd: float | Decimal,
        confidence: float,
        portfolio_value_usd_before: float | Decimal,
        drawdown_before: float,
        portfolio_value_usd_after: float | Decimal,
        drawdown_after: float,
        open_position_value_after: float | Decimal,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """
        Schrijft een signal_evaluated event met de portfolio-state NA verwerking.

        Dit is het enige event-type dat signal-specifieke velden bevat.
        """
        return self._insert_event(
            event_type=EVENT_SIGNAL_EVALUATED,
            portfolio_value_usd=float(portfolio_value_usd_after),
            drawdown_pct=float(drawdown_after),
            open_position_value_usd=float(open_position_value_after),
            signal_id=signal_id,
            verdict=verdict,
            position_size_usd=float(position_size_usd),
            confidence=float(confidence),
            metadata={
                **(metadata or {}),
                "portfolio_value_usd_before": float(portfolio_value_usd_before),
                "drawdown_before": float(drawdown_before),
            },
        )

    def append_revalue(
        self,
        portfolio_value_usd: float | Decimal,
        drawdown_pct: float,
        open_position_value_usd: float | Decimal,
        reason: str = "manual",
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """
        Schrijft een portfolio_revalue event voor externe herwaardering.
        """
        return self._insert_event(
            event_type=EVENT_PORTFOLIO_REVALUE,
            portfolio_value_usd=float(portfolio_value_usd),
            drawdown_pct=float(drawdown_pct),
            open_position_value_usd=float(open_position_value_usd),
            signal_id=None,
            verdict=None,
            position_size_usd=None,
            confidence=None,
            metadata={
                "reason": reason,
                **(metadata or {}),
            },
        )

    # ── State reconstructie (runtime aggregatie) ────

    def reconstruct_state(self) -> dict[str, Any]:
        """
        Loopt ALLE events in chronologische volgorde (id ASC) en reconstrueert
        de actuele portfolio-state.

        Dit is een pure runtime-aggregatie; geen UPDATE of DELETE ooit uitgevoerd.

        Returns:
            Dict met portfolio_state + ledger-metadata:
                - portfolio_value_usd (float)
                - current_drawdown_pct (float)
                - open_position_value_usd (float)
                - last_signal_id (str | None)
                - last_verdict (str | None)
                - total_events (int)
                - last_event_ts (str | None)
        """
        cursor = self._conn.execute(
            "SELECT event_type, portfolio_value_usd, drawdown_pct, "
            "open_position_value_usd, signal_id, verdict, created_at "
            "FROM risk_ledger ORDER BY id ASC"
        )
        rows = cursor.fetchall()

        if not rows:
            return {
                "portfolio_value_usd": 0.0,
                "current_drawdown_pct": 0.0,
                "open_position_value_usd": 0.0,
                "last_signal_id": None,
                "last_verdict": None,
                "total_events": 0,
                "last_event_ts": None,
            }

        # De laatste rij in de chronologische volgorde = actuele state
        last = rows[-1]

        return {
            "portfolio_value_usd": last["portfolio_value_usd"],
            "current_drawdown_pct": last["drawdown_pct"],
            "open_position_value_usd": last["open_position_value_usd"],
            "last_signal_id": last["signal_id"],
            "last_verdict": last["verdict"],
            "total_events": len(rows),
            "last_event_ts": last["created_at"],
        }

    def reconstruct_full_timeline(self) -> list[dict[str, Any]]:
        """
        Retourneert de volledige event-timeline als lijst van dicts.
        Alleen voor analyse/debug; reconstruct_state() is de performante variant.
        """
        cursor = self._conn.execute(
            "SELECT id, sequence, event_type, signal_id, verdict, "
            "position_size_usd, confidence, portfolio_value_usd, "
            "drawdown_pct, open_position_value_usd, metadata, created_at "
            "FROM risk_ledger ORDER BY id ASC"
        )
        return [dict(row) for row in cursor.fetchall()]

    # ── Meta / status ─────────────────────────

    def get_event_count(self) -> int:
        """Totaal aantal events in de ledger."""
        row = self._conn.execute("SELECT COUNT(*) AS cnt FROM risk_ledger").fetchone()
        return row["cnt"] if row else 0

    def get_last_event(self) -> dict[str, Any] | None:
        """Haalt het laatste event op (None bij lege ledger)."""
        cursor = self._conn.execute(
            "SELECT id, sequence, event_type, portfolio_value_usd, "
            "drawdown_pct, open_position_value_usd, created_at "
            "FROM risk_ledger ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    # ── Lifecycle ──────────────────────────────

    def close(self) -> None:
        """Sluit de database-verbinding."""
        if self._conn:
            self._conn.commit()
            self._conn.close()
            self._conn = None

    def __enter__(self) -> RiskLedger:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ── Intern ─────────────────────────────────

    def _next_sequence(self) -> int:
        """Volgende sequentienummer (gebaseerd op max + 1)."""
        row = self._conn.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 AS next_seq FROM risk_ledger"
        ).fetchone()
        return row["next_seq"] if row else 1

    def _insert_event(
        self,
        *,
        event_type: str,
        portfolio_value_usd: float,
        drawdown_pct: float,
        open_position_value_usd: float,
        signal_id: str | None,
        verdict: str | None,
        position_size_usd: float | None,
        confidence: float | None,
        metadata: dict[str, Any] | None,
    ) -> int:
        """INSERT-only writer. Dit is de enige plek in de module die INSERT uitvoert."""
        seq = self._next_sequence()
        now = datetime.now(timezone.utc).isoformat()
        meta_json = json.dumps(metadata) if metadata else None

        cursor = self._conn.execute(
            """
            INSERT INTO risk_ledger
                (sequence, event_type,
                 signal_id, verdict, position_size_usd, confidence,
                 portfolio_value_usd, drawdown_pct, open_position_value_usd,
                 metadata, created_at)
            VALUES (?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?)
            """,
            (
                seq,
                event_type,
                signal_id,
                verdict,
                position_size_usd,
                confidence,
                portfolio_value_usd,
                drawdown_pct,
                open_position_value_usd,
                meta_json,
                now,
            ),
        )
        self._conn.commit()
        return cursor.lastrowid