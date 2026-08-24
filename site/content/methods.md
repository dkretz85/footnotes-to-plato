---
title: Methods
subtitle: What's in the index, and how to read it
description: What Footnotes to Plato covers, how citations are placed, and what the numbers can and cannot be made to say.
---

*Footnotes to Plato (and Others)* shows how modern scholarship cites five ancient authors —
**Homer, Pindar, Plato, Aristotle, and Paul**. The basic idea is very simple. 
These ancient authors are not cited by page-number, which vary across editions, 
but standardized passage-numbers or even line-numbers. This makes it easy to 
machine-search a corpus of scholarly journals for citations, and count their 
distribution over time.  

This page explains in detail what the index covers, how citations were detected 
and placed, what the resulting numbers can and cannot be made to say. 
Every figure is checkable against the[published derived data](/data/).

## The corpus

The underlying data was provided by JSTOR's Text Analysis Support. I am very grateful
for their support. We got **{{n_articles}} articles** across **{{journal_count}} journals**,
spanning **{{year_from}}–{{year_to}}**. Because the text arrives page by page, every 
citation's position within its article is known. Citation strings appear verbatim 
in the text (`PLAT. MEN. 80D5`, `Il. 1.5`, `Rom 8:1`). This means no tokenization would corrupt them. 
Often, when we do computational text-analysis, text has to be 'tokenized'—broken down 
into computer-digestible chunks. But here, we did not have to do that; we could simply search 
the full text for patterns that match the canonical citation standards for Homer (Il./Od. Book.line), 
Pindar (Ol., Py. Ne. Is. + line), Plato (Stephanus number), Aristotle (Bekker number), 
Paul (chapter:verse). In each case, we accounted for variations on those standard patterns:
capitalization, Roman vs Arabic numerals, longer or shorter abbreviations, 
and differences across languages—English, French, German, Italian, Latin, Greek.

The journals fall into three fields, which the filter panel in Viewers A and B
lets you select and compare:

- **Philosophy** — 7 journals (*Phronesis*, *History of Philosophy Quarterly*, and others).
- **Classics** — 18 journals (*The Classical Quarterly*, *Classical Philology*, *Hermes*, *Mnemosyne*, and others).
- **Theology & New Testament** — 23 journals (*Journal of Biblical Literature*, *Novum Testamentum*, *The Harvard Theological Review*, and others), themselves subdivided by discipline into Biblical studies, theology & church history, and religious studies.

The filter panel of Viewers A and B is the fastest way to get a sense of the full list.

**Some caveats** Note that the corpus excludes monographs, edited volumes,
commentaries, and journals outside the JSTOR delivery — including, sadly, such 
Heavy-weights as *Oxford Studies in Ancient Philosophy*. Coverage skews Anglophone, 
although it includes some German, French, and Italian journals. It includes also 
book reviews, which provides a small window onto monographs. Treat the tool as a large 
sample of various fields' attention. Absence of evidence of scholarly attention 
should not be read as evidence of absence. 

Coverage is also uneven over time. The journals are not evenly spread across
the span: the pre-1950 decades are very thin. Output climbs steeply from the 1960s. 
Well over half of all placed citations fall after 1980. A flat or empty
early stretch in a time chart reflects how little was published and digitized
then, not a drop in attention. 

And two small caveats.

- Bekker treatise boundaries outside the *Parva Naturalia* are still unverified at
  their exact edges; impact is confined to citations landing on shared pages.
- Line numbers parse noisily in the Bekker (Aristotle) works, so Aristotle's
  line detail is grouped into bands rather than shown line by line, with a
  separate cell for citations that give only a page.

## The three viewers

- **Viewer A — Texts over Time.** How much attention a whole text (or a cluster of
  texts) draws across the decades, as a share of the corpus. Plot *Republic*
  against *Laws*, or the Platonic corpus against the Aristotelian—or Plato against 
  Paul!
- **Viewer B — Passage-level attention.** Inside one text: which books/chapter or
  lines/verses does the literature cite, and which does it mostly ignore.
  **Click on a passage drills to see the articles that cite it,** with a link to read
  the passage itself and create an exportable bibliography.
- **Viewer C — Comparing disciplines.** How two freely chosen sets of journals
  divide their attention across a single text. Pick journals of contrasting disciplines 
  — philosophy beside theology, say — or within a discipline, to see what passages
  they privilege, for a given period. 

## From text to placement

Citations reach the index in two forms, resolved differently:

- **Greek philosophers** (Plato, Aristotle) are cited by **Stephanus** page
  (`511d`) or **Bekker** page + column + line (`980b25`). These forms overlap and are
  often ambiguous — a bare `80b` with no work named could be *Meno*, *Phaedo*,
  *Timaeus*, or Aristotle's *Posterior Analytics*. Each is resolved against the
  reference ranges of every work and the work-names in the surrounding sentence,
  and is placed **only** when the evidence singles out one work. Everything below
  that bar goes to the review queue, tagged with its competing works.
- **Homer, Pindar, and Paul** are cited by an abbreviation that **names the work
  in the reference itself**, plus a line or verse: `Il. 1.5`, `Ol. 1.1`, `Rom 8:1`) 
  These resolve on the cue, so they carry almost no ambiguity. But note, of course, 
  where a work is cited only the first time by name, afterwards just by number, the 
  script picks up only the first citation. 

One important distinction here is between a work that is *cited* and one that is
*mentioned*: the index here is of citations, not mentions. Also, for Plato & Aristotle, 
how well a work resolves is a property of its page range, not its importance. *Crito* 
resolves at a lower rate than *Republic* not because it is neglected but because 
its Stephanus range happens to overlap with other dialogues.

Non-citation content — back-of-volume indices, publication years, references to
other authors — is removed before placement.

### Floors, not totals

To illustrate the issue of detectable-but-unplaceable citations, in the cases of 
Plato and Aristotle, consider the below graph. Solid bars are floors, fades indicate
citations that *could* belong to a work, technically, given its numeric range, but 
could also belong to others, and therefore could not be placed with confidence. 

The fade is deliberately **multi-counted** — a bare `80b` that could be *Meno*,
*Phaedo*, or *Timaeus* is counted in the fade of each — so it is an honest per-work
upper gesture ("attention here could be this much more"), but a quantity that
must not be summed across works. Read a long fade as "much of this work's traffic 
could not be placed," not as evidence that the work is little studied.

Every text in the corpus, ranked by its confident floor, with the fade drawn to
scale beside it — the full version of the sample on the home page. Bars are
coloured by author; hover a row for its floor, distinct articles, and collision
partners.

### Anaphoric citation

For Homer, Pindar, Paul, the script relies on work-name abbreviations to place a citation: e.g., an Odyssey book + line number (12.432) needs to be preceded by "Od." to be recognized by the script as an Odyssey citation. Of course, many articles practice anaphoric citation: the primary text is cited the first time, and following citations are given by book + line number only, or even just line numbers. We ran several statistical tests to see if the non-capture of anaphoric citations introduces systematic biases in the data (e.g., towards textually earlier passages). A combination of seven tests suggests that this is not the case. It does not bias the *distribution* of the citations (across passages, periods, or disciplines); it only lowers the absolute counts somewhat for these three corpora. Here as everywhere, numbers should be read as floors, not totals. See [here](/anaphoric-citation-validation.md/) for the full tests and figures.

See here for the full numbers.

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
order of magnitude, not a precise count. The exact number is always available
on hover. Relatedly, a few passages draw so much attention that they would flatten
the colour scale for everything else (the opening of the *Iliad* is the clearest
case); Viewer B's heatmaps scale their colour to the bulk of the data rather than
to that single spike, so ordinary variation stays legible.

## Grouping schemes

*Works.* Viewer A lets you plot named sets of works — *Plato* (the 36 works
paginated by Stephanus), *Aristotle* (the 32 paginated by Bekker), the *Organon*,
the biological works, and so on. Of course, all these groupings (e.g, the developmentalist
chronology of Plato) are controversial, are marked *contested* and off by default. 
Still, it seemed useful to offer a few convenient and conventional bundles. The full
definitions live in `work_groups.json`.

*Journals.* Viewers A, B, and C group journals by field (Philosophy, Classics,
Theology & NT), with the theology journals subdivided by discipline: again, a convenience 
for comparison, not a claim about where a journal "really" belongs. If you think I've
miscategorized a journal, please do let me know!

## Reading the passage itself

Each passage in Viewer B links out to the text:

- *Greek works* frame the matching page of the
  [Perseus Digital Library](https://www.perseus.tufts.edu/hopper/), Tufts
  University — a finding-aid pointer, framed live, neither hosted nor mirrored
  here. Plato is fully covered; **Perseus's Aristotle holdings are thin** (six
  treatises), and Homer and Pindar link at the book/ode level. The strip always
  shows the exact citation it built, so a wrong mapping is visible, not silent.
- *Paul* links to [BibleGateway](https://www.biblegateway.com/) in the New
  Revised Standard Version, Updated Edition (NRSVUE). 

NB: this part of the tool depends to an extent on how these other websites work and might
On occasion be a little buggy. I'll try to keep checking on it to keep it working. 

## Checking the work

The [derived data is published](/data/) under CC BY 4.0. If you find an error,
[please tell me](/contact/) — corrections will be recorded and credited.

The pipeline, the analysis, and this site were developed with substantial
assistance from Claude (Anthropic) throughout; responsibility for the
methodological decisions is mine.
