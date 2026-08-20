#!/usr/bin/env python3
"""
find_titles.py — dump the exact journal-title strings JSTOR uses, for any
title containing one of our probe fragments. Run this to discover the real
spellings before committing them to the survey script.

Usage:
    python3 find_titles.py jstor_metadata_2026-07-18.jsonl.gz
"""
import sys, json, gzip, io, collections, unicodedata

# Fragments to hunt for — lowercased, accent-stripped substring match so we
# catch things regardless of umlauts / diacritics / casing.
FRAGMENTS = [
    "apeiron", "phronesis", "ancient philosophy", "methexis",
    "philosophie ancienne", "archiv", "geschichte der philosophie",
    "classical quarterly", "classical philology", "classical review",
    "ancient", "philosoph",   # broad nets — will catch extra, that's fine
]

def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))

def norm(s):
    return strip_accents(str(s)).lower()

def open_stream(path):
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")

def main():
    path = sys.argv[1]
    hits = collections.Counter()   # exact title string -> count
    with open_stream(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            j = rec.get("is_part_of")
            if not j:
                continue
            jn = norm(j)
            if any(f in jn for f in FRAGMENTS):
                hits[j] += 1

    print(f"{'COUNT':>8}  TITLE  (exact string in file)")
    print("=" * 70)
    for title, n in sorted(hits.items(), key=lambda kv: -kv[1]):
        # show a repr so hidden/odd whitespace becomes visible
        print(f"{n:8,d}  {title!r}")

if __name__ == "__main__":
    main()
