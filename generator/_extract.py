#!/usr/bin/env python3
"""Bootstrap-хелпер: извлекает config-запись и content-фрагмент из уже
существующей страницы сайта, чтобы генератор мог воспроизвести её 1:1.
Используется разово при заведении страницы в реестр, не при обычной сборке."""
import json, os, re, sys

GEN_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(GEN_DIR)

def extract(rel_url):
    fn = os.path.join(ROOT, rel_url.strip("/"), "index.html")
    s = open(fn, encoding="utf-8").read()
    title = re.search(r"<title>(.*?) \| НАШДОМ</title>", s).group(1)
    desc = re.search(r'<meta name="description" content="([^"]*)"', s).group(1)
    canonical = re.search(r'rel="canonical" href="([^"]*)"', s).group(1)
    url = canonical.replace("https://ursdom.ru", "")
    og_title = re.search(r'property="og:title" content="([^"]*)"', s).group(1)
    og_desc = re.search(r'property="og:description" content="([^"]*)"', s).group(1)

    graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', s, re.S).group(1))["@graph"]
    types = {g["@type"]: g for g in graph}

    bc = []
    for it in types["BreadcrumbList"]["itemListElement"]:
        e = {"name": it["name"]}
        if "item" in it:
            e["item"] = it["item"]
        bc.append(e)

    faq = [{"q": q["name"], "a": q["acceptedAnswer"]["text"]}
           for q in types.get("FAQPage", {}).get("mainEntity", [])]

    slug = url.strip("/").split("/")[-1]
    entry = {
        "url": url,
        "template": "rating" if "ItemList" in types else "article",
        "cluster": url.strip("/").split("/")[0],
        "title": title,
        "description": desc,
        "og_title": og_title,
        "og_description": og_desc,
        "breadcrumbs": bc,
        "faq": faq,
        "content": slug + ".html",
    }
    if "Article" in types:
        a = types["Article"]
        entry["marker"] = title.split(":")[0].strip().lower()
        entry["headline"] = a["headline"]
        entry["jsonld_description"] = a["description"]
        entry["datePublished"] = a["datePublished"]
        entry["dateModified"] = a["dateModified"]
    if "ItemList" in types:
        il = types["ItemList"]
        entry["marker"] = title.split(":")[0].strip().lower()
        entry["itemlist_name"] = il["name"]
        entry["itemlist"] = [x["name"] for x in il["itemListElement"]]

    body = s.split("<article>\n", 1)[1].rsplit("\n</article>", 1)[0] + "\n"
    with open(os.path.join(GEN_DIR, "content", slug + ".html"), "w", encoding="utf-8") as f:
        f.write(body)
    return entry

if __name__ == "__main__":
    entries = [extract(u) for u in sys.argv[1:]]
    print(json.dumps(entries, ensure_ascii=False, indent=2))
