#!/usr/bin/env python3
"""
survey_jstor.py — inspect a JSTOR Text Analysis Support bibliographic metadata
file (JSONL, gzip-compressed) and report coverage for the six core
ancient-philosophy journals.

Usage:
    python3 survey_jstor.py /path/to/jstor_metadata.jsonl.gz

Produces:
    - console: full journal list (so you can confirm exact title strings)
    - console: per-journal totals for the six targets
    - core_counts.tsv: journal / year / doctype / count  (the six targets)
    - core_item_ids.txt: one JSTOR item ID per line (the six targets), ready
      to trim and upload as a dataset request

Nothing is decompressed to disk; the file is streamed line by line.
"""

import sys, json, gzip, collections, io

# --- The six core journals (HPT and JHI dropped for v1) --------------------
# These are *substring* matchers, case-insensitive, chosen to survive
# title-string variation (leading "The", subtitles, umlaut encodings).
# After the first run, tighten these against the printed full journal list.
TARGET_PATTERNS = {
    "Phronesis":            ["phronesis"],
    "Ancient Philosophy":   ["ancient philosophy"],
    "Apeiron":              ["apeiron"],
    "Classical Quarterly":  ["classical quarterly"],
    "Classical Philology":  ["classical philology"],
    "AGPh":                 ["archiv fur geschichte der philosophie",
                             "archiv f\u00fcr geschichte der philosophie",
                             "archiv fuer geschichte der philosophie"],
}

# Field names confirmed from the actual file schema.
JOURNAL_FIELDS = ["is_part_of", "isPartOf", "journalTitle"]
YEAR_FIELDS    = ["published_date", "publicationYear", "year"]
TYPE_FIELDS    = ["content_subtype", "content_type", "docSubType"]
ID_FIELDS      = ["item_id", "id", "docId"]


def first_present(rec, fields, default=None):
    for f in fields:
        v = rec.get(f)
        if v not in (None, ""):
            return v
    return default


def normalize(s):
    return str(s).strip().lower() if s is not None else ""


def match_target(journal_raw):
    j = normalize(journal_raw)
    for canonical, pats in TARGET_PATTERNS.items():
        if any(p in j for p in pats):
            return canonical
    return None


def open_stream(path):
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    path = sys.argv[1]

    all_journals = collections.Counter()          # every journal, item count
    core_counts  = collections.Counter()          # (canonical, year, doctype)
    core_totals  = collections.Counter()          # canonical -> total
    core_reviews = collections.Counter()          # canonical -> doctype "review" items
    core_gated   = collections.Counter()          # canonical -> review_required=True items
    core_ids     = []                             # (canonical, item_id)
    bad_lines = 0
    total_lines = 0
    sample_keys = None

    with open_stream(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            total_lines += 1
            try:
                rec = json.loads(line)
            except Exception:
                bad_lines += 1
                continue

            if sample_keys is None:
                sample_keys = sorted(rec.keys())

            journal = first_present(rec, JOURNAL_FIELDS, "?")
            all_journals[journal] += 1

            canonical = match_target(journal)
            if canonical is None:
                continue

            year  = first_present(rec, YEAR_FIELDS, "?")
            # keep only a 4-digit year if the field is a full date string
            ys = str(year)
            for tok in ys.replace("-", " ").split():
                if len(tok) == 4 and tok.isdigit():
                    year = tok
                    break

            dtype = first_present(rec, TYPE_FIELDS, "?")
            item_id = first_present(rec, ID_FIELDS, None)

            core_counts[(canonical, year, dtype)] += 1
            core_totals[canonical] += 1
            if "review" in normalize(dtype):
                core_reviews[canonical] += 1
            if rec.get("review_required") in (True, "true", "True", 1):
                core_gated[canonical] += 1
            if item_id:
                core_ids.append((canonical, item_id))

    # --- report -----------------------------------------------------------
    print("=" * 60)
    print(f"Lines read: {total_lines:,}   unparseable: {bad_lines:,}")
    if sample_keys:
        print(f"\nFields present in first record:\n  {', '.join(sample_keys)}")
    print("\n" + "=" * 60)
    print("ALL JOURNALS IN FILE (item count, title) — top 60 by size")
    print("Confirm your six target strings appear here as expected.")
    print("=" * 60)
    for journal, n in all_journals.most_common(60):
        print(f"{n:8,d}  {journal}")

    print("\n" + "=" * 60)
    print("CORE SIX — totals")
    print("  book-reviews = doctype is a review (reception signal, keep)")
    print("  copyright-gated = review_required=True (goes to JSTOR review queue)")
    print("=" * 60)
    grand = grand_gated = 0
    for canonical in TARGET_PATTERNS:
        t = core_totals.get(canonical, 0)
        r = core_reviews.get(canonical, 0)
        g = core_gated.get(canonical, 0)
        grand += t
        grand_gated += g
        flag = "  <-- ZERO: check title match" if t == 0 else ""
        print(f"{canonical:22s} {t:7,d} items   "
              f"({r:,} book-reviews, {g:,} copyright-gated){flag}")
    print("-" * 60)
    print(f"{'TOTAL':22s} {grand:7,d} items   ({grand_gated:,} copyright-gated)")

    # --- write TSV --------------------------------------------------------
    with open("core_counts.tsv", "w", encoding="utf-8") as out:
        out.write("journal\tyear\tdoctype\tcount\n")
        for (j, y, t), n in sorted(core_counts.items()):
            out.write(f"{j}\t{y}\t{t}\t{n}\n")

    # --- write item IDs ---------------------------------------------------
    with open("core_item_ids.txt", "w", encoding="utf-8") as out:
        for _, item_id in core_ids:
            out.write(f"{item_id}\n")

    print(f"\nWrote core_counts.tsv  ({len(core_counts):,} journal/year/type rows)")
    print(f"Wrote core_item_ids.txt ({len(core_ids):,} item IDs)")
    print("\nNext: eyeball the journal list above. If any of the six shows")
    print("ZERO or a wrong count, adjust TARGET_PATTERNS and re-run.")


if __name__ == "__main__":
    main()
