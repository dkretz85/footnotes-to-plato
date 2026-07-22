#!/usr/bin/env python3
"""
build_viewer_data.py — turn the local citation TSV + review queue + JSTOR
metadata into the small JSON files the "Footnotes to Plato" viewer loads.

Runs entirely on your machine. Reads the big local files, writes small derived
JSON. The 34 MB TSV and the ~381 MB metadata never leave your laptop, and the
confidential `context` column (verbatim full text) is DROPPED — it never enters
any output file. Only derived facts ship: work, book, page, section, journal,
year, DOI.

VIEW A MODEL (revised — see project decisions):
  The old `ceiling = resolved + queued` is GONE. The review queue's work
  attribution is non-exclusive: one ambiguous citation is filed under every
  candidate work (e.g. Apology AND Philebus AND Timaeus), so summing a work's
  whole queue into its ceiling multi-counts collisions and is incoherent.
  Instead each work gets:
    - floor           = resolved count (rock-solid lower bound)
    - band            = resolved + queued-rows-at-confidence >= --band-threshold
                        (a NARROW, honest extension: "reasonably sure these too")
    - unplaceable     = queued rows BELOW threshold (diffuse ambiguity; rendered
                        as an open-ended fade, NOT a bar to a false number)
    - collides_with   = collision-partner works parsed from the queue `reason`
    - resolution_rate = resolved / (resolved + queued)
    - tier            = "trustworthy" if rate >= --tier-threshold else "uncertain"

INPUTS (defaults point at ~/Downloads):
    resolved_with_books.tsv               citation rows (13 cols, tab-sep)
    review_queue.tsv                      queued candidates (14 cols; +reason)
    jstor_metadata_2026-07-18.jsonl.gz    catalogue (item_id -> title/DOI/...)
    collision_bands.json                  within-work shading overlay (copied as-is)

OUTPUTS (into --outdir, default ./viewer_data):
    view_a.json               per-work floor/band/unplaceable/tier/collides_with
    works_index.json          works list for the View B selector
    view_b/<work>.json        per-work section-grain profile (pooled + by-journal),
                              book-faceted for the four big works, + drill-in dots
                              with per-citation DOI links (deduped by iid)
    meta.json                 journals, year range, totals, thresholds, build stamp

Usage:
    python3 build_viewer_data.py
    python3 build_viewer_data.py --band-threshold 0.50 --tier-threshold 0.80
    python3 build_viewer_data.py --no-meta          # skip metadata join (DOIs blank)
    python3 build_viewer_data.py --no-queue         # skip queue (floor only)
"""
import sys, os, csv, gzip, json, re, argparse, datetime
from collections import defaultdict, Counter

import locus  # shared parser — single source of truth with derive_book.py

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))  # context column can be large

HOME = os.path.expanduser("~")
DEF_TSV   = os.path.join(HOME, "Downloads", "resolved_with_books.tsv")
DEF_QUEUE = os.path.join(HOME, "Downloads", "review_queue.tsv")
DEF_META  = os.path.join(HOME, "Downloads", "jstor_metadata_2026-07-18.jsonl.gz")
DEF_BANDS = os.path.join(HOME, "Downloads", "collision_bands.json")

# TSV columns (zero-based). Mirrors locus.WORK/MATCH/BOOK; names for the rest.
C_IID, C_JOURNAL, C_YEAR, C_DOCTYPE, C_CORPUS = 0, 1, 2, 3, 4
C_PAGE_INDEX, C_SEQ, C_MATCH, C_WORK, C_BOOK = 5, 6, 7, 8, 9
C_CONF, C_METHOD, C_CONTEXT = 10, 11, 12   # C_CONTEXT is NEVER emitted
C_REASON = 13   # queue-only trailing column

# candidates ['Apology', 'Philebus', 'Prior_Analytics', 'Timaeus']
CANDIDATES_RE = re.compile(r"candidates\s*\[([^\]]*)\]")
NAME_RE = re.compile(r"'([^']+)'|\"([^\"]+)\"")


def open_maybe_gz(path):
    with open(path, "rb") as fh:
        magic = fh.read(2)
    if magic == b"\x1f\x8b":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "rt", encoding="utf-8", errors="replace")


def safe_name(work):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in work)


def parse_candidates(reason):
    """Pull the candidate work list out of a queue reason string.
    Returns a list of work names, or [] if the pattern isn't present."""
    if not reason:
        return []
    m = CANDIDATES_RE.search(reason)
    if not m:
        return []
    names = []
    for a, b in NAME_RE.findall(m.group(1)):
        names.append(a or b)
    return names


# ---------------------------------------------------------------------------
# Pass 1: iids needed for the metadata join
# ---------------------------------------------------------------------------
def load_needed_iids(tsv_path):
    iids = set()
    with open(tsv_path, encoding="utf-8", newline="") as fh:
        r = csv.reader(fh, delimiter="\t")
        next(r, None)
        for row in r:
            if len(row) > C_IID and row[C_IID]:
                iids.add(row[C_IID])
    return iids


def journal_title(rec):
    j = rec.get("is_part_of")
    if isinstance(j, dict):
        return j.get("title") or j.get("name")
    return j


def build_meta_lookup(meta_path, needed_iids):
    lookup = {}
    if not needed_iids:
        return lookup
    with open_maybe_gz(meta_path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            iid = rec.get("item_id")
            if iid not in needed_iids:
                continue
            lookup[iid] = {
                "doi":     rec.get("ithaka_doi") or "",
                "title":   (rec.get("title") or "").strip(),
                "journal": journal_title(rec) or "",
                "year":    (str(rec.get("published_date") or "")[:4]),
                "author":  (rec.get("creators_string") or "").strip(),
            }
            if len(lookup) == len(needed_iids):
                break
    return lookup


# ---------------------------------------------------------------------------
# Queue aggregation for View A
# ---------------------------------------------------------------------------
def profile_queue(queue_path, band_threshold):
    """Return per-work:
        queued_total, band_extra (>= threshold), unplaceable (< threshold),
        collides_with (Counter of partner works)."""
    q_total = Counter()
    q_band = Counter()       # >= band_threshold
    q_unplaceable = Counter()  # < band_threshold
    collides = defaultdict(Counter)
    sample_parses = []
    if not os.path.exists(queue_path):
        return q_total, q_band, q_unplaceable, collides, sample_parses
    with open(queue_path, encoding="utf-8", newline="") as fh:
        r = csv.reader(fh, delimiter="\t")
        next(r, None)
        for row in r:
            if len(row) <= C_WORK or not row[C_WORK]:
                continue
            work = row[C_WORK]
            try:
                conf = float(row[C_CONF]) if len(row) > C_CONF else 0.0
            except ValueError:
                conf = 0.0
            reason = row[C_REASON] if len(row) > C_REASON else ""
            q_total[work] += 1
            if conf >= band_threshold:
                q_band[work] += 1
            else:
                q_unplaceable[work] += 1
            cands = parse_candidates(reason)
            for c in cands:
                if c != work:
                    collides[work][c] += 1
            if len(sample_parses) < 5 and cands:
                sample_parses.append((work, reason[:60], cands))
    return q_total, q_band, q_unplaceable, collides, sample_parses


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tsv", default=DEF_TSV)
    ap.add_argument("--queue", default=DEF_QUEUE)
    ap.add_argument("--meta", default=DEF_META)
    ap.add_argument("--bands", default=DEF_BANDS)
    ap.add_argument("--outdir", default="./viewer_data")
    ap.add_argument("--band-threshold", type=float, default=0.50,
                    help="queued rows with confidence >= this fold into the "
                         "narrow band above the floor (default 0.50)")
    ap.add_argument("--tier-threshold", type=float, default=0.80,
                    help="resolution rate >= this => 'trustworthy' tier, else "
                         "'uncertain'. Default 0.80 = publication-grade: reserve "
                         "'trustworthy' for the high-resolution mass, not merely "
                         "above-half works.")
    ap.add_argument("--no-meta", action="store_true")
    ap.add_argument("--no-queue", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.tsv):
        sys.exit(f"ERROR: TSV not found: {args.tsv}")

    os.makedirs(args.outdir, exist_ok=True)
    vb_dir = os.path.join(args.outdir, "view_b")
    os.makedirs(vb_dir, exist_ok=True)

    # ---- pass 1: iids -------------------------------------------------------
    print("Pass 1/4: scanning TSV for iids ...", file=sys.stderr)
    needed = load_needed_iids(args.tsv)
    print(f"  {len(needed):,} distinct iids referenced", file=sys.stderr)

    # ---- pass 2: metadata ---------------------------------------------------
    meta = {}
    if not args.no_meta:
        if not os.path.exists(args.meta):
            print(f"  WARNING: metadata not found ({args.meta}); DOIs blank.",
                  file=sys.stderr)
        else:
            print("Pass 2/4: streaming metadata for those iids ...", file=sys.stderr)
            meta = build_meta_lookup(args.meta, needed)
            print(f"  matched {len(meta):,}/{len(needed):,} iids", file=sys.stderr)
    else:
        print("Pass 2/4: skipped (--no-meta)", file=sys.stderr)

    # ---- pass 3: queue ------------------------------------------------------
    if not args.no_queue:
        print("Pass 3/4: profiling review queue ...", file=sys.stderr)
        q_total, q_band, q_unpl, collides, samples = profile_queue(
            args.queue, args.band_threshold)
        if not os.path.exists(args.queue):
            print(f"  WARNING: queue not found ({args.queue}); floor only.",
                  file=sys.stderr)
        else:
            print(f"  {sum(q_total.values()):,} queued rows across "
                  f"{len(q_total)} works", file=sys.stderr)
            if samples:
                print("  sample candidate parses (sanity check):", file=sys.stderr)
                for w, rs, cs in samples:
                    print(f"    {w}: {cs}", file=sys.stderr)
    else:
        q_total = q_band = q_unpl = Counter(); collides = {}
        print("Pass 3/4: skipped (--no-queue)", file=sys.stderr)

    # ---- pass 4: aggregate citations ---------------------------------------
    print("Pass 4/4: aggregating citations ...", file=sys.stderr)
    work_resolved = Counter()
    work_iids     = defaultdict(set)
    # View A filtering: floor citations broken out by journal and year, plus the
    # distinct-article equivalent. FLOOR ONLY — queued rows are deliberately
    # excluded. A queued row's *work* attribution is what's uncertain, and
    # spreading it across a year axis would attribute a year to a citation we
    # can't attribute to a work at all. The fade stays a whole-corpus quantity.
    work_jy       = defaultdict(lambda: defaultdict(Counter))   # work -> journal -> year -> n
    work_jy_iids  = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    section_cells = defaultdict(lambda: defaultdict(
        lambda: {"pooled": 0, "by_journal": Counter(), "iids": set()}))
    dots = defaultdict(list)
    journals_seen = Counter()
    years_seen = Counter()
    all_works = Counter()

    with open(args.tsv, encoding="utf-8", newline="") as fh:
        r = csv.reader(fh, delimiter="\t")
        next(r, None)
        for row in r:
            if len(row) <= C_CONTEXT:
                row = row + [""] * (C_CONTEXT + 1 - len(row))
            iid = row[C_IID]; journal = row[C_JOURNAL]; year = row[C_YEAR]
            work = row[C_WORK]; book = row[C_BOOK] or ""; match = row[C_MATCH]
            # row[C_CONTEXT] is deliberately never read into any output.
            if not work:
                continue
            journals_seen[journal] += 1
            years_seen[year] += 1
            all_works[work] += 1
            work_resolved[work] += 1
            if iid:
                work_iids[work].add(iid)
            # Counted BEFORE the parse_locus early-continue below, so these
            # sum exactly to `floor` (which is work_resolved). Rows whose locus
            # can't be parsed still belong to the work, journal and year.
            if journal and year:
                work_jy[work][journal][year] += 1
                if iid:
                    work_jy_iids[work][journal][year].add(iid)
            page, sec, line = locus.parse_locus(match)
            if page is None:
                continue
            sec = sec or "a"
            cell = section_cells[work][(book, page, sec)]
            cell["pooled"] += 1
            cell["by_journal"][journal] += 1
            if iid:
                cell["iids"].add(iid)
            m = meta.get(iid, {})
            dots[work].append({
                "book": book, "page": page, "section": sec, "line": line,
                "journal": journal, "year": year, "iid": iid,
                "doi": m.get("doi", ""), "title": m.get("title", ""),
                "author": m.get("author", ""),
            })

    # ---- View A -------------------------------------------------------------
    view_a = []
    for work in all_works:
        resolved = work_resolved[work]
        qt = q_total.get(work, 0)
        band_extra = q_band.get(work, 0)
        unplaceable = q_unpl.get(work, 0)
        denom = resolved + qt
        rate = (resolved / denom) if denom else 1.0
        tier = "trustworthy" if rate >= args.tier_threshold else "uncertain"
        partners = [w for w, _ in collides.get(work, Counter()).most_common(6)]
        view_a.append({
            "work": work,
            "floor": resolved,
            "band": resolved + band_extra,      # narrow honest extension
            "band_extra": band_extra,
            "unplaceable": unplaceable,         # diffuse; render as open fade
            "queued_total": qt,
            "resolution_rate": round(rate, 3),
            "tier": tier,
            "distinct_articles": len(work_iids[work]),
            "faceted": work in locus.FACETED_WORKS,
            "collides_with": partners,
        })
    # sort: tier first (trustworthy above), then floor desc
    view_a.sort(key=lambda d: (d["tier"] != "trustworthy", -d["floor"]))
    with open(os.path.join(args.outdir, "view_a.json"), "w", encoding="utf-8") as f:
        json.dump(view_a, f, ensure_ascii=False, indent=1)

    # ---- View A filter matrix (SEPARATE FILE) -------------------------------
    # Sparse journal x year counts per work, FLOOR ONLY. Kept out of view_a.json
    # because it is ~25x that file's size: view_a.json must stay small so the
    # first paint is instant. The viewer fetches this only when the user first
    # touches the filter.
    #
    # FLOOR ONLY is deliberate. Queued rows are excluded because a queued row's
    # *work* attribution is the uncertain part — giving it a year would let the
    # viewer scale `unplaceable` along a time axis, asserting per-work-per-year
    # numbers the pipeline cannot support. `unplaceable` therefore has NO year
    # dimension, and the viewer must hold the fade at full width (greyed) when
    # filtering rather than scaling it.
    filter_matrix = {}
    for work in all_works:
        bjy = {j: dict(sorted(yrs.items()))
               for j, yrs in sorted(work_jy.get(work, {}).items()) if yrs}
        bjy_art = {j: {y: len(s) for y, s in sorted(yrs.items())}
                   for j, yrs in sorted(work_jy_iids.get(work, {}).items()) if yrs}
        filter_matrix[work] = {"citations": bjy, "articles": bjy_art}
    with open(os.path.join(args.outdir, "view_a_filter.json"), "w",
              encoding="utf-8") as f:
        json.dump(filter_matrix, f, ensure_ascii=False, separators=(",", ":"))

    # ---- resolution-rate histogram to stderr (for tier-cut sanity) ---------
    print("\nResolution-rate distribution (each '#' ~ a work):", file=sys.stderr)
    buckets = Counter()
    for d in view_a:
        b = int(d["resolution_rate"] * 10) * 10  # 0,10,...,100
        b = min(b, 90)
        buckets[b] += 1
    for lo in range(0, 100, 10):
        n = buckets.get(lo, 0)
        marker = " <-- tier cut" if lo <= args.tier_threshold*100 < lo+10 else ""
        print(f"  {lo:3d}-{lo+9:3d}%  {'#'*n} ({n}){marker}", file=sys.stderr)
    n_trust = sum(1 for d in view_a if d["tier"] == "trustworthy")
    print(f"  trustworthy: {n_trust}   uncertain: {len(view_a)-n_trust}   "
          f"(cut at {args.tier_threshold:.0%})", file=sys.stderr)

    # ---- works_index.json ---------------------------------------------------
    works_index = [{
        "work": w, "citations": all_works[w],
        "distinct_articles": len(work_iids[w]),
        "faceted": w in locus.FACETED_WORKS,
        "tier": next(d["tier"] for d in view_a if d["work"] == w),
        "file": f"view_b/{safe_name(w)}.json",
    } for w, _ in all_works.most_common()]
    with open(os.path.join(args.outdir, "works_index.json"), "w",
              encoding="utf-8") as f:
        json.dump(works_index, f, ensure_ascii=False, indent=1)

    # ---- View B files -------------------------------------------------------
    for work in all_works:
        cells = section_cells[work]
        cell_list = []
        for (book, page, sec), c in cells.items():
            cell_list.append({
                "book": book, "page": page, "section": sec,
                "count": c["pooled"], "articles": len(c["iids"]),
                "by_journal": dict(c["by_journal"]),
            })
        cell_list.sort(key=lambda d: (d["book"], d["page"], d["section"]))
        # Dots are the per-citation drill-in records. They used to be deduped on
        # (iid, page, section, line), which silently DROPPED genuine repeat
        # citations — the same article citing the same line more than once. That
        # made sum(cells.count) and len(dots) disagree by ~18-22% (NE: 6,730 vs
        # 5,499), so any viewer filter recomputing from dots showed a y-axis
        # ~20% below the unfiltered totals for reasons unrelated to the filter.
        # Dots now carry every resolved row, exactly matching cells.count.
        # Distinct-article counts are computed by the VIEWER from iid, so no
        # information is lost by keeping duplicates here.
        dot_list = list(dots[work])
        out = {
            "work": work, "faceted": work in locus.FACETED_WORKS,
            "tier": next(d["tier"] for d in view_a if d["work"] == work),
            "cells": cell_list, "dots": dot_list,
        }
        with open(os.path.join(vb_dir, f"{safe_name(work)}.json"),
                  "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)

    # ---- meta.json ----------------------------------------------------------
    years_int = sorted(int(y) for y in years_seen if y.isdigit())
    meta_out = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "band_threshold": args.band_threshold,
        "tier_threshold": args.tier_threshold,
        "journals": [j for j, _ in journals_seen.most_common()],
        "journal_counts": dict(journals_seen),
        "year_min": years_int[0] if years_int else None,
        "year_max": years_int[-1] if years_int else None,
        "year_histogram": {str(y): years_seen[str(y)] for y in years_int},
        "total_citations": sum(all_works.values()),
        "total_queued": sum(q_total.values()),
        "distinct_works": len(all_works),
        "faceted_works": sorted(locus.FACETED_WORKS),
        "doi_coverage": (round(sum(1 for d in meta.values() if d["doi"]) /
                               len(meta), 3) if meta else None),
    }
    with open(os.path.join(args.outdir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta_out, f, ensure_ascii=False, indent=1)

    # ---- collision_bands.json passthrough ----------------------------------
    if os.path.exists(args.bands):
        with open(args.bands, encoding="utf-8") as f:
            bands = json.load(f)
        with open(os.path.join(args.outdir, "collision_bands.json"),
                  "w", encoding="utf-8") as f:
            json.dump(bands, f, ensure_ascii=False, indent=1)
    else:
        print(f"  note: collision_bands.json not found at {args.bands}.",
              file=sys.stderr)

    print(f"\nDone. Wrote {args.outdir}/", file=sys.stderr)
    print(f"  {meta_out['total_citations']:,} citations, "
          f"{meta_out['total_queued']:,} queued, "
          f"{meta_out['distinct_works']} works, "
          f"{len(meta_out['journals'])} journals", file=sys.stderr)

    # ---- invariant self-checks ---------------------------------------------
    # These caught a real bug (dots deduped against cells). Cheap to run, and a
    # loud failure here beats a silently wrong y-axis in the viewer.
    print("\nSelf-checks:", file=sys.stderr)
    problems = []
    for work in all_works:
        cells_tot = sum(c["pooled"] for c in section_cells[work].values())
        dots_tot  = len(dots[work])
        if cells_tot != dots_tot:
            problems.append(f"{work}: sum(cells.count)={cells_tot} != len(dots)={dots_tot}")
        jy_tot = sum(sum(y.values()) for y in work_jy.get(work, {}).values())
        floor  = work_resolved[work]
        # by_journal_year can legitimately fall short of floor when a row has a
        # blank journal or year; report the gap rather than asserting equality.
        if jy_tot > floor:
            problems.append(f"{work}: by_journal_year={jy_tot} EXCEEDS floor={floor}")
    tot_jy = sum(sum(sum(y.values()) for y in work_jy[w].values()) for w in work_jy)
    tot_floor = sum(work_resolved.values())
    print(f"  cells/dots agreement: "
          f"{'OK' if not any('!=' in p for p in problems) else 'FAILED'}", file=sys.stderr)
    print(f"  by_journal_year total {tot_jy:,} of floor {tot_floor:,} "
          f"({tot_jy/tot_floor:.1%} — remainder is rows with blank journal/year)",
          file=sys.stderr)
    if problems:
        for p in problems[:10]:
            print(f"  PROBLEM: {p}", file=sys.stderr)
        if len(problems) > 10:
            print(f"  ... and {len(problems)-10} more", file=sys.stderr)
    else:
        print("  all per-work invariants hold", file=sys.stderr)

    # size report — by_journal_year is new; make its cost visible
    va_path = os.path.join(args.outdir, "view_a.json")
    fm_path = os.path.join(args.outdir, "view_a_filter.json")
    print(f"  view_a.json: {os.path.getsize(va_path)/1024:.0f} KB "
          f"(+ view_a_filter.json {os.path.getsize(fm_path)/1024:.0f} KB, lazy-loaded)",
          file=sys.stderr)


if __name__ == "__main__":
    main()
