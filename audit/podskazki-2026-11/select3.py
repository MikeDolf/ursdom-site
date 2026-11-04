# -*- coding: utf-8 -*-
"""Третья партия фраз для Вордстата.

Берёт справочные подсказки (классификация из analyze.py), которые:
- ещё не проверялись в Вордстате (партии 1, 350 и 2);
- не стоят на сайте дословно;
- не мусор (чужие значения слов, электромонтаж, кулинария, мебель);
и раскладывает их по темам, чтобы партия покрывала много тем, а не
сотню вариантов одной.

Запуск: распаковать raw.jsonl.gz в raw.jsonl рядом, затем
python3 select3.py  ->  proverit-partiya3.txt
"""
import collections, csv, glob, io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze as A
import _wordstat as W

N_TOTAL = 400
PER_TOPIC = 4

# Мусор, который подсказки цепляют к нашим словам.
JUNK = re.compile(
    r"морожен|пудинг|десерт|выпечк|коктейл|матрас|кроват|диван|"
    r"хомут|промрукав|монтажн\w* пистолет|площадк\w* под стяжк|кабельн\w* стяжк|"
    r"шлаг|как пишется|кроссворд|ударени|синоним|"
    r"\bрб\b|беларус|казахстан|украин|"
    r"под ключ|фото|отзыв|форум|своими руками из бочк|"
    r"кирпич\w* поддон|поддон кирпич|вибратор|перфоратор|дрел|"
    r"эпоксид|для лепки|глазур|"
    r"\bсон\b|приснил|"
    r"мпа$|методы испытаний|паспорт качества|гарантийн")


def checked():
    seen = set()
    for p in ("proverit-v-wordstat.txt", "proverit-350.txt", "proverit-partiya2.txt"):
        for line in io.open(os.path.join(HERE, p), encoding="utf-8"):
            if line.strip():
                seen.add(" ".join(W.query_tokens(line.strip())))
    for p in glob.glob(os.path.join(HERE, "wordstat-partiya*-rezultat.csv")):
        for r in list(csv.reader(io.open(p, encoding="utf-8-sig"), delimiter=";"))[1:]:
            if len(r) > 1:
                seen.add(" ".join(W.query_tokens(r[1])))
    return seen


def on_site(queries):
    """Какие из фраз (списки токенов) стоят где-то на сайте подряд."""
    by_first = collections.defaultdict(list)
    for q in queries:
        by_first[q[0]].append(q)
    found = set()
    for g in ("dostavka/**/index.html", "livnevka/**/index.html", "drenazh/**/index.html",
              "skvazhina/**/index.html"):
        for p in glob.glob(os.path.join(A.ROOT, g), recursive=True):
            for t in W.segments(io.open(p, encoding="utf-8").read()):
                for i, w in enumerate(t):
                    for q in by_first.get(w, ()):
                        if tuple(t[i:i + len(q)]) == q:
                            found.add(q)
    return found


def main():
    raw = A.load_raw()
    seen = checked()
    pre = []
    for r in raw:
        if A.classify(r) != "инфо":
            continue
        q = r["q"]
        n = len(q.split())
        if n < 2 or n > 6 or JUNK.search(q):
            continue
        qt = tuple(W.query_tokens(q))
        if not qt or " ".join(qt) in seen:
            continue
        core = tuple(sorted(set(x for x in A.content_lemmas(q) if x not in A.GENERIC and not x.isdigit())))
        if not core:
            continue
        r["core"], r["qt"] = core, qt
        pre.append(r)
    have = on_site([r["qt"] for r in pre])
    cand = [r for r in pre if r["qt"] not in have]
    print("справочных после чистки", len(pre), "из них уже на сайте", len(pre) - len(cand))
    # тема: две самых редких опорных леммы фразы
    freq = collections.Counter(x for r in cand for x in r["core"])
    topics = collections.defaultdict(list)
    for r in cand:
        key = tuple(sorted(sorted(r["core"], key=lambda x: freq[x])[:2]))
        topics[key].append(r)
    tlist = []
    for key, L in topics.items():
        L.sort(key=lambda r: -r["score"])
        tlist.append((sum(r["score"] for r in L[:10]), key, L))
    tlist.sort(key=lambda t: -t[0])
    out, used_cores = [], set()
    for rnd in range(PER_TOPIC):
        for sc, key, L in tlist:
            got = [r for r in L if r["core"] not in used_cores]
            if len(got) > 0:
                r = got[0]
                used_cores.add(r["core"])
                L.remove(r)
                out.append((sc, r["q"]))
            if len(out) >= N_TOTAL:
                break
        if len(out) >= N_TOTAL:
            break
    print("кандидатов", len(cand), "тем", len(topics), "в партии", len(out))
    io.open(os.path.join(HERE, "proverit-partiya3.txt"), "w", encoding="utf-8").write(
        "\n".join(q for sc, q in out) + "\n")


if __name__ == "__main__":
    main()
