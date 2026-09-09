// Cloudflare Worker: отдаёт 410 Gone для мёртвых страниц старого сайта
// (каталог домов «НАШДОМ», давно снятый с продажи) и мусора от сканеров.
// Всё остальное проксируется на origin (GitHub Pages) без изменений.
//
// Подключение: Workers & Pages -> Create Worker -> вставить этот файл ->
// в настройках домена ursdom.ru добавить Workers Route: ursdom.ru/*

// Префиксы: под ними в текущем сайте нет вообще ничего, безопасно рубить всё.
const GONE_PREFIXES = [
  "/shop",
  "/my-postroili",
  "/novosti",
  "/aktsii-i-skidki",
  "/rieltor",
  "/rieltors",
  "/realty",
  "/otzyvy",
  "/kviz",
  "/support",
  "/tags",
  "/stati_old",
];

// Точные пути: рядом есть живой контент (/stati/, /userfls/), поэтому
// только конкретные адреса, а не всё под префиксом.
const GONE_EXACT = new Set([
  "/stati/etapy%20stroitelstva%20doma/",
  "/stati/khod-stroitelstva-zagorodnogo-doma-zimoy1/",
  "/stati/plyusy-i-minusy-zagorodnogo-stroitelstva-v-osenne-1/",
  "/stati/pokraska-doma-iz-brusa1/",
  "/userfls/",
  "/userfls/ufiles/",
  "/test.php/",
  "/test2.php/",
  "/test3.php/",
  "/mysql/",
  "/42qw586x5b7u811.php/",
  "/watchSE/",
  "/ads.txt/",
  "/NOCLICK_/",
]);

const GONE_BODY = `<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<title>Страница удалена</title><meta name="robots" content="noindex"></head>
<body><h1>Страница удалена окончательно</h1>
<p>Этой страницы больше нет и не будет — раздел, к которому она относилась,
закрыт. <a href="https://ursdom.ru/">На главную</a>.</p></body></html>`;

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname;

    const isGone =
      GONE_EXACT.has(path) ||
      GONE_PREFIXES.some((p) => path === p || path.startsWith(p + "/"));

    if (isGone) {
      return new Response(GONE_BODY, {
        status: 410,
        headers: { "content-type": "text/html; charset=utf-8" },
      });
    }

    return fetch(request);
  },
};
