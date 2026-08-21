# -*- coding: utf-8 -*-
"""Варианты снимка под <picture>: 1600 JPEG, 1200 JPEG, 800 и 1600 WebP.

Раньше варианты делались вручную по одному, и это уже стоило ошибки:
у granit-40-70-hand не хватает 1600.webp и 1200.jpg, потому что шаг
пропустили. photos_for подставляет вариант, только если файл лежит
рядом, поэтому пропуск не ломает страницу, а молча отдаёт телефону
полуторатысячный JPEG.

Запуск: python3 mkvariants.py <исходник> <куда/имя-без-расширения>
"""
import sys, os
from PIL import Image

SRC, DST = sys.argv[1], sys.argv[2]
os.makedirs(os.path.dirname(DST), exist_ok=True)


def fit(im, side):
    """Вписать в квадрат стороной side, не растягивая мелкое."""
    w, h = im.size
    if max(w, h) <= side:
        return im.copy()
    k = side / float(max(w, h))
    return im.resize((round(w * k), round(h * k)), Image.LANCZOS)


with Image.open(SRC) as im:
    im = im.convert("RGB")
    fit(im, 1600).save(DST + ".jpg", "JPEG", quality=82, optimize=True,
                       progressive=True)
    fit(im, 1200).save(DST + "-1200.jpg", "JPEG", quality=82, optimize=True,
                       progressive=True)
    # 320 - для миниатюр: стопка сит на хабе показывает снимок
    # шириной 104 пикселя, и 800-й вариант там весит вдесятеро больше
    # нужного, да ещё в первом экране.
    fit(im, 320).save(DST + "-320.webp", "WEBP", quality=80, method=6)
    fit(im, 800).save(DST + "-800.webp", "WEBP", quality=78, method=6)
    fit(im, 1600).save(DST + "-1600.webp", "WEBP", quality=78, method=6)

for suf in (".jpg", "-1200.jpg", "-320.webp", "-800.webp", "-1600.webp"):
    p = DST + suf
    with Image.open(p) as v:
        print("%-22s %-11s %5d КБ" % (os.path.basename(p), "%dx%d" % v.size,
                                      os.path.getsize(p) // 1024))
