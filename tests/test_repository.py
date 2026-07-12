from fca_pulse.storage.db import connect
from fca_pulse.storage.repository import get_all_items, insert_item, item_exists

def _item(item_id, title="Some title"):
    return {
        "id": item_id,
        "url": f"https://example.com/{item_id}",
        "title": title,
        "source": "FCA",
        "published_date": "2026-01-01",
        "ingested_at": "2026-01-01T00:00:00+00:00",
        "raw_text": "text",
        "document_type": "Policy Statement",
        "regulation_areas": ["Consumer Duty"],
        "affected_firm_types": ["Banks"],
        "summary": "summary",
        "key_deadlines": [],
        "impact_level": "informational",
        "classification_failed": False,
        "classification_error": None,
    }


def test_item_exists_false_before_insert_true_after(tmp_path):
    conn = connect(tmp_path / "test.db")
    assert item_exists(conn, "a") is False
    insert_item(conn, _item("a"))
    assert item_exists(conn, "a") is True

def test_reinserting_same_id_is_a_no_op(tmp_path):
    """Idempotency (NFR2.1): a rerun that sees the same item never duplicates it."""
    conn = connect(tmp_path / "test.db")
    insert_item(conn, _item("a", title="Original title"))
    insert_item(conn, _item("a", title="A different title"))

    items = get_all_items(conn)
    assert len(items) == 1
    assert items[0]["title"] == "Original title"

def test_classification_failed_items_are_stored_not_dropped(tmp_path):
    conn = connect(tmp_path / "test.db")
    item = _item("a")
    item["classification_failed"] = True
    item["classification_error"] = "schema validation failed twice"
    item["document_type"] = None
    insert_item(conn, item)

    stored = get_all_items(conn)[0]
    assert stored["classification_failed"] is True
    assert stored["classification_error"] == "schema validation failed twice"
