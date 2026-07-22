# Footnotes to Plato

A passage-level citation index of the ancient-philosophy journal literature,
built from a JSTOR Text Analysis Support delivery.

Live at <https://footnotes.dkretz.com>

## Layout

```
build_viewer_data.py   aggregator: JSTOR delivery -> viewer_data/
locus.py               locus parsing + work boundaries (imported above)
build_site.py          static site generator (stdlib only)

view_a.html            viewer: works over time
view_b.html            viewer: passages within a work
filterbar.*            shared journal/year filter
series.*               time-series comparison chart
journal_groups.json    journal -> field (philosophy / classics)
work_groups.json       named sets of works for comparison

site/
  domain.txt           custom domain, written to docs/CNAME on every build
  content/*.md         page text
  static/*             site CSS/JS

viewer_data/           aggregator output (generated)
docs/                  built site (generated; GitHub Pages serves this)
```

## Build

```bash
python3 build_viewer_data.py     # regenerate viewer_data/ (needs local JSTOR files)
python3 build_site.py --draft    # render docs/ with noindex + draft banner
python3 build_site.py            # render docs/ for publication
python3 build_site.py --serve    # ...and serve at localhost:8000
```

No dependencies beyond the Python standard library.

## Publishing

GitHub Pages, Settings > Pages > Deploy from a branch > `main` / `/docs`.
The custom domain is regenerated into `docs/CNAME` on every build from
`site/domain.txt`, so it survives the build wiping `docs/`.

## Data & licensing

- Pipeline and site code: MIT
- Derived data (`viewer_data/`, `docs/data/`): CC BY 4.0
- Underlying JSTOR full text: **not redistributable**, never committed

See the About page for details.
