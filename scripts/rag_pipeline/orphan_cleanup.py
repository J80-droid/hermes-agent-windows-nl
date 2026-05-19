"""Verwijder LanceDB-chunks die niet meer bij de huidige bron horen (orphan cleanup)."""

from __future__ import annotations


def _sql_escape(value: str) -> str:
    return value.replace("'", "''")


def delete_orphan_chunks_for_source(table, relative_source: str, active_ids: list[str]) -> int:
    """Verwijder rijen met `source` waar `id` niet in `active_ids` staat.

    Retourneert het aantal verwijderde rijen (indien door LanceDB gerapporteerd, anders 0).
    """
    rel = _sql_escape(relative_source)
    if not active_ids:
        predicate = f"source = '{rel}'"
    else:
        id_list = ", ".join(f"'{_sql_escape(i)}'" for i in active_ids)
        predicate = f"source = '{rel}' AND id NOT IN ({id_list})"
    try:
        result = table.delete(predicate)
    except Exception:
        table.delete(predicate)
        return 0
    if result is None:
        return 0
    if isinstance(result, int):
        return result
    return getattr(result, "count", 0) or 0


def delete_all_chunks_for_source(table, relative_source: str) -> int:
    """Verwijder alle chunks voor een bron die uit de bronmap is verdwenen."""
    return delete_orphan_chunks_for_source(table, relative_source, [])
