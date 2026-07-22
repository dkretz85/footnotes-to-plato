#!/usr/bin/env python3
"""
locus.py  — shared locus parser + book faceting (single source of truth)

Lifted verbatim from derive_book.py (v2, VERIFIED boundaries) so that the
citation-heatmap aggregator and the book-derivation CLI use the SAME parse,
guaranteeing View B's section cells and the book facets never disagree.

Public API:
    parse_locus(match_cell) -> (page:int|None, section:str|None, line:int|None)
    assign(work, match_cell) -> (book_label:str|None, is_common_book:bool)
    COLUMNS: WORK, MATCH, BOOK  (zero-based indices into the TSV row)
    FACETED_WORKS: set of works that carry a derived `book`

Boundaries are DETERMINISTIC: each book spans [its opening locus, the next
book's opening locus). A citation is converted to a sortable key (page, section,
line) and placed by which half-open interval contains it. Mid-page openings
(e.g. Metaphysics little-alpha at 993a30, NE II at 1103a15) are handled exactly,
so 1103a14 -> NE I and 1103a15 -> NE II. No heuristic, no boundary flag needed.

Common books: NE V/VI/VII (Bekker 1129a1, 1138b15, 1145a15) are textually EE
IV/V/VI. Labelled 'V*'/'VI*'/'VII*' under NE; EE IV*/V*/VI* map to the same
pages. '*' marks a common book for the UI fold/split toggle.

Standalone CLI (unchanged from derive_book.py):
    python3 locus.py resolved.tsv > resolved_with_books.tsv
    python3 locus.py resolved.tsv --audit
"""
import sys, csv, re

# Zero-based column indices into the TSV row.
# Header: iid journal year doctype corpus page_index seq match work_id book confidence method context
#         0   1       2    3       4      5          6   7     8       9    10         11     12
WORK, MATCH, BOOK = 8, 7, 9

REP = [("I",327),("II",357),("III",386),("IV",419),("V",449),
       ("VI",484),("VII",514),("VIII",543),("IX",571),("X",595)]
LAWS = [("I",624),("II",652),("III",676),("IV",704),("V",726),("VI",751),
        ("VII",788),("VIII",828),("IX",853),("X",884),("XI",913),("XII",941)]

STEPH = {"Republic": [(lab, p, "a", 0) for lab, p in REP],
         "Laws":     [(lab, p, "a", 0) for lab, p in LAWS]}
STEPH_END = {"Republic": (621, "e", 9999), "Laws": (969, "e", 9999)}

META = [
    ("\u0391",980,"a",21),("\u03b1",993,"a",30),("\u0392",995,"a",24),("\u0393",1003,"a",21),
    ("\u0394",1012,"b",34),("\u0395",1025,"b",3),("\u0396",1028,"a",10),("\u0397",1042,"a",3),
    ("\u0398",1045,"b",27),("\u0399",1052,"a",15),("\u039a",1059,"a",18),("\u039b",1069,"a",18),
    ("\u039c",1076,"a",8),("\u039d",1087,"a",29),
]
NE = [
    ("I",1094,"a",1),("II",1103,"a",15),("III",1109,"b",30),("IV",1119,"b",20),
    ("V*",1129,"a",1),("VI*",1138,"b",15),("VII*",1145,"a",15),
    ("VIII",1155,"a",3),("IX",1163,"b",33),("X",1172,"a",19),
]
EE = [
    ("I",1214,"a",1),("II",1218,"b",30),("III",1228,"a",21),
    ("IV*",1129,"a",1),("V*",1138,"b",15),("VI*",1145,"a",15),
    ("VII",1234,"b",18),("VIII",1246,"a",26),
]
BEKKER = {"Metaphysics": META, "Nicomachean_Ethics": NE, "Eudemian_Ethics": EE}
BEKKER_END = {"Metaphysics": (1093,"b",9999),
              "Nicomachean_Ethics": (1181,"b",9999),
              "Eudemian_Ethics": (1249,"b",9999)}

FACETED_WORKS = set(STEPH) | set(BEKKER)

def key(page, section, line):
    return (page, section or "a", line if line is not None else 0)

def build_intervals(work):
    if work in STEPH:
        opens = STEPH[work]; end = STEPH_END[work]
    elif work in BEKKER:
        opens = BEKKER[work]; end = BEKKER_END[work]
    else:
        return None
    pts = sorted(({"label":lab, "k":key(p,s,l)} for lab,p,s,l in opens),
                 key=lambda d: d["k"])
    # Split into contiguous RUNS: a new run starts wherever there is a page gap
    # of >40 between consecutive openings' pages. This stops a book at the end of
    # one run (e.g. EE common book VI* ending ~1155) from absorbing the gap up to
    # the next run (EE-proper resuming at 1214). Within a run, each book ends at
    # the next book's opening; the last book of a run ends at the START of the
    # next run (or the treatise end for the final run).
    RUN_CAPS = {"Eudemian_Ethics": {"VI*": (1155, "a", 3)}}
    caps = RUN_CAPS.get(work, {})
    runs = []; cur = [pts[0]]
    for prev, nxt in zip(pts, pts[1:]):
        if nxt["k"][0] - prev["k"][0] > 40:   # page jump => new run
            runs.append(cur); cur = [nxt]
        else:
            cur.append(nxt)
    runs.append(cur)
    intervals = []
    for ri, run in enumerate(runs):
        default_end = runs[ri+1][0]["k"] if ri+1 < len(runs) else key(*end)
        for i, it in enumerate(run):
            if i+1 < len(run):
                hi = run[i+1]["k"]
            else:
                hi = caps.get(it["label"], default_end)   # run's true close
            intervals.append((it["label"], it["k"], hi))
    intervals.sort(key=lambda t: t[1])
    return intervals

INTERVALS = {}

def parse_locus(match_cell):
    """Parse a raw match cell (e.g. '80D5', '1094a', '300a1') into
    (page:int|None, section:str|None, line:int|None). Section lower-cased."""
    m = re.match(r"\s*(\d{2,4})\s*([a-eA-E])?\s*(\d+)?", match_cell or "")
    if not m: return (None, None, None)
    page = int(m.group(1))
    sec = m.group(2).lower() if m.group(2) else None
    line = int(m.group(3)) if m.group(3) else None
    return (page, sec, line)

def assign(work, match_cell):
    """Return (book_label, is_common_book) for a faceted work, else (None, False)."""
    if work not in INTERVALS:
        INTERVALS[work] = build_intervals(work)
    ivs = INTERVALS[work]
    if ivs is None: return (None, False)
    page, sec, line = parse_locus(match_cell)
    if page is None: return (None, False)

    if line is None:
        k = (page, sec or "a", 0)
        for label, lo, hi in ivs:
            if lo <= k < hi:
                return (label, label.endswith("*"))
        cands = [(lo, label) for label, lo, hi in ivs if lo[0] == page]
        if cands:
            label = min(cands)[1]
            return (label, label.endswith("*"))
        below = [(lo, label) for label, lo, hi in ivs if lo <= (page, "z", 10**9)]
        if below:
            label = max(below)[1]
            return (label, label.endswith("*"))
        return (None, False)
    else:
        k = (page, sec or "a", line)

    for label, lo, hi in ivs:
        if lo <= k < hi:
            return (label, label.endswith("*"))
    if k >= ivs[-1][1]:
        label = ivs[-1][0]; return (label, label.endswith("*"))
    return (None, False)

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit()
    path = sys.argv[1]; audit = "--audit" in sys.argv
    total = assigned = common_rows = 0
    with open(path, encoding="utf-8", newline="") as fh:
        r = csv.reader(fh, delimiter="\t"); header = next(r)
        w = None if audit else csv.writer(sys.stdout, delimiter="\t")
        if w: w.writerow(header)
        for row in r:
            if len(row) > max(WORK,MATCH,BOOK) and row[WORK] in FACETED_WORKS:
                total += 1
                lab, common = assign(row[WORK], row[MATCH])
                if lab:
                    assigned += 1; row[BOOK] = lab
                    if common: common_rows += 1
            if w: w.writerow(row)
    rate = 100*assigned/total if total else 0
    sys.stderr.write(f"\n[audit] faceted rows: {total:,}  assigned: {assigned:,} "
                     f"({rate:.1f}%)  common-book rows: {common_rows:,}  "
                     f"unassigned: {total-assigned:,}\n")
    if rate < 98:
        sys.stderr.write("[audit] <98% - some loci unparsed; paste a few unassigned "
                         "matches to Claude.\n")

if __name__ == "__main__":
    main()
