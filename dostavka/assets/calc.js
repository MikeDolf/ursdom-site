/* Калькулятор доставки: надстройка над рабочей таблицей.

   Скрипт НЕ создаёт содержимое, он подменяет статическую таблицу
   примеров на интерактивную форму. Если файл не загрузился или
   JavaScript отключён, посетитель видит таблицу, а поисковик её
   индексирует. Поэтому здесь нет ни одного innerHTML с текстом,
   который иначе нигде не встречается.

   Формула повторяет data/calc.py буква в букву. Расхождение между
   ними ловится проверкой арифметики в audit/_verify.py: цифры
   в таблице и в интерактиве обязаны совпадать при тех же входных
   данных, иначе человек увидит одно, а в заявке получит другое. */
(function () {
  "use strict";
  var root = document.getElementById("kalkulyator");
  if (!root) return;

  var ui = root.querySelector(".d-calc-ui");
  var stat = root.querySelector(".d-calc-static");
  var mat = document.getElementById("calc-mat");
  var vol = document.getElementById("calc-vol");
  var volOut = document.getElementById("calc-vol-out");
  var dest = document.getElementById("calc-dest");
  var out = document.getElementById("calc-out");
  if (!ui || !mat || !vol || !dest || !out) return;

  var RATE = parseInt(root.getAttribute("data-rate"), 10) || 95;
  var MIN = parseInt(root.getAttribute("data-min"), 10) || 5;
  var TRUCKS = [5, 10, 20];

  function trips(v) {
    for (var i = 0; i < TRUCKS.length; i++) {
      if (v <= TRUCKS[i]) return { n: 1, cap: TRUCKS[i] };
    }
    var big = TRUCKS[TRUCKS.length - 1];
    return { n: Math.ceil(v / big), cap: big };
  }

  /* Пробел как разделитель разрядов, а не запятая: на сайте все числа
     набраны по русской типографике, и калькулятор не исключение. */
  function money(n) {
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  }

  function plural(n, one, few, many) {
    var m10 = n % 10, m100 = n % 100;
    if (m10 === 1 && m100 !== 11) return one;
    if (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) return few;
    return many;
  }

  function render() {
    var v = parseInt(vol.value, 10);
    var price = parseInt(mat.value, 10);
    var km = parseInt(dest.value, 10);
    var t = trips(v);
    var material = v * price;
    var delivery = t.n * km * RATE;
    var total = material + delivery;

    volOut.textContent = v;

    var lines = [
      ["Материал", v + " м³ × " + money(price) + " руб", money(material) + " руб"],
      ["Доставка", t.n + " " + plural(t.n, "рейс", "рейса", "рейсов") +
        " × " + km + " км × " + RATE + " руб", money(delivery) + " руб"],
      ["Итого предварительно", "", money(total) + " руб"]
    ];

    var html = '<table class="d-calc-table"><tbody>';
    for (var i = 0; i < lines.length; i++) {
      /* В строке итога колонка формулы пуста, поэтому заголовок
         занимает её через colspan: пустая ячейка это разметочный мусор,
         и проверка на пустые смысловые теги её ловит. */
      var last = i === lines.length - 1;
      html += last
        ? '<tr class="d-calc-total"><th scope="row" colspan="2">' + lines[i][0] +
          "</th><td>" + lines[i][2] + "</td></tr>"
        : '<tr><th scope="row">' + lines[i][0] + "</th><td>" +
          lines[i][1] + "</td><td>" + lines[i][2] + "</td></tr>";
    }
    html += "</tbody></table>";

    html += '<p class="d-note">Кузов ' + t.cap + " м³. ";
    if (v < MIN) {
      html += "Объём меньше " + MIN + " м³: рейс оплачивается целиком, " +
              "поэтому куб выходит дороже. ";
    }
    if (t.n > 1) {
      html += "Объём не входит в один кузов, плечо оплачивается за каждый рейс. ";
    }
    html += "Расчёт предварительный, точную сумму называем по заявке.</p>";

    out.innerHTML = html;
  }

  /* Форма показывается только после того, как обработчики повешены:
     иначе между отрисовкой и готовностью скрипта существует момент,
     когда ползунок виден и не работает. */
  mat.addEventListener("input", render);
  vol.addEventListener("input", render);
  dest.addEventListener("input", render);
  render();
  ui.hidden = false;
  if (stat) stat.hidden = true;
})();
