# -*- coding: utf-8 -*-
"""Покрытие формулировок из выгрузки Яндекс Вордстата текстом сайта.

Владелец: «все формулировки, которые идут в выгрузке, должны быть
на сайте». Проверяется видимый текст страниц (title и содержимое
<main>, без скриптов и разметки JSON-LD), а не мета-теги: формулировка
должна читаться человеком, а не лежать в невидимом поле.

Как сравнивается. Вордстат показывает запрос нормализованным: без
предлогов («куб щебня доставкой» из «куб щебня с доставкой»), дефис
в «20-40» у него пробел, «м3» вместо «м³». Поэтому:
- регистр, «ё/е», дефисы, «³» приводятся к одному виду;
- слова запроса идут в тексте в том же порядке, между соседними
  допускается до двух слов (предлог, «и», прилагательное);
- совпадение ищется внутри одного предложения или ячейки таблицы,
  а не через точку: «щебень. Весы» формулировкой не считается.

Словоформы не склеиваются: «щебень купить» не находится во фразе
«купить щебня». Формулировка должна стоять в тексте так, как её ищут.
"""
import csv
import glob
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
GAP = 2

# Формулировки, которые на сайт не ставятся, с причиной. Всё остальное
# из выгрузки обязано найтись хотя бы на одной странице.
SKIP = {
    "селен щебень": "название чужой компании",
    "авито щебень": "поиск по чужой площадке объявлений",
}


def norm(text):
    t = text.lower().replace("ё", "е").replace("³", "3").replace("²", "2")
    t = re.sub(r"[‐-―\-/×]", " ", t)
    # «1,5» Вордстат пишет как «1 5»: знаки препинания он выбрасывает
    t = re.sub(r"(\d)[,.](\d)", r"\1 \2", t)
    return t


def segments(html):
    """Видимый текст страницы кусками: предложения, ячейки, пункты."""
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    main = re.search(r"<main[^>]*>(.*?)</main>", html, re.S)
    body = (title.group(1) if title else "") + " . " + (main.group(1) if main else "")
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", body, flags=re.S)
    # границы блоков становятся границами предложений
    body = re.sub(r"</?(p|li|td|th|h[1-6]|div|section|tr|caption|summary|figcaption|dt|dd|br)[^>]*>",
                  " . ", body)
    body = re.sub(r"<[^>]+>", " ", body)
    body = (body.replace("&nbsp;", " ").replace("&laquo;", "«").replace("&raquo;", "»")
                .replace("&quot;", '"').replace("&amp;", "&"))
    out = []
    # Точка после одиночной буквы это сокращение («Н. Тагил», «г. Екатеринбург»),
    # а не конец предложения: по ней фраза не рвётся.
    for seg in re.split(r"(?<![\s(][а-яa-z])[.](?!\d)|[!?;:]", norm(body)):
        toks = re.findall(r"[a-zа-я0-9]+", seg)
        if toks:
            out.append(toks)
    return out


def query_tokens(q):
    return re.findall(r"[a-zа-я0-9]+", norm(q))


def found_in(qt, segs):
    n = len(qt)
    for toks in segs:
        L = len(toks)
        for i in range(L):
            if toks[i] != qt[0]:
                continue
            pos, ok = i, True
            for w in qt[1:]:
                nxt = next((j for j in range(pos + 1, min(L, pos + 2 + GAP)) if toks[j] == w), None)
                if nxt is None:
                    ok = False
                    break
                pos = nxt
            if ok:
                return True
    return False


def load_queries():
    rows = []
    for path in sorted(glob.glob(os.path.join(HERE, "wordstat-*.csv"))):
        if path.endswith("-otfiltr.csv"):
            continue
        with io.open(path, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                rows.append((r["запрос"].strip(), int(r["частота"] or 0)))
    seen, out = set(), []
    for q, fr in rows:
        if q not in seen:
            seen.add(q)
            out.append((q, fr))
    return out


def coverage(pages):
    """{запрос: [адреса]} по словарю {адрес: html}."""
    segs = {u: segments(h) for u, h in pages.items()}
    res = {}
    for q, _ in load_queries():
        qt = query_tokens(q)
        res[q] = [u for u, s in segs.items() if found_in(qt, s)]
    return res


if __name__ == "__main__":
    import sys
    root = os.path.dirname(HERE)
    pages = {}
    for path in glob.glob(os.path.join(root, "dostavka", "**", "index.html"), recursive=True):
        url = "/" + os.path.relpath(os.path.dirname(path), root).replace(os.sep, "/") + "/"
        pages[url] = io.open(path, encoding="utf-8").read()
    cov = coverage(pages)
    freq = dict(load_queries())
    miss = [(freq[q], q) for q, us in cov.items() if not us and q not in SKIP]
    miss.sort(reverse=True)
    print("запросов: %d, найдено: %d, нет на сайте: %d, пропущено по списку: %d"
          % (len(cov), sum(1 for u in cov.values() if u), len(miss), len(SKIP)))
    for fr, q in miss:
        print("%6d  %s" % (fr, q))
    if "-v" in sys.argv:
        for q, us in cov.items():
            if us:
                print("OK %-45s %d стр., напр. %s" % (q, len(us), us[0]))
