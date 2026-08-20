#!/usr/bin/env python3
"""
identify_manifest.py — figure out what population core_item_ids.txt actually is
by resolving every id in it to a journal via the metadata.

Answers:
  - Which journals do the 19,509 manifest ids belong to?
  - Is it exactly your 10 built journals, or wider (e.g. includes HSCP)?
  - Content-type breakdown, as a bonus.

Usage:
    python3 identify_manifest.py core_item_ids.txt METADATA.jsonl.gz

Read-only. Writes nothing.
"""

import sys
import gzip
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
    ids_path, meta_path = sys.argv[1], sys.argv[2]

    want = set()
    with open(ids_path, encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if s:
                want.add(s)
    print("Manifest ids to resolve: {:,}".format(len(want)), file=sys.stderr)

    by_journal = Counter()
    by_content = Counter()
    matched = 0
    with open_maybe_gz(meta_path) as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("item_id") in want:
                matched += 1
                by_journal[rec.get("is_part_of") or "<none>"] += 1
                by_content[rec.get("content_subtype")
                           or rec.get("content_type") or "<none>"] += 1
            if n % 1_000_000 == 0:
                print("  …scanned {:>12,} rows".format(n), file=sys.stderr)

    print("\nResolved {:,} / {:,} manifest ids in metadata.".format(matched, len(want)))
    print("(shortfall = ids in the manifest that aren't in this metadata file)\n")

    print("=" * 66)
    print("JOURNALS SPANNED BY THE MANIFEST")
    print("=" * 66)
    for j, c in by_journal.most_common():
        print("  {:<48} {:>7,}".format((j or "<none>")[:48], c))

    print("\n" + "=" * 66)
    print("CONTENT-TYPE BREAKDOWN")
    print("=" * 66)
    for k, c in by_content.most_common():
        print("  {:<48} {:>7,}".format(k[:48], c))

    print("\nReading:")
    n_j = len([j for j in by_journal if j != "<none>"])
    print("  Manifest spans {} distinct journal(s).".format(n_j))
    print("  If that's ~10 -> it's your built-corpus journal set.")
    print("  If it's more (e.g. includes HSCP) -> it's a broader earlier "
          "delivery manifest; do NOT use it as a dedup key for the new fusion.")


if __name__ == "__main__":
    main()
