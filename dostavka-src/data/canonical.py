# -*- coding: utf-8 -*-
"""Каноникализация: один адрес на один документ.

ЧТО ЭТО РЕШАЕТ. Сайт статический, сервера нет, обработать ?sort=price
на бэкенде негде. Но серверная обработка для этой задачи и не нужна:
достаточно, чтобы КАЖДЫЙ документ в любой своей вариации отдавал один
и тот же <link rel="canonical"> на чистый адрес. Тогда /shcheben/20-40/,
/shcheben/20-40/?sort=price и /shcheben/20-40/?utm_source=yandex это
для поиска одна страница, а не три.

Плюс к этому Яндекс понимает директиву Clean-param в robots.txt, которая
выкидывает параметры ещё на этапе обхода, до склейки дублей. Гугл такой
директивы не знает и работает только по canonical, поэтому нужны обе.

ПРАВИЛА КАНОНА в этом проекте:
- всегда абсолютный URL со схемой и доменом;
- всегда с завершающим слешем: каталоги отдаются как /path/, и адрес
  без слеша Pages редиректит сам;
- никогда не содержит index.html;
- никогда не содержит query и fragment;
- никогда не указывает на несуществующую страницу. Это проверяется
  группой 21 в audit/_verify.py: canonical, ведущий в никуда, хуже
  отсутствующего, потому что склеивает живую страницу с ошибкой 404.
"""
import re

DOMAIN = "https://ursdom.ru"

# Параметры, которые не меняют содержимое документа. Порядок в строке
# Clean-param значения не имеет, разделитель - амперсанд.
NOISE_PARAMS = [
    # сортировка и вид каталога
    "sort", "order", "view", "per_page", "page_size",
    # фасеты, которые не создают отдельной посадочной страницы
    "color", "brand", "min_price", "max_price", "in_stock",
    # рекламные метки
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "yclid", "gclid", "ymclid", "fbclid", "from", "roistat", "_openstat",
]

_SLASH = re.compile(r"/{2,}")


def canonical(path: str, domain: str = DOMAIN) -> str:
    """Абсолютный канонический адрес из внутреннего пути.

    Принимает и '/dostavka/shcheben/', и 'dostavka/shcheben/index.html',
    и '/dostavka/shcheben?sort=price#ceny'. Возвращает всегда одно:
    'https://ursdom.ru/dostavka/shcheben/'.
    """
    p = path.split("#", 1)[0].split("?", 1)[0]
    p = p.replace("index.html", "")
    if not p.startswith("/"):
        p = "/" + p
    p = _SLASH.sub("/", p)
    if not p.endswith("/"):
        p += "/"
    return domain.rstrip("/") + p


def clean_param_directive(params=None) -> str:
    """Строка Clean-param для robots.txt.

    Яндекс ограничивает длину одной директивы, поэтому длинный список
    разбивается на несколько строк. Лимит взят с запасом: 500 символов
    на строку вместо документированных 500 байт, чтобы кириллица
    в будущих параметрах не переполнила строку незаметно.
    """
    params = list(params or NOISE_PARAMS)
    lines, cur = [], []
    for p in params:
        probe = "&".join(cur + [p])
        if len(probe) > 480 and cur:
            lines.append("Clean-param: " + "&".join(cur))
            cur = [p]
        else:
            cur.append(p)
    if cur:
        lines.append("Clean-param: " + "&".join(cur))
    return "\n".join(lines)
