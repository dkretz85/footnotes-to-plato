#!/usr/bin/env python3
"""
dump_rates.py — emit per-work resolution rate + est_true for the text-level view.

If you already have work_resolution_rates.tsv, just paste that instead; this is
only for regenerating it from resolved.tsv + review_queue.tsv.

Usage:
    python3 dump_rates.py resolved.tsv review_queue.tsv

Prints, per work:  resolved  queued  total  rate  est_true(=resolved/rate)
sorted by est_true desc. Rate = resolved / (resolved + queued).

Assumes both files share the work_id column (index 8 in resolved.tsv). If
review_queue.tsv has a different layout, paste its header and Claude will adjust.
"""
import sys, csv, collections

def count_by_work(path, work_col_hint="work_id"):
    f = open(path, encoding="utf-8", newline="")
    r = csv.reader(f, delimiter="\t")
    header = next(r)
    lower = [h.strip().lower() for h in header]
    # find work column
    wi = None
    for i, h in enumerate(lower):
        if h in ("work_id", "work", "dialogue", "treatise"):
            wi = i; break
    if wi is None:
        sys.exit(f"no work column in {path}; header={header}")
    c = collections.Counter()
    for row in r:
        if len(row) > wi and row[wi].strip():
            c[row[wi]] += 1
    f.close()
    return c

def main():
    if len(sys.argv) < 3:
        print("usage: python3 dump_rates.py resolved.tsv review_queue.tsv"); sys.exit()
    res = count_by_work(sys.argv[1])
    que = count_by_work(sys.argv[2])
    works = set(res) | set(que)
    rows = []
    for w in works:
        r = res.get(w, 0); q = que.get(w, 0); tot = r + q
        rate = r / tot if tot else 0.0
        est = r / rate if rate else 0.0
        rows.append((w, r, q, tot, rate, est))
    rows.sort(key=lambda x: -x[5])
    print(f"{'work':<28} {'resolved':>8} {'queued':>7} {'total':>7} {'rate':>6} {'est_true':>9}")
    for w, r, q, tot, rate, est in rows:
        print(f"{w:<28} {r:>8,} {q:>7,} {tot:>7,} {rate:>6.1%} {est:>9,.0f}")

if __name__ == "__main__":
    main()
