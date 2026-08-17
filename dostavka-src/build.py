#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка раздела доставки в /dostavka/. Изолирован от ursdom.
Зависимости: Python 3 + jinja2. Вывод: статические index.html + sitemap раздела."""
import os, sys, json, re, difflib
from PIL import Image
from jinja2 import Environment, FileSystemLoader

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "dostavka")
sys.path.insert(0, os.path.join(HERE, "data"))

from site_config import SITE, ADVANTAGES, GUARANTEES
from products import MATERIALS, EXTRA
from products_ext import MATERIALS_EXT, MONEY_CFG_EXT
from products_zhbi import MATERIALS_ZHBI, MONEY_CFG_ZHBI
from products_beton import MATERIALS_BETON, MONEY_CFG_BETON
from products_gap import MATERIALS_GAP, MONEY_CFG_GAP
from products_gap2 import MATERIALS_GAP2, MONEY_CFG_GAP2
from products_gap3 import MATERIALS_GAP3, MONEY_CFG_GAP3
from products_rev import MATERIALS_REV, MONEY_CFG_REV
from geo_matrix import (CITY_FACTS, MATRIX, ALREADY, MAT_FORMS,
                        ANGLE, LOCAL, MAT_TASK, example_for, plecho)
import autolink
from hubs import HUBS
from canonical import canonical
from calc import calc_for, PER_PAGE as _CALC_ON

# Список страниц с калькулятором живёт в data/calc.py вместе с их
# материалами и объёмами: два списка в двух файлах разошлись бы
# при первом же добавлении страницы.
from conversion import PRICE_SETS, FAM, ORDER_STEPS, OBJECTIONS
from prices import PER_CUBE, PRICE_NOTE, DELIVERY_NOTE, CATALOG, SIEVE, HERO_CELL, HERO_FRAC
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
from tags import TAG_LONGREADS
LONGREADS = LONGREADS + CORE_LONGREADS + BETON_LONGREADS + ZADACHI_LONGREADS + SMEZH_LONGREADS + BETON2_LONGREADS + GAP_LONGREADS + GAP2_LONGREADS + PLITKA_LONGREADS + BETON3_LONGREADS + SMESI_LONGREADS + SKALA_LONGREADS + REV_LONGREADS + BRENDY_LONGREADS + TAG_LONGREADS
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
        base = os.path.splitext(f)[0]
        path = os.path.join(IMGDIR, slug, f)
        with Image.open(path) as im:
            w, h = im.size
        webp, jpg = [], []
        for wd in (800, 1600):
            cand = "%s-%d.webp" % (base, wd)
            if os.path.exists(os.path.join(IMGDIR, slug, cand)):
                webp.append("/dostavka/assets/img/%s/%s %dw" % (slug, cand, wd))
        cand = "%s-1200.jpg" % base
        if os.path.exists(os.path.join(IMGDIR, slug, cand)):
            jpg.append("/dostavka/assets/img/%s/%s 1200w" % (slug, cand))
        jpg.append("/dostavka/assets/img/%s/%s %dw" % (slug, f, w))
        out.append(dict(src="/dostavka/assets/img/" + slug + "/" + f,
                        alt=a, cap=c, w=w, h=h,
                        webp=", ".join(webp), jpg=", ".join(jpg)))
    return out


def _photo_ctx(slug, items, default_head=None):
    """Три переменные галереи одним куском.

    Заголовок и подводка лежат в PHOTOS_META по слагу: подпись пишется
    под конкретный набор кадров, а не шаблонной фразой «фото материала».
    Если снимков нет, макрос не рендерит ничего, и заголовок с подводкой
    в разметку не попадают.
    """
    meta = PHOTOS_META.get(slug, {})
    return dict(photos=items,
                photos_head=meta.get("head", default_head),
                photos_intro=meta.get("intro"))


FLEET_PHOTOS = photos_for("fleet")

BASE_CTX = dict(cfg=SITE, advantages=ADVANTAGES, guarantees=GUARANTEES,
                fleet_photos=FLEET_PHOTOS,
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
    'pesok': [('/dostavka/stati/modul-krupnosti-peska/', 'Модуль крупности песка'), ('/dostavka/stati/gost-na-shcheben-i-pesok/', 'ГОСТ на щебень и песок: что спрашивать')],
    'otsev': [('/dostavka/stati/otsev-gde-primenyat/', 'Отсев 0-5: где применяют и чем заменить'), ('/dostavka/stati/frakcii-shchebnya/', 'Фракции щебня: какая под какую задачу')],
    'pgs': [('/dostavka/stati/pgs-ili-opgs/', 'ПГС и ОПГС: чем отличаются'), ('/dostavka/stati/skalnyy-grunt-dresva-but/', 'Скальный грунт, дресва и бут')],
    'keramzit': [('/dostavka/stati/keramzit-frakcii-i-ves/', 'Керамзит: фракции, вес и где выгоден')],
    'skalnyy-grunt': [('/dostavka/stati/skalnyy-grunt-klassifikaciya/', 'Скальный грунт: классификация и разработка'),
                      ('/dostavka/stati/skalnyy-grunt-dresva-but/', 'Скальный грунт, дресва и бут'), ('/dostavka/stati/pgs-ili-opgs/', 'ПГС и ОПГС: чем отличаются')],
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
    _calc = calc_for(slug)
    htmlp = env.get_template("money.j2").render(
        **BASE_CTX, **mc, calc=_calc, has_calc=bool(_calc),
        canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items), jsonld=jl,
        intro=mat["intro"], types=mat["types"], fractions=mat.get("fractions"),
        faq=mat["faq"], hero_cell=HERO_CELL.get(slug, 34),
        **_photo_ctx(slug, _ph, "Как выглядит " + mc["mat_vin"]),
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
    _calc = calc_for(a["slug"])
    htmlp = env.get_template("longread.j2").render(
        calc=_calc, has_calc=bool(_calc),
        **_photo_ctx(a["slug"], photos_for(a["slug"])),
        **BASE_CTX, author=AUTHOR_FULL, updated=UPDATED,
        canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items), jsonld=jl,
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
    _calc = calc_for(slug)
    htmlp = env.get_template("money.j2").render(
        **BASE_CTX, calc=_calc, has_calc=bool(_calc), canonical=DOMAIN + url, crumbs_html=crumbs(crumb_items),
        jsonld=jl, title=mc["title"], desc=mc["desc"], h1=mc["h1"],
        hero_sub=mc["hero_sub"], mat_vin=mc["mat_vin"], mat_rod=mc["mat_rod"],
        mat_order=mc["mat_order"], subject=mc["mat_vin"] + ", " + SITE["region_short"],
        intro=mat["intro"], types=mat["types"], fractions=mat.get("fractions"),
        faq=mat["faq"], related_links=list(dict.fromkeys(rel))[:14], hero_cell=HERO_CELL.get(slug, 34),
        **_photo_ctx(slug, photos_for(slug), "Как выглядит " + mc["mat_vin"]),
        hero_frac=HERO_FRAC.get(slug, "щебень 20-40 мм"))
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
               product_schema(mat["name"], mc["desc"], mc["low"], url))
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
        related_links=list(dict.fromkeys(rel))[:14],
        hero_cell=ZHBI_CELL.get(slug, 34), hero_frac=ZHBI_FRAC.get(slug, "щебень 20-40 мм"),
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
        **BASE_CTX, canonical=canonical(url), crumbs_html=crumbs(crumb_items),
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
  "В WhatsApp обычно в течение пяти минут в рабочее время, %s. "
  "На заявку с сайта %s." % (SITE["hours"], SITE["callback_promise"])],
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
    **BASE_CTX, canonical=canonical(url), crumbs_html=crumbs(crumb_items), jsonld=jl,
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

if _NOFAM:
    print("\nБЕЗ СЕМЕЙСТВА ПРАЙСА, ушли в nerud по умолчанию:")
    for _s in _NOFAM:
        print("  " + _s)

wc = [(u, len(visible(h).split())) for u, h, f in pages]
print("\nОбъём текста (слов):")
for u, n in sorted(wc, key=lambda x: -x[1]):
    print(f"  {n:5}  {u}")
