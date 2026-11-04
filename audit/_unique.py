# -*- coding: utf-8 -*-
"""Уникальность и шаблонность новых статей внутри сайта.

Владелец: тексты должны быть уникальны и не шаблонны. Здесь проверяется
то, что можно проверить без внешнего сервиса:

1. Повторы с другими страницами сайта. Текст режется на фрагменты по пять
   слов подряд (шинглы). Фрагменты, которые стоят на 15 страницах и больше,
   это общие блоки шаблона (форма заявки, доставка, оплата), их не считаем.
   Доля остальных фрагментов статьи, найденных хотя бы на одной другой
   странице, и есть процент повтора.
2. Штампы-заполнители («в этой статье», «важно отметить», «не секрет» и т.п.).
3. Одинаковые начала предложений в разных новых статьях: признак шаблона.

Запуск: python3 audit/_unique.py /dostavka/stati/slug1/ /dostavka/stati/slug2/ ...
Без адресов проверяет все страницы из audit/klyuchi-tochnye.json.
Порог: повтор больше 5% или любой штамп это ошибка (код выхода 1).
"""
import collections, glob, io, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "audit"))
import _wordstat as W

N = 5
BOILER_DF = 15
LIMIT = 0.05
STAMPS = [
    "в этой статье", "в данной статье", "давайте разберемся", "давайте рассмотрим", "важно отметить",
    "стоит отметить", "следует отметить", "не секрет", "как известно", "на сегодняшний день",
    "в заключение", "подводя итог", "играет важную роль", "широко используется", "обладает рядом",
    "является одним из", "в наше время", "ни для кого не секрет", "в современном мире",
    "огромное значение", "неотъемлемой частью", "прежде всего стоит", "итак, ", "таким образом, можно",
    "надеемся", "мы рассмотрели", "рассмотрим подробнее", "многие задаются вопросом",
]


def body_text(html):
    m = re.search(r"<main[^>]*>(.*?)</main>", html, re.S)
    t = m.group(1) if m else html
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)
    return t


def article_text(a):
    """Только авторский текст статьи из данных: без блоков шаблона."""
    # заголовки законно повторяются в блоках «читайте также» на других страницах
    parts = [a.get("hero_sub", ""), a.get("lead", ""), a.get("cta_text", "")]
    for sec in a.get("sections", []):
        parts.append(sec.get("h", ""))
        for k in ("p", "ul", "ol", "steps", "after", "callout", "callout_warn"):
            # в дописках встречаются и строки, и списки
            parts += list(sec.get(k, []))
        t = sec.get("table")
        if t:
            parts.append(t.get("caption", ""))
            parts += [" , ".join(r) for r in t.get("rows", [])]
        for sb in sec.get("sub", []):
            parts.append(sb.get("h3", ""))
            parts += list(sb.get("p", [])) + list(sb.get("ul", []))
    for q, a_ in a.get("faq", []):
        parts += [q, a_]
    return " . ".join(parts)


def shingles_of(text):
    s = set()
    for toks in W.segments("<main>" + text + "</main>"):
        for i in range(len(toks) - N + 1):
            s.add(tuple(toks[i:i + N]))
    return s


def main():
    sys.path.insert(0, os.path.join(ROOT, "dostavka-src", "data"))
    from longreads_ws2 import WS2_LONGREADS
    arts = {"/dostavka/" + a["slug"] + "/": a for a in WS2_LONGREADS}
    # дописки к существующим страницам: проверяется только добавленный текст
    from wordstat_cover2 import S as _S2, F as _F2
    from wordstat_cover3 import S as _S3, F as _F3
    for _sl in set(_S2) | set(_F2) | set(_S3) | set(_F3):
        arts["/dostavka/" + _sl + "/"] = {"sections": _S2.get(_sl, []) + _S3.get(_sl, []),
                                          "faq": list(_F2.get(_sl, [])) + list(_F3.get(_sl, []))}
    pages = {}
    for p in glob.glob(os.path.join(ROOT, "dostavka", "**", "index.html"), recursive=True):
        u = "/" + os.path.relpath(os.path.dirname(p), ROOT).replace(os.sep, "/") + "/"
        pages[u] = io.open(p, encoding="utf-8").read()
    targets = [a for a in sys.argv[1:] if a.startswith("/")] or sorted(arts)
    sh = {u: shingles_of(body_text(h)) for u, h in pages.items()}
    df = collections.Counter()
    for s in sh.values():
        df.update(s)
    boiler = {g for g, n in df.items() if n >= BOILER_DF}
    fail = False
    starts = collections.defaultdict(set)
    own_all = {}
    for u in targets:
        own = shingles_of(article_text(arts[u])) - boiler
        own_all[u] = own
        hit = collections.Counter()
        rep = set()
        for v, s in sh.items():
            # блог выводит заголовки и анонсы этих же статей: это не повтор
            if v == u or v == "/dostavka/stati/":
                continue
            k = own & s
            if k:
                hit[v] = len(k)
                rep |= k
        share = len(rep) / max(1, len(own))
        txt = W.norm(article_text(arts[u]))
        st = [x for x in STAMPS if x in txt]
        for seg in W.segments("<main>" + article_text(arts[u]) + "</main>"):
            if len(seg) >= 6:
                starts[" ".join(seg[:3])].add(u)
        flag = share > LIMIT or st
        fail = fail or flag
        print("%s %-45s фрагментов %4d, повтор %.1f%%%s%s" % (
            "!!" if flag else "ok", u, len(own), share * 100,
            ", больше всего общего с %s (%d)" % hit.most_common(1)[0] if hit else "",
            ", штампы: %s" % ", ".join(st) if st else ""))
        for g in sorted(rep)[:40 if "-v" in sys.argv else (6 if share > LIMIT else 0)]:
            print("      повтор: %s" % " ".join(g))
    common = {k: v for k, v in starts.items() if len(v) >= 3}
    if common:
        print("одинаковые начала предложений в 3+ новых статьях:")
        for k, v in sorted(common.items(), key=lambda kv: -len(kv[1]))[:20]:
            print("   «%s» в %d статьях" % (k, len(v)))
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
