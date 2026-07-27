#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка раздела доставки в /dostavka/. Изолирован от ursdom.
Зависимости: Python 3 + jinja2. Вывод: статические index.html + sitemap раздела."""
import os, sys, json, html, difflib, datetime
from jinja2 import Environment, FileSystemLoader

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "dostavka")
sys.path.insert(0, os.path.join(HERE, "data"))

from site_config import SITE, ADVANTAGES, GUARANTEES
from products import MATERIALS, EXTRA
from prices import PER_CUBE, PRICE_NOTE, DELIVERY_NOTE
from cities import CITIES
from articles import ARTICLES, AUTHOR

env = Environment(loader=FileSystemLoader(os.path.join(HERE, "templates")),
                  autoescape=False, trim_blocks=False, lstrip_blocks=False)
DOMAIN = SITE["domain"]
TODAY = "2026-07-23"
PER_CUBE_LIST = list(PER_CUBE.items())

def crumbs(items):
    out = []
    for i, (name, url) in enumerate(items):
        if url and i != len(items) - 1:
            out.append(f'<a href="{url}">{name}</a>')
        else:
            out.append(name)
    return " › ".join(out)

def localbusiness():
    return {
        "@type": "LocalBusiness",
        "@id": DOMAIN + SITE["base"] + "#business",
        "name": SITE["brand"],
        "description": SITE["tagline"] + " по " + SITE["region"],
        "url": DOMAIN + SITE["base"],
        "telephone": SITE["phone"],
        "email": SITE["email"],
        "areaServed": SITE["region"],
        "openingHours": "Mo-Sa 08:00-20:00",
        "priceRange": "по запросу",
    }

def bc_schema(items):
    el = []
    for i, (name, url) in enumerate(items):
        d = {"@type": "ListItem", "position": i + 1, "name": name}
        if url:
            d["item"] = DOMAIN + url
        el.append(d)
    return {"@type": "BreadcrumbList", "itemListElement": el}

def faq_schema(faq):
    return {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q,
         "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}

def article_schema(url, title, desc):
    return {"@type": "Article", "headline": title, "description": desc,
            "inLanguage": "ru-RU", "datePublished": TODAY, "dateModified": TODAY,
            "mainEntityOfPage": DOMAIN + url,
            "author": {"@type": "Person", "name": AUTHOR["name"], "jobTitle": AUTHOR["role"]},
            "publisher": {"@type": "Organization", "name": SITE["brand"]}}

def graph(*nodes):
    return json.dumps({"@context": "https://schema.org", "@graph": list(nodes)},
                      ensure_ascii=False, indent=2)

def write(url, html_str):
    path = os.path.join(OUT, url[len(SITE["base"]):].strip("/"), "index.html") \
        if url != SITE["base"] else os.path.join(OUT, "index.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(html_str)
    return path

BASE_CTX = dict(cfg=SITE, advantages=ADVANTAGES, guarantees=GUARANTEES,
                per_cube=PER_CUBE_LIST, price_note=PRICE_NOTE, delivery_note=DELIVERY_NOTE,
                extra=EXTRA, cities=CITIES)

pages = []  # (url, rendered_html, family)

# ---- ХАБ ----
url = SITE["base"]
crumb_items = [("Главная", "/"), ("Доставка материалов", None)]
jl = graph(localbusiness(), bc_schema(crumb_items), faq_schema(MATERIALS["shcheben"]["faq"][:4]))
htmlp = env.get_template("hub.j2").render(
    **BASE_CTX, title="Доставка щебня, песка и нерудных материалов по Екатеринбургу и области",
    desc="Доставка щебня, песка, ПГС и отсева по Екатеринбургу и Свердловской области. Самосвалы от 5 до 20 кубов, оплата после выгрузки, честный объём.",
    canonical=DOMAIN + url, h1="Доставка щебня, песка и нерудных материалов по " + SITE["region"],
    crumbs_html=crumbs(crumb_items), jsonld=jl,
    faq=MATERIALS["shcheben"]["faq"][:4],
    related_links=[("/dostavka/shcheben/", "Доставка щебня: фракции и цены"),
                   ("/dostavka/pesok/", "Доставка песка"),
                   ("/dostavka/stati/kakoy-shcheben-vybrat/", "Какой щебень выбрать")])
pages.append((url, htmlp, "hub"))

# ---- MONEY: щебень, песок ----
money_cfg = {
    "shcheben": dict(hero_sub="Гранитный, известняковый, гравийный и вторичный щебень с доставкой по " + SITE["region"] + ". Фракции 5-20, 20-40, 40-70 и отсев, самосвалы от 5 до 20 кубов.",
                     mat_gen="щебня", mat_acc="доставку щебня", subject="доставка щебня, " + SITE["region_short"],
                     title="Доставка щебня в Екатеринбурге и области: фракции, цена",
                     desc="Доставка щебня по Екатеринбургу и Свердловской области: гранит, известняк, фракции 5-20, 20-40, 40-70. Самосвалы 5-20 кубов, оплата после выгрузки.",
                     h1="Доставка щебня по Екатеринбургу и Свердловской области"),
    "pesok": dict(hero_sub="Карьерный и речной песок с доставкой по " + SITE["region"] + ". Под отсыпку, подушку фундамента, бетон и кладку.",
                  mat_gen="песка", mat_acc="доставку песка", subject="доставка песка, " + SITE["region_short"],
                  title="Доставка песка в Екатеринбурге и области: карьерный, речной",
                  desc="Доставка песка по Екатеринбургу и Свердловской области: карьерный для отсыпки, речной мытый для бетона. Самосвалы от 5 кубов, оплата после выгрузки.",
                  h1="Доставка песка по Екатеринбургу и Свердловской области"),
}
for slug, mc in money_cfg.items():
    mat = MATERIALS[slug]
    url = SITE["base"] + slug + "/"
    crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]), (mat["name"], None)]
    jl = graph(localbusiness(), bc_schema(crumb_items), faq_schema(mat["faq"]))
    rel = [("/dostavka/", "Все материалы и города"),
           ("/dostavka/pesok/" if slug == "shcheben" else "/dostavka/shcheben/",
            "Доставка песка" if slug == "shcheben" else "Доставка щебня"),
           ("/dostavka/stati/skolko-shchebnya-nuzhno/", "Сколько нужно и сколько в самосвале")]
    htmlp = env.get_template("money.j2").render(
        **BASE_CTX, **mc, canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items), jsonld=jl,
        intro=mat["intro"], types=mat["types"], fractions=mat.get("fractions"),
        faq=mat["faq"], related_links=rel)
    pages.append((url, htmlp, "money"))

# ---- ГЕО: щебень × город ----
for c in CITIES:
    url = SITE["base"] + "shcheben/" + c["slug"] + "/"
    crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]),
                   ("Щебень", SITE["base"] + "shcheben/"), (c["name"], None)]
    # city-specific FAQ, чтобы страницы не были дублями
    cfaq = [
        (f"Сколько стоит доставка щебня {c['prep']}?",
         f"Стоимость зависит от фракции, объёма и расстояния ({c['dist']}). Назовите материал, "
         f"объём и адрес, посчитаем цену с доставкой и {SITE['callback_promise']}."),
        (f"За какой срок привезёте щебень {c['prep']}?",
         f"Срок согласуем при заказе. {c['block'].split('.')[0]}."),
        ("Какую фракцию щебня выбрать?",
         "Под фундамент гранит 20-40, под заезд 40-70 в основание и 20-40 сверху, под дорожки 5-20. "
         "Поможем подобрать под задачу."),
        ("Возможен ли самовывоз?",
         "Да, самовывоз возможен. Если есть свой транспорт, подскажем ближайшую площадку."),
    ]
    jl = graph(localbusiness(), bc_schema(crumb_items), faq_schema(cfaq))
    others = [(f"/dostavka/shcheben/{o['slug']}/", f"Доставка щебня {o['prep']}")
              for o in CITIES if o["slug"] != c["slug"]][:3]
    rel = [("/dostavka/shcheben/", "Доставка щебня: все фракции и цены"),
           ("/dostavka/", "Другие города и материалы")] + others
    htmlp = env.get_template("geo.j2").render(
        **BASE_CTX, city=c, canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items), jsonld=jl,
        title=f"Доставка щебня {c['prep']}: цена, самосвалом с выгрузкой",
        desc=f"Доставка щебня {c['prep']} и в район ({c['dist']}). Гранит, известняк, фракции 20-40, 40-70. Самосвалы 5-20 кубов, оплата после выгрузки.",
        h1=f"Доставка щебня {c['prep']}", faq=cfaq, related_links=rel[:5])
    pages.append((url, htmlp, "geo"))

# ---- СТАТЬИ ----
for a in ARTICLES:
    url = SITE["base"] + "stati/" + a["slug"] + "/"
    crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]),
                   ("Статьи", None), (a["title"], None)]
    jl = graph(localbusiness(), bc_schema(crumb_items[:3] + [(a["title"], None)]),
               faq_schema(a["faq"]), article_schema(url, a["title"], a["desc"]))
    rel = [("/dostavka/" + s + "/", "Доставка " + MATERIALS[s]["name"].lower()) for s in a["links"]]
    rel.append(("/dostavka/", "Все города и материалы"))
    htmlp = env.get_template("article.j2").render(
        **BASE_CTX, author=AUTHOR, canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items), jsonld=jl,
        title=a["title"] + " | " + SITE["brand"], desc=a["desc"], h1=a["h1"], lead=a["lead"],
        sections=a["sections"], faq=a["faq"], related_links=rel)
    pages.append((url, htmlp, "article"))

# ---- ЗАПИСЬ ----
written = []
for url, h, fam in pages:
    written.append((write(url, h), url, fam))

# ---- SITEMAP раздела ----
sm = ['<?xml version="1.0" encoding="UTF-8"?>',
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for url, h, fam in pages:
    sm.append(f"  <url>\n    <loc>{DOMAIN}{url}</loc>\n    <lastmod>{TODAY}</lastmod>\n  </url>")
sm.append("</urlset>\n")
open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8").write("\n".join(sm))

print(f"Собрано страниц: {len(pages)}")
for p, url, fam in written:
    print(f"  [{fam:7}] {url}")

# ---- ПРОВЕРКА ДУБЛЕЙ (anti-doorway, ratio < 0.80) ----
def visible(hs):
    import re
    hs = re.sub(r"<script.*?</script>", " ", hs, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", hs)).strip()
geo = [(u, visible(h)) for u, h, f in pages if f == "geo"]
print("\nПроверка похожести гео-страниц (порог < 0.80):")
mx = 0
for i in range(len(geo)):
    for j in range(i + 1, len(geo)):
        r = difflib.SequenceMatcher(None, geo[i][1], geo[j][1]).ratio()
        mx = max(mx, r)
        if r >= 0.80:
            print(f"  ВЫСОКАЯ {r:.2f}: {geo[i][0]} vs {geo[j][0]}")
print(f"  максимум похожести: {mx:.2f}  {'OK' if mx < 0.80 else 'ПРЕВЫШЕНО'}")
