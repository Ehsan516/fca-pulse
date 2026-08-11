"""Static site generation from the archive (FR4)."""

import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from fca_pulse.config import load_vocab
from fca_pulse.storage.repository import get_all_items, get_upcoming_deadlines

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"

DEADLINE_WINDOW_DAYS = 90


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
    )


def build_site(conn: sqlite3.Connection, output_dir: str) -> None:
    """Render the digest (FR4.1-3), deadlines view (FR4.4), and static assets."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    items = get_all_items(conn)
    deadlines = get_upcoming_deadlines(conn, within_days=DEADLINE_WINDOW_DAYS)
    vocab = load_vocab()
    last_updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    env = _env()

    (out / "index.html").write_text(
        env.get_template("index.html").render(
            items=items, vocab=vocab, last_updated=last_updated, item_count=len(items)
        ),
        encoding="utf-8",
    )

    (out / "deadlines.html").write_text(
        env.get_template("deadlines.html").render(
            deadlines=deadlines, last_updated=last_updated, window_days=DEADLINE_WINDOW_DAYS
        ),
        encoding="utf-8",
    )

    static_out = out / "static"
    if static_out.exists():
        shutil.rmtree(static_out)
    shutil.copytree(STATIC_DIR, static_out)
