import hashlib


def make_item_id(url):
    # hash the url so we get a stable short id to use as the primary key
    normalized = url.strip().rstrip("/")
    h = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return h[:16]
