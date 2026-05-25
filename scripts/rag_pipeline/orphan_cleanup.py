"""Verwijder LanceDB-chunks die niet meer bij de huidige bron horen (orphan cleanup)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_ORPHAN_NOT_IN_BATCH = 100


def _sql_escape(value: str) -> str:
    return value.replace("'", "''")


def _orphan_predicate(relative_source: str, active_ids: list[str]) -> str:
    rel = _sql_escape(relative_source)
    if not active_ids:
        return f"source = '{rel}'"
    # Preserve order, drop duplicates (veiliger voor grote bronnen).
    active_ids = list(dict.fromkeys(active_ids))
    batches = [
        active_ids[i : i + _ORPHAN_NOT_IN_BATCH]
        for i in range(0, len(active_ids), _ORPHAN_NOT_IN_BATCH)
    ]
    if len(batches) == 1:
        id_list = ", ".join(f"'{_sql_escape(i)}'" for i in active_ids)
        return f"source = '{rel}' AND id NOT IN ({id_list})"
    not_in_clauses = []
    for batch in batches:
        id_list = ", ".join(f"'{_sql_escape(i)}'" for i in batch)
        not_in_clauses.append(f"id NOT IN ({id_list})")
    return f"source = '{rel}' AND " + " AND ".join(not_in_clauses)


def delete_orphan_chunks_for_source(table, relative_source: str, active_ids: list[str]) -> int:
    """Verwijder rijen met `source` waar `id` niet in `active_ids` staat.

    Retourneert het aantal verwijderde rijen (indien door LanceDB gerapporteerd, anders 0).
    """
    predicate = _orphan_predicate(relative_source, active_ids)
    try:
        result = table.delete(predicate)
    except Exception as exc:
        logger.warning(
            "Orphan cleanup delete failed for %r (%d active id(s)): %s",
            relative_source,
            len(active_ids),
            exc,
        )
        return 0
    if result is None:
        return 0
    if isinstance(result, int):
        return result
    return getattr(result, "count", 0) or 0


def delete_all_chunks_for_source(table, relative_source: str) -> int:
    """Verwijder alle chunks voor een bron die uit de bronmap is verdwenen."""
    return delete_orphan_chunks_for_source(table, relative_source, [])
