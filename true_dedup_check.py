#!/usr/bin/env python3
"""
true_dedup_check.py — determine the CORRECT fusion/dedup key.

core_item_ids.txt turned out to be a 4-journal dev sample, NOT the built
corpus, so it is the wrong thing to dedup against. The real "already built"
set is the distinct iids present in resolved_with_books.tsv (column 1).

This script:
  1. Reads the built iids from the TSV (streamed; col 0 = iid).
  2. Streams the new delivery and reports how many of its iids are already
     in the built corpus -> the real duplicates to drop on fusion.
  3. Breaks those true-duplicate iids down by journal (via metadata) so we
     see exactly what (if anything) genuinely overlaps.

Usage:
    python3 true_dedup_check.py resolved_with_books.tsv newdata.jsonl.gz METADATA.jsonl.gz

The metadata arg is optional; without it you still get the counts, just no
per-journal breakdown of the true duplicates.

Read-only. Writes nothing.
"""

import sys
import gzip
import csv
import json
from collections import Counter


def open_maybe_gz(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "rt", encoding="utf-8", errors="replace")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    tsv_path, new_path = sys.argv[1], sys.argv[2]
    meta_path = sys.argv[3] if len(sys.argv) >= 4 else None

    # ---- 1. built iids from the TSV (col 0) ----
    print("Reading built iids from {} …".format(tsv_path), file=sys.stderr)
    built = set()
    with open(tsv_path, encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.reader(fh, delimiter="\t")
        for row in reader:
            if row:
                built.add(row[0])
    # the header cell 'iid' will be in there; harmless for set membership
    built.discard("iid")
    print("  {:,} distinct built iids".format(len(built)), file=sys.stderr)

    # ---- 2. test the delivery against it ----
    print("Streaming new delivery …", file=sys.stderr)
    total = 0
    dup = []
    with gzip.open(new_path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            total += 1
            iid = json.loads(line).get("iid")
            if iid in built:
                dup.append(iid)
            if total % 25_000 == 0:
                print("  …{:>9,} delivery records".format(total), file=sys.stderr)

    dupset = set(dup)
    print("\n" + "=" * 60)
    print("TRUE DEDUP RESULT")
    print("=" * 60)
    print("Delivery records:            {:>9,}".format(total))
    print("Built corpus iids:           {:>9,}".format(len(built)))
    print("Delivery iids already built: {:>9,}".format(len(dupset)))
    print("Net-new records to ingest:   {:>9,}".format(total - len(dupset)))
    if len(dupset) == 0:
        print("\n  -> Delivery is a CLEAN partition vs the built corpus.")
        print("     Fusion = concatenate, no dedup. (HSCP enters fresh.)")
    else:
        print("\n  -> {:,} genuine duplicates. Dedup these iids on fusion.".format(
            len(dupset)))

    # ---- 3. per-journal breakdown of the true duplicates ----
    if meta_path and dupset:
        print("\nJournal breakdown of the genuine duplicates:")
        bj = Counter()
        with open_maybe_gz(meta_path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("item_id") in dupset:
                    bj[rec.get("is_part_of") or "<none>"] += 1
        for j, c in bj.most_common():
            print("  {:<48} {:>6,}".format((j or "<none>")[:48], c))

    print("\n" + "=" * 60)
    print("Done — nothing written.")
    print("=" * 60)


if __name__ == "__main__":
    main()
