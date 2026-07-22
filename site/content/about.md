---
title: About
subtitle: What this is, who made it, how to cite it, and what you may do with it
description: Background, scope, licensing and citation information for Footnotes to Plato.
---

## What this is

*Footnotes to Plato* is a passage-level citation index of the ancient-philosophy
journal literature. It answers a question that indexes of secondary literature
normally cannot: not *which works* scholars discuss, but *which passages* — down
to the Stephanus or Bekker line.

The underlying corpus is a full-text delivery from JSTOR's Text Analysis Support
programme covering ten journals. A pipeline extracts candidate citation strings
from article body text, resolves each to a specific work and locus where it can
do so with confidence, and routes the rest to an auditable review queue rather
than guessing. The [methods record](/methods/) documents every stage.

The tool is a **finding aid**. It reports where citations point and links out to
the citing articles on JSTOR. It does not reproduce article text, and it is not
a substitute for reading the scholarship it indexes.

## Scope and its limits

The corpus is **journal articles from ten titles, 1887–2022**. That excludes
monographs, edited volumes, commentaries, and journals outside the delivery —
including *Oxford Studies in Ancient Philosophy*, where a great deal of the most
consequential recent work has appeared. Coverage skews Anglophone.

The honest description of what this measures is *citation traffic in these ten
journals*. It is a large and useful sample of the field's attention. It is not a
census, and a passage's absence here is not evidence that nobody has written
about it.

A second limit is placement. Roughly 141,000 citation candidates were detected;
90,502 could be tied to a specific passage. The remainder are mostly cases where
page-number ranges collide between works — a bare "80b" is ambiguous across
several dialogues. Those citations are real and are counted in the totals, but
they are not attributed to any one work, and every chart on this site
distinguishes what was placed from what was not.

## How to cite

<h3 id="how-to-cite">Citing this tool</h3>

If this contributed to published work, please cite it. A version-specific
identifier matters here, because the corpus and the resolution pipeline will
both change: a reader checking your citation in three years should be able to
retrieve the version you actually used.

**Recommended form** (adapt to your style guide):

```
Kretz, David. Footnotes to Plato: A Passage-Level Citation Index of the
Ancient-Philosophy Scholarship. Version 1.0, 2026.
https://<your-pages-url>/  DOI: <to be assigned>
```

**On getting a DOI.** The straightforward route is
[Zenodo](https://zenodo.org/), which is free, run by CERN, and integrates
directly with GitHub: link the repository, cut a release, and Zenodo archives
that exact state and mints a DOI for it. It issues both a version DOI and a
concept DOI that always resolves to the newest release, so readers can cite
either "the version I used" or "the project." This is the standard route for
research software and derived datasets, and it is what I would recommend before
publicising the site.

If you would rather not use Zenodo, the alternatives are an institutional
repository (many universities run one, and yours may prefer it) or the Open
Science Framework. What matters is that the identifier is persistent and
version-specific; a bare URL is not, since the site will change under it.

**Citing the underlying corpus.** The full text came from JSTOR under a Text
Analysis Support agreement. If your argument depends on the corpus rather than
on this tool's analysis, acknowledge JSTOR as the source of the underlying data
and note that access was granted under that programme.

## Licensing

Different parts of this project carry different terms, because they are
different kinds of thing.

| Component | Licence | Notes |
| --- | --- | --- |
| Pipeline and site code | MIT | Permissive; reuse freely with attribution. |
| Derived data (`viewer_data/`) | CC BY 4.0 | Counts, loci, and identifiers. Attribute this project. |
| Site prose (methods, About) | CC BY 4.0 | Same terms as the data. |
| Underlying JSTOR full text | **Not redistributable** | Never leaves the local machine. Not included in any download here. |

A note on why the split. **MIT** for code is the least restrictive sensible
choice and imposes nothing on people who reuse the pipeline. **CC BY 4.0** for
the derived data asks only for attribution, which keeps the data usable in
further research — including commercial or AI research — while ensuring the
provenance travels with it. The alternatives were considered and rejected:
CC0 (public domain) would drop the attribution that lets a reader trace a
number back to its method, and a NonCommercial or ShareAlike clause would make
the data awkward to combine with other openly licensed corpora, which is most of
its potential value.

The one hard boundary is the source text. The JSTOR delivery is confidential
research data under the Text Analysis Support terms. It is processed only on a
local machine, the verbatim context of each citation is dropped before anything
is written to a shareable file, and no part of it is published here or available
for download. What is published is derived facts: which work, which passage,
which journal, which year, which DOI.

## Disclosure

The pipeline, the analysis, and this site were developed with substantial
assistance from Claude (Anthropic), used as a working collaborator throughout —
writing and reviewing code, stress-testing the statistical reasoning, and
catching several errors that would otherwise have shipped. Every methodological
decision, and responsibility for what is published here, remains mine.

I mention this because the work should be assessable on its merits, and because
how it was made is part of what a reader may want to weigh. The pipeline is
open, the derived data is published, and the [methods record](/methods/)
documents the failures alongside the results precisely so that none of this has
to be taken on trust.

## Acknowledgements

To JSTOR's Text Analysis Support programme, for making full-text research access
possible at all, and for the care taken over the delivery.

To the editors and contributors of the ten journals indexed here. This tool is
entirely parasitic on their work: every data point is a scholar deciding a
passage was worth arguing about.

And to Perseus Digital Library at Tufts, whose canonical citation infrastructure
makes it possible to link a locus to the text it names.

## Contact

Corrections, methodological objections, and feature suggestions are all welcome
— see the [contact page](/contact/). Objections to the method are especially
welcome; that is what the methods record is for.
