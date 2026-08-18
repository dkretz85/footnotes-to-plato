#!/usr/bin/env python3
"""
cue_audit.py — audit the harvested Homer/Pindar/NT cue tokens (RANGE §5 / Aug-12
§5 calibration). READ-ONLY. Run on the CURRENT citations.tsv so we can finalize
the extractor's cue lists and separators BEFORE the single re-harvest.

What it answers:
  * Which cue tokens actually occur, and at what volume (so dead cues can be
    dropped and high-volume ones sanity-checked).
  * For Homer: the book-line SEPARATOR distribution (dot vs comma vs space) —
    the space separator is the suspected over-firer (Aug-12 §5.1) — and how
    often the book is a Roman numeral vs Arabic.
  * A few real sample cells per cue, to eyeball for noise (e.g. Phil. =
    Philippians vs Plato's Philebus; patristic homily leakage).

Nothing here changes data; it only reports. Run:

    python3 cue_audit.py citations.tsv
"""
import sys, csv, re
from collections import Counter, defaultdict

def _raise_csv_limit():
    lim = sys.maxsize
    while True:
        try:
            csv.field_size_limit(lim); break
        except OverflowError:
            lim = int(lim // 10)
_raise_csv_limit()

CORPUS_COL, MATCH_COL, CONTEXT_COL = 4, 8, 9
TARGET = ("homer", "pindar", "nt")
SAMPLES_PER_CUE = 3

# Cue = leading token: an optional 1/2 book-number prefix (NT: "1 Cor") then a
# run of letters. First alpha token only, so a Roman-numeral Homer book
# ("Od. IV 1") is NOT mistaken for the cue.
CUE_RE = re.compile(r"^\s*([12]\s?)?([A-Za-z]+)")
# Homer book-line separator: the char(s) between the book token and the line.
HOMER_BL = re.compile(
    r"^\s*(?:[A-Za-z]+)\.?[\s ]{0,4}"          # cue
    r"(\d{1,2}|[IVXivx]+)"                            # book (Arabic or Roman)
    r"(\.|,\s?|\s)"                                   # separator (captured)
    r"(\d{1,3})")                                     # line start
ROMAN_RE = re.compile(r"^[IVXivx]+$")


def cue_of(cell):
    m = CUE_RE.match(cell or "")
    if not m:
        return None
    prefix = (m.group(1) or "").strip()
    word = m.group(2)
    return (prefix + " " + word).strip() if prefix else word


def sep_label(ch):
    if ch == ".":
        return "dot  ."
    if ch.startswith(","):
        return "comma ,"
    return "space  "


def main():
    if len(sys.argv) < 2:
        print("usage: python3 cue_audit.py citations.tsv"); sys.exit(1)
    path = sys.argv[1]

    cue_counts = {c: Counter() for c in TARGET}
    cue_samples = {c: defaultdict(list) for c in TARGET}
    homer_sep = Counter()
    homer_book_kind = Counter()
    no_cue = Counter()

    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        r = csv.reader(fh, delimiter="\t")
        next(r, None)
        for row in r:
            if len(row) <= CONTEXT_COL:
                continue
            corpus = row[CORPUS_COL]
            if corpus not in cue_counts:
                continue
            cell = row[MATCH_COL]
            cue = cue_of(cell)
            if cue is None:
                no_cue[corpus] += 1
                continue
            key = cue.lower()
            cue_counts[corpus][key] += 1
            if len(cue_samples[corpus][key]) < SAMPLES_PER_CUE:
                cue_samples[corpus][key].append(cell)
            if corpus == "homer":
                m = HOMER_BL.match(cell)
                if m:
                    homer_sep[sep_label(m.group(2))] += 1
                    homer_book_kind["Roman" if ROMAN_RE.match(m.group(1))
                                    else "Arabic"] += 1

    for corpus in TARGET:
        cc = cue_counts[corpus]
        total = sum(cc.values())
        print(f"\n{'='*60}\n{corpus.upper()}  —  {total:,} cued rows"
              + (f"  (+{no_cue[corpus]:,} with no parseable cue)" if no_cue[corpus] else ""))
        print(f"{'-'*60}")
        for cue, n in cc.most_common():
            pct = 100 * n / total if total else 0
            samp = "   e.g. " + " | ".join(cue_samples[corpus][cue][:SAMPLES_PER_CUE])
            print(f"  {cue:12} {n:8,}  {pct:5.1f}%{samp}")
        if corpus == "homer" and homer_sep:
            print(f"\n  Homer book–line SEPARATOR distribution:")
            tot = sum(homer_sep.values())
            for lab, n in homer_sep.most_common():
                print(f"    {lab:8} {n:8,}  {100*n/tot:5.1f}%")
            print(f"  Homer book kind:")
            tb = sum(homer_book_kind.values())
            for lab, n in homer_book_kind.most_common():
                print(f"    {lab:8} {n:8,}  {100*n/tb:5.1f}%")

    print("\nUse this to (a) drop dead cues, (b) confirm high-volume cues are "
          "real not noise, (c) decide whether Homer's space/comma separators "
          "over-fire, (d) spot single-letter or new cues worth adding — then "
          "lock the extractor cue lists before the one re-harvest.")


if __name__ == "__main__":
    main()
