# Handoff: Footnotes to Plato — landing page + Viewer C ("passage-level attention shifts over time")

## Overview

Two designs for **footnotestoplato** (repo: `dkretz85/footnotes-to-plato`, branch `main`):

1. **Landing page** — the site's front door. Lede, corpus figures, previews of the three viewers, caveats (including a short floor-vs-fade sample chart), citation + acknowledgements.
2. **Viewer C** — the third of the three tools: *within a single text, how the distribution of scholarly attention shifted across decades*. Two steps: a text index, then the per-text map.

Both are built in the visual language of the existing site (`docs/static/site.css`, `filterbar.css`, `series.css`) — same header, footer, paper panels, serif/mono stacks, lavender/clay palette.

## About the design files

The files in this bundle are **design references written as HTML**. They are prototypes of look and behaviour, not production code to lift. The task is to **recreate them inside the existing site generator** — this site is built by `build_site.py` into static pages under `docs/`, with plain JS viewers (`series.js`, `filterbar.js`, `landing-bars.js`) reading JSON from `viewer_data/`. Follow those established patterns; do not introduce a framework for these two pages.

The `.dc.html` files use a small in-browser component runtime (`support.js`) purely so the prototype could be authored quickly. **None of that runtime should ship.** Read them as: a template (markup + inline styles) plus a class whose `renderVals()` computes the values the template interpolates. Every visual decision lives in the inline styles; every rule about *when* something renders lives in `renderVals()`.

Open either file directly in a browser to see it.

## Fidelity

**High-fidelity.** Colours, type, spacing, radii, and the copy are final unless flagged below. Recreate pixel-for-pixel using the site's existing CSS classes where they already exist (`.panel`, `.callout`, `.statrow`, `.cap`, filter-bar chips) rather than re-declaring the inline styles from the prototype.

**What is real data vs. illustrative** — this matters more than usual here:

| Element | Status |
|---|---|
| Text names, distinct-article counts, faceted flags | **Real** — `viewer_data/works_index.json` |
| Corpus figures (88 texts, 48 journals, 1827–2022, 493,233 placed citations) | **Real** — `viewer_data/meta.json` |
| Reference spans on band labels (Stephanus / Bekker pages), book divisions | **Real** — `stephanus_ranges.json`, `bekker_ranges.json`, `metaphysics_books.json`, `ethics_books.json` |
| Journal-set membership and share weights (`AUSHARE`, `SETSHARE`) | **Illustrative** — derived by eye from `meta.json`'s `journal_counts`; replace with the real grouping from `journal_groups.json` |
| Per-ode Pindar counts | **Apportioned, not measured** — the index holds Pindar at book level (Olympian 346, Pythian 703, Nemean 538, Isthmian 178); the prototype splits each total across its odes. If the pipeline can emit per-ode counts, use them; if not, keep the "apportioned" note visible |
| Shift verdicts (moved one way / rose and fell / steady / too thin), heat values, volume curve | **Illustrative** — placeholders until the temporal run covers the full 48-journal corpus. The *shapes of the verdicts* are specified; the values are not |
| Floor-vs-fade sample bars on the landing page | **Illustrative fade lengths**, real solid counts. Ground the fades in the collision pass |

---

## The one structural rule

**A caption may never outlive the branch it describes.**

Every failing review in this design's history was the same bug: a sentence describing a view that was no longer on screen ("no before-and-after is offered, because…" printed next to a before-and-after). The fix is structural, and the implementation must preserve it:

> The shape verdict, the view mode, and the caption are derived **together, from one object, in one place**. Nothing downstream re-decides what to show.

In the prototype that place is `renderVals()`: `code` (the verdict) determines `statement`, `whyThis`, whether the split summary is offered at all, and which glyphs render — in a single pass. Do not scatter these into template conditionals. If a verdict gains a case, every string for that case is added in the same object, or the page can print a caption for a state that cannot exist.

The same discipline governs the grain toggle: only the levels a text actually has are offered. Five works are faceted (`Republic`, `Laws`, `Metaphysics`, `Nicomachean Ethics`, `Eudemian Ethics`); every other text is passage-only, and for those the book button is **not rendered** with an explanation in its place — never rendered-and-disabled.

---

## Screens

### 1. Landing page (`Landing Page.dc.html`)

Single column, `max-width: 1120px`, `padding: 44px 24px 90px`, sections stacked with `gap: 30px`.

**Header (sticky).** `rgba(241,240,251,.94)`, `backdrop-filter: saturate(1.6) blur(8px)`, 1px bottom border `#ddd9ee`. Brand at 19px serif ("Footnotes to Plato" 600 + italic 400 `… and others` in `#5b6478`). Nav right-aligned, 13.5px, `#5b6478`, 6px/10px padding, 6px radius; current page is `#5a5497` 600 on `#eae7f7`. Items: Home · Texts over time · Passages · Passages over time · Methods · Data · Contact — i.e. **one nav entry per viewer** (labels are placeholders pending the final viewer names).

**Page head.** `h1` 44px serif 600, "(and Others)" in 400 italic `#5b6478`. Subhead 15px `#5b6478`.

**Lede panel.** White, 1px `#ddd9ee`, 10px radius, shadow `0 1px 2px rgba(28,34,48,.06), 0 4px 16px rgba(28,34,48,.06)`, padding `34px 38px 36px`. Prose column `max-width: 96ch`, `gap: 15px`, 16.5px/1.7. First paragraph is 19px serif. Copy is final (author-supplied) — the journals link points to a **Methods subsection anchor** (`#methods-journals`), not the Data page.

**Figures row.** 5-up equal grid, `gap: 14px`; each card white, 10px radius, padding `18px 20px 16px`; number 29px serif 600; label 9.5px mono, `.11em` tracking, uppercase, `#5b6478`. Values: 5 ancient authors · 88 texts indexed · 493,233 citations placed to a passage · 48 journals included · 1827–2022 period covered.

**The three tools.** Section label 10px mono uppercase. Three stacked cards, each an `<a>`: `grid-template-columns: 300px 1fr`, `gap: 0 30px`, padding `24px 30px`. Left is a 150px-tall abstract thumbnail built from divs (no images): **A** = two series of columns rising across decades (lavender + clay); **B** = ranked horizontal bars; **C** = a heatmap grid. Right: kicker (9.5px mono uppercase `#8a90a0`, `flex:none; white-space:nowrap`) + title (23px serif 600) on one baseline row, body 14.5px/1.65 `#3d4453` at `max-width: 64ch`, then "Open →" 10.5px mono `#5a5497`.

Titles are fixed: **Viewer A — Attention to text (clusters) over time**; **Viewer B — Passage-level attention distribution**; **Viewer C — Passage-level attention shifts over time**.

**Caveats panel.** Heading 28px serif. Three columns, `gap: 22px`, each with a 2px `#ddd9ee` top rule: *Select journals ≠ the whole field* · *Uneven across two centuries* · *Every count is a floor*.

Inside it, the **short floor-vs-fade sample**: clay callout (`#faf1ea`, border `#e7d3c4`, 9px radius, padding `22px 24px 24px`) holding eight sample texts. Row grid `150px 1fr 62px`: right-aligned serif label, bar track 15px tall, mono count. Solid = `#5a5497`; fade = `linear-gradient(90deg, rgba(176,106,58,.5), rgba(176,106,58,0))`, both 13px tall, shared max scale. Legend beneath a 1px `#e7d3c4` rule, with "All 88 texts, in Methods →" pushed right (`white-space: nowrap`). **The full floor-vs-fade chart for all texts moves to Methods** — this is the sampler, deliberately short.

**Citing / acknowledgements.** White panel, prose at `max-width: 96ch` to match the lede. Citation string is now: *Kretz, David, Footnotes to Plato: A Passage-Level Citation Index for Ancient Texts,* Version 2.0, date. Acknowledgements copy unchanged from the current site.

**Footer.** `#eceafa`, 1px top border, 13px `#5b6478`, link column right.

### 2. Viewer C — Step 1, the text index (`Viewer C v2.dc.html`, `screen: "list"`)

**Purpose:** pick a text. Nothing else. There is no classification step and no mode chooser.

Panel: white, 10px radius, padding `30px 34px 34px`. Title 30px serif 600 ("How attention shifted over time within a single work"), subhead 13.5px `#5b6478` at `max-width: 80ch`, 1px `#ddd9ee` rule beneath.

**Author blocks**, chronological (Homer, Pindar, Plato, Aristotle, Paul), `gap: 20px`. Each is `grid-template-columns: 132px 1fr; gap: 0 20px`: a right-aligned 10.5px mono uppercase author label in the author's colour with a 2px right border at `33` alpha, then the texts.

**The texts are a grid, not wrapped inline items** — `display: grid; gap: 6px; grid-template-columns: repeat(4, minmax(0,1fr))` (Pindar: 6 columns, since odes are cited by abbreviation and run short). Equal columns mean every row ends flush at the right edge; this is the "quiet gravitas" requirement and should not be reverted to `flex-wrap`. Each cell: `display:flex; justify-content:space-between; align-items:baseline; min-width:0`, padding `6px 11px`, 7px radius, 2px left border in the author colour over the author's pale tint; title 15.5px serif (ellipsis on overflow), count 10px mono `#8a90a0`, `flex:none`.

Author colours (data only — never on chrome): Homer `#7d6a2a` / tint `#f9f8f3`; Pindar `#3f6f9c` / `#f4f8fc`; Plato and Aristotle per `AU` in the file; Paul `#a15a72` / `#fcf6f8`.

Pindar's odes are **separate texts**, listed as `Ol. 1`, `Pyth. 4`, `Nem. 7`, `Isth. 3` — the abbreviations they are cited under.

**"Too thinly cited to test" panel**, below the lists: `#faf1ea`, border `#e7d3c4`, 3px left border `#b06a3a`, radius `0 9px 9px 0`, padding `18px 20px`. Heading 17px serif + count in 10px mono clay, right-aligned. Explanatory paragraph 13px/1.6 at `max-width: 84ch`. Then the thin texts themselves, grouped by author on the same `132px 1fr` grid, 4 columns (Pindar 6), cells on white with a plain `#e7d3c4` border and muted `#8a7566` text.

These texts **live only here** — they are not also in the lists above. A text is "never testable" when it fails at every grain and in every journal set. They remain clickable: opening one shows its citation volume over time and says why no map is drawn.

Closing note: 10.5px mono clay, stating what is real and what is illustrative.

### 3. Viewer C — Step 2, the map (`screen: "work"`)

Back link ("← all texts", 10px mono uppercase lavender). Title row: author-coloured bar, 31px serif title, mono meta right.

**Control bar** (filter-bar treatment, structural not saturated): "Read at" + grain buttons + "Journals" + set buttons (All / Philosophy / Classics / Theology & NT — all four now live) + the set's one-line description in 10.5px mono. Chip styles: on = `#5a5497` fill, white text; off = white, `#5a5497` text, `#ddd9ee` border.

**Finding block.** Two glyph tiles (direction; whether specific passages lead) at 86px min-width, then the verdict as a sentence in 19px serif, then a smaller paragraph explaining how to read the map and — where applicable — why a before-and-after is or is not offered.

**The heatmap is the view.** Passages (or books) down, decades across (1890s–2020s), cell opacity `.06 + v*.88` in the author's RGB. Rows 17px with 3px gaps; above 26 rows a density toggle drops to 6px/1px and thins the labels to every fifth. A volume curve sits above the decade axis so a dark band in a thin decade cannot be misread. Early decades' labels are muted (`#b9bcc7`) because the corpus is thin there.

**Split summary** (before/after around a chosen year) is offered **only** for one-direction, passage-led texts, as an opt-in panel below the map — never as a rival view. The compare panel is present but disabled pending real per-journal series.

## Interactions

- Click a text → step 2 (`screen`, `work` set; `splitOpen`/`cmpOpen` reset to false).
- "← all texts" → step 1. No route change in the prototype; wire to real URLs (`/explore/shifts/<work>/`).
- Grain toggle: only valid levels rendered; invalid level replaced by a short explanation.
- Journal-set toggle: recomputes the verdict, the sentence, the map, and the availability of the split summary together.
- Density toggle appears only above 26 rows.
- Split summary: opens on click, year selectable; only for `1p` verdicts.
- No animation beyond default hover; hover on chips/cells is a border/opacity change only.

## State

`screen` (`list` | `work`), `work` (string | null), `grain` (`coarse` | `fine`, forced to `fine` when the text is not faceted), `jset` (`all` | `phil` | `classics` | `theo`), `split` (year), `splitOpen`, `cmpOpen`, `metric` (`share` | `absolute`), `density` (`full` | `glance`).

Data needed per text, per grain, per journal set: the verdict code (`1p` one-direction passage-led, `1w` one-direction diffuse, `rp` rose-and-fell passage-led, `rw` rose-and-fell diffuse, `s` steady-and-powered, `t` too thin), the decade × unit matrix, per-decade volume, and which units are named movers (FDR-solid **and** clear of the early-count floor — see `TEMPORAL_FINDINGS_POST_AUDIT.md` §8).

## Design tokens

Colours: page `#f1f0fb`; panel `#fff`; border `#ddd9ee`; ink `#1c2230`; secondary ink `#3d4453`; muted `#5b6478`; faint `#8a90a0`; rule-muted `#b9bcc7`; lavender `#5a5497` (hover `#403b78`), lavender tint `#eae7f7`, lavender line `#c9c5e4`; clay `#b06a3a`, clay paper `#faf1ea`, clay border `#e7d3c4`, clay ink `#8a7566`; footer `#eceafa`; volume bars `#e2ddcc`.

Type: serif `'Iowan Old Style','Palatino Linotype',Palatino,'Book Antiqua',Georgia,serif` (44/31/30/29/23/22/19/17/15.5/14.5px); sans `'Inter','Helvetica Neue',Arial,system-ui` (16.5/15/14.5/13.5/13/12.5px); mono `'SF Mono',ui-monospace,'Cascadia Mono',Menlo,Consolas` (11/10.5/10/9.5/9/8.5px, uppercase with `.08–.14em` tracking). Body line-height 1.6–1.7; headings 1.1–1.2.

Spacing: 3 / 6 / 7 / 10 / 14 / 18 / 20 / 22 / 30 / 34 / 44px. Radii: 2px (cells) · 6–7px (chips, rows) · 9px (callouts) · 10px (panels). Shadow: `0 1px 2px rgba(28,34,48,.06), 0 4px 16px rgba(28,34,48,.06)`.

**Colour discipline (from the site's own stylesheet):** saturated colour is reserved for data. Author colours appear in the heatmap, the volume curve, and the list rows — never on buttons, chips, or callouts. Controls are white/lavender; warnings are clay.

## Assets

None. Every graphic — thumbnails, glyphs, bars, heatmap — is built from divs and inline styles. No icon font, no SVG sprite, no images.

## Open decisions

1. **Common books.** `Nicomachean Ethics` V–VII and `Eudemian Ethics` IV–VI are one text cited under two works. The prototype marks them `*` in both book axes and prints a note. Decide whether to merge them into a shared unit or keep them apart to study how labelling splits attention — this changes the data model, not just the label.
2. **Nav labels** for the three viewers are placeholders.
3. **Per-ode Pindar counts** — see the table above.
4. **Where the full floor-vs-fade chart lives.** The landing page now carries only the eight-text sampler; the full chart is assumed to move into Methods.

## Files

- `Landing Page.dc.html` — landing page design reference
- `Viewer C v2.dc.html` — Viewer C, both steps
- `support.js` — prototype runtime; **do not ship**
- `github.md` — repo/branch, last sync, and the screen → source-file map
