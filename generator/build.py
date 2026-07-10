#!/usr/bin/env python3
"""Сборщик статических страниц НАШДОМ из partials и config.

Зависимости: Python 3 + jinja2 (уже установлен в окружении).
Генератор предназначен для НОВЫХ страниц (статьи и рейтинги). Существующие
страницы сайта он не трогает: пути вывода задаются явно через --out.

Примеры:
  python3 generator/build.py --all --out _built
  python3 generator/build.py --page /drenazh/rating-geotekstilya/ --out _built
"""
import argparse, json, os, sys
from jinja2 import Environment, FileSystemLoader

GEN_DIR = os.path.dirname(os.path.abspath(__file__))
SITE = "https://ursdom.ru"

env = Environment(
    loader=FileSystemLoader([os.path.join(GEN_DIR, "templates"), GEN_DIR]),
    keep_trailing_newline=False,
    autoescape=False,
)

def render_partial(name, ctx):
    return env.get_template(os.path.join("partials", name)).render(**ctx).rstrip("\n")

def build_graph(page, ctx):
    """Собирает @graph в порядке, принятом на сайте, из JSON-LD partials."""
    if page["template"] == "rating":
        order = ["jsonld_breadcrumbs.j2", "jsonld_itemlist.j2", "jsonld_faq.j2"]
    else:
        order = ["jsonld_article.j2", "jsonld_breadcrumbs.j2", "jsonld_faq.j2"]
    parts = [render_partial(name, ctx) for name in order]
    return ",\n".join(parts)

def render_page(page):
    canonical = SITE + page["url"]
    ctx = dict(page)
    ctx["canonical"] = canonical
    ctx["og_title"] = page.get("og_title", page["title"])
    ctx["og_description"] = page.get("og_description", page["description"])
    # предрендер видимых partials
    ctx["header"] = render_partial("header.j2", ctx)
    ctx["breadcrumbs_html"] = render_partial("breadcrumbs.j2", ctx)
    ctx["footer"] = render_partial("footer.j2", ctx)
    ctx["metrika"] = render_partial("metrika.j2", ctx)
    ctx["graph_block"] = build_graph(page, ctx)
    # тело страницы из content/
    content_path = os.path.join(GEN_DIR, "content", page["content"])
    ctx["body"] = open(content_path, encoding="utf-8").read()
    tmpl = env.get_template(page["template"] + ".j2")
    html = tmpl.render(**ctx)
    return html.rstrip("\n") + "\n"

def load_pages():
    with open(os.path.join(GEN_DIR, "config", "pages.json"), encoding="utf-8") as f:
        return json.load(f)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", help="URL страницы для сборки (например /drenazh/rating-geotekstilya/)")
    ap.add_argument("--all", action="store_true", help="Собрать все страницы из config")
    ap.add_argument("--out", default="_built", help="Каталог вывода (по умолчанию _built)")
    args = ap.parse_args()

    pages = load_pages()
    if args.page:
        pages = [p for p in pages if p["url"] == args.page]
        if not pages:
            print("Страница не найдена в config:", args.page); sys.exit(1)
    elif not args.all:
        ap.error("укажите --page <url> или --all")

    for p in pages:
        html = render_page(p)
        rel = p["url"].strip("/")
        out_path = os.path.join(args.out, rel, "index.html")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print("собрано:", out_path)

if __name__ == "__main__":
    main()
