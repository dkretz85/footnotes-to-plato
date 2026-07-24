#!/usr/bin/env python3
"""
estimate_within_set.py — the "best guess" test for the fade tick, run BEFORE
building any UI. Decides whether a within-set proportional estimate lands far
enough from the floor to be worth showing.

THE ESTIMATOR (within-set proportional). Each queued citation is split among
ONLY the works in its own candidate set, in proportion to those works' resolved
(floor) counts:

    share(w | C) = floor[w] / sum_{v in C} floor[v]
    estimate[w]  = floor[w] + sum_{rows c with w in C(c)} share(w | C(c))

Not uniform (which ignores that `327d` is overwhelmingly Republic, not Letters)
and not global-proportional (which ignores the constraint the collision supplies).

ALLOCATION IS EXCLUSIVE. Every allocatable queued citation is distributed exactly
once, so the estimates sum to floor_total + (allocatable rows) — unlike the fade,
which multi-counts candidate-set membership on purpose.

WHAT COUNTS AS ALLOCATABLE. Candidate-bearing rows are split within their set.
Scope-fallback rows (a bare number that inherited one named work, no candidate
list) go entirely to that one work. `scope_range_mismatch` rows are CONFIDENT
NEGATIVES — a work proven NOT to own the page — and are excluded, exactly as the
fade excludes them. So the sanity total is:

    sum(estimate) == floor_total + total_queued   (both from meta.json)
                  == 90,502 + 46,782 == 137,284    (July 2026 delivery)

NOT 90,502 + 50,450: that 50,450 re-includes the ~3,668 confident negatives the
fade drops. If your run sums to ~141k you are allocating the negatives.

Reuses the pipeline's own column layout and candidate parser so the sets are
identical to the ones that drive `collides_with` and the fade.

Usage:
    python3 estimate_within_set.py                 # defaults to ~/Downloads
    python3 estimate_within_set.py --tsv R.tsv --queue Q.tsv --csv out.csv
"""
import argparse
import csv
import sys
from collections import Counter

import build_viewer_data as bvd


def load_floors(tsv_path):
    floors = Counter()
    with open(tsv_path, encoding="utf-8", newline="") as f:
        r = csv.reader(f, delimiter="\t")
        for row in r:
            if len(row) <= bvd.C_WORK or not row[bvd.C_WORK]:
                continue
            floors[row[bvd.C_WORK]] += 1
    return floors


def allocate(queue_path, floors):
    """Distribute each allocatable queued citation within its candidate set."""
    add = Counter()          # fractional credit added on top of the floor
    stats = Counter()
    with open(queue_path, encoding="utf-8", newline="") as f:
        r = csv.reader(f, delimiter="\t")
        for row in r:
            if len(row) <= bvd.C_WORK or not row[bvd.C_WORK]:
                stats["blank"] += 1
                continue
            method = row[bvd.C_METHOD] if len(row) > bvd.C_METHOD else ""
            if method in bvd.SCOPE_METHODS_EXCLUDED:
                stats["confident_negative_excluded"] += 1
                continue
            reason = row[bvd.C_REASON] if len(row) > bvd.C_REASON else ""
            cands = sorted(set(bvd.parse_candidates(reason)))
            if not cands:
                # scope fallback: one named work inherited, no candidate list.
                cands = [row[bvd.C_WORK]]
                stats["scope_fallback"] += 1
            else:
                stats["candidate_bearing"] += 1
            total = sum(floors.get(w, 0) for w in cands)
            if total > 0:
                for w in cands:
                    add[w] += floors.get(w, 0) / total
            else:
                # every candidate has a zero floor (e.g. deep spuria) — fall back
                # to uniform so the citation is not silently dropped.
                for w in cands:
                    add[w] += 1.0 / len(cands)
            stats["allocated"] += 1
    return add, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tsv", default=bvd.DEF_TSV, help="resolved_with_books.tsv")
    ap.add_argument("--queue", default=bvd.DEF_QUEUE, help="review_queue.tsv")
    ap.add_argument("--double-threshold", type=float, default=2.0,
                    help="flag works whose estimate exceeds this * floor")
    ap.add_argument("--csv", default=None, help="also write the table to CSV")
    args = ap.parse_args()

    floors = load_floors(args.tsv)
    add, stats = allocate(args.queue, floors)

    rows = []
    for w in sorted(floors, key=lambda w: -floors[w]):
        fl = floors[w]
        est = fl + add.get(w, 0.0)
        rows.append((w, fl, est, (est / fl if fl else float("inf"))))

    # ---- table -------------------------------------------------------------
    print(f"{'work':<26}{'floor':>8}{'estimate':>11}{'ratio':>8}")
    print("-" * 53)
    for w, fl, est, ratio in rows:
        print(f"{w:<26}{fl:>8,}{est:>11,.0f}{ratio:>8.2f}")

    # ---- sanity checks -----------------------------------------------------
    floor_total = sum(floors.values())
    est_total = floor_total + sum(add.values())
    expected = floor_total + stats["allocated"]
    print("\n--- sanity ---")
    print(f"floor total                : {floor_total:,}")
    print(f"allocated queued citations : {stats['allocated']:,}"
          f"  (candidate-bearing {stats['candidate_bearing']:,} + "
          f"scope-fallback {stats['scope_fallback']:,})")
    print(f"confident negatives excluded: {stats['confident_negative_excluded']:,}"
          f"   blanks: {stats['blank']:,}")
    print(f"sum of estimates           : {est_total:,.1f}")
    print(f"expected (floor+allocated) : {expected:,}"
          f"   {'OK' if abs(est_total - expected) < 1 else 'MISMATCH'}")
    print(f"  (compare against meta.json floor_total + total_queued; if you see "
          f"~141k you are re-including the confident negatives.)")

    # ---- decision signals --------------------------------------------------
    doubled = [r for r in rows if r[1] and r[2] > args.double_threshold * r[1]]
    print(f"\n--- works whose estimate > {args.double_threshold:g}x floor "
          f"({len(doubled)}) ---")
    for w, fl, est, ratio in sorted(doubled, key=lambda r: -r[3]):
        print(f"  {w:<26} floor {fl:>7,}  ->  {est:>8,.0f}   ({ratio:.2f}x)")

    tim = next((r for r in rows if r[0] == "Timaeus"), None)
    if tim:
        print("\n--- bias probe (Timaeus) ---")
        print(f"  floor {tim[1]:,}  estimate {tim[2]:,.0f}  ratio {tim[3]:.2f}")
        print("  Timaeus appears in ~13.9k candidate sets. If the estimate sits "
              "near the floor,\n  that is the self-reinforcing bias, not a "
              "finding: read it as a warning, not a result.")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            wtr = csv.writer(f)
            wtr.writerow(["work", "floor", "within_set_estimate", "ratio"])
            for w, fl, est, ratio in rows:
                wtr.writerow([w, fl, round(est, 2), round(ratio, 4)])
        print(f"\nwrote {args.csv}", file=sys.stderr)


if __name__ == "__main__":
    main()
