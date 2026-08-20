#!/usr/bin/env python3
"""
promote_scope.py — decide which `scope_inherited` queue rows can honestly be
promoted to resolved.

WHY THIS EXISTS
---------------
`scope_inherited` rows (1,242 of the 50,586-row queue) are cases where a nearby
work-name established scope, the cited number falls INSIDE that work's range
(resolve_citations.py checks `_work_contains` before emitting this method), and
the only thing that failed was the distance-decay confidence gate
(`--scope-accept`, default 0.83; see the decay at resolve_citations.py:490).

The argument for promoting them: the work is named, the number is in range, so
if nothing else could cover that number, confidence should be high.

That argument is sound ONLY where the number admits exactly one work. It does
not hold generally, for two separate reasons:

  1. STEPHANUS SELF-COLLISION. Stephanus pagination resets per volume, so 52%
     of Stephanus pages (514 of 986) are covered by more than one dialogue, up
     to three deep. 29 dialogues — Meno, Timaeus, Apology, Gorgias, Phaedrus,
     Symposium, Theaetetus among them — have NO page uniquely their own.

  2. CROSS-SYSTEM COLLISION. Bekker pagination is unique within Aristotle, but
     903 of its 1,363 pages (66%) also exist as Stephanus pages. 26 treatises
     sit ENTIRELY inside that zone: Physics, De Anima, Posterior Analytics,
     Topics, Categories, Historia Animalium ... For a bare number in that zone
     with an a/b column, the candidate set is NEVER unique — measured at 0/903
     pages. Only works above Stephanus p. 992 (Metaphysics, NE, EE, Politics,
     Rhetoric, Poetics) are unambiguous by number alone.

The section letter helps, but only in one direction: Bekker has columns a/b
only, so a letter in c/d/e rules Bekker out entirely. A letter of a/b rules out
nothing.

THE RULE IMPLEMENTED HERE
-------------------------
Promote a scope_inherited row iff the candidate set implied by (page, letter,
corpus) contains exactly ONE work, and that work is the one scope inherited.
Everything else stays queued.

This is deliberately conservative. It reports before it writes, and by default
writes nothing.

NOTE ON `corpus`: the row's own corpus column is authoritative — it is set
upstream in build_citation_db.py by citation format, and may already encode a
judgement this script cannot see. We read it rather than re-deriving it. Rows
marked "ambiguous" are treated as spanning both systems, exactly as
resolve_citations.py does at its line 368.

USAGE
    python3 promote_scope.py --queue review_queue.tsv --tables .
    python3 promote_scope.py --queue review_queue.tsv --apply \
        --out-resolved promoted.tsv --out-queue review_queue.trimmed.tsv
"""
import sys, os, csv, json, re, argparse
from collections import Counter, defaultdict

C_IID, C_JOURNAL, C_YEAR, C_DOCTYPE, C_CORPUS = 0, 1, 2, 3, 4
C_PAGE_INDEX, C_SEQ, C_MATCH, C_WORK, C_BOOK = 5, 6, 7, 8, 9
C_CONF, C_METHOD, C_CONTEXT = 10, 11, 12
C_REASON = 13


def _raise_csv_limit():
    lim = sys.maxsize
    while True:
        try:
            csv.field_size_limit(lim); break
        except OverflowError:
            lim = int(lim // 10)


_raise_csv_limit()


def page_int(match):
    m = re.match(r"\d+", match or "")
    return int(m.group()) if m else None


def match_letter(match):
    m = re.match(r"\d+([a-eA-E])", match or "")
    return m.group(1).lower() if m else None


def load_tables(tables_dir):
    """page -> set(work_id), for each system."""
    bek = defaultdict(set)
    stp = defaultdict(set)
    bpath = os.path.join(tables_dir, "bekker_ranges.json")
    spath = os.path.join(tables_dir, "stephanus_ranges.json")
    with open(bpath, encoding="utf-8") as f:
        for t in json.load(f)["treatises"]:
            for p in range(t["bekker_start"], t["bekker_end"] + 1):
                bek[p].add(t["id"])
    with open(spath, encoding="utf-8") as f:
        for d in json.load(f)["dialogues"]:
            for p in range(d["stephanus_start"], d["stephanus_end"] + 1):
                stp[p].add(d["id"])
    return bek, stp


def candidate_set(bek, stp, page, letter, corpus):
    """The works a (page, letter) could denote, mirroring resolve_citations.py.

    Bekker has columns a/b only, so a letter of c/d/e excludes Bekker entirely.
    A letter of a/b, or no letter, excludes nothing.
    """
    bekker_possible = letter in (None, "a", "b")
    b = bek.get(page, set()) if bekker_possible else set()
    s = stp.get(page, set())
    if corpus == "bekker":
        return set(b)
    if corpus == "stephanus":
        return set(s)
    return set(b) | set(s)          # "ambiguous": both systems live


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", default=os.path.expanduser("~/Downloads/review_queue.tsv"))
    ap.add_argument("--tables", default=".")
    ap.add_argument("--method", default="scope_inherited",
                    help="which queue method to consider promoting")
    ap.add_argument("--strict", action="store_true",
                    help="refuse to promote rows whose page exists in BOTH "
                         "pagination systems, i.e. do not trust the upstream "
                         "corpus assignment")
    ap.add_argument("--apply", action="store_true",
                    help="actually write output files (default: report only)")
    ap.add_argument("--out-resolved", default="promoted_scope.tsv")
    ap.add_argument("--out-queue", default="review_queue.trimmed.tsv")
    args = ap.parse_args()

    if not os.path.exists(args.queue):
        sys.exit(f"ERROR: queue not found: {args.queue}")
    bek, stp = load_tables(args.tables)

    stats = Counter()
    promote_by_work = Counter()
    keep_by_work = Counter()
    reasons = Counter()
    conf_promoted = []
    examples = {"promote": [], "keep": [], "corpus_trust": []}

    promoted_rows, kept_rows = [], []
    with open(args.queue, encoding="utf-8", newline="") as fh:
        r = csv.reader(fh, delimiter="\t")
        header = next(r, None)
        for row in r:
            stats["rows"] += 1
            method = row[C_METHOD] if len(row) > C_METHOD else ""
            if method != args.method:
                kept_rows.append(row)
                continue
            stats["candidates_considered"] += 1
            work = row[C_WORK]
            page = page_int(row[C_MATCH] if len(row) > C_MATCH else "")
            letter = match_letter(row[C_MATCH] if len(row) > C_MATCH else "")
            corpus = row[C_CORPUS] if len(row) > C_CORPUS else ""
            try:
                conf = float(row[C_CONF])
            except (ValueError, IndexError):
                conf = 0.0

            if page is None:
                reasons["unparseable page"] += 1
                keep_by_work[work] += 1
                kept_rows.append(row)
                continue

            cand = candidate_set(bek, stp, page, letter, corpus)
            if len(cand) == 1 and work in cand:
                # How much of this promotion rests on the upstream `corpus`
                # call rather than on the number itself? If the page also
                # exists in the OTHER system, we are trusting
                # build_citation_db.py's format judgement. Worth counting
                # separately: that stage has not been audited.
                naive = candidate_set(bek, stp, page, letter, "ambiguous")
                if len(naive) > 1 and args.strict:
                    reasons["strict: page exists in both systems"] += 1
                    keep_by_work[work] += 1
                    kept_rows.append(row)
                    continue
                if len(naive) > 1:
                    stats["promoted_via_corpus_trust"] += 1
                    if len(examples["corpus_trust"]) < 6:
                        examples["corpus_trust"].append(
                            (work, row[C_MATCH], corpus, sorted(naive)[:5]))
                stats["promotable"] += 1
                promote_by_work[work] += 1
                conf_promoted.append(conf)
                if len(examples["promote"]) < 6:
                    examples["promote"].append(
                        (work, row[C_MATCH], corpus, conf, sorted(cand)))
                prow = list(row[:C_REASON]) if len(row) > C_REASON else list(row)
                promoted_rows.append(prow)
            else:
                if len(cand) == 0:
                    reasons["no candidate (page out of all ranges)"] += 1
                elif work not in cand:
                    reasons["inherited work not in candidate set"] += 1
                else:
                    reasons[f"ambiguous: {len(cand)} candidate works"] += 1
                keep_by_work[work] += 1
                if len(examples["keep"]) < 6:
                    examples["keep"].append(
                        (work, row[C_MATCH], corpus, conf, sorted(cand)[:5]))
                kept_rows.append(row)

    # ---------------------------------------------------------------- report
    n = stats["candidates_considered"]
    p = stats["promotable"]
    print(f"queue rows scanned            : {stats['rows']:,}")
    print(f"rows with method={args.method!r} : {n:,}")
    print(f"PROMOTABLE (page+letter unique): {p:,}"
          f"  ({p / n * 100:.1f}% of them)" if n else "  n/a")
    print(f"staying queued                : {n - p:,}")
    if conf_promoted:
        lo, hi = min(conf_promoted), max(conf_promoted)
        avg = sum(conf_promoted) / len(conf_promoted)
        print(f"\npromoted-row confidence       : min {lo:.3f}  mean {avg:.3f}  max {hi:.3f}")
        print("  NB these enter `resolved` BELOW the normal accept gate, so the")
        print("  resolved set is no longer uniformly >= --scope-accept. They keep")
        print("  method='scope_inherited' and stay auditable.")

    ct = stats["promoted_via_corpus_trust"]
    if ct:
        print(f"\n  of which resting on the upstream `corpus` call : {ct:,}"
              f" ({ct / max(p,1) * 100:.0f}% of promotions)")
        print("  These pages exist in BOTH pagination systems; the promotion is")
        print("  only as sound as build_citation_db.py's format judgement, which")
        print("  has not been audited. Re-run with --strict to exclude them.")
        for w, m, c, naive in examples["corpus_trust"]:
            print(f"    {w:26s} match={m:<10s} corpus={c:<10s} both-systems={naive}")

    print("\nwhy rows were kept:")
    for k, v in reasons.most_common():
        print(f"  {k:44s} {v:6,}")

    if promote_by_work:
        print("\npromotions by work (top 20):")
        for w, k in promote_by_work.most_common(20):
            print(f"  {w:32s} +{k:,}")

    if examples["promote"]:
        print("\nsample PROMOTED rows:")
        for w, m, c, cf, cand in examples["promote"]:
            print(f"  {w:26s} match={m:<10s} corpus={c:<10s} conf={cf:.2f} cand={cand}")
    if examples["keep"]:
        print("\nsample KEPT rows:")
        for w, m, c, cf, cand in examples["keep"]:
            print(f"  {w:26s} match={m:<10s} corpus={c:<10s} conf={cf:.2f} cand={cand}")

    if not args.apply:
        print("\n(report only — nothing written. Re-run with --apply to write "
              f"{args.out_resolved} and {args.out_queue}.)")
        return

    res_header = header[:C_REASON] if header and len(header) > C_REASON else header
    with open(args.out_resolved, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        if res_header:
            w.writerow(res_header)
        w.writerows(promoted_rows)
    with open(args.out_queue, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        if header:
            w.writerow(header)
        w.writerows(kept_rows)
    print(f"\nwrote {len(promoted_rows):,} promoted rows -> {args.out_resolved}")
    print(f"wrote {len(kept_rows):,} remaining queue rows -> {args.out_queue}")
    print("\nNEXT: append the promoted rows to resolved_with_books.tsv (they carry")
    print("the same 13 columns, reason stripped), then re-run build_viewer_data.py.")
    print("Copy the old view_a.json to viewer_data/view_a.prev.json first to get")
    print("a tier-flip report.")


if __name__ == "__main__":
    main()
