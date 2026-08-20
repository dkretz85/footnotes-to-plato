# Temporal Passage-Attention — Findings & Design Brief

**For:** Claude Design (temporal-view mockups), and the record.
**From:** the Stage-1 analysis (UI handoff §8), run on real data via `temporal_analysis.py`.
**Status:** analysis complete. The temporal views are earned; this doc says *which*,
*at what grain*, *with what controls*, and *with what honesty*.

---

## 0. TL;DR

Attention to a work's passages **does** shift over time for many texts — but the
change is usually **diffuse** (many passages nudging), rarely carried by a few
"hero" passages, and its **legible grain and even its direction depend on two
controls**: the analysis grain (passage vs book/chapter) and the journal-set.
Four design consequences:

1. **Grain is a user control**, not a fixed choice. Some works reshuffle *between*
   books (Republic, Metaphysics, Paul), others only *within* books at passage grain
   (Nic. Ethics), others not at all. For `book.line`/`chapter:verse` corpora
   (Homer, Pindar, Paul) the passage grain is too sparse temporally — book/chapter
   grain is the default.
2. **The journal-set is load-bearing** — it can *reverse* the finding (Republic
   Book VIII *falls* across all journals but *rises* within philosophy). "All
   journals" must never masquerade as "the field's reading."
3. **Every claim needs its uncertainty shown**: a whole-work verdict
   (reshuffled / stable / too-sparse) against a permutation null, and per-unit
   movers gated by FDR + a minimum-count floor. Most individual "stories" are noise
   until corrected.
4. **Units live at levels (0 cluster / 1 text / 2 book-chapter / 3 line-verse), and
   a level can be empty.** Viewer placement follows the level, not the file: View A
   traces levels 0–1 (clusters, texts), the sub-text difference-map traces levels
   2–3. Pindar's ode is a level-1 **text** (→ View A, ode-book as cluster color) and
   Pindar has **no level 2 at all**, so it is absent from the sub-text map — see
   §4, §6.

**Hero example for the difference-map: Paul / the New Perspective** (§5).

---

## 1. Method (how a claim is made honest)

Input: the deduped `dots` in `viewer_data/view_b/<work>.json` (each = one article's
citation to a passage, with its year). All measures are **article-incidence
shares** (volume-invariant) and use **distinct articles** (so "3 citations from one
article" is never a trend).

- **Whole-work verdict.** Split citations early/late (median year, or a chosen
  date). Compare the early vs late passage-share distributions by Spearman ρ and
  total-variation distance, each against a **permutation null** (shuffle which
  citations are "late," recompute 200×). Verdict: **REAL** (TVD z≥3), **marginal**
  (1.5–3), or **stability finding** (<1.5 — a positive result, not a null).
- **Individual movers.** Per-passage permutation p-value (departure from random
  temporal allocation, size-aware), then **Benjamini–Hochberg FDR** across passages
  (raw p<0.05 on hundreds of passages buys ~5%×N false positives), **and** a
  **min-articles floor** (default 15 — below it the exact permutation + FDR is
  anti-conservative on tiny counts and waves through `5→0` coin-flips). A mover is
  a real story only if it survives FDR **and** the floor.
- **Controls:** `--journals <group|list>` (composition vs within-community),
  `--grain passage|book`, `--split-year <Y>` (test a dated hypothesis),
  `--min-articles`.
- **Second-pass guards (audit B1–B6), all now emitted per §8):** an **early-bin
  floor** so an FDR mover on a thin early base can't render as a bright arrow
  (`floor_fail_early`); a **within-shelf control** separating cluster-block from
  genuine text-level movement (`survives_within_shelf`); the **full per-unit raw
  early/late counts** so a share-drop isn't misread as an absolute drop (`units[]`);
  a **≥3-period structure test** so a rose-then-fell trajectory isn't called stable
  (`multibin_structure`, `two_bin_flat_only`); a **stability-power floor** so an
  under-powered null is reported as too-sparse-to-tell, not stability
  (`stability_powered`); and a **near-threshold flag** marking which verdicts to
  re-run at higher permutation count (`near_threshold`).

Every guard is load-bearing: without the null we'd have called ρ=0.6 a shift;
without FDR+floor we'd have reported dozens of coin-flips as passage-stories;
without the second-pass guards a thin-early arrow, a block-carried ode, a
share-vs-absolute confusion, a non-monotonic "stable," or an under-powered null
could each have reached the mockups as a claim it can't support.

---

## 2. The verdict table (whole-work shape change)

REAL = the reading reshuffled beyond sampling noise. All values are the TVD z
(vs the work's own permutation null).

| work | grain | all journals | philosophy only |
|---|---|---|---|
| Metaphysics | passage | REAL +7.6 | REAL +8.0 |
| Metaphysics | book | REAL +4.2 (Α,Μ ↓; α ↑) | stable +0.4 |
| Nic. Ethics | passage | REAL +4.7 | REAL +4.3 |
| Nic. Ethics | book | **stable −0.8** (intra-book) | marginal +2.5 |
| Republic | book | REAL +5.6 (VIII,IX ↓; III,VI,VII ↑) | REAL +5.4 (**VIII,IX,X ↑; VI,I ↓**) |
| Eudemian Ethics | book | stable +0.9 | REAL +4.6 (I ↓; II ↑) |
| Theaetetus | passage | REAL +3.2 | REAL +3.7 (diffuse) |
| De Anima | passage | marginal +2.6, **mb +4.3** (2-bin under-reads; 433a↑ active intellect) | REAL +3.3 (diffuse) |
| Laws | book | marginal +1.6 | stable −0.2 |
| Laws | passage | marginal +1.9, **mb +5.0** (2-bin under-reads; diffuse) | — |
| **Romans** | book | REAL +6.1 | — |
| **Galatians** | book | REAL +5.2 | — |
| **Iliad** | book | REAL +25.2 (Bk 1/proem ↓; battle bks 5,13,16 ↑) | — |
| **Odyssey** | book | REAL +12.3 (Book 11 ↑) | — |
| **Pindar (pooled odes)** | ode = **level-1 text** (View A) | REAL +26.7 (Olympian *cluster* ↑; genuine ode movers O.5,O.6,P.1,P.6,P.11,N.1,N.2 — §6, B2) | — |
| Timaeus | passage | **non-monotonic** — stable +0.3 at 2-bin but **mb +4.1** (structure the split hides) | — |
| **Gorgias** | passage | **stable, well-powered** −0.5 (mb −0.5 — genuinely flat) | — |
| **Meno** | passage | **stable, well-powered** +0.8 (mb −0.4 — genuinely flat) | — |

---

## 3. The four temporal patterns (each needs its own presentation)

1. **Between-book reshuffle** — legible, FDR-solid book movers. Republic,
   Metaphysics (all-journals), Eudemian Ethics (philosophy), Romans, Galatians,
   Iliad, Odyssey. → **book/chapter difference-map, crisp.** Pindar is the
   between-*text* / between-*cluster* analog and lives in **View A**, not the
   sub-text difference-map (each ode a level-1 text, ode-book a cluster) — see §6.
2. **Intra-book / diffuse** — whole-work REAL but no single passage or book
   survives FDR; the drift is a broad rearrangement. Nic. Ethics, Theaetetus,
   De Anima, Metaphysics-within-philosophy. → **passage difference-map as a
   *gestalt*** (no hero cells), or "reshuffled, diffusely."
3. **Stable (genuinely flat)** — unchanged at two bins *and* across ≥3 periods,
   well-powered. **Gorgias** (mb z −0.5), **Meno** (mb z −0.4), NE-at-book-grain. →
   **a dignified stability badge** (a real finding, not an empty chart).
4. **Non-monotonic / two-bin-under-read** — flat-or-weak at two bins but real ≥3-period
   structure (`two_bin_flat_only` / `two_bin_understates`): the shape *did* move, just
   not as a clean early→late drift. **Timaeus** (stable +0.3 but mb z **+3.9**),
   **Laws** (marginal +1.9, mb **+5.2**), **De Anima** (marginal +2.6, mb **+4.7**). →
   **show the multi-period trajectory, never a stability badge.** This is the state the
   audit's B4 test exists to catch — Timaeus was mistaken for a stability exemplar
   until the ≥3-period test flagged it. **Whether that structure is hero-carried or
   diffuse is a separate axis — see §3a.**

### 3a. Is the structure hero-carried or diffuse? (the Viewer-C question)

The two-bin mover test is blind to rose-then-fell passages, so a structured work's
"0 FDR movers" says nothing about whether its ≥3-period structure sits on a few named
passages or is spread thin. Decomposing the ≥3-period dispersion **by passage** (each
passage's contribution, permutation-tested and FDR'd, plus a concentration read —
`multibin_movers` + `multibin_structure.concentration`) settles it. Run on the
structured works plus two calibration contrasts:

| work | 2-bin | mb z | **shape** | FDR heroes | top-5 share | passages→50% |
|---|---|---|---|---|---|---|
| **De Anima** | marginal | +4.7 | **BOTH** (hero + tail) | **3** (404a,431b,405a) | **21%** | 16 / 57 |
| Timaeus | stable | +3.9 | **DIFFUSE** | 0 | 5% | 82 / 279 |
| Laws | marginal | +5.2 | **DIFFUSE** | 0 | 2% | 194 / 625 |
| Theaetetus | REAL | +4.7 | **DIFFUSE** | 0 | 10% | 36 / 123 |
| Republic (passage) | REAL | +5.8 | **DIFFUSE** | 0 | 2% | 293 / 1004 |

Two findings, both load-bearing for Viewer C:

- **Structure is almost always DIFFUSE.** Four of five spread across dozens–hundreds
  of passages with no nameable heroes. The lone hero case, **De Anima**, is the small,
  dense, *topically focused* one (70 passages; its structure sits on the soul-definition
  debates — 404–405 the atomist soul, 429–433 the intellect). Sprawling works dilute.
  So **"non-monotonic / structured" ≠ "a few hero passages"** — Viewer C must default
  the structure layer to a **gestalt**, promoting to named-passage trajectories only
  when the concentration statistic earns it.
- **Concentration is GRAIN-DEPENDENT, exactly as the verdict is.** **Republic is a
  clean hero reshuffle at *book* grain (Books VIII/IX…) but fully diffuse at *passage*
  grain.** A work is not hero-or-diffuse absolutely; it is hero at the grain where its
  movement lives. So the hero/diffuse determination — and whether Viewer C shows named
  cells or a gestalt — must be **recomputed per grain and follow the grain toggle.**

Methodological note: for large works the **FDR-survivor count is conservative** (Republic
FDRs over 1,004 passages vs De Anima's 57), so read the **concentration metric**
(top-k share, passages-to-50%) as the primary hero/diffuse signal and FDR survival as
confirmation. They agree here — De Anima 21% top-5 *and* 3 survivors; all others ≤10%
top-5 *and* zero.

---

## 4. The three load-bearing lessons

**Grain is a control.** The same work tells a different story (or none) at
different grains: NE reshuffles at passage grain but is book-stable (the drift is
*within* books); Republic/Metaphysics move *between* books. There is no single
right grain — the viewer must let the user toggle passage ↔ book/chapter. For
Homer/Pindar (`book.line`) and the verse grain of Paul, per-passage is too sparse
temporally; book/chapter is the default.

**Journal-set can reverse the finding.** Republic Books VIII/IX *fall* across all
journals but *rise* within philosophy (the Rawls-era political-philosophy
engagement with the decline-of-regimes books). A philosopher shown the default
all-journals view would see the **opposite** of their own community's trend. So
the journal-selector is not chrome — it is the difference between "the corpus
changed its mix" and "this community changed its reading." Surface it prominently;
label the composition-vs-within-community distinction.

**Units live at levels, and a level can be empty.** The corpus has a unit ontology,
top to bottom:

- **Level 0 — text-cluster:** ode-books (Olympian/Pythian/Nemean/Isthmian); any
  future corpus grouping.
- **Level 1 — text:** the Iliad, the Odyssey; a Plato dialogue; an Aristotle
  treatise; a Pauline letter; **a single Pindaric ode.**
- **Level 2 — book/chapter:** Republic/Laws/NE/EE/Metaphysics books; Iliad/Odyssey
  books; Paul's chapters.
- **Level 3 — line/verse:** lines (pagan corpora); verses (Paul).

Temporal viewer placement follows the **level**, not the file boundary: **View A**
("attention over time / compare works") traces shifts at **levels 0–1** (clusters
and texts); the **sub-text difference-map** traces **levels 2–3** (books/chapters,
and lines/verses where dense enough).

The trap is treating a level-1 text as a sub-text unit. Pindar's ode-books are
editorial **collections of independent poems**: the ode is a **level-1 text** (peer
of the Iliad), and the ode-book is a **level-0 cluster**, not a work. So the ode is
below its *ode-book*, but a cluster is *above* text — "below the ode-book" and
"below a text" point in opposite directions, and conflating them files the ode as a
passage-analog by mistake. Measured that way you take each ode's share of an
arbitrary denominator and hide the between-cluster shift (see §6 — pooling turned
four soft per-shelf verdicts into one z+26.7 **text-level** reshuffle). And a level
may simply be **absent**: Pindar has **no level 2 at all** — an ode has no
book/chapter subdivision — so Pindar is absent from the sub-text difference-map not
because it is stable or sparse but because the unit does not exist for it. **General
rule: a corpus declares, per level, whether a unit exists; viewer placement follows
the level.** (Mild echo, not a problem: Aristotle's *Metaphysics* and the two
*Ethics* are semi-compiled, but they're cross-referential and read as wholes, so
book grain stays right for them. Pindar is the one corpus here whose "work" is
genuinely just a shelf.)

---

## 5. Hero case — Paul and the New Perspective

The showcase. At **chapter grain, split at 1977** (E.P. Sanders, *Paul and
Palestinian Judaism*), both letters reshuffle REAL and FDR-solid, and the moving
chapters *are* the New Perspective on Paul:

- **Romans** (all FDR-solid at 1977, all early-powered): away from individual
  soteriology — ch **8 ↓** (the largest mover: "no condemnation" / life in the
  Spirit) and ch **6 ↓** (baptismal dying-and-rising) — toward Israel/covenant —
  ch **11 ↑**, ch **10 ↑** (the olive tree, "all Israel will be saved") — and
  ch **16 ↑** (the coworkers: Phoebe, Junia, Prisca — feminist / social-historical
  Paul). *(The earlier "ch 5 ↓" does **not** survive FDR at this grain — dropped;
  ch 16 ↑ is the addition the rigorous run surfaced.)*
- **Galatians** (all FDR-solid, all early-powered): ch **3 ↑** (Abraham, faith,
  "no Jew nor Greek," law-as-pedagogue) and ch **1 ↑** (Paul's *call* — Stendahl's
  "call, not conversion"), away from ch **2 ↓** (the 2:16 justification formula —
  the Reformation prooftext, *declining*) and ch **4 ↓** (the Hagar allegory).

This is exactly the historiographical turn (Sanders → Dunn → Wright) from
"justification as individual guilt/grace" to "covenant membership / Jew–Gentile
inclusion." It is the one place in the whole corpus where a temporal shift is
**strong, dateable, chapter-localizable, and maps onto a paradigm shift every
specialist recognizes** — the hero demonstration that the tool detects real
intellectual history. Pair it with the `--split-year` control (the shift is best
seen at 1977, not the median).

Caveat, and the guard for it (audit B1) — **checked and cleared.** The corpus is
heavily post-1977, so the pre-1977 base is thin, exactly the small-count regime the
mover floor exists to reject. The 1977 book-grain run reports the **pre-1977 (early)
distinct-article count** for every featured chapter, and **all of them clear the
floor**: Romans 33–193 early articles per featured chapter (ch 8: 193→482, ch 11:
43→275, ch 16: 37→243, ch 10: 33→205, ch 6: 74→232), Galatians 89–138 (ch 3:
135→680, ch 1: 89→440, ch 2: 138→501, ch 4: 127→427). **No featured arrow is
`floor_fail_early`** — every one is FDR-solid *and* early-powered
(`n_fdr_movers_solid` = the full set). So the hero difference-map may render these as
bright arrows in good conscience. The New Perspective direction is *known*, so a
matching arrow *feels* confirmed — but here the pre-1977 n is stated and it holds up
on its own; the external validation is corroboration, not the load-bearing evidence.

---

## 6. Homer (book grain) & Pindar (ode = text, View A)

Line grain is temporally hopeless for `book.line` corpora (Iliad, Odyssey, and all
four Pindar ode-groups: near-zero passages clear the ≥15-article floor, 0 FDR
movers anywhere). **Book/ode grain is the only viable temporal grain** and gives
strong, FDR-solid movers. This rule is now validated on two independent corpora.

**Homer.** Both epics reshuffle REAL at book grain.
- **Odyssey** — the clean single-mover exemplar: Book **11 ↑** (the Nekyia; z+12.3).
- **Iliad** — the migration exemplar (z+25.2): attention moved **off Book 1** (the
  proem + opening quarrel; also Bk 9, the embassy) and **onto the central battle
  narrative** — Bk **5** (Diomedes; medYr 2014), Bks **11/13/16** (the Patrocleia)
  — and the closing books. The recognizable turn toward narratological /
  battle-narrative Homer.

**Iliad flag — RESOLVED (was: possible artifact).** The §6 worry that the 2009
median and the Book 1 "collapse" were a date/OCR artifact does not hold up. The
`diagnose_homer.py` check shows: (a) the proem lines are each carried by **8–21
distinct journals** — real broad citation, not a 1–2-journal false-match magnet;
(b) **no batch duplication** — the worst `(journal,year,line)` multiplicity is ×6,
from *1888*; (c) the proem's decline is **genuine and old** — its own citation
medians are 1912–1969 (Book 1 is the most-cited *and* earliest-cited book), while
the recent median reflects a real, broadly-sourced Iliad surge landing in the
battle books. The Iliad is a featureable reshuffle, not a suppressed one. *One
honest footnote:* the proem's early prominence partly reflects older citation
*convention* (quoting the famous opening) as much as sustained interpretation — a
reception-history nuance, not a data defect.

**Pindar is a level-1 (text-level) shift — a View A result, not a sub-text one.**
Pindar's four "works" — Olympian, Pythian, Nemean, Isthmian — are editorial
**collections of independent poems** (level-0 clusters). Each ode is a complete
level-1 **text**, peer of the Iliad; no ode presupposes another; the ode-book is an
Alexandrian shelf, conventional and to a degree arbitrary. So Pindar's temporal
result belongs in **View A**, with the **ode as the text** and the **ode-book as
the level-0 cluster color** — and Pindar is **absent from the sub-text
difference-map entirely**, because it has **no level 2** (an ode has no
book/chapter). Not stable, not sparse — the unit simply does not exist for it.

Running each ode-book as its own "work" (the first pass) was a level error: it
measured each ode's share of an **arbitrary cluster denominator** and fragmented
~1,190 articles into four thin subsets, giving soft per-shelf verdicts
(Olympian/Nemean marginal, Pythian/Isthmian weak-REAL). **Pooling all four shelves
into one Pindar corpus with the ode as the level-1 unit** (`--pool Pindar`, one
corpus-wide denominator, 46 ode-units) changes the picture completely: a **huge**
text-level reshuffle — TVD z **+26.7**, Spearman z **−48.5**, **26 of 40** testable
odes surviving FDR. The between-*cluster* movement the per-shelf runs structurally
could not see is the headline: the **Olympian cluster rises as a block** while the
other clusters fall (P.4, N.3, N.7, I.8 ↓).

**Cluster-block vs genuine ode-level movement (within-shelf control, B2).** The
pooled mover list is entangled with a **cluster-level recency difference** (per-shelf
median split years: Olympian **2013**, Pythian 2000, Nemean 1998, Isthmian 1993), so
`--pool` now runs a **within-shelf control**: each ode-book re-analysed at ode grain,
where a uniform cluster-wide recency shift cancels (shelf-internal shares), so only
an ode moving *relative to its shelf-mates* survives. The result cleanly separates
two real things at two levels (**verified on the real corpus**: of the pooled
top-10 movers, *only* O.6 carries the `§ survives_within_shelf` flag — every other
headline mover is `·` block-carried):
- **Cluster block (level 0):** the Olympians as a whole (O.1, O.2, O.7, O.10, O.13
  ↑) rise because their *cluster* rose — these are **block-carried** (`·`), do **not**
  survive the within-shelf control, and must render as a **cluster movement**, not
  as named-ode arrows.
- **Genuine ode-level movers (level 1, `survives_within_shelf`):** O.5↑, O.6↓; P.1↑,
  P.6↑, P.11↓; N.1↓, N.2↑ — the only odes that move relative to their shelf-mates,
  and the only ones that earn a **named-ode arrow**.
- **Direction gotcha (render the within-shelf delta, not the pooled one):** O.6 is
  the one top-pooled mover that is also genuine ode-level, and it is a **sign flip** —
  pooled it reads **↑** (+0.019, carried up by the Olympian block) but *within its
  shelf* it is **↓** (−0.059: O.6 rose in absolute terms yet **lost ground among the
  Olympians**). A `§` ode's named arrow must use its **within-shelf** delta (from the
  per-shelf JSON), never the pooled delta, or the map will call O.6 a riser when its
  own-cluster trend is down.

That the cluster block is **real reception history, not an artifact**, was confirmed
with the `diagnose_homer.py` check (Olympian vs Nemean): the recency is broad across
all major classics journals, and *within the same journal* Olympians run ~10–20 yr
later than Nemeans (CQ 2013/2005, AJP 2013/1992, HSCP 2011/1993, Classical Antiquity
2013/1996, TAPA 2013/1990); two genuinely different histogram shapes (Nemean peaked
~1985–90 and plateaued, Olympian surged post-2005); no batch/concordance smell. So
the headline stands as a **cluster-level** finding: **Pindaric attention migrated
from the Nemeans/shorter odes toward the Olympian showpieces** — a canon-concentration
effect — with the seven `survives_within_shelf` odes as the genuine ode-level
overlay on top of it.

(Data item — B7, **resolved: there is no stray.** `find_stray_odes.py` shows every
shelf within canonical range — Olympian 1–14, Pythian 1–12, Nemean 1–11, **Isthmian
1–9**. The "46th" is simply **Isthmian 9**, a genuine *fragmentary* ode; "45" was a
miscount that assumed only the 8 complete Isthmians. Not an artifact, nothing to
remove. Lone curiosity, immaterial to every verdict: I.9's five articles are all
2017–2020 — worth a one-line spot-check that they really cite the fragment, no more.)

The settled lessons stand regardless of that caveat: **line grain is hopeless**
across all four shelves (0 FDR movers, near-zero odes clearing the floor), so
**ode/book grain is the only viable temporal grain**; and even a modest corpus
supports an ode-grain view but never a passage one.

---

## 7. Design brief — what the temporal views should be

1. **Verdict-first.** Every temporal view headlines the whole-work verdict
   (reshuffled / stable / too-sparse) with its z — the temporal analog of View B's
   trustworthy/uncertain tier banner. This is the robust layer.
2. **Difference-map, significance-encoded — with an absolute anchor (B3).** Early−late
   share deltas on a static passage/book layout; FDR-solid movers rendered bright, the
   diffuse remainder muted, so the eye can't misread noise as story. But a share can
   fall purely because *others* rose while a unit's own attention is flat or growing —
   a humanities reader reads "ch 8 ↓" as "people stopped citing Romans 8," which may
   be false. So the map needs an **absolute-vs-share toggle**, and every cell carries
   its **raw early/late distinct-article counts** in a tooltip (emitted per unit in
   `units[]`). An all-muted map under a REAL verdict honestly says "reshuffled, but
   diffusely." Default grain = book/chapter where the work is faceted or
   `book.line`/`chapter:verse`. **Only bright-render a mover that is FDR-solid AND not
   `floor_fail_early`** (its early bin must clear the floor — B1); use `n_fdr_movers_solid`.
3. **Grain toggle** (passage ↔ book/chapter) — first-class; the story lives at
   different grains for different works.
4. **Journal-set selector** — first-class and prominent, with the
   composition-vs-within-community framing (it can reverse the finding).
5. **Split-year / "test a date"** control for dateable hypotheses (New Perspective
   1977, Gettier ~1965) — pairs with the difference-map.
6. **Drill-in single-passage/book time-series** — the honest everyday feature for
   any sufficiently-dense unit; overlay the work's total volume as a faint band so
   "this rose" ≠ "everything rose." The verdict is a **two-bin** split, blind to
   rose-then-fell shapes; back it with the **≥3-period structure test** (`multibin_
   structure.z`, B4). A unit/work flat at two bins but structured across ≥3 periods
   carries `two_bin_flat_only` — the drill-in trajectory, not a flat badge, is the
   honest presentation.
7. **Four states, all dignified (B5):** reshuffled (difference-map), **stable —
   well-powered** (a real flat finding; `stability_powered=true`, badge), **too-sparse
   -to-tell** (stable at two-bin but under-powered — `stability_powered=false`;
   aggregate-only, "can't name the passages," e.g. classics-only Metaphysics), and
   **non-monotonic** (`two_bin_flat_only` — show the multi-period trajectory, never a
   stability badge). The badge must not claim "unchanged" from an under-powered or a
   two-bin-flat-only null.
7a. **Non-monotonic structure: gestalt by default, named heroes only when earned
   (§3a).** For a structured work, decompose the ≥3-period dispersion by passage
   (`multibin_movers`, `multibin_structure.concentration`). Structure is **almost
   always diffuse** — Viewer C's structure layer defaults to an **aggregate "the shape
   wandered here" gestalt**, and promotes to **named-passage rose-then-fell
   trajectories** only when the concentration earns it (a few passages survive the
   multi-period FDR *and* top-k carries a real share — the De Anima case, not the
   Timaeus/Laws case). Naming heroes on a diffuse work fabricates them. **And this
   determination is grain-dependent** (Republic: hero at book grain, diffuse at
   passage grain), so recompute it per grain and let the grain toggle drive
   named-cells-vs-gestalt. For large works trust the concentration metric over the
   (conservative) FDR-survivor count.
8. **View A carries the level-0/1 (cluster/text) temporal shifts (B2, §4).** Where the
   comparable text is a level-1 unit inside a level-0 cluster (Pindar: ode inside
   ode-book), the temporal view is **View A** — each ode a text/series, the ode-book a
   cluster color — *not* the sub-text difference-map (Pindar has no level 2). Render
   the **cluster block** movement (Olympians ↑) as a cluster-level mark; give a
   **named-ode arrow only to odes with `survives_within_shelf=true`** — the ones that
   move relative to their shelf-mates once the block recency is partialled out.

Everything is **volume-aware** (shares, not counts) and **uncertainty-visible**
(verdict + FDR + power + multi-period structure), consistent with the tool's standing
commitments.

---

## 8. The dataset for mockups

The `temporal_*.json` files ARE the mockup dataset (real numbers, same works):

- `temporal_<work>.json` — passage grain, all journals.
- `temporal_<work>_<set>.json` — journal-set filtered (e.g. `_philosophy`).
- `temporal_<work>_book.json` / `_<set>_book.json` — book/chapter grain.
- `temporal_Pindar_book.json` — the **pooled** Pindar corpus for **View A**: each ode
  a level-1 text, ode-book as level-0 cluster label `O.`/`P.`/`N.`/`I.`; movers carry
  `survives_within_shelf` (block vs genuine ode-level).

Each carries: `verdict` + `shape_change` (ρ/tvd vs null, z, verdict inputs);
`multibin_structure` (≥3-period dispersion vs null, z — B4, **plus `.concentration`:
`n_structure_movers_fdr`, `top5_share`, `n_passages_to_50pct` — the hero-vs-diffuse
read, §3a**) + `multibin_movers` (per-passage dispersion contribution, p, q,
`significant_fdr` — the passages carrying the ≥3-period structure) + `two_bin_flat_only`;
`stability_powered` + `min_stable_articles` (B5); `sparsity` (drawable counts);
`top_passages` (per-unit `by_bin` trajectories); `top_movers` (delta, p, q,
`significant_fdr`, `floor_fail_early` (B1), `survives_within_shelf`/`within_shelf_q`
(B2)); **`units[]`** — the full per-unit early/late raw-article table + shares (B3);
`focus` trajectories; `n_significant_movers_fdr`, `n_fdr_movers_solid` (FDR-solid AND
early-powered), `n_movers_expected_by_chance`, `movers_min_articles`, `mover_min_early`,
`near_threshold` (B6).

Recommended hero set for mockups: **Romans** (chapter grain, 1977 split — the
difference-map showpiece), **Republic** (book grain, all-journals vs philosophy —
the journal-reversal demo), **Iliad** (book grain — the migration story, Bk 1 →
battle books; the strongest reshuffle), **Odyssey** (book grain — the clean
single-mover `book.line` case), **Pindar (pooled odes)** (`temporal_Pindar_book.json`
— the **View A** level-0/1 case: ode = text, ode-book = cluster color; cluster-block
vs `survives_within_shelf` odes, with the O.6 sign-flip as the render-the-within-shelf
-delta lesson), **Gorgias** (the true stability badge — `stability_powered`, flat at
both 2-bin and ≥3-period), **Timaeus** (the **diffuse non-monotonic** exemplar —
two-bin-flat, structured but no hero passages: the Viewer-C *gestalt* case), and
**De Anima** (the **hero-structure** exemplar — named passages 404a/431b/405a carry
its ≥3-period structure: the Viewer-C named-trajectory case). Timaeus + De Anima are
the gestalt-vs-hero pair for the non-monotonic state.

---

## 9. Open items (for the record)

**Audit second-pass status — A1–A3 applied; B1–B7 run on the real corpus and
resolved:**

- ~~**B1 (Paul early-n)**~~ — **CLEARED** (§5): every featured Romans/Galatians arrow
  is FDR-solid *and* early-powered (pre-1977 base 33–193 / 89–138 per chapter, all
  above the floor); no `floor_fail_early`. Mover sets refined (Romans +ch16, −ch5;
  Galatians +ch1, +ch4).
- ~~**B2 (Pindar within-shelf)**~~ — **CONFIRMED** (§6): only O.6 is `§` among the
  pooled top-10; the rest are `·` block-carried. Genuine ode movers = O.5,O.6,P.1,
  P.6,P.11,N.1,N.2. Render `§` arrows with the **within-shelf** delta (O.6 sign flip).
- ~~**B4 (non-monotonic)**~~ — **CAUGHT ONE** (§3): Timaeus is two-bin-flat but mb
  z +4.1 → reclassified non-monotonic (was the stability hero); Laws (+1.9/mb+5.0) and
  De Anima (+2.6/mb+4.3) marginal-but-structured. Gorgias/Meno genuinely flat.
- ~~**B5 (stable power)**~~ — **DONE** (§3): Timaeus/Gorgias/Meno all
  `stability_powered` (>2000/1000/800 articles); Gorgias is the new stability
  exemplar.
- **B6 (near-threshold)** — near-threshold works re-run; verdicts hold: De Anima
  all-journals stays **marginal** (+2.6), Laws marginal (+1.9), Theaetetus borderline
  **REAL** (+3.0, diffuse). No category flips. (Re-confirm any future marginal at
  `--perm 2000` before featuring.)
- ~~**B7 (46th ode)**~~ — **RESOLVED, no stray** (§6): the 46th is **Isthmian 9**, a
  genuine fragment; "45" was a miscount of complete odes. Nothing to remove.
- ~~Iliad `Il. 1.x` / date sanity check~~ — **RESOLVED** (§6): real reception
  history (proem → battle books), not a date/OCR artifact. Iliad promoted to a
  featured reshuffle case.
- ~~Pindar Olympian-recency check~~ — **RESOLVED** (§6): real reception history, not
  composition. The recency is broad across all major classics journals, and *within
  the same journal* Olympians run ~10–20 yr later than Nemeans (CQ 2013/2005, AJP
  2013/1992, HSCP 2011/1993, TAPA 2013/1990); no batch/concordance smell. The
  "Olympians rise as a block" shift is genuine — read at the shelf level, and the
  named-ode overlay only from `survives_within_shelf` odes (B2). (The 46-vs-45 count
  is resolved: the 46th is the Isthmian 9 fragment, not a stray — see §6.)
- **NT/Homer/Pindar journals aren't grouped** in `journal_groups.json` (only the
  10 Plato/Aristotle journals are), so `--journals` can't do a within-community
  split for the new corpora yet. A journal typology for the NT/theology venues is
  the prerequisite for View C on Paul (already flagged in the UI handoff).
- The `build_viewer_data.work_system` mislabel (Aristotle works with only 3-digit
  Bekker pages tagged `stephanus`) — cosmetic here, a viewer-render bug to fix when
  the viewer is built.
