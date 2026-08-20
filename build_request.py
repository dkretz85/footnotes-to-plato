#!/usr/bin/env python3
"""
build_request.py — from an explicit journal roster, report each journal's
presence and exact item count in the JSTOR metadata file, and emit the
item_id list to submit as a dataset request.

Usage:
    python3 build_request.py jstor_metadata_2026-07-18.jsonl.gz

Outputs:
    request_roster.tsv     tier / journal / matched-title / items / reviews
    request_item_ids.txt   one item_id per line (ready to upload to JSTOR)
    request_missing.txt     roster entries that matched NOTHING (investigate)

Matching is exact against the 'is_part_of' string, because we now KNOW the
exact strings from find_titles.py. Each roster entry lists the exact title(s)
to accept; a journal with title variants can list several.
"""
import sys, json, gzip, io, collections

# ---- The roster. Exact 'is_part_of' strings, grouped by tier. -------------
# Tier 1: on-target minable specialist ancient-philosophy journals
# Tier 2: Classics journals that carry ancient-phil work
# Tier 3: general history-of-philosophy / general philosophy (reception)
# Add or remove exact strings here; anything not found is reported.
ROSTER = {
    # ─── EXISTING CORPUS — already held, DO NOT re-request ───────────────
    # Left OUT of the roster so the new deliveries form a clean iid-partition
    # with the current TSV (fusion = concatenate + rerun, no dedup needed).
    # For the record, the 10 held journals are:
    #   T1_specialist: Phronesis, Méthexis, Revue de Philosophie Ancienne
    #   T2_classics:   The Classical Quarterly, Classical Philology,
    #                  The Classical Review
    #   T3_histphil:   Les Études philosophiques, Revue Internationale de
    #                  Philosophie, Archivio di Filosofia,
    #                  History of Philosophy Quarterly

    # ─── NEW T4: classics for Homer / Pindar ────────────────────────────
    # Exact strings confirmed via find_titles.py against the metadata file.
    "T4_classics_epic_lyric": [
        # Greek-literature & philology core (best Homer/Pindar yield)
        "The American Journal of Philology",
        "Harvard Studies in Classical Philology",
        "Mnemosyne",
        # TAPA — ONE journal, THREE dated strings, all needed or 2/3 of the run is lost:
        "Transactions and Proceedings of the American Philological Association",
        "Transactions of the American Philological Association (1974-2014)",
        "Transactions of the American Philological Association (1869-1896)",
        # Broad classics with solid density
        "Greece & Rome",
        "The Classical World",
        "Classical Antiquity",
        "The Classical Journal",
        # Pindar-relevant
        "Quaderni Urbinati di Cultura Classica",
        "Illinois Classical Studies",
        # German philology (heavy Homer; German-language)
        "Hermes",
        # Rheinisches Museum — ONE journal, two strings:
        "Rheinisches Museum für Philologie",
        "Rheinisches Museum für Philologie, Geschichte und griechische Philosophie",
    ],

    # ─── NEW T5: theology / religion for the later Paul instance ─────────
    # Wide scope, multilingual (English + German + French), consistent with
    # the Hermes/RhM inclusion on the classics side.
    "T5_theology_paul": [
        # core NT / biblical studies
        "The Catholic Biblical Quarterly",
        "Journal of Biblical Literature",
        "Journal of the Society of Biblical Literature and Exegesis",  # JBL predecessor
        "Biblica",
        "Novum Testamentum",
        "Neotestamentica",
        "The Biblical World",                    # Chicago, 1893–1920
        "The American Journal of Theology",      # Chicago, 1897–1920
        # general theology / religion
        "The Harvard Theological Review",
        "The Journal of Religion",
        "Church History",
        "Religious Studies",
        "History of Religions",
        "American Journal of Theology & Philosophy",
        # early Christianity / patristics
        "Vigiliae Christianae",
        # Recherches — ONE journal, title change, both strings:
        "Recherches de théologie ancienne et médiévale",
        "Recherches de théologie et philosophie médiévales",
        # German-language theology
        "Zeitschrift für katholische Theologie",
        "Zeitschrift für Theologie und Kirche",
        "Theologische Rundschau",
        "Deutsche Theologie",
        # French-language theology
        # Rev. de Théologie et de Philosophie — ONE journal, two strings:
        "Revue de Théologie et de Philosophie",
        "Revue de Théologie et de Philosophie et Compte-rendu des Principales Publications Scientifiques",
    ],
}

# Which content_subtype values count as "review-like" (for reporting only;
# reviews are KEPT in the request per the include-reviews decision).
REVIEW_HINTS = ("review", "book review", "book note", "book-review")

JOURNAL_FIELD = "is_part_of"
TYPE_FIELDS   = ["content_subtype", "content_type"]
ID_FIELD      = "item_id"
YEAR_FIELD    = "published_date"


def first_present(rec, fields):
    for f in fields:
        v = rec.get(f)
        if v not in (None, ""):
            return v
    return ""


def is_review(dtype):
    d = str(dtype).lower()
    return any(h in d for h in REVIEW_HINTS)


def open_stream(path):
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")


def main():
    if len(sys.argv) != 2:
        print(__doc__); sys.exit(1)
    path = sys.argv[1]

    # exact-title -> (tier, canonical display)
    wanted = {}
    for tier, titles in ROSTER.items():
        for t in titles:
            wanted[t] = tier

    counts   = collections.Counter()          # title -> items
    reviews  = collections.Counter()          # title -> review-like items
    years    = collections.defaultdict(lambda: [9999, 0])  # title -> [min,max]
    ids      = []                             # (tier, title, item_id)

    with open_stream(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            j = rec.get(JOURNAL_FIELD)
            if j not in wanted:
                continue
            counts[j] += 1
            dtype = first_present(rec, TYPE_FIELDS)
            if is_review(dtype):
                reviews[j] += 1
            iid = rec.get(ID_FIELD)
            if iid:
                ids.append((wanted[j], j, iid))
            # track year span
            yr = str(rec.get(YEAR_FIELD, ""))
            for tok in yr.replace("-", " ").split():
                if len(tok) == 4 and tok.isdigit():
                    y = int(tok)
                    lo, hi = years[j]
                    years[j] = [min(lo, y), max(hi, y)]
                    break

    # ---- report ----------------------------------------------------------
    print("=" * 72)
    print(f"{'TIER':14} {'ITEMS':>7} {'REVIEWS':>8}  {'YEARS':>11}  JOURNAL")
    print("=" * 72)
    grand = grand_rev = 0
    missing = []
    for tier, titles in ROSTER.items():
        for t in titles:
            n = counts.get(t, 0)
            if n == 0:
                missing.append((tier, t))
                continue
            r = reviews.get(t, 0)
            lo, hi = years.get(t, [None, None])
            span = f"{lo}\u2013{hi}" if lo else "?"
            grand += n; grand_rev += r
            print(f"{tier:14} {n:7,d} {r:8,d}  {span:>11}  {t}")
    print("-" * 72)
    print(f"{'TOTAL':14} {grand:7,d} {grand_rev:8,d}   (reviews kept in request)")

    if missing:
        print("\nNOT FOUND in file (exact-string mismatch or not on JSTOR):")
        for tier, t in missing:
            print(f"   [{tier}] {t!r}")
        print("   -> if you expected one of these, re-check its exact string")
        print("      with find_titles.py and correct the ROSTER.")

    # ---- write outputs ---------------------------------------------------
    with open("request_roster.tsv", "w", encoding="utf-8") as out:
        out.write("tier\tjournal\titems\treviews\tyear_min\tyear_max\n")
        for tier, titles in ROSTER.items():
            for t in titles:
                if counts.get(t, 0) == 0:
                    continue
                lo, hi = years.get(t, ["", ""])
                out.write(f"{tier}\t{t}\t{counts[t]}\t{reviews.get(t,0)}\t{lo}\t{hi}\n")

    with open("request_item_ids.txt", "w", encoding="utf-8") as out:
        for _, _, iid in ids:
            out.write(f"{iid}\n")

    with open("request_missing.txt", "w", encoding="utf-8") as out:
        for tier, t in missing:
            out.write(f"{tier}\t{t}\n")

    print(f"\nWrote request_roster.tsv     ({grand:,} items across "
          f"{len(counts)} journals)")
    print(f"Wrote request_item_ids.txt   ({len(ids):,} item IDs to submit)")
    print(f"Wrote request_missing.txt    ({len(missing)} unmatched roster rows)")
    print("\nInspect the roster, resolve any NOT FOUND lines, then upload")
    print("request_item_ids.txt with your JSTOR dataset request.")


if __name__ == "__main__":
    main()
