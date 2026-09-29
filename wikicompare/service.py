"""Backend logic shared by the Streamlit app and the FastAPI server."""
from .llm import suggest_outline
from .loader import load_index
from .matcher import find_missing
from .metrics import LABELS, coverage_score, ratio


def compare_records(a, b, threshold=0.55):
    """Compare two compact records (from shards OR live Wikipedia)."""
    sec, method = find_missing(a["sections"], b["sections"], threshold)
    fld, _ = find_missing(a["fields"], b["fields"], threshold)
    return {
        "a": a, "b": b, "score": coverage_score(a, b), "method": method,
        "metrics": [{"metric": lbl, "a": a[k], "b": b[k], "coverage_pct": round(100 * ratio(a[k], b[k]))}
                    for lbl, k in LABELS],
        "missing_sections": sec, "missing_fields": fld,
    }


class Store:
    """Holds both languages (from Kaggle shards) in memory. linked=True pairs articles by
    Wikidata ID; linked=False lets you pick any article from each side."""

    def __init__(self, a_src, b_src, linked=True, max_a=100000, max_b=100000):
        self.linked = linked
        self.B = load_index(b_src, max_articles=max_b)
        if linked:
            qids = {r["qid"] for r in self.B.values() if r["qid"]}
            self.A = load_index(a_src, max_articles=10**9, only_qids=qids)
        else:
            self.A = load_index(a_src, max_articles=max_a)
        a_by_q = {r["qid"]: k for k, r in self.A.items() if r["qid"]}
        self.pairs = sorted(((a_by_q[r["qid"]], k) for k, r in self.B.items() if r["qid"] in a_by_q),
                            key=lambda p: self.A[p[0]]["name"].lower())

    def search(self, side, text, limit=50):
        idx = self.A if side == "a" else self.B
        t = (text or "").strip().lower()
        hits = [k for k, r in idx.items() if t in r["name"].lower()] if t else list(idx)[:limit]
        hits.sort(key=lambda k: (not idx[k]["name"].lower().startswith(t), len(idx[k]["name"])))
        return hits[:limit]

    def search_pairs(self, text, limit=100):
        t = (text or "").strip().lower()
        hits = [p for p in self.pairs
                if not t or t in self.A[p[0]]["name"].lower() or t in self.B[p[1]]["name"].lower()]
        return hits[:limit]

    def stats(self):
        return {"linked": self.linked, "articles_a": len(self.A), "articles_b": len(self.B),
                "shared_topics": len(self.pairs)}

    def compare(self, a_key, b_key, threshold=0.55):
        return compare_records(self.A[a_key], self.B[b_key], threshold)

    def leaderboard(self):
        rows = []
        for ak, bk in self.pairs:
            a, b = self.A[ak], self.B[bk]
            rows.append({"topic": a["name"], "target_title": b["name"], "qid": a["qid"],
                         "coverage_pct": round(100 * coverage_score(a, b)),
                         "sections_a": a["n_sections"], "sections_b": b["n_sections"],
                         "words_a": a["body_words"], "words_b": b["body_words"],
                         "a_key": ak, "b_key": bk})
        return sorted(rows, key=lambda r: r["coverage_pct"])

    def suggest(self, a_key, b_key, a_lang="English", b_lang="Hindi", threshold=0.55):
        c = self.compare(a_key, b_key, threshold)
        return suggest_outline(c["a"]["name"], c["missing_sections"], c["missing_fields"], b_lang, a_lang)
