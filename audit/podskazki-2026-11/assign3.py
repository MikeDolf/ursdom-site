# -*- coding: utf-8 -*-
"""Раскладка третьей партии Вордстата по страницам сайта.

Правила идут сверху вниз, первое совпавшее решает. Новые статьи
помечены префиксом NEW:. Ноль в Вордстате отбрасывается.
Выход: ключи третьей партии дописываются в klyuchi-po-stranicam.json
(pages[url]["add"], keys[q]) и печатается сводка.
"""
import csv, io, json, os, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))

R = [
 (r"плиточн\w* кле", "NEW:stati/plitochnyy-kley"),
 (r"^шлак это", "NEW:stati/shlak"),
 (r"погреб|кессон", "NEW:stati/pogreb"),
 (r"штукатурк", "stati/cementnaya-shtukaturka"),
 (r"крыльц", "stati/osnovanie-pod-krylco"),
 (r"бассейн", "stati/osnovanie-pod-basseyn"),
 (r"детская площадка", "stati/detskaya-ploshchadka"),
 (r"брусчатка своими руками укладка|укладка брусчатки|укладка тротуарной|основание под тротуарную|"
  r"основание под брусчатку|выровнять основание|брусчатка гост", "stati/ukladka-trotuarnoy-plitki"),
 (r"брусчатка своими руками", "stati/plitka-svoimi-rukami"),
 (r"брусчатка для отмостки", "stati/otmostka-vokrug-doma"),
 (r"тротуарн\w* плитк\w* .*размер|тротуарная плитка размеры|брусчатка размеры", "trotuarnaya-plitka-razmery"),
 (r"брусчатка для парковки|площадка для машины|парковка на", "stati/parkovka-iz-shchebnya"),
 (r"отсев лучше для тротуарн", "stati/otsev-gde-primenyat"),
 (r"бордюр пластиков", "stati/plastikovyy-sadovyy-bordyur"),
 (r"бордюр для дорожек|садовый бордюр|поребрик садовый", "stati/sadovyy-bordyur"),
 (r"поребрик это|поребрик чем|бордюр или поребрик", "stati/porebrik-i-bordyur"),
 (r"бордюр|поребрик", "stati/razmery-bordyurov"),
 (r"кольц\w* .*септик|септик", "stati/septik-iz-kolec"),
 (r"выгребн", "stati/vygrebnaya-yama"),
 (r"колодец размеры", "stati/kolodec-iz-kolec-obustroystvo"),
 (r"кольц|колец|кс 1|кс 2", "stati/kolca-zhbi-razmery"),
 (r"плита дорожная с отверстием", "stati/dorozhnye-plity-razmery"),
 (r"крышк|плита днища|пп 10", "stati/kryshki-i-dnishcha-kolodcev"),
 (r"люк", "stati/lyuki-kolodcev"),
 (r"теплотрасс", "lotki-teplotrass"),
 (r"\bлот|дождеприемник", "stati/lotki-i-dozhdepriemniki"),
 (r"ливневк", "LIVNEVKA"),
 (r"труба для канавы", "truby-zhbi-beznapornye"),
 (r"фбс|фундаментн\w* блок|блоки бетонные размеры", "stati/bloki-fbs-razmery"),
 (r"под забор с откатными", "stati/osnovanie-pod-vorota-i-besedku"),
 (r"фундамент\w* .*забор|забор.*фундамент", "stati/stolbchatyy-fundament"),
 (r"забор|столбы для забора", "stati/betonnyy-zabor-razmery"),
 (r"плит\w* перекрыт|плиты пустотн|плита пк|пк или пб", "stati/plity-perekrytiya-razmery"),
 (r"дорожн\w* плит|плита дорожная|аэродромн", "stati/dorozhnye-plity-razmery"),
 (r"перемычк", "stati/peremychki"),
 (r"армопояс", "stati/armopoyas"),
 (r"лестничн", "stati/lestnichnye-marshi"),
 (r"армировани", "stati/armirovanie-fundamenta"),
 (r"ростверк", "stati/rostverk"),
 (r"опалубк", "stati/opalubka"),
 (r"плитный фундамент|монолитная плита|ленточный или плитный", "stati/plitnyy-fundament"),
 (r"фундамент\w* под гараж", "stati/fundament-pod-garazh"),
 (r"фундамент под баню", "stati/fundament-pod-banyu"),
 (r"столбчат|свайн|винтовые сваи", "stati/stolbchatyy-fundament"),
 (r"подушк", "stati/podushka-pod-fundament"),
 (r"ленточн", "stati/lentochnyy-fundament"),
 (r"глубина промерзания", "stati/glubina-promerzaniya"),
 (r"пенетрон|проникающ", "stati/pronikayushchaya-gidroizolyaciya"),
 (r"жидкое стекло", "stati/gidroizolyaciya-betona"),
 (r"утеплени\w* фундамент", "stati/gidroizolyaciya-fundamenta"),
 (r"трещины в бетоне", "stati/remontnye-smesi-dlya-betona"),
 (r"сколько сохнет бетон", "stati/skolko-sohnet-beton"),
 (r"куб бетона .*цемент", "stati/skolko-shchebnya-i-peska-na-kub-betona"),
 (r"куб бетона", "stati/ves-kuba-betona"),
 (r"керамзитобетон своими руками пропорции для стен", "stati/keramzitoblok"),
 (r"керамзитобетон своими руками", "stati/keramzit-v-styazhke"),
 (r"пгс для бетона|отсев и цемент|отсев или песок для бетона", "stati/beton-iz-otseva-i-pgs"),
 (r"бетон м300 пропорции", "beton/m300"),
 (r"бетон м100", "beton/m100"),
 (r"бетон м200|бетон в15", "beton/m200"),
 (r"бетон м250|бетон в20", "beton/m250"),
 (r"бетон м300", "beton/m300"),
 (r"бетон м350", "beton/m350"),
 (r"пропорци|бетон своими руками", "stati/zames-betona-vedrami"),
 (r"марк\w* бетона|классы бетона|тощий бетон|какой бетон лучше", "stati/marki-betona"),
 (r"железобетон|жби изделия", "zhbi-izdeliya"),
 (r"цементно.?песчан|сухая смесь для кладки", "stati/cementno-peschanyy-rastvor"),
 (r"цемент", "stati/cement-m400-i-m500"),
 (r"раствор для кладки цоколя|цоколь", "stati/cokol"),
 (r"раствор для кладки печи|шамотн", "stati/kladochnaya-smes-dlya-pechey"),
 (r"глина для печи", "stati/pechnoy-rastvor"),
 (r"пескобетон", "stati/peskobeton"),
 (r"полистирол", "stati/arbolit-i-polistirolbeton"),
 (r"керамзит под стяжк|керамзит для пола|керамзит нужен для пола|керамзитобетон своими руками", "stati/keramzit-v-styazhke"),
 (r"стяжк", "stati/styazhka-pola"),
 (r"черновой пол|пол по грунту", "stati/pol-po-gruntu"),
 (r"пол .*гараж", "stati/pol-v-garazhe"),
 (r"смотровая яма", "stati/smotrovaya-yama"),
 (r"штукатурк", "stati/cementnaya-shtukaturka"),
 (r"известь", "stati/izvest"),
 (r"керамзитоблок|пескоблок|керамзитобетон", "stati/keramzitoblok"),
 (r"керамзит .*утеплител|керамзит как утеплитель", "stati/uteplenie-keramzitom"),
 (r"керамзит", "stati/keramzit-frakcii-i-ves"),
 (r"щпс", "shchps"),
 (r"пгс", "stati/pgs-ili-opgs"),
 (r"дресва и отсев", "stati/skalnyy-grunt-dresva-but"),
 (r"отсев вес|песок вес|кубов песка в", "stati/skolko-vesit-kub"),
 (r"гост 31424|отсев", "stati/otsev-gde-primenyat"),
 (r"насыпная плотность", "stati/nasypnaya-plotnost"),
 (r"кварцев", "stati/kvarcevyy-pesok"),
 (r"коэффициент уплотнения", "stati/koefficient-uplotneniya"),
 (r"уплотнение грунта", "stati/uplotnenie-grunta"),
 (r"гост 8736|песок .*гост|песок гост", "stati/gost-na-shcheben-i-pesok"),
 (r"песок|песка", "stati/kakoy-pesok-vybrat"),
 (r"обратная засыпка", "stati/obratnaya-zasypka"),
 (r"мягкая отмостка", "stati/myagkaya-otmostka"),
 (r"щебень для отмостки|отмостк", "stati/otmostka-vokrug-doma"),
 (r"щебень для бетона|щебень или гравий для бетона", "stati/kakoy-shcheben-vybrat"),
 (r"щебень (какой фракции бывает|какой бывает)", "stati/frakcii-shchebnya"),
 (r"щебень что это|вторичный щебень|известняков", "stati/vidy-shchebnya"),
 (r"гравий|щебень или", "stati/shcheben-ili-graviy"),
 (r"гранитная крошка для кладбища", "stati/otsypka-mogily"),
 (r"гранитная крошка", "granitnaya-kroshka"),
 (r"мраморн", "stati/mramornaya-kroshka"),
 (r"бутов", "butovyy-kamen"),
 (r"скальный грунт", "stati/skalnyy-grunt-klassifikaciya"),
 (r"холодного асфальта", "stati/holodnyy-asfalt"),
 (r"дренаж", "stati/drenazh-uchastka"),
 (r"отсыпка участка|болотист", "stati/chem-otsypat-uchastok"),
 (r"швы плитки", "stati/shvy-trotuarnoy-plitki"),
 (r"вентблок", "ventilyacionnye-bloki"),
 (r"полусфер", "malye-formy"),
]


def main():
    rows = list(csv.reader(io.open(os.path.join(HERE, "wordstat-partiya3-rezultat.csv"), encoding="utf-8"),
                           delimiter=";"))[1:]
    by = collections.defaultdict(list)
    left = []
    for _, q, f in rows:
        f = int(f)
        if not f:
            continue
        for rx, slug in R:
            if re.search(rx, q):
                by[slug].append((f, q))
                break
        else:
            left.append((f, q))
    P = json.load(io.open(os.path.join(HERE, "klyuchi-po-stranicam.json"), encoding="utf-8"))
    for slug, L in by.items():
        url = "/livnevka/livnevaya-kanalizaciya/" if slug == "LIVNEVKA" else "/dostavka/" + slug.replace("NEW:", "") + "/"
        d = P["pages"].setdefault(url, {"add": []})
        for f, q in L:
            P["keys"][q] = f
            if q not in d["add"]:
                d["add"].append(q)
        d.setdefault("partiya3", [q for f, q in L])
        d["partiya3"] = [q for f, q in L]
    json.dump(P, io.open(os.path.join(HERE, "klyuchi-po-stranicam.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    new = {s: L for s, L in by.items() if s.startswith("NEW:")}
    old = {s: L for s, L in by.items() if not s.startswith("NEW:")}
    print("ключей", sum(len(L) for L in by.values()), "страниц", len(by), "новых статей", len(new),
          "без страницы", len(left), left)
    for s, L in sorted(new.items(), key=lambda kv: -sum(f for f, q in kv[1])):
        print("НОВАЯ %-28s %6d | %s" % (s[4:], sum(f for f, q in L), "; ".join("%s %d" % (q, f) for f, q in sorted(L, reverse=True))))
    for s, L in sorted(old.items(), key=lambda kv: -sum(f for f, q in kv[1])):
        print("%-44s %3d %6d | %s" % (s, len(L), sum(f for f, q in L), "; ".join("%s %d" % (q, f) for f, q in sorted(L, reverse=True)[:5])))


if __name__ == "__main__":
    main()
