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


# --------------------------------------------------------------------------
# Range / span expansion (RANGE handoff). A multi-unit citation is counted as
# attention to EVERY unit it covers, each weighted equally with a single-unit
# citation (settled decision — no span down-weighting). expand_range() turns a
# range match cell into the list of single-unit cells it covers, so the
# resolver can fan one input row into N unit rows (each stamped with the raw
# range as span_src for the future drill panel). A NON-range cell returns the
# cell VERBATIM in a one-element list, so the single-unit path is byte-for-byte
# unchanged (RANGE §6: counts identical except where rows were range-truncated).
# An over-long or incoherent span returns None so the caller can DIVERT it to
# the review queue rather than fan out phantom cells (RANGE §6 divert-not-drop).
# --------------------------------------------------------------------------

STEPH_SECTIONS = "abcde"          # fixed Stephanus section alphabet
DASHES = "-–—"          # hyphen, en-dash, em-dash
_RANGE_SPLIT = re.compile(r"\s*[%s]\s*" % DASHES)
# Default per-system unit caps. Stephanus: ~30 units (§6) — a legitimate span
# rarely exceeds a few pages; beyond this it's a mis-parse (e.g. '553-620'),
# OCR garbage, or a dash that isn't a range.
STEPH_MAX_UNITS = 40

def _parse_steph_endpoint(tok):
    """Parse one Stephanus endpoint token. '620a'->(620,'a'), bare 'e'->(None,'e'),
    '553'->(553,None). Line digits are ignored: Stephanus aggregates at
    page+section grain (build_viewer_data keys View B on (book,page,sec))."""
    m = re.match(r"\s*(\d{2,4})?\s*([a-eA-E])?", tok or "")
    if not m:
        return (None, None)
    page = int(m.group(1)) if m.group(1) else None
    sec = m.group(2).lower() if m.group(2) else None
    return (page, sec)

def expand_stephanus(match_cell, max_units=STEPH_MAX_UNITS):
    """Expand a Stephanus (or ambiguous, same digit+letter shape) range cell to
    a list of 'PAGEsec' unit strings, inclusive. Returns [cell] verbatim for a
    non-range cell; None for an incoherent or over-long span (caller diverts).

        '620a-622c' -> 620a,b,c,d,e / 621a-e / 622a,b,c        (13 units)
        '553a-e'    -> 553a,b,c,d,e   (bare section tail inherits start page)
        '553a-554b' -> 553a-e / 554a,b                          (7 units)
    """
    if match_cell is None:
        return None
    if not any(d in match_cell for d in DASHES):
        return [match_cell]                       # single unit: verbatim
    parts = _RANGE_SPLIT.split(match_cell.strip(), 1)
    if len(parts) != 2:
        return None
    start_p, start_s = _parse_steph_endpoint(parts[0])
    if start_p is None or start_s is None:
        return None                               # not a clean Stephanus start
    end_p, end_s = _parse_steph_endpoint(parts[1])
    if end_p is None:
        end_p = start_p                           # bare-section tail inherits page
    if end_s is None:
        end_s = start_s
    start_key = (start_p, STEPH_SECTIONS.index(start_s))
    end_key = (end_p, STEPH_SECTIONS.index(end_s))
    if end_key < start_key:
        return None                               # reversed / incoherent
    units = []
    p, si = start_key
    while (p, si) <= end_key:
        units.append("%d%s" % (p, STEPH_SECTIONS[si]))
        if len(units) > max_units:
            return None                           # runaway span -> divert
        si += 1
        if si == len(STEPH_SECTIONS):
            si = 0
            p += 1
    return units

# --- book.line systems (Homer, Pindar): single-LINE grain -------------------
# The line-span diagnostic showed median span = 1 line (67% Homer / 59% Pindar
# single-line), so we store at line grain and let the viewer bin for display —
# never fabricate a coarser unit no scholar cited. The long tail (a 984-line
# "span" is a book-level gesture, not line attention) is diverted by the cap.

HOMER_MAX_LINES = 30            # spans beyond this -> divert (whole-book / OCR)
PINDAR_MAX_LINES = 20

_ROMAN = {"i":1,"v":5,"x":10,"l":50,"c":100,"d":500,"m":1000}
def _roman_to_int(s):
    s = s.lower()
    if not s or any(c not in _ROMAN for c in s):
        return None
    total = prev = 0
    for c in reversed(s):
        v = _ROMAN[c]
        total += -v if v < prev else v
        prev = v
    return total

def _book_to_int(tok):
    return int(tok) if tok.isdigit() else _roman_to_int(tok)

def _expand_line_end(start, end_tok):
    """Abbreviated trailing endpoint shares the start's high-order digits:
    '111-12' -> 112, '484-93' -> 493, '7-11' -> 11."""
    end = int(end_tok)
    if end < start:
        scale = 10 ** len(end_tok)
        end = (start - start % scale) + end
    return end

_HOMER_CANON = {"il":"Il","iliad":"Il","od":"Od","odyssey":"Od"}
_HOMER_PARSE = re.compile(
    r"^\s*(Il|Od|Iliad|Odyssey)\.?\s*"
    r"(\d{1,2}|[ivxlcdm]{1,7})"                 # book: Arabic OR Roman
    r"[.,\s]\s*(\d{1,3})(?:\s*[-–—]\s*(\d{1,3}))?", re.I)

_PINDAR_CANON = {"ol":"Ol","olympian":"Ol","pyth":"Pyth","pythian":"Pyth",
                 "nem":"Nem","nemean":"Nem","isth":"Isth","isthmian":"Isth"}
_PINDAR_PARSE = re.compile(
    r"^\s*(Ol|Pyth|Nem|Isth|Olympian|Pythian|Nemean|Isthmian)\.?\s*"
    r"(\d{1,2})\.(\d{1,3})(?:\s*[-–—]\s*(\d{1,3}))?", re.I)

def _expand_bookline(match_cell, parse_re, canon, max_units, book_conv):
    """Shared Homer/Pindar expander: parse cue + book/ode + line(-range),
    normalise (cue canonical, book Arabic), enumerate lines. Returns [cell]
    verbatim if unparseable (resolver may still divert); None if over-cap or
    incoherent."""
    m = parse_re.match(match_cell or "")
    if not m:
        return [match_cell]
    cue = canon.get(m.group(1).lower())
    book = book_conv(m.group(2))
    if cue is None or book is None:
        return [match_cell]
    start = int(m.group(3))
    if m.group(4) is None:
        return ["%s. %d.%d" % (cue, book, start)]
    end = _expand_line_end(start, m.group(4))
    if end < start or end - start + 1 > max_units:
        return None
    return ["%s. %d.%d" % (cue, book, ln) for ln in range(start, end + 1)]

def expand_homer(match_cell, max_units=HOMER_MAX_LINES):
    return _expand_bookline(match_cell, _HOMER_PARSE, _HOMER_CANON,
                            max_units, _book_to_int)

def expand_pindar(match_cell, max_units=PINDAR_MAX_LINES):
    return _expand_bookline(match_cell, _PINDAR_PARSE, _PINDAR_CANON,
                            max_units, int)

# --- chapter:verse system (Pauline NT): verse grain -------------------------
# Cross-chapter ranges (Rom 7:25-8:2) need verses-per-chapter, and the same
# table rejects out-of-range citations (Phlm 6:15). Pass book_lengths = the
# array for the resolved book from nt_chapter_lengths.json; the resolver looks
# it up after mapping the cue -> book.

NT_MAX_VERSES = 30
_NT_REF = re.compile(
    r"(\d{1,3}):(\d{1,3})(?:\s*[-–—]\s*(?:(\d{1,3}):)?(\d{1,3}))?")

def expand_nt(match_cell, book_lengths=None, max_units=NT_MAX_VERSES):
    """Expand a Pauline chapter:verse cell. book_lengths = verses-per-chapter
    array for the resolved book (index = chapter-1), or None to skip validation
    and cross-chapter expansion. Returns [cell] if no ref parses; None to divert
    (out of range, reversed, or over-cap)."""
    m = _NT_REF.search(match_cell or "")
    if not m:
        return [match_cell]
    cue = match_cell[:m.start()].strip()
    sch, sv = int(m.group(1)), int(m.group(2))
    end_ch = int(m.group(3)) if m.group(3) else None
    end_tok = m.group(4)
    unit = lambda ch, v: ("%s %d:%d" % (cue, ch, v)).strip()
    def ch_len(ch):
        if book_lengths and 1 <= ch <= len(book_lengths):
            return book_lengths[ch - 1]
        return None
    if end_tok is None:                                   # single verse
        if book_lengths is not None and (ch_len(sch) is None or sv > ch_len(sch)):
            return None
        return [unit(sch, sv)]
    if end_ch is None or end_ch == sch:                   # within one chapter
        ev = _expand_line_end(sv, end_tok)
        L = ch_len(sch)
        if book_lengths is not None and (L is None or sv > L or ev > L):
            return None
        if ev < sv or ev - sv + 1 > max_units:
            return None
        return [unit(sch, v) for v in range(sv, ev + 1)]
    if not book_lengths:                                  # cross-chapter needs table
        return None
    ev = int(end_tok)
    if sch < 1 or end_ch > len(book_lengths) or end_ch < sch \
       or sv > ch_len(sch) or ev > ch_len(end_ch):
        return None
    units = []
    for ch in range(sch, end_ch + 1):
        v_lo = sv if ch == sch else 1
        v_hi = ev if ch == end_ch else ch_len(ch)
        for v in range(v_lo, v_hi + 1):
            units.append(unit(ch, v))
            if len(units) > max_units:
                return None
    return units

# --- Bekker (Aristotle): page+column, displayed in 15-line bands ------------
# We STORE line-level (single cites keep their exact line, so no precision is
# lost and Aristotle can be shown at line grain later) and the viewer bins by
# band = line // 15 for display. Only a RANGE crossing a column boundary is
# enumerated at band grain here, because enumerating individual lines across the
# boundary would need per-column line counts we don't have. A band is emitted as
# a representative cell: band 0 = bare column ('1097b'), band k>0 = '<page><col><15k>'
# so that line // 15 recovers the band. Column order is a -> b -> next page a.

BEKKER_BAND = 15
BEKKER_BANDS_PER_COL = 3        # assume <=45 lines/column (covers typical Bekker)
BEKKER_MAX_UNITS = 20
_COL_RANK = {"a": 0, "b": 1}
_RANK_COL = {0: "a", 1: "b"}

def _parse_bekker_endpoint(tok):
    """'1097b8'->(1097,'b',8), '1098a'->(1098,'a',0), bare 'a20'->(None,'a',20).
    Pages are 3-4 digits: 4-digit cites arrive tagged 'bekker', but low (3-digit)
    Bekker pages arrive tagged 'ambiguous' and reach here once the resolver has
    decided the cell is Aristotle, not Plato."""
    m = re.match(r"\s*(\d{3,4})?\s*([abAB])?\s*(\d+)?", tok or "")
    if not m:
        return (None, None, None)
    page = int(m.group(1)) if m.group(1) else None
    col = m.group(2).lower() if m.group(2) else None
    line = int(m.group(3)) if m.group(3) else 0
    return (page, col, line)

def _bekker_unit(page, col, band):
    return "%d%s%s" % (page, col, "" if band == 0 else band * BEKKER_BAND)

def expand_bekker(match_cell, max_units=BEKKER_MAX_UNITS):
    """Expand a Bekker range to band-representative cells; [cell] verbatim for a
    single cite (exact line retained); None to divert (incoherent / over-cap)."""
    if not any(d in match_cell for d in DASHES):
        return [match_cell]
    parts = _RANGE_SPLIT.split(match_cell.strip(), 1)
    if len(parts) != 2:
        return None
    sp, sc, sl = _parse_bekker_endpoint(parts[0])
    if sp is None or sc is None:
        return None
    ep, ec, el = _parse_bekker_endpoint(parts[1])
    if ep is None:
        ep = sp
    if ec is None:
        ec = sc
    start = (sp, _COL_RANK[sc], sl // BEKKER_BAND)
    end = (ep, _COL_RANK[ec], el // BEKKER_BAND)
    if end < start:
        return None
    units = []
    p, cr, b = start
    while (p, cr, b) <= end:
        units.append(_bekker_unit(p, _RANK_COL[cr], b))
        if len(units) > max_units:
            return None
        b += 1
        if b >= BEKKER_BANDS_PER_COL:
            b = 0; cr += 1
            if cr > 1:
                cr = 0; p += 1
        if p > ep + 1:              # safety: end unreachable
            return None
    return units

# Dispatch by REFERENCE SYSTEM. Note: an 'ambiguous'-tagged cell (2-3 digit +
# a/b) is Plato OR low Aristotle; the caller (resolver) must pass the RESOLVED
# system ('stephanus' or 'bekker'), not 'ambiguous', because the section
# alphabet differs (Plato a-e vs Bekker columns a/b). 'ambiguous' here is only a
# fallback and defaults to the Plato reading (the common case).
def expand_range(match_cell, corpus=None, nt_lengths=None, max_units=None):
    """Return the list of single-unit match cells a (possibly-range) cell covers,
    or None to divert. nt_lengths = verses-per-chapter for the resolved NT book."""
    if corpus in ("stephanus", "ambiguous"):
        return expand_stephanus(match_cell, max_units or STEPH_MAX_UNITS)
    if corpus == "bekker":
        return expand_bekker(match_cell, max_units or BEKKER_MAX_UNITS)
    if corpus == "homer":
        return expand_homer(match_cell, max_units or HOMER_MAX_LINES)
    if corpus == "pindar":
        return expand_pindar(match_cell, max_units or PINDAR_MAX_LINES)
    if corpus == "nt":
        return expand_nt(match_cell, nt_lengths, max_units or NT_MAX_VERSES)
    return [match_cell]

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
