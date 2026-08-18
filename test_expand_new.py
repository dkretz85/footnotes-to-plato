#!/usr/bin/env python3
"""
test_expand_new.py — Homer/Pindar single-line + NT verse expansion in locus.py.
Run: python3 test_expand_new.py
"""
import json, locus

ROM = json.load(open("nt_chapter_lengths.json"))["books"]["Romans"]
COR1 = json.load(open("nt_chapter_lengths.json"))["books"]["1 Corinthians"]
PHLM = json.load(open("nt_chapter_lengths.json"))["books"]["Philemon"]

HOMER = [
    ("Il. 16.7-11", ["Il. 16.7","Il. 16.8","Il. 16.9","Il. 16.10","Il. 16.11"]),
    ("Iliad 2.484-93", ["Il. 2.%d" % n for n in range(484, 494)]),   # 484..493, normalised cue
    ("Od. 4.89",   ["Od. 4.89"]),
    ("Il. XXIV.804", ["Il. 24.804"]),                # Roman book -> Arabic
    ("Od. IV 1",   ["Od. 4.1"]),                     # Roman + space separator
    ("Il. 5, 385", ["Il. 5.385"]),                   # comma separator
    ("Ol. 1.111-12", None),                          # wrong corpus for homer -> handled in dispatch test
]
HOMER_DIVERT = ["Il. 1.1-611"]                       # 611 lines > cap -> None

PINDAR = [
    ("Ol. 1.111-12", ["Ol. 1.111","Ol. 1.112"]),     # abbreviated endpoint
    ("Pyth. 4.162", ["Pyth. 4.162"]),
    ("Nem. 2.1-3", ["Nem. 2.1","Nem. 2.2","Nem. 2.3"]),
    ("Olympian 7.13-14", ["Ol. 7.13","Ol. 7.14"]),   # full name -> canonical
]

NT = [
    ("Rom. 3:21-26", ROM, ["Rom. 3:%d" % v for v in range(21, 27)]),
    ("Rom. 7:25-8:2", ROM, ["Rom. 7:25","Rom. 8:1","Rom. 8:2"]),  # cross-chapter
    ("1 Cor 11:2-16", COR1, ["1 Cor 11:%d" % v for v in range(2, 17)]),
    ("Rom. 3:27", ROM, ["Rom. 3:27"]),               # single verse
]
NT_DIVERT = [("Phlm 6:15-16", PHLM)]                 # chapter 6 doesn't exist

def check(label, got, expected):
    ok = got == expected
    print(("PASS" if ok else "FAIL"), f"{label}")
    if not ok:
        print(f"     expected {expected}")
        print(f"     got      {got}")
    return ok

def run():
    p = f = 0
    for cell, exp in HOMER:
        if exp is None:
            continue
        ok = check(f"homer  {cell!r}", locus.expand_homer(cell), exp); p += ok; f += not ok
    for cell in HOMER_DIVERT:
        ok = check(f"homer  {cell!r} -> divert", locus.expand_homer(cell), None); p += ok; f += not ok
    for cell, exp in PINDAR:
        ok = check(f"pindar {cell!r}", locus.expand_pindar(cell), exp); p += ok; f += not ok
    for cell, lengths, exp in NT:
        ok = check(f"nt     {cell!r}", locus.expand_nt(cell, lengths), exp); p += ok; f += not ok
    for cell, lengths in NT_DIVERT:
        ok = check(f"nt     {cell!r} -> divert", locus.expand_nt(cell, lengths), None); p += ok; f += not ok

    # dispatch through expand_range with corpus tags
    ok = check("dispatch homer", locus.expand_range("Il. 16.7-8", "homer"),
               ["Il. 16.7","Il. 16.8"]); p += ok; f += not ok
    ok = check("dispatch nt", locus.expand_range("Rom. 3:21-22", "nt", nt_lengths=ROM),
               ["Rom. 3:21","Rom. 3:22"]); p += ok; f += not ok
    # --- Bekker band expansion ---
    ok = check("bekker cross-column 1097b8-1098a20",
               locus.expand_bekker("1097b8-1098a20"),
               ["1097b","1097b15","1097b30","1098a","1098a15"]); p += ok; f += not ok
    ok = check("bekker within-column 453b11-453b20",
               locus.expand_bekker("453b11-453b20"),
               ["453b","453b15"]); p += ok; f += not ok
    ok = check("bekker single cite keeps exact line",
               locus.expand_bekker("1097b8"), ["1097b8"]); p += ok; f += not ok
    ok = check("bekker bare column verbatim",
               locus.expand_bekker("1094a"), ["1094a"]); p += ok; f += not ok
    ok = check("bekker over-cap -> divert",
               locus.expand_bekker("1097a-1300b"), None); p += ok; f += not ok
    ok = check("dispatch bekker",
               locus.expand_range("1097b8-1098a20", "bekker"),
               ["1097b","1097b15","1097b30","1098a","1098a15"]); p += ok; f += not ok

    print(f"\n{p} passed, {f} failed")
    return f == 0

if __name__ == "__main__":
    import sys
    sys.exit(0 if run() else 1)
