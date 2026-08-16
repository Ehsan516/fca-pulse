import argparse
import logging
import os
import sqlite3
import sys
from datetime import datetime, timezone

import anthropic
from dotenv import load_dotenv

from fca_pulse.classify.client import classify_item
from fca_pulse.config import load_feeds
from fca_pulse.ingest.dedupe import make_item_id
from fca_pulse.ingest.feeds import poll_all_feeds
from fca_pulse.ingest.fetch import RateLimiter, RobotsCache, build_client, fetch_full_text
from fca_pulse.site.generate import build_site
from fca_pulse.storage.db import connect
from fca_pulse.storage.repository import insert_item, item_exists

load_dotenv()  # loads ANTHROPIC_API_KEY from .env if it's there

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/archive.db"
DEFAULT_SITE_DIR = "docs"

# used when we don't have an api key / user passed --skip-classification
SKIPPED_CLASSIFICATION = {
    "document_type": None,
    "regulation_areas": [],
    "affected_firm_types": [],
    "summary": None,
    "key_deadlines": [],
    "impact_level": None,
    "classification_failed": True,
    "classification_error": "classification skipped (no Claude API key configured)",
}


def run_ingest_and_classify(conn, anthropic_client):
    # returns number of new items added this run
    feeds_config = load_feeds()
    http_client = build_client(feeds_config["http"]["user_agent"], feeds_config["http"]["timeout_seconds"])
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

        if anthropic_client is not None:
            classification = classify_item(anthropic_client, item)
        else:
            classification = dict(SKIPPED_CLASSIFICATION)
        item.update(classification)

        insert_item(conn, item)
        new_count = new_count + 1
        logger.info("Stored new item: %s (%s)", entry["title"], entry["source"])

    return new_count


def main(argv=None):
    parser = argparse.ArgumentParser(description="ingest FCA/PRA feeds, classify with claude, store, build site")
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    parser.add_argument("--site-dir", default=DEFAULT_SITE_DIR)
    parser.add_argument(
        "--skip-classification",
        action="store_true",
        help="skip classification, items get stored with classification_failed=True",
    )
    parser.add_argument("--site-only", action="store_true", help="just rebuild the site, don't ingest anything")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    conn = connect(args.db)
    try:
        if not args.site_only:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            anthropic_client = None
            if args.skip_classification:
                pass
            elif not api_key:
                logger.warning("ANTHROPIC_API_KEY not set; classification will be skipped for this run.")
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
