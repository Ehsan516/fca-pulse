import logging
import time

import feedparser
import httpx

logger = logging.getLogger(__name__)


def _extract_published_date(entry):
    for key in ("published_parsed", "updated_parsed"):
        struct = entry.get(key)
        if struct:
            return time.strftime("%Y-%m-%d", struct)
    return None


def poll_feed(client, feed):
    try:
        resp = client.get(feed["url"])
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Failed to fetch feed %r (%s): %s", feed["name"], feed["url"], exc)
        return []

    parsed = feedparser.parse(resp.content)
    if parsed.bozo and not parsed.entries:
        logger.error("Failed to parse feed %r (%s): %s", feed["name"], feed["url"], parsed.get("bozo_exception"))
        return []

    entries = []
    for e in parsed.entries:
        link = (e.get("link") or "").strip()
        title = (e.get("title") or "").strip()
        if not link or not title:
            continue
        entries.append({
            "title": title,
            "url": link,
            "source": feed["source"],
            "published_date": _extract_published_date(e),
        })
    return entries


def poll_all_feeds(client, feeds):
    entries = []
    for feed in feeds:
        result = poll_feed(client, feed)
        entries += result
    return entries
