"""CRUD operations over the item archive (FR3, FR4.4)."""

import json
import sqlite3
from datetime import date, timedelta

_LIST_COLUMNS = ("regulation_areas", "affected_firm_types", "key_deadlines")


def item_exists(conn: sqlite3.Connection, item_id: str) -> bool:
    cur = conn.execute("SELECT 1 FROM items WHERE id = ?", (item_id,))
    return cur.fetchone() is not None


def insert_item(conn: sqlite3.Connection, item: dict) -> None:
    """Insert a classified (or classification-failed) item. Never overwrites an
    existing id (FR3.2) — reruns are safe because dedupe already skips known ids,
    and INSERT OR IGNORE is a second line of defence.
    """
    row = dict(item)
    for col in _LIST_COLUMNS:
        row[col] = json.dumps(row.get(col) or [])
    row["classification_failed"] = int(row.get("classification_failed", False))
    row.setdefault("document_type", None)
    row.setdefault("summary", None)
    row.setdefault("impact_level", None)
    row.setdefault("classification_error", None)

    conn.execute(
        """
        INSERT OR IGNORE INTO items (
            id, url, title, source, published_date, ingested_at, raw_text,
            document_type, regulation_areas, affected_firm_types, summary,
            key_deadlines, impact_level, classification_failed, classification_error
        ) VALUES (
            :id, :url, :title, :source, :published_date, :ingested_at, :raw_text,
            :document_type, :regulation_areas, :affected_firm_types, :summary,
            :key_deadlines, :impact_level, :classification_failed, :classification_error
        )
        """,
        row,
    )
    conn.commit()


def _row_to_item(row: sqlite3.Row) -> dict:
    d = dict(row)
    for col in _LIST_COLUMNS:
        d[col] = json.loads(d[col] or "[]")
    d["classification_failed"] = bool(d["classification_failed"])
    return d


def get_all_items(conn: sqlite3.Connection) -> list[dict]:
    cur = conn.execute(
        "SELECT * FROM items ORDER BY published_date DESC, ingested_at DESC"
    )
    return [_row_to_item(row) for row in cur.fetchall()]


def get_upcoming_deadlines(conn: sqlite3.Connection, within_days: int = 90) -> list[dict]:
    """FR4.4: all extracted deadlines within the next `within_days` days, soonest first."""
    today = date.today()
    horizon = today + timedelta(days=within_days)
    deadlines = []
    for item in get_all_items(conn):
        for dl in item["key_deadlines"]:
            try:
                d = date.fromisoformat(dl["date"])
            except (ValueError, KeyError, TypeError):
                continue
            if today <= d <= horizon:
                deadlines.append(
                    {
                        "date": dl["date"],
                        "description": dl.get("description", ""),
                        "item_id": item["id"],
                        "item_title": item["title"],
                        "item_url": item["url"],
                        "source": item["source"],
                    }
                )
    deadlines.sort(key=lambda d: d["date"])
    return deadlines
