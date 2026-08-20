---
title: Methods
subtitle: How the numbers were made, and how far they can be pushed
description: Pipeline, resolution logic, data quality, and known limitations for the Footnotes to Plato citation index.
---

This page is the short version. The [full pipeline and methods
record](/methods/pipeline/) documents the build as actually executed —
including the bugs found, the assumptions tested, and the things still
outstanding.

## The pipeline in brief

1. **Delivery.** A 381 MB gzipped full-text corpus from JSTOR Text Analysis
   Support: 69,177 documents across ten journals.
2. **Extraction.** Candidate citation strings are pulled from article body text
   by shape — Stephanus (`509d`), Bekker (`1097b12`), and named-work forms.
   Roughly 141,000 genuine candidates survive filtering.
3. **Resolution.** Each candidate is matched against reference tables of work
   boundaries. Where the locus falls unambiguously inside one work, it is
   resolved. Where it does not, it goes to a review queue with the competing
   candidates recorded.
4. **Aggregation.** Resolved citations are counted per work, per passage, per
   journal and per year, and joined to article metadata for DOI links.

The governing principle is **precision first**: at every stage the default is to
decline to resolve rather than guess, and every exclusion diverts data to an
auditable file rather than deleting it.

## What "placed" means

Of about 141,000 candidates, **90,502 (64%) were placed** to a specific work and
passage. The other 36% are not errors and are not lost — they are recorded in
the review queue with their candidate works.

The dominant reason for non-placement is **collision**. Stephanus pagination
runs continuously across the Platonic corpus, so a citation to "80b" with no
work named could belong to *Meno*, *Apology*, or several others. Where the
surrounding text does not disambiguate, the pipeline declines to choose.

This has an important consequence for reading the charts: **placement rate is a
property of a work's page range, not of its scholarly importance.** *Crito*
places at 20% not because it is neglected but because its Stephanus range is
crowded.

## The two tiers

Works are split at an **80% placement rate**:

- **Trustworthy** (26 works) — at least 80% of detected citations resolve.
  Bar lengths and time series can be compared directly.
- **Uncertain** (42 works) — fewer do. The counts are floors: real lower bounds,
  but with a substantial and unevenly distributed gap.

The 80% cut was chosen from the actual distribution, which is genuinely
bimodal — a dense mass below 50%, an empty valley between 50% and 79%, and a
spike from 80% up. The threshold sits in the valley rather than at a round
number picked in advance.

The split is also **robust to how queued citations are filed.** Because filing
is alphabetical, a work sorted ahead of its collision partners can have its rate
depressed by luck alone. Recomputing each work's uncertainty from candidate-set
membership instead of filing order moves only a single work across the 80% line
and leaves the bimodal shape intact — so the tier assignments are not an artefact
of filing order.

Uncertain-tier works are **included, not hidden**. Excluding them would remove
*Phaedo*, *Phaedrus*, *Gorgias*, *Apology*, *Meno* and *Crito* — 28% of all
placed citations, and much of what the field actually argues about. They are
marked instead: dashed lines in the time chart, a fading tail in the summary
chart, and a stated placement rate wherever they appear.

## Small-n works

A placement rate is only as trustworthy as the number of citations it is
computed from. A dozen works in the corpus carry very few placed citations —
under about a hundred — and for those the rate says more about chance than about
how cleanly the work resolves: a work with thirty citations can reach 100% by
luck, or dip well below its neighbours for no structural reason. Tier membership
for a small-n work is therefore **not** a claim that the work is well studied,
and its bar should not be read against the long ones or ranked among them.

This is why small-n is surfaced only in the summary chart's hover, not as a
persistent badge: the fact is worth having when you inspect a specific work, but
it is not a global flag about the data, and putting it on every chart surface
gave a minor property the visual weight of a major one. The count itself is
always shown, so a thinly-cited work never masquerades as a heavily-cited one.

## Collision bands

Within a single work, missingness is usually spread evenly — but a few works
have a **specific stretch of pages** that resolves worse than the rest, almost
always a Stephanus or Bekker range that collides with another work. These are
the collision bands (machine-readable in `collision_bands.json`). Where they
exist, the passage map marks the affected pages and notes them in one line
beneath the chart, because the *shape* of attention across those pages is
depressed rather than merely lower.

They are a **localised, minor** caveat, which is why they no longer lead the
per-work view. The most band-heavy work is the *Laws*: seven contiguous bands
across Books IX–XII (Stephanus 860–959) account for an estimated 348 unplaced
citations — under a tenth of the work's placed total, spread thin. Most works
flag none at all: 47 of 59 measured works have no band, and their within-work
shape can be read as-is. The full band table, the detection method, and the two
distinct axes of missingness (which *passages* are under-counted versus which
*works* carry a wide floor-to-ceiling gap) are in the [pipeline
record](/methods/pipeline/), §6.

## Grouping schemes

Several of the groupings offered in the time chart are **interpretive, not
neutral**, and are tagged *contested* in the picker:

- **The developmentalist chronology** (early / middle / late Plato) is the
  standard ordering, but unitarian readers reject the premise that Plato's
  thought develops across datable periods at all, and stylometric and doctrinal
  datings disagree at the edges. Plotting "early Plato" plots an interpretation
  of the corpus, not a fact about it.
- **The theoretical / practical division** is Aristotle's own for his works;
  applied to Plato it is a borrowed heuristic Plato does not draw himself, and
  several dialogues resist it (the *Republic* is both at once).

For a scholarly audience the *contested* tag is enough of a flag, so the chart
no longer spells the dispute out in a warning box each time such a group is
selected. The grouping definitions live in `work_groups.json`.

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

Coverage is also **uneven over time.** The journals are not evenly distributed
across the 1887–2022 span: the pre-1950 decades are thin, output climbs steeply
from the late 1970s, and well over half of all placed citations fall after 1980.
A flat or empty early stretch in the time chart therefore reflects how little was
published and digitised then, not a drop in attention — which is why the raw
series are noisier before 1950, and why the smoothing options exist.

## What is deliberately not shown

- **Unplaceable citations have no year or journal breakdown.** A citation we
  could not attribute to a work cannot honestly be attributed to a decade
  either. When you filter by year, the uncertainty tail therefore stays at full
  width and turns grey rather than shrinking with the bars.
- **The queue holds two different quantities, and only one is multi-counted.**
  Each queued citation is *filed* under exactly one work — the alphabetically
  first of its candidate set — so a work's filed queue count is exclusive and the
  per-work totals sum cleanly (97.7% of multi-candidate rows fall to that first
  candidate). But the faint "could belong here" tail counts *candidate-set
  membership*: a citation whose page-number collides across several works is
  counted against each of them, on purpose, because any one could be its true
  home. Those memberships overlap and must not be summed — which is why there is
  no single "estimated true total" anywhere on the site.
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
- Several Aristotelian treatise boundaries remain to be verified; see the
  [full record](/methods/pipeline/#9-known-limitations--the-honest-to-do-list).

## Checking the work

The [derived data is published](/data/) under CC BY 4.0, and the pipeline is
open source. If you find an error, [please tell me](/contact/) — corrections
will be recorded and credited.
