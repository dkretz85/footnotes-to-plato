# Site build — setup

## Layout

Put everything in one directory:

```
your-repo/
  build_site.py            <- the generator
  build_viewer_data.py     <- the aggregator (run this first)
  locus.py                 <- unchanged, from the project
  view_a.html  view_b.html
  filterbar.js  filterbar.css
  series.js     series.css
  journal_groups.json  work_groups.json
  site/
    content/               <- page text (Markdown)
      index.md  about.md  methods.md  data.md  contact.md
      _intro_works.md  _intro_passages.md
      citation-pipeline-methods.md   <- COPY THIS IN from the project
    static/
      site.css  site.js  landing-bars.js
  viewer_data/             <- created by build_viewer_data.py
  docs/                    <- created by build_site.py; commit this
```

Two files must be copied in by hand, since they're yours rather than mine:

1. `site/content/citation-pipeline-methods.md` — from the project. This becomes
   `/methods/pipeline/`, the detailed record. Without it that page is skipped.
2. `locus.py` — unchanged; the aggregator imports it.

## Build

```bash
python3 build_viewer_data.py        # regenerates viewer_data/ (needs ~/Downloads files)
python3 build_site.py               # renders docs/
python3 build_site.py --serve       # ...and serve it at localhost:8000
```

`build_site.py` uses only the Python standard library. No npm, no framework, no
build toolchain to rot.

## Publishing on GitHub Pages

1. Commit `docs/`.
2. Settings → Pages → Source: *Deploy from a branch* → branch `main`, folder
   `/docs`.

That's it. `.nojekyll` is emitted automatically so Pages serves the files as-is
rather than running Jekyll over them.

**Before publicising**, replace the placeholders:

- `site/content/contact.md` — email address and repository link (currently
  marked *"add your address here before publishing"*).
- `site/content/about.md` — the Pages URL and DOI in the citation block.
- Consider adding `<meta name="robots" content="noindex">` to
  `build_site.py`'s `page()` head while drafting, and removing it when ready.

## Editing

- **Page text** → edit the `.md` in `site/content/`, rebuild.
- **Navigation** → the `NAV` list at the top of `build_site.py`. One place;
  every page's header and footer regenerate from it.
- **Site styling** → `site/static/site.css`. The viewers keep their own inline
  styles, so this won't disturb them.
- **The two viewers** → still standalone files. `build_site.py` extracts their
  body, styles and scripts and re-hosts them inside the site chrome, rewriting
  asset and data paths. You can still open `view_a.html` / `view_b.html`
  directly against a local `viewer_data/` for quick iteration.

## The Markdown subset

Headings, emphasis, lists (nested), tables, fenced code, blockquotes, links,
images, horizontal rules — and raw HTML passes through, which is how the landing
page does its stat row and callouts. `<script>` and `<style>` blocks are
protected from the converter.

It is not a general Markdown engine. If a document needs something it doesn't
support, write that bit as HTML in the `.md` and it will pass through untouched.

## Content notes

- **Word counts are placeholders in one place only**: the About page's citation
  block needs your URL and DOI.
- **`work_groups.json`** still wants your review — the early/middle/late Plato
  chronology and the theoretical/practical split are marked `contested` and
  warn in the UI when plotted. Replace with your own scheme if you prefer.
- The landing page states coverage limits prominently (ten journals, articles
  only, Anglophone-skewed) and shows the tier chart before anything
  interactive, per the "epistemically upstream" principle.
