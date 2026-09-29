"""Turn one raw Wikimedia structured article into a small comparable record."""


def _walk(parts):
    for p in parts or []:
        if isinstance(p, dict):
            yield p
            yield from _walk(p.get("has_parts"))


def compact(article):
    """Return a compact profile dict, or None if the record is unusable.
    `qid` is the Wikidata ID (None if missing); `key` is a unique id inside one language."""
    if not isinstance(article, dict):
        return None
    name = article.get("name") or ""
    qid = (article.get("main_entity") or {}).get("identifier")
    if not name and not qid:
        return None
    sections, words, images = [], 0, 0
    for p in _walk(article.get("sections")):
        kind = p.get("type")
        if kind == "section" and p.get("name") and p["name"].strip().lower() != "abstract":
            sections.append(p["name"].strip())
        elif kind == "paragraph":
            words += len((p.get("value") or "").split())
        elif kind == "image":
            images += 1
    fields = [p["name"].strip() for p in _walk(article.get("infoboxes"))
              if p.get("type") == "field" and p.get("name")]
    abstract = article.get("abstract") or ""
    return {
        "key": qid or f"name:{name}", "qid": qid, "name": name or qid,
        "url": article.get("url", ""), "abstract": abstract,
        "abstract_words": len(abstract.split()),
        "sections": sections, "n_sections": len(sections),
        "fields": fields, "n_fields": len(fields),
        "body_words": words, "n_images": images + (1 if article.get("image") else 0),
    }


def ratio(ref, target):
    """Share of the reference that the target covers (capped at 1). Nothing to cover = 1."""
    return 1.0 if ref == 0 else min(target / ref, 1.0)


WEIGHTS = {"abstract_words": 0.20, "n_sections": 0.30, "n_fields": 0.20,
           "body_words": 0.25, "n_images": 0.05}
LABELS = [("Abstract words", "abstract_words"), ("Sections", "n_sections"),
          ("Infobox fields", "n_fields"), ("Body words", "body_words"), ("Images", "n_images")]


def coverage_score(a, b):
    """Weighted 0..1 score: how much of article A's content article B has."""
    return sum(w * ratio(a[k], b[k]) for k, w in WEIGHTS.items())
