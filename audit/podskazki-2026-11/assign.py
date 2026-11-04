import json, re, os
src = open("sug/plan_xlsx.py", encoding="utf-8").read()
ns = {}
exec(src.split("HERE = ")[0] + "\nPLAN = " + src.split("PLAN = ", 1)[1].split("\nused = ")[0], ns)
PLAN = ns["PLAN"]
E = json.load(open("ws2/exact.json")); keys, on = E["keys"], E["on"]
miss = [q for q in keys if not on[q]]
asg = {}
for sec, title, typ, slug, rx, ex, note in PLAN:
    rr, xx = re.compile(rx), re.compile(ex) if ex else None
    for q in miss:
        if q in asg: continue
        if rr.search(q) and not (xx and xx.search(q)):
            asg[q] = (typ, "/dostavka/" + slug + "/", title)
un = sorted([q for q in miss if q not in asg], key=lambda q: -keys[q])
json.dump({"asg": asg, "un": un}, open("ws2/asg.json", "w"), ensure_ascii=False)
print("распределено по плану", len(asg), "без темы", len(un))
for q in un: print("%6d %s" % (keys[q], q))
