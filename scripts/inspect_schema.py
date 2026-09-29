"""Print the structure of the first record of a shard, to verify field names.
Usage: python scripts/inspect_schema.py data/en/enwiki_namespace_0_0.jsonl"""
import gzip
import json
import sys


def show(obj, depth=0, maxdepth=3):
    pad = "  " * depth
    if isinstance(obj, dict):
        for k, v in obj.items():
            print(f"{pad}{k}: {type(v).__name__}")
            if depth < maxdepth:
                show(v, depth + 1, maxdepth)
    elif isinstance(obj, list) and obj and depth < maxdepth:
        print(f"{pad}[0] of {len(obj)}")
        show(obj[0], depth + 1, maxdepth)


path = sys.argv[1]
opener = gzip.open if path.endswith(".gz") else open
with opener(path, "rt", encoding="utf-8") as f:
    show(json.loads(f.readline()))
