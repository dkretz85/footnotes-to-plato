# Footnotes to Plato (and Others) — Design Handoff

**For:** Claude Design (temporal-view mockups)
**From:** David Kretz, with the conceptual/analysis thread
**What this is:** the whole picture — what the project is, who it's for, what the
temporal analysis found, and (most important) the design posture that should govern
the mockups. Read §0 and §6 even if you skim the middle: §0 is what we're building,
§6 is the one thing we most need you to get right.

---

## 0. The project in one breath

**Footnotes to Plato (and Others)** (footnotes.dkretz.com) is a free scholarly
finding aid. It maps, at the passage level, how often and when specific passages of
ancient texts — Plato, Aristotle, Homer, Pindar, Paul/NT — get cited in the academic
journal literature. A classicist can ask *which passages of the Republic does the
scholarship dwell on, and has that changed since the 1970s?* and get an honest,
sourced answer that links back out to the articles on JSTOR.

It is a **finding aid, not a content mirror**. It shows counts, patterns, and
citation trajectories, and links *out* to JSTOR / Perseus. It never reproduces
article text. (This is both a principle and a hard licensing constraint — see §7.)

The audience is **humanities scholars first**, with digital-humanities and
data-science readers as an important second audience who must be able to trust the
methods. Designing well for *both at once* is the core challenge — §6.

---

## 1. The viewers (the product surface)

There are three passage/text viewers. The **immediate focus of this work is View C**,
but we want to think with you about the **whole website** — View C has to feel of a
piece with the rest, and the site's overall design language, navigation, and framing
are all in scope. Don't treat View C as an island bolted onto an existing thing;
treat the site as one designed object that View C completes.

| Viewer | What it shows | Grain (unit level — see §3) |
|---|---|---|
| **View A** | Attention to whole **texts** (and text-clusters) over time; compare texts | Levels 0–1 (cluster, text) |
| **View B** | Passage-level attention **within one text**, one journal-set, period selector | Levels 2–3 (book/chapter, line/verse) |
| **View C** | Passage-level within a text, **contrasting** journal-sets | Levels 2–3 |

**Build status: Views A and B both already exist** (built and verified) — you can and
should look at them directly (David can point you at the live site and the repo). They
are your design baseline: View C and any site-wide refinements should extend their
visual and interaction language, not diverge from it. View C is the piece still to
build (it needs a theology-journal typology first, so parts of it are near-future
rather than immediate). The **temporal findings you're designing from** (the attached
`TEMPORAL_FINDINGS_POST_AUDIT.md`) feed the "over time" behavior of View A
(text/cluster level) and the sub-text difference-map that Views B/C share.

**Standing commitments the whole tool honors** (these are principles; make them
*legible* in the design without letting them dominate the first impression — see §6):
- **Volume-aware, with absolute counts available too.** The default framing is
  *shares* (article-incidence), so a busy modern journal-year doesn't masquerade as
  growing interest. But absolute counts are not banished — they're a real, wanted view:
  **View A lets the user toggle between share and absolute count**, and **View B is
  shown in absolute article counts.** So the design needs a clean, legible way to
  present *both* framings and to make clear which one the user is looking at. Share-vs-
  absolute is a first-class distinction the interface should teach, not hide.
- **Uncertainty-visible — but not at the cost of accessibility.** Showing confidence
  honestly is the project's signature and its trust anchor, and nothing certain-looking
  should be certain when it isn't. *But* this must not become a wall of caveats that
  greets the user before they've seen anything worth caveating. If the first thing a
  scholar meets is a paragraph of hedges, they leave. The resolution is **layering**
  (§6): a clean, confident, plain-language surface, with the rigor one deliberate step
  back — reachable, precise, never absent, but never the front door. Caution that
  costs us the user is a failure, not a virtue.
- **Links out, never mirrors.** Every passage/article resolves to a JSTOR DOI or a
  Perseus URN. We surface the door, not the room.

---

## 2. What the temporal analysis established (the short version)

The attached findings doc is the full record; here's what you actually need to hold
in your head while designing:

- Attention to a text's passages **does** shift over time for many texts — but the
  shift is usually **diffuse** (many passages nudging), only sometimes carried by a
  few nameable "hero" passages. **Design must be able to show diffuse-ness honestly**,
  not manufacture crisp arrows where there aren't any.
- **Two controls change the story**, so both are first-class UI, not chrome:
  - **Grain** (text ↔ book/chapter ↔ line/verse): the same text can reshuffle at one
    grain and be flat at another.
  - **Journal-set** (all vs. a scholarly community): this can *reverse* a finding.
    Republic Books VIII/IX **fall** across all journals but **rise** within
    philosophy. "All journals" must never be presented as "the field's reading."
- Findings come in **four honest states**, each needing its own visual treatment
  (this is the heart of the design — §4).

---

## 3. The unit ontology (why grain is a control, and why a level can be empty)

Every corpus's units live at levels:

- **Level 0 — cluster:** e.g. Pindar's ode-books (Olympian/Pythian/Nemean/Isthmian).
- **Level 1 — text:** a dialogue, a treatise, an epic, a letter, **a single ode**.
- **Level 2 — book/chapter:** Republic books, Paul's chapters, Iliad books.
- **Level 3 — line/verse:** lines (Greek), verses (Paul).

Two consequences that affect layout:

1. **A level can be empty.** Pindar is the instructive case: an ode is a *level-1
   text* (peer of the Iliad), the ode-book is a *level-0 cluster* — and Pindar has
   **no level 2 at all** (an ode has no books/chapters). So Pindar appears in **View
   A only** (text/cluster over time, ode-book as a cluster color) and is **absent
   from the sub-text difference-map** — not because it's flat or sparse, but because
   the unit doesn't exist. The design should let a corpus *have nothing* at a level
   without that reading as an error or an empty state.
2. **Grain is a toggle, first-class.** For dense Greek prose (Plato, Aristotle) the
   passage grain is live. For `book.line` / `chapter:verse` corpora (Homer, Pindar,
   Paul) the **line/verse grain is temporally hopeless** and **book/chapter/ode is
   the default and often the only** viable grain. The toggle should make the default
   obvious and not tempt users into a grain that can't support a finding.

---

## 4. The four temporal states — each needs a distinct, dignified treatment

This is the most important design content. A viewer that renders all four the same
way would lie. From the findings:

1. **Between-book reshuffle (crisp).** Nameable movers survive the statistics.
   *Republic, Metaphysics, Romans, Galatians, Iliad, Odyssey.* → a **difference-map**
   with **bright** significant movers and a **muted** remainder. Bright = survived
   FDR **and** cleared the early-count floor (`n_fdr_movers_solid`). Everything else
   is visibly secondary.
2. **Diffuse reshuffle.** The whole text moved but **no single passage** survives —
   the drift is broad. *Nic. Ethics, Theaetetus, De Anima.* → the difference-map as a
   **gestalt**, *no hero cells*, honestly captioned "reshuffled, but diffusely." An
   all-muted map under a "reshuffled" verdict is correct, not a bug.
3. **Stable, well-powered.** Genuinely flat, and we had enough data to *detect* a
   shift if there'd been one. *Gorgias, Meno.* → a **dignified stability badge** — a
   real finding, not an empty chart. Must not be confusable with:
4. **Non-monotonic / two-bin-under-read.** Flat if you only compare early-vs-late,
   but **structured** across ≥3 periods (rose-then-fell, etc.). *Timaeus* (looked
   stable at two bins; is actually structured), *Laws, De Anima.* → **show the
   multi-period trajectory, never a stability badge.** The whole point is that a
   two-point comparison would have hidden the interesting shape.

And a fifth, orthogonal condition:

- **Too-sparse-to-tell.** Not enough data to make *any* verdict trustworthy (distinct
  from "stable"). → aggregate-only, "we can confirm a shift but can't name the
  passages." A stability badge here would overclaim.

Design implication: **the verdict badge has four+ faces, and the difference-map has
a bright/muted split that must be driven by the significance flags, not by visual
punchiness.** The temptation is to make everything look crisp. Resist it — the
honesty *is* the product.

---

## 5. Controls and honest defaults (spec-level, for the mockups)

Every temporal view should headline the **whole-text verdict** first (the robust
layer), then let the user drill in. Concretely:

- **Verdict banner** — state + z, four faces (§4). The temporal analog of View B's
  trustworthy/uncertain tier banner.
- **Difference-map** with an **absolute-vs-share toggle** — ideally the *same* toggle
  affordance View A already uses for share vs absolute count (§1), so the distinction
  is taught once and behaves consistently site-wide, not reinvented per view. Critical
  for the humanities reader: a passage's *share* can fall while its *absolute*
  attention is flat or rising (others rose faster). "Romans 8 ↓" must not be misread
  as "people stopped citing Romans 8." Every cell carries its **raw early/late article
  counts** in a tooltip. (Data is emitted per unit as `units[]`.)
- **Grain toggle** (§3) — first-class; default made obvious.
- **Journal-set selector** (§2) — first-class and prominent, framed as
  *composition* ("the corpus's mix changed") vs *within-community* ("this field's
  reading changed"). This selector can reverse a finding, so it can't look optional.
- **Split-year / "test a date" control** — lets a scholar test a dated hypothesis
  (New Perspective 1977, Gettier ~1965) rather than only the median split.
- **Drill-in trajectory** for any dense unit, with the text's **total volume as a
  faint band** behind it so "this rose" is never confused with "everything rose,"
  and backed by the ≥3-period structure test so non-monotonic shapes show honestly.

**One caution for featuring:** a couple of verdicts sit near a category threshold
(marginal↔real). Don't design a mockup that presents a *marginal* verdict as a solid
one. The hero set below is chosen to avoid this.

---

## 6. THE DESIGN POSTURE — read this twice

Two audiences, one surface, and a real tension between them.

**(a) Don't scare the humanists.** The primary users are classicists, philosophers,
theologians — brilliant readers who are *not* statisticians and should never have to
be. The front of every view should speak their language: a verdict phrased like
*"Attention to the Republic's books on the ideal city has grown in
political-philosophy journals since the 1970s,"* not *"TVD z = +5.4 vs permutation
null, FDR q < 0.05."* Plain-language verdicts, human-legible labels, the statistics
available but **one layer back** — behind a tooltip, an "about this measure" link, a
methods page. The default surface should feel like a well-made reference tool, not a
stats dashboard. (The verdict *phrasing* is yours to craft — it's functional
micro-copy, §6d — but the surrounding *narrative* framing is David's.)

**(b) Don't lose the DH/data-science reader's trust.** That same second audience is
exactly who will decide whether this tool is *credible*. For them, every caveat, every
null, every FDR correction, every "diffuse not crisp," every raw-count tooltip must be
**reachable and precise.** The transparency isn't decoration — it's the reason a
serious methods person will endorse the tool to the humanist who'll actually use it.
So: nothing dumbed-down *away*, only ever dumbed-down *forward* — plain on the surface,
rigorous underneath, and a clear path from one to the other.

**(c) — and this is the big one — build an instrument, not a slideshow of our
conclusions.** We have just done a great deal of analysis. We know a lot of specific
stories now: the New Perspective in Paul, the Olympian rise in Pindar, the battle-book
migration in Homer. **These are demonstrations that the tool works — they are NOT the
tool.** The purpose of Footnotes is to let a scholar ask *their own* question of the
corpus and reach *their own* conclusion. The gravest design failure would be a viewer
that quietly walks every user to the seven findings we happen to have looked at —
pre-baked "insights," a landing page of our greatest hits, defaults that steer toward
our examples. Design for the question we *didn't* anticipate. The hero cases (§8)
should live in a clearly-marked "examples / how to read this" area — a way in, an
onboarding — never the main event, and never the shape of the whole. Our findings are
scaffolding we used to make sure the instrument is honest and expressive enough. Then
the scaffolding comes down and the user's question takes the stage.

**(d) Leave the prose to David — the introductory prose, at least.** The
**introductory / block text** — landing-page framing, section intros, the "what this
is and how to read it" narrative, anything that sets the tone and voice — **David
writes.** Don't draft it; leave it as marked placeholders (`[intro copy — David]` or
similar) so it's obvious what's his to fill and the layout is designed *around* real
text length without pre-empting his words. What you *should* write is the
**functional micro-copy**: control labels, button and toggle text, axis and legend
labels, explanatory hover/tooltip text, empty-state and error strings, the plain-
language verdict phrasings. That's design's craft and it's genuinely wanted — a good
tooltip is part of the interface. The line: **voice-bearing prose is David's;
interface text is yours.** When unsure which side a given string falls on, treat it as
David's and leave a placeholder.

If (a)–(d) ever seem to conflict in a specific screen, that's a real design decision
worth surfacing to David rather than resolving silently — the resolution is usually a
layered disclosure (plain default, rigorous on demand), not a compromise that
shortchanges either audience or pre-empts the user's question.

---

## 7. Hard constraints (licensing & data — these bound the design)

- **Finding aid only.** Link out to JSTOR (stable DOIs, `doi.org/10.2307/…`) and
  Perseus (canonical URNs). **Never mirror or reproduce article text or the verbatim
  citation context.** No design element should ever display source-article prose.
- **No raw internal IDs** surfaced to users; article links key on the stable DOI.
- **Uncertainty is always shown, never hidden** — a design principle *and* a
  methodological commitment. Don't design an interface that can present a shaky number
  as a confident one.

---

## 8. Concrete dataset & hero set for the mockups

The real analysis output ships as `temporal_*.json` — these ARE your mockup data
(real numbers, real works), so nothing needs to be invented:

- `temporal_<work>.json` — passage grain, all journals
- `temporal_<work>_<set>.json` — journal-set filtered (e.g. `_philosophy`)
- `temporal_<work>_book.json` / `_<set>_book.json` — book/chapter grain
- `temporal_Pindar_book.json` — pooled Pindar for **View A**: each ode a level-1
  text, ode-book as level-0 cluster color; movers carry `survives_within_shelf`
  (cluster-block vs genuine ode-level).

Each record carries (names you'll bind to): `verdict` + `shape_change` (z vs null);
`multibin_structure.z` + `two_bin_flat_only` (the ≥3-period test); `stability_powered`;
`units[]` (per-unit raw early/late counts + shares — for the absolute/share toggle and
tooltips); `top_movers` with `significant_fdr`, `floor_fail_early`,
`survives_within_shelf`; `n_fdr_movers_solid` (bright-render only these);
`near_threshold` (don't feature as solid).

**Hero set — for the "how to read this" / onboarding area, NOT the main surface
(§6c):**
- **Romans** (chapter grain, 1977 split) — the crisp difference-map showpiece.
- **Republic** (book grain, all-journals vs philosophy) — the journal-reversal demo;
  the single best argument for why the journal-selector is load-bearing.
- **Iliad** (book grain) — the migration story (Book 1 → battle books); strongest
  reshuffle.
- **Odyssey** (book grain) — the clean single-mover case (Book 11 ↑).
- **Pindar (pooled odes)** — the **View A** level-0/1 case: ode = text, ode-book =
  cluster color; render the **cluster block** (Olympians ↑) as a cluster mark, and
  give a **named-ode arrow only to `survives_within_shelf` odes.** Note the O.6
  gotcha — it's ↑ pooled but ↓ within its own shelf; a named arrow must use the
  within-shelf delta. (A good stress-test that your mover-rendering respects the
  flags rather than the raw number.)
- **Gorgias** — the true **stability badge** (well-powered flat).
- **Timaeus** — the **non-monotonic** exemplar (looks flat at two bins, structured
  across ≥3 periods; show the trajectory, never a badge). The clearest case for why
  the four-state treatment matters.

These seven exist to prove the instrument spans all four states and both controls.
Use them to *teach the interface*, then get out of the user's way.

---

## 9. What's in / out of scope for this handoff

**In:** temporal mockups for View A (text/cluster over time) and the sub-text
difference-map (Views B/C share it), the four-state verdict system, the two controls,
the drill-in trajectory, and the layered plain↔rigorous disclosure of §6.

**Out / later:** View C's contrasting-journal machinery for Paul (needs a
theology-journal typology first — flagged, not ready); the non-temporal View B (built);
back-end/pipeline (done). If a mockup needs one of these to make sense, note it for
David rather than assuming it.

**A note on your context:** you likely don't have access to the project's chat history
or files — this document is meant to stand alone. If something here points at a file or
decision you can't see and you need it to design well, ask David; don't infer it.
