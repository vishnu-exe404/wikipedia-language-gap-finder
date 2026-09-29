"""Cross-language matching of section titles / infobox field names.
Three tiers: (1) offline glossary, (2) multilingual embeddings (optional), (3) exact text."""
import re

from .glossary import GLOSSARY, REVERSE

_model = None


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model


def glossary_match(item, target_norm):
    """True if `item` has a known translation (either direction) or exact match in target."""
    n = norm(item)
    if n in target_norm:
        return True
    if any(v in t for v in GLOSSARY.get(n, []) for t in target_norm):
        return True
    return REVERSE.get(n) in target_norm if n in REVERSE else False


def missing_items(ref, target, threshold=0.55):
    """Embedding tier: items of `ref` with no semantically similar item in `target`."""
    from sentence_transformers import util
    m = _get_model()
    sim = util.cos_sim(m.encode(list(ref)), m.encode(list(target)))
    return [t for t, row in zip(ref, sim) if float(row.max()) < threshold]


def find_missing(ref, target, threshold=0.55):
    """Returns (missing_items, method_description). Never raises."""
    ref, target = list(ref or []), list(target or [])
    if not ref:
        return [], "nothing to compare"
    if not target:
        return ref, "target has none"
    tnorm = [norm(t) for t in target]
    remaining = [r for r in ref if not glossary_match(r, tnorm)]
    if not remaining:
        return [], "glossary"
    try:
        return missing_items(remaining, target, threshold), "glossary + embeddings"
    except Exception as e:  # not installed, offline model download failed, etc.
        why = "not installed" if isinstance(e, ImportError) else type(e).__name__
        return remaining, f"glossary + exact match only (embeddings unavailable: {why})"
