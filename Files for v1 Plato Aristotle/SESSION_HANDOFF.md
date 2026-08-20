# Footnotes to Plato — viewer build handoff

*Written at the end of the session that built the data aggregator and the two
core views (A and B). Pick up here for the filter bar, view integration, and
Perseus links.*

---

## Where the project stands

Both **core views are built, refined, and working against real data**. The data
pipeline that feeds them is final. What remains is connective tissue (a shared
filter bar), a comparison feature, merging the two views into one page, the
Perseus "see the passage" links, and deployment.

The tool is a **finding aid**: it shows which works and which passages the
ancient-philosophy scholarship cites, and links out to the articles. It never
mirrors article content (a JSTOR terms requirement — see "Constraints").

---

## What was built this session

### 1. The data aggregator (FINAL — runs locally on David's machine)

Two Python files, both verified against the real corpus (90,502 citations, 68
works, 10 journals, 6,545 articles):

- **`build_viewer_data.py`** — reads three local files from `~/Downloads`
  (`resolved_with_books.tsv`, `review_queue.tsv`,
  `jstor_metadata_2026-07-18.jsonl.gz`) plus `collision_bands.json`, and writes
  a `./viewer_data/` folder of small JSON the viewer loads.
  - Thresholds are parameters: `--band-threshold 0.50`, `--tier-threshold 0.80`
    (both are now the defaults).
  - The confidential `context` column (col 13, verbatim full text) is **never**
    read into any output — verified structurally. This is a terms requirement.
  - Run: `python3 build_viewer_data.py` (defaults point at `~/Downloads`).
- **`locus.py`** — the shared locus parser, lifted verbatim from the project's
  `derive_book.py` so View B's cells and the book facets can never disagree.
  `build_viewer_data.py` imports it. Also runnable standalone as a drop-in
  replacement for `derive_book.py`.

**Outputs in `./viewer_data/`:**
- `meta.json` — journals (10), journal_counts, year range (1887–2022),
  year_histogram, totals, thresholds, doi_coverage (1.0).
- `view_a.json` — per-work: `floor`, `band`, `band_extra`, `unplaceable`,
  `queued_total`, `resolution_rate`, `tier`, `distinct_articles`, `faceted`,
  `collides_with` (collision-partner works parsed from the queue's `reason`).
- `works_index.json` — work list with tier + citation counts, for the selector.
- `view_b/<work>.json` — per work: `cells` (section-grain counts + by_journal +
  articles) and `dots` (per-citation: page/section/line/journal/year/iid/doi/
  title/author, deduped by iid+locus). NOTE: the NE dots file is 1.8 MB — see
  "Known issues / deferred" about splitting cells from dots.

### 2. View A — "Which works get attention" (`view_a.html`)

Text-level. Horizontal bars, **two tiers** (Trustworthy / Uncertain), sorted by
floor within each tier. Each bar has three parts:
- **floor** (solid) = confidently placed citations.
- **band** (thin, lighter) = floor + queued rows at confidence ≥ 0.50 (a narrow
  honest extension).
- **fade** (smooth gradient dissolving to transparent) = the sub-threshold
  "unplaceable" mass. It's an open-ended gesture, NOT a bar to a false number.

**Tier model rationale (important — don't revert this):** the old
`ceiling = resolved + queued` was rejected as incoherent. The review queue's
work attribution is *non-exclusive* — one ambiguous citation is filed under
every candidate work (Apology AND Philebus AND Timaeus…), so summing a work's
whole queue multi-counts collisions. The fade shows *magnitude of ambiguity*
without asserting a per-work number, and the hover names the collision partners.

**Tier cut = 0.80 resolution rate** ("publication grade"), chosen from a
genuinely bimodal histogram (dense mass 0–49%, empty valley 50–79%, spike
80–99%). Real split: **26 trustworthy, 42 uncertain**. The uncertain tier is
INCLUDED and clearly marked, with guardrail copy ("a short floor here does not
mean a work is little-studied", "don't compare floors across tiers").

**Author colouring:** Plato = indigo (`--p-*`), Aristotle = brighter green-teal
(`--a-*`, `#1f9e8a`). Basis is **editorial, not authorial** — Stephanus
pagination → Plato/indigo, Bekker → Aristotle/teal. Dubia coloured by corpus.
Footnote at page bottom states this ("as traditionally ascribed", no authorship
claim). **The 68-work author map is INLINED in the HTML** (`AUTHORS_INLINE`),
NOT fetched — this was a deliberate fix after a separate `authors.json` fetch
kept 404ing silently and defaulting everything to indigo. Keep small static
maps inlined for the same reason.

Hover on any bar shows floor / band / unplaceable (with "≈X if all belonged
here" clearly conditional) / resolution rate / article count / collision
partners.

This view is **static** (all-time totals). It's a candidate for the intro or
methods page. Its dynamic successor is the comparison plot (see "Next").

### 3. View B — "Passage-level attention" (`view_b.html`)

One work at a time. Two stacked visualisations of the same data:
- **Top: heat-tinted bar chart** at section grain (a/b), ~300px tall, real
  y-axis (citation counts; label flips to "distinct articles" on the metric
  toggle), x-axis with book dividers + Roman-numeral labels for faceted works.
  Bars encode magnitude (the strong channel).
- **Below: heatmap** in a **5-per-row grid** (5×2 for the 10-book faceted
  works). This carries **line-band detail**: Bekker works (Metaphysics/NE/EE)
  split each column a/b into **3 line-bands** (1–15, 16–30, 31+) — NOT 6,
  because parsed line numbers run noisily to ~46, so finer bands would be mostly
  empty. Plato works stay a–e section grain. Non-faceted works render as one
  full-width panel (no fake book grid).

Both bars and cells **drill in** to a right-side panel listing the citing
articles (serif titles with HTML tags stripped, journal · year, DOI links to
`https://doi.org/10.2307/…`), with **CSV export** of the current selection.
Two-tier banner at top (trustworthy = blue, uncertain = clay warning with the
same guardrail guidance as View A). Pooled/by-journal and citations/
distinct-articles toggles are present. **The journal *selector* is deferred to
the shared filter bar** (the by-journal split logic is wired but has no UI yet).

### Design language (both views)
- Serif masthead (title 44px, subtitle 15px), calm light-blue→lavender palette,
  saturated colour reserved for the heat ramp + clay for the uncertainty
  apparatus. A humanities instrument, not a dashboard.
- Single self-contained HTML files. **Must be SERVED, not opened as file://**
  (browsers block fetch from file://). Local: `python3 -m http.server 8000`.
  Target host: GitHub Pages (static, free, same as dkretz.com).

---

## Constraints that must not be violated (JSTOR TAS terms)

- The verbatim `context` column is confidential full text ("Advanced Research
  Data") — it must NOT ship to the viewer or any export. Only derived facts
  (work, passage, journal, year, DOI) may ship. Verified structurally in the
  aggregator.
- The tool must remain a **finding aid that links OUT** to JSTOR, never a
  content mirror (satisfies the "no substitute" clause).
- Do not use the corpus to train/fine-tune any LLM/AI model.
- DOIs are cleared to ship: 98% of article records carry resolvable
  `10.2307/<number>` stable DOIs; export keys on `ithaka_doi` with a plain-
  citation fallback; raw JSTOR `iid` is never surfaced.

---

## Next steps (in order)

1. **Shared filter bar** — the connective tissue both views need. 10 journal
   checkboxes (select-all/none), a year-range slider 1887–2022 (default a recent
   window; ~75% of citations are post-1980) with a volume sparkline behind it.
   Wiring this activates View B's by-journal split (already logic-ready) and is
   the prerequisite for the comparison plot.
2. **Comparison plot (on View A)** — plot selected works' attention **over time
   / by journal** against each other. This is View A's dynamic successor and
   the most scholarly-valuable dynamic feature. **Trustworthy-tier only** (or
   hard-flag uncertain works) — plotting uncertain floors over time graphs a
   quarter of the signal as if it were the whole. Depends on the filter bar.
3. **Merge the two views into one page** with the shared filter bar and a
   view switch; clicking a work's bar in View A should jump to that work in
   View B.
4. **Perseus "see the passage" deep-links** — a click on a passage (e.g. Meno
   77b) opens the actual text on Perseus (Tufts): Greek + a public-domain
   translation. Map our `work_id` + locus → Perseus canonical citation URN.
   This is the design-now/wire-after-filter-bar item. Keep it a link-OUT
   (consistent with the finding-aid principle), not a bundled translation.
5. **Deploy to GitHub Pages.** Small surface; could also be done earlier to
   flush out hosting wrinkles.

### Small polish items (non-blocking)
- View B x-axis: make book start/end **clearer** — a slightly stronger
  full-height reference line at each book boundary + alternating subtle zone
  banding. Frame as navigation, not a claim (book divisions are editorial). A
  one-line note under the chart ("book divisions are editorial; passage
  positions are exact") is the honest place to acknowledge the arbitrariness,
  rather than keeping dividers vague.

---

## Files (in `/home/claude/viewer/` this session; delivered to outputs)

**Ship / keep:**
- `build_viewer_data.py`, `locus.py` — the aggregator (run locally).
- `view_a.html` — View A (author map inlined; self-contained but fetches
  `view_a.json`).
- `view_b.html` — View B (fetches `Nicomachean_Ethics.json`, `Meno.json`,
  `meta.json`, `works_index.json`; wired to those two works in this standalone).
- `authors.json` — the Plato/Aristotle × Stephanus/Bekker map (now ALSO inlined
  into view_a.html; keep the file as the source of truth / for other views).

**Scratch / reference:**
- `compare.html` — the 3-encoding comparison (heatmap vs bars vs lollipop) used
  to decide View B's design. Verdict: tinted bars ON TOP + heatmap BELOW.

**Real data present in the project (from the aggregator):** `meta.json`,
`view_a.json`, `works_index.json`, `Nicomachean_Ethics.json` (1.8 MB — faceted,
trustworthy), `Meno.json` (uncertain, non-faceted), `collision_bands.json`.

---

## Known issues / deferred

- **View B file size:** each `view_b/<work>.json` carries the full `dots` array
  inline (NE = 1.8 MB). For the merged viewer, split each work into a light
  `cells` file (loads instantly) + a separate `dots` file fetched only on
  drill-in. Also eases the project-capacity squeeze David flagged (~80% full).
- **`collision_bands.json`** (within-work under-resolution shading) is generated
  and copied through but **not yet rendered** in View B. It's the 21-band /
  12-work overlay for flagging Bekker/Stephanus collision bands with a per-cell
  caveat. Wire into the heatmap when convenient.
- Claude's **image-view tool was intermittently broken** this whole session, so
  the views were verified via measured DOM geometry (bar widths, colours, tier
  order, tooltip contents) rather than screenshots. David confirmed the visuals
  by eye and they're correct — but a fresh visual QA pass next session is worth
  doing.
- **Bekker treatise boundaries:** the four *faceted* works' book divisions are
  verified; the larger table of remaining Bekker treatise boundaries (methods
  §9) is still an open, non-blocking item.
