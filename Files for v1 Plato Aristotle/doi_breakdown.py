#!/usr/bin/env python3
"""
doi_breakdown.py — on the GENUINE article records, are the DOIs publisher DOIs
or JSTOR 'community.' DOIs? And is there a better identifier field to use?

Usage:
    python3 doi_breakdown.py                 # uses the default path below
    python3 doi_breakdown.py /other/file.jsonl.gz
    python3 doi_breakdown.py --sample 20000  # inspect a subset (default: all)
"""
import sys, gzip, json, re, argparse
from collections import Counter, defaultdict

DEFAULT_PATH = "/Users/davidkretz/Downloads/jstor_metadata_2026-07-18.jsonl.gz"

DOI_RE = re.compile(r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+')
COMMUNITY_RE = re.compile(r'^10\.2307/community\.', re.I)
JSTOR_STABLE_RE = re.compile(r'^10\.2307/\d+$', re.I)

ARTICLE_HINTS = ('article', 'research-article', 'research article')
NONARTICLE_HINTS = ('front', 'back', 'cover', 'matter', 'toc', 'contents',
                    'editorial-board', 'index', 'advertisement', 'misc',
                    'announcement', 'volume-information')

def open_maybe_gz(path):
    with open(path, 'rb') as fh:
        magic = fh.read(2)
    if magic == b'\x1f\x8b':
        return gzip.open(path, 'rt', encoding='utf-8', errors='replace')
    return open(path, 'rt', encoding='utf-8', errors='replace')

def iter_records(path):
    f = open_maybe_gz(path)
    first = f.read(1)
    while first and first.isspace():
        first = f.read(1)
    if first == '[':
        rest = first + f.read()
        f.close()
        for rec in json.loads(rest):
            yield rec
        return
    f.close()
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

def get(rec, *keys):
    for k in keys:
        v = rec.get(k)
        if v:
            return v
    return None

def classify_type(rec):
    label_fields = [
        rec.get('content_type'), rec.get('content_subtype'),
        rec.get('c5_data_type'), rec.get('c5_section_type'),
        rec.get('doctype'), rec.get('ccda_resource_type'),
        rec.get('ccda_resource_subtype'),
    ]
    labels = ' '.join(str(x).lower() for x in label_fields if x)
    if not labels.strip():
        return 'unknown'
    if any(h in labels for h in NONARTICLE_HINTS):
        if not any(h in labels for h in ARTICLE_HINTS):
            return 'other'
    if any(h in labels for h in ARTICLE_HINTS):
        return 'article'
    return 'unknown'

def bucket_doi(doi):
    if not doi:
        return 'missing'
    s = str(doi).strip()
    if COMMUNITY_RE.match(s):
        return 'community'
    if JSTOR_STABLE_RE.match(s):
        return 'jstor_stable'
    if DOI_RE.match(s):
        return 'publisher'
    return 'malformed'

def journal_of(rec):
    j = rec.get('is_part_of')
    if isinstance(j, dict):
        return j.get('title') or j.get('name') or str(j)
    return j or (rec.get('identifiers', {}) or {}).get('journal_code') or '?'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path', nargs='?', default=DEFAULT_PATH)
    ap.add_argument('--sample', type=int, default=0,
                    help='records to inspect; 0 = all (default)')
    args = ap.parse_args()

    try:
        rec_iter = iter_records(args.path)
    except FileNotFoundError:
        print(f'\nFile not found: {args.path}\n')
        sys.exit(1)

    n = 0
    type_counts = Counter()
    type_vocab = Counter()
    ithaka_bucket = defaultdict(Counter)
    aluka_bucket = defaultdict(Counter)
    article_examples = []

    for rec in rec_iter:
        n += 1
        cls = classify_type(rec)
        type_counts[cls] += 1
        ct = rec.get('content_type') or rec.get('c5_data_type') or 'None'
        type_vocab[str(ct)] += 1

        ith = get(rec, 'ithaka_doi')
        alu = (rec.get('identifiers', {}) or {}).get('aluka_doi')
        ithaka_bucket[cls][bucket_doi(ith)] += 1
        aluka_bucket[cls][bucket_doi(alu)] += 1

        if cls == 'article' and len(article_examples) < 15:
            article_examples.append((
                (rec.get('title') or '')[:60],
                str(journal_of(rec))[:34],
                str(ith or '-')[:44],
            ))

        if args.sample and n >= args.sample:
            break

    if n == 0:
        print(f'\nNo records read from {args.path}\n')
        sys.exit(1)

    print(f'\nInspected {n} records from {args.path}\n')

    print('Record class (article vs other vs unknown):')
    for k, c in type_counts.most_common():
        print(f'  {c:7d}  {k}  ({c/n:.0%})')

    print('\ncontent_type / c5_data_type vocabulary present (first 25):')
    for k, c in type_vocab.most_common(25):
        print(f'  {c:7d}  {k}')

    def show_buckets(name, table):
        print(f'\n{name} DOI buckets:')
        for cls in ('article', 'unknown', 'other'):
            if not table[cls]:
                continue
            total = sum(table[cls].values())
            print(f'  [{cls}]  (n={total})')
            for b, c in table[cls].most_common():
                print(f'      {c:7d}  {b:12s}  {c/total:.0%}')

    show_buckets('ithaka_doi', ithaka_bucket)
    show_buckets('aluka_doi', aluka_bucket)

    print('\nSample ARTICLE records - title | journal | ithaka_doi:')
    if article_examples:
        for title, journal, doi in article_examples:
            print(f'  {title:<60}  {journal:<34}  {doi}')
    else:
        print('  (no records classified as article - check the type vocab above)')

    art = ithaka_bucket['article']
    if art:
        total = sum(art.values())
        pub = art.get('publisher', 0)
        comm = art.get('community', 0)
        stable = art.get('jstor_stable', 0)
        print('\n----- headline -----')
        print(f'  Of {total} article records:')
        print(f'    publisher DOIs : {pub:6d}  ({pub/total:.0%})')
        print(f'    JSTOR stable   : {stable:6d}  ({stable/total:.0%})')
        print(f'    community DOIs : {comm:6d}  ({comm/total:.0%})')
        print(f'    missing        : {art.get("missing",0):6d}  ({art.get("missing",0)/total:.0%})')
    print()

if __name__ == '__main__':
    main()