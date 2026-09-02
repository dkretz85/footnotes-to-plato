#!/usr/bin/env python3
"""
sequentia_audit.py — how many of our citations carry a dropped "and-following"
tail (f. / ff. / sq. / sqq.)?

BACKGROUND. The v2 extractor (build_citation_db_v2.py) captures an EXPLICIT
range whole ('620a-622c' -> every unit) via a letter-guarded dash tail, but it
has no tail for the scholarly "sequentia" abbreviations. So a citation written
"327a f." / "1094a25 ff." / "Il. 2.484 ff." / "Rom 8:28 sqq." is harvested as
its ANCHOR unit ALONE (327a, 1094a25, Il. 2.484, Rom 8:28); the "and following"
pages/lines are silently dropped. The anchor is NOT lost — only the extension.
(Edge case: a TIGHT-set "327aff." with no space loses the whole citation, anchor
included, because no word boundary follows the anchor; those rows never exist to
be measured here, so treat this audit's numbers as a lower bound.)

This script quantifies the prevalence of the dropped-tail case so we can decide
whether it is a rounding-error footnote or a systematic bias worth hedging in
the methods page. It works by re-inspecting the `context` window already stored
next to every harvested match: it finds the match inside its context and checks
whether an f./ff./sq./sqq. marker sits immediately after it.

INPUT (auto-detected; first that exists wins, or pass a path):
    resolved_with_books.tsv   (best — adds the by-WORK breakdown)
    resolved.tsv              (adds by-WORK)
    citations.tsv             (no work_id; journal/field/period/corpus only)

None of these live in the repo (JSTOR-derived, gitignored). Run this where you
regenerated them, e.g.:
    python3 sequentia_audit.py                       # auto-detect
    python3 sequentia_audit.py resolved.tsv
    python3 sequentia_audit.py citations.tsv --tsv sequentia_by_group.tsv

OUTPUT: a readable report to stdout (overall rate; then by field, journal,
period/decade, corpus, and work), splitting single-following (f./sq.) from
multi-following (ff./sqq.). Optionally a tidy TSV of every group with --tsv.
"""
import sys, os, csv, re, json, argparse, collections

csv.field_size_limit(10 * 1024 * 1024)   # contexts can be long

# The marker must sit right after the anchor: optional spaces, then f/ff/sq/sqq,
# then a period or other boundary (so "f." matches but "for"/"fr." do not).
MARKER = re.compile(r"^\s{0,3}(ff?|sqq?)(?=[\s.,;:)\]]|$)", re.I)
SINGLE = {"f", "sq"}      # "one following unit"
MULTI  = {"ff", "sqq"}    # "an indefinite span following"

CANDIDATE_FILES = ["resolved_with_books.tsv", "resolved.tsv", "citations.tsv"]


def load_field_map(path="journal_groups.json"):
    """journal name -> field label ('Philosophy'/'Classics'/'Theology & NT')."""
    if not os.path.exists(path):
        return {}, {}
    groups = json.load(open(path, encoding="utf-8"))["groups"]
    jmap, labels = {}, {}
    for key, obj in groups.items():
        labels[key] = obj.get("label", key)
        for j in obj.get("journals", []):
            jmap[j] = key
    return jmap, labels


def classify_tail(match, context):
    """Return 'single', 'multi', or None for the text right after `match` in
    `context`. Uses the LAST occurrence of the match so a match string that also
    appears earlier in the window (e.g. repeated in the sentence) doesn't
    mis-anchor; the harvested match is normally the final locus in its context."""
    if not match or not context:
        return None
    idx = context.rfind(match)
    if idx < 0:
        return None
    m = MARKER.match(context[idx + len(match):])
    if not m:
        return None
    tok = m.group(1).lower()
    return "single" if tok in SINGLE else "multi" if tok in MULTI else None


def detect_columns(header):
    """Map needed field -> column index, tolerating both the citations.tsv and
    resolved.tsv layouts."""
    h = {name: i for i, name in enumerate(header)}
    need = {}
    for key, aliases in {
        "iid":     ["iid"],
        "seq":     ["seq"],
        "journal": ["journal"],
        "year":    ["year"],
        "corpus":  ["corpus"],
        "match":   ["match"],
        "context": ["context"],
        "work":    ["work_id"],          # optional
        "span":    ["span_src"],          # optional (range fan-out marker)
    }.items():
        for a in aliases:
            if a in h:
                need[key] = h[a]
                break
    return need


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", help="TSV to audit (auto-detected if omitted)")
    ap.add_argument("--tsv", help="also write a per-group breakdown TSV here")
    ap.add_argument("--top", type=int, default=25,
                    help="rows to show in the journal/work tables (default 25)")
    ap.add_argument("--min-n", type=int, default=30,
                    help="hide groups with fewer than this many citations (default 30)")
    args = ap.parse_args()

    path = args.path
    if not path:
        path = next((p for p in CANDIDATE_FILES if os.path.exists(p)), None)
    if not path or not os.path.exists(path):
        sys.exit("No input TSV found. Looked for: " + ", ".join(CANDIDATE_FILES) +
                 ". Regenerate the citation DB first, or pass a path.")

    jfield, flabels = load_field_map()

    # Each source citation = one (iid, seq). Range fan-out repeats (iid, seq)
    # across units; we collapse to one record per source citation. f./ff. only
    # occur on single-unit (non-range) citations, so collapsing loses nothing.
    seen = set()
    # counters: dimension -> group -> {"n": total, "single": x, "multi": y}
    dims = {d: collections.defaultdict(lambda: [0, 0, 0])
            for d in ("overall", "field", "journal", "period", "corpus", "work")}

    with open(path, encoding="utf-8", newline="") as fh:
        r = csv.reader(fh, delimiter="\t")
        header = next(r)
        col = detect_columns(header)
        for req in ("iid", "journal", "year", "corpus", "match", "context"):
            if req not in col:
                sys.exit(f"Input {path} is missing required column '{req}'. "
                         f"Header was: {header}")
        has_work = "work" in col
        has_seq  = "seq" in col
        has_span = "span" in col

        for row in r:
            if len(row) <= max(col.values()):
                continue
            iid = row[col["iid"]]
            seq = row[col["seq"]] if has_seq else None
            key = (iid, seq)
            if has_seq:
                if key in seen:
                    continue          # already counted this source citation
                seen.add(key)

            match   = row[col["match"]]
            context = row[col["context"]]
            # For a fanned-out range, prefer the original range cell so we never
            # mis-read a mid-range unit; ranges are explicit, never f./ff.
            if has_span and row[col["span"]]:
                match = row[col["span"]]

            journal = row[col["journal"]]
            year    = row[col["year"]]
            corpus  = row[col["corpus"]]
            work    = row[col["work"]] if has_work else ""

            kind = classify_tail(match, context)

            decade = (year[:3] + "0s") if (year[:3].isdigit() and len(year) >= 4) else year
            field  = flabels.get(jfield.get(journal, ""), "· unclassified")

            for dim, grp in (("overall", "ALL"), ("field", field),
                             ("journal", journal), ("period", decade),
                             ("corpus", corpus), ("work", work or "· unresolved")):
                if dim == "work" and not has_work:
                    continue
                c = dims[dim][grp]
                c[0] += 1
                if kind == "single":
                    c[1] += 1
                elif kind == "multi":
                    c[2] += 1

    # ---------- report ----------
    def pct(x, n):
        return (100.0 * x / n) if n else 0.0

    def rate(c):
        return pct(c[1] + c[2], c[0])

    o = dims["overall"]["ALL"]
    total, single, multi = o[0], o[1], o[2]
    both = single + multi
    print("=" * 72)
    print(f"SEQUENTIA AUDIT  ·  source: {path}")
    print("=" * 72)
    print(f"source citations examined : {total:,}")
    print(f"  with a following-marker : {both:,}  ({pct(both,total):.2f}%)")
    print(f"     f./sq.  (one unit)   : {single:,}  ({pct(single,total):.2f}%)")
    print(f"     ff./sqq. (a span)    : {multi:,}  ({pct(multi,total):.2f}%)")
    print("Every marked citation dropped >=1 following unit from the anchor;")
    print("the ff./sqq. rows dropped an INDEFINITE span (the ones to worry about).")

    def table(title, dim, top=None):
        print("\n" + title)
        print("-" * 72)
        print(f"{'group':40s} {'cites':>8s} {'f/sq':>6s} {'ff/sqq':>7s} {'rate':>7s}")
        rows = sorted(dims[dim].items(), key=lambda kv: (-rate(kv[1]), -kv[1][0]))
        shown = 0
        for grp, c in rows:
            if c[0] < args.min_n:
                continue
            print(f"{grp[:40]:40s} {c[0]:8,d} {c[1]:6,d} {c[2]:7,d} {rate(c):6.2f}%")
            shown += 1
            if top and shown >= top:
                break
        if not shown:
            print(f"(no group with >= {args.min_n} citations)")

    table("BY FIELD", "field")
    table("BY PERIOD (decade)", "period")
    table("BY CORPUS (reference system)", "corpus")
    table(f"BY JOURNAL (top {args.top} by rate, min {args.min_n} cites)",
          "journal", top=args.top)
    if any(dims["work"]):
        table(f"BY WORK (top {args.top} by rate, min {args.min_n} cites)",
              "work", top=args.top)
    else:
        print("\n(BY WORK skipped: input has no work_id column — run against "
              "resolved.tsv for the per-text breakdown.)")

    if args.tsv:
        with open(args.tsv, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, delimiter="\t")
            w.writerow(["dimension", "group", "citations", "f_or_sq",
                        "ff_or_sqq", "marked_total", "marked_pct"])
            for dim in ("overall", "field", "period", "corpus", "journal", "work"):
                for grp, c in sorted(dims[dim].items(),
                                     key=lambda kv: (-rate(kv[1]), -kv[1][0])):
                    w.writerow([dim, grp, c[0], c[1], c[2], c[1] + c[2],
                                f"{rate(c):.3f}"])
        print(f"\nWrote per-group breakdown -> {args.tsv}")


if __name__ == "__main__":
    main()
