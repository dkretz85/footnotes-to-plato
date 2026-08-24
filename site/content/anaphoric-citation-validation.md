# Anaphoric citation: does non-capture bias the data?

*Methods appendix to* Footnotes to Plato. *Every figure below is reproducible
from the published derived data with `frontloading_probe.py` (see the end).*

## The concern

For **Homer, Pindar, and the Pauline epistles**, the extractor places a citation
by an adjacent **work-name cue**: an *Odyssey* book + line number such as `12.432`
is recognised as *Odyssey* only when preceded by a cue like `Od.` (the cue also
decides *Iliad* vs *Odyssey*). Scholarship, however, routinely cites
**anaphorically**: the work is named on first reference, and later references give
book + line, or bare line numbers, with the name dropped. Those cue-less
continuations are **not captured**.

The question is whether this non-capture *distorts the shape* of the data — most
obviously toward textually **earlier** passages (the named, captured reference is
usually the first one an article makes, hence usually the earliest), but also
across **periods** and **disciplines**, the axes the tool actually reports on.

Plato and Aristotle are the natural **control**. Their citations use
self-identifying pagination (Stephanus / Bekker), so the pipeline *recovers*
cue-less continuations by scope-tracking. The two corpus groups therefore differ
precisely on the variable in question — continuations **dropped** (Homer / Pindar
/ Paul) vs **recovered** (Plato / Aristotle) — which lets a battery of seven tests
isolate the effect.

## The seven tests

| # | Question | Result |
|---|----------|--------|
| 1 | Are the cue-anchored corpora more front-loaded than the scope-tracked ones? | A modest gap (pooled front-loading **+0.120 vs +0.044**), but confounded — Bekker (control) is also high (+0.111). Not decisive on its own. |
| 2 | Does *dropping continuations* actually **cause** front-loading? (decisive) | **No.** Simulating the cue-anchored regime inside Plato/Aristotle (deleting recovered continuations) changes front-loading by **−0.007 / −0.001** — essentially zero, and slightly negative. Recovered continuations cluster *near their anchor*, not at the end. |
| 3 | Do the cue-anchored corpora show the "first-citation-only" fingerprint (one locus per article)? | **No — the opposite.** They average *more* distinct loci per article (Homer 7.6 vs Plato 4.8); the cue is usually repeated. |
| 4 | Does capture depth diverge by **era** between the two regimes? | **No.** Both trend in parallel across all decades — no era-correlated capture bias in the temporal floors. |
| 5 | Is the heavy-reading (right) tail truncated for cue-anchored corpora? | **No.** Homer has the *fattest* tail (Gini 0.70, p99 = 83) — deep readings are not clipped. |
| 6 | Are cue-anchored citations over-concentrated on canonical loci? | **No.** They are *less* concentrated (normalised entropy 0.955–0.964 vs 0.90–0.92). |
| 7 | Is the cross-**discipline** depth gap a citing-style artifact? | **No.** The shallow discipline (theology, 4.6 loci/article) drops the *fewest* cues (4.2% vs classics 9.7%), so its shallowness is real; correcting for the drop-rate *widens* the classics–theology gap rather than closing it. |

## Conclusion

Non-capture of anaphoric citations does **not** bias the *distribution* of the
data — not toward earlier passages (Tests 1–3, 6), not across time (Test 4), not
across disciplines (Test 7), and it does not truncate deep engagements (Test 5).
The observed front-loading of these texts is a **real signal** — attention to
proems and opening set-pieces (e.g. *Iliad* 1, *Olympian* 1) — not an extraction
artifact.

What non-capture *does* produce is a modest, roughly **uniform undercount** of
citations for these three corpora: from the recovery rate measured on
Plato/Aristotle, cue-less continuations are on the order of **~4% (theology
citers) to ~10% (classics / philosophy citers)** of references. This lowers the
*level* of the counts, not their *shape* — consistent with the tool's standing
["floors, not totals"](/methods/#floors-not-totals) framing. The published
numbers should be read as floors; the anaphoric shortfall makes the
Homer / Pindar / Paul floors modestly and evenly lower than the true totals,
without reshaping any comparison the tool invites.

## One caveat

Tests 2 and 7 measure the mechanism **inside Plato/Aristotle** (the only corpora
where continuations are recovered and can be inspected) and read the result as
the analog for Homer/Pindar/Paul. This assumes continuation-*positioning* and
per-discipline cue-dropping *habits* carry across corpora — reasonable, and the
best available evidence, but an assumption rather than a direct measurement on the
cue-anchored texts themselves.

## Reproducing

```
python3 frontloading_probe.py --resolved resolved.tsv
```

Tests 1 and 3–6 run on the published viewer data alone; Tests 2 and 7 additionally
read `resolved.tsv` (the per-citation resolution table) for the `method` field
that distinguishes name-matched from scope-recovered citations. All figures above
are printed verbatim by the script.
