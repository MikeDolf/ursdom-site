/* Плавающий блок связи и мобильная липкая панель: оба появляются один
   раз после прокрутки и больше не пропадают.

   Что было раньше и почему это переделано. Скрипт следил за блоками
   связи через IntersectionObserver и убирал виджет с экрана, когда
   рядом оказывалась форма заявки или блок с кнопками: логика была
   «не перекрывать то, что виджет и так дублирует». На практике это
   читалось как поломка. Владелец описал это так: кнопка появляется,
   а потом пропадает. Он прав, и это важнее исходной причины.

   Мигающий элемент интерфейса всегда выглядит сбоем, даже когда
   мигает по правилу: человек не видит правила, он видит, что кнопка
   была и исчезла, и перестаёт ей доверять. Перекрытие снято иначе,
   без скрипта: на телефоне плавающего блока нет, его значки стоят
   в липкой панели внизу, под которую у страницы есть нижний отступ.

   Осталось единственное правило: на первом экране блока нет. Там
   собственные кнопки крупнее и стоят в потоке, а виджет ложился
   на цену в стопке сит. После 700 пикселей прокрутки блок выезжает
   и дальше стоит на месте до конца страницы.

   Липкая панель внизу телефона (.d-mobilebar) раньше жила отдельно
   и была видна с самой загрузки страницы. На телефоне это значило
   четыре одинаковых по смыслу призыва в одном первом экране разом:
   три полноширинные кнопки геро (MAX, WhatsApp, заявка) и панель
   поверх них пятым слоем. Витрина цен, ради которой человек и зашёл,
   уезжала вниз под этот частокол кнопок. Правило то же, что и для
   плавающего блока: скрыта, пока не прокрутили мимо первого экрана.

   Без скрипта оба блока видны всегда: класс is-off ставится только
   отсюда, поэтому отключённый JavaScript ничего не ломает. */
(function () {
  "use strict";
  var targets = [".d-float", ".d-mobilebar"]
    .map(function (sel) { return document.querySelector(sel); })
    .filter(Boolean);
  if (!targets.length) return;

  var SHOW_AFTER = 700;
  var shown = false;

  function onScroll() {
    if (shown) return;
    if ((window.pageYOffset || document.documentElement.scrollTop) > SHOW_AFTER) {
      shown = true;
      targets.forEach(function (el) { el.classList.remove("is-off"); });
      /* Слушатель снимается сразу после первого срабатывания:
         дальше следить не за чем, а лишний обработчик на прокрутке
         это работа на каждом кадре ради ничего. */
      window.removeEventListener("scroll", onScroll);
    }
  }

  targets.forEach(function (el) { el.classList.add("is-off"); });
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
})();

/* Лента «Наши доставки». Без скрипта это горизонтальная лента
   с прилипанием кадра, её листают пальцем или колесом. Скрипт
   только показывает стрелки и листает на один кадр. */
(function () {
  "use strict";
  var navs = document.querySelectorAll(".d-slides-nav");
  Array.prototype.forEach.call(navs, function (nav) {
    var track = nav.parentNode.querySelector(".d-slides");
    if (!track) return;
    nav.hidden = false;
    Array.prototype.forEach.call(nav.querySelectorAll(".d-slides-btn"), function (btn) {
      btn.addEventListener("click", function () {
        var slide = track.querySelector(".d-slide");
        var step = slide ? slide.getBoundingClientRect().width + 16 : track.clientWidth;
        track.scrollBy({ left: step * parseInt(btn.getAttribute("data-dir"), 10), behavior: "smooth" });
      });
    });
  });
})();
