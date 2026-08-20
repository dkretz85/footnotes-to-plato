#!/usr/bin/env python3
"""
survey_newdata.py — first look at the new JSTOR delivery (newdata.jsonl.gz).

Streams the gzip in a single pass. Does NOT load the whole file into memory.
Two phases:
  1. SCHEMA SNIFF: pull the first N records, report every key seen and a short
     sample value, so we can see what JSTOR actually named things.
  2. FULL PASS: stream all records and tally the numbers the handoff checklist
     needs — total count, per-journal, doctype split, year range, and an
     id-stability check against the existing corpus.

Usage:
    python3 survey_newdata.py /path/to/newdata.jsonl.gz [core_item_ids.txt]

The second arg is optional: if you point it at your existing core_item_ids.txt
(the iids already in the current 10-journal corpus), the script checks whether
any ids in the new delivery collide with the old set — the §5-step-2
"is this a clean partition?" question.

Nothing is written. Read-only. Safe to run repeatedly.
"""

import sys
import gzip
import json
from collections import Counter, defaultdict

SCHEMA_SAMPLE = 5          # records to inspect for schema
PROGRESS_EVERY = 25_000    # heartbeat so you know it's alive


def sniff_schema(path):
    print("=" * 70)
    print("PHASE 1 — SCHEMA SNIFF (first {} records)".format(SCHEMA_SAMPLE))
    print("=" * 70)
    keys_seen = Counter()
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            if i >= SCHEMA_SAMPLE:
                break
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            keys_seen.update(rec.keys())
            print("\n--- record {} ---".format(i))
            for k, v in rec.items():
                sv = repr(v)
                if len(sv) > 90:
                    sv = sv[:90] + "…"
                print("  {:<24} {}".format(k, sv))
    print("\nKeys appearing across sampled records:")
    for k, n in keys_seen.most_common():
        flag = "" if n == SCHEMA_SAMPLE else "  (only in {}/{})".format(n, SCHEMA_SAMPLE)
        print("  {:<24}{}".format(k, flag))
    return set(keys_seen)


def pick(rec, *candidates):
    """Return the first present, non-empty candidate key's value."""
    for c in candidates:
        if c in rec and rec[c] not in (None, "", []):
            return rec[c]
    return None


def full_pass(path, known_ids=None):
    print("\n" + "=" * 70)
    print("PHASE 2 — FULL PASS")
    print("=" * 70)

    total = 0
    by_journal = Counter()
    by_doctype = Counter()
    doctype_by_journal = defaultdict(Counter)
    years = Counter()
    missing_year = 0
    id_key_used = None
    ids_seen = set()
    dup_ids_within = 0
    collisions_with_old = 0

    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            total += 1

            # id — try the field names we've seen JSTOR / your pipeline use
            rid = pick(rec, "id", "item_id", "iid", "doi", "ithaka_doi")
            if rid is not None:
                if id_key_used is None:
                    # remember which key won, for the report
                    for cand in ("id", "item_id", "iid", "doi", "ithaka_doi"):
                        if cand in rec and rec[cand] not in (None, "", []):
                            id_key_used = cand
                            break
                if rid in ids_seen:
                    dup_ids_within += 1
                else:
                    ids_seen.add(rid)
                    if known_ids and rid in known_ids:
                        collisions_with_old += 1

            journal = pick(rec, "journal", "isPartOf", "journalTitle", "source")
            by_journal[journal or "<none>"] += 1

            doctype = pick(rec, "docType", "doctype", "docSubType",
                           "content_subtype", "type")
            doctype = (doctype or "<none>")
            by_doctype[doctype] += 1
            if journal:
                doctype_by_journal[journal][doctype] += 1

            yr = pick(rec, "publicationYear", "year", "datePublished")
            if yr is None:
                missing_year += 1
            else:
                # normalise a leading 4-digit year out of strings like "1923-04-01"
                s = str(yr)[:4]
                if s.isdigit():
                    years[int(s)] += 1
                else:
                    missing_year += 1

            if total % PROGRESS_EVERY == 0:
                print("  …{:>9,} records".format(total), file=sys.stderr)

    # ---- report ----
    print("\nTotal records: {:,}".format(total))
    print("ID field used: {}".format(id_key_used))
    print("Unique ids:    {:,}".format(len(ids_seen)))
    print("Dup ids within delivery: {:,}".format(dup_ids_within))
    if known_ids is not None:
        print("Collisions with existing corpus ids: {:,}".format(collisions_with_old))
        print("  -> {}".format(
            "CLEAN PARTITION (concatenate, no dedup)" if collisions_with_old == 0
            else "NOT clean — dedup needed before fusion"))

    print("\nDoctype split (whole delivery):")
    for dt, n in by_doctype.most_common():
        print("  {:<28} {:>9,}  ({:5.1f}%)".format(dt, n, 100 * n / total))

    print("\nPer-journal counts ({} journals):".format(len(by_journal)))
    for j, n in by_journal.most_common():
        review = doctype_by_journal[j]
        # crude review share: anything whose doctype string mentions 'review'
        rev = sum(v for k, v in review.items() if "review" in k.lower())
        pct = (100 * rev / n) if n else 0
        print("  {:<45} {:>8,}   reviews ~{:4.0f}%".format(
            (j or "<none>")[:45], n, pct))

    if years:
        lo, hi = min(years), max(years)
        print("\nYear range: {}–{}  (missing/unparsed: {:,})".format(
            lo, hi, missing_year))

    print("\n" + "=" * 70)
    print("Survey complete — nothing written.")
    print("=" * 70)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = sys.argv[1]
    known_ids = None
    if len(sys.argv) >= 3:
        idpath = sys.argv[2]
        print("Loading existing ids from {} …".format(idpath), file=sys.stderr)
        known_ids = set()
        with open(idpath, encoding="utf-8") as fh:
            for line in fh:
                s = line.strip()
                if s:
                    known_ids.add(s)
        print("  {:,} existing ids loaded".format(len(known_ids)), file=sys.stderr)

    sniff_schema(path)
    full_pass(path, known_ids)


if __name__ == "__main__":
    main()
