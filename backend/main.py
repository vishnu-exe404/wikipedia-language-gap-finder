"""REST backend.  Run:  uvicorn backend.main:app --reload --port 8000
Docs UI: http://localhost:8000/docs
Data sources come from env vars A_SRC, B_SRC, LINKED (defaults: the demo sample)."""
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from wikicompare.live import WikiError, empty_record, live_pair, search_titles
from wikicompare.service import Store, compare_records

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = FastAPI(title="Wikipedia Language Compare API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
_store = None


class LoadReq(BaseModel):
    a_src: str
    b_src: str
    linked: bool = True
    max_a: int = 100000
    max_b: int = 100000


class PairReq(BaseModel):
    a_key: str
    b_key: str
    a_lang: str = "English"
    b_lang: str = "Hindi"
    threshold: float = 0.55


def store():
    global _store
    if _store is None:
        try:
            _store = Store(os.getenv("A_SRC", os.path.join(ROOT, "sample_data", "en_sample.jsonl")),
                           os.getenv("B_SRC", os.path.join(ROOT, "sample_data", "hi_sample.jsonl")),
                           os.getenv("LINKED", "1") == "1")
        except FileNotFoundError as e:
            raise HTTPException(400, str(e))
    return _store


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/load")
def load(req: LoadReq):
    global _store
    try:
        _store = Store(req.a_src, req.b_src, req.linked, req.max_a, req.max_b)
    except FileNotFoundError as e:
        raise HTTPException(400, str(e))
    return _store.stats()


@app.get("/stats")
def stats():
    return store().stats()


@app.get("/search")
def search(side: str = "a", q: str = "", limit: int = 50):
    s = store()
    idx = s.A if side == "a" else s.B
    return [{"key": k, "name": idx[k]["name"], "qid": idx[k]["qid"]} for k in s.search(side, q, limit)]


@app.get("/pairs")
def pairs(q: str = "", limit: int = 100):
    s = store()
    return [{"a_key": a, "b_key": b, "a_name": s.A[a]["name"], "b_name": s.B[b]["name"]}
            for a, b in s.search_pairs(q, limit)]


@app.get("/compare")
def compare(a_key: str, b_key: str, threshold: float = 0.55):
    s = store()
    if a_key not in s.A or b_key not in s.B:
        raise HTTPException(404, "Unknown article key")
    return s.compare(a_key, b_key, threshold)


@app.get("/leaderboard")
def leaderboard(limit: int = 50):
    return store().leaderboard()[:limit]


@app.post("/suggest")
def suggest(req: PairReq):
    s = store()
    if req.a_key not in s.A or req.b_key not in s.B:
        raise HTTPException(404, "Unknown article key")
    try:
        return {"outline": s.suggest(req.a_key, req.b_key, req.a_lang, req.b_lang, req.threshold)}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/live/search")
def live_search(lang: str = "en", q: str = ""):
    try:
        return list(search_titles(lang, q))
    except WikiError as e:
        raise HTTPException(502, str(e))


@app.get("/live/compare")
def live_compare(topic: str, a_lang: str = "en", b_lang: str = "hi", threshold: float = 0.55):
    """Fetch the topic live from Wikipedia in both languages and compare."""
    try:
        a, b = live_pair(a_lang, b_lang, topic)
    except WikiError as e:
        raise HTTPException(502, str(e))
    out = compare_records(a, b or empty_record(b_lang, "(no article)"), threshold)
    out["target_exists"] = b is not None
    return out
