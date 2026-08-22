---
title: Footnotes to Plato
subtitle: A passage-level citation index of five ancient authors across the journal literature
description: A passage-level citation index tracking how the journal literature cites Homer, Pindar, Plato, Aristotle and Paul — which works and passages draw scholarly attention, how that shifts over time, and how much of the picture is missing.
---

<div class="lede" style="font-family:var(--serif);font-size:19px;line-height:1.6">Welcome! <strong>Footnotes to Plato (and Others)</strong> is a tool for scholars in ancient philosophy, classics, theology, reception studies, intellectual history, history of the humanities, and digital humanities.</div>

<p class="lede">It tracks citations to five ancient authors—Homer, Pindar, Plato, Aristotle, and Paul—across a corpus of {{journal_count}} academic journals, published between {{year_from}} and {{year_to}}. Shoutout to the folks at JSTOR who kindly provided the data.</p>

<p class="lede">Three visualization tools let you analyze how scholarly attention distributes between and within texts at passage-level granularity, how that shifts over time, and how it differs from journal to journal and discipline to discipline.</p>

<p class="lede">For the list of journals covered see [the methods page](/methods/#coverage); for the full method see [methods](/methods/), and for the data, [the data page](/data/).</p>

<div class="figrow">
  <div class="fig"><div class="n">5</div><div class="l">ancient authors</div></div>
  <div class="fig"><div class="n">{{work_count}}</div><div class="l">texts indexed</div></div>
  <div class="fig"><div class="n">{{placed_total}}</div><div class="l">citations placed to a passage</div></div>
  <div class="fig"><div class="n">{{journal_count}}</div><div class="l">journals included</div></div>
  <div class="fig"><div class="n">{{year_from}}–{{year_to}}</div><div class="l">period covered</div></div>
</div>

<h4 style="font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-soft);border:0;margin:8px 0 0">The three tools</h4>

<div class="tools">
  <a class="tool" href="/explore/works/">
    <div><div class="thead"><span class="kk">Viewer A</span><span class="tt">Texts over Time</span></div>
      <p class="tbody">Plot whole texts, or clusters of them, against each other across two centuries. Set <em>Republic</em> beside <em>Laws</em>, or the Platonic corpus beside the Aristotelian, and watch the shares of attention rise and fall.</p>
      <span class="go">Open →</span></div>
  </a>
  <a class="tool" href="/explore/passages/">
    <div><div class="thead"><span class="kk">Viewer B</span><span class="tt">Passage-level attention distribution</span></div>
      <p class="tbody">Inside a single text: which pages, sections and lines the literature keeps returning to, and which it leaves alone. Drill through any passage to the articles that cite it, and export the list as a bibliography.</p>
      <span class="go">Open →</span></div>
  </a>
  <a class="tool" href="/explore/journals/">
    <div><div class="thead"><span class="kk">Viewer C</span><span class="tt">Comparing disciplines</span></div>
      <p class="tbody">Set two groups of journals against each other on a single text — philosophy beside theology, or any journals you pick — and see, passage by passage, which side leans into which. A diverging bar for every book or section, within the period you choose.</p>
      <span class="go">Open →</span></div>
  </a>
</div>

<div class="figure" style="margin-top:34px">
<h2 style="border:0;margin:0 0 6px">Three caveats, before you start</h2>

<div class="caveats">
  <div class="cv"><h4>Select journals ≠ the whole field</h4><p>Journal articles only — no monographs, edited volumes or commentaries, and with an Anglophone and European skew. Much influential work is simply absent from these counts.</p></div>
  <div class="cv"><h4>Uneven across two centuries</h4><p>The early decades are thin and most citations fall after 1980. A quiet early stretch reflects how little was published and digitized then, not a lapse in scholarly attention.</p></div>
  <div class="cv"><h4>Every count is a floor</h4><p>A bare reference like <em>80b</em> fits <em>Meno</em>, <em>Phaedo</em>, <em>Timaeus</em> or <em>Posterior Analytics</em> at once, and does not even declare which pagination it uses. Where the surrounding text does not settle it, we decline to guess.</p></div>
</div>

<div class="sampler">
  <div class="sh"><span class="t">What a floor looks like</span><span class="k">eight texts of {{work_count}}</span></div>
  <p class="intro">Solid is what we could place with confidence. The fade is traffic we detected but could not attribute — shared among the texts a bare page number could belong to, so it is an upper limit, never a subtotal. A short solid bar with a long fade means "much of its traffic couldn't be placed," not "little studied."</p>
  <div class="srows" id="fade-sampler">
    <noscript>The sampler requires JavaScript; the underlying numbers are on the <a href="/data/">data page</a>.</noscript>
  </div>
  <div class="sfoot">
    <span class="kk"><span class="sw" style="background:var(--p-floor)"></span>placed with confidence</span>
    <span class="kk"><span class="sw" style="background:linear-gradient(90deg,rgba(176,106,58,.5),rgba(176,106,58,0))"></span>detected, unresolvable</span>
    <a href="/methods/#floors-not-totals">All {{work_count}} texts, in Methods →</a>
  </div>
</div>
</div>

## Citing and contributing

If this contributed to published work, please cite as: *Kretz, David, Footnotes to Plato: A Passage-Level Citation Index for Ancient Texts,* Version 2.0, date. The derived data is [published for download](/data/) so results can be checked or reused.

**Publish or edit a journal you would like to see included?** Please [write to me](/contact/)! Corrections, methodological objections, and suggestions for additional features are also all very welcome.

## Acknowledgements

The pipeline, the analysis, and this website were developed with substantial assistance from Claude Opus 4.8 (by Anthropic) throughout. The responsibility for methodological decisions remains mine. I would like to thank the team at JSTOR Text Analysis Support for sharing the data that made this possible, and Joshua Mendelsohn for feedback on an earlier version.

<script>
/* The eight-text floor-vs-fade sampler (real: solid = placed floor, fade =
   unplaceable, from view_a.json). The full chart for all texts is on the
   methods page. */
(function(){
  var host=document.getElementById('fade-sampler');
  if(!host) return;
  var PICK=["Odyssey","Romans","Republic","Iliad","Timaeus","Phaedo","Apology","Meno"];
  fetch('/data/viewer/view_a.json').then(function(r){return r.json();}).then(function(D){
    var by={}; D.forEach(function(w){by[w.work]=w;});
    var rows=PICK.map(function(n){var w=by[n]||{floor:0,unplaceable:0};
      return {name:n,solid:w.floor||0,fade:w.unplaceable||0};});
    var max=rows.reduce(function(m,r){return Math.max(m,r.solid+r.fade);},1);
    host.innerHTML=rows.map(function(r){
      return '<div class="srow"><div class="sn">'+r.name+'</div>'
        +'<div class="strack"><span class="ssolid" style="width:'+(r.solid/max*100).toFixed(1)+'%"></span>'
        +'<span class="sfade" style="width:'+(r.fade/max*100).toFixed(1)+'%"></span></div>'
        +'<div class="sval">'+r.solid.toLocaleString()+'</div></div>';
    }).join('');
  }).catch(function(){ host.innerHTML='<p class="muted">Sampler unavailable — data not published yet.</p>'; });
})();
</script>
