# Генератор страниц НАШДОМ

Сборщик статичных страниц сайта из partials и реестра. Нужен для **новых**
страниц (статьи и рейтинги), чтобы они были неотличимы от уже выложенных.
Существующие файлы сайта генератор не трогает: он пишет только в каталог,
указанный через `--out`.

Зависимости: Python 3 и `jinja2` (уже стоит в окружении). Больше ничего,
никаких CDN и внешних пакетов, как и весь сайт.

## Что где лежит

- `partials/` — куски разметки под текущий дизайн (`header`, `footer`,
  `breadcrumbs`, `metrika`) и JSON-LD блоки (`jsonld_article`,
  `jsonld_breadcrumbs`, `jsonld_faq`, `jsonld_itemlist`). Плюс `macros.j2`
  с макросами для авторской вёрстки нового тела (`tldr`, `faq_item`,
  `rating_card`, `comparison_table`).
- `templates/` — `_base.j2` (общий каркас страницы) и две точки входа:
  `article.j2` (статья: Article + BreadcrumbList + FAQPage) и `rating.j2`
  (рейтинг: BreadcrumbList + ItemList + FAQPage).
- `config/pages.json` — реестр страниц: url, шаблон, кластер, маркер, тексты
  title/description/og, хлебные крошки, FAQ, даты и путь к телу.
- `content/<slug>.html` — тело страницы (всё, что внутри `<article>`).
- `build.py` — сборка. `_extract.py` — разовый хелпер, вытаскивает
  запись реестра и тело из уже существующей страницы.

## Сборка

```
# собрать все страницы реестра во временный каталог
python3 generator/build.py --all --out generator/_out

# собрать одну страницу
python3 generator/build.py --page /drenazh/rating-geotekstilya/ --out generator/_out
```

Каталог `--out` временный: проверьте результат и вручную скопируйте нужный
`index.html` на его место в репозитории. Так исключены случайные перезаписи.

## Как добавить новую страницу за 3 шага

1. **Тело.** Создайте `content/<slug>.html` с содержимым `<article>`:
   `<h1>`, `<p class="tldr">`, секции, для рейтинга блок `buy-grid` с
   карточками и сравнительная таблица, `<section class="faq">` на
   `details/summary`, в конце `<nav class="related">`. Можно писать руками
   или собирать из макросов `partials/macros.j2`. Партнёрские кнопки только
   с `rel="sponsored nofollow noopener" target="_blank"`. Без длинных тире,
   без цен, без AggregateRating/Review.
2. **Реестр.** Добавьте запись в `config/pages.json`: `url`, `template`
   (`article` или `rating`), `title`, `description`, `og_title`,
   `og_description`, `breadcrumbs` (последняя крошка без `item`), `faq`
   (вопросы синхронно с `details` в теле). Для статьи: `headline`,
   `jsonld_description`, `datePublished`, `dateModified`. Для рейтинга:
   `itemlist_name`, `itemlist`.
3. **Сборка и выкладка.** `python3 generator/build.py --page <url> --out
   generator/_out`, проверьте `index.html`, скопируйте на место в
   репозитории, добавьте URL в `sitemap.xml` с `lastmod`, закоммитьте.

## Проверка соответствия дизайну

Генератор воспроизводит текущие страницы `config/pages.json` побайтово.
Проверить после правок partials:

```
python3 generator/build.py --all --out generator/_out
for u in skvazhina/kesson-dlya-skvazhiny drenazh/rating-drenazhnyh-trub \
         drenazh/rating-geotekstilya skvazhina/rating-gidroakkumulyatorov; do
  diff "$u/index.html" "generator/_out/$u/index.html" && echo "OK: $u"
done
rm -rf generator/_out
```

Пустой diff означает, что сборка совпадает с выложенными страницами.
