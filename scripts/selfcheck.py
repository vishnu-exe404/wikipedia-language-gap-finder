"""Run:  python scripts/selfcheck.py   -> shows exactly what works and what does not."""
import importlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
fails = 0


def check(label, fn, required=True):
    global fails
    try:
        out = fn()
        print(f"[ OK ] {label}" + (f"  -> {out}" if out else ""))
    except Exception as e:
        tag = "FAIL" if required else "WARN"
        fails += required
        print(f"[{tag}] {label}  -> {type(e).__name__}: {e}")


print(f"Python {sys.version.split()[0]}")
for pkg, req in (("pandas", 1), ("streamlit", 1), ("fastapi", 0), ("uvicorn", 0),
                 ("sentence_transformers", 0), ("anthropic", 0)):
    check(f"import {pkg}" + ("" if req else " (optional)"), lambda p=pkg: importlib.import_module(p) and None, bool(req))

from wikicompare.service import Store  # noqa: E402

S = os.path.join(ROOT, "sample_data")
store = {}


def load_demo():
    store["s"] = Store(os.path.join(S, "en_sample.jsonl"), os.path.join(S, "hi_sample.jsonl"))
    assert len(store["s"].pairs) == 3, f"expected 3 pairs, got {len(store['s'].pairs)}"
    return f"{len(store['s'].pairs)} linked topics"


def compare_demo():
    s = store["s"]
    a, b = s.pairs[0]
    c = s.compare(a, b)
    assert c["missing_sections"], "no missing sections detected"
    return f"{c['a']['name']}: score {c['score']:.0%}, missing {c['missing_sections']}"


def embeddings():
    from wikicompare.matcher import missing_items
    r = missing_items(["History", "Climate"], ["इतिहास"], 0.5)
    return f"embedding model works, missing={r}"


def data_dirs():
    from wikicompare.loader import find_files
    out = []
    for d in ("data/en", "data/hi"):
        out.append(f"{d}: {len(find_files(os.path.join(ROOT, d)))} shard file(s)")
    return "; ".join(out)


check("load demo data", load_demo)
check("compare + glossary matching", compare_demo)
check("embedding model (optional, first run downloads ~470 MB)", embeddings, False)
def live_api():
    from wikicompare.live import live_pair
    a, b = live_pair("en", "hi", "Taj Mahal")
    return f"{a['name']}: {a['n_sections']} sections, {a['n_fields']} infobox fields; Hindi: {b['name'] if b else 'none'}"


check("Live Wikipedia connection (optional, needs internet)", live_api, False)
check("Kaggle shard folders", data_dirs, False)
def api_key():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("not set (only needed for the AI button)")


check("ANTHROPIC_API_KEY (optional)", api_key, False)
print("\nAll required checks passed." if not fails else f"\n{fails} required check(s) failed.")
sys.exit(1 if fails else 0)
