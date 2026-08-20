#!/usr/bin/env python3
"""
find_titles.py — dump the exact journal-title strings JSTOR uses, for any
title containing one of our probe fragments. Run this to discover the real
spellings before committing them to the request roster (build_request.py).

This is the EXPANSION-BATCH version: fragments target the new classics
journals (Homer/Pindar) and the theology/NT journals (later Paul instance).
The original ancient-philosophy fragments are kept too, so re-running this
reproduces the existing corpus's strings alongside the new ones (useful for a
single fused manifest — see the double-request note below).

Usage:
    python3 find_titles.py jstor_metadata_2026-07-18.jsonl.gz

Reading the output:
    - COUNT is the number of items (articles/reviews) under that exact string.
    - The title is printed with repr() so stray whitespace / odd characters are
      visible. COPY THE STRING VERBATIM (without the surrounding quotes repr
      adds) into build_request.py's ROSTER.
    - The broad nets ('homer', 'pindar', ...) will catch extra unrelated
      titles (e.g. a journal with 'Homer' in an article-level field won't match,
      but a themed volume might). That's expected — eyeball the list and take
      only the real journal titles.
"""
import sys, json, gzip, io, collections, unicodedata

# Fragments to hunt for — lowercased, accent-stripped substring match so we
# catch things regardless of umlauts / diacritics / casing.
FRAGMENTS = [
    # === THEOLOGY / RELIGIOUS-STUDIES SURVEY (for the Paul instance) =========
    # Goal: map the FULL landscape of venues where Pauline citation plausibly
    # lives — not just strict NT exegesis, but systematic theology, patristics,
    # early-church history, and religious studies. Broad nets on purpose; the
    # output WILL contain noise (sermons, pamphlets, OT-only venues) — eyeball
    # and keep only the real scholarly journals with usable runs.

    # --- NT exegesis (the core) ---------------------------------------------
    "biblical literature",               # JBL (+ its predecessor 'Society of Biblical Literature and Exegesis')
    "novum testamentum",
    "new testament",                     # New Testament Studies, ZNW-English forms, etc.
    "neutestamentliche",                 # Zeitschrift für die neutestamentliche Wissenschaft (ZNW)
    "catholic biblical",                 # CBQ
    "neotestamentica",
    "biblica",                           # Biblica (Pontifical Biblical Institute)
    "biblical",                          # broad net for biblical-studies venues

    # --- systematic / general theology --------------------------------------
    "theological studies",               # Journal of Theological Studies; Theological Studies
    "theological review",                # Harvard Theological Review; Anglican Theol. Review
    "theology",                          # broad net
    "theologische",                      # German theology venues
    "theologie",
    "scottish journal of theology",
    "modern theology",

    # --- early Christianity / patristics ------------------------------------
    "early christian",                   # Journal of Early Christian Studies
    "christian studies",
    "vigiliae",                          # Vigiliae Christianae
    "church history",
    "ecclesiastical history",
    "patristic",

    # --- religion (general, where philosophy-of-religion Paul work appears) --
    "journal of religion",
    "religious studies",
    "history of religions",
    "harvard theological",
    "interpretation",                    # 'Interpretation: A Journal of Bible and Theology'

    # === CLASSICS ADDS (Homer / Pindar) — confirmed strings from prior run ===
    # Kept so a combined re-run reproduces them; exact strings already harvested.
    "american journal of philology",
    "philological association",          # TAPA — NOTE: 3 distinct dated strings
    "harvard studies in classical",
    "greece & rome", "greece and rome",
    "classical world",
    "quaderni urbinati",
    "mnemosyne",
    "illinois classical",
    "hermes",
    "rheinisches museum",
    "classical antiquity",
    "classical journal",
]

def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))

def norm(s):
    return strip_accents(str(s)).lower()

def open_stream(path):
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")

def main():
    if len(sys.argv) != 2:
        print(__doc__); sys.exit(1)
    path = sys.argv[1]
    hits = collections.Counter()   # exact title string -> count
    with open_stream(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            j = rec.get("is_part_of")
            if not j:
                continue
            jn = norm(j)
            if any(f in jn for f in FRAGMENTS):
                hits[j] += 1

    print(f"{'COUNT':>8}  TITLE  (exact string in file)")
    print("=" * 70)
    for title, n in sorted(hits.items(), key=lambda kv: -kv[1]):
        # show a repr so hidden/odd whitespace becomes visible
        print(f"{n:8,d}  {title!r}")

if __name__ == "__main__":
    main()
