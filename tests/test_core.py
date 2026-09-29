import os
from wikicompare.matcher import find_missing
from wikicompare.metrics import coverage_score, ratio
from wikicompare.service import Store

D = os.path.join(os.path.dirname(__file__), "..", "sample_data")
EN, HI = os.path.join(D, "en_sample.jsonl"), os.path.join(D, "hi_sample.jsonl")


def test_linked_store():
    s = Store(EN, HI)
    assert len(s.pairs) == 3
    for a, b in s.pairs:
        assert 0 <= coverage_score(s.A[a], s.B[b]) <= 1


def test_free_mode_and_search():
    s = Store(EN, HI, linked=False)
    assert s.search("a", "taj") and s.search("b", "ताज")


def test_compare_glossary():
    s = Store(EN, HI)
    a = next(k for k in s.A if s.A[k]["name"] == "Prayagraj")
    c = s.compare(a, a)
    assert "Climate" in c["missing_sections"] and "History" not in c["missing_sections"]


def test_ratio_and_matcher():
    assert ratio(0, 5) == 1.0 and ratio(10, 5) == 0.5 and ratio(5, 10) == 1.0
    m, _ = find_missing(["History", "Culture"], ["history"])
    assert m == ["Culture"]
    assert find_missing(["Sports"], [])[0] == ["Sports"]
