#!/usr/bin/env python3
"""
temporal_analysis.py — Stage 1 of the temporal passage-attention analysis
(UI-redesign handoff §8). ANALYSIS FIRST: decide whether the SHAPE of attention
to a work's passages shifts over time BEFORE any temporal viz is designed.

Reads the per-work `dots` already in viewer_data/view_b/<work>.json (each dot =
one deduped article-citation to a passage, carrying its year), and for each work
produces — printed to stdout AND written to temporal_<work>.json (the dataset
Claude Design will mock against):

  * per-passage x 5-year-bin table (distinct-article counts)
  * SHARE-based early-vs-late deltas (volume-invariant; raw counts would just
    track corpus growth — the recurring volume caveat)
  * a "did the shape change" number: Spearman rank-corr AND total-variation
    distance between the early and late passage distributions. Flat = a FINDING
    (stability), not a null result.
  * a sparsity read: how thin per-(passage,bin) cells get, and how many passages
    are dense enough to draw a confident trajectory.
  * an optional --focus: a page's per-bin trajectory (e.g. Meno 98, the Gettier
    locus; NE 1097, the ergon argument).

Shares are ARTICLE-INCIDENCE shares: within a period, share(p) = (# distinct
articles citing passage p) / (sum over passages of that), a proper distribution
that dedups span fan-out within a passage. Distinct articles (not raw citations)
are used throughout so "3 citations from one article" never reads as a trend.

Stdlib only. Run locally:

    python3 temporal_analysis.py viewer_data Meno Theaetetus Nicomachean_Ethics Gorgias
    python3 temporal_analysis.py viewer_data Meno --focus 97,98 --bin 5
"""
import sys, os, json, argparse, random
from collections import defaultdict, Counter

def safe_name(work):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in work)

def passage_label(system, book, page, section):
    if system in ("homer", "pindar"):
        return "%s.%s" % (book, page)        # book.line
    if system == "nt":
        return "%s:%s" % (book, page)        # chapter:verse
    return "%s%s" % (page, section)          # Greek page+section/column

# ---- small stats (no numpy) ----
def _ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r

def _pearson(a, b):
    n = len(a)
    if n < 2:
        return float("nan")
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    return cov / ((va * vb) ** 0.5) if va > 0 and vb > 0 else float("nan")

def spearman(a, b):
    return _pearson(_ranks(a), _ranks(b))

def tvd(dist_a, dist_b, keys):
    """Total-variation distance between two share-dicts over the key union."""
    return 0.5 * sum(abs(dist_a.get(k, 0.0) - dist_b.get(k, 0.0)) for k in keys)

def shape_metrics(early_p, late_p):
    """(spearman_rho, tvd) between two period passage->{iid} maps, on
    article-incidence shares."""
    e = {pl: len(s) for pl, s in early_p.items()}
    l = {pl: len(s) for pl, s in late_p.items()}
    et = sum(e.values()) or 1
    lt = sum(l.values()) or 1
    es = {pl: n / et for pl, n in e.items()}
    ls = {pl: n / lt for pl, n in l.items()}
    allp = sorted(set(es) | set(ls))
    return (spearman([es.get(p, 0.0) for p in allp], [ls.get(p, 0.0) for p in allp]),
            tvd(es, ls, allp))

def bh_qvalues(p_by_key):
    """Benjamini-Hochberg FDR q-values from per-passage p-values. Controls the
    expected FALSE-DISCOVERY rate across all passages tested, so the flagged set
    isn't padded with the ~5%xN singletons a per-passage p<0.05 admits by chance."""
    items = sorted(p_by_key.items(), key=lambda kv: kv[1])
    m = len(items)
    q = {}
    prev = 1.0
    for i in range(m - 1, -1, -1):     # walk up from the largest p, enforce monotone
        k, p = items[i]
        prev = min(prev, p * m / (i + 1))
        q[k] = prev
    return q

def _mean_sd(xs):
    n = len(xs)
    if n == 0:
        return (float("nan"), float("nan"))
    m = sum(xs) / n
    sd = (sum((x - m) ** 2 for x in xs) / n) ** 0.5
    return (m, sd)

def permutation_null(recs, split, n_perm, obs_delta, seed=0):
    """Break the passage<->period association: keep each passage's total incidence
    and the early/late sizes fixed, reshuffle which citations are 'late', recompute
    n_perm times. Returns (null_rho[], null_tvd[], p_delta) where p_delta[passage]
    is the two-sided permutation p-value that the passage's observed early->late
    share change is beyond sampling noise. recs = [(passage, iid, year), ...];
    obs_delta = {passage: observed late_share - early_share}."""
    rng = random.Random(seed)
    pis = [(pl, iid) for (pl, iid, _) in recs]
    n_late = sum(1 for (_, _, y) in recs if y >= split)
    labels = [1] * n_late + [0] * (len(recs) - n_late)
    rhos, tvds = [], []
    exceed = {p: 0 for p in obs_delta}
    for _ in range(n_perm):
        rng.shuffle(labels)
        ep, lp = defaultdict(set), defaultdict(set)
        for (pl, iid), lab in zip(pis, labels):
            (lp if lab else ep)[pl].add(iid)
        e = {pl: len(s) for pl, s in ep.items()}
        l = {pl: len(s) for pl, s in lp.items()}
        et = sum(e.values()) or 1
        lt = sum(l.values()) or 1
        es = {pl: n / et for pl, n in e.items()}
        ls = {pl: n / lt for pl, n in l.items()}
        allp = sorted(set(es) | set(ls))
        rhos.append(spearman([es.get(p, 0.0) for p in allp], [ls.get(p, 0.0) for p in allp]))
        tvds.append(tvd(es, ls, allp))
        for p, od in obs_delta.items():
            if abs(ls.get(p, 0.0) - es.get(p, 0.0)) >= abs(od):
                exceed[p] += 1
    p_delta = {p: (exceed[p] + 1) / (n_perm + 1) for p in obs_delta}
    return rhos, tvds, p_delta


def multibin_structure(recs, n_periods=3, n_perm=200, seed=1):
    """A monotonicity-AGNOSTIC temporal-structure test (audit B4). The two-bin
    early/late split collapses each trajectory to two points, so a unit that rose
    THEN fell reads as 'stable'. Here we cut the citations into `n_periods` equal
    -article periods (by year) and measure how much the passage-share distribution
    moves ACROSS periods = mean pairwise total-variation distance between the period
    distributions. Compared to a permutation null (shuffle which period each
    citation lands in), this detects any-shape temporal structure, not just a
    net early->late drift.

    Crucially the whole-work dispersion DECOMPOSES by passage: it is exactly the sum
    over passages of each passage's mean pairwise |share_i - share_j|/2. So the same
    loop yields (a) the whole-work z AND (b) each passage's dispersion CONTRIBUTION
    plus a permutation p-value for it — which answers 'is the non-monotonic structure
    carried by a few HERO passages or is it DIFFUSE?' (the two-bin mover test can't,
    being blind to rose-then-fell shapes). Returns
    (obs_disp, null_mean, null_sd, z, periods, passage_disp, passage_p) where
    passage_disp[pl] is the per-passage contribution (they sum to obs_disp) and
    passage_p[pl] its two-sided permutation p-value. recs = [(unit, iid, y)]."""
    if len(recs) < n_periods * 5:
        return (float("nan"), float("nan"), float("nan"), float("nan"), [], {}, {})
    ys = sorted(y for (_, _, y) in recs)
    # equal-count period cut points (year thresholds)
    cuts = [ys[min(len(ys) - 1, (i * len(ys)) // n_periods)] for i in range(1, n_periods)]
    pairs = [(i, j) for i in range(n_periods) for j in range(i + 1, n_periods)]

    def period_of(y):
        p = 0
        for c in cuts:
            if y >= c:
                p += 1
        return p

    def passage_dispersion(labels):
        # labels: period index per rec (aligned to recs order). Returns
        # {passage: its contribution to the mean pairwise TVD}. Summing the dict
        # reproduces the whole-work dispersion.
        per = [defaultdict(set) for _ in range(n_periods)]
        for (pl, iid, _), lab in zip(recs, labels):
            per[lab][pl].add(iid)
        tots = [sum(len(s) for s in pd.values()) or 1 for pd in per]
        shares = [{pl: len(s) / tots[i] for pl, s in per[i].items()} for i in range(n_periods)]
        keys = set()
        for s in shares:
            keys |= set(s)
        out = {}
        for pl in keys:
            out[pl] = sum(0.5 * abs(shares[i].get(pl, 0.0) - shares[j].get(pl, 0.0))
                          for i, j in pairs) / len(pairs)
        return out

    obs_labels = [period_of(y) for (_, _, y) in recs]
    obs_disp = passage_dispersion(obs_labels)
    obs = sum(obs_disp.values())
    rng = random.Random(seed)
    perm_labels = list(obs_labels)
    nulls = []
    exceed = {pl: 0 for pl in obs_disp}
    for _ in range(n_perm):
        rng.shuffle(perm_labels)
        d = passage_dispersion(perm_labels)
        nulls.append(sum(d.values()))
        for pl, od in obs_disp.items():
            if d.get(pl, 0.0) >= od:
                exceed[pl] += 1
    m, sd = _mean_sd(nulls)
    z = (obs - m) / sd if sd > 0 else float("nan")
    passage_p = {pl: (exceed[pl] + 1) / (n_perm + 1) for pl in obs_disp}
    period_bounds = []
    edges = [ys[0]] + cuts + [ys[-1]]
    for i in range(n_periods):
        period_bounds.append([edges[i], edges[i + 1]])
    return (obs, m, sd, z, period_bounds, obs_disp, passage_p)


def analyse(viewer_dir, work, bin_size, focus_pages, split_override=0, n_perm=200,
            journals=None, journals_label="", min_articles=15, grain="passage",
            dots_override=None, system_override=None, min_early=8, min_stable_articles=100,
            n_periods=3, extra_mover_flags=None, write=True):
    # dots_override lets a caller (the --pool corpus mode) feed a pre-built,
    # cross-file dot list — used for a corpus whose nominal "works" are editorial
    # collections of independent texts (Pindar's ode-books), where the comparable
    # text is the ODE, not the ode-group. The ode label is stashed in each dot's
    # `book` field upstream, so grain="book" makes each ode the unit.
    if dots_override is not None:
        system = system_override or "pooled"
        dots = dots_override
        n_all = len(dots)
    else:
        path = os.path.join(viewer_dir, "view_b", safe_name(work) + ".json")
        if not os.path.exists(path):
            print(f"  !! {path} not found — skipping {work}")
            return None
        d = json.load(open(path, encoding="utf-8"))
        system = d.get("system", "stephanus")
        dots = d.get("dots", [])
        n_all = len(dots)
    if journals:
        dots = [dot for dot in dots if dot.get("journal") in journals]
        if not dots:
            print(f"  !! {work}: no citations from journal-set {journals_label!r} "
                  f"(of {n_all}) — skipping")
            return None

    # article set per (passage, bin); year histogram
    pb_iids = defaultdict(set)          # (passage, bin) -> {iid}
    passage_book = {}                   # passage -> book (for labels)
    year_hist = Counter()
    def ybin(y):
        return (y // bin_size) * bin_size

    # the analysis UNIT: a passage (page+section / book.line / chapter:verse) or,
    # with --grain book, the book facet itself (Republic X, Metaphysics Lambda...).
    # Book grain pools passages into books: for a faceted work whose reshuffle is
    # real-but-diffuse at passage grain, the drift may localise legibly by book.
    def unit_key(dot):
        if grain == "book":
            return dot.get("book", "")     # "" for a non-faceted work -> skipped
        return passage_label(system, dot.get("book", ""), dot.get("page"),
                             dot.get("section", ""))

    kept = skipped_nobook = 0
    for dot in dots:
        y = dot.get("year", "")
        if not (isinstance(y, str) and y.isdigit() and len(y) == 4):
            continue
        pl = unit_key(dot)
        if grain == "book" and not pl:
            skipped_nobook += 1
            continue
        yi = int(y)
        iid = dot.get("iid", "")
        pb_iids[(pl, ybin(yi))].add(iid)
        passage_book.setdefault(pl, pl if grain == "book" else dot.get("book", ""))
        year_hist[yi] += 1
        kept += 1

    if kept == 0:
        extra = " (no book facet — not a faceted work)" if grain == "book" else ""
        print(f"  !! {work}: no dated citations at grain={grain}{extra}")
        return None

    years = sorted(year_hist)
    ymin, ymax = years[0], years[-1]
    bins = sorted(set(b for (_, b) in pb_iids))

    # per-passage per-bin distinct-article counts + totals
    passages = defaultdict(dict)        # passage -> {bin: n_articles}
    passage_total = Counter()           # passage -> distinct articles overall
    passage_all_iids = defaultdict(set)
    for (pl, b), iids in pb_iids.items():
        passages[pl][b] = len(iids)
        passage_all_iids[pl] |= iids
    for pl, iids in passage_all_iids.items():
        passage_total[pl] = len(iids)

    # ---- early vs late split. Default = MEDIAN citation year (balances sample
    #      size; any resolution bias roughly cancels under a share comparison).
    #      Override with --split-year to test a dated hypothesis (e.g. Gettier
    #      1963 on Meno 98). ----
    if split_override:
        split = split_override
    else:
        flat_years = []
        for y, n in year_hist.items():
            flat_years += [y] * n
        flat_years.sort()
        split = flat_years[len(flat_years) // 2]

    # split each dot exactly by its year; also collect recs for the permutation null
    early_p = defaultdict(set); late_p = defaultdict(set)
    recs = []
    for dot in dots:
        y = dot.get("year", "")
        if not (isinstance(y, str) and y.isdigit() and len(y) == 4):
            continue
        pl = unit_key(dot)
        if grain == "book" and not pl:
            continue
        yi = int(y)
        iid = dot.get("iid", "")
        (early_p if yi < split else late_p)[pl].add(iid)
        recs.append((pl, iid, yi))
    early_art = {pl: len(s) for pl, s in early_p.items()}
    late_art = {pl: len(s) for pl, s in late_p.items()}
    e_tot = sum(early_art.values()) or 1
    l_tot = sum(late_art.values()) or 1
    e_share = {pl: n / e_tot for pl, n in early_art.items()}
    l_share = {pl: n / l_tot for pl, n in late_art.items()}
    allp = sorted(set(e_share) | set(l_share))
    rho, tv = shape_metrics(early_p, late_p)

    # The WHOLE-WORK shape test (rho/tvd) pools every passage, so it stays robust
    # even in sparse subsets. But the PER-PASSAGE significance test misbehaves on
    # tiny-count passages: an exact permutation hands a 5->0 passage a small p, and
    # BH-FDR is anti-conservative on such discrete data, so dozens of coin-flips
    # get waved through. Gate the per-passage test to passages with enough total
    # articles to carry a trajectory, then FDR over THAT set only.
    tested = [pl for pl in allp if passage_total.get(pl, 0) >= min_articles]
    obs_delta = {pl: l_share.get(pl, 0.0) - e_share.get(pl, 0.0) for pl in tested}

    # ---- permutation null: is the observed reshuffle beyond the sampling floor?
    #      (whole-work rho/tvd, on ALL passages) and which INDIVIDUAL (gated)
    #      passages move beyond it (p) ----
    null_rho, null_tvd, p_delta = permutation_null(recs, split, n_perm, obs_delta)
    q_delta = bh_qvalues(p_delta)      # FDR across the gated (testable) passages
    nr_m, nr_sd = _mean_sd(null_rho)
    nt_m, nt_sd = _mean_sd(null_tvd)
    rho_z = (rho - nr_m) / nr_sd if nr_sd > 0 else float("nan")
    tvd_z = (tv - nt_m) / nt_sd if nt_sd > 0 else float("nan")
    tvd_pctile = 100.0 * sum(1 for t in null_tvd if t <= tv) / len(null_tvd)

    # top movers by |delta share|, each flagged with its permutation p-value so a
    # big delta from a sparse passage isn't mistaken for a story (esp. in works
    # that are stable in aggregate but have real individual movers).
    # floor_fail_early (audit B1): the min_articles floor gates on TOTAL articles,
    # but a mover can pass it on a fat LATE bin while its EARLY bin is too thin to
    # anchor a direction (the Paul/pre-1977 regime). Such a mover must NOT render as
    # a bright FDR arrow — Design drops it to the muted layer / a footnote.
    # survives_within_shelf (audit B2): supplied by the pool caller — whether the
    # unit still moves once its cluster's block-level recency is partialled out.
    xf = extra_mover_flags or {}
    def _mk(pl):
        m = {"passage": pl, "book": passage_book.get(pl, ""),
             "early_share": round(e_share.get(pl, 0.0), 4),
             "late_share": round(l_share.get(pl, 0.0), 4),
             "delta": round(l_share.get(pl, 0.0) - e_share.get(pl, 0.0), 4),
             "early_articles": early_art.get(pl, 0), "late_articles": late_art.get(pl, 0),
             "p_value": round(p_delta.get(pl, 1.0), 3),
             "q_value": round(q_delta.get(pl, 1.0), 3),
             "significant": p_delta.get(pl, 1.0) < 0.05,        # raw, per-passage
             "significant_fdr": q_delta.get(pl, 1.0) < 0.10,    # survives FDR 10%
             "floor_fail_early": early_art.get(pl, 0) < min_early}
        if pl in xf:
            m["survives_within_shelf"] = bool(xf[pl].get("significant_fdr"))
            m["within_shelf_q"] = xf[pl].get("q_value")
        return m
    movers = sorted((_mk(pl) for pl in tested), key=lambda r: -abs(r["delta"]))
    n_sig_movers = sum(1 for m in movers if m["significant"])
    n_fdr_movers = sum(1 for m in movers if m["significant_fdr"])
    n_fdr_solid = sum(1 for m in movers if m["significant_fdr"] and not m["floor_fail_early"])
    n_expected_chance = round(0.05 * len(tested), 1)   # false positives p<0.05 buys

    # ---- B3: full per-unit early/late table (absolute anchor, not just top movers).
    #      A share can fall because OTHERS rose while this unit's own attention is
    #      flat/growing; the difference-map needs the raw counts, for EVERY unit. ----
    units = sorted(
        ({"passage": pl, "book": passage_book.get(pl, ""),
          "early_articles": early_art.get(pl, 0), "late_articles": late_art.get(pl, 0),
          "early_share": round(e_share.get(pl, 0.0), 4),
          "late_share": round(l_share.get(pl, 0.0), 4),
          "delta": round(l_share.get(pl, 0.0) - e_share.get(pl, 0.0), 4),
          "total_articles": passage_total.get(pl, 0)}
         for pl in allp), key=lambda r: -r["total_articles"])

    # ---- B4: monotonicity-agnostic structure test across n_periods (>=3) bins ----
    mb_obs, mb_m, mb_sd, mb_z, mb_periods, mb_disp, mb_p = multibin_structure(
        recs, n_periods, n_perm)

    # ---- HERO-vs-DIFFUSE for the non-monotonic structure (design Q for Viewer C):
    #      decompose the >=3-period dispersion by passage, FDR the per-passage
    #      permutation p over the GATED passages, and measure CONCENTRATION (does a
    #      little set of passages carry most of the structure, or is it spread thin?).
    #      This is the multi-period analogue of top_movers, and unlike the two-bin
    #      mover test it CAN see rose-then-fell passages. ----
    mb_movers, mb_concentration = [], {}
    if mb_disp:
        mb_q = bh_qvalues({pl: mb_p.get(pl, 1.0) for pl in tested}) if tested else {}
        mb_movers = sorted(
            ({"passage": pl, "book": passage_book.get(pl, ""),
              "dispersion": round(mb_disp.get(pl, 0.0), 5),
              "total_articles": passage_total.get(pl, 0),
              "p_value": round(mb_p.get(pl, 1.0), 3),
              "q_value": round(mb_q.get(pl, 1.0), 3),
              "significant_fdr": mb_q.get(pl, 1.0) < 0.10}
             for pl in tested), key=lambda r: -r["dispersion"])
        # concentration over the TESTED (drawable) passages
        tested_disp = sorted((mb_disp.get(pl, 0.0) for pl in tested), reverse=True)
        tdt = sum(tested_disp) or 1.0
        def _topk(k):
            return round(sum(tested_disp[:k]) / tdt, 3)
        cum, n50 = 0.0, 0
        for v in tested_disp:
            cum += v; n50 += 1
            if cum >= 0.5 * tdt:
                break
        mb_concentration = {
            "n_structure_movers_fdr": sum(1 for m in mb_movers if m["significant_fdr"]),
            "n_tested": len(tested),
            "tested_dispersion_total": round(tdt, 4),
            "share_of_whole": round(tdt / (mb_obs or 1.0), 3),
            "top1_share": _topk(1), "top3_share": _topk(3),
            "top5_share": _topk(5), "top10_share": _topk(10),
            "n_passages_to_50pct": n50}

    # ---- verdict category (two-bin), + B4/B5 qualifiers ----
    n_articles = len(set().union(*passage_all_iids.values())) if passage_all_iids else 0
    two_bin_verdict = ("REAL" if tvd_z >= 3 else "marginal" if tvd_z >= 1.5 else "stable")
    # B4: a two-bin split collapses each trajectory to two points, so it is blind to
    # non-monotonic (rose-then-fell) structure. two_bin_flat_only = a 'stable' verdict
    # that nonetheless has real >=3-period structure (must NOT get a stability badge).
    # two_bin_understates = any not-REAL verdict (stable OR marginal) whose >=3-period
    # structure is strong — the 2-bin split under-reads a non-monotonic reshuffle
    # (Timaeus, Laws, De Anima). Both require a real mb_z (not NaN).
    mb_ok = (mb_z == mb_z)
    two_bin_flat_only = (two_bin_verdict == "stable" and mb_ok and mb_z >= 3)
    two_bin_understates = (two_bin_verdict != "REAL" and mb_ok and mb_z >= 3)
    # B5: a 'stable' verdict is only informative if the test COULD have moved — i.e.
    # the work has enough distinct articles. Below the floor it is too-sparse-to-tell,
    # not a positive stability finding.
    stability_powered = (two_bin_verdict == "stable" and n_articles >= min_stable_articles
                         and len(tested) >= 3)
    near_threshold = (abs(tvd_z - 1.5) <= 1.0 or abs(tvd_z - 3.0) <= 1.0)  # B6 hint

    # ---- sparsity ----
    cell_hist = Counter()
    for (_, _), iids in pb_iids.items():
        n = len(iids)
        cell_hist["1" if n == 1 else "2" if n == 2 else "3-4" if n <= 4 else "5+"] += 1
    drawable = {"ge5": sum(1 for v in passage_total.values() if v >= 5),
                "ge10": sum(1 for v in passage_total.values() if v >= 10),
                "ge20": sum(1 for v in passage_total.values() if v >= 20)}

    # ---- focus pages (targeted trajectory) ----
    focus = {}
    for pg in focus_pages:
        traj = Counter()
        for (pl, b), iids in pb_iids.items():
            # match any section on this page: label starts with the page number
            if pl.startswith(str(pg)) and (len(pl) == len(str(pg)) or not pl[len(str(pg))].isdigit()):
                traj[b] += len(iids)
        if traj:
            focus[str(pg)] = {str(b): traj[b] for b in sorted(traj)}

    # bin totals (distinct-article-incidence, work-wide)
    bin_totals = {}
    for b in bins:
        s = set()
        # count article incidences per bin = sum over passages of distinct arts
        tot = sum(len(iids) for (pl, bb), iids in pb_iids.items() if bb == b)
        bin_totals[str(b)] = tot

    out = {
        "work": work, "system": system, "bin_years": bin_size, "grain": grain,
        "journals_filter": journals_label or "all",
        "movers_min_articles": min_articles, "mover_min_early": min_early,
        "n_passages_tested": len(tested),
        "n_significant_movers": n_sig_movers,
        "n_significant_movers_fdr": n_fdr_movers,
        "n_fdr_movers_solid": n_fdr_solid,   # FDR-solid AND early bin adequately powered
        "n_movers_expected_by_chance": n_expected_chance,
        "n_citations": kept, "n_articles": n_articles,
        "n_passages": len(passage_total), "year_range": [ymin, ymax],
        "split_year": split,
        "verdict": two_bin_verdict,
        "stability_powered": stability_powered,      # B5: informative null vs too-sparse
        "min_stable_articles": min_stable_articles,
        "two_bin_flat_only": two_bin_flat_only,      # B4: non-monotonic under a 'stable'
        "two_bin_understates": two_bin_understates,  # B4: 2-bin under-reads real structure
        "near_threshold": near_threshold,            # B6: re-run at higher --perm
        "shape_change": {"spearman_rho": round(rho, 4), "tvd": round(tv, 4),
                         "n_passages_compared": len(allp),
                         "early_article_incidences": e_tot, "late_article_incidences": l_tot,
                         "null": {"n_perm": n_perm,
                                  "rho_mean": round(nr_m, 4), "rho_sd": round(nr_sd, 4),
                                  "tvd_mean": round(nt_m, 4), "tvd_sd": round(nt_sd, 4),
                                  "rho_z": round(rho_z, 2), "tvd_z": round(tvd_z, 2),
                                  "tvd_percentile": round(tvd_pctile, 1)}},
        "multibin_structure": {"n_periods": n_periods,
                               "periods": mb_periods,
                               "dispersion": None if mb_obs != mb_obs else round(mb_obs, 4),
                               "null_mean": None if mb_m != mb_m else round(mb_m, 4),
                               "null_sd": None if mb_sd != mb_sd else round(mb_sd, 4),
                               "z": None if mb_z != mb_z else round(mb_z, 2),
                               "concentration": mb_concentration},
        "multibin_movers": mb_movers[:25],   # passages carrying the >=3-period structure
        "sparsity": {"cell_article_hist": dict(cell_hist), "drawable_passages": drawable},
        "bin_totals": bin_totals,
        "top_passages": [{"passage": pl, "book": passage_book.get(pl, ""),
                          "total_articles": passage_total[pl],
                          "by_bin": {str(b): passages[pl][b] for b in sorted(passages[pl])}}
                         for pl, _ in passage_total.most_common(25)],
        "top_movers": movers[:25],
        "units": units,          # B3: full per-unit early/late raw counts + shares
        "focus": focus,
    }
    if write:
        suffix = ("_" + safe_name(journals_label)) if journals else ""
        suffix += "_book" if grain == "book" else ""
        outfile = f"temporal_{safe_name(work)}{suffix}.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        out["_outfile"] = outfile

    # ---- printed summary ----
    jlabel = f"  [journals: {journals_label}, {kept:,}/{n_all:,} cites]" if journals else ""
    glabel = "  [grain: BOOK]" if grain == "book" else ""
    unit = "books" if grain == "book" else "passages"
    print(f"\n==================  {work}  ({system}){jlabel}{glabel}  ==================")
    print(f"  citations {kept:,} · distinct articles {out['n_articles']:,} · "
          f"{unit} {len(passage_total):,} · years {ymin}-{ymax}")
    print(f"  SHAPE CHANGE (early <{split} vs late >={split}):")
    print(f"    Spearman rho = {rho:.3f}   vs null {nr_m:.3f}+-{nr_sd:.3f}  (z={rho_z:+.1f})")
    print(f"    total-var dist = {tv:.3f}   vs null {nt_m:.3f}+-{nt_sd:.3f}  (z={tvd_z:+.1f}, "
          f"{tvd_pctile:.0f}th pctile of null)")
    if two_bin_verdict == "REAL":
        verdict = "REAL reshuffle (well beyond sampling noise)"
    elif two_bin_verdict == "marginal":
        verdict = "marginal — near the noise floor"
    elif stability_powered:
        verdict = "STABLE (well-powered null — a real stability finding)"
    else:
        verdict = ("too-sparse-to-tell (stable at 2-bin, but under-powered: "
                   f"n_articles {n_articles} < {min_stable_articles})")
    print(f"    -> {verdict}")
    if near_threshold:
        print(f"    !! near a verdict threshold (tvd_z {tvd_z:+.1f}) — re-run at --perm 2000 (B6)")
    if mb_z == mb_z:   # not NaN
        if two_bin_flat_only:
            note = "  <-- NON-MONOTONIC: real >=3-period structure hidden under a STABLE 2-bin verdict"
        elif two_bin_understates:
            note = "  <-- 2-bin UNDER-READS: >=3-period structure exceeds the 2-bin signal"
        else:
            note = ""
        print(f"    {n_periods}-period structure: dispersion {mb_obs:.3f} vs null "
              f"{mb_m:.3f}+-{mb_sd:.3f} (z={mb_z:+.1f}){note}")
        if mb_concentration:
            c = mb_concentration
            nfdr = c["n_structure_movers_fdr"]
            # hero vs diffuse: FDR survivors + top-k concentration of the dispersion
            if nfdr >= 1 and c["top5_share"] >= 0.40:
                shape = "HERO-driven (a few passages carry it)"
            elif nfdr == 0 and c["n_passages_to_50pct"] >= max(8, 0.15 * c["n_tested"]):
                shape = "DIFFUSE (spread across many passages)"
            elif nfdr >= 1:
                shape = "BOTH (hero passages + a diffuse tail)"
            else:
                shape = "weak/borderline"
            print(f"    STRUCTURE SHAPE: {nfdr} passage(s) survive multi-period FDR; "
                  f"top-5 carry {100*c['top5_share']:.0f}% of dispersion, "
                  f"{c['n_passages_to_50pct']} passages reach 50% (of {c['n_tested']} tested) "
                  f"-> {shape}")
            for m in mb_movers[:6]:
                star = "**" if m["significant_fdr"] else "  "
                bybin = passages.get(m["passage"], {})
                traj = " ".join(f"{b}:{bybin[b]}" for b in sorted(bybin)) if bybin else ""
                print(f"     {star}{m['passage']:>7}  disp {m['dispersion']:.4f} "
                      f"({m['total_articles']} arts; p={m['p_value']:.3f} q={m['q_value']:.3f})  {traj}")
    print(f"    articles compared: early {e_tot:,} / late {l_tot:,}")
    print(f"  SPARSITY: per-(passage,bin) article cells: "
          + " ".join(f"{k}:{cell_hist[k]}" for k in ("1","2","3-4","5+")))
    print(f"    passages dense enough to draw a line: "
          f">=5 arts {drawable['ge5']} · >=10 {drawable['ge10']} · >=20 {drawable['ge20']} "
          f"(of {len(passage_total)})")
    print(f"  INDIVIDUAL MOVERS (only passages with >={min_articles} articles are "
          f"testable: {len(tested)} of {len(allp)}):")
    print(f"    {n_sig_movers} at p<0.05 (~{n_expected_chance:.0f} expected by chance) "
          f"-> {n_fdr_movers} survive FDR 10% ({n_fdr_solid} also early-powered). "
          f"** = FDR-solid; * = raw p<0.05; †=early bin under floor ({min_early}); "
          f"§=survives within-shelf.")
    for m in movers[:10]:
        arrow = "up  " if m["delta"] > 0 else "down"
        star = "**" if m["significant_fdr"] else (" *" if m["significant"] else "  ")
        early_flag = "†" if m.get("floor_fail_early") else " "
        shelf_flag = ("§" if m.get("survives_within_shelf") else "·") if "survives_within_shelf" in m else " "
        print(f"   {star}{early_flag}{shelf_flag}{m['passage']:>7}  {arrow} "
              f"{m['early_share']:.3f} -> {m['late_share']:.3f} "
              f"(d {m['delta']:+.3f}; {m['early_articles']}->{m['late_articles']} arts; "
              f"p={m['p_value']:.3f} q={m['q_value']:.3f})")
    if focus:
        print(f"  FOCUS trajectories (distinct articles per {bin_size}-yr bin):")
        for pg, traj in focus.items():
            line = "  ".join(f"{b}:{n}" for b, n in traj.items())
            print(f"    page {pg}:  {line}")
    if write:
        print(f"  -> wrote {out.get('_outfile')}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("viewer_dir")
    ap.add_argument("works", nargs="+")
    ap.add_argument("--bin", type=int, default=5, help="year bin size (default 5)")
    ap.add_argument("--focus", default="", help="comma-sep page numbers to trace, "
                    "e.g. 97,98 for Meno/Gettier or 1097 for NE ergon")
    ap.add_argument("--split-year", type=int, default=0,
                    help="override the median early/late split (e.g. 1965 to test "
                         "a pre/post-Gettier hypothesis); 0 = median")
    ap.add_argument("--perm", type=int, default=200,
                    help="permutation-null iterations for the shape-change test")
    ap.add_argument("--min-articles", type=int, default=15,
                    help="only test passages with >= this many total articles for "
                         "individual significance (below it the permutation p-value "
                         "+ FDR is unreliable on tiny counts). Default 15.")
    ap.add_argument("--min-early", type=int, default=8,
                    help="a mover whose EARLY-bin distinct-article count is below this "
                         "is flagged floor_fail_early: FDR-solid but its direction is "
                         "under-powered on the early side (the Paul/pre-1977 regime); "
                         "not to be rendered as a bright arrow. Default 8. (audit B1)")
    ap.add_argument("--min-stable-articles", type=int, default=100,
                    help="a 'stable' 2-bin verdict counts as an informative null only "
                         "with >= this many distinct articles; below it the verdict is "
                         "too-sparse-to-tell, not stable. Default 100. (audit B5)")
    ap.add_argument("--periods", type=int, default=3,
                    help=">= this many equal-count periods for the monotonicity-"
                         "agnostic structure test that catches rose-then-fell "
                         "trajectories a 2-bin split reads as flat. Default 3. (B4)")
    ap.add_argument("--grain", choices=["passage", "book"], default="passage",
                    help="analysis unit: 'passage' (page+section etc.) or 'book' "
                         "(the book facet — only meaningful for faceted works: "
                         "Republic, Laws, Metaphysics, Nicomachean/Eudemian Ethics).")
    ap.add_argument("--journals", default="",
                    help="restrict to a journal-set to separate a real reading shift "
                         "from a corpus-composition shift: a group name from "
                         "journal_groups.json (e.g. philosophy, classics) or a "
                         "comma-list of journal titles. Empty = all journals.")
    ap.add_argument("--pool", default="", metavar="LABEL",
                    help="POOL the positional works into ONE corpus named LABEL and "
                         "make each work's BOOK-facet unit a distinct text across the "
                         "pool (label 'Work book'). For a corpus whose nominal works "
                         "are editorial COLLECTIONS of independent texts — Pindar's "
                         "ode-books — so the comparable text is the ode, not the "
                         "ode-group, and shares use one corpus-wide denominator. "
                         "Forces --grain book. e.g. --pool Pindar Olympian Pythian "
                         "Nemean Isthmian")
    args = ap.parse_args()
    focus_pages = [p.strip() for p in args.focus.split(",") if p.strip()]

    # resolve the journal-set filter (group name -> members, else literal list)
    jfilter, jlabel = None, ""
    if args.journals.strip():
        jlabel = args.journals.strip()
        groups = {}
        try:
            gj = json.load(open("journal_groups.json"))["groups"]
            groups = {k.lower(): (v if isinstance(v, list) else v.get("journals", []))
                      for k, v in gj.items()}
        except Exception as e:
            print(f"  (could not read journal_groups.json: {e})")
        key = jlabel.lower()
        jfilter = set(groups[key]) if key in groups else {
            j.strip() for j in args.journals.split(",") if j.strip()}
    # ---- pooled-corpus mode: fold the positional works into one corpus whose UNIT
    #      is the book-facet of each source work (Pindar: the ode), so the odes are
    #      compared against a single corpus-wide denominator rather than each
    #      arbitrary ode-book's internal one. ----
    if args.pool.strip():
        # canonical Pindar ode-book abbreviations; fall back to the work name.
        ABBREV = {"Olympian": "O.", "Pythian": "P.", "Nemean": "N.", "Isthmian": "I."}
        pooled, systems, n_src = [], set(), 0
        within_shelf = {}   # pooled-ode-label -> per-shelf mover record (audit B2)
        for work in args.works:
            path = os.path.join(args.viewer_dir, "view_b", safe_name(work) + ".json")
            if not os.path.exists(path):
                print(f"  !! {path} not found — skipping {work}")
                continue
            d = json.load(open(path, encoding="utf-8"))
            systems.add(d.get("system", "?"))
            ab = ABBREV.get(work, work + " ")
            shelf_dots = d.get("dots", [])
            for dot in shelf_dots:
                nd = dict(dot)
                nd["book"] = f"{ab}{dot.get('book', '')}"   # ode label = the text
                pooled.append(nd)
            n_src += 1
            # WITHIN-SHELF CONTROL (B2): re-run this shelf alone at BOOK(=ode) grain.
            # Because shares are taken over the shelf's own denominator, a uniform
            # shelf-level recency shift (the block effect) cancels — so an ode that
            # is still an FDR mover HERE moves relative to its shelf-mates, i.e. it
            # is a genuine ODE-level shift, not carried by the block. write=False so
            # this diagnostic sub-run doesn't spew per-shelf files during a pool run.
            shelf_out = analyse(args.viewer_dir, work, args.bin, [], args.split_year,
                                args.perm, journals=jfilter, journals_label=jlabel,
                                min_articles=args.min_articles, grain="book",
                                dots_override=[dict(x) for x in shelf_dots],
                                system_override=d.get("system", "?"),
                                min_early=args.min_early,
                                min_stable_articles=args.min_stable_articles,
                                n_periods=args.periods, write=False)
            if shelf_out:
                for m in shelf_out.get("top_movers", []):
                    within_shelf[f"{ab}{m['passage']}"] = m
        if not pooled:
            print(f"  !! pool {args.pool!r}: no dots found across {args.works}")
            return
        print(f"\n  [pool {args.pool!r}: {n_src} source works, {len(pooled):,} dots, "
              f"system(s) {sorted(systems)} — unit = ode/book across the pool; "
              f"within-shelf control on {len(within_shelf)} odes]")
        analyse(args.viewer_dir, args.pool, args.bin, [], args.split_year, args.perm,
                journals=jfilter, journals_label=jlabel, min_articles=args.min_articles,
                grain="book", dots_override=pooled,
                system_override=(systems.pop() if len(systems) == 1 else "pooled"),
                min_early=args.min_early, min_stable_articles=args.min_stable_articles,
                n_periods=args.periods, extra_mover_flags=within_shelf)
        return

    # sensible auto-focus for the hero works if none given
    AUTO = {"Meno": ["97", "98"], "Theaetetus": ["201", "202"],
            "Nicomachean_Ethics": ["1097"], "Metaphysics": ["1029"],
            "De_Anima": ["429"], "Timaeus": ["27", "28"]}
    for work in args.works:
        fp = focus_pages or AUTO.get(work, [])
        analyse(args.viewer_dir, work, args.bin, fp, args.split_year, args.perm,
                journals=jfilter, journals_label=jlabel, min_articles=args.min_articles,
                grain=args.grain, min_early=args.min_early,
                min_stable_articles=args.min_stable_articles, n_periods=args.periods)

if __name__ == "__main__":
    main()
