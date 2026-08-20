#!/usr/bin/env python3
"""
missingness.py — is the UNRESOLVED (queued) set randomly distributed within
each work, or patterned? This determines what the heatmap can claim.

For each work, compare the page-distribution of RESOLVED vs QUEUED citations.
  - If resolved and queued citations cover the same pages in similar proportion,
    missingness is ~random: the within-work heatmap shape is trustworthy, and
    cross-work totals can be recovered by dividing by the resolution rate.
  - If queued citations CLUSTER on particular pages (typically pages that
    collide with other works' ranges), those specific cells are under-counted
    and need caveats.

Method: for each work, bin citations by Bekker/Stephanus page into coarse bins,
compute the resolved-share per bin, and report the spread. A work whose queued
citations are concentrated in a few bins gets flagged.

Also reports, per work: resolved, queued, resolution rate, and the estimated
TRUE volume (resolved / rate) for honest cross-work comparison.

Usage: python3 missingness.py [--resolved resolved.tsv] [--queue review_queue.tsv]
"""
import sys, csv, re, argparse, collections
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

def page_of(match):
    m = re.match(r"\d+", match)
    return int(m.group()) if m else None

def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            yield from csv.DictReader(fh, delimiter="\t")
    except FileNotFoundError:
        return

ap = argparse.ArgumentParser()
ap.add_argument("--resolved", default="resolved.tsv")
ap.add_argument("--queue", default="review_queue.tsv")
ap.add_argument("--min-total", type=int, default=200)
ap.add_argument("--bin", type=int, default=10, help="page bin width")
ap.add_argument("--flag-gap", type=float, default=0.15,
                help="report EVERY band whose resolved-share falls this far "
                     "below the work's average rate (default 0.15 = 15pp)")
ap.add_argument("--min-bin-vol", type=int, default=30,
                help="ignore bands with fewer than this many total citations "
                     "(too few to claim a pattern responsibly)")
args = ap.parse_args()

# per work: resolved pages, queued pages
res_pages = collections.defaultdict(list)
que_pages = collections.defaultdict(list)

for row in read(args.resolved):
    w = row.get("work_id") or "?"
    p = page_of(row.get("match",""))
    if p is not None:
        res_pages[w].append(p)
for row in read(args.queue):
    w = row.get("work_id") or "?"
    p = page_of(row.get("match",""))
    if p is not None:
        que_pages[w].append(p)

works = sorted(set(res_pages) | set(que_pages))
B = args.bin

rows = []
for w in works:
    r = res_pages[w]; q = que_pages[w]
    tot = len(r) + len(q)
    if tot < args.min_total:
        continue
    rate = len(r)/tot if tot else 0
    def binned(pages):
        c = collections.Counter(p//B for p in pages)
        return c
    rb, qb = binned(r), binned(q)
    allbins = set(rb) | set(qb)

    # Collect EVERY band that is materially under-resolved relative to this
    # work's own average rate — not just the single worst. A band is flagged
    # only if it has enough volume to claim a pattern responsibly (min-bin-vol)
    # AND its resolved-share sits >= flag-gap below the work average.
    flagged = []
    for b in sorted(allbins):
        bt = rb.get(b,0) + qb.get(b,0)
        if bt < args.min_bin_vol:
            continue
        bshare = rb.get(b,0)/bt
        gap = rate - bshare
        if gap >= args.flag_gap:
            flagged.append({
                "band": (b*B, b*B+B-1),
                "gap": gap,
                "vol": bt,
                "resolved_share": bshare,
                # citations we likely FAILED to resolve in this band, estimated
                # as the shortfall against the work's own average rate:
                "est_missing": round(bt * gap),
            })
    # A work is "uniformly hard" (low rate everywhere) vs "locally collided"
    # (a few bad bands in an otherwise fine work). Distinguish them so the UI
    # doesn't shade a whole low-rate work as if it had a localized problem.
    n_flagged = len(flagged)
    flagged_vol = sum(f["vol"] for f in flagged)
    total_missing_in_flagged = sum(f["est_missing"] for f in flagged)
    rows.append({
        "work": w, "res": len(r), "que": len(q), "rate": rate,
        "flagged": flagged, "n_flagged": n_flagged,
        "flagged_vol": flagged_vol, "est_missing": total_missing_in_flagged,
    })

# order: works with the most estimated-missing citations in flagged bands first
rows.sort(key=lambda d: -d["est_missing"])

import json

# ---- human-readable report --------------------------------------------------
print(f"Flagging every {B}-page band whose resolved-share is >= "
      f"{args.flag_gap:.0%} below its work's average rate, among bands with "
      f">= {args.min_bin_vol} citations.\n")
print(f"{'work':26s} {'rate':>5s} {'#bands':>6s} {'est_missing':>11s}")
print("-"*52)
for d in rows:
    if d["n_flagged"] == 0:
        continue
    print(f"{d['work']:26s} {d['rate']:5.0%} {d['n_flagged']:6d} {d['est_missing']:11d}")

print("\nPer-band detail (the caveat set the interface will shade):\n")
print(f"{'work':26s} {'band':>10s} {'vol':>5s} {'res_share':>9s} {'gap':>5s} {'est_miss':>8s}")
print("-"*72)
band_table = []
for d in rows:
    for f in d["flagged"]:
        lo, hi = f["band"]
        print(f"{d['work']:26s} {lo:>4d}-{hi:<4d} {f['vol']:5d} "
              f"{f['resolved_share']:9.0%} {f['gap']:5.0%} {f['est_missing']:8d}")
        band_table.append({
            "work": d["work"], "band_start": lo, "band_end": hi,
            "resolved_share": round(f["resolved_share"], 3),
            "gap": round(f["gap"], 3), "band_volume": f["vol"],
            "est_missing": f["est_missing"],
        })

# works with NO flagged bands: their within-work heatmaps are trustworthy end
# to end. List them explicitly — an affirmative "these are clean" statement is
# as important for the community as the caveats.
clean = [d["work"] for d in rows if d["n_flagged"] == 0]
print(f"\nWorks with NO flagged bands (heatmap trustworthy throughout): "
      f"{len(clean)}")
print("  " + ", ".join(sorted(clean)) if clean else "  (none)")

# ---- machine-readable output for the shading overlay ------------------------
with open("collision_bands.json", "w", encoding="utf-8") as out:
    json.dump({
        "_meta": {
            "generated_by": "missingness.py",
            "bin_width_pages": B,
            "flag_gap": args.flag_gap,
            "min_bin_vol": args.min_bin_vol,
            "note": ("Each entry is a within-work page band whose citations are "
                     "under-resolved relative to the work's own average rate, "
                     "typically due to Bekker/Stephanus page-number collisions "
                     "with other works. 'est_missing' is a first-order estimate "
                     "of citations not captured in that band. Bands are a "
                     "responsible FLOOR on the caveat set, not proof of the only "
                     "problems; absence of a flag means no band-level pattern was "
                     "detected above threshold, not certainty of completeness."),
        },
        "bands": band_table,
    }, out, ensure_ascii=False, indent=2)

print(f"\nWrote collision_bands.json  ({len(band_table)} bands across "
      f"{len(set(b['work'] for b in band_table))} works)")

print("\nInterpretation:")
print("  gap = how far a band's resolved-share falls below the work's average")
print("  rate. A flagged band means queued (unresolved) citations CLUSTER")
print("  there — those passage-cells are under-counted and the interface shades")
print("  them. A work can be uniformly LOW-rate yet have FEW flagged bands: that")
print("  means it's hard everywhere, not locally collided — a different caveat,")
print("  handled at the text level (floor/ceiling bar), not by band shading.")
