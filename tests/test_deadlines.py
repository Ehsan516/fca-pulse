from datetime import date, timedelta
from fca_pulse.storage.db import connect
from fca_pulse.storage.repository import get_upcoming_deadlines, insert_item

def _item(item_id, deadlines):
    return {
        "id": item_id,
        "url": f"https://example.com/{item_id}",
        "title": f"Item {item_id}",
        "source": "FCA",
        "published_date": "2026-01-01",
        "ingested_at": "2026-01-01T00:00:00+00:00",
        "raw_text": "text",
        "document_type": "Policy Statement",
        "regulation_areas": ["Consumer Duty"],
        "affected_firm_types": ["Banks"],
        "summary": "summary",
        "key_deadlines": deadlines,
        "impact_level": "action-required",
        "classification_failed": False,
        "classification_error": None,
    }


def test_deadlines_within_window_returned_soonest_first(tmp_path):
    conn = connect(tmp_path / "test.db")
    today = date.today()

    soon = (today + timedelta(days=5)).isoformat()
    later = (today + timedelta(days=40)).isoformat()
    too_far = (today + timedelta(days=200)).isoformat()
    past = (today - timedelta(days=5)).isoformat()

    insert_item(conn, _item("a", [{"date": later, "description": "later deadline"}]))
    insert_item(conn, _item("b", [{"date": soon, "description": "soon deadline"}]))
    insert_item(conn, _item("c", [{"date": too_far, "description": "too far"}]))
    insert_item(conn, _item("d", [{"date": past, "description": "already passed"}]))

    deadlines = get_upcoming_deadlines(conn, within_days=90)

    assert [d["description"] for d in deadlines] == ["soon deadline", "later deadline"]
    assert deadlines[0]["date"] < deadlines[1]["date"]


def test_malformed_or_missing_deadline_dates_are_omitted(tmp_path):
    conn = connect(tmp_path / "test.db")
    insert_item(
        conn,
        _item(
            "x",[{"date": "not-a-date", "description": "ambiguous, should be omitted"},
            ],
        ),
    )
    assert get_upcoming_deadlines(conn, within_days=90) == []


def test_no_items_means_no_deadlines(tmp_path):
    conn = connect(tmp_path / "test.db")
    assert get_upcoming_deadlines(conn, within_days=90) == []
