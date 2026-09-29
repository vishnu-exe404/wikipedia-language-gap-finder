"""Read Kaggle shards (JSONL / NDJSON / JSON array, optionally .gz) into {key: compact record}."""
import glob
import gzip
import json
import os

from .metrics import compact

PATTERNS = ("*.jsonl", "*.ndjson", "*.json", "*.jsonl.gz", "*.ndjson.gz", "*.json.gz")


def find_files(source):
    """`source` may be a folder (every shard inside is used), a glob pattern, or one file."""
    source = os.path.expanduser(source.strip())
    if os.path.isdir(source):
        files = []
        for pat in PATTERNS:
            files += glob.glob(os.path.join(source, "**", pat), recursive=True)
        return sorted(set(files))
    return sorted(glob.glob(source))


def _open(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, encoding="utf-8", errors="replace")


def iter_records(path):
    """Yield raw article dicts from one shard (JSON Lines, or a single JSON array)."""
    with _open(path) as fh:
        first = fh.readline()
        while first and not first.strip():
            first = fh.readline()
        if not first:
            return
        if first.lstrip().startswith("["):
            data = json.loads(first + fh.read())
            yield from data
            return
        lines = [first]
        while True:
            for line in lines:
                line = line.strip()
                if line:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        pass
            lines = fh.readlines(1 << 20)  # read ~1 MB of lines at a time
            if not lines:
                return


def load_index(source, max_articles=100000, only_qids=None):
    """Stream every shard. `only_qids` keeps only articles with those Wikidata IDs."""
    files = find_files(source)
    if not files:
        raise FileNotFoundError(f"No shard files found at: {source}")
    idx = {}
    for path in files:
        for raw in iter_records(path):
            rec = compact(raw)
            if not rec:
                continue
            if only_qids is not None and rec["qid"] not in only_qids:
                continue
            idx[rec["key"]] = rec
            if len(idx) >= max_articles:
                return idx
    return idx
