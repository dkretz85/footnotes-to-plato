#!/usr/bin/env python3
"""
test_extractor_regex.py — validate the v2 extractor's harvest behaviour before
the (expensive) re-harvest. Checks range capture, the letter-guard against
bibliographic noise, de-overlap, dropped Pindar cues, and Roman NT numbers.

    python3 test_extractor_regex.py
"""
import build_citation_db_v2 as ex

def matches(text):
    """(corpus, match) pairs in reading order."""
    return [(c, g) for c, g, s, e in ex.iter_matches_in_text(text)]

CASES = [
    # --- Greek range capture (the core fix) ---
    ("see Republic 620a-622c on the myth",
     [("ambiguous", "620a-622c")]),                 # whole range, endpoint NOT re-yielded
    ("at 553a-e Plato turns to",
     [("ambiguous", "553a-e")]),                    # bare-section tail inherits page
    ("Bekker 1097b8-1098a20 discusses",
     [("bekker", "1097b8-1098a20")]),
    ("the sure-Stephanus 553d-556a range",
     [("stephanus", "553d-556a")]),
    ("en-dash 620a–622c typeset",
     [("ambiguous", "620a–622c")]),

    # --- letter-guard: bibliographic page ranges must NOT grow a tail ---
    ("BRUNSCHWIG (1996a), 123-25 and",
     [("bekker", "1996a")]),                        # '-123-25' has no letter -> no tail
    ("cf. 327a-based reading here",
     [("ambiguous", "327a")]),                      # hyphenated word -> \b rejects '-b...'
    ("Rep. 331d-example shows",
     [("stephanus", "331d")]),

    # --- single-unit pass-through unchanged ---
    ("plain 80d5 citation",  [("stephanus", "80d5")]),
    ("bare 234a here",       [("ambiguous", "234a")]),   # 2-3 digit + a/b = ambiguous
    ("bare 1094a here",      [("bekker", "1094a")]),      # 4 digit + a/b = bekker (Aristotle)

    # --- de-overlap keeps the two SEPARATE cites when a dash is prose, not a range ---
    ("327a — but 331d elsewhere",
     [("ambiguous", "327a"), ("stephanus", "331d")]),  # spaced em-dash: two cites, tight-dash rule

    # --- Homer / Pindar / NT still captured (incl. ranges & roman) ---
    ("Iliad 2.484-93 lists",     [("homer", "Iliad 2.484-93")]),
    ("Il. XXIV.804 the ransom",  [("homer", "Il. XXIV.804")]),
    ("Ol. 1.111-12 of Pindar",   [("pindar", "Ol. 1.111-12")]),
    ("1 Cor 11:2-16 on veils",   [("nt", "1 Cor 11:2-16")]),

    # --- Roman-numeral NT letter numbers (newly added) ---
    ("II Cor 3:6 says",  [("nt", "II Cor 3:6")]),
    ("I Tim 3:16 hymn",  [("nt", "I Tim 3:16")]),
    ("II Thess 2:15 on", [("nt", "II Thess 2:15")]),

    # --- dropped bare Pindar cue must NOT fire; ode-typed cue still does ---
    ("Pind. 4.162 unresolvable", []),
    ("Pyth. 4.162 resolvable", [("pindar", "Pyth. 4.162")]),
]

def run():
    passed = failed = 0
    for text, expected in CASES:
        got = matches(text)
        ok = got == expected
        print(("PASS" if ok else "FAIL"), repr(text))
        if not ok:
            print(f"     expected {expected}")
            print(f"     got      {got}")
        passed += ok; failed += not ok
    print(f"\n{passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    import sys
    sys.exit(0 if run() else 1)
