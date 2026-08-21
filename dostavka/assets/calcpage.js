/* Калькуляторы объёма и веса на страницах раздела /kalkulyator/.

   Устроено так же, как калькулятор доставки: скрипт НЕ создаёт
   содержимое, он подменяет статические таблицы готовых расчётов
   на поля ввода. Без JavaScript посетитель видит таблицы, поисковик
   их индексирует. Поэтому здесь нет ни одного innerHTML с текстом,
   которого больше нигде на странице нет.

   Формулы повторяют calcpage_ctx в build.py буква в букву: числа
   в таблице и в интерактиве обязаны совпадать при тех же входных
   данных, иначе человек увидит одно, а в заявке получит другое. */
(function () {
  "use strict";

  /* Пробел как разделитель разрядов и запятая как десятичный знак:
     на сайте все числа набраны по русской типографике. */
  function money(n) {
    return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  }
  function fmt(x) {
    var r = Math.round(x * 10) / 10;
    if (Math.abs(r - Math.round(r)) < 0.05) return String(Math.round(r));
    return r.toFixed(1).replace(".", ",");
  }
  /* Плотность двумя знаками: 1,35 и 1,40 при округлении до одного
     превращались в «1,4-1,4», и диапазон переставал быть диапазоном. */
  function dens(x) { return x.toFixed(2).replace(".", ","); }
  function plural(n, one, few, many) {
    var m10 = n % 10, m100 = n % 100;
    if (m10 === 1 && m100 !== 11) return one;
    if (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) return few;
    return many;
  }
  /* Поля текстовые, а не number: type=number отвергает запятую,
     а десятичный знак на сайте именно запятая. Поэтому и границы
     проверяются здесь, а не атрибутами min/max. */
  function num(el, fallback, lo, hi) {
    var v = parseFloat(String(el.value).replace(",", "."));
    if (!isFinite(v) || v <= 0) return fallback;
    if (lo != null && v < lo) return lo;
    if (hi != null && v > hi) return hi;
    return v;
  }

  var TRUCKS = [5, 10, 20];
  function trips(v) {
    for (var i = 0; i < TRUCKS.length; i++) {
      if (v <= TRUCKS[i]) return { n: 1, cap: TRUCKS[i] };
    }
    var big = TRUCKS[TRUCKS.length - 1];
    return { n: Math.ceil(v / big), cap: big };
  }

  /* ---------------------------------------------- объём по размерам */
  (function () {
    var root = document.getElementById("obem");
    if (!root) return;
    var ui = root.querySelector(".d-vc-ui");
    var stat = root.querySelector(".d-vc-static");
    var L = document.getElementById("vc-l");
    var W = document.getElementById("vc-w");
    var H = document.getElementById("vc-h");
    var out = document.getElementById("vc-out");
    if (!ui || !L || !W || !H || !out) return;

    var K = parseFloat(root.getAttribute("data-k")) || 1;
    var DLO = parseFloat(root.getAttribute("data-dens-lo"));
    var DHI = parseFloat(root.getAttribute("data-dens-hi"));
    var PRICE = parseInt(root.getAttribute("data-price"), 10) || 0;

    function render() {
      var l = num(L, 6, 0.1, 500), w = num(W, 4, 0.1, 500), h = num(H, 15, 1, 300);
      var geom = l * w * h / 100;
      var vol = geom * K;
      var t = trips(vol);

      var html = '<table class="d-calc-table"><tbody>';
      html += '<tr><th scope="row">Площадь</th>' +
        '<td class="d-calc-formula">' + fmt(l) + " × " + fmt(w) + " м</td>" +
        "<td>" + fmt(l * w) + " м²</td></tr>";
      html += '<tr><th scope="row">Слой в готовом виде</th>' +
        '<td class="d-calc-formula">' + fmt(l * w) + " м² × " + fmt(h) + " см</td>" +
        "<td>" + fmt(geom) + " м³</td></tr>";
      if (K > 1) {
        html += '<tr><th scope="row">Запас на уплотнение</th>' +
          '<td class="d-calc-formula">× ' + fmt(K) + "</td>" +
          "<td>" + fmt(vol - geom) + " м³</td></tr>";
      }
      if (isFinite(DLO) && isFinite(DHI)) {
        html += '<tr><th scope="row">Вес</th>' +
          '<td class="d-calc-formula">' + fmt(vol) + " м³ × " +
          dens(DLO) + "-" + dens(DHI) + " т/м³</td>" +
          "<td>" + fmt(vol * DLO) + "-" + fmt(vol * DHI) + " т</td></tr>";
      }
      if (PRICE) {
        html += '<tr><th scope="row">Материал</th>' +
          '<td class="d-calc-formula">' + fmt(vol) + " м³ × " + money(PRICE) +
          " руб</td><td>от " + money(vol * PRICE) + " руб</td></tr>";
      }
      html += '<tr class="d-calc-total"><th scope="row" colspan="2">' +
        "Заказать" + "</th><td>" + fmt(vol) + " м³</td></tr>";
      html += "</tbody></table>";

      html += '<p class="d-note">' + t.n + " " +
        plural(t.n, "рейс", "рейса", "рейсов") + " самосвалом " + t.cap + " м³. ";
      if (vol < 5) {
        html += "Объём меньше пяти кубов: рейс оплачивается целиком, " +
                "поэтому куб выходит дороже. ";
      }
      html += "Стоимость материала без доставки, доставку считает " +
              "калькулятор ниже. Расчёт предварительный.</p>";
      out.innerHTML = html;
    }

    L.addEventListener("input", render);
    W.addEventListener("input", render);
    H.addEventListener("input", render);
    render();
    ui.hidden = false;
    if (stat) stat.hidden = true;
  })();

  /* ---------------------------------------------- тонны и кубы */
  (function () {
    var root = document.getElementById("ves");
    if (!root) return;
    var ui = root.querySelector(".d-tc-ui");
    var stat = root.querySelector(".d-tc-static");
    var m3 = document.getElementById("tc-m3");
    var tn = document.getElementById("tc-t");
    var out = document.getElementById("tc-out");
    if (!ui || !m3 || !tn || !out) return;

    var DLO = parseFloat(root.getAttribute("data-dens-lo"));
    var DHI = parseFloat(root.getAttribute("data-dens-hi"));
    if (!isFinite(DLO) || !isFinite(DHI)) return;
    var MID = (DLO + DHI) / 2;

    /* Поля связаны в обе стороны, но пересчёт идёт только от того,
       в котором печатают. Иначе округление гуляет туда-обратно
       и число под пальцем меняется само. */
    function fromM3() {
      var v = num(m3, 0, 0, 100000);
      if (!v) { out.textContent = ""; return; }
      tn.value = fmt(v * MID);
      show(v, v * DLO, v * DHI);
    }
    function fromT() {
      var v = num(tn, 0, 0, 100000);
      if (!v) { out.textContent = ""; return; }
      m3.value = fmt(v / MID);
      show(v / MID, v, v);
    }
    function show(vol, tlo, thi) {
      var s = fmt(vol) + " м³ это " +
        (Math.abs(tlo - thi) < 0.05
          ? fmt(tlo) + " " + plural(Math.round(tlo), "тонна", "тонны", "тонн")
          : fmt(tlo) + "-" + fmt(thi) + " " +
            plural(Math.round(thi), "тонна", "тонны", "тонн")) +
        ". Разброс из-за влажности и фракции: после дождя тот же объём тяжелее.";
      out.textContent = s;
    }

    m3.addEventListener("input", fromM3);
    tn.addEventListener("input", fromT);
    fromM3();
    ui.hidden = false;
    if (stat) stat.hidden = true;
  })();
})();
