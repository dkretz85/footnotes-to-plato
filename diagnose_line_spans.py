#!/usr/bin/env python3
"""
diagnose_line_spans.py — Homer/Pindar line-span distribution (RANGE handoff §5)

GATE diagnostic. Reads the harvested citations.tsv, isolates the `homer` and
`pindar` corpus rows, parses the LINE-range out of each match cell, and reports
the span-length distribution per author. The point is to choose a heatmap BIN
WIDTH before rewriting the parser: individual lines are almost certainly too
fine for a ~15k-line epic, and Pindar (short odes) probably wants a different,
finer bin than Homer. We pick a bin so a *typical* span touches ~2–4 cells.

Read-only, stdlib-only, streaming (bounded memory). Run locally:

    python3 diagnose_line_spans.py citations.tsv

Schema assumed (v2 citations.tsv, 11 cols):
    iid journal year doctype corpus page_index char_offset seq match context title
    0   1       2    3       4      5          6           7   8     9       10

We only touch columns 4 (corpus) and 8 (match).
"""
import sys, csv, re, statistics
from collections import Counter

# The csv module caps a single field at 131072 chars by default; a context
# window off a pathological (scanned-volume) page can exceed that and raise
# "field larger than field limit". Raise to the platform max so the reader
# never chokes mid-file. (Same guard resolve_citations.py uses.)
def _raise_csv_limit():
    lim = sys.maxsize
    while True:
        try:
            csv.field_size_limit(lim)
            break
        except OverflowError:
            lim = int(lim // 10)
_raise_csv_limit()

CORPUS_COL = 4
MATCH_COL  = 8
TARGET_CORPORA = ("homer", "pindar")

# The match cell is the WHOLE cue+number the extractor harvested, e.g.
#   "Il. 16.7-11"  "Iliad 16.7-11"  "Od. IV 1"  "Pyth. 4.162"  "Ol. 1.111-12"
# Book/ode may be Arabic or Roman; separators vary (dot/comma/space). We don't
# care about the book here — only the LINE part, which is the trailing numeric
# (optionally a range). Grab the LAST number-or-range token in the cell.
TRAILING_LINE = re.compile(r"(\d{1,4})(?:\s*[-–]\s*(\d{1,4}))?\s*$")


def span_length(match_cell):
    """Return the span length in lines for a match cell, or None if no line
    token can be parsed. A single line is length 1. Abbreviated trailing
    endpoints share the start's high-order digits: '111-12' -> 111..112 (=2),
    '7-11' -> 7..11 (=5), '804-8' -> 804..808 (=5)."""
    m = TRAILING_LINE.search(match_cell or "")
    if not m:
        return None
    start = int(m.group(1))
    if m.group(2) is None:
        return 1
    end_tok = m.group(2)
    end = int(end_tok)
    if end < start:
        # abbreviated endpoint: replace the last len(end_tok) digits of start
        scale = 10 ** len(end_tok)
        end = (start - start % scale) + end
    if end < start:
        return None  # still incoherent (e.g. genuine reversed range) -> skip
    return end - start + 1


def percentile(sorted_vals, q):
    """Nearest-rank percentile on a pre-sorted list. q in [0,100]."""
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = min(len(sorted_vals) - 1, max(0, round(q / 100 * (len(sorted_vals) - 1))))
    return sorted_vals[idx]


def histogram(spans):
    """Small bucketed histogram of span lengths."""
    buckets = [(1, 1), (2, 2), (3, 4), (5, 8), (9, 16), (17, 32), (33, 10**9)]
    labels  = ["1", "2", "3-4", "5-8", "9-16", "17-32", "33+"]
    counts = Counter()
    for s in spans:
        for (lo, hi), lab in zip(buckets, labels):
            if lo <= s <= hi:
                counts[lab] += 1
                break
    return [(lab, counts.get(lab, 0)) for lab in labels]


def report(author, spans, unparsed):
    total = len(spans) + unparsed
    print(f"\n=== {author.upper()}  (rows: {total:,}) ===")
    if not spans:
        print("  no parseable line spans.")
        if unparsed:
            print(f"  unparsed match cells: {unparsed:,}")
        return
    s = sorted(spans)
    print(f"  parseable spans : {len(spans):,}"
          + (f"   (unparsed: {unparsed:,})" if unparsed else ""))
    print(f"  min / median    : {s[0]}  /  {statistics.median(s):g}")
    print(f"  mean            : {statistics.mean(s):.2f}")
    print(f"  p90 / max       : {percentile(s, 90)}  /  {s[-1]}")
    singles = sum(1 for x in s if x == 1)
    print(f"  single-line     : {singles:,}  ({100*singles/len(s):.1f}%)")
    print(f"  histogram (lines per span):")
    width = max(n for _, n in histogram(spans)) or 1
    for lab, n in histogram(spans):
        bar = "#" * int(40 * n / width)
        print(f"    {lab:>6} | {n:6,} {bar}")


def main():
    if len(sys.argv) < 2:
        print("usage: python3 diagnose_line_spans.py citations.tsv")
        sys.exit(1)
    path = sys.argv[1]
    spans = {a: [] for a in TARGET_CORPORA}
    unparsed = {a: 0 for a in TARGET_CORPORA}
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        r = csv.reader(fh, delimiter="\t")
        next(r, None)  # header
        for row in r:
            if len(row) <= MATCH_COL:
                continue
            corpus = row[CORPUS_COL]
            if corpus not in spans:
                continue
            length = span_length(row[MATCH_COL])
            if length is None:
                unparsed[corpus] += 1
            else:
                spans[corpus].append(length)
    for a in TARGET_CORPORA:
        report(a, spans[a], unparsed[a])
    print("\nDecision rule (RANGE §5): pick a bin so a TYPICAL span touches "
          "~2-4 cells — i.e. bin ≈ median span / 3, rounded to something clean. "
          "Homer and Pindar are set independently.")


if __name__ == "__main__":
    main()
