# Footnotes to Plato — handoff to Claude Code

*Written at the end of a chat-interface session that worked through
`AUDIT_HANDOFF.md`. Everything data-side was finished and verified against real
data; the viewer fixes were written but landed on the **wrong files** (see
"What went wrong" below). Companion to `AUDIT_HANDOFF.md`,
`SESSION_HANDOFF.md`, and `citation-pipeline-methods.md`.*

**Read this first, then `AUDIT_HANDOFF.md` for the original findings.**

---

## 0. Repository facts that caused the failure — verify these before editing

GitHub Pages serves from **`/docs`**, not the repository root.

| what | where |
|---|---|
| Live passages view | `docs/explore/passages/index.html` → `footnotes.dkretz.com/explore/passages/` |
| Live works view | `docs/explore/works/index.html` |
| Viewer JSON | `docs/data/viewer/` — fetched with **absolute** paths `/data/viewer/...` |
| **Stale prototypes** | `view_a.html`, `view_b.html` at repo root — **NOT SERVED, delete them** |

The root `view_a.html` / `view_b.html` are two-work standalone prototypes. An
entire session of fixes was applied to them before anyone noticed the live site
never loads them. **Delete both** so this cannot recur, or move them to
`prototypes/` with a README saying they are dead.

There are also (at least) two versions of `build_viewer_data.py`. The one in
the Claude Project is stale. The live one emits `view_a_filter.json`,
`journal_groups.json`, and `work_groups.json`, which the deployed viewers fetch
and the stale one does not produce. **Find the newest, confirm by checking it
emits those three files, and delete or clearly mark the rest.**

First action for Claude Code: inventory the tree. Locate every copy of
`build_viewer_data.py`, `view_a.html`, `view_b.html`, `index.html` under
`docs/explore/`, and the data directory. Establish which files the deploy
actually serves before changing a line.

---

## 1. What went wrong, so it doesn't repeat

The chat interface can only see files uploaded to the Project. Those had
drifted from the working tree. Consequences:

- Fixes were written against root prototypes that no user ever loads.
- The aggregator was patched from a stale copy that lacks the filter-bar outputs.
- Two `NameError`s reached the user because the pipeline could only be tested
  against a synthetic fixture, never the real 34 MB TSV.

Claude Code does not have these limits: it reads the working tree, can grep for
call sites before editing, and can run the pipeline on real data. **Use that.**
Before editing any viewer, confirm the file is the one the live URL serves.

---

## 2. Settled decisions — do not re-litigate

### 2.1 The queue filing rule (audit Finding 1) — RESOLVED

The record in `SESSION_HANDOFF.md` and the old aggregator docstring claimed
queue filing is **non-exclusive** (one citation filed under every candidate).
**That was false.** Confirmed two ways:

- Per-work `queued_total` sums to exactly 50,450; queue is 50,586 rows with 136
  blank `work_id`. Non-exclusive filing could not produce that.
- `resolve_citations.py` files under `sorted(candidates)[0]` in all three
  queueing branches:
  - line ~415 `name_multi_candidate` → `sorted(inter)[0]` (name-matched subset)
  - line ~420 `name_range_conflict` → `sorted(cand_set)[0]` (range candidates)
  - line ~454 `unresolved` / `cross_system_unresolved` → `cands[0]`

So filing is **exclusive and alphabetical**, over a *branch-dependent* candidate
set — which is why the audit's pure-alphabetical hypothesis broke on Gorgias.

Measured on real data: **97.7%** of multi-candidate rows (44,478 / 45,540) were
filed under the alphabetically-first candidate. Apology (0.255) and Meno (0.256)
had rates depressed by sorting before their collision partners.

**Correct these documents** — they still assert the false rationale:
`SESSION_HANDOFF.md`, the live methods page. (The aggregator docstring was
fixed but that fix is on the stale copy; re-apply.)

### 2.2 The two quantities must stay separate — THE key invariant

A first attempt at the Finding 1 fix used candidate-set membership as the
denominator of `resolution_rate`. **This is wrong and produced garbage:**
Republic 0.95 → 0.508, Minos 1.00 → 0.082, 19 works flipped out of the
trustworthy tier, all in one direction, and the bimodal histogram collapsed.

Mean candidate-set size is **3.09 works per queued row**, so every denominator
inflated ~3× and every rate collapsed. A rate is a proportion; its denominator
must count each row once.

| quantity | counter | multi-counts? | why |
|---|---|---|---|
| `resolution_rate` denominator | **filed** (exclusive) | no | it is a proportion |
| `unplaceable` / the fade | **candidate-set** | yes, intentionally | a shared citation really could belong to each candidate |

**All-one-way tier movement is the signature of a broken denominator.** If a
future change produces it, that is the first thing to check.

Report the filing bias rather than substituting a non-proportion: each work
carries `filed_share_of_candidates` = filed ÷ candidate-set count. High values
mean the work's rate is depressed by alphabetical luck.

### 2.3 Result: tiers are ROBUST — a strong sentence for the methods page

After dropping confident negatives and recomputing `unplaceable` from candidate
sets: **1 tier flip** (Rival Lovers, uncertain → trustworthy, 0.471 → 1.000),
27 trustworthy vs 41 uncertain (was 26/42). Histogram still bimodal: 25 works
at 90–99%, empty valley at 60–89%, dense mass below 50%. The 0.80 cut sits in
the valley.

This is publishable: *tier assignments survive correcting for filing order.*
Note Rival Lovers is small-n — verify its floor before trusting the flip.

### 2.4 Queue dispositions

| method | rows | disposition |
|---|---|---|
| `name_range_conflict` | 24,458 | candidate-set membership |
| `cross_system_unresolved` | 13,202 | candidate-set membership |
| `unresolved` | 5,392 | candidate-set membership |
| `name_multi_candidate` | 2,624 | candidate-set membership |
| `scope_range_mismatch` | 3,668 | **excluded from `unplaceable` entirely** |
| `scope_inherited` | 1,242 | left queued — promotion tested and rejected |

`scope_range_mismatch` = scope named a work, number falls outside that work's
range → a **confident negative**. Filing confident negatives under the very
work they were proven not to belong to would inflate the fade that means "could
be more of *this* work." They stay in the queue file; they contribute to
nothing. Caveat for the methods page: *"not Republic" is not "not a citation"* —
they may be real loci of some other work.

### 2.5 The scope promotion — asked, answered, closed

Idea: promote `scope_inherited` rows (work named, number in range, only
confidence failed) to resolved where the page admits exactly one work.
`promote_scope.py` implements and tests it. **Result on real data: 0 of 1,242
promotable.** Every row has 2–5 candidate works. Do not revisit.

Why, measured from the range tables:

- **Stephanus self-collision:** 514 of 986 pages (52%) covered by >1 dialogue,
  up to 3 deep. **29 dialogues have no page uniquely their own** — Meno,
  Timaeus, Apology, Gorgias, Phaedrus, Symposium, Theaetetus among them.
- **Cross-system collision:** 903 of 1,363 Bekker pages (66%) also exist as
  Stephanus pages. **26 treatises sit entirely inside that zone** — Physics,
  De Anima, Posterior Analytics, Topics, Categories, Historia Animalium. Only
  works above Stephanus p. 992 (Metaphysics, NE, EE, Politics, Rhetoric,
  Poetics) are unambiguous by number alone.
- The section letter helps in one direction only: c/d/e excludes Bekker
  (Bekker has columns a/b only); a/b excludes nothing. For a/b or no letter in
  the collision zone, uniqueness is **0 of 903 pages**.

Keep `promote_scope.py` in the repo as the record that the question was asked
and answered against data.

### 2.6 Bar/heatmap semantics (audit 2b) — DECIDED

**Both surfaces show distinct-article-per-locus.** That is what the drill panel
and the CSV export already list. The user's rationale: a single article citing
a passage ten times inflates apparent attention unrealistically.

Consequence: the metric toggle ("Citations" / "Distinct articles") becomes two
labels for one quantity. Hide it rather than leave a dead control. Total counts
drop visibly (NE ~6,730 → the distinct-article sum) — correct, not a regression,
but the data page's description of `view_b/<work>.json` and the homepage's
1097b figure both need updating.

This also **obsoletes the `#fbCaveat` warning** at ~line 509 of the deployed
passages file, which currently explains that filtered citation counts run
15–20% low. Its own comment says the proper fix belongs in the aggregator. Once
both surfaces dedupe, delete the warning.

---

## 3. Work to redo against the correct files

All four View B bugs and both View A polish items are **confirmed present** in
the deployed files. Verified line numbers as of this handoff:

### `docs/explore/passages/index.html`

**2a — drill panel overcounts.** Dots deduped by `(iid,page,section,line)` but
the drill reports `dots.length`. Verified against real NE data:

| passage | reported | true distinct |
|---|---|---|
| NE 1097b | 91 | **53** |
| NE 1147b | 48 | **37** |
| NE 1139b | 71 | **52** |

1097b is the flagship passage cited on the homepage. Fix: count distinct iids;
group the list by article, showing each once with its loci.

**2b — bars vs heatmap disagree.** Bars from `cells` (raw rows), heatmap from
deduped `dots`. **159 of NE's 183 sections** disagree; 1097b reads 179 vs 91.
Fix per §2.6: build section values from deduped dots.

**2c — line-less citations inflate band 1.** Line ~949: `bandOf(null)` returns
`0`, so citations with no line number render in band ₁ (lines 1–15) and drill
in labelled "1097b₁" as if line-specific. **740 of 5,499 NE dots (13.5%)**; 16
of the 91 at 1097b. Fix: fourth `UNSPEC` band, distinctly labelled (never "₁").

**2d — 29 of 32 Aristotle works on the wrong grid.** Line ~952:
`isBekker()` hardcodes `["Metaphysics","Nicomachean_Ethics","Eudemian_Ethics"]`
and is used for *two different questions* at lines ~897–898: which pagination
system (a/b vs a–e) and whether to draw line bands. Every other Aristotle work
falls through to the Stephanus a–e grid with three permanently empty columns.

**18,815 citations affected**: Politics 3,525 · Physics 2,433 · De Anima 2,200 ·
Rhetoric 1,782 · Poetics 1,512 · Posterior Analytics 985 · Topics 866 · Prior
Analytics 626 · De Caelo 569 · Meteorology 510 · Categories 122 · and 18 more.

Fix: split into two predicates sourced correctly —
- `paginationOf(work)` from the author/edition map (`AUTHORS_INLINE`, already
  inlined in the works view). Bekker → `["a","b"]`, Stephanus → `["a".."e"]`.
- `hasLineBands(work)` from `current.faceted` in the data, not a hardcoded list.

The map is currently duplicated between the two viewers. Define it once.

### `docs/explore/works/index.html`

- Line ~423: tooltip total is `floor + unplaceable`, omitting `band_extra`, so
  "≈X if all belonged here" is short by the whole band segment.
- Line ~333: bar scale has the same omission; band segments can overrun.
- Line ~335: `TRACK = 740` hardcoded, no responsiveness — bars overflow on
  narrow screens. Measure the grid column instead.
- Line ~406: fade capped at 320 px, so Apology's 5,084 and a much smaller mass
  render identically. Decide alongside the `est_true` toggle (§4).

### Both viewers

- `fetch` calls need `.catch` with a **visible** failure message (there was an
  earlier silent-404 incident).
- Hover-only tooltips exclude touch devices.
- Charts don't re-render on resize.
- CSV export drops book and line, so a band-level export loses the distinction
  that scoped it.
- `niceTicks` can emit a tick above the plot top (cosmetic).

**Do not overwrite the deployed files with the root prototypes.** The deployed
versions are ahead in ways the prototypes are not: a shared journal/year filter
bar (`view_a_filter.json`, `journal_groups.json`, `work_groups.json`),
`READING_ORDER`, absolute `/data/viewer/` paths, and the `#fbCaveat` system.
Port the fixes *onto* the deployed files.

---

## 4. Audit items still open

Numbering follows `AUDIT_HANDOFF.md`.

**Finding 3 — collision bands overlay.** `collision_bands.json` exists (21
bands, 12 works), is copied through by the aggregator, and **is not rendered**.
The uncertain-tier banner says "trust the *shape*", which methods §6.1 says is
exactly what is unsafe for these works. Note **3 of the 12 flagged works are
trustworthy-tier** — Laws (7 bands, ~348 est. missing), Parmenides, Republic —
so this is not only an uncertain-tier caveat. Largest: Phaedo (~874 missing,
pages 50–69), Phaedrus (~530, pages 250–269). Overlay and copy edit must land
**together**.

**Finding 3 — small-n.** The tier conflates rate with sample size. Trustworthy
tier spans **30 to 12,350** citations. Minos (floor 30, rate 1.000), Theages
(39), Rhetorica ad Alexandrum (66) sit in "publication grade" beside Republic.
Threshold of 100 flags exactly those three. Rival Lovers (§2.3) makes this
urgent. Needs a badge, visual de-emphasis, and a note.

**Finding 3 — `est_true` toggle.** Within-tier rates range 80–98%, so raw
floors misstate relative volume by up to ~20%. Methods §6.2 defines the
rate-correction and it appears nowhere in the viewer. **Decide together with
the fade cap** — if View A gains a rate-corrected mode the fade may become
redundant.

**Finding 4 — "demonstrably do not."** The homepage claims philosophers and
classicists demonstrably read different passages. Needs a **within-period**
comparison first: journals differ enormously in era (~83% of Classical Review's
excluded material was pre-1910) and genre (reviews vs articles cite
differently). A raw by-journal split shows differences even if the fields read
identically, because attention moved over 135 years. This is real analysis, not
a sentence fix — the audit says waiting beats rewording.

**Finding 5 — smaller items.** `derive_book.py` is a drift hazard against
`locus.py`; delete or stub it. Range citations (`80d5–e5`) collapse to their
start locus — fine, but belongs in the methods page list. **Verify, not fix:**
the data page publishes article titles and author strings from the JSTOR
catalogue under CC BY 4.0; DOI clearance is on record, bulk catalogue-metadata
clearance is not. Re-read the TAS terms before the draft banner comes off.

**Prose/code separation.** A `copy.json` was designed and built (see repo root
or ask the user) externalising all user-facing strings, so the user can edit
prose on GitHub while code changes land independently. It was applied to the
root prototypes only. Suggested sequence: land the bug fixes on the deployed
files first, verify visually, *then* do the prose refactor as a separate pass —
easier to review than four bug fixes plus a refactor at once.

---

## 5. Aggregator changes to re-apply

These were written and tested against the **stale** `build_viewer_data.py`.
Re-apply to the live one (the one emitting the filter-bar files).

1. **`profile_queue` returns two counter families** —
   `(q_filed, q_cand_total, q_cand_band, q_cand_unpl, collides, samples, stats)`.
   `q_filed` is exclusive (one row, one work) and is the **rate denominator**.
   `q_cand_*` are candidate-set memberships and drive the **fade**. See §2.2.
2. **Skip `scope_range_mismatch`** rows entirely (§2.4).
3. **Candidate-set attribution** — attribute each row to every work in
   `parse_candidates(reason)`; fall back to the filed work when no candidate
   list is present (the `scope_*` methods, 1,242 rows).
4. **Per-work fields**: `queued_filed`, `queued_as_candidate`,
   `filed_share_of_candidates`, `collision_bands`, `band_est_missing`,
   `small_n` (threshold via `--small-n-threshold`, default 100).
5. **`meta.json`**: `total_queued` must be the **exclusive** count (reconciles
   with the queue file); expose the multi-counted figure separately as
   `total_candidate_attributions`. Getting this wrong publishes 144,330 where
   46,782 belongs, silently.
6. **`doi_coverage`** divided by `len(meta)` (matched iids) — overstates.
   Divide by `len(needed)`; keep the old value as `doi_coverage_of_matched`
   and add `meta_match_rate`.
7. **Printed invariants**, because the data page advertises that a bad run
   announces itself:
   - accounting check: `blank + negatives + with_candidates + fallback == rows_read`
   - `filed_total == rows_read - blank - negatives` — **this is the check that
     would have caught the broken-denominator bug**
   - mean works per queued row (expect ~3.09)
   - filed-as-first-candidate percentage (expect ~97.7%)
8. **Tier-flip report** against `viewer_data/view_a.prev.json` if present.

Expected output on a correct run:

```
  46,782 queued rows across 61 works
    rows read                     : 50,586
    blank work_id (skipped)       : 136
    confident negatives (dropped) : 3,668
    rows with candidate sets      : 45,540
    rows falling back to filed    : 1,242
    total attributions            : 144,330
    filed rows (rate denominator) : 46,782
    filed count checks out (= rows - blank - negatives)
    filed as FIRST of >1 candidates: 44,478 (97.7%)
    mean works per queued row     : 3.09
  TIER FLIPS: 1
  trustworthy: 27   uncertain: 41
```

If `total_queued` reads 144,330, the denominators are broken.

---

## 6. Verification checklist

Fixes are only real once visible at `footnotes.dkretz.com/explore/passages/`.
After deploying, in a private window (cache has already caused one false alarm):

- [ ] **Posterior Analytics** — two columns (a/b), not five. The single
      clearest tell for 2d.
- [ ] **NE 1097b drill** — 53 articles, not 91.
- [ ] **NE 1097b bands** — four bands, the fourth labelled as unspecified, not
      "₁". Before the fix the bands read 117 / 53 / 8.
- [ ] **Bar at 1097b** equals the sum of its heatmap cells.
- [ ] **Phaedo or Republic** — collision-band overlay visible (once built).
- [ ] **Works view** — Minos, Theages, Rhetorica ad Alexandrum marked small-n.
- [ ] **Filter bar still works** — the deployed viewers' journal/year filter
      must survive the port.
- [ ] Totals dropped relative to before. Expected (§2.6), but update the data
      page and homepage figures to match.

---

## 7. Suggested order

1. Inventory the tree; establish which files are live; delete the root
   prototypes and any stale `build_viewer_data.py` (§0).
2. Re-apply aggregator changes to the live script; run on real data; check the
   invariants against the expected output above (§5).
3. Port the four View B bugs onto `docs/explore/passages/index.html` (§3).
   Deploy and verify **Posterior Analytics** before doing anything else.
4. View A polish onto `docs/explore/works/index.html` (§3).
5. Collision-bands overlay + small-n, with their copy, landing together (§4).
6. Correct `SESSION_HANDOFF.md` and the live methods page (§2.1), and record
   the robustness result (§2.3).
7. Then the open questions: `est_true` + fade cap as one decision, and Finding
   4's within-period comparison.
