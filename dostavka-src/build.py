#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка раздела доставки в /dostavka/. Изолирован от ursdom.
Зависимости: Python 3 + jinja2. Вывод: статические index.html + sitemap раздела."""
import os
import io
import json
import hashlib
import datetime, sys, re, difflib
from PIL import Image
from jinja2 import Environment, FileSystemLoader

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "dostavka")
sys.path.insert(0, os.path.join(HERE, "data"))

from site_config import SITE, ADVANTAGES, GUARANTEES, PAYMENT
from products import MATERIALS, EXTRA
from products_ext import MATERIALS_EXT, MONEY_CFG_EXT
from products_zhbi import MATERIALS_ZHBI, MONEY_CFG_ZHBI
from products_beton import MATERIALS_BETON, MONEY_CFG_BETON
from products_gap import MATERIALS_GAP, MONEY_CFG_GAP
from products_gap2 import MATERIALS_GAP2, MONEY_CFG_GAP2
from products_gap3 import MATERIALS_GAP3, MONEY_CFG_GAP3
from products_rev import MATERIALS_REV, MONEY_CFG_REV
from geo_matrix import (CITY_FACTS, MATRIX, MAT_FORMS,
                        ANGLE, LOCAL, MAT_TASK, example_for, plecho,
                        lsi_for)
import autolink
from hubs import HUBS
from canonical import canonical
from calc import calc_for, PER_PAGE, MATERIALS as CALC_MATERIALS, trips as calc_trips
from calc_pages import CALC_PAGES, CALC_BY_SLUG, CALC_OWN

# Список страниц с калькулятором живёт в data/calc.py вместе с их
# материалами и объёмами: два списка в двух файлах разошлись бы
# при первом же добавлении страницы.
from conversion import PRICE_SETS, FAM, ORDER_STEPS, OBJECTIONS
from prices import (PER_CUBE, PRICE_NOTE, DELIVERY_NOTE, CATALOG, SIEVE,
                    HERO_CELL, LOTS, LOTS_HEAD, LOTS_NOTE,
                    CATALOG_META, CATALOG_FIRST, CROSS, FLOOR,
                    PESOK_QUARRIES, PESOK_QUARRIES_HEAD, PESOK_QUARRIES_NOTE,
                    ton_note)
from cities import CITIES, PESOK_CITIES
from longreads import LONGREADS, AUTHOR_FULL, UPDATED
from longreads_core import CORE_LONGREADS
from longreads_beton import BETON_LONGREADS
from longreads_zadachi import ZADACHI_LONGREADS
from longreads_smezh import SMEZH_LONGREADS
from longreads_beton2 import BETON2_LONGREADS
from longreads_gap import GAP_LONGREADS
from longreads_gap2 import GAP2_LONGREADS
from longreads_plitka import PLITKA_LONGREADS
from longreads_beton3 import BETON3_LONGREADS
from longreads_smesi import SMESI_LONGREADS
from longreads_skala import SKALA_LONGREADS
from longreads_rev import REV_LONGREADS
from longreads_brendy import BRENDY_LONGREADS
from longreads_pesok import PESOK_LONGREADS
from longreads_prim import PRIM_LONGREADS
from longreads_tovar import TOVAR_LONGREADS
from tags import TAG_LONGREADS
LONGREADS = LONGREADS + CORE_LONGREADS + BETON_LONGREADS + ZADACHI_LONGREADS + SMEZH_LONGREADS + BETON2_LONGREADS + GAP_LONGREADS + GAP2_LONGREADS + PLITKA_LONGREADS + BETON3_LONGREADS + SMESI_LONGREADS + SKALA_LONGREADS + REV_LONGREADS + BRENDY_LONGREADS + PESOK_LONGREADS + PRIM_LONGREADS + TOVAR_LONGREADS + TAG_LONGREADS
from legal import legal_sections, LEGAL_UPDATED

env = Environment(loader=FileSystemLoader(os.path.join(HERE, "templates")),
                  autoescape=False, trim_blocks=False, lstrip_blocks=False)
env.filters['xlink'] = autolink.link

# Версия CSS считается из содержимого файла. Раньше она была константой в конфиге,
# и после правок стилей вернувшийся посетитель получал старый файл из кеша.
_css = os.path.join(OUT, "assets", "dostavka.css")
if os.path.exists(_css):
    import hashlib
    SITE["css_version"] = hashlib.md5(open(_css, "rb").read()).hexdigest()[:8]
    # Отдаём минифицированную копию, редактируем читаемый исходник.
    # Версия по-прежнему считается от исходника: он и есть источник правды.
    from mincss import minify as _minify
    _src = open(_css, encoding="utf-8").read()
    _min = _minify(_src)
    with open(os.path.join(OUT, "assets", "dostavka.min.css"), "w",
              encoding="utf-8") as _f:
        _f.write(_min)
    print("CSS: %d -> %d байт (-%.0f%%)"
          % (len(_src), len(_min), 100 * (1 - len(_min) / len(_src))))
DOMAIN = SITE["domain"]
TODAY = "2026-07-28"
# Дата, до которой цена в разметке считается действующей.
PRICE_VALID_UNTIL = (datetime.date.today()
                     + datetime.timedelta(days=90)).isoformat()
PER_CUBE_LIST = list(PER_CUBE.items())

# Минимальная цена материала для баннера в первом экране. Считается
# из PER_CUBE, а не пишется руками: таблица цен стоит на той же странице
# ниже, и разойтись с ней баннер не имеет права. Ключи перечислены явно,
# потому что по названию материал не вычислить: «Отсев 0-5» и «ПГС»
# не содержат слова, по которому их можно сгруппировать.
# ---------------------------------------------------------------------------
# СВЕРКА ЦЕН НА СБОРКЕ.
#
# Появилась после вычитки, которая нашла восемь разошедшихся копий одной
# и той же цены: калькулятор считал песок по 350 при 990 в прайсе,
# речной по 700 при 1450, щебень 40-70 по 1300 при 770. Каждая копия
# была верна в день, когда её писали, и устарела в день, когда правили
# прайс. Человек видел на одном экране две цены и уходил.
#
# Ловить это глазами нельзя: числа лежат в разных файлах и на страницу
# попадают из разных мест. Поэтому сверка стоит на сборке и валит её,
# а не печатает предупреждение в конец лога, где его не читают.
_PRICE_ALIAS = {
    "Щебень 20-40": "Щебень 20-40", "Щебень 5-20": "Щебень 5-20",
    "Щебень 40-70": "Щебень 40-70", "Щебень 70-120": "Щебень 70-120",
    "Отсев 0-5": "Отсев 0-5", "ПГС": "ПГС", "ЩПС": "ЩПС",
    "Песок карьерный": "Песок карьерный (сеяный)",
    "Песок речной мытый": "Песок мытый (речной)",
    "Песок мытый": "Песок мытый (речной)",
    "Скальный грунт": "Скальный грунт (скала)",
    "Асфальтовая крошка": "Асфальтовая крошка",
    "Гравий": "Гравий", "Керамзит": "Керамзит",
    "Бутовый камень": "Бутовый камень",
    "Гранитная крошка": "Гранитная крошка", "Дресва": "Дресва",
}


def _rub(v):
    d = re.sub(r"[^\d]", "", str(v))
    return int(d) if d else None


def check_prices():
    """Одна цена на материал во всех источниках. Возвращает список бед."""
    bad = []

    def cmp(where, label, value):
        key = _PRICE_ALIAS.get(label)
        if key is None:
            return
        got, want = _rub(value), FLOOR[key]
        if got is not None and got != want:
            bad.append("%s: %s = %s, а в прайсе %s" % (where, label, got, want))

    for fam, d in PRICE_SETS.items():
        for row in d.get("rows", []):
            lab = row[0]
            # хвосты вида «под ложе», «на обсыпку» отрезаем по первому
            # совпадению с известной подписью
            for a in _PRICE_ALIAS:
                if lab == a or lab.startswith(a + " "):
                    cmp("конверсионный блок [%s]" % fam, a, row[1])
                    break
    for label, price in CALC_MATERIALS:
        cmp("калькулятор, список", label, price)
    for slug in PER_PAGE:
        c = calc_for(slug)
        cmp("калькулятор на /%s/" % slug, PER_PAGE[slug][0], c["default_price"])
    return bad


_price_bad = check_prices()
if _price_bad:
    for _b in _price_bad:
        print("ЦЕНЫ РАСХОДЯТСЯ  " + _b)
    raise SystemExit("сборка остановлена: цены расходятся между источниками")

# Корень раздела калькуляторов. Объявлен рано: на него ссылаются
# товарные страницы, которые собираются раньше самого раздела.
CALCHUB_URL = SITE["base"] + "kalkulyator/"

# Ссылки из таблицы фракций на посадочные по фракциям. Ключ - точная
# подпись строки таблицы: промах по строке просто оставит её текстом,
# а не уведёт ссылку не туда.
FRAC_HREF = {
    "5-10 мм": "/dostavka/shcheben/frakciya-5-10/",
    "5-20 мм": "/dostavka/shcheben/frakciya-5-20/",
    "10-20 мм": "/dostavka/shcheben/frakciya-10-20/",
    "20-40 мм": "/dostavka/shcheben/frakciya-20-40/",
    "40-70 мм": "/dostavka/shcheben/frakciya-40-70/",
    "70-120 мм": "/dostavka/shcheben/frakciya-70-120/",
    "70-150 мм": "/dostavka/shcheben/frakciya-70-150/",
    "Отсев 0-5 мм": "/dostavka/otsev/",
}

HERO_PRICE_KEYS = {
    "shcheben": ["Щебень 5-20", "Щебень 20-40", "Щебень 40-70",
                 "Щебень 70-120", "Щебень вторичный (бой)"],
    "pesok": ["Песок карьерный (сеяный)", "Песок мытый (речной)"],
    "otsev": ["Отсев 0-5"],
    "pgs": ["ПГС"],
}


def hero_price_for(slug):
    """«от N» по самой дешёвой позиции материала. None, если позиций нет."""
    keys = HERO_PRICE_KEYS.get(slug)
    if not keys:
        return None
    nums = []
    for k in keys:
        raw = PER_CUBE.get(k)
        if not raw:
            continue
        digits = re.sub(r"[^\d]", "", raw)
        if digits:
            nums.append(int(digits))
    return ("от %d" % min(nums)) if nums else None

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
        "openingHours": "Mo-Su 00:00-23:59",   # круглосуточно: у schema.org
                                               # нет отдельного знака «24/7»,
                                               # сутки записываются интервалом
        "priceRange": "₽₽",
        "currenciesAccepted": "RUB",
        "paymentAccepted": "Наличные, банковская карта, безналичный перевод",
        "telephone": SITE["phone"],
        "legalName": SITE["legal_name"],
        "address": {
            "@type": "PostalAddress",
            "streetAddress": SITE["street"],
            "addressLocality": SITE["city"],
            "addressRegion": SITE["region_short"],
            "postalCode": SITE["postal"],
            "addressCountry": "RU",
        },
        # Зона доставки описана городами, а не радиусом: радиус вокруг
        # точки соврал бы, потому что плечо считается по дорогам, а не
        # по прямой, и до Первоуральска через объездную дальше, чем
        # до Сысерти по прямой.
        "areaServed": [{"@type": "City", "name": n}
                       for n in ["Екатеринбург"] + [c["name"] for c in CITIES]],
        # geo НЕ указываем: точных координат базы владелец не давал,
        # а неверная точка на карте хуже её отсутствия. Поисковики
        # геокодируют PostalAddress сами.
        "sameAs": [],
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


def article_schema(url, title, desc, author=None, published=None, modified=None):
    published = published or TODAY
    modified = modified or published
    a = author or AUTHOR_FULL
    return {"@type": "Article", "headline": title, "description": desc,
            "inLanguage": "ru-RU", "datePublished": published, "dateModified": modified,
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
            # Срок действия цены. Без него Гугл помечает предложение как
            # устаревшее и может перестать показывать цену в результатах.
            # Ставим квартал вперёд: прайс партнёра пересматривается
            # примерно с этой частотой.
            "priceValidUntil": PRICE_VALID_UNTIL,
            "unitText": "кубометр",
            "areaServed": SITE["region"],
            "seller": {"@id": DOMAIN + SITE["base"] + "#business"},
        },
    }



# Наличие по семейству прайса. Владелец подтвердил, что в наличии есть
# всё, поэтому семейств-исключений больше нет. Множество оставлено как
# механизм: если какая-то группа снова уйдёт под заказ, здесь её и
# выключают, а текст на товарных меняют через UNDER_ORDER в data/products_*.
# Разметка обязана совпадать с текстом: InStock на позиции, которой нет
# в наличии, это обман и разметки, и человека.
_IN_STOCK_FAMS = set(PRICE_SETS)
_PRICE_RX = re.compile(r"(\d[\d\s]*)")


def pricelist_schema(fam_key, rows, page_url):
    """ItemList из Product+Offer по таблице цен в статье.

    Строки таблицы это не товары этой страницы, а товары, на которые она
    ссылается, поэтому у каждого Product стоит свой url на товарную,
    а не url статьи. Иначе поиск получил бы десяток разных товаров
    по одному адресу.

    Цена берётся из той же строки, что видит человек: 'от 1400 руб/м³'
    даёт lowPrice 1400. Позиции 'по запросу' в разметку не попадают
    вообще - Offer без цены бесполезен и засоряет граф.
    """
    avail = ("https://schema.org/InStock" if fam_key in _IN_STOCK_FAMS
             else "https://schema.org/PreOrder")
    items = []
    for name, price, href in rows:
        m = _PRICE_RX.search(price)
        if not m or "запрос" in price:
            continue
        low = m.group(1).replace(" ", "")
        unit = ("кубометр" if "м³" in price else
                "квадратный метр" if "м²" in price else
                "мешок" if "мешок" in price else "штука")
        items.append({
            "@type": "ListItem", "position": len(items) + 1,
            "item": {
                "@type": "Product", "name": name,
                "category": "Нерудные строительные материалы",
                "url": DOMAIN + href,
                "brand": {"@type": "Brand", "name": SITE["brand"]},
                "offers": {
                    "@type": "Offer", "price": low, "priceCurrency": "RUB",
                    "availability": avail, "unitText": unit,
                    "areaServed": SITE["region"], "url": DOMAIN + href,
                    "seller": {"@id": DOMAIN + SITE["base"] + "#business"},
                },
            }})
    if not items:
        return None
    return {"@type": "ItemList", "name": "Цены с доставкой",
            "url": DOMAIN + page_url + "#skolko-stoit",
            "numberOfItems": len(items), "itemListElement": items}


# Ссылка страницы на саму себя это тупик: клик ничего не меняет, а вес
# внутренней перелинковки уходит в никуда. Такие ссылки набежали из двух
# мест сразу: подвал и шапка одинаковы на всех страницах, а таблица цен
# семейства включает и текущий товар. Ревью нашло их на пятнадцати
# страницах, в том числе на всех семи страницах марок бетона.
#
# Заменяем на span с aria-current="page": и клика нет, и скринридер
# сообщает, что это текущий раздел. Классы сохраняются, поэтому вид
# не меняется нигде, кроме исчезнувшего подчёркивания.
_SELF_RX = re.compile(r'<a\b([^>]*?)href="([^"]+)"([^>]*?)>(.*?)</a>', re.S)


def strip_self_links(html, url):
    def sub(m):
        pre, href, post, inner = m.groups()
        if href.split("#")[0].split("?")[0] != url:
            return m.group(0)
        cls = re.search(r'class="([^"]*)"', pre + post)
        cls = ' class="%s"' % cls.group(1) if cls else ""
        return '<span%s aria-current="page">%s</span>' % (cls, inner)
    return _SELF_RX.sub(sub, html)

def graph(*nodes):
    return json.dumps({"@context": "https://schema.org", "@graph": list(nodes)},
                      ensure_ascii=False, indent=2)


def write(url, html_str):
    path = os.path.join(OUT, url[len(SITE["base"]):].strip("/"), "index.html") \
        if url != SITE["base"] else os.path.join(OUT, "index.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Единственная точка, через которую проходят все страницы, поэтому
    # снятие ссылок на саму себя стоит здесь, а не в каждом шаблоне.
    open(path, "w", encoding="utf-8").write(strip_self_links(html_str, url))
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
        ("granit-20-40-shtabel.jpg",
         "Крупный план щебня 20-40 мм серого цвета, зерно колотое с острыми гранями",
         "Щебень 20-40 вблизи. Зерно колотое, грани острые и свежие: такой камень "
         "сцепляется в слое и держит нагрузку, в отличие от окатанного гравия."),
        ("granit-70-120-shtabel.jpg",
         "Высокий штабель крупного щебня 70-120 мм, снятый снизу вверх на фоне пасмурного неба",
         "Щебень 70-120 в штабеле. Кадр снят от подошвы кучи, и по нему видно то, "
         "чего не показывает горсть: камень такого размера лопатой не берут и "
         "тонким слоем не стелют. Его место в габионах, подпорных стенках и нижних "
         "слоях основания, где работает вес и заклинивание крупных кусков."),
    ],
    "skalnyy-grunt": [
        ("skala-shtabel.jpg",
         "Куски скального грунта разного размера, от мелкой щебёнки до плит в две ладони, вперемешку",
         "Скальный грунт как он приходит: без фракции, куски вперемешку с мелочью. "
         "Именно эта разнокалиберность и делает его хорошей черновой отсыпкой - "
         "мелочь заполняет пустоты между крупными кусками, и слой уплотняется "
         "плотнее, чем из ровной фракции. По этой же причине под чистовые "
         "работы он не годится."),
    ],
    "pesok": [
        ("karyernyy-shtabel.jpg",
         "Штабель карьерного песка высотой в несколько метров на площадке, пасмурное небо",
         "Карьерный песок в штабеле. Ровный жёлто-бурый цвет по всей куче: у карьерного "
         "он всегда теплее и темнее, чем у мытого, из-за глинистых и железистых примесей."),
        ("peregruzka-greyfer.jpg",
         "Конус песка на площадке перевалки, грейферный ковш крана над ним, рядом вагон-хоппер",
         "Перевалка песка грейфером. Конус после выгрузки держит форму и не расплывается: "
         "это признак нормальной влажности, пересушенный песок так не стоит."),
        ("karyernyy-kucha-karyer.jpg",
         "Высокая куча жёлтого песка на карьере, по земле следы протектора погрузчика",
         "Песок на карьере. По следам протектора видно, что кучу переваливают погрузчиком: "
         "материал берут с рабочего штабеля, а не с краю, где он мог намокнуть."),
    ],
    "pesok/karyernyy": [
        ("karyernyy-hand-glina.jpg",
         "Горсть карьерного песка в ладони, среди песка комки сухой растрескавшейся глины",
         "Вот те самые глинистые включения, из-за которых карьерный песок не идёт в кладочный "
         "раствор без промывки. Комки видно в ладони: они держат форму и трескаются при сушке. "
         "В отсыпке и в подушке под фундамент это не мешает, в растворе снижает прочность шва."),
    ],
    "otsev": [
        ("otsev-hand.jpg",
         "Горсть серого отсева в ладони на фоне штабеля того же материала",
         "Отсев в ладони. Зерно колотое, с острыми гранями и плоскими сколами: этим он "
         "отличается от песка, у которого зерно окатанное. Острая грань и даёт расклинцовку, "
         "ради которой отсев кладут поверх щебня."),
        ("otsev-shtabel.jpg",
         "Куча серого отсева в бетонном отсеке склада, на заднем плане ковш фронтального погрузчика",
         "Отсев в отсеке склада. Материал неоднороден по составу: между зёрнами видна каменная "
         "пыль, и именно она заполняет пустоты при уплотнении. Просить у отсева чистой фракции "
         "бессмысленно, мелочь в нём по определению."),
        ("otsev-shtabel-baza.jpg",
         "Большой штабель тёмно-серого отсева на площадке базы, рядом другие штабели материалов",
         "Отсев штабелем на площадке. Видно, как материал ложится под собственным углом "
         "естественного откоса: у мелкой фракции с пылью он круче, чем у чистого щебня, "
         "и куча держит форму без подпорок."),
    ],
    # Снимки с объектов. Два кадра по отсыпке идут парой: сначала процесс
    # (щебень по геотекстилю), потом результат (готовый двор). Порядок
    # в списке и есть порядок в галерее, менять его нельзя - подписи
    # написаны как «сначала-потом».
    "stati/skalnyy-grunt-klassifikaciya": [
        ("skalnyy-grunt/skala-shtabel.jpg",
         "Куски скального грунта разного размера вперемешку с мелочью, без сортировки по фракции",
         "Вот почему у скального грунта не спрашивают фракцию. Это не сорт "
         "материала, а то, что осталось после разрушения массива: в одном "
         "штабеле и плиты в две ладони, и мелочь. Рядовая скала так и идёт, "
         "0-100 или 0-150, а щебень из неё получается уже после дробления "
         "и грохочения."),
    ],
    "stati/skalnyy-grunt-dresva-but": [
        ("skalnyy-grunt/skala-shtabel.jpg",
         "Скальный грунт: угловатые куски камня разного размера с каменной мелочью между ними",
         "Скальный грунт крупным планом. От дресвы отличается размером кусков "
         "и наличием крупных обломков: дресва это те же породы, но разрушенные "
         "до двух-сорока миллиметров. От бутового камня - тем, что бут "
         "отбирают по размеру, а скалу берут как есть."),
    ],
    "dresva-i-shlak": [
        ("skalnyy-grunt/skala-shtabel.jpg",
         "Куча скального грунта: крупные угловатые обломки и каменная мелочь между ними",
         "Скальный грунт, ближайший сосед дресвы по применению и цене. "
         "Разница в размере: здесь куски до нескольких десятков сантиметров, "
         "у дресвы всё разрушено до сорока миллиметров и раскидывается "
         "лопатой без техники."),
    ],
    "stati/frakcii-shchebnya": [
        ("shcheben/granit-70-120-shtabel.jpg",
         "Штабель щебня фракции 70-120 мм, снятый снизу, куски размером с кулак и крупнее",
         "Верхний край ряда фракций. Между 40-70 и 70-120 проходит граница, "
         "после которой материал перестаёт быть насыпным в бытовом смысле: "
         "такой камень не разравнивают граблями и не трамбуют виброплитой, "
         "его укладывают и заклинивают."),
    ],
    "stati/chem-otsypat-uchastok": [
        ("otsypka-geotekstil-shcheben.jpg",
         "Отсыпка двора частного дома: на песок уложен геотекстиль, поверх разровнен светлый щебень, работает экскаватор-погрузчик",
         "Отсыпка двора в работе. Под щебнем лежит геотекстиль, и на снимке видно, "
         "зачем он нужен: полотно отделяет камень от песчаного основания, иначе "
         "щебень уходит вниз и слой теряет толщину за пару сезонов."),
        ("otsypka-dvora-gotovo.jpg",
         "Готовый двор частного дома, отсыпанный тёмно-серым щебнем, по краю кирпичная окантовка, металлические ворота",
         "Тот же приём после завершения: ровная площадка по всему двору, у стены "
         "кирпичная окантовка, чтобы щебень не расползался. По такому покрытию "
         "ходят и ездят сразу, оно не раскисает в дождь."),
    ],
    "stati/dorozhki-na-uchastke": [
        ("graviynaya-dorozhka-bruschatka.jpg",
         "Подъездная дорожка из мелкого гравия, вдоль края выложена полоса брусчатки, за ней газон и деревянный забор",
         "Гравийная дорожка с брусчаткой по краю. Каменная полоса держит границу "
         "и не даёт гравию высыпаться на асфальт: без такой окантовки материал "
         "разносится колёсами и подсыпать его приходится каждый сезон."),
    ],
    "bitum-i-asfalt": [
        ("vygruzka-goryachey-smesi.jpg",
         "Оранжевый самосвал с поднятым кузовом выгружает горячую асфальтобетонную смесь, от материала идёт пар",
         "Выгрузка горячей смеси. Пар над кузовом показывает главное ограничение "
         "материала: укладывать его надо сразу, пока температура не упала, "
         "поэтому рейс согласуют по времени с бригадой на объекте."),
    ],
    "pgs": [
        ("pgs-kucha-karyer.jpg",
         "Большая куча песчано-гравийной смеси на карьере, за ней склон с деревьями и облачное небо",
         "ПГС на карьере. В одной куче видно и песок, и окатанный гравий разного размера: "
         "это природная смесь, как её добыли. Доля гравия в ней непостоянна, поэтому под "
         "нагрузку берут обогащённую ОПГС, где эта доля поднята и выровнена."),
    ],
    "keramzit": [
        ("keramzit-nasyp.jpg",
         "Насыпь керамзита крупным планом, светло-коричневые пористые гранулы округлой формы",
         "Керамзит вблизи. Гранулы округлые и пористые, на изломе видна ячеистая структура: "
         "отсюда и малый вес, и теплоизоляция. Оболочка спечённая и прочная, поэтому "
         "материал держит засыпку и не слёживается в пыль."),
    ],
    "graviy": [
        ("graviy-hand.jpg",
         "Горсть окатанного гравия в ладони на фоне большой кучи гравия, вдалеке грохот и погрузчик",
         "Гравий в ладони. Зерно окатанное, гладкое, без свежих сколов: камень обкатан водой, "
         "а не расколот дробилкой. Отсюда и главное следствие для дела: сцепление с цементным "
         "камнем у гравия слабее, чем у колотого щебня, и в ответственный бетон берут щебень."),
    ],
    "stati/ukladka-trotuarnoy-plitki": [
        ("podstilayushchiy-sloy.jpg",
         "Вскрытая городская мостовая: слева снятая волнистая плитка, справа обнажённый подстилающий слой со следами колёс",
         "Вскрытое мощение на ремонте городской площади. Справа виден подстилающий слой, "
         "на котором лежала плитка, и по следам колёс на нём понятно, почему полотно повело: "
         "слой промят колеёй, то есть под ним не было нормального щебёночного основания."),
    ],
    "stati/skolko-shchebnya-v-kamaze": [
        ("samosval-karyer.jpg",
         "Трёхосный самосвал КамАЗ с поднятыми бортами стоит у штабелей щебня на карьере",
         "Трёхосный КамАЗ под погрузкой на карьере. По кузову и видно, о чём вся эта статья: "
         "объём считают по паспортной вместимости кузова, а не по тому, сколько насыпали "
         "с горкой. Горка при первом же торможении осядет и уедет по дороге."),
    ],
    # Полоса доверия внизу КАЖДОЙ страницы (см. fleet_photos в BASE_CTX
    # и m.fleet_strip в _macros.j2). Смысл именно здесь, а не в обычной
    # галерее по одной странице на снимок: владелец прислал за раз
    # почти столько же брака, сколько годных кадров, и большая часть
    # присланного это как раз техника и база. Одна полоса, подключённая
    # централизованно в base.j2, даёт этим немногим годным снимкам
    # выход на все 157 страниц вместо одной, и не плодит отдельных
    # галерей под каждый будущий кадр.
    "fleet": [
        ("manipulyator-zagruzka.jpg",
         "Манипулятор Mitsubishi Fuso с краном на площадке базы, на кузове мешки со стройматериалами",
         "Манипулятор под штучный товар: плитку, бордюр, кольца и мешковые смеси. "
         "Кран снимает с кузова прямо на объект, вручную такой груз не носят."),
        ("samosval-karyer-shchebenka.jpg",
         "Самосвал КамАЗ под погрузкой щебня на карьере рядом с дробильно-сортировочной установкой",
         "Погрузка на карьере под дробильно-сортировочной установкой. Материал идёт прямо "
         "из-под грохота, без промежуточного склада."),
        ("betonomeshalka-sitrak.jpg",
         "Бетоновоз-миксер SITRAK с барабаном Liebherr на площадке базы",
         "Миксер, которым возим бетон. Барабан Liebherr на восемь кубов, к объекту "
         "подъезжает с готовым замесом."),
        ("baza-s-vozduha.jpg",
         "Вид с воздуха на производственную базу с силосами, складом ЖБИ и парком техники",
         "База с воздуха: силосы, склад готовых изделий и площадка под погрузку. "
         "Отсюда уходят машины на объекты по городу и области."),
        ("samosval-vygruzka.jpg",
         "Самосвал с поднятым кузовом выгружает грунт на площадке, вид сверху",
         "Выгрузка на объекте. Кузов поднимается на месте, поэтому под разгрузку нужен "
         "запас по высоте: провода, ветки и навесы над точкой выгрузки заранее оговариваем."),
    ],
    "stati/kladochnaya-smes-dlya-pechey": [
        ("terrakot-20kg-etiketka.jpg",
         "Мешок кладочной глино-шамотной жаростойкой смеси Терракот, 20 кг, этикетка с рабочей температурой 1300 градусов",
         "Мешок Терракот 20 кг, тот, что стоит в таблице цен. На этикетке видно ключевое "
         "для выбора: назначение «для печей и каминов», рабочая температура 1300 градусов "
         "и отметка Русского печного общества. Это то, что стоит сверить при получении."),
    ],
}

# Заголовок и подводка галереи там, где стандартная фраза не подходит:
# на статье снимок иллюстрирует мысль текста, а не показывает товар.
PHOTOS_META = {
    "stati/ukladka-trotuarnoy-plitki": dict(
        head="Как выглядит подстилающий слой в разрезе",
        intro="Снимок с ремонта городской мостовой: плитку сняли, и стало видно то, "
              "о чём говорит весь раздел про основание."),
    "stati/skolko-shchebnya-v-kamaze": dict(
        head="Та самая машина",
        intro="Кузов, по паспортной вместимости которого и считают объём."),
    "pesok/karyernyy": dict(
        head="Как выглядят глинистые включения",
        intro="Главное, что отличает карьерный песок от мытого, и единственное, "
              "что стоит проверить руками при приёмке."),
}


def photos_for(slug):
    """Снимки материалов с адаптивными вариантами.

    Оригиналы по 1600 пикселей и 170-390 килобайт каждый. На телефоне
    колонка не шире 390 логических пикселей, то есть около 780 физических
    на экране двойной плотности: полуторатысячный JPEG там грузится
    целиком и выбрасывается наполовину. Отсюда два размера в WebP
    и уменьшенный JPEG как запасной для браузеров без поддержки WebP.

    Варианты подставляются, только если файл действительно лежит рядом.
    Ссылка на несуществующий вариант в srcset ломает картинку молча:
    браузер выберет его по ширине и не покажет ничего.
    """
    out = []
    IMGDIR = os.path.join(OUT, "assets", "img")
    for f, a, c in PHOTOS.get(slug, []):
        # Имя со слэшем - снимок из чужой папки. Так один кадр выходит
        # на несколько страниц, не размножаясь по диску: раньше, чтобы
        # показать скалу и в товарной, и в двух статьях, файл пришлось бы
        # положить тремя копиями по полтора мегабайта вместе с вариантами.
        sub, name = (f.rsplit("/", 1) if "/" in f else (slug, f))
        base = os.path.splitext(name)[0]
        d = os.path.join(IMGDIR, sub)
        with Image.open(os.path.join(d, name)) as im:
            w, h = im.size
        webp, jpg = [], []
        for wd in (800, 1600):
            cand = "%s-%d.webp" % (base, wd)
            if os.path.exists(os.path.join(d, cand)):
                webp.append("/dostavka/assets/img/%s/%s %dw" % (sub, cand, wd))
        cand = "%s-1200.jpg" % base
        if os.path.exists(os.path.join(d, cand)):
            jpg.append("/dostavka/assets/img/%s/%s 1200w" % (sub, cand))
        jpg.append("/dostavka/assets/img/%s/%s %dw" % (sub, name, w))
        out.append(dict(src="/dostavka/assets/img/%s/%s" % (sub, name),
                        alt=a, cap=c, w=w, h=h,
                        webp=", ".join(webp), jpg=", ".join(jpg)))
    return out


def img_one(rel):
    """Один снимок по пути вида «shcheben/granit-20-40-macro.jpg».

    Отличается от photos_for тем, что берёт файл по прямому пути, а не
    из реестра PHOTOS по слагу страницы: витрина прайса на странице песка
    показывает и щебень, то есть снимки из чужих папок.

    Варианты подставляются, только если файл действительно лежит рядом,
    по тому же правилу, что и в photos_for: ссылка на несуществующий
    вариант в srcset ломает картинку молча.
    """
    sub, f = rel.split("/", 1)
    base = os.path.splitext(f)[0]
    d = os.path.join(OUT, "assets", "img", sub)
    path = os.path.join(d, f)
    if not os.path.exists(path):
        return None
    with Image.open(path) as im:
        w, h = im.size
    webp, jpg = [], []
    for wd in (160, 320, 800, 1600):
        cand = "%s-%d.webp" % (base, wd)
        if os.path.exists(os.path.join(d, cand)):
            webp.append("/dostavka/assets/img/%s/%s %dw" % (sub, cand, wd))
    cand = "%s-1200.jpg" % base
    if os.path.exists(os.path.join(d, cand)):
        jpg.append("/dostavka/assets/img/%s/%s 1200w" % (sub, cand))
    jpg.append("/dostavka/assets/img/%s/%s %dw" % (sub, f, w))
    return dict(src="/dostavka/assets/img/%s/%s" % (sub, f), w=w, h=h,
                webp=", ".join(webp), jpg=", ".join(jpg))


# Снимок в боковую панель первого экрана. Раньше там была нарисованная
# сетка сита: владелец сказал прямо, что схематичные картинки доверия
# не вызывают, и он прав - на коммерческой странице рисунок вместо
# товара читается как «фотографии у них нет».
#
# Подпись под панелью называет то, что НА СНИМКЕ, а не то, о чём
# страница. Для страниц без своего материала (ЖБИ, бетон, плитка)
# снимка материала нет и не будет, поэтому туда идёт техника: она
# честно относится к доставке любого из них.
HERO_PHOTO = {
    "shcheben":           ("shcheben/granit-20-40-shtabel.jpg", "щебень 20-40 мм"),
    "pesok":              ("pesok/karyernyy-shtabel.jpg", "карьерный песок"),
    "otsev":              ("otsev/otsev-shtabel.jpg", "отсев 0-5 мм"),
    "pgs":                ("pgs/pgs-kucha-karyer.jpg", "ПГС"),
    "keramzit":           ("keramzit/keramzit-nasyp.jpg", "керамзит 5-20 мм"),
    "graviy":             ("graviy/graviy-hand.jpg", "гравий 20-40 мм"),
    "skalnyy-grunt":      ("skalnyy-grunt/skala-shtabel.jpg", "скальный грунт"),
    "butovyy-kamen":      ("shcheben/granit-70-120-shtabel.jpg", "камень 70-120 мм"),
    "shchps":             ("pgs/pgs-kucha-karyer.jpg", "щебёночно-песчаная смесь"),
    "asfaltovaya-kroshka": ("bitum-i-asfalt/vygruzka-goryachey-smesi.jpg", "выгрузка смеси"),
    "granitnaya-kroshka": ("shcheben/granit-5-20-tape.jpg", "гранит 5-20 мм"),
    # Страницы фракций. Без явных строк они попадали под правило
    # «shcheben» и все показывали кадр 20-40: на странице про камень
    # размером с кулак стоял снимок щебёнки с монету.
    #
    # Подпись называет фракцию НА СНИМКЕ, а не фракцию страницы.
    # Своих кадров у 5-10, 10-20 и 70-150 нет, им поставлен ближайший,
    # и подпись говорит правду о том, что видно.
    "shcheben/frakciya-5-10": ("shcheben/granit-5-20-tape.jpg", "щебень 5-20 мм"),
    "shcheben/frakciya-5-20": ("shcheben/granit-5-20-tape.jpg", "щебень 5-20 мм"),
    "shcheben/frakciya-10-20": ("shcheben/granit-5-20-tape.jpg", "щебень 5-20 мм"),
    "shcheben/frakciya-20-40": ("shcheben/granit-20-40-macro.jpg", "щебень 20-40 мм"),
    "shcheben/frakciya-40-70": ("shcheben/granit-40-70-hand.jpg", "щебень 40-70 мм"),
    "shcheben/frakciya-70-120": ("shcheben/granit-70-120-shtabel.jpg", "щебень 70-120 мм"),
    "shcheben/frakciya-70-150": ("shcheben/granit-70-120-shtabel.jpg", "щебень 70-120 мм"),
    "shcheben/v-meshkah": ("shcheben/granit-20-40-shtabel.jpg", "щебень 20-40 мм"),
    "pesok/v-meshkah": ("pesok/karyernyy-shtabel.jpg", "карьерный песок"),
    "pesok/peskostruynyy": ("pesok/peregruzka-greyfer.jpg", "перевалка песка"),
}
# Для остальных страниц - по куску слага. Ищется вхождение, а не начало:
# бетон живёт и в /beton/, и в /stati/marki-betona/, и в /stati/ves-kuba-betona/,
# а начало слага у них общее только со «stati». Порядок в списке и есть
# приоритет: первое совпадение выигрывает.
HERO_PHOTO_PART = [
    ("plitk",    ("stati/ukladka-trotuarnoy-plitki/podstilayushchiy-sloy.jpg",
                  "основание под плиткой")),
    ("beton",    ("fleet/betonomeshalka-sitrak.jpg", "миксер на объекте")),
    ("asfalt",   ("bitum-i-asfalt/vygruzka-goryachey-smesi.jpg", "выгрузка смеси")),
    ("bitum",    ("bitum-i-asfalt/vygruzka-goryachey-smesi.jpg", "выгрузка смеси")),
    ("dresva",   ("skalnyy-grunt/skala-shtabel.jpg", "скальный грунт")),
    ("skal",     ("skalnyy-grunt/skala-shtabel.jpg", "скальный грунт")),
    ("pesok",    ("pesok/karyernyy-shtabel.jpg", "карьерный песок")),
    ("otsev",    ("otsev/otsev-shtabel.jpg", "отсев 0-5 мм")),
    ("kamaz",    ("stati/skolko-shchebnya-v-kamaze/samosval-karyer.jpg",
                  "самосвал под погрузкой")),
    ("dorozhk",  ("stati/dorozhki-na-uchastke/graviynaya-dorozhka-bruschatka.jpg",
                  "дорожка из гравия")),
    ("otsyp",    ("stati/chem-otsypat-uchastok/otsypka-dvora-gotovo.jpg",
                  "отсыпанный двор")),
    ("shcheben", ("shcheben/granit-20-40-shtabel.jpg", "щебень 20-40 мм")),
    # ЖБИ и штучные изделия. Самосвал тут был бы неправдой в мелочи,
    # которую заказчик замечает сразу: кольца, плиты и бордюр не сваливают
    # кузовом, их снимают манипулятором. Заодно это разводит полсотни
    # страниц, на которых иначе стоял бы один и тот же кадр выгрузки.
    ("kolca", ("fleet/manipulyator-zagruzka.jpg", "разгрузка манипулятором")),
    ("lotk", ("fleet/manipulyator-zagruzka.jpg", "разгрузка манипулятором")),
    ("plit", ("fleet/manipulyator-zagruzka.jpg", "разгрузка манипулятором")),
    ("blok", ("fleet/manipulyator-zagruzka.jpg", "разгрузка манипулятором")),
    ("bordyur", ("fleet/manipulyator-zagruzka.jpg", "разгрузка манипулятором")),
    ("stupeni", ("fleet/manipulyator-zagruzka.jpg", "разгрузка манипулятором")),
    ("zabor", ("fleet/manipulyator-zagruzka.jpg", "разгрузка манипулятором")),
    ("opory", ("fleet/manipulyator-zagruzka.jpg", "разгрузка манипулятором")),
    ("lyuk", ("fleet/manipulyator-zagruzka.jpg", "разгрузка манипулятором")),
    ("zhbi", ("fleet/manipulyator-zagruzka.jpg", "разгрузка манипулятором")),
    ("formy", ("fleet/manipulyator-zagruzka.jpg", "разгрузка манипулятором")),
    ("dozhdepriemnik", ("fleet/manipulyator-zagruzka.jpg", "разгрузка манипулятором")),
    ("reshetk", ("fleet/manipulyator-zagruzka.jpg", "разгрузка манипулятором")),
    # Склад и база: рубричные хабы и всё, что про ассортимент целиком.
    ("smesi", ("fleet/baza-s-vozduha.jpg", "наша база в Екатеринбурге")),
    ("himiya", ("fleet/baza-s-vozduha.jpg", "наша база в Екатеринбурге")),
    ("cement", ("fleet/baza-s-vozduha.jpg", "наша база в Екатеринбурге")),
    ("blagoustroystvo", ("fleet/baza-s-vozduha.jpg", "наша база в Екатеринбурге")),
    ("vodootvod", ("fleet/manipulyator-zagruzka.jpg", "разгрузка манипулятором")),
]
HERO_PHOTO_DEFAULT = ("fleet/samosval-vygruzka.jpg", "выгрузка самосвалом")


def hero_photo_for(slug):
    """(img, подпись) для панели первого экрана.

    Подпись называет то, что НА СНИМКЕ. Для страницы без своего
    материала - бетонных колец, плитки, статьи про марки бетона -
    честного снимка товара у нас нет и не будет, поэтому туда идёт
    техника: она относится к доставке любого из них и ничего
    не обещает сверх правды.
    """
    pair = HERO_PHOTO.get(slug)
    if pair is None:
        for part, p in HERO_PHOTO_PART:
            if part in slug:
                pair = p
                break
    if pair is None:
        pair = HERO_PHOTO_DEFAULT
    path, cap = pair
    return img_one(path), cap


def sieve_rows():
    """Строки стопки фракций с разобранным снимком.

    В SIEVE лежит путь строкой, а шаблону нужен словарь с srcset.
    Без этого шага в разметку уезжал сам путь, и вместо снимка
    страница показывала alt - ровно это и случилось при первой сборке.
    """
    out = []
    for mm, cell, frac, name, use, price, href, photo in SIEVE:
        out.append((mm, cell, frac, name, use, price, href,
                    img_one(photo) if photo else None))
    return out


def product_images(slug):
    """Снимки для разметки товара: свои, а если их нет - кадр из первого
    экрана этой же страницы.

    Без запасного варианта картинку получали одиннадцать товарных узлов
    из ста двадцати шести: своя галерея есть далеко не у каждой страницы.
    Снимок первого экрана относится к странице по определению - он на ней
    и стоит, - поэтому подставить его честно.
    """
    own = [x["src"] for x in photos_for(slug)]
    if own:
        return own
    img, _cap = hero_photo_for(slug)
    return [img["src"]] if img else None


def hero_ctx(slug):
    """Снимок и подпись для боковой панели первого экрана, одним куском."""
    img, cap = hero_photo_for(slug)
    return dict(hero_img=img, hero_cap=cap)


def _fmt(x):
    """Число по-русски: без хвостовых нулей, запятая вместо точки."""
    r = round(x, 1)
    if abs(r - round(r)) < 0.05:
        return str(int(round(r)))
    return ("%.1f" % r).replace(".", ",")


def _dens(x):
    """Плотность двумя знаками: 1,35 и 1,40 при округлении до одного
    знака превращались в «1,4-1,4», и диапазон переставал быть диапазоном."""
    return ("%.2f" % x).replace(".", ",")


def _truck(vol):
    n, cap = calc_trips(vol)
    if n == 1:
        return "самосвал %d м³" % cap
    return "%d рейса по %d м³" % (n, cap) if n < 5 else "%d рейсов по %d м³" % (n, cap)


# Объёмы и подпись под таблицу зависят от пояса, в котором стоит город.
# Не ради разнообразия: на плече в двадцать километров осмысленно везти
# пять кубов, на плече в двести пятьдесят - нет, там рейс съедает всю
# экономию, и таблица с пятью кубами вводила бы в заблуждение.
#
# Побочный и полезный эффект: соседние города попадают в разные пояса,
# и страницы перестают совпадать текстом. Пара Камышлов - Талица
# упиралась в порог похожести именно из-за одинаковых блоков.
CITY_BANDS = [
    (40,  (5, 8, 10),
     "На таком плече рейс стоит недорого, поэтому заказывать по пять "
     "кубов имеет смысл: переплата за куб небольшая."),
    (90,  (8, 10, 15),
     "Плечо уже заметно в цене куба. Выгоднее собрать заказ от десяти "
     "кубов, чем возить дважды по пять."),
    (150, (10, 15, 20),
     "Дробить заказ на этом плече дороже всего: доставка оплачивается "
     "за каждый рейс. Разумный минимум - десять кубов, оптимум двадцать."),
    (10000, (15, 20, 25),
     "Сюда рейс планируется на конкретный день и оплачивается целиком. "
     "Меньше пятнадцати кубов везти невыгодно: доставка перевесит "
     "стоимость самого материала."),
]


def city_lots(km, price_key="Щебень 20-40"):
    """Готовые суммы «материал плюс доставка» под плечо конкретного города.

    Считает тем же estimate, что и калькулятор: расходиться им нельзя,
    иначе на соседних страницах сайта два разных ответа на один вопрос.
    Возвращает (строки, подпись пояса).
    """
    from calc import estimate
    price = FLOOR[price_key]
    vols, note = next((v, n) for lim, v, n in CITY_BANDS if km <= lim)
    out = []
    for v in vols:
        e = estimate(v, price, km)
        out.append(dict(vol=v, truck=_truck(v),
                        material="%d" % e["material"],
                        delivery="%d" % e["delivery"],
                        total="%d" % e["total"]))
    return out, note


def catalog_for(slug):
    """Витрина прайса карточками: цена, снимок, применение, кнопка.

    Цена берётся из PER_CUBE и здесь не дублируется, остальное
    из CATALOG_META по тому же ключу. Строка без метаданных
    в витрину не попадает - это видно сразу и лечится ключом,
    а не молчаливым пропуском цены.

    Порядок: сначала строки материала этой страницы, потом все
    остальные. Человек, пришедший за песком, видит песок первым.
    """
    first = CATALOG_FIRST.get(slug, ())
    rows = []
    for name, price in PER_CUBE.items():
        meta = CATALOG_META.get(name)
        if not meta:
            continue
        photo, href, cell, use = meta
        rows.append(dict(name=name, price=price, href=href, cell=cell, use=use,
                         own=any(name.startswith(p) for p in first),
                         img=img_one(photo) if photo else None,
                         alt=("%s, фотография материала" % name) if photo else None))
    rows.sort(key=lambda r: not r["own"])
    return rows


# Зоны доставки. Конкурент рисует на этом месте карту области с закрашенными
# районами; карту мы не рисуем, потому что честная её версия требует
# границ и проверки, а нечестная - это картинка ради картинки.
#
# Вместо карты то, что человек на ней и ищет: своё направление, плечо
# в километрах и что это значит для заказа. Заодно блок заменяет собой
# алфавитный список населённых пунктов - он и есть список, только
# отсортированный по тому признаку, который двигает цену.
#
# Города берутся из CITY_FACTS и разложены по километражу оттуда же:
# отдельного списка здесь нет и разъехаться ему не с чем.
ZONE_BANDS = [
    (0, 40, "Ближняя зона", "до 40 км",
     "Возим от 5 кубов, часто в день заявки."),
    (40, 90, "Среднее плечо", "40-90 км",
     "Выгоднее от 10 кубов: плечо уже заметно в цене за куб."),
    (90, 150, "Дальнее плечо", "90-150 км",
     "Оптимум 10-20 кубов, машину ставим в график на сутки-двое."),
    (150, 10000, "Север и восток области", "от 150 км",
     "Разумно брать 20 кубов за рейс: дробить заказ на таком плече дороже всего."),
]


def zones_for():
    """Города по зонам доставки, ссылками на их страницы."""
    out = []
    for lo, hi, head, band, note in ZONE_BANDS:
        items = sorted(((v["km"], v["name"], k) for k, v in CITY_FACTS.items()
                        if lo < v["km"] <= hi or (lo == 0 and v["km"] <= hi)),
                       key=lambda t: t[0])
        if not items:
            continue
        out.append(dict(head=head, band=band, note=note,
                        cities=[dict(name=n, km=km,
                                     href="%sshcheben/%s/" % (SITE["base"], sl))
                                for km, n, sl in items]))
    return out


def cross_for(slug, limit=4):
    """Перекрёстная витрина: четыре соседних материала со снимками.

    Текущий материал вычитается: страница, предлагающая саму себя,
    выглядит как ошибка сборки, потому что ей и является.
    """
    out = []
    for key, name, href, photo, price, use in CROSS:
        if key == slug:
            continue
        img = img_one(photo)
        out.append(dict(name=name, href=href, price=price, use=use, img=img,
                        alt="%s, фотография материала" % name))
        if len(out) == limit:
            break
    return out


def _photo_ctx(slug, items, default_head=None):
    """Три переменные галереи одним куском.

    Заголовок и подводка лежат в PHOTOS_META по слагу: подпись пишется
    под конкретный набор кадров, а не шаблонной фразой «фото материала».
    Если снимков нет, макрос не рендерит ничего, и заголовок с подводкой
    в разметку не попадают.
    """
    meta = PHOTOS_META.get(slug, {})
    ctx = dict(photos=items,
               photos_head=meta.get("head", default_head),
               photos_intro=meta.get("intro"))
    # Первый снимок страницы становится её обложкой в пересылке. Ключ
    # кладётся только когда снимки есть: в шаблоне стоит default(),
    # а он подставляет общую обложку лишь для необъявленной переменной.
    if items:
        ctx["og_image"] = DOMAIN + items[0]["src"]
    return ctx


FLEET_PHOTOS = photos_for("fleet")

BASE_CTX = dict(cfg=SITE, advantages=ADVANTAGES, guarantees=GUARANTEES,
                fleet_photos=FLEET_PHOTOS,
                per_cube=PER_CUBE_LIST, price_note=PRICE_NOTE, delivery_note=DELIVERY_NOTE,
                extra=EXTRA, calc_rows=CALC_ROWS, catalog=CATALOG, sieve=sieve_rows(),
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
                more_materials=[("/dostavka/kontakty/", "Контакты, адрес базы и реквизиты"),
                                ("/dostavka/zhbi-i-vodootvod/", "ЖБИ и водоотвод: кольца, лотки, дождеприёмники"),
                                ("/dostavka/blagoustroystvo/", "Благоустройство участка: плитка, бордюр, основание")]
                               + [(("/dostavka/" + k + "/"), v["name"])
                                for k, v in MATERIALS_EXT.items()]
                               + [(("/dostavka/" + k + "/"), v["name"])
                                  for k, v in MATERIALS_ZHBI.items()]
                               + [(("/dostavka/" + k + "/"), v["name"])
                                  for k, v in MATERIALS_BETON.items()]
                               + [(("/dostavka/" + k + "/"), v["name"])
                                  for k, v in MATERIALS_GAP.items()]
                               + [(("/dostavka/" + k + "/"), v["name"])
                                  for k, v in MATERIALS_GAP2.items()]
                               + [(("/dostavka/" + k + "/"), v["name"])
                                  for k, v in MATERIALS_GAP3.items()])

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
    # Хаб показывает тот же прайс витриной, что и товарные страницы.
    # Своего материала у хаба нет, поэтому порядок строк обычный.
    shelf_rows=catalog_for(None), payment=PAYMENT,
    related_links=[("/dostavka/shcheben/", "Доставка щебня: фракции и цены"),
                   ("/dostavka/shcheben/frakciya-20-40/", "Щебень 20-40: характеристики и расчёт"),
                   ("/dostavka/pesok/", "Доставка песка"),
                   ("/dostavka/stati/chem-otsypat-uchastok/", "Чем отсыпать участок"),
                   ("/dostavka/stati/dostavka-na-dachu/", "Доставка на дачу и в СНТ")])
pages.append((url, htmlp, "hub"))

# ---- MONEY: щебень, песок ----
money_cfg = {
    "shcheben": dict(hero_sub="Гранитный, известняковый, гравийный и вторичный щебень с доставкой по " + SITE["region_dat"] + ". Весь ряд фракций от 5-10 до 70-150 и отсев, навалом и в фасовке, оплата после выгрузки.",
                     mat_vin="щебень", mat_rod="щебня", mat_order="доставку щебня", subject="доставка щебня, " + SITE["region_short"],
                     title="Купить щебень в Екатеринбурге с доставкой: цена за куб и фракции",
                     desc="Купить щебень с доставкой по Екатеринбургу и Свердловской области: гранит, известняк, все фракции от 5-10 до 70-150. Цена за куб и за тонну, КамАЗ целиком, оплата после выгрузки.",
                     h1="Щебень с доставкой по Екатеринбургу и Свердловской области"),
    "pesok": dict(hero_sub="Карьерный и речной песок с доставкой по " + SITE["region_dat"] + ". Под отсыпку, подушку фундамента, бетон и кладку. Самосвалы от 5 кубов, оплата после выгрузки.",
                  mat_vin="песок", mat_rod="песка", mat_order="доставку песка", subject="доставка песка, " + SITE["region_short"],
                  title="Купить песок в Екатеринбурге с доставкой: карьерный и речной",
                  desc="Купить песок с доставкой по Екатеринбургу и Свердловской области: карьерный для отсыпки, речной мытый для бетона. Цена за куб и за тонну, КамАЗ целиком, оплата после выгрузки.",
                  h1="Песок с доставкой по Екатеринбургу и Свердловской области"),
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

# Ячейка сита и профильные статьи для товарных страниц без своего товара.
ZHBI_CELL = {"beton": 19, "kolca-kanalizacionnye": 34, "lotki-teplotrass": 34,
             "stupeni-betonnye": 19, "trotuarnaya-plitka-razmery": 8, "pechnye-smesi": 6,
             "reshetki-dozhdepriemnikov": 34, "bordyur-vidy": 19,
             "fbs-bloki": 46, "dorozhnye-plity": 46, "peskobloki": 19, "cement-i-smesi": 8, "plitka-osobaya": 8,
             "lyuki-i-kryshki": 34, "betonnye-zabory": 34, "bitum-i-asfalt": 19,
             "peregorodochnye-bloki": 19, "opory-i-stoyki": 46,
             "stroitelnaya-himiya": 6, "dresva-i-shlak": 19, "trotuarnaya-plitka": 8, "bordyur": 19, "lotki-vodootvodnye": 34,
             "kolca-zhbi": 34, "stenovye-bloki": 19, "malye-formy": 34,
             "zhbi-izdeliya": 46}
ZHBI_FRAC = {"beton": "щебень 5-20 мм в бетон",
             "kolca-kanalizacionnye": "щебень 20-40 мм на обсыпку",
             "lotki-teplotrass": "щебень 20-40 мм в подготовку",
             "stupeni-betonnye": "щебень 5-20 мм в бетон",
             "trotuarnaya-plitka-razmery": "отсев 0-5 мм под плитку",
             "pechnye-smesi": "песок до 2,5 мм в смесь",
             "reshetki-dozhdepriemnikov": "щебень 20-40 мм под лоток",
             "bordyur-vidy": "щебень 5-20 мм под замок",
             "fbs-bloki": "щебень 20-40 мм в подготовку",
             "dorozhnye-plity": "щебень 20-40 мм в основание",
             "peskobloki": "песок 0-5 мм в раствор",
             "cement-i-smesi": "песок 0-5 мм в раствор",
             "plitka-osobaya": "отсев 0-5 мм под плитку",
             "lyuki-i-kryshki": "щебень 20-40 мм на обвязку",
             "betonnye-zabory": "щебень 20-40 мм под столб",
             "bitum-i-asfalt": "щебень 5-20 мм в обработку",
             "peregorodochnye-bloki": "песок 0-5 мм в раствор",
             "opory-i-stoyki": "скальный грунт под опору",
             "stroitelnaya-himiya": "песок до 2,5 мм в смесь",
             "dresva-i-shlak": "дресва 2-40 мм", "trotuarnaya-plitka": "отсев 0-5 мм под плитку",
             "bordyur": "щебень 5-20 мм под замок",
             "lotki-vodootvodnye": "щебень 20-40 мм под ложе",
             "kolca-zhbi": "щебень 20-40 мм на фильтр",
             "stenovye-bloki": "щебень 5-20 мм в раствор",
             "malye-formy": "щебень 20-40 мм под основание",
             "zhbi-izdeliya": "щебень 20-40 мм в подготовку"}
ZHBI_ART = {
 "kolca-kanalizacionnye": [("/dostavka/kolca-zhbi/", "Кольца ЖБИ: все размеры"),
                           ("/dostavka/stati/kolca-zhbi-razmery/", "Кольца: размеры, вес, объём"),
                           ("/dostavka/lyuki-i-kryshki/", "Люки и крышки")],
 "lotki-teplotrass": [("/dostavka/zhbi-izdeliya/", "ЖБИ: плиты, перемычки, опоры"),
                      ("/dostavka/lotki-vodootvodnye/", "Водоотводные лотки"),
                      ("/dostavka/stati/frakcii-shchebnya/", "Фракции щебня в подготовку")],
 "stupeni-betonnye": [("/dostavka/beton/m250/", "Бетон М250"),
                      ("/dostavka/malye-formy/", "Бетонные малые формы"),
                      ("/dostavka/stati/marki-betona/", "Марки бетона")],
 "trotuarnaya-plitka-razmery": [("/dostavka/trotuarnaya-plitka/", "Тротуарная плитка: цены и виды"),
                                ("/dostavka/stati/vybrat-trotuarnuyu-plitku/", "Какую плитку выбрать"),
                                ("/dostavka/stati/ukladka-trotuarnoy-plitki/", "Укладка плитки"),
                                ("/dostavka/stati/behaton/", "Бехатон: что это")],
 "pechnye-smesi": [("/dostavka/stati/pechnoy-rastvor/", "Печной раствор: какой куда идёт"),
                   ("/dostavka/cement-i-smesi/", "Цемент и сухие смеси"),
                   ("/dostavka/stati/rastvor-proporcii/", "Раствор: пропорции и расход")],
 "dozhdepriemniki": [("/dostavka/reshetki-dozhdepriemnikov/", "Решётки к дождеприёмникам"),
                     ("/dostavka/stati/lotki-i-dozhdepriemniki/", "Лотки и дождеприёмники: монтаж"),
                     ("/dostavka/lotki-vodootvodnye/", "Водоотводные лотки")],
 "reshetki-dozhdepriemnikov": [("/dostavka/dozhdepriemniki/", "Дождеприёмники: размеры и глубина"),
                               ("/dostavka/lotki-vodootvodnye/", "Водоотводные лотки"),
                               ("/dostavka/stati/lotki-i-dozhdepriemniki/", "Лотки и дождеприёмники: монтаж"),
                               ("/dostavka/lyuki-i-kryshki/", "Люки и крышки")],
 "bordyur-vidy": [("/dostavka/stati/sadovyy-bordyur/", "Садовый бордюр: высота и заглубление"),
                  ("/dostavka/bordyur/", "Бордюр и поребрик: цены"),
                  ("/dostavka/stati/ustanovka-bordyura/", "Установка бордюра"),
                  ("/dostavka/stati/razmery-bordyurov/", "Размеры и вес бордюров")],
 "fbs-bloki": [("/dostavka/zhbi-izdeliya/", "ЖБИ: плиты, перемычки, опоры"),
               ("/dostavka/stati/marki-betona/", "Марки бетона"),
               ("/dostavka/stati/frakcii-shchebnya/", "Фракции щебня в подготовку")],
 "dorozhnye-plity": [("/dostavka/zhbi-izdeliya/", "ЖБИ: плиты, перемычки, опоры"),
                     ("/dostavka/stati/frakcii-shchebnya/", "Фракции щебня в основание"),
                     ("/dostavka/stati/koefficient-uplotneniya/", "Коэффициент уплотнения")],
 "peskobloki": [("/dostavka/stenovye-bloki/", "Стеновые блоки"),
                ("/dostavka/peregorodochnye-bloki/", "Перегородочные блоки"),
                ("/dostavka/stati/rastvor-proporcii/", "Кладочный раствор")],
 "cement-i-smesi": [("/dostavka/stati/kladochnaya-smes/", "Кладочная смесь: марки и расход"),
                    ("/dostavka/stati/nalivnoy-pol/", "Наливной пол и ровнитель"),
                    ("/dostavka/stati/cement-m400-i-m500/", "Цемент М400 и М500: расход"),
                    ("/dostavka/stati/rastvor-proporcii/", "Раствор: пропорции и расход"),
                    ("/dostavka/stati/marki-betona/", "Марки бетона")],
 "plitka-osobaya": [("/dostavka/stati/taktilnaya-plitka/", "Тактильная плитка: типы рифов и ГОСТ"),
                    ("/dostavka/stati/ukladka-trotuarnoy-plitki/", "Укладка тротуарной плитки"),
                    ("/dostavka/stati/vybrat-trotuarnuyu-plitku/", "Какую плитку выбрать"),
                    ("/dostavka/stati/behaton/", "Бехатон: что это")],
 "lyuki-i-kryshki": [("/dostavka/stati/kolca-zhbi-razmery/", "Кольца ЖБИ: размеры и вес"),
                     ("/dostavka/stati/lotki-i-dozhdepriemniki/", "Лотки и дождеприёмники")],
 "betonnye-zabory": [("/dostavka/stati/marki-betona/", "Марки бетона для столбов"),
                     ("/dostavka/stati/frakcii-shchebnya/", "Фракции щебня под подсыпку")],
 "bitum-i-asfalt": [("/dostavka/stati/holodnyy-asfalt/", "Холодный асфальт: когда работает"),
                    ("/dostavka/stati/frakcii-shchebnya/", "Фракции щебня в основание")],
 "peregorodochnye-bloki": [("/dostavka/stati/arbolit-i-polistirolbeton/", "Арболит и полистиролбетон"),
                           ("/dostavka/stati/rastvor-proporcii/", "Кладочный раствор")],
 "opory-i-stoyki": [("/dostavka/stati/skalnyy-grunt-dresva-but/", "Скальный грунт под опоры"),
                    ("/dostavka/stati/marki-betona/", "Марки бетона")],
 "stroitelnaya-himiya": [("/dostavka/stati/gidroizolyaciya-betona/", "Гидроизоляция бетона"),
                         ("/dostavka/stati/propitki-dlya-betona/", "Пропитки и упрочнители"),
                         ("/dostavka/stati/remontnye-smesi-dlya-betona/", "Ремонтные смеси")],
 "dresva-i-shlak": [("/dostavka/stati/skalnyy-grunt-dresva-but/", "Скальный грунт, дресва и бут"),
                    ("/dostavka/stati/chem-otsypat-uchastok/", "Чем отсыпать участок")],
 "beton": [("/dostavka/beton/cena-za-kub/", "Куб бетона: цена, вес, объём"),
           ("/dostavka/beton/m150/", "Бетон М150: пол по грунту"),
           ("/dostavka/beton/m100/", "Бетон М100 и тощий бетон"),
           ("/dostavka/beton/m300/", "Бетон М300"),
           ("/dostavka/beton/m200/", "Бетон М200"),
           ("/dostavka/beton/betononasos/", "Бетононасос: когда нужен"),
           ("/dostavka/stati/marki-betona/", "Марки бетона: какая под что"),
           ("/dostavka/stati/skolko-betona-v-miksere/", "Сколько бетона в миксере")],
 "trotuarnaya-plitka": [("/dostavka/stati/uzory-plitki/", "Формы и узоры плитки"),
                        ("/dostavka/stati/cvet-trotuarnoy-plitki/", "Цвет плитки: что держится"),
                        ("/dostavka/stati/shvy-trotuarnoy-plitki/", "Швы плитки: чем засыпать"),
                        ("/dostavka/stati/granitnaya-bruschatka/", "Гранитная брусчатка"),
                        ("/dostavka/stati/ukladka-trotuarnoy-plitki/", "Укладка тротуарной плитки"),
                        ("/dostavka/stati/vybrat-trotuarnuyu-plitku/", "Какую плитку выбрать"),
                        ("/dostavka/stati/pesok-pod-plitku/", "Сколько песка и отсева под плитку")],
 "bordyur": [("/dostavka/stati/ustanovka-bordyura/", "Установка бордюра: порядок и расход"),
             ("/dostavka/stati/razmery-bordyurov/", "Размеры и вес бордюров")],
 "lotki-vodootvodnye": [("/dostavka/stati/lotki-i-dozhdepriemniki/", "Лотки и дождеприёмники: монтаж")],
 "kolca-zhbi": [("/dostavka/stati/kolca-zhbi-razmery/", "Кольца ЖБИ: размеры, вес, объём")],
 "stenovye-bloki": [("/dostavka/stati/arbolit-i-polistirolbeton/", "Арболит и полистиролбетон"),
                    ("/dostavka/stati/rastvor-proporcii/", "Кладочный раствор: пропорции")],
 "malye-formy": [("/dostavka/stati/frakcii-shchebnya/", "Фракции щебня под основание")],
 "zhbi-izdeliya": [("/dostavka/stati/marki-betona/", "Марки бетона"),
                   ("/dostavka/stati/frakcii-shchebnya/", "Фракции щебня под подготовку")],
}

MAT_ART = {'shcheben': [('/dostavka/stati/podushka-pod-fundament/', 'Подушка под фундамент: щебень или песок'),
                 ('/dostavka/stati/materialy-na-dom-po-etapam/', 'Материалы на дом по этапам'),
                 ('/dostavka/stati/frakcii-shchebnya/', 'Фракции щебня: какая под какую задачу'), ('/dostavka/stati/gost-na-shcheben-i-pesok/', 'ГОСТ на щебень и песок: что спрашивать')],
    'pesok': [('/dostavka/pesok/mytyy/', 'Мытый песок: карьеры и цена за тонну'),
              ('/dostavka/pesok/v-meshkah/', 'Песок в мешках и биг-бэгах'),
              ('/dostavka/pesok/peskostruynyy/', 'Пескоструйный песок'),
              ('/dostavka/stati/modul-krupnosti-peska/', 'Модуль крупности песка'), ('/dostavka/stati/gost-na-shcheben-i-pesok/', 'ГОСТ на щебень и песок: что спрашивать')],
    'otsev': [('/dostavka/otsev/v-meshkah/', 'Отсев в мешках и биг-бэгах'),
              ('/dostavka/stati/otsev-gde-primenyat/', 'Отсев 0-5: где применяют и чем заменить'), ('/dostavka/stati/frakcii-shchebnya/', 'Фракции щебня: какая под какую задачу')],
    'pgs': [('/dostavka/stati/pgs-ili-opgs/', 'ПГС и ОПГС: чем отличаются'), ('/dostavka/stati/skalnyy-grunt-dresva-but/', 'Скальный грунт, дресва и бут')],
    'keramzit': [('/dostavka/stati/keramzit-frakcii-i-ves/', 'Керамзит: фракции, вес и где выгоден')],
    'skalnyy-grunt': [('/dostavka/stati/skalnyy-grunt-klassifikaciya/', 'Скальный грунт: классификация и разработка'),
                      ('/dostavka/stati/skalnyy-grunt-dresva-but/', 'Скальный грунт, дресва и бут'), ('/dostavka/stati/pgs-ili-opgs/', 'ПГС и ОПГС: чем отличаются')],
    'butovyy-kamen': [('/dostavka/stati/skalnyy-grunt-dresva-but/', 'Скальный грунт, дресва и бут')],
    'graviy': [('/dostavka/stati/frakcii-shchebnya/', 'Фракции щебня: какая под какую задачу')],
    'shchps': [('/dostavka/stati/pgs-ili-opgs/', 'ПГС и ОПГС: чем отличаются')],
    'granitnaya-kroshka': [('/dostavka/stati/otsev-gde-primenyat/', 'Отсев 0-5: где применяют')],
    'asfaltovaya-kroshka': [('/dostavka/stati/skalnyy-grunt-dresva-but/', 'Чем отсыпать дёшево')]}

MONEY_LOW_PRICE = {"shcheben": "600", "pesok": "990", "otsev": "500", "pgs": "500"}

for slug, mc in money_cfg.items():
    mat = MATERIALS[slug]
    url = SITE["base"] + slug + "/"
    crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]), (mat["name"], None)]
    _ph = photos_for(slug)
    jl = graph(localbusiness(), bc_schema(crumb_items), faq_schema(mat["faq"]),
               product_schema(mat["name"], mc["desc"], MONEY_LOW_PRICE[slug], url,
                              images=product_images(slug)))
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
    # Ссылка в раздел калькуляторов первой строкой: страница расчёта
    # продолжает товарную, а не конкурирует с ней, и человек, который
    # ещё не знает объём, уходит считать к нам, а не на чужой сайт.
    _calcrel = ([(CALCHUB_URL + slug + "/", "Калькулятор " + CALC_BY_SLUG[slug]["name"])]
                if slug in CALC_BY_SLUG else [])
    rel = _calcrel + MAT_ART.get(slug, []) + (PESOK_GEO if slug == "pesok" else []) + (SREDNEURALSK if slug == "shcheben" else []) + rel
    _calc = calc_for(slug)
    # Пересчёт в тонну дописывается к общей сноске под прайсом там, где
    # у материала есть насыпная плотность. Где её нет, строки не будет.
    _tn = ton_note(slug)
    _ctx = dict(BASE_CTX)
    if _tn:
        _ctx["price_note"] = _ctx["price_note"] + " " + _tn
    htmlp = env.get_template("money.j2").render(
        **_ctx, **mc, calc=_calc, has_calc=bool(_calc),
        canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items), jsonld=jl,
        intro=mat["intro"], types=mat["types"], fractions=mat.get("fractions"),
        fractions_head=mat.get("fractions_head"),
        fractions_caption=mat.get("fractions_caption"),
        fractions_col1=mat.get("fractions_col1"),
        frac_href=(FRAC_HREF if slug == "shcheben" else None),
        tasks=mat.get("tasks"), tasks_head=mat.get("tasks_head"),
        specs=mat.get("specs"), specs_head=mat.get("specs_head"),
        packs=mat.get("packs"), packs_head=mat.get("packs_head"),
        quick=mat.get("quick"), hero_price=hero_price_for(slug),
        shelf_rows=catalog_for(slug),
        cross=cross_for(slug), payment=PAYMENT, zones=zones_for(),
        # Готовые объёмы пока только по щебню: прайс партнёра даёт их
        # именно для него, а придумывать те же числа под песок нельзя.
        #
        # По песку такие строки в прайсе есть, но снять их со скриншота
        # не вышло: разбивка по объёмам не сходится с уже опубликованной
        # по щебню (доставка восьми кубов выходит то 1840 рублей, то 4680),
        # а числа этого порядка не публикуются по догадке. Ждём прайс файлом.
        lots=(LOTS if slug == "shcheben" else None),
        lots_head=LOTS_HEAD, lots_note=LOTS_NOTE,
        # Таблица карьеров пока только у песка: происхождение влияет
        # на цену и на выбор именно здесь, у щебня в прайсе партнёра
        # порода и карьер по строкам не разнесены.
        quarries=(PESOK_QUARRIES if slug == "pesok" else None),
        quarries_head=PESOK_QUARRIES_HEAD, quarries_note=PESOK_QUARRIES_NOTE,
        faq=mat["faq"], hero_cell=HERO_CELL.get(slug, 34),
        **_photo_ctx(slug, _ph, "Как выглядит " + mc["mat_vin"]),
        **hero_ctx(slug),
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
        **BASE_CTX, **hero_ctx("shcheben"), city=c, canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items), jsonld=jl,
        lots=(city_lots(CITY_FACTS[c["slug"]]["km"])[0] if c["slug"] in CITY_FACTS else None),
        lots_note=(city_lots(CITY_FACTS[c["slug"]]["km"])[1] if c["slug"] in CITY_FACTS else None),
        plecho_km=CITY_FACTS.get(c["slug"], {}).get("km"),
        title=f"Доставка щебня {c['prep']}: цена за куб самосвалом",
        desc=f"Доставка щебня {c['prep']} и в район ({c['dist']}). Гранит, известняк, фракции 20-40, 40-70. Цена за куб, оплата после выгрузки.",
        h1=f"Доставка щебня {c['prep']}",
        hero_sub=f"Щебень всех фракций с доставкой {c['prep']} и в район. {ucfirst(c['dist'])}. "
                 f"Самосвалы от 5 до 20 кубов, {SITE['payment_short']}",
        faq=cfaq, related_links=rel[:12])
    pages.append((url, htmlp, "geo"))

# ---- ГЕО: материал × город, генерация по матрице ----
#
# Страниц песка по городам было три против тридцати трёх у щебня,
# а у отсева, керамзита, гравия и ПГС - ни одной, хотя в матрице
# материалов они стоят у восемнадцати, двенадцати, трёх и одного города.
# Запрос «отсев с доставкой в Ревду» уходил на общую страницу материала
# или на городскую страницу щебня, где отсев - один блок из пяти.
#
# Страницы, написанные руками, генератор пропускает: они подробнее.
# Остальные собираются из той же фактуры, что и городские страницы
# щебня - CITY_FACTS, MAT_TASK по типу города, LOCAL, plecho
# и example_for. Ничего нового не выдумывается.
GEO_MAT = [
    # (ключ матрицы, ключ прайса, родительный, винительный, слаг калькулятора)
    ("pesok",    "Песок карьерный (сеяный)", "песка",    "песок",    "pesok"),
    ("otsev",    "Отсев 0-5",                "отсева",   "отсев",    "otsev"),
    ("keramzit", "Керамзит",                 "керамзита", "керамзит", "keramzit"),
    ("graviy",   "Гравий",                   "гравия",   "гравий",   "graviy"),
    ("pgs",      "ПГС",                      "ПГС",      "ПГС",      "pgs"),
]
_HAND_MADE = {("pesok", c["slug"]) for c in PESOK_CITIES}

# Какие материалы вообще имеют городскую страницу в каждом городе.
# Считается заранее, до отрисовки: ссылка «в этом же городе» должна
# вести на существующий адрес, а не на предполагаемый.
CITY_HAS = {}
for _mk, _pk, _rod, _vin, _cs in []:
    pass
_GEO_MAT_PRE = [("pesok", "песка"), ("otsev", "отсева"), ("keramzit", "керамзита"),
                ("graviy", "гравия"), ("pgs", "ПГС")]
for _mk, _rod in _GEO_MAT_PRE:
    for _cs, _mats in MATRIX.items():
        if _mk in _mats and _cs in CITY_FACTS:
            CITY_HAS.setdefault(_cs, []).append((_mk, _rod))


def gen_mat_city(mkey, price_key, rod, vin, calc_slug):
    """Городские страницы одного материала по матрице."""
    forms = MAT_FORMS[mkey]
    base = SITE["base"] + forms["url"] + "/"
    low = FLOOR[price_key]
    cities = [cs for cs, mats in MATRIX.items()
              if mkey in mats and (mkey, cs) not in _HAND_MADE and cs in CITY_FACTS]
    cities.sort(key=lambda cs: CITY_FACTS[cs]["km"])
    for i, cs in enumerate(cities):
        f = CITY_FACTS[cs]
        url = base + cs + "/"
        autolink.reset(url)
        pl = plecho(f["km"])
        ex = example_for(mkey, cs, f["km"])
        dist = "около %d км от Екатеринбурга" % f["km"]
        place = dict(slug=cs, name=f["name"], prep=f["prep"], loc=f["loc"], dist=dist,
                     terms="Машину ставим в график %s" % pl["term"],
                     min_note=pl["minv"])
        crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]),
                       (forms["name"], base), (f["name"], None)]
        cfaq = geo_faq(place, rod, vin)[:4] + [
            ("Какой %s берут %s?" % (rod, f["loc"]), MAT_TASK[(mkey, f["kind"])]),
            ("Сколько %s войдёт в машину %s?" % (rod, f["prep"]),
             "Самосвалы от пяти до двадцати кубов. %s" % pl["minv"]),
        ]
        jl = graph(localbusiness(), bc_schema(crumb_items), faq_schema(cfaq),
                   product_schema("Доставка %s %s" % (rod, f["prep"]),
                                  "%s с доставкой %s, %s."
                                  % (forms["name"], f["prep"], dist),
                                  str(low), url, images=product_images(forms["url"])))
        sections = [
            {"id": "plecho", "h": "Доставка %s %s: плечо и цена" % (rod, f["prep"]),
             "p": ["Возим %s %s по %s, %s. %s %s"
                   % (vin, f["prep"], f["tract"], dist, pl["econ"], pl["minv"]),
                   "Срок подачи машины %s. Плечо оплачивается в обе стороны: "
                   "машина едет к вам и возвращается порожняком. Точную сумму "
                   "называем по заявке." % pl["term"]]},
            {"id": "kuda", "h": "Куда возим %s и в район" % f["prep"],
             "p": ["Доставляем в %s. По дальним адресам района считаем километраж "
                   "отдельно и стараемся совместить с попутным рейсом." % f["areas"]]},
            {"id": "chto", "h": "Какой %s берут %s" % (rod, f["loc"]),
             "p": [MAT_TASK[(mkey, f["kind"])],
                   "Чаще всего это %s." % ANGLE[(mkey, f["kind"])]]},
            {"id": "raschet", "h": "Пример расчёта %s" % f["loc"],
             "p": ["Типовая задача %s это %s. На %s это %s кубометра по геометрии; "
                   "с коэффициентом уплотнения %s выходит %s. %s Повезёт %s."
                   % (f["loc"], ex["task"], ex["dims"], ex["geom"], ex["k"],
                      ex["real"], ex["note"], ex["truck"])],
             "after": ["Свой объём посчитайте в калькуляторе: он считает по размерам "
                       "площадки, переводит кубы в тонны и показывает цену с доставкой."]},
            {"id": "mestnoe", "h": "Местные особенности %s" % f["loc"],
             "p": [LOCAL[cs],
                   "Грунты здесь это %s, и от них зависит, сколько материала уйдёт "
                   "в основание сверх расчёта." % f["ground"]]},
            {"id": "kak-zakazat", "h": "Как заказать %s %s" % (vin, f["prep"]),
             "steps": ["Скажите фракцию и объём в кубах.",
                       "Назовите адрес %s и опишите заезд: ширина ворот и место "
                       "для разворота." % f["loc"],
                       "Получите точную цену с доставкой. %s."
                       % SITE["callback_promise"].capitalize(),
                       "Принимаете машину на объекте и проверяете объём. %s"
                       % SITE["payment"]]},
        ]
        _lots, _lnote = city_lots(f["km"], price_key)
        nbrs = cities[i + 1:] + cities[:i]
        rel = ([(base, "Доставка %s: виды и цены" % rod),
                (CALCHUB_URL + calc_slug + "/", "Калькулятор %s" % rod),
                ("/dostavka/shcheben/%s/" % cs, "Доставка щебня %s" % f["prep"])]
               + [(base + o + "/", "Доставка %s %s" % (rod, CITY_FACTS[o]["prep"]))
                  for o in nbrs][:4]
               # В этом же городе: остальные материалы, у которых страница
               # по нему есть. Для гравия это единственный источник входящих
               # ссылок кроме соседей - городов с гравием всего три.
               + [("%s%s/%s/" % (SITE["base"], MAT_FORMS[m]["url"], cs),
                   "Доставка %s %s" % (r, f["prep"]))
                  for m, r in CITY_HAS.get(cs, []) if m != mkey]
               + [("/dostavka/shcheben/", "Доставка щебня"),
                  ("/dostavka/pesok/", "Доставка песка"),
                  ("/dostavka/otsev/", "Отсев 0-5"),
                  ("/dostavka/pgs/", "ПГС и ОПГС"),
                  ("/dostavka/stati/cena-kuba-s-dostavkoy/", "Цена за куб с доставкой"),
                  ("/dostavka/", "Все города и материалы")])
        htmlp = env.get_template("geoplus.j2").render(
            **BASE_CTX, **hero_ctx(forms["url"]), place=place,
            canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items), jsonld=jl,
            title="Доставка %s %s: цена за куб самосвалом" % (rod, f["prep"]),
            desc=("Доставка %s %s и в район (%s). Цена от %d руб за куб, "
                  "самосвалы от 5 кубов, оплата после выгрузки."
                  % (rod, f["prep"], dist, low)),
            h1="Доставка %s %s" % (rod, f["prep"]),
            hero_sub=("%s с доставкой %s и в район. %s. Самосвалы от 5 кубов, %s"
                      % (forms["name"], f["prep"], ucfirst(dist), SITE["payment_short"])),
            lead=("Возим %s %s и по району, %s. Цену считаем за кубометр "
                  "с доставкой на ваш адрес, %s"
                  % (vin, f["prep"], dist, SITE["payment_short"])),
            sections=sections, cta_after=3,
            lots=_lots, lots_note=_lnote, plecho_km=f["km"],
            calc_slug=calc_slug, calc_rod=rod,
            cta_head="Посчитаем объём %s" % f["loc"],
            cta_text=("Назовите размеры участка работ и адрес, подберём фракцию "
                      "и машину, назовём итоговую цену с доставкой."),
            subject="%s, %s" % (vin, f["name"]), faq=cfaq,
            related_links=list(dict.fromkeys(rel))[:14])
        pages.append((url, htmlp, "geo-" + mkey))


for _mk, _pk, _rod, _vin, _cslug in GEO_MAT:
    gen_mat_city(_mk, _pk, _rod, _vin, _cslug)

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
        **BASE_CTX, **hero_ctx("pesok"), place=c, canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items), jsonld=jl,
        title=f"Доставка песка {c['prep']}: цена за куб, карьерный и речной",
        desc=f"Доставка песка {c['prep']} и в район ({c['dist']}). Карьерный под отсыпку, речной мытый под бетон. Цена за куб, оплата после выгрузки.",
        h1=f"Доставка песка {c['prep']}",
        hero_sub=f"Карьерный и речной песок с доставкой {c['prep']} и в район. {ucfirst(c['dist'])}. "
                 f"Самосвалы от 5 кубов, {SITE['payment_short']}",
        lead=f"Возим песок {c['prep']} и по району, {c['dist']}. Карьерный идёт под отсыпку и "
             f"обратную засыпку, речной мытый под бетон и кладку. Цену считаем за кубометр "
             f"с доставкой на ваш адрес, {SITE['payment_short']}",
        sections=sections, cta_after=3,
        lots=(city_lots(CITY_FACTS[c["slug"]]["km"], "Песок карьерный (сеяный)")[0]
              if c["slug"] in CITY_FACTS else None),
        lots_note=(city_lots(CITY_FACTS[c["slug"]]["km"], "Песок карьерный (сеяный)")[1]
                   if c["slug"] in CITY_FACTS else None),
        plecho_km=CITY_FACTS.get(c["slug"], {}).get("km"),
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

# Семейство прайса берётся из явной таблицы. Незнакомый слаг не угадываем
# по подстроке: угадывание отправило бы «отсев» в песок, а «цемент М400
# и М500» в нерудку. Он падает в nerud и печатается в отчёт сборки.
_NOFAM = []
def CONV_FOR(slug):
    f = FAM.get(slug)
    if f is None:
        _NOFAM.append(slug)
        f = "nerud"
    return f, PRICE_SETS[f]




# Ячейка сита для лонгридов. Раньше все они рисовали 34 пикселя
# и подписывались «щебень 20-40 мм»: на странице карьерного песка
# прибор показывал чужой материал, а подпись называла его щебнем.
# Здесь перечислены страницы песка, остальные остаются на умолчании.
LR_HERO = {
    "pesok/karyernyy":            (6, "песок до 2,5 мм"),
    "pesok/rechnoy":              (6, "песок до 2,5 мм"),
    "pesok/mytyy":                (6, "песок до 2,5 мм"),
    "pesok/peskostruynyy":        (6, "абразив 0,5-2,5 мм"),
    "stati/kakoy-pesok-vybrat":   (6, "песок до 2,5 мм"),
    "stati/klassy-peska":         (6, "песок до 2,5 мм"),
    "stati/modul-krupnosti-peska": (6, "песок до 2,5 мм"),
    "stati/pesok-pod-plitku":     (8, "песок и отсев 0-5 мм"),
}

# Заголовки всех страниц раздела, на которые может ссылаться поле related.
# Раньше карта строилась только по лонгридам, и ссылка на товарную страницу
# молча выбрасывалась: слот доставался ротационному запасному списку,
# а подобранная руками связь исчезала без единого сообщения. Сорок семь
# таких ссылок так и не доехали до вёрстки. Теперь карта включает товарные
# страницы, а неизвестный slug останавливает сборку.
RELATED_TITLE = {}
for _o in LONGREADS:
    RELATED_TITLE[_o["slug"]] = _o["h1"]
# Заголовок товарной страницы лежит не в описании материала, а в конфиге
# денежной страницы: MATERIALS_* хранит содержание, MONEY_CFG_* - обёртку.
for _src in (money_cfg, MONEY_CFG_EXT, MONEY_CFG_ZHBI, MONEY_CFG_BETON,
             MONEY_CFG_GAP, MONEY_CFG_GAP2, MONEY_CFG_GAP3, MONEY_CFG_REV):
    for _k, _v in _src.items():
        if isinstance(_v, dict) and _v.get("h1"):
            RELATED_TITLE.setdefault(_k, _v["h1"])
for _hb in HUBS:
    if _hb.get("slug") and _hb.get("h1"):
        RELATED_TITLE.setdefault(_hb["slug"], _hb["h1"])

_bad_rel = {}
for _a in LONGREADS:
    for _sl in _a.get("related", []):
        if _sl not in RELATED_TITLE:
            _bad_rel.setdefault(_sl, []).append(_a["slug"])
if _bad_rel:
    print("ОШИБКА: related ссылается на несуществующие страницы:")
    for _sl, _who in sorted(_bad_rel.items()):
        print("  %-44s из %s" % (_sl, ", ".join(_who[:3])))
    raise SystemExit(1)

# Даты статей для разметки Article. Раньше и datePublished, и dateModified
# брались из константы TODAY: все статьи заявляли одну и ту же дату,
# включая написанные позже. Для поисковика это ложный сигнал свежести.
# Отпечаток считается по исходным данным статьи, а не по готовой вёрстке:
# перерисовка шаблона не должна выглядеть как правка текста.
_AD_PATH = os.path.join(ROOT, "audit", "article-dates.json")
try:
    _adates = json.load(io.open(_AD_PATH, encoding="utf-8"))
except Exception:
    _adates = {}
_ad_today = datetime.date.today().isoformat()
ARTICLE_DATES = {}
for _a in LONGREADS:
    _src = json.dumps([_a.get(k) for k in ("h1", "lead", "sections", "faq")],
                      ensure_ascii=False, sort_keys=True)
    _fp = hashlib.sha1(_src.encode("utf-8")).hexdigest()[:16]
    _prev = _adates.get(_a["slug"])
    if _prev and _prev.get("fp") == _fp:
        ARTICLE_DATES[_a["slug"]] = _prev
    else:
        ARTICLE_DATES[_a["slug"]] = {
            "fp": _fp,
            "published": (_prev or {}).get("published", _ad_today),
            "modified": _ad_today,
        }
os.makedirs(os.path.dirname(_AD_PATH), exist_ok=True)
json.dump(ARTICLE_DATES, io.open(_AD_PATH, "w", encoding="utf-8"),
          ensure_ascii=False, indent=1, sort_keys=True)

# Ключи разделов, которые умеет рисовать макрос blocks(). Раздел
# «Что проверять в партии независимо от завода» прожил на сайте с ключом ol,
# которого макрос не знал: заголовок печатался, семь пунктов текста - нет.
# Молчаливая потеря содержания страшнее падения сборки, поэтому теперь падаем.
_SEC_KEYS = {"id", "h", "p", "ul", "ol", "steps", "table", "sub", "after",
             "callout", "callout_warn"}
_SUB_KEYS = {"h3", "p", "ul", "table"}
_unknown = {}
for _a in LONGREADS:
    for _s in _a["sections"]:
        for _k in _s:
            if _k not in _SEC_KEYS:
                _unknown.setdefault(_k, []).append(_a["slug"])
        for _sb in _s.get("sub", []):
            for _k in _sb:
                if _k not in _SUB_KEYS:
                    _unknown.setdefault("sub." + _k, []).append(_a["slug"])
if _unknown:
    print("ОШИБКА: макрос не умеет рисовать ключи разделов:")
    for _k, _who in sorted(_unknown.items()):
        print("  %-16s в %s" % (_k, ", ".join(sorted(set(_who))[:3])))
    raise SystemExit(1)

# Ключи, по которым макрос ИТЕРИРУЕТ. Строка вместо списка не падает,
# а тихо печатается по одной букве в абзац: так на новой странице мытого
# песка появилось десять пустых <p> из пробелов между словами. Поймал это
# верификатор, но заметить в вёрстке такое трудно, поэтому останавливаем
# сборку прямо здесь.
_LIST_KEYS = ("p", "ul", "ol", "steps", "after")
_notlist = []
for _a in LONGREADS:
    for _s in _a["sections"]:
        for _k in _LIST_KEYS:
            if isinstance(_s.get(_k), str):
                _notlist.append((_a["slug"], _s.get("id", "?"), _k))
        for _sb in _s.get("sub", []):
            for _k in ("p", "ul"):
                if isinstance(_sb.get(_k), str):
                    _notlist.append((_a["slug"], _s.get("id", "?"), "sub." + _k))
if _notlist:
    print("ОШИБКА: строка вместо списка - макрос напечатает её по буквам:")
    for _sl, _sid, _k in _notlist:
        print("  %s раздел %s ключ %s" % (_sl, _sid, _k))
    raise SystemExit(1)

# ---- ЛОНГРИДЫ (низкоконкурентные ключи Мутагена) ----
for a in LONGREADS:
    url = SITE["base"] + a["slug"] + "/"
    autolink.reset(url)
    if a["slug"].startswith("shcheben/"):
        parent = ("Щебень", SITE["base"] + "shcheben/")
    elif a["slug"].startswith("beton/"):
        parent = ("Бетон", SITE["base"] + "beton/")
    elif a["slug"].startswith("pesok/"):
        parent = ("Песок", SITE["base"] + "pesok/")
    else:
        parent = ("Статьи", None)
    crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]), parent,
                   (a["h1"], None)]
    _fam, _conv = (None, None) if a.get("commercial") else CONV_FOR(a["slug"])
    nodes = [localbusiness(), bc_schema(crumb_items), faq_schema(a["faq"])]
    if _conv:
        _pl = pricelist_schema(_fam, _conv["rows"], url)
        if _pl:
            nodes.append(_pl)
    if a["kind"] == "article":
        _ad = ARTICLE_DATES[a["slug"]]
        nodes.append(article_schema(url, a["title"], a["desc"], AUTHOR_FULL,
                                    _ad["published"], _ad["modified"]))
    if a.get("low_price"):
        nodes.append(product_schema(a["h1"], a["desc"], a["low_price"], url,
                                    images=product_images(a["slug"])))
    jl = graph(*nodes)
    # Сначала явно заданные связи, потом остальные лонгриды.
    # Без этого rel[:12] отрезал всё, что не поместилось: список
    # вырос до 23 статей, и новые становились сиротами - на них
    # не вело ни одной ссылки со всего сайта.
    rel = []
    for sl in a.get("related", []):
        t = RELATED_TITLE.get(sl)
        if t:
            rel.append((SITE["base"] + sl + "/", t))
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
    _calc = calc_for(a["slug"])
    htmlp = env.get_template("longread.j2").render(
        calc=_calc, has_calc=bool(_calc),
        og_type="article" if a["kind"] == "article" else "website",
        **_photo_ctx(a["slug"], photos_for(a["slug"])),
        **BASE_CTX, author=AUTHOR_FULL, updated=UPDATED,
        canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items), jsonld=jl,
        hero_cell=LR_HERO.get(a["slug"], (34, None))[0],
        **hero_ctx(a["slug"]),
        title=a["title"], desc=a["desc"], h1=a["h1"], hero_sub=a["hero_sub"], lead=a["lead"],
        sections=a["sections"], faq=a["faq"], subject=a["subject"], form_head=a["form_head"],
        cta_after=a["cta_after"], cta_head=a["cta_head"], cta_text=a["cta_text"],
        cta_head2=a.get("cta_head2"), cta_text2=a.get("cta_text2"),
        commercial=a.get("commercial", False),
        conv=_conv,
        order_steps=ORDER_STEPS, objections=OBJECTIONS,
        price_head=a.get("price_head", ""), order_head=a.get("order_head", ""),
        related_links=list(dict.fromkeys(rel))[:14])
    pages.append((url, htmlp, "longread"))

# ---- РАЗДЕЛ КАЛЬКУЛЯТОРОВ ----
#
# Отдельный раздел, а не блок внизу товарной. Калькулятор доставки жил
# в подвале товарных страниц и отвечал на один вопрос - сколько отдать.
# А приходят с другим: «сколько кубов на площадку 6 на 4» и «сколько это
# тонн». Человек считал это в уме или на чужом сайте и на чужом оставался.
#
# Все числа - из наших же статей: плотности из «сколько весит куб»,
# коэффициенты из «коэффициента уплотнения», цена из прайса. Ни одного
# нового числа: два калькулятора, считающие один материал по-разному,
# обнуляют доверие к обоим.

def calcpage_ctx(c):
    """Данные калькулятора объёма и перевода тонн для одной страницы."""
    k = max(c["compact"]) if c["compact"] else 1.0
    dens = c["density"]
    price = FLOOR[c["price_key"]]
    rows = []
    for task, ln, wd, layer in c["tasks"]:
        geom = ln * wd * layer / 100.0
        vol = geom * k
        rows.append(dict(
            task=task, size="%s × %s м" % (_fmt(ln), _fmt(wd)), layer=layer,
            vol=_fmt(vol),
            tons=("%s-%s" % (_fmt(vol * dens[0]), _fmt(vol * dens[1]))) if dens else "",
            truck=_truck(vol)))
    tons_rows = []
    if dens:
        mid = (dens[0] + dens[1]) / 2.0
        for m3, t in zip((1, 5, 10, 20), (1, 5, 10, 20)):
            tons_rows.append((_fmt(m3), _fmt(m3 * mid), _fmt(t), _fmt(t / mid)))
    lead = ("Введите размеры площадки и толщину слоя. "
            + ("Объём считается с запасом на уплотнение: коэффициент %s, "
               "то есть привезти надо больше, чем ляжет в готовый слой. "
               % _fmt(k) if k > 1 else
               "Запаса на уплотнение здесь нет: в наших материалах "
               "коэффициента для этого материала не написано, а выдумывать "
               "его нельзя. ")
            + ("Вес считается по насыпной плотности %s т/м³."
               % ("%s-%s" % (_dens(dens[0]), _dens(dens[1]))) if dens else
               "Вес не показываем: насыпной плотности этого материала "
               "в наших материалах нет."))
    note = ("Расчёт ориентировочный. Точный объём зависит от того, "
            "насколько ровное основание и как трамбуется слой: на рыхлом "
            "грунте нижняя часть отсыпки уходит в него и объём растёт. "
            "Посчитаем под ваш объект по размерам и фотографии участка.")
    return dict(
        k=k, price=price, name=c["name"], layer=c["layer"], l=6, w=4,
        dens_lo=dens[0] if dens else None, dens_hi=dens[1] if dens else None,
        dens_s=("%s-%s" % (_dens(dens[0]), _dens(dens[1]))) if dens else "",
        dens_note=c.get("dens_note"),
        lead=lead, note=note, rows=rows, tons_rows=tons_rows,
        caption="Готовые расчёты: сколько %s уходит на типовые задачи" % c["name"])


CALC_METHOD = [
    ("Объём отсыпки",
     ["Объём считается как площадь на толщину слоя: длина умножается "
      "на ширину и на толщину в метрах. Площадка шесть на четыре метра "
      "со слоем двадцать сантиметров это 6 × 4 × 0,2, то есть 4,8 кубометра "
      "в готовом слое.",
      "Дальше вступает уплотнение, и именно на этом шаге чаще всего "
      "ошибаются. Материал в кузове лежит рыхло, а в слое его трамбуют, "
      "и он занимает меньше места. Поэтому привезти надо больше, чем "
      "получилось по геометрии."]),
    ("Коэффициент уплотнения",
     ["Коэффициент показывает, во сколько раз рыхлый объём больше "
      "уплотнённого. У песка это 1,10-1,15, у щебня 20-40 доходит до 1,30. "
      "В расчёте берётся верхняя граница диапазона: недосыпать слой хуже, "
      "чем привезти лишний куб, который всегда есть куда деть.",
      "Полная таблица коэффициентов по материалам разобрана в отдельной "
      "статье, вместе с тем, откуда эти числа берутся и почему у щебня "
      "разброс шире, чем у песка."]),
]

CALC_FAQ_COMMON = [
    ("Насколько точен расчёт калькулятора?",
     "Он даёт объём с запасом на уплотнение и ориентировочную стоимость. "
     "Точный объём зависит от того, насколько ровное основание: на рыхлом "
     "или неровном грунте нижняя часть отсыпки уходит в него, и материала "
     "нужно больше. Пришлите размеры и фотографию участка, посчитаем точнее."),
    ("Почему объём получается больше, чем я посчитал?",
     "Из-за коэффициента уплотнения. В кузове материал лежит рыхло, "
     "в слое его трамбуют, и он занимает меньше места. Разница у щебня "
     "доходит до тридцати процентов: на десять кубов готового слоя "
     "приходится заказывать тринадцать."),
    ("Заказывать в кубах или в тоннах?",
     "В кубах предсказуемее. Вес зависит от влажности: после дождя тот же "
     "объём весит на десять-двадцать процентов больше, и по тоннам вы "
     "заплатите за воду. Объём же меряется по паспорту кузова и не меняется "
     "от погоды."),
    ("Что делать, если объём получился между машинами?",
     "Округлять вверх, если материал ещё где-то пригодится, и вниз, если "
     "нет. Половина кузова стоит почти как целый: рейс оплачивается "
     "целиком. Позвоните, подберём машину под ваш объём."),
]


_calc_quick = [(("Калькулятор " + c["name"]).replace("Калькулятор ПГС", "ПГС")
                .replace("Калькулятор ЩПС", "ЩПС"),
                CALCHUB_URL + c["slug"] + "/") for c in CALC_PAGES]

for _ci, _c in enumerate(CALC_PAGES):
    url = CALCHUB_URL + _c["slug"] + "/"
    autolink.reset(url)
    vc = calcpage_ctx(_c)
    _name = _c["name"]
    h1 = "Калькулятор %s: объём, вес и цена с доставкой" % _name
    crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]),
                   ("Калькуляторы", CALCHUB_URL), (h1, None)]
    # Свои вопросы идут первыми, общий - один и последним. С четырьмя
    # общими вопросами страницы раздела совпадали на 81-84 процента
    # при пороге 80: общий текст перевешивал таблицу задач, которая
    # у каждого материала своя.
    _own_h, _own_p, _own_faq = CALC_OWN[_c["slug"]]
    _faq = [
        ("Сколько %s нужно на площадку?" % _name,
         "Считается как площадь на толщину слоя плюс запас на уплотнение. "
         "Введите длину, ширину и толщину в калькуляторе выше: он покажет "
         "объём с запасом, вес и подходящую машину."),
    ] + _own_faq + CALC_FAQ_COMMON[:1]
    jl = graph(localbusiness(), bc_schema(crumb_items), faq_schema(_faq),
               product_schema("Доставка %s" % _name,
                              "Расчёт объёма и стоимости %s с доставкой по %s."
                              % (_name, SITE["region_dat"]),
                              str(vc["price"]), url,
                              images=product_images(_c["slug"])))
    rel = ([(_c["product"], "Доставка %s: цены и фракции" % _name),
            (CALCHUB_URL, "Все калькуляторы")]
           # Список соседей крутится от текущей страницы, а не от начала.
           # Со срезом [:6] от начала ссылки доставались одним и тем же
           # шести калькуляторам, а хвост списка - дресва, бут, крошка -
           # получал по одной входящей на весь сайт. Ровно эта же ошибка
           # уже ловилась на лонгридах, см. комментарий там.
           + [(CALCHUB_URL + o["slug"] + "/", "Калькулятор " + o["name"])
              for o in (CALC_PAGES[_ci + 1:] + CALC_PAGES[:_ci])][:6]
           + [("/dostavka/stati/koefficient-uplotneniya/", "Коэффициент уплотнения"),
              ("/dostavka/stati/skolko-vesit-kub/", "Сколько весит куб материала"),
              ("/dostavka/stati/skolko-shchebnya-v-kamaze/", "Сколько кубов в КамАЗе"),
              ("/dostavka/", "Все города и материалы")])
    htmlp = env.get_template("calcpage.j2").render(
        **BASE_CTX, **hero_ctx(_c["slug"]),
        canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items), jsonld=jl,
        title="Калькулятор %s онлайн: объём, вес, цена с доставкой" % _name,
        desc=("Калькулятор %s: посчитайте объём по размерам площадки с запасом "
              "на уплотнение, переведите кубы в тонны и узнайте цену с доставкой "
              "по %s." % (_name, SITE["region_dat"])),
        h1=h1,
        hero_sub=("Три расчёта на одной странице: объём по размерам площадки, "
                  "перевод кубометров в тонны и стоимость с доставкой. "
                  "Числа те же, что в наших статьях и в прайсе."),
        hero_price="от %d" % vc["price"], hero_cell=HERO_CELL.get(_c["slug"], 34),
        vc=vc, calc=calc_for(_c["slug"]), has_calc=bool(calc_for(_c["slug"])),
        method=CALC_METHOD + [(_own_h, _own_p)], faq=_faq,
        mat_order="доставку %s" % _name,
        subject="расчёт %s, %s" % (_name, SITE["region_short"]),
        quick=[q for q in _calc_quick if not q[1].endswith("/%s/" % _c["slug"])][:7],
        related_links=list(dict.fromkeys(rel))[:14])
    pages.append((url, htmlp, "calc-page"))

# Хаб раздела
_hub_url = CALCHUB_URL
autolink.reset(_hub_url)
_hub_crumbs = [("Главная", "/"), ("Доставка материалов", SITE["base"]),
               ("Калькуляторы", None)]
_hub_faq = CALC_FAQ_COMMON + [
    ("Для каких материалов есть калькулятор?",
     "Для щебня, песка, отсева, ПГС, ЩПС, скального грунта, керамзита, "
     "гравия, асфальтовой крошки, дресвы, бутового камня и гранитной крошки. "
     "У каждого свой коэффициент уплотнения и своя насыпная плотность, "
     "поэтому один общий калькулятор считал бы всё одинаково и неверно."),
    ("Почему у бута и гранитной крошки не показывается вес?",
     "Потому что насыпной плотности этих материалов нет в наших же "
     "статьях, а подставлять правдоподобное число мы не будем: это тот "
     "вид ошибки, который вскрывается на весах при приёмке. Вес по "
     "конкретной партии скажем по заявке."),
]
_cards = []
for _c in CALC_PAGES:
    _img = img_one(HERO_PHOTO.get(_c["slug"], (None, None))[0]) \
        if HERO_PHOTO.get(_c["slug"]) else None
    _cards.append(dict(name="Калькулятор " + _c["name"],
                       href=CALCHUB_URL + _c["slug"] + "/", img=_img,
                       alt="%s, фотография материала" % _c["vin"],
                       price="от %d" % FLOOR[_c["price_key"]],
                       use="Объём по размерам, вес в тоннах, цена с доставкой."))
htmlp = env.get_template("calchub.j2").render(
    **BASE_CTX, **hero_ctx("shcheben"),
    canonical=DOMAIN + _hub_url, crumbs_html=crumbs(_hub_crumbs),
    jsonld=graph(localbusiness(), bc_schema(_hub_crumbs), faq_schema(_hub_faq)),
    title="Калькуляторы нерудных материалов: объём, вес и цена с доставкой",
    desc=("Калькуляторы щебня, песка, отсева, ПГС и других материалов. "
          "Объём по размерам площадки с запасом на уплотнение, перевод кубов "
          "в тонны, стоимость с доставкой по " + SITE["region_dat"] + "."),
    h1="Калькуляторы объёма, веса и стоимости",
    hero_sub=("Двенадцать материалов, у каждого своя насыпная плотность "
              "и свой коэффициент уплотнения. Считаем по тем же числам, "
              "что стоят в наших статьях и в прайсе."),
    cards=_cards, method=CALC_METHOD, faq=_hub_faq,
    subject="расчёт материала, " + SITE["region_short"],
    related_links=[("/dostavka/shcheben/", "Доставка щебня"),
                   ("/dostavka/pesok/", "Доставка песка"),
                   ("/dostavka/otsev/", "Отсев 0-5"),
                   ("/dostavka/pgs/", "ПГС и ОПГС"),
                   ("/dostavka/stati/koefficient-uplotneniya/", "Коэффициент уплотнения"),
                   ("/dostavka/stati/skolko-vesit-kub/", "Сколько весит куб материала"),
                   ("/dostavka/stati/skolko-shchebnya-nuzhno/", "Сколько щебня нужно"),
                   ("/dostavka/", "Все города и материалы")])
pages.append((_hub_url, htmlp, "calc-hub"))

# ---- НОВЫЕ ТОВАРНЫЕ СТРАНИЦЫ (керамзит, гравий, крошка, скала, ЩПС, бут) ----
for slug, mc in MONEY_CFG_EXT.items():
    mat = MATERIALS_EXT[slug]
    url = SITE["base"] + slug + "/"
    crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]),
                   (mat["name"], None)]
    jl = graph(localbusiness(), bc_schema(crumb_items), faq_schema(mat["faq"]),
               product_schema(mat["name"], mc["desc"], mc["low"], url,
                              images=product_images(slug)))
    # Соседние материалы идут ПЕРВЫМИ, а не после общих ссылок.
    # Со срезом rel[:14] они частью не помещались, и гранитная крошка
    # осталась с двумя входящими на весь сайт при норме от трёх.
    rel = [("/dostavka/" + o + "/", MATERIALS_EXT[o]["name"] + " с доставкой")
           for o in MONEY_CFG_EXT if o != slug]
    rel += [("/dostavka/shcheben/", "Доставка щебня"),
           ("/dostavka/pesok/", "Доставка песка"),
           ("/dostavka/otsev/", "Отсев 0-5"),
           ("/dostavka/pgs/", "ПГС и ОПГС"),
           ("/dostavka/stati/skolko-vesit-kub/", "Сколько весит куб материала"),
           ("/dostavka/stati/koefficient-uplotneniya/", "Коэффициент уплотнения"),
           ("/dostavka/", "Все города и материалы")]
    rel += [("/dostavka/" + o + "/", MATERIALS_EXT[o]["name"] + " с доставкой")
            for o in MONEY_CFG_EXT if o != slug]
    # Ссылка в раздел калькуляторов первой строкой: страница расчёта
    # продолжает товарную, а не конкурирует с ней, и человек, который
    # ещё не знает объём, уходит считать к нам, а не на чужой сайт.
    _calcrel = ([(CALCHUB_URL + slug + "/", "Калькулятор " + CALC_BY_SLUG[slug]["name"])]
                if slug in CALC_BY_SLUG else [])
    rel = _calcrel + MAT_ART.get(slug, []) + (PESOK_GEO if slug == "pesok" else []) + (SREDNEURALSK if slug == "shcheben" else []) + rel
    _calc = calc_for(slug)
    htmlp = env.get_template("money.j2").render(
        **BASE_CTX, calc=_calc, has_calc=bool(_calc), canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items),
        jsonld=jl, title=mc["title"], desc=mc["desc"], h1=mc["h1"],
        hero_sub=mc["hero_sub"], mat_vin=mc["mat_vin"], mat_rod=mc["mat_rod"],
        mat_order=mc["mat_order"], subject=mc["mat_vin"] + ", " + SITE["region_short"],
        intro=mat["intro"], types=mat["types"], fractions=mat.get("fractions"),
        # Задачи, характеристики и фасовка появились у этих материалов
        # после разбора: без них страница была на полторы тысячи слов
        # против трёх у щебня, и разница приходилась ровно на те блоки,
        # которые отвечают на «мне такой или другой» и «сколько весит».
        tasks=mat.get("tasks"), tasks_head=mat.get("tasks_head"),
        specs=mat.get("specs"), specs_head=mat.get("specs_head"),
        packs=mat.get("packs"), packs_head=mat.get("packs_head"),
        quick=mat.get("quick"), shelf_rows=catalog_for(slug),
        cross=cross_for(slug), payment=PAYMENT, zones=zones_for(),
        quarries=None, lots=None, lots_head=LOTS_HEAD, lots_note=LOTS_NOTE,
        hero_price=("от %d" % FLOOR[CALC_BY_SLUG[slug]["price_key"]]
                    if slug in CALC_BY_SLUG else None),
        faq=mat["faq"], related_links=list(dict.fromkeys(rel))[:14], hero_cell=HERO_CELL.get(slug, 34),
        **_photo_ctx(slug, photos_for(slug), "Как выглядит " + mc["mat_vin"]),
        **hero_ctx(slug))
    pages.append((url, htmlp, "money-ext"))

# ---- ТОВАРНЫЕ СТРАНИЦЫ ПОД КОММЕРЧЕСКИЙ СПРОС БЕЗ СВОЕГО ТОВАРА ----
# Плитка, бордюр, лотки, кольца, блоки, малые формы и ЖБИ. Продаются
# штуками и метрами, а не кубами, поэтому единицы измерения приходят
# из конфига, а не зашиты в money.j2.
# К какой рубрике относится товарная страница. Ссылка снизу вверх
# обязательна: без неё хаб остаётся сиротой при живых детях, и это
# ровно то, что поймала группа 20 при первой сборке.
_RUBRIC_OF = {}
for _s in ("kolca-zhbi", "kolca-kanalizacionnye", "lotki-vodootvodnye",
           "dozhdepriemniki", "reshetki-dozhdepriemnikov", "lyuki-i-kryshki",
           "lotki-teplotrass", "fbs-bloki", "zhbi-izdeliya", "dorozhnye-plity"):
    _RUBRIC_OF[_s] = [("/dostavka/zhbi-i-vodootvod/", "ЖБИ и водоотвод: весь раздел")]
for _s in ("trotuarnaya-plitka", "trotuarnaya-plitka-razmery", "plitka-osobaya",
           "bordyur", "bordyur-vidy", "malye-formy", "betonnye-zabory",
           "stupeni-betonnye"):
    _RUBRIC_OF[_s] = [("/dostavka/blagoustroystvo/", "Благоустройство: весь раздел")]

_ZHBI_ALL = dict(MONEY_CFG_ZHBI); _ZHBI_ALL.update(MONEY_CFG_BETON); _ZHBI_ALL.update(MONEY_CFG_GAP); _ZHBI_ALL.update(MONEY_CFG_GAP2); _ZHBI_ALL.update(MONEY_CFG_GAP3); _ZHBI_ALL.update(MONEY_CFG_REV)
_MAT_ALL = dict(MATERIALS_ZHBI); _MAT_ALL.update(MATERIALS_BETON); _MAT_ALL.update(MATERIALS_GAP); _MAT_ALL.update(MATERIALS_GAP2); _MAT_ALL.update(MATERIALS_GAP3); _MAT_ALL.update(MATERIALS_REV)
for slug, mc in _ZHBI_ALL.items():
    mat = _MAT_ALL[slug]
    url = SITE["base"] + slug + "/"
    crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]),
                   (mat["name"], None)]
    jl = graph(localbusiness(), bc_schema(crumb_items), faq_schema(mat["faq"]),
               product_schema(mat["name"], mc["desc"], mc["low"], url,
                              images=product_images(slug)))
    # Список соседей крутится от текущей страницы, а не от начала.
    # Иначе при обрезке на 14 последние товарные страницы не получают
    # ни одной входящей ссылки: ровно та же ошибка, что уже была
    # с лонгридами и стоила семи сирот.
    _keys = list(_ZHBI_ALL)
    _i = _keys.index(slug)
    rel = [("/dostavka/" + o + "/", _MAT_ALL[o]["name"] + " с доставкой")
           for o in _keys[_i + 1:] + _keys[:_i]]
    rel += ZHBI_ART.get(slug, [])
    rel = _RUBRIC_OF.get(slug, []) + rel
    rel += [("/dostavka/shcheben/", "Доставка щебня: все фракции и цены"),
            ("/dostavka/pesok/", "Доставка песка"),
            ("/dostavka/otsev/", "Отсев 0-5"),
            ("/dostavka/", "Все города и материалы")]
    ctx = dict(BASE_CTX)
    _calc = calc_for(slug)
    ctx.update(
        calc=_calc, has_calc=bool(_calc),
        canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items), jsonld=jl,
        title=mc["title"], desc=mc["desc"], h1=mc["h1"], hero_sub=mc["hero_sub"],
        mat_vin=mc["mat_vin"], mat_rod=mc["mat_rod"], mat_order=mc["mat_order"],
        subject=mat["name"] + ", " + SITE["region_short"],
        intro=mat["intro"], types=mat["types"], fractions=mat.get("fractions"),
        faq=mat["faq"],
        price_rows=mat["price_rows"], calc_rows=mat["calc_rows"],
        price_col1=mc["price_col1"], price_col2=mc["price_col2"],
        calc_head=mc["calc_head"], calc_caption=mc["calc_caption"],
        calc_col1=mc["calc_col1"], calc_col2=mc["calc_col2"], calc_col3=mc["calc_col3"],
        types_head=mc["types_head"],
        fractions_head=mat.get("fractions_head", mc.get("fractions_head", "Размеры и применение")),
        fractions_col1=mat.get("fractions_col1", mc.get("fractions_col1", "Позиция")),
        fractions_col2=mat.get("fractions_col2", mc.get("fractions_col2", "Где применяют")),
        fractions_caption="Что под какую задачу",
        # Семейство money-zhbi единственное шло без снимков: вызова
        # _photo_ctx здесь не было вовсе, и фотография по слагу
        # молча не попадала на страницу. Слоты пустые почти у всех
        # позиций, макрос в этом случае не рендерит ничего.
        **_photo_ctx(slug, photos_for(slug)),
        related_links=list(dict.fromkeys(rel))[:14],
        hero_cell=ZHBI_CELL.get(slug, 34), **hero_ctx(slug),
        price_note="Цены ориентировочные по рынку Свердловской области. "
                   "Товар есть в наличии: размер и срок отгрузки подтверждаем по заявке.",
        delivery_note="Доставку считаем отдельно: она зависит от веса, габарита и плеча. "
                      "Тяжёлые изделия требуют манипулятора, и это оговаривается заранее.")
    htmlp = env.get_template("money.j2").render(**ctx)
    pages.append((url, htmlp, "money-zhbi"))

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
               product_schema(h1, desc, MAT_FORMS[mats[0]]["low"], url,
                              images=product_images(MAT_FORMS[mats[0]]["url"])))

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

    # Смысловое ядро города. Два заголовка в geo2.j2 были дословно
    # одинаковы на всех 32 страницах, и проверка похожести в конце
    # сборки держалась на 0.79 при пороге 0.80. Подставляем в них
    # местную конкретику: грунт и ближний посёлок.
    _lsi = lsi_for(city_slug, mats)
    # Берём ПЕРВУЮ именную группу, а не случайную: в исходных описаниях
    # главная характеристика грунта стоит первой, и хеш-выбор давал куски
    # вроде «участки сухие» вместо «лесные супеси и скальное основание».
    # Уникальность страниц обеспечивает разный грунт у разных городов,
    # а не перебор кусков внутри одного города.
    # Если чистой группы не нашлось, берём исходную фразу целиком:
    # она грамматична, просто длиннее.
    _ground_tag = (_lsi["ground_lsi"] or [facts["ground"]])[0]
    # Сами массивы тоже уходят в контекст: geo_lsi годится только
    # перечислением после двоеточия, падеж после предлога не согласуется
    # (см. _lsi_places в geo_matrix). Отдельного списка посёлков в текст
    # не добавляем: facts["areas"] уже перечисляет их в блоке «Куда возим».
    htmlp = env.get_template("geo2.j2").render(
        **BASE_CTX, **hero_ctx("shcheben"), canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items),
        jsonld=jl, title=title, desc=desc, h1=h1, hero_sub=hero,
        **_lsi, ground_tag=_ground_tag,
        city=dict(facts, dist=dist), dist=dist, mat_blocks=mat_blocks,
        lots=city_lots(facts["km"])[0], lots_note=city_lots(facts["km"])[1],
        plecho_km=facts["km"],
        p_plecho=p_plecho, p_econ=p_econ, p_kuda=p_kuda, p_grunt=p_grunt,
        p_sroki=p_sroki, p_minv=pl["minv"], p_local=LOCAL[city_slug],
        faq=cfaq, related_links=rel[:12])
    pages.append((url, htmlp, "geo-city"))

# ---- РУБРИЧНЫЕ ХАБЫ (ШАГ 1 архитектуры каталога) ----
# Роль фильтра на статическом хостинге играет предгенерированный набор
# посадочных страниц, а хаб это его точка входа. Динамических фасетов
# быть не может: сервера нет, ?filter=... обработать негде.
for hb in HUBS:
    url = SITE["base"] + hb["slug"] + "/"
    autolink.reset(url)
    crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]),
                   (hb["h1"], None)]
    _items = [("/dostavka/", "Все материалы и города")] + \
             [(it["href"], it["name"]) for it in hb["items"]]
    jl = graph(localbusiness(), bc_schema(crumb_items), faq_schema(hb["faq"]),
               {"@type": "ItemList", "name": hb["items_head"],
                "itemListElement": [
                    {"@type": "ListItem", "position": i + 1,
                     "url": DOMAIN + it["href"], "name": it["name"]}
                    for i, it in enumerate(hb["items"])]})
    htmlp = env.get_template("hub_rubric.j2").render(
        **BASE_CTX, **hero_ctx(""), canonical=canonical(url), crumbs_html=crumbs(crumb_items),
        jsonld=jl, title=hb["title"], desc=hb["desc"], h1=hb["h1"],
        hero_sub=hb["hero_sub"], lead=hb["lead"], anchor=hb["anchor"],
        items_head=hb["items_head"], items=hb["items"],
        sections=hb["sections"], faq=hb["faq"], subject=hb["subject"],
        form_head=hb["form_head"], cta_after=hb["cta_after"],
        cta_head=hb["cta_head"], cta_text=hb["cta_text"],
        order_steps=ORDER_STEPS, objections=OBJECTIONS,
        related_links=list(dict.fromkeys(_items))[:14])
    pages.append((url, htmlp, "hub-rubric"))

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

# ---- КОНТАКТЫ (ШАГ 5 и 6: E-E-A-T и локальное SEO) ----
# Отдельная страница нужна была давно: /kontakty/ в корне принадлежит
# другому бренду и про доставку материалов не говорит ничего.
# ИНН и ОГРН выводятся, только если заданы в конфиге. Пустой блок
# реквизитов хуже отсутствующего: он обещает данные, которых нет.
url = SITE["base"] + "kontakty/"
autolink.reset(url)
crumb_items = [("Главная", "/"), ("Доставка материалов", SITE["base"]),
               ("Контакты", None)]
_c_faq = [
 ["Где вы находитесь?",
  "База в Екатеринбурге, %s. Отгрузка идёт с базы и напрямую с карьеров: "
  "на дальнем плече мы часто грузим ближе к вашему объекту, и это дешевле." % SITE["street"]],
 ["Можно ли приехать и забрать самому?",
  "Да, самовывоз возможен. Скажите заранее материал и объём, чтобы мы "
  "подготовили отгрузку и вы не ждали на весах."],
 ["Как быстро вы отвечаете?",
  "В MAX и WhatsApp обычно в течение пяти минут, работаем круглосуточно "
  "и без выходных. На заявку с сайта %s." % SITE["callback_promise"]],
 ["Работаете с юридическими лицами?",
  "Да. Оплата безналичным переводом, документы по запросу. "
  "Для расчёта пришлите объём, адрес объекта и срок."],
 ["Куда вы возите?",
  "Екатеринбург и вся Свердловская область. Плечо считается по дорогам, "
  "и по каждому городу у нас есть отдельная страница с расчётом."],
 ["Какой минимальный заказ?",
  "От пяти кубов одной машиной. Меньше тоже привезём, но рейс "
  "оплачивается целиком, и куб выйдет дороже."],
]
_c_sections = [
 {"id": "kak-rabotaem",
  "h": "Как проходит заказ",
  "steps": [
   "Пишете или звоните, называете материал, объём и адрес объекта.",
   "Мы считаем стоимость с доставкой и называем её до выезда машины.",
   "Согласуем время и заезд: ширину ворот, место для разворота и подъёма кузова.",
   "Машина приходит, вы принимаете объём по кузову до разгрузки.",
   "Рассчитываетесь после выгрузки. Предоплату не берём.",
  ],
  "callout": ["Объём проверяется до разгрузки, а не после.",
              "У кузова самосвала есть паспортная вместимость, и она "
              "сверяется на месте. Недовоз пересчитываем в вашу пользу."]},
 {"id": "avtopark",
  "h": "Наш автопарк",
  "p": ["Возим самосвалами от 5 до 20 кубометров. Машина подбирается "
        "не по объёму заказа, а по заезду: там, где двадцатикубовый "
        "не развернётся, идут две ходки пятикубовым, и это обсуждается "
        "до выезда, а не у ворот."],
  "table": {
   "caption": "Чем возим и куда это проходит",
   "head": ["Машина", "Объём", "Где проходит"],
   "rows": [
    ["Самосвал 5 м³", "до 5 м³", "Узкие улицы, дачные проезды, участки без разворота"],
    ["Самосвал 10 м³", "до 10 м³", "Обычный частный участок с нормальным заездом"],
    ["Самосвал 20 м³", "до 20 м³", "Открытая площадка, объект, широкий заезд"],
    ["Манипулятор", "штучный товар", "Кольца, блоки, плиты, поддоны плитки"],
   ]},
  "after": ["Фотографии техники добавим отдельно: показывать чужие снимки "
            "из фотобанка вместо своих машин мы не будем."]},
]
jl = graph(localbusiness(), bc_schema(crumb_items), faq_schema(_c_faq))
htmlp = env.get_template("contacts.j2").render(
    # На контактах в панели база с воздуха: страница про то, где мы стоим.
    **BASE_CTX, hero_img=img_one("fleet/baza-s-vozduha.jpg"),
    hero_cap="наша база в Екатеринбурге", canonical=canonical(url), crumbs_html=crumbs(crumb_items), jsonld=jl,
    title="Контакты Щебень-Урал в Екатеринбурге: адрес, телефон, режим работы",
    desc=("Контакты %s: база в Екатеринбурге, %s, телефон %s, режим работы %s. "
          "Честный объём по кузову, оплата после выгрузки."
          % (SITE["legal_name"], SITE["street"], SITE["phone"], SITE["hours"]))[:200],
    h1="Контакты и как мы работаем",
    hero_sub=("База в Екатеринбурге, %s. Возим по всей Свердловской области, "
              "объём проверяется по кузову до разгрузки, оплата после выгрузки."
              % SITE["street"]),
    sections=_c_sections, faq=_c_faq, subject="вопрос или заявка",
    form_head="Оставить заявку или задать вопрос",
    cta_after=1, cta_head="Проще написать, чем звонить",
    cta_text="Напишите материал, объём и адрес. Посчитаем стоимость с доставкой "
             "и ответим в течение рабочего дня.",
    objections=OBJECTIONS,
    related_links=[("/dostavka/", "Все материалы и города"),
                   ("/dostavka/shcheben/", "Доставка щебня"),
                   ("/dostavka/pesok/", "Доставка песка"),
                   ("/dostavka/zhbi-i-vodootvod/", "ЖБИ и водоотвод"),
                   ("/dostavka/blagoustroystvo/", "Благоустройство участка"),
                   ("/dostavka/politika/", "Обработка персональных данных")])
pages.append((url, htmlp, "contacts"))

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

def visible(hs):
    """Видимый текст страницы без разметки и скриптов."""
    hs = re.sub(r"<script.*?</script>", " ", hs, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", hs)).strip()


# ---- SITEMAP раздела ----
#
# lastmod у КАЖДОЙ страницы свой и меняется только когда меняется её текст.
# Раньше здесь стояла одна дата на все страницы, вписанная константой:
# она устаревала между правками, а в день сборки сообщала поисковику,
# что обновились разом все сто девяносто пять адресов. Это ровно та
# ситуация, в которой lastmod перестают учитывать.
#
# Считается по отпечатку видимого текста, не всей разметки: правка
# в шапке или подвале задевает все страницы сразу и датой обновления
# страницы не является. Отпечатки лежат в audit/lastmod.json и живут
# между сборками - без них дата сбрасывалась бы на сегодняшнюю каждый раз.
_LM_PATH = os.path.join(ROOT, "audit", "lastmod.json")
try:
    _lastmod = json.load(io.open(_LM_PATH, encoding="utf-8"))
except Exception:
    _lastmod = {}

_today = datetime.date.today().isoformat()
_lm_new = {}
for url, h, fam in pages:
    _fp = hashlib.sha1(visible(h).encode("utf-8")).hexdigest()[:16]
    _prev = _lastmod.get(url)
    if _prev and _prev.get("fp") == _fp:
        _lm_new[url] = _prev                      # текст не менялся, дату храним
    else:
        _lm_new[url] = {"fp": _fp, "date": _today}
os.makedirs(os.path.dirname(_LM_PATH), exist_ok=True)
json.dump(_lm_new, io.open(_LM_PATH, "w", encoding="utf-8"),
          ensure_ascii=False, indent=1, sort_keys=True)
_touched = sum(1 for u, v in _lm_new.items()
               if _lastmod.get(u, {}).get("fp") != v["fp"])
print("lastmod: текст изменился у %d из %d страниц" % (_touched, len(_lm_new)))

sm = ['<?xml version="1.0" encoding="UTF-8"?>',
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
# Страница благодарности закрыта от индексации, поэтому в карту не идёт:
# иначе Вебмастер отчитается о ней как об исключённой и будет прав.
for url, h, fam in pages:
    if fam == "thanks":
        continue
    sm.append(f"  <url>\n    <loc>{DOMAIN}{url}</loc>"
              f"\n    <lastmod>{_lm_new[url]['date']}</lastmod>\n  </url>")
sm.append("</urlset>\n")
open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8").write("\n".join(sm))

# список URL для переобхода в Яндекс.Вебмастере. Кладём в audit/ (закрыт в robots.txt),
# чтобы служебный файл не попал в индекс вместе со страницами раздела.
AUDIT = os.path.join(ROOT, "audit")
os.makedirs(AUDIT, exist_ok=True)
with open(os.path.join(AUDIT, "dostavka-urls.txt"), "w", encoding="utf-8") as fh:
    for url, h, fam in pages:
        # Страница благодарности закрыта от индексации, как и в карте сайта.
        # Отправлять её на переобход значит просить робота зайти туда,
        # откуда его же и выгоняют метатегом.
        if fam == "thanks":
            continue
        fh.write(DOMAIN + url + "\n")

print(f"Собрано страниц: {len(pages)}")
for p, url, fam in written:
    print(f"  [{fam:10}] {url}")


# ---- ПРОВЕРКА ДУБЛЕЙ (anti-doorway, ratio < 0.80) ----
# Сравниваем ВСЕ гео-страницы между собой, а не внутри семейства.
# Раньше проверка шла по семействам, и пара "щебень в Реже" против
# "отсев в Реже" вообще не сравнивалась, хотя это тоже дорвейная ось.
# Порог поднят с 0,80 до 0,92 по решению владельца. На шаблонных
# городских страницах 0,80 это нормальная плотность общего каркаса:
# совпадают шапка, подвал, оплата и порядок заказа - то есть ровно то,
# что и должно совпадать. Настоящий дубль начинается там, где совпадает
# уже сам текст, и вот его печать ниже и ловит.
SIM_LIMIT = 0.92
grp = [(u, visible(h)) for u, h, f in pages if f.startswith("geo")]
print(f"\nПохожесть гео-страниц, все пары (порог < {SIM_LIMIT}): {len(grp)} страниц")
mx, worst, high = 0, None, []
for i in range(len(grp)):
    for j in range(i + 1, len(grp)):
        r = difflib.SequenceMatcher(None, grp[i][1], grp[j][1]).ratio()
        if r > mx:
            mx, worst = r, (grp[i][0], grp[j][0])
        if r >= SIM_LIMIT:
            high.append((r, grp[i][0], grp[j][0]))
high.sort(reverse=True)
for r, a, b in high:
    print(f"  ВЫСОКАЯ {r:.2f}: {a} vs {b}")
print(f"  пар выше порога: {len(high)}")
print(f"  максимум {mx:.2f} ({worst[0]} vs {worst[1]})  {'OK' if mx < SIM_LIMIT else 'ПРЕВЫШЕНО'}")

if _NOFAM:
    print("\nБЕЗ СЕМЕЙСТВА ПРАЙСА, ушли в nerud по умолчанию:")
    for _s in _NOFAM:
        print("  " + _s)

wc = [(u, len(visible(h).split())) for u, h, f in pages]
print("\nОбъём текста (слов):")
for u, n in sorted(wc, key=lambda x: -x[1]):
    print(f"  {n:5}  {u}")
