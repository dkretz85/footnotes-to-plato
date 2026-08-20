#!/usr/bin/env python3
"""Dump the top-level keys of the first few metadata records so we can find
the article-title field's exact name. Run against the metadata .gz."""
import sys, json, gzip, io
path = sys.argv[1] if len(sys.argv) > 1 else "jstor_metadata_2026-07-18.jsonl.gz"
def op(p):
    return io.TextIOWrapper(gzip.open(p,"rb"),encoding="utf-8",errors="replace") if p.endswith(".gz") else open(p,encoding="utf-8")
with op(path) as fh:
    for i, line in enumerate(fh):
        line=line.strip()
        if not line: continue
        rec=json.loads(line)
        print(f"--- record {i} keys ---")
        for k in sorted(rec.keys()):
            v = rec[k]
            s = str(v)
            print(f"  {k:24s} = {s[:80]}")
        if i>=2: break
