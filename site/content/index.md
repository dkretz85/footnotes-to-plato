---
title: Footnotes to Plato
subtitle: Which passages of Plato and Aristotle the scholarship actually cites — and which it only appears to
description: A passage-level citation index built from 135 years of ancient-philosophy journals. Explore which works and which passages draw scholarly attention, and see exactly how much of the picture is missing.
---

<p class="lede">Scholarship on ancient philosophy leaves a trail. Every article
that cites <em>Republic</em> 509d or <em>Nicomachean Ethics</em> 1097b marks a
passage as worth arguing about. Collected across 135 years of journals, those
marks form a map of what the field has attended to — and what it has passed
over.</p>

<p class="lede">This tool draws that map at the level of the individual passage,
and links each mark back to the article that made it.</p>

<div class="statrow">
  <div class="stat"><div class="n">90,502</div><div class="l">citations placed to a passage</div></div>
  <div class="stat"><div class="n">68</div><div class="l">works of Plato &amp; Aristotle</div></div>
  <div class="stat"><div class="n">10</div><div class="l">journals</div></div>
  <div class="stat"><div class="n">1887–2022</div><div class="l">years covered</div></div>
</div>

## What you can ask it

- **Which passages of a work carry the argument?** *Nicomachean Ethics* Book VI
  and the *ergon* argument at 1097b draw far more citation traffic than the
  surrounding text. The passage map shows that shape for any work in the corpus.
- **How did attention to a work move over time?** Plot *Republic* against
  *Laws*, or the whole Platonic corpus against the Aristotelian, across 135
  years.
- **Do philosophers and classicists read the same passages?** They demonstrably
  do not. The two fields' journals emphasise different parts of the same text,
  and the comparison makes that visible.
- **Who cited this passage?** Every cell drills through to the citing articles,
  with DOI links out to JSTOR.

## What it cannot tell you

This is the part worth reading before the charts.

<div class="callout warn">
<h4>Coverage</h4>
<p>Ten journals is not "the scholarship." The corpus is
<strong>journal articles only</strong> — no monographs, no edited volumes, no
commentaries, and no <em>Oxford Studies in Ancient Philosophy</em>. It skews
Anglophone. A great deal of the most influential work on Plato and Aristotle has
appeared in books, and none of that is here.</p>
<p>What the tool measures precisely is <strong>citation traffic in these ten
journals</strong>. Treat it as a large sample of the field's attention, not a
census of it.</p>
</div>

<div class="callout warn">
<h4>Placement, not accuracy</h4>
<p>Of roughly 141,000 detected citations, <strong>90,502 could be placed</strong>
to a specific work and passage. The rest could not — usually because page
numbers collide between works, not because the citations are bad. A short bar
below may mean "rarely cited" or it may mean "we could not place it." The
difference is always shown, never hidden.</p>
</div>

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
  <div class="cap"><b>Reading this chart.</b> Works are split into two tiers.
  For the <b>trustworthy</b> tier, at least 80% of detected citations resolve to
  a passage, and bar lengths can be compared directly. For the
  <b>uncertain</b> tier, fewer do — so a short solid bar means the placement
  failed, <b>not</b> that the work is little studied. <em>Meno</em>,
  <em>Crito</em> and <em>Apology</em> sit in the second tier because Stephanus
  page numbers in their range collide with other dialogues, not because they are
  neglected. Colour follows the reference edition a citation uses — Stephanus or
  Bekker — which is how the scholarship addresses these texts, and is not a claim
  about authorship.</div>
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
    <p>How citations were extracted, resolved, and audited — including
    everything that went wrong and what was done about it.</p>
    <span class="go">Read →</span>
  </a>
</div>

## Citing and contributing

If you use this in published work, please cite it — see
[how to cite](/about/#how-to-cite). The derived data is
[published for download](/data/) so that results can be checked or reused.

**Publish or edit a journal you would like to see included?**
[Write to me](/contact/). I cannot add titles unilaterally — the corpus came
through a JSTOR Text Analysis Support agreement, and expanding it means going
back to JSTOR and the publisher — but I would like to know which journals
scholars want represented, and an approach from an editor carries considerably
more weight than one from me.

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
