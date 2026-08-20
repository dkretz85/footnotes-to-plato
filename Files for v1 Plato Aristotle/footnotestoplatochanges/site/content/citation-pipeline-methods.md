# Pipeline & methods record

This document sets out how *Footnotes to Plato* is built: how citations are
extracted from the journal full text, how they are resolved to particular works
and passages, what is filtered out and why, and — most important for anyone
reading the charts — what the resulting numbers can and cannot be made to say.
It is the long companion to the [short methods page](/methods/). Every figure
here can be checked against the [published derived data](/data/).

The pipeline is **precision-first** throughout. At each stage the default is to
decline rather than guess: a citation that cannot be placed beyond reasonable
doubt is set aside in a review queue, not forced to a best guess, and every
exclusion is diverted to an auditable file rather than deleted. The headline
placement figure — **{{placed_total}} of roughly 141,000 detected citations
(64%)** — is therefore a trustworthy floor, not a rate reached by relaxing
correctness.

## The source corpus

The underlying data is a full-text delivery from JSTOR Text Analysis Support:
**{{n_articles}} articles** across ten journals of ancient philosophy and classics,
one record per article, each carrying the article's text as a list of page
strings. Because the text arrives page by page, every citation's page-level
position within its article is known without further work, and citation strings
appear verbatim in the text (`PLAT. MEN. 80D5-E5`), so there is no tokenisation
to corrupt them.

Article-level metadata — journal, year, document type, and title — is not part of
the text delivery; it is joined from JSTOR's separate catalogue by article ID.
The delivery matches the request exactly but for a single item JSTOR flagged as
un-includable (0.001% of the corpus, immaterial to any aggregate). No other
items are dropped silently; the reconciliation is re-run on every pass.

The raw `references` field — secondary-literature citations (Diels–Kranz, modern
editions) rather than the primary-passage references this project counts — is
reserved for a possible future co-citation study and is not used here.

## Extracting citation candidates

### Two pagination systems, and where they collide

Ancient citations use two numbering systems whose surface forms overlap:

- **Bekker** (Aristotle): a page number followed by a column letter `a` or `b`,
  optionally a line — `1252a`, `980b25`. Pages run to about 1462.
- **Stephanus** (Plato): a page number followed by a section letter `a`–`e`,
  optionally a line — `511d`, `80d5`. Pages run to about 621.

The section letter partly disambiguates, so each extracted match is tagged one of
three ways: **Bekker** (a four-digit page with `a`/`b`, unambiguously Aristotle),
**Stephanus** (a two- or three-digit page with `c`–`e`, unambiguously Plato,
since Bekker uses only `a`/`b`), or **ambiguous** (a two- or three-digit page with
`a`/`b`, which could belong to either system). Roughly 62% of matches are
ambiguous — expected, since most Aristotle citations end in `a` or `b` — and are
deferred to the resolver rather than assigned by a guess about the system.

The extractor errs toward **over-capture**: an early version required three
leading digits and so silently dropped every sub-100 Stephanus citation (`80d5`,
*Meno*), which is unrecoverable, whereas over-captured noise can be filtered
downstream against context. Each match also carries a short context window and
reading-order fields (page index, character offset, a per-article sequence
counter) that later stages use to track which work is under discussion.

## Resolving candidates to works

Each surviving candidate is matched against reference tables of work boundaries
and resolved through an ordered architecture, in descending order of authority:

1. **Unique range.** If exactly one work contains the cited page, accept it. A
   work merely *named* elsewhere in the context does not override a unique range —
   Aristotle discussing Plato's *Republic* does not turn a unique Bekker page into
   a *Republic* citation.
2. **Range plus name.** If several works contain the page but the surrounding
   text names exactly one of them, accept that one.
3. **Cross-system resolution.** If an ambiguous number's candidates span both
   Bekker and Stephanus, accept only when an adjacent name collapses the full
   cross-system set to one work.
4. **Scope inheritance.** A bare number inherits the last-named work in reading
   order, with confidence decaying by distance, and is accepted only if the page
   falls inside that work's range.
5. **Title prior.** A bare, in-range number in an article *titled* after a work
   resolves to that work — short dialogues are often cited bare precisely because
   the whole article is about them. This ranks below an adjacent name and local
   scope and above giving up: an article titled "Plato's *Meno*" resolves a bare
   in-range `72a` to *Meno*, but a nearby "*Rep.*" still wins, and an out-of-range
   number is never forced.
6. **Otherwise**, the candidate goes to the review queue, tagged with the specific
   ambiguity and the competing works.

The distinction in step 1 — between a work that is *cited* and a work that is
merely *mentioned* — is the single most consequential piece of the resolver: a
globally unique Bekker page is authoritative regardless of what else is named
nearby, and treating it so recovers many thousands of citations that a naive
name-proximity rule would wrongly defer.

## What is filtered out

Non-citation content is removed before resolution, and every excluded row is kept
with its reason so the decision is auditable and reversible. The filters, each set
by inspecting real false positives rather than by assumption:

| Reason | Count | What it catches |
|---|---|---|
| Non-content document types | 54,409 | back-of-volume indices and non-scholarly back-matter |
| Modern year | 4,762 | numbers ≥ 1463, above Bekker's ceiling — can only be a publication year |
| Book.section reference | 4,227 | `12.25e`-type refs to another author (e.g. Polybius) |
| Foreign text | 1,070 | an adjacent marker names a non-Plato/Aristotle work (`Aj. 134a`) |
| Diels–Kranz fragment | 190 | a Presocratic fragment number, not a passage citation |

### The document-type decision

The largest single exclusion — non-content document types — is also the most
consequential methodological call, and it was made on evidence. The `misc`
document type made up a quarter of all raw candidates, too large to keep or drop
blindly. A dedicated probe found it to be overwhelmingly **back-of-volume subject
indices** ("*Rep.* 344e: 213" meaning *discussed on page 213*), 94% of it from a
single journal's old annual indices and 83% of it pre-1910 — locators, not
scholarly citations. Book reviews, by contrast, are 89% substantive prose across
all decades, and are kept. Excluding by document type removed the index
contamination cleanly, and did so where an earlier density-based heuristic could
not: real dense footnote pages and index pages score almost identically on
numeric density, and the discriminating signal turned out to be the document type,
not anything in the text itself.

## Reference tables

- **Stephanus ranges** — 36 dialogues, independently verified, with per-book
  sub-ranges for the *Republic* and *Laws*.
- **Bekker ranges** — Aristotle treatise page ranges. The tightly-packed
  *Parva Naturalia* required exact `(page, column, line)` boundaries, taken from
  Ross's *Works of Aristotle* (Oxford, 1931), so that treatises sharing a page can
  be told apart by column and line (`449a34` → *De Sensu*, `449b3` → *De Memoria*).
  These twelve short treatises had previously resolved at literally zero, from a
  double cause: shared pages, and no name variants at all in the abbreviation
  table. Both were fixed, and the treatises moved from 0% to 40–90%.
- **Abbreviation and synonym table** — multilingual work-name variants
  (English, Latin, French, German, Italian), with shared or ambiguous forms
  explicitly flagged "do not resolve on the abbreviation alone." Variants for the
  twelve *Parva Naturalia* treatises were added during this build and are marked
  unverified (standard scholarly forms, not yet concordance-checked).

Bekker treatise boundaries **outside** the *Parva Naturalia* remain unverified at
their exact edges; this is the largest outstanding table-quality item, and its
impact is confined to citations landing precisely on a shared page.

## Book-level faceting

The four highest-volume works — *Republic*, *Laws*, *Metaphysics*, *Nicomachean
Ethics* — are large enough that a single passage axis is unreadable, so the
interface facets them by book. Book is derived at load time from the citation's
locus rather than baked into the raw rows, which keeps book assignment an
auditable, swappable layer. Book-opening loci were looked up against Burnet
(Stephanus) and Bekker and inlined as exact split points, mid-page openings
included (*Metaphysics* little-alpha begins at 993a30; *NE* II at 1103a15). All
35,968 citations in the four faceted works are assigned, none unassigned.

Two details of scholarly interest fall out of this. *Metaphysics* is labelled by
Greek book letter (Α, α, Β, Γ…), matching how it is cited, with the little-alpha
= Book II offset handled explicitly. And the *NE*/*EE* common books — *NE* V–VII,
which are textually *EE* IV–VI, transmitted once but cited under either name —
are marked so the interface can fold them by default and offer a split view that
shows the *NE*-versus-*EE* labelling, itself a datum of reception history; about
2,200 citations fall in these shared books.

## Reading the results

A placement figure is a measure of **coverage, not accuracy**. "*Phaedrus* 61%"
means 61% of candidate *Phaedrus* citations were confidently placed; the rest are
unplaced, not misplaced. The placed set is clean but incomplete, and the
incompleteness is not spread evenly. Two structurally different kinds of
uncertainty follow, and the interface keeps them visually distinct.

### Floors, and the shared fade

Every count on the site is a **floor** — what was confidently placed. Above each
work's floor sits a **fade**: the ambiguous citations whose candidate set
*includes* that work. This fade is deliberately **multi-counted**. A bare `80b`
whose candidates are *Meno*, *Apology*, and others is counted in the fade of each,
because any one of them could be its true home. That makes the fade an honest
per-work upper gesture — "attention here could be this much more" — but a quantity
that **must not be summed** across works, and one that is independent of any
arbitrary filing rule.

This is why the site publishes **no per-work resolution rate and no reliability
tiers**. A rate would need to charge each ambiguous citation to a single work, and
there is no neutral way to do that. An earlier version filed each queued citation
under the alphabetically-first of its candidate works; the resulting rate tracked
alphabetical position as much as resolvability — *Timaeus*, sorting late, was
charged for almost none of the roughly fourteen thousand ambiguous citations it
shares and so appeared 98% resolved, while *Apology*, sorting early, appeared 26%,
though a symmetric split places both near the middle. Seventeen of sixty-eight
works cross an 80% line depending only on which filing rule is chosen. The floor,
by contrast, is filing-independent, and it is what the site reports.

### Cross-work versus within-work uncertainty

The two kinds of uncertainty fall on genuinely different sets of works:

- **Cross-work uncertainty** is about *how much a work is studied in total*. The
  low-placement short dialogues — *Apology*, *Meno*, *Crito*, *Lysis*,
  *Charmides*, *Categories* — are cited bare across their whole span ("as Socrates
  argues in the *Meno*"), so their missingness is spread evenly and no single
  stretch stands out. These works have wide floor-to-fade gaps and are the works
  most understated by a raw floor comparison. Their uncertainty lives in the
  **fade**, not in passage-level shading.
- **Within-work uncertainty** is about *which passages of a work are
  under-counted*. The works that carry it are mostly well-placed overall — *Laws*,
  *Republic*, *Parmenides*, *Philebus*, *Phaedo* — but have sharp local drops
  where a stretch of their pages collides with another work's range.

A natural prediction is that the low-placement short dialogues would be the ones
with localised collision damage; the data refutes it, and the refutation is the
design rationale. Shading a uniformly-hard dialogue's whole span would misdescribe
it (it is thin everywhere, not locally collided), and leaving *Laws* IX–XII
unshaded would misdescribe *that* (real local holes in an otherwise reliable text).
So the interface carries both treatments and keeps them apart: the fade at the
work level, and named band shading within a work.

### Collision bands

The within-work damage is captured as a set of **collision bands** — page ranges
where placement drops well below the work's own average, detected on a fixed bin
width with a volume guard and published in `collision_bands.json`. The exhaustive
set is **21 bands across 12 works**. The rest of the corpus is clean: **47 of 59
measured works flag no band at all**, so their within-work shape can be read end
to end. Among the flagged works, the *Laws* is the extreme case, with seven
contiguous bands across Books IX–XII (Stephanus 860–959) totalling an estimated
348 unplaced citations — under a tenth of its placed total, spread thin;
*Phaedo* 60–69 is the single highest-impact band; *Phaedrus* 250–269 sits, as
expected, in a cross-system collision zone. Absence of a band means no
band-level pattern above threshold, not a proof of completeness.

### Page-range integrity

To confirm that no mis-parsed page numbers were inflating any band, every placed
citation was checked against its work's known Stephanus or Bekker span. **Three of
90,502 citations (0.003%)** fell outside their work's range, all three in *De
Juventute* and all three attributable to a neighbouring treatise's page bleeding
in from the tightly-packed *Parva Naturalia* cluster. There is no systematic
page-parse leakage anywhere in the corpus.

## Method discipline

Three principles account for the data quality and are worth stating plainly:

1. **Look before filtering.** Every exclusion and threshold was set by inspecting
   real samples, random and targeted, not by assumption. Several plausible filters
   — numeric density for index pages, aggressive citation-count cutoffs — were
   rejected after measurement showed they would remove genuine data.
2. **Precision over recall; decline over guess.** Ambiguous cases are deferred to
   the queue, never force-resolved. The 64% is a trustworthy floor, not a ceiling
   reached by relaxing correctness.
3. **Divert, don't delete.** Every excluded row is kept with a reason, so every
   decision is auditable and reversible, and useful by-products (the Diels–Kranz
   fragments) are preserved for reuse.

## Known limitations

- **Bekker treatise boundaries outside the *Parva Naturalia* are unverified** at
  their exact edges — the largest remaining table-quality item. Impact is confined
  to citations landing on shared pages. The internal book divisions of the four
  faceted works are verified against Burnet and Bekker and are not part of this
  caveat.
- **Added abbreviation variants are unverified** — standard forms, not yet
  cross-checked against a concordance.
- **The 21 collision bands** need cell-level shading in any within-work
  visualisation; the band set is a responsible floor, not a completeness proof.
- **The review queue (~47,000 citations)** is genuine ambiguity — bare numbers
  with no name, scope, or title signal. A richer future model or a manual pass
  could recover some; it should not be force-resolved by heuristic.
- **Spuria** (*Alcibiades II*, *Hipparchus*, *Clitophon*, and others) resolve
  poorly and are marginal to most attention narratives; treat them separately.
- **The secondary-literature `references` field is unused**, reserved for a
  possible future co-citation analysis.

The [derived data is published](/data/) under CC BY 4.0 and the pipeline is open
source. Corrections are welcome and will be recorded and credited.
