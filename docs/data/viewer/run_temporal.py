#!/usr/bin/env python3
"""Drive temporal_analysis.py across the whole corpus to produce every
temporal_*.json Viewer C needs, at the right grain and journal set for each work.

Viewer C reads, per (work, grain, journal-set): a whole-work verdict, the
per-unit decade trajectories, the movers, and the multi-period structure — all
emitted by temporal_analysis.py. Only a handful of hero works had been run; this
regenerates the full set with one consistent (post-audit) schema.

GRAIN POLICY (from TEMPORAL_FINDINGS_POST_AUDIT §3-§6 — grain is not free):
  * Plato / Aristotle, non-faceted ....... passage
  * Plato / Aristotle, faceted ........... passage AND book
        (Republic, Laws, Metaphysics, Nicomachean Ethics, Eudemian Ethics)
  * Homer (Iliad, Odyssey) ............... book        (line grain is hopeless)
  * Paul  (nt) .......................... book        (verse grain is hopeless)
  * Pindar .............................. pooled ode grain, via --pool
        (each ode a level-1 text; the four ode-books are level-0 clusters, so
         they are pooled into one Pindar corpus, never run as four "works")

JOURNAL SETS: all journals, then each group in journal_groups.json
(philosophy / classics / theology). A set a work has no citations in is skipped
by temporal_analysis.py automatically (it writes no file for it).

This shells out to temporal_analysis.py so the vetted CLI — including the Pindar
--pool within-shelf control — is reused exactly. It reads journal_groups.json,
so run build_journal_groups.py FIRST if you want the theology set populated.

Run:  python3 run_temporal.py                       # full corpus, all sets, perm=200
      python3 run_temporal.py --skip-existing        # only make what's missing
      python3 run_temporal.py --works Republic Timaeus
      python3 run_temporal.py --sets all philosophy   # limit journal sets
      python3 run_temporal.py --perm 2000 --works De_Anima   # re-run a marginal at high perm
      python3 run_temporal.py --dry-run               # print the commands, run nothing
"""
import argparse, json, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
VIEWER = os.path.join(ROOT, "viewer_data")
INDEX = os.path.join(VIEWER, "works_index.json")
ANALYSIS = os.path.join(ROOT, "temporal_analysis.py")
GROUPS = os.path.join(ROOT, "journal_groups.json")

# author resolution shared with build_authors.py (imported so the two never drift)
sys.path.insert(0, ROOT)
try:
    from build_authors import author_of  # noqa: E402
except Exception as e:                    # pragma: no cover
    sys.exit(f"error: could not import author_of from build_authors.py: {e}")

FACETED_AUTHORS = {"Homer", "Pindar", "Plato", "Aristotle", "Paul"}
PINDAR_SHELVES = ["Olympian", "Pythian", "Nemean", "Isthmian"]


def safe_name(w):
    return w.replace(" ", "_").replace("/", "_")


def grains_for(rec, author):
    """Which grains to run for a work (Pindar is handled separately, via the pool)."""
    if author == "Homer":
        return ["book"]         # Iliad/Odyssey book; line grain is temporally hopeless
    if author == "Paul":
        return ["book"]         # chapter; verse grain is hopeless
    if rec.get("faceted"):
        return ["passage", "book"]
    return ["passage"]


def outfile(work, jlabel, grain):
    suffix = ("_" + safe_name(jlabel)) if jlabel else ""
    suffix += "_book" if grain == "book" else ""
    return os.path.join(ROOT, f"temporal_{safe_name(work)}{suffix}.json")


def run(cmd, dry):
    print("    $ " + " ".join(cmd))
    if dry:
        return True
    r = subprocess.run(cmd, cwd=ROOT)
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--works", nargs="*", help="limit to these works_index names")
    ap.add_argument("--authors", nargs="*", help="limit to these authors")
    ap.add_argument("--sets", nargs="*",
                    help="journal sets to run (default: all + every group). "
                         "Use 'all' for the all-journals run; group keys otherwise.")
    ap.add_argument("--grains", nargs="*", choices=["passage", "book"],
                    help="limit to these grains (overrides the per-work policy)")
    ap.add_argument("--perm", type=int, default=200, help="permutation iterations (default 200)")
    ap.add_argument("--bin", type=int, default=5, help="year bin size (default 5)")
    ap.add_argument("--skip-existing", action="store_true",
                    help="skip a run whose output file already exists")
    ap.add_argument("--dry-run", action="store_true", help="print commands, run nothing")
    args = ap.parse_args()

    if not os.path.exists(INDEX):
        sys.exit(f"error: {INDEX} not found — run build_viewer_data.py first")
    if not os.path.exists(ANALYSIS):
        sys.exit(f"error: {ANALYSIS} not found")
    works = json.load(open(INDEX, encoding="utf-8"))

    # journal sets = all, then the groups present in journal_groups.json
    group_keys = []
    if os.path.exists(GROUPS):
        try:
            group_keys = list(json.load(open(GROUPS, encoding="utf-8"))["groups"].keys())
        except Exception as e:
            print(f"  warning: could not read {GROUPS}: {e}", file=sys.stderr)
    else:
        print("  warning: journal_groups.json missing — running all-journals only "
              "(run build_journal_groups.py first for per-field sets)", file=sys.stderr)
    # ("" is the all-journals run; temporal_analysis takes an empty --journals)
    all_sets = [""] + group_keys
    if args.sets:
        want = {("" if s == "all" else s) for s in args.sets}
        all_sets = [s for s in all_sets if s in want]

    py = sys.executable or "python3"
    planned = skipped = ran = failed = 0
    t0 = time.time()

    # ---- per-work runs (everyone except Pindar's four shelves) ----
    for rec in works:
        work = rec["work"]
        author = author_of(rec)
        if author == "Pindar":
            continue    # pooled below
        if args.works and work not in args.works:
            continue
        if args.authors and author not in args.authors:
            continue
        grains = grains_for(rec, author)
        if args.grains:
            grains = [g for g in grains if g in args.grains]
        if not grains:
            continue
        print(f"\n== {work}  ({author})  grains={grains} ==")
        for grain in grains:
            for jset in all_sets:
                out = outfile(work, jset, grain)
                planned += 1
                if args.skip_existing and os.path.exists(out):
                    print(f"    skip (exists): {os.path.basename(out)}")
                    skipped += 1
                    continue
                cmd = [py, ANALYSIS, VIEWER, work, "--bin", str(args.bin),
                       "--perm", str(args.perm), "--grain", grain]
                if jset:
                    cmd += ["--journals", jset]
                ok = run(cmd, args.dry_run)
                ran += 1
                if not ok:
                    failed += 1

    # ---- Pindar: pool the four ode-books into one corpus, ode = the unit ----
    do_pindar = (not args.authors or "Pindar" in args.authors) \
        and (not args.works or any(s in (args.works or []) for s in PINDAR_SHELVES + ["Pindar"])) \
        and (not args.grains or "book" in args.grains)
    if do_pindar:
        print(f"\n== Pindar  (pooled odes)  grain=book ==")
        for jset in all_sets:
            out = outfile("Pindar", jset, "book")
            planned += 1
            if args.skip_existing and os.path.exists(out):
                print(f"    skip (exists): {os.path.basename(out)}")
                skipped += 1
                continue
            cmd = [py, ANALYSIS, VIEWER] + PINDAR_SHELVES + \
                  ["--pool", "Pindar", "--bin", str(args.bin), "--perm", str(args.perm)]
            if jset:
                cmd += ["--journals", jset]
            ok = run(cmd, args.dry_run)
            ran += 1
            if not ok:
                failed += 1

    dt = time.time() - t0
    print(f"\n{'DRY RUN — ' if args.dry_run else ''}planned {planned} run(s): "
          f"{ran} executed, {skipped} skipped, {failed} failed  ({dt:.0f}s)")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
