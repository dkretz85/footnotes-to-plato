# Footnotes to Plato — external audit & remediation plan

*Written at the end of an audit session (Fable 5) reviewing the pipeline, the
aggregator, both viewers, and the live site at footnotes.dkretz.com. Companion
to `SESSION_HANDOFF.md` and `citation-pipeline-methods.md`. Pick up here.*

---

## What was reviewed

`citation-pipeline-methods.md`, `SESSION_HANDOFF.md`, `build_viewer_data.py`,
`locus.py`, `view_a.html`, `view_b.html`, the real data files in the project
(`view_a.json`, `meta.json`, `Nicomachean_Ethics.json`, `Meno.json`,
`collision_bands.json`), and the live site's home, data, and navigation pages.

`resolve_citations.py` and `build_citation_db.py` were **not** available in the
project and were not reviewed — which turns out to matter (see Finding 1).

## Overall assessment

The pipeline discipline is genuinely strong. Precision-first, divert-don't-delete,
probe-before-filter is the right methodology, and the methods record shows it was
practiced rather than professed — filters rejected after measurement, bugs found
by reading real rows, reference tables repaired mid-build. The site's honesty
apparatus (two tiers, the fade encoding, "what it cannot tell you") is better
than most published digital-humanities work.

Three classes of problem were found: one conceptual (the tier model's stated
rationale is contradicted by the data), four live-visible bugs in View B, and a
set of places where the copy claims more than the data currently supports.

---

## Finding 1 — the tier model's recorded rationale is wrong (CONCEPTUAL, blocking)

**The claim on record.** Both `SESSION_HANDOFF.md` and `build_viewer_data.py`'s
module docstring state that `ceiling = resolved + queued` was rejected because
queue filing is *non-exclusive*: one ambiguous citation is filed under every
candidate work, so summing a work's queue multi-counts collisions.

**What the data says.** Filing is **exclusive**. Per-work `queued_total` in
`view_a.json` sums to exactly **50,450**, matching `meta.json`'s `total_queued`
and ≈ the 50,586 queue rows in the methods doc (the gap is presumably rows with
an empty work field). Under non-exclusive filing that sum would substantially
exceed the queue. Each queued citation carries **one** `work_id`; the other
candidates appear only in the `reason` string.

**Why it matters.**

1. The stated reason for the redesign is factually wrong. The conclusion may
   still be right, but it needs a different justification on the record.
2. The real problem is an **undocumented filing rule**. If each ambiguous
   citation lands under exactly one candidate, then *which* candidate it lands
   under determines that work's fade magnitude and its resolution-rate
   denominator — and therefore its tier. Apology's 25.5% and Philebus's 76.2%
   are partly artifacts of where shared collision rows were filed. Nothing in
   the methods record says how `resolve_citations.py` chooses.
3. Suggestive but not conclusive: the two worst rates (Apology 0.255, Meno
   0.256) belong to works sorting alphabetically before their collision
   partners. Gorgias breaks a pure-alphabetical hypothesis, so the rule cannot
   be inferred from the outputs alone.

**The fix.** The quantity the fade and the "≈X if all belonged here" tooltip
actually *mean* is "queue rows whose candidate set includes this work" —
computable from the `reason` column already being parsed for `collides_with`.
That quantity legitimately multi-counts across works (a shared citation really
could belong to each), which is correct for a per-work upper gesture.

**Steps, in order:**

- Open `resolve_citations.py`; find the branch writing `review_queue.tsv` and
  determine what goes in `work_id` when the candidate set has >1 member.
  Sanity-check by sampling queue rows whose `reason` names ≥2 candidates and
  seeing which candidate the `work_id` column holds.
- Document the rule in `citation-pipeline-methods.md` §4.
- Recompute per-work `unplaceable` from candidate-set membership in
  `build_viewer_data.py`.
- Check whether any work's tier flips under a resolution rate whose denominator
  uses candidate-set membership. **If tiers are robust to it, say so on the
  methods page** — that is a strong sentence to be able to write.
- Correct the non-exclusivity claim in `SESSION_HANDOFF.md`,
  `build_viewer_data.py`'s docstring, and the live methods page.

**Do this before anything else.** Everything View A asserts about uncertainty
flows through this one undocumented choice, and the copy fixes downstream should
only be written once.

---

## Finding 2 — View B bugs (live-visible; verified against real NE data)

**2a. The drill panel overcounts articles.** Dots are deduped by
`(iid, page, section, line)`, but the section-grain drill collects all dots at a
page+section and reports `dots.length` as "N articles cite this passage." An
article citing 1097b25 and 1097b33 appears twice.

- NE 1097b: header says **91 articles**; true distinct count is **53**.
- NE 1147a: **82** vs **34**. NE 1139a: **107** vs **67**.
- This is on the flagship example passage cited on the homepage.

Fix: count distinct iids for the header; probably group the list by article,
showing each once with its loci.

**2b. Bar chart and heatmap disagree about the same passage.** Bars are drawn
from `cells` (raw TSV rows — repeat mentions within an article each count); the
heatmap is built from deduped `dots`. At NE 1097b the bar says **179** while the
heatmap cells for 1097b sum to **91**. True for **159 of NE's 183 sections**.
Both semantics are defensible; having both on one page under the word
"citations" is not.

**Decide this up front** — it propagates to the y-axis label, the metric toggle
wording, the drill header, and the data page's description of
`view_b/<work>.json`. Recommendation: dedupe both to distinct-article-per-locus,
since that is the quantity the drill panel and CSV export actually list.

**2c. Line-less citations silently inflate the first line-band.**
`bandOf(null)` returns `0`, so every Bekker citation without a line number
renders in band ₁ (lines 1–15) and drills in labelled e.g. "1097b₁" as if
line-specific. **740 of 5,499 NE dots (13.5%)**; 16 of the 91 at 1097b. Needs a
fourth "unspecified" band, exclusion from the band grid with a count note, or
proportional spreading — anything but a false precision claim.

**2d. Phantom c/d/e columns for non-faceted Aristotle works.** `isBekker()`
lists only the three faceted treatises, so De Anima, Physics, Politics etc. fall
through to the a–e Stephanus grid — three permanently empty dashed columns per
page for works whose pagination has only a/b. Not visible in the two-work
standalone; **check whether this shipped to the live Passages view.** The right
test is the author/edition map (already inlined in View A), not the faceted list.

---

## Finding 3 — "trust the shape" overclaims where it is least safe

The uncertain-tier banner says "Trust the *shape* of what resolved." But methods
§6.1 identifies ~8 works with a **localised** under-resolved band (Meno 100–109,
Apology 10–19, Phaedrus 250–259, Phaedo/Philebus 50–59, Laws 860–869, Parmenides
150–159, Gorgias 510–519) — works whose resolved shape is systematically biased
in a specific region. `collision_bands.json` was built precisely to caveat this,
is copied through by the aggregator, and **is not rendered**.

As it stands the banner asserts the one thing §6.1 says isn't safe, for the tier
where it isn't safe. Either wire the overlay in, or amend the banner
("…except in the marked collision bands") in the interim. **The overlay and the
copy edit should land together** rather than the banner being softened and then
re-hardened.

**Related, on the other side:** the trustworthy note ("bar lengths are reliable
— you can compare how much these works are studied") glosses that within-tier
rates still range 80–98%, so raw floors misstate relative volume by up to ~20%.
The methods doc's own `est_true` rate-correction (§6.2) exists exactly for this
and appears nowhere in the viewer. A raw / rate-corrected toggle on View A —
which the methods doc itself recommends — would close the gap.

**Also:** the tier conflates rate with sample size. Minos (floor 30, rate 1.0)
sits in "publication grade" beside Republic. Add a small-n de-emphasis or an n
threshold note so no one compares Theages to Timaeus with tier-granted
confidence.

---

## Finding 4 — "they demonstrably do not"

The homepage claims philosophers and classicists demonstrably read different
passages. Before that word survives to the non-draft version, the comparison
needs to handle two confounds the pipeline itself documents:

- **Era.** The journals differ enormously in period (~83% of Classical Review's
  excluded material was pre-1910; the surviving classics corpus still skews
  older).
- **Genre.** Book reviews vs research articles cite differently.

A raw by-journal split of passage profiles will show differences even if the two
fields read identically, because attention itself moved over 135 years. Minimum:
make the comparison within-period, or soften the wording until it is.

This is the one item where waiting is better than rewording — a within-period
comparison is a real piece of analysis, not a sentence fix.

---

## Finding 5 — smaller items

No correctness bug was found in `locus.py`'s interval logic. The EE
run-splitting with the `VI*` cap is handled correctly, mid-page book openings
work as documented, and lifting the parser to a shared module was the right call.

**View A**
- Tooltip total (`floor + unplaceable`) omits `band_extra`, so "≈X if all
  belonged here" is short by the band.
- Bar scale has the same omission, so band segments can slightly overrun the
  intended track.
- `TRACK = 740` px is hardcoded with no responsiveness — bars overflow the grid
  column on narrow screens.
- The fade is capped at 320px, which undercuts "the fade shows magnitude of
  ambiguity" (Apology's 5,084 and a much smaller mass can render identically).
  Defensible as a design choice while the legend keeps "could be much more" —
  but if View A gains a rate-corrected mode, the fade may become redundant and
  the whole encoding could simplify. **Worth deciding alongside the est_true
  toggle, not separately.**

**Both views**
- `fetch` calls have no `.catch`. Given the earlier silent-404 incident, a
  visible failure message is warranted.
- Hover-only tooltips exclude touch devices.
- The chart doesn't rerender on resize.

**Aggregator / data**
- `doi_coverage` divides by matched metadata rather than needed iids, so it can
  overstate.
- CSV export drops line and book from the locus, so a band-level export loses
  the very distinction that scoped it.
- `niceTicks` can emit a tick above the plot top (cosmetic).
- Range citations like `80d5–e5` collapse to their start locus — a fine
  measurement decision, but it belongs in the methods page's list.
- `derive_book.py` is now a drift hazard against `locus.py`. Delete or stub it.

**To verify, not fix:** the data page publishes per-citation records including
article **titles and author strings from the JSTOR catalogue file** under CC BY
4.0. DOI clearance is on record; clearance for republishing catalogue metadata
in bulk under an open licence is not. Bibliographic facts are normally fine, but
TAS agreements sometimes have their own language about the metadata file. One
re-read of the terms before the draft banner comes off.

---

## Remediation order

The items are not independent; a couple change what the others should say.

1. **Queue filing rule** (Finding 1) — before any code. Determines whether
   `unplaceable`, `resolution_rate`, and tier assignments need recomputing, and
   settles whether the methods record needs correcting or just clarifying.
2. **Aggregator changes** — candidate-set `unplaceable`, corrected tooltip
   total, `doi_coverage` denominator, and a record of which works flipped tier.
   Add a printed invariant for the new quantity while in there; the data page
   already advertises that a bad run announces itself.
3. **View B bugs** (Finding 2) — the ones a visitor can see today. Small and
   mutually independent; the only real decision is 2b.
4. **`collision_bands.json` overlay + uncertain-tier copy** (Finding 3),
   together.
5. **Copy and framing** — `est_true` toggle or its absence explained, small-n
   caveat, the "demonstrably do not" claim.
6. **Polish**, batched — responsive TRACK, fetch `.catch`, resize rerender,
   touch tooltips, CSV locus fields, `derive_book.py` removal, range-citation
   note in methods.

## Decide before starting

- **Bar/heatmap semantics** (2b) — propagates to four surfaces. Settle once.
- **Fade cap vs rate-corrected mode** — may be one decision, not two.

## Caution for the next session

Several fixes correct things the handoff and methods documents currently assert
as **settled** — the non-exclusivity rationale most of all. Update those
documents in the same session as the code, or the next handoff will re-litigate
decisions from the superseded record. The live methods page needs the same
correction.
