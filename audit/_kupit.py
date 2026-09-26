# -*- coding: utf-8 -*-
"""Коммерческие запросы «купить» из выгрузки Вордстата (audit/wordstat-kupit).

Владелец: это самые денежные запросы, тёплые покупатели, и формулировки
должны стоять на сайте точным вхождением. Здесь фильтр и разметка
по интенту; покрытие проверяет тот же _wordstat.found_in.

Что отбрасывается и почему:
- чужие регионы: мы возим по Екатеринбургу и Свердловской области,
  страница под «купить песок в Тюмени» была бы обманом;
- чужой товар под тем же словом: полимерная и косметическая глина,
  сахарный и кинетический песок, песок для аквариума и кошек, диплом
  ПГС, сайдинг «бутовый камень», лопаты;
- названия магазинов и площадок (Авито, Озон, Леруа, Лемана): под
  них страница не нужна, человек ищет конкретную витрину.
"""
import collections
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Фильтр и чтение выгрузок общие со сборкой: dostavka-src/data/kupit_cover.py.
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "dostavka-src", "data"))
from kupit_cover import load  # noqa: E402


def intent(q):
    """Грубая разметка интента для отчёта и распределения по страницам."""
    if re.search(r"мешк|биг|бэг|фасов|\bкг\b", q):
        return "фасовка"
    if re.search(r"екатеринбург|екб|свердловск|област|нижн|тагил|каменск|асбест|первоуральск|"
                 r"полевск|ревд|березовск|серов|ирбит|реж|новоуральск|невьянск|косулин|"
                 r"сысерт|пышм|белоярск|краснотурьинск|арамил|богданович|кушв|красноуфимск|"
                 r"алапаевск|салд|тур[аеы]\b|бобровск|артемовск|среднеуральск|качканар|"
                 r"билимба|исет|щит|карпинск|камышлов|талиц|сухо[мй] лог|дегтярск|заречн|"
                 r"верхн|кольцово|шарташ|малышева", q):
        return "город"
    if re.search(r"достав|цен|стоим|сколько стоит|почем|недорог|дешев|опт|тонн|куб|м3|машин|"
                 r"камаз|самосвал|самовывоз", q):
        return "цена и доставка"
    if re.search(r"для |под |в качестве", q):
        return "под задачу"
    if re.search(r"\d", q) or re.search(r"фракц|мелк|крупн|речн|карьер|мыт|сеян|строител|"
                 r"кварц|гранит|мрамор|бел|декор|шлак|известн|гравийн|вторичн|морск|"
                 r"цветн|природн|намыв|сухо|огнеуп|шамот|каолин|жирн", q):
        return "вид и фракция"
    return "купить"


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    import _wordstat
    root = os.path.dirname(HERE)
    rows = load()
    keep = [r for r in rows if not r[3]]
    drop = collections.Counter(r[3] for r in rows if r[3])
    print("всего %d, оставлено %d (%d показов), отброшено %s"
          % (len(rows), len(keep), sum(r[2] for r in keep), dict(drop)))
    pages = {}
    for path in glob.glob(os.path.join(root, "dostavka", "**", "index.html"), recursive=True):
        url = "/" + os.path.relpath(os.path.dirname(path), root).replace(os.sep, "/") + "/"
        pages[url] = io.open(path, encoding="utf-8").read()
    segs = {u: _wordstat.segments(h) for u, h in pages.items()}
    miss = collections.defaultdict(list)
    hit = 0
    for mat, q, n, _ in keep:
        qt = _wordstat.query_tokens(q)
        if any(_wordstat.found_in(qt, s) for s in segs.values()):
            hit += 1
        else:
            miss[(mat, intent(q))].append((n, q))
    print("на сайте %d из %d, нет %d" % (hit, len(keep), len(keep) - hit))
    for (mat, it), lst in sorted(miss.items(), key=lambda kv: -sum(n for n, _ in kv[1])):
        lst.sort(reverse=True)
        print("\n== %s / %s: %d запросов, %d показов" % (mat, it, len(lst), sum(n for n, _ in lst)))
        for n, q in lst[: (400 if "-a" in sys.argv else 15)]:
            print("   %5d %s" % (n, q))
