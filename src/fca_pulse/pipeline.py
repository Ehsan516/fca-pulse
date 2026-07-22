"""ingest -> classify -> store -> build site .

Each stage implemented in its own module and can be exercised independently in tests
"""
import argparse
import logging
import os
import sqlite3
import sys
from datetime import datetime, timezone
import anthropic
from fca_pulse.classify.client import classify_item
from fca_pulse.config import load_feeds
from fca_pulse.ingest.dedupe import make_item_id
from fca_pulse.ingest.feeds import poll_all_feeds
from fca_pulse.ingest.fetch import RateLimiter, RobotsCache, build_client, fetch_full_text
from fca_pulse.site.generate import build_site
from fca_pulse.storage.db import connect
from fca_pulse.storage.repository import insert_item, item_exists

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/archive.db"
DEFAULT_SITE_DIR = "docs"

_SKIPPED_CLASSIFICATION = {
    "document_type": None,
    "regulation_areas": [],
    "affected_firm_types": [],
    "summary": None,
    "key_deadlines": [],
    "impact_level": None,
    "classification_failed": True,
    "classification_error": "classification skipped (no Claude API key configured)",
}


def run_ingest_and_classify(conn: sqlite3.Connection, anthropic_client: anthropic.Anthropic | None) -> int:
    """poll feeds, fetch full text, classify, and store new items.

    returns the count of new items stored. items already present in the archive are skipped, so reruns never duplicate
    entries"""
    feeds_config = load_feeds()
    http_client = build_client(
        feeds_config["http"]["user_agent"], feeds_config["http"]["timeout_seconds"]
    )
    robots = RobotsCache(http_client, feeds_config["http"]["user_agent"])
    rate_limiter = RateLimiter(feeds_config["http"]["per_domain_delay_seconds"])

    entries = poll_all_feeds(http_client, feeds_config["feeds"])
    logger.info("Polled %d feed entries across %d feed(s)", len(entries), len(feeds_config["feeds"]))

    new_count = 0
    for entry in entries:
        item_id = make_item_id(entry["url"])
        if item_exists(conn, item_id):
            continue

        raw_text = fetch_full_text(http_client, entry["url"], robots, rate_limiter)
        if raw_text is None:
            logger.warning("Skipping (will retry next run): %s", entry["url"])
            continue

        item = {
            "id": item_id,
            "url": entry["url"],
            "title": entry["title"],
            "source": entry["source"],
            "published_date": entry["published_date"],
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "raw_text": raw_text,
        }

        classification = (
            classify_item(anthropic_client, item)
            if anthropic_client is not None
            else dict(_SKIPPED_CLASSIFICATION)
        )
        item.update(classification)

        insert_item(conn, item)
        new_count += 1
        logger.info("Stored new item: %s (%s)", entry["title"], entry["source"])

    return new_count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="FCA Pulse: ingest FCA/PRA feeds, classify with ai, store, and build the digest site."
    )
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="Path to the SQLite archive")
    parser.add_argument("--site-dir", default=DEFAULT_SITE_DIR, help="Output directory for the generated site")
    parser.add_argument(
        "--skip-classification",
        action="store_true",
        help="Skip ai classification (items are stored with classification_failed=True). "
        "Useful for smoke-testing ingestion and site generation without an API key.",
    )
    parser.add_argument(
        "--site-only",
        action="store_true",
        help="Only (re)generate the site from the existing archive; skip ingestion entirely.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    conn = connect(args.db)
    try:
        if not args.site_only:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if args.skip_classification:
                anthropic_client = None
            elif not api_key:
                logger.warning("ANTHROPIC_API_KEY not set; classification will be skipped for this run.")
                anthropic_client = None
            else:
                anthropic_client = anthropic.Anthropic(api_key=api_key)

            new_count = run_ingest_and_classify(conn, anthropic_client)
            logger.info("Ingestion complete: %d new item(s) stored", new_count)

        build_site(conn, args.site_dir)
        logger.info("Site generated at %s", args.site_dir)
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
