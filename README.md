# 🌍 Wikipedia Language Compare

Compare the same Wikipedia topic in two languages (default English vs Hindi) using the
**Wikimedia Structured Wikipedia dataset** (Kaggle), and see what the smaller article is missing.

Features: topic search, side-by-side abstracts, coverage score, charts, missing sections and infobox
fields (offline glossary + optional multilingual AI matching), "weakest articles" ranking with CSV export,
data-check tab, optional Claude outline suggestions, REST backend (FastAPI), dark mode (menu ⋮ → Settings).
Remedy

The proposed solution is a Wikipedia Language Gap Finder, a web application that compares Wikipedia articles in two different languages and identifies missing information.

The application is available online:

Live Demo: "Wikipedia Language Gap Finder" (https://reference-url-citation.invalid/0)

It compares article abstracts, sections, and infobox fields, calculates a coverage score, and highlights missing content in the smaller article.
## 1. Install (Python 3.10+)

```bash
cd wikipedia-language-gap-finder
python -m venv .venv
# Windows: .venv\Scripts\activate        Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
```
Optional, better cross-language matching (large download, installs PyTorch, ~470 MB model on first use):
```bash
pip install -r requirements-ml.txt
```
The app works without it: it falls back to a built-in English-Hindi glossary of common section names.

## 2. Check that everything works

```bash
python scripts/selfcheck.py
```
Every line should say `[ OK ]`. `[WARN]` lines are optional features. A `[FAIL]` line names the exact problem.

## 3. Run the app

```bash
streamlit run app.py
```
Opens http://localhost:8501 (Live Wikipedia mode; choose 'Demo sample' in the sidebar to work offline). This is a single command; the backend logic is built in.

## 4a. Live Wikipedia mode (default, needs internet)

Pick **Live Wikipedia** in the sidebar. Reference language defaults to English; the target language
dropdown lists the 10 major Indian languages plus a few more:

| Language | Code | | Language | Code |
|---|---|---|---|---|
| Hindi | hi | | Gujarati | gu |
| Bengali | bn | | Kannada | kn |
| Telugu | te | | Malayalam | ml |
| Marathi | mr | | Punjabi | pa |
| Tamil | ta | | Urdu | ur |

(Odia, Assamese, Maithili, Sanskrit and Nepali are also in the dropdown.) Type a topic, choose an
article, and the app fetches it from Wikipedia's public API, follows its language link to the target
article, and compares them. If no article exists in that language, it says so — a good sign it needs
writing. The second tab ranks a list of topics (up to 25). No download or API key is needed.
Backend equivalents: `GET /live/search` and `GET /live/compare?topic=Prayagraj&a_lang=en&b_lang=hi`
(swap `hi` for any of the codes above).

The offline glossary (used when the embedding model isn't installed) covers common section and
infobox names in all 10 Indian languages, in `wikicompare/glossary.py`.

## 4b. Use the real Kaggle shards

1. Put all English shard files in `data/en/` and all Hindi shard files in `data/hi/` (`.jsonl`, `.ndjson`, `.json`, or `.gz`; subfolders are fine).
2. `python scripts/inspect_schema.py data/hi/<a shard file>` to confirm field names
   (expected: `name`, `abstract`, `sections`, `infoboxes`, `image`, `main_entity.identifier`). If they differ, edit only `wikicompare/metrics.py`.
3. In the sidebar choose **Kaggle shards**.
4. Check the **Data check** tab. If "Shared topics" is 0, your English and Hindi shards hold different topics
   (the dataset is split into random chunks). Either download more shards, or set Pairing to **Pick any two articles**.

## 5. Optional backend API (for other frontends or teammates)

```bash
uvicorn backend.main:app --reload --port 8000
```
Docs and a try-it UI: http://localhost:8000/docs. Endpoints: `/health`, `/load`, `/stats`, `/search`, `/pairs`,
`/compare`, `/leaderboard`, `/suggest`. By default it serves the demo data; set `A_SRC`, `B_SRC`
(and `LINKED=0` for any-two mode) in `.env`, or call `POST /load`.

## 6. Optional AI suggestions

```bash
cp .env.example .env     # (Windows: copy .env.example .env) then add ANTHROPIC_API_KEY
```
Never commit `.env` (it is in `.gitignore`).

## 7. Tests

```bash
python -m pytest
```

## 8. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/wikipedia-language-gap-finder.git
git push -u origin main
```
(Create an empty repo on github.com first.) Teammates: `git clone <url>`, then `git checkout -b my-feature`, `git push`, open a pull request.
`data/` is git-ignored so the dataset is never uploaded.

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` / `pip` not found | use `python3` / `pip3` |
| `streamlit` not found | activate the venv, run `pip install -r requirements.txt` |
| "No shard files found" | check folder names `data/en`, `data/hi` and that files end in `.jsonl`/`.json`/`.gz` |
| "Could not reach wikipedia.org" | check internet/proxy/firewall, or use 'Demo sample' |
| Shared topics = 0 | switch Pairing to "Pick any two articles" |
| Everything shows 0 sections/words | field names differ: run `inspect_schema.py`, edit `metrics.py` |
| Slow / out of memory | lower "Max target articles" in the sidebar |
| Embedding model errors | ignore: the app falls back to glossary + exact matching |
| AI button error | add `ANTHROPIC_API_KEY` to `.env` and restart |

## Layout

```
app.py                  Streamlit UI
backend/main.py         FastAPI REST server
wikicompare/service.py  shared logic (Store: load, search, compare, leaderboard)
wikicompare/loader.py   shard reader   | metrics.py  scoring (edit if schema differs)
wikicompare/matcher.py  glossary / embeddings / exact matching | glossary.py  EN-HI terms
wikicompare/llm.py      Claude outline suggestions
scripts/                selfcheck, schema inspector, sample-data generator
```
