import sys, glob, io, os, csv, json
sys.path.insert(0, "/home/user/ursdom-site/audit"); sys.path.insert(0, "/home/user/ursdom-site/dostavka-src/data")
import _wordstat as W
from kupit_cover import load
ROOT = "/home/user/ursdom-site"
segs = {}
for p in glob.glob(ROOT + "/dostavka/**/index.html", recursive=True):
    segs[p] = W.segments(io.open(p, encoding="utf-8").read())
def strict(qt):
    n = len(qt)
    for s in segs.values():
        for t in s:
            for i in range(len(t) - n + 1):
                if t[i:i + n] == qt: return True
    return False
gen = [(q, f) for q, f in W.load_queries() if q not in W.SKIP]
kup = [(q, n) for m, q, n, why in load() if not why]
for name, L in (("общие 2026-09", gen), ("купить и синонимы", kup)):
    miss = [(f, q) for q, f in L if not strict(W.query_tokens(q))]
    miss.sort(reverse=True)
    print(name, "всего", len(L), "точно есть", len(L) - len(miss), "только с вставкой слов", len(miss))
    print("   ", "; ".join("%s %d" % (q, f) for f, q in miss[:25]))
    json.dump(miss, open("ws2/old_miss_%s.json" % ("gen" if name.startswith("общ") else "kup"), "w"), ensure_ascii=False)
