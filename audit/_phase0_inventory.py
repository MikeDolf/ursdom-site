#!/usr/bin/env python3
"""Phase 0 inventory builder. Read-only over the repo, writes audit/inventory.csv.
Stdlib only, no external deps."""
import re, os, csv, glob
from urllib.parse import urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

STOP = {
    'для','как','что','это','или','под','при','без','его','все','всё','она','они',
    'наш','наша','нужно','какой','какая','какие','нашдом','из','на','по','от','до',
    'выбрать','дома','дом','воды','вода','частного','такой','этот','этого'
}

def discover_pages():
    files = sorted(set(
        glob.glob('index.html') + glob.glob('*/index.html') + glob.glob('*/*/index.html')
    ))
    files = [f for f in files if not f.startswith('_templates') and not f.startswith('audit')]
    pages = {}
    for f in files:
        d = os.path.dirname(f)
        url = '/' if d == '' else '/' + d + '/'
        pages[url] = f
    return pages

def strip_tags(html):
    html = re.sub(r'<script.*?</script>', ' ', html, flags=re.S)
    html = re.sub(r'<svg.*?</svg>', ' ', html, flags=re.S)
    html = re.sub(r'<[^>]+>', ' ', html)
    return re.sub(r'\s+', ' ', html).strip()

def get_tag_block(html, tag_start_re, end_tag):
    m = re.search(tag_start_re, html)
    if not m:
        return None, None, None
    start = m.start()
    end = html.find(end_tag, m.end())
    if end == -1:
        return None, None, None
    end += len(end_tag)
    return html[start:end], start, end

def extract_meta(html):
    t = re.search(r'<title>(.*?)</title>', html, re.S)
    title = strip_tags(t.group(1)) if t else ''
    h1m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
    h1 = strip_tags(h1m.group(1)) if h1m else ''
    dm = re.search(r'<meta name="description" content="([^"]*)"', html)
    desc = dm.group(1) if dm else ''
    return title, h1, desc

def marker_query(title, h1):
    def words(s):
        ws = re.findall(r'[а-яё]{4,}', s.lower())
        return [w for w in ws if w not in STOP]
    tw, hw = words(title), words(h1)
    tw_set = set(tw)
    common = [w for w in hw if w in tw_set]
    if common:
        return ' '.join(common[:4])
    return ' '.join(hw[:4]) if hw else ' '.join(tw[:4])

def word_count_and_links(html):
    art, a_start, a_end = get_tag_block(html, r'<article[ >]', '</article>')
    if art is None:
        main, m_start, m_end = get_tag_block(html, r'<main[ >]', '</main>')
        body = main if main else ''
        is_article = False
    else:
        body = art
        is_article = True
    text = strip_tags(body)
    wc = len(text.split()) if text else 0
    links = []
    for href, inner in re.findall(r'<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>', body, re.S):
        if href.startswith('/'):
            anchor = strip_tags(inner)
            links.append((href, anchor))
    return wc, links, is_article

INTERNAL_HTML_RE = re.compile(r'href="(/[^"#?]*)')

def classify_section(html, tag_start_re, end_tag):
    block, _, _ = get_tag_block(html, tag_start_re, end_tag)
    return block or ''

def normalize_target(href, valid_urls):
    if not href.startswith('/'):
        return None
    # strip query/fragment defensively (already excluded by regex) and ensure trailing slash form
    if href in ('/',):
        return '/'
    if not href.endswith('/'):
        # could be an asset path (css/img/xml/txt) -> not a page
        if re.search(r'\.[a-zA-Z0-9]+$', href):
            return None
        href = href + '/'
    return href if href in valid_urls else None

def main():
    pages = discover_pages()
    valid_urls = set(pages.keys())

    inbound = {u: [] for u in valid_urls}  # url -> list of (source_url, location)
    per_page = {}

    for url, fn in pages.items():
        html = open(fn, encoding='utf-8').read()
        title, h1, desc = extract_meta(html)
        marker = marker_query(title, h1)
        wc, body_links, is_article = word_count_and_links(html)

        header_block = classify_section(html, r'<header class="site-header"', '</header>')
        footer_block = classify_section(html, r'<footer class="site-footer"', '</footer>')
        breadcrumb_block = classify_section(html, r'<nav class="breadcrumbs"', '</nav>')
        related_block = classify_section(html, r'<nav class="related"', '</nav>')

        def hrefs_in(block):
            return set(m for m in INTERNAL_HTML_RE.findall(block))

        header_hrefs = hrefs_in(header_block)
        footer_hrefs = hrefs_in(footer_block)
        breadcrumb_hrefs = hrefs_in(breadcrumb_block)
        related_hrefs = hrefs_in(related_block)

        all_hrefs_with_pos = re.findall(r'href="(/[^"#?]*)"', html)
        for href in all_hrefs_with_pos:
            target = normalize_target(href, valid_urls)
            if not target or target == url:
                continue
            if href in header_hrefs:
                loc = 'header-nav'
            elif href in footer_hrefs:
                loc = 'footer-nav'
            elif href in breadcrumb_hrefs:
                loc = 'breadcrumbs'
            elif href in related_hrefs:
                loc = 'related'
            elif is_article:
                loc = 'article-body'
            else:
                loc = 'main-card'
            inbound[target].append((url, loc))

        body_out = [(h, a) for h, a in body_links if normalize_target(h, valid_urls) and normalize_target(h, valid_urls) != url]

        per_page[url] = dict(
            file=fn, title=title, h1=h1, desc=desc, marker=marker,
            word_count=wc, is_article=is_article,
            outbound_body=body_out,
        )

    rows = []
    for url in sorted(pages.keys()):
        p = per_page[url]
        inb = inbound[url]
        inb_content = [x for x in inb if x[1] not in ('header-nav', 'footer-nav', 'breadcrumbs')]
        loc_counts = {}
        for _, loc in inb:
            loc_counts[loc] = loc_counts.get(loc, 0) + 1
        rows.append(dict(
            url=url,
            title=p['title'],
            h1=p['h1'],
            description=p['desc'],
            marker_query=p['marker'],
            word_count=p['word_count'],
            is_article='yes' if p['is_article'] else 'no',
            outbound_body_count=len(p['outbound_body']),
            outbound_body_links='; '.join(f"{h} ({a})" for h, a in p['outbound_body']),
            inbound_total=len(inb),
            inbound_content_only=len(inb_content),
            inbound_breakdown='; '.join(f"{k}:{v}" for k, v in sorted(loc_counts.items())),
        ))

    os.makedirs('audit', exist_ok=True)
    with open('audit/inventory.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=';')
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # ---- summary ----
    print(f"Всего страниц: {len(rows)}")
    sections = {}
    for r in rows:
        u = r['url']
        sec = 'главная' if u == '/' else u.strip('/').split('/')[0]
        sections[sec] = sections.get(sec, 0) + 1
    print("Разбивка по разделам:", sections)

    orphans = [r for r in rows if r['inbound_content_only'] == 0]
    print(f"\nСтраницы-сироты (0 входящих из контента, без учёта header/footer/breadcrumbs): {len(orphans)}")
    for r in orphans:
        print(f"  {r['url']}")

    no_out = [r for r in rows if r['is_article'] == 'yes' and r['outbound_body_count'] == 0]
    print(f"\nСтатьи без единой ссылки в теле: {len(no_out)}")
    for r in no_out:
        print(f"  {r['url']}")

    titles = {}
    for r in rows:
        titles.setdefault(r['title'], []).append(r['url'])
    dup_titles = {t: u for t, u in titles.items() if len(u) > 1}
    print(f"\nДубли title: {len(dup_titles)}")
    for t, u in dup_titles.items():
        print(f"  '{t}': {u}")

    descs = {}
    for r in rows:
        descs.setdefault(r['description'], []).append(r['url'])
    dup_descs = {d: u for d, u in descs.items() if len(u) > 1}
    print(f"\nДубли description: {len(dup_descs)}")
    for d, u in dup_descs.items():
        print(f"  '{d[:60]}...': {u}")

    print(f"\nСредний объём статьи (слов): {sum(r['word_count'] for r in rows if r['is_article']=='yes') // max(1,sum(1 for r in rows if r['is_article']=='yes'))}")

if __name__ == '__main__':
    main()
