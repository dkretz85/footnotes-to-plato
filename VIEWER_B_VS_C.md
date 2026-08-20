# Does Viewer C make Viewer B superfluous?

**Question.** Viewer B shows the within-work distribution of scholarly attention
(which passages the literature cites). Viewer C shows that same within-work
distribution *over time*. Does C subsume B?

**Answer. No.** C is the second-order view — *did the distribution move?* — and it
can only exist where a shift is both present and testable. B is the first-order
view — *where does attention sit?* — and it stays the better tool for its question
wherever C can't pay the price of the time axis. The relationship is
complementary, not hierarchical.

Put as a grid, the three viewers are `{across-works, within-work} × {static,
over-time}`. B is the within-work / static cell; C is the within-work / over-time
cell. Neither cell collapses into the other.

---

## Why B survives C

### 1. C is grain-capped by temporal testability; B is not.
To say anything about *change*, C must slice citations into decade bins and clear
sparsity floors (≥15 articles per passage to test a mover, permutation power, and
so on — see `TEMPORAL_FINDINGS_POST_AUDIT`). At line/verse grain that is hopeless
for Homer/Pindar/Paul and thin for much of Plato/Aristotle, so C is forced up to
book/chapter or an aggregated passage band — or it refuses with "too thin to
test." B pools *all* years into each passage at once, so it resolves the footprint
at a far finer grain: the individual Stephanus page+section, the line, the verse.
Meno 98 (the Gettier page) is a bright cell in B; in C, Meno is a whole-work
"stable, well-powered" verdict with no passage map. **B keeps the fine "where"
that C spends to buy the "when."**

### 2. C must stay silent exactly where B is full.
C's governing rule is that it never draws a map whose test did not run. In the
committed data, **165 of 355 verdicts are "stable"** and a large set of
work/grain/journal-set combinations are "too thin to test." For all of those, C's
temporal view is definitionally blank or a flat badge — yet those same works still
have a rich static distribution. If C subsumed B, every steady or thin work would
be a dead end. Steadiness over time does not make the static footprint
uninteresting; often it is the point ("this text has always been read here").

### 3. Different quantity, not just different framing.
C is deliberately volume-invariant: it works in article-incidence **shares**, so
corpus growth cannot masquerade as a passage rising. B reports the absolute
**footprint** (counts, distinct articles). "Most-cited passage overall" (B) and
"passage whose share shifted" (C) are genuinely different measures — a passage can
dominate B yet be flat in C, and a minor passage can be a C mover while being a
rounding error in B. Neither is recoverable from the other.

### 4. B is a finding aid; C is an analysis.
B's core affordance is drill-through: click a passage → the actual articles (DOI,
title, author) → export as a bibliography. That *is* the reason the site exists —
"a finding aid that links out to the articles." C's cells are shares with a
significance story, not clickable article lists. The scholar who wants "the papers
that cite Republic VII" is served only by B. C would have to grow that whole
enumeration/export layer to replace it — at which point B has been rebuilt inside
C, which proves B's function is essential, not superfluous.

### 5. They surface different uncertainties.
B carries the placement/floor honesty at passage level (placed vs. unplaceable,
the fade — "every count is a floor"). C reframes uncertainty as *temporal*
significance (permutation null, FDR, early-bin power). A reader needs both: "how
confident are we this passage is cited here at all" and "how confident are we the
pattern moved."

### 6. Pedagogical ladder.
A reader learns the distribution first (B), then asks whether it changed (C). C
presupposes B's mental model; pulling B out removes the rung C stands on.

---

## The one honest caveat

You *could* bolt a "collapse the decades" toggle plus drill-through onto C so it
technically contains B's row-sums. That would not make B superfluous — it would
make B's job unavoidable, and merging would degrade both tools: C loses the
discipline that makes it trustworthy (it is *about* the shift, and refuses when the
shift cannot be tested), and B loses its fine grain, its count/floor honesty, and
its bibliography drill. So keep their jobs distinct and each stays the best tool
for its question:

> **B is the marginal you can always compute, resolve finely, and drill to
> sources. C is the second-order question that is only sometimes answerable — and
> answerable only at coarser grain.**

The sharper design risk for later is not "does C kill B" but the inverse: making
sure C's map is never *read as* B — a dark cell in a thin early decade misread as
"most-cited." That is exactly why C carries the volume curve above the decade axis
and mutes the early-decade labels. That guard only makes sense because B's
question is a real, separate one that people will try to ask of C.
