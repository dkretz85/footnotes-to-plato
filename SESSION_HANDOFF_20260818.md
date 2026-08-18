# Session Handoff — Range/span parser + Homer/Pindar/Paul pipeline

**Session date:** 2026-08-18
**Scope:** Built the range/span expansion fix (Plato/Aristotle) AND the harvest +
expansion foundation for the new corpora (Homer, Pindar, Pauline NT). Locked and
ran the ONE re-harvest. The resolver is the next big piece and is fully specced
below. No resolver/aggregator/viewer changes yet.

Branch: `claude/footnotes-plato-parser-fix-g2s58u`. All work is committed locally
on that branch (David commits to GitHub manually — file list in §7).

---

## 0. TL;DR — where things stand

- **The single re-harvest is DONE and clean.** `citations.tsv` now contains
  Greek ranges intact (`620a-622c`), Roman-numeral NT (`II Cor 3:6`), dropped
  the noise `Pind` cue, and — critically — **every record has metadata** (the
  Aug-12 `"?"` problem is fixed: `records w/o metadata match: 0`).
- **The expansion core (`locus.py`) is complete and tested for all 5 systems.**
  Stephanus, Bekker (15-line bands), Homer/Pindar (single line), NT (verses,
  incl. cross-chapter). `expand_range()` is the shared entry point.
- **NEXT SESSION = the resolver** (`resolve_citations.py`): route Homer/Pindar/NT
  to works, fan every range row out into N unit rows via `expand_range`, stamp
  `span_src`, divert over-cap spans. Full spec in §4. Everything downstream of the
  harvest re-runs cheaply — **no second harvest needed.**

---

## 1. The harvest results (this run vs the Aug-12 run)

```
delivery records : 283,574          pages scanned : 1,870,831
citation matches : 607,773          records w/o metadata match: 0
   ambiguous 299,346 · stephanus 124,897 · bekker 79,110
   nt 62,291 · homer 37,198 · pindar 4,931
```

Every delta is explained and expected:

| corpus | Aug-12 | now | Δ | why |
|---|---|---|---|---|
| ambiguous | 314,878 | 299,346 | −15,532 | range endpoints that were 2 separate matches now merge into 1 range cell; de-overlap drops swallowed endpoints |
| stephanus | 131,343 | 124,897 | −6,446 | same: stephanus endpoints inside ambiguous ranges dropped by de-overlap |
| bekker | 80,274 | 79,110 | −1,164 | Bekker ranges merge to one cell |
| nt | 59,818 | **62,291** | **+2,473** | Roman-numeral letter numbers (I/II Cor/Tim/Thess) newly captured |
| homer | 37,198 | 37,198 | 0 | no Homer regex/cue change |
| pindar | 4,981 | 4,931 | −50 | dropped bare `Pind` cue (unresolvable noise) |

The Greek total dropping ~23k is NOT lost attention — those were double-counted
range endpoints; after the resolver expands the merged range cells, the covered
units are restored (and the interior units, previously invisible, are added).

### ⚠️ One thing to verify first tomorrow
The coverage block shows `requested: 0`, meaning the extractor did **not** load
`all_item_ids.txt` as the `--requested` roster and fell back to indexing the FULL
12.6M-record catalogue. The outcome is still correct (`records w/o metadata: 0`),
but confirm the old-delivery rows really carry journals now:
```bash
grep -cP '\t\?\t' citations.tsv          # expect 0 (no "?" journal/year/doctype)
```
If that's 0, we're good and the roster detail is moot. If not, re-run the harvest
passing `--requested all_item_ids.txt` (check the file is non-empty and the path
is right; `make_roster.py` writes ~283,574 iids).

---

## 2. Settled decisions (do NOT re-litigate)

- **Spans = attention to EVERY unit, equal weight.** No down-weighting. (Owner
  decision from the RANGE handoff.) A methods-page footnote is still TODO (§6).
- **Grain, per system** (store finest, bin for DISPLAY — never foreclose):
  - Stephanus (Plato): page + section (a–e). *(shipping grain, unchanged)*
  - Bekker (Aristotle): **store line-level; display in 15-line bands**
    (`band = line // 15`). Single cites keep their exact line; only a
    cross-column range interior rounds to bands (no per-column line counts).
  - Homer / Pindar: **single line.** The diagnostic settled it — median span = 1
    line (67% / 59% single-line). Binning would fabricate a unit nobody cited.
  - NT (Pauline): verse.
- **NT is Pauline-only** (13 letters). Gospels/Acts/Catholic epistles excluded by
  design (versification variance). Adding them later = another harvest.
- **Divert caps** (over-cap spans → review queue, not fanned out):
  Stephanus 40 units, Bekker 20, Homer 30 lines, Pindar 20, NT 30 verses.
- **Homer space separator kept** at harvest; down-weight at the resolver if it
  over-fires (reversible; dropping at harvest is not).

---

## 3. Pipeline state

| Stage | File | State |
|---|---|---|
| Extractor | `build_citation_db_v2.py` | ✅ done, ran the harvest |
| Roster | `make_roster.py` | ✅ done (see §1 caveat) |
| Line-span diagnostic | `diagnose_line_spans.py` | ✅ done its job |
| Cue audit | `cue_audit.py` | ✅ done its job |
| Expansion core | `locus.py` | ✅ all 5 systems + tests |
| NT verse table | `nt_chapter_lengths.json` | ✅ verified vs KJV |
| Cue→work table | `work_cues.json` | ✅ staged for resolver |
| **Resolver** | `resolve_citations.py` | ⏳ **NEXT — §4** |
| Aggregator | `build_viewer_data.py` | ⏳ span_src + per-corpus grain (§5) |
| Viewer | `view_b.html` etc. | ⏳ display new corpora (§5) |

---

## 4. NEXT TASK — the resolver (`resolve_citations.py`)

The resolver currently handles ONLY bekker/stephanus/ambiguous (via range tables
+ name/scope/title). Homer/Pindar/NT cells fall through `page_int()` → `None` →
dumped to `review_queue` as "no_page". Four changes, in order:

### 4a. Route the new corpora (cue → work)
For `corpus in {homer, pindar, nt}`: parse the cue from the match cell, `norm()`
it (the resolver already has `norm`), for NT convert a Roman letter-number to
Arabic first (`II Cor` → `2 cor`), then look up **`work_cues.json`** → `work_id`.
The cue NAMES the work, so confidence is high (method e.g. `cue_work`). No range
table needed. Set `book` directly from the parsed major unit:
- Homer: `work_id` = Iliad/Odyssey, `book` = book number (Arabic; expander
  already normalises Roman → Arabic).
- Pindar: `work_id` = Olympian/Pythian/Nemean/Isthmian, `book` = ode number.
- NT: `work_id` = e.g. "Romans", `book` = chapter.

### 4b. Fan-out via `locus.expand_range` (the core of the fix)
After a cell resolves to a work, expand it and emit **one output row per unit**:
```python
system = resolved_reference_system(corpus, wid)   # see note
nt_lengths = NT_TABLE["books"].get(wid) if corpus == "nt" else None
units = locus.expand_range(match_cell, system, nt_lengths=nt_lengths)
if units is None:
    -> divert whole cell to review_queue (reason "span_over_cap"/"span_incoherent")
else:
    for u in units:
        emit a row with match=u, work_id=wid, book=<major>, span_src=(match_cell if len(units)>1 else "")
```
**Critical `system` note:** an `ambiguous`-tagged cell is Plato OR low Aristotle.
`expand_range` MUST be called with the RESOLVED system, not `"ambiguous"`, because
the section alphabet differs (Plato a–e vs Bekker columns a/b). Use the resolver's
existing `work_system[wid]` (`"stephanus"` or `"bekker"`). For stephanus/bekker/
homer/pindar/nt tags, system == tag.

Single-unit cells return `[cell]` verbatim → the fan-out is a no-op → non-range
behaviour is unchanged (regression-safe). Dedup still works: N unit rows share
the iid, so the aggregator's per-cell iid-dedup counts the article once per unit.

### 4c. Add the `span_src` column
Append `span_src` as a NEW trailing column (after `context`) in resolved.tsv,
review_queue.tsv, excluded.tsv. Update the `cols` list and every writerow. Empty
for single-unit rows; the raw range string for fanned rows. (For the future drill
panel: "cited as part of 620a–622c".) Keep it AFTER context so existing indices
don't shift; `build_viewer_data` reads by index and ignores extras.

### 4d. Book faceting interaction
Greek unit rows keep `book=""` and are filled by the existing
`locus.py resolved.tsv > resolved_with_books.tsv` stage — which now works
correctly per-unit (each fanned row is a single unit, so cross-book spans get the
right book per unit). New-corpus rows get `book` set at resolve time (4a); they're
not in `FACETED_WORKS`, so the faceting stage leaves them alone.

### 4e. Verify-as-you-go (spot-checks)
- `620a-622c` (ambiguous→Republic) → exactly 13 unit rows, book X, span_src set.
- `Rom 3:21-26` → 6 verse rows; `Rom 7:25-8:2` → 3 rows (7:25, 8:1, 8:2).
- `Il. 16.7-11` → 5 line rows, work Iliad, book 16.
- A known Bekker cross-column range → band cells.
- Non-range Plato/Aristotle counts ≈ unchanged vs the pre-fix resolved output.

---

## 5. After the resolver — aggregator + viewer (data model)

`build_viewer_data.py` currently keys View B cells on `(book, page, sec)` and
parses via `locus.parse_locus`, which is **Greek-only** (`parse_locus("Il. 16.7")`
returns `(None,None,None)`). The plan:

- **Unify the cell key as `(work, major, minor)`**: Greek = (page, section[, line
  for Bekker band]); Homer = (book, line); Pindar = (ode, line); NT = (chapter,
  verse). This is a rename of the existing loop's key, not a restructure.
- Add per-corpus parsing (a small `parse_by_corpus(match, corpus)`), or emit
  major/minor as explicit columns from the resolver so the aggregator doesn't
  re-parse.
- Tolerate/optionally carry `span_src`.
- **Never emit `context`** (unchanged invariant).
- Bekker display: bin by `line // 15`.

Viewer (`view_b.html` etc.): render the new reference systems' axes (book.line,
chapter:verse). This is the deferred "UI redesign" — now we have real volumes to
design against (Homer 37k, NT 62k, Pindar 5k). Design against numbers, not in the
abstract.

---

## 6. Open calibration / TODO (post-resolver, no harvest needed)

- **Methods-page footnote** on the span decision (attention ≠ intensity; a span is
  counted as notice to each unit it covers).
- Homer Roman-book OCR noise (`IlI, 715` → Iliad I line 715, but book 1 has 611
  lines): a Homer/Pindar line-count table would let us validate + reject. Optional.
- Homer space-separator over-fire: inspect resolved cells, down-weight if needed.
- `Phil.` (Philippians) vs Philebus: audit confirmed clean (`:verse` guard), but
  spot-check in resolved output.
- Cross-book Homer ranges (`Il. 16.700-17.5`) currently mis-parse (rare) — divert
  or handle if they show up.

---

## 7. Files this session (commit these)

New: `build_citation_db_v2.py`, `make_roster.py`, `diagnose_line_spans.py`,
`cue_audit.py`, `nt_chapter_lengths.json`, `work_cues.json`, `test_expand.py`,
`test_expand_new.py`, `test_extractor_regex.py`.
Modified: `locus.py` (added `expand_range` + per-system expanders; `parse_locus`
untouched).

Tests: `python3 test_expand.py && python3 test_expand_new.py && python3 test_extractor_regex.py`
(all green). `build_citation_db_v2.py` renames to `build_citation_db.py` once
you're happy (replacing the old one), per the Aug-12 note.

Note: pushing to origin failed all session (403, read-only creds in the remote
env) — that's why it's local-only; commit manually.

---

## 8. The one-line mental model

Harvest captures raw range/cue strings intact → **resolver expands each into N
equal-weight unit rows** (via `locus.expand_range`) and routes the new corpora →
faceting labels books → aggregator bins per system → viewer renders. The
expensive step (harvest) is done and correct; everything left is cheap to iterate.
