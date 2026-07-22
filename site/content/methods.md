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

Uncertain-tier works are **included, not hidden**. Excluding them would remove
*Phaedo*, *Phaedrus*, *Gorgias*, *Apology*, *Meno* and *Crito* — 28% of all
placed citations, and much of what the field actually argues about. They are
marked instead: dashed lines in the time chart, a fading tail in the summary
chart, and a stated placement rate wherever they appear.

## What is deliberately not shown

- **Unplaceable citations have no year or journal breakdown.** A citation we
  could not attribute to a work cannot honestly be attributed to a decade
  either. When you filter by year, the uncertainty tail therefore stays at full
  width and turns grey rather than shrinking with the bars.
- **The review queue's work attribution is non-exclusive.** One ambiguous
  citation is filed under *every* candidate work, so those counts cannot be
  summed. This is why there is no "estimated true total" anywhere on the site.
- **No verbatim article text.** The citation context extracted during processing
  is confidential under the JSTOR agreement and is dropped before anything is
  written to a shareable file.

## Known limitations

- Coverage is ten journals, articles only, Anglophone-skewed. See
  [scope](/about/#scope-and-its-limits).
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
