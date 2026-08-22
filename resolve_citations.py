#!/usr/bin/env python3
"""
resolve_citations.py — resolve the extracted citation candidates in
citations.tsv to specific works/passages, using the five reference tables.

Implements the handoff's resolution architecture, in order of authority:
  1. FORMAT ROUTING   — the number's shape already says Bekker vs Stephanus.
                        (Done at extraction time as the corpus tag; re-checked.)
  2. RANGE CONSTRAINT — which work(s)' page-range contains this integer.
                        Bekker: globally unique -> usually one treatise outright.
                        Stephanus: resets -> a shortlist of candidate dialogues.
  3. ABBREVIATION MATCH — score the work-name/abbrev tokens in the context
                        window against the synonym table; intersect with the
                        range shortlist. An abbreviation is NEVER trusted on its
                        own for an ambiguous form — range membership must agree.
  4. SCOPE TRACKING   — for a bare number with no adjacent name, inherit the
                        last-named work in reading order (seq), with confidence
                        decaying by distance (page + char_offset gap).

Everything is CONSERVATIVE by design (the handoff's central warning: a wrong
resolution silently corrupts the heatmap, so bias toward the review queue).
  - Confidence >= ACCEPT_THRESHOLD  -> resolved.tsv   (auto-accepted)
  - anything below, plus every boundary-page Bekker hit, plus common-books
    double-maps -> review_queue.tsv  (human eyeballs, context attached)

Outputs:
  resolved.tsv      iid, journal, year, doctype, corpus, page_index, seq,
                    match, work_id, book, confidence, method, context
  review_queue.tsv  same columns + reason
  resolve_report.txt  tallies: resolved vs queued, by corpus, by method,
                    top reasons for queueing.

Usage:
    python3 resolve_citations.py citations.tsv \\
        --tables /path/to/tables_dir \\
        [--accept 0.90] [--scope-decay-pages 1] [--max-scope-chars 4000]

The tables dir must contain: bekker_ranges.json, stephanus_ranges.json,
abbreviation_synonyms.json, metaphysics_books.json, ethics_books.json.
Defaults to the current directory.
"""

import sys, os, json, csv, re, argparse, unicodedata, collections
import locus   # shared parser — range expansion + cue->work key (single source of truth)

# The csv module caps a single field at 131072 chars by default; a context
# window off a pathological (scanned-volume) page can exceed that. Raise the
# limit to the platform max so DictReader never chokes mid-file.
def _raise_csv_limit():
    lim = sys.maxsize
    while True:
        try:
            csv.field_size_limit(lim)
            break
        except OverflowError:
            lim = int(lim // 10)
_raise_csv_limit()

# ------------------------------------------------------------------ helpers
def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))

def norm(s):
    """lowercase, accent-stripped, trailing-period-stripped, for matching."""
    return strip_accents(str(s)).lower().strip().rstrip(".").strip()

def page_int(match):
    """Leading integer of a citation token: '80d5'->80, '1252a'->1252,
    '327b'->327. Returns None if it doesn't start with digits."""
    m = re.match(r"\d+", match)
    return int(m.group()) if m else None

def match_letter(match):
    """The section/column letter: '80d5'->'d', '1252a'->'a'. None if absent."""
    m = re.match(r"\d+([a-eA-E])", match)
    return m.group(1).lower() if m else None

def match_col_line(match):
    """Bekker column+line: '453b11'->('b',11), '449a'->('a',0), '80d5'->(None,0)
    for non-Bekker letters. Returns (col_or_None, line_int)."""
    m = re.match(r"\d+([abAB])(\d*)$", match)
    if not m:
        return None, 0
    return m.group(1).lower(), int(m.group(2) or 0)

# ---------------------------------------------------------------- exclusions
# The extractor tags anything of citation SHAPE; several non-Plato/Aristotle
# citation systems share that shape. We divert (not delete) them to
# excluded.tsv with a reason, so e.g. the Diels-Kranz set is a ready-made
# Presocratics dataset for a future heatmap.

BEKKER_CEILING = 1462          # Bekker 1831 ends ~1462b; anything >= 1463 that
                               # looks Bekker-shaped is a modern year, not Aristotle.

# a citation token immediately followed by a DK marker -> Diels-Kranz fragment
_DK_AFTER = re.compile(r"^\s*[-–—]?\s*(?:=\s*)?(?:d[\s.\-]?k|diels)", re.I)
# foreign / non-classical text markers that, when they IMMEDIATELY precede the
# number, indicate a citation to some other author (Homer, Sophocles, papyri,
# biblical, etc.). Kept deliberately short and specific; extend as data shows.
_FOREIGN_BEFORE = re.compile(
    r"(?:\b(?:Aj|Od|Il|Ar|Nub|Ran|Soph|Eur|Hom|Aesch|Pind|Sall|Iug|his|Tac|"
    r"Verg|Aen|Ov|Hor|Cic|Liv|Plut|Sext|adv|math|schol|fr|frg|POxy|PMG|"
    r"Gen|Ex|Lev|Matt|Luc|Joh)\.?\s*)$",
    re.I)

# index/concordance page detection. The measurement pass showed these are
# overwhelmingly 'misc'/'book-review' doctype (old journal back-matter, e.g.
# Classical Review place-name indices) with very high numeric-token density.
# Restricting to those doctypes protects research-article footnotes, which can
# be citation-dense but are genuine. A pure count/density filter over ALL rows
# would gut real dense footnotes; this narrow combination does not.
# Doctype scope decision (evidence-based; see probe_misc analysis):
#  - 'misc' is 54,665 candidates, 94% from one journal (The Classical Review)
#    and 83% pre-1910: these are back-of-volume SUBJECT INDICES recording page
#    locators ("Rep. 344e: 213" = discussed on p.213), not scholarly citations.
#    77% trip the index signal; the 'prose' remainder is mostly ToC/index
#    entries too. Excluded wholesale as a scope decision.
#  - 'book-review' is 89% substantive prose (reviewers discussing passages),
#    spread across decades and journals: KEPT.
#  - 'research-article' and 'discussion': KEPT.
#  - frontmatter/backmatter/news/books-received: non-content, excluded.
# This one clean rule replaces the fragile density/count index heuristic:
# with misc gone, the index contamination is removed at the source, and the
# citation-dense footnotes inside research articles are never touched.
KEEP_DOCTYPES = {"research-article", "book-review", "book-reviews", "discussion"}
_TOKEN = re.compile(r"[^\s,;]+")
_NUMISH = re.compile(r"^\(?\d+[a-eA-E]?\d*[.,;:)]*$")
_CITE_SHAPED = re.compile(r"\b\d+[a-eA-E]\d*\b")

def _numeric_density(context):
    toks = _TOKEN.findall(context)
    if not toks:
        return 0.0
    return sum(1 for t in toks if _NUMISH.match(t)) / len(toks)

def classify_exclusion(match, context, corpus, doctype=""):
    """Return a reason string if this row should be EXCLUDED (diverted), else
    None. context is the flattened window; match is the citation token."""
    page = page_int(match)
    # locate the match inside the context to inspect immediate neighbours
    idx = context.find(match)
    after  = context[idx + len(match): idx + len(match) + 8] if idx >= 0 else ""
    before = context[max(0, idx - 12): idx] if idx >= 0 else ""

    # 0. book.section reference to ANOTHER work: a number of the form N.NNe
    #    (e.g. Polybius '12.25e', '12.27a') where the citation is immediately
    #    preceded by 'digits.' — that leading 'book.' marks it as some other
    #    author's book/chapter, not a bare Stephanus/Bekker page.
    if re.search(r"\d+\.$", before):
        return "book_section_ref"

    # 1. Diels-Kranz fragment (number followed by DK / D-K / Diels)
    if _DK_AFTER.match(after):
        return "dk_fragment"

    # 2. modern-scholarship year: leading integer above Bekker's ceiling.
    #    (only meaningful for bekker/ambiguous shapes; stephanus pages are <=621)
    if page is not None and page >= BEKKER_CEILING + 1:
        return "modern_year"

    # 3. immediate foreign-text marker just before the number
    if _FOREIGN_BEFORE.search(before):
        return "foreign_text"

    # 4. doctype scope: keep only substantive content types. 'misc' (old
    #    journal subject-indices) and non-content back-matter are diverted.
    #    Runs last so content-level reasons (dk/year/etc.) are tagged when they
    #    also apply, but any kept-doctype row still gets scoped out here if misc.
    if doctype and doctype not in KEEP_DOCTYPES:
        return "excluded_doctype"

    return None


# ------------------------------------------------------------------ tables
class Tables:
    def __init__(self, d):
        self.bekker = self._load(d, "bekker_ranges.json")
        self.steph  = self._load(d, "stephanus_ranges.json")
        self.abbr   = self._load(d, "abbreviation_synonyms.json")
        self.meta_books = self._load(d, "metaphysics_books.json")
        self.eth_books  = self._load(d, "ethics_books.json")
        # New corpora (Homer/Pindar/NT): cue -> work, NT verses-per-chapter, and
        # Homer lines-per-book (both reject citations past a facet's real end).
        self.work_cues = self._load(d, "work_cues.json")
        self.nt_lengths = self._load(d, "nt_chapter_lengths.json")["books"]
        self.homer_lengths = self._load(d, "homer_line_counts.json")["books"]
        # Pindar ode lengths vary a little by edition, so pad each by ~15% + 3
        # lines: catch the wild strays (line 813 in a 115-line ode) without
        # clipping legitimate near-boundary lines.
        _pin = self._load(d, "pindar_line_counts.json")["books"]
        self.pindar_lengths = {w: [round(x * 1.15) + 3 for x in arr] for w, arr in _pin.items()}
        self._build_indexes()

    @staticmethod
    def _load(d, name):
        with open(os.path.join(d, name), encoding="utf-8") as fh:
            return json.load(fh)

    def _build_indexes(self):
        # --- Bekker: list of (start, end, work_id) + which pages are shared ---
        self.bekker_ranges = []
        self.bekker_boundary_pages = set()
        for t in self.bekker["treatises"]:
            self.bekker_ranges.append((t["bekker_start"], t["bekker_end"], t["id"]))
            note = t.get("notes", "")
            for pg in re.findall(r"shares? p\.?(\d+)", note):
                self.bekker_boundary_pages.add(int(pg))
        for s, e, _ in self.bekker_ranges:
            for s2, e2, _ in self.bekker_ranges:
                if s == e2 and s != s2:
                    self.bekker_boundary_pages.add(s)

        # --- Stephanus: list of (start, end, dialogue_id) ---
        self.steph_ranges = []
        for d in self.steph["dialogues"]:
            self.steph_ranges.append((d["stephanus_start"], d["stephanus_end"], d["id"]))

        # which system each work_id belongs to (for cross-system detection)
        self.work_system = {}
        for _, _, wid in self.bekker_ranges:
            self.work_system[wid] = "bekker"
        for _, _, wid in self.steph_ranges:
            self.work_system[wid] = "stephanus"

        # precise (page,col,line) boundaries where present (Parva Naturalia,
        # from Ross 1931). Lets us disambiguate shared pages by column+line.
        # map: work_id -> (start_tuple, end_tuple) with tuple=(page,col_rank,line)
        # col_rank: 'a'->0, 'b'->1 so (page,col,line) sorts correctly.
        self.precise = {}
        for t in self.bekker["treatises"]:
            sp, ep = t.get("start_precise"), t.get("end_precise")
            if sp and ep:
                self.precise[t["id"]] = (
                    (sp["page"], 0 if sp["col"] == "a" else 1, sp["line"]),
                    (ep["page"], 0 if ep["col"] == "a" else 1, ep["line"]),
                )

        # --- abbreviation -> set of work_ids; ambiguous-form set ---
        self.form_to_ids = collections.defaultdict(set)
        self.ambiguous_forms = set()
        self.author_names = collections.defaultdict(set)
        for author_key, block in (("plato", self.abbr["plato"]),
                                   ("aristotle", self.abbr["aristotle"])):
            for lang, names in block.get("author_names", {}).items():
                for nm in names:
                    self.author_names[norm(nm)].add(author_key)
            for w in block["works"]:
                wid = w["id"]
                for lang, variants in w.get("variants", {}).items():
                    for v in variants:
                        self.form_to_ids[norm(v)].add(wid)
                for amb in w.get("ambiguous_forms", {}):
                    for piece in amb.split("/"):
                        self.ambiguous_forms.add(norm(piece))

        self.meta_letter = {}
        for b in self.meta_books["books"]:
            span = (b["bekker_start"], b["bekker_end"], b["book_number"])
            for key in (b.get("letter_greek"), b.get("letter_translit"),
                        b.get("letter_latin")):
                if key:
                    self.meta_letter[norm(key)] = span

        self.ne_books = {b["book"]: b for b in self.eth_books["nicomachean_ethics"]["books"]}
        self.ee_books = {b["book"]: b for b in self.eth_books["eudemian_ethics"]["books"]}

    # ---- range lookups ----
    def bekker_lookup(self, page):
        hits = [wid for s, e, wid in self.bekker_ranges if s <= page <= e]
        return hits

    def steph_lookup(self, page):
        return [wid for s, e, wid in self.steph_ranges if s <= page <= e]

    def is_bekker_boundary(self, page):
        return page in self.bekker_boundary_pages

    def cued_work(self, corpus, cell):
        """Route a Homer/Pindar/NT cell to its work via the cue. Returns work_id
        (e.g. 'Iliad', 'Olympian', 'Romans') or None if the cue doesn't resolve."""
        key = locus.work_cue_key(cell, corpus)
        if key is None:
            return None
        return self.work_cues.get(corpus, {}).get(key)

    def refine_by_precise(self, candidate_ids, page, col, line):
        """Given candidate work_ids all containing `page` at integer level, use
        precise (page,col,line) boundaries to keep only those whose precise span
        actually contains this position. Candidates WITHOUT precise data are
        left in (we can't rule them out). Returns the refined candidate list.
        col: 'a'/'b' or None; line: int or 0."""
        if col is None:
            return candidate_ids
        pos = (page, 0 if col == "a" else 1, line)
        refined = []
        for wid in candidate_ids:
            span = self.precise.get(wid)
            if span is None:
                refined.append(wid)          # no precise data: can't exclude
                continue
            start, end = span
            # a line of 0 means "unspecified" — treat as inclusive at page edge
            if start <= pos <= end:
                refined.append(wid)
        return refined if refined else candidate_ids


# ------------------------------------------------------------------ resolver
class Resolver:
    def __init__(self, tables, accept, decay_pages, max_scope_chars, scope_accept=0.83):
        self.T = tables
        self.accept = accept
        self.scope_accept = scope_accept
        self.decay_pages = decay_pages
        self.max_scope_chars = max_scope_chars

    def context_forms(self, context):
        """Return the set of work_ids named in the context window, and whether
        any matched form was ambiguous. Matches multi-word names greedily by
        scanning normalised n-grams up to 3 tokens."""
        toks = re.findall(r"[A-Za-zÀ-ÿ.]+", context)
        found_ids = set()
        saw_ambiguous = False
        ntoks = [norm(t) for t in toks]
        for i in range(len(ntoks)):
            for span in (3, 2, 1):
                if i + span > len(ntoks):
                    continue
                form = " ".join(ntoks[i:i+span]).strip()
                if not form:
                    continue
                if form in self.T.form_to_ids:
                    found_ids |= self.T.form_to_ids[form]
                    if form in self.T.ambiguous_forms:
                        saw_ambiguous = True
        return found_ids, saw_ambiguous

    def title_forms(self, title):
        """Work_ids named in the article TITLE. Titles use FULL work names
        ('Plato's Meno', 'the Nicomachean Ethics'), so we match full-name forms
        only — not ambiguous abbreviations — to keep the title prior clean.
        A title naming a work is a strong DOCUMENT-LEVEL prior that a bare
        in-range number belongs to that work."""
        if not title:
            return set()
        toks = re.findall(r"[A-Za-zÀ-ÿ.]+", title)
        ntoks = [norm(t) for t in toks]
        found = set()
        for i in range(len(ntoks)):
            for span in (3, 2, 1):
                if i + span > len(ntoks):
                    continue
                form = " ".join(ntoks[i:i+span]).strip()
                if form and form in self.T.form_to_ids:
                    # only accept forms that are NOT flagged ambiguous — the
                    # title prior must be unambiguous to be trusted document-wide
                    if form not in self.T.ambiguous_forms:
                        found |= self.T.form_to_ids[form]
        return found

    def resolve_one(self, row, scope):
        """row: dict from citations.tsv. scope: per-iid last-named-work state.
        Returns (work_id, book, confidence, method, reason_or_None)."""
        corpus = row["corpus"]

        # ---- new corpora: the CUE names the work (Il->Iliad, Ol->Olympian,
        #      Rom->Romans). No range table needed; book is derived per unit at
        #      fan-out. High confidence — the author abbreviation is decisive. ----
        if corpus in ("homer", "pindar", "nt"):
            wid = self.T.cued_work(corpus, row["match"])
            if wid is None:
                return None, "", 0.0, "cue_unresolved", \
                    f"no work_cue match for {row['match']!r}"
            return wid, "", 0.95, "cue_work", None

        page = page_int(row["match"])
        if page is None:
            return None, "", 0.0, "no_page", "unparseable match"

        named_ids, saw_ambiguous = self.context_forms(row["context"])

        # ---- candidate works by range, per system ----
        bek = self.T.bekker_lookup(page)
        # precise-boundary refinement: on shared Parva Naturalia pages, the
        # column+line picks the right treatise (e.g. 449a34 -> De Sensu,
        # 449b3 -> De Memoria). Only narrows Bekker candidates; harmless when
        # the citation carries no Bekker column or the works lack precise data.
        col, line = match_col_line(row["match"])
        if len(bek) > 1 and col is not None:
            bek = self.T.refine_by_precise(bek, page, col, line)
        stp = self.T.steph_lookup(page)
        if corpus == "bekker":
            cand = list(bek)
        elif corpus == "stephanus":
            cand = list(stp)
        else:  # ambiguous: the number could belong to EITHER system
            cand = list(bek) + list(stp)
        cand_set = set(cand)

        # does the candidate set span both pagination systems?
        systems = {self.T.work_system.get(w) for w in cand_set}
        cross_system = ("bekker" in systems and "stephanus" in systems)

        # is this a within-Bekker treatise-boundary page? (separate axis)
        bek_boundary = self.T.is_bekker_boundary(page) and len(set(bek)) > 1

        # ---- unique by range alone (no name needed) ----
        if len(cand_set) == 1 and not cross_system:
            wid = next(iter(cand_set))
            # A UNIQUE range match is authoritative. Other work-names in the
            # context are almost always works MENTIONED, not the work cited
            # (e.g. Aristotle's Politics 1254b discussing Plato's Republic).
            # So we do NOT treat a mismatched name as a conflict here; we accept
            # the range. We still BOOST confidence when the name AGREES.
            if named_ids and wid in named_ids:
                conf, method = 0.97, "range_unique+name"
            elif named_ids:
                # name present but points elsewhere -> mentioned work, not a
                # conflict. Accept range, mild discount, tag for auditability.
                conf, method = 0.90, "range_unique_name_mentioned"
            else:
                conf, method = 0.93, "range_unique"
            self._update_scope(scope, row, wid)
            return wid, "", conf, method, None

        # ---- multiple candidates: the NAME must single out exactly one ----
        if cand_set:
            inter = cand_set & named_ids
            if len(inter) == 1:
                wid = inter.pop()
                self._update_scope(scope, row, wid)
                # label honestly by what the ambiguity actually was
                if cross_system:
                    method = "cross_system_resolved_by_name"
                elif bek_boundary:
                    method = "boundary_resolved_by_name"
                else:
                    method = "range+name"
                # a clean unique name-match is trustworthy in all three cases
                return wid, "", 0.90, method, None
            if len(inter) > 1:
                # name matches several candidates (e.g. two dialogues) -> queue
                return (sorted(inter)[0], "", 0.5, "name_multi_candidate",
                        f"name matches {sorted(inter)} within candidates "
                        f"{sorted(cand_set)}")
            # name present but matches NONE of the range candidates -> suspicious
            if named_ids:
                return (sorted(cand_set)[0], "", 0.45, "name_range_conflict",
                        f"named {sorted(named_ids)} not in range candidates "
                        f"{sorted(cand_set)}")

        # ---- no decisive name: scope inheritance ----
        inherited = self._inherit_scope(scope, row)
        if inherited:
            wid, decay_conf = inherited
            if self._work_contains(wid, page, corpus):
                reason = None if decay_conf >= self.scope_accept else "scope_conf_below_threshold"
                return wid, "", decay_conf, "scope_inherited", reason
            return wid, "", 0.4, "scope_range_mismatch", \
                f"inherited {wid} but {page} not in its range"

        # ---- title prior: article titled after a work disambiguates bare
        #      in-range numbers. Precedence is BELOW adjacent name and local
        #      scope (both already tried above) and applies only when the
        #      title uniquely intersects the range candidates — i.e. the number
        #      is in-range for exactly one title-named work. Conservative:
        #      never overrides a nearer signal, never resolves out-of-range.
        title_ids = self.title_forms(row.get("title", ""))
        if title_ids and cand_set:
            t_inter = cand_set & title_ids
            if len(t_inter) == 1:
                wid = t_inter.pop()
                self._update_scope(scope, row, wid)
                # strong but not certain: a title-about-X paper can still cite
                # X's page-neighbours in other works. High enough to accept,
                # tagged so it's auditable and tunable.
                return wid, "", 0.85, "title_prior", None

        # ---- nothing resolves ----
        cands = sorted(cand_set)
        tag = "cross_system_unresolved" if cross_system else "unresolved"
        return (cands[0] if cands else None), "", 0.3, tag, \
            f"no decisive name, no scope; candidates {cands}"

    def _work_contains(self, wid, page, corpus):
        for s, e, w in self.T.bekker_ranges:
            if w == wid:
                return s <= page <= e
        for s, e, w in self.T.steph_ranges:
            if w == wid:
                return s <= page <= e
        return False

    def _update_scope(self, scope, row, wid):
        scope[row["iid"]] = {
            "wid": wid,
            "page_index": int(row["page_index"]),
            "char_offset": int(row["char_offset"]),
            "seq": int(row["seq"]),
        }

    def _inherit_scope(self, scope, row):
        st = scope.get(row["iid"])
        if not st:
            return None
        # distance since last named work, in (page, char) terms
        dpage = int(row["page_index"]) - st["page_index"]
        if dpage < 0:
            return None
        if dpage == 0:
            dist = int(row["char_offset"]) - st["char_offset"]
        else:
            dist = dpage * 100000 + int(row["char_offset"])  # coarse cross-page
        if dist < 0 or dist > self.max_scope_chars * (self.decay_pages + dpage):
            return None
        # linear-ish decay: full inside a page, degrading across pages
        base = 0.88
        conf = base - 0.15 * dpage - 0.10 * min(dist / max(self.max_scope_chars, 1), 1.0)
        return st["wid"], round(max(conf, 0.0), 3)


# ------------------------------------------------------------------ fan-out
def resolved_system(corpus, wid, T):
    """The reference system to expand under. An 'ambiguous' cell (2-3 digit +
    a/b) is Plato OR low Aristotle; use the RESOLVED work's system so the section
    alphabet is right (Plato a-e vs Bekker a/b). Others expand under their tag."""
    if corpus == "ambiguous":
        return T.work_system.get(wid, "stephanus")
    return corpus

def unit_book(unit, corpus):
    """The 'book' facet for one fanned unit. Homer/Pindar: the book/ode number;
    NT: the chapter (so a cross-chapter range books each unit correctly). Greek
    units are left blank — the locus.py faceting stage fills them per unit."""
    if corpus in ("homer", "pindar"):
        m = re.search(r"(\d+)\.\d+$", unit)
        return m.group(1) if m else ""
    if corpus == "nt":
        m = re.search(r"(\d+):\d+$", unit)
        return m.group(1) if m else ""
    return ""


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("citations")
    ap.add_argument("--tables", default=".")
    ap.add_argument("--accept", type=float, default=0.90)
    ap.add_argument("--scope-accept", type=float, default=0.83,
                    help="lower accept gate for scope-inherited hits, which the "
                         "grep validation showed are reliable down to ~0.84 once "
                         "book.section refs are filtered out")
    ap.add_argument("--scope-decay-pages", type=int, default=1)
    ap.add_argument("--max-scope-chars", type=int, default=4000)
    args = ap.parse_args()

    T = Tables(args.tables)
    R = Resolver(T, args.accept, args.scope_decay_pages, args.max_scope_chars,
                 scope_accept=args.scope_accept)

    cols = ["iid","journal","year","doctype","corpus","page_index","seq",
            "match","work_id","book","confidence","method","context","span_src"]

    scope = {}   # iid -> last-named-work state
    n = resolved = queued = excluded = emitted = 0
    by_method = collections.Counter()
    by_reason = collections.Counter()
    by_corpus_res = collections.Counter()
    by_exclusion = collections.Counter()

    fres = open("resolved.tsv", "w", encoding="utf-8", newline="")
    frev = open("review_queue.tsv", "w", encoding="utf-8", newline="")
    fexc = open("excluded.tsv", "w", encoding="utf-8", newline="")
    wres = csv.writer(fres, delimiter="\t"); wres.writerow(cols)
    wrev = csv.writer(frev, delimiter="\t"); wrev.writerow(cols + ["reason"])
    wexc = csv.writer(fexc, delimiter="\t"); wexc.writerow(cols + ["exclusion"])

    with open(args.citations, encoding="utf-8") as fh:
        r = csv.DictReader(fh, delimiter="\t")
        for row in r:
            n += 1
            corpus = row["corpus"]
            # --- exclusion pass. The DK/foreign-marker/book-section checks are
            #     GREEK-specific (they divert non-Plato/Aristotle citations caught
            #     by the Greek regexes) and would wrongly nuke real Homer/Pindar/NT
            #     cells (e.g. "Hom. Il. 16.7"), so only run them for the Greek
            #     corpora. The doctype scope filter (old journal indices) still
            #     applies to everyone. ---
            if corpus in ("stephanus", "bekker", "ambiguous"):
                exreason = classify_exclusion(row["match"], row["context"],
                                              corpus, row.get("doctype", ""))
            else:
                dt = row.get("doctype", "")
                exreason = "excluded_doctype" if (dt and dt not in KEEP_DOCTYPES) else None
            if exreason:
                wexc.writerow([row["iid"], row["journal"], row["year"], row["doctype"],
                               corpus, row["page_index"], row["seq"], row["match"],
                               "", "", "", "excluded", row["context"], "", exreason])
                excluded += 1
                by_exclusion[exreason] += 1
                continue

            wid, book, conf, method, reason = R.resolve_one(row, scope)
            by_method[method] += 1
            accepted = (reason is None and conf >= min(args.accept, args.scope_accept))

            def base_row(match_cell, book_val):
                return [row["iid"], row["journal"], row["year"], row["doctype"],
                        corpus, row["page_index"], row["seq"], match_cell,
                        wid or "", book_val or "", f"{conf:.3f}", method, row["context"]]

            if not accepted:
                wrev.writerow(base_row(row["match"], book) + ["", reason or "below_threshold"])
                queued += 1
                by_reason[reason or "below_threshold"] += 1
                continue

            # --- accepted: FAN OUT the (possibly-range) cell into unit rows. ---
            system = resolved_system(corpus, wid, T)
            nt_len = T.nt_lengths.get(wid) if corpus == "nt" else None
            homer_len = T.homer_lengths.get(wid) if corpus == "homer" else None
            if corpus == "pindar":
                homer_len = T.pindar_lengths.get(wid)   # same line_counts channel
            units = locus.expand_range(row["match"], system, nt_lengths=nt_len,
                                       line_counts=homer_len)
            if units is None:
                # over-cap / incoherent / out-of-range span -> divert, don't fan.
                wrev.writerow(base_row(row["match"], book) + ["", "span_diverted"])
                queued += 1
                by_reason["span_diverted"] += 1
                continue
            span_src = row["match"] if len(units) > 1 else ""
            for u in units:
                wres.writerow(base_row(u, unit_book(u, corpus)) + [span_src])
            resolved += 1
            emitted += len(units)
            by_corpus_res[corpus] += 1

    fres.close(); frev.close(); fexc.close()

    with open("resolve_report.txt", "w", encoding="utf-8") as o:
        genuine = n - excluded   # denominator that matters: real P/A citations
        lines = ["CITATION RESOLUTION REPORT",
                 f"  input candidates      : {n:,}",
                 f"  excluded (diverted)   : {excluded:,} "
                 f"({excluded/n*100:.1f}% of input)" if n else "",
                 f"  genuine P/A citations : {genuine:,}",
                 "",
                 f"  auto-resolved : {resolved:,} "
                 f"({resolved/genuine*100:.1f}% of genuine)" if genuine else "",
                 f"  unit rows emitted (after span fan-out) : {emitted:,}",
                 f"  review queue  : {queued:,} "
                 f"({queued/genuine*100:.1f}% of genuine)" if genuine else "",
                 "", "  exclusions by reason (diverted to excluded.tsv):"]
        for rs, k in by_exclusion.most_common():
            lines.append(f"    {rs:20s} {k:,}")
        lines.append("")
        lines.append("  resolved by corpus:")
        for c, k in by_corpus_res.most_common():
            lines.append(f"    {c:10s} {k:,}")
        lines.append("")
        lines.append("  method distribution:")
        for m, k in by_method.most_common():
            lines.append(f"    {m:28s} {k:,}")
        lines.append("")
        lines.append("  top reasons for queueing:")
        for rs, k in by_reason.most_common(15):
            lines.append(f"    {rs:40s} {k:,}")
        o.write("\n".join(l for l in lines if l != "") + "\n")

    print(open("resolve_report.txt").read())
    print("Wrote resolved.tsv, review_queue.tsv, resolve_report.txt")


if __name__ == "__main__":
    main()
