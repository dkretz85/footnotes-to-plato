---
title: "Sequentia" citations (f., ff., sq., sqq.)
subtitle: How often scholarship says "and following", and what the index does with it
description: Incidence of f./ff./sq./sqq. citation tails across the corpus, how the extractor handles them, and why they lower the counts without reshaping the map.
---

*Methods appendix to* Footnotes to Plato. *Every figure below is reproducible
from the published derived data with `sequentia_audit.py` (see the end).*

## The concern

Scholars routinely cite not a single passage but a passage **and what follows
it**, using an abbreviated tail: `Republic 327a f.` ("and the following page"),
`Metaphysics 1094a25 ff.` ("and the following pages"), or the Latin equivalents
`sq.` / `sqq.` (*sequens*, *sequentia*). The reference names a starting locus and
gestures, open-endedly, at a run of text after it.

The extractor captures an **explicit** range whole — `620a-622c` is expanded to
every Stephanus unit it covers — because both endpoints are written out. A
*sequentia* tail has no closing endpoint, so there is nothing to expand to. What
the extractor does instead is capture the **anchor locus alone** (`327a`,
`1094a25`) and drop the "and following" gesture. The starting passage is indexed;
its unspecified continuation is not.

This is the same *shape* of shortfall documented for
[anaphoric citation](/methods/anaphoric-citation-validation.md): a real reference
is captured at a floor value, with some attention past the captured point going
uncounted. The question is the same too — **how much**, and **does it distort the
shape of the data or only lower its level?**

## A note on `f.` versus `ff.`

In principle `f.` / `sq.` mean "and the *one* following unit" (a bounded,
expandable reference) while `ff.` / `sqq.` mean "and an *indefinite* run
following". In practice the distinction is soft: authors and typesetters use the
forms interchangeably, drop or double the final letter inconsistently, and rarely
intend a precise count. We therefore **report the combined figure** as the real
one and treat the split below as descriptive colour, not a quantity to lean on.

## The numbers

Of **258,374** placed citations, **4,080 — 1.58%** carry a *sequentia* tail. Split
(with the caveat above): about **0.44%** are `f.`/`sq.` and **1.13%** are
`ff.`/`sqq.`

That is a small fraction, and — the reassuring part — it is **smallest exactly
where the data is densest and largest where the data is already thin.** The
pattern is clearest across time:

| Decade | Citations | Sequentia rate |
|--------|----------:|---------------:|
| 1970s  | 14,780    | 4.49% |
| 1980s  | 36,200    | 2.45% |
| 1990s  | 42,907    | 1.63% |
| 2000s  | 46,667    | 1.05% |
| 2010s  | 56,910    | 0.51% |
| 2020s  | 15,425    | 0.39% |

The recent decades carry roughly half of all placed citations and sit at
0.4–1.1%; the sparse pre-1990 decades, which carry little weight, run 2–4.5%. The
convention is simply going out of fashion — modern authors write explicit ranges,
which the index *does* capture. So the correction matters least in the part of the
map that bears the most weight.

The same gradient holds by **field** — the effect tracks citing culture, heaviest
in philological classics and lightest in verse-by-verse theology:

| Field | Citations | Sequentia rate |
|-------|----------:|---------------:|
| Classics | 130,535 | 2.06% |
| Philosophy | 49,369 | 1.42% |
| Theology & NT | 78,470 | 0.89% |

and by **reference system**, where the smallest corpus (Pindar) shows the highest
rate and the largest well-behaved ones cluster near the average:

| Corpus | Citations | Sequentia rate |
|--------|----------:|---------------:|
| Pindar | 4,514 | 3.70% |
| Homer | 34,140 | 1.94% |
| Stephanus (Plato) | 57,025 | 1.77% |
| Ambiguous (Plato/Aristotle) | 64,685 | 1.68% |
| Bekker (Aristotle) | 37,961 | 1.54% |
| NT (Paul) | 60,049 | 0.94% |

## Local hot spots

A handful of individual journals and texts rise above **5%**. Every one of them
sits in a thin cell — a small-*n* text, or an early, low-volume (and now defunct)
journal — so the high rate rides on a small absolute count and coincides with the
places the tool already asks you to read cautiously:

| Where | Citations | Sequentia rate |
|-------|----------:|---------------:|
| *The American Journal of Theology* (jrnl, 1897–1920) | 1,487 | 6.86% |
| *Critias* (text) | 286 | 6.99% |
| *Meteorology* (text) | 864 | 5.79% |
| *The Biblical World* (jrnl, 1893–1920) | 1,190 | 5.13% |

That the two journal hot spots are theology titles — in the field with the
*lowest* overall rate — is the period effect showing through: both are among the
oldest journals in the corpus, and age, not discipline, is what drives the tail
here. A few more cells cluster just under the line (*Greece & Rome* 4.72%, the
*Pythian* odes 4.39%), and the full tables at the foot of this page list the top
25 journals and works by rate. Treat any cell above ~5% as one where the placed
count is a slightly softer floor than usual — the same standing advice the
[sparse early decades](/methods/) already carry.

## What it means

*Sequentia* non-capture **lowers the level** of the counts a little; it does not
reshape the distribution. Because the anchor is always the passage the author put
first — usually the most important locus of the run — the citation still registers
at the right place; only the trailing spillover onto adjacent pages is lost. The
result is a mild **under-weighting of multi-passage spans**, concentrated in older
classical-philology writing, not a bias toward or against any passage, period, or
discipline the tool invites you to compare.

Read the published numbers, here as everywhere, as [**floors, not
totals**](/methods/). The
*sequentia* shortfall makes those floors modestly lower than the true attention —
about 1.6% of citations corpus-wide, more in the thin cells, less in the dense
ones — without moving the shape of any comparison.

## Why we don't mechanically correct it

We considered expanding the tails the way explicit ranges are expanded, and chose
not to. The `ff.`/`sqq.` cases — the bulk of them — are **genuinely open-ended**:
there is no principled number of following units to add, so any expansion would be
invented attention. The bounded `f.`/`sq.` cases (0.44% of citations) *could* be
expanded by one adjacent unit, but at that share the added precision is not worth
the added assumption, especially given how loosely the two forms are used. A
mechanical regex has no honest way to recover an unstated endpoint, and inventing
one would trade a transparent floor for a fabricated total.

## Caveats

- **This is a lower bound.** The measurement reads the tail out of the text
  immediately after each captured anchor. A *tight-set* form with no space —
  `327aff.` — captures nothing at all (no word boundary follows the anchor), so
  those citations never enter the index and cannot be counted here. The true
  incidence is therefore a little higher than 1.58%.
- **The `f.`/`ff.` split is indicative only**, for the reasons given above. The
  combined rate is the figure to cite.

## Reproducing

```
python3 sequentia_audit.py resolved.tsv
```

The script re-inspects the `context` window stored beside every resolved citation,
locates the anchor, and tests whether an `f.`/`ff.`/`sq.`/`sqq.` marker follows it;
it prints the overall rate and the by-field, by-period, by-corpus, by-journal, and
by-work breakdowns verbatim. Run it against `citations.tsv` instead for everything
except the per-work table (that column is added at resolution). Add
`--tsv out.tsv` for a tidy per-group export.

---

## Full tables

### By journal — top 25 by rate (min. 30 citations)

| Journal | Citations | `f.`/`sq.` | `ff.`/`sqq.` | Rate |
|---------|----------:|-----------:|-------------:|-----:|
| The American Journal of Theology | 1,487 | 61 | 41 | 6.86% |
| The Biblical World | 1,190 | 38 | 23 | 5.13% |
| Greece & Rome | 2,078 | 15 | 83 | 4.72% |
| Transactions and Proceedings of the American Philological Association | 4,184 | 25 | 106 | 3.13% |
| The Classical Journal | 5,086 | 38 | 106 | 2.83% |
| The Journal of Religion | 2,650 | 26 | 43 | 2.60% |
| Rheinisches Museum für Philologie | 8,417 | 113 | 103 | 2.57% |
| Revue de Théologie et de Philosophie | 863 | 21 | 1 | 2.55% |
| The Classical World | 3,644 | 10 | 77 | 2.39% |
| The Classical Review | 5,622 | 26 | 106 | 2.35% |
| The American Journal of Philology | 11,979 | 90 | 189 | 2.33% |
| The Classical Quarterly | 22,996 | 82 | 435 | 2.25% |
| Harvard Studies in Classical Philology | 7,540 | 61 | 108 | 2.24% |
| Illinois Classical Studies | 4,041 | 13 | 71 | 2.08% |
| Mnemosyne | 13,487 | 108 | 145 | 1.88% |
| Zeitschrift für Theologie und Kirche | 483 | 3 | 6 | 1.86% |
| Classical Philology | 14,088 | 33 | 209 | 1.72% |
| Classical Antiquity | 4,711 | 16 | 63 | 1.68% |
| Phronesis | 24,658 | 34 | 373 | 1.65% |
| Les Études philosophiques | 1,457 | 18 | 6 | 1.65% |
| Hermes | 11,108 | 56 | 124 | 1.62% |
| History of Philosophy Quarterly | 5,885 | 1 | 91 | 1.56% |
| History of Religions | 661 | 1 | 9 | 1.51% |
| Transactions of the American Philological Association | 4,235 | 8 | 54 | 1.46% |
| Revue Internationale de Philosophie | 1,541 | 4 | 17 | 1.36% |

### By work — top 25 by rate (min. 30 citations)

| Work | Citations | `f.`/`sq.` | `ff.`/`sqq.` | Rate |
|------|----------:|-----------:|-------------:|-----:|
| Critias | 286 | 0 | 20 | 6.99% |
| Meteorology | 864 | 6 | 44 | 5.79% |
| Pythian | 1,824 | 24 | 56 | 4.39% |
| Nemean | 1,415 | 23 | 37 | 4.24% |
| Euthydemus | 1,100 | 10 | 30 | 3.64% |
| Phaedo | 5,707 | 44 | 144 | 3.29% |
| Isthmian | 389 | 4 | 8 | 3.08% |
| De Partibus Animalium | 812 | 5 | 20 | 3.08% |
| Odyssey | 21,336 | 169 | 418 | 2.75% |
| Rhetoric | 4,530 | 40 | 84 | 2.74% |
| De Somno | 149 | 0 | 4 | 2.68% |
| De Insomniis | 149 | 0 | 4 | 2.68% |
| Meno | 2,255 | 4 | 54 | 2.57% |
| Physics | 3,359 | 23 | 61 | 2.50% |
| De Sensu | 413 | 0 | 10 | 2.42% |
| Gorgias | 3,742 | 25 | 65 | 2.41% |
| Philebus | 2,913 | 12 | 51 | 2.16% |
| Theaetetus | 2,940 | 6 | 57 | 2.14% |
| Poetics | 4,097 | 24 | 58 | 2.00% |
| De Interpretatione | 550 | 2 | 9 | 2.00% |
| Timaeus | 7,664 | 27 | 124 | 1.97% |
| Topics | 1,497 | 10 | 19 | 1.94% |
| De Generatione et Corruptione | 267 | 0 | 5 | 1.87% |
| Hippias Major | 340 | 2 | 4 | 1.76% |
| Clitophon | 116 | 2 | 0 | 1.72% |
