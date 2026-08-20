#!/usr/bin/env python3
"""
build_site.py — assemble the Footnotes to Plato static site.

Deliberately dependency-free (Python standard library only) and framework-free.
Run it, commit `docs/`, and GitHub Pages serves it. No Actions, no npm, no
toolchain to rot.

    python3 build_site.py                 # build into ./docs
    python3 build_site.py --out _site      # build elsewhere
    python3 build_site.py --serve          # build, then serve for a look

Inputs
    site/content/*.md      page content (Markdown; front-matter as `key: value`
                           lines before the first blank line)
    site/static/*          copied verbatim (css, js, images)
    viewer_data/           the aggregator's output; copied into the build
    view_a.html, view_b.html, filterbar.*, series.*, *_groups.json
                           the two interactive viewers and their assets

Output
    docs/index.html, docs/about/, docs/methods/, docs/data/, docs/contact/,
    docs/explore/works/, docs/explore/passages/, plus assets.

Pages are written as `<name>/index.html` so URLs are clean (`/methods/` rather
than `/methods.html`).

The Markdown subset implemented here is small on purpose — headings, emphasis,
lists, tables, code, blockquotes, links, footnotes-as-links, and raw HTML
passthrough. It covers what the methods record actually uses. It is not a
general Markdown engine and does not try to be; if a document needs more, the
right move is to write that bit as HTML in the .md file, which passes through.
"""
import argparse, html, http.server, os, re, shutil, socketserver, sys
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
CONTENT = os.path.join(SITE, "content")
STATIC = os.path.join(SITE, "static")

# ---------------------------------------------------------------------------
# Navigation. Single source of truth — every page's nav is generated from this,
# so a link change happens once. (order, url, label)
# ---------------------------------------------------------------------------
NAV = [
    ("/",                   "Home"),
    ("/explore/works/",     "Works over time"),
    ("/explore/passages/",  "Passages"),
    ("/methods/",           "Methods"),
    ("/data/",              "Data"),
    ("/about/",             "About"),
    ("/contact/",           "Contact"),
]

SITE_TITLE = "Footnotes to Plato"
SITE_TAGLINE = "A passage-level citation index of the ancient-philosophy scholarship"


# ---------------------------------------------------------------------------
# Minimal Markdown
# ---------------------------------------------------------------------------
def _inline(t):
    """Inline spans. Order matters: code first so its contents are literal."""
    out, i = [], 0
    for m in re.finditer(r"`([^`]+)`", t):
        out.append(_inline_no_code(t[i:m.start()]))
        out.append("<code>" + html.escape(m.group(1)) + "</code>")
        i = m.end()
    out.append(_inline_no_code(t[i:]))
    return "".join(out)


def _inline_no_code(t):
    # Raw HTML in content is intentional (used for figures and callouts), so we
    # do NOT escape here; content is authored, not user-supplied.
    t = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1">', t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", t)
    return t


def slugify(s):
    s = re.sub(r"<[^>]+>", "", s).strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"[\s_]+", "-", s).strip("-")


def markdown(md):
    """Return (html, toc) where toc is [(level, id, text), ...]."""
    # Raw <script>/<style>/<pre> blocks must survive untouched: the inline
    # formatter would otherwise mangle JavaScript (a lone `*` becomes emphasis,
    # `//` looks like a link) and silently break the page. Stash them, run the
    # converter, then restore.
    stash = []

    def _stash(m):
        stash.append(m.group(0))
        return f"\x00STASH{len(stash) - 1}\x00"

    md = re.sub(r"<(script|style)\b[\s\S]*?</\1>", _stash, md, flags=re.I)

    html_out, toc = _markdown_inner(md)

    for i, block in enumerate(stash):
        # the stash token may have been wrapped in <p> by the block parser
        html_out = html_out.replace(f"<p>\x00STASH{i}\x00</p>", block)
        html_out = html_out.replace(f"\x00STASH{i}\x00", block)
    return html_out, toc


def _markdown_inner(md):
    lines = md.split("\n")
    out, toc = [], []
    i, n = 0, len(lines)
    para = []

    def flush():
        if para:
            out.append("<p>" + _inline(" ".join(para).strip()) + "</p>")
            para.clear()

    while i < n:
        ln = lines[i]

        # fenced code
        if ln.startswith("```"):
            flush()
            lang = ln[3:].strip()
            body = []
            i += 1
            while i < n and not lines[i].startswith("```"):
                body.append(lines[i]); i += 1
            i += 1
            cls = f' class="lang-{html.escape(lang)}"' if lang else ""
            out.append(f"<pre><code{cls}>" + html.escape("\n".join(body)) + "</code></pre>")
            continue

        # horizontal rule
        if re.fullmatch(r"\s*---+\s*", ln):
            flush(); out.append("<hr>"); i += 1; continue

        # heading
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m:
            flush()
            lvl = len(m.group(1)); txt = _inline(m.group(2).strip())
            sid = slugify(m.group(2))
            if lvl <= 3:
                toc.append((lvl, sid, re.sub(r"<[^>]+>", "", txt)))
            out.append(f'<h{lvl} id="{sid}">{txt}'
                       f'<a class="anchor" href="#{sid}" aria-label="link">#</a></h{lvl}>')
            i += 1; continue

        # table (pipe style, with a --- separator row)
        if "|" in ln and i + 1 < n and re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]*$", lines[i + 1]):
            flush()
            def cells(r):
                r = r.strip()
                if r.startswith("|"): r = r[1:]
                if r.endswith("|"): r = r[:-1]
                return [c.strip() for c in r.split("|")]
            head = cells(ln); i += 2
            rows = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append(cells(lines[i])); i += 1
            t = ["<div class='tablewrap'><table><thead><tr>"]
            t += [f"<th>{_inline(c)}</th>" for c in head]
            t.append("</tr></thead><tbody>")
            for r in rows:
                t.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t)); continue

        # blockquote
        if ln.startswith(">"):
            flush()
            body = []
            while i < n and lines[i].startswith(">"):
                body.append(lines[i].lstrip(">").strip()); i += 1
            out.append("<blockquote>" + _inline(" ".join(body)) + "</blockquote>")
            continue

        # lists (nested by indent, ordered or not)
        if re.match(r"^\s*([-*+]|\d+\.)\s+", ln):
            flush()
            out.append(_list(lines, i))
            i = _list_end(lines, i)
            continue

        if not ln.strip():
            flush(); i += 1; continue

        para.append(ln.strip()); i += 1

    flush()
    return "\n".join(out), toc


def _item_re(ln):
    return re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", ln)


def _list_end(lines, start):
    i, n = start, len(lines)
    base = len(_item_re(lines[start]).group(1))
    while i < n:
        ln = lines[i]
        m = _item_re(ln)
        if m and len(m.group(1)) >= base:
            i += 1; continue
        if ln.strip() and (len(ln) - len(ln.lstrip())) > base:
            i += 1; continue          # continuation line
        if not ln.strip() and i + 1 < n and _item_re(lines[i + 1] or ""):
            i += 1; continue          # blank line inside a list
        break
    return i


def _list(lines, start):
    end = _list_end(lines, start)
    base = len(_item_re(lines[start]).group(1))
    ordered = bool(re.match(r"^\s*\d+\.", lines[start]))
    items, cur, sub = [], None, []
    i = start
    while i < end:
        ln = lines[i]
        m = _item_re(ln)
        if m and len(m.group(1)) == base:
            if cur is not None:
                items.append((cur, sub)); sub = []
            cur = m.group(3); i += 1; continue
        if m and len(m.group(1)) > base:
            j = _list_end(lines, i)
            sub.append(_list(lines, i)); i = j; continue
        if ln.strip():
            cur = (cur or "") + " " + ln.strip()
        i += 1
    if cur is not None:
        items.append((cur, sub))
    tag = "ol" if ordered else "ul"
    body = "".join(f"<li>{_inline(t.strip())}{''.join(s)}</li>" for t, s in items)
    return f"<{tag}>{body}</{tag}>"


# ---------------------------------------------------------------------------
# Page assembly
# ---------------------------------------------------------------------------
def read_content(path):
    """Parse `key: value` front matter followed by a blank line, then body."""
    raw = open(path, encoding="utf-8").read()
    meta, body = {}, raw
    if raw.lstrip().startswith("---"):
        parts = raw.lstrip().split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            body = parts[2]
    return meta, body


def nav_html(current):
    items = []
    for url, label in NAV:
        cls = ' class="on"' if url == current else ""
        items.append(f'<a href="{url}"{cls}>{html.escape(label)}</a>')
    return "".join(items)


DRAFT = False


def page(title, body, current, *, subtitle=None, toc=None, head_extra="",
         wide=False, description=None):
    desc = description or SITE_TAGLINE
    toc_html = ""
    if toc:
        li = []
        for lvl, sid, txt in toc:
            if lvl > 3:
                continue
            li.append(f'<li class="l{lvl}"><a href="#{sid}">{html.escape(txt)}</a></li>')
        if li:
            toc_html = ('<nav class="toc" aria-label="On this page">'
                        '<div class="toc-h">On this page</div><ul>'
                        + "".join(li) + "</ul></nav>")
    sub = f'<div class="sub">{subtitle}</div>' if subtitle else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — {SITE_TITLE}</title>
<meta name="description" content="{html.escape(desc)}">
{'<meta name="robots" content="noindex,nofollow">' if DRAFT else ''}
<link rel="stylesheet" href="/static/site.css">
{head_extra}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
{'<div class="draftbar">Draft — figures and text are still being checked. Not indexed; please do not cite yet.</div>' if DRAFT else ''}
<header class="site">
  <div class="bar">
    <a class="brand" href="/"><span class="bt">{SITE_TITLE}</span></a>
    <button class="navtoggle" aria-label="Menu" aria-expanded="false">☰</button>
    <nav class="mainnav">{nav_html(current)}</nav>
  </div>
</header>
<main id="main" class="{'wide' if wide else ''}">
  <div class="pagehead">
    <h1>{title}</h1>
    {sub}
  </div>
  {toc_html}
  <div class="prose">
{body}
  </div>
</main>
<footer class="site">
  <div class="fwrap">
    <div>
      <strong>{SITE_TITLE}</strong> · {SITE_TAGLINE}<br>
      <span class="muted">Built {date.today().isoformat()}. Derived from a JSTOR
      Text Analysis Support delivery; a finding aid that links out to the
      articles, never a substitute for them.</span>
    </div>
    <div class="flinks">{nav_html(None)}</div>
  </div>
</footer>
<script src="/static/site.js"></script>
</body>
</html>
"""


def write(out, relpath, text):
    dest = os.path.join(out, relpath)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text)
    return dest


# ---------------------------------------------------------------------------
# Viewer pages: wrap the existing standalone HTML in the site chrome
# ---------------------------------------------------------------------------
def extract_viewer(path):
    """Pull <style>, body content and <script> out of a standalone viewer so it
    can be re-hosted inside the site shell without losing anything."""
    src = open(path, encoding="utf-8").read()
    styles = "\n".join(m.group(0) for m in re.finditer(r"<style>[\s\S]*?</style>", src))
    links = "\n".join(m.group(0) for m in re.finditer(r'<link rel="stylesheet"[^>]*>', src))
    scripts = "\n".join(m.group(0) for m in re.finditer(r"<script[\s\S]*?</script>", src))
    m = re.search(r"<body>([\s\S]*?)</body>", src)
    body = m.group(1) if m else ""
    body = re.sub(r"<script[\s\S]*?</script>", "", body)
    # the viewer's own masthead is replaced by the site header
    body = re.sub(r'<header class="mast">[\s\S]*?</header>', "", body)
    return links, styles, body, scripts


def build_viewer_page(out, src, url, title, subtitle, intro_md, current):
    links, styles, body, scripts = extract_viewer(src)
    intro, _ = markdown(intro_md)
    # asset paths are relative in the standalone files; make them absolute so
    # they resolve from /explore/works/ and /explore/passages/ alike
    def absolutize(s):
        s = re.sub(r'(src|href)="(?!/|https?:|#)([^"]+)"', r'\1="/\2"', s)
        return s
    links, scripts = absolutize(links), absolutize(scripts)
    # data fetches inside the viewer scripts point at viewer_data/
    scripts = re.sub(r"fetch\('(?!/|https?:)([^']+)'", r"fetch('/data/viewer/\1'", scripts)
    # View B resolves per-work paths from works_index.json at runtime, and those
    # paths are relative to the data directory ("view_b/Republic.json"). Give it
    # the published base so they resolve from any page URL.
    scripts = scripts.replace('const FILES = {};',
                              'const FILES = {__base:"/data/viewer/"};')
    # ...and don't double-prefix anything already absolute
    scripts = scripts.replace("/data/viewer//data/viewer/", "/data/viewer/")
    html_out = page(
        title, f'<div class="viewer-intro">{intro}</div>\n{body}', current,
        subtitle=subtitle, wide=True,
        head_extra=links + "\n" + styles,
    )
    html_out = html_out.replace("</body>", scripts + "\n</body>")
    write(out, url.strip("/") + "/index.html", html_out)


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs")
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--viewer-data", default="viewer_data",
                    help="aggregator output directory to publish")
    ap.add_argument("--domain", default=None,
                    help="custom domain for GitHub Pages; writes docs/CNAME. "
                         "Persist it in site/domain.txt to avoid repeating.")
    ap.add_argument("--draft", action="store_true",
                    help="add <meta name=robots content=noindex,nofollow> so "
                         "search engines skip the site while it is unfinished")
    args = ap.parse_args()

    global DRAFT
    DRAFT = args.draft

    out = os.path.join(ROOT, args.out)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)

    # static assets
    if os.path.isdir(STATIC):
        shutil.copytree(STATIC, os.path.join(out, "static"), dirs_exist_ok=True)

    # viewer assets used by both explore pages
    for f in ("filterbar.js", "filterbar.css", "series.js", "series.css",
              "journal_groups.json", "work_groups.json"):
        p = os.path.join(ROOT, f)
        if os.path.exists(p):
            shutil.copy(p, os.path.join(out, f))
        else:
            print(f"  note: {f} not found — skipped", file=sys.stderr)

    # published data
    vd = os.path.join(ROOT, args.viewer_data)
    if os.path.isdir(vd):
        shutil.copytree(vd, os.path.join(out, "data", "viewer"), dirs_exist_ok=True)
        print(f"  published {args.viewer_data}/ -> data/viewer/", file=sys.stderr)
    else:
        print(f"  WARNING: {args.viewer_data}/ not found. The viewers will have "
              f"no data. Run build_viewer_data.py first.", file=sys.stderr)

    # content pages
    pages = {
        "index.md":    ("/",         False),
        "about.md":    ("/about/",   False),
        "methods.md":  ("/methods/", True),
        "data.md":     ("/data/",    False),
        "contact.md":  ("/contact/", False),
    }
    for fn, (url, with_toc) in pages.items():
        path = os.path.join(CONTENT, fn)
        if not os.path.exists(path):
            print(f"  note: content/{fn} missing — skipped", file=sys.stderr)
            continue
        meta, body_md = read_content(path)
        body, toc = markdown(body_md)
        h = page(meta.get("title", fn),
                 body, url,
                 subtitle=meta.get("subtitle"),
                 toc=toc if with_toc else None,
                 description=meta.get("description"))
        rel = "index.html" if url == "/" else url.strip("/") + "/index.html"
        write(out, rel, h)

    # the methods record, converted from the project's own Markdown
    mrec = os.path.join(CONTENT, "citation-pipeline-methods.md")
    if os.path.exists(mrec):
        body_md = open(mrec, encoding="utf-8").read()
        body_md = re.sub(r"^# .*\n", "", body_md, count=1)   # title comes from the shell
        body, toc = markdown(body_md)
        write(out, "methods/pipeline/index.html",
              page("Pipeline & methods record", body, "/methods/",
                   subtitle="The build as actually executed — every decision, "
                            "assumption, and known limitation",
                   toc=toc))

    # viewers
    va = os.path.join(ROOT, "view_a.html")
    vb = os.path.join(ROOT, "view_b.html")
    if os.path.exists(va):
        build_viewer_page(
            out, va, "/explore/works/", "Works over time",
            "How attention to each work moved across 135 years of scholarship",
            open(os.path.join(CONTENT, "_intro_works.md"), encoding="utf-8").read()
            if os.path.exists(os.path.join(CONTENT, "_intro_works.md")) else "",
            "/explore/works/")
    if os.path.exists(vb):
        build_viewer_page(
            out, vb, "/explore/passages/", "Passages",
            "Which passages of a single work the scholarship actually cites",
            open(os.path.join(CONTENT, "_intro_passages.md"), encoding="utf-8").read()
            if os.path.exists(os.path.join(CONTENT, "_intro_passages.md")) else "",
            "/explore/passages/")

    # GitHub Pages: don't run Jekyll over our output
    write(out, ".nojekyll", "")

    # GitHub Pages custom domain. This has to be REGENERATED on every build,
    # because the build wipes `out/` first — a hand-placed docs/CNAME would
    # vanish on the next run and the domain would quietly stop resolving.
    # Precedence: --domain flag, else site/domain.txt if present.
    domain = args.domain
    if not domain:
        dfile = os.path.join(SITE, "domain.txt")
        if os.path.exists(dfile):
            domain = open(dfile, encoding="utf-8").read().strip()
    if domain:
        write(out, "CNAME", domain + "\n")
        print(f"  CNAME -> {domain}", file=sys.stderr)
    else:
        print("  note: no custom domain set. Pass --domain example.com or put "
              "it in site/domain.txt, or GitHub Pages will drop the domain "
              "on the next deploy.", file=sys.stderr)

    if DRAFT:
        print("  DRAFT mode: pages carry noindex and a draft banner.",
              file=sys.stderr)

    n = sum(len(f) for _, _, f in os.walk(out))
    print(f"\nBuilt {n} files into {args.out}/", file=sys.stderr)
    print("Commit that directory and point GitHub Pages at it "
          "(Settings > Pages > Deploy from branch > /docs).", file=sys.stderr)

    if args.serve:
        os.chdir(out)
        class H(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *a): pass
        with socketserver.TCPServer(("", args.port), H) as httpd:
            print(f"\nServing http://localhost:{args.port}/  (ctrl-c to stop)",
                  file=sys.stderr)
            httpd.serve_forever()


if __name__ == "__main__":
    main()
