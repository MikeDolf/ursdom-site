#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка раздела доставки в /dostavka/. Изолирован от ursdom.
Зависимости: Python 3 + jinja2. Вывод: статические index.html + sitemap раздела."""
import os, sys, json, difflib
from jinja2 import Environment, FileSystemLoader

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "dostavka")
sys.path.insert(0, os.path.join(HERE, "data"))

from site_config import SITE, ADVANTAGES, GUARANTEES
from products import MATERIALS, EXTRA
from prices import PER_CUBE, PRICE_NOTE, DELIVERY_NOTE, CATALOG
from cities import CITIES, PESOK_CITIES
from longreads import LONGREADS, AUTHOR_FULL, UPDATED

env = Environment(loader=FileSystemLoader(os.path.join(HERE, "templates")),
                  autoescape=False, trim_blocks=False, lstrip_blocks=False)
DOMAIN = SITE["domain"]
TODAY = "2026-07-28"
PER_CUBE_LIST = list(PER_CUBE.items())

# готовые расчёты объёма: помогают заказчику прикинуть кубы до звонка (конверсия)
CALC_ROWS = [
    ("Заезд 3 на 8 м, слой 20 см", "около 6 м³", "Самосвал 5-6,5 м³"),
    ("Площадка под авто 6 на 4 м, слой 20 см", "около 6 м³", "Самосвал 5-6,5 м³"),
    ("Подушка под дом 10 на 10 м, слой 15 см", "около 18 м³", "Полуприцеп или 2 КамАЗа"),
    ("Отсыпка двора 200 м², слой 15 см", "около 36 м³", "2 полуприцепа"),
    ("Дорога 100 м, ширина 3 м, слой 30 см", "около 108 м³", "4-5 полуприцепов"),
]


def ucfirst(t):
    """Заглавная только первая буква. str.capitalize() ломает имена собственных."""
    return t[:1].upper() + t[1:]


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
        "description": SITE["tagline"] + " по " + SITE["region_dat"],
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


def article_schema(url, title, desc, author=None):
    a = author or AUTHOR_FULL
    return {"@type": "Article", "headline": title, "description": desc,
            "inLanguage": "ru-RU", "datePublished": TODAY, "dateModified": TODAY,
            "mainEntityOfPage": DOMAIN + url,
            "author": {"@type": "Person", "name": a["name"], "jobTitle": a["role"]},
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
                extra=EXTRA, cities=CITIES, calc_rows=CALC_ROWS, catalog=CATALOG)

pages = []  # (url, rendered_html, family)

# ---- ХАБ ----
url = SITE["base"]
crumb_items = [("Главная", "/"), ("Доставка материалов", None)]
jl = graph(localbusiness(), bc_schema(crumb_items), faq_schema(MATERIALS["shcheben"]["faq"][:4]))
htmlp = env.get_template("hub.j2").render(
    **BASE_CTX, title="Доставка щебня, песка и нерудных материалов по Екатеринбургу и области",
    desc="Доставка щебня, песка, ПГС и отсева по Екатеринбургу и Свердловской области. Самосвалы от 5 до 20 кубов, оплата после выгрузки, честный объём.",
    canonical=DOMAIN + url, h1="Доставка щебня, песка и нерудных материалов по " + SITE["region_dat"],
    crumbs_html=crumbs(crumb_items), jsonld=jl,
    faq=MATERIALS["shcheben"]["faq"][:4],
    related_links=[("/dostavka/shcheben/", "Доставка щебня: фракции и цены"),
                   ("/dostavka/shcheben/frakciya-20-40/", "Щебень 20-40: характеристики и расчёт"),
                   ("/dostavka/pesok/", "Доставка песка"),
                   ("/dostavka/stati/skolko-shchebnya-v-kamaze/", "Сколько щебня в КамАЗе")])
pages.append((url, htmlp, "hub"))

# ---- MONEY: щебень, песок ----
money_cfg = {
    "shcheben": dict(hero_sub="Гранитный, известняковый, гравийный и вторичный щебень с доставкой по " + SITE["region_dat"] + ". Фракции 5-20, 20-40, 40-70 и отсев, самосвалы от 5 до 20 кубов, оплата после выгрузки.",
                     mat_gen="щебень", mat_acc="доставку щебня", subject="доставка щебня, " + SITE["region_short"],
                     title="Доставка щебня в Екатеринбурге и области: цена за куб, фракции",
                     desc="Доставка щебня по Екатеринбургу и Свердловской области: гранит, известняк, фракции 5-20, 20-40, 40-70. Цена за куб, самосвалы 5-20 кубов, оплата после выгрузки.",
                     h1="Доставка щебня по Екатеринбургу и Свердловской области"),
    "pesok": dict(hero_sub="Карьерный и речной песок с доставкой по " + SITE["region_dat"] + ". Под отсыпку, подушку фундамента, бетон и кладку. Самосвалы от 5 кубов, оплата после выгрузки.",
                  mat_gen="песок", mat_acc="доставку песка", subject="доставка песка, " + SITE["region_short"],
                  title="Доставка песка в Екатеринбурге и области: карьерный, речной",
                  desc="Доставка песка по Екатеринбургу и Свердловской области: карьерный для отсыпки, речной мытый для бетона. Цена за куб, самосвалы от 5 кубов, оплата после выгрузки.",
                  h1="Доставка песка по Екатеринбургу и Свердловской области"),
    "otsev": dict(hero_sub="Гранитный, известняковый и вторичный отсев 0-5 с доставкой по " + SITE["region_dat"] + ". Под тротуарную плитку, расклинцовку и планировку участка.",
                  mat_gen="отсев", mat_acc="доставку отсева", subject="доставка отсева, " + SITE["region_short"],
                  title="Отсев с доставкой в Екатеринбурге: купить щебёночный отсев",
                  desc="Отсев 0-5 с доставкой по Екатеринбургу и Свердловской области: гранитный, известняковый, вторичный. Под плитку и планировку. Цена за куб, оплата после выгрузки.",
                  h1="Отсев с доставкой по Екатеринбургу и Свердловской области"),
    "pgs": dict(hero_sub="Природная ПГС и обогащённая ОПГС с доставкой по " + SITE["region_dat"] + ". Под планировку territории, подсыпку оснований и обратную засыпку.",
                mat_gen="ПГС", mat_acc="доставку ПГС", subject="доставка ПГС, " + SITE["region_short"],
                title="Купить ПГС с доставкой в Екатеринбурге: цена за куб",
                desc="Доставка ПГС и ОПГС по Екатеринбургу и Свердловской области. Песчано-гравийная смесь под отсыпку и планировку. Цена за куб, самосвалы 5-20 кубов, оплата после выгрузки.",
                h1="Доставка ПГС по Екатеринбургу и Свердловской области"),
}
for slug, mc in money_cfg.items():
    mat = MATERIALS[slug]
    url = SITE["base"] + slug + "/"
    crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]), (mat["name"], None)]
    jl = graph(localbusiness(), bc_schema(crumb_items), faq_schema(mat["faq"]))
    if slug == "shcheben":
        rel = [("/dostavka/shcheben/frakciya-20-40/", "Щебень 20-40: характеристики, расчёт, цена"),
               ("/dostavka/shcheben/v-meshkah/", "Щебень в мешках: фасовка и когда это выгодно"),
               ("/dostavka/stati/skolko-shchebnya-v-kamaze/", "Сколько щебня в КамАЗе"),
               ("/dostavka/pesok/", "Доставка песка"),
               ("/dostavka/", "Все города и материалы")]
    elif slug == "otsev":
        rel = [("/dostavka/shcheben/", "Доставка щебня"),
               ("/dostavka/pesok/", "Доставка песка"),
               ("/dostavka/stati/cena-kuba-s-dostavkoy/", "Из чего складывается цена куба"),
               ("/dostavka/", "Все города и материалы")]
    elif slug == "pgs":
        rel = [("/dostavka/pesok/", "Доставка песка"),
               ("/dostavka/shcheben/", "Доставка щебня"),
               ("/dostavka/stati/cena-kuba-s-dostavkoy/", "Из чего складывается цена куба"),
               ("/dostavka/", "Все города и материалы")]
    else:
        rel = [("/dostavka/pesok/bogdanovich/", "Доставка песка в Богданович"),
               ("/dostavka/pesok/irbit/", "Доставка песка в Ирбит"),
               ("/dostavka/shcheben/", "Доставка щебня"),
               ("/dostavka/stati/skolko-shchebnya-nuzhno/", "Сколько нужно и сколько в самосвале"),
               ("/dostavka/", "Все города и материалы")]
    htmlp = env.get_template("money.j2").render(
        **BASE_CTX, **mc, canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items), jsonld=jl,
        intro=mat["intro"], types=mat["types"], fractions=mat.get("fractions"),
        faq=mat["faq"], related_links=rel)
    pages.append((url, htmlp, "money"))


def geo_faq(c, mat_gen="щебня", mat_acc="щебень"):
    """Коммерческий FAQ под интент заказа, с городской конкретикой.
    mat_gen - родительный падеж (доставка щебня), mat_acc - винительный (привезёте щебень)."""
    return [
        (f"Сколько стоит доставка {mat_gen} {c['prep']}?",
         f"Стоимость зависит от материала, объёма и расстояния ({c['dist']}). Назовите фракцию, "
         f"объём и адрес, посчитаем итоговую цену с доставкой и {SITE['callback_promise']}. "
         f"На месте сумма не меняется."),
        (f"За какой срок привезёте {mat_acc} {c['prep']}?",
         f"{c['terms'].split('.')[0]}. Точное окно доставки согласуем при заказе."),
        ("Какой минимальный объём заказа?",
         f"Возим от 5 кубов, дальше объём подбираем под задачу и заезд. {c['min_note']}"),
        ("Нужна ли предоплата?",
         f"Нет. {SITE['payment']} Сначала машина приезжает и выгружается, вы проверяете объём, потом расчёт."),
        ("Как проверить, что привезли полный объём?",
         "Замерьте кузов рулеткой до разгрузки: длина на ширину на высоту борта. "
         "Это паспортный объём машины. При недостаче досыпаем за свой счёт."),
        ("Возможен ли самовывоз?",
         "Да, самовывоз возможен. Если есть свой транспорт, подскажем ближайшую площадку "
         "и актуальную отпускную цену."),
    ]


# ---- ГЕО: щебень × город ----
for c in CITIES:
    url = SITE["base"] + "shcheben/" + c["slug"] + "/"
    crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]),
                   ("Щебень", SITE["base"] + "shcheben/"), (c["name"], None)]
    cfaq = geo_faq(c, "щебня", "щебень")
    jl = graph(localbusiness(), bc_schema(crumb_items), faq_schema(cfaq))
    others = [(f"/dostavka/shcheben/{o['slug']}/", f"Доставка щебня {o['prep']}")
              for o in CITIES if o["slug"] != c["slug"]][:3]
    rel = [("/dostavka/shcheben/", "Доставка щебня: все фракции и цены"),
           ("/dostavka/shcheben/frakciya-20-40/", "Щебень 20-40: расчёт объёма и цена")] + others
    htmlp = env.get_template("geo.j2").render(
        **BASE_CTX, city=c, canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items), jsonld=jl,
        title=f"Доставка щебня {c['prep']}: цена за куб самосвалом",
        desc=f"Доставка щебня {c['prep']} и в район ({c['dist']}). Гранит, известняк, фракции 20-40, 40-70. Цена за куб, оплата после выгрузки.",
        h1=f"Доставка щебня {c['prep']}",
        hero_sub=f"Щебень всех фракций с доставкой {c['prep']} и в район. {ucfirst(c['dist'])}. "
                 f"Самосвалы от 5 до 20 кубов, {SITE['payment_short']}",
        faq=cfaq, related_links=rel[:5])
    pages.append((url, htmlp, "geo"))

# ---- ГЕО: песок × город (ключи Мутагена конк 1) ----
for c in PESOK_CITIES:
    url = SITE["base"] + "pesok/" + c["slug"] + "/"
    crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]),
                   ("Песок", SITE["base"] + "pesok/"), (c["name"], None)]
    cfaq = geo_faq(c, "песка", "песок")
    jl = graph(localbusiness(), bc_schema(crumb_items), faq_schema(cfaq))
    sections = [
        {"id": "plecho", "h": f"Доставка песка {c['prep']}: плечо и цена", "p": [c["block"]]},
        {"id": "kuda", "h": f"Куда возим {c['prep']} и в район", "p": [c["areas"]]},
        {"id": "chto", "h": f"Какой песок берут {c['prep']}", "p": [c["use"]]},
        {"id": "sroki", "h": "Сроки и какая машина приедет", "p": [c["terms"]]},
        {"id": "obekty", "h": f"Типовые объекты {c['prep']}", "p": [c["objects"]]},
        {"id": "kak-zakazat", "h": f"Как заказать песок {c['prep']}",
         "steps": ["Скажите вид песка (карьерный или речной мытый) и объём в кубах.",
                   f"Назовите адрес {c['prep']} и опишите заезд: ширина ворот и место для разворота.",
                   f"Получите точную цену с доставкой. {SITE['callback_promise'].capitalize()}.",
                   f"Принимаете машину на объекте и проверяете объём. {SITE['payment']}"]},
    ]
    htmlp = env.get_template("geoplus.j2").render(
        **BASE_CTX, place=c, canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items), jsonld=jl,
        title=f"Доставка песка {c['prep']}: цена за куб, карьерный и речной",
        desc=f"Доставка песка {c['prep']} и в район ({c['dist']}). Карьерный под отсыпку, речной мытый под бетон. Цена за куб, оплата после выгрузки.",
        h1=f"Доставка песка {c['prep']}",
        hero_sub=f"Карьерный и речной песок с доставкой {c['prep']} и в район. {ucfirst(c['dist'])}. "
                 f"Самосвалы от 5 кубов, {SITE['payment_short']}",
        lead=f"Возим песок {c['prep']} и по району, {c['dist']}. Карьерный идёт под отсыпку и "
             f"обратную засыпку, речной мытый под бетон и кладку. Цену считаем за кубометр "
             f"с доставкой на ваш адрес, {SITE['payment_short']}",
        sections=sections, cta_after=3,
        cta_head=f"Посчитаем объём песка {c['prep']}",
        cta_text="Назовите размеры участка работ и адрес, подберём вид песка и машину, "
                 "назовём итоговую цену с доставкой.",
        subject=f"песок, {c['name']}", faq=cfaq,
        related_links=[("/dostavka/pesok/", "Доставка песка: виды и цены"),
                       (f"/dostavka/shcheben/{c['slug']}/", f"Доставка щебня {c['prep']}"),
                       ("/dostavka/stati/skolko-shchebnya-v-kamaze/", "Сколько кубов в самосвале"),
                       ("/dostavka/", "Все города и материалы")])
    pages.append((url, htmlp, "geo-pesok"))

# ---- ЛОНГРИДЫ (низкоконкурентные ключи Мутагена) ----
for a in LONGREADS:
    url = SITE["base"] + a["slug"] + "/"
    parent = ("Щебень", SITE["base"] + "shcheben/") if a["slug"].startswith("shcheben/") \
        else ("Статьи", None)
    crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]), parent,
                   (a["h1"], None)]
    nodes = [localbusiness(), bc_schema(crumb_items), faq_schema(a["faq"])]
    if a["kind"] == "article":
        nodes.append(article_schema(url, a["title"], a["desc"], AUTHOR_FULL))
    jl = graph(*nodes)
    rel = [("/dostavka/shcheben/", "Доставка щебня: все фракции и цены"),
           ("/dostavka/", "Все города и материалы")]
    for other in LONGREADS:
        if other["slug"] != a["slug"]:
            rel.append((SITE["base"] + other["slug"] + "/", other["h1"]))
    htmlp = env.get_template("longread.j2").render(
        **BASE_CTX, author=AUTHOR_FULL, updated=UPDATED,
        canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items), jsonld=jl,
        title=a["title"], desc=a["desc"], h1=a["h1"], hero_sub=a["hero_sub"], lead=a["lead"],
        sections=a["sections"], faq=a["faq"], subject=a["subject"], form_head=a["form_head"],
        cta_after=a["cta_after"], cta_head=a["cta_head"], cta_text=a["cta_text"],
        related_links=rel[:5])
    pages.append((url, htmlp, "longread"))

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

# список URL для переобхода в Яндекс.Вебмастере. Кладём в audit/ (закрыт в robots.txt),
# чтобы служебный файл не попал в индекс вместе со страницами раздела.
AUDIT = os.path.join(ROOT, "audit")
os.makedirs(AUDIT, exist_ok=True)
with open(os.path.join(AUDIT, "dostavka-urls.txt"), "w", encoding="utf-8") as fh:
    for url, h, fam in pages:
        fh.write(DOMAIN + url + "\n")

print(f"Собрано страниц: {len(pages)}")
for p, url, fam in written:
    print(f"  [{fam:10}] {url}")


# ---- ПРОВЕРКА ДУБЛЕЙ (anti-doorway, ratio < 0.80) ----
def visible(hs):
    import re
    hs = re.sub(r"<script.*?</script>", " ", hs, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", hs)).strip()


for fam in ("geo", "geo-pesok"):
    grp = [(u, visible(h)) for u, h, f in pages if f == fam]
    if len(grp) < 2:
        continue
    print(f"\nПохожесть страниц [{fam}] (порог < 0.80):")
    mx, worst = 0, None
    for i in range(len(grp)):
        for j in range(i + 1, len(grp)):
            r = difflib.SequenceMatcher(None, grp[i][1], grp[j][1]).ratio()
            if r > mx:
                mx, worst = r, (grp[i][0], grp[j][0])
            if r >= 0.80:
                print(f"  ВЫСОКАЯ {r:.2f}: {grp[i][0]} vs {grp[j][0]}")
    print(f"  максимум {mx:.2f} ({worst[0]} vs {worst[1]})  {'OK' if mx < 0.80 else 'ПРЕВЫШЕНО'}")

wc = [(u, len(visible(h).split())) for u, h, f in pages]
print("\nОбъём текста (слов):")
for u, n in sorted(wc, key=lambda x: -x[1]):
    print(f"  {n:5}  {u}")
