#!/usr/bin/env python3
"""
measure_density.py — THROWAWAY ANALYSIS (not part of the pipeline).

Measures the "numeric-token density" of every context window in citations.tsv,
so we can set the index/concordance-page filter threshold from DATA rather than
guesswork. Reports:
  - the density distribution (histogram)
  - what fraction of rows each candidate threshold would divert
  - random samples in each density band, so you can EYEBALL whether a band is
    mostly index-pages (safe to cut) or real footnote-citations (must spare)
  - a doctype breakdown of high-density rows (are these mostly old
    'misc'/'book-review' index pages? then doctype may be a cleaner signal)

Density = (# tokens that are citation-shaped or bare numbers) / (# all tokens)
in the context window. Real prose citations score low (mostly words); index /
concordance / apparatus pages score high (mostly numbers).

Usage:
    python3 measure_density.py citations.tsv [--samples 12]
"""

import sys, csv, re, argparse, collections, random

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

TOKEN = re.compile(r"[^\s,;]+")
# a token counts as "numeric-ish" if it is a bare number, a citation-shaped
# number, or a number with trailing letter / punctuation (185a, 378b, 330a,)
NUMISH = re.compile(r"^\(?\d+[a-eA-E]?\d*[.,;:)]*$")
# a CITATION-SHAPED token specifically: number + section/column letter, the
# thing our extractor matches. Counting these in a window is robust to
# word-dilution (place names, sigla) that defeats a pure ratio.
CITE_SHAPED = re.compile(r"\b\d+[a-eA-E]\d*\b")


def density(context):
    toks = TOKEN.findall(context)
    if not toks:
        return 0.0, 0
    num = sum(1 for t in toks if NUMISH.match(t))
    return num / len(toks), len(toks)


def cite_count(context):
    """How many citation-shaped tokens appear in the window. An index/
    concordance page has many; a real prose citation has 1-2."""
    return len(CITE_SHAPED.findall(context))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("citations")
    ap.add_argument("--samples", type=int, default=12)
    args = ap.parse_args()

    bands = [(0.0,0.3),(0.3,0.5),(0.5,0.7),(0.7,0.9),(0.9,1.01)]
    band_rows = {b: [] for b in bands}
    band_count = collections.Counter()
    doctype_hi = collections.Counter()   # doctype among density>=0.7
    total = 0
    thresholds = [0.5, 0.6, 0.7, 0.8, 0.9]
    over = collections.Counter()

    # citation-count signal (likely more robust than density)
    cite_hist = collections.Counter()        # capped bucket -> count
    cite_over = collections.Counter()         # threshold -> rows with >= that many
    cite_thresholds = [3, 4, 5, 6, 8, 10]
    cite_samples = collections.defaultdict(list)  # bucket -> samples

    with open(args.citations, encoding="utf-8") as fh:
        r = csv.DictReader(fh, delimiter="\t")
        for row in r:
            ctx = row.get("context", "")
            d, ntok = density(ctx)
            cc = cite_count(ctx)
            total += 1
            for t in thresholds:
                if d >= t:
                    over[t] += 1
            bucket = min(cc, 12)
            cite_hist[bucket] += 1
            for ct in cite_thresholds:
                if cc >= ct:
                    cite_over[ct] += 1
            if 3 <= cc and len(cite_samples[bucket]) < args.samples * 3:
                cite_samples[bucket].append((row.get("match",""),
                                             row.get("doctype",""), ctx[:150]))
            for b in bands:
                if b[0] <= d < b[1]:
                    band_count[b] += 1
                    if len(band_rows[b]) < args.samples * 4:
                        band_rows[b].append((row.get("match",""),
                                             row.get("doctype",""),
                                             ctx[:150]))
                    break
            if d >= 0.7:
                doctype_hi[row.get("doctype","?")] += 1

    print(f"Total rows: {total:,}\n")
    print("=== SIGNAL 1: citation-shaped tokens per context window ===")
    print("(an index/concordance page has many; a real citation has 1-2)")
    for k in sorted(cite_hist):
        label = f"{k}" if k < 12 else "12+"
        c = cite_hist[k]
        print(f"  {label:>3s} cite-tokens: {c:8,d}  ({c/total*100:5.1f}%)")
    print("\n  What each citation-count threshold would DIVERT:")
    for ct in cite_thresholds:
        print(f"    >= {ct:2d} cite-tokens: {cite_over[ct]:8,d}  "
              f"({cite_over[ct]/total*100:5.1f}% of all rows)")

    print("\n=== SIGNAL 2: numeric-token density ===")
    print("Density distribution:")
    for b in bands:
        c = band_count[b]
        print(f"  {b[0]:.1f}–{b[1]:.1f}: {c:8,d}  ({c/total*100:5.1f}%)")
    print("\n  What each density threshold would DIVERT:")
    for t in thresholds:
        print(f"    density >= {t:.1f}: {over[t]:8,d}  ({over[t]/total*100:5.1f}%)")

    print("\nDoctype among high-density (>=0.7) rows:")
    for dt, c in doctype_hi.most_common():
        print(f"  {dt:20s} {c:,}")

    print("\n" + "="*70)
    print("SAMPLES by citation-count bucket (match | doctype | context):")
    for k in sorted(cite_samples):
        rows = cite_samples[k]
        random.shuffle(rows)
        print(f"\n--- {k}{'+' if k>=12 else ''} cite-tokens in window ---")
        for m, dt, ctx in rows[:args.samples]:
            print(f"  [{m:8s}|{dt:16s}] {ctx}")


if __name__ == "__main__":
    main()
