# -*- coding: utf-8 -*-
"""Сколько ещё страниц выдерживает выгрузка. Строгий счёт.

ЧТО ЭТОТ СКРИПТ НЕ УМЕЕТ, и это надо читать вместе с его выводом:
- группировка жадная, и крупные группы бывают склеены из нескольких тем.
  Верхняя группа по плитке склеила все размеры в одну строку: это
  не одна страница, а одна-три.
- многозначность ловится списком, и список неполон по определению.
  «ФГИС ПГС» и «ПГС вход» вычищены руками после того, как всплыли
  в выводе. Следующая партия принесёт свои.
Поэтому итоговое число тем это верхняя оценка, а не наряд на работу.

Два предыдущих подхода дали неверный ответ, и оба раза по своей причине.

_residual.py занижал остаток: он засчитывал фразу покрытой, если у её
ТЕМЫ есть страница. «Опоры СВ» относятся к ЖБИ, страница ЖБИ есть,
значит покрыто. Ответ получился «ноль», и это было неправдой.

_gaps.py завышал: он считал непокрытой любую фразу, чьи слова не стоят
в заголовках. «Дресва купить в Екатеринбурге» попадала в пробел при
существующей странице /dresva-i-shlak/ только потому, что слов «купить»
и «Екатеринбург» нет в заголовке.

Здесь снимаются обе ошибки. Из фразы вырезаются коммерческие модификаторы
(купить, цена, недорого, доставка) и география: они не меняют тему,
их закрывает та же страница. Остаётся тематическое ядро, и оно
сопоставляется с заголовками. Ядра, которые никто не таргетирует,
группируются по различающему слову, и считаются группы выше порога 150.
"""
import csv, io, re, os, glob, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Модификаторы, которые не меняют тему страницы
MOD = re.compile(
    r'\b(куп\w*|цена|цены|ценам|стоимость|стоит|заказ\w*|доставк\w*|прайс|продаж\w*|'
    r'недорого|дёшево|дешево|дешевл\w*|выгодн\w*|оптом|розниц\w*|акци\w*|скидк\w*|'
    r'екатеринбург\w*|свердловск\w*|области|обл|россии|рф|фото|видео|отзыв\w*|'
    r'сайт|интернет|магазин\w*|каталог|наличи\w*|склад\w*|шт|штук\w*|компани\w*|'
    r'нижн\w*|тагил\w*|первоуральск\w*|каменск\w*|асбест\w*|ревд\w*|полевск\w*|'
    r'берёзовск\w*|березовск\w*|пышм\w*|серов\w*|ирбит\w*|камышлов\w*|арамил\w*)\b',
    re.I)
# Многозначность, которую не поймал фильтр в _cluster.py.
# «ФГИС ПГС» это федеральная информационная система, а не песчано-гравийная
# смесь: 4 742 частотности принадлежат чужой теме целиком. Проверяется
# глазами по списку тем, автоматически такое не ловится.
POLY = re.compile(r'\bфгис\b|вход в систему|личный кабинет|логин|регистрац\w*|'
                  r'госуслуг|портал|пгс вход|пгс сервис|специальност|вуз\b|институт|учебн\w*|'
                  r'диплом|курсов\w*|реферат|егэ|огэ', re.I)
# Бренды и производители: таргетировать их чужие названия смысла нет
BRAND = re.compile(r'поревит|храбр\w*|белая река|терракот|пенетрон|акватрон|'
                   r'кнауф|церезит|основит|бергауф|плитонит', re.I)

STOP = set('и в на на с со по для от до за из у о а не или что как это'
           ' там где так же бы то ли под над при без через мм см м кг т'.split())

def core(s):
    s = MOD.sub(' ', s.lower())
    w = re.findall(r'[а-яёa-z0-9]+', s)
    return {x[:6] for x in w if x not in STOP and len(x) > 2}

def terms(s):
    w = re.findall(r'[а-яёa-z0-9]+', s.lower())
    return {x[:6] for x in w if x not in STOP and len(x) > 2}

pages = {}
for path in glob.glob(os.path.join(ROOT, 'dostavka', '**', 'index.html'), recursive=True):
    h = io.open(path, encoding='utf-8').read()
    url = '/' + os.path.relpath(os.path.dirname(path), ROOT).replace(os.sep, '/') + '/'
    bits = re.findall(r'<title>(.*?)</title>', h, re.S)
    bits += re.findall(r'<h1[^>]*>(.*?)</h1>', h, re.S)
    bits += re.findall(r'<h2[^>]*>(.*?)</h2>', h, re.S)
    bits += re.findall(r'<h3[^>]*>(.*?)</h3>', h, re.S)
    bits += re.findall(r'<summary>(.*?)</summary>', h, re.S)
    bits += re.findall(r'<caption>(.*?)</caption>', h, re.S)
    pages[url] = terms(' '.join(re.sub(r'<[^>]+>', ' ', b) for b in bits))

ROWS = list(csv.reader(io.open(os.path.join(ROOT, 'audit/out/clusters.csv'),
                              encoding='utf-8-sig'), delimiter=';'))[1:]
INFO = {'расчёт', 'выбор', 'как сделать', 'характеристики', 'применение'}

untargeted = []
brand_freq = 0
poly_freq = 0
for cl, ints, ph, fr, var in ROWS:
    f = int(fr)
    if BRAND.search(ph):
        brand_freq += f
        continue
    if POLY.search(ph) or POLY.search(var):
        poly_freq += f
        continue
    c = core(ph)
    if not c:
        continue
    best = max((len(c & pt) / len(c) for pt in pages.values()), default=0.0)
    if best >= 0.75:
        continue
    i = set(ints.split('|')) if ints else set()
    kind = 'инфо' if (i & INFO) and 'коммерческий' not in i else 'комм'
    untargeted.append((f, cl, ph, kind, frozenset(c)))

# Группируем ядра по пересечению: ядро попадает в группу, если делит
# с её ключом не меньше половины слов.
groups = []
for f, cl, ph, kind, c in sorted(untargeted, reverse=True):
    placed = False
    for g in groups:
        if len(c & g['key']) / max(len(c), 1) >= 0.5:
            g['freq'] += f; g['n'] += 1; g['ex'].append(ph); placed = True
            break
    if not placed:
        groups.append(dict(key=c, freq=f, n=1, cl=cl, kind=kind, ex=[ph]))

groups.sort(key=lambda g: -g['freq'])
TH = 150
big = [g for g in groups if g['freq'] >= TH]

print(f'фраз без таргетинга: {len(untargeted)}, их частотность {sum(x[0] for x in untargeted)}')
print(f'отброшено как чужие бренды: {brand_freq}')
print(f'отброшено как многозначность: {poly_freq}')
print(f'тематических групп всего: {len(groups)}, из них выше порога {TH}: {len(big)}')
print(f'частотность групп выше порога: {sum(g["freq"] for g in big)}\n')

byc = collections.Counter()
byk = collections.Counter()
for g in big:
    byc[g['cl']] += 1
    byk[g['kind']] += 1
print(f'{"кластер":24}{"страниц":>9}')
for cl, n in byc.most_common():
    print(f'{cl:24}{n:9}')
print(f'\nиз них информационных: {byk["инфо"]}, коммерческих: {byk["комм"]}')

print(f'\nВСЕ {len(big)} ТЕМ:')
for g in big:
    print(f'  {g["freq"]:6}  [{g["kind"]}] [{g["cl"]}]  {g["ex"][0][:58]}')
