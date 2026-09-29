"""Live connection to Wikipedia (MediaWiki Action API). Standard library only, needs internet.
One `action=parse` call per article returns HTML, section list, language links and Wikidata ID."""
import html as htmllib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache
from html.parser import HTMLParser

UA = os.getenv("WIKI_USER_AGENT", "WikiLangCompare/1.0 (open-source-day lab project)")
LANG_RE = re.compile(r"^[a-z][a-z0-9\-]{1,11}$")


class WikiError(Exception):
    """Readable error for the UI (no internet, page missing, bad language code...)."""


def _get(lang, params):
    if not LANG_RE.match(lang or ""):
        raise WikiError(f"'{lang}' is not a valid Wikipedia language code (examples: en, hi, ta, bn).")
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {**params, "format": "json", "formatversion": "2"})
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise WikiError(f"Wikipedia returned HTTP {e.code}. If it persists, set WIKI_USER_AGENT in .env to a descriptive name plus your email (Wikimedia policy), and check that your network allows wikipedia.org.") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise WikiError(f"Could not reach {lang}.wikipedia.org. Check your internet connection. ({e})") from e


class _Page(HTMLParser):
    """Extracts abstract, body word count, infobox labels and image count from article HTML."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.abstract, self.fields = [], []
        self.words = self.images = 0
        self.seen_h2 = False
        self.table = self.info = self.skip = 0   # info = table depth where the infobox started
        self.in_p, self.buf, self.cells, self.cell = False, [], [], None

    def _in_info_cell(self):
        return self.info and self.table == self.info

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class") or ""
        if tag in ("sup", "style", "script"):
            self.skip += 1
        elif tag == "table":
            self.table += 1
            if not self.info and "infobox" in cls:
                self.info = self.table
        elif tag == "tr" and self._in_info_cell():
            self.cells = []
        elif tag in ("th", "td") and self._in_info_cell():
            self.cell = []
        elif tag == "p" and not self.table:
            self.in_p, self.buf = True, []
        elif tag == "h2":
            self.seen_h2 = True
        elif tag == "img":
            try:
                if int(a.get("width") or 0) >= 80:
                    self.images += 1
            except ValueError:
                pass

    def handle_data(self, data):
        if self.skip:
            return
        if self.cell is not None and self._in_info_cell():
            self.cell.append(data)
        if self.in_p:
            self.buf.append(data)

    def handle_endtag(self, tag):
        if tag in ("sup", "style", "script"):
            self.skip = max(0, self.skip - 1)
        elif tag in ("th", "td") and self.cell is not None and self._in_info_cell():
            self.cells.append(" ".join(" ".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self._in_info_cell():
            if len(self.cells) >= 2 and self.cells[0] and self.cells[1] and len(self.cells[0]) <= 60:
                self.fields.append(self.cells[0].rstrip(": "))
            self.cells = []
        elif tag == "table":
            if self.info and self.table == self.info:
                self.info = 0
            self.table = max(0, self.table - 1)
        elif tag == "p" and self.in_p:
            self.in_p = False
            text = " ".join(" ".join(self.buf).split())
            if text:
                self.words += len(text.split())
                if not self.seen_h2:
                    self.abstract.append(text)


def parse_html(page_html):
    p = _Page()
    p.feed(page_html or "")
    p.close()
    return p


def _strip_tags(s):
    return htmllib.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def _qid(props):
    """Wikidata ID from the `properties` field, which is a dict in newer API responses
    ({'wikibase_item': 'Q161'}) and a list of {'name','value'} items in older ones."""
    if isinstance(props, dict):
        return props.get("wikibase_item")
    if isinstance(props, list):
        for pr in props:
            if isinstance(pr, dict) and pr.get("name") == "wikibase_item":
                return pr.get("value") or pr.get("*")
    return None


@lru_cache(maxsize=512)
def fetch_article(lang, title):
    """Returns {'rec': compact-style record, 'langlinks': {lang_code: title}}."""
    data = _get(lang, {"action": "parse", "page": title, "prop": "text|sections|langlinks|properties",
                       "redirects": 1, "disableeditsection": 1, "disablelimitreport": 1})
    if "error" in data:
        info = data["error"].get("info", "unknown error")
        raise WikiError(f"{lang}.wikipedia.org: {info} (page: '{title}')")
    p = data["parse"]
    text = p.get("text")
    page_html = text.get("*", "") if isinstance(text, dict) else (text or "")
    pg = parse_html(page_html)
    sections = [s for s in (_strip_tags(x.get("line")) for x in (p.get("sections") or [])
                            if isinstance(x, dict)) if s]
    fields = list(dict.fromkeys(pg.fields))
    qid = _qid(p.get("properties"))
    name = p.get("title", title)
    abstract = " ".join(pg.abstract)
    rec = {"key": qid or f"{lang}:{name}", "qid": qid, "name": name, "lang": lang,
           "url": f"https://{lang}.wikipedia.org/wiki/" + urllib.parse.quote(name.replace(" ", "_")),
           "abstract": abstract, "abstract_words": len(abstract.split()),
           "sections": sections, "n_sections": len(sections),
           "fields": fields, "n_fields": len(fields),
           "body_words": pg.words, "n_images": pg.images}
    links = {l["lang"]: (l.get("title") or l.get("*")) for l in (p.get("langlinks") or [])
             if isinstance(l, dict) and l.get("lang")}
    return {"rec": rec, "langlinks": links}


@lru_cache(maxsize=256)
def search_titles(lang, text, limit=8):
    if not (text or "").strip():
        return ()
    data = _get(lang, {"action": "opensearch", "search": text, "limit": limit, "namespace": 0})
    return tuple(data[1]) if isinstance(data, list) and len(data) > 1 else ()


def empty_record(lang, name):
    return {"key": f"{lang}:none", "qid": None, "name": name, "lang": lang, "url": "", "abstract": "",
            "abstract_words": 0, "sections": [], "n_sections": 0, "fields": [], "n_fields": 0,
            "body_words": 0, "n_images": 0}


def live_pair(a_lang, b_lang, topic):
    """Fetch `topic` in a_lang, follow its language link to b_lang.
    Returns (a_record, b_record_or_None). None means no article exists in b_lang."""
    a = fetch_article(a_lang, topic)
    title_b = a["langlinks"].get(b_lang)
    b = fetch_article(b_lang, title_b)["rec"] if title_b else None
    return a["rec"], b
