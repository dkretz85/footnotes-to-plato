import gzip, json, sys

FILE = "16b50028-4490-4086-8fd0-d20505f6e998.jsonl.gz"

with gzip.open(FILE, "rt", encoding="utf-8") as fh:
    rec = json.loads(next(fh))

print("KEYS:", list(rec.keys()))

print("\n--- full_text: type", type(rec["full_text"]).__name__, "len", len(rec["full_text"]))
ft = rec["full_text"]
print("  element types:", {type(x).__name__ for x in ft})
print("  first element (truncated):")
print("   ", (json.dumps(ft[0])[:600]) if ft else "(empty)")

print("\n--- references: type", type(rec["references"]).__name__, "len", len(rec["references"]))
rf = rec["references"]
print("  element types:", {type(x).__name__ for x in rf})
if rf:
    print("  first 2 elements (truncated):")
    for r in rf[:2]:
        print("   ", json.dumps(r)[:400])
