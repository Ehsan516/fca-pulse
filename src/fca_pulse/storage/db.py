import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    published_date TEXT,
    ingested_at TEXT NOT NULL,
    raw_text TEXT,
    document_type TEXT,
    regulation_areas TEXT NOT NULL DEFAULT '[]',
    affected_firm_types TEXT NOT NULL DEFAULT '[]',
    summary TEXT,
    key_deadlines TEXT NOT NULL DEFAULT '[]',
    impact_level TEXT,
    classification_failed INTEGER NOT NULL DEFAULT 0,
    classification_error TEXT
);
"""


def connect(db_path):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn
