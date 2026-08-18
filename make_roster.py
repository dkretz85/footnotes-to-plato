#!/usr/bin/env python3
"""
make_roster.py — build a COMPLETE request roster from the delivery itself, so the
extractor's metadata keep-filter covers every delivered record (fixes the old-
delivery "?" journal/year/doctype rows from the Aug-12 run).

The roster's only job is to tell load_metadata() which iids to index out of the
12.6M-record catalogue. Using every iid actually present in combined.jsonl.gz
means no delivered record is left without metadata — while still indexing only
~283k of 12.6M (the memory saving is preserved).

We scan each line for the top-level "iid" with a regex instead of json.loads,
so we never parse the megabyte-long full_text array just to read the id — fast
and bounded memory (a set of ~283k UUIDs).

    python3 make_roster.py combined.jsonl.gz            # -> all_item_ids.txt
    python3 make_roster.py combined.jsonl.gz roster.txt # custom output name
"""
import sys, gzip, re

IID_RE = re.compile(r'"iid"\s*:\s*"([^"]+)"')

def open_stream(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")

def main():
    if len(sys.argv) < 2:
        print("usage: python3 make_roster.py combined.jsonl.gz [out.txt]")
        sys.exit(1)
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "all_item_ids.txt"
    seen = set()
    n = 0
    with open_stream(src) as fh:
        for line in fh:
            n += 1
            m = IID_RE.search(line)   # first match = the record's top-level iid
            if m:
                seen.add(m.group(1))
            if n % 20000 == 0:
                print(f"  ...{n:,} records, {len(seen):,} distinct iids", flush=True)
    with open(out, "w", encoding="utf-8") as o:
        o.write("\n".join(sorted(seen)) + "\n")
    print(f"Wrote {len(seen):,} distinct iids to {out} (from {n:,} records).")

if __name__ == "__main__":
    main()
