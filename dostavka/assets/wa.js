/* Плавающий виджет уступает место блокам связи.

   Ревью на телефоне показало, что виджет закрывает кнопку «Узнать цену
   с доставкой» в блоке связи: у неё срезается хвост текста. Фиксированный
   элемент перекрывает что-нибудь всегда, поэтому задача не убрать
   перекрытие вообще, а не перекрывать то, что дублирует сам виджет.

   Без этого скрипта виджет просто остаётся видимым всегда: деградация
   такая же, как была до правки, ничего не ломается. */
(function () {
  "use strict";
  var wa = document.querySelector(".d-wa");
  if (!wa || !("IntersectionObserver" in window)) return;

  var zones = document.querySelectorAll("#zayavka, .d-callblock, .d-midcta, footer.d-footer");
  if (!zones.length) return;

  var visible = 0;
  var io = new IntersectionObserver(function (entries) {
    for (var i = 0; i < entries.length; i++) {
      visible += entries[i].isIntersecting ? 1 : -1;
    }
    if (visible < 0) visible = 0;
    wa.classList.toggle("is-off", visible > 0);
  }, { rootMargin: "-10% 0px -10% 0px" });

  for (var i = 0; i < zones.length; i++) io.observe(zones[i]);
})();
