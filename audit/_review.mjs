// Поведенческая проверка страниц в настоящем браузере, телефон и компьютер.
// Дополняет _ui_audit.mjs (контраст, кегль, цели нажатия): здесь то,
// что ломается при работе со страницей, а не при взгляде на неё.
//
//   ошибки JS и упавшие запросы своего домена;
//   битые картинки (после прокрутки, чтобы догрузились ленивые);
//   горизонтальная прокрутка страницы;
//   калькулятор: ползунок и город меняют итог;
//   форма заявки: без телефона и согласия не уходит (ничего не отправляем);
//   частые вопросы: раскрываются, «показать ещё» открывает скрытые;
//   переход к форме по якорю не прячет её под липкую шапку.
//
// Запуск: python3 -m http.server 8899 --directory . &
//         node audit/_review.mjs urls.json mob|desk > out.json
import { chromium } from 'playwright';
import fs from 'fs';

const BASE = 'http://127.0.0.1:8899';
const urls = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const mode = process.argv[3] === 'desk' ? 'desk' : 'mob';
const VIEW = mode === 'desk' ? { width: 1440, height: 900 } : { width: 390, height: 844 };

// Проектный playwright может ждать другую сборку браузера; берём системную.
const browser = await chromium.launch({ executablePath: process.env.PW_CHROME || '/opt/pw-browsers/chromium' });
const ctx = await browser.newContext({ viewport: VIEW, deviceScaleFactor: 1,
  isMobile: mode === 'mob', hasTouch: mode === 'mob' });
// Чужие домены (метрика, реклама, формы) не нужны для проверки и тормозят.
await ctx.route(/^https?:\/\/(?!127\.0\.0\.1)/, r => r.abort());

const report = {};
const add = (u, k, v) => { (report[u] ||= {}); (report[u][k] ||= []).push(v); };

for (const u of urls) {
  const page = await ctx.newPage();
  page.on('pageerror', e => add(u, 'js', String(e.message).slice(0, 200)));
  page.on('console', m => { if (m.type() === 'error' && !/net::ERR_FAILED|ERR_BLOCKED|Failed to load resource: net::/.test(m.text())) add(u, 'console', m.text().slice(0, 200)); });
  page.on('response', r => { const x = r.url(); if (x.startsWith(BASE) && r.status() >= 400) add(u, 'http', r.status() + ' ' + x.slice(BASE.length)); });
  try {
    await page.goto(BASE + u, { waitUntil: 'load', timeout: 30000 });
  } catch (e) { add(u, 'load', String(e.message).slice(0, 120)); await page.close(); continue; }

  try {
  // прокрутка до конца: ленивые картинки и панель внизу
  await page.evaluate(async () => {
    const h = document.documentElement.scrollHeight;
    for (let y = 0; y < h; y += 700) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 25)); }
    window.scrollTo(0, 0);
  });
  await page.waitForTimeout(150);

  const st = await page.evaluate(() => {
    const out = {};
    const de = document.documentElement;
    if (de.scrollWidth > window.innerWidth + 1) out.hscroll = de.scrollWidth - window.innerWidth;
    out.broken = [...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.currentSrc || i.getAttribute('src')).slice(0, 5);
    out.noalt = [...document.images].filter(i => !i.hasAttribute('alt')).map(i => i.getAttribute('src')).slice(0, 5);
    out.badlinks = [...document.querySelectorAll('a')].filter(a => { const h = a.getAttribute('href'); return h === null || h === '' || h === '#' || /^javascript:/i.test(h); }).map(a => a.outerHTML.slice(0, 90)).slice(0, 5);
    const ids = {}; for (const e of document.querySelectorAll('[id]')) ids[e.id] = (ids[e.id] || 0) + 1;
    out.dupid = Object.entries(ids).filter(([k, n]) => n > 1).map(([k]) => k).slice(0, 5);
    // поля формы без подписи
    out.nolabel = [...document.querySelectorAll('input:not([type=hidden]):not(.d-hp), select, textarea')].filter(el => {
      if (el.getAttribute('aria-label') || el.getAttribute('aria-labelledby')) return false;
      if (el.id && document.querySelector('label[for="' + el.id + '"]')) return false;
      return !el.closest('label');
    }).map(el => el.outerHTML.slice(0, 80)).slice(0, 5);
    return out;
  });
  for (const [k, v] of Object.entries(st)) if (Array.isArray(v) ? v.length : v) add(u, k, v);

  // калькулятор
  if (await page.$('#calc-vol')) {
    const res = await page.evaluate(async () => {
      const ui = document.querySelector('.d-calc-ui');
      if (ui && ui.hidden) return 'интерфейс калькулятора остался скрыт (JS не запустился)';
      const out = () => (document.querySelector('#calc-out') || {}).textContent || '';
      const vol = document.querySelector('#calc-vol');
      const a = out();
      vol.value = vol.value === '20' ? '7' : '20';
      vol.dispatchEvent(new Event('input', { bubbles: true }));
      vol.dispatchEvent(new Event('change', { bubbles: true }));
      await new Promise(r => setTimeout(r, 80));
      const b = out();
      if (a === b) return 'итог не изменился после смены объёма';
      const dest = document.querySelector('#calc-dest');
      if (dest && dest.options.length > 1) {
        const cur = dest.value;
        const other = [...dest.options].findIndex(o => o.value !== cur);
        if (other >= 0) dest.selectedIndex = other;
        dest.dispatchEvent(new Event('input', { bubbles: true }));
        dest.dispatchEvent(new Event('change', { bubbles: true }));
        await new Promise(r => setTimeout(r, 80));
        if (out() === b) return 'итог не изменился после смены города';
      }
      if (/NaN|undefined|Infinity/.test(out())) return 'в итоге NaN/undefined';
      return '';
    });
    if (res) add(u, 'calc', res);
  }

  // форма: пустая не уходит
  const forms = await page.$$('form.d-form');
  if (forms.length) {
    const res = await page.evaluate(() => {
      const f = document.querySelector('form.d-form');
      const tel = f.querySelector('input[type=tel]');
      const cons = f.querySelector('input[name="Согласие"]');
      const errs = [];
      if (!tel || !tel.required) errs.push('телефон не обязателен');
      if (!cons || !cons.required) errs.push('согласие не обязательно');
      if (f.checkValidity()) errs.push('пустая форма проходит проверку');
      if (tel) { tel.value = '+7 912 345 67 89'; } if (cons) cons.checked = true;
      if (!f.checkValidity()) errs.push('заполненная форма не проходит проверку');
      if (tel) tel.value = ''; if (cons) cons.checked = false;
      const btn = f.querySelector('button[type=submit]');
      if (!btn) errs.push('нет кнопки отправки');
      if (!/web3forms/.test(f.action)) errs.push('action формы: ' + f.action);
      return errs;
    });
    for (const e of res) add(u, 'form', e);
  }

  // частые вопросы
  const faq = await page.evaluate(async () => {
    const d = document.querySelector('main details');
    if (!d) return '';
    const s = d.querySelector('summary');
    const was = d.open; s.click(); await new Promise(r => setTimeout(r, 30));
    if (d.open === was) return 'вопрос не раскрывается';
    const more = [...document.querySelectorAll('button')].find(b => /ещё вопрос/i.test(b.textContent));
    if (more) {
      const hiddenBefore = [...document.querySelectorAll('main details')].filter(x => x.offsetParent === null).length;
      more.click(); await new Promise(r => setTimeout(r, 60));
      const hiddenAfter = [...document.querySelectorAll('main details')].filter(x => x.offsetParent === null).length;
      if (hiddenBefore && hiddenAfter >= hiddenBefore) return '«показать ещё» не открывает вопросы';
    }
    return '';
  });
  if (faq) add(u, 'faq', faq);

  // якорь к форме не под шапкой
  const anc = await page.evaluate(async () => {
    const a = document.querySelector('a[href="#zayavka"]');
    const t = document.getElementById('zayavka');
    if (!a || !t) return '';
    a.scrollIntoView(); a.click();
    await new Promise(r => setTimeout(r, 700));
    const head = document.querySelector('.d-header');
    const hb = head ? head.getBoundingClientRect().bottom : 0;
    const tt = t.getBoundingClientRect().top;
    return tt < hb - 2 ? 'форма уходит под шапку: верх ' + Math.round(tt) + ', низ шапки ' + Math.round(hb) : '';
  });
  if (anc) add(u, 'anchor', anc);

  } catch (e) { add(u, 'crash', String(e.message).split('\n')[0].slice(0, 160) + ' -> ' + page.url()); }
  await page.close();
}
await browser.close();
console.log(JSON.stringify(report, null, 1));
