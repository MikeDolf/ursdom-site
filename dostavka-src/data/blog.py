# -*- coding: utf-8 -*-
"""Блог раздела: статьи по видам работ.

До блога статьи жили только ссылками со страниц: в хлебных крошках
стояло «Статьи» без адреса, и списка всех статей не было нигде.
Владелец попросил раздел, где статьи собраны под вид работ, а у каждой
есть призыв купить материал для этой работы у нас.

Рубрика это вид работ, а не материал: человек приходит с задачей
«сделать дорожку», а не «купить щебень 20-40». У рубрики свои материалы
с ценами: они стоят полосой в блоге и блоком в каждой статье рубрики.
Материалы берутся строками прайса из conversion.PRICE_SETS, поэтому
подпись ссылки и адрес те же, что по всему сайту, а цена та же, что
в прайсе.

Каждая статья обязана быть в какой-то рубрике: сборка падает, если
статья появилась, а рубрику ей не назначили.
"""
from conversion import PRICE_SETS

_ROWS = {}
for _fam in PRICE_SETS.values():
    for _name, _price, _href in _fam["rows"]:
        _ROWS.setdefault(_name, (_name, _price, _href))


def _m(*names):
    return [_ROWS[n] for n in names]


BLOG_RUBRICS = [
 dict(id="fundament", h="Фундамент и подготовка под дом",
      lead="Подушка, обратная засыпка, бутование столбов и основания под крыльцо: "
           "что под чем лежит и сколько кубов заказывать на каждый этап.",
      mats=_m("Щебень 20-40", "Песок карьерный", "ПГС"),
      slugs=["podushka-pod-fundament", "obratnaya-zasypka", "materialy-na-dom-po-etapam",
             "butovanie-stolbov", "osnovanie-pod-krylco", "zasypka-podpola"]),
 dict(id="dorozhki", h="Дорожки, заезды, парковки и дороги",
      lead="Укладка щебня слоями, дорожки, заезд для машины, парковка на участке "
           "и дорога к нему: толщина, фракции и уплотнение.",
      mats=_m("Щебень 20-40", "Щебень 40-70", "Отсев 0-5", "Асфальтовая крошка"),
      slugs=["ukladka-shchebnya", "dorozhka-iz-shchebnya", "dorozhki-na-uchastke",
             "parkovka-iz-shchebnya", "doroga-k-uchastku", "holodnyy-asfalt",
             "osnovanie-pod-teplicu", "osnovanie-pod-basseyn"]),
 dict(id="drenazh", h="Дренаж, отмостка и водоотвод",
      lead="Дренаж участка, дренажный колодец, септик из колец, отмостка и лотки: "
           "какой щебень пропускает воду и сколько его уходит.",
      mats=_m("Щебень 20-40", "Щебень 5-20", "Кольцо КС 10-9", "Лоток бетонный 1000×140×125"),
      slugs=["drenazh-uchastka", "drenazhnyy-kolodec", "geotekstil-pod-shcheben",
             "myagkaya-otmostka", "otmostka-vokrug-doma", "lotki-i-dozhdepriemniki",
             "septik-iz-kolec", "kolca-zhbi-razmery"]),
 dict(id="otsypka", h="Отсыпка и планировка участка",
      lead="Чем поднять и выровнять участок подешевле: ПГС, скальный грунт, дресва, "
           "отсев и песок под газон, с расходом на квадратный метр.",
      mats=_m("ПГС", "Скальный грунт", "Отсев 0-5", "Песок карьерный"),
      slugs=["chem-otsypat-uchastok", "skalnyy-grunt-dresva-but", "skalnyy-grunt-klassifikaciya",
             "pgs-ili-opgs", "otsev-gde-primenyat", "pesok-pod-gazon", "rashod-na-m2",
             "dostavka-na-dachu"]),
 dict(id="beton", h="Бетон, растворы, стяжка и полы",
      lead="Пропорции бетона и раствора, марки, стяжка, полы в гараже и бане, "
           "керамзит в стяжке и гидроизоляция.",
      mats=_m("Бетон М200, класс B15", "Щебень 5-20", "Песок речной мытый",
              "Цемент М500, мешок 50 кг"),
      slugs=["skolko-shchebnya-i-peska-na-kub-betona", "marki-betona", "zames-betona-vedrami",
             "beton-iz-otseva-i-pgs", "skolko-betona-v-miksere", "ves-kuba-betona",
             "rastvor-proporcii", "cement-m400-i-m500", "styazhka-pola", "nalivnoy-pol",
             "pol-v-garazhe", "pol-v-bane", "keramzit-v-styazhke", "uteplenie-keramzitom",
             "gidroizolyaciya-betona", "pronikayushchaya-gidroizolyaciya",
             "propitki-dlya-betona", "remontnye-smesi-dlya-betona", "kladochnaya-smes",
             "kladochnaya-smes-dlya-pechey", "pechnoy-rastvor", "arbolit-i-polistirolbeton"]),
 dict(id="blagoustroystvo", h="Плитка, бордюр и декоративная отсыпка",
      lead="Основание под тротуарную плитку, бордюр, швы, декоративный щебень "
           "и отсыпка клумб: что класть под низ и что будет видно сверху.",
      mats=_m("Брусчатка 200×100×60, вибропрессованная", "Бордюр садовый БР 100.20.8",
              "Отсев 0-5", "Щебень 20-40"),
      slugs=["ukladka-trotuarnoy-plitki", "pesok-pod-plitku", "plitka-na-betonnoe-osnovanie",
             "plitka-svoimi-rukami", "vybrat-trotuarnuyu-plitku", "behaton", "formy-dlya-plitki",
             "uzory-plitki", "cvet-trotuarnoy-plitki", "granitnaya-bruschatka", "taktilnaya-plitka",
             "shvy-trotuarnoy-plitki", "proizvoditeli-trotuarnoy-plitki", "ustanovka-bordyura",
             "razmery-bordyurov", "sadovyy-bordyur", "plastikovyy-sadovyy-bordyur",
             "dekorativnyy-shcheben", "dekorativnaya-otsypka", "otsypka-mogily"]),
 dict(id="vybor", h="Выбор материала и расчёт объёма",
      lead="Виды и фракции щебня, классы песка, вес куба, коэффициент уплотнения "
           "и сколько материала входит в машину.",
      mats=_m("Щебень 20-40", "Песок карьерный", "Отсев 0-5"),
      slugs=["vidy-shchebnya", "frakcii-shchebnya", "kakoy-shcheben-vybrat", "shcheben-ili-graviy",
             "kakoy-pesok-vybrat", "klassy-peska", "modul-krupnosti-peska",
             "gost-na-shcheben-i-pesok", "skolko-vesit-kub", "nasypnaya-plotnost",
             "koefficient-uplotneniya", "skolko-shchebnya-nuzhno", "skolko-shchebnya-v-kamaze",
             "cena-kuba-s-dostavkoy", "keramzit-frakcii-i-ves"]),
]

# статья -> рубрика
BLOG_OF = {}
for _r in BLOG_RUBRICS:
    for _s in _r["slugs"]:
        BLOG_OF["stati/" + _s] = _r
