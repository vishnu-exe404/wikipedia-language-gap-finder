"""Wikipedia Language Compare (Streamlit UI).  Run:  streamlit run app.py"""
import os

import pandas as pd
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from wikicompare.languages import ALL_LANGUAGES, INDIAN_LANGUAGES, REFERENCE_LANGUAGES
from wikicompare.live import WikiError, empty_record, live_pair, search_titles
from wikicompare.llm import suggest_outline
from wikicompare.metrics import WEIGHTS, coverage_score
from wikicompare.service import Store, compare_records

st.set_page_config(page_title="Wikipedia Language Compare", page_icon="🌍", layout="wide")
HERE = os.path.dirname(os.path.abspath(__file__))


@st.cache_resource(show_spinner="Reading shards (big files can take a few minutes)...")
def get_store(a_src, b_src, linked, max_a, max_b):
    return Store(a_src, b_src, linked, max_a, max_b)


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("Settings")
    mode = st.radio("Data source", ["Live Wikipedia", "Kaggle shards", "Demo sample"],
                    help="Live Wikipedia needs internet. Kaggle shards read local files.")

    ref_names = [n for n, _ in REFERENCE_LANGUAGES]
    tgt_names = [n for n, _ in ALL_LANGUAGES]
    a_lang = st.selectbox("Reference language", ref_names, index=0)
    b_lang = st.selectbox("Target language (10 major Indian languages + more)", tgt_names, index=1)
    a_code = dict(REFERENCE_LANGUAGES)[a_lang]
    b_code = dict(ALL_LANGUAGES)[b_lang]
    if a_lang == b_lang:
        st.warning("Reference and target are the same language. Pick two different ones.")
    with st.expander("Language codes used"):
        st.write(f"{a_lang} → `{a_code}.wikipedia.org`, {b_lang} → `{b_code}.wikipedia.org`")

    if mode == "Kaggle shards":
        a_src = st.text_input("Reference language folder/file", "data/en")
        b_src = st.text_input("Target language folder/file", "data/hi")
    else:
        a_src = os.path.join(HERE, "sample_data", "en_sample.jsonl")
        b_src = os.path.join(HERE, "sample_data", "hi_sample.jsonl")
    if mode != "Live Wikipedia":
        pairing = st.radio("Pairing", ["Linked by Wikidata ID", "Pick any two articles"],
                           help="Use 'Pick any two' if your shards contain different topics.")
        linked = pairing.startswith("Linked")
        max_b = st.number_input("Max target articles to load", 100, 2_000_000, 100_000, step=1000)
        max_a = st.number_input("Max reference articles (Pick-any mode)", 100, 2_000_000, 100_000,
                                step=1000, disabled=linked)
        if st.button("Reload data"):
            get_store.clear()
    thr = st.slider("Section match threshold", 0.30, 0.90, 0.55, 0.05,
                    help="Only used by the embedding matcher. Higher = more sections reported missing.")

st.title("🌍 Wikipedia Language Compare")
st.caption(f"What does the {b_lang} article miss compared with {a_lang}? "
           + ("Data is fetched live from Wikipedia." if mode == "Live Wikipedia"
              else "Built on the Wikimedia Structured Wikipedia dataset."))


# ------------------------------------------------------------------ shared comparison view
def show_comparison(c, uid):
    a, b = c["a"], c["b"]
    col1, col2 = st.columns(2)
    for col, rec, lang in ((col1, a, a_lang), (col2, b, b_lang)):
        col.subheader(f'{lang}: {rec["name"]}')
        text = rec["abstract"]
        col.write(text[:500] + ("..." if len(text) > 500 else "") if text else "_No abstract._")
        if rec["url"]:
            col.markdown(f'[Open on Wikipedia]({rec["url"]})')

    st.metric("Coverage score", f'{c["score"]:.0%}',
              help="Weighted: " + ", ".join(f"{k} {int(w * 100)}%" for k, w in WEIGHTS.items()))
    df = pd.DataFrame(c["metrics"]).rename(columns={"metric": "Metric", "a": a_lang, "b": b_lang,
                                                    "coverage_pct": "Coverage %"})
    m1, m2 = st.columns(2)
    m1.dataframe(df, hide_index=True)
    m2.bar_chart(df.set_index("Metric")["Coverage %"])

    st.caption(f'Matching method: {c["method"]}')
    s1, s2 = st.columns(2)
    s1.subheader(f'Sections missing in {b_lang} ({len(c["missing_sections"])})')
    s1.write(c["missing_sections"] or "None 🎉")
    s2.subheader(f'Infobox fields missing in {b_lang} ({len(c["missing_fields"])})')
    s2.write(c["missing_fields"] or "None 🎉")

    if st.button("✨ Suggest improvements with Claude", key=f"btn_{uid}"):
        try:
            with st.spinner("Asking Claude..."):
                st.session_state[f"out_{uid}"] = suggest_outline(
                    a["name"], c["missing_sections"], c["missing_fields"], b_lang, a_lang)
        except Exception as e:
            st.error(str(e))
    if f"out_{uid}" in st.session_state:
        st.markdown(st.session_state[f"out_{uid}"])


def csv_table(rows, name):
    df = pd.DataFrame(rows)
    st.dataframe(df, hide_index=True)
    st.bar_chart(df.head(15).set_index("Topic")["Coverage %"])
    st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), name, "text/csv")


# ------------------------------------------------------------------ LIVE WIKIPEDIA MODE
if mode == "Live Wikipedia":
    tab_one, tab_many = st.tabs(["🔍 Compare a topic", "📊 Rank several topics"])

    with tab_one:
        q = st.text_input(f"Search a topic on {a_code}.wikipedia.org", "Prayagraj")
        try:
            options = list(search_titles(a_code, q))
        except WikiError as e:
            options = []
            st.error(str(e))
        if q.strip() and not options and not st.session_state.get("_err"):
            st.info("No Wikipedia article found for that search.")
        title = st.selectbox("Choose an article", options) if options else None
        if title:
            try:
                with st.spinner("Fetching from Wikipedia..."):
                    a, b = live_pair(a_code, b_code, title)
                if b is None:
                    st.warning(f"There is **no {b_lang} article** for this topic yet. "
                               "Everything below is missing, which makes it a great one to write!")
                c = compare_records(a, b or empty_record(b_code, "(no article)"), thr)
                show_comparison(c, f"live_{a_code}_{b_code}_{title}")
            except WikiError as e:
                st.error(str(e))

    with tab_many:
        topics = st.text_area("One topic per line (titles on the reference-language Wikipedia, max 25)",
                              "Prayagraj\nTaj Mahal\nKumbh Mela\nVaranasi\nHoli", height=140)
        if st.button("Fetch & rank"):
            names = [t.strip() for t in topics.splitlines() if t.strip()][:25]
            rows, prog = [], st.progress(0.0)
            for i, t in enumerate(names):
                try:
                    a, b = live_pair(a_code, b_code, t)
                    b = b or empty_record(b_code, "(no article)")
                    rows.append({"Topic": a["name"], f"{b_lang} title": b["name"],
                                 "Coverage %": round(100 * coverage_score(a, b)),
                                 f"Sections {a_lang}": a["n_sections"], f"Sections {b_lang}": b["n_sections"],
                                 f"Words {a_lang}": a["body_words"], f"Words {b_lang}": b["body_words"]})
                except WikiError as e:
                    st.warning(f"{t}: {e}")
                prog.progress((i + 1) / len(names))
            st.session_state["live_rows"] = sorted(rows, key=lambda r: r["Coverage %"])
        if st.session_state.get("live_rows"):
            st.write(f"Weakest {b_lang} articles first.")
            csv_table(st.session_state["live_rows"], "weak_articles.csv")
    st.stop()

# ------------------------------------------------------------------ SHARD MODES
try:
    store = get_store(a_src, b_src, linked, int(max_a), int(max_b))
except FileNotFoundError as e:
    st.error(f"{e}\n\nPut your shard files in those folders (see README) or switch to another data source.")
    st.stop()
except Exception as e:
    st.error(f"Could not read the data: {type(e).__name__}: {e}")
    st.stop()

tab_cmp, tab_weak, tab_data = st.tabs(["🔍 Compare", "📉 Weakest articles", "🛠 Data check"])

with tab_cmp:
    pick = None
    if store.linked:
        if not store.pairs:
            st.warning("No article appears in both languages (matched by Wikidata ID). Switch 'Pairing' to "
                       "'Pick any two articles', download matching shards, or use 'Live Wikipedia'.")
        else:
            q = st.text_input("Search topic (either language)")
            hits = store.search_pairs(q)
            if hits:
                pick = st.selectbox("Topic", hits, format_func=lambda p: f"{store.A[p[0]]['name']} / {store.B[p[1]]['name']}")
            else:
                st.info("No topic matches that search.")
    else:
        ca, cb = st.columns(2)
        ka = ca.selectbox(f"{a_lang} article", store.search("a", ca.text_input(f"Search {a_lang} title")),
                          format_func=lambda k: store.A[k]["name"])
        kb = cb.selectbox(f"{b_lang} article", store.search("b", cb.text_input(f"Search {b_lang} title")),
                          format_func=lambda k: store.B[k]["name"])
        if ka and kb:
            pick = (ka, kb)
    if pick:
        show_comparison(store.compare(pick[0], pick[1], thr), f"shard_{pick[0]}_{pick[1]}")

with tab_weak:
    board = pd.DataFrame(store.leaderboard())
    if board.empty:
        st.info("The ranking needs articles linked by Wikidata ID in both languages.")
    else:
        show = board.drop(columns=["a_key", "b_key"]).rename(columns={
            "topic": "Topic", "target_title": f"{b_lang} title", "qid": "Wikidata",
            "coverage_pct": "Coverage %", "sections_a": f"Sections {a_lang}", "sections_b": f"Sections {b_lang}",
            "words_a": f"Words {a_lang}", "words_b": f"Words {b_lang}"})
        st.write(f"Weakest {b_lang} articles first.")
        csv_table(show.to_dict("records"), "weak_articles.csv")

with tab_data:
    s = store.stats()
    x, y, z = st.columns(3)
    x.metric(f"{a_lang} articles loaded", s["articles_a"])
    y.metric(f"{b_lang} articles loaded", s["articles_b"])
    z.metric("Shared topics (same Wikidata ID)", s["shared_topics"])
    st.write(f"Sample {a_lang} titles:", [r["name"] for r in list(store.A.values())[:8]])
    st.write(f"Sample {b_lang} titles:", [r["name"] for r in list(store.B.values())[:8]])
    st.caption("If 'Shared topics' is 0, your two sets of shards contain different topics: "
               "use 'Pick any two articles', 'Live Wikipedia', or download matching shards.")
