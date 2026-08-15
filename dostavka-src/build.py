#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка раздела доставки в /dostavka/. Изолирован от ursdom.
Зависимости: Python 3 + jinja2. Вывод: статические index.html + sitemap раздела."""
import os, sys, json, difflib
from PIL import Image
from jinja2 import Environment, FileSystemLoader

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "dostavka")
sys.path.insert(0, os.path.join(HERE, "data"))

from site_config import SITE, ADVANTAGES, GUARANTEES
from products import MATERIALS, EXTRA
from products_ext import MATERIALS_EXT, MONEY_CFG_EXT
from geo_matrix import (CITY_FACTS, MATRIX, ALREADY, MAT_FORMS,
                        ANGLE, LOCAL, MAT_TASK, example_for, plecho)
from prices import PER_CUBE, PRICE_NOTE, DELIVERY_NOTE, CATALOG, SIEVE, HERO_CELL, HERO_FRAC
from cities import CITIES, PESOK_CITIES
from longreads import LONGREADS, AUTHOR_FULL, UPDATED
from longreads_core import CORE_LONGREADS
LONGREADS = LONGREADS + CORE_LONGREADS
from legal import legal_sections, LEGAL_UPDATED

env = Environment(loader=FileSystemLoader(os.path.join(HERE, "templates")),
                  autoescape=False, trim_blocks=False, lstrip_blocks=False)

# Версия CSS считается из содержимого файла. Раньше она была константой в конфиге,
# и после правок стилей вернувшийся посетитель получал старый файл из кеша.
_css = os.path.join(OUT, "assets", "dostavka.css")
if os.path.exists(_css):
    import hashlib
    SITE["css_version"] = hashlib.md5(open(_css, "rb").read()).hexdigest()[:8]
DOMAIN = SITE["domain"]
TODAY = "2026-07-28"
PER_CUBE_LIST = list(PER_CUBE.items())

# готовые расчёты объёма: помогают заказчику прикинуть кубы до заявки (конверсия)
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
        "email": SITE["email"],
        "areaServed": SITE["region"],
        "openingHours": "Mo-Sa 08:00-20:00",
        "priceRange": "₽₽",
        "currenciesAccepted": "RUB",
        "paymentAccepted": "Наличные, банковская карта, безналичный перевод",
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


def product_schema(name, desc, low_price, url, images=None):
    """Product + AggregateOffer с честной ценой 'от N'. lowPrice отражает
    минимальную цену за куб по прайсу, поэтому разметка не расходится со страницей."""
    return {
        "@type": "Product",
        "name": name,
        "description": desc,
        "category": "Нерудные строительные материалы",
        "url": DOMAIN + url,
        **({"image": [DOMAIN + i for i in images]} if images else {}),
        "brand": {"@type": "Brand", "name": SITE["brand"]},
        "offers": {
            "@type": "AggregateOffer",
            "lowPrice": low_price,
            "priceCurrency": "RUB",
            "availability": "https://schema.org/InStock",
            "unitText": "кубометр",
            "areaServed": SITE["region"],
            "seller": {"@id": DOMAIN + SITE["base"] + "#business"},
        },
    }


def graph(*nodes):
    return json.dumps({"@context": "https://schema.org", "@graph": list(nodes)},
                      ensure_ascii=False, indent=2)


def write(url, html_str):
    path = os.path.join(OUT, url[len(SITE["base"]):].strip("/"), "index.html") \
        if url != SITE["base"] else os.path.join(OUT, "index.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(html_str)
    return path



# ---- ФОТОГРАФИИ МАТЕРИАЛОВ ----
# Alt и подпись пишутся под конкретный кадр. Шаблонный alt вида
# "щебень фото" не помогает ни скринридеру, ни поиску по картинкам.
PHOTOS = {
    "shcheben": [
        ("granit-5-20-tape.jpg",
         "Гранитный щебень фракции 5-20 мм, рядом рулетка с делениями до 50 см",
         "Гранитный щебень 5-20 на площадке. Рулетка рядом показывает реальный "
         "размер зерна: основная масса проходит между 5 и 20 миллиметрами."),
        ("granit-20-40-macro.jpg",
         "Крупный план гранитного щебня 20-40 мм с монетой 10 рублей для масштаба",
         "Гранит 20-40 крупным планом. Видны свежие сколы и розовые вкрапления "
         "полевого шпата, характерные для уральского гранита. Монета для масштаба."),
        ("granit-40-70-hand.jpg",
         "Крупные куски гранитного щебня 40-70 мм в руке в рабочей перчатке",
         "Фракция 40-70 в ладони: такой камень идёт в основание дороги и в отсыпку "
         "слабых грунтов, где нужен объём и несущая способность."),
        ("izvestnyak-20-40.jpg",
         "Известняковый щебень 20-40 мм светло-серого и жёлтого цвета",
         "Известняковый щебень 20-40. Светлее гранита, поверхность матовая без "
         "блеска. Дешевле, но мягче: под нагрузку и в воду его не берут."),
        ("graviyniy-20-40.jpg",
         "Гравийный щебень 20-40 мм с частично окатанным зерном",
         "Гравийный щебень 20-40. Зерно частично окатанное, частично колотое: "
         "это дроблёный гравий, промежуточный вариант между гравием и гранитом."),
        ("vtorichniy-boy-betona.jpg",
         "Вторичный щебень из дроблёного бетона с торчащим куском ржавой арматуры",
         "Вторичный щебень из бетонного боя. На переднем плане видна арматурная "
         "проволока: под чистовые работы и в дренаж такой материал не годится, "
         "его место в черновой отсыпке."),
    ],
}


def photos_for(slug):
    out = []
    for f, a, c in PHOTOS.get(slug, []):
        path = os.path.join(OUT, "assets", "img", slug, f)
        with Image.open(path) as im:
            w, h = im.size
        out.append(dict(src="/dostavka/assets/img/" + slug + "/" + f,
                        alt=a, cap=c, w=w, h=h))
    return out


BASE_CTX = dict(cfg=SITE, advantages=ADVANTAGES, guarantees=GUARANTEES,
                per_cube=PER_CUBE_LIST, price_note=PRICE_NOTE, delivery_note=DELIVERY_NOTE,
                extra=EXTRA, calc_rows=CALC_ROWS, catalog=CATALOG, sieve=SIEVE,
                cities=[dict(slug=cs, prep=CITY_FACTS[cs]["prep"],
                             loc=CITY_FACTS[cs]["loc"],
                             name=CITY_FACTS[cs]["name"],
                             km=CITY_FACTS[cs]["km"],
                             mats=", ".join(MAT_FORMS[m]["vin"] for m in ms))
                        for cs, ms in sorted(MATRIX.items(),
                                             key=lambda i: CITY_FACTS[i[0]]["km"])]
                       + [dict(slug="sredneuralsk", prep="в Среднеуральск",
                               loc="в Среднеуральске", name="Среднеуральск", km=25,
                               mats="щебень")],
                more_materials=[(("/dostavka/" + k + "/"), v["name"])
                                for k, v in MATERIALS_EXT.items()])

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
                   ("/dostavka/stati/chem-otsypat-uchastok/", "Чем отсыпать участок"),
                   ("/dostavka/stati/dostavka-na-dachu/", "Доставка на дачу и в СНТ")])
pages.append((url, htmlp, "hub"))

# ---- MONEY: щебень, песок ----
money_cfg = {
    "shcheben": dict(hero_sub="Гранитный, известняковый, гравийный и вторичный щебень с доставкой по " + SITE["region_dat"] + ". Фракции 5-20, 20-40, 40-70 и отсев, самосвалы от 5 до 20 кубов, оплата после выгрузки.",
                     mat_vin="щебень", mat_rod="щебня", mat_order="доставку щебня", subject="доставка щебня, " + SITE["region_short"],
                     title="Доставка щебня в Екатеринбурге и области: цена за куб, фракции",
                     desc="Доставка щебня по Екатеринбургу и Свердловской области: гранит, известняк, фракции 5-20, 20-40, 40-70. Цена за куб, самосвалы 5-20 кубов, оплата после выгрузки.",
                     h1="Доставка щебня по Екатеринбургу и Свердловской области"),
    "pesok": dict(hero_sub="Карьерный и речной песок с доставкой по " + SITE["region_dat"] + ". Под отсыпку, подушку фундамента, бетон и кладку. Самосвалы от 5 кубов, оплата после выгрузки.",
                  mat_vin="песок", mat_rod="песка", mat_order="доставку песка", subject="доставка песка, " + SITE["region_short"],
                  title="Доставка песка в Екатеринбурге и области: карьерный, речной",
                  desc="Доставка песка по Екатеринбургу и Свердловской области: карьерный для отсыпки, речной мытый для бетона. Цена за куб, самосвалы от 5 кубов, оплата после выгрузки.",
                  h1="Доставка песка по Екатеринбургу и Свердловской области"),
    "otsev": dict(hero_sub="Гранитный, известняковый и вторичный отсев 0-5 с доставкой по " + SITE["region_dat"] + ". Под тротуарную плитку, расклинцовку и планировку участка.",
                  mat_vin="отсев", mat_rod="отсева", mat_order="доставку отсева", subject="доставка отсева, " + SITE["region_short"],
                  title="Отсев с доставкой в Екатеринбурге: купить щебёночный отсев",
                  desc="Отсев 0-5 с доставкой по Екатеринбургу и Свердловской области: гранитный, известняковый, вторичный. Под плитку и планировку. Цена за куб, оплата после выгрузки.",
                  h1="Отсев с доставкой по Екатеринбургу и Свердловской области"),
    "pgs": dict(hero_sub="Природная ПГС и обогащённая ОПГС с доставкой по " + SITE["region_dat"] + ". Под планировку территории, подсыпку оснований и обратную засыпку.",
                mat_vin="ПГС", mat_rod="ПГС", mat_order="доставку ПГС", subject="доставка ПГС, " + SITE["region_short"],
                title="Купить ПГС с доставкой в Екатеринбурге: цена за куб",
                desc="Доставка ПГС и ОПГС по Екатеринбургу и Свердловской области. Песчано-гравийная смесь под отсыпку и планировку. Цена за куб, самосвалы 5-20 кубов, оплата после выгрузки.",
                h1="Доставка ПГС по Екатеринбургу и Свердловской области"),
}
# Городские страницы песка стоят отдельно от таблицы городов на хабе,
# поэтому ссылки на них проставляем явно: без этого они остаются сиротами
# (поймано проверкой 20 в audit/_verify.py).
PESOK_GEO = [("/dostavka/pesok/bogdanovich/", "Доставка песка в Богданович"),
             ("/dostavka/pesok/irbit/", "Доставка песка в Ирбит"),
             ("/dostavka/pesok/nevyansk/", "Доставка песка в Невьянск")]
SREDNEURALSK = [("/dostavka/shcheben/sredneuralsk/", "Доставка щебня в Среднеуральск")]

MAT_ART = {'shcheben': [('/dostavka/stati/frakcii-shchebnya/', 'Фракции щебня: какая под какую задачу'), ('/dostavka/stati/gost-na-shcheben-i-pesok/', 'ГОСТ на щебень и песок: что спрашивать')],
    'pesok': [('/dostavka/stati/modul-krupnosti-peska/', 'Модуль крупности песка'), ('/dostavka/stati/gost-na-shcheben-i-pesok/', 'ГОСТ на щебень и песок: что спрашивать')],
    'otsev': [('/dostavka/stati/otsev-gde-primenyat/', 'Отсев 0-5: где применяют и чем заменить'), ('/dostavka/stati/frakcii-shchebnya/', 'Фракции щебня: какая под какую задачу')],
    'pgs': [('/dostavka/stati/pgs-ili-opgs/', 'ПГС и ОПГС: чем отличаются'), ('/dostavka/stati/skalnyy-grunt-dresva-but/', 'Скальный грунт, дресва и бут')],
    'keramzit': [('/dostavka/stati/keramzit-frakcii-i-ves/', 'Керамзит: фракции, вес и где выгоден')],
    'skalnyy-grunt': [('/dostavka/stati/skalnyy-grunt-dresva-but/', 'Скальный грунт, дресва и бут'), ('/dostavka/stati/pgs-ili-opgs/', 'ПГС и ОПГС: чем отличаются')],
    'butovyy-kamen': [('/dostavka/stati/skalnyy-grunt-dresva-but/', 'Скальный грунт, дресва и бут')],
    'graviy': [('/dostavka/stati/frakcii-shchebnya/', 'Фракции щебня: какая под какую задачу')],
    'shchps': [('/dostavka/stati/pgs-ili-opgs/', 'ПГС и ОПГС: чем отличаются')],
    'granitnaya-kroshka': [('/dostavka/stati/otsev-gde-primenyat/', 'Отсев 0-5: где применяют')],
    'asfaltovaya-kroshka': [('/dostavka/stati/skalnyy-grunt-dresva-but/', 'Чем отсыпать дёшево')]}

MONEY_LOW_PRICE = {"shcheben": "600", "pesok": "350", "otsev": "500", "pgs": "500"}

for slug, mc in money_cfg.items():
    mat = MATERIALS[slug]
    url = SITE["base"] + slug + "/"
    crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]), (mat["name"], None)]
    _ph = photos_for(slug)
    jl = graph(localbusiness(), bc_schema(crumb_items), faq_schema(mat["faq"]),
               product_schema(mat["name"], mc["desc"], MONEY_LOW_PRICE[slug], url,
                              images=[x["src"] for x in _ph]))
    if slug == "shcheben":
        rel = [("/dostavka/shcheben/frakciya-20-40/", "Щебень 20-40: характеристики, расчёт, цена"),
               ("/dostavka/shcheben/v-meshkah/", "Щебень в мешках: фасовка и когда это выгодно"),
               ("/dostavka/stati/skolko-shchebnya-v-kamaze/", "Сколько щебня в КамАЗе"),
               ("/dostavka/stati/shcheben-ili-graviy/", "Чем отличается щебень от гравия"),
               ("/dostavka/stati/skolko-vesit-kub/", "Сколько весит куб щебня и песка"),
               ("/dostavka/stati/koefficient-uplotneniya/", "Коэффициент уплотнения: сколько заказывать"),
               ("/dostavka/pesok/", "Доставка песка"),
               ("/dostavka/", "Все города и материалы")]
    elif slug == "otsev":
        rel = [("/dostavka/shcheben/", "Доставка щебня"),
               ("/dostavka/pesok/", "Доставка песка"),
               ("/dostavka/stati/chem-otsypat-uchastok/", "Чем отсыпать участок"),
               ("/dostavka/stati/koefficient-uplotneniya/", "Коэффициент уплотнения: сколько заказывать"),
               ("/dostavka/stati/skolko-vesit-kub/", "Сколько весит куб отсева и щебня"),
               ("/dostavka/stati/cena-kuba-s-dostavkoy/", "Из чего складывается цена куба"),
               ("/dostavka/", "Все города и материалы")]
    elif slug == "pgs":
        rel = [("/dostavka/pesok/", "Доставка песка"),
               ("/dostavka/shcheben/", "Доставка щебня"),
               ("/dostavka/stati/chem-otsypat-uchastok/", "Чем отсыпать участок"),
               ("/dostavka/stati/shcheben-ili-graviy/", "Чем отличается щебень от гравия"),
               ("/dostavka/stati/koefficient-uplotneniya/", "Коэффициент уплотнения ПГС"),
               ("/dostavka/stati/cena-kuba-s-dostavkoy/", "Из чего складывается цена куба"),
               ("/dostavka/", "Все города и материалы")]
    else:
        rel = [("/dostavka/pesok/karyernyy/", "Карьерный песок: виды и цена"),
               ("/dostavka/pesok/rechnoy/", "Речной мытый песок"),
               ("/dostavka/stati/kakoy-pesok-vybrat/", "Какой песок выбрать под задачу"),
               ("/dostavka/stati/skolko-shchebnya-i-peska-na-kub-betona/", "Сколько песка и щебня на куб бетона"),
               ("/dostavka/stati/skolko-vesit-kub/", "Сколько весит куб песка"),
               ("/dostavka/pesok/bogdanovich/", "Доставка песка в Богданович"),
               ("/dostavka/pesok/irbit/", "Доставка песка в Ирбит")]
    rel = MAT_ART.get(slug, []) + (PESOK_GEO if slug == "pesok" else []) + (SREDNEURALSK if slug == "shcheben" else []) + rel
    htmlp = env.get_template("money.j2").render(
        **BASE_CTX, **mc, canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items), jsonld=jl,
        intro=mat["intro"], types=mat["types"], fractions=mat.get("fractions"),
        faq=mat["faq"], photos=_ph, hero_cell=HERO_CELL.get(slug, 34),
        hero_frac=HERO_FRAC.get(slug, "щебень 20-40 мм"),
        related_links=list(dict.fromkeys(rel + [(f"/dostavka/shcheben/{o['slug']}/", f"Доставка щебня {o['prep']}") for o in CITIES[:6]]))[:14])
    pages.append((url, htmlp, "money"))


def geo_faq(c, mat_rod="щебня", mat_vin="щебень"):
    """Коммерческий FAQ под интент заказа, с городской конкретикой.
    mat_rod - родительный (доставка щебня), mat_vin - винительный (привезёте щебень)."""
    return [
        (f"Сколько стоит доставка {mat_rod} {c['prep']}?",
         f"Стоимость зависит от материала, объёма и расстояния ({c['dist']}). Назовите фракцию, "
         f"объём и адрес, посчитаем итоговую цену с доставкой и {SITE['callback_promise']}. "
         f"На месте сумма не меняется."),
        (f"За какой срок привезёте {mat_vin} {c['prep']}?",
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
    # соседние города берём со сдвигом от текущего, чтобы вес не оседал на первых по списку
    idx = [i for i, o in enumerate(CITIES) if o["slug"] == c["slug"]][0]
    ring = CITIES[idx + 1:] + CITIES[:idx]
    others = [(f"/dostavka/shcheben/{o['slug']}/", f"Доставка щебня {o['prep']}")
              for o in ring][:6]
    rel = [("/dostavka/shcheben/", "Доставка щебня: все фракции и цены"),
           ("/dostavka/shcheben/frakciya-20-40/", "Щебень 20-40: расчёт объёма и цена"),
           ("/dostavka/shcheben/frakciya-5-20/", "Щебень 5-20: под бетон и дорожки"),
           ("/dostavka/pesok/", "Доставка песка"),
           ("/dostavka/otsev/", "Отсев 0-5"),
           ("/dostavka/stati/cena-kuba-s-dostavkoy/", "Цена за куб с доставкой")] + others
    htmlp = env.get_template("geo.j2").render(
        **BASE_CTX, city=c, canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items), jsonld=jl,
        title=f"Доставка щебня {c['prep']}: цена за куб самосвалом",
        desc=f"Доставка щебня {c['prep']} и в район ({c['dist']}). Гранит, известняк, фракции 20-40, 40-70. Цена за куб, оплата после выгрузки.",
        h1=f"Доставка щебня {c['prep']}",
        hero_sub=f"Щебень всех фракций с доставкой {c['prep']} и в район. {ucfirst(c['dist'])}. "
                 f"Самосвалы от 5 до 20 кубов, {SITE['payment_short']}",
        faq=cfaq, related_links=rel[:12])
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
        {"id": "chto", "h": f"Какой песок берут {c['loc']}", "p": [c["use"]]},
        {"id": "sroki", "h": "Сроки и какая машина приедет", "p": [c["terms"]]},
        {"id": "obekty", "h": f"Типовые объекты {c['loc']}", "p": [c["objects"]]},
        {"id": "kak-zakazat", "h": f"Как заказать песок {c['prep']}",
         "steps": ["Скажите вид песка (карьерный или речной мытый) и объём в кубах.",
                   f"Назовите адрес {c['loc']} и опишите заезд: ширина ворот и место для разворота.",
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
        cta_head=f"Посчитаем объём песка {c['loc']}",
        cta_text="Назовите размеры участка работ и адрес, подберём вид песка и машину, "
                 "назовём итоговую цену с доставкой.",
        subject=f"песок, {c['name']}", faq=cfaq,
        related_links=[x for x in PESOK_GEO if x[0] != url] +
                      SREDNEURALSK +
                      [("/dostavka/pesok/", "Доставка песка: виды и цены"),
                       ("/dostavka/pesok/karyernyy/", "Карьерный песок"),
                       ("/dostavka/pesok/rechnoy/", "Речной мытый песок"),
                       ("/dostavka/shcheben/", "Доставка щебня"),
                       ("/dostavka/otsev/", "Отсев 0-5"),
                       ("/dostavka/pgs/", "ПГС и ОПГС"),
                       ("/dostavka/stati/cena-kuba-s-dostavkoy/", "Цена за куб с доставкой"),
                       ("/dostavka/stati/skolko-shchebnya-v-kamaze/", "КамАЗ: цена за машину"),
                       ("/dostavka/", "Все города и материалы")]
                      + [(f"/dostavka/shcheben/{o['slug']}/", f"Доставка щебня {o['prep']}")
                         for o in CITIES[:3]])
    pages.append((url, htmlp, "geo-pesok"))

# ---- ЛОНГРИДЫ (низкоконкурентные ключи Мутагена) ----
for a in LONGREADS:
    url = SITE["base"] + a["slug"] + "/"
    if a["slug"].startswith("shcheben/"):
        parent = ("Щебень", SITE["base"] + "shcheben/")
    elif a["slug"].startswith("pesok/"):
        parent = ("Песок", SITE["base"] + "pesok/")
    else:
        parent = ("Статьи", None)
    crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]), parent,
                   (a["h1"], None)]
    nodes = [localbusiness(), bc_schema(crumb_items), faq_schema(a["faq"])]
    if a["kind"] == "article":
        nodes.append(article_schema(url, a["title"], a["desc"], AUTHOR_FULL))
    if a.get("low_price"):
        nodes.append(product_schema(a["h1"], a["desc"], a["low_price"], url))
    jl = graph(*nodes)
    # Сначала явно заданные связи, потом остальные лонгриды.
    # Без этого rel[:12] отрезал всё, что не поместилось: список
    # вырос до 23 статей, и новые становились сиротами - на них
    # не вело ни одной ссылки со всего сайта.
    by_slug = {o["slug"]: o for o in LONGREADS}
    rel = []
    for sl in a.get("related", []):
        o = by_slug.get(sl)
        if o:
            rel.append((SITE["base"] + sl + "/", o["h1"]))
    rel += [("/dostavka/shcheben/", "Доставка щебня: все фракции и цены"),
            ("/dostavka/pesok/", "Доставка песка"),
            ("/dostavka/otsev/", "Отсев 0-5"),
            ("/dostavka/pgs/", "ПГС и ОПГС"),
            ("/dostavka/", "Все города и материалы")]
    # Запасной список крутится от текущей статьи, а не от начала.
    # Иначе ссылки достаются первым девяти по порядку объявления,
    # а всё, что добавлено позже, не получает ни одной входящей.
    i0 = next(i for i, o in enumerate(LONGREADS) if o["slug"] == a["slug"])
    ordered = LONGREADS[i0 + 1:] + LONGREADS[:i0]
    for other in ordered:
        rel.append((SITE["base"] + other["slug"] + "/", other["h1"]))
    rel += [(f"/dostavka/shcheben/{o['slug']}/", f"Доставка щебня {o['prep']}")
            for o in CITIES[:4]]
    htmlp = env.get_template("longread.j2").render(
        **BASE_CTX, author=AUTHOR_FULL, updated=UPDATED,
        canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items), jsonld=jl,
        title=a["title"], desc=a["desc"], h1=a["h1"], hero_sub=a["hero_sub"], lead=a["lead"],
        sections=a["sections"], faq=a["faq"], subject=a["subject"], form_head=a["form_head"],
        cta_after=a["cta_after"], cta_head=a["cta_head"], cta_text=a["cta_text"],
        cta_head2=a.get("cta_head2"), cta_text2=a.get("cta_text2"),
        commercial=a.get("commercial", False),
        price_head=a.get("price_head", ""), order_head=a.get("order_head", ""),
        related_links=list(dict.fromkeys(rel))[:14])
    pages.append((url, htmlp, "longread"))

# ---- НОВЫЕ ТОВАРНЫЕ СТРАНИЦЫ (керамзит, гравий, крошка, скала, ЩПС, бут) ----
for slug, mc in MONEY_CFG_EXT.items():
    mat = MATERIALS_EXT[slug]
    url = SITE["base"] + slug + "/"
    crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]),
                   (mat["name"], None)]
    jl = graph(localbusiness(), bc_schema(crumb_items), faq_schema(mat["faq"]),
               product_schema(mat["name"], mc["desc"], mc["low"], url))
    rel = [("/dostavka/shcheben/", "Доставка щебня"),
           ("/dostavka/pesok/", "Доставка песка"),
           ("/dostavka/otsev/", "Отсев 0-5"),
           ("/dostavka/pgs/", "ПГС и ОПГС"),
           ("/dostavka/stati/skolko-vesit-kub/", "Сколько весит куб материала"),
           ("/dostavka/stati/koefficient-uplotneniya/", "Коэффициент уплотнения"),
           ("/dostavka/", "Все города и материалы")]
    rel += [("/dostavka/" + o + "/", MATERIALS_EXT[o]["name"] + " с доставкой")
            for o in MONEY_CFG_EXT if o != slug]
    rel = MAT_ART.get(slug, []) + (PESOK_GEO if slug == "pesok" else []) + (SREDNEURALSK if slug == "shcheben" else []) + rel
    htmlp = env.get_template("money.j2").render(
        **BASE_CTX, canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items),
        jsonld=jl, title=mc["title"], desc=mc["desc"], h1=mc["h1"],
        hero_sub=mc["hero_sub"], mat_vin=mc["mat_vin"], mat_rod=mc["mat_rod"],
        mat_order=mc["mat_order"], subject=mc["mat_vin"] + ", " + SITE["region_short"],
        intro=mat["intro"], types=mat["types"], fractions=mat.get("fractions"),
        faq=mat["faq"], related_links=list(dict.fromkeys(rel))[:14], hero_cell=HERO_CELL.get(slug, 34),
        hero_frac=HERO_FRAC.get(slug, "щебень 20-40 мм"))
    pages.append((url, htmlp, "money-ext"))

# ---- ГОРОДСКИЕ СТРАНИЦЫ: ОДИН ГОРОД = ОДНА СТРАНИЦА ----
# Первая попытка была делать отдельную страницу на каждую пару город-материал.
# Проверка похожести это забраковала: "песок в Нижнем Тагиле" и "керамзит
# в Нижнем Тагиле" совпадали на 89 процентов, потому что вся городская часть
# у них общая, а различается только название материала. Это дорвейность
# в чистом виде, и под фильтр уехал бы весь раздел.
# Поэтому город получает одну страницу, а материалы идут на ней секциями
# со своими заголовками, ценой и расчётом. Запрос "керамзит Реж" эта
# страница закрывает разделом, а не отдельным адресом.
GEO_FRACTIONS = {
    "shcheben": [("5-20 мм", "Бетон, дорожки, отмостка, тонкие слои"),
                 ("20-40 мм", "Фундамент, заезд, площадка, дренаж"),
                 ("40-70 мм", "Основание дороги, отсыпка слабых грунтов"),
                 ("Отсев 0-5", "Расклинцовка верха и подсыпка под плитку")],
    "pesok": [("Карьерный сеяный", "Отсыпка, обратная засыпка, подушка фундамента"),
              ("Речной мытый", "Бетон, кладочные и штукатурные растворы")],
    "otsev": [("0-5 гранитный", "Основание под тротуарную плитку"),
              ("0-10", "Расклинцовка щебня 20-40 и 40-70")],
    "keramzit": [("10-20 мм", "Утепление пола по грунту и между лагами"),
                 ("20-40 мм", "Утепление кровли, засыпка больших пустот")],
    "graviy": [("20-40 мм", "Дренаж вокруг дома, засыпка, подъём уровня"),
               ("40-120 мм", "Галька: ландшафт и сухие ручьи")],
    "pgs": [("Природная ПГС", "Планировка территории и черновая отсыпка"),
            ("Обогащённая ОПГС", "Основания под нагрузку")],
}


def geo_city_faq(facts, mats, pl, dist):
    """FAQ городской страницы. Падежи материалов подставляются явно:
    ровно на этом месте раньше вылезали 'привезёте щебня' и 'виды щебень'."""
    first = MAT_FORMS[mats[0]]
    q = [
        (f"Сколько стоит доставка {facts['prep']}?",
         f"Цена складывается из стоимости материала за куб и доставки на плечо "
         f"{dist}. Назовите материал, объём и адрес, посчитаем итог и "
         f"{SITE['callback_promise']}. На месте сумма не меняется."),
        (f"Какие материалы возите {facts['prep']}?",
         "Возим " + ", ".join(MAT_FORMS[m]["vin"] for m in mats) +
         ". Всё это можно взять одной заявкой: расчёт общий, "
         "рейсы планируем на один день."),
        (f"За какой срок привезёте {first['vin']} {facts['prep']}?",
         f"Рейс {pl['term']}. Точное окно доставки согласуем при заказе "
         f"и предупреждаем о выезде машины."),
        ("Какой минимальный объём заказа?",
         f"Возим от 5 кубов. {pl['minv']}"),
        ("Нужна ли предоплата?",
         f"Нет. {SITE['payment']} Сначала машина приезжает и выгружается, "
         f"вы проверяете объём, потом расчёт."),
        ("Как проверить объём при приёмке?",
         "Замерьте кузов рулеткой до разгрузки: длина на ширину на высоту борта. "
         "Паспортный объём кузова водитель называет по документам на машину. "
         "Мы разгружаем при заказчике, чтобы это можно было сделать сразу."),
        (f"Куда именно возите {facts['prep']} и в округ?",
         f"{facts['areas'][0].upper()}{facts['areas'][1:]}. По адресам за городом "
         f"уточняйте состояние подъезда: гружёный самосвал проходит не везде."),
    ]
    if facts.get("note"):
        q.insert(1, (f"Есть ли особенности с доставкой {facts['prep']}?",
                     facts["note"]))
    return q


OLD_CITY = {c["slug"]: c for c in CITIES}

for city_slug, mats in MATRIX.items():
    facts = CITY_FACTS[city_slug]
    pl = plecho(facts["km"])
    dist = f"около {facts['km']} км от Екатеринбурга"
    url = f"{SITE['base']}shcheben/{city_slug}/"
    old = OLD_CITY.get(city_slug)

    mat_blocks = []
    for mkey in mats:
        mat = MAT_FORMS[mkey]
        mat_blocks.append(dict(
            key=mkey, name=mat["name"], vin=mat["vin"], rod=mat["rod"],
            url="/dostavka/" + mat["url"] + "/",
            task=MAT_TASK.get((mkey, facts["kind"]), MAT_TASK[(mkey, "small")]),
            ex=example_for(mkey, city_slug, facts["km"]),
            fractions=GEO_FRACTIONS.get(mkey),
            price=next((p for n, p in PER_CUBE.items()
                        if n.lower().startswith(mat["vin"][:5].lower())), mat["low"]),
        ))

    names = [MAT_FORMS[m]["vin"] for m in mats]
    # Порядок материалов в заголовке: щебень первым всегда, дальше по спросу.
    head = ["shcheben"] + [m for m in mats if m != "shcheben"]
    m1, m2 = MAT_FORMS[head[0]], MAT_FORMS[head[1]] if len(head) > 1 else None
    pair = m1["name"] + (" и " + m2["vin"] if m2 else "")
    h1 = f"{pair} {facts['loc']} с доставкой"
    title = f"{m1['name']} {facts['loc']}: доставка, цена за куб"
    if len(title) > 70:
        title = f"{m1['name']} {facts['loc']}: цена за куб"
    desc = (f"Доставка {facts['prep']} и по округу: " + ", ".join(names) +
            f". Плечо {dist}, самосвалы от 5 до 20 кубов, оплата после "
            f"выгрузки. Цену с доставкой называем по заявке.")[:200]
    hero = (f"Везём " + ", ".join(names) + f" {facts['prep']} самосвалами "
            f"от 5 до 20 кубов. Плечо {pl['tier']}, {dist}: {pl['term']}. "
            f"Оплата после выгрузки, объём проверяете при приёмке.")

    if old:
        p_plecho, p_kuda, p_grunt = old["block"], old["areas"], old["objects"]
        p_econ = old["use"]
        p_sroki = old["terms"]
    else:
        p_plecho = (f"{facts['name']} стоит {dist} по {facts['tract']}. "
                    f"Это {pl['tier']} рейс. {pl['econ']}")
        p_econ = (f"{facts['name']} это {facts['life']}. От этого зависит и что "
                  f"здесь заказывают, и какими объёмами: снабженец предприятия "
                  f"и хозяин участка приходят с разными задачами, и материал "
                  f"мы подбираем под задачу, а не по прайсу сверху вниз.")
        p_kuda = (f"Возим {facts['prep']} и в округ: {facts['areas']}. "
                  f"По адресам за чертой города заранее скажите, какой заезд: "
                  f"гружёный самосвал не везде разворачивается и не везде "
                  f"поднимает кузов под проводами и ветками.")
        p_grunt = (f"{facts['ground'][0].upper()}{facts['ground'][1:]} - вот с чем "
                   f"здесь приходится считаться при выборе материала и толщины слоя. "
                   f"На слабом основании слой делают толще и стелют геотекстиль, "
                   f"иначе материал уходит вниз за пару сезонов.")
        p_sroki = (f"Рейс {facts['prep']} {pl['term']}. Машину подбираем "
                   f"под объём и под ваш заезд: если ворота узкие или негде "
                   f"развернуться, подадим короткий самосвал вместо длинного.")

    crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]),
                   ("Щебень", SITE["base"] + "shcheben/"), (facts["name"], None)]
    cfaq = geo_city_faq(facts, mats, pl, dist)
    jl = graph(localbusiness(), bc_schema(crumb_items), faq_schema(cfaq),
               product_schema(h1, desc, MAT_FORMS[mats[0]]["low"], url))

    rel = [("/dostavka/shcheben/", "Щебень: все виды и цены"),
           ("/dostavka/stati/skolko-vesit-kub/", "Сколько весит куб материала"),
           ("/dostavka/stati/koefficient-uplotneniya/", "Сколько заказывать с учётом уплотнения"),
           ("/dostavka/", "Все города и материалы")]
    rel += [("/dostavka/" + MAT_FORMS[m]["url"] + "/",
             MAT_FORMS[m]["name"] + ": виды и цены") for m in mats[1:4]]
    ring = list(MATRIX)
    k = ring.index(city_slug)
    for nb in ring[k + 1:] + ring[:k]:
        if len(rel) >= 12:
            break
        rel.append((f"/dostavka/shcheben/{nb}/",
                    f"Доставка {CITY_FACTS[nb]['prep']}"))

    htmlp = env.get_template("geo2.j2").render(
        **BASE_CTX, canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items),
        jsonld=jl, title=title, desc=desc, h1=h1, hero_sub=hero,
        city=dict(facts, dist=dist), dist=dist, mat_blocks=mat_blocks,
        p_plecho=p_plecho, p_econ=p_econ, p_kuda=p_kuda, p_grunt=p_grunt,
        p_sroki=p_sroki, p_minv=pl["minv"], p_local=LOCAL[city_slug],
        faq=cfaq, related_links=rel[:12])
    pages.append((url, htmlp, "geo-city"))

# старые гео-страницы по щебню заменены городскими: убираем дубли по URL
_seen, _uniq = set(), []
for u, h, f in pages:
    if u in _seen and f == "geo":
        continue
    if u in _seen:
        _uniq = [(uu, hh, ff) for uu, hh, ff in _uniq if uu != u]
    _seen.add(u)
    _uniq.append((u, h, f))
pages = _uniq

# ---- СТРАНИЦА БЛАГОДАРНОСТИ ----
# Без неё Web3Forms после отправки показывал свою страницу на чужом домене:
# человек уходил с сайта, а сессия в Метрике обрывалась. Здесь же засчитывается
# цель - по факту доставки, а не по нажатию кнопки.
url = SITE["base"] + "spasibo/"
crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]),
               ("Заявка принята", None)]
htmlp = env.get_template("thanks.j2").render(
    **BASE_CTX, canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items),
    jsonld=graph(localbusiness(), bc_schema(crumb_items)),
    title="Заявка принята: считаем стоимость с доставкой",
    desc="Заявка на доставку нерудных материалов принята. Считаем объём и стоимость с доставкой на ваш адрес и возвращаемся с ответом.",
    h1="Заявка принята",
    lead="Спасибо. Заявка ушла к нам, считаем объём и стоимость с доставкой "
         "на ваш адрес.",
    next_step=SITE["callback_promise"][0].upper() + SITE["callback_promise"][1:] +
              ". Назовём точную сумму с доставкой и согласуем удобное окно "
              "приезда машины. Заявка ни к чему не обязывает.",
    links=[("/dostavka/stati/skolko-vesit-kub/", "Сколько весит куб щебня, песка и отсева"),
           ("/dostavka/stati/koefficient-uplotneniya/", "Сколько заказывать с запасом на уплотнение"),
           ("/dostavka/stati/skolko-shchebnya-v-kamaze/", "Сколько кубов входит в КамАЗ"),
           ("/dostavka/", "Все материалы и города")],
    noindex=True, no_cta=True)
pages.append((url, htmlp, "thanks"))

# ---- ПОЛИТИКА ОБРАБОТКИ ДАННЫХ (у раздела свои формы, нужна своя политика) ----
url = SITE["base"] + "politika/"
crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]),
               ("Обработка данных", None)]
htmlp = env.get_template("legal.j2").render(
    **BASE_CTX, canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items),
    jsonld=graph(localbusiness(), bc_schema(crumb_items)),
    title="Обработка персональных данных: раздел доставки материалов",
    desc="Как раздел доставки нерудных материалов обрабатывает данные из формы заявки: какие поля, зачем, кому передаются, сроки хранения и как отозвать согласие.",
    h1="Обработка персональных данных в разделе доставки",
    updated=LEGAL_UPDATED, sections=legal_sections(SITE),
    form_anchor=SITE["base"] + "#zayavka")
pages.append((url, htmlp, "legal"))

# ---- ЗАПИСЬ ----
# Сначала убираем страницы, которых больше нет в плане сборки. Без этого
# после смены архитектуры на диске остаются осиротевшие адреса: они
# продолжают отдаваться, попадают в индекс и выглядят как дубли.
_planned = {os.path.join(ROOT, u.strip("/"), "index.html") for u, _, _ in pages}
_orphans = []
for _dp, _dn, _fn in os.walk(OUT):
    if "index.html" in _fn:
        _f = os.path.join(_dp, "index.html")
        if _f not in _planned:
            _orphans.append(_f)
for _f in _orphans:
    os.remove(_f)
    _d = os.path.dirname(_f)
    while _d != OUT and not os.listdir(_d):
        os.rmdir(_d)
        _d = os.path.dirname(_d)
if _orphans:
    print("Удалено осиротевших страниц: %d" % len(_orphans))
    for _f in sorted(_orphans):
        print("  - /%s/" % os.path.relpath(os.path.dirname(_f), ROOT).replace(os.sep, "/"))

written = []
for url, h, fam in pages:
    written.append((write(url, h), url, fam))

# ---- SITEMAP раздела ----
sm = ['<?xml version="1.0" encoding="UTF-8"?>',
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
# Страница благодарности закрыта от индексации, поэтому в карту не идёт:
# иначе Вебмастер отчитается о ней как об исключённой и будет прав.
for url, h, fam in pages:
    if fam == "thanks":
        continue
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


# Сравниваем ВСЕ гео-страницы между собой, а не внутри семейства.
# Раньше проверка шла по семействам, и пара "щебень в Реже" против
# "отсев в Реже" вообще не сравнивалась, хотя это тоже дорвейная ось.
grp = [(u, visible(h)) for u, h, f in pages if f.startswith("geo")]
print(f"\nПохожесть гео-страниц, все пары (порог < 0.80): {len(grp)} страниц")
mx, worst, high = 0, None, []
for i in range(len(grp)):
    for j in range(i + 1, len(grp)):
        r = difflib.SequenceMatcher(None, grp[i][1], grp[j][1]).ratio()
        if r > mx:
            mx, worst = r, (grp[i][0], grp[j][0])
        if r >= 0.80:
            high.append((r, grp[i][0], grp[j][0]))
high.sort(reverse=True)
for r, a, b in high:
    print(f"  ВЫСОКАЯ {r:.2f}: {a} vs {b}")
print(f"  пар выше порога: {len(high)}")
print(f"  максимум {mx:.2f} ({worst[0]} vs {worst[1]})  {'OK' if mx < 0.80 else 'ПРЕВЫШЕНО'}")

wc = [(u, len(visible(h).split())) for u, h, f in pages]
print("\nОбъём текста (слов):")
for u, n in sorted(wc, key=lambda x: -x[1]):
    print(f"  {n:5}  {u}")
