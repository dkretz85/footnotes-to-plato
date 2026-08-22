---
title: Methods
subtitle: What's in the index, and how to read it
description: What Footnotes to Plato covers, how citations are placed, and what the numbers can and cannot be made to say.
---

*Footnotes to Plato* indexes how modern scholarship cites five ancient authors —
**Homer, Pindar, Plato, Aristotle, and Paul** — down to the individual passage.
It is built from the full text of scholarly journals: every citation of a
Stephanus page, a Bekker column, a book-and-line, or a chapter-and-verse is
extracted, placed to a specific work and passage, and counted.

This page says what the index covers, how a citation becomes a placement, and —
most important for anyone reading the charts — **what the resulting numbers can
and cannot be made to say.** Every figure is checkable against the
[published derived data](/data/).

The pipeline is **precision-first**: at each step the default is to decline
rather than guess. A citation that cannot be placed beyond reasonable doubt is
set aside in a review queue, not forced to a best guess. So every count on the
site is a **floor** — what could be placed with confidence — not an estimate.

## The corpus

The underlying data is a full-text delivery from JSTOR Text Analysis Support:
**{{n_articles}} articles** across **{{journal_count}} journals**, journal
articles only, spanning **{{year_from}}–{{year_to}}**. Because the text arrives
page by page, every citation's position within its article is known, and citation
strings appear verbatim in the text (`PLAT. MEN. 80D5`, `Il. 1.5`, `Rom 8:1`), so
there is no tokenisation to corrupt them.

The journals fall into three fields, which the filter panel in Viewers A and B
lets you select and compare:

- **Philosophy** — 7 journals (*Phronesis*, *History of Philosophy Quarterly*, and others).
- **Classics** — 18 journals (*The Classical Quarterly*, *Classical Philology*, *Hermes*, *Mnemosyne*, and others).
- **Theology & New Testament** — 23 journals (*Journal of Biblical Literature*, *Novum Testamentum*, *The Harvard Theological Review*, and others), themselves subdivided by discipline into biblical studies, theology & church history, and religious studies.

The full per-journal list, with each journal's citation count, is in the filter
panel of Viewers A and B.

**What this is not.** The corpus excludes monographs, edited volumes,
commentaries, and journals outside the JSTOR delivery — including *Oxford Studies
in Ancient Philosophy*, where a great deal of consequential work has appeared.
Coverage skews Anglophone. Treat the tool as a large **sample** of the field's
attention, not a census: a passage's absence here is not evidence that nobody has
written about it.

Coverage is also **uneven over time.** The journals are not evenly spread across
the span: the pre-1950 decades are thin, output climbs steeply from the late
1970s, and well over half of all placed citations fall after 1980. A flat or empty
early stretch in a time chart reflects how little was published and digitised
then, not a drop in attention — which is why the early series are noisier, and why
Viewer A offers smoothing.

## The three viewers

- **Viewer A — Texts over Time.** How much attention a whole text (or a cluster of
  texts) draws across the decades, as a share of the corpus. Plot *Republic*
  against *Laws*, or the Platonic corpus against the Aristotelian.
- **Viewer B — Passage-level attention.** Inside one text: which pages, sections,
  lines or verses the literature keeps returning to, and which it leaves alone.
  Every passage drills through to the articles that cite it, with a link to read
  the passage itself and an exportable bibliography.
- **Viewer C — Comparing disciplines.** How two freely chosen sets of journals
  divide their attention across a single text — philosophy beside theology, say —
  shown as a per-passage difference within the period you select.

## From text to placement

Citations reach the index in two forms, resolved differently:

- **Greek philosophers** (Plato, Aristotle) are cited by **Stephanus** page
  (`511d`) or **Bekker** page and column (`980b25`). These forms overlap and are
  often ambiguous — a bare `80b` with no work named could be *Meno*, *Phaedo*,
  *Timaeus*, or Aristotle's *Posterior Analytics*. Each is resolved against the
  reference ranges of every work and the work-names in the surrounding sentence,
  and is placed **only** when the evidence singles out one work. Everything below
  that bar goes to the review queue, tagged with its competing works.
- **Homer, Pindar, and Paul** are cited by an abbreviation that **names the work
  in the reference itself** (`Il. 1.5`, `Ol. 1.1`, `Rom 8:1`), plus a line or
  verse. These resolve on the cue, so they carry almost no ambiguity.

The single most consequential rule is the distinction between a work that is
*cited* and one merely *mentioned*: a citation is placed on the reference it
carries, not on whatever work happens to be named nearby. One corollary matters
for the charts — **how well a work resolves is a property of its page range, not
its importance.** *Crito* resolves at a lower rate than *Republic* not because it
is neglected but because its Stephanus range is crowded with other dialogues.

Non-citation content — back-of-volume indices, publication years, references to
other authors — is removed before placement, and every excluded row is kept with
its reason so the decision is auditable and reversible.

## Reading the numbers

A placement figure is a measure of **coverage, not accuracy**. "*Phaedrus* 61%"
would mean 61% of candidate *Phaedrus* citations were confidently placed; the rest
are *unplaced*, not *misplaced*. The placed set is clean but incomplete, and the
incompleteness is not spread evenly.

### Floors, not totals

Every count is a **floor** — what was confidently placed. Above each work's floor
sits a **fade**: the ambiguous citations whose candidate set *includes* that work.
The fade is deliberately **multi-counted** — a bare `80b` that could be *Meno*,
*Phaedo*, or *Timaeus* is counted in the fade of each — so it is an honest per-work
upper gesture ("attention here could be this much more"), but a quantity that
**must not be summed** across works. This is also why the site publishes no
per-work "resolution rate" and no reliability tiers: a colliding citation belongs
by construction to several works at once, and there is no neutral way to charge it
to one. Read a long fade as "much of this work's traffic could not be placed,"
**not** as evidence that the work is little studied.

Every text in the corpus, ranked by its confident floor, with the fade drawn to
scale beside it — the full version of the sample on the home page. Bars are
coloured by author; hover a row for its floor, distinct articles, and collision
partners.

<div class="figure">
  <div id="landing-bars">
    <noscript>The chart requires JavaScript; the underlying numbers are on the
    <a href="/data/">data page</a>.</noscript>
  </div>
  <div class="cap"><b>Solid</b> is what we could place with confidence;
  <b>fade</b> is detected-but-unresolvable traffic that could belong to this text,
  shared with its collision partners — an upper gesture, never a subtotal, and
  never summed across texts. A short solid bar with a long fade (like
  <em>Timaeus</em> or <em>Apology</em>) means "much of its traffic couldn't be
  placed," not "little studied." <b>The fade is almost entirely a Stephanus
  (Plato) phenomenon</b>: bare Stephanus pages like <em>80b</em> recur across
  dozens of dialogues, so a citation with no dialogue named is genuinely
  ambiguous. Bekker (Aristotle) numbers are mostly unique to one treatise, so
  Aristotle's fades are small; and Homer, Pindar and Paul name the work in the
  reference itself, so they have essentially no fade at all.</div>
</div>

<script>
(function(){
  var host = document.getElementById('landing-bars');
  if(!host) return;
  Promise.all([
    fetch('/data/viewer/view_a.json').then(function(r){ return r.json(); }),
    fetch('/data/viewer/authors.json').then(function(r){ return r.json(); }).catch(function(){ return null; })
  ]).then(function(res){ renderLandingBars(host, res[0], res[1]); })
    .catch(function(){ host.innerHTML = '<p class="muted">Chart unavailable — data not published yet.</p>'; });
})();
</script>
<script src="/static/landing-bars.js"></script>

### Within-work gaps: collision bands

Some works are well-placed overall but have sharp local drops where a stretch of
their pages collides with another work's range. These are marked as **collision
bands** in Viewer B — a short note that a page range is under-counted relative to
the rest of the text. The *Laws* IX–XII is the extreme case; most works flag none,
so their passage shape can be read end to end. Absence of a band means no
above-threshold pattern, not a proof of completeness.

### Small-n works, and the Homeric proem

A work — or a single passage — resting on very few citations should be read as an
**order of magnitude, not a precise count**. The exact number is always available
on hover. Relatedly, a few passages draw so much attention that they would flatten
the colour scale for everything else (the opening of the *Iliad* is the clearest
case); Viewer B's heatmaps scale their colour to the bulk of the data rather than
to that single spike, so ordinary variation stays legible.

Two housekeeping points. A queued (unplaced) citation carries a year and journal
but no *work*, so it counts in the corpus totals and the shared fade but never
enters a work's passage map. And **no verbatim article text is ever published**:
the citation context used during processing is confidential under the JSTOR
agreement and is dropped before anything shareable is written.

## Grouping schemes

**Works.** Viewer A lets you plot named sets of works — *Plato* (the 36 works
paginated by Stephanus), *Aristotle* (the 32 paginated by Bekker), the *Organon*,
the biological works, and so on; a few interpretive sets (the developmentalist
chronology of Plato) are marked *contested* and off by default. The full
definitions live in `work_groups.json` — each a common starting point, not an
endorsement.

**Journals.** Viewers A, B, and C group journals by field (Philosophy, Classics,
Theology & NT), with the theology journals subdivided by discipline. The
assignments live in the site data and can be adjusted; they are a convenience for
comparison, not a claim about where a journal "really" belongs.

## Reading the passage itself

Each passage in Viewer B links out to the text:

- **Greek works** frame the matching page of the
  [Perseus Digital Library](https://www.perseus.tufts.edu/hopper/), Tufts
  University — a finding-aid pointer, framed live, neither hosted nor mirrored
  here. Plato is fully covered; **Perseus's Aristotle holdings are thin** (six
  treatises), and Homer and Pindar link at the book/ode level. The strip always
  shows the exact citation it built, so a wrong mapping is visible, not silent.
- **Paul** links to [BibleGateway](https://www.biblegateway.com/) in the New
  Revised Standard Version, Updated Edition (NRSVUE).

## Known limitations

- **Bekker treatise boundaries** outside the *Parva Naturalia* are unverified at
  their exact edges; impact is confined to citations landing on shared pages.
- **Line numbers parse noisily in the Bekker (Aristotle) works,** so Aristotle's
  line detail is grouped into bands rather than shown line by line, with a
  separate cell for citations that give only a page.
- **The review queue** is genuine ambiguity — bare numbers with no name, scope, or
  title signal. It should not be force-resolved by heuristic.
- The index is a **sample of the discipline's journal literature**, not the whole
  of it; see the corpus caveats above.

## Checking the work

The [derived data is published](/data/) under CC BY 4.0. If you find an error,
[please tell me](/contact/) — corrections will be recorded and credited.

The pipeline, the analysis, and this site were developed with substantial
assistance from Claude (Anthropic) throughout; responsibility for the
methodological decisions is mine.
