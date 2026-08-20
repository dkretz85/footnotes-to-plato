#!/usr/bin/env python3
"""
find_stray_odes.py — locate the stray 46th Pindar ode-number (audit B7).

The pooled Pindar run reported 46 ode-units for 45 canonical odes. This scans the
Pindar view_b files and lists every ode (book) number present per shelf, flagging
any outside the canonical range, with citation counts, example iids, journals, and
years — enough to tell whether it is an OCR/fragment artifact and whether it also
sits in the non-temporal viewer_data (where it would render as a phantom unit).

    python3 find_stray_odes.py viewer_data
    python3 find_stray_odes.py viewer_data --works Olympian Pythian Nemean Isthmian

Canonical ranges: Olympian 1-14, Pythian 1-12, Nemean 1-11, Isthmian 1-9
(Isthmian 9 survives only in fragments; 1-8 are the complete odes).
"""
import sys, os, json, argparse
from collections import defaultdict, Counter

CANON = {"Olympian": (1, 14), "Pythian": (1, 12), "Nemean": (1, 11), "Isthmian": (1, 9)}


def safe_name(work):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in work)


def scan(viewer_dir, works):
    total_units = 0
    for work in works:
        path = os.path.join(viewer_dir, "view_b", safe_name(work) + ".json")
        if not os.path.exists(path):
            print(f"  !! {path} not found — skipping {work}")
            continue
        d = json.load(open(path, encoding="utf-8"))
        dots = d.get("dots", [])
        lo, hi = CANON.get(work, (1, 999))
        per_ode = defaultdict(lambda: {"n": 0, "iids": set(), "journals": set(), "years": []})
        for dot in dots:
            b = str(dot.get("book", "")).strip()
            per_ode[b]["n"] += 1
            per_ode[b]["iids"].add(dot.get("iid", ""))
            per_ode[b]["journals"].add(dot.get("journal", ""))
            y = dot.get("year", "")
            if isinstance(y, str) and y.isdigit():
                per_ode[b]["years"].append(int(y))

        def as_int(b):
            try:
                return int(b)
            except ValueError:
                return -1
        odes = sorted(per_ode, key=as_int)
        total_units += len(odes)
        print(f"\n=====  {work}  (canonical odes {lo}-{hi}; found {len(odes)} distinct ode-numbers)  =====")
        for b in odes:
            v = per_ode[b]
            n_i = as_int(b)
            stray = not (lo <= n_i <= hi)
            yr = f"{min(v['years'])}-{max(v['years'])}" if v["years"] else "no dates"
            flag = "  <-- STRAY (outside canon)" if stray else ""
            print(f"    ode {b:>4}  cites {v['n']:>5,}  arts {len(v['iids']):>4,}  "
                  f"journals {len(v['journals']):>2}  years {yr}{flag}")
            if stray:
                ex = [iid for iid in list(v["iids"])[:5]]
                print(f"           example iids: {ex}")
                print(f"           journals: {sorted(j for j in v['journals'] if j)[:6]}")
    print(f"\n  TOTAL distinct ode-units across shelves: {total_units} "
          f"(canonical total = 45: O 14 + P 12 + N 11 + I 8)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("viewer_dir")
    ap.add_argument("--works", nargs="+",
                    default=["Olympian", "Pythian", "Nemean", "Isthmian"])
    args = ap.parse_args()
    scan(args.viewer_dir, args.works)


if __name__ == "__main__":
    main()
