# -*- coding: utf-8 -*-
"""Минификация CSS для отдачи, исходник остаётся читаемым.

Lighthouse просил 10 КБ на минификации. Готовый минификатор тянуть
в проект ради одного файла незачем, но и регулярками резать CSS опасно:
строки в content, url() и пробелы внутри calc() ломаются первыми.
Поэтому здесь не регулярки по всему тексту, а посимвольный проход,
который знает про строки и комментарии и не трогает содержимое скобок
функций.

Что делается:
  - вырезаются комментарии, кроме тех, что внутри строк;
  - схлопываются пробельные последовательности;
  - убираются пробелы вокруг { } ; : , и вокруг комбинаторов > ~;
  - убирается последняя ; перед };
  - НЕ трогаются + и -: они значимы внутри calc() и в :nth-child.
"""


def minify(css):
    out = []
    i, n = 0, len(css)
    depth_fn = 0            # глубина круглых скобок: внутри них не режем
    quote = None
    while i < n:
        c = css[i]
        if quote:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(css[i + 1]); i += 2; continue
            if c == quote:
                quote = None
            i += 1; continue
        if c in "\"'":
            quote = c; out.append(c); i += 1; continue
        if c == "/" and i + 1 < n and css[i + 1] == "*":
            j = css.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == "(":
            depth_fn += 1; out.append(c); i += 1; continue
        if c == ")":
            depth_fn = max(0, depth_fn - 1); out.append(c); i += 1; continue
        if c in " \t\r\n":
            j = i
            while j < n and css[j] in " \t\r\n":
                j += 1
            nxt = css[j] if j < n else ""
            prev = out[-1] if out else ""
            if depth_fn:
                # внутри calc() и подобных пробел значим - оставляем один
                if prev and nxt:
                    out.append(" ")
            elif prev in "{};:,>~" or nxt in "{};:,>~)" or not prev or not nxt:
                pass
            else:
                out.append(" ")
            i = j; continue
        if c == ";" and not depth_fn:
            j = i + 1
            while j < n and css[j] in " \t\r\n":
                j += 1
            if j < n and css[j] == "}":
                i = j; continue
        out.append(c); i += 1
    return "".join(out).strip()
