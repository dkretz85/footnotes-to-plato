# Session Handoff — Corpus Expansion (Homer · Pindar · Paul)

**Session date:** 2026-08-07 (evening)
**Scope:** planning + request-building + taxonomy design for expanding *Footnotes to
Plato* beyond Plato/Aristotle. No pipeline code shipped this session; parser
implementation handed to Claude Code (see companion `HOMER_PINDAR_HANDOFF.md`).

---

## 1. What happened this session (decisions, settled)

### JSTOR request — SUBMITTED
A second TAS dataset request was built and filed. Status: awaiting response
(expected a few days to a few weeks; delivery link lives 60 days once granted).

- **Two tiers, new-only** (no journal already in the current 10-journal corpus,
  so the new delivery is a clean `iid`-partition — fusion = concatenate + rerun,
  NO dedup needed).
- **T4 classics (Homer/Pindar):** American Journal of Philology, Harvard Studies
  in Classical Philology, Mnemosyne, TAPA (**3 dated strings** — all needed),
  Greece & Rome, The Classical World, Classical Antiquity, The Classical Journal,
  Quaderni Urbinati di Cultura Classica (Pindar-relevant), Illinois Classical
  Studies, Hermes, Rheinisches Museum (**2 strings**). German venues deliberately
  included (Homer scholarship is bilingual).
- **T5 theology (Paul, wide+multilingual):** CBQ, JBL (+ predecessor string),
  Biblica, Novum Testamentum, Neotestamentica, The Biblical World, American
  Journal of Theology, Harvard Theological Review, Journal of Religion, Church
  History, Religious Studies, History of Religions, American Journal of Theology &
  Philosophy, Vigiliae Christianae, Recherches (**2 strings**), Zeitschrift für
  katholische Theologie, Zeitschrift für Theologie und Kirche, Theologische
  Rundschau, Deutsche Theologie, Revue de Théologie et de Philosophie (**2
  strings**).
- **Totals:** 38 exact strings / ~30 distinct journals / 214,397 items /
  0 unmatched rows. `build_request.py` ROSTER updated (T4 + T5 tiers) and verified
  to parse (accents intact).
- **Request form:** "Product development?" answered **No** (consistent with prior
  request; the tool is a non-consumptive finding aid that drives traffic TO JSTOR
  via stable links — the anti-substitute — so "No" is both honest and
  strategically correct). Purpose framed as non-consumptive DH text analysis.

### Scope decisions (settled — don't re-litigate without saying so)
- **Homer:** two works × 24 books, canonical.
- **Pindar:** four victory-ode books only (Ol./Pyth./Nem./Isth.). **Fragments
  excluded** (edition-dependent numbering).
- **Joint build, Homer-first:** Homer to verifiable-shippable before Pindar layers
  in. Never two half-built corpora in flight.
- **Paul first among NT texts:** the requested full-text is NT-wide, so extending
  later to Gospels / whole NT needs NO new JSTOR request — only recognizer work on
  the already-built machine. Paul chosen as beachhead (cleanest versification,
  most philosophy-adjacent, most distinctive abbreviations).

---

## 2. Parser plan (→ Claude Code; details in HOMER_PINDAR_HANDOFF.md)

The one non-obvious point: **`book.line` needs a SECOND grammar + a router.**
`locus.py :: parse_locus` is hardwired to the Greek page-reference shape
(`page + section-letter + line`). Homer/Pindar are `book.line` (two ints + a
separator) — a different grammar. Add `parse_locus_bookline` + a `REF_SYSTEM`
router dispatching each work to stephanus | bekker | bookline. It's the *easy*
kind of new grammar (no cross-system collision, no boundary pages).

**Gating:** parser *grammar* is buildable now against hand-made test strings.
The abbreviation *recognizer* must be calibrated from REAL match cells once the
journals land — populate synonym tables from a frequency scan, not a priori.
Conservative posture: bare `1.1` with no work cue → review queue, never a guess.
Different abbreviation schemata (Greek book-letters, comma-style `1,1`,
`Hom. Il.` vs bare `Il.`) accepted only as they actually appear in the corpus.

Companion files drafted this session: `homer_ranges.json`, `pindar_ranges.json`
(skeletons — book counts canonical; per-book line bounds left as placeholders for
Claude Code to populate or skip).

---

## 3. Review-as-monograph-window (NEW insight → tri-state toggle)

The theology delivery is **~51% book reviews** (108,816 / 214,397), wildly uneven
by journal (ZkTh 77%, Church History 80%, CBQ 78%; vs several 0%).

**Reframe (David):** reviews aren't just noise — they're the ONLY window this
journal-only corpus has onto the *monograph* world (invisible otherwise). For
Homer and Paul especially, whole books focus on a few lines / one letter, and a
review plausibly reflects that. Weak signal, but a real complement.

**Decision: tri-state viewer toggle**
1. Articles only (default; high-precision "scholarly attention")
2. Articles + reviews (enriched; monograph shadow)
3. Reviews only (crude map of where *monograph* attention concentrates — divergence
   from the article map is itself an interesting finding)

Caveats: global one on landing page; "reviews tag venue/monograph-proxy, NOT
passage-precision" gloss in the toggle hover + methods page. Monograph-window
effect is *strongest* for the new epic/NT corpora, weaker for existing philosophy
corpus — say so, don't imply uniformity.

**PREREQUISITE (→ Claude Code, gated on data):** a `doctype` audit. Several
journals report 0 reviews — web-checked this session:
- **HSCP zero is REAL** (publisher confirms articles-only annual; no audit needed).
- **TAPA zero is SUSPECT** (historically introduced reviews at some point — likely
  partial tagging gap).
- Pattern: annual/essay-collection venues (HSCP, likely Illinois CS, California
  Studies) plausibly genuinely review-free; society + continental venues (TAPA,
  Hermes) more likely mis-tagged. Audit is now **targeted**, not a blind sweep:
  confirm suspect zeros + confirm `REVIEW_HINTS` catches the `content_subtype`
  strings the society/German/French journals actually use. The tri-state toggle
  can't be trusted until the article/review split is clean.

---

## 4. Journal taxonomy for Paul (NEW design — two ragged-tree axes)

Two **journal-level** overlays (hand-assigned lookup tables, ~like
`journal_groups.json`; never touch the parser). Both are **ragged trees**: robust
top level, branch-conditional depth, unequal n. Data model: **path-valued tags**
(list-of-paths per journal, allowing primary + optional secondary), NOT fixed
two-field. UI: **progressive disclosure** — expose a sub-level only where it's
populated enough to be more than a relabeled single venue. Methods-page caveat for
both: *these tag the VENUE, not the scholarship or the scholar.*

### Discipline axis
- **L1: insider vs outsider** (divinity-school/theology-faculty world vs secular
  religious-studies world). This is the STURDY, defensible, interesting split —
  "insider vs outsider attention to Paul" is well-supported. Privilege it.
- **L2 insider:** the fourfold-plus — biblical studies/exegesis · patristics/early
  Christianity · historical/church history · systematic/constructive theology ·
  (+ philosophy of religion as an insider-adjacent straddle). Maps roughly onto the
  classic theological-encyclopedia curriculum.
- **L2 outsider:** subdivides too (historical-comparative · philosophical ·
  philological-textual · social-scientific) — BUT thinly populated here, so
  **outsider stays terminal-in-practice** in the UI (see census below).
- Design signal: shallow contrasts = sturdy; deep contrasts = speculative. Let
  users descend but have the interface signal the slope (uncertainty-visible
  principle expressed through interaction depth).

### Confession axis
- **L1: strength-graded** (NOT denomination-sorted): strongly/explicitly
  confessional · confessional-but-ecumenical (flag these AS SUCH) · non-confessional
  academic · unclear. Every assignment defensible from the journal's own
  self-presentation.
- **L2 (only under "strongly confessional"):** denominational clusters — but only
  **Catholic** is populated enough to expose (CBQ, ZkTh, Biblica?, Recherches?).
  The "strongly Catholic journals only" filter David wanted IS defensible.
  Protestant/Orthodox clusters unpopulated → not exposed. German-Protestant and
  French-Reformed venues placed coarsely (ecumenical/unclear), not forced into a
  one-journal "Protestant" cluster.

### Provisional census (all `?` = close-read targets, not shippable)
Populated & exposable: insider fourfold (all four have real journals); Catholic
confessional cluster (3–4). Thin/terminal: outsider sub-tree (~2 nodes, 1 journal
each, one shared via straddle). Straddle/multi-tag cases (~5, handle by hand):
Religious Studies (insider-adj phil / outsider phil), Church History
(historical/patristics), Harvard Theological Review & ZkTh (span many insider
sub-fields → maybe "general theology"/multi-tag), Revue de Théologie et de
Philosophie (theology/philosophy).

Confirmed via web this session: Religious Studies = phil-of-religion (straddle);
History of Religions = clean outsider (comparative, Eliade-founded, "religion as
exclusively human phenomenon").

---

## 5. When-the-data-lands checklist (one sitting, ~22 journals in front of you)
1. **`doctype` audit** (targeted — §3): verify suspect zeros, fix `REVIEW_HINTS` /
   classification so article/review split is clean. GATES the tri-state toggle.
2. **Fuse** new delivery into main TSV (concatenate + rerun; confirm `iid` is
   stable across deliveries — one-line collision check).
3. **Populate abbreviation recognizers** for Homer/Pindar from real match-cell
   frequency scan (conservative; check whether single-letter Pindar forms
   O./P./N./I. actually appear before including them).
4. **Discipline tags** (`journal_discipline.json`): per journal, read
   masthead/scope → assign L1 insider/outsider + L2 path (primary + optional
   secondary).
5. **Confession tags** (`journal_confession.json`): per journal, assign strength
   grade + ecumenical flag; confirm Catholic-cluster membership.
6. **Branch-population check:** only expose a sub-level with ≥2 real journals;
   collapse singletons to parent and note why.

---

## 6. Open questions / deferred
- **View B faceting for Pindar:** four-works vs per-ode profiles — decide AFTER
  seeing citation density (is Ol.1 more like Ol.5 or Pyth.8? data decides). Same
  deferred faceting question for Homer book-vs-line-band grain.
- **Outsider discipline sub-tree:** conceptually 4-way, currently ~2 thin nodes.
  Revisit if future deliveries add comparative-philology / sociology-of-religion
  venues.
- **Confession L2 beyond Catholic:** only Catholic exposable now; revisit if a
  future NT/theology request populates a second cluster.
- **Whole-NT expansion:** data already covers it; purely recognizer work later.
  "27 books at chapter:verse" is a future View B real-estate question.
- **Missing NT heavyweights** (New Testament Studies, JThS, ZNW, Journal of Early
  Christian Studies) — did NOT appear under a wide net; almost certainly outside
  JSTOR's full-text delivery (Oxford/Cambridge/De Gruyter platforms). Add later
  only if a future delivery includes them.
- **Paul as sibling instance:** own landing/filter bar/journal corpus, shares
  pipeline+viewer code. Architecture supports the split; nothing committed yet.

---

## 7. Working-rules notes
- Divide of labor held: this session = planning/diagnosis/prose/taxonomy in chat;
  parser implementation → Claude Code with repo + local data.
- Everything gated on the JSTOR delivery, which is the slow resource — spent
  generously (NT-wide, multilingual) so future extensions don't re-request.
- Companion artifacts from this session: `HOMER_PINDAR_HANDOFF.md`,
  `homer_ranges.json`, `pindar_ranges.json`, updated `build_request.py`,
  updated `find_titles.py` (expansion + theology-survey fragment sets).
