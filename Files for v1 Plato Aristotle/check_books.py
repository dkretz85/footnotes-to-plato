#!/usr/bin/env python3
"""
check_books.py — for each work, how many resolved rows carry a non-empty book,
and what the distinct book values are. Decides which works get book-faceted panels.

Usage: python3 check_books.py resolved.tsv

resolved.tsv columns (0-indexed): 8=work_id, 9=book
"""
import sys, csv, collections

path = sys.argv[1] if len(sys.argv) > 1 else "resolved.tsv"
WORK, BOOK = 8, 9

total = collections.Counter()
withbook = collections.Counter()
booksets = collections.defaultdict(set)

with open(path, encoding="utf-8", newline="") as fh:
    r = csv.reader(fh, delimiter="\t")
    next(r)
    for row in r:
        if len(row) <= BOOK: continue
        w = row[WORK]; b = row[BOOK].strip()
        total[w] += 1
        if b:
            withbook[w] += 1
            booksets[w].add(b)

print(f"{'work':<26} {'rows':>7} {'w/book':>7} {'%':>5}  distinct book values")
for w, n in total.most_common():
    wb = withbook.get(w, 0)
    if wb == 0: continue          # only show works that have ANY book data
    vals = sorted(booksets[w])
    shown = ", ".join(vals[:14]) + (" …" if len(vals) > 14 else "")
    print(f"{w:<26} {n:>7,} {wb:>7,} {100*wb/n:>4.0f}%  [{len(vals)}] {shown}")

print("\nWorks with NO book data are single-panel; the above are candidates for")
print("book-faceted layout (need high % and a sensible set of book values).")
