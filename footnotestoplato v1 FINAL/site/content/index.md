---
title: Footnotes to Plato
subtitle: Which passages of Plato and Aristotle the scholarship cites — and which remain understudied
description: A passage-level citation index built from 135 years of ancient-philosophy journals. Explore which works and which passages draw scholarly attention, and see exactly how much of the picture is missing.
---

<p class="lede">This tool shows which works—and which passages—by Plato and
Aristotle receive the most scholarly attention, and which are relatively
understudied, for both philosophy and classics, for individual journals, across
135 years.</p>

<div class="statrow">
  <div class="stat"><div class="n">90,502</div><div class="l">citations placed to a passage</div></div>
  <div class="stat"><div class="n">68</div><div class="l">works of Plato &amp; Aristotle</div></div>
  <div class="stat"><div class="n">10</div><div class="l">journals</div></div>
  <div class="stat"><div class="n">1887–2022</div><div class="l">years covered</div></div>
</div>

## What this tool can do for you

- **Which passages receive the most scholarly attention?** See where, in a given
  work, scholarly attention spikes — for entire fields (philosophy/classics),
  specific journals, and periods.
- **How did attention to a work move over time?** Plot *Republic* against
  *Laws*, or the whole Platonic corpus against the Aristotelian, across 135
  years.
- **Do philosophers and classicists read the same passages?** Explore how the
  two fields' journals emphasize different parts of the same text.
- **Who cited this passage?** Create exportable bibliographies of all the works
  in the database that cite a specific passage, with one click.

## What it cannot tell you

- **Ten journals, not the field.** Journal articles only — no monographs, edited
  volumes, or commentaries — with an Anglophone skew, so much of the most
  influential work on Plato and Aristotle (which appeared in books) is simply
  absent. [The ten titles are listed on the methods page.](/methods/#coverage)
- **Uneven across 1887–2022.** The early decades are thin and most of the
  citations fall after 1980, so a quiet early stretch reflects how little was
  published then, not a lapse in attention.
- **Every count is a floor.** We placed {{placed_total}} citations to a specific
  passage, but {{queued_total}} more were detected and could not be uniquely
  resolved — usually because page numbers collide. A bare reference like *80b*,
  with no work named, fits *Meno*, *Phaedo*, *Timaeus* or *Posterior Analytics*
  at once, and does not even declare whether it is a Stephanus or a Bekker number
  to begin with; where the surrounding text does not settle it, we decline to
  guess. So a short bar can mean "rarely cited" or "we could not place it" — the
  two are always shown apart, and no number here is ever a total.
  [How resolution works →](/methods/#floors-not-totals)

## How much of the picture we actually have

Everything else on this site depends on this chart, so it comes first. Each bar
is a work; solid length is what we could place with confidence. The tail that
fades to nothing is citation traffic we detected but could not attribute — real
attention that belongs *somewhere*, but which we decline to assign.

<div class="figure">
  <div id="landing-bars">
    <noscript>The summary chart requires JavaScript. The underlying numbers are
    published on the <a href="/data/">data page</a>.</noscript>
  </div>
  <div class="cap cap-lg"><b>Reading this chart.</b> Works are ranked by their
  <b>solid floor</b> — the citations we could place with confidence. The
  <b>fade</b> is traffic we detected but could not attribute; it is shared among
  the works a bare page number could belong to, so it is an upper gesture, never
  a subtotal. Read the two together: a short solid bar with a <em>long</em> fade
  (like <em>Meno</em> or <em>Apology</em>, whose Stephanus page numbers collide
  with other dialogues) means "much of its traffic couldn't be placed," <b>not</b>
  that the work is little studied — while a short bar with little fade really is
  a quiet work. Because the fade is shared, don't compare bars by adding their
  fades, and treat every solid length as a floor.</div>
</div>

## Explore

<div class="cards">
  <a class="card" href="/explore/works/">
    <h3>Works over time</h3>
    <p>Plot attention to any work or group across 135 years. Compare
    <em>Republic</em> with <em>Laws</em>, Plato with Aristotle, or philosophy
    journals with classics journals.</p>
    <span class="go">Open →</span>
  </a>
  <a class="card" href="/explore/passages/">
    <h3>Passages</h3>
    <p>Inside a single work: which pages, sections and lines the literature
    returns to. Drill through any passage to the articles that cite it.</p>
    <span class="go">Open →</span>
  </a>
  <a class="card" href="/methods/">
    <h3>Methods</h3>
    <p>How citations were extracted, resolved, and audited — what the counts
    can support, and where the picture is thin.</p>
    <span class="go">Read →</span>
  </a>
</div>

## Citing and contributing

If this contributed to published work, please cite it with the version you used
— the corpus and the pipeline will both change, so a bare URL will not point a
future reader at what you actually saw. The durable route is a DOI via
[Zenodo](https://zenodo.org/), which archives a GitHub release and mints one;
until then, cite the URL and version. A recommended form: *Kretz, David.
Footnotes to Plato: A Passage-Level Citation Index of the Ancient-Philosophy
Scholarship. Version 1.0, 2026.* The derived data is
[published for download](/data/) so results can be checked or reused.

**Publish or edit a journal you would like to see included?** Please
[write to me](/contact/)! Corrections, methodological objections, and feature
suggestions are also all welcome.

## Acknowledgements

The pipeline, the analysis, and this site were developed with substantial
assistance from Claude Opus 4.8 (by Anthropic) throughout. The responsibility
for methodological decisions remains mine. I would like to thank the team at
JSTOR Text Analysis Support for sharing the data that made this possible, and
Joshua Mendelsohn for feedback on an earlier version.

<script>
/* The landing chart is the same View A bar chart, rendered read-only: no
   filter, no metric toggle, no interaction beyond the tooltip. Its job here is
   to frame everything else, so it should look like a figure, not a control
   panel. */
(function(){
  var host = document.getElementById('landing-bars');
  if(!host) return;
  fetch('/data/viewer/view_a.json').then(function(r){ return r.json(); })
    .then(function(d){ renderLandingBars(host, d); })
    .catch(function(){
      host.innerHTML = '<p class="muted">Summary chart unavailable — the '
        + 'derived data has not been published yet.</p>';
    });
})();
</script>
<script src="/static/landing-bars.js"></script>
