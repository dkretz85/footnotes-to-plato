#!/usr/bin/env python3
"""
profile_resolved.py  —  profile resolved.tsv to settle interface-design questions.

Run each section independently:  python3 profile_resolved.py <section> [path]
Sections:
    schema     header + 5 sample rows + column count           (RUN THIS FIRST)
    journals   volume per journal, sorted, with cumulative %   (checkbox design)
    years      volume per year / decade                        (time-slider range)
    works      resolved-count per work, sorted                 (text-level view)
    bins       for one work, citations per Stephanus/Bekker unit at 3 grains
    density    for one work, how sparse cells are at each grain (binning decision)

Examples:
    python3 profile_resolved.py schema
    python3 profile_resolved.py journals
    python3 profile_resolved.py bins Republic
    python3 profile_resolved.py density Meno

The script auto-detects column positions from the header, so it does not assume
exact field names. If detection fails it prints what it found and stops — paste
that to Claude.
"""

import sys, csv, collections, re

PATH_DEFAULT = "resolved.tsv"

# --- flexible column detection ------------------------------------------------
# maps a role -> list of candidate header names (lowercased substrings)
ROLE_HINTS = {
    "work":     ["work", "dialogue", "treatise", "resolved_work"],
    "journal":  ["journal", "jtitle", "source_title"],
    "year":     ["year", "pub_year", "date"],
    "page":     ["page_num", "stephanus", "bekker", "page_number", "num", "citation_page"],
    "section":  ["section", "column", "letter", "col"],
    "line":     ["line", "line_num"],
    "system":   ["system", "corpus", "scheme"],   # bekker / stephanus tag
    "raw":      ["raw", "match", "citation_str", "string", "text"],
    "conf":     ["conf", "confidence", "score"],
    "author":   ["author", "who"],
}

def detect(header):
    cols = {}
    lower = [h.strip().lower() for h in header]
    for role, hints in ROLE_HINTS.items():
        for i, h in enumerate(lower):
            if any(hint == h for hint in hints):   # exact first
                cols[role] = i; break
        if role in cols: continue
        for i, h in enumerate(lower):
            if any(hint in h for hint in hints):    # substring fallback
                cols[role] = i; break
    return cols

def load(path):
    f = open(path, encoding="utf-8", newline="")
    r = csv.reader(f, delimiter="\t")
    header = next(r)
    return header, r, f

def section_schema(path):
    header, r, f = load(path)
    print("COLUMN COUNT:", len(header))
    print("HEADER:")
    for i, h in enumerate(header):
        print(f"  [{i}] {h}")
    print("\nDETECTED ROLES:", detect(header))
    print("\nFIRST 5 ROWS:")
    for i, row in enumerate(r):
        if i >= 5: break
        print(" | ".join(row))
    f.close()

def _col(cols, role, header):
    if role not in cols:
        sys.exit(f"Could not find a '{role}' column. Header was:\n{header}\n"
                 f"Detected: {cols}\nPaste this to Claude.")
    return cols[role]

def section_journals(path):
    header, r, f = load(path); cols = detect(header)
    j = _col(cols, "journal", header)
    c = collections.Counter()
    for row in r:
        if len(row) > j: c[row[j]] += 1
    f.close()
    total = sum(c.values()); run = 0
    print(f"{total:,} resolved rows across {len(c)} journals\n")
    print(f"{'rank':>4} {'count':>9} {'cum%':>6}  journal")
    for rank, (name, n) in enumerate(c.most_common(), 1):
        run += n
        print(f"{rank:>4} {n:>9,} {100*run/total:>5.1f}%  {name}")

def section_years(path):
    header, r, f = load(path); cols = detect(header)
    y = _col(cols, "year", header)
    per_year = collections.Counter(); per_dec = collections.Counter()
    for row in r:
        if len(row) <= y: continue
        m = re.search(r"(1[6-9]\d\d|20[0-2]\d)", row[y])
        if not m: continue
        yr = int(m.group(1)); per_year[yr]+=1; per_dec[(yr//10)*10]+=1
    f.close()
    print("BY DECADE:")
    for d in sorted(per_dec): print(f"  {d}s  {per_dec[d]:>8,}")
    yrs = sorted(per_year)
    if yrs: print(f"\nyear range: {yrs[0]}–{yrs[-1]}   nonzero years: {len(yrs)}")

def section_works(path):
    header, r, f = load(path); cols = detect(header)
    w = _col(cols, "work", header)
    c = collections.Counter()
    for row in r:
        if len(row) > w: c[row[w]] += 1
    f.close()
    total = sum(c.values())
    print(f"{total:,} resolved rows across {len(c)} works\n")
    for rank, (name, n) in enumerate(c.most_common(), 1):
        print(f"{rank:>4} {n:>8,} {100*n/total:>5.1f}%  {name}")

def _page_section_line(row, cols):
    """Best-effort extraction of (page:int, section:str, line:int|None)."""
    page = sec = line = None
    if "page" in cols and len(row) > cols["page"]:
        m = re.search(r"(\d{2,4})", row[cols["page"]]); page = int(m.group(1)) if m else None
    if "section" in cols and len(row) > cols["section"]:
        m = re.search(r"([a-eA-E])", row[cols["section"]]); sec = m.group(1).lower() if m else None
    if "line" in cols and len(row) > cols["line"]:
        m = re.search(r"(\d+)", row[cols["line"]]); line = int(m.group(1)) if m else None
    # fallback: parse everything out of a raw citation string
    if page is None and "raw" in cols and len(row) > cols["raw"]:
        m = re.search(r"(\d{2,4})\s*([a-eA-E])?\s*(\d+)?", row[cols["raw"]])
        if m:
            page = int(m.group(1))
            sec = m.group(2).lower() if m.group(2) else sec
            line = int(m.group(3)) if m.group(3) else line
    return page, sec, line

def section_bins(path, target):
    header, r, f = load(path); cols = detect(header)
    w = _col(cols, "work", header)
    grain_page = collections.Counter()   # 300
    grain_sec  = collections.Counter()   # 300a
    grain_line = collections.Counter()   # 300a1-10
    n = 0
    for row in r:
        if len(row) <= w or row[w] != target: continue
        page, sec, line = _page_section_line(row, cols)
        if page is None: continue
        n += 1
        grain_page[page] += 1
        grain_sec[(page, sec or "?")] += 1
        if line is not None:
            grain_line[(page, sec or "?", (line-1)//10)] += 1
    f.close()
    print(f"WORK: {target}   resolved citations with a parseable page: {n:,}\n")
    for label, g in [("per page (300)", grain_page),
                     ("per section (300a)", grain_sec),
                     ("per 10-line (300a1-10)", grain_line)]:
        if not g: print(f"{label}: no data"); continue
        vals = list(g.values())
        occupied = len(g); tot = sum(vals)
        mean = tot/occupied
        singles = sum(1 for v in vals if v == 1)
        print(f"{label}:")
        print(f"    occupied cells: {occupied:,}   mean/occupied cell: {mean:.1f}"
              f"   cells with exactly 1: {100*singles/occupied:.0f}%")

def section_density(path, target):
    """Same as bins but frames it as: what fraction of the work's span is empty."""
    header, r, f = load(path); cols = detect(header)
    w = _col(cols, "work", header)
    pages=set(); secs=set(); lines=set(); n=0
    pmin=pmax=None
    for row in r:
        if len(row) <= w or row[w] != target: continue
        page, sec, line = _page_section_line(row, cols)
        if page is None: continue
        n+=1; pages.add(page)
        pmin = page if pmin is None else min(pmin,page)
        pmax = page if pmax is None else max(pmax,page)
        if sec: secs.add((page,sec))
        if line is not None: lines.add((page,sec,(line-1)//10))
    f.close()
    if pmin is None: print("no data for", target); return
    span_pages = pmax - pmin + 1
    print(f"WORK: {target}   citations: {n:,}   page span: {pmin}–{pmax} ({span_pages} pages)")
    print(f"  distinct pages touched:      {len(pages):>5}  ({100*len(pages)/span_pages:.0f}% of span)")
    print(f"  distinct sections touched:   {len(secs):>5}  (of ~{span_pages*5} possible)")
    if lines:
        print(f"  distinct 10-line cells:      {len(lines):>5}")
    print("\n  -> if 'per section' occupancy is low, the section grain is too fine;")
    print("     bin coarser (e.g. 10-page bands) for a readable heatmap.")

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit()
    section = sys.argv[1]
    path = sys.argv[3] if section in ("bins","density") and len(sys.argv)>3 else \
           (sys.argv[2] if section not in ("bins","density") and len(sys.argv)>2 else PATH_DEFAULT)
    if section == "schema":   section_schema(path)
    elif section == "journals": section_journals(path)
    elif section == "years":  section_years(path)
    elif section == "works":  section_works(path)
    elif section == "bins":
        if len(sys.argv)<3: sys.exit("usage: bins <WorkName> [path]")
        section_bins(path, sys.argv[2])
    elif section == "density":
        if len(sys.argv)<3: sys.exit("usage: density <WorkName> [path]")
        section_density(path, sys.argv[2])
    else: print(__doc__)

if __name__ == "__main__":
    main()
