#!/usr/bin/env python3
"""Confirm the 'title' field is populated for research-article / book-review
records (the community-collection records at the top of the file have title=None,
but journal articles should have real titles). Streams until it finds some.

Usage: python3 probe_titles.py jstor_metadata_2026-07-18.jsonl.gz
"""
import sys, json, gzip, io
path = sys.argv[1] if len(sys.argv) > 1 else "jstor_metadata_2026-07-18.jsonl.gz"
def op(p):
    return io.TextIOWrapper(gzip.open(p,"rb"),encoding="utf-8",errors="replace") if p.endswith(".gz") else open(p,encoding="utf-8")
seen = 0
with_title = 0
shown = 0
with op(path) as fh:
    for line in fh:
        line=line.strip()
        if not line: continue
        try: rec=json.loads(line)
        except: continue
        st = rec.get("content_subtype","")
        if st in ("research-article","book-review","journal_article") or (rec.get("is_part_of") and rec.get("title")):
            seen += 1
            if rec.get("title"):
                with_title += 1
                if shown < 12:
                    print(f"[{st}] {str(rec.get('title'))[:90]}")
                    shown += 1
            if seen >= 5000:
                break
print(f"\nOf {seen:,} journal-ish records scanned, {with_title:,} had a non-null title.")
