from fca_pulse.ingest.dedupe import make_item_id


def test_same_url_produces_same_id():
    url = "https://www.fca.org.uk/news/example"
    assert make_item_id(url) == make_item_id(url)


def test_different_urls_produce_different_ids():
    assert make_item_id("https://a.example/1") != make_item_id("https://a.example/2")


def test_trailing_slash_is_normalized():
    assert make_item_id("https://a.example/page") == make_item_id("https://a.example/page/")


def test_id_is_a_stable_hex_string():
    item_id = make_item_id("https://a.example/page")
    assert len(item_id) == 16
    int(item_id, 16)  # raises ValueError if not valid hex
