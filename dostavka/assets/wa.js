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

  /* Раньше скрипт вешал is-off и тут же читал позицию прокрутки:
     чтение сразу после смены класса заставляло браузер синхронно
     разложить всю страницу. На главной это 490 мс принудительной
     раскладки и длинная задача на секунду в Lighthouse. Класс
     по-прежнему ставится сразу (запись раскладку не запускает),
     а первое чтение идёт в requestAnimationFrame, когда раскладка
     уже готова. */
  function onScroll() {
    if ((window.pageYOffset || document.documentElement.scrollTop) > SHOW_AFTER) {
      targets.forEach(function (el) { el.classList.remove("is-off"); });
      /* Слушатель снимается сразу после первого срабатывания:
         дальше следить не за чем, а лишний обработчик на прокрутке
         это работа на каждом кадре ради ничего. */
      window.removeEventListener("scroll", onScroll);
    }
  }

  targets.forEach(function (el) { el.classList.add("is-off"); });
  window.addEventListener("scroll", onScroll, { passive: true });
  /* Кадр и таймер: проверка идёт уже после отрисовки кадра, когда
     раскладка посчитана и чтение позиции ничего не пересчитывает. */
  if (window.requestAnimationFrame) {
    window.requestAnimationFrame(function () { setTimeout(onScroll, 0); });
  } else {
    setTimeout(onScroll, 0);
  }
})();

/* Шапка уезжает вверх, когда страницу листают вниз, и возвращается
   при первом движении вверх. На телефоне липкая шапка занимала 60 px
   каждого экрана, а нужна она в момент, когда человек ищет, куда
   нажать, и почти всегда в этот момент он листает назад. Кнопка MAX
   при этом не пропадает: внизу стоит липкая панель.

   - Прячется только после того, как ушла служебная полоса и сама
     шапка (порог 200 px), иначе на первом экране она дёргалась бы.
   - Мелкие движения пальца (меньше 6 px) не считаются, иначе шапка
     мигала бы от дрожания при чтении.
   - Если фокус внутри шапки (переход с клавиатуры), она не прячется.
   - Позиция читается в requestAnimationFrame, не чаще раза за кадр.
   Без JavaScript шапка просто липкая, как и была. */
(function () {
  "use strict";
  var head = document.querySelector(".d-header");
  if (!head || !window.requestAnimationFrame) return;
  var last = 0, queued = false;
  var DELTA = 6, AFTER = 200;

  function update() {
    queued = false;
    var y = Math.max(0, window.pageYOffset || document.documentElement.scrollTop || 0);
    head.classList.toggle("is-stuck", y > 48);
    if (Math.abs(y - last) < DELTA) return;
    var down = y > last;
    last = y;
    if (down && y > AFTER && !head.contains(document.activeElement)) {
      head.classList.add("is-hidden");
    } else if (!down || y <= AFTER) {
      head.classList.remove("is-hidden");
    }
  }

  window.addEventListener("scroll", function () {
    if (!queued) { queued = true; window.requestAnimationFrame(update); }
  }, { passive: true });
  head.addEventListener("focusin", function () { head.classList.remove("is-hidden"); });
  window.requestAnimationFrame(function () {
    setTimeout(function () {
      last = window.pageYOffset || 0;
      update();
    }, 0);
  });
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

/* Формы заявки. Два правила, оба про то, чтобы заявка дошла.

   1. Номер короче десяти цифр не отправляем: «+7 912 345» проходил
      проверку required и приходил владельцу номером, по которому
      не перезвонить. Подсказка появляется у поля, а не страницей
      ошибки после отправки.
   2. После нажатия кнопка блокируется и пишет «Отправляем заявку»:
      сервис форм отвечает не мгновенно, и на медленном мобильном
      интернете человек жал кнопку второй раз, заявка приходила дважды.
      Возврат назад со страницы «спасибо» снимает блокировку (pageshow),
      иначе форма оставалась мёртвой. */
(function () {
  "use strict";
  var forms = document.querySelectorAll("form.d-form, form.d-qform");
  Array.prototype.forEach.call(forms, function (form) {
    var tel = form.querySelector('input[type="tel"]');
    var btn = form.querySelector('button[type="submit"]');
    var label = btn ? btn.textContent : "";
    if (tel) tel.addEventListener("input", function () { tel.setCustomValidity(""); });
    form.addEventListener("submit", function (e) {
      if (tel && tel.value.replace(/\D/g, "").length < 10) {
        e.preventDefault();
        tel.setCustomValidity("Проверьте номер: нужно 10-11 цифр, например +7 912 345-67-89");
        tel.reportValidity();
        return;
      }
      if (btn) {
        btn.disabled = true;
        btn.textContent = "Отправляем заявку...";
      }
    });
    window.addEventListener("pageshow", function () {
      if (btn) {
        btn.disabled = false;
        btn.textContent = label;
      }
    });
  });
})();
