#!/usr/bin/env python3
"""
diagnose_homer.py — sanity-check the temporal profile of a book.line corpus
(Homer/Pindar) BEFORE trusting a book-grain temporal verdict.

Motivating puzzle (from TEMPORAL_FINDINGS §6): the Iliad's median citation year
came out 2009 while the Odyssey's is 1999 — the SAME journals, so a 10-year gap
is a data smell — and Book 1's early mass "collapsed" (1016 -> 282 articles),
driven by the proem (lines 1.1-1.12). Either a real recent surge or an artifact
(a recent batch / a false-match magnet on the proem). This script shows where the
recency comes from so we can tell which.

It reads the same viewer_data/view_b/<work>.json `dots` the temporal analysis
uses (book, page(=line), section, year, iid, journal). Stdlib only.

    python3 diagnose_homer.py viewer_data Iliad
    python3 diagnose_homer.py viewer_data Iliad Odyssey --split 2009
    python3 diagnose_homer.py viewer_data Iliad --proem-book 1 --proem-lines 12

Prints, per work:
  1. year histogram (5-yr bins) + mean/median + the cumulative crossing point
  2. per-JOURNAL table: n_cites, n_articles, median year, share — the fastest way
     to see a single recent journal dragging the median (flags median >= 2005)
  3. per-BOOK table: n_articles + median year (is recency global or book-local?)
  4. top lines by article count, each with its own median year
  5. PROEM zoom: lines <book>.1 .. <book>.N — per-line early/late counts (at the
     split) and how many distinct journals carry them (a magnet shows 1-2)
  6. duplicate/concordance smell: iids citing an implausible number of lines,
     and identical (journal,year,line) multiplicities
"""
import sys, os, json, argparse, statistics
from collections import defaultdict, Counter


def safe_name(work):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in work)


def load_dots(viewer_dir, work):
    path = os.path.join(viewer_dir, "view_b", safe_name(work) + ".json")
    if not os.path.exists(path):
        print(f"  !! {path} not found — skipping {work}")
        return None, None
    d = json.load(open(path, encoding="utf-8"))
    return d.get("system", "?"), d.get("dots", [])


def year_of(dot):
    y = dot.get("year", "")
    return int(y) if isinstance(y, str) and y.isdigit() and len(y) == 4 else None


def median_years(year_list):
    return int(statistics.median(year_list)) if year_list else None


def diagnose(viewer_dir, work, split, proem_book, proem_lines, bin_size, top_n):
    system, dots = load_dots(viewer_dir, work)
    if dots is None:
        return
    dated = [(year_of(d), d) for d in dots]
    dated = [(y, d) for (y, d) in dated if y is not None]
    n_all, n_dated = len(dots), len(dated)
    if not dated:
        print(f"\n===== {work} ({system}) =====  no dated citations")
        return
    all_years = [y for (y, _) in dated]
    med = median_years(all_years)
    mean = sum(all_years) / len(all_years)
    split = split or med

    print(f"\n===================  {work}  ({system})  ===================")
    print(f"  dots {n_all:,} · dated {n_dated:,} ({100*n_dated/n_all:.0f}%) · "
          f"years {min(all_years)}-{max(all_years)}")
    print(f"  MEAN year {mean:.1f} · MEDIAN year {med}   (split used: {split})")

    # 1. year histogram (binned) + cumulative crossing
    hist = Counter((y // bin_size) * bin_size for y in all_years)
    print("  year histogram (%d-yr bins):" % bin_size)
    run = 0
    half = n_dated / 2
    for b in sorted(hist):
        run += hist[b]
        bar = "#" * min(60, hist[b] * 60 // max(hist.values()))
        cross = "  <-- median crossing" if run - hist[b] < half <= run else ""
        print(f"    {b}s  {hist[b]:6,}  {bar}{cross}")

    # 2. per-journal table
    jn = defaultdict(lambda: {"cites": 0, "arts": set(), "years": []})
    for (y, d) in dated:
        j = d.get("journal", "?")
        jn[j]["cites"] += 1
        jn[j]["arts"].add(d.get("iid", ""))
        jn[j]["years"].append(y)
    print(f"  per-JOURNAL (sorted by articles; * median >= 2005):")
    print(f"    {'journal':<42} {'cites':>7} {'arts':>6} {'medYr':>6} {'share':>6}")
    rows = sorted(jn.items(), key=lambda kv: -len(kv[1]["arts"]))
    for j, v in rows[:20]:
        mj = median_years(v["years"])
        flag = " *" if mj and mj >= 2005 else "  "
        print(f"   {flag}{j[:42]:<42} {v['cites']:>7,} {len(v['arts']):>6,} "
              f"{mj:>6} {100*v['cites']/n_dated:>5.1f}%")

    # 3. per-book table
    bk = defaultdict(lambda: {"arts": set(), "years": []})
    for (y, d) in dated:
        b = str(d.get("book", ""))
        bk[b]["arts"].add(d.get("iid", ""))
        bk[b]["years"].append(y)
    print(f"  per-BOOK (article count · median year · early/late at {split}):")

    def sort_book(k):
        try:
            return (0, int(k[0]))
        except ValueError:
            return (1, 0)
    for b, v in sorted(bk.items(), key=sort_book):
        early = sum(1 for yy in v["years"] if yy < split)
        late = len(v["years"]) - early
        print(f"    book {b:>3}  arts {len(v['arts']):>6,}  medYr {median_years(v['years'])}"
              f"  cites {early:>6,}/{late:<6,}")

    # 4. top lines
    ln = defaultdict(lambda: {"arts": set(), "years": []})
    for (y, d) in dated:
        key = "%s.%s" % (d.get("book", ""), d.get("page", ""))
        ln[key]["arts"].add(d.get("iid", ""))
        ln[key]["years"].append(y)
    print(f"  TOP {top_n} lines by articles (line · arts · median year):")
    for key, v in sorted(ln.items(), key=lambda kv: -len(kv[1]["arts"]))[:top_n]:
        print(f"    {key:>10}  arts {len(v['arts']):>5,}  medYr {median_years(v['years'])}")

    # 5. proem zoom
    print(f"  PROEM zoom — book {proem_book}, lines 1..{proem_lines} "
          f"(line · early/late arts at {split} · #journals):")
    for line in range(1, proem_lines + 1):
        key = "%s.%s" % (proem_book, line)
        v = ln.get(key)
        if not v:
            continue
        earts = {d.get("iid") for (y, d) in dated
                 if str(d.get("book")) == str(proem_book) and str(d.get("page")) == str(line)
                 and y < split}
        larts = {d.get("iid") for (y, d) in dated
                 if str(d.get("book")) == str(proem_book) and str(d.get("page")) == str(line)
                 and y >= split}
        jrnls = {d.get("journal") for (y, d) in dated
                 if str(d.get("book")) == str(proem_book) and str(d.get("page")) == str(line)}
        print(f"    {key:>8}  early {len(earts):>5,} / late {len(larts):<5,}  "
              f"journals {len(jrnls)}")

    # 6. concordance / duplicate smell
    iid_lines = defaultdict(set)
    for (y, d) in dated:
        iid_lines[d.get("iid", "")].add("%s.%s" % (d.get("book", ""), d.get("page", "")))
    heavy = sorted(iid_lines.items(), key=lambda kv: -len(kv[1]))[:5]
    print(f"  CONCORDANCE smell — iids citing the most distinct lines:")
    for iid, lines in heavy:
        print(f"    iid {str(iid)[:16]:<16} cites {len(lines)} distinct lines")
    # identical (journal, year, line) multiplicities: a batch would show high dupes
    trip = Counter((d.get("journal"), y, "%s.%s" % (d.get("book"), d.get("page")))
                   for (y, d) in dated)
    top_trip = trip.most_common(5)
    print(f"  (journal,year,line) with most citations (batch/dupe smell):")
    for (j, y, line), c in top_trip:
        print(f"    {str(j)[:30]:<30} {y}  {line:>8}  x{c}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("viewer_dir")
    ap.add_argument("works", nargs="+")
    ap.add_argument("--split", type=int, default=0, help="early/late split year (0=median)")
    ap.add_argument("--proem-book", type=int, default=1)
    ap.add_argument("--proem-lines", type=int, default=12)
    ap.add_argument("--bin", type=int, default=5)
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args()
    for work in args.works:
        diagnose(args.viewer_dir, work, args.split, args.proem_book,
                 args.proem_lines, args.bin, args.top)


if __name__ == "__main__":
    main()
