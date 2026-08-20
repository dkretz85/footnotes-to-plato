#!/usr/bin/env python3
"""
survey_delivery.py — inspect the dataset JSTOR *delivered* (the gzipped JSONL
that came back from the Text Analysis Support request), as opposed to the
upstream bibliographic metadata the request was built from.

This does three jobs the earlier scripts (survey_jstor / build_request /
find_titles) do NOT:
  1. SCHEMA PROBE   — print the structure of the first few delivered records
                      so we can SEE JSTOR's actual delivery format instead of
                      guessing (top-level keys, n-gram containers, a sample).
  2. COVERAGE       — reconcile delivered IDs against request_item_ids.txt:
                      how many of the 69,178 arrived, which are missing,
                      and confirm the flagged drop (ab0e7253-…) is among them.
                      Surfaces any *other* silent drops beyond the flagged one.
  3. N-GRAM SANITY  — which gram levels are present (uni/bi/tri/4/5), and
                      whether citation-shaped tokens (Stephanus \\d{3}[a-e],
                      Bekker \\d{3,4}[ab]) survive tokenisation — the project's
                      single riskiest technical unknown.

Usage:
    python3 survey_delivery.py /path/to/jstor_delivery.jsonl.gz \\
            [--requested request_item_ids.txt] \\
            [--probe 3] [--max-records N]

Nothing is decompressed to disk; the file is streamed line by line.
The script assumes NOTHING about field names beyond a set of candidates and
reports whatever it actually finds. Run it once, read the PROBE section, and
if a field is misnamed we tighten the candidate lists and re-run.
"""

import sys, os, json, gzip, io, argparse, collections, re

# --- candidate field names (delivery schema varies; we detect what's there) --
ID_FIELDS      = ["id", "item_id", "docId", "doi", "file_name", "identifier"]
JOURNAL_FIELDS = ["isPartOf", "is_part_of", "journalTitle", "journal"]
YEAR_FIELDS    = ["publicationYear", "published_date", "year", "date"]
TYPE_FIELDS    = ["docSubType", "content_subtype", "docType", "content_type"]

# n-gram containers seen across JSTOR/Constellate-style deliveries.
# key = gram level, value = list of candidate JSON keys holding that dict/list.
NGRAM_FIELDS = {
    1: ["unigramCount", "unigrams", "unigram_count"],
    2: ["bigramCount",  "bigrams",  "bigram_count"],
    3: ["trigramCount", "trigrams", "trigram_count"],
    4: ["fourgramCount", "fourgrams", "4gramCount", "fourgram_count"],
    5: ["fivegramCount", "fivegrams", "5gramCount", "fivegram_count"],
}
FULLTEXT_FIELDS = ["fullText", "full_text", "text", "plainText"]

STEPHANUS = re.compile(r"\b\d{3}[a-e]\b")        # Plato, e.g. 511d
BEKKER    = re.compile(r"\b\d{3,4}[ab]\d*\b")     # Aristotle, e.g. 1252a

FLAGGED_MISSING = "ab0e7253-8739-3667-b98e-025ad9fd37f5"


def first_present(rec, fields):
    for f in fields:
        if f in rec and rec[f] not in (None, "", [], {}):
            return f, rec[f]
    return None, None


def year_of(val):
    for tok in str(val).replace("-", " ").split():
        if len(tok) == 4 and tok.isdigit():
            return tok
    return str(val)


def open_stream(path):
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")


def detect_ngram_keys(rec):
    """Return {level: actual_key_present_in_this_record}."""
    found = {}
    for level, cands in NGRAM_FIELDS.items():
        for c in cands:
            if c in rec:
                found[level] = c
                break
    return found


def iter_ngram_tokens(container):
    """Yield the n-gram *strings* from whatever shape the container is."""
    if isinstance(container, dict):
        yield from container.keys()
    elif isinstance(container, list):
        for el in container:
            if isinstance(el, str):
                yield el
            elif isinstance(el, dict):
                # e.g. {"ngram": "...", "count": N}
                for k in ("ngram", "gram", "term", "text"):
                    if k in el:
                        yield el[k]
                        break


def probe(path, n_probe):
    print("=" * 72)
    print(f"SCHEMA PROBE — first {n_probe} record(s)")
    print("=" * 72)
    shown = 0
    with open_stream(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception as e:
                print(f"  (record {shown+1} did not parse: {e})")
                shown += 1
                if shown >= n_probe:
                    break
                continue
            print(f"\n--- record {shown+1} -------------------------------------")
            print("top-level keys:")
            for k in sorted(rec.keys()):
                v = rec[k]
                t = type(v).__name__
                if isinstance(v, (dict, list)):
                    size = len(v)
                    print(f"   {k:24s} {t}(len={size})")
                else:
                    s = str(v)
                    s = s[:70] + "…" if len(s) > 70 else s
                    print(f"   {k:24s} {t}: {s}")
            idf, idv = first_present(rec, ID_FIELDS)
            jf, jv   = first_present(rec, JOURNAL_FIELDS)
            print(f"  -> id field  : {idf} = {idv}")
            print(f"  -> journal   : {jf} = {jv}")
            grams = detect_ngram_keys(rec)
            print(f"  -> n-gram keys detected: "
                  f"{ {lvl: grams[lvl] for lvl in sorted(grams)} }")
            # show a few citation-shaped n-grams if any trigram+ container exists
            for lvl in (3, 4, 5, 2, 1):
                if lvl in grams:
                    toks = list(iter_ngram_tokens(rec[grams[lvl]]))
                    cited = [t for t in toks
                             if STEPHANUS.search(t) or BEKKER.search(t)]
                    if cited:
                        print(f"  -> sample {lvl}-grams w/ citation shape "
                              f"({len(cited)} found): {cited[:5]}")
                        break
            shown += 1
            if shown >= n_probe:
                break
    print()


def survey(path, requested_path, max_records):
    requested = set()
    if requested_path and os.path.exists(requested_path):
        with open(requested_path) as fh:
            requested = {ln.strip() for ln in fh if ln.strip()}
        print(f"Loaded {len(requested):,} requested IDs from {requested_path}")
    else:
        print("(!) No requested-ID file found; skipping coverage reconciliation.")

    delivered_ids   = set()
    per_journal     = collections.Counter()
    per_jy          = collections.Counter()          # (journal, year)
    gram_presence   = collections.Counter()          # level -> #records having it
    cite_bearing    = collections.Counter()          # level -> #records w/ a citation-shaped gram
    has_fulltext    = 0
    id_field_seen   = collections.Counter()
    gram_field_seen = collections.Counter()
    total = bad = 0

    with open_stream(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            total += 1
            if max_records and total > max_records:
                total -= 1
                break
            try:
                rec = json.loads(line)
            except Exception:
                bad += 1
                continue

            idf, idv = first_present(rec, ID_FIELDS)
            if idf:
                id_field_seen[idf] += 1
            if idv:
                delivered_ids.add(str(idv))

            _, jv = first_present(rec, JOURNAL_FIELDS)
            journal = str(jv) if jv else "?"
            per_journal[journal] += 1
            _, yv = first_present(rec, YEAR_FIELDS)
            per_jy[(journal, year_of(yv) if yv else "?")] += 1

            grams = detect_ngram_keys(rec)
            for lvl, key in grams.items():
                gram_presence[lvl] += 1
                gram_field_seen[f"{lvl}:{key}"] += 1
                # cheap citation-shape check on tri+ grams only (perf)
                if lvl >= 2:
                    for t in iter_ngram_tokens(rec[key]):
                        if STEPHANUS.search(t) or BEKKER.search(t):
                            cite_bearing[lvl] += 1
                            break

            ftf, _ = first_present(rec, FULLTEXT_FIELDS)
            if ftf:
                has_fulltext += 1

    # ---------------- report ----------------
    print("=" * 72)
    print(f"Records read: {total:,}   unparseable: {bad:,}")
    print(f"ID fields seen: {dict(id_field_seen)}")
    print(f"Full-text present in {has_fulltext:,} records "
          f"({'FULL-TEXT delivery' if has_fulltext else 'n-gram-only delivery'})")

    print("\n" + "=" * 72)
    print("N-GRAM LEVELS PRESENT  (records carrying each level)")
    print("  cite-shaped = at least one gram matching Stephanus/Bekker form")
    print("=" * 72)
    if not gram_presence:
        print("  (!) No n-gram containers detected. Check NGRAM_FIELDS against")
        print("      the PROBE output above — the delivery names them differently.")
    for lvl in sorted(gram_presence):
        cb = cite_bearing.get(lvl, 0)
        print(f"  {lvl}-gram: {gram_presence[lvl]:7,d} records   "
              f"cite-shaped in {cb:,}")
    print(f"  (container keys actually used: {dict(gram_field_seen)})")

    if requested:
        print("\n" + "=" * 72)
        print("COVERAGE — delivered vs requested")
        print("=" * 72)
        inter   = delivered_ids & requested
        missing = requested - delivered_ids
        extra   = delivered_ids - requested
        print(f"  requested : {len(requested):,}")
        print(f"  delivered : {len(delivered_ids):,}")
        print(f"  matched   : {len(inter):,}")
        print(f"  MISSING   : {len(missing):,}  (requested but not delivered)")
        print(f"  extra     : {len(extra):,}  (delivered but not requested)")
        flagged_in = FLAGGED_MISSING in missing
        print(f"\n  flagged drop {FLAGGED_MISSING}")
        print(f"     -> {'CONFIRMED missing' if flagged_in else 'present in delivery (unexpected!)'}")
        others = sorted(missing - {FLAGGED_MISSING})
        if others:
            print(f"  (!) {len(others)} OTHER silent drop(s) beyond the flagged one:")
            for m in others[:20]:
                print(f"        {m}")
            if len(others) > 20:
                print(f"        … and {len(others)-20} more")
        else:
            print("  No silent drops: the flagged item is the only one missing.")

    print("\n" + "=" * 72)
    print("DELIVERED DOCUMENTS PER JOURNAL")
    print("=" * 72)
    for j, n in per_journal.most_common():
        print(f"  {n:7,d}  {j}")

    # write a per-journal/year TSV for the record
    with open("delivery_counts.tsv", "w", encoding="utf-8") as out:
        out.write("journal\tyear\tcount\n")
        for (j, y), n in sorted(per_jy.items()):
            out.write(f"{j}\t{y}\t{n}\n")
    print("\nWrote delivery_counts.tsv (journal/year/count of delivered docs)")

    # write the missing-ID list if any
    if requested:
        miss = sorted(requested - delivered_ids)
        with open("delivery_missing_ids.txt", "w", encoding="utf-8") as out:
            for m in miss:
                out.write(m + "\n")
        print(f"Wrote delivery_missing_ids.txt ({len(miss)} IDs)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--requested", default="request_item_ids.txt")
    ap.add_argument("--probe", type=int, default=3)
    ap.add_argument("--max-records", type=int, default=0,
                    help="stop after N records (0 = all); useful for a fast first look")
    args = ap.parse_args()

    if args.probe:
        probe(args.path, args.probe)
    survey(args.path, args.requested, args.max_records)


if __name__ == "__main__":
    main()
