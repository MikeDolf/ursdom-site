// Проверка отрисовки по всем страницам раздела в настоящем браузере.
// Считает то, что нельзя проверить чтением CSS: реальный фон под текстом
// (он приходит от предка), фактический кегль, фактический размер кнопки.
import { chromium } from 'playwright';
import fs from 'fs';

const BASE = 'http://127.0.0.1:8899';
const urls = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const VIEW = process.argv[3] === 'desk' ? { width: 1440, height: 900 } : { width: 390, height: 844 };

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const ctx = await browser.newContext({ viewport: VIEW, deviceScaleFactor: 1 });
const page = await ctx.newPage();

const PROBE = () => {
  const out = { contrast: [], tap: [], row: [], overflow: [], font: [], fs: [], hidden: [] };

  const lin = c => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  const lum = ([r, g, b]) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  const parse = s => { const m = s.match(/[\d.]+/g); return m ? m.map(Number) : null; };
  const ratio = (a, b) => { const la = lum(a), lb = lum(b); const hi = Math.max(la, lb), lo = Math.min(la, lb); return (hi + 0.05) / (lo + 0.05); };

  // Реальный фон под элементом: поднимаемся, пока не найдём непрозрачную заливку.
  const bgOf = el => {
    let n = el;
    while (n && n !== document.documentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && (c.length < 4 || c[3] > 0.85)) return c.slice(0, 3);
      n = n.parentElement;
    }
    return [255, 255, 255];
  };
  const sel = el => el.tagName.toLowerCase() +
    (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).join('.') : '');

  // Шрифты: оба наших семейства обязаны быть загружены.
  for (const f of ['16px "Golos Text"', '16px "Mono Num"']) {
    if (!document.fonts.check(f)) out.font.push('не загружен: ' + f);
  }

  const all = [...document.querySelectorAll('body *')];

  for (const el of all) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') continue;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;

    // текст непосредственно в этом элементе, а не в потомках
    const own = [...el.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim()).map(n => n.textContent.trim()).join(' ');
    if (own) {
      const fg = parse(cs.color);
      if (fg && (fg.length < 4 || fg[3] > 0.5)) {
        const cr = ratio(fg.slice(0, 3), bgOf(el));
        const px = parseFloat(cs.fontSize);
        const bold = parseInt(cs.fontWeight, 10) >= 700;
        const large = px >= 24 || (px >= 18.66 && bold);
        const need = large ? 3 : 4.5;
        if (cr < need) out.contrast.push({ el: sel(el), text: own.slice(0, 42), cr: +cr.toFixed(2), need, px });
      }
      // кегль: ниже 12px на этом сайте нечитаемо, аудитория смотрит на улице
      const px = parseFloat(cs.fontSize);
      if (px < 12) out.fs.push({ el: sel(el), text: own.slice(0, 30), px });
    }

    // плейсхолдер проверяется отдельно: у него свой цвет
    if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
      const ph = getComputedStyle(el, '::placeholder');
      const fg = parse(ph.color);
      if (el.placeholder && fg) {
        const cr = ratio(fg.slice(0, 3), bgOf(el));
        if (cr < 4.5) out.contrast.push({ el: sel(el) + '::placeholder', text: el.placeholder.slice(0, 30), cr: +cr.toFixed(2), need: 4.5, px: parseFloat(ph.fontSize) });
      }
    }

    // Размер цели нажатия.
    // Три поправки, каждая после ложного срабатывания:
    // 1) элемент, уведённый за экран (ссылка «к содержимому»), меряется
    //    в скрытом состоянии и всегда мал - его размер имеет смысл только
    //    в фокусе, проверяется отдельно ниже;
    // 2) ссылка внутри строки сита растянута псевдоэлементом на всю
    //    строку, поэтому целью служит строка, а не бокс самой ссылки;
    // 3) для галки порог 24px по WCAG 2.5.8 (AA), а не 44 по 2.5.5 (AAA):
    //    сама метка кликабельна целиком, квадрат лишь прицел.
    if (el.tagName === 'A' || el.tagName === 'BUTTON' || (el.tagName === 'INPUT' && el.type === 'checkbox')) {
      const offscreen = r.right < 0 || r.left > window.innerWidth;
      const stretched = el.closest('.d-sieve-row, .d-cat-card');
      const box = stretched ? stretched.getBoundingClientRect() : r;
      // Порог поднят с 44 до 48 по требованию владельца. 44 это
      // минимум WCAG 2.5.5 (AAA), 48 это рекомендация Material и
      // Lighthouse: под неё же проверяет мобильный аудит Google.
      // Галка остаётся на 24 по WCAG 2.5.8 (AA): у неё своя норма.
      const need = el.tagName === 'INPUT' ? 24 : 48;
      if (!offscreen && cs.display !== 'inline' && r.height > 0
          && (box.height < need - 0.5 || box.width < 24)) {
        out.tap.push({ el: sel(el), w: Math.round(box.width), h: Math.round(box.height), need });
      }
    }

    if (r.right > window.innerWidth + 2 && cs.overflowX !== 'auto' && cs.overflowX !== 'scroll') {
      const p = el.closest('[style*="overflow"], .d-table-wrap');
      if (!p) out.overflow.push({ el: sel(el), right: Math.round(r.right), win: window.innerWidth });
    }
  }

  // «К содержимому» видна только в фокусе, там её и меряем.
  const skip = document.querySelector('.d-skip');
  if (skip) {
    skip.focus();
    const sr = skip.getBoundingClientRect();
    // Скрытый смысл. Рендер-аудит проверяет то, что видно, и поэтому
    // слеп к обратной ошибке: элемент с важным текстом получил
    // display:none и пропал совсем. Так на телефоне исчезла итоговая
    // сумма калькулятора: правило прятало колонку по позиции, а в строке
    // итога на этой позиции оказалась сумма. Проверяем адресно те узлы,
    // без которых блок теряет смысл.
    const mustSee = [
      ['.d-calc-total td', 'итоговая сумма калькулятора'],
      ['.d-pricebar b', 'цена в полосе якоря'],
      ['.d-head-tel', 'телефон в шапке'],
    ];
    for (const [sel, what] of mustSee) {
      const n = document.querySelector(sel);
      if (!n) continue;
      const r = n.getBoundingClientRect();
      const st = getComputedStyle(n);
      if (st.display === 'none' || st.visibility === 'hidden' || r.width < 1 || r.height < 1) {
        out.hidden.push({ sel, what, w: Math.round(r.width), h: Math.round(r.height) });
      }
    }

    if (sr.height < 47.5) out.tap.push({ el: 'a.d-skip:focus', w: Math.round(sr.width), h: Math.round(sr.height), need: 48 });
    skip.blur();
  }

  // симметрия: кнопки в одном ряду обязаны быть одной высоты
  for (const row of document.querySelectorAll('.d-cta-row')) {
    const bs = [...row.querySelectorAll('.d-btn')].map(b => b.getBoundingClientRect());
    if (bs.length > 1) {
      const hs = bs.map(b => Math.round(b.height));
      if (Math.max(...hs) - Math.min(...hs) > 1) out.row.push({ what: 'разная высота кнопок', hs });
      const tops = bs.map(b => Math.round(b.top));
      if (Math.max(...tops) - Math.min(...tops) > 1 && new Set(tops).size > 1 && bs[0].top === bs[1].top) { /* перенос строки допустим */ }
    }
  }
  return out;
};

const report = {};
for (const u of urls) {
  await page.goto(BASE + u, { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(120);
  const r = await page.evaluate(PROBE);
  const total = Object.values(r).reduce((a, b) => a + b.length, 0);
  if (total) report[u] = r;
}
await browser.close();
console.log(JSON.stringify(report, null, 1));
