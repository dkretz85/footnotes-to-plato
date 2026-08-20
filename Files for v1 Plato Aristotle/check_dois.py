#!/usr/bin/env python3
"""
check_dois.py — does the JSTOR delivery file carry DOIs?

Default target is David's file:
    /Users/davidkretz/Downloads/jstor_metadata_2026-07-18.jsonl.gz

Usage:
    python3 check_dois.py                       # uses the default path above
    python3 check_dois.py /some/other/file.jsonl
    python3 check_dois.py --sample 5000         # inspect more records

Works on .gz or plain; JSONL (one object per line) or a single JSON array.
Reports: which keys look DOI-ish, how often they're populated, and any
10.xxxx/... DOI pattern found anywhere in the record (even nested).
Only reads a sample, so it won't churn through the whole file.
"""
import sys, gzip, json, re, argparse
from collections import Counter

DEFAULT_PATH = "/Users/davidkretz/Downloads/jstor_metadata_2026-07-18.jsonl.gz"

DOI_RE = re.compile(r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+')
DOI_KEY_HINTS = ('doi', 'identifier', 'ark', 'article-id', 'articleid')

def open_maybe_gz(path):
    with open(path, 'rb') as fh:
        magic = fh.read(2)
    if magic == b'\x1f\x8b':
        return gzip.open(path, 'rt', encoding='utf-8', errors='replace')
    return open(path, 'rt', encoding='utf-8', errors='replace')

def iter_records(path):
    """Yield dict records whether the file is JSONL or one big JSON array."""
    f = open_maybe_gz(path)
    first = f.read(1)
    while first and first.isspace():
        first = f.read(1)
    if first == '[':                       # whole file is a JSON array
        rest = first + f.read()
        f.close()
        for rec in json.loads(rest):
            yield rec
        return
    f.close()
    # otherwise treat as JSONL (one JSON object per line)
    f = open_maybe_gz(path)
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue
    f.close()

def walk_keys(obj, prefix=''):
    """Recurse into nested dicts/lists, yielding (dotted_key, value) for scalars."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_keys(v, f'{prefix}{k}.')
    elif isinstance(obj, list):
        for item in obj:
            yield from walk_keys(item, prefix)
    else:
        yield prefix.rstrip('.'), obj

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path', nargs='?', default=DEFAULT_PATH,
                    help=f'file to inspect (default: {DEFAULT_PATH})')
    ap.add_argument('--sample', type=int, default=2000,
                    help='how many records to inspect (default 2000)')
    args = ap.parse_args()

    try:
        rec_iter = iter_records(args.path)
    except FileNotFoundError:
        print(f'\nFile not found: {args.path}')
        print('Pass the correct path as the first argument.\n')
        sys.exit(1)

    n = 0
    key_hint_hits = Counter()       # keys whose NAME looks DOI-ish, and are populated
    key_pattern_hits = Counter()    # keys whose VALUE matches a DOI pattern
    records_with_any_doi = 0
    example_dois = []
    all_keys_seen = Counter()

    for rec in rec_iter:
        n += 1
        found_in_this_record = False
        for key, val in walk_keys(rec):
            leaf = key.split('.')[-1].lower()
            all_keys_seen[key] += 1
            sval = str(val) if val is not None else ''
            # name-based signal
            if any(h in leaf for h in DOI_KEY_HINTS) and sval.strip():
                key_hint_hits[key] += 1
            # value-based signal (a real DOI string anywhere)
            m = DOI_RE.search(sval)
            if m:
                key_pattern_hits[key] += 1
                found_in_this_record = True
                if len(example_dois) < 8:
                    example_dois.append((key, m.group(0)))
        if found_in_this_record:
            records_with_any_doi += 1
        if n >= args.sample:
            break

    if n == 0:
        print(f'\nNo records read from {args.path} — is the file empty or a different format?\n')
        sys.exit(1)

    print(f'\nInspected {n} records from {args.path}\n')

    print('Top-level / nested keys present (by frequency, first 40):')
    for k, c in all_keys_seen.most_common(40):
        print(f'  {c:6d}  {k}')

    print('\nKeys whose NAME suggests a DOI/identifier and are populated:')
    if key_hint_hits:
        for k, c in key_hint_hits.most_common():
            print(f'  {c:6d}/{n}  {k}')
    else:
        print('  (none)')

    print('\nKeys whose VALUE actually matches a DOI pattern (10.xxxx/...):')
    if key_pattern_hits:
        for k, c in key_pattern_hits.most_common():
            print(f'  {c:6d}/{n}  {k}')
    else:
        print('  (none)')

    print(f'\nRecords containing at least one DOI-shaped string: '
          f'{records_with_any_doi}/{n} ({records_with_any_doi/n:.0%})')

    if example_dois:
        print('\nExample DOIs found:')
        for key, doi in example_dois:
            print(f'  [{key}]  {doi}')
    print()

if __name__ == '__main__':
    main()
