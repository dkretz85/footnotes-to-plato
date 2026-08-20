#!/usr/bin/env python3
"""Write viewer_data/authors.json — the work -> author map Viewer C's index needs.

works_index.json carries a `system` tag (homer / pindar / nt / stephanus /
bekker) but not an author, and the tag does not separate Plato from Aristotle:
a batch of Aristotle treatises are mislabelled `stephanus`
(TEMPORAL_FINDINGS_POST_AUDIT §9, "build_viewer_data.work_system mislabel"), so
`system` alone would file De Anima or the Metaphysics under Plato. Author is
therefore resolved as:

    system == homer   -> Homer
    system == pindar  -> Pindar          (the four ode-books)
    system == nt      -> Paul
    otherwise         -> Aristotle if the title is in ARISTOTLE, else Plato

ARISTOTLE is the explicit, reviewable list of Aristotelian titles (index names,
underscored). Everything else on the Stephanus/Bekker side is Plato. Output:

    viewer_data/authors.json   {"Republic": "Plato", "Metaphysics": "Aristotle", ...}

Run:  python3 build_authors.py          # writes viewer_data/authors.json
      python3 build_authors.py --check   # print the mapping, write nothing
"""
import argparse, json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(ROOT, "viewer_data", "works_index.json")
OUT = os.path.join(ROOT, "viewer_data", "authors.json")

# Aristotelian works, by their works_index `work` name (underscored). Any
# Stephanus/Bekker work NOT in this set is Plato. Edit here if a title is added.
ARISTOTLE = {
    "Metaphysics", "Nicomachean_Ethics", "Eudemian_Ethics", "Magna_Moralia",
    "Politics", "Rhetoric", "Rhetorica_ad_Alexandrum", "Poetics",
    "Physics", "De_Caelo", "De_Generatione_et_Corruptione", "Meteorology",
    "De_Anima", "De_Sensu", "De_Memoria", "De_Somno", "De_Insomniis",
    "De_Divinatione_per_Somnum", "De_Longitudine_Vitae", "De_Juventute",
    "De_Respiratione", "Historia_Animalium", "De_Partibus_Animalium",
    "De_Motu_Animalium", "De_Incessu_Animalium", "De_Generatione_Animalium",
    "Categories", "De_Interpretatione", "Prior_Analytics", "Posterior_Analytics",
    "Topics", "Sophistical_Refutations", "Problems",
}

SYSTEM_AUTHOR = {"homer": "Homer", "pindar": "Pindar", "nt": "Paul"}
# chronological order the index renders authors in
AORDER = ["Homer", "Pindar", "Plato", "Aristotle", "Paul"]


def author_of(rec):
    sys_ = rec.get("system", "")
    if sys_ in SYSTEM_AUTHOR:
        return SYSTEM_AUTHOR[sys_]
    return "Aristotle" if rec["work"] in ARISTOTLE else "Plato"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="print the mapping and counts, write nothing")
    args = ap.parse_args()

    if not os.path.exists(INDEX):
        sys.exit(f"error: {INDEX} not found — run build_viewer_data.py first")
    works = json.load(open(INDEX, encoding="utf-8"))

    mapping = {rec["work"]: author_of(rec) for rec in works}

    from collections import Counter
    counts = Counter(mapping.values())
    print(f"mapped {len(mapping)} works -> "
          + ", ".join(f"{a} {counts.get(a, 0)}" for a in AORDER))

    # sanity: a Bekker-tagged work that landed as Plato, or a Stephanus Aristotle
    # still tagged Plato despite being in ARISTOTLE — surface anything surprising
    by_author = {a: sorted(w for w, au in mapping.items() if au == a) for a in AORDER}
    for a in AORDER:
        if by_author[a]:
            print(f"\n  {a} ({len(by_author[a])}):")
            print("    " + ", ".join(by_author[a]))
    unknown = [w for w, a in mapping.items() if a not in AORDER]
    if unknown:
        sys.exit(f"\nerror: unclassified works: {unknown}")

    if args.check:
        print("\n--check: nothing written")
        return

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"\n-> wrote {OUT}")


if __name__ == "__main__":
    main()
