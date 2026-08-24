#!/usr/bin/env python3
"""
frontloading_probe.py — diagnose whether the within-work "front-loading" of
citations (texts cited more heavily near their beginning) is, in part, an
EXTRACTION ARTIFACT rather than a real signal of scholarly attention.

The mechanism under test (Aug-24 discussion): an article that walks a source
from beginning to end names the work fully on first contact ("Iliad 1.1",
"Rom 8:1") and then drops the cue for continuations ("later, at 6.146…",
"then 3:4, 2:7"). Our cue-anchored harvest (homer/pindar/nt) catches the
first, cue-bearing reference — usually the EARLIEST position — and misses the
cue-less follow-ons, which are LATER. Survivorship toward cue-bearing thus
becomes survivorship toward early positions => artificial front-loading.

Three tests, exactly as scoped:

  TEST 1  Differential front-loading by corpus.
          Two regimes differ precisely on the variable in question:
            - bare-number harvest + scope-tracking  -> stephanus, bekker
              (cue-less continuations ARE recovered)
            - cue-anchored only                     -> homer, pindar, nt
              (cue-less continuations are DROPPED)
          If the artifact is real, the cue-anchored corpora should be
          markedly MORE front-loaded than the bare-number corpora.

  TEST 2  Named vs scope-inherited position (REQUIRES resolved.tsv).
          Within Plato/Aristotle, split resolved citations by their `method`.
          scope_inherited hits (the recovered continuations) should sit
          systematically LATER in the work than name/abbrev-matched hits.
          Recomputing the front-loading index on "named-only" vs the full set
          estimates the size of the artifact — and since homer/pindar/nt live
          permanently in that named-only world, that gap is our best estimate
          of how much of their front-loading is artifactual.
          The `method` tag survives ONLY in resolved.tsv; it is not preserved
          in the viewer aggregates, so this test is skipped unless --resolved
          points at that file.

  TEST 3  Distinct loci per (article x work) — a cheap corroborating fingerprint.
          If "catch the first, drop the rest" is operating, the cue-anchored
          corpora should pile up at 1 distinct locus per article-work, while
          the scope-tracked corpora show a longer tail.

Front-loading is only the passage axis. TESTS 4-7 probe the axes the tool
actually reports on (time, journal/discipline) and the shape of engagement,
where a systematic cue-dropping bias would do more damage:

  TEST 4  Capture DEPTH by decade x regime. Scope-tracked corpora are a
          control (continuations recovered); a regime x decade interaction
          would signal an era-correlated capture artifact in the temporal floors.

  TEST 5  Right-tail of per-article engagement. A thinner tail for cue-anchored
          corpora would mean the heaviest (deep-reading) engagements are clipped.

  TEST 6  Within-work concentration (normalised entropy). Lower entropy for
          cue-anchored corpora = citations bunched on canonical loci, the
          "keep the anchor, lose the deep cuts" distortion.

  TEST 7  Cue-dropping propensity by discipline & decade (REQUIRES resolved.tsv).
          scope_inherited share is a direct proxy for cue-dropping; measured on
          Plato/Aristotle and read as the analog for the cue-anchored corpora,
          it tells whether TEST 4's cross-discipline depth gap is citing STYLE
          or real attention.

Reads only existing data — nothing is rebuilt:
  viewer_data/view_b/*.json   per-work dots (position + iid + corpus `system`)
  homer_line_counts.json, pindar_line_counts.json, nt_chapter_lengths.json,
  stephanus_ranges.json, bekker_ranges.json   within-work position denominators
  [optional] --resolved PATH  resolved.tsv, only for TESTS 2 and 7

Usage:
    python3 frontloading_probe.py
    python3 frontloading_probe.py --view-b viewer_data/view_b --tables .
    python3 frontloading_probe.py --resolved resolved.tsv     # enables TESTS 2 & 7
"""

import argparse, glob, json, os, statistics, sys, csv, re, collections

CUE_ANCHORED = {"homer", "pindar", "nt"}      # continuations dropped
SCOPE_TRACKED = {"stephanus", "bekker"}       # continuations recovered
CORPUS_ORDER = ["homer", "pindar", "nt", "stephanus", "bekker"]


# --------------------------------------------------------------------------
# reference tables -> within-work position in [0,1]
# --------------------------------------------------------------------------
def _norm(s):
    """Loose key so 'Nicomachean_Ethics', 'Nicomachean Ethics' etc. all match."""
    return str(s).replace("_", " ").strip().lower()


def _to_int(v):
    """First integer in a possibly-messy field ('13', '13a', '', None)."""
    if v is None:
        return None
    m = re.search(r"\d+", str(v))
    return int(m.group()) if m else None


class Positions:
    """Maps one dot -> fractional position p in [0,1] within its work.

    p=0 is the work's first line/page, p=1 its last. Homer/Pindar/NT use
    book.line (cumulative over the length tables); Stephanus/Bekker use the
    page's offset within the dialogue/treatise range, with the a–e (or a/b)
    section adding a sub-page fraction so early- and late-page cites separate.
    Returns None when the work or unit isn't in the tables (caller skips it),
    so a missing denominator never silently distorts the index."""

    def __init__(self, tables_dir):
        d = tables_dir
        self.homer = self._books(os.path.join(d, "homer_line_counts.json"))
        self.pindar = self._books(os.path.join(d, "pindar_line_counts.json"))
        self.nt = self._books(os.path.join(d, "nt_chapter_lengths.json"))
        self.steph = self._ranges(os.path.join(d, "stephanus_ranges.json"),
                                  "dialogues", "stephanus_start", "stephanus_end")
        self.bekker = self._ranges(os.path.join(d, "bekker_ranges.json"),
                                   "treatises", "bekker_start", "bekker_end")

    @staticmethod
    def _books(path):
        """{work_norm: [unit_len, ...]} from a *_line_counts / chapter_lengths file."""
        try:
            books = json.load(open(path))["books"]
        except Exception as e:
            print(f"  (warn) could not load {path}: {e}", file=sys.stderr)
            return {}
        return {_norm(k): v for k, v in books.items()}

    @staticmethod
    def _ranges(path, key, s_field, e_field):
        """{work_norm: (start_page, end_page)} from a ranges file."""
        try:
            rows = json.load(open(path))[key]
        except Exception as e:
            print(f"  (warn) could not load {path}: {e}", file=sys.stderr)
            return {}
        out = {}
        for r in rows:
            s, e = r.get(s_field), r.get(e_field)
            if s is not None and e is not None and e > s:
                out[_norm(r["id"])] = (s, e)
        return out

    # -- per-corpus positioners; each returns p in [0,1] or None --
    def _bookline(self, table, work, book, line):
        lens = table.get(_norm(work))
        if not lens:
            return None
        b, ln = _to_int(book), _to_int(line)
        if b is None or b < 1 or b > len(lens):
            return None
        ln = ln or 1
        before = sum(lens[:b - 1])
        total = sum(lens)
        if total <= 1:
            return None
        # clamp a line past the unit's real end onto the unit
        ln = min(ln, lens[b - 1])
        return min(max((before + ln) / total, 0.0), 1.0)

    def _page(self, table, work, page, section, sec_letters):
        rng = table.get(_norm(work))
        if not rng:
            return None
        p = _to_int(page)
        if p is None:
            return None
        start, end = rng
        span = (end + 1) - start
        if span <= 0:
            return None
        frac = 0.0
        if section:
            c = str(section).strip().lower()[:1]
            if c in sec_letters:
                frac = sec_letters.index(c) / len(sec_letters)
        return min(max(((p + frac) - start) / span, 0.0), 1.0)

    def of(self, corpus, work, dot):
        if corpus == "homer":
            return self._bookline(self.homer, work, dot.get("book"), dot.get("line"))
        if corpus == "pindar":
            return self._bookline(self.pindar, work, dot.get("book"), dot.get("line"))
        if corpus == "nt":
            return self._bookline(self.nt, work, dot.get("book"), dot.get("line"))
        if corpus == "stephanus":
            return self._page(self.steph, work, dot.get("page"), dot.get("section"), "abcde")
        if corpus == "bekker":
            return self._page(self.bekker, work, dot.get("page"), dot.get("section"), "ab")
        return None


# --------------------------------------------------------------------------
# load dots
# --------------------------------------------------------------------------
def load_view_b(view_b_dir):
    """Yield (corpus, work, dots) per work file."""
    files = sorted(glob.glob(os.path.join(view_b_dir, "*.json")))
    for f in files:
        try:
            d = json.load(open(f))
        except Exception as e:
            print(f"  (warn) skip {f}: {e}", file=sys.stderr)
            continue
        yield d.get("system", "?"), d.get("work", os.path.basename(f)), d.get("dots") or []


# --------------------------------------------------------------------------
# helpers for the front-loading index
# --------------------------------------------------------------------------
def fl_index(ps):
    """Front-loading index = share in first quartile minus share in last
    quartile. >0 front-loaded, <0 back-loaded, ~0 flat. Also returns the mean
    position (0.5 == uniform)."""
    n = len(ps)
    if not n:
        return None
    q1 = sum(1 for p in ps if p < 0.25) / n
    q4 = sum(1 for p in ps if p >= 0.75) / n
    return {"n": n, "mean_p": sum(ps) / n, "q1": q1, "q4": q4, "fl": q1 - q4}


def pct(x):
    return f"{100 * x:5.1f}%"


def gini(xs):
    """Gini of a list of non-negative counts. 0 = perfectly even, ->1 = concentrated."""
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return 0.0
    tot = sum(xs)
    if tot == 0:
        return 0.0
    cum = 0
    for i, x in enumerate(xs, 1):
        cum += i * x
    return (2 * cum) / (n * tot) - (n + 1) / n


def norm_entropy(counts):
    """Shannon entropy of a locus-count distribution, normalised by log(#loci)
    so 1.0 = citations spread perfectly evenly over the work's cited loci and
    ->0 = piled on a single locus. Undefined (None) for <2 loci."""
    import math
    vals = [c for c in counts if c > 0]
    n = len(vals)
    if n < 2:
        return None
    tot = sum(vals)
    h = -sum((c / tot) * math.log(c / tot) for c in vals)
    return h / math.log(n)


def _decade(y):
    i = _to_int(y)
    return (i // 10) * 10 if i else None


# --------------------------------------------------------------------------
# TEST 1
# --------------------------------------------------------------------------
def test1(pos, works):
    print("=" * 74)
    print("TEST 1 — Differential front-loading by corpus")
    print("=" * 74)
    print("Cue-anchored corpora DROP cue-less continuations; scope-tracked")
    print("corpora RECOVER them. If front-loading is an extraction artifact,")
    print("the cue-anchored group should be markedly more front-loaded.\n")

    by_corpus = collections.defaultdict(list)      # corpus -> [p, ...] pooled
    per_work_fl = collections.defaultdict(list)     # corpus -> [fl per work]
    positioned = collections.Counter()
    total = collections.Counter()

    for corpus, work, dots in works:
        ps = []
        for dot in dots:
            total[corpus] += 1
            p = pos.of(corpus, work, dot)
            if p is not None:
                ps.append(p)
                positioned[corpus] += 1
        if ps:
            by_corpus[corpus].extend(ps)
            fw = fl_index(ps)
            if fw:
                per_work_fl[corpus].append((work, fw["fl"], fw["n"]))

    hdr = f"{'corpus':10} {'regime':13} {'cites':>8} {'placed':>7} {'mean_p':>7} {'%q1':>7} {'%q4':>7} {'FL(q1-q4)':>10}"
    print(hdr)
    print("-" * len(hdr))
    group_pool = {"cue-anchored": [], "scope-tracked": []}
    for corpus in CORPUS_ORDER:
        ps = by_corpus.get(corpus)
        if not ps:
            continue
        regime = "cue-anchored" if corpus in CUE_ANCHORED else "scope-tracked"
        group_pool[regime].extend(ps)
        s = fl_index(ps)
        cov = positioned[corpus] / total[corpus] if total[corpus] else 0
        print(f"{corpus:10} {regime:13} {total[corpus]:8,} {pct(cov):>7} "
              f"{s['mean_p']:7.3f} {pct(s['q1']):>7} {pct(s['q4']):>7} {s['fl']:+10.3f}")

    print("-" * len(hdr))
    for regime, ps in group_pool.items():
        if ps:
            s = fl_index(ps)
            print(f"{'POOLED':10} {regime:13} {'':8} {'':>7} "
                  f"{s['mean_p']:7.3f} {pct(s['q1']):>7} {pct(s['q4']):>7} {s['fl']:+10.3f}")

    ca = fl_index(group_pool["cue-anchored"]) if group_pool["cue-anchored"] else None
    st = fl_index(group_pool["scope-tracked"]) if group_pool["scope-tracked"] else None
    print()
    if ca and st:
        gap = ca["fl"] - st["fl"]
        print(f"Cue-anchored vs scope-tracked front-loading gap: {gap:+.3f}")
        print("Reading: a large positive gap is consistent with the artifact")
        print("(cue-anchored corpora over-front-loaded because continuations,")
        print("which fall LATER in the text, are dropped). A gap near zero says")
        print("the front-loading is mostly a real signal, not an extraction bias.")
    print()

    # a few most/least front-loaded works, for eyeballing
    print("Per-work FL, most front-loaded (n>=30):")
    flat = [(c, w, fl, n) for c, lst in per_work_fl.items() for (w, fl, n) in lst if n >= 30]
    for c, w, fl, n in sorted(flat, key=lambda r: -r[2])[:8]:
        print(f"  {fl:+.3f}  {c:9} {w}  (n={n})")
    print("Per-work FL, least front-loaded / back-loaded (n>=30):")
    for c, w, fl, n in sorted(flat, key=lambda r: r[2])[:8]:
        print(f"  {fl:+.3f}  {c:9} {w}  (n={n})")
    print()


# --------------------------------------------------------------------------
# TEST 3
# --------------------------------------------------------------------------
def test3(works):
    print("=" * 74)
    print("TEST 3 — Distinct loci per (article x work)")
    print("=" * 74)
    print("'Catch the first, drop the rest' predicts the cue-anchored corpora")
    print("pile up at 1 distinct locus per article-work; scope-tracked corpora")
    print("should show a longer tail.\n")

    # corpus -> {(iid, work): set(locus)}
    pairs = collections.defaultdict(lambda: collections.defaultdict(set))
    for corpus, work, dots in works:
        for dot in dots:
            iid = dot.get("iid")
            if not iid:
                continue
            locus = (str(dot.get("book", "")), str(dot.get("page", "")),
                     str(dot.get("section", "")), str(dot.get("line", "")))
            pairs[corpus][(iid, work)].add(locus)

    hdr = f"{'corpus':10} {'regime':13} {'artcl·wrk':>9} {'mean':>6} {'median':>6} {'%==1':>7} {'%<=2':>7} {'max':>5}"
    print(hdr)
    print("-" * len(hdr))
    for corpus in CORPUS_ORDER:
        pm = pairs.get(corpus)
        if not pm:
            continue
        counts = [len(s) for s in pm.values()]
        regime = "cue-anchored" if corpus in CUE_ANCHORED else "scope-tracked"
        one = sum(1 for c in counts if c == 1) / len(counts)
        two = sum(1 for c in counts if c <= 2) / len(counts)
        print(f"{corpus:10} {regime:13} {len(counts):9,} {statistics.mean(counts):6.2f} "
              f"{statistics.median(counts):6.1f} {pct(one):>7} {pct(two):>7} {max(counts):5,}")
    print()
    print("Reading: a high %==1 for homer/pindar/nt (vs stephanus/bekker) is the")
    print("fingerprint of first-citation-only capture. Note this is corroborating,")
    print("not decisive: short works and single-locus arguments also produce 1s.")
    print()


# --------------------------------------------------------------------------
# TESTS 4-6 — distortions on axes OTHER than within-work position.
# Front-loading is a bias along the passage axis; these probe the axes the
# tool actually reports on (time, journal/discipline) and the shape of
# engagement. All run on view_b data alone; resolved.tsv would sharpen but is
# not required.
# --------------------------------------------------------------------------
def _pairs_with_meta(works):
    """corpus -> {(iid, work): {'loci': set, 'decade': int|None, 'group': str}}
    plus a journal->group map baked in by the caller."""
    out = collections.defaultdict(lambda: collections.defaultdict(
        lambda: {"loci": set(), "decade": None, "journal": None}))
    for corpus, work, dots in works:
        for dot in dots:
            iid = dot.get("iid")
            if not iid:
                continue
            rec = out[corpus][(iid, work)]
            rec["loci"].add((str(dot.get("book", "")), str(dot.get("page", "")),
                             str(dot.get("section", "")), str(dot.get("line", ""))))
            if rec["decade"] is None:
                rec["decade"] = _decade(dot.get("year"))
            if rec["journal"] is None:
                rec["journal"] = dot.get("journal")
    return out


def test4(works, jgroups):
    print("=" * 74)
    print("TEST 4 — Capture DEPTH by decade x regime  (the consequential one)")
    print("=" * 74)
    print("Front-loading is a passage-axis bias. The tool's headline outputs are")
    print("on the TIME and JOURNAL axes, so the real worry is that cue-dropping")
    print("propensity correlates with era or discipline. Design: scope-tracked")
    print("corpora act as a CONTROL (continuations recovered), cue-anchored as")
    print("treatment (continuations lost). A regime x decade INTERACTION — depth")
    print("falling off faster back in time for cue-anchored than scope-tracked —")
    print("is the fingerprint of an era-correlated capture artifact.\n")

    pm = _pairs_with_meta(works)
    # regime -> decade -> [loci counts]
    by = {"cue-anchored": collections.defaultdict(list),
          "scope-tracked": collections.defaultdict(list)}
    for corpus, pairs in pm.items():
        regime = "cue-anchored" if corpus in CUE_ANCHORED else "scope-tracked"
        for rec in pairs.values():
            d = rec["decade"]
            if d is not None:
                by[regime][d].append(len(rec["loci"]))

    decades = sorted(d for r in by for d in by[r] if 1880 <= d <= 2020)
    decades = sorted(set(decades))
    print(f"{'decade':>7} {'cue-anchored (n)':>22} {'scope-tracked (n)':>22}")
    print("-" * 54)
    for d in decades:
        ca = by["cue-anchored"].get(d, [])
        st = by["scope-tracked"].get(d, [])
        cav = f"{statistics.mean(ca):5.2f} ({len(ca):,})" if len(ca) >= 20 else (f"· ({len(ca)})" if ca else "·")
        stv = f"{statistics.mean(st):5.2f} ({len(st):,})" if len(st) >= 20 else (f"· ({len(st)})" if st else "·")
        print(f"{d:>7} {cav:>22} {stv:>22}")
    print("-" * 54)
    print("Read the two columns as trend lines. If they move together, capture")
    print("depth tracks real engagement and is NOT era-biased. If cue-anchored")
    print("sags in early decades while scope-tracked holds, that gap is an")
    print("era-correlated capture artifact — and it would bias the temporal")
    print("floors of homer/pindar/nt specifically. (resolved.tsv would replace")
    print("this proxy with the exact scope_inherited share per decade.)\n")

    # discipline-axis view: capture depth by journal group, cue-anchored only
    print("Capture depth by discipline (cue-anchored corpora only):")
    grp_counts = collections.defaultdict(list)
    for corpus in CUE_ANCHORED:
        for rec in pm.get(corpus, {}).values():
            g = jgroups.get(rec["journal"], "other")
            grp_counts[g].append(len(rec["loci"]))
    for g, cs in sorted(grp_counts.items(), key=lambda kv: -len(kv[1])):
        if len(cs) >= 20:
            print(f"  {g:12} mean loci/article {statistics.mean(cs):5.2f}  (n={len(cs):,})")
    print("  A large discipline spread here means cross-journal comparisons in")
    print("  the cue-anchored corpora partly reflect citing STYLE, not attention.\n")


def test5(works):
    print("=" * 74)
    print("TEST 5 — Right-tail of per-article engagement  (article-weight bias)")
    print("=" * 74)
    print("Dropping continuations truncates the heaviest engagements: an article")
    print("that walks a work 30x but drops the cue after a few looks like a light")
    print("user. That compresses the article-weight distribution. If cue-anchored")
    print("corpora have a thinner right tail than scope-tracked, deep readings are")
    print("being under-counted.\n")

    hdr = f"{'corpus':10} {'regime':13} {'pairs':>8} {'mean':>6} {'p90':>5} {'p99':>5} {'max':>5} {'Gini':>6}"
    print(hdr)
    print("-" * len(hdr))
    pm = _pairs_with_meta(works)
    for corpus in CORPUS_ORDER:
        pairs = pm.get(corpus)
        if not pairs:
            continue
        counts = sorted(len(r["loci"]) for r in pairs.values())
        if not counts:
            continue
        regime = "cue-anchored" if corpus in CUE_ANCHORED else "scope-tracked"
        p90 = counts[min(len(counts) - 1, int(0.90 * len(counts)))]
        p99 = counts[min(len(counts) - 1, int(0.99 * len(counts)))]
        print(f"{corpus:10} {regime:13} {len(counts):8,} {statistics.mean(counts):6.2f} "
              f"{p90:5} {p99:5} {max(counts):5} {gini(counts):6.3f}")
    print()
    print("Read: a lower p99 / Gini for cue-anchored corpora signals a clipped")
    print("tail. NB Test 3 showed cue-anchored means run HIGHER (cues get repeated),")
    print("so a clipped tail here would be the more specific worry, not overall depth.\n")


def test6(works):
    print("=" * 74)
    print("TEST 6 — Within-work concentration  (canonical-peak bias)")
    print("=" * 74)
    print("If the surviving citation is the famous anchor and the dropped")
    print("continuations drift to deep-cut passages, the map over-concentrates on")
    print("canonical loci. Normalised entropy: 1.0 = citations spread evenly over")
    print("a work's loci, ->0 = piled on a few. Lower for cue-anchored than")
    print("scope-tracked would be the concentration fingerprint.\n")

    # corpus -> per-work normalised entropy (cite-weighted mean), works with >=10 loci
    per_corpus = collections.defaultdict(list)   # (entropy, weight)
    for corpus, work, dots in works:
        loc_counts = collections.Counter()
        for dot in dots:
            loc_counts[(str(dot.get("book", "")), str(dot.get("page", "")),
                        str(dot.get("section", "")), str(dot.get("line", "")))] += 1
        if len(loc_counts) >= 10:
            h = norm_entropy(list(loc_counts.values()))
            if h is not None:
                per_corpus[corpus].append((h, sum(loc_counts.values())))

    hdr = f"{'corpus':10} {'regime':13} {'works':>6} {'mean H':>7} {'cite-wtd H':>11}"
    print(hdr)
    print("-" * len(hdr))
    reg_pool = collections.defaultdict(list)
    for corpus in CORPUS_ORDER:
        rows = per_corpus.get(corpus)
        if not rows:
            continue
        regime = "cue-anchored" if corpus in CUE_ANCHORED else "scope-tracked"
        mean_h = statistics.mean(h for h, _ in rows)
        wtot = sum(w for _, w in rows)
        wh = sum(h * w for h, w in rows) / wtot if wtot else 0
        reg_pool[regime].extend(rows)
        print(f"{corpus:10} {regime:13} {len(rows):6} {mean_h:7.3f} {wh:11.3f}")
    print("-" * len(hdr))
    for regime, rows in reg_pool.items():
        wtot = sum(w for _, w in rows)
        wh = sum(h * w for h, w in rows) / wtot if wtot else 0
        print(f"{'POOLED':10} {regime:13} {len(rows):6} {statistics.mean(h for h,_ in rows):7.3f} {wh:11.3f}")
    print()
    print("Read: markedly lower entropy for cue-anchored corpora = citations")
    print("bunched on fewer (canonical) loci, consistent with keeping anchors and")
    print("losing deep-cut continuations. Similar entropy argues against it.\n")


# --------------------------------------------------------------------------
# TEST 7 — cue-dropping propensity by discipline and decade (needs resolved.tsv)
# --------------------------------------------------------------------------
def test7(resolved_path, jgroups):
    print("=" * 74)
    print("TEST 7 — Cue-dropping propensity by discipline & decade")
    print("=" * 74)
    print("Closes the one flag left by TEST 4 (classics 7.35 vs theology 4.55")
    print("loci/article): is that a citing-STYLE difference or real attention?")
    print("A scope_inherited hit IS a recovered cue-less continuation, so its")
    print("share of a stratum's citations is a DIRECT proxy for cue-dropping.")
    print("It exists only in scope-tracked corpora (stephanus/bekker), so we")
    print("measure it on Plato/Aristotle and read it as the analog for the")
    print("cue-anchored corpora. If the share swings hard by discipline, the")
    print("Homer/Pindar/NT cross-discipline map is partly style, not attention.\n")

    if not resolved_path or not os.path.exists(resolved_path):
        print("SKIPPED — needs resolved.tsv. Re-run with --resolved resolved.tsv\n")
        return

    # (group|decade) -> [total, scope]  restricted to scope-tracked corpora
    by_disc = collections.defaultdict(lambda: [0, 0])
    by_dec = collections.defaultdict(lambda: [0, 0])
    grid = collections.defaultdict(lambda: [0, 0])   # (group, decade) -> [total, scope]
    with open(resolved_path, newline="") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            if row.get("corpus") not in SCOPE_TRACKED:
                continue
            method = (row.get("method") or "").strip()
            is_scope = 1 if method in SCOPE_METHODS else 0
            grp = jgroups.get(row.get("journal"), "other")
            dec = _decade(row.get("year"))
            by_disc[grp][0] += 1; by_disc[grp][1] += is_scope
            if dec is not None:
                by_dec[dec][0] += 1; by_dec[dec][1] += is_scope
                grid[(grp, dec)][0] += 1; grid[(grp, dec)][1] += is_scope

    def share(pair):
        t, s = pair
        return (s / t) if t else 0.0

    print("By discipline (scope_inherited share = cue-dropping rate):")
    print(f"  {'discipline':12} {'cites':>9} {'scope':>8} {'drop-rate':>10}")
    disc_order = sorted(by_disc, key=lambda g: -by_disc[g][0])
    for g in disc_order:
        t, s = by_disc[g]
        if t >= 50:
            print(f"  {g:12} {t:9,} {s:8,} {pct(share(by_disc[g])):>10}")
    print()

    print("By decade:")
    print(f"  {'decade':>7} {'cites':>9} {'drop-rate':>10}")
    for d in sorted(by_dec):
        if 1880 <= d <= 2020 and by_dec[d][0] >= 50:
            print(f"  {d:>7} {by_dec[d][0]:9,} {pct(share(by_dec[d])):>10}")
    print()

    # discipline x decade grid for the big disciplines, to catch an interaction
    big = [g for g in disc_order if by_disc[g][0] >= 500][:3]
    decs = [d for d in sorted(by_dec) if 1880 <= d <= 2020 and by_dec[d][0] >= 50]
    if big and decs:
        print("Drop-rate grid (discipline x decade), blank = <30 cites in cell:")
        print("  decade  " + "".join(f"{g[:9]:>11}" for g in big))
        for d in decs:
            cells = []
            for g in big:
                t, s = grid[(g, d)]
                cells.append(f"{pct(s/t):>11}" if t >= 30 else f"{'·':>11}")
            print(f"  {d:>6}  " + "".join(cells))
        print()

    # headline reconciliation with TEST 4's depth spread
    disc_rate = {g: share(by_disc[g]) for g in by_disc if by_disc[g][0] >= 500}
    if len(disc_rate) >= 2:
        hi = max(disc_rate, key=disc_rate.get)
        lo = min(disc_rate, key=disc_rate.get)
        print(f"Spread: {hi} drops cues at {pct(disc_rate[hi])} vs {lo} at "
              f"{pct(disc_rate[lo])} (gap {disc_rate[hi]-disc_rate[lo]:+.3f}).")
        print("Reconcile with TEST 4: if the LOW-capture-depth discipline (theology,")
        print("4.55 loci/article) also has the HIGHER drop-rate here, its Homer/NT")
        print("capture is the more undercounted, so part of the classics-vs-theology")
        print("depth gap is a style artifact. If drop-rates are ~equal across")
        print("disciplines, the depth gap is real attention, not capture bias.")
        print("(Caveat: measured on Plato/Aristotle citers; assumes the same")
        print("citing habit carries to how those journals cite Homer/Pindar/NT.)")
    print()


# --------------------------------------------------------------------------
# TEST 2  (needs resolved.tsv for the `method` column)
# --------------------------------------------------------------------------
# resolve_citations.py methods that mean "the work was NAMED here" vs the
# scope-inherited continuations we want to isolate.
NAMED_METHODS = {"range+name", "range_unique+name", "cross_system_resolved_by_name",
                 "range_unique_name_mentioned", "boundary_resolved_by_name",
                 "name_range", "title_prior", "range_unique", "cue_work"}
SCOPE_METHODS = {"scope_inherited"}


def test2(pos, resolved_path):
    print("=" * 74)
    print("TEST 2 — Named vs scope-inherited position (Plato/Aristotle)")
    print("=" * 74)
    if not resolved_path or not os.path.exists(resolved_path):
        print("SKIPPED — needs resolved.tsv (the `method` column is not preserved")
        print("in the viewer aggregates). Regenerate it and re-run with")
        print("  --resolved resolved.tsv")
        print("Wiring is in place; the moment that file exists this test runs.\n")
        return

    # position from the resolved row's `match` (e.g. '553a', '1097b8') + work_id
    buckets = {"named": collections.defaultdict(list),   # corpus -> [p]
               "scope": collections.defaultdict(list)}
    seen_methods = collections.Counter()
    with open(resolved_path, newline="") as fh:
        rd = csv.DictReader(fh, delimiter="\t")
        for row in rd:
            corpus = row.get("corpus")
            if corpus not in SCOPE_TRACKED:      # named-vs-scope only meaningful here
                continue
            method = (row.get("method") or "").strip()
            seen_methods[method] += 1
            if method in SCOPE_METHODS:
                grp = "scope"
            elif method in NAMED_METHODS:
                grp = "named"
            else:
                continue
            work = row.get("work_id") or ""
            match = row.get("match") or ""
            mp = re.match(r"\s*(\d+)\s*([a-eA-E]?)", match)
            if not mp:
                continue
            dot = {"page": mp.group(1), "section": mp.group(2).lower(), "line": None, "book": None}
            p = pos.of(corpus, work, dot)
            if p is not None:
                buckets[grp][corpus].append(p)

    hdr = f"{'corpus':10} {'group':6} {'n':>8} {'mean_p':>7} {'%q1':>7} {'%q4':>7} {'FL':>8}"
    print(hdr)
    print("-" * len(hdr))
    for corpus in ("stephanus", "bekker"):
        for grp in ("named", "scope"):
            ps = buckets[grp].get(corpus)
            if not ps:
                continue
            s = fl_index(ps)
            print(f"{corpus:10} {grp:6} {s['n']:8,} {s['mean_p']:7.3f} "
                  f"{pct(s['q1']):>7} {pct(s['q4']):>7} {s['fl']:+8.3f}")
    print("-" * len(hdr))

    # the headline: full vs named-only front-loading, and the implied artifact
    for corpus in ("stephanus", "bekker"):
        named = buckets["named"].get(corpus, [])
        scope = buckets["scope"].get(corpus, [])
        if not named or not scope:
            continue
        full = named + scope
        fn, ff = fl_index(named), fl_index(full)
        dpos = (sum(scope) / len(scope)) - (sum(named) / len(named))
        print(f"\n{corpus}: scope-inherited mean position is {dpos:+.3f} vs named "
              f"({'later' if dpos > 0 else 'earlier'} in the work).")
        print(f"  Front-loading  full set : {ff['fl']:+.3f}")
        print(f"  Front-loading  named-only: {fn['fl']:+.3f}  "
              f"(artifact estimate: {fn['fl'] - ff['fl']:+.3f})")
    print()
    print("Named-only simulates the cue-anchored regime (homer/pindar/nt). The")
    print("named-only-minus-full gap is the front-loading the artifact ADDS; apply")
    print("it to the cue-anchored corpora to estimate how much of their")
    print("front-loading is artifactual — i.e. how tall the v3 'fades' should be.")
    if seen_methods:
        print("\n(method tallies seen in resolved.tsv, for reference:)")
        for m, n in seen_methods.most_common():
            tag = "scope" if m in SCOPE_METHODS else ("named" if m in NAMED_METHODS else "other")
            print(f"    {m or '(blank)':32} {n:8,}  [{tag}]")
    print()


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--view-b", default="viewer_data/view_b",
                    help="dir of per-work view_b JSON (default: viewer_data/view_b)")
    ap.add_argument("--tables", default=".",
                    help="dir holding the *_line_counts / *_ranges JSON tables")
    ap.add_argument("--resolved", default=None,
                    help="resolved.tsv path — enables TEST 2 (else skipped)")
    args = ap.parse_args()

    if not os.path.isdir(args.view_b):
        print(f"ERROR: view_b dir not found: {args.view_b}", file=sys.stderr)
        sys.exit(1)

    pos = Positions(args.tables)
    works = list(load_view_b(args.view_b))       # small enough to materialise
    n_works = len(works)
    n_dots = sum(len(d) for _, _, d in works)
    print(f"Loaded {n_works} works, {n_dots:,} citation dots from {args.view_b}\n")

    # journal -> discipline group (for TEST 4)
    jgroups = {}
    try:
        g = json.load(open(os.path.join(args.tables, "journal_groups.json")))["groups"]
        for k, v in g.items():
            for j in (v.get("journals", []) if isinstance(v, dict) else v):
                jgroups[j] = k
    except Exception as e:
        print(f"  (warn) journal_groups.json unavailable, TEST 4 discipline view degraded: {e}",
              file=sys.stderr)

    test1(pos, works)
    test2(pos, args.resolved)
    test3(works)
    test4(works, jgroups)
    test5(works)
    test6(works)
    test7(args.resolved, jgroups)


if __name__ == "__main__":
    main()
