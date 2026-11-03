# -*- coding: utf-8 -*-
"""Разбор подсказок: чистка, сверка со статьями сайта, группировка новых тем.

Выход (в папке скрипта):
  sug.json         - все чистые фразы с разметкой
  plan.json        - темы для новых статей и фразы для дописывания
"""
import collections, glob, html, io, json, os, re, sys
import pymorphy3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/user/ursdom-site"
sys.path.insert(0, ROOT + "/audit")
import _wordstat  # found_in, segments, query_tokens

M = pymorphy3.MorphAnalyzer()
_lc, _geo = {}, {}


def lem(w):
    if w not in _lc:
        p = M.parse(w)[0]
        _lc[w] = p.normal_form.replace("ё", "е")
        _geo[w] = "Geox" in p.tag or "Surn" in p.tag and False
    return _lc[w]


def toks(s):
    s = s.lower().replace("ё", "е").replace("³", "3")
    s = re.sub(r"[‐-―\-/×]", " ", s)
    return re.findall(r"[a-zа-я0-9]+", s)


STOP = set("в во на с со и для под по из от до к у о об за при без или а как что это ли же".split())
GENERIC = set("какой сколько как размер вес гост цена расход таблица толщина схема своими руками "
              "чем для под или плюс минус лучше нужно надо можно сделать фото видео".split())

FANLINE = re.compile(r"торф|чернозем|чернозём|перегно|навоз|биогумус|сапропел|плодородн|гряд|рассад|удобрен|посадк|сорт\w* |урожа|полив")
DOMAIN = re.compile(r"щеб|песо?к|песк|песч|грави|отсев|пгс|щпс|бетон|цемент|раствор|фундамент|жби|\bжб\b|плит|блок|кольц|бордюр|поребрик|брусчат|отмостк|стяжк|засып|отсып|подсып|дренаж|керамзит|глин|камн|камен|крошк|арматур|армир|опалубк|ростверк|армопояс|сва[ий]|столб|забор|колод|септик|лот[ок]|лотк|люк|ступен|крыльц|дорожк|площадк|заезд|подушк|грунт|уплотн|гидроизол|утепл|погреб|подпол|\bям|кессон|\bпол\b|пола\b|полы\b|ворот|основани|штукатур|клей|кладк|кирпич|шлак|дресв|извест|смес|асфальт|ливнев|водосток|водоотвод|перемычк|марш|перекрыт|ригел|вентблок|полусфер|вазон|промерзан|цокол|миксер|бетононасос|трещин|пропитк|участ")
SHOPS = re.compile(r"леруа|лемана|авито|озон|ozon|wildberries|вайлдберриз|петрович|\bоби\b|максидом|"
                   r"касторама|хоббиком|яндекс маркет|алиэкспресс|aliexpress|видео|youtube|ютуб|"
                   r"скачать|pdf|dwg|чертеж|чертёж|реферат|презентац|курсовая|егэ|огэ|кроссворд|"
                   r"майнкрафт|minecraft|\bсон\b|сонник|игра")
COMM = re.compile(r"купить|куплю|цен[аыуе]|стоимост|стоит|стоят|достав|прода[жт]|заказ|недорог|дешев|прайс|"
                  r"оптом|самовывоз|аренд|производител|завод|магазин|вакансии|работа ")
# посторонние значения слов-затравок
OFFTOPIC = re.compile(r"поршнев|обручальн|кольц[ао] для (штор|ключ|девушк)|золот|серебр|ювелир|"
                      r"олимпийск|гимнаст|кольца сатурн|властелин|кольцо всевластия|"
                      r"бордюр для (ногт|обоев|торта|кухн|ванн|столешниц)|бордюр (в ванн|на кухн|для плитки в ванн)|"
                      r"обои|потолочн|багет|скинали|маникюр|ногт|торт|"
                      r"песок (в глаз|в почк|в желч|в мочев)|почк|желч|мочев|кинетическ|"
                      r"сахарн|песочн(ое|ые|ая) (печень|тест)|аквариум|кошачий|для кошек|"
                      r"керамзит для (растений|цветов|орхидей)|орхиде|комнатн|"
                      r"щебень в (майнкрафт|игре)|гравий для аквариума|гравийн(ый|ого) байк|"
                      r"асфальтов(ая|ой) болезн|отмостк[аи] зуб|"
                      r"бут(ик|ерброд|ылк|сы)|пескоструй(ный аппарат|ка своими)|"
                      r"\bгта\b|\bgta\b|лего|lego|тату")
EKB_CITIES = set()


def is_geo(t_list):
    for w in t_list:
        lem(w)
        if _geo.get(w):
            return True
    return False


def load_raw():
    rows = collections.OrderedDict()
    for line in io.open(os.path.join(HERE, "raw.jsonl"), encoding="utf-8"):
        d = json.loads(line)
        for i, s in enumerate(d["s"]):
            s = re.sub(r"\s+", " ", s.strip().lower().replace("ё", "е"))
            if not s:
                continue
            r = rows.setdefault(s, {"q": s, "eng": set(), "seeds": set(), "score": 0.0, "hits": 0})
            r["eng"].add(d["e"])
            r["seeds"].add(d["seed"])
            r["score"] += (10 - min(i, 9)) / 10.0
            r["hits"] += 1
    return list(rows.values())


def classify(r):
    q = r["q"]
    t = toks(q)
    if len(t) < 2:
        return "короткий"
    if FANLINE.search(q):
        return "тема fanline"
    if SHOPS.search(q):
        return "магазин или не текст"
    if OFFTOPIC.search(q):
        return "другое значение"
    if not DOMAIN.search(q):
        return "вне темы"
    if is_geo(t):
        return "город или регион"
    if COMM.search(q):
        return "коммерческий"
    return "инфо"


def site_pages():
    pages = {}
    globs = ["dostavka/stati/*/index.html", "drenazh/*/index.html", "skvazhina/*/index.html",
             "livnevka/*/index.html", "dostavka/kalkulyator/*/index.html"]
    for g in globs:
        for p in glob.glob(os.path.join(ROOT, g)):
            u = "/" + os.path.relpath(os.path.dirname(p), ROOT) + "/"
            h = io.open(p, encoding="utf-8").read()
            t = re.search(r"<title>(.*?)</title>", h, re.S)
            h1 = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
            hs = re.findall(r"<h[23][^>]*>(.*?)</h[23]>", h, re.S)
            clean = lambda x: html.unescape(re.sub(r"<[^>]+>", "", x or "")).strip()
            title = clean(t.group(1)) if t else ""
            head = clean(h1.group(1)) if h1 else ""
            pages[u] = dict(url=u, title=title, h1=head,
                            hl=set(lem(w) for w in toks(title + " " + head) if w not in STOP),
                            sl=set(lem(w) for w in toks(" ".join(clean(x) for x in hs)) if w not in STOP),
                            segs=_wordstat.segments(h))
    return pages


def content_lemmas(q):
    return [lem(w) for w in toks(q) if w not in STOP]


def main():
    raw = load_raw()
    for r in raw:
        r["cls"] = classify(r)
    info = [r for r in raw if r["cls"] == "инфо"]
    pages = site_pages()
    # сверка с сайтом
    for r in info:
        L = content_lemmas(r["q"])
        core = [x for x in L if x not in GENERIC and not x.isdigit()] or L
        best, bs = None, 0.0
        for u, p in pages.items():
            s = sum(1.0 for x in core if x in p["hl"]) + sum(0.5 for x in core if x in p["sl"] and x not in p["hl"])
            s /= max(1, len(core))
            if s > bs:
                best, bs = u, s
        r["best"], r["best_s"] = best, round(bs, 2)
        qt = _wordstat.query_tokens(r["q"])
        r["exact"] = any(_wordstat.found_in(qt, p["segs"]) for p in pages.values())
        r["core"] = sorted(set(core))
    # статус: закрыто (точная фраза на лучшей странице), дописать (тема та же), новая тема
    for r in info:
        if r["best_s"] >= 0.99 and r["exact"]:
            r["status"] = "уже есть"
        elif r["best_s"] >= 0.66:
            r["status"] = "дописать в статью"
        else:
            r["status"] = "новая тема"
    # группировка новых тем: жадно по ядру лемм
    new = sorted([r for r in info if r["status"] == "новая тема"], key=lambda r: -r["score"])
    clusters = []
    for r in new:
        cs = set(r["core"])
        placed = False
        for c in clusters:
            inter = len(cs & c["core"])
            if inter and inter / len(cs | c["core"]) >= 0.5:
                c["items"].append(r)
                placed = True
                break
        if not placed:
            clusters.append({"core": cs, "items": [r]})
    for c in clusters:
        c["score"] = round(sum(x["score"] for x in c["items"]), 1)
        c["both"] = sum(1 for x in c["items"] if len(x["eng"]) == 2)
        c["name"] = c["items"][0]["q"]
        c["near"] = c["items"][0]["best"]
    clusters.sort(key=lambda c: -c["score"])
    # дописать: по статьям
    add = collections.defaultdict(list)
    for r in info:
        if r["status"] == "дописать в статью":
            add[r["best"]].append(r)
    stat = collections.Counter(r["cls"] for r in raw)
    stat2 = collections.Counter(r["status"] for r in info)
    json.dump({"stat": stat, "stat2": stat2,
               "clusters": [{"name": c["name"], "score": c["score"], "n": len(c["items"]),
                             "both": c["both"], "near": c["near"],
                             "phrases": [x["q"] for x in c["items"]]} for c in clusters],
               "add": {u: sorted([(x["q"], round(x["score"], 1)) for x in L], key=lambda t: -t[1])
                       for u, L in add.items()},
               "titles": {u: p["title"] for u, p in pages.items()}},
              open(os.path.join(HERE, "plan.json"), "w"), ensure_ascii=False, indent=0)
    for r in raw:
        r["eng"] = sorted(r["eng"]); r["seeds"] = sorted(r["seeds"])
    json.dump(raw, open(os.path.join(HERE, "sug.json"), "w"), ensure_ascii=False)
    print("фраз всего", len(raw), dict(stat))
    print("инфо по статусу", dict(stat2))
    print("новых тем", len(clusters), "из них с 3+ фразами", sum(1 for c in clusters if len(c["items"]) >= 3))
    for c in clusters[:40]:
        print("%6.1f %3d %s | рядом %s" % (c["score"], len(c["items"]), c["name"], c["near"]))


if __name__ == "__main__":
    main()
