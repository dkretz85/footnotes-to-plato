#!/usr/bin/env python3
"""
work_resolution_rates.py — per-work diagnostic answering: "is ambiguity
non-random? do specific works end up unresolved more often, leaving soft
spots in the heatmap?"

Reads resolved.tsv and review_queue.tsv (and optionally excluded.tsv for
context) and reports, per work_id:
  - resolved count      (auto-accepted)
  - queued count        (went to review)
  - resolution rate     = resolved / (resolved + queued)
  - dominant queue reason for that work

A LOW resolution rate for a work means the pre-cleanup heatmap under-counts
it — those cells need a caveat until the manual pass fills them. A work with
high volume AND low rate is the priority for review-queue triage.

Note on attribution: queued rows carry only a BEST-GUESS work_id (the resolver's
top candidate), so per-work queue counts are approximate for unresolved rows.
We report both a 'confident' view (resolved rows, work_id is real) and a
'queue-attributed' view (queue rows by their guessed work_id), and flag the
distinction rather than blurring it.

Usage:
    python3 work_resolution_rates.py \\
        [--resolved resolved.tsv] [--queue review_queue.tsv] \\
        [--min-total 20]
"""

import csv, sys, argparse, collections

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def read_tsv(path):
    try:
        with open(path, encoding="utf-8") as fh:
            yield from csv.DictReader(fh, delimiter="\t")
    except FileNotFoundError:
        return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resolved", default="resolved.tsv")
    ap.add_argument("--queue", default="review_queue.tsv")
    ap.add_argument("--min-total", type=int, default=20,
                    help="only show works with at least this many total candidates")
    args = ap.parse_args()

    resolved = collections.Counter()      # work_id -> resolved count (real)
    queued   = collections.Counter()      # work_id -> queued count (best-guess)
    queue_reason = collections.defaultdict(collections.Counter)
    corpus_of = {}                        # work_id -> corpus (for grouping)

    for row in read_tsv(args.resolved):
        wid = row.get("work_id") or "(none)"
        resolved[wid] += 1
        corpus_of.setdefault(wid, row.get("corpus", "?"))

    for row in read_tsv(args.queue):
        wid = row.get("work_id") or "(none)"
        queued[wid] += 1
        queue_reason[wid][row.get("reason", "?")] += 1
        corpus_of.setdefault(wid, row.get("corpus", "?"))

    works = set(resolved) | set(queued)
    rows = []
    for w in works:
        r = resolved[w]; q = queued[w]; tot = r + q
        if tot < args.min_total:
            continue
        rate = r / tot if tot else 0.0
        top_reason = queue_reason[w].most_common(1)
        top_reason = top_reason[0][0] if top_reason else ""
        rows.append((w, corpus_of.get(w, "?"), r, q, tot, rate, top_reason))

    # sort by resolution rate ascending — worst (softest heatmap spots) first
    rows.sort(key=lambda x: (x[5], -x[4]))

    print(f"{'work':26s} {'corpus':10s} {'resolv':>7s} {'queued':>7s} "
          f"{'total':>7s} {'rate':>6s}  top_queue_reason")
    print("-" * 100)
    for w, c, r, q, tot, rate, reason in rows:
        reason_short = reason[:46]
        print(f"{w:26s} {c:10s} {r:7d} {q:7d} {tot:7d} {rate:6.1%}  {reason_short}")

    # write a tsv too
    with open("work_resolution_rates.tsv", "w", encoding="utf-8", newline="") as o:
        wr = csv.writer(o, delimiter="\t")
        wr.writerow(["work_id","corpus","resolved","queued","total",
                     "resolution_rate","top_queue_reason"])
        for w, c, r, q, tot, rate, reason in rows:
            wr.writerow([w, c, r, q, tot, f"{rate:.4f}", reason])

    # headline: overall + the works most in need of review (high vol, low rate)
    tot_r = sum(resolved.values()); tot_q = sum(queued.values())
    denom = tot_r + tot_q
    print("-" * 100)
    if denom:
        print(f"overall genuine resolution rate: {tot_r/denom:.1%} "
              f"({tot_r:,} resolved / {denom:,} genuine)")
    print("\nPriority for review (high volume, low resolution rate):")
    priority = sorted(rows, key=lambda x: (x[5], -x[4]))[:12]
    for w, c, r, q, tot, rate, reason in priority:
        print(f"  {w:26s} {rate:5.1%}  ({q:,} queued of {tot:,})")

    print("\nWrote work_resolution_rates.tsv")


if __name__ == "__main__":
    main()
