#!/usr/bin/env python3
"""
probe_misc.py — characterise the 'misc' doctype bucket so we can decide,
on evidence, whether to include / exclude / subdivide it. Reads citations.tsv.

Reports for misc (and separately book-review, for comparison):
  - distribution over time (by decade)
  - top journals
  - fraction that look like INDEX/apparatus pages vs clean prose citations,
    using the citation-crowding + colon-locator signals
  - a RANDOM sample of contexts (not cherry-picked) to eyeball

Usage: python3 probe_misc.py [citations.tsv] [--doctype misc] [--samples 25]
"""
import sys, csv, re, argparse, collections, random
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

CITE_SHAPED = re.compile(r"\b\d+[a-eA-E]\d*\b")
# index locator signature: 'work-ish page: number' — a citation followed by
# ': digits' (the in-book page locator typical of back-of-book indices)
COLON_LOCATOR = re.compile(r"\d+[a-eA-E]?\s*:\s*\d")

def looks_index(ctx):
    n_cites = len(CITE_SHAPED.findall(ctx))
    has_locator = bool(COLON_LOCATOR.search(ctx))
    # heuristic label only, for measurement — NOT the production filter
    return n_cites >= 5 or has_locator

def decade(y):
    try:
        return f"{int(str(y)[:4])//10*10}s"
    except Exception:
        return "?"

ap = argparse.ArgumentParser()
ap.add_argument("citations", nargs="?", default="citations.tsv")
ap.add_argument("--doctype", default="misc")
ap.add_argument("--samples", type=int, default=25)
args = ap.parse_args()

by_decade = collections.Counter()
by_journal = collections.Counter()
n = idx_like = 0
samples = []
with open(args.citations, encoding="utf-8") as fh:
    for row in csv.DictReader(fh, delimiter="\t"):
        if (row.get("doctype","") or "") != args.doctype:
            continue
        n += 1
        by_decade[decade(row.get("year",""))] += 1
        by_journal[row.get("journal","?")] += 1
        if looks_index(row.get("context","")):
            idx_like += 1
        if len(samples) < args.samples * 8:
            samples.append((row.get("journal","?"), row.get("year",""),
                            row.get("match",""), row.get("context","")[:160]))

print(f"doctype='{args.doctype}': {n:,} citation candidates")
if not n:
    sys.exit()
print(f"index-like (crowded or colon-locator): {idx_like:,} ({idx_like/n*100:.1f}%)")
print(f"prose-like (the rest):                 {n-idx_like:,} ({(n-idx_like)/n*100:.1f}%)")
print("\nBy decade:")
for d,c in sorted(by_decade.items()):
    bar = "#"*int(c/n*60)
    print(f"  {d:6s} {c:7,d}  {bar}")
print("\nTop 15 journals:")
for j,c in by_journal.most_common(15):
    print(f"  {c:7,d}  {j}")
print("\n" + "="*70)
print(f"RANDOM sample of {args.samples} '{args.doctype}' contexts:")
random.shuffle(samples)
for j,y,m,ctx in samples[:args.samples]:
    print(f"\n  [{y} | {m:8s} | {j[:30]}]")
    print(f"    {ctx}")
