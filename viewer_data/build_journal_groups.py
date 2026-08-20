#!/usr/bin/env python3
"""Regenerate journal_groups.json for the full 48-journal corpus.

Viewer C's journal-set selector (All / Philosophy / Classics / Theology & NT)
is load-bearing: the audit found it can *reverse* a finding (Republic VIII/IX
fall across all journals but rise within philosophy). Until now the grouping
covered only the 10 original Plato/Aristotle journals; the theology & NT
venues and the rest of the classics/philosophy set were ungrouped, so the
"Theology & NT" preset had nothing to select and `--journals` could not do a
within-community split for the new corpora (TEMPORAL_FINDINGS_POST_AUDIT §9).

This script writes the field classification for ALL journals in meta.json into
the existing journal_groups.json schema:

    {"_comment": [...], "groups": {
        "philosophy": {"label": "Philosophy",     "journals": [...]},
        "classics":   {"label": "Classics",       "journals": [...]},
        "theology":   {"label": "Theology & NT",  "journals": [...]}}}

The classification below is an EDITORIAL judgement about disciplinary culture,
kept as data precisely so it can be argued with. Review FIELD before shipping —
the seven philosophy and three classics journals marked (original) reproduce the
prior grouping unchanged; everything else is newly classified here. A handful of
genuinely cross-disciplinary venues (the "théologie et philosophie" titles,
Religious Studies, History of Religions) are judgement calls flagged inline.

Run:  python3 build_journal_groups.py            # writes journal_groups.json
      python3 build_journal_groups.py --check    # validate coverage, write nothing
"""
import argparse, json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
META = os.path.join(ROOT, "viewer_data", "meta.json")
OUT = os.path.join(ROOT, "journal_groups.json")

# ---------------------------------------------------------------------------
# Field per journal. Every journal in meta.json must appear exactly once.
# "(original)" = carried over verbatim from the prior 10-journal grouping.
# ---------------------------------------------------------------------------
FIELD = {
    # -- philosophy ---------------------------------------------------------
    "Phronesis": "philosophy",                          # (original)
    "Méthexis": "philosophy",                           # (original)
    "Revue de Philosophie Ancienne": "philosophy",      # (original)
    "History of Philosophy Quarterly": "philosophy",    # (original)
    "Revue Internationale de Philosophie": "philosophy",# (original)
    "Les Études philosophiques": "philosophy",          # (original)
    "Archivio di Filosofia": "philosophy",              # (original)

    # -- classics -----------------------------------------------------------
    "The Classical Quarterly": "classics",              # (original)
    "Classical Philology": "classics",                  # (original)
    "The Classical Review": "classics",                 # (original)
    "Mnemosyne": "classics",
    "The American Journal of Philology": "classics",
    "Hermes": "classics",
    "Harvard Studies in Classical Philology": "classics",
    "Rheinisches Museum für Philologie": "classics",
    "Quaderni Urbinati di Cultura Classica": "classics",
    "Classical Antiquity": "classics",
    "The Classical Journal": "classics",
    "Transactions of the American Philological Association (1974-2014)": "classics",
    "The Classical World": "classics",
    "Illinois Classical Studies": "classics",
    "Transactions and Proceedings of the American Philological Association": "classics",
    "Greece & Rome": "classics",
    "Transactions of the American Philological Association (1869-1896)": "classics",
    "Rheinisches Museum für Philologie, Geschichte und griechische Philosophie": "classics",

    # -- theology & New Testament ------------------------------------------
    "The Catholic Biblical Quarterly": "theology",
    "Journal of Biblical Literature": "theology",
    "Novum Testamentum": "theology",
    "Neotestamentica": "theology",
    "The Harvard Theological Review": "theology",
    "Vigiliae Christianae": "theology",
    "The Journal of Religion": "theology",
    "Recherches de théologie ancienne et médiévale": "theology",
    "Recherches de théologie et philosophie médiévales": "theology",  # judgement: theology venue
    "Biblica": "theology",
    "The American Journal of Theology": "theology",
    "The Biblical World": "theology",
    "Church History": "theology",
    "History of Religions": "theology",                 # judgement: religion, not classics
    "Revue de Théologie et de Philosophie": "theology", # judgement: Protestant theology venue
    "Zeitschrift für katholische Theologie": "theology",
    "Zeitschrift für Theologie und Kirche": "theology",
    "Religious Studies": "theology",                    # judgement: philosophy of religion, filed w/ theology
    "American Journal of Theology & Philosophy": "theology",  # judgement: theology venue
    "Theologische Rundschau": "theology",
    "Revue de Théologie et de Philosophie et Compte-rendu des Principales Publications Scientifiques": "theology",
    "Journal of the Society of Biblical Literature and Exegesis": "theology",
    "Deutsche Theologie": "theology",
}

LABELS = {"philosophy": "Philosophy", "classics": "Classics", "theology": "Theology & NT"}
ORDER = ["philosophy", "classics", "theology"]

COMMENT = [
    "Field classification for the journals in the corpus. Kept as DATA, not code,",
    "because it is an editorial judgement about disciplinary culture and a user may",
    "reasonably disagree. Regenerate with build_journal_groups.py; edit FIELD there.",
    "",
    "'philosophy' = journals of philosophy / history of philosophy.",
    "'classics'   = general classical-studies journals (philology, literature,",
    "               history, papyrology) where ancient philosophy sits alongside.",
    "'theology'   = theology, New Testament and religious-studies journals — the",
    "               venues that carry the Pauline corpus. A few cross-disciplinary",
    "               titles (the theologie-et-philosophie journals, Religious Studies,",
    "               History of Religions) are judgement calls; see the script.",
    "Both viewers and temporal_analysis.py --journals pick this up.",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="validate coverage against meta.json and exit without writing")
    args = ap.parse_args()

    if not os.path.exists(META):
        sys.exit(f"error: {META} not found — run build_viewer_data.py first")
    meta = json.load(open(META, encoding="utf-8"))
    journals = list(meta.get("journals", []))
    if not journals:
        sys.exit("error: meta.json has no 'journals' list")

    known = set(FIELD)
    corpus = set(journals)
    missing = sorted(corpus - known)     # in the corpus, not classified
    stray = sorted(known - corpus)       # classified, not in the corpus (typo?)
    ok = True
    if missing:
        ok = False
        print("UNCLASSIFIED journals (add them to FIELD):", file=sys.stderr)
        for j in missing:
            print(f"    {meta['journal_counts'].get(j, 0):>7}  {j}", file=sys.stderr)
    if stray:
        ok = False
        print("FIELD names a journal not in the corpus (typo?):", file=sys.stderr)
        for j in stray:
            print(f"    {j}", file=sys.stderr)
    bad = {j: f for j, f in FIELD.items() if f not in LABELS}
    if bad:
        ok = False
        print(f"unknown field label(s): {bad}", file=sys.stderr)
    if not ok:
        sys.exit(1)

    # order journals within each group by descending citation count, so the
    # group's dominant venue reads first (matches the viewer's set-line copy)
    jc = meta.get("journal_counts", {})
    groups = {}
    for key in ORDER:
        members = sorted((j for j in journals if FIELD[j] == key),
                         key=lambda j: -jc.get(j, 0))
        groups[key] = {"label": LABELS[key], "journals": members}

    counts = {k: len(v["journals"]) for k, v in groups.items()}
    print(f"classified {len(journals)} journals -> "
          + ", ".join(f"{LABELS[k]} {counts[k]}" for k in ORDER))
    for k in ORDER:
        top = groups[k]["journals"][0] if groups[k]["journals"] else "—"
        print(f"  {LABELS[k]:<14} led by {top} ({jc.get(top, 0):,})")

    if args.check:
        print("--check: coverage OK, nothing written")
        return

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"_comment": COMMENT, "groups": groups}, f,
                  ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"-> wrote {OUT}")


if __name__ == "__main__":
    main()
