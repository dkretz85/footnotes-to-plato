---
title: Methods
subtitle: How the numbers were made, and how far they can be pushed
description: Pipeline, resolution logic, data quality, and known limitations for the Footnotes to Plato citation index.
---

This is the short version. A [fuller pipeline and methods
record](/methods/pipeline/) documents the extraction, resolution, and
data-quality work in detail.

## The pipeline in brief

1. **Delivery.** A full-text corpus from JSTOR Text Analysis Support:
   {{n_articles}} articles across ten journals of ancient philosophy and classics.
2. **Extraction.** Candidate citation strings are pulled from article body text
   by shape — Stephanus (`509d`), Bekker (`1097b12`), and named-work forms.
   Roughly 141,000 genuine candidates survive filtering.
3. **Resolution.** Each candidate is matched against reference tables of work
   boundaries. Where the locus falls unambiguously inside one work, it is
   placed. Where it does not, it is set aside in a review queue with the
   competing works recorded.
4. **Aggregation.** Placed citations are counted per work, per passage, per
   journal, and per year, and joined to article metadata for DOI links.

The governing principle is **precision first**: at every stage the default is to
decline rather than guess, and every exclusion is diverted to an auditable file
rather than deleted.

## What "placed" means

Of roughly 141,000 detected citations, **{{placed_total}} (64%) were placed** to
a specific work and passage. The rest are neither errors nor lost — they are held
in a review queue with their candidate works recorded.

The dominant reason a citation cannot be placed is **collision**. Stephanus
pagination runs across the Platonic corpus in a way that repeats page numbers, so
a citation to "80b" with no work named could belong to *Meno*, *Apology*, or
several other dialogues; Bekker and Stephanus numbers also overlap. Where the
surrounding text does not settle it, the pipeline declines to choose.

This has a consequence worth keeping in mind: **how well a work resolves is a
property of its page range, not of its scholarly importance.** *Crito* resolves
at a low rate not because it is neglected but because its Stephanus range is
crowded with other dialogues.

## Floors, not totals

Every count on this site is a **floor** — the citations we could place with
confidence. It is always a lower bound, never a total.

We deliberately do **not** publish a per-work "resolution rate" or sort works
into reliable and unreliable tiers. The reason is that there is no neutral way to
turn the queue into a per-work percentage. A rate would need a denominator — the
work's own share of the ambiguous citations — but an ambiguous citation like
`80b` belongs, by construction, to *several* works at once, and any rule for
awarding it to one of them is arbitrary. An earlier version of this project filed
each queued citation under the alphabetically-first of its candidate works; that
made a work's apparent rate depend on where its **name fell in the alphabet**.
*Timaeus*, which sorts late, was charged for almost none of the ambiguous
citations it shares and so looked 98% resolved; *Apology*, which sorts early, was
charged for nearly all of its own and looked 26% — when a symmetric split puts
both near the middle. Rather than dress an alphabetical accident as a
measurement, we retired the rate and the tiers.

In their place each work shows two honest quantities:

- a **solid floor** — what we placed; and
- a **fade** — the ambiguous citations that *could* belong to it.

The fade is **shared**. The same bare `80b` is counted in the fade of every
dialogue it might name, on purpose, because any one of them could be its true
home. Shared quantities cannot be added: there is no single "estimated true
total" anywhere on the site, and two works' fades must never be summed. Read the
floor as a firm lower bound; read a long fade as "much of this work's traffic
could not be placed," **not** as evidence that the work is little studied. A work
with a short floor and a long fade should not be ranked against a work with a
solid floor on bar height alone.

## Small-n works

A handful of works carry very few placed citations — under about a hundred. Their
bars should be read as an **order of magnitude, not a precise count**: a work
resting on thirty citations can swing on chance, and its short bar should not be
compared closely with the long ones or ranked among them. The count itself is
always shown, so a thinly-cited work never masquerades as a heavily-cited one.
This is surfaced in the summary chart's hover rather than as a persistent badge:
it is worth having when you inspect a specific work, but it is a minor property
and does not deserve the visual weight of a major one.

## Collision bands

Within a single work, missingness is usually spread evenly across its pages — so
the *shape* of attention (which passages are cited more) survives even where the
overall floor is low. A few works are the exception: they have a **specific
stretch of pages** that resolves worse than the rest, almost always a Stephanus
or Bekker range that collides with another work. These are the collision bands
(machine-readable in `collision_bands.json`). Where they exist, the passage map
marks the affected pages and notes them in one line beneath the chart, because
across those pages the shape is depressed rather than merely lower.

They are a **localised** caveat, which is why they do not lead the per-work view.
The most band-heavy work is the *Laws*: seven contiguous bands across Books IX–XII
(Stephanus 860–959) account for an estimated 348 unplaced citations — under a
tenth of the work's placed total, spread thin. *Phaedo* 60–69 is the single
highest-impact band. Most works flag none at all: 47 of 59 measured works have no
band, and their within-work shape can be read as-is. The full band table and the
detection method are in the [pipeline record](/methods/pipeline/#reading-the-results).

## Grouping schemes

Several of the groupings offered in the time chart are **interpretive, not
neutral**, and are tagged *contested* in the picker:

- **The developmentalist chronology** (early / middle / late Plato) is the
  standard ordering, but unitarian readers reject the premise that Plato's
  thought develops across datable periods at all, and stylometric and doctrinal
  datings disagree at the edges. Plotting "early Plato" plots an interpretation
  of the corpus, not a fact about it.
- **The theoretical / practical division** is Aristotle's own for his works;
  applied to Plato it is a borrowed heuristic he does not draw himself, and
  several dialogues resist it (the *Republic* is both at once).

For a scholarly audience the *contested* tag is flag enough, so the chart does
not spell the dispute out in a warning box each time. The grouping definitions
live in `work_groups.json`.

## Coverage

The corpus is **ten journals, journal articles only, 1887–2022**:

- *Phronesis*
- *The Classical Quarterly*
- *Classical Philology*
- *Méthexis*
- *Revue de Philosophie Ancienne*
- *History of Philosophy Quarterly*
- *The Classical Review*
- *Revue Internationale de Philosophie*
- *Les Études philosophiques*
- *Archivio di Filosofia*

That excludes monographs, edited volumes, commentaries, and journals outside the
JSTOR delivery — including *Oxford Studies in Ancient Philosophy*, where a great
deal of consequential recent work has appeared. Coverage skews Anglophone. Treat
the tool as a large sample of the field's attention, not a census of it; see also
[scope](/about/#scope-and-its-limits).

Coverage is also **uneven over time.** The journals are not evenly spread across
the 1887–2022 span: the pre-1950 decades are thin, output climbs steeply from the
late 1970s, and well over half of all placed citations fall after 1980. A flat or
empty early stretch in the time chart therefore reflects how little was published
and digitised then, not a drop in attention — which is why the raw series are
noisier before 1950, and why the smoothing options exist.

## What is deliberately not shown

- **Unplaceable citations have no year or journal breakdown.** A citation we
  could not attribute to a work cannot honestly be attributed to a decade
  either. When you filter by year, the fade therefore stays at full width and
  turns grey rather than shrinking with the bars.
- **The queue holds two different quantities, and only one is comparable across
  works.** Each queued citation is *filed* under exactly one work internally, so
  the raw queue totals sum cleanly — but that filing is arbitrary (see
  [Floors, not totals](#floors-not-totals)), so it is never shown. What the fade
  displays instead is *candidate-set membership*: a citation whose page number
  collides across several works is counted against each of them, on purpose. Those
  memberships overlap and must not be summed.
- **No verbatim article text.** The citation context extracted during processing
  is confidential under the JSTOR agreement and is dropped before anything is
  written to a shareable file.

## Known limitations

- Coverage is ten journals, articles only, Anglophone-skewed, and uneven over
  time — see [Coverage](#coverage) above.
- Book divisions for faceted works are editorial conveniences; passage positions
  are exact, book boundaries are a display choice.
- Line numbers parse noisily in the Bekker works, so line-band detail is
  grouped rather than exact.
- Several Aristotelian treatise boundaries outside the *Parva Naturalia* remain
  to be verified against a concordance; see the
  [full record](/methods/pipeline/#known-limitations).

## Passage links (Perseus)

Each passage in the [passage viewer](/explore/passages/) carries a collapsed
"View passage on Perseus" strip that frames the matching page of the
[Perseus Digital Library](https://www.perseus.tufts.edu/hopper/), Tufts
University. This is a **finding-aid pointer only**: the text is Perseus's, framed
live from its reading view, and is neither hosted nor mirrored here. Each work is
mapped to its Perseus text-document ID, and the passage address is built from the
locus — section-level (e.g. 80a) for the Platonic dialogues, Bekker page for the
Aristotelian treatises.

One real limitation attaches to it: **Perseus's Aristotle coverage is thin.**
All 36 Platonic works are present, but of the Aristotelian corpus Perseus holds
only six — the *Nicomachean* and *Eudemian Ethics*, *Metaphysics*, *Rhetoric*,
*Poetics* and *Politics*. The other treatises (the *Physics*, *De Anima*, the
*Organon*, the biological and *Parva Naturalia* works, and more — about **13% of
all placed citations**) have no Perseus text at all, and the strip says so
rather than linking to nothing. The strip also always shows the exact citation it
built, so if a mapping is ever wrong it is visible on screen rather than silent.

## Checking the work

The [derived data is published](/data/) under CC BY 4.0, and the pipeline is
open source. If you find an error, [please tell me](/contact/) — corrections
will be recorded and credited.
