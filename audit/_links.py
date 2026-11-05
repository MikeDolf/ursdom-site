# -*- coding: utf-8 -*-
"""Ссылки по всему сайту, а не только по разделу доставки.

_verify.py проверяет /dostavka/. Здесь все страницы репозитория (НАШДОМ:
главная, дренаж, ливнёвка, скважина, статьи) и все виды ссылок:
- внутренняя ссылка ведёт на существующую страницу или файл;
- якорь #id есть на целевой странице;
- src картинок, скриптов и стилей существует;
- внешняя ссылка в новой вкладке несёт rel="noopener";
- нет http:// на свои страницы.

Запуск: python3 audit/_links.py   (пустой вывод - замечаний нет)
"""
import glob, html, io, os, re, sys, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = ("/audit/", "/dostavka-src/", "/node_modules/", "/.git/", "/_templates/", "/generator/", "/userfls/")

pages = {}
for p in glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True):
    rel = "/" + os.path.relpath(p, ROOT).replace(os.sep, "/")
    if any(s in rel for s in SKIP_DIRS):
        continue
    pages[rel] = io.open(p, encoding="utf-8").read()

def url_of(rel):
    return rel[:-len("index.html")] if rel.endswith("/index.html") else rel

ids = {}
for rel, h in pages.items():
    ids[url_of(rel)] = set(re.findall(r'\bid="([^"]+)"', h))

def resolve(path):
    """Путь от корня -> (существует, ключ страницы для якорей)."""
    path = urllib.parse.unquote(path)
    fs = os.path.join(ROOT, path.lstrip("/"))
    if path.endswith("/"):
        return os.path.exists(os.path.join(fs, "index.html")), path
    if os.path.isfile(fs):
        return True, path
    if os.path.isdir(fs) and os.path.exists(os.path.join(fs, "index.html")):
        return True, path + "/"
    return False, path

problems = []
for rel, h in sorted(pages.items()):
    me = url_of(rel)
    body = re.sub(r"(?is)<script\b[^>]*>.*?</script>", " ", h)
    for tag, attr, val in re.findall(r'<(a|link|script|img|source|iframe)\b[^>]*?\b(href|src|srcset)="([^"]*)"', h, re.I):
        if attr == "srcset":
            cand = [x.strip().split(" ")[0] for x in val.split(",") if x.strip()]
        else:
            cand = [val]
        for v in cand:
            v = html.unescape(v)
            if not v or v.startswith(("mailto:", "tel:", "data:", "javascript:")):
                continue
            if re.match(r"https?://(www\.)?ursdom\.ru", v):
                if v.startswith("http://"):
                    problems.append((me, "http:// на свой сайт", v))
                v = re.sub(r"https?://(www\.)?ursdom\.ru", "", v) or "/"
            if re.match(r"[a-z]+://", v):
                continue
            if v.startswith("#"):
                frag = v[1:]
                if frag and frag not in ids.get(me, set()):
                    problems.append((me, "нет якоря на странице", v))
                continue
            path, _, frag = v.partition("#")
            path = path.split("?")[0]
            if not path.startswith("/"):
                path = urllib.parse.urljoin(me, path)
            ok, key = resolve(path)
            if not ok:
                problems.append((me, "нет страницы/файла (%s)" % tag, v))
            elif frag and key in ids and frag not in ids[key]:
                problems.append((me, "нет якоря на целевой странице", v))
    for a in re.findall(r"<a\b[^>]*>", body, re.I):
        if 'target="_blank"' in a and "noopener" not in a:
            problems.append((me, "target=_blank без noopener", a[:100]))

for me, kind, v in problems:
    print("%-55s %-34s %s" % (me, kind, v))
sys.exit(1 if problems else 0)
