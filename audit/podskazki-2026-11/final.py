import json, os, collections
ROOT = "/home/user/ursdom-site"
E = json.load(open("ws2/exact.json")); keys, on = E["keys"], E["on"]
A = json.load(open("ws2/asg.json")); asg = {q: tuple(v) for q, v in A["asg"].items()}
S = "/dostavka/stati/"
M = {
 "удельный вес": S+"nasypnaya-plotnost/", "насыпная плотность цемента м500": S+"nasypnaya-plotnost/",
 "септик для дома": S+"septik-iz-kolec/", "дорожки на даче": S+"dorozhki-na-uchastke/", "чем отсыпать дорожки на даче": S+"dorozhki-na-uchastke/",
 "классы бетона": S+"marki-betona/", "тощий бетон что это такое": S+"marki-betona/",
 "цемент для фундамента": S+"cement-m400-i-m500/", "цемент м500 для чего используют": S+"cement-m400-i-m500/",
 "какие марки цемента существуют": S+"cement-m400-i-m500/", "цемент м400 как разводить пропорции": S+"cement-m400-i-m500/",
 "размеры бордюров": S+"razmery-bordyurov/", "бордюр тротуарный размеры": S+"razmery-bordyurov/", "бордюр дорожный размеры": S+"razmery-bordyurov/",
 "размеры бордюров для тротуарной плитки": S+"razmery-bordyurov/", "размеры садового бордюра": S+"razmery-bordyurov/",
 "как установить бордюр для дорожек": S+"ustanovka-bordyura/", "садовый бордюр своими руками": S+"sadovyy-bordyur/",
 "размеры колец для колодца": S+"kolca-zhbi-razmery/", "размеры колец жби": S+"kolca-zhbi-razmery/",
 "размеры колец жби для канализации": S+"kolca-zhbi-razmery/", "кольца кс размеры": S+"kolca-zhbi-razmery/",
 "щебень вес 1 м3": S+"skolko-vesit-kub/", "керамзит вес 1 м3": S+"skolko-vesit-kub/", "пгс вес 1 м3": S+"skolko-vesit-kub/",
 "погреб для хранения овощей": S+"zasypka-podpola/", "подпол в частном доме": S+"zasypka-podpola/", "кессон для погреба": S+"zasypka-podpola/",
 "обратная засыпка траншеи": S+"obratnaya-zasypka/", "обратная засыпка с послойным уплотнением": S+"obratnaya-zasypka/",
 "обратная засыпка котлована исполнительная схема": S+"obratnaya-zasypka/",
 "болотистый участок": S+"chem-otsypat-uchastok/", "как поднять участок в низине": S+"chem-otsypat-uchastok/",
 "подъем участка как правильно сделать": S+"chem-otsypat-uchastok/", "вода на участке что делать": S+"drenazh-uchastka/",
 "лоток бетонный с чугунной решеткой": S+"lotki-i-dozhdepriemniki/", "лоток бетонный под кабель": S+"lotki-i-dozhdepriemniki/",
 "песок какой бывает": S+"kakoy-pesok-vybrat/",
 "бетонные трубы для канавы": "/dostavka/truby-zhbi-beznapornye/", "труба водопропускная железобетонная": "/dostavka/truby-zhbi-beznapornye/",
 "брусчатка размеры тротуарная": S+"behaton/", "укладка брусчатки своими руками пошаговая": S+"ukladka-trotuarnoy-plitki/",
 "брусчатка для парковки": S+"parkovka-iz-shchebnya/", "брусчатка под машину": S+"parkovka-iz-shchebnya/",
 "щебень гост технические условия": S+"gost-na-shcheben-i-pesok/", "гост щебень для автомобильных дорог": S+"gost-na-shcheben-i-pesok/",
 "вторичный щебень гост": S+"gost-na-shcheben-i-pesok/",
 "гравий как выглядит": S+"shcheben-ili-graviy/", "гравий это простыми словами": S+"shcheben-ili-graviy/", "гравий это какая горная порода": S+"shcheben-ili-graviy/",
 "ливневка для крыши": "/livnevka/livnevaya-kanalizaciya/", "ливневка для частного дома": "/livnevka/livnevaya-kanalizaciya/",
 "основание под искусственный газон": S+"pesok-pod-gazon/",
 "глина для обжига в печи": S+"pechnoy-rastvor/", "шамотная глина как использовать": S+"kladochnaya-smes-dlya-pechey/",
 "вазоны бетонные для цветов уличные": "/dostavka/malye-formy/", "бетонные вазоны для улицы": "/dostavka/malye-formy/", "полусфера бетонная вес": "/dostavka/malye-formy/",
 "керамзит это что такое": S+"keramzit-frakcii-i-ves/", "керамзит это дренаж": S+"keramzit-frakcii-i-ves/",
 "керамзит гост 32496-2013 технические характеристики": S+"keramzit-frakcii-i-ves/", "керамзит это камень или нет": S+"keramzit-frakcii-i-ves/",
 "вентблоки размеры": "/dostavka/ventilyacionnye-bloki/", "вентблоки для многоэтажных домов размеры": "/dostavka/ventilyacionnye-bloki/",
 "коэффициент уплотнения скального грунта": S+"koefficient-uplotneniya/", "кладочная смесь для кирпича пропорции": S+"kladochnaya-smes/",
 "дорога на участке своими руками": S+"doroga-k-uchastku/", "чем отсыпать подъезд к дому": S+"doroga-k-uchastku/",
 "асфальтовая крошка укладка своими руками": "/dostavka/asfaltovaya-kroshka/",
 "гранитный щебень в ландшафтном дизайне": S+"dekorativnyy-shcheben/", "упрочнение бетона глубокого проникновения": S+"propitki-dlya-betona/",
}
NEWMAP = {
 "армирование ленточного фундамента": "армирование", "армирование плитного фундамента": "армирование",
 "бетонные столбы для забора": "забор", "сколько бетон набирает прочность": "сохнет", "заливка бетона под уклоном": "сохнет",
 "утепленная шведская плита": "плитный", "газобетон для перегородок": "газобетон", "перемычки для газобетона": "перемычки",
 "блоки бетонные под фундамент": "фбс", "черновой пол по деревянным лагам": "пол по грунту", "площадка под мангальную зону": "основание под",
 "керамзитобетон размеры блоков": "керамзитоблок", "керамзитобетон или газобетон": "керамзитоблок", "керамзитобетон вес 1 м3 таблица": "керамзитоблок",
 "как закрыть колодец из колец": "колодец из", "жби изделия для колодцев": "колодец из",
}
SKIP = {"сколько весит поддон кирпича": "кирпич не продаём", "вибратор для бетона глубинный электрический": "инструмент, не наша тема"}
titles = {v[2]: (v[0], v[1]) for v in asg.values()}
for q, key in NEWMAP.items():
    t = [tt for tt in titles if key.lower() in tt.lower()]
    assert t, (q, key)
    typ, url = titles[t[0]]
    asg[q] = (typ, url, t[0])
for q, u in M.items():
    assert os.path.exists(ROOT + u + "index.html"), u
    asg[q] = ("дописать", u, None)
miss = [q for q in keys if not on[q]]
left = [q for q in miss if q not in asg and q not in SKIP]
assert not left, left
# тип по факту: существует ли страница
pages = collections.defaultdict(lambda: {"add": [], "title": None})
for q in miss:
    if q in SKIP: continue
    typ, url, title = asg[q]
    exists = os.path.exists(ROOT + url + "index.html")
    url = url.replace("//", "/")
    if url == "/dostavka/beton/":
        # марки: раскладываем по товарным страницам
        import re
        m = re.search(r"м ?(100|150|200|250|300|350|400)|в ?(7\.5|12\.5|15|20|22\.5|25)", q)
        mark = {"в7.5": "m100", "в12.5": "m150", "в15": "m200", "в20": "m250", "в22.5": "m300", "в25": "m350"}
        if m and m.group(1): url = "/dostavka/beton/m%s/" % m.group(1)
        elif m: url = "/dostavka/beton/%s/" % mark.get("в" + m.group(2), "m250")
        exists = os.path.exists(ROOT + url + "index.html")
    p = pages[url]; p["add"].append(q); p["exists"] = exists; p["title"] = p["title"] or title
new = {u: p for u, p in pages.items() if not p["exists"]}
old = {u: p for u, p in pages.items() if p["exists"]}
print("ключей к добавлению:", sum(len(p["add"]) for p in pages.values()), "пропущено:", len(SKIP))
print("НОВЫХ статей:", len(new), "ключей в них:", sum(len(p["add"]) for p in new.values()))
print("СУЩЕСТВУЮЩИХ страниц дописать:", len(old), "ключей в них:", sum(len(p["add"]) for p in old.values()))
json.dump({"pages": pages, "keys": keys, "on": on, "skip": SKIP}, open("ws2/final.json", "w"), ensure_ascii=False)
for u, p in sorted(new.items(), key=lambda kv: -sum(keys[q] for q in kv[1]["add"])):
    print("N %3d %7d %s %s" % (len(p["add"]), sum(keys[q] for q in p["add"]), u, p["title"]))
for u, p in sorted(old.items(), key=lambda kv: -sum(keys[q] for q in kv[1]["add"])):
    print("D %3d %7d %s" % (len(p["add"]), sum(keys[q] for q in p["add"]), u))
