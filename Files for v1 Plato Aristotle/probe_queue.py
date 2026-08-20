#!/usr/bin/env python3
"""
probe_queue.py — profile the review queue so we can set the floor/ceiling rule
on evidence, not guesswork.

For each work it reports:
  - resolved count (the floor), from resolved_with_books.tsv
  - total queued rows, from review_queue.tsv
  - queued broken down by `reason`
  - queued broken down by confidence band
  - a cross-tab of reason x confidence for the whole queue

The question we're answering: is the queue mostly "soft-but-plausible"
(name_range_conflict, decent confidence -> belongs to its guessed work) or
mostly "genuinely unknown" (unresolved, low confidence -> shouldn't inflate any
one work's ceiling)? The answer sets where we draw the confidence interval.

Inputs default to ~/Downloads. Both files share the same leading columns; the
queue has one extra trailing column, `reason`.

    resolved_with_books.tsv : iid journal year doctype corpus page_index seq
                              match work_id book confidence method context
    review_queue.tsv        : ...same 13... + reason

Usage:
    python3 probe_queue.py
    python3 probe_queue.py --resolved /path/to.tsv --queue /path/to.tsv
    python3 probe_queue.py --top 25        # show this many works (default 20)
"""
import sys, os, csv, argparse
from collections import Counter, defaultdict

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))  # context can be large

HOME = os.path.expanduser("~")
DEF_RESOLVED = os.path.join(HOME, "Downloads", "resolved_with_books.tsv")
DEF_QUEUE    = os.path.join(HOME, "Downloads", "review_queue.tsv")

# shared column indices (zero-based)
C_WORK, C_CONF, C_METHOD = 8, 10, 11
C_REASON = 13   # queue-only trailing column

# confidence bands for bucketing
def conf_band(c):
    try:
        x = float(c)
    except (TypeError, ValueError):
        return "n/a"
    if x >= 0.90: return "0.90-1.00"
    if x >= 0.70: return "0.70-0.89"
    if x >= 0.50: return "0.50-0.69"
    if x >= 0.30: return "0.30-0.49"
    return "0.00-0.29"

BAND_ORDER = ["0.90-1.00","0.70-0.89","0.50-0.69","0.30-0.49","0.00-0.29","n/a"]


def count_resolved(path):
    counts = Counter()
    if not os.path.exists(path):
        print(f"  WARNING: resolved file not found: {path}", file=sys.stderr)
        return counts
    with open(path, encoding="utf-8", newline="") as fh:
        r = csv.reader(fh, delimiter="\t")
        next(r, None)
        for row in r:
            if len(row) > C_WORK and row[C_WORK]:
                counts[row[C_WORK]] += 1
    return counts


def profile_queue(path):
    per_work_total = Counter()
    per_work_reason = defaultdict(Counter)      # work -> reason -> n
    per_work_band = defaultdict(Counter)        # work -> conf band -> n
    global_reason = Counter()
    global_band = Counter()
    reason_x_band = defaultdict(Counter)        # reason -> band -> n
    if not os.path.exists(path):
        print(f"  WARNING: queue file not found: {path}", file=sys.stderr)
        return (per_work_total, per_work_reason, per_work_band,
                global_reason, global_band, reason_x_band)
    with open(path, encoding="utf-8", newline="") as fh:
        r = csv.reader(fh, delimiter="\t")
        header = next(r, None)
        for row in r:
            if len(row) <= C_WORK or not row[C_WORK]:
                continue
            work = row[C_WORK]
            conf = row[C_CONF] if len(row) > C_CONF else ""
            reason = row[C_REASON] if len(row) > C_REASON else "(none)"
            band = conf_band(conf)
            per_work_total[work] += 1
            per_work_reason[work][reason] += 1
            per_work_band[work][band] += 1
            global_reason[reason] += 1
            global_band[band] += 1
            reason_x_band[reason][band] += 1
    return (per_work_total, per_work_reason, per_work_band,
            global_reason, global_band, reason_x_band)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resolved", default=DEF_RESOLVED)
    ap.add_argument("--queue", default=DEF_QUEUE)
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args()

    print("Reading resolved counts ...", file=sys.stderr)
    resolved = count_resolved(args.resolved)
    print("Profiling review queue ...", file=sys.stderr)
    (qtotal, qreason, qband, greason, gband, rxb) = profile_queue(args.queue)

    # ---- global picture ----------------------------------------------------
    total_q = sum(qtotal.values())
    total_r = sum(resolved.values())
    print("\n" + "="*70)
    print("GLOBAL")
    print("="*70)
    print(f"resolved citations : {total_r:,}")
    print(f"queued citations   : {total_q:,}")

    print("\nQueued by reason:")
    for reason, n in greason.most_common():
        print(f"  {n:8,}  {n/total_q:5.1%}  {reason}")

    print("\nQueued by confidence band:")
    for band in BAND_ORDER:
        if gband.get(band):
            n = gband[band]
            print(f"  {n:8,}  {n/total_q:5.1%}  {band}")

    print("\nReason x confidence-band cross-tab (queued rows):")
    reasons_sorted = [r for r, _ in greason.most_common()]
    hdr = "reason \\ band".ljust(24) + "".join(b.rjust(11) for b in BAND_ORDER)
    print("  " + hdr)
    for reason in reasons_sorted:
        line = reason[:23].ljust(24) + "".join(
            (f"{rxb[reason].get(b,0):,}").rjust(11) for b in BAND_ORDER)
        print("  " + line)

    # ---- per-work picture --------------------------------------------------
    # rank works by queued volume (that's where the ceiling question bites)
    print("\n" + "="*70)
    print(f"PER-WORK (top {args.top} by queued volume)")
    print("="*70)
    print(f"{'work':24s} {'resolved':>9s} {'queued':>8s} "
          f"{'q>=.50':>8s} {'q<.50':>8s}  dominant reason")
    print("-"*78)
    ranked = sorted(qtotal.items(), key=lambda kv: -kv[1])[:args.top]
    for work, q in ranked:
        r = resolved.get(work, 0)
        # split queued into "plausible" (>=0.50) vs "soft" (<0.50)
        hi = sum(n for b, n in qband[work].items()
                 if b in ("0.90-1.00","0.70-0.89","0.50-0.69"))
        lo = q - hi
        dom = qreason[work].most_common(1)
        dom_s = f"{dom[0][0]} ({dom[0][1]:,})" if dom else "-"
        print(f"{work[:24]:24s} {r:9,} {q:8,} {hi:8,} {lo:8,}  {dom_s}")

    print("\nInterpretation guide:")
    print("  q>=.50  = queued rows we'd plausibly fold into the ceiling band")
    print("  q<.50   = softer/unresolved; likely to inflate a single work's")
    print("            ceiling dishonestly if summed in")
    print("  If most queued volume sits in q>=.50 with reason=name_range_conflict,")
    print("  a confidence threshold cleanly separates 'plausible band' from noise.")
    print()


if __name__ == "__main__":
    main()
