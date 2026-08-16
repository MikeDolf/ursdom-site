# -*- coding: utf-8 -*-
"""Проверка собранных страниц раздела /dostavka/.

Каждая проверка здесь появилась после реальной ошибки, которую поймал
не я, а пользователь на скриншоте. Поэтому набор растёт и ничего
из него не убирается.

Запуск: python3 audit/_verify.py
"""
import io, json, os, re, sys, glob, collections, difflib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "dostavka")

problems = []


def bad(page, kind, detail):
    problems.append((page, kind, detail))


pages = {}
for path in glob.glob(os.path.join(DIR, "**", "index.html"), recursive=True):
    url = "/" + os.path.relpath(os.path.dirname(path), ROOT).replace(os.sep, "/") + "/"
    pages[url] = io.open(path, encoding="utf-8").read()

if not pages:
    sys.exit("страницы не найдены, сначала соберите сайт")

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr", "!doctype"}
TAG = re.compile(r"<(/?)([a-zA-Z!][a-zA-Z0-9-]*)[^>]*?(/?)>")

titles = collections.defaultdict(list)
descs = collections.defaultdict(list)
anchors = collections.defaultdict(set)
prose = {}

for url, html in sorted(pages.items()):

    # --- 1. баланс тегов
    # Комментарии выбрасываем до разбора. Регулярка тегов видела в "<!--"
    # тег с именем "!--" и клала его на стек навсегда, поэтому любая
    # страница с комментарием в теле объявлялась сломанной. Заодно это
    # чинит настоящую дыру: закомментированный <div> раньше тоже попадал
    # на стек, хотя браузер его не видит.
    stack = []
    scan = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    for closing, name, selfclose in TAG.findall(scan):
        n = name.lower()
        if n in VOID or selfclose:
            continue
        if closing:
            if not stack:
                bad(url, "теги", "закрывающий </%s> без открывающего" % n)
                break
            if stack[-1] != n:
                bad(url, "теги", "ожидался </%s>, встретился </%s>" % (stack[-1], n))
                break
            stack.pop()
        else:
            stack.append(n)
    else:
        if stack:
            bad(url, "теги", "не закрыты: %s" % ", ".join(stack[-5:]))

    # --- 2. JSON-LD валиден и FAQ совпадает один в один с разметкой
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>',
                         html, re.S):
        try:
            data = json.loads(m.group(1))
        except ValueError as e:
            bad(url, "json-ld", "не парсится: %s" % e)
            continue
        nodes = data.get("@graph", [data])
        for node in nodes:
            if node.get("@type") == "FAQPage":
                schema_q = [q["name"] for q in node.get("mainEntity", [])]
                page_q = re.findall(r"<summary>(.*?)</summary>", html, re.S)
                page_q = [re.sub(r"<[^>]+>", "", q).strip() for q in page_q]
                if schema_q != page_q:
                    only_s = set(schema_q) - set(page_q)
                    only_p = set(page_q) - set(schema_q)
                    bad(url, "faq", "разметка и текст расходятся: только в схеме %s, "
                                    "только на странице %s"
                        % (sorted(only_s)[:2], sorted(only_p)[:2]))

    # --- 3. тире: в проекте только дефис
    for ch, name in (("—", "длинное тире"), ("–", "среднее тире"),
                     ("−", "минус"), ("­", "мягкий перенос")):
        if ch in html:
            ctx = html[max(0, html.index(ch) - 40):html.index(ch) + 40]
            bad(url, "типографика", "%s: ...%s..." % (name, ctx.replace("\n", " ")))

    # --- 4. остатки шаблонизатора
    for pat in (r"\{\{", r"\{%", r"\bUndefined\b"):
        if re.search(pat, html):
            bad(url, "jinja", "в выводе остался %s" % pat)

    # --- 5. значения-заглушки, попавшие в текст
    for pat in (r">\s*None\s*<", r">\s*True\s*<", r">\s*False\s*<",
                r"\bTODO\b", r"\bFIXME\b", r"\bXXX\b", r">\s*\[\]\s*<",
                r">\s*\{\}\s*<", r"\bNaN\b"):
        m = re.search(pat, html)
        if m:
            bad(url, "заглушка", "в тексте %r" % m.group(0))

    # --- 6. пустые смысловые теги
    for m in re.finditer(r"<(h[1-6]|p|li|td|th|summary|strong|caption)>\s*</\1>", html):
        bad(url, "пустой тег", m.group(0))

    # --- 7. латиница внутри русского слова и наоборот
    for m in re.finditer(r"[А-Яа-яЁё]+[A-Za-z]+|[A-Za-z]+[А-Яа-яЁё]+", html):
        w = m.group(0)
        ctx = html[max(0, m.start() - 30):m.end() + 30]
        if "<" in ctx and ">" in ctx and re.search(r"<[^>]*%s" % re.escape(w), ctx):
            continue  # часть тега или атрибута
        bad(url, "смешанный алфавит", w)

    # --- 8. посторонние системы письма
    for m in re.finditer(r"[一-鿿぀-ヿ؀-ۿ֐-׿]", html):
        bad(url, "чужой алфавит", html[max(0, m.start() - 30):m.start() + 30])

    # --- 9. тема другого проекта: защита от аффилиат-фильтра с fanline.su
    for w in ("чернозём", "чернозем", "торф", "перегной",
              "навоз", "биогумус", "сапропель"):
        if re.search(r"\b%s" % w, html, re.I):
            bad(url, "чужая тема", "слово %r принадлежит fanline.su" % w)
    # "плодородный слой" у нас законен: его снимают перед отсыпкой.
    # Чужая тема - когда плодородку предлагают как товар.
    for m in re.finditer(r"плодородн\w*\s+(грунт\w*|земл\w+|почв\w+)", html, re.I):
        bad(url, "чужая тема", "%r это товар fanline.su" % m.group(0))

    # --- 10. мета
    t = re.search(r"<title>(.*?)</title>", html, re.S)
    d = re.search(r'<meta name="description" content="(.*?)"', html, re.S)
    if not t:
        bad(url, "мета", "нет title")
    else:
        tt = t.group(1).strip()
        titles[tt].append(url)
        if not 25 <= len(tt) <= 75:
            bad(url, "мета", "title %d символов: %s" % (len(tt), tt))
    if not d:
        bad(url, "мета", "нет description")
    else:
        dd = d.group(1).strip()
        descs[dd].append(url)
        if not 70 <= len(dd) <= 200:
            bad(url, "мета", "description %d символов" % len(dd))

    h1 = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    if len(h1) != 1:
        bad(url, "структура", "h1 на странице: %d" % len(h1))

    # --- 11. картинки: alt, существование файла, заявленные размеры
    # Проверка src появилась после того, как подменённый путь к фото
    # прошёл всю сюиту незамеченным: проверялись только href.
    for m in re.finditer(r"<img\b[^>]*>", html):
        tag = m.group(0)
        if 'alt="' not in tag:
            bad(url, "доступность", "img без alt: %s" % tag[:60])
        src = re.search(r'src="([^"]+)"', tag)
        if not src:
            bad(url, "картинка", "img без src: %s" % tag[:60])
            continue
        path = src.group(1)
        if path.startswith("http") or path.startswith("data:"):
            continue
        fs = os.path.join(ROOT, path.split("?")[0].lstrip("/"))
        if not os.path.exists(fs):
            bad(url, "ссылка", "битая картинка: %s" % path)
            continue
        wm = re.search(r'width="(\d+)"', tag)
        hm = re.search(r'height="(\d+)"', tag)
        if wm and hm:
            try:
                from PIL import Image as _Im
                with _Im.open(fs) as _i:
                    rw, rh = _i.size
                if (rw, rh) != (int(wm.group(1)), int(hm.group(1))):
                    bad(url, "картинка",
                        "размеры в теге %sx%s, у файла %dx%d: браузер зарезервирует "
                        "неверное место и вёрстка прыгнет"
                        % (wm.group(1), hm.group(1), rw, rh))
            except ImportError:
                pass

    # --- 12. якоря и ссылки
    for m in re.finditer(r'id="([^"]+)"', html):
        anchors[url].add(m.group(1))

    # --- 13. падежи и согласование: шаблоны реальных прошлых ошибок
    for pat, why in (
        (r"виды щебень", "нужен родительный: виды щебня"),
        (r"привезёте щебня\b", "нужен винительный: привезёте щебень"),
        (r"(?:Цены на |Щебень |Песок |Отсев |Керамзит |Гравий )"
         r"(?:и \w+ )?в (Нижний Тагил|Первоуральск|Полевской|Ревду|Ирбит|"
         r"Асбест|Арамиль|Сысерть|Дегтярск|Билимбай|Невьянск|Реж|Камышлов|"
         r"Новоуральск|Серов|Кушву|Качканар|Михайловск|Красноуфимск|"
         r"Сухой Лог|Талицу|Заречный|Белоярский|Артёмовский|Краснотурьинск|"
         r"Верхнюю Пышму|Верхнюю Салду|Богданович|Берёзовский|Среднеуральск)\b",
         "материал требует предложного падежа: щебень в Реже, а не в Реж"),
        (r"\bот екатеринбург", "нужна заглавная и родительный"),
        (r"\bДля [А-ЯЁ][а-яё]+ итог", "неестественная конструкция"),
        (r"[а-яё]\. [а-яё]{3,}", "предложение начинается со строчной"),
        (r"\bв Нижний Тагиле\b|\bв Нижнем Тагил\b", "рассогласование"),
        (r"\s+([,.:;!?])", "пробел перед знаком препинания"),
        (r"([,.:;!?]){2,}", "двойной знак препинания"),
        (r"\bперевод\. [а-яё]", "предложение начинается со строчной"),
    ):
        for m in re.finditer(pat, html, re.I if "щебень" in pat else 0):
            frag = html[max(0, m.start() - 50):m.end() + 50].replace("\n", " ")
            if "<" in m.group(0) or "http" in frag:
                continue
            bad(url, "грамматика", "%s: ...%s..." % (why, frag))

    # текст без разметки для сравнения страниц между собой
    body = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    body = re.sub(r"<style.*?</style>", " ", body, flags=re.S)
    prose[url] = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)).strip()

# --- 14. дубли мета
for t, urls in titles.items():
    if len(urls) > 1:
        bad(urls[1], "дубль", "title повторяется на %s" % ", ".join(urls))
for d, urls in descs.items():
    if len(urls) > 1:
        bad(urls[1], "дубль", "description повторяется на %s" % ", ".join(urls))

# --- 15. внутренние ссылки и якоря
for url, html in sorted(pages.items()):
    for m in re.finditer(r'href="(/[^"#?]*)(\?[^"#]*)?(#[^"]*)?"', html):
        target, frag = m.group(1), m.group(3)
        if not target.endswith("/"):
            if not os.path.exists(os.path.join(ROOT, target.lstrip("/"))):
                bad(url, "ссылка", "битая: %s" % target)
            continue
        if target not in pages and not os.path.exists(
                os.path.join(ROOT, target.strip("/"), "index.html")):
            bad(url, "ссылка", "битая: %s" % target)
            continue
        if frag:
            aid = frag[1:]
            tgt = target if target in anchors else url
            if aid and aid not in anchors.get(target, anchors.get(url, set())):
                bad(url, "якорь", "нет #%s на %s" % (aid, target))
    for m in re.finditer(r'href="(#[^"]+)"', html):
        aid = m.group(1)[1:]
        if aid not in anchors[url]:
            bad(url, "якорь", "нет #%s на самой странице" % aid)

# --- 16. один и тот же анкор ведёт на разные адреса
anchor_map = collections.defaultdict(set)
for url, html in pages.items():
    for m in re.finditer(r'<a [^>]*href="([^"]+)"[^>]*>([^<]{4,})</a>', html):
        anchor_map[m.group(2).strip()].add(m.group(1))
for text, hrefs in anchor_map.items():
    if len(hrefs) > 1 and not text.startswith(("Написать", "Узнать", "Рассчитать",
                                               "Связаться", "Отправить")):
        bad("(весь раздел)", "анкор", "%r ведёт на %s" % (text, sorted(hrefs)))

# --- 20. сироты: на каждую страницу должны вести ссылки с других страниц
# Появилась после того, как семь новых статей собрались, прошли всю сюиту
# и оказались недостижимы: список связанных обрезался на двенадцати, а статей
# стало двадцать три. Sitemap их содержал, ссылок не вело ни одной, и ни одна
# из девятнадцати проверок этого не заметила.
_links = collections.defaultdict(set)
for url, html in pages.items():
    for href in re.findall(r'href="(/dostavka/[^"#?]*)"', html):
        if not href.endswith("/"):
            href += "/"
        if href != url:
            _links[href].add(url)
MIN_IN = 3
for url in sorted(pages):
    if url.endswith("/spasibo/"):      # страница благодарности вне навигации
        continue
    n = len(_links.get(url, ()))
    if n < MIN_IN:
        bad(url, "сироты", "входящих внутренних ссылок %d, нужно от %d" % (n, MIN_IN))

# --- 17. похожесть страниц: защита от дорвейности
urls = sorted(prose)
for i, a in enumerate(urls):
    for b in urls[i + 1:]:
        r = difflib.SequenceMatcher(None, prose[a][:6000], prose[b][:6000]).ratio()
        if r >= 0.80:
            bad(a, "дорвей", "совпадение %.0f%% с %s" % (r * 100, b))

# --- 18. арифметика в текстах, которую легко сломать правкой
ARITH = [
    ("10 кубов гранитного щебня = 14 т", 10 * 1.4, 14, 0.2),
    ("20 т песка = 12,9 куба", 20 / 1.55, 12.9, 0.2),
    ("80 м2 x 0,15 м = 12 кубов", 80 * 0.15, 12, 0.01),
    ("12 кубов x 1,2 = 14,4", 12 * 1.2, 14.4, 0.01),
    ("6 кубов бетона М300 -> 4,7 куба щебня", 6 * 0.79, 4.74, 0.1),
    ("6 кубов бетона М300 -> 2,7 куба песка", 6 * 0.45, 2.7, 0.05),
    ("100 м2 x 0,15 м = 15 кубов", 100 * 0.15, 15, 0.01),
    ("15 x 1,2 = 18 кубов", 15 * 1.2, 18, 0.01),
    ("350 кг цемента = 7 мешков по 50", 350 / 50, 7, 0.01),
    ("тонна щебня = 0,72 куба", 1 / 1.39, 0.72, 0.01),
    ("тонна песка = 0,65 куба", 1 / 1.55, 0.65, 0.01),
    ("50 м2 слой 0,15 щебень к1.2 = 9 кубов", 50 * 0.15 * 1.2, 9, 0.01),
    ("200 м2 слой 0,2 к1.2 = 48 кубов", 200 * 0.2 * 1.2, 48, 0.01),
]
# Калькулятор: формула в data/calc.py и в assets/calc.js должна давать
# одно и то же. Расхождение означает, что человек видит одну сумму,
# а в заявке получает другую, и заметить это без проверки нельзя.
sys.path.insert(0, os.path.join(ROOT, "dostavka-src", "data"))
try:
    from calc import estimate as _est, RATE_PER_KM as _RATE, trips as _trips
    ARITH += [
        ("калькулятор: 10 м³ x 1400 + 45 км x 95", _est(10, 1400, 45)["total"], 18275, 0.01),
        ("калькулятор: 5 м³ x 350 + 25 км x 95", _est(5, 350, 25)["total"], 4125, 0.01),
        ("калькулятор: 30 м³ это 2 рейса по 20", _trips(30)[0], 2, 0.01),
        ("калькулятор: 30 м³ x 500 + 2 рейса x 140 км x 95", _est(30, 500, 140)["total"], 41600, 0.01),
        ("тариф в конфиге 95 руб/км", _RATE, 95, 0.01),
    ]
    _js = io.open(os.path.join(DIR, "assets", "calc.js"), encoding="utf-8").read()
    for _need in ("TRUCKS = [5, 10, 20]", "Math.ceil(v / big)", "v * price", "t.n * km * RATE"):
        if _need not in _js:
            bad("(калькулятор)", "арифметика",
                "формула в calc.js разошлась с calc.py: нет %r" % _need)
except Exception as _e:
    bad("(калькулятор)", "арифметика", "не удалось проверить: %s" % _e)

for name, got, want, tol in ARITH:
    if abs(got - want) > tol:
        bad("(тексты)", "арифметика", "%s: расчёт даёт %.2f" % (name, got))

# --- 19. классы в разметке без стилей и стили без разметки
# Появилось после редизайна: CSS был написан под воображаемую разметку,
# и весь каталог с подвалом уехали в прод без оформления. Глазами
# это заметно не на всех страницах, а расхождение видно сразу.
_css_path = os.path.join(DIR, "assets", "dostavka.css")
if os.path.exists(_css_path):
    _css = io.open(_css_path, encoding="utf-8").read()
    _css_nc = re.sub(r"/\*.*?\*/", " ", _css, flags=re.S)
    _defined = set(re.findall(r"\.([a-zA-Z][\w-]*)", _css_nc))
    _used = collections.Counter()
    for _u, _h in pages.items():
        for _m in re.finditer(r'class="([^"]+)"', _h):
            for _c in _m.group(1).split():
                _used[_c] += 1
    for _c, _n in sorted(_used.items()):
        if _c.startswith("d-") and _c not in _defined:
            bad("(стили)", "css", "класс %r есть на %d страницах, но стилей нет" % (_c, _n))
    for _c in sorted(_defined):
        if _c.startswith("d-") and _c not in _used:
            bad("(стили)", "css", "стиль для %r написан, но такого класса в разметке нет" % _c)

# --- 21. каноникализация: canonical обязан вести на существующую страницу
# Появилось в ШАГЕ 1 архитектуры каталога. Канон, ведущий в никуда, хуже
# отсутствующего: он склеивает живую страницу с ошибкой 404, и из индекса
# выпадают обе. Проверяются четыре вещи сразу: тег есть, он абсолютный,
# он заканчивается слешем и он указывает на реально собранный документ.
_urls = set(pages.keys())
for _u, _h in pages.items():
    _m = re.search(r'<link rel="canonical" href="([^"]+)"', _h)
    if not _m:
        bad(_u, "canonical", "тега нет")
        continue
    _c = _m.group(1)
    if not _c.startswith("https://"):
        bad(_u, "canonical", "не абсолютный: %r" % _c)
        continue
    if "?" in _c or "#" in _c or "index.html" in _c:
        bad(_u, "canonical", "не чистый адрес: %r" % _c)
    if not _c.endswith("/"):
        bad(_u, "canonical", "без завершающего слеша: %r" % _c)
    _path = _c.split("ursdom.ru", 1)[-1]
    if _path not in _urls:
        bad(_u, "canonical", "ведёт на несуществующую страницу %r" % _path)

# --- 22. Clean-param в robots.txt для Яндекса
# Секция Yandex должна быть полной: найдя свою секцию, Яндекс полностью
# игнорирует User-agent: *, и Disallow из общей секции на него не действуют.
_rob = os.path.join(ROOT, "robots.txt")
if os.path.exists(_rob):
    _r = io.open(_rob, encoding="utf-8").read()
    if "User-agent: Yandex" not in _r:
        bad("(robots)", "robots", "нет отдельной секции User-agent: Yandex")
    else:
        _ya = _r.split("User-agent: Yandex", 1)[1].split("User-agent:", 1)[0]
        if "Clean-param:" not in _ya:
            bad("(robots)", "robots", "в секции Yandex нет Clean-param")
        for _d in ("/audit/", "/dostavka-src/", "/generator/"):
            if _d not in _ya:
                bad("(robots)", "robots",
                    "секция Yandex не закрывает %s, а общую секцию Яндекс игнорирует" % _d)

# ------------------------------------------------------------------ вывод
by_kind = collections.Counter(k for _, k, _ in problems)
print("страниц проверено: %d" % len(pages))
if not problems:
    print("проблем не найдено")
    sys.exit(0)
print("проблем: %d" % len(problems))
for k, n in by_kind.most_common():
    print("  %-20s %d" % (k, n))
print()
for page, kind, detail in problems[:80]:
    print("[%s] %s\n    %s" % (kind, page, detail[:300]))
sys.exit(1)
