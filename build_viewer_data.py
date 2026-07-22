#!/usr/bin/env python3
"""
build_viewer_data.py — turn the local citation TSV + review queue + JSTOR
metadata into the small JSON files the "Footnotes to Plato" viewer loads.

Runs entirely on your machine. Reads the big local files, writes small derived
JSON. The 34 MB TSV and the ~381 MB metadata never leave your laptop, and the
confidential `context` column (verbatim full text) is DROPPED — it never enters
any output file. Only derived facts ship: work, book, page, section, journal,
year, DOI.

VIEW A MODEL (revised twice — see project decisions):
  The old `ceiling = resolved + queued` is GONE, but NOT for the reason this
  docstring previously gave. The earlier text claimed queue filing was
  non-exclusive (one citation filed under every candidate). That was WRONG, and
  an external audit caught it: per-work `queued_total` sums to exactly the queue
  size (50,450 filed rows + 136 blank = 50,586), which could not happen under
  non-exclusive filing. Each queued row carries exactly ONE work_id.

  The real problem is the filing RULE. In resolve_citations.py every queueing
  branch files under `sorted(candidates)[0]` — the ALPHABETICALLY FIRST candidate:
      name_multi_candidate  -> sorted(name-matched candidates)[0]
      name_range_conflict   -> sorted(range candidates)[0]
      unresolved / cross_system_unresolved -> sorted(range candidates)[0]
  So a shared ambiguous citation lands on whichever candidate sorts first, and
  that work alone absorbs it: its `unplaceable` inflates and its resolution-rate
  denominator grows, while its collision partners stay clean. Apology (0.255) and
  Meno (0.256) are largely artifacts of sorting before Crito/Charmides and
  Menexenus/Phaedo/Timaeus respectively. Summing that into a ceiling would be
  reading an alphabetical accident as a measurement.

  FIX: `unplaceable` is now computed from CANDIDATE-SET MEMBERSHIP — "queue rows
  whose candidate set includes this work" — parsed from the same `reason` column
  already used for collides_with. That quantity legitimately multi-counts across
  works (a shared citation really could belong to each), which is exactly right
  for a per-work upper gesture, and it is independent of filing order.

  Queue dispositions (project decisions, recorded):
    - the four candidate-bearing methods (name_range_conflict,
      cross_system_unresolved, unresolved, name_multi_candidate; 45,676 rows)
      contribute to every work in their candidate set.
    - scope_range_mismatch (3,668 rows) is EXCLUDED from unplaceable entirely.
      Scope named a work and the number falls outside that work's range: that is
      a confident NEGATIVE, not unplaceable mass. Filing confident negatives
      under the very work they were proven not to belong to would inflate the
      fade that is supposed to mean "could be more of this work". They stay in
      the queue file; they just stop contributing to any work's uncertainty.
      (NB "not Republic" is not "not a citation" — they may be real loci of some
      other work; we simply have no candidate set to say which.)
    - scope_inherited (1,242 rows) may be PROMOTED to resolved, but only where
      page+section-letter admit exactly one work. See promote_scope.py; the
      promotable share is small because 903 of 1,363 Bekker pages collide with
      Stephanus, and in that zone an a/b column is never unique.

  Each work gets:
    - floor           = resolved count (rock-solid lower bound)
    - band            = resolved + queued-rows-at-confidence >= --band-threshold
                        (a NARROW, honest extension: "reasonably sure these too")
    - unplaceable     = candidate-set membership below threshold (diffuse
                        ambiguity; rendered as an open-ended fade, NOT a bar)
    - collides_with   = collision-partner works parsed from the queue `reason`
    - resolution_rate = resolved / (resolved + queued-FILED)  [exclusive]
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
SCOPE_METHODS_EXCLUDED = {"scope_range_mismatch"}


def profile_queue(queue_path, band_threshold):
    """Per-work queue profile, computed by CANDIDATE-SET MEMBERSHIP rather than
    by which work the row happened to be filed under.

    Filing is exclusive and alphabetical (sorted(candidates)[0] in every queueing
    branch of resolve_citations.py), so filed-work counts measure sort order as
    much as ambiguity. Instead every row contributes to EVERY work in its
    candidate set. That deliberately multi-counts across works: a citation that
    could be Meno or Phaedo or Timaeus really could belong to each, which is the
    correct semantics for a per-work upper gesture.

    Rows whose method is in SCOPE_METHODS_EXCLUDED are confident negatives and
    contribute to nothing. Rows with no parseable candidate list (the scope_*
    methods) fall back to their filed work, which for scope_inherited is the
    single work scope actually named.

    TWO DISTINCT QUANTITIES — do not merge them:

      CANDIDATE-SET counts (q_cand_*) multi-count. One shared row lands on every
      work that could own it. This is right for the FADE: "how much ambiguous
      mass could belong here?" A citation that might be Meno or Phaedo or
      Timaeus really could belong to each, so each gets the full weight.

      FILED counts (q_filed) do not multi-count: one row, one work, as
      resolve_citations.py filed it. This is right for the RESOLUTION RATE,
      which is a PROPORTION — resolved / (resolved + competing rows). Feeding a
      multi-counted denominator into a rate destroys it: with a mean 3.09 works
      per queued row, every denominator inflates ~3x and every rate collapses.
      A first attempt at this fix did exactly that and sent Republic from 0.95
      to 0.508 and Minos from 1.00 to 0.082, flipping 19 works out of the
      trustworthy tier in one direction. All-one-way movement is the signature
      of a broken denominator, not a corrected one.

      Filing order still biases the rate (that is Finding 1, and it is real),
      but the answer is to REPORT the bias, not to substitute a quantity that
      is not a proportion. See `filed_share` in view_a.json: the fraction of a
      work's filed queue rows on which it was the alphabetically-first
      candidate and therefore absorbed the collision.

    Returns per-work Counters:
        q_filed       rows FILED under this work (exclusive; denominator of rate)
        q_cand_total  rows naming this work as a candidate (multi-counted)
        q_cand_band   those at confidence >= band_threshold
        q_cand_unpl   those below it  (the fade)
        collides      Counter of partner works
      plus diagnostics: sample_parses, stats dict.
    """
    q_filed = Counter()
    q_cand_total = Counter()
    q_cand_band = Counter()
    q_cand_unpl = Counter()
    collides = defaultdict(Counter)
    sample_parses = []
    stats = Counter()
    if not os.path.exists(queue_path):
        return (q_filed, q_cand_total, q_cand_band, q_cand_unpl, collides,
                sample_parses, stats)
    with open(queue_path, encoding="utf-8", newline="") as fh:
        r = csv.reader(fh, delimiter="\t")
        next(r, None)
        for row in r:
            stats["rows_read"] += 1
            if len(row) <= C_WORK or not row[C_WORK]:
                stats["blank_work_id"] += 1
                continue
            filed = row[C_WORK]
            method = row[C_METHOD] if len(row) > C_METHOD else ""
            if method in SCOPE_METHODS_EXCLUDED:
                stats["excluded_confident_negative"] += 1
                continue
            try:
                conf = float(row[C_CONF]) if len(row) > C_CONF else 0.0
            except ValueError:
                conf = 0.0
            reason = row[C_REASON] if len(row) > C_REASON else ""
            cands = parse_candidates(reason)
            if cands:
                stats["rows_with_candidates"] += 1
                targets = sorted(set(cands))
            else:
                # scope_* rows carry no candidate list; scope named one work.
                stats["rows_fallback_to_filed"] += 1
                targets = [filed]

            # --- exclusive: one row, one work. Denominator of resolution_rate.
            q_filed[filed] += 1
            if len(targets) > 1 and filed == targets[0]:
                stats["filed_as_first_candidate"] += 1

            # --- multi-counted: candidate-set membership. Drives the fade.
            stats["attributions"] += len(targets)
            for w in targets:
                q_cand_total[w] += 1
                if conf >= band_threshold:
                    q_cand_band[w] += 1
                else:
                    q_cand_unpl[w] += 1
                for c in targets:
                    if c != w:
                        collides[w][c] += 1
            if len(sample_parses) < 5 and cands:
                sample_parses.append((filed, reason[:60], cands))
    return (q_filed, q_cand_total, q_cand_band, q_cand_unpl, collides,
            sample_parses, stats)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tsv", default=DEF_TSV)
    ap.add_argument("--queue", default=DEF_QUEUE)
    ap.add_argument("--meta", default=DEF_META)
    ap.add_argument("--bands", default=DEF_BANDS)
    ap.add_argument("--small-n-threshold", type=int, default=100,
                    help="works with fewer placed citations than this are "
                         "flagged small_n: their resolution rate rests on too "
                         "little evidence to carry tier confidence (default 100)")
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
        (q_filed, q_cand_total, q_cand_band, q_cand_unpl, collides,
         samples, qstats) = profile_queue(args.queue, args.band_threshold)
        if not os.path.exists(args.queue):
            print(f"  WARNING: queue not found ({args.queue}); floor only.",
                  file=sys.stderr)
        else:
            print(f"  {sum(q_filed.values()):,} queued rows across "
                  f"{len(q_filed)} works", file=sys.stderr)

            # ---- invariants for the candidate-set quantity ------------------
            # A bad run should announce itself (the data page advertises this).
            rr  = qstats["rows_read"]
            blank = qstats["blank_work_id"]
            neg = qstats["excluded_confident_negative"]
            wc  = qstats["rows_with_candidates"]
            fb  = qstats["rows_fallback_to_filed"]
            att = qstats["attributions"]
            print(f"  queue invariants:", file=sys.stderr)
            print(f"    rows read                     : {rr:,}", file=sys.stderr)
            print(f"    blank work_id (skipped)       : {blank:,}", file=sys.stderr)
            print(f"    confident negatives (dropped) : {neg:,}"
                  f"  [scope_range_mismatch]", file=sys.stderr)
            print(f"    rows with candidate sets      : {wc:,}", file=sys.stderr)
            print(f"    rows falling back to filed    : {fb:,}", file=sys.stderr)
            print(f"    total attributions            : {att:,}"
                  f"  (multi-counting is EXPECTED here)", file=sys.stderr)
            accounted = blank + neg + wc + fb
            if accounted != rr:
                print(f"    !! ACCOUNTING MISMATCH: {accounted:,} != {rr:,}",
                      file=sys.stderr)
            if wc and att <= wc + fb:
                print(f"    !! attributions did not exceed rows — candidate-set "
                      f"parsing may have failed", file=sys.stderr)
            filed_total = sum(q_filed.values())
            cand_total = sum(q_cand_total.values())
            print(f"    filed rows (rate denominator) : {filed_total:,}",
                  file=sys.stderr)
            print(f"    candidate attributions (fade) : {cand_total:,}",
                  file=sys.stderr)
            expect_filed = rr - blank - neg
            if filed_total != expect_filed:
                print(f"    !! FILED COUNT WRONG: {filed_total:,} != "
                      f"{expect_filed:,}; rates would be invalid",
                      file=sys.stderr)
            else:
                print(f"    filed count checks out (= rows - blank - negatives)",
                      file=sys.stderr)
            first = qstats["filed_as_first_candidate"]
            if wc:
                print(f"    filed as FIRST of >1 candidates: {first:,} "
                      f"({first / wc * 100:.1f}% of multi-candidate rows)"
                      f"  <- Finding 1 bias, now reported per work",
                      file=sys.stderr)
            avg = att / max(wc + fb, 1)
            print(f"    mean works per queued row     : {avg:.2f}", file=sys.stderr)
            if samples:
                print("  sample candidate parses (sanity check):", file=sys.stderr)
                for w, rs, cs in samples:
                    print(f"    {w}: {cs}", file=sys.stderr)
    else:
        q_filed = q_cand_total = q_cand_band = q_cand_unpl = Counter()
        collides = {}; qstats = Counter()
        print("Pass 3/4: skipped (--no-queue)", file=sys.stderr)

    # ---- pass 4: aggregate citations ---------------------------------------
    print("Pass 4/4: aggregating citations ...", file=sys.stderr)
    work_resolved = Counter()
    work_iids     = defaultdict(set)
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

    # ---- collision bands, loaded early so View A can carry them -------------
    # Audit Finding 3: collision_bands.json was built precisely to caveat works
    # whose under-resolution is LOCALISED to a page range, was copied through by
    # this script, and was then never rendered. Attaching it per work here so the
    # viewer cannot quietly ignore it again.
    bands_by_work = defaultdict(list)
    if os.path.exists(args.bands):
        try:
            with open(args.bands, encoding="utf-8") as f:
                _b = json.load(f)
            for e in _b.get("bands", []):
                bands_by_work[e["work"]].append({
                    "start": e["band_start"],
                    "end": e["band_end"],
                    "resolved_share": e.get("resolved_share"),
                    "est_missing": e.get("est_missing", 0),
                })
            for w in bands_by_work:
                bands_by_work[w].sort(key=lambda d: d["start"])
            print(f"  collision bands: {sum(len(v) for v in bands_by_work.values())} "
                  f"across {len(bands_by_work)} works", file=sys.stderr)
        except Exception as e:
            print(f"  WARNING: could not read bands: {e}", file=sys.stderr)

    # ---- View A -------------------------------------------------------------
    view_a = []
    for work in all_works:
        resolved = work_resolved[work]
        # RATE uses the EXCLUSIVE filed count: a proportion needs a denominator
        # that counts each row once. Candidate-set membership multi-counts ~3x
        # and is not a proportion.
        filed_q = q_filed.get(work, 0)
        denom = resolved + filed_q
        rate = (resolved / denom) if denom else 1.0
        # FADE uses candidate-set membership: how much ambiguous mass could
        # belong here, counting shared rows in full for every candidate.
        cand_q = q_cand_total.get(work, 0)
        band_extra = q_cand_band.get(work, 0)
        unplaceable = q_cand_unpl.get(work, 0)
        tier = "trustworthy" if rate >= args.tier_threshold else "uncertain"
        partners = [w for w, _ in collides.get(work, Counter()).most_common(6)]
        view_a.append({
            "work": work,
            "floor": resolved,
            "band": resolved + band_extra,      # narrow honest extension
            "band_extra": band_extra,
            "unplaceable": unplaceable,         # diffuse; render as open fade
            "queued_filed": filed_q,            # exclusive; denominator of rate
            "queued_as_candidate": cand_q,      # multi-counted; drives the fade
            "queued_total": filed_q,            # back-compat alias
            "resolution_rate": round(rate, 3),
            "tier": tier,
            "distinct_articles": len(work_iids[work]),
            "faceted": work in locus.FACETED_WORKS,
            "collides_with": partners,
            # Finding 1 made visible rather than hidden: of the queue rows filed
            # under this work, what fraction did it win by sorting first among
            # >1 candidates? High values mean this work's rate is depressed by
            # alphabetical luck, not by being harder to place.
            "filed_share_of_candidates": (round(filed_q / cand_q, 3)
                                          if cand_q else None),
            # Localised under-resolution (Finding 3). Empty list = no band-level
            # pattern detected above threshold, NOT proof of even coverage.
            "collision_bands": bands_by_work.get(work, []),
            "band_est_missing": sum(b["est_missing"]
                                    for b in bands_by_work.get(work, [])),
            # Small-n flag (Finding 3): the tier conflates RATE with SAMPLE SIZE.
            # Minos (floor 30, rate 1.00) otherwise sits in "publication grade"
            # beside Republic (floor 12,350). A rate off 30 citations is noise.
            "small_n": resolved < args.small_n_threshold,
        })
    # sort: tier first (trustworthy above), then floor desc
    view_a.sort(key=lambda d: (d["tier"] != "trustworthy", -d["floor"]))
    with open(os.path.join(args.outdir, "view_a.json"), "w", encoding="utf-8") as f:
        json.dump(view_a, f, ensure_ascii=False, indent=1)

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
    # ---- tier-flip report vs a previous view_a.json (audit remediation #2) --
    # Candidate-set unplaceable changes resolution-rate denominators, so tiers
    # can move. Print exactly which, so the change is on the record.
    prev_path = os.path.join(args.outdir, "view_a.prev.json")
    if os.path.exists(prev_path):
        try:
            with open(prev_path, encoding="utf-8") as f:
                prev = {d["work"]: d for d in json.load(f)}
            flips = []
            for d in view_a:
                o = prev.get(d["work"])
                if o and o.get("tier") != d["tier"]:
                    flips.append((d["work"], o["tier"], d["tier"],
                                  o.get("resolution_rate"), d["resolution_rate"]))
            print(f"\n  TIER FLIPS vs view_a.prev.json: {len(flips)}", file=sys.stderr)
            for w, t0, t1, r0, r1 in sorted(flips, key=lambda x: x[0]):
                print(f"    {w:30s} {t0:12s} -> {t1:12s}  rate {r0} -> {r1}",
                      file=sys.stderr)
            if not flips:
                print("    (none — tiers are ROBUST to the candidate-set "
                      "recomputation; that is a strong sentence for the "
                      "methods page)", file=sys.stderr)
        except Exception as e:
            print(f"  (tier-flip report skipped: {e})", file=sys.stderr)
    else:
        print(f"\n  (no {os.path.basename(prev_path)}; copy the old view_a.json "
              f"there to get a tier-flip report)", file=sys.stderr)

    # ---- Finding 3 reporting ------------------------------------------------
    smalls = [d for d in view_a if d["small_n"] and d["tier"] == "trustworthy"]
    if smalls:
        print(f"\n  SMALL-N works inside the trustworthy tier "
              f"(< {args.small_n_threshold} citations): {len(smalls)}",
              file=sys.stderr)
        for d in sorted(smalls, key=lambda x: x["floor"]):
            print(f"    {d['work']:28s} floor {d['floor']:>5,}  "
                  f"rate {d['resolution_rate']:.3f}", file=sys.stderr)
        print("    These clear the tier cut on very little evidence; the viewer "
              "marks them.", file=sys.stderr)
    banded = [d for d in view_a if d["collision_bands"]]
    if banded:
        tb = [d for d in banded if d["tier"] == "trustworthy"]
        print(f"\n  works with LOCALISED under-resolution: {len(banded)} "
              f"({len(tb)} of them in the trustworthy tier)", file=sys.stderr)
        for d in sorted(banded, key=lambda x: -x["band_est_missing"])[:6]:
            rng = ", ".join(f"{b['start']}-{b['end']}" for b in d["collision_bands"])
            print(f"    {d['work']:24s} {len(d['collision_bands'])} band(s) "
                  f"~{d['band_est_missing']:,} missing  [{rng}]", file=sys.stderr)

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
        seen = set(); dot_list = []
        for d in dots[work]:
            k = (d["iid"], d["page"], d["section"], d["line"])
            if k in seen:
                continue
            seen.add(k); dot_list.append(d)
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
        # Exclusive: one row, one work. Reconciles with review_queue.tsv
        # (rows - blank - confident negatives). This is the number to compare
        # against the queue file.
        "total_queued": sum(q_filed.values()),
        # Multi-counted candidate attributions, which drive the per-work fade.
        # EXPECTED to exceed total_queued (~3x); not a row count.
        "total_candidate_attributions": sum(q_cand_total.values()),
        "distinct_works": len(all_works),
        "faceted_works": sorted(locus.FACETED_WORKS),
        # Audit finding 5: this divided by len(meta) — the iids we MATCHED in
        # the catalogue — so unmatched iids vanished from the denominator and
        # coverage read high. The honest denominator is every iid the corpus
        # needs a link for.
        "doi_coverage": (round(sum(1 for d in meta.values() if d["doi"]) /
                               len(needed), 3) if needed else None),
        "doi_coverage_of_matched": (round(sum(1 for d in meta.values() if d["doi"]) /
                               len(meta), 3) if meta else None),
        "meta_match_rate": (round(len(meta) / len(needed), 3) if needed else None),
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


if __name__ == "__main__":
    main()
