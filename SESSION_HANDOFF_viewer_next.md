# Session Handoff — Data pipeline COMPLETE; viewer is next

**Supersedes:** SESSION_HANDOFF_20260818.md (which ended at the harvest; resolver,
faceting, and aggregator are now all done and validated on the real corpus).
**Branch:** `claude/footnotes-plato-parser-fix-g2s58u`. All work committed locally;
David commits to GitHub manually (push is 403 in the remote env). `citations.tsv`
(240 MB) lives only on David's machine, as do the resolver tables and metadata.

---

## 0. TL;DR

The **entire data pipeline now runs end-to-end for all five reference systems** —
Plato (Stephanus), Aristotle (Bekker), Homer & Pindar (book.line), Paul (NT
chapter:verse) — from raw JSTOR text to viewer-ready JSON. Range/span citations
are fanned into their units; the new corpora are routed, expanded, faceted, and
aggregated. Validated on the real 283k-record corpus:
**493,652 resolved citation-units across 88 works.**

**The ONE remaining build is the VIEWER** (`view_b.html` + `view_a.html` +
`filterbar.js` / `series.js`): render the three new reference systems off the new
`system` tag. Everything it needs is already in `viewer_data/`.

---

## 1. What each stage does (all DONE)

    build_citation_db_v2.py  harvest raw cells (ranges + cues intact)   -> citations.tsv
    resolve_citations.py     route to works, FAN OUT ranges, span_src   -> resolved.tsv (+review_queue,+excluded)
    locus.py resolved.tsv    fill the book facet per unit               -> resolved_with_books.tsv
    build_viewer_data.py     aggregate per-system cells                 -> viewer_data/*.json

`locus.py` is the single source of truth: `expand_range(cell, system, nt_lengths)`
dispatches to per-system expanders (Stephanus sections, Bekker 15-line bands,
Homer/Pindar single line, NT verses incl. cross-chapter), and `work_cue_key`
maps a cued cell to its `work_cues.json` key. Reference data: `work_cues.json`
(cue->work), `nt_chapter_lengths.json` (Pauline verses-per-chapter, KJV-verified).

Run order to regenerate from citations.tsv (no re-harvest ever needed again
unless the EXTRACTOR changes):

    python3 resolve_citations.py citations.tsv
    python3 locus.py resolved.tsv > resolved_with_books.tsv
    python3 build_viewer_data.py --tsv resolved_with_books.tsv --queue review_queue.tsv \
        --meta jstor_metadata_2026-07-18.jsonl.gz --bands collision_bands.json --outdir viewer_data

---

## 2. THE VIEWER — the data contract it consumes

`build_viewer_data.py` tags every work with a `system` in **both** `works_index.json`
and each `view_b/<work>.json`: one of `stephanus | bekker | homer | pindar | nt`.
Render axes by system. Each View B cell is:

    {"book","page","section","band","count","articles","by_journal"}

Interpretation per system (the fields are reused; `system` tells you how to label):

| system    | facet (`book`) | major (`page`) | minor (`section`) | `band`        |
|-----------|----------------|----------------|-------------------|---------------|
| stephanus | dialogue book  | Stephanus page | section a-e       | 0 (unused)    |
| bekker    | treatise book  | Bekker page    | column a/b        | line//15 band |
| homer     | book 1-24      | line           | "" (empty)        | 0 (unused)    |
| pindar    | ode number     | line           | "" (empty)        | 0 (unused)    |
| nt        | chapter        | verse          | "" (empty)        | 0 (unused)    |

So: Plato = page x section grid; Aristotle = page x column, each column split into
15-line bands; Homer/Pindar = book x line (dense — Iliad lights ~69% of its lines);
NT = chapter x verse. `dots` carry per-citation detail (deduped by iid) with the
same page/section/line fields + doi/title/author.

**Design steer (from the real volumes):** the "Others" are NOT a footnote —
Homer ~88k + NT ~145k + Pindar ~11k units ≈ the whole Plato+Aristotle core. Give
the new systems first-class presentation, not a bolted-on tab. This is the
"UI redesign" the older handoffs deferred until real numbers existed. They exist
now (see §4). Recommend: read `view_b.html` first, propose per-system rendering,
THEN build.

---

## 3. Real-corpus numbers (last full run)

- Resolved units: **493,652** across **88 works**, 48 journals.
- New-corpus mass (citation-units): Odyssey 53,870 · Romans 43,094 · 1 Cor 35,215 ·
  Iliad 34,385 · Galatians 18,088 · … · Pythian 4,658 · … · Philemon 17.
- Review queue: **202,600** (~45%) — the resolver's PRE-EXISTING conservative
  Greek ambiguity (a bare 2-3 digit page in-range for several dialogues, no name/
  scope). Not caused by this arc; name it as the standing limitation.
- `cue_unresolved` 114 (near-total cue coverage); `span_diverted` 4,032 (~1.5%).
- Flagship fix confirmed live: `Meno 80D5-E5` -> cells 80d + 80e (was truncated
  to 80D5); `Euthydemus 276e-277c` -> 276e,277a,277b,277c.

---

## 4. Remaining calibration (all cheap; resolver+aggregator re-run, NO re-harvest)

1. **book-0/line-0 Homer/Pindar guard — DONE (committed).** Needs a resolver +
   aggregator re-run to clear the phantom cells from `viewer_data/`.
2. **Methods-page footnote** on the span decision (settled long ago): a citation
   records THAT a passage drew notice, never how much; a span is counted as notice
   to each unit it covers because guessing where within it the weight sat would be
   the greater fabrication. Add to the methods markdown.
3. **Space-separated Homer** (`Od. 4 4`): kept at harvest, ~9% of Homer. Inspect
   resolved cells; if it over-fires, down-weight or divert at the resolver.
4. Optional: a Homer/Pindar per-book line-count table would let us validate line
   numbers (not just book range) — deeper than the §1 guard, low priority.

---

## 5. Files (all committed on the branch)

New this arc: `build_citation_db_v2.py`, `make_roster.py`, `diagnose_line_spans.py`,
`cue_audit.py`, `resolve_citations.py`, `nt_chapter_lengths.json`, `work_cues.json`,
`test_expand.py`, `test_expand_new.py`, `test_extractor_regex.py`.
Modified: `locus.py` (expanders + work_cue_key), `build_viewer_data.py` (all-system
aggregation + Aristotle bands + reason-column fix).
Tests (all green): `python3 test_expand.py && python3 test_expand_new.py && python3 test_extractor_regex.py`.

Once validated, `build_citation_db_v2.py` can be renamed to `build_citation_db.py`
(replacing the old one), per the original Aug-12 note.
