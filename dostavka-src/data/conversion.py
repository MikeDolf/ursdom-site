# -*- coding: utf-8 -*-
"""Конверсионный слой статей: цена, заказ, снятие возражений.

Задача поставлена владельцем прямо: человек, дочитавший статью, должен
захотеть написать и заказать. Ревизия показала, чего для этого не было.

1. ЦЕНЫ НЕ БЫЛО НИГДЕ. Из 61 статьи цену показывали три
   (cena-kuba-s-dostavkoy, skolko-shchebnya-v-kamaze и хаб бетона):
   у остальных стоял флаг commercial=False, и человек дочитывал
   подробный разбор, не узнав ни одной цифры в рублях. Главный барьер
   «а сколько это стоит» статья не снимала вообще.
2. ПОСЛЕ ПОСЛЕДНЕГО РАЗДЕЛА БЫЛ ОБРЫВ. Текст заканчивался, и читатель
   падал в блок «Как мы возим», написанный не для него. Между концом
   чтения и заявкой не было ни одного шага.
3. ВОЗРАЖЕНИЯ НЕ СНИМАЛИСЬ. Минимальный объём, порядок оплаты, что
   с недовозом, за сколько приедет машина: всё это человек выяснял
   уже в переписке, то есть после того, как решался написать.

Здесь лежат данные под эти три блока. Цены не выдуманы заново,
а взяты из тех же строк, что стоят на товарных страницах: одна
и та же позиция не должна стоить по-разному в статье и в каталоге.

Семейство подбирается по слагу. Список FAM явный, без угадывания по
подстроке: угадывание один раз уже отправило бы «отсев» в песок,
а «цемент М400 и М500» в нерудку. Незнакомый слаг падает в 'nerud'
и попадает в отчёт сборки, чтобы это было видно, а не молча.
"""

# --- Пояснения под таблицами там, где написание на сайте расходится
# с написанием в поиске.
#
# Проверка покрытия длинных хвостов (audit/_longtail.py) показала
# «непокрытые» слова В15, В30, 300х300х30, 400х400х50. Это оказался
# не пробел в содержании, а разные символы: класс бетона по ГОСТ 26633
# пишется латинской B, а набирают его кириллической В; размеры плитки
# на сайте набраны знаком умножения ×, а в поиске буквой х. Правильную
# типографику мы не ломаем, но один раз называем вариант, которым
# запрос набирают на клавиатуре.
NOTE_BETON = ("Класс прочности по ГОСТ 26633 записывают латинской буквой: B15, B22,5. "
              "В поиске то же обозначение чаще набирают кириллицей, В15 и В22,5, "
              "разница только в раскладке клавиатуры. Купить бетон можно от одного куба: "
              "до двух кубов дешевле выходит самосвалом, дальше миксером.")

NOTE_PLITKA = ("Размеры на сайте набраны знаком умножения, 300×300×30, а в поиске их набирают "
               "буквой х: 300х300х30, 400х400х50, 500х500х50. Это одни и те же ходовые форматы. "
               "Купить плитку можно от одного поддона, отсев и щебень под основание везём той же "
               "машиной, чтобы не платить за два выезда.")

# --- Прайс по семействам. Позиция, цена, куда ведёт ссылка.
PRICE_SETS = {

"nerud": dict(
 head="Материалы под эту задачу с доставкой",
 anchor="Щебень от 600 руб за куб, песок от 990, отсев от 500 с доставкой по области.",
 rows=[
  ("Щебень 20-40", "от 770 руб/м³", "/dostavka/shcheben/frakciya-20-40/"),
  ("Щебень 5-20", "от 1150 руб/м³", "/dostavka/shcheben/frakciya-5-20/"),
  ("Щебень 40-70", "от 770 руб/м³", "/dostavka/shcheben/frakciya-40-70/"),
  ("Отсев 0-5", "от 500 руб/м³", "/dostavka/otsev/"),
  ("Песок карьерный", "от 990 руб/м³", "/dostavka/pesok/karyernyy/"),
  ("ПГС", "от 500 руб/м³", "/dostavka/pgs/"),
  ("Скальный грунт", "от 400 руб/м³", "/dostavka/skalnyy-grunt/"),
 ]),

"pesok": dict(
 head="Песок и смеси с доставкой",
 anchor="Песок карьерный от 990 руб за куб, речной мытый от 1450, отсев от 500 с доставкой.",
 rows=[
  ("Песок карьерный", "от 990 руб/м³", "/dostavka/pesok/karyernyy/"),
  ("Песок речной мытый", "от 1450 руб/м³", "/dostavka/pesok/rechnoy/"),
  ("Отсев 0-5", "от 500 руб/м³", "/dostavka/otsev/"),
  ("ПГС", "от 500 руб/м³", "/dostavka/pgs/"),
  ("ЩПС", "от 700 руб/м³", "/dostavka/shchps/"),
 ]),

"beton": dict(
 head="Бетон с доставкой миксером",
 note=NOTE_BETON,
 anchor="Бетон от 3900 руб за куб за М100 до 5800 за М400 с доставкой миксером.",
 rows=[
  ("Бетон М100, класс B7,5", "от 3900 руб/м³", "/dostavka/beton/m100/"),
  ("Бетон М150, класс B12,5", "от 4200 руб/м³", "/dostavka/beton/m150/"),
  ("Бетон М200, класс B15", "от 4500 руб/м³", "/dostavka/beton/m200/"),
  ("Бетон М250, класс B20", "от 4800 руб/м³", "/dostavka/beton/m250/"),
  ("Бетон М300, класс B22,5", "от 5100 руб/м³", "/dostavka/beton/m300/"),
  ("Бетон М350, класс B25", "от 5400 руб/м³", "/dostavka/beton/m350/"),
  ("Бетон М400, класс B30", "от 5800 руб/м³", "/dostavka/beton/m400/"),
 ]),

"plitka": dict(
 head="Плитка и материалы основания с доставкой",
 note=NOTE_PLITKA,
 anchor="Плитка от 600 руб за квадрат, отсев под основание от 500 за куб с доставкой.",
 rows=[
  ("Квадрат 300×300×30, вибролитая", "от 600 руб/м²", "/dostavka/trotuarnaya-plitka-razmery/"),
  ("Брусчатка 200×100×40, вибропрессованная", "от 750 руб/м²", "/dostavka/trotuarnaya-plitka/"),
  ("Брусчатка 200×100×60, вибропрессованная", "от 950 руб/м²", "/dostavka/trotuarnaya-plitka/"),
  ("Старый город, набор размеров, 60 мм", "от 1100 руб/м²", "/dostavka/trotuarnaya-plitka-razmery/"),
  ("Отсев 0-5 под подстилающий слой", "от 500 руб/м³", "/dostavka/otsev/"),
  ("Щебень 20-40 в основание", "от 770 руб/м³", "/dostavka/shcheben/frakciya-20-40/"),
 ]),

"bordyur": dict(
 head="Бордюр и материалы установки с доставкой",
 anchor="Бордюр садовый от 260 руб за штуку, тротуарный от 520, дорожный от 640 с доставкой.",
 rows=[
  ("Бордюр садовый БР 100.20.8", "от 260 руб/шт", "/dostavka/bordyur/"),
  ("Бордюр садовый усиленный БР 100.20.10", "от 320 руб/шт", "/dostavka/bordyur/"),
  ("Бордюр тротуарный БР 100.30.15", "от 520 руб/шт", "/dostavka/bordyur/"),
  ("Бордюр дорожный БР 100.30.18", "от 640 руб/шт", "/dostavka/bordyur/"),
  ("Щебень 20-40 под ложе", "от 770 руб/м³", "/dostavka/shcheben/frakciya-20-40/"),
  ("Песок карьерный под подсыпку", "от 990 руб/м³", "/dostavka/pesok/karyernyy/"),
 ]),

"vodootvod": dict(
 head="Водоотвод с доставкой",
 anchor="Лоток бетонный от 720 руб за штуку, дождеприёмник от 900, решётка от 480.",
 rows=[
  ("Лоток бетонный 1000×140×125", "от 720 руб/шт", "/dostavka/lotki-vodootvodnye/"),
  ("Лоток бетонный 1000×200×185", "от 1250 руб/шт", "/dostavka/lotki-vodootvodnye/"),
  ("Дождеприёмник пластиковый 300×300", "от 900 руб/шт", "/dostavka/dozhdepriemniki/"),
  ("Решётка стальная оцинкованная A15", "от 480 руб/шт", "/dostavka/reshetki-dozhdepriemnikov/"),
  ("Решётка чугунная B125 на 100 мм", "от 950 руб/шт", "/dostavka/reshetki-dozhdepriemnikov/"),
  ("Щебень 20-40 в обойму", "от 770 руб/м³", "/dostavka/shcheben/frakciya-20-40/"),
 ]),

"kolca": dict(
 head="Кольца, днища и крышки с доставкой",
 anchor="Кольцо КС 10-9 от 3200 руб за штуку, днище от 3400, крышка от 3600 с доставкой.",
 rows=[
  ("Кольцо КС 7-9", "от 2400 руб/шт", "/dostavka/kolca-zhbi/"),
  ("Кольцо КС 10-9", "от 3200 руб/шт", "/dostavka/kolca-zhbi/"),
  ("Кольцо КС 15-9", "от 6800 руб/шт", "/dostavka/kolca-zhbi/"),
  ("Днище КЦД 10", "от 3400 руб/шт", "/dostavka/kolca-kanalizacionnye/"),
  ("Крышка КЦП 1-10", "от 3600 руб/шт", "/dostavka/kolca-kanalizacionnye/"),
  ("Щебень 20-40 на обсыпку", "от 770 руб/м³", "/dostavka/shcheben/frakciya-20-40/"),
 ]),

"bloki": dict(
 head="Блоки и кладочные материалы с доставкой",
 anchor="Керамзитоблок от 95 руб за штуку, арболит от 175, полистиролбетон от 195.",
 rows=[
  ("Керамзитобетонный блок 390×190×188", "от 95 руб/шт", "/dostavka/peskobloki/"),
  ("Перегородочный блок 600×100×300", "от 110 руб/шт", "/dostavka/peregorodochnye-bloki/"),
  ("Арболитовый блок 500×300×200", "от 175 руб/шт", "/dostavka/stenovye-bloki/"),
  ("Полистиролбетонный блок 600×300×200", "от 195 руб/шт", "/dostavka/stenovye-bloki/"),
  ("Цемент М500, мешок 50 кг", "от 470 руб/мешок", "/dostavka/cement-i-smesi/"),
  ("Песок карьерный под раствор", "от 990 руб/м³", "/dostavka/pesok/karyernyy/"),
 ]),

"smesi": dict(
 head="Цемент, смеси и химия с доставкой",
 anchor="Цемент М400 от 420 руб за мешок, М500 от 470, сухие смеси от 240.",
 rows=[
  ("Цемент М400, мешок 50 кг", "от 420 руб/мешок", "/dostavka/cement-i-smesi/"),
  ("Цемент М500, мешок 50 кг", "от 470 руб/мешок", "/dostavka/cement-i-smesi/"),
  ("Кладочная смесь, мешок 25 кг", "от 240 руб/мешок", "/dostavka/cement-i-smesi/"),
  ("Печная и жаростойкая смесь", "по запросу", "/dostavka/pechnye-smesi/"),
  ("Гидроизоляция и пропитки", "по запросу", "/dostavka/stroitelnaya-himiya/"),
  ("Песок речной мытый под раствор", "от 1450 руб/м³", "/dostavka/pesok/rechnoy/"),
 ]),

"zhbi": dict(
 head="ЖБИ с доставкой и разгрузкой",
 anchor="Блок ФБС от 3300 руб за штуку, плита перекрытия от 10800, перемычка от 850.",
 rows=[
  ("Блок ФБС 24.3.6", "от 3300 руб/шт", "/dostavka/fbs-bloki/"),
  ("Блок ФБС 24.4.6", "от 4200 руб/шт", "/dostavka/fbs-bloki/"),
  ("Плита перекрытия ПК 42-12", "от 10800 руб/шт", "/dostavka/zhbi-izdeliya/"),
  ("Плита дорожная ПДН", "от 19000 руб/шт", "/dostavka/dorozhnye-plity/"),
  ("Перемычка брусковая 2ПБ 13-1", "от 850 руб/шт", "/dostavka/zhbi-izdeliya/"),
  ("Щебень 20-40 в подготовку", "от 770 руб/м³", "/dostavka/shcheben/frakciya-20-40/"),
 ]),

"asfalt": dict(
 head="Материалы дорожного покрытия с доставкой",
 anchor="Асфальтовая крошка от 450 руб за куб, щебень 20-40 от 770 самовывозом.",
 rows=[
  ("Асфальтовая крошка", "от 500 руб/м³", "/dostavka/asfaltovaya-kroshka/"),
  ("Щебень 20-40", "от 770 руб/м³", "/dostavka/shcheben/frakciya-20-40/"),
  ("Отсев 0-5 на расклинцовку", "от 500 руб/м³", "/dostavka/otsev/"),
  ("Битумная эмульсия", "по запросу", "/dostavka/bitum-i-asfalt/"),
  ("Холодный асфальт в мешках", "по запросу", "/dostavka/bitum-i-asfalt/"),
 ]),
}

# --- Семейство для каждой статьи. Явно, без угадывания по подстроке.
FAM = {
 # Брендовые страницы: семейство задано явно, чтобы гидроизоляция
 # не показывала прайс на щебень, как это уже случалось с бордюром.
 "stati/pronikayushchaya-gidroizolyaciya": "smesi",
 "stati/kladochnaya-smes-dlya-pechey": "smesi",
 "stati/plastikovyy-sadovyy-bordyur": "bordyur",
 "stati/proizvoditeli-trotuarnoy-plitki": "plitka",

 # нерудка, расчёты и характеристики
 "stati/frakcii-shchebnya": "nerud",
 "stati/kakoy-shcheben-vybrat": "nerud",
 "stati/shcheben-ili-graviy": "nerud",
 "stati/skolko-shchebnya-nuzhno": "nerud",
 "stati/skolko-vesit-kub": "nerud",
 "stati/koefficient-uplotneniya": "nerud",
 "stati/gost-na-shcheben-i-pesok": "nerud",
 "stati/chem-otsypat-uchastok": "nerud",
 "stati/skalnyy-grunt-dresva-but": "nerud",
 "stati/skalnyy-grunt-klassifikaciya": "nerud",
 "stati/keramzit-frakcii-i-ves": "nerud",
 "stati/otsev-gde-primenyat": "nerud",
 "stati/pgs-ili-opgs": "nerud",
 "stati/dostavka-na-dachu": "nerud",
 "stati/cena-kuba-s-dostavkoy": "nerud",
 "stati/skolko-shchebnya-v-kamaze": "nerud",
 "stati/podushka-pod-fundament": "nerud",
 "stati/materialy-na-dom-po-etapam": "nerud",
 "shcheben/frakciya-40-70": "nerud",
 "shcheben/frakciya-20-40": "nerud",
 "shcheben/frakciya-5-20": "nerud",
 "shcheben/frakciya-5-10": "nerud",
 "shcheben/frakciya-10-20": "nerud",
 "shcheben/frakciya-70-120": "nerud",
 "shcheben/frakciya-70-150": "nerud",
 "shcheben/v-meshkah": "nerud",
 "pesok/karyernyy": "pesok",
 "pesok/rechnoy": "pesok",
 "pesok/peskostruynyy": "pesok",
 "pesok/v-meshkah": "pesok",
 # песок
 "stati/kakoy-pesok-vybrat": "pesok",
 "stati/klassy-peska": "pesok",
 "stati/modul-krupnosti-peska": "pesok",
 "stati/pesok-pod-plitku": "plitka",
 # бетон и раствор
 "stati/marki-betona": "beton",
 "stati/ves-kuba-betona": "beton",
 "stati/skolko-betona-v-miksere": "beton",
 "stati/skolko-shchebnya-i-peska-na-kub-betona": "beton",
 "stati/zames-betona-vedrami": "beton",
 "stati/styazhka-pola": "beton",
 "stati/otmostka-vokrug-doma": "beton",
 "stati/dorozhki-na-uchastke": "nerud",
 "beton/cena-za-kub": "beton",
 "beton/m100": "beton",
 "beton/m150": "beton",
 "beton/m200": "beton",
 "beton/m250": "beton",
 "beton/m300": "beton",
 "beton/m350": "beton",
 "beton/m400": "beton",
 "beton/betononasos": "beton",
 # смеси и химия
 "stati/rastvor-proporcii": "smesi",
 "stati/cement-m400-i-m500": "smesi",
 "stati/kladochnaya-smes": "smesi",
 "stati/pechnoy-rastvor": "smesi",
 "stati/nalivnoy-pol": "smesi",
 "stati/propitki-dlya-betona": "smesi",
 "stati/gidroizolyaciya-betona": "smesi",
 "stati/remontnye-smesi-dlya-betona": "smesi",
 # плитка
 "stati/vybrat-trotuarnuyu-plitku": "plitka",
 "stati/ukladka-trotuarnoy-plitki": "plitka",
 "stati/behaton": "plitka",
 "stati/plitka-svoimi-rukami": "plitka",
 "stati/formy-dlya-plitki": "plitka",
 "stati/uzory-plitki": "plitka",
 "stati/cvet-trotuarnoy-plitki": "plitka",
 "stati/granitnaya-bruschatka": "plitka",
 "stati/taktilnaya-plitka": "plitka",
 "stati/shvy-trotuarnoy-plitki": "plitka",
 # бордюр
 "stati/razmery-bordyurov": "bordyur",
 "bordyur/trotuarnyy": "bordyur",
 "bordyur/sadovyy": "bordyur",
 "stati/ustanovka-bordyura": "bordyur",
 "stati/sadovyy-bordyur": "bordyur",
 # водоотвод и кольца
 "stati/lotki-i-dozhdepriemniki": "vodootvod",
 "stati/kolca-zhbi-razmery": "kolca",
 # блоки
 "stati/arbolit-i-polistirolbeton": "bloki",
 # асфальт
 "stati/holodnyy-asfalt": "asfalt",
}

# --- Порядок заказа. Один на все статьи: процесс у нас действительно один.
ORDER_STEPS = [
 "Скажите, что купить и в каком объёме. Не знаете объём: назовите размеры участка работ, посчитаем по формулам из этой статьи.",
 "Назовите адрес и опишите заезд: ширину ворот, место для разворота и есть ли где поднять кузов.",
 "Получите точную цену с доставкой на ваш адрес. На месте сумма не меняется.",
 "Принимаете машину на объекте и проверяете объём по кузову, потом рассчитываетесь.",
]

# --- Возражения, которые до сих пор выяснялись только в переписке.
OBJECTIONS = [
 ("Минимальный объём", "Возим от 5 кубов одной машиной. Меньший объём тоже привезём, но за куб выйдет дороже: рейс оплачивается целиком."),
 ("Оплата", "После выгрузки на объекте. Предоплату не берём, аванс за материал не просим."),
 ("Как проверить объём", "Кузов самосвала имеет паспортную вместимость, и по нему объём проверяется на месте до разгрузки. Недовоз пересчитываем в вашу пользу."),
 ("Сроки", "Ходовые материалы отгружаем в день заявки или на следующий. Позиции под заказ подтверждаем по срокам до выезда машины."),
 ("Если ошиблись с объёмом", "Досыпать проще, чем вывозить. Считайте по нижней границе и добирайте: вторая машина обойдётся дешевле, чем вывоз лишнего."),
 ("Заезд на участок", "Скажите про узкие ворота, низкие провода и мягкий грунт заранее. Подберём машину по месту, а не развернёмся у ворот."),
]
