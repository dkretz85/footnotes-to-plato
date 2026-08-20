#!/usr/bin/env python3
"""
collect_collisions.py — dump the iids that appear in BOTH the new delivery
and the existing corpus id set.

Usage:
    python3 collect_collisions.py newdata.jsonl.gz core_item_ids.txt

Writes:
    collisions.txt          one colliding iid per line (~1,496 expected)

Read-only on the inputs. The only thing written is collisions.txt.
"""

import sys
import gzip
import json


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    new_path, ids_path = sys.argv[1], sys.argv[2]

    print("Loading existing ids from {} …".format(ids_path), file=sys.stderr)
    known = set()
    with open(ids_path, encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if s:
                known.add(s)
    print("  {:,} existing ids".format(len(known)), file=sys.stderr)

    hits = []
    total = 0
    with gzip.open(new_path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            total += 1
            rec = json.loads(line)
            iid = rec.get("iid")
            if iid and iid in known:
                hits.append(iid)
            if total % 25_000 == 0:
                print("  …{:>9,} records".format(total), file=sys.stderr)

    with open("collisions.txt", "w", encoding="utf-8") as out:
        for iid in hits:
            out.write(iid + "\n")

    print("\nScanned {:,} records.".format(total))
    print("Colliding iids: {:,}  ->  collisions.txt".format(len(hits)))


if __name__ == "__main__":
    main()
