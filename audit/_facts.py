# -*- coding: utf-8 -*-
"""Противоречия в числах между страницами.

Самый частый дефект большого контентного сайта не опечатка, а
расхождение: на одной странице куб щебня весит 1,4 тонны, на другой
1,35, на третьей «около полутора». Поодиночке каждая цифра выглядит
правдой, вместе они разрушают доверие быстрее любой ошибки вёрстки,
потому что читатель сверяет две страницы и видит, что мы сами не знаем.

Здесь собираются числовые утверждения по шаблонам и группируются
по смыслу. Скрипт НЕ решает, какое значение верное: он показывает
разброс, а решение принимает человек.
"""
import re, io, os, glob, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NUM = r"(\d+[,.]?\d*)"

# (имя факта, регэксп с одной группой числа, допустимый разброс в процентах)
FACTS = [
    ("вес куба гранитного щебня, т",
     r"куб[а-я]*\s+гранитн\w+\s+щебн\w+[^.]{0,40}?весит\s+около\s+" + NUM, 5),
    ("коэффициент уплотнения щебня",
     r"коэффициент[а-я]*\s+уплотнени\w+[^.]{0,60}?щебн\w+[^.]{0,20}?" + NUM, 0),
    ("минимальный заказ, м3",
     r"минимальн\w+\s+заказ[^.]{0,40}?" + NUM + r"\s*куб", 0),
    ("тариф доставки, руб/км",
     NUM + r"\s*(?:рублей|руб)\s*(?:за\s*)?километр", 0),
    ("плечо по городу, км",
     r"Екатеринбург[^.]{0,30}?,\s*" + NUM + r"\s*км", 0),
    ("вместимость большого самосвала, м3",
     r"самосвал\w*\s+(?:до\s+)?" + NUM + r"\s*(?:кубов|м³|кубометров)", 0),
]

pages = {}
for p in glob.glob(os.path.join(ROOT, "dostavka", "**", "index.html"), recursive=True):
    h = io.open(p, encoding="utf-8").read()
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S)
    url = "/" + os.path.relpath(os.path.dirname(p), ROOT).replace(os.sep, "/") + "/"
    pages[url] = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))

print("РАЗБРОС ЧИСЛОВЫХ УТВЕРЖДЕНИЙ\n")
for name, rx, tol in FACTS:
    vals = collections.defaultdict(list)
    for u, t in pages.items():
        for m in re.finditer(rx, t, re.I):
            vals[m.group(1).replace(",", ".")].append(u)
    if len(vals) <= 1:
        print(f"  ok   {name}: {list(vals) or 'не найдено'}")
        continue
    nums = sorted(float(v) for v in vals)
    spread = (nums[-1] - nums[0]) / nums[0] * 100 if nums[0] else 999
    flag = "ОК " if spread <= tol else "!!!"
    print(f"  {flag}  {name}: разброс {spread:.0f}%")
    for v, us in sorted(vals.items(), key=lambda x: float(x[0])):
        print(f"          {v}  на {len(us)} стр., напр. {us[0]}")
