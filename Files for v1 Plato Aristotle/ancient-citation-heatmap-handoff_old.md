# Hand-off memo: Passage-level citation heatmap for ancient philosophy

*Working note, July 2026. State of thinking before the build begins.*

## The idea in one line

Plato is cited by Stephanus number, Aristotle by Bekker pagination — both standardised — so with the right corpus one can count which passages the scholarly literature actually cites, by journal and by year, and visualise it as a passage-level heatmap.

## Why it's worth doing

1. **Redirect scholarship** to under-explored passages/texts.
2. **History of the discipline** — tell stories about how the field developed.
3. **Read an era by its skew** — whether a period leaned more Platonic or more Aristotelian says something about it.

A caveat carried throughout: raw citation *frequency* conflates the genuinely contested passage, the boilerplate-cited passage (the cave, the divided line, *Metaphysics* Γ on non-contradiction), and the translation crux. A blank region on the heatmap can mean "understudied" OR "settled" — though note David's own view: virtually no Plato/Aristotle passage is truly undebatable, so blankness is more likely a reception fact than an exegetical one. Still worth building in a **raw-vs-normalised toggle** and, ideally later, some notion of citation *type* rather than bare count. Flag this in any methodology writeup to pre-empt the obvious referee objection.

## The data question — this is what the whole project hinges on

**Constellate is dead** (sunset 1 July 2025). Do not plan around it. Its successor is **JSTOR Text Analysis Support** (formerly Data for Research).

### The confirmed path: JSTOR Text Analysis Support

Workflow:
1. Download JSTOR's full bibliographic metadata file as **JSONL** (free, personal JSTOR account).
2. Identify the item IDs for the journals/years wanted.
3. Submit a dataset request.

Key facts:
- Self-service tier: metadata + **n-grams** for up to 25,000 documents.
- N-grams survive — so the token-count route (does "Rep. 511d" appear, how often) is alive. Want **trigrams/4-grams/5-grams**, not unigrams, to preserve the abbreviation–number binding.
- Full-text / larger datasets go through a **review** (in-copyright material especially). Average **2–4 week** wait on the agreement; not all requests approved.
- Full-text extracts usable for text analysis but **not** for LLM training (irrelevant here, but noted).

### Decision: start with the confirmed JSTOR core only

Eight mainstream journals expected to be well-covered (long backfiles, established, DOI-rich):

- *Phronesis*
- *Ancient Philosophy*
- *Apeiron*
- *Classical Quarterly* (CQ)
- *Classical Philology*
- *Archiv für Geschichte der Philosophie* (AGPh)
- *History of Political Thought* (HPT)
- *Journal of the History of Ideas* (JHI)

This is a legitimate v1, not a toy. The specialist journals are v2 enrichment, not a precondition. Starting here avoids the classic failure mode of chasing corpus-completeness and never shipping.

### Verified reference table (founding, coverage, reviews)

Founding dates, publishers, and reviews policy confirmed by web search July 2026. "Years on JSTOR" is approximate and subject to a moving wall (~3–5 yrs); the JSONL grep gives exact per-journal item counts and supersedes these estimates.

| Journal | Founded | Publisher | ~Years on JSTOR | Reviews? | Notes |
|---|---|---|---|---|---|
| *Phronesis* | 1955 | Brill | 1955– (wall ~5 yr) | No (Book Notes only) | Freq. changed: semiannual 1955–71, 3×/yr 1972–97, quarterly 1998–. Early decades thinner. Brill title *also* on JSTOR. |
| *Apeiron* | 1966 | De Gruyter | ~1966–2007 | — | Split coverage: JSTOR ~vols 1–40; recent yrs on De Gruyter platform behind wall. De Gruyter title *also* on JSTOR. |
| *Ancient Philosophy* | 1980 | Mathesis / PDC | 1980– | **Yes** | Biannual (only 2 issues/yr) → fewer items/yr. |
| *Classical Quarterly* (CQ) | 1907 | Cambridge (for Classical Assoc.) | 1907– | Yes | Longest backfile; large journal. Classics, not phil-specialist → high volume, diluted ancient-phil signal. Item-count heavyweight. |
| *Classical Philology* (CP) | 1906 | Univ. Chicago Press | 1906– | Yes | Quarterly. Classics, not phil-specialist → same high-volume/mixed-relevance profile as CQ. Item-count heavyweight. |
| *Archiv f. Gesch. der Philosophie* (AGPh) | 1888 | De Gruyter | 1888– (gaps) | — | Oldest in set. Multilingual (Ger/Eng/Fr/It → abbrev-matching wrinkle). Publication gap from 1933 (suspended under NS govt). Covers *all* history of phil, ancient is a fraction. De Gruyter title *also* on JSTOR. |
| *History of Political Thought* (HPT) | 1980 | Imprint Academic | 1980– | — | Quarterly. Multidisciplinary; ancient is a subset (much medieval/early-modern/modern). |
| *Journal of the History of Ideas* (JHI) | 1940 | Univ. Penn Press | 1940– | Yes | Quarterly. Broadest — intellectual history all periods; ancient-phil a *small* fraction. Included for reception-history payoff. |

**Decision on reviews: keep them.** They cite passages too, so they're reception signal, not noise. But they're the swing factor on whether the core clears the 25k self-service cap.

**Item-count shape going in (settle precisely via the grep):** two long Classics journals (CQ 1907, CP 1906) dominate the item count *and* carry the most diluted ancient-phil signal — the budget gets eaten most by the least on-target titles. Three titles (Phronesis, Apeiron, AGPh) are Brill/De Gruyter-on-JSTOR with recent years behind the publisher wall, so "all years" isn't fully JSTOR-reachable for them anyway — which conveniently also trims item count. The specialist philosophy journals are pleasingly small. If the core tips over 25k, the clean fix is to **date-slice the Classics pair** while taking the specialist journals whole.

### The uncertain tiers (deferred, need verification — do NOT take on faith)

- **Brill / De Gruyter specialist journals** — *Polis* (Brill; the one genuinely on-target ancient-political-thought venue), *Rhizomata* (De Gruyter), *Elenchos*, *Méthexis*. My earlier claim that these publishers "run their own researcher-accessible TDM channels" is **unverified** — could be institution-gated, routed through Crossref TDM, or not offered as n-gram extraction at all. **Search this before planning around it.**
- Note the complication: *Phronesis* and *AGPh* are themselves Brill/De Gruyter journals that are *also* on JSTOR (moving wall), so the "JSTOR vs Brill/De Gruyter" split isn't clean.
- **Probably out of reach without more effort:** *Oxford Studies in Ancient Philosophy* (annual, OUP — may be in neither JSTOR's minable set nor a clean TDM channel, and it's one of the most important sources); *Elenchos*, *Méthexis* (small Italian venues).

### Ruled out: The General Index

Malamud / Public.Resource.Org, 2021. Free, open, non-consumptive n-grams (unigrams–5-grams) from ~107M articles, including paywalled ones. Attractive in principle (5-gram depth suits the abbreviation-binding problem; covers paywalled content). **Rejected because:**
- 5TB compressed → **~38TB unzipped**. David's current drives can't handle it; download could take days.
- Extraction is **SpaCy-based** and imperfect by the creators' own admission — may have garbled exactly the alphanumeric citation strings we need.
- **Science-first corpus** — unknown and doubtful whether specialist ancient-philosophy journals are even in it.
- No query portal; must roll your own against the whole thing.

Revisit only if a friendlier mirror / queryable layer / post-2021 refresh appears — worth a quick search someday, but not the path now.

### Other tools noted

- **Crossref** — citation *metadata* (DOIs, titles, years, reference lists), free API. Builds the journal×year skeleton. No body text.
- **OpenAlex** — richest free bibliographic layer; enumerate exactly which articles exist in a journal×year. No body text.
- **Europe PMC** — biomedical, **dropped**; doesn't fit this corpus (my earlier mention was a mistake).
- **HathiTrust Research Center** — funding ends end of 2026; don't build on it.

## The parser — design settled, build deferred until data is confirmed

### Format routing (free first-pass disambiguation)

- Stephanus/Plato: `\d{3}[a-e]`
- Bekker/Aristotle: `\d{3,4}[ab]\d*`

The number *format itself* tells you which corpus before you parse digits — so "Pol. 1252a" resolves to Aristotle's *Politics* (Bekker) not Plato's *Politicus* (Stephanus) automatically.

### The key asymmetry: Aristotle is easy, Plato is hard

- **Bekker numbers are globally unique** across the Aristotelian corpus (continuous pagination in the 1831 edition). A page→treatise lookup table resolves them cleanly. Caveat: pseudo-Aristotelian material, and fragments use Rose numbers (different system).
- **Stephanus numbers RESET per dialogue** (~36 times, once per dialogue in the 1578 edition). So a bare "511d" is NOT unique — which is why Plato is always cited "*Rep.* 511d", never "511d" alone: the dialogue name does load-bearing identification the number can't. Table is **dialogue-name → valid-range**, and the parser must carry the dialogue name from context.

Consequence for the token-count route: the reset means "Rep." and "511d" must stay bound, so **unigrams are useless for Plato**; need the multi-gram windows. Aristotle survives token-counting far better because the number self-identifies. **Plato and Aristotle are effectively two different-difficulty sub-projects; ship Aristotle first if Plato resists.**

### Resolution architecture (refines the old Messkataloge matching approach)

1. **Scope tracking** — carry last-named work as state; bare numbers inherit it; confidence decays with distance since last named work.
2. **Range constraint** — compute which works' ranges contain the number; consistency-check against scope; flag mismatches (the reset actually *helps* here — ranges are short and constraining, narrowing a bare number to 2–3 candidates).
3. **Abbreviation match** — score adjacent abbreviations against a hand-built synonym table; let the number's range membership disambiguate the abbreviation. Watch abbreviation chaos: *Republic* = Rep./R./Resp./Pol.(!); *Metaphysics* = Met./Metaph./book-letters; "Pol." ambiguous across *Politicus*/*Politics*/older-*Republic*.
4. **Confidence output + triage** — threshold (~0.9), auto-accept above, dump below into a manual-review queue with context window attached. Realistic auto-resolution 95%+, probably 97–98%.

**Critical bias note:** unlike Messkataloge (where a wrong match gave an eyeballable wrong translation), here a wrong dialogue resolution **silently corrupts the heatmap** — invisible downstream. So bias the threshold *conservative*; better to hand-review 5% than publish 2% silent contamination a specialist will spot and distrust the whole tool over.

### Also anticipate

- **PDF-to-text normalisation** would be the real time-sink IF working from typeset PDFs (ligatures, superscript line numbers, hyphenation, two-column layouts corrupt exactly the strings we key on). **The n-gram route sidesteps this** — another reason to prefer JSTOR n-grams over raw PDFs.
- Residual hard cases: bare-number stretches after a scope break; footnote/endnote citations far from the named work in the body; "ad loc."/"there" anaphora (unresolvable by regex).

## The visualiser — genuinely easy, ~a weekend or less

- Static site, fits the existing **GitHub Pages** setup (same deploy as dkretz.com). Data baked to JSON, all client-side, no backend, free to host.
- Dropdowns: dialogue/treatise × journal × decade, driving a heat strip along the Stephanus/Bekker axis.
- **D3** for a continuous/zoomable passage axis; **Observable Plot** or **Recharts** if faster-with-less-code is preferred.
- **Design problem to solve up front:** the passage axis is non-uniform (*Republic* = 294 Stephanus pages, *Euthyphro* = 16). A raw strip makes long works look busy purely by length. Ship a **citations-per-page normalisation toggle** alongside raw counts.
- Toggles compound: the passage-axis normalisation (per-page) is separate from the cross-journal normalisation (per-article) described under "Granularity, normalisation, and traceback" — the UI should let both operate. Cells can also carry **click-through to article/DOI** (terms permitting).

## Granularity, normalisation, and article traceback

### Year granularity is free

JSTOR n-grams are **per-article**, not pooled. Each n-gram binds to a document ID; each document's metadata (in the JSONL) carries its publication year. So the join is n-gram → article ID → metadata → year; you never date a passage directly, you date the *article*, which already knows its year. Aggregating up to decade is trivial. The per-article boundary that *loses* cross-passage structure (hence the co-citation limitation) is the same boundary that *preserves* per-article metadata — dating comes for free precisely because the data stays document-partitioned.

Two realities, neither an obstacle: (a) it's *publication* year, not composition year — journals lag, so don't over-read single-year spikes as real-time intellectual events; fine at decadal resolution. (b) Volume-year vs. issue-cover-date can differ by one; immaterial at this grain.

### Three normalisation views (offer as toggles)

Raw counts let a high-volume or citation-dense journal dominate as a publishing-habits artifact, not a reflection of interest. Offer three views, which answer different questions:

1. **Raw occurrence count** — how much ink (e.g. "511d appears 40× across the journal-year").
2. **Distinct-articles count** — how many separate pieces engaged it (e.g. "cited in 5 articles").
3. **Articles-normalised** — share of the journal's output that touched the passage. This is the one that makes *cross-journal* comparison mean what we want.

**Denominator caveat:** per-article normalisation needs the *total articles per journal-year* — a **separate data pull** (from OpenAlex or the JSTOR metadata enumeration), NOT derivable from the n-gram data itself. Cheap, but a distinct ingredient to remember. Add an **article-count-per-journal-per-year table** to the reference dependencies.

### Article traceback — turns the heatmap into a finding aid

Because each n-gram binds to a document ID, and the metadata record carries title, author, and usually a **DOI / stable JSTOR URL**, the tool can in principle link a heatmap cell *directly* to the article(s) — not just "cited in *Phronesis* 1985" but "cited in [Author, title, 1985] → link." That's categorically more useful: click a rare-passage hotspot, get the actual papers.

**Happy asymmetry:** traceback is least precise where it matters least and most precise where it matters most. A heavily-cited passage (the cave, *NE* II) in a journal-year maps to a dozen articles — coarse pointer, but you could find those anyway. A **rare passage** (the *Philebus* 30 desert-spot — the whole point of payoff (1)) likely maps to *one* article that year, so even a coarse "journal + year" pointer resolves to a single findable paper. The feature works best exactly for the under-explored passages we most care about.

**Terms flag (verify before building the click-through):** aggregate counts (the heatmap) are almost certainly fine under JSTOR's TDM agreement. But **publicly surfacing article-level JSTOR item IDs** may be a different permission — licensed for your analysis, not necessarily for public redistribution — even though the underlying facts (X cited Y in year Z) aren't copyrightable. Likely resolution: link to **DOIs** (public metadata via Crossref) rather than JSTOR internal IDs. **Read the dataset agreement on this point before building the finding-aid feature.** The aggregate heatmap is safe regardless.

## What the cheap route delivers vs. what needs the expensive route

- Token-count (n-gram) route delivers payoffs **(1), (2), (3)** — under-explored passages, disciplinary-development stories, era-skew — all just aggregate counts.
- **Co-citation / passage-clustering / network analysis** (which passages appear together in one article) needs **full text** — the reviewed, slower, permission-heavy JSTOR path. Only pursue if the network ambition justifies it.

## Reference dependencies to build

- **Bekker page→treatise table** — checkable against Bekker 1831.
- **Stephanus dialogue→range table** — checkable against Burnet's OCT.
- **Abbreviation synonym table** — hand-built.
- **~100-citation hand-labelled test set** from one *Phronesis* year — ground truth to measure real parser hit-rate against, rather than guessing.
- **Article-count-per-journal-per-year table** — the denominator for per-article normalisation. Separate pull (OpenAlex or JSTOR metadata enumeration), not derivable from n-gram data.

*(These were offered as a first concrete artifact; not yet built. Good first move once data feasibility is confirmed.)*

## NEXT ACTIONS (in order)

1. **Pull the JSTOR bibliographic metadata JSONL** and grep the eight core journal titles against it. Learn actual minable coverage. ~an afternoon. *This is the single move that turns the project from "cool idea" to "known-feasible."*
2. **Request a pilot:** one journal (suggest *Phronesis* — central, and Brill-published-but-JSTOR-carried, so it quietly tests that overlap), one decade of n-grams. Test whether **"Rep. 511d" survives JSTOR's n-gram tokenisation** in the 4-/5-gram windows. This is the single riskiest technical unknown — hit it early on real data, before building the parser.
3. Only after 1 & 2: decide whether to chase Brill/De Gruyter for the specialist journals, or ship the mainstream core as v1.
4. Build the range tables + test set, then the parser, then the visualiser — all downstream of "does the data survive tokenisation."

**Calendar shape:** an afternoon on the JSONL grep now → a **2–4 week review wait** (not continuous) → a couple of evenings of actual building once data lands. The gap is the JSTOR queue, not the project stalling.

## The floor

If Brill/De Gruyter falls through and only the mainstream core is reachable, the project doesn't die — it *is* the core. Nobody currently has a passage-level heatmap of what ancient-philosophy scholarship attends to. A grad student wondering "has anyone worked on *Philebus* 30-ish, or is it a desert?" has no tool for that today. v1 answers it for eight journals. Small enough to finish, novel enough to matter.
