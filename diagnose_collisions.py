#!/usr/bin/env python3
"""
diagnose_collisions.py — explain the 1,496-iid overlap between the new
delivery and the existing corpus, using the metadata file.

The overlap has three candidate explanations, and the journal distribution
of the colliding iids tells them apart:

  (A) SAME ITEMS re-delivered
      -> collisions spread across your existing 10 corpus journals.
         Meaning: iid is stable; these really are already-ingested articles.
         Fix: dedup on fusion (drop new rows whose iid is already in corpus).

  (B) A "new" journal was ALREADY partially in the corpus
      -> collisions concentrate in one or a few T4/T5 journals.
         Meaning: the new-journals-only assumption was wrong for those venues.
         Fix: still dedup, but also note which journal double-counted.

  (C) iid REUSE across deliveries for DIFFERENT items
      -> collisions look arbitrary / land on journals that shouldn't overlap,
         OR the same iid maps to two different titles in old vs new full-text.
         Meaning: iid is NOT a safe dedup key. Dedup would drop real rows.
         Fix: do NOT dedup on iid; find a content-based key.

This script reports the journal breakdown of the colliding iids (from
metadata) so we can read which pattern we're in. It also samples a few
collisions showing metadata title vs the new delivery's full-text head,
so we can spot (C) — same iid, different article.

Usage:
    python3 diagnose_collisions.py collisions.txt METADATA.jsonl.gz [newdata.jsonl.gz]

The third arg (new delivery) is optional but recommended: with it, the
script shows metadata-title vs new-full-text-head side by side for a sample,
which is what catches id-reuse.

Read-only. Writes nothing.
"""

import sys
import gzip
import json
from collections import Counter

SCHEMA_SAMPLE = 3
SAMPLE_SHOW = 12   # how many collisions to print title-vs-text for


def open_maybe_gz(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "rt", encoding="utf-8", errors="replace")


def pick(rec, *cands):
    for c in cands:
        if c in rec and rec[c] not in (None, "", []):
            return rec[c]
    return None


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    coll_path = sys.argv[1]
    meta_path = sys.argv[2]
    new_path = sys.argv[3] if len(sys.argv) >= 4 else None

    # load colliding iids
    coll = set()
    with open(coll_path, encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if s:
                coll.add(s)
    print("Colliding iids to explain: {:,}".format(len(coll)), file=sys.stderr)

    # ---- sniff metadata schema ----
    print("=" * 70)
    print("METADATA SCHEMA SNIFF (first {} records)".format(SCHEMA_SAMPLE))
    print("=" * 70)
    id_key = None
    with open_maybe_gz(meta_path) as fh:
        for i, line in enumerate(fh):
            if i >= SCHEMA_SAMPLE:
                break
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            print("\n--- metadata record {} ---".format(i))
            for k, v in rec.items():
                sv = repr(v)
                if len(sv) > 90:
                    sv = sv[:90] + "…"
                print("  {:<24} {}".format(k, sv))
            if id_key is None:
                for cand in ("item_id", "iid", "id", "doi"):
                    if cand in rec:
                        id_key = cand
                        break
    print("\n-> using metadata id field: {}".format(id_key))
    if id_key is None:
        print("!! Could not guess the metadata id field. Paste the schema above "
              "and I'll fix the script.")
        sys.exit(1)

    # ---- full pass over metadata: journal breakdown for colliding iids ----
    print("\n" + "=" * 70)
    print("JOURNAL BREAKDOWN OF THE COLLIDING iids")
    print("=" * 70)
    by_journal = Counter()
    titles = {}     # iid -> metadata title, for the sample
    matched = 0
    with open_maybe_gz(meta_path) as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            rid = rec.get(id_key)
            if rid in coll:
                matched += 1
                j = pick(rec, "journal", "isPartOf", "journalTitle", "source") or "<none>"
                by_journal[j] += 1
                t = pick(rec, "title", "articleTitle", "docTitle")
                if len(titles) < SAMPLE_SHOW * 3:
                    titles[rid] = (j, t)
            if n % 1_000_000 == 0:
                print("  …scanned {:>12,} metadata rows".format(n), file=sys.stderr)

    print("\nColliding iids found in metadata: {:,} / {:,}".format(matched, len(coll)))
    print("(any shortfall = colliding iids NOT in metadata — itself a clue)\n")
    print("Journal distribution of collisions:")
    for j, c in by_journal.most_common():
        print("  {:<48} {:>6,}  ({:4.1f}%)".format(
            j[:48], c, 100 * c / matched if matched else 0))

    # crude read of the pattern
    print("\nReading:")
    if by_journal:
        top_share = by_journal.most_common(1)[0][1] / matched
        n_journals = len(by_journal)
        if n_journals <= 3:
            print("  Collisions concentrate in {} journal(s) — looks like (B): a "
                  "'new' journal was already partly in the corpus.".format(n_journals))
        elif top_share < 0.35 and n_journals >= 5:
            print("  Collisions spread across many journals — consistent with (A): "
                  "same items re-delivered (iid stable, dedup is correct).")
        else:
            print("  Mixed pattern — inspect the sample below for (C) id-reuse.")

    # ---- sample: metadata title vs new-delivery full-text head ----
    if new_path:
        print("\n" + "=" * 70)
        print("SAMPLE — metadata title vs NEW delivery full-text head")
        print("(if these describe DIFFERENT articles, that's (C) id-reuse)")
        print("=" * 70)
        want = set(list(titles.keys())[:SAMPLE_SHOW])
        heads = {}
        with gzip.open(new_path, "rt", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                iid = rec.get("iid")
                if iid in want:
                    ft = rec.get("full_text") or []
                    head = (ft[0] if ft else "")[:120]
                    heads[iid] = head
                    if len(heads) == len(want):
                        break
        for iid in want:
            j, t = titles.get(iid, ("?", None))
            print("\n  iid: {}".format(iid))
            print("    metadata journal: {}".format(j))
            print("    metadata title:   {}".format((t or "<none>")[:100]))
            print("    new full-text[0]: {}".format(heads.get(iid, "<not found in new>")))

    print("\n" + "=" * 70)
    print("Diagnostic complete — nothing written.")
    print("=" * 70)


if __name__ == "__main__":
    main()
