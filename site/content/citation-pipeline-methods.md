# Passage-level citation heatmap — pipeline & methods record

*Companion to `ancient-citation-heatmap-handoff.md`. Records the build as
actually executed: the pipeline, every decision, the assumptions tested, the
probes run, and the resulting data quality. Written to be lifted into a methods
section. July 2026.*

---

## 0. Summary of outcome

Starting from a 381 MB gzipped JSONL full-text delivery from JSTOR Text Analysis
Support (69,177 documents, one requested item withheld by JSTOR), we built a
pipeline that extracts candidate ancient-citation strings from article body
text, resolves them to specific works of Plato and Aristotle, and reports
per-work resolution quality.

Final state on the genuine-citation set (after excluding non-scholarly content):

- **141,088** genuine Plato/Aristotle citation candidates
- **90,502 auto-resolved (64.1%)** at high precision
- **50,586** routed to a review queue (characterised, not lost)
- Per-work resolution rates ranging from ~1% (spuria) to ~98% (major works),
  with the corpus "spine" (Republic, Timaeus, the major Aristotle treatises)
  resolving at 90–98%.

Crucially, the pipeline was built **precision-first**: at every stage the
default was to *decline to resolve* rather than guess, and every exclusion
diverts data to an auditable file rather than deleting it. The residual queue is
genuine, quantified ambiguity, not silent error.

---

## 1. The delivered data — what JSTOR actually sent

**Decision point / surprise.** The request was expected to return n-grams (the
handoff planned around trigram/4-gram token counts, with the "riskiest technical
unknown" being whether citation strings survive tokenisation). In fact JSTOR
delivered **full text**, one record per article:

```
{ "iid": "<id>", "full_text": [ "<page 1 text>", "<page 2 text>", … ],
  "references": [ "<raw citation string>", … ] }
```

Consequences, all favourable:
- `full_text` is a **list of page strings** → page-level position is free.
- Citation strings appear **verbatim** in the text (e.g. `PLAT. MEN. 80D5-E5`),
  so the tokenisation-survival risk **evaporated** — there is no tokenisation.
- `references` holds raw *secondary-literature* citations (Diels-Kranz, modern
  editions), not the primary-passage references we want. Reserved for a possible
  future co-citation analysis; **not used** in this build.
- Article-level metadata (journal, year, doctype, **title**) is **not** in the
  delivery; it is joined from the separate JSTOR catalogue metadata file by
  `iid`.

**Probe used:** dumped the keys and structure of the first delivered record
before writing any processing code (schema-probe-first discipline).

---

## 2. Coverage reconciliation

**Assumption tested:** that the delivery matches the request.

- Requested: 69,178 item IDs. Delivered: 69,177. Missing: exactly **1**.
- The single missing item, `ab0e7253-8739-3667-b98e-025ad9fd37f5`, is the item
  JSTOR flagged as un-includable. It is present in both `request_item_ids.txt`
  (line 5607) and `core_item_ids.txt` (line 4922), i.e. it was a **core** item,
  not classics filler — worth noting in the writeup, though at 0.0014% of the
  corpus it is immaterial to any aggregate.
- **No silent drops:** the flagged item is the only omission.

This reconciliation is re-run on every extraction pass (`coverage_report.txt`).

---

## 3. The extraction stage (`build_citation_db.py`)

Streams the delivery, joins metadata, and emits one row per citation-shaped
match to `citations.tsv`. Design decisions:

### 3.1 Citation-shape regexes and the three-way corpus tag

Ancient citations have two systems whose shapes overlap:
- **Bekker** (Aristotle): number + column letter `a`/`b` (+ optional line),
  e.g. `1252a`, `980b25`. Pages run to ~1462.
- **Stephanus** (Plato): number + section letter `a`–`e` (+ optional line),
  e.g. `511d`, `80d5`. Pages run to ~621.

The letter partly disambiguates, so extraction tags each match three ways:
- `bekker` — 4-digit page + `[ab]`: unambiguously Aristotle.
- `stephanus` — 2–3-digit + `[c-e]`: unambiguously Plato (Bekker uses only a/b).
- `ambiguous` — 2–3-digit + `[ab]`: could be either system; deferred to the
  resolver. **~62% of matches** land here — expected, since most Aristotle
  citations end in a/b.

**Two bugs caught and fixed during testing (both by looking at real cases):**
1. Initial regex required 3 leading digits (`\d{3}`), silently dropping all
   sub-100 Stephanus citations (e.g. `80d5`, *Meno*). Widened to `\d{2,3}`.
   Rationale: **under-capture is worse than over-capture** — noise can be
   filtered downstream using context; missed citations cannot be recovered.
2. Initial code hard-assigned `327a`-type overlaps to Bekker via precedence.
   Replaced with the mutually-exclusive three-way tag above, so genuinely
   ambiguous forms are *never* mislabelled — they are explicitly deferred.

### 3.2 Context window and reading-order fields

Each match row carries a **±120-char context window** (newline-flattened),
plus `page_index`, `char_offset`, and a per-article `seq` counter. The latter
three exist to support **scope-tracking** (see §4.4): they preserve reading
order and inter-citation distance in a sort-proof way.

### 3.3 Metadata join and the two engineering hazards

- The metadata file is JSTOR's **full 12.6M-record catalogue**, not the 69k
  roster. Loading it whole caused an **out-of-memory crash** on an 8 GB machine.
  Fix: load only metadata for the requested IDs (pass the roster as a keep-set),
  stopping early once all are found. Reduced the in-RAM index ~180×.
- Bounded-memory throughout: the delivery is streamed one record at a time,
  match rows are written straight to disk (never accumulated), pathological
  pages (>500k chars — scanned-volume records) are scanned in overlapping
  windows, and distinct-article counts are computed in a cheap second pass over
  the finished TSV. A `--resume` path (checkpointed) allows restart after
  interruption.

### 3.4 Title join (added later, see §4.4)

A `title` column is joined from metadata by `iid`, sanitised of tabs/newlines.
Confirmed populated for journal articles (the null titles observed in probing
were JSTOR "contributed_content" community-collection records, not journal
articles).

---

## 4. The resolution stage (`resolve_citations.py`)

Reads `citations.tsv`, applies exclusion filters, then resolves each surviving
candidate through an ordered architecture. Everything is conservative by design:
confidence ≥ threshold *and* no flagged reason ⇒ `resolved.tsv`; else
`review_queue.tsv`; excluded content ⇒ `excluded.tsv`.

### 4.1 Reference tables used

- `stephanus_ranges.json` — 36 dialogues, integer ranges, **independently
  verified**, with per-book sub-ranges for Republic and Laws. Production-grade.
- `bekker_ranges.json` — Aristotle treatise page-ranges. Initially unverified at
  boundaries; **patched during this build** (see §4.5).
- `abbreviation_synonyms.json` — multilingual work-name variants (en/la/fr/de/
  it), with shared/ambiguous forms explicitly flagged "do not resolve on
  abbreviation alone." **Extended during this build** (see §4.5).
- `metaphysics_books.json`, `ethics_books.json` — book-letter offsets
  (e.g. *Metaphysics* Γ = Book IV) and NE/EE common-books double-mapping.

### 4.2 Resolution architecture (precedence order)

For each candidate: compute range candidates (which work(s) contain the page);
then resolve by, in order of authority —
1. **Unique range** — one candidate ⇒ accept. A *mentioned* work-name elsewhere
   in the context does **not** override a unique range (see §4.3, bug 1).
2. **Range + name** — several candidates, context names exactly one ⇒ accept.
3. **Cross-system resolution** — an `ambiguous` number whose candidates span
   both Bekker and Stephanus, disambiguated by an adjacent name ⇒ accept, tagged
   `cross_system_resolved_by_name`.
4. **Scope inheritance** — a bare number inherits the last-named work in reading
   order, confidence decaying with distance, accepted only if the page falls in
   that work's range.
5. **Title prior** — a bare in-range number in an article *titled* after a work
   resolves to that work, if the title uniquely intersects the range candidates.
6. Otherwise ⇒ review queue, tagged with the specific ambiguity.

### 4.3 Bugs caught by inspecting resolved/queued samples

The resolution logic was corrected **three times**, each prompted by reading
actual rows rather than aggregate counts:

1. **Mentioned-vs-cited (the biggest recall bug).** A unique 4-digit Bekker
   number (e.g. *Politics* `1254b`) was being queued at low confidence whenever
   another work was *mentioned* nearby — e.g. Aristotle discussing Plato's
   *Republic*. But a mentioned work is not the cited work; a globally-unique
   Bekker page is authoritative regardless. Fixed: unique range wins; a
   non-matching name is recorded (`range_unique_name_mentioned`) but never
   blocks resolution. Recovered ~7k outright and cut heavily into ~37k more.
2. **Cross-system mislabelling.** `184a`/`100a`-type numbers are ambiguous
   across *pagination systems* (Aristotle Bekker vs a Plato Stephanus page), not
   merely across Bekker treatise boundaries. Reworked so "which system" and
   "which work within a system" are separate axes; auto-accept only when a name
   collapses the full cross-system candidate set to one.
3. **Scope threshold + a contaminant.** Sub-threshold scope hits were mostly
   correct (validated by sampling), but included a contaminating pattern
   (`12.25e` = Polybius book.section, not Stephanus). Added a `book_section_ref`
   filter, *then* lowered the scope-accept gate — the two together, since
   lowering alone would have admitted the contaminant.

### 4.4 Scope-tracking and the title prior

- **Scope-tracking** carries the last-named work forward so bare numbers inherit
  it, with confidence decaying by page/char distance and rejected if the page is
  out of the inherited work's range. Requires the reading-order fields from
  §3.2.
- **Title prior** (added after seeing that short dialogues are cited *bare*
  because the whole article is about them). Precedence is deliberately **below**
  adjacent name and local scope and **above** giving up: an article titled
  "Plato's *Meno*" resolves a bare in-range `72a` to *Meno*, but a nearby "Rep."
  still wins, and an out-of-range number is never forced. Validated on a random
  sample of `title_prior` resolutions: all correct.

### 4.5 Reference-table repairs made during the build

- **Parva Naturalia at 0.0% — dual root cause.** The short biological treatises
  (De Sensu, De Memoria, De Somno, …) resolved at *literally zero*. Investigation
  found **two** causes: (a) they share Bekker pages (De Sensu ends 449a, De
  Memoria starts 449b, etc.), so integer-page lookup never yielded a unique
  candidate; and (b) — the deeper cause — these twelve treatises had **no name
  variants at all** in the abbreviation table, which covered only the 20 major
  works, so they were literally unnameable by context or title.
  - Fix (a): added precise `(page, column, line)` boundaries from **Ross 1931
    (Works of Aristotle, Oxford)**, and taught the resolver to disambiguate
    shared pages by column+line (`449a34` → De Sensu, `449b3` → De Memoria).
  - Fix (b): added multilingual name variants for all twelve missing treatises
    (the Parva Naturalia, plus Magna Moralia and Rhetorica ad Alexandrum).
  - Result: these works moved from 0% to ~40–90%.

  *Boundary line-numbers used (Ross 1931):* De Sensu 436a–449a34; De Memoria
  449b3–453b10; De Somno 453b11–458a33; De Insomniis 458b–462b12; De Divinatione
  per Somnum 462b13–464b18; De Longitudine Vitae 464b19–467b9; De Juventute /
  De Vita et Morte / De Respiratione (one continuous block) 467b10–480b30.

  *Note carried forward:* the added variants are marked `verified: false`
  (standard scholarly forms, not yet cross-checked against a concordance), and
  the remaining Bekker boundaries outside the Parva Naturalia band are still
  unverified — the highest-value future table work.

### 4.6 Book-level faceting — derived and verified (this session)

The four highest-volume works (Republic, Laws, Metaphysics, Nicomachean Ethics)
are large enough that a single passage axis is unreadable; the interface will
facet them **by book** (Rep. I–X, Metaphysics Α–Ν, etc.). This required a
`book` value per citation, and surfaced two things:

- **The `book` column shipped empty.** The resolver never populated it. Rather
  than re-run resolution, book is **derived at load time from the citation page**
  — the book structure is fully recoverable from the Stephanus/Bekker locus. This
  keeps book-assignment an auditable, swappable layer rather than baking it into
  the raw rows. Loader: `derive_book.py` → `resolved_with_books.tsv`.
- **`page_index` (col 5) is the article's internal scan index, not the citation
  page.** The Stephanus/Bekker page must be parsed from the `match` column
  (col 7): `80D5` → 80, `1094a1` → 1094. (The profiling scripts already did this
  correctly via regex; the first book-loader read the wrong column and assigned
  0%, which the audit caught immediately. All page-based interface logic must key
  off `match`, not `page_index`.)

**Boundaries are verified, not heuristic.** Exact book-opening loci were looked
up against Burnet (Stephanus) and Bekker and inlined as deterministic split
points. Each book spans `[its opening locus, the next book's opening locus)`;
a citation's `(page, section, line)` key selects the containing interval.
Mid-page openings are handled exactly — Metaphysics little-alpha at 993a30
(so 993a29 → Α, 993a30 → α), NE II at 1103a15 (1103a14 → I, 1103a15 → II).
Result: **100.0% of 35,968 faceted-work citations assigned, 0 unassigned.**

Three sub-problems worth recording:
- **Metaphysics is labelled by Greek letter** (Α, α, Β, Γ…), matching how it is
  cited, with the little-alpha = Book II offset handled explicitly. A number is
  available in a tooltip.
- **NE/EE common books.** NE V/VI/VII are textually EE IV/V/VI (Bekker
  ~1129–1155, transmitted once, cited under either name). They are marked with a
  `*` suffix so the interface can **fold** them by default and offer a **split**
  toggle showing the NE-vs-EE labelling — itself a reception-history datum.
  2,206 citations fall in these common books.
- **EE's interleaved pagination.** EE's own text runs 1214–1249 but the common
  books sit inside NE's 1129–1155, so a naïve page-sorted interval let the last
  common book absorb the 1155–1214 gap. Fixed by building intervals per
  contiguous page-run and capping the common-book run at NE VIII's opening
  (1155a3). Verified by unit tests covering every boundary case.

**This retires a limitation.** Book-boundary assignment for these four works was
previously flagged as unverified; it is now verified against Burnet/Bekker and no
longer needs a caveat. (The *other* Bekker treatise boundaries — §4.5, §9 — remain
unverified; this session verified only the four faceted works' internal book
divisions.)

A handful of edge citations (bare opening-page references like NE `1094a`, and
the genuinely line-ambiguous case of a bare `1103a` where a new book opens
mid-section) are assigned deterministically to the book owning the top of the
cited section, and are rare enough to footnote rather than agonise over.

---

## 5. Exclusion filters — what was removed and why

All exclusions **divert to `excluded.tsv` with a reason**, never delete. Filters
were added one at a time, each justified by inspecting real false positives.

| Reason | Count | What it catches | Justification |
|---|---|---|---|
| `excluded_doctype` | 54,409 | `misc` + non-content back-matter | Scope decision — see §5.1 |
| `modern_year` | 4,762 | number ≥ 1463 | Above Bekker's ceiling (~1462); can only be a publication year |
| `book_section_ref` | 4,227 | `12.25e`-type refs (leading `N.`) | Book.chapter reference to another author (e.g. Polybius) |
| `foreign_text` | 1,070 | `Aj. 134a`, `Od. 2.107a`, etc. | Adjacent marker names a non-Plato/Aristotle text |
| `dk_fragment` | 190 | number + `DK`/`D-K`/`Diels` | Diels-Kranz Presocratic fragment, not a passage citation |

Total excluded: **64,658 (31.4% of raw candidates).**

### 5.1 The doctype decision (the largest single exclusion)

**This was the most consequential methodological call, and it was made on
evidence, not assumption.** `misc` doctype was 26.6% of raw candidates — too
large to exclude or keep blindly. A dedicated probe (`probe_misc.py`) found:

- **77% of `misc` is index-like**; the random sample showed it is overwhelmingly
  **back-of-volume subject indices** ("Rep. 344e: 213" = *discussed on p.213*),
  not scholarly citations.
- **94% of `misc` is from a single journal** (The Classical Review) and **83% is
  pre-1910** — i.e. one journal's old annual indices and notices.
- By contrast, **`book-review` is 89% substantive prose** (reviewers discussing
  passages), spread across all decades and journals.

Decision: **exclude `misc` and non-content back-matter; keep `research-article`,
`book-review`, and `discussion`.** Framed as a *scope* decision (indices record
locators, not scholarly citations), which also removes the index-page
contamination cleanly — replacing an earlier, fragile density/count heuristic
that **testing showed could not separate real dense footnotes from index pages**
(both scored ~0.45–0.53 numeric density). A key lesson: the discriminator was
**doctype**, not any within-text signal.

### 5.2 Reserved for future use

The `dk_fragment` exclusions are a **ready-made Diels-Kranz dataset** for a
possible future Presocratics heatmap. `excluded.tsv` filtered by reason keeps
each class recoverable.

---

## 6. Data quality — what the resolution rates mean

**A resolution rate is not an accuracy figure.** "Phaedrus 61%" means 61% of
*candidate* Phaedrus citations were confidently assigned to Phaedrus; the other
39% are **unassigned** (queued), not misassigned. The resolved set is clean but
incomplete. Two distinct distortions follow, and both were measured
(`missingness.py`):

### 6.1 Within-work distortion (which passages get attention)

A citation is unresolved mainly when it is **bare and on a page that collides**
with another work's range. So the risk is that passages on colliding pages are
under-represented relative to passages on clean pages. Measured per work as the
gap between a page-band's resolved-share and the work's average rate.

**This session produced the exhaustive band table** (see §6.4 for the method
change and the full result; the machine-readable output is `collision_bands.json`).
The earlier "~8 bands" figure was an artifact of a diagnostic that reported only
each work's *single worst* band; re-run to report **every** band above threshold,
the true set is **21 bands across 12 works**. Headline shape:

- **47 of 59 measured works have NO flagged band** — within-work heatmap shape
  trustworthy end to end. Includes the entire high-volume spine (Republic,
  Metaphysics, Nicomachean Ethics, Timaeus, Theaetetus, Physics, Politics,
  Sophist, etc.).
- **12 works carry one or more localised under-resolved bands.** Laws is the
  extreme case with **7** contiguous bands across Books IX–XII (Stephanus
  860–959); Phaedo's 60–69 band is the highest-impact single band (~667
  estimated-missing citations); Phaedrus 250–259 and 260–269 are the predicted
  cross-system collision zones. In every case the *rest* of the work is clean;
  only the flagged bands need a cell-level caveat.

**Correction to an earlier characterisation.** A prior draft listed Meno 100–109
and Apology 10–19 among the collision bands. The exhaustive re-run shows this is
wrong: Meno, Apology, Crito, Charmides, Lysis, Categories and the other
low-resolution short dialogues are **uniformly** hard, not locally collided —
their missingness is spread evenly across their whole span, so no single band
stands out. Their uncertainty is a *cross-work* (§6.2) phenomenon (wide
floor/ceiling bar), **not** a *within-work* one. See §6.4 — this distinction is
the single most important empirical finding of the visualisation-design stage.

### 6.2 Cross-work distortion (relative weight of works) — bound, not point-estimated

Raw resolved counts are **not comparable across works**, because resolvability
varies (Republic 95%, Meno 26%). Plotting raw counts systematically understates
the short, collision-prone dialogues.

**Correction on the framing (revised this session).** An earlier version of this
record proposed dividing resolved count by resolution rate to get an "estimated
true count" (`est_true`). That formula collapses to a no-op: since
`rate = resolved / (resolved + queued)`, the quotient `resolved / rate` is
identically `resolved + queued` — i.e. it just recovers the **candidate total**.
The queue *is* the missing citations; there is no separate model to fit. The
honest object is therefore not a point estimate but a **range**:

- **Floor** = `resolved` (citations we confidently placed).
- **Ceiling** = `resolved + queued` (every candidate, if all queued ones were
  really this work).

The truth lies between, and the *width* of the interval is the uncertainty. This
is both more correct and more legible than an error bar derived from the rate:
the interface should render each work as a **floor-to-ceiling bar**, where a
tight bar means the count is solid and a wide bar means genuine uncertainty about
how studied the work is.

The widths are dramatic and carry the finding. Examples (resolved → total):
Republic 12,350 → 12,997 (essentially certain); Timaeus 3,977 → 4,198 (tight);
but Apology 1,738 → 6,822, Meno 1,575 → 6,156, Crito 637 → 3,261, Categories
122 → 1,389. On raw counts Apology (1,738) ranks below Timaeus (3,977); on the
ceiling it outranks it. That inversion is exactly the distortion this section
warns about, made visible by the bar width rather than hidden behind a single
number.

Note this is the **cross-work** uncertainty axis (how much a work is studied
*in total*). It is distinct from, and must not be conflated with, the
**within-work** collision-band axis of §6.1 (which *passages* are under-counted).
The two are empirically different populations of works — see §6.4.

### 6.3 What the heatmap can claim (three products)

1. **Resolved-count heatmap** — "at least this much attention." Rock-solid
   everywhere; a floor.
2. **Rate-corrected heatmap** (`est_true`) — honest cross-work comparison. Valid
   for ~45 works; caveated for the localised-gap works and the spuria.
3. **Within-work passage heatmaps** — trustworthy for Tier A; footnoted on
   specific collision-bands for Tier B.

The handoff's original caveat still stands and should be repeated: raw frequency
conflates the contested passage, the boilerplate-cited passage, and the
translation crux; a blank cell may mean "understudied" or "settled." A
raw-vs-normalised toggle remains advisable.

### 6.4 Two uncertainty axes — the key design finding

The visualisation-design stage established, on evidence, that uncertainty in this
dataset is **two structurally different phenomena**, and that a single
uncertainty treatment would misdescribe both. The exhaustive band re-run
(§6.1) partly *overturned* the prior expectation and made the distinction sharp:

- **Uniformly-hard works (cross-work axis).** The low-resolution short dialogues
  — Apology (25%), Meno (26%), Crito (20%), Lysis (25%), Charmides (25%),
  Categories (9%) — are cited *bare* across their whole text ("as Socrates argues
  in the *Meno*"), so missingness is spread evenly and **no band stands out**.
  These works flag **zero** collision bands yet have the *widest* floor/ceiling
  intervals. Their uncertainty is about **how much the work is studied in total**,
  and it belongs in the **text-level floor/ceiling bar** (§6.2), not in passage
  shading.
- **Locally-collided works (within-work axis).** The band-flagged works are
  mostly *high*-resolution overall — Laws (85%), Republic (95%), Parmenides
  (81%), Philebus (76%), Phaedo (56%) — with sharp local drops where their pages
  collide with another work's range. Their uncertainty is about **which passages
  are under-counted**, and it belongs in **within-work band shading** (§6.1), not
  in the text-level bar.

The prediction going in was the opposite (that the low-rate short dialogues would
be the band-flagged ones). The data refuted it, and the refutation *is* the
design rationale: shading a uniformly-hard work's whole span would be wrong (it
is thin everywhere, not collided), and leaving Laws IX–XII unshaded would be
wrong (real localised holes in an otherwise reliable text). **The interface must
therefore carry both treatments and keep them visually distinct** — a
floor/ceiling bar per work at the text level, and named band shading per passage
within a work.

### 6.5 Page-range integrity audit (this session)

To confirm no mis-parsed page numbers were silently inflating any band, every
resolved citation was checked against its work's known Stephanus/Bekker span
(`audit_page_ranges.py`). Result: **3 out-of-range citations in 90,502
(0.003%)** — all three in *De Juventute*, and all three attributable to
adjacent-work Bekker citations bleeding in from the tightly-packed Parva
Naturalia cluster (e.g. a `Metaph. 1067a6` marker, or a neighbouring treatise's
page). No systematic page-parse leakage anywhere in the corpus. This is a
publishable integrity result: it can be stated plainly that a full range audit
found out-of-range parsing in 0.003% of citations, all from known adjacent-work
collisions.

*(One cosmetic note carried to the build: `missingness.py` flags a Republic
"60–69" band of 39 citations. Since the range audit shows **zero** Republic
citations parse outside 327–621, these are not out-of-range; the "60–69" label is
a low-volume binning artifact, not a data-integrity problem. Immaterial to
Republic's 95% reliability; note but do not chase.)*

---

## 7. Method discipline (worth stating in the writeup)

Three principles were held throughout, and account for the data quality:

1. **Look before filtering.** Every exclusion filter and threshold was set by
   inspecting real samples (random *and* targeted), never by assumption. Several
   plausible-sounding filters (numeric-density for index pages; aggressive
   citation-count cutoffs) were **rejected after measurement** showed they would
   remove genuine data.
2. **Precision over recall; decline over guess.** Ambiguous cases are deferred
   to the review queue, never force-resolved. The 64.1% is a *trustworthy* floor,
   not a ceiling reached by relaxing correctness.
3. **Divert, don't delete.** Every excluded row is retained with a reason, so
   every decision is auditable and reversible, and by-products (Diels-Kranz) are
   preserved for reuse.

---

## 8. Pipeline artifacts (file inventory)

**Scripts (in run order):**
- `build_citation_db.py` — extract candidates from delivery + metadata join →
  `citations.tsv`, `citation_summary.tsv`, `coverage_report.txt`.
- `resolve_citations.py` — exclude + resolve → `resolved.tsv`,
  `review_queue.tsv`, `excluded.tsv`, `resolve_report.txt`.
- `work_resolution_rates.py` — per-work resolved/queued/rate → console +
  `work_resolution_rates.tsv`.
- `missingness.py` — within-work missingness → console + `collision_bands.json`
  (analysis; not part of the core pipeline). **Revised this session** to report
  every band above threshold, not just each work's worst, with a volume guard
  and a machine-readable band table. Note: its own `est_true` column is the
  no-op identity described in §6.2 and should be ignored in favour of the
  floor/ceiling framing.

**Visualisation-stage artifacts (this session):**
- `derive_book.py` — load-time book derivation from the citation locus, with
  verified Burnet/Bekker boundaries → `resolved_with_books.tsv` (the build file).
- `collision_bands.json` — the 21-band caveat set for within-work shading.
- `audit_page_ranges.py` — page-range integrity check (§6.5).
- `profile_resolved.py`, `dump_rates.py`, `check_books.py` — profiling used to
  settle binning grain, journal-checkbox design, and book-column population.

**Diagnostics (throwaway/analysis, kept for reproducibility):**
- `probe_misc.py`, `doctype_breakdown.py`, `measure_density.py`,
  `probe_meta_keys.py`, `probe_titles.py`, `probe_record.py`.

**Reference tables (some repaired this build):**
- `stephanus_ranges.json` (verified), `bekker_ranges.json` (Parva Naturalia
  boundaries added, Ross 1931; rest still unverified), `abbreviation_synonyms.json`
  (12 treatises' variants added), `metaphysics_books.json`, `ethics_books.json`.

**Key intermediate/outputs:**
- `citations.tsv` (all candidates), `resolved.tsv`, `review_queue.tsv`,
  `excluded.tsv`, plus the summary/report files above.

---

## 9. Known limitations & the honest to-do list

- **Bekker *treatise* boundaries outside the Parva Naturalia are unverified** —
  the largest remaining table-quality item. Impact is confined to citations
  landing exactly on shared pages. *(Note: the internal *book* divisions of the
  four faceted works — Republic, Laws, Metaphysics, NE — were verified this
  session, §4.6, and are no longer part of this caveat.)*
- **Added abbreviation variants are `verified: false`** — standard forms, not yet
  concordance-checked.
- **The 21 localised-collision bands across 12 works** (§6.1, §6.4;
  `collision_bands.json`) need cell-level shading in any within-work
  visualisation. The band set is a responsible *floor*, not a completeness proof:
  absence of a flag means no band-level pattern above threshold, not certainty.
- **The review queue (~50.5k)** is genuine ambiguity: bare numbers with no name,
  scope, or title signal. A future richer model or a manual pass could recover
  some; it should not be force-resolved by heuristic.
- **`references` field unused** — reserved for a future secondary-literature
  co-citation analysis.
- **Spuria** (Alcibiades 2, Hipparchus, Clitophon, etc.) resolve poorly and are
  marginal to most attention narratives; treat separately.

---

*End of methods record. Visualiser **design** is now settled (see the handoff
memo's "Interface design — settled" section); the build files
(`resolved_with_books.tsv`, `collision_bands.json`) exist and are verified. Next
stage: build the interface (new working session).*
