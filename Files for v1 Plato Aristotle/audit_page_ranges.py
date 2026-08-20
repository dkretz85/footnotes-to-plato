#!/usr/bin/env python3
"""
audit_page_ranges.py — find citations whose parsed page falls OUTSIDE the
work's known Stephanus/Bekker span. These are candidates for mis-parsed
`match` strings (line numbers, fragment refs, 'p. 60' bleed, OCR noise).

Usage: python3 audit_page_ranges.py resolved.tsv

Prints, per work, how many citations land outside range and a sample of the
offending match strings + context, so you can see what they really are.
"""
import sys, csv, re, collections
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# Known page spans (Stephanus for Plato, Bekker for Aristotle). Generous bounds;
# we only care about clear out-of-range hits, not off-by-one at edges.
SPAN = {
    "Republic": (327, 621), "Laws": (624, 969), "Timaeus": (17, 92),
    "Phaedo": (57, 118), "Phaedrus": (227, 279), "Gorgias": (447, 527),
    "Meno": (70, 100), "Apology": (17, 42), "Crito": (43, 54),
    "Parmenides": (126, 166), "Philebus": (11, 67), "Epinomis": (973, 992),
    "Symposium": (172, 223), "Theaetetus": (142, 210), "Sophist": (216, 268),
    "Statesman": (257, 311), "Protagoras": (309, 362), "Charmides": (153, 176),
    "Laches": (178, 201), "Lysis": (203, 223), "Euthyphro": (2, 16),
    "Euthydemus": (271, 307), "Cratylus": (383, 440), "Menexenus": (234, 249),
    "Ion": (530, 542), "Hippias_Major": (281, 304), "Hippias_Minor": (363, 376),
    "Alcibiades_1": (103, 135), "Alcibiades_2": (138, 151), "Clitophon": (406, 410),
    "Critias": (106, 121), "Letters": (309, 363), "Hipparchus": (225, 232),
    # Aristotle (Bekker)
    "Metaphysics": (980, 1093), "Nicomachean_Ethics": (1094, 1181),
    "Eudemian_Ethics": (1214, 1249), "Politics": (1252, 1342),
    "Physics": (184, 267), "De_Anima": (402, 435), "De_Caelo": (268, 313),
    "Rhetoric": (1354, 1420), "Poetics": (1447, 1462), "Topics": (100, 164),
    "Prior_Analytics": (24, 70), "Posterior_Analytics": (71, 100),
    "Categories": (1, 15), "De_Interpretatione": (16, 24),
    "Sophistical_Refutations": (164, 184), "Meteorology": (338, 390),
    "Historia_Animalium": (486, 638), "De_Partibus_Animalium": (639, 697),
    "De_Generatione_Animalium": (715, 789), "De_Sensu": (436, 449),
    "De_Memoria": (449, 453), "De_Somno": (453, 458), "De_Insomniis": (458, 462),
    "De_Juventute": (467, 470), "De_Motu_Animalium": (698, 704),
    "De_Generatione_et_Corruptione": (314, 338), "Magna_Moralia": (1181, 1213),
}

WORK, MATCH, CONTEXT = "work_id", "match", "context"

def page_of(m):
    mm = re.match(r"\s*(\d{1,4})", m or "")
    return int(mm.group(1)) if mm else None

out_of_range = collections.defaultdict(list)
totals = collections.Counter()

with open(sys.argv[1] if len(sys.argv)>1 else "resolved.tsv", encoding="utf-8") as fh:
    for row in csv.DictReader(fh, delimiter="\t"):
        w = row.get(WORK); m = row.get(MATCH,"")
        if w not in SPAN: continue
        totals[w] += 1
        p = page_of(m)
        lo, hi = SPAN[w]
        if p is None or p < lo or p > hi:
            out_of_range[w].append((m, (row.get(CONTEXT,"") or "")[:70]))

print(f"{'work':26s} {'total':>6s} {'out':>5s} {'%':>5s}")
print("-"*46)
flagged = sorted(out_of_range.items(), key=lambda kv: -len(kv[1]))
for w, hits in flagged:
    print(f"{w:26s} {totals[w]:6d} {len(hits):5d} {100*len(hits)/totals[w]:4.1f}%")

print("\nSample offending matches (match | context):")
for w, hits in flagged[:12]:
    print(f"\n[{w}]  span {SPAN[w]}")
    seen = collections.Counter(h[0] for h in hits)
    for match_str, n in seen.most_common(8):
        ctx = next(c for m,c in hits if m==match_str)
        print(f"   {n:4d}x  {match_str!r:12s}  {ctx!r}")

grand = sum(len(h) for h in out_of_range.values())
print(f"\nTotal out-of-range citations: {grand:,} "
      f"({100*grand/sum(totals.values()):.2f}% of ranged works)")
