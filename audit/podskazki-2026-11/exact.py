import csv, glob, io, os, re, sys, json
sys.path.insert(0, "/home/user/ursdom-site/audit")
import _wordstat as W
ROOT = "/home/user/ursdom-site"
F = {}
for p in ("ws1/results1.csv", "ws2/results2.csv"):
    for r in list(csv.reader(open(p, encoding="utf-8-sig"), delimiter=";"))[1:]:
        F[r[1].strip()] = int(r[2])
keys = {q: f for q, f in F.items() if f > 0}
print("ключей с частотой", len(F), "из них ненулевых", len(keys))

def strict(qt, segs):
    n = len(qt)
    for t in segs:
        for i in range(len(t) - n + 1):
            if t[i:i + n] == qt:
                return True
    return False

pages = {}
for g in ("dostavka/**/index.html", "drenazh/**/index.html", "skvazhina/**/index.html", "livnevka/**/index.html", "index.html"):
    for p in glob.glob(os.path.join(ROOT, g), recursive=True):
        u = "/" + os.path.relpath(os.path.dirname(p), ROOT).replace("\\", "/") + "/"
        u = u.replace("/./", "/")
        pages[u] = W.segments(io.open(p, encoding="utf-8").read())
res = {}
for q in keys:
    qt = W.query_tokens(q)
    res[q] = [u for u, s in pages.items() if strict(qt, s)]
on = sum(1 for q in res if res[q])
print("уже стоят точным вхождением:", on, "нет на сайте:", len(keys) - on)
json.dump({"keys": keys, "on": res}, open("ws2/exact.json", "w"), ensure_ascii=False)
