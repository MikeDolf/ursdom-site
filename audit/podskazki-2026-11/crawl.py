# -*- coding: utf-8 -*-
"""Сбор поисковых подсказок Яндекса и Google по затравкам.

Для каждой затравки: сама затравка, затравка + буква а-я, затравка + уточнение.
Результат пишется построчно в jsonl, повторный запуск продолжает с места остановки.
"""
import json, os, sys, time, urllib.parse, urllib.request, random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "raw.jsonl")
DONE = os.path.join(HERE, "done.txt")

SEEDS = [
    # лидеры трафика и их соседи
    "размеры колец жби", "кольца жби", "кольца бетонные", "кольца для колодца", "кольцо с дном",
    "крышка колодца бетонная", "коэффициент уплотнения", "уплотнение грунта", "размеры бордюров",
    "бордюр", "поребрик", "бордюрный камень",
    # ЖБИ
    "блоки фбс", "фбс размеры", "плиты перекрытия", "плита дорожная", "аэродромные плиты",
    "лотки жби", "лоток водоотводный", "труба жби", "сваи жби", "перемычки жби",
    "ступени бетонные", "бетонный забор", "еврозабор", "пескоблок", "керамзитоблок",
    "газобетон размеры", "полистиролбетон", "септик из колец", "колодец из колец",
    "люк колодца", "дождеприемник",
    # бетон и смеси
    "марки бетона", "бетон м300", "бетон м200", "куб бетона", "пропорции бетона",
    "раствор для кладки", "цементно песчаный раствор", "стяжка пола", "цемент м500",
    "керамзитобетон", "гидроизоляция бетона", "фундамент ленточный", "плитный фундамент",
    "армирование фундамента",
    # сыпучие
    "щебень", "фракции щебня", "песок", "виды песка", "пгс", "щпс", "отсев", "гравий",
    "керамзит", "скальный грунт", "асфальтовая крошка", "гранитная крошка", "бутовый камень",
    "насыпная плотность", "сколько весит куб", "удельный вес",
    # работы
    "отмостка", "дорожка из", "отсыпка участка", "подъем участка", "обратная засыпка",
    "подушка под фундамент", "дренаж участка", "основание под плитку", "укладка тротуарной плитки",
    "тротуарная плитка размеры", "брусчатка", "парковка на участке", "дорога на участке",
    "заезд на участок", "площадка под", "основание под",
]

MODS = ["размеры", "вес", "гост", "как", "сколько", "своими руками", "цена", "расход",
        "чем", "какой", "для", "под", "или", "таблица", "толщина", "схема", "плюсы и минусы"]
ALPHA = "абвгдежзиклмнопрстуфхцчшщэюя"


def ya(q):
    u = ("https://suggest.yandex.ru/suggest-ya.cgi?v=4&lr=225&part="
         + urllib.parse.quote(q))
    d = json.loads(urllib.request.urlopen(u, timeout=15).read().decode("utf-8"))
    return [x if isinstance(x, str) else x[1] for x in d[1]]


def gg(q):
    u = ("https://www.google.com/complete/search?client=firefox&hl=ru&gl=ru&q="
         + urllib.parse.quote(q))
    raw = urllib.request.urlopen(u, timeout=15).read()
    try:
        txt = raw.decode("utf-8")
    except UnicodeDecodeError:
        txt = raw.decode("cp1251")
    return json.loads(txt)[1]


def main():
    done = set(open(DONE).read().split("\n")) if os.path.exists(DONE) else set()
    jobs = []
    for s in SEEDS:
        jobs.append((s, s))
        jobs += [(s, s + " " + c) for c in ALPHA]
        jobs += [(s, s + " " + m) for m in MODS]
    print("заданий", len(jobs), "сделано", len(done), flush=True)
    import threading
    from concurrent.futures import ThreadPoolExecutor
    out = open(OUT, "a")
    dn = open(DONE, "a")
    lock = threading.Lock()
    tasks = [(seed, q, eng) for seed, q in jobs for eng in ("ya", "gg") if eng + "|" + q not in done]
    FN = {"ya": ya, "gg": gg}
    cnt = [0]

    def work(t):
        seed, q, eng = t
        res = None
        for attempt in range(3):
            try:
                res = FN[eng](q)
                break
            except Exception:
                time.sleep(3 * (attempt + 1))
        with lock:
            if res is None:
                print("ошибка", eng, q, flush=True)
                return
            out.write(json.dumps({"e": eng, "seed": seed, "q": q, "s": res}, ensure_ascii=False) + "\n")
            dn.write(eng + "|" + q + "\n")
            cnt[0] += 1
            if cnt[0] % 300 == 0:
                out.flush(); dn.flush()
                print(cnt[0], "из", len(tasks), q, flush=True)
        time.sleep(0.2 + random.random() * 0.3)

    with ThreadPoolExecutor(4) as ex:
        list(ex.map(work, tasks))
    out.close(); dn.close()
    print("готово", cnt[0], flush=True)


if __name__ == "__main__":
    main()
