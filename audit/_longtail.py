# -*- coding: utf-8 -*-
"""Покрытие длинных хвостов выгрузки текстом сайта.

Длинный хвост здесь это фраза из трёх и более значимых слов. Такие
запросы редко имеют собственную страницу и почти всегда закрываются
абзацем внутри существующей: если на странице встречаются ВСЕ корни
фразы, человек, пришедший по ней, ответ найдёт.

ОСТОРОЖНО СО СТЕММАМИ, та же ловушка, что в _residual.py. Стемм должен
быть корнем, общим для всех словоформ: «щеб», а не «щебень». Иначе
скрипт отчитается о пробеле, которого нет. Проверка простая: если после
правки стеммов непокрытых заметно меньше, прежняя цифра была ошибкой
измерения.

В отличие от _residual.py тут матчинг идёт по ПОЛНОМУ тексту страницы,
а не по заголовкам: хвост закрывается абзацем, и требовать от него
собственного заголовка значит завысить пробел в разы.
"""
import csv, io, re, os, glob, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_WORDS = 3

STOP = set('и в во на с со по для от до за из у о об а не или что это как там где так же бы то ли '
           'под над при без через если его её их вы мы он она они был была быть есть было '
           'нужно надо можно только уже ещё еще все всё вот том тем чем чём который которая '
           'мне вам нам ими них его чего кто когда чтобы'.split())

# Окончания режутся жадно: цель получить общий корень словоформ.
END = re.compile(r'(ами|ями|иями|ого|его|ему|ыми|ими|ах|ях|ов|ев|ём|ем|ой|ей|ий|ый|ая|яя|ое|ые|ие'
                 r'|ую|юю|ью|ю|я|а|у|е|о|ы|и|ь|й)$')


def stem(w):
    w = w.replace('ё', 'е')
    for _ in range(2):
        s = END.sub('', w)
        if len(s) < 4:
            break
        w = s
    return w


def toks(s):
    return [stem(x) for x in re.findall(r'[а-яa-z0-9]+', s.replace('ё', 'е').lower())
            if x not in STOP and len(x) > 2]


def page_text(path):
    h = io.open(path, encoding='utf-8').read()
    h = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', h, flags=re.S)
    h = re.sub(r'<[^>]+>', ' ', h)
    return h


def load_pages():
    pages = {}
    for path in glob.glob(os.path.join(ROOT, 'dostavka', '**', 'index.html'), recursive=True):
        url = '/' + os.path.relpath(os.path.dirname(path), ROOT).replace(os.sep, '/') + '/'
        pages[url] = set(toks(page_text(path)))
    return pages


def load_queries():
    """Фразы из всех выгрузок. Одна фраза может встретиться в нескольких
    файлах с разной частотностью: берём максимум, а не сумму, иначе
    пересечение файлов раздувает вес."""
    freq = {}
    for path in sorted(glob.glob(os.path.join(ROOT, 'audit/in/*.csv'))):
        rd = csv.reader(io.open(path, encoding='utf-8-sig'), delimiter=';')
        next(rd, None)
        for row in rd:
            if len(row) < 2:
                continue
            ph = row[0].strip().lower().replace('ё', 'е')
            try:
                fr = int(re.sub(r'\D', '', row[1]) or 0)
            except ValueError:
                continue
            if ph:
                freq[ph] = max(freq.get(ph, 0), fr)
    return freq


def main():
    pages = load_pages()
    freq = load_queries()
    tails = {p: f for p, f in freq.items() if len(toks(p)) >= MIN_WORDS}

    covered, partial, missing = [], [], []
    for ph, fr in tails.items():
        need = set(toks(ph))
        best_u, best_hit = None, -1
        for url, bag in pages.items():
            hit = len(need & bag)
            if hit > best_hit:
                best_u, best_hit = url, hit
        share = best_hit / float(len(need))
        rec = (fr, ph, best_u, best_hit, len(need))
        if share == 1.0:
            covered.append(rec)
        elif share >= 0.6:
            partial.append(rec)
        else:
            missing.append(rec)

    tot = len(tails)
    fsum = sum(tails.values()) or 1
    print('всего длинных хвостов (>=%d значимых слов): %d, суммарная частотность %d'
          % (MIN_WORDS, tot, fsum))
    for name, lst in (('покрыты полностью', covered),
                      ('покрыты частично', partial),
                      ('не покрыты', missing)):
        f = sum(r[0] for r in lst)
        print('  %-20s %5d фраз (%4.1f%%), частотность %6d (%4.1f%%)'
              % (name, len(lst), 100.0 * len(lst) / tot, f, 100.0 * f / fsum))

    lim = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    for name, lst in (('НЕ ПОКРЫТЫ', missing), ('ЧАСТИЧНО', partial)):
        print('\n=== %s, топ %d по частотности ===' % (name, lim))
        for fr, ph, url, hit, need in sorted(lst, reverse=True)[:lim]:
            print('%6d  %-58s %d/%d  %s' % (fr, ph[:58], hit, need, url))

    # Куда пришлись бы непокрытые: по лучшей странице видно, какую
    # именно статью надо дописать, а не какую новую заводить.
    agg = collections.Counter()
    for fr, ph, url, hit, need in missing + partial:
        agg[url] += fr
    print('\n=== страницы, которым не хватает текста (частотность рядом) ===')
    for url, f in agg.most_common(25):
        print('%6d  %s' % (f, url))


if __name__ == '__main__':
    main()
