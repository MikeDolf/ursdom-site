import csv, re, json, collections
src = open("sug/plan_xlsx.py", encoding="utf-8").read()
ns = {}
exec(src.split("used = collections.Counter()")[0].split("HERE = ")[0] + "\nPLAN = " + src.split("PLAN = ", 1)[1].split("\nused = ")[0], ns)
PLAN = ns["PLAN"]
F = {}
for path in ("ws1/results1.csv", "ws2/results2.csv"):
    rows = list(csv.reader(open(path, encoding="utf-8-sig"), delimiter=";"))[1:]
    for r in rows:
        F[r[1].strip()] = int(r[2])
print("фраз с частотой", len(F))
topics = []
assigned = set()
for sec, title, typ, slug, rx, ex, note in PLAN:
    rr, xx = re.compile(rx), re.compile(ex) if ex else None
    m = sorted([(f, q) for q, f in F.items() if rr.search(q) and not (xx and xx.search(q))], reverse=True)
    for f, q in m: assigned.add(q)
    head = m[0][0] if m else 0
    tail = sum(f for f, q in m[1:])
    topics.append(dict(sec=sec, title=title, typ=typ, url="/dostavka/" + slug + "/", head=head,
                       top=m[:8], n=len(m), note=note))
topics.sort(key=lambda t: -t["head"])
json.dump(topics, open("ws2/topics.json", "w"), ensure_ascii=False)
for t in topics:
    print("%7d %-8s %-9s %s | %s" % (t["head"], t["sec"], t["typ"], t["title"][:60], "; ".join("%s %d" % (q, f) for f, q in t["top"][:4])))
un = sorted([(f, q) for q, f in F.items() if q not in assigned], reverse=True)
print("\nне попали в темы:", len(un))
print("; ".join("%s %d" % (q, f) for f, q in un[:70]))
