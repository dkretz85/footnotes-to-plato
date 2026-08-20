repo: dkretz85/footnotes-to-plato
branch: main

## Last sync
date: 2026-08-20T17:33:00Z

### Updated in this project
- Full-corpus sync: all five authors now present in the repo. Viewer C's index rebuilt from works_index.json at 88 texts with real distinct-article counts; Homer, Pindar and Paul are no longer placeholders and the synthetic per-ode Pindar rows are gone (the corpus counts each book of odes as one text).
- Journal model corrected again to the real 48 journals across philosophy / classics / theology & NT, span 1827-2022, 493,233 placed citations; the Theology & NT journal set is now selectable rather than disabled.
- Step 1 redesigned for calm: texts laid out in equal columns flush to the right edge, and the never-testable texts moved out of the author lists into their own clay panel below.
- New Landing Page.dc.html: user-supplied lede, five headline figures, the three tool previews stacked with thumbnails, a three-caveat block with an eight-text floor-vs-fade sample, and the contact + acknowledgements copy carried over unchanged.
- Rebuilt Viewer C's text index from the real corpus: 68 Plato + Aristotle works with article counts and faceted flags read from works_index.json.
- Corrected the journal model to the actual 10 journals (7 philosophy / 3 classics, no theology set) and the real ~59/41 volume split.
- Encoded the faceted constraint: only Republic, Laws, Metaphysics, Nicomachean Ethics and Eudemian Ethics have book-level facets; every other work is passage-only, so the grain toggle hides itself.
- Added a "too thinly cited to test" panel using the site's existing uncertain palette; Homer, Pindar and Paul remain design-only, flagged as not yet ingested.
- Design audit against the live site: adopted the real sticky header/nav and footer, --paper, --shadow, 10px panel radius and the full serif/mono stacks; moved controls to the filterbar's structural treatment so saturated colour stays reserved for data, per the stylesheet's own rule.
- Replaced fabricated passage references with the real reference spans: every band label now names a page the work actually occupies, and all five faceted works use their published book divisions.

## Screen map
| Project screen | Built from |
|---|---|
| Viewer C v2.dc.html — text index, corpus + counts + faceted flags | viewer_data/works_index.json, viewer_data/authors.json |
| Landing Page.dc.html — lede figures, caveats, floor-vs-fade sample | viewer_data/meta.json, viewer_data/works_index.json, docs/index.html |
| Viewer C v2.dc.html — journal sets, field grouping, volume shares | viewer_data/journal_groups.json, viewer_data/meta.json |
| Viewer C v2.dc.html — palette, type stacks, callout + tier styling | docs/static/site.css |
| Viewer C v2.dc.html — site header, nav, footer, landing framing | docs/index.html, docs/static/site.css |
| Viewer C v2.dc.html — control bar, journal grouping treatment | filterbar.css |
| Viewer C v2.dc.html — chart panel, scope banner, warning blocks | series.css |
| Viewer C v2.dc.html — decade axis, 1887–2022 span, thin early decades | viewer_data/meta.json (year_histogram) |
| Viewer C v2.dc.html — passage-reference bands, book sub-ranges | stephanus_ranges.json, bekker_ranges.json |
| Viewer C v2.dc.html — Metaphysics / NE / EE book axes, common books | metaphysics_books.json, ethics_books.json |
| Temporal Views.dc.html — earlier exploration rounds (superseded) | site.css, filterbar.css, series.css, copy.json, view_a.html, view_b.html |

## Sync history
- 2026-08-19T23:29:00Z — read the site's design language (tokens, chrome, filter bar, series chart, copy.json) as the baseline for the temporal views; built round-1 mockups. No repository files modified.
