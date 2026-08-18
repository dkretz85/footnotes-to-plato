#!/usr/bin/env python3
"""
build_citation_db.py — turn the delivered JSTOR full-text corpus into the
working citation database the parser will consume. LOW-MEMORY, CHECKPOINTED.

Runs in BOUNDED memory regardless of corpus size:
  * the delivery file is streamed one record at a time;
  * citation rows are written straight to disk (never held in a list);
  * matches within a page are yielded, not collected, so a single giant page
    can't build a huge span list;
  * distinct-article counts are computed in a cheap SECOND pass over the
    on-disk citations.tsv, so no per-key iid sets are held during the scan;
  * the only in-RAM structures are: the metadata index (iid->journal/year/type,
    ~69k small tuples), a set of delivered iids (coverage), and an integer-only
    Counter of (journal,year,corpus) match totals. All bounded and small.

Progress is printed every PROGRESS_EVERY records so you can watch it work and
see immediately if one record stalls. Output is flushed periodically, so a
crash mid-run keeps everything written so far (and --resume can continue).

INPUT (both gzipped JSONL, streamed — never unpacked to disk):
  delivery : {iid, full_text:[page,…], references:[str,…]}
  metadata : keyed by item_id, carrying is_part_of / published_date / content_subtype

OUTPUT:
  citations.tsv         iid, journal, year, doctype, corpus, page_index, match, context
  citation_summary.tsv  journal, year, corpus, n_matches, n_articles
  coverage_report.txt   delivered-vs-requested reconciliation + the single drop

Usage:
    python3 build_citation_db.py \\
        16b50028-4490-4086-8fd0-d20505f6e998.jsonl.gz \\
        jstor_metadata_2026-07-18.jsonl.gz \\
        [--requested request_item_ids.txt] \\
        [--context 120] [--max-records N] [--resume]
"""

import sys, os, json, gzip, io, re, argparse, collections

FLAGGED_MISSING = "ab0e7253-8739-3667-b98e-025ad9fd37f5"
PROGRESS_EVERY  = 2000        # print a heartbeat every N delivery records
FLUSH_EVERY     = 2000        # flush citations.tsv every N records
# Guard: if a single page is longer than this many chars, scan it in windows
# rather than all at once. 2 MB of text per page is already absurd for an
# article; this only trips on pathological scanned-volume records.
PAGE_CHUNK      = 500_000
PAGE_OVERLAP    = 40          # re-scan a small overlap so a match on a chunk
                              # boundary isn't lost

# --- citation regexes (GREEK PAGE-REFERENCE — UNCHANGED) ---------------------
# BEKKER_SURE : 4-digit page + [ab]  -> Aristotle, unambiguous
# STEPH_SURE  : 2-3 digit + [c-e]    -> Plato, unambiguous (letter gives it away)
# AMBIGUOUS   : 2-3 digit + [ab]     -> could be either; parser decides
# v2 range extension: each shape now optionally captures a RANGE TAIL so that
# multi-unit citations survive into citations.tsv intact (620a-622c, 553a-e,
# 1097b8-1098a20) for the downstream parser to expand. The tail is LETTER-
# GUARDED: it must end in a section/column letter, so a bibliographic page range
# ('BRUNSCHWIG (1996a), 123-25') can never match — a bare '-25' has no letter.
# The dash is required TIGHT (no surrounding whitespace) and the trailing \b
# rejects hyphenated words ('327a-based' -> just '327a', since 'b' isn't at a
# word boundary). Single-unit matching is unchanged: with no dash the optional
# group matches empty, byte-for-byte identical to v1, so the old Plato/Aristotle
# citations.tsv remains a valid baseline for the non-range rows.
_STEPH_TAIL  = r"(?:[-–—](?:\d{2,3})?[a-eA-E]\d{0,2})?"  # -[page]sec, sec required
_BEKKER_TAIL = r"(?:[-–—](?:\d{4})?[abAB]\d{0,2})?"       # -[page]col, col required
BEKKER_SURE = re.compile(r"\b\d{4}[abAB]\d{0,2}" + _BEKKER_TAIL + r"\b")
STEPH_SURE  = re.compile(r"\b\d{2,3}[c-eC-E]\d{0,2}" + _STEPH_TAIL + r"\b")
AMBIGUOUS   = re.compile(r"\b\d{2,3}[abAB]\d{0,2}" + _STEPH_TAIL + r"\b")

# --- NEW: author-cued book.line and chapter:verse harvesting -----------------
#
# WHY THIS SHAPE. A bare "1.1" is hopelessly ambiguous — it could be Homer,
# Pindar, a chapter:verse, a decimal, a section number, a page range, a date.
# The ONLY reliable disambiguator in running prose is the author/work
# ABBREVIATION sitting next to the number ("Il. 1.1", "Rom. 8:28"). So we do
# NOT harvest bare numbers. We harvest an abbreviation-cue token IMMEDIATELY
# followed (within a few chars) by a book.line or chapter:verse shape, and we
# emit the WHOLE thing (cue + number) as the match, so the downstream parser
# has the author cue to route on.
#
# CALIBRATION WARNING (Aug-7 handoff §2/§5.3): the CUE LISTS below are seeded
# ONLY with forms we are confident appear. They are DELIBERATELY conservative.
# After the first harvest, scan the real match cells and ADD forms that
# actually occur (and REMOVE any that produce garbage). Do NOT add single-letter
# Pindar cues (O./P./N./I.) until confirmed present — they collide violently
# with initials, enumerations, and roman-numeral list markers. Each list is a
# plain, editable table on purpose.
#
# corpus tags emitted: "homer", "pindar", "nt" (Pauline/NT chapter:verse).
# Work attribution (Iliad vs Odyssey, which ode, which epistle) is NOT decided
# here — that is downstream parser/router work. Here we only tag the reference
# SYSTEM by its cue, harvest broadly, and let the parser resolve.

# Number shapes (structural, committed):
#   book.line     : 1-2 digit book . 1-3 digit line     e.g. 1.1, 24.804, 9.412
#   chapter:verse : 1-3 digit chapter : 1-3 digit verse  e.g. 1:1, 8:28, 15:3
#
# HOMER SPECIAL CASE — Roman-numeral books. Classicists cite Homer with the
# BOOK in Roman numerals (upper OR lower case) very frequently:
#   Il. XXIV.804,  Od. ix.412,  Il. i.1,  Iliad XVIII.478-608
# and with varied separators (dot, comma, or bare space). We therefore give
# Homer its own book.line shape that accepts EITHER Arabic (1-2 digit) OR a
# Roman numeral BOUNDED TO I..XXIV (Homer has 24 books). Bounding the numeral
# is deliberate: a loose [ivxlcdm]+ would overmatch words and initials, and it
# also means an out-of-range numeral like "XXV" cannot be mistaken for a book.
# Pindar is NOT given Roman numerals: its odes are numbered in Arabic by near-
# universal convention (Ol. 1, Pyth. 8), so Roman matching there would only add
# false positives. (Revisit from real cells if that assumption proves wrong.)
_LINE          = r"\d{1,3}(?:[-\u2013]\d{1,3})?"                 # line / line-range
_VERSE_SHAPE   = r"\d{1,3}:\d{1,3}(?:[-\u2013]\d{1,3})?"          # chapter:verse (+range)
_PINDAR_SHAPE  = r"\d{1,2}\.\d{1,3}(?:[-\u2013]\d{1,3})?"          # Arabic ode.line only

def _roman_1_24_alt():
    """Explicit Roman numerals I..XXIV, longest-first so 'XXIV' matches before
    'XX'. Returned as a regex alternation fragment."""
    vals = ["I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII",
            "XIII","XIV","XV","XVI","XVII","XVIII","XIX","XX","XXI","XXII",
            "XXIII","XXIV"]
    return "|".join(sorted(vals, key=len, reverse=True))

_HOMER_BOOK = r"(?:\d{1,2}|%s)" % _roman_1_24_alt()   # Arabic 1-2 digit OR Roman I-XXIV
_HOMER_SEP  = r"(?:\.|,\s?|\s)"                         # dot | comma(+space) | space
_HOMER_SHAPE = r"%s%s%s" % (_HOMER_BOOK, _HOMER_SEP, _LINE)

# Cue tokens. Kept SEPARATE per corpus so each can be tuned independently.
# Trailing "." in a cue is matched literally but optionally (some prose drops it).
# Case-insensitive at compile time. These are STARTER sets — expand from corpus.
HOMER_CUES = [
    r"Il",        # Iliad
    r"Od",        # Odyssey
    r"Iliad",
    r"Odyssey",
    # NOTE: bare "Hom" cue REMOVED after smoke test — it caught patristic
    # "Hom. 9.4" (homily) citations en masse in the theology corpus. Real
    # "Hom. Il." / "Hom. Od." references are still caught by the Il/Od cues
    # (the "Hom." prefix is simply ignored). Do not re-add bare Hom without a
    # follow-cue guard (e.g. require Il/Od after it).
]
PINDAR_CUES = [
    r"Ol",  r"Pyth", r"Nem", r"Isth",     # Ol./Pyth./Nem./Isth. — multi-letter, safe
    r"Olympian", r"Pythian", r"Nemean", r"Isthmian",
    # NOTE: bare "Pind"/"Pindar" cues REMOVED after the cue audit — they carry no
    # ode-TYPE, so even a clean "Pind. 4.162" is unresolvable (Olympian? Pythian?
    # Nemean? Isthmian?), and the 50 harvested cells were noise ("Pind. 0.9").
    # Real Pindar always names the ode-type, caught above; a "Pind." prefix before
    # them is harmlessly ignored.
    # NOTE: single-letter O./P./N./I. intentionally EXCLUDED — high collision risk
    # (initials, enumerations, roman list markers); the audit shows no need.
]
# 1/2 as Arabic OR Roman I/II — some scholars number the letters in Roman
# (I Cor, II Tim). Guarded by the :verse shape, so collision risk is minimal.
_NT_NUM = r"(?:[12]|II?)"
NT_CUES = [
    # Pauline letters — conservative, distinctive abbreviations.
    r"Rom",                                # Romans
    _NT_NUM + r" ?Cor",                    # 1/2/I/II Corinthians (space optional)
    r"Gal", r"Eph", r"Phil", r"Col",       # Galatians…Colossians
    _NT_NUM + r" ?Thess",
    _NT_NUM + r" ?Tim", r"Tit", r"Phlm",
    # NOTE: "Phil" (Philippians) vs "Phlb"/"Phileb" (Plato's Philebus) — Philebus
    # uses Stephanus pages, not chapter:verse, so the :verse shape guards against
    # collision. Audit confirmed clean (all samples Phil. 2:6-11, the Christ hymn).
    # Pauline-only by design: the Gospels/Acts/Catholic epistles carry versification
    # variance that would muddy a bibliometric map; add later (needs a re-harvest).
]

def _compile_cued(cues, shape):
    """One regex: (cue token) + up to 4 separator chars + (number shape).
    The cue and number are both captured; group(0) is the whole match."""
    cue_alt = "|".join(cues)
    # cue, optional '.', 1-4 spaces/nbsp, then the shape
    pat = r"\b(?:%s)\.?[\s\u00a0]{0,4}(?:%s)" % (cue_alt, shape)
    return re.compile(pat, re.IGNORECASE)

HOMER_RX  = _compile_cued(HOMER_CUES,  _HOMER_SHAPE)
PINDAR_RX = _compile_cued(PINDAR_CUES, _PINDAR_SHAPE)
NT_RX     = _compile_cued(NT_CUES,     _VERSE_SHAPE)

METADATA_ID   = "item_id"
JOURNAL_FIELD = "is_part_of"
YEAR_FIELD    = "published_date"
TYPE_FIELD    = "content_subtype"
TITLE_FIELD   = "title"
DELIVERY_ID   = "iid"
DELIVERY_TEXT = "full_text"


def open_stream(path):
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")


def year_of(val):
    for tok in str(val).replace("-", " ").split():
        if len(tok) == 4 and tok.isdigit():
            return tok
    return str(val) if val else "?"


def load_metadata(path, keep_iids=None):
    """iid -> (journal, year, doctype).

    The metadata file is JSTOR's FULL catalogue (~12.6M records across all
    disciplines), but we only need the ~69k iids in our request. Passing
    keep_iids restricts the in-RAM index to just those, cutting memory by
    ~180x — this is the fix for the 8 GB OOM. sys.intern shares the repeated
    journal/year strings across records."""
    meta = {}
    n = scanned = 0
    with open_stream(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            scanned += 1
            try:
                rec = json.loads(line)
            except Exception:
                continue
            iid = rec.get(METADATA_ID)
            if not iid:
                continue
            if keep_iids is not None and iid not in keep_iids:
                continue
            meta[iid] = (
                sys.intern(str(rec.get(JOURNAL_FIELD, "?") or "?")),
                sys.intern(year_of(rec.get(YEAR_FIELD, ""))),
                sys.intern(str(rec.get(TYPE_FIELD, "?") or "?")),
                str(rec.get(TITLE_FIELD, "") or ""),   # unique per article; don't intern
            )
            n += 1
            if keep_iids is not None and len(meta) == len(keep_iids):
                break  # got them all; no need to scan the rest of 12.6M
    print(f"Metadata: scanned {scanned:,} catalogue records, "
          f"kept {n:,} matching our request.", flush=True)
    return meta


def iter_matches_in_text(text):
    """Yield (corpus, match, start, end) for a page, in reading order, with
    overlapping matches resolved to the LONGEST.

    The author-cued patterns (homer/pindar/nt) match a DIFFERENT shape
    (book.line / chapter:verse) anchored on an abbreviation, so they never
    overlap the Greek-page harvest. But since v2, a range like '620a-622c'
    (matched whole by the ambiguous shape) positionally CONTAINS the Stephanus
    endpoint '622c' (matched alone by the stephanus shape). Yielding both would
    double-count the endpoint — once inside the range's later expansion, once as
    a standalone cell. So we collect the page's matches, drop any span contained
    in a longer one (keep the full range, drop the swallowed endpoint), and emit
    in text order. Emitting in position order also makes `seq` reflect true
    reading order, which is what the resolver's scope-tracking assumes.

    Per-page match counts are small and PAGE_CHUNK windowing bounds pathological
    pages, so collecting one page's matches is safe for memory."""
    cands = []
    for corpus, rx in (("bekker", BEKKER_SURE),
                       ("stephanus", STEPH_SURE),
                       ("ambiguous", AMBIGUOUS),
                       ("homer", HOMER_RX),
                       ("pindar", PINDAR_RX),
                       ("nt", NT_RX)):
        for m in rx.finditer(text):
            cands.append((m.start(), m.end(), corpus, m.group()))
    # Greedy longest-wins by start position: sort by (start asc, length desc);
    # keep a match only if it starts at or after the end of the last kept match.
    cands.sort(key=lambda c: (c[0], -(c[1] - c[0])))
    last_end = -1
    for s, e, corpus, g in cands:
        if s >= last_end:
            yield corpus, g, s, e
            last_end = e


def iter_page_matches(page):
    """Scan a page, chunking if it is pathologically long so we never hold a
    giant string's worth of match objects at once. Yields (corpus, match,
    abs_start, abs_end) with absolute offsets into the page."""
    n = len(page)
    if n <= PAGE_CHUNK:
        yield from iter_matches_in_text(page)
        return
    # pathological page: window through it with a small overlap
    start = 0
    while start < n:
        end = min(start + PAGE_CHUNK, n)
        chunk = page[start:end]
        for corpus, g, s, e in iter_matches_in_text(chunk):
            # drop matches that fall entirely in the overlap tail except on the
            # final chunk, to avoid double-emitting boundary matches
            if end < n and s >= (PAGE_CHUNK - PAGE_OVERLAP):
                continue
            yield corpus, g, start + s, start + e
        if end >= n:
            break
        start = end - PAGE_OVERLAP


def flatten(s):
    return " ".join(s.split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("delivery")
    ap.add_argument("metadata")
    ap.add_argument("--requested", default="request_item_ids.txt")
    ap.add_argument("--context", type=int, default=120)
    ap.add_argument("--max-records", type=int, default=0)
    ap.add_argument("--resume", action="store_true",
                    help="skip iids already present in an existing citations.tsv")
    args = ap.parse_args()

    for p in (args.delivery, args.metadata):
        if not os.path.exists(p):
            print(f"ERROR: file not found: {p}"); sys.exit(1)

    # load the request roster FIRST — it doubles as the metadata keep-filter,
    # so we index only our ~69k iids out of the 12.6M-record catalogue.
    requested = set()
    if args.requested and os.path.exists(args.requested):
        with open(args.requested) as fh:
            requested = {ln.strip() for ln in fh if ln.strip()}
        print(f"Request roster: {len(requested):,} iids.", flush=True)
    else:
        print("(!) No requested-id file; will index the FULL catalogue "
              "(heavy) and skip coverage. Pass --requested to fix.", flush=True)

    meta = load_metadata(args.metadata, keep_iids=requested or None)

    # --- resume support: learn which iids are already done ---
    done_iids = set()
    write_header = True
    open_mode = "w"
    if args.resume and os.path.exists("citations.tsv"):
        with open("citations.tsv", encoding="utf-8") as fh:
            next(fh, None)  # header
            for row in fh:
                tab = row.find("\t")
                if tab > 0:
                    done_iids.add(row[:tab])
        if done_iids:
            open_mode = "a"; write_header = False
            print(f"Resume: {len(done_iids):,} iids already in citations.tsv; "
                  f"skipping those.", flush=True)

    delivered_ids = set()
    summary = collections.Counter()       # (journal,year,corpus) -> int  (small)
    n_records = n_pages = n_matches = no_meta = 0
    big_pages = 0
    ctx = args.context

    out = open("citations.tsv", open_mode, encoding="utf-8")
    if write_header:
        out.write("iid\tjournal\tyear\tdoctype\tcorpus\tpage_index\t"
                  "char_offset\tseq\tmatch\tcontext\ttitle\n")

    try:
        with open_stream(args.delivery) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                n_records += 1
                if args.max_records and n_records > args.max_records:
                    n_records -= 1
                    break

                try:
                    rec = json.loads(line)
                except Exception:
                    continue

                iid = rec.get(DELIVERY_ID)
                if iid:
                    delivered_ids.add(iid)
                if args.resume and iid in done_iids:
                    rec = None
                    continue

                journal, year, doctype, title = meta.get(iid, ("?", "?", "?", ""))
                if iid not in meta:
                    no_meta += 1
                title = flatten(title)   # strip tabs/newlines so TSV stays intact

                pages = rec.get(DELIVERY_TEXT) or []
                seq = 0   # per-article running index, reading order, for scope-tracking
                for pi, page in enumerate(pages):
                    if not isinstance(page, str):
                        continue
                    n_pages += 1
                    if len(page) > PAGE_CHUNK:
                        big_pages += 1
                    plen = len(page)
                    for corpus, g, s, e in iter_page_matches(page):
                        n_matches += 1
                        context = flatten(page[max(0, s - ctx): min(plen, e + ctx)])
                        out.write(f"{iid}\t{journal}\t{year}\t{doctype}\t{corpus}\t"
                                  f"{pi}\t{s}\t{seq}\t{g}\t{context}\t{title}\n")
                        summary[(journal, year, corpus)] += 1
                        seq += 1

                # free the big object explicitly before next iteration
                rec = None

                if n_records % PROGRESS_EVERY == 0:
                    print(f"  …{n_records:,} records | {n_pages:,} pages | "
                          f"{n_matches:,} matches", flush=True)
                if n_records % FLUSH_EVERY == 0:
                    out.flush()
    finally:
        out.close()

    # --- summary tsv: distinct-article counts via a cheap 2nd pass on disk ---
    # count distinct iids per (journal,year,corpus) without holding iid sets in
    # the hot loop: stream the (now sorted-by-nothing) tsv once. To keep this
    # bounded too, we use a set keyed on (j,y,c,iid) hashes — still far smaller
    # than the full-text pass, and only touched here at the end.
    art = collections.defaultdict(set)
    with open("citations.tsv", encoding="utf-8") as fh:
        next(fh, None)
        for row in fh:
            parts = row.rstrip("\n").split("\t")
            if len(parts) < 6:
                continue
            i, j, y, _dt, c = parts[0], parts[1], parts[2], parts[3], parts[4]
            art[(j, y, c)].add(i)
    with open("citation_summary.tsv", "w", encoding="utf-8") as o:
        o.write("journal\tyear\tcorpus\tn_matches\tn_articles\n")
        for (j, y, c), n in sorted(summary.items()):
            o.write(f"{j}\t{y}\t{c}\t{n}\t{len(art.get((j,y,c), ()))}\n")

    # --- coverage report ---
    with open("coverage_report.txt", "w", encoding="utf-8") as o:
        missing = requested - delivered_ids if requested else set()
        extra   = delivered_ids - requested if requested else set()
        lines = [
            "COVERAGE — delivered vs requested",
            f"  requested : {len(requested):,}",
            f"  delivered : {len(delivered_ids):,}",
        ]
        if requested:
            lines.append(f"  matched   : {len(requested & delivered_ids):,}")
        lines += [f"  missing   : {len(missing):,}",
                  f"  extra     : {len(extra):,}", "",
                  f"  flagged drop {FLAGGED_MISSING}: "
                  f"{'CONFIRMED missing' if FLAGGED_MISSING in missing else 'NOT the missing one'}"]
        others = sorted(missing - {FLAGGED_MISSING})
        if others:
            lines.append(f"  (!) {len(others)} OTHER drop(s): " + ", ".join(others[:20]))
        elif requested:
            lines.append("  No silent drops: flagged item is the only omission.")
        o.write("\n".join(lines) + "\n")

    print("=" * 64)
    print(f"delivery records : {n_records:,}")
    print(f"pages scanned    : {n_pages:,}")
    print(f"citation matches : {n_matches:,}")
    print(f"records w/o metadata match: {no_meta:,}")
    if big_pages:
        print(f"pathological pages chunked: {big_pages:,}")
    by_corpus = collections.Counter()
    for (_, _, c), n in summary.items():
        by_corpus[c] += n
    for c, n in by_corpus.most_common():
        print(f"   {c:10s}: {n:,}")
    print("=" * 64)
    print(open("coverage_report.txt").read())
    print("Wrote citations.tsv, citation_summary.tsv, coverage_report.txt")


if __name__ == "__main__":
    main()