# Temporal Analysis — Audit Handoff (Second Pass)

**For:** Claude Code (re-run / correct the Stage-1 temporal analysis)
**From:** review of `TEMPORAL_FINDINGS.md` with David
**Status:** the analysis is sound and the honesty guards are real. This is a
punch-list of corrections and verifications to run *before* the findings go to
Claude Design for mockups. Items are ordered: (A) a settled ontology correction
that changes viewer placement, then (B) verification/robustness items that may
change what the mockups are allowed to show.

Do not re-litigate settled design decisions elsewhere in the project. The one
decision being *reopened* here is Pindar's viewer placement (§A1), and it is
being reopened deliberately.

---

## A. Settled correction — Pindar belongs in Viewer A, not Viewer C

### A1. The tri-level (four-level, with clusters) ontology, stated

The project's unit ontology, top to bottom:

- **Level 0 — text-cluster:** ode-books (Olympian/Pythian/Nemean/Isthmian);
  any future corpus grouping.
- **Level 1 — text:** Iliad, Odyssey; a Plato dialogue; an Aristotle treatise;
  a Pauline letter; **a single Pindaric ode.**
- **Level 2 — book/chapter:** Republic/Laws/NE/EE/Metaphysics books; Iliad/Odyssey
  books; Paul's chapters.
- **Level 3 — line/verse:** lines (pagan corpora); verses (Paul).

Viewer assignment by level:

- **Viewer A** traces temporal shifts at **levels 0–1** (text-clusters and texts).
- **Viewer C** traces temporal shifts at **levels 2–3** (books/chapters, and
  lines/verses where dense enough).

### A2. The correction

`TEMPORAL_FINDINGS.md` (§4, §6, §7.8, §8) treats the Pindar ode as a
passage-analog and files the pooled-ode reshuffle under a Viewer-C-adjacent
"comparing-texts" temporal view. **This is a level error.** The Pindaric ode is
a **level-1 text**, not a sub-text unit. Therefore:

- The z+26.7 pooled reshuffle (Olympians rising as a block; individual odes
  moving) is a **level-1, text-level** phenomenon → it is a **Viewer A** result,
  with the **ode as the text** and the **ode-book as the level-0 cluster color**.
- **Level 2 does not exist for Pindar at all.** An ode has no book/chapter
  subdivision. This is not "stable" and not "too sparse" — the unit is simply
  **absent from the ontology** for this corpus.
- **Level 3 (line) exists but is temporally hopeless** (0 FDR movers; near-zero
  odes clear the floor — already established, §6).

**Conclusion to write into the findings doc:** Pindar is the one corpus with a
noteworthy **level-1 (text)** temporal shift, **no level-2 unit whatsoever**, and
**nothing showable at level-3**. It therefore appears in **Viewer A only** and is
**absent from Viewer C entirely** — not because its shifts aren't significant, but
because it has no unit at the grain Viewer C operates on.

Corollary: the ode-book (cluster) is a **Viewer A grouping**, not a Viewer C
facet. The entire Pindar apparatus lives at levels 0–1, inside Viewer A.

### A3. Concrete edits requested

- Rewrite §4's "comparable text isn't always the work" passage so the Pindaric
  ode is explicitly a **level-1 text** and the ode-book an explicit **level-0
  cluster** — remove any framing that places the ode "below the work" as a
  sub-text/passage unit. (The ode is below the *nominal file/ode-book*, yes, but
  the ode-book is a *cluster above text*, not a work. "Below the ode-book" and
  "below the text" are different directions; the doc currently conflates them.)
- Move Pindar's temporal result from the §7.8 "comparing-texts" (C-adjacent)
  slot into the **Viewer A** description as the exemplar of a text-level shift
  with a cluster grouping.
- In §8 (mockup dataset), relabel `temporal_Pindar_book.json` as the **Viewer A**
  text-level / cluster-grouped case, not the comparing-texts-for-C case.
- Add one sentence making the general rule explicit for future corpora:
  *a corpus declares, per level, whether a unit exists; a level may be empty
  (Pindar has no level 2), and viewer placement follows the level, not the file
  boundary.*

---

## B. Verification & robustness — resolve before mockups

These are the items that may change what the difference-maps are allowed to
*show*. B1–B3 gate the hero mockups directly.

### B1. Paul / 1977 split — report the pre-1977 per-chapter n before featuring arrows

§5 is the hero case, and its own caveat notes the pre-1977 base is thin. The
whole-work verdict is aggregate and survives, but the **chapter-localized arrows**
(Romans ch 8 ↓, ch 11 ↑, ch 10 ↑; Galatians ch 3 ↑, ch 2 ↓) are the showcase and
are the most exposed to the exact small-count regime the `--min-articles 15` floor
exists to reject.

**Do:** for each featured chapter, emit the **pre-1977 distinct-article count**
and the **post-1977 count** into the temporal JSON, and print them in the run log.
Any featured arrow whose pre-1977 bin is below the mover floor must be marked
`floor_fail_early` and **must not** be rendered as a bright FDR-solid mover in the
mockup — it drops to the diffuse/muted layer or is footnoted as
"whole-work-significant, chapter direction under-powered."

**Watch for confirmation bias:** the New Perspective direction is known, so movers
matching it *feel* confirmed. External validation is genuine but is not a
substitute for the pre-1977 n. State the n; let it speak.

### B2. Pindar — resolve the median-split confound before naming odes in the mockup

§6 is honest that the pooled median split "maps the shelf-recency difference onto
the up/down axis" and says to read the movement **at the shelf level**. But the
headline and §8 hero entry still name individual odes (O.1, O.2, O.6, O.7 ↑). The
doc says "don't over-interpret ode-by-ode" and then hands Design ode-by-ode data.
Resolve the tension one of two ways:

- **(preferred)** Run a **within-shelf permutation control**: within each ode-book,
  is there still significant ode-level reshuffling once the shelf-level recency
  difference is partialled out? Only odes that survive *that* get named-ode arrows.
  If none survive, the mockup movers are **shelf blocks**, not named odes.
- **(fallback)** If the within-shelf control isn't run, the Pindar mockup shows
  **shelf-level movement only** (O./P./N./I. as the moving units), and named odes
  appear only in drill-in, explicitly labelled "shelf-recency may drive direction."

Emit a flag per ode: `survives_within_shelf` (bool) so Design can gate rendering.

### B3. Difference-map needs an absolute anchor, not just share-deltas

Everything is article-incidence share (volume-invariant — correct). But a share
can fall purely because *other* units rose, with the unit's own absolute attention
flat or growing. §7.6 gives the drill-in a faint total-volume band, but the
**difference-map (§7.2)** shows share-deltas with no absolute anchor. A humanities
reader will read "ch 8 ↓" as "people stopped citing Romans 8," which may be false.

**Do:** emit, per unit, both the **share-delta** and the **raw distinct-article
count per bin** (early/late). The difference-map spec gets an **absolute-vs-share
toggle**, or at minimum every difference-map cell carries a tooltip with raw
early/late counts. This is load-bearing for the dual audience and is cheap — the
counts already exist upstream of the share computation.

### B4. Two-bin split is blind to non-monotonic trajectories

The median (or dated) split collapses each trajectory to two points. A unit that
**rose then fell** (or vice versa) reads as "stable" under two-bin TVD while
actually having the most interesting reception history. `by_bin` trajectories
already exist (§7.6, §8), so the data supports ≥3 bins.

**Do:** add a **monotonicity-agnostic trend test across ≥3 bins** (e.g. a
per-unit test for any-shape temporal structure, or at least a variance-across-bins
statistic vs the permutation null) and a per-work `non_monotonic` flag. Any work
currently labelled **stable** at two-bin should be re-checked: is Timaeus /
Gorgias / Meno genuinely flat across time, or up-then-down averaging to flat? The
current output cannot distinguish these, and a "stability badge" over a
non-monotonic trajectory would overclaim. Report which stable verdicts are
flat-monotonic vs. merely two-bin-flat.

### B5. State the power behind every "stable" verdict

§3.3/§7.7 rightly dignify stability as a positive finding — but only if the test
*could* have detected a shift at that sample size. A stability verdict from a
well-powered work (many articles, genuinely flat) and one from an underpowered
work (too few articles to move the z) deserve **different badges**.

**Do:** define a **minimum distinct-article n for a stability claim to count as
informative** (not merely under-powered). Below it, the verdict is
**too-sparse-to-tell** (§7.7's third state), not **stable**. Emit
`stability_powered` (bool) and the n on every stable verdict. Timaeus at +0.3:
confirm it's a well-powered null, not a thin one.

### B6. Bump permutation count near the verdict thresholds

200 permutations gives a floor p ≈ 0.005 and a noisy z in the tail — fine for
z ≈ +7, shaky in the **marginal band (1.5–3)** where the verdict category actually
flips (De Anima: +2.7 all-journals = marginal, +3.3 philosophy = REAL; that
boundary is drawn on 200 shuffles).

**Do:** for any work whose z lands within, say, ±1 of a category boundary
(1.5 or 3.0), **re-run at ≥2000 permutations** (or report a bootstrap CI on the z
and let the CI, not the point estimate, set the category). Cheap insurance;
matters only near the thresholds, so it's a targeted re-run, not a full recompute.

### B7. Chase the 46th ode-number across *all* Pindar data, not just temporal

§6/§9 note 46 ode-units for 45 canonical odes — a stray ode-number, called
immaterial to the temporal shape (true). But if it's an OCR/fragment artifact it
may also sit in the **non-temporal Viewer A/C Pindar data**, where a phantom 46th
ode would render as a real (empty or misattributed) unit.

**Do:** identify the stray ode-number, confirm whether it's OCR/fragment, and
verify it's cosmetic **everywhere** (viewer_data as well as temporal_*), not just
in the temporal shape result. Remove or correctly reattribute it.

---

## C. What to hand back

For each item, the run log / updated JSON should make the answer legible without
re-reading the code:

- **A1–A3:** findings-doc edits applied; Pindar reassigned to Viewer A; ode-book
  reassigned as level-0 cluster; note added that a level may be empty.
- **B1:** per-featured-chapter pre/post-1977 article counts; `floor_fail_early`
  flags.
- **B2:** `survives_within_shelf` per ode; decision on named-ode vs shelf-block
  movers.
- **B3:** raw early/late counts emitted per unit alongside share-deltas.
- **B4:** ≥3-bin trend test; `non_monotonic` per work; re-audit of stable verdicts.
- **B5:** `stability_powered` + n per stable verdict; stable-vs-too-sparse boundary
  defined.
- **B6:** targeted ≥2000-perm re-run (or z-CI) for near-threshold works.
- **B7:** stray ode-number identified and confirmed cosmetic everywhere.

Nothing here undermines the core findings. B1–B3 change what the hero mockups may
show, so they gate the Claude Design handoff; B4–B7 tighten honesty and can land in
parallel.
