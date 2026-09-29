from unittest.mock import patch

from wikicompare import live

HTML = ('<div class="mw-parser-output"><table class="infobox vcard"><tbody>'
        '<tr><th colspan="2">Prayagraj</th></tr>'
        '<tr><th scope="row">Country</th><td>India<sup>[1]</sup></td></tr>'
        '<tr><th>Elevation:</th><td>98 m</td></tr>'
        '<tr><td colspan="2"><img width="220"><img width="16"></td></tr></tbody></table>'
        '<p>Prayagraj is a city.<sup class="reference">[1]</sup></p><p>Second para.</p>'
        '<div class="mw-heading"><h2 id="History">History</h2></div>'
        '<p>Old city with many words here.</p><table><tr><td><p>ignored text</p></td></tr></table></div>')

PAGES = {
    ("en", "Prayagraj"): {"parse": {"title": "Prayagraj", "text": HTML,
                                    "sections": [{"line": "History"}, {"line": "<i>Geography</i>"}],
                                    "langlinks": [{"lang": "hi", "title": "प्रयागराज"}],
                                    "properties": [{"name": "wikibase_item", "value": "Q161"}]}},
    ("hi", "प्रयागराज"): {"parse": {"title": "प्रयागराज", "text": "<p>यह शहर है।</p>",
                                    "sections": [{"line": "इतिहास"}], "langlinks": [],
                                    "properties": {"wikibase_item": "Q161", "page_image_free": "x.jpg"}}},
    ("en", "Lonely"): {"parse": {"title": "Lonely", "text": "<p>x</p>", "sections": [], "langlinks": [],
                                 "properties": []}},
}


def fake_get(lang, params):
    if params["action"] == "opensearch":
        return [params["search"], ["Prayagraj", "Prayagraj district"], [], []]
    key = (lang, params["page"])
    return PAGES[key] if key in PAGES else {"error": {"info": "The page you specified doesn't exist."}}


def setup():
    live.fetch_article.cache_clear()
    live.search_titles.cache_clear()


def test_parse_and_pair():
    setup()
    with patch.object(live, "_get", fake_get):
        a, b = live.live_pair("en", "hi", "Prayagraj")
        assert a["qid"] == "Q161" and b["name"] == "प्रयागराज"
        assert a["sections"] == ["History", "Geography"]
        assert a["fields"] == ["Country", "Elevation"] and a["n_images"] == 1
        assert a["abstract"] == "Prayagraj is a city. Second para." and a["body_words"] == 12
        assert live.search_titles("en", "Praya")[0] == "Prayagraj"


def test_missing_target_and_errors():
    setup()
    with patch.object(live, "_get", fake_get):
        a, b = live.live_pair("en", "hi", "Lonely")
        assert b is None
        try:
            live.fetch_article("en", "Nope")
            assert False
        except live.WikiError:
            pass
    try:
        live._get("evil.com/x", {})
        assert False
    except live.WikiError:
        pass


def test_qid_shapes():
    assert live._qid({"wikibase_item": "Q5"}) == "Q5"
    assert live._qid([{"name": "wikibase_item", "value": "Q6"}]) == "Q6"
    assert live._qid([{"name": "wikibase_item", "*": "Q7"}]) == "Q7"
    assert live._qid(None) is None and live._qid([]) is None and live._qid({}) is None
