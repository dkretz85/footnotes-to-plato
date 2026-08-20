# Design Handoff — UI Redesign: Three-Viewer Architecture

**Session date:** 2026-08-18 (evening, conceptual design session)
**Scope:** Conceptual/architectural design only. No file changes, no builds, no
mockups yet. Settles the top-level viewer architecture for the expanded corpus
(Plato, Aristotle, Homer, Pindar, Paul — all now live with real data) and the
home page. One question is left deliberately open for Claude Design to explore as
mockups (§5). Nothing in the parser/aggregator/data model was changed tonight.

**Precondition (context):** back-end data work is DONE. All five authors now have
real citation data. This session was about how to *present* it.

---

## TL;DR — what was decided

The project moves to **three viewers**, organized as cells of a 2×2 design grid
(see §1). The grid is the key mental model — it makes the whole architecture
legible and tells you which viewers to build, which to skip, and why.

- **View A** — text-dimension, aggregate grain: works and work-clusters over time,
  for a selectable journal-set. (Existing, largely unchanged.)
- **View B** — text-dimension, fine grain: passages within a given work, for a
  selectable journal-set and period. (Existing, built and working.)
- **View C** — **NEW** — passages within a given work, for **contrasting**
  journal-sets, over a selectable period. The comparison viewer. Passage-level.

**Two corrections from the prior draft of this handoff:**
1. There is **NO existing View C or philosophy-vs-classics comparison viewer**
   anywhere in the current build. It existed in an OLDER version, now gone. View C
   is built fresh — it is not a migration/promotion out of View A. (The prior
   handoff wrongly said the feature was currently folded into View A.)
2. View C is confirmed **passage-level** (contrast how, e.g., philosophy vs
   classics journals cite *Republic* passages differently), with a
   **volume-indication requirement** (see §4).

---

## 1. The design grid (the load-bearing mental model)

Every viewer is a choice on two independent axes:

- **Text grain:** aggregate (works/clusters over time) vs. fine (passages within
  one work)
- **Journal mode:** one selectable set (*describe*) vs. contrasting sets
  (*compare*)

That is a 2×2:

|                          | one journal-set (describe) | contrasting sets (compare) |
|--------------------------|----------------------------|----------------------------|
| **works/clusters over time** | **A**                  | **D** — not a viewer (see §6) |
| **passages within a work**   | **B**                  | **C**                      |

Reading the grid:
- A and B are the **describe** column; C is the **compare** cell of the passage
  row. This is why A/B/C feel like a family — they're cells of one space.
- **B and C are the same row** (same text grain, same passage substrate),
  differing only in journal mode: B asks "where does attention fall," C asks
  "where does attention *diverge*." Same data, orthogonal question. They are NOT
  one viewer — describe and compare want different chrome — but **C is B with the
  journal dimension split in two**, so they should be built on a **shared
  passage-rendering core** with journal mode as the thing that varies. C is
  therefore cheaper than it looks: the passage substrate already exists in B.

---

## 2. The three viewers, precisely stated

- **View A:** text-clusters over time, for variously selectable journal-sets.
- **View B:** attention to passages within a given text, for variously selectable
  journal-sets and periods.
- **View C:** attention to passages within a given text, for **contrasting**
  journal-sets, over selectable periods.

Note the axis/selector asymmetry, made explicit (see §7): **period is an AXIS in
A but a SELECTOR in B and C.** This is a deliberate design choice, not a law, and
it has consequences worth revisiting (§7).

---

## 3. Governing principles (carried from earlier decisions, reaffirmed)

Load-bearing; do not re-litigate without explicit reopening.

- **Authors set DEFAULTS, never walls.** Author selection pre-checks a sensible
  journal-set and (in View C) a default partition. It does NOT partition the data
  model. One shared corpus space with per-author default filter states — NOT five
  instances with escape hatches.
  - Plato / Aristotle → default journals = philosophy ∪ classics
  - Homer / Pindar → default journals = classics
  - Paul → default journals = NT / theology / religious studies
- **Defaults fire on FRESH ARRIVAL ONLY.** Once a user touches the filters, the
  tool stops being opinionated. **Adding an author never mutates an
  already-touched filter/journal state.** Cross-author comparison (e.g. Plato vs
  Paul in classics journals) is just the general case of "defaults are a starting
  position."
- **Soft suggestions, nothing hard-coded.** All groupings/partitions are
  pre-checked defaults and offered groupings a scholar can accept, extend, or
  ignore. Maximal flexibility is the point.
- **Uncertainty-visible.** Interface depth/shape should signal confidence
  (shallow contrasts = sturdy, deep contrasts = speculative). Same commitment as
  View B's trustworthy/uncertain tier banner.

---

## 4. View C specifics

- **Grain: passage-level.** Contrast how two (or more) journal-sets cite the
  passages of a single work — e.g. "philosophy vs classics on the *Republic*."
  This is the novel, distinctive view: nobody has this picture of the literature.
- **Volume indication is REQUIRED.** When contrasting journal-sets, the viewer
  must indicate the **total citation volume of each set being compared**. Without
  it, a divergence is unreadable — a set with 10× the citations will look
  categorically different for reasons of sample size, not reading habits. How to
  show this (normalized rates? absolute counts alongside? a volume bar per set?)
  is part of the Q1 design brief in §5.
- **Build on the View B core.** C = B with the journal dimension split. Shared
  passage-rendering substrate; journal mode is what varies.
- **Partition control is the central UI.** "Choose your partition" is View C's
  main control. Philosophy/classics is one *instance* of that general mechanism,
  not a hardcoded pair. Insider/outsider, confessional-grade, method-vs-method
  are other instances — all the same operation (partition the corpus into
  journal-sets, compare across the partition).

---

## 5. OPEN QUESTION — for Claude Design (mockups)

**Q1 — how View C renders a passage-level contrast between journal-sets, WITH
legible volume indication.** This is the one genuine visual fork and it wants
mockups, not prose. Sub-questions:
- Two overlaid passage maps? A difference/divergence surface? Side-by-side small
  multiples? Something else?
- How is per-set total volume shown so divergences aren't misread as sample-size
  artifacts (normalized rates vs. absolute counts vs. an explicit volume bar per
  set)?
- How does it degrade with 3+ sets (does C support only pairwise, or n-way)?

Recommend taking View C into Claude Design with this as the brief. Everything else
in this document is settled enough for Claude Code to begin in parallel.

**Note on the Paul typology and progressive disclosure:** the two-axis ragged-tree
Paul journal typology (discipline axis: insider/outsider + L2 fourfold;
confession axis: strength-graded + L2 Catholic cluster) is the source of View C's
*partition options* for the Paul instance. It stays **soft** (suggested defaults,
never hard-coded) and is scoped **sturdy-first**: launch View C with **L1-only
partitions** (insider/outsider, confession-grade); defer the L2 ragged trees and
the close-read census as later enrichment. Full typology detail + the two
data-integrity carryovers (split "unclear" into genuine-indeterminate vs.
not-yet-reviewed; make the venue-not-scholar caveat first-class axis-specific copy
on insider/outsider) are in the prior handoff and still stand. Progressive
disclosure should signal the sturdy/speculative slope visually (not merely
"can't expand") — moot at L1-only launch but the rendering pattern should
anticipate L2.

---

## 6. View D — coherent question, NOT a viewer (deferred as a MODE of A)

D would be the compare-cell of the works row: "work-clusters over time,
contrasting journal-sets" (e.g. does philosophy's attention to the
*Republic*-cluster rise while classics' falls across the decades).

**D is a coherent question but a poorly-legible viewer**, and the reason is worth
recording so it isn't re-derived later: A's natural payload (trends over time)
and the compare operation (two sets contrasted) **compete for the same visual
channel**. A-over-time is already a 2-D read (cluster × year); contrasting two
journal-sets on top of that muddies fast. By contrast, C contrasts sets over a
*static* passage layout (time collapsed to a selectable window), which frees the
visual budget for the comparison. So **B generalizes to C gracefully; A
generalizes to D awkwardly.** The asymmetry is real, not a matter of taste — it's
why there is no symmetric fourth viewer.

**Disposition:** do NOT build D as a fourth viewer. The question it answers is
real and should live as a **deferred MODE inside View A**: "compare two
journal-sets, restricted to ONE selected cluster." Collapsing the cluster axis to
a single cluster buys back the visual channel, so the time × journal-set contrast
renders as a clean 2-line or difference-band chart. Record as a deferred A-mode,
not a launch viewer.

---

## 7. Deferred / off-radar views (recorded so they aren't re-discovered cold)

Explicitly **NOT launch scope.** Captured so future sessions don't rebuild the
thinking from scratch.

1. **"View B-over-time" — the genuinely missing cell.** In the A/B/C scheme,
   **period is an axis in A but a selector in B/C.** That asymmetry hides a real
   view: *one* journal-set's within-a-work attention shifting across periods (the
   history of a single scholarly community's reading of one text), with period as
   an AXIS rather than a selector. Not any of A–D. Cheapest and most clearly
   useful of the deferred items. Decide deliberately whether it's a MODE of B or
   its own surface — and, more generally, decide per-viewer whether period is
   axis-or-selector rather than letting it be inherited silently. **Concrete first
   move on this item is worked out in §8 (analysis-first, then mockups).**
2. **Co-attention / passage correlation.** Not "how much is 509b cited" but
   "which passages get cited *together*" (the sun/line/cave lighting up as a
   unit). A different mathematical object — a passage×passage matrix, not a
   histogram — answering a question none of A–D can: the internal structure of how
   scholars bundle a text. The most intellectually distinctive item here;
   research-grade, later.
3. **Cross-work comparison at passage grain.** All fine views currently hardcode
   ONE work. "Do the *Republic* and the *Gorgias* get read with the same shape of
   attention" is a real comparative-reading question with no cell in the current
   scheme. Niche, deferred.

---

## 8. Temporal passage-attention views — ANALYSIS FIRST, then mockups

Concrete first move on the "View B-over-time" item (§7.1). Prompted by David
sampling the passage viewer across time-scales and seeing **little obvious shift**
in a few works since the 80s (when data gets good) — but rightly unsure whether
there's a real subtle shift the bare eye misses. (Flipping between period
snapshots of two dense passage maps is exactly the comparison human vision is
worst at, so a modest shift *would* hide.)

**Decision: analysis before design.** Do NOT build temporal-view visualizations
against a phenomenon not yet confirmed to exist. Run a data-analysis pass on 2–3
works first; let the result decide which visualizations earn a mockup. This is
verify-as-you-go: the analysis is itself diagnostic — flat distributions are a
*finding* (stability), not a null result, and either outcome is useful.

**Two distinct questions the views serve (different charts):**
- *Does one passage's trajectory rise/fall over time* — the drill-in single-locus
  time-series. The cheap near-term win.
- *Does the SHAPE of attention shift* (different passages hot in different eras,
  holding volume aside) — the harder, more interesting question David was
  eyeballing.

**Stage 1 — data-analysis pass (Claude Code; needs real data + local compute).**
Produce, for 2–3 chosen works:
- a per-work, per-passage, per-time-bin citation table (the raw material for every
  temporal view). Decide binning here — **5-year bins** is the working guess given
  good data from the 80s; the analysis may revise it.
- **share-based** summary measures (NOT raw counts — see the volume caveat below):
  each passage's share-of-work early vs. late, ranked by absolute change, so you
  can see whether the top movers moved *meaningfully* or trivially.
- one crude "did the shape change" figure per work — rank-correlation or total
  variation distance between the early and late passage distributions — so
  stability-vs-reordering is a NUMBER, not a squint. This directly answers David's
  bare-eye question.
- a **sparsity read**: how thin the per-passage-per-bin cells actually get. This
  *calibrates* (does not guess) the floor below which a trajectory is too sparse
  to draw as a confident line. (A rising line built from 3 citations is not a
  trend — uncertainty-visible principle applies to every temporal view.)

The analysis output **IS the mockup dataset** — the same 2–3 works, with real
numbers, go to Claude Design.

**Stage 2 — mockups against that real output (Claude Design), gated on Stage 1.**
Candidate visualizations, to be mocked up only for whatever the analysis shows is
worth showing:
- **Drill-in single-passage time-series** (build first regardless): click a
  passage in View B → a small line/bar chart of citations to THIS locus over time.
  Offer both **absolute count** and **share-of-work**, and overlay the work's total
  volume as a faint background band so "this passage rose" is distinguishable from
  "the whole work rose." Legible because the eye reads a slope far better than two
  heatmaps.
- **Share-based difference map** (the tool for settling the stability question):
  early-period minus late-period on SHARES, so gained-attention passages glow one
  color, lost-attention another, unchanged stay neutral. Most sensitive to small
  shifts (subtracts the baseline the eye must otherwise see past); an all-neutral
  result is strong positive evidence of genuine stability. MUST be on shares/rates,
  not counts, or volume growth lights up everything.
- **Sparkline column** (survey enrichment): top-K passages listed, each with a tiny
  inline trajectory sparkline. Highest info-per-pixel for surveying a whole work.
- **Small-multiples filmstrip** (survey enrichment): same passage map as N period
  thumbnails in a row; all periods simultaneously visible beats a slider for
  *seeing* change. Costs screen space.

**Volume caveat (recurring, same as View C's):** every temporal comparison must be
volume-aware. Raw counts make a set/period with more total citations look
categorically different for sample-size reasons, not reading-habit reasons. Shares
or rates, with volume shown, everywhere.

**Sample choice — the Meno 98 / Gettier case study (hero example).**
Pick works that span the range so the mockups are tested honestly:
- **Meno** — the *hero* sample. We earlier hypothesized a post-Gettier surge at
  **Meno 98** (the "true belief tethered into knowledge" / aitias logismos passage,
  where Socrates distinguishes right opinion from knowledge). This is a genuine
  natural experiment: an a-priori historical reason to expect a shift at a SPECIFIC
  locus after a SPECIFIC date (Gettier 1963, real uptake lagging into the 70s–90s).
  If the signal's there it validates the whole temporal apparatus; if not, that's
  an interesting negative result about whether analytic epistemology cited Plato's
  *text* or just invoked the idea. **Also pull Theaetetus** (final definition:
  knowledge as true belief + logos) — the other obvious home of that literature;
  check whether they move together or Meno alone.
  - **Caveat that makes Meno a GOOD test, not a weak one:** Meno is an
    **uncertain-tier** work (low, flat resolution — bare-floor, not band-flagged).
    A relative-shift-over-time inference is the inference the tier caveat LEAST
    undermines: whatever suppresses absolute resolution is ~constant across years
    and cancels under share-of-work. So Meno demonstrates that an uncertain-tier
    work can still carry a reliable *temporal* finding — but ONLY on **share, not
    counts.** This is exactly why the analysis must be share-based. Meno also tests
    the temporal views on soft-tier data, not just clean high-res works.
- **Nicomachean Ethics** — high-resolution, sharp spikes (1097b ergon argument);
  expected stability or slow drift. Tests the clean case.
- **one mid-volume work** — to span between clean and soft.

---

## 9. Home page redesign

- **All prose hand-written by David from scratch.** Lives in `copy.json` (already
  the convention). Methods page remains David's exclusively.
- **Numbers pull via `{{placeholder}}`** from `meta.json` / viewer data so figures
  self-update on rebuild. Artisanal words, automated figures.
- **Floors-vs-fades illustration:** does NOT scale with the corpus. It's a
  **hand-picked pedagogical vignette** — a few exemplar texts chosen to show the
  floor/band/fade tier model cleanly (e.g. a high-floor heavily-studied work next
  to a low-floor one, one with a visible band). Its job is to teach the reader how
  to read *one bar* before they hit the real viewer, NOT to be comprehensive. At
  80+ texts, letting it try to be the whole corpus would make it a wall; the fix
  is to explicitly not do that.
- **Full 80+ graph gets its own page**, behind a short intro, **per-author
  colour-coded** for legibility.

---

## 10. Journal lists — collapsible groups (all three viewers)

The corpus is now large enough (80+ works, many journals) that a flat checkbox
list is unusable.

- Disciplinary group as a **collapsible header** (Philosophy, Classics,
  NT/Theology, …); individual journals nested inside.
- **Header is a SELECTOR, not a container.** Checking a header adds its members to
  the active set. This matters because journals can be **dual-citizens** (belong
  to more than one group) — a pure tristate "container owns a fixed roster" model
  breaks when the same journal appears under two headers and a toggle in one place
  must reflect in the other. Build header-as-selector from the start.
- Collapsed by default; expand to toggle individual journals. The groups *are* the
  soft suggestion — visually present, every journal still individually reachable.
- The simple grouped-journal control is what all three viewers use for journal
  selection. In View C the partition control sits on top of it (§4).

---

## 11. What did NOT change tonight

- No parser, aggregator, `locus.py`, or data-model changes.
- View B untouched (built, working).
- The data pipeline / roster-union fix / doctype audit from prior handoffs still
  stand as their own separate work items — unaffected by this design session.

---

## 12. Suggested next move

Take **View C** into **Claude Design** with §5 Q1 as the brief (passage-level
contrast rendering + volume indication). In parallel, Claude Code can begin the
settled structural work: the header-as-selector collapsible journal grouping (§10)
shared across all viewers, and scaffolding View C on the View B passage-rendering
core (§1, §4). D stays a deferred A-mode (§6); §7 items are recorded but out of
scope.

Separately and in parallel, the **temporal-views analysis-first pass (§8)** can
start: Claude Code runs the Stage-1 data analysis on Meno (+ Theaetetus), NE, and
one mid-volume work — share-based, 5-year bins, with the "did the shape change"
figure and the sparsity read — and that real output becomes the dataset for the
Stage-2 temporal mockups in Claude Design. The drill-in single-passage time-series
is worth building regardless of what the analysis finds; the difference-map and
survey views are gated on it.
