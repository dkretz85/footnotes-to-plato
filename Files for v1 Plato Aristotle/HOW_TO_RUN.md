# Running the View B prototype

The viewer loads data with `fetch()`, so it must be *served*, not opened as a
file:// URL (browsers block fetch from file://).

1. Put `view_b.html` in the same folder as your `viewer_data/` files, OR copy
   these four JSON files next to it:
     - Nicomachean_Ethics.json
     - Meno.json
     - meta.json
     - works_index.json

2. From that folder, run:
     python3 -m http.server 8000

3. Open:  http://localhost:8000/view_b.html

This is a STANDALONE prototype of View B only, wired to two works
(NE = trustworthy/faceted, Meno = uncertain). The full viewer — shared filter
bar, View A floor/band/fade bars, all 68 works — comes next.
