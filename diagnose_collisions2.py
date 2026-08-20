#!/usr/bin/env python3
"""
diagnose_collisions2.py — corrected for the real metadata schema.

Metadata field map (confirmed from sniff):
    id       -> item_id
    journal  -> is_part_of
    title    -> title
    year     -> published_date
    doctype  -> content_type / content_subtype

Explains the ~1,496-iid overlap between the new delivery and the existing
corpus. Journal distribution of the colliding iids discriminates:
  (A) same items re-delivered  -> spread across the original 10 journals
  (B) a 'new' journal already partly in corpus -> concentrates in 1-2 journals
  (C) iid reuse for different items -> sample shows title != new full-text head

Usage:
    python3 diagnose_collisions2.py collisions.txt METADATA.jsonl.gz [newdata.jsonl.gz]

Read-only. Writes nothing.
"""

import sys
import gzip
import json
from collections import Counter

SAMPLE_SHOW = 12


def open_maybe_gz(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "rt", encoding="utf-8", errors="replace")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    coll_path, meta_path = sys.argv[1], sys.argv[2]
    new_path = sys.argv[3] if len(sys.argv) >= 4 else None

    coll = set()
    with open(coll_path, encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if s:
                coll.add(s)
    print("Colliding iids to explain: {:,}".format(len(coll)), file=sys.stderr)

    by_journal = Counter()
    by_content = Counter()
    info = {}          # iid -> (journal, title, year, content_subtype)
    matched = 0
    with open_maybe_gz(meta_path) as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("item_id") in coll:
                matched += 1
                j = rec.get("is_part_of") or "<none>"
                cst = rec.get("content_subtype") or rec.get("content_type") or "<none>"
                by_journal[j] += 1
                by_content[cst] += 1
                if len(info) < SAMPLE_SHOW * 4:
                    info[rec["item_id"]] = (
                        j, rec.get("title"),
                        rec.get("published_date"), cst)
            if n % 1_000_000 == 0:
                print("  …scanned {:>12,} metadata rows".format(n), file=sys.stderr)

    print("\nColliding iids found in metadata: {:,} / {:,}".format(matched, len(coll)))
    print("(shortfall = colliding iids absent from metadata — itself a clue)\n")

    print("=" * 70)
    print("JOURNAL DISTRIBUTION OF COLLISIONS")
    print("=" * 70)
    for j, c in by_journal.most_common():
        print("  {:<50} {:>6,}  ({:4.1f}%)".format(
            (j or "<none>")[:50], c, 100 * c / matched if matched else 0))

    print("\n" + "=" * 70)
    print("CONTENT-TYPE OF COLLISIONS")
    print("=" * 70)
    for k, c in by_content.most_common():
        print("  {:<50} {:>6,}".format(k[:50], c))

    print("\nReading:")
    if by_journal:
        nj = len(by_journal)
        top = by_journal.most_common(1)[0]
        top_share = top[1] / matched
        if nj <= 3:
            print("  -> Concentrated in {} journal(s): pattern (B). A 'new' journal "
                  "was already in the corpus ({}).".format(nj, top[0]))
        elif top_share < 0.35 and nj >= 5:
            print("  -> Spread across {} journals: pattern (A). Same items "
                  "re-delivered; dedup on iid is correct.".format(nj))
        else:
            print("  -> Mixed ({} journals, top {:.0%}): inspect sample for (C).".format(
                nj, top_share))

    if new_path:
        print("\n" + "=" * 70)
        print("SAMPLE — metadata title vs NEW delivery full-text head")
        print("(different articles for the same iid => (C) id-reuse)")
        print("=" * 70)
        want = list(info.keys())[:SAMPLE_SHOW]
        wantset = set(want)
        heads = {}
        with gzip.open(new_path, "rt", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                iid = rec.get("iid")
                if iid in wantset:
                    ft = rec.get("full_text") or []
                    heads[iid] = (ft[0] if ft else "")[:120]
                    if len(heads) == len(wantset):
                        break
        for iid in want:
            j, t, y, cst = info[iid]
            print("\n  iid: {}".format(iid))
            print("    meta journal: {}".format(j))
            print("    meta title:   {}".format((t or "<none>")[:100]))
            print("    meta year:    {}   content: {}".format(y, cst))
            print("    new text[0]:  {}".format(heads.get(iid, "<not in new delivery>")))

    print("\n" + "=" * 70)
    print("Diagnostic complete — nothing written.")
    print("=" * 70)


if __name__ == "__main__":
    main()
