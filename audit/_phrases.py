# -*- coding: utf-8 -*-
"""Какие фразы выгрузки достались конкретной странице.

Нужен, чтобы дописывать вопросы в FAQ формулировками людей, а не
своими. Матчинг тот же, что в _deepen.py.
"""
import csv, io, re, os, glob, sys, collections
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
    w = w.replace('ё', 'е'); s = END.sub('', w)
    return s if len(s) >= 4 else w
def words(s):
    return [norm(x) for x in re.findall(r'[а-яёa-z0-9]+', s.lower())
            if x not in STOP and len(x) > 2]
pages = {}
for path in glob.glob(os.path.join(ROOT, 'dostavka', '**', 'index.html'), recursive=True):
    h = io.open(path, encoding='utf-8').read()
    url = '/' + os.path.relpath(os.path.dirname(path), ROOT).replace(os.sep, '/') + '/'
    h = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', h, flags=re.S)
    heads = ' '.join(re.sub(r'<[^>]+>', ' ', x) for x in
                     re.findall(r'<title>(.*?)</title>|<h[1-3][^>]*>(.*?)</h[1-3]>|'
                                r'<summary>(.*?)</summary>|<caption>(.*?)</caption>', h, re.S)
                     for x in x if x)
    pages[url] = set(words(heads))
ROWS = list(csv.reader(io.open(os.path.join(ROOT, 'audit/out/clusters.csv'),
                               encoding='utf-8-sig'), delimiter=';'))[1:]
want = sys.argv[1:]
got = collections.defaultdict(list)
for cl, ints, ph, fr, var in ROWS:
    core = set(words(MOD.sub(' ', ph)))
    if not core: continue
    best_u, best_s = None, 0.0
    for u, pt in pages.items():
        s = len(core & pt) / len(core)
        if s > best_s: best_u, best_s = u, s
    if best_u and best_s >= 0.5:
        got[best_u].append((int(fr), ph))
for w in want:
    u = '/dostavka/' + w.strip('/') + '/'
    print(f'=== {u}')
    for f, p in sorted(got.get(u, []), reverse=True)[:22]:
        print(f'  {f:6}  {p}')
    print()
