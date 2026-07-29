---
title: Data
subtitle: Download the derived data, or read what may and may not be redistributed
description: Published derived data for Footnotes to Plato, with licensing terms and file documentation.
---

Everything the viewers use is published here. If you want to check a number,
reproduce a chart, or build something else on top of this, start with these
files.

## What is published

<div class="callout">
<p><strong>Derived facts only.</strong> Each record says which work, which
passage, which journal, which year, and which article DOI. There is no article
text of any kind. The verbatim citation context extracted during processing is
confidential under the JSTOR Text Analysis Support terms and is dropped before
any shareable file is written.</p>
</div>

| File | Contents |
| --- | --- |
| <a href="/data/viewer/meta.json" download><code>meta.json</code></a> | Journals, year range and histogram, corpus totals, thresholds used. |
| <a href="/data/viewer/view_a.json" download><code>view_a.json</code></a> | Per work: placed count (the floor), uncertainty band, unplaceable mass, distinct articles, collision partners. Also carries an internal `resolution_rate` / `tier`, retained for provenance but no longer used by the site (see methods). |
| <a href="/data/viewer/view_a_filter.json" download><code>view_a_filter.json</code></a> | Per work: sparse journal × year matrix of placed citations. The time chart's source. |
| <a href="/data/viewer/works_index.json" download><code>works_index.json</code></a> | Work list with placed-citation totals (plus an unused internal `tier` field). |
| `view_b/<work>.json` | Per work: section-level cells and per-citation records with DOI links. |

## Licence

The derived data is **CC BY 4.0** — use it for anything, including commercially,
provided you attribute the source. The pipeline and site code are **MIT**; the
site prose is **CC BY 4.0** on the same terms as the data.

The underlying JSTOR full text is **not redistributable** and is not available
here. It never leaves the machine that processes it: the verbatim context of
each citation is dropped before anything is written to a shareable file, and
what is published is derived facts only — work, passage, journal, year, DOI.

## Reproducing the build

The aggregator that produces these files runs locally against the JSTOR
delivery. Given the delivery, `build_viewer_data.py` regenerates every file
above, and prints invariant self-checks so a bad run announces itself.

Without the delivery you cannot regenerate the data from scratch — but you can
verify every published number against these files, and the
[methods page](/methods/) documents each transformation between the two.

## Caveat before reuse

Every `floor` in `view_a.json` is a **lower bound**, not a total, and how much a
work loses to the queue varies enormously — a raw count means something different
for *Republic*, whose page range is clean, than for *Crito*, whose Stephanus
range is crowded. If you reuse these numbers, carry that with them: report the
floor as a floor, and note that the `unplaceable` fade is shared candidate-set
membership that **cannot be summed across works**. See
[Floors, not totals](/methods/#floors-not-totals).
