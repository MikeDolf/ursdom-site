# -*- coding: utf-8 -*-
"""Контекстные ссылки в тексте статей.

До этого в теле статьи не было ни одной ссылки: двадцать семь абзацев
разбора и ноль путей к товару. Все внутренние ссылки жили в блоке
«Смотрите также» под подвалом, куда человек доходит уже после того,
как решил уйти. Поисковые системы при этом читают анкор в тексте
иначе, чем список в футере: там он в контексте предложения.

Правила жёсткие, потому что переспам ссылками хуже их отсутствия:
- одна ссылка на один адрес на страницу, по первому вхождению;
- не больше MAX_LINKS на страницу;
- никогда на саму себя;
- только в обычных абзацах и списках. Врезки, таблицы, шаги, врезка
  «коротко» и блоки-призывы не трогаются: там либо стальной фон,
  где латунная ссылка требует отдельной проверки контраста, либо
  и без того плотный текст.

Термины подобраны так, чтобы анкор был осмысленным сам по себе.
«Тут» и «подробнее» не используются: анкор это и есть описание
страницы, на которую он ведёт.
"""
import re

MAX_LINKS = 8

# Стем плюс допустимые окончания. Порядок важен: узкое выше широкого,
# иначе «щебень» съест «щебень 20-40» и ссылка уйдёт не туда.
#
# Границы слова обязательны. Первая версия писала «керамзит\\w*», и это
# поймало «керамзитобетон» в статье про стяжку: ссылка на керамзит
# стояла на слове, которое означает совсем другой материал. Поймано
# просмотром готовых страниц, а не проверкой: автоматической проверки
# на смысл анкора не существует, поэтому список правят глазами.
TERMS = [
 (r'щебн[ея]\w*\s+20-40|щеб(?:ень|ня|нем|нём)\s+20-40', '/dostavka/shcheben/frakciya-20-40/'),
 (r'щебн[ея]\w*\s+5-20|щеб(?:ень|ня|нем|нём)\s+5-20', '/dostavka/shcheben/frakciya-5-20/'),
 (r'скальн\w+\s+грунт\w*', '/dostavka/skalnyy-grunt/'),
 (r'бутов\w+\s+кам(?:ень|ня|нем|нём)', '/dostavka/butovyy-kamen/'),
 (r'речн\w+\s+пес(?:ок|ка|ком)|мыт\w+\s+пес(?:ок|ка|ком)', '/dostavka/pesok/rechnoy/'),
 (r'карьерн\w+\s+пес(?:ок|ка|ком)', '/dostavka/pesok/karyernyy/'),
 (r'асфальтов\w+\s+крошк\w+', '/dostavka/asfaltovaya-kroshka/'),
 (r'\bкерамзит(?:а|ом|е|у|ы)?\b', '/dostavka/keramzit/'),
 (r'\bОПГС\b|\bПГС\b', '/dostavka/pgs/'),
 (r'\bЩПС\b', '/dostavka/shchps/'),
 (r'\bотсев(?:а|ом|е|у|ы)?\b', '/dostavka/otsev/'),
 (r'\bдресв(?:а|ы|е|у|ой)\b', '/dostavka/dresva-i-shlak/'),
 (r'тротуарн\w+\s+плитк\w+|плитк\w+\s+тротуарн\w+', '/dostavka/trotuarnaya-plitka/'),
 (r'\bбордюр(?:а|ом|е|у|ы|ов|ами)?\b|\bпоребрик(?:а|ом|е|у|и)?\b', '/dostavka/bordyur/'),
 (r'водоотводн\w+\s+лот(?:ок|ка|ки|ков)', '/dostavka/lotki-vodootvodnye/'),
 (r'\bдождеприёмник(?:а|ом|е|у|и|ов|ами)?\b', '/dostavka/dozhdepriemniki/'),
 (r'кольц\w+\s+КС\b|кольц\w+\s+ЖБИ\b', '/dostavka/kolca-zhbi/'),
 (r'блок\w*\s+ФБС\b|\bФБС\b', '/dostavka/fbs-bloki/'),
 (r'дорожн\w+\s+плит\w+', '/dostavka/dorozhnye-plity/'),
 (r'\bарболит(?:а|ом|е|у)?\b|арболитов\w+\s+блок\w*', '/dostavka/stenovye-bloki/'),
 (r'цемент\w*\s+М500|цемент\w*\s+М400', '/dostavka/stati/cement-m400-i-m500/'),
 (r'коэффициент\w*\s+уплотнени\w+', '/dostavka/stati/koefficient-uplotneniya/'),
 (r'модул\w+\s+крупност\w+', '/dostavka/stati/modul-krupnosti-peska/'),
 (r'марк\w+\s+бетона', '/dostavka/stati/marki-betona/'),
 (r'\bбетононасос(?:а|ом|е|у|ы)?\b', '/dostavka/beton/betononasos/'),
 (r'кладочн\w+\s+смес\w+', '/dostavka/stati/kladochnaya-smes/'),
 (r'тактильн\w+\s+плитк\w+', '/dostavka/stati/taktilnaya-plitka/'),
 (r'гранитн\w+\s+брусчатк\w+', '/dostavka/stati/granitnaya-bruschatka/'),
 (r'\bстяжк(?:а|и|е|у|ой)\s+пола', '/dostavka/stati/styazhka-pola/'),
 (r'\bотмостк(?:а|и|е|у|ой)\b', '/dostavka/stati/otmostka-vokrug-doma/'),
 (r'наливн\w+\s+пол\w*', '/dostavka/stati/nalivnoy-pol/'),
 (r'гидроизоляци(?:я|и|ю|ей)\b', '/dostavka/stati/gidroizolyaciya-betona/'),
 (r'пропитк(?:а|и|е|у|ой|ами)\b', '/dostavka/stati/propitki-dlya-betona/'),
 (r'укладк(?:а|и|е|у|ой)\s+(?:тротуарной\s+)?плитки', '/dostavka/stati/ukladka-trotuarnoy-plitki/'),
 (r'битумн\w+\s+эмульси\w+', '/dostavka/bitum-i-asfalt/'),
 (r'холодн\w+\s+асфальт\w*', '/dostavka/stati/holodnyy-asfalt/'),
 (r'плит\w+\s+перекрыти\w+', '/dostavka/zhbi-izdeliya/'),
 (r'опор\w+\s+СВ\b', '/dostavka/opory-i-stoyki/'),
 (r'\bпескоблок(?:а|ом|е|у|и|ов)?\b|керамзитоблок\w*', '/dostavka/peskobloki/'),
 (r'\bсептик(?:а|ом|е|у|и)?\b', '/dostavka/kolca-kanalizacionnye/'),
 (r'\bлюк(?:а|ом|е|у|и|ов)?\b', '/dostavka/lyuki-i-kryshki/'),
 (r'бетонн\w+\s+забор\w*', '/dostavka/betonnye-zabory/'),
 (r'\bмарк(?:а|и|е|у|ой)\s+по\s+дробимости', '/dostavka/stati/gost-na-shcheben-i-pesok/'),
 (r'фракци(?:я|и|ю|ей|ям|ями)\b', '/dostavka/stati/frakcii-shchebnya/'),

 # Общие слова идут последними: если на странице уже нашлось что-то
 # точное, ссылка достанется ему, а не «песку вообще».
 (r'\bщеб(?:ень|ня|нем|нём|не|ню)\b', '/dostavka/shcheben/'),
 (r'\bпес(?:ок|ка|ком|ке|ку)\b', '/dostavka/pesok/'),
 (r'\bцемент(?:а|ом|е|у|ы)?\b', '/dostavka/cement-i-smesi/'),
 (r'\bбетон(?:а|ом|е|у|ы)?\b', '/dostavka/beton/'),
 (r'\bплитк(?:а|и|е|у|ой)\b', '/dostavka/trotuarnaya-plitka/'),
]

# Марки бетона отдельно: голое «М300» встречается в тексте гораздо чаще,
# чем «бетон М300», но то же обозначение носят цемент, раствор и сухая
# смесь. Поэтому марка связывается, только если рядом слева нет слов
# «цемент», «раствор» или «смесь», а сам абзац говорит про бетон.
MARKS = {m: '/dostavka/beton/m%s/' % m[1:] for m in
         ('М100', 'М150', 'М200', 'М250', 'М300', 'М350', 'М400')}
import re as _re
MARK_RX = _re.compile(r'\bМ(?:100|150|200|250|300|350|400)\b')
NOT_BETON = _re.compile(r'цемент|раствор|смес|кирпич|бордюр', _re.I)

RX = [(re.compile(p), href) for p, href in TERMS]

STATE = {"url": "", "used": set(), "n": 0}

def reset(url):
    STATE["url"] = url
    STATE["used"] = set()
    STATE["n"] = 0

def link(text):
    """Расставить ссылки в одном абзаце.

    Совпадения сначала СОБИРАЮТСЯ, потом вставляются с конца строки.
    Первая версия вставляла по ходу, и следующее правило могло попасть
    внутрь уже вставленного тега, включая адрес в href.
    """
    if not text or "<a " in text:
        return text
    spans = []          # (начало, конец, адрес)
    taken = []

    def free(a, b):
        return all(b <= x or a >= y for x, y, _ in spans)

    for rx, href in RX:
        if href is None or href in STATE["used"] or href == STATE["url"]:
            continue
        if len(spans) + STATE["n"] >= MAX_LINKS:
            break
        for m in rx.finditer(text):
            if free(m.start(), m.end()):
                spans.append((m.start(), m.end(), href))
                taken.append(href)
                break

    if len(spans) + STATE["n"] < MAX_LINKS and not NOT_BETON.search(text) \
       and 'бетон' in text.lower():
        for m in MARK_RX.finditer(text):
            href = MARKS[m.group(0)]
            if href in STATE["used"] or href in taken or href == STATE["url"]:
                continue
            if free(m.start(), m.end()):
                spans.append((m.start(), m.end(), href))
                taken.append(href)
                if len(spans) + STATE["n"] >= MAX_LINKS:
                    break

    for a, b, href in sorted(spans, reverse=True):
        text = text[:a] + '<a href="' + href + '">' + text[a:b] + '</a>' + text[b:]
    STATE["used"].update(taken)
    STATE["n"] += len(spans)
    return text
