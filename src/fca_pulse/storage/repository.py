import json
import sqlite3
from datetime import date, timedelta

LIST_COLUMNS = ("regulation_areas", "affected_firm_types", "key_deadlines")


def item_exists(conn, item_id):
    cur = conn.execute("SELECT 1 FROM items WHERE id = ?", (item_id,))
    return cur.fetchone() is not None


def insert_item(conn, item):
    # NB: INSERT OR IGNORE so reruns don't blow up on duplicate ids
    row = dict(item)
    for col in LIST_COLUMNS:
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


def _row_to_item(row):
    d = dict(row)
    for col in LIST_COLUMNS:
        d[col] = json.loads(d[col] or "[]")
    d["classification_failed"] = bool(d["classification_failed"])
    return d


def get_all_items(conn):
    cur = conn.execute("SELECT * FROM items ORDER BY published_date DESC, ingested_at DESC")
    items = []
    for row in cur.fetchall():
        items.append(_row_to_item(row))
    return items


def get_upcoming_deadlines(conn, within_days=90):
    today = date.today()
    horizon = today + timedelta(days=within_days)
    deadlines = []
    for item in get_all_items(conn):
        for dl in item["key_deadlines"]:
            try:
                d = date.fromisoformat(dl["date"])
            except (ValueError, KeyError, TypeError):
                continue
            if d < today or d > horizon:
                continue
            deadlines.append({
                "date": dl["date"],
                "description": dl.get("description", ""),
                "item_id": item["id"],
                "item_title": item["title"],
                "item_url": item["url"],
                "source": item["source"],
            })
    deadlines.sort(key=lambda d: d["date"])
    return deadlines
