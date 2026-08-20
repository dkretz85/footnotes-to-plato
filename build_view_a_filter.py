#!/usr/bin/env python3
"""Regenerate viewer_data/view_a_filter.json — the work × journal × year matrix the
Works-over-time viewer (view_a) plots. Derived from the committed view_b dots, so it
covers the full corpus (build_viewer_data.py normally emits it from the source
delivery, which isn't in the repo).

Shape (series.js): matrix[work][metric][journal][year] = n, metric in
{"citations","articles"} — citations = placed-citation count (one per dot),
articles = distinct citing-article count (distinct iid).

Run:  python3 build_view_a_filter.py
"""
import json, os, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
VD = os.path.join(ROOT, "viewer_data")
INDEX = os.path.join(VD, "works_index.json")
VB = os.path.join(VD, "view_b")
OUT = os.path.join(VD, "view_a_filter.json")


def safe(w):
    return w.replace(" ", "_").replace("/", "_")


def main():
    works = json.load(open(INDEX, encoding="utf-8"))
    matrix, missing = {}, []
    for rec in works:
        work = rec["work"]
        path = os.path.join(VB, safe(work) + ".json")
        if not os.path.exists(path):
            missing.append(work)
            continue
        dots = json.load(open(path, encoding="utf-8")).get("dots", [])
        cites = defaultdict(lambda: defaultdict(int))       # journal -> year -> n
        arts = defaultdict(lambda: defaultdict(set))        # journal -> year -> {iid}
        for d in dots:
            y = d.get("year", "")
            if not (isinstance(y, str) and y.isdigit() and len(y) == 4):
                continue
            j = d.get("journal", "")
            if not j:
                continue
            cites[j][y] += 1
            arts[j][y].add(d.get("iid", ""))
        matrix[work] = {
            "citations": {j: dict(ys) for j, ys in cites.items()},
            "articles": {j: {y: len(s) for y, s in ys.items()} for j, ys in arts.items()},
        }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(matrix, f, ensure_ascii=False)
    print(f"-> wrote {OUT}: {len(matrix)} works"
          + (f"  ({len(missing)} without view_b dots: {missing})" if missing else ""))


if __name__ == "__main__":
    main()
