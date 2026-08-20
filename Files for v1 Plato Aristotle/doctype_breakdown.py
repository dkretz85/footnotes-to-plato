#!/usr/bin/env python3
"""Quick diagnostic: citation counts by doctype in citations.tsv, so we can
decide whether to include misc/book-review at all (a research-design choice
that also happens to remove the index-page contamination cleanly)."""
import sys, csv, collections
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
path = sys.argv[1] if len(sys.argv) > 1 else "citations.tsv"
by_dt = collections.Counter()
by_dt_corpus = collections.Counter()
total = 0
with open(path, encoding="utf-8") as fh:
    for row in csv.DictReader(fh, delimiter="\t"):
        dt = row.get("doctype","?") or "?"
        by_dt[dt] += 1
        by_dt_corpus[(dt,row.get("corpus","?"))] += 1
        total += 1
print(f"Total citation candidates: {total:,}\n")
print("By doctype:")
for dt,c in by_dt.most_common():
    print(f"  {dt:22s} {c:8,d}  ({c/total*100:5.1f}%)")
print("\nmisc + book-review combined:")
mb = by_dt.get("misc",0)+by_dt.get("book-review",0)
print(f"  {mb:,} ({mb/total*100:.1f}%) — what excluding them would remove")
