# -*- coding: utf-8 -*-
"""Чего не хватает уже написанным страницам.

Для каждой фразы выгрузки находим страницу, которая ближе всего к её
теме, и смотрим, какие СЛОВА этой фразы на странице не встречаются.
Слово, которого нет в тексте, это вопрос, на который страница
не отвечает. Так получается список подтем на усиление, привязанный
к конкретному адресу, а не к кластеру.

Стемминг здесь нормализован окончаниями, а не усечением до шести
символов: [:6] не сводит «бетон» и «бетона», и на этом уже один раз
завысили остаток вдвое. Ещё «ё» приводится к «е»: в выгрузке пишут
«дождеприемник», на сайте «дождеприёмник», и без этого страница
выглядит непокрытой при полном покрытии.
"""
import csv, io, re, os, glob, collections, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
END = re.compile(r'(ами|ями|ого|ему|ыми|ими|ах|ях|ов|ев|ей|ий|ый|ая|ое|ые|ую|ю|я|а|у|е|о|ы|и|ь)$')
STOP = set('и в на с со по для от до за из у о а не или что это как там где так же бы то ли под над '
           'при без через мм см кг шт руб если его её их вы мы он она они был была быть есть '
           'нужно надо можно только уже ещё еще все всё вот том тем чем чём который которая'.split())
MOD = re.compile(r'\b(куп\w*|цена|цены|ценам|стоимость|стоит|заказ\w*|доставк\w*|прайс|продаж\w*|'
                 r'недорого|дёшево|дешево|оптом|акци\w*|скидк\w*|фото|видео|отзыв\w*|сайт|'
                 r'интернет|магазин\w*|каталог|наличи\w*|склад\w*|компани\w*|авито|озон|ozon|'
                 r'екатеринбург\w*|свердловск\w*|области|обл|россии|рф)\b', re.I)

def norm(w):
    w = w.replace('ё', 'е')
    s = END.sub('', w)
    return s if len(s) >= 4 else w

def words(s):
    return [norm(x) for x in re.findall(r'[а-яёa-z0-9]+', s.lower())
            if x not in STOP and len(x) > 2]

pages, ptext = {}, {}
for path in glob.glob(os.path.join(ROOT, 'dostavka', '**', 'index.html'), recursive=True):
    h = io.open(path, encoding='utf-8').read()
    url = '/' + os.path.relpath(os.path.dirname(path), ROOT).replace(os.sep, '/') + '/'
    h = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', h, flags=re.S)
    heads = ' '.join(re.sub(r'<[^>]+>', ' ', x) for x in
                     re.findall(r'<title>(.*?)</title>|<h[1-3][^>]*>(.*?)</h[1-3]>|'
                                r'<summary>(.*?)</summary>|<caption>(.*?)</caption>', h, re.S)
                     for x in x if x)
    pages[url] = set(words(heads))
    ptext[url] = set(words(re.sub(r'<[^>]+>', ' ', h)))

ROWS = list(csv.reader(io.open(os.path.join(ROOT, 'audit/out/clusters.csv'),
                               encoding='utf-8-sig'), delimiter=';'))[1:]

owned = collections.defaultdict(int)
missing = collections.defaultdict(collections.Counter)
for cl, ints, ph, fr, var in ROWS:
    f = int(fr)
    core = set(words(MOD.sub(' ', ph)))
    if not core:
        continue
    best_u, best_s = None, 0.0
    for u, pt in pages.items():
        s = len(core & pt) / len(core)
        if s > best_s:
            best_u, best_s = u, s
    if best_u is None or best_s < 0.5:
        continue
    owned[best_u] += f
    for w in core - ptext[best_u]:
        missing[best_u][w] += f

only = sys.argv[1] if len(sys.argv) > 1 else ''
order = sorted(owned, key=lambda u: -owned[u])
for u in order:
    if only and only not in u:
        continue
    gaps = [(w, n) for w, n in missing[u].most_common(14) if n >= 60]
    if not gaps:
        continue
    print(f'{owned[u]:6}  {u}')
    print('        ' + ', '.join(f'{w} ({n})' for w, n in gaps))
