#!/usr/bin/env python3
"""Reshape the temporal_*.json analysis files into the data Viewer C consumes.

Viewer C ("how attention shifted over time within a single work") reads, per
(work, grain, journal-set): a shape verdict, a passages/books x decades heatmap,
per-decade citation volume, and the named movers. The temporal_*.json files carry
far more than that (permutation nulls, FDR tables, sparsity, focus trajectories);
this script distils them into two compact, viewer-ready files that load the same
way view_a / view_b data does (viewer_data/, published to /data/viewer/):

    viewer_data/view_c.json          index: every text, its author, counts, and
                                     whether it is testable anywhere (step 1)
    viewer_data/view_c/<work>.json   per-text bundle: one entry per grain x set,
                                     each with shape, heatmap, volume, movers

THE ONE STRUCTURAL RULE (handoff README): the shape verdict, the view mode and the
caption are derived TOGETHER, here, once. `shape_of()` is that single place; the
viewer never re-decides what to show. Shape codes:

    1p one-direction, passage-led     rp rose-and-fell, passage-led
    1w one-direction, diffuse         rw rose-and-fell, diffuse
    s  steady (well-powered null)     t  too thin to test

Mapping (from TEMPORAL_FINDINGS_POST_AUDIT and David's marginal call):

    no temporal file / stable+under-powered .......... t
    stable + two_bin_flat_only (real >=3-period) ..... rp / rw   (non-monotonic)
    stable + stability_powered ....................... s
    REAL ............................................. 1p / 1w
    marginal + two_bin_understates (>=3-period) ...... rp / rw
    marginal + FDR-solid two-bin movers .............. 1p
    marginal, weak, diffuse .......................... 1w  (hedged: near the floor)

passage-led vs diffuse: FDR-solid two-bin movers for one-direction; the >=3-period
concentration (an FDR survivor AND top-5 >= 40% of dispersion, per §3a) for
rose-and-fell. The determination is per grain, so it follows the grain toggle.

Run (after run_temporal.py has produced the temporal_*.json):
    python3 build_view_c.py
    python3 build_view_c.py --check      # report coverage, write nothing
"""
import argparse, glob, json, os, re, sys
from collections import defaultdict, Counter
from temporal_analysis import passage_label   # same unit labels as the analysis

ROOT = os.path.dirname(os.path.abspath(__file__))
VD = os.path.join(ROOT, "viewer_data")
INDEX = os.path.join(VD, "works_index.json")
AUTHORS = os.path.join(VD, "authors.json")
GROUPS = os.path.join(ROOT, "journal_groups.json")
OUT_INDEX = os.path.join(VD, "view_c.json")
OUT_DIR = os.path.join(VD, "view_c")

# journal -> field, for the custom-set builder (only offer journals with citations)
JFIELD = {}
if os.path.exists(GROUPS):
    for key, g in json.load(open(GROUPS, encoding="utf-8"))["groups"].items():
        for j in g.get("journals", []):
            JFIELD[j] = key

SETS = ["all", "phil", "classics", "theo"]
SET_SUFFIX = {"all": "", "phil": "philosophy", "classics": "classics", "theo": "theology"}
# 14 decade columns, 1890s .. 2020s
DECADES = [1890 + 10 * i for i in range(14)]


def safe(w):
    return w.replace(" ", "_").replace("/", "_")


def decade_idx(year):
    d = (int(year) // 10) * 10
    return max(0, min(13, (d - 1890) // 10))


# ---- text-order sort keys -------------------------------------------------
_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
_GREEK_META = "ΑαΒΓΔΕΖΗΘΙΚΛΜΝ"          # Metaphysics book order (little-alpha 2nd)
_PINDAR_SHELF = {"O": 0, "P": 1, "N": 2, "I": 3}


def roman_to_int(s):
    s = s.replace("*", "").strip().upper()
    if not s or any(c not in _ROMAN for c in s):
        return None
    total, prev = 0, 0
    for c in reversed(s):
        v = _ROMAN[c]
        total += -v if v < prev else v
        prev = max(prev, v)
    return total


def sort_key(label, system, grain):
    """A (primary, secondary) key that puts units in the order they appear in the
    text — books/chapters by their sequence, passages by page then section."""
    lab = label.strip()
    if grain == "book":
        if system == "pindar":                     # "O.3" -> shelf, then ode number
            m = re.match(r"([OPNI])\.?\s*(\d+)", lab)
            if m:
                return (_PINDAR_SHELF.get(m.group(1), 9), int(m.group(2)))
        if system in ("homer", "nt") or lab.strip("*").isdigit():
            m = re.match(r"(\d+)", lab)
            return (int(m.group(1)) if m else 999, 0)
        if lab.strip("* ") and lab.strip("* ")[0] in _GREEK_META:  # Metaphysics letters
            gi = _GREEK_META.find(lab.strip("* ")[0])
            return (gi if gi >= 0 else 999, 0)
        ri = roman_to_int(lab)                      # Republic/Laws/NE/EE
        if ri is not None:
            return (ri, 1 if "*" in lab else 0)
        return (999, 0)
    # passage grain: leading page number, then section letters
    m = re.match(r"(\d+)\s*([a-z]*)", lab)
    if m:
        return (int(m.group(1)), m.group(2))
    return (10 ** 9, lab)


# ---- shape derivation (the single source of truth) ------------------------
def _hero_one_direction(d):
    return d.get("n_fdr_movers_solid", 0) >= 1


def _hero_reversing(d):
    # §3a: name the rose-and-fell passages only when the >=3-period structure has
    # FDR survivors (De Anima: 404a/431b/405a). A structure with zero survivors is
    # diffuse however concentrated (Timaeus, Laws) -> naming heroes would fabricate.
    c = (d.get("multibin_structure") or {}).get("concentration") or {}
    return c.get("n_structure_movers_fdr", 0) >= 1


def shape_of(d):
    """Return (shape_code, hedged). d is a temporal file dict, or None (no file)."""
    if d is None:
        return "t", False
    v = d.get("verdict")
    if v == "stable":
        if d.get("two_bin_flat_only"):                 # non-monotonic hiding under a flat 2-bin
            return ("rp" if _hero_reversing(d) else "rw"), False
        if d.get("stability_powered"):
            return "s", False
        return "t", False                              # too-sparse-to-tell
    if v == "REAL":
        return ("1p" if _hero_one_direction(d) else "1w"), False
    if v == "marginal":
        if d.get("two_bin_understates"):               # strong >=3-period structure
            return ("rp" if _hero_reversing(d) else "rw"), True
        if _hero_one_direction(d):
            return "1p", True
        return "1w", True                              # weak, diffuse — hedged copy
    return "t", False


# ---- per-variant reshape --------------------------------------------------
def build_variant(d):
    """Compact heatmap + volume + movers for one temporal file."""
    grain = d.get("grain", "passage")
    system = d.get("system", "stephanus")
    shape, hedged = shape_of(d)

    # per-decade citation volume (5-yr bins folded into decades)
    vol = [0] * 14
    for b, n in (d.get("bin_totals") or {}).items():
        vol[decade_idx(b)] += n
    # rows = the units we have decade trajectories for (top_passages, <=25),
    # returned to text order. Column-normalised share uses the WORK-WIDE decade
    # total (vol), so displayed rows are a true share of each decade even when a
    # long tail is not drawn.
    named = _named_set(d, shape)
    rows = []
    for p in d.get("top_passages", []):
        cells = [0] * 14
        for b, n in (p.get("by_bin") or {}).items():
            cells[decade_idx(b)] += n
        share = [round(cells[i] / vol[i], 4) if vol[i] else 0.0 for i in range(14)]
        # `share` (column-normalised, share of each decade) drives the heatmap;
        # `counts` (raw distinct-article counts per decade) lets the viewer compute
        # a true before/after share-shift at any split year for the strip.
        rows.append({"label": p["passage"], "named": p["passage"] in named,
                     "arts": p.get("total_articles", 0), "share": share, "counts": cells,
                     "_k": sort_key(p["passage"], system, grain)})
    rows.sort(key=lambda r: r["_k"])
    for r in rows:
        del r["_k"]

    return {
        "shape": shape, "hedged": hedged,
        "articles": d.get("n_articles", 0),
        "n_units": d.get("n_passages", len(rows)),
        "split_year": d.get("split_year"),
        "volume": vol,
        "rows": rows,
        "movers": _movers(d, shape, system, grain),
    }


def _named_set(d, shape):
    if shape in ("1p",):
        return {m["passage"] for m in d.get("top_movers", [])
                if m.get("significant_fdr") and not m.get("floor_fail_early")}
    if shape == "rp":
        return {m["passage"] for m in d.get("multibin_movers", [])
                if m.get("significant_fdr")}
    return set()   # 1w / rw / s / t name nothing


def _movers(d, shape, system, grain):
    if shape == "1p":
        out = []
        for m in d.get("top_movers", []):
            if not (m.get("significant_fdr") and not m.get("floor_fail_early")):
                continue
            out.append({
                "label": m["passage"],
                "delta_share": round(m.get("delta", 0) * 100, 1),      # points of share
                "delta_arts": m.get("late_articles", 0) - m.get("early_articles", 0),
                "gloss": "",                                            # from passage index (todo)
                "_k": sort_key(m["passage"], system, grain)})
        out.sort(key=lambda r: abs(r["delta_share"]), reverse=True)
        for r in out:
            del r["_k"]
        return out[:8]
    if shape == "rp":
        out = []
        for m in d.get("multibin_movers", []):
            if not m.get("significant_fdr"):
                continue
            peak = _peak_decade(d, m["passage"])
            out.append({"label": m["passage"], "peak": peak, "gloss": "",
                        "arts": m.get("total_articles", 0)})
        return out[:8]
    return []


def build_custom(dots, system, grain, labels):
    """Per-(unit, decade, journal) distinct-article counts, so the viewer can sum an
    arbitrary journal set into a descriptive heatmap client-side (no verdict). `labels`
    are the rows to draw (the all-journals map's units, in text order). Distinct-article
    counts sum cleanly across journals because each article sits in one journal."""
    if not labels:
        return None
    seen = defaultdict(set)          # (unit, decade, journal) -> {iid}
    jcount = Counter()
    for dot in dots:
        y = dot.get("year", "")
        if not (isinstance(y, str) and y.isdigit() and len(y) == 4):
            continue
        if grain == "book":
            u = dot.get("book", "")
            if not u:
                continue
        else:
            u = passage_label(system, dot.get("book", ""), dot.get("page"), dot.get("section", ""))
        j = dot.get("journal", "")
        if not j:
            continue
        seen[(u, decade_idx(y), j)].add(dot.get("iid", ""))
        jcount[j] += 1
    if not jcount:
        return None
    jlist = sorted(jcount, key=lambda j: -jcount[j])
    jidx = {j: i for i, j in enumerate(jlist)}
    jvol = defaultdict(lambda: [0] * 14)                    # journal -> [14] work-wide
    ucell = defaultdict(lambda: defaultdict(lambda: [0] * 14))  # unit -> journal -> [14]
    for (u, d, j), iids in seen.items():
        n = len(iids)
        jvol[jidx[j]][d] += n
        ucell[u][jidx[j]][d] += n
    label_set = set(labels)
    units = [{"label": lab, "jc": {str(ji): c for ji, c in ucell.get(lab, {}).items() if any(c)}}
             for lab in labels]
    return {
        "journals": [[j, JFIELD.get(j, "")] for j in jlist],
        "units": units,
        "jvol": {str(ji): c for ji, c in jvol.items()},
    }


def _peak_decade(d, label):
    for p in d.get("top_passages", []):
        if p["passage"] == label:
            cells = [0] * 14
            for b, n in (p.get("by_bin") or {}).items():
                cells[decade_idx(b)] += n
            i = max(range(14), key=lambda k: cells[k])
            return f"{DECADES[i]}s"
    return ""


# ---- driver ---------------------------------------------------------------
def load(work, grain, jset):
    suf = SET_SUFFIX[jset]
    name = f"temporal_{safe(work)}"
    if suf:
        name += "_" + suf
    if grain == "book":
        name += "_book"
    path = os.path.join(ROOT, name + ".json")
    if not os.path.exists(path):
        return None
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception as e:
        print(f"  !! {path}: {e}", file=sys.stderr)
        return None


def grains_for(author, faceted):
    if author == "Pindar":
        return ["book"]
    if author in ("Homer", "Paul"):
        return ["book"]
    # faceted works: book grain first, so it is the default and the leading toggle
    return ["book", "passage"] if faceted else ["passage"]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report coverage, write nothing")
    args = ap.parse_args()

    works = json.load(open(INDEX, encoding="utf-8"))
    authors = json.load(open(AUTHORS, encoding="utf-8"))
    by_name = {w["work"]: w for w in works}

    # Pindar is one pooled Viewer-C text (units = odes); its four ode-books are
    # not per-work maps (line grain is hopeless), so they fold into "Pindar".
    entries, index = {}, []
    shape_tally = defaultdict(int)

    def process(work, author, faceted, citations, articles, display, pool_file=None):
        grains = grains_for(author, faceted)
        variants, any_testable, default_grain = {}, False, grains[0]
        # for Pindar the file base is the pool ("Pindar"); else the work name
        for grain in grains:
            for jset in SETS:
                d = (load(pool_file, grain, jset) if pool_file else load(work, grain, jset))
                shape, _ = shape_of(d)
                shape_tally[shape] += 1
                if d is None:
                    variants[f"{grain}|{jset}"] = {"shape": "t", "hedged": False,
                                                   "articles": 0, "rows": [], "volume": [0] * 14,
                                                   "movers": [], "n_units": 0, "split_year": None}
                else:
                    variants[f"{grain}|{jset}"] = build_variant(d)
                    if shape != "t":
                        any_testable = True
        # default grain: prefer the one whose all-journals variant is testable
        for grain in grains:
            if variants.get(f"{grain}|all", {}).get("shape", "t") != "t":
                default_grain = grain
                break
        med = variants.get(f"{default_grain}|all", {}).get("split_year")
        # per-journal data for the custom-set builder (descriptive maps only), keyed
        # by grain, using the all-journals map's rows. Read the work's dots once.
        custom = {}
        if any_testable and not pool_file:
            vb = os.path.join(VD, "view_b", safe(work) + ".json")
            if os.path.exists(vb):
                dd = json.load(open(vb, encoding="utf-8"))
                dots = dd.get("dots", [])
                sysname = dd.get("system", "stephanus")
                for grain in grains:
                    labels = [r["label"] for r in variants.get(f"{grain}|all", {}).get("rows", [])]
                    c = build_custom(dots, sysname, grain, labels)
                    if c:
                        custom[grain] = c
        entries[safe(work)] = {
            "work": work, "display": display, "author": author, "faceted": faceted,
            "grains": grains, "default_grain": default_grain, "median": med,
            "variants": variants, "custom": custom,
        }
        index.append({"work": work, "display": display, "author": author,
                      "system": by_name.get(work, {}).get("system", ""),
                      "faceted": faceted, "articles": articles, "citations": citations,
                      "never_testable": not any_testable})

    for w in works:
        work = w["work"]
        author = authors.get(work, "Plato")
        # Pindar is excluded from Viewer C: no ode supports a within-work
        # shift-over-time map (line grain is too sparse for every ode — checked on the
        # real corpus). Pindar's temporal signal is between odes, a Works-over-time
        # result. The index carries a note in its place (see view_c.html).
        if author == "Pindar":
            continue
        process(work, author, bool(w.get("faceted")), w.get("citations", 0),
                w.get("distinct_articles", 0), work.replace("_", " "))

    n_never = sum(1 for e in index if e["never_testable"])
    print(f"works: {len(index)}  (never-testable: {n_never})")
    print("variant shapes:", dict(shape_tally))

    if args.check:
        print("--check: nothing written")
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    for key, e in entries.items():
        with open(os.path.join(OUT_DIR, key + ".json"), "w", encoding="utf-8") as f:
            json.dump(e, f, ensure_ascii=False)
    print(f"-> wrote {OUT_INDEX} and {len(entries)} files in {OUT_DIR}/")


if __name__ == "__main__":
    main()
