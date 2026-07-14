"""Stable item identity and deduplication"""

import hashlib


def make_item_id(url: str) -> str:
    """stable identifier for a publication derived from its URL
    Used as the archive's primary key so the same publication is never
    processed or displayed twice
    """
    normalized = url.strip().rstrip("/")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
