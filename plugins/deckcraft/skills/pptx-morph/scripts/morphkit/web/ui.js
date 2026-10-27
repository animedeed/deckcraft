/* deckcraft web — интерфейс показа (ui.js, 0.3.0).
 * Опции колоды: DC.data.ui = {menu: "top"|"tabs"|"stamp"|"none", hud: true, theme: "auto"|"dark"|"light", …} —
 * полный список в OPT ниже; всё с запасными значениями. Слои: #dc-overlay (координаты сцены 1600×900: меню, кнопка
 * «вернуться», подсказки, подсветка ссылок, перо, указка) и #dcu (окно браузера: HUD, прогресс, заметки, обзор,
 * справка, переход по номеру). Окно докладчика — та же страница с ?presenter, синхронизация через BroadcastChannel
 * (+ postMessage между окном и его открывателем). Печать — #dcu-print из DC.renderStatic(i), страница на слайд.
 * Клавиши регистрируются в DC.keys (латиница и кириллица); перехват в фазе capture — только для открытых окон
 * (обзор, справка, номер слайда) и для кнопок/ссылок в фокусе (Enter/Space нажимают их, а не листают). */
'use strict';
(function () {
const DC = window.DC;
const stage = document.getElementById('dc-stage'), overlay = document.getElementById('dc-overlay');
if (!DC || !DC.data || !stage || !overlay) return;
const D = DC.data, N = D.slides.length, C = D.colors || {}, F = D.fonts || {};
const OPT = Object.assign({
  menu: 'top',          // top — строка разделов сверху; tabs — вкладки справа; stamp — штамп ГОСТ + линейка; none
  hud: true,            // нижняя панель управления (скрывается при бездействии)
  theme: 'auto',        // тон меню: auto — по фону слайда; dark / light — всегда
  hudPos: null,         // right | left | center (по умолчанию left при stamp, иначе right)
  idle: 2600,           // мс бездействия мыши до скрытия HUD и курсора
  dots: true,           // точки-слайды внутри раздела
  dotsMax: 14,          // в разделе длиннее — без точек (номер и обзор остаются)
  progress: true,       // нить прогресса сверху
  notes: false,         // открыть заметки-стикер сразу
  printNotes: false,    // печать: страница заметок после каждого слайда
  links: true,          // подсветка объектов-ссылок с подписью «куда»
  presenter: true,      // кнопка и клавиша окна докладчика
  pen: true, laser: true,
  laserColor: '#ff2a2a',
  accent: null,         // акцент интерфейса (роль или #hex); по умолчанию colors.accent
  tabColors: null,      // цвета вкладок (роли/hex)
  author: '', checker: '', date: '', code: 'ДК', org: '', lit: 'У', // поля штампа
}, D.ui || {});
if (!['top', 'tabs', 'stamp', 'none'].includes(OPT.menu)) OPT.menu = 'top';
const PRESENTER = new URLSearchParams(location.search).has('presenter');
const UI = DC.ui = Object.assign(DC.ui || {}, { opt: OPT, presenter: PRESENTER });
/* ---------- язык интерфейса: ui.lang или язык презентации (DC.data.lang), иначе ru ---------- */
const LANG = String(OPT.lang || D.lang || 'ru').slice(0, 2).toLowerCase();
const EN = {
  "Слайд {0}": "Slide {0}",
  "Раздел {0}": "Section {0}",
  "Слайды раздела «{0}»": "Slides of section “{0}”",
  "Слайд {0}: {1}": "Slide {0}: {1}",
  "Раздел {0}: {1}": "Section {0}: {1}",
  "Разделы презентации": "Presentation sections",
  "Разделы": "Sections",
  "Штамп: лист и разделы": "Title block: sheet and sections",
  "Изм.": "Rev.",
  "Лист": "Sheet",
  "Лит.": "Lit.",
  "Листов": "Sheets",
  "Разраб.": "Drawn",
  "Пров.": "Checked",
  "Дата": "Date",
  "Листы": "Sheets",
  "Лист {0}: {1}": "Sheet {0}: {1}",
  "Раздел {0} · {1}": "Section {0} · {1}",
  "вернуться к «": "back to “",
  "Вернуться к слайду {0}: {1} (Backspace)": "Back to slide {0}: {1} (Backspace)",
  "Backspace — к слайду {0}": "Backspace — to slide {0}",
  "вкл": "on",
  "выкл": "off",
  "→ раздел «{0}»": "→ section “{0}”",
  "→ раздел": "→ section",
  "← назад к «{0}»": "← back to “{0}”",
  "← назад": "← back",
  "↗ ссылка": "↗ link",
  "▸ следующий шаг": "▸ next step",
  "Рисунок на слайде стёрт": "Drawing on this slide erased",
  "Перо": "Pen",
  "Цвет {0}": "Colour {0}",
  "Тонкое": "Thin",
  "Среднее": "Medium",
  "Толстое": "Thick",
  " перо": " pen",
  "Ластик (E)": "Eraser (E)",
  "Отменить штрих (Z)": "Undo stroke (Z)",
  "Стереть всё на слайде (C)": "Clear slide (C)",
  "Закончить рисование (D, Esc)": "Stop drawing (D, Esc)",
  "Перо: рисуйте мышью · C — стереть · Esc — выйти": "Pen: draw with the mouse · C — clear · Esc — exit",
  "Указка: L — выключить": "Laser: L — turn off",
  "Прогресс показа": "Presentation progress",
  "Слайд {0} из {1}": "Slide {0} of {1}",
  "Заметки докладчика": "Speaker notes",
  "— к этому слайду заметок нет —": "— no notes for this slide —",
  "Слайд №": "Slide #",
  "нет такого (1–{0})": "no such slide (1–{0})",
  "Enter — перейти · Esc — отмена": "Enter — go · Esc — cancel",
  "Нет слайда {0}": "No slide {0}",
  "Полный экран недоступен": "Full screen is not available",
  "Номер слайда — обзор (O)": "Slide number — overview (O)",
  "Заметки": "Notes",
  "Заметки (N)": "Notes (N)",
  "Обзор": "Overview",
  "Обзор слайдов (O, Esc)": "Slide overview (O, Esc)",
  "Докладчик": "Presenter",
  "Окно докладчика (P)": "Presenter view (P)",
  "Перо (D)": "Pen (D)",
  "Указка": "Laser",
  "Лазерная указка (L)": "Laser pointer (L)",
  "Экран": "Screen",
  "Полный экран (F)": "Full screen (F)",
  "Управление показом": "Presentation controls",
  "Назад (←)": "Back (←)",
  "Вперёд (→, пробел)": "Next (→, space)",
  "Печать / PDF": "Print / PDF",
  "Клавиши (?)": "Keys (?)",
  "Обзор слайдов": "Slide overview",
  "Презентация": "Presentation",
  "← → ↑ ↓ — выбор · Enter — открыть · Esc — закрыть": "← → ↑ ↓ — select · Enter — open · Esc — close",
  "Закрыть обзор (Esc)": "Close overview (Esc)",
  "Без раздела": "No section",
  "→ · Пробел · PgDn": "→ · Space · PgDn",
  "дальше: шаг или слайд": "next: step or slide",
  "назад": "back",
  "первый · последний слайд": "first · last slide",
  "цифры + Enter": "digits + Enter",
  "перейти к слайду по номеру": "go to a slide by number",
  "вернуться туда, откуда пришли по ссылке": "return to where a link took you from",
  "обзор всех слайдов": "overview of all slides",
  "заметки-стикер": "sticky notes",
  "окно докладчика": "presenter view",
  "перо (C — стереть, E — ластик, Z — отменить)": "pen (C — clear, E — eraser, Z — undo)",
  "лазерная указка": "laser pointer",
  "чёрный экран": "black screen",
  "полный экран": "full screen",
  "эта справка": "this help",
  "свайп": "swipe",
  "листать на сенсорном экране": "page on a touch screen",
  "Клавиши": "Keys",
  "Клавиши показа": "Presentation keys",
  "Закрыть справку (Esc)": "Close help (Esc)",
  "Клик по объекту с рамкой — переход по ссылке; наведение — подсказка. Буквы работают и в русской раскладке.": "Click an outlined object to follow its link; hover for a tip. Keys also work in the Russian layout.",
  "Окно докладчика открыто — листать можно из любого окна": "Presenter view is open — you can page from either window",
  "Браузер не дал открыть окно: разрешите всплывающие окна для этой страницы": "The browser blocked the window: allow pop-ups for this page",
  "Докладчик · ": "Presenter · ",
  "Пауза": "Pause",
  "Пауза / продолжить таймер": "Pause / resume timer",
  "Дальше": "Resume",
  "Сброс": "Reset",
  "Сбросить таймер": "Reset timer",
  "Текущий слайд": "Current slide",
  "Чёрный экран": "Black screen",
  "Чёрный экран в окне показа (B)": "Black screen in the show window (B)",
  "Время доклада": "Talk time",
  "Следующий слайд": "Next slide",
  "Далее": "Next",
  "Мельче": "Smaller",
  "Крупнее": "Larger",
  "Управление": "Controls",
  "Вперёд (→)": "Next (→)",
  "Обзор слайдов (O)": "Slide overview (O)",
  "Перо (D) — рисунок появится и в окне показа": "Pen (D) — the drawing also appears in the show window",
  "шаг {0} из {1}": "step {0} of {1}",
  "Этот же слайд, шаг {0} из {1}": "Same slide, step {0} of {1}",
  "Конец": "End",
  "Последний слайд": "Last slide",
  "Слайд {0} из {1}. {2}": "Slide {0} of {1}. {2}",
  "слайд": "slide",
  "слайда": "slides",
  "слайдов": "slides"
  };
const tr = (s, ...a) => { let t = (LANG === 'en' && EN[s]) || s; a.forEach((v, i) => { t = t.split('{' + i + '}').join(v) }); return t };
UI.lang = LANG; UI.tr = tr;
if (LANG === 'en') { if (OPT.code === 'ДК') OPT.code = 'DC'; if (OPT.lit === 'У') OPT.lit = '' }

/* ---------- утилиты ---------- */
function h(tag, a, ...kids) {
  const e = document.createElement(tag);
  if (a) for (const k in a) {
    const v = a[k]; if (v === undefined || v === null || v === false) continue;
    if (k === 'class') e.className = v; else if (k === 'text') e.textContent = v;
    else if (k.startsWith('on') && typeof v === 'function') e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? '' : v);
  }
  for (const c of kids.flat()) if (c !== null && c !== undefined && c !== false) e.append(c);
  return e;
}
function btn(label, aria, fn, cls, more) {
  const b = h('button', Object.assign({ type: 'button', class: 'dcu-b' + (cls ? ' ' + cls : ''), 'aria-label': aria, title: aria }, more || {}), label);
  b.addEventListener('click', e => { e.stopPropagation(); fn(e, b) });
  return b;
}
const role = v => (v && C[v]) || v;
const title = i => (D.slides[i] && D.slides[i].title) || tr('Слайд {0}', i + 1);
const short = (t, n = 38) => (t = String(t)).length > n ? t.slice(0, n - 1).trimEnd() + '…' : t;
const pad2 = n => String(n).padStart(2, '0');
const plural = (n, a, b, c) => { if (String((DC.ui && DC.ui.lang) || DC.data.lang || 'ru').startsWith('en')) return n === 1 ? a : c; const x = n % 10, y = n % 100; return x === 1 && y !== 11 ? a : x >= 2 && x <= 4 && (y < 12 || y > 14) ? b : c };
function lum(hex) {
  if (!hex || hex[0] !== '#' || hex.length < 7) return 1;
  const v = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255).map(c => c <= .03928 ? c / 12.92 : Math.pow((c + .055) / 1.055, 2.4));
  return .2126 * v[0] + .7152 * v[1] + .0722 * v[2];
}
const contrast = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + .05) / (Math.min(x, y) + .05) };
const onColor = c => contrast(c, '#ffffff') >= contrast(c, C.ink || '#16171b') ? '#ffffff' : (C.ink || '#16171b');
function mixHex(a, b, t) { if (!a || a[0] !== '#' || !b || b[0] !== '#') return a; const p = [1, 3, 5].map(i => parseInt(a.slice(i, i + 2), 16)), q = [1, 3, 5].map(i => parseInt(b.slice(i, i + 2), 16)); return '#' + p.map((v, i) => Math.round(v + (q[i] - v) * t).toString(16).padStart(2, '0')).join('') }
function toStage(cx, cy) { const r = stage.getBoundingClientRect(), k = r.width / 1600 || 1; return [(cx - r.left) / k, (cy - r.top) / k, k] }
const isDark = i => lum((D.slides[i] && D.slides[i].bg) || C.bg || '#ffffff') < .3;
const stepsOf = i => ((D.slides[i] && D.slides[i].steps) || []).length;
const stepsDone = i => ((D.slides[i] && D.slides[i].stepT) || []).length;

/* ---------- тема интерфейса ---------- */
const root = document.documentElement;
const accent = role(OPT.accent) || C.accent || '#8e1f33';
const setv = (k, v) => { if (v) root.style.setProperty(k, v) };
setv('--dcu-accent', accent); setv('--dcu-on-accent', onColor(accent));
setv('--dcu-accent-hi', lum(accent) < .12 ? mixHex(accent, '#ffffff', .42) : accent);
setv('--dcu-ink', C.ink); setv('--dcu-paper', C.bg); setv('--dcu-surface', C.surface); setv('--dcu-line', C.line);
setv('--dcu-muted', C.muted); setv('--dcu-bad', C.bad); setv('--dcu-head', F.head); setv('--dcu-body', F.body); setv('--dcu-mono', F.mono);
root.classList.add('dcu', OPT.theme === 'light' ? 'dcu-light' : 'dcu-darkui');
if (DC.REDUCED) root.classList.add('dcu-reduced');
// ui.css на месте? (html.py кладёт все *.css; без стилей не показываем HUD и панели — только клавиши и логику)
const CSS_OK = !!getComputedStyle(root).getPropertyValue('--dcu-pop').trim();
const ABS = 'position:absolute;left:0;top:0;'; // раскладка, которая не зависит от ui.css

/* ---------- разделы ---------- */
const SECS = (D.sections || []).map((s, k) => ({ title: s.title || tr('Раздел {0}', k + 1), start: s.start || 0, k, slides: [] }));
function secOf(i) {
  const s = D.slides[i] && D.slides[i].sec;
  if (typeof s === 'number' && SECS[s]) return s;
  let r = -1; SECS.forEach((x, k) => { if (x.slides.length ? x.slides[0] <= i : x.start <= i) r = k }); return r;
}
D.slides.forEach((s, i) => { if (typeof s.sec === 'number' && SECS[s.sec]) SECS[s.sec].slides.push(i) });
D.slides.forEach((s, i) => { if (!(typeof s.sec === 'number' && SECS[s.sec])) { const k = secOf(i); if (k >= 0) SECS[k].slides.push(i) } });
SECS.forEach(s => s.slides.sort((a, b) => a - b));
UI.secOf = secOf;

/* ---------- слои ---------- */
const L = h('div', { class: 'dcu-layer', style: ABS + 'width:1600px;height:900px;pointer-events:none' }); // координаты сцены
overlay.appendChild(L);
const V = h('div', { id: 'dcu', class: 'dcu-v', style: 'position:fixed;inset:0;pointer-events:none;z-index:20', hidden: !CSS_OK }); // во всё окно
document.body.appendChild(V);
const sr = h('div', { class: 'dcu-sr', 'aria-live': 'polite', 'aria-atomic': 'true' }); V.append(sr);

/* ---------- состояние ---------- */
const st = { notes: !!OPT.notes, ov: false, help: false, pen: false, laser: false, black: false, goto: '' };
let cur = -1, remote = false, quiet = PRESENTER; // quiet: докладчик не двигает показ, пока не получил его позицию
let clickLock = 0, clickPrev;
function lockClick(on) { // перо/указка: клик по сцене не листает; после выключения — как было
  if (on) { if (!clickLock++) { clickPrev = DC.clickAdvance; DC.clickAdvance = false } }
  else if (clickLock > 0 && !--clickLock) DC.clickAdvance = clickPrev;
}
function pointOf(elm) { if (!elm || !DC.sheetPoint) return; const r = elm.getBoundingClientRect(); const [x, y] = toStage(r.left + r.width / 2, r.top + r.height / 2); if (x >= 0 && x <= 1600 && y >= 0 && y <= 900) DC.sheetPoint(x, y) }
function goSection(k, elm) { const s = SECS[k]; if (!s || !s.slides.length) return; pointOf(elm); if (D.sections[k] && D.sections[k].start !== s.slides[0]) DC.go(s.slides[0], { push: true }); else DC.follow({ section: k }) }
function goSlide(i, elm, push) { pointOf(elm); DC.go(i, push ? { push: true } : {}) }

/* ---------- меню разделов ---------- */
function dotsOf(s, vertical) {
  const box = h('span', { class: 'dcu-dots' + (vertical ? ' dcu-vert' : ''), role: 'group', 'aria-label': tr('Слайды раздела «{0}»', s.title) });
  for (const i of s.slides) {
    const d = h('button', { type: 'button', class: 'dcu-dot', 'data-i': i, 'aria-label': tr('Слайд {0}: {1}', i + 1, title(i)), title: `${i + 1} · ${title(i)}` });
    d.addEventListener('click', e => { e.stopPropagation(); goSlide(i, d) });
    box.append(d);
  }
  return box;
}
function markDots(scope, i) { scope.querySelectorAll('.dcu-dot').forEach(d => { const on = +d.dataset.i === i; d.classList.toggle('dcu-cur', on); if (on) d.setAttribute('aria-current', 'step'); else d.removeAttribute('aria-current') }) }
function secButton(s, k, cls, kids) {
  const b = h('button', { type: 'button', class: cls, 'aria-label': tr('Раздел {0}: {1}', k + 1, s.title), disabled: !s.slides.length }, kids);
  b.addEventListener('click', e => { e.stopPropagation(); goSection(k, b) });
  return b;
}
function menuTop() {
  const nav = h('nav', { class: 'dcu-menu dcu-top dcu-i', 'aria-label': tr('Разделы презентации') }), pill = h('div', { class: 'dcu-pill', 'aria-hidden': 'true' });
  nav.append(pill);
  const items = SECS.map((s, k) => {
    const dots = OPT.dots && s.slides.length > 1 && s.slides.length <= OPT.dotsMax;
    const it = h('div', { class: 'dcu-sec' + (dots ? '' : ' dcu-nodots') + (s.slides.length ? '' : ' dcu-empty') }, secButton(s, k, 'dcu-sec-b', s.title), dots ? dotsOf(s) : null);
    nav.append(it); return it;
  });
  L.append(nav);
  let first = true;
  const place = k => {
    const it = items[k]; if (!it) { pill.style.opacity = 0; return }
    if (first) pill.classList.add('dcu-noanim');
    pill.style.opacity = 1; pill.style.width = it.offsetWidth + 'px'; pill.style.transform = `translateX(${it.offsetLeft}px)`;
    if (first) { void pill.offsetWidth; pill.classList.remove('dcu-noanim'); first = false }
  };
  return { el: nav, update(i) { const k = secOf(i); items.forEach((it, j) => { it.classList.toggle('dcu-on', j === k); const b = it.firstChild; if (j === k) b.setAttribute('aria-current', 'true'); else b.removeAttribute('aria-current') }); markDots(nav, i); place(k) }, relayout() { first = true; place(secOf(DC.cur)) } };
}
function menuTabs() {
  const nav = h('nav', { class: 'dcu-menu dcu-tabs dcu-i', 'aria-label': tr('Разделы презентации') });
  const pal = (OPT.tabColors || ['accent', 'accent2', 'accent3', 'good', 'warn', 'ink2']).map(role).filter(c => c && c[0] === '#');
  const items = SECS.map((s, k) => {
    const bg = pal[k % pal.length] || accent, tab = h('div', { class: 'dcu-tab' + (s.slides.length ? '' : ' dcu-empty') });
    tab.style.setProperty('--tab-bg', bg); tab.style.setProperty('--tab-fg', onColor(bg));
    tab.append(secButton(s, k, 'dcu-tab-b', [h('span', { class: 'dcu-tab-n' }, pad2(k + 1)), h('span', { class: 'dcu-tab-t' }, s.title)]));
    if (OPT.dots && s.slides.length > 1 && s.slides.length <= OPT.dotsMax) tab.append(dotsOf(s, true));
    nav.append(tab); return tab;
  });
  L.append(nav);
  return { el: nav, update(i) { const k = secOf(i); items.forEach((it, j) => { it.classList.toggle('dcu-on', j === k); const b = it.firstChild; if (j === k) b.setAttribute('aria-current', 'true'); else b.removeAttribute('aria-current') }); markDots(nav, i) } };
}
function menuStamp() {
  const cell = (area, cls, txt) => h('div', { class: 'dcu-c' + (cls ? ' ' + cls : ''), style: `grid-area:${area}` }, txt);
  const ttl = cell('1/3/5/4', 'dcu-st-ttl', ''), n = cell('2/5/3/6', 'dcu-st-big', ''), code = cell('3/4/4/7', 'dcu-st-code', ''), org = cell('4/4/5/7', 'dcu-st-org', '');
  const secs = h('div', { class: 'dcu-st-secs', style: 'grid-area:5/1/6/7', role: 'group', 'aria-label': tr('Разделы') });
  const sb = SECS.map((s, k) => { const b = secButton(s, k, 'dcu-st-sec', [h('b', {}, String(k + 1)), ' ', short(s.title, 22)]); secs.append(b); return b });
  const box = h('nav', { class: 'dcu-menu dcu-stamp dcu-i', 'aria-label': tr('Штамп: лист и разделы') },
    cell('1/1/2/2', 'dcu-k', tr('Изм.')), cell('1/2/2/3', 'dcu-k', tr('Лист')), ttl, cell('1/4/2/5', 'dcu-k', tr('Лит.')), cell('1/5/2/6', 'dcu-k', tr('Лист')), cell('1/6/2/7', 'dcu-k', tr('Листов')),
    cell('2/1/3/2', 'dcu-k', tr('Разраб.')), cell('2/2/3/3', '', OPT.author || '—'), cell('2/4/3/5', '', OPT.lit || ''), n, cell('2/6/3/7', 'dcu-st-big', String(N)),
    cell('3/1/4/2', 'dcu-k', tr('Пров.')), cell('3/2/4/3', '', OPT.checker || '—'), code,
    cell('4/1/5/2', 'dcu-k', tr('Дата')), cell('4/2/5/3', '', OPT.date || '—'), org, secs);
  const ruler = h('nav', { class: 'dcu-ruler dcu-i', 'aria-label': tr('Листы') });
  for (let i = 0; i < N; i++) {
    const maj = SECS.some(s => s.slides[0] === i);
    const b = h('button', { type: 'button', class: 'dcu-dot' + (maj ? ' dcu-maj' : ''), 'data-i': i, 'aria-label': tr('Лист {0}: {1}', i + 1, title(i)), title: `${i + 1} · ${title(i)}` });
    b.addEventListener('click', e => { e.stopPropagation(); goSlide(i, b) });
    ruler.append(b);
  }
  L.append(ruler, box);
  return { el: box, update(i) {
    const k = secOf(i); ttl.textContent = title(i); n.textContent = String(i + 1);
    code.textContent = tr('{0}.{1}.{2}', OPT.code || 'ДК', pad2(k + 1), pad2(i + 1));
    org.textContent = OPT.org || (SECS[k] ? tr('Раздел {0} · {1}', k + 1, SECS[k].title) : '');
    sb.forEach((b, j) => { b.classList.toggle('dcu-on', j === k); if (j === k) b.setAttribute('aria-current', 'true'); else b.removeAttribute('aria-current') });
    markDots(ruler, i);
  } };
}
const menu = PRESENTER || !SECS.length ? null : OPT.menu === 'top' ? menuTop() : OPT.menu === 'tabs' ? menuTabs() : OPT.menu === 'stamp' ? menuStamp() : null;
L.classList.add('dcu-m-' + (menu ? OPT.menu : 'none'));

/* ---------- кнопка «вернуться» ---------- */
const backBtn = h('button', { type: 'button', class: 'dcu-back dcu-i', hidden: true });
backBtn.addEventListener('click', e => { e.stopPropagation(); DC.back() });
L.append(backBtn);
function updBack() {
  const bs = DC.backStack || [];
  if (!bs.length) { backBtn.hidden = true; return }
  const j = bs[bs.length - 1];
  backBtn.replaceChildren(h('span', { class: 'dcu-back-a', 'aria-hidden': 'true' }, '←'), h('span', {}, tr('вернуться к «'), h('b', {}, short(title(j), 40)), '»'));
  backBtn.setAttribute('aria-label', tr('Вернуться к слайду {0}: {1} (Backspace)', j + 1, title(j)));
  backBtn.title = tr('Backspace — к слайду {0}', j + 1);
  if (backBtn.hidden) { backBtn.hidden = false; backBtn.classList.remove('dcu-pop'); void backBtn.offsetWidth; backBtn.classList.add('dcu-pop') }
}

/* ---------- подсказки ---------- */
const tipEl = h('div', { class: 'dcu-tip', role: 'tooltip', id: 'dcu-tip', style: ABS });
L.append(tipEl);
let tipObj = null;
function fillTip(tip) {
  const lines = Array.isArray(tip) ? tip.map(String) : String(tip).split('\n');
  tipEl.replaceChildren(...(lines.length > 1 ? [h('b', {}, lines[0]), ...lines.slice(1).map(l => h('span', {}, l))] : [h('span', {}, lines[0])]));
}
function placeTip(cx, cy) {
  const [x, y] = toStage(cx, cy), w = tipEl.offsetWidth, ht = tipEl.offsetHeight, m = 10;
  let lx = x + 18, ly = y + 22;
  if (lx + w > 1600 - m) lx = x - 18 - w;
  if (ly + ht > 900 - m) ly = y - 16 - ht;
  lx = Math.max(m, Math.min(1600 - w - m, lx)); ly = Math.max(m, Math.min(900 - ht - m, ly));
  tipEl.style.transform = `translate(${lx.toFixed(1)}px, ${ly.toFixed(1)}px)`;
}
function showTip(o, cx, cy) { tipObj = o; fillTip(o.tip); tipEl.classList.add('dcu-show'); placeTip(cx, cy); lhlLabel.hidden = true }
function hideTip() { tipObj = null; tipEl.classList.remove('dcu-show') }
DC.on('tip', (o, e, on) => {
  const w = e && e.currentTarget;
  if (w && w.querySelectorAll) w.querySelectorAll('title').forEach(t => t.remove()); // своя подсказка вместо системной
  if (on) { if (!st.pen && !st.ov) showTip(o, e ? e.clientX : 800, e ? e.clientY : 450) }
  else if (tipObj === o) hideTip();
});
stage.addEventListener('pointermove', e => { if (tipObj) placeTip(e.clientX, e.clientY) }, { passive: true });

/* ---------- подсветка ссылок ---------- */
const lhlLabel = h('span', { class: 'dcu-lhl-t' }), lhl = h('div', { class: 'dcu-lhl', 'aria-hidden': 'true', style: ABS }, lhlLabel);
L.append(lhl);
let lhlNode = null;
const fmt = v => v === true ? tr('вкл') : v === false ? tr('выкл') : String(v);
function linkLabel(l) {
  if (!l) return '';
  if (l.slide !== undefined) return `→ ${l.slide + 1}. ${short(title(l.slide), 34)}`;
  if (l.section !== undefined) return SECS[l.section] ? tr('→ раздел «{0}»', short(SECS[l.section].title, 28)) : tr('→ раздел');
  if (l.back) { const bs = DC.backStack || []; return bs.length ? tr('← назад к «{0}»', short(title(bs[bs.length - 1]), 28)) : tr('← назад') }
  if (l.href) { try { return '↗ ' + new URL(l.href, location.href).host } catch (e) { return tr('↗ ссылка') } }
  if (l.toggle) { const vals = l.values || [true, false], cv = DC.state[l.toggle] ?? vals[0], nx = vals[(vals.indexOf(cv) + 1) % vals.length]; return `⇄ ${fmt(cv)} → ${fmt(nx)}` }
  if (l.set) return '✓ ' + Object.entries(l.set).map(([k, v]) => `${k}: ${fmt(v)}`).join(', ');
  if (l.step) return tr('▸ следующий шаг');
  return '';
}
function objOfNode(g) {
  if (!DC.main || !DC.main.live) return null;
  const sl = D.slides[DC.cur]; if (!sl) return null;
  for (const [k, n] of DC.main.live) if (n.wrap === g) return sl.byName[k] || sl.byName[String(k).split('#')[0]] || null;
  return null;
}
function showLhl(g) {
  if (OPT.links === false || st.pen || st.ov) return;
  const o = objOfNode(g), r = g.getBoundingClientRect(), [x, y, k] = toStage(r.left, r.top), pad = 8;
  const w = r.width / k + 2 * pad, ht = r.height / k + 2 * pad;
  Object.assign(lhl.style, { left: (x - pad).toFixed(1) + 'px', top: (y - pad).toFixed(1) + 'px', width: w.toFixed(1) + 'px', height: ht.toFixed(1) + 'px' });
  const txt = o && o.link && !(tipObj && tipObj === o) && !o.tip ? linkLabel(o.link) : '';
  lhlLabel.textContent = txt; lhlLabel.hidden = !txt;
  lhl.classList.toggle('dcu-up', y + ht > 820);
  lhl.classList.toggle('dcu-right', x + 260 > 1600);
  lhl.classList.add('dcu-show'); lhlNode = g;
}
function hideLhl() { lhl.classList.remove('dcu-show'); lhlNode = null }
stage.addEventListener('pointerover', e => { const g = e.target.closest && e.target.closest('.dc-link'); if (g && !g.closest('.dc-snap') && g !== lhlNode) showLhl(g) });
stage.addEventListener('pointerout', e => { const g = e.target.closest && e.target.closest('.dc-link'); if (g && g === lhlNode && !(e.relatedTarget && g.contains(e.relatedTarget))) hideLhl() });
stage.addEventListener('focusin', e => {
  const g = e.target.closest && e.target.closest('.dc-link, .dc-tip'); if (!g) return;
  if (g.classList.contains('dc-link')) showLhl(g);
  const o = objOfNode(g); if (o && o.tip) { const r = g.getBoundingClientRect(); showTip(o, r.left + r.width * .5, r.bottom - 6) }
});
stage.addEventListener('focusout', () => { hideLhl(); hideTip() });
// ссылки и подсказки — доступны с клавиатуры (Tab, Enter / Space)
function a11yLinks() {
  if (!DC.main || !DC.main.live) return;
  const sl = D.slides[DC.cur]; if (!sl) return;
  for (const [k, n] of DC.main.live) {
    const w = n.wrap, isLink = w.classList.contains('dc-link');
    if (w.hasAttribute('tabindex') || !(isLink || w.classList.contains('dc-tip'))) continue;
    const o = sl.byName[k] || sl.byName[String(k).split('#')[0]];
    w.setAttribute('tabindex', '0'); w.setAttribute('role', isLink ? 'button' : 'note');
    const txt = o ? (o.t ? o.t.lines.map(r => r.map(x => x[0]).join('')).join(' ') : '') : '';
    const tip = o && o.tip ? [].concat(o.tip).join('. ') : '';
    const lab = [isLink && o ? linkLabel(o.link) : '', txt, tip].filter(Boolean).join(' — ');
    if (lab) w.setAttribute('aria-label', lab);
  }
}
const rootG = document.getElementById('dc-root');
if (rootG && window.MutationObserver) new MutationObserver(a11yLinks).observe(rootG, { childList: true });

/* ---------- перо и указка ---------- */
const uniq = a => a.filter((c, i) => c && a.indexOf(c) === i);
const PEN = uniq([accent, '#e03131', '#fcc419', '#1c7ed6', '#2f9e44', C.ink || '#16171b', '#ffffff']); // акцент темы + яркие маркеры
const ink = { color: PEN[0], size: 6, eraser: false, strokes: {}, cur: null, drawn: 0 };
UI.ink = ink;
const cv = h('canvas', { class: 'dcu-ink', 'aria-hidden': 'true', width: 2, height: 2, style: ABS + 'width:1600px;height:900px' }), cx = cv.getContext('2d');
let ires = 0;
L.append(cv);
function sizeInk() { const k = Math.min(2.5, (devicePixelRatio || 1) * Math.max(1, DC.scale || 1)); if (k === ires) return; ires = k; cv.width = Math.round(1600 * k); cv.height = Math.round(900 * k); redrawInk() }
function seg(s, from, end) { // сглаживание: квадратичные кривые через середины отрезков
  const p = s.p, n = p.length / 2;
  cx.save(); cx.setTransform(ires, 0, 0, ires, 0, 0);
  cx.globalCompositeOperation = s.e ? 'destination-out' : 'source-over';
  cx.strokeStyle = cx.fillStyle = s.c; cx.lineWidth = s.w; cx.lineCap = cx.lineJoin = 'round';
  if (n === 1) { if (from === 0) { cx.beginPath(); cx.arc(p[0], p[1], s.w / 2, 0, 2 * Math.PI); cx.fill() } }
  else {
    const i0 = Math.max(1, from); cx.beginPath();
    if (i0 === 1) cx.moveTo(p[0], p[1]); else cx.moveTo((p[2 * i0 - 4] + p[2 * i0 - 2]) / 2, (p[2 * i0 - 3] + p[2 * i0 - 1]) / 2);
    for (let i = i0; i < n; i++) cx.quadraticCurveTo(p[2 * i - 2], p[2 * i - 1], (p[2 * i - 2] + p[2 * i]) / 2, (p[2 * i - 1] + p[2 * i + 1]) / 2);
    if (end) cx.lineTo(p[2 * n - 2], p[2 * n - 1]);
    cx.stroke();
  }
  cx.restore();
}
function redrawInk() {
  if (!ires) return;
  cx.setTransform(1, 0, 0, 1, 0, 0); cx.clearRect(0, 0, cv.width, cv.height);
  for (const s of ink.strokes[DC.cur] || []) seg(s, 0, true);
}
const r1 = v => Math.round(v * 10) / 10;
cv.addEventListener('pointerdown', e => {
  if (!st.pen || e.button > 0) return;
  e.preventDefault(); e.stopPropagation();
  try { cv.setPointerCapture(e.pointerId) } catch (er) { }
  const [x, y] = toStage(e.clientX, e.clientY);
  const s = { c: ink.color, w: ink.eraser ? ink.size * 4 + 10 : ink.size, e: ink.eraser ? 1 : 0, p: [r1(x), r1(y)] };
  (ink.strokes[DC.cur] || (ink.strokes[DC.cur] = [])).push(s); ink.cur = s; ink.drawn = 0;
  seg(s, 0, false); ink.drawn = 1;
});
cv.addEventListener('pointermove', e => {
  if (!ink.cur) return;
  const evs = e.getCoalescedEvents ? e.getCoalescedEvents() : [e], p = ink.cur.p;
  for (const ev of evs.length ? evs : [e]) { const [x, y] = toStage(ev.clientX, ev.clientY); if (Math.hypot(x - p[p.length - 2], y - p[p.length - 1]) >= 1.5) p.push(r1(x), r1(y)) }
  const n = p.length / 2; if (n > ink.drawn) { seg(ink.cur, ink.drawn, false); ink.drawn = n }
});
function endStroke() { if (!ink.cur) return; ink.cur = null; redrawInk(); sendInk(DC.cur) }
cv.addEventListener('pointerup', endStroke); cv.addEventListener('pointercancel', endStroke);
cv.addEventListener('click', e => e.stopPropagation());
['touchstart', 'touchend'].forEach(t => cv.addEventListener(t, e => { if (st.pen) e.stopPropagation() }, { passive: true }));
function clearInk() { if (!(ink.strokes[DC.cur] || []).length) return; ink.strokes[DC.cur] = []; redrawInk(); sendInk(DC.cur); toast(tr('Рисунок на слайде стёрт')) }
function undoInk() { const a = ink.strokes[DC.cur]; if (!a || !a.length) return; a.pop(); redrawInk(); sendInk(DC.cur) }
const penBar = h('div', { class: 'dcu-pentools dcu-i', role: 'toolbar', 'aria-label': tr('Перо'), 'aria-orientation': 'vertical', hidden: true });
const swatches = PEN.map((c, k) => { const b = btn('', tr('Цвет {0}', k + 1), () => { ink.color = c; setEraser(false); markPen() }, 'dcu-sw'); b.style.setProperty('--sw', c); return b });
const sizes = [3, 6, 12].map((w, k) => { const b = btn(h('i', { style: `width:${w + 2}px;height:${w + 2}px` }), [tr('Тонкое'), tr('Среднее'), tr('Толстое')][k] + tr(' перо'), () => { ink.size = w; markPen() }, 'dcu-sz'); b.dataset.w = w; return b });
const ICON = {
  eraser: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 17l9-9 6 6-6 6H7z M14 20h7" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/></svg>',
  undo: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 7L4 12l5 5 M4 12h10a6 6 0 0 1 0 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" transform="translate(0 -3)"/></svg>',
  clear: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 7h14 M10 7V4h4v3 M7 7l1 13h8l1-13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  done: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12l5 5 9-10" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
};
const iconBtn = (ic, aria, fn) => { const b = btn('', aria, fn, 'dcu-ic'); b.innerHTML = ICON[ic]; return b };
const bEraser = iconBtn('eraser', tr('Ластик (E)'), () => setEraser(!ink.eraser));
penBar.append(...swatches, h('span', { class: 'dcu-hr' }), ...sizes, h('span', { class: 'dcu-hr' }), bEraser,
  iconBtn('undo', tr('Отменить штрих (Z)'), undoInk), iconBtn('clear', tr('Стереть всё на слайде (C)'), clearInk), iconBtn('done', tr('Закончить рисование (D, Esc)'), () => pen(false)));
L.append(penBar);
function markPen() {
  swatches.forEach((b, k) => b.setAttribute('aria-pressed', String(!ink.eraser && PEN[k] === ink.color)));
  sizes.forEach(b => b.setAttribute('aria-pressed', String(+b.dataset.w === ink.size)));
  bEraser.setAttribute('aria-pressed', String(ink.eraser));
  cv.classList.toggle('dcu-erasing', ink.eraser);
}
function setEraser(on) { ink.eraser = !!on; markPen() }
function pen(on) {
  on = !!on && OPT.pen !== false; if (on === st.pen) return;
  if (on && st.laser) laser(false);
  st.pen = on; lockClick(on);
  if (on) { penBar.hidden = false; void penBar.offsetWidth } // панель: hidden вне режима пера (и без ui.css)
  else setTimeout(() => { if (!st.pen) penBar.hidden = true }, DC.REDUCED ? 0 : 400);
  L.classList.toggle('dcu-pen-on', on);
  if (on) { hideTip(); hideLhl(); sizeInk(); markPen(); toast(tr('Перо: рисуйте мышью · C — стереть · Esc — выйти')) }
  hud && hud.mark();
}
// лазерная указка: красная точка со шлейфом
const lz = h('canvas', { class: 'dcu-laser', 'aria-hidden': 'true', width: 2, height: 2, style: ABS + 'width:1600px;height:900px' }), lc = lz.getContext('2d');
L.append(lz);
let lzPts = [], lzRaf = 0, lzHead = null, lzK = 0;
function laserFrame(now) {
  lzRaf = 0; if (!st.laser) { lc.setTransform(1, 0, 0, 1, 0, 0); lc.clearRect(0, 0, lz.width, lz.height); return }
  const life = 340; lzPts = lzPts.filter(p => now - p[2] < life);
  lc.setTransform(1, 0, 0, 1, 0, 0); lc.clearRect(0, 0, lz.width, lz.height); lc.setTransform(lzK, 0, 0, lzK, 0, 0);
  lc.lineCap = lc.lineJoin = 'round';
  for (let i = 1; i < lzPts.length; i++) {
    const a = lzPts[i - 1], b = lzPts[i], f = 1 - (now - b[2]) / life;
    lc.strokeStyle = OPT.laserColor; lc.globalAlpha = .55 * f; lc.lineWidth = 2 + 9 * f;
    lc.beginPath(); lc.moveTo(a[0], a[1]); lc.lineTo(b[0], b[1]); lc.stroke();
  }
  if (lzHead) {
    lc.globalAlpha = 1; lc.shadowColor = OPT.laserColor; lc.shadowBlur = 18; lc.fillStyle = OPT.laserColor;
    lc.beginPath(); lc.arc(lzHead[0], lzHead[1], 7.5, 0, 2 * Math.PI); lc.fill();
    lc.shadowBlur = 0; lc.fillStyle = '#ffffff'; lc.globalAlpha = .85; lc.beginPath(); lc.arc(lzHead[0] - 1.5, lzHead[1] - 1.5, 2.4, 0, 2 * Math.PI); lc.fill();
  }
  lc.globalAlpha = 1; lzRaf = requestAnimationFrame(laserFrame);
}
addEventListener('pointermove', e => {
  if (!st.laser) return;
  const [x, y] = toStage(e.clientX, e.clientY);
  if (x < -20 || y < -20 || x > 1620 || y > 920) { lzHead = null; return }
  lzHead = [x, y]; lzPts.push([x, y, performance.now()]); if (lzPts.length > 80) lzPts.shift();
}, { passive: true });
function laser(on) {
  on = !!on && OPT.laser !== false; if (on === st.laser) return;
  if (on && st.pen) pen(false);
  st.laser = on; lockClick(on); stage.classList.toggle('dcu-laser-on', on);
  if (on) { lzK = Math.min(2, (devicePixelRatio || 1) * Math.max(1, DC.scale || 1)); lz.width = Math.round(1600 * lzK); lz.height = Math.round(900 * lzK); lzPts = []; lzHead = null; if (!lzRaf) lzRaf = requestAnimationFrame(laserFrame); toast(tr('Указка: L — выключить')) }
  hud && hud.mark();
}

/* ---------- окно браузера: прогресс, HUD, заметки, номер, тосты, чёрный экран ---------- */
let prog = null;
if (OPT.progress !== false && !PRESENTER) {
  const bar = h('i'), el = h('div', { class: 'dcu-prog', role: 'progressbar', 'aria-label': tr('Прогресс показа'), 'aria-valuemin': 1, 'aria-valuemax': N }, bar);
  SECS.forEach(s => { if (s.slides[0] > 0) el.append(h('s', { style: `left:${(s.slides[0] / N * 100).toFixed(3)}%` })) });
  V.append(el);
  prog = { update(i) { bar.style.width = ((i + 1) / N * 100).toFixed(3) + '%'; el.setAttribute('aria-valuenow', i + 1); el.setAttribute('aria-valuetext', tr('Слайд {0} из {1}', i + 1, N)) } };
}
const notesTxt = h('div', { class: 'dcu-notes-t' });
const notesEl = h('aside', { class: 'dcu-notes', 'aria-label': tr('Заметки докладчика'), hidden: true }, h('b', {}, tr('Заметки докладчика')), notesTxt);
if (!PRESENTER) V.append(notesEl);
function notesUpd(i) { const t = (D.slides[i] && D.slides[i].notes) || ''; notesTxt.textContent = t || tr('— к этому слайду заметок нет —'); notesTxt.classList.toggle('dcu-empty', !t) }
function toggleNotes(on) {
  if (PRESENTER) return;
  st.notes = on === undefined ? !st.notes : !!on;
  if (st.notes) { notesEl.hidden = false; void notesEl.offsetWidth; notesEl.classList.add('dcu-show') }
  else { notesEl.classList.remove('dcu-show'); setTimeout(() => { if (!st.notes) notesEl.hidden = true }, DC.REDUCED ? 0 : 320) }
  hud && hud.mark();
}
const gotoEl = h('div', { class: 'dcu-goto', role: 'status', 'aria-live': 'assertive', hidden: true });
V.append(gotoEl);
let gotoT = 0;
function showGoto() {
  const n = parseInt(st.goto, 10), ok = n >= 1 && n <= N;
  gotoEl.replaceChildren(h('span', {}, tr('Слайд №')), h('b', {}, st.goto, h('i', { class: 'dcu-caret' })), h('em', {}, ok ? short(title(n - 1), 36) : tr('нет такого (1–{0})', N)), h('small', {}, tr('Enter — перейти · Esc — отмена')));
  gotoEl.hidden = false;
}
function gotoDigit(d) { st.goto = (st.goto + d).replace(/^0+/, '').slice(0, 4); if (!st.goto) return; showGoto(); clearTimeout(gotoT); gotoT = setTimeout(cancelGoto, 4000) }
function cancelGoto() { st.goto = ''; gotoEl.hidden = true; clearTimeout(gotoT) }
function commitGoto() { const n = parseInt(st.goto, 10); cancelGoto(); if (n >= 1 && n <= N) DC.go(n - 1); else toast(tr('Нет слайда {0}', n)) }
const toastEl = h('div', { class: 'dcu-toast', role: 'status', 'aria-live': 'polite', hidden: true });
V.append(toastEl);
let toastT = 0;
function toast(msg) { toastEl.textContent = msg; toastEl.hidden = false; toastEl.classList.remove('dcu-show'); void toastEl.offsetWidth; toastEl.classList.add('dcu-show'); clearTimeout(toastT); toastT = setTimeout(() => { toastEl.classList.remove('dcu-show'); setTimeout(() => { toastEl.hidden = true }, 300) }, 2200) }
UI.toast = toast;
const blackEl = h('div', { class: 'dcu-black', 'aria-hidden': 'true' });
blackEl.addEventListener('click', () => black(false));
V.append(blackEl);
function black(on) {
  st.black = !!on;
  if (!PRESENTER) blackEl.classList.toggle('dcu-show', st.black); // у докладчика гаснет только окно показа
  pres && pres.black(st.black);
  if (!remote) send({ t: 'black', on: st.black });
}
function fullscreen() {
  try {
    if (!document.fullscreenElement) { const p = document.documentElement.requestFullscreen && document.documentElement.requestFullscreen(); if (p && p.catch) p.catch(() => toast(tr('Полный экран недоступен'))) }
    else document.exitFullscreen();
  } catch (e) { toast(tr('Полный экран недоступен')) }
}

let hud = null;
function buildHud() {
  const pos = OPT.hudPos || (menu && OPT.menu === 'stamp' ? 'left' : 'right');
  const num = h('b', {}, '1'), steps = h('span', { class: 'dcu-steps', 'aria-hidden': 'true' });
  const bNum = btn([num, h('span', {}, ' / ' + N)], tr('Номер слайда — обзор (O)'), () => overview(true), 'dcu-num');
  const bNotes = btn(tr('Заметки'), tr('Заметки (N)'), () => toggleNotes(), '', { 'aria-pressed': 'false' });
  const bOv = btn(tr('Обзор'), tr('Обзор слайдов (O, Esc)'), () => overview(true));
  const bPres = OPT.presenter !== false ? btn(tr('Докладчик'), tr('Окно докладчика (P)'), openPresenter, 'dcu-hide-s') : null;
  const bPen = OPT.pen !== false ? btn(tr('Перо'), tr('Перо (D)'), () => pen(!st.pen), 'dcu-hide-s', { 'aria-pressed': 'false' }) : null;
  const bLz = OPT.laser !== false ? btn(tr('Указка'), tr('Лазерная указка (L)'), () => laser(!st.laser), 'dcu-hide-s', { 'aria-pressed': 'false' }) : null;
  const bFs = btn(tr('Экран'), tr('Полный экран (F)'), fullscreen, '', { 'aria-pressed': 'false' });
  const bar = h('div', { class: 'dcu-hud dcu-' + pos, role: 'toolbar', 'aria-label': tr('Управление показом') },
    btn('←', tr('Назад (←)'), () => DC.prev(), 'dcu-arrow'), bNum, steps, btn('→', tr('Вперёд (→, пробел)'), () => DC.next(), 'dcu-arrow'),
    h('span', { class: 'dcu-sep' }), bNotes, bOv, bPres, bPen, bLz, h('span', { class: 'dcu-sep dcu-hide-s' }),
    btn('PDF', tr('Печать / PDF'), printDeck, 'dcu-hide-s'), bFs, btn('?', tr('Клавиши (?)'), () => help(true), 'dcu-q'));
  V.append(bar);
  addEventListener('fullscreenchange', () => bFs.setAttribute('aria-pressed', String(!!document.fullscreenElement)));
  return {
    el: bar,
    update(i) { num.textContent = String(i + 1); this.steps(i) },
    steps(i) { const n = stepsOf(i), d = stepsDone(i); steps.replaceChildren(...Array.from({ length: n }, (_, k) => h('i', { class: k < d ? 'dcu-done' : '' }))); steps.hidden = !n },
    mark() { bNotes.setAttribute('aria-pressed', String(st.notes)); bPen && bPen.setAttribute('aria-pressed', String(st.pen)); bLz && bLz.setAttribute('aria-pressed', String(st.laser)) },
  };
}
if (OPT.hud !== false && !PRESENTER && CSS_OK) hud = buildHud();
// бездействие: HUD и курсор прячутся, движение мыши возвращает
let idleT = 0;
function wake() {
  document.body.classList.remove('dcu-idle'); clearTimeout(idleT);
  idleT = setTimeout(() => { if (hud && (hud.el.matches(':hover') || hud.el.contains(document.activeElement))) return wake(); if (!PRESENTER) document.body.classList.add('dcu-idle') }, OPT.idle);
}
addEventListener('pointermove', wake, { passive: true }); addEventListener('pointerdown', wake, { passive: true });
if (!PRESENTER) document.body.classList.add('dcu-idle'); // до первого движения мыши HUD не мешает (и не попадает в снимки)

/* ---------- обзор ---------- */
let ov = null, ovThumbs = [], ovSel = 0, ovSig = '', ovFocus = null;
function thumb(i) { const s = DC.renderStatic(i); s.removeAttribute('style'); s.setAttribute('aria-hidden', 'true'); s.setAttribute('focusable', 'false'); s.setAttribute('preserveAspectRatio', 'xMidYMid slice'); return s }
function buildOv() {
  ov = h('div', { class: 'dcu-ov', role: 'dialog', 'aria-modal': 'true', 'aria-label': tr('Обзор слайдов'), hidden: true });
  const head = h('div', { class: 'dcu-ov-head' },
    h('div', { class: 'dcu-ov-title' }, D.title || tr('Презентация'), h('span', {}, tr(' · {0} {1}', N, plural(N, tr('слайд'), tr('слайда'), tr('слайдов'))))),
    h('div', { class: 'dcu-ov-hint' }, tr('← → ↑ ↓ — выбор · Enter — открыть · Esc — закрыть')),
    btn('×', tr('Закрыть обзор (Esc)'), () => overview(false), 'dcu-x'));
  ov.append(head);
  const groups = []; let g = null;
  for (let i = 0; i < N; i++) { const k = secOf(i); if (!g || g.k !== k) { g = { k, items: [] }; groups.push(g) } g.items.push(i) }
  for (const gr of groups) {
    const grid = h('div', { class: 'dcu-ov-grid' });
    const sec = h('section', { class: 'dcu-ov-sec' }, gr.k >= 0 ? h('h3', {}, h('b', {}, pad2(gr.k + 1)), SECS[gr.k].title) : h('h3', {}, tr('Без раздела')), grid);
    for (const i of gr.items) {
      const b = h('button', { type: 'button', class: 'dcu-th', 'data-i': i, 'aria-label': tr('Слайд {0}: {1}', i + 1, title(i)) },
        h('div', { class: 'dcu-th-img' }), h('div', { class: 'dcu-th-cap' }, h('b', {}, pad2(i + 1)), h('span', {}, title(i))));
      b.addEventListener('click', e => { e.stopPropagation(); ovOpen(i) });
      b.addEventListener('focus', () => ovMark(i, false));
      grid.append(b); ovThumbs[i] = b;
    }
    ov.append(sec);
  }
  ov.addEventListener('click', e => { if (e.target === ov) overview(false) });
  V.append(ov);
}
function ovFill() { const sig = JSON.stringify(DC.state); if (sig === ovSig) return; ovSig = sig; ovThumbs.forEach((b, i) => b.firstChild.replaceChildren(thumb(i))) }
function ovMark(i, focus) {
  ovSel = Math.max(0, Math.min(N - 1, i));
  ovThumbs.forEach((b, j) => { b.classList.toggle('dcu-sel', j === ovSel); b.classList.toggle('dcu-cur', j === DC.cur); if (j === DC.cur) b.setAttribute('aria-current', 'true'); else b.removeAttribute('aria-current') });
  if (focus) { const b = ovThumbs[ovSel]; b.focus({ preventScroll: true }); b.scrollIntoView({ block: 'nearest', behavior: DC.REDUCED ? 'auto' : 'smooth' }) }
}
function overview(on) {
  on = !!on; if (on === st.ov) return;
  if (on) {
    if (!ov) buildOv();
    if (st.help) help(false); if (st.pen) pen(false); hideTip(); hideLhl(); cancelGoto();
    ovFocus = document.activeElement; ovFill(); ov.hidden = false; st.ov = true;
    void ov.offsetWidth; ov.classList.add('dcu-show'); ovMark(DC.cur, true);
    const b = ovThumbs[DC.cur]; b && b.scrollIntoView({ block: 'center' });
  } else {
    st.ov = false; ov.classList.remove('dcu-show');
    setTimeout(() => { if (!st.ov) ov.hidden = true }, DC.REDUCED ? 0 : 260);
    if (ovFocus && ovFocus.focus && document.contains(ovFocus)) try { ovFocus.focus({ preventScroll: true }) } catch (e) { }
  }
}
function ovOpen(i) { overview(false); pointOf(null); if (i !== DC.cur) DC.go(i) }
function ovMove(dx, dy) {
  if (dx) return ovMark(ovSel + dx, true);
  const a = ovThumbs[ovSel].getBoundingClientRect(), ax = a.left + a.width / 2, ay = a.top + a.height / 2;
  let best = -1, bd = Infinity;
  ovThumbs.forEach((b, j) => {
    const r = b.getBoundingClientRect(), y = r.top + r.height / 2, x = r.left + r.width / 2;
    if (dy > 0 ? y <= ay + 4 : y >= ay - 4) return;
    const d = Math.abs(y - ay) * 3 + Math.abs(x - ax); if (d < bd) { bd = d; best = j }
  });
  if (best >= 0) ovMark(best, true);
}
function ovKey(e) {
  const k = e.key, code = e.code;
  const map = { ArrowRight: () => ovMove(1, 0), ArrowLeft: () => ovMove(-1, 0), ArrowDown: () => ovMove(0, 1), ArrowUp: () => ovMove(0, -1),
    Home: () => ovMark(0, true), End: () => ovMark(N - 1, true), Enter: () => ovOpen(ovSel), ' ': () => ovOpen(ovSel), Escape: () => overview(false) };
  if (map[k]) { e.preventDefault(); e.stopPropagation(); map[k](); return }
  if (code === 'KeyO' || k === 'o' || k === 'O' || k === 'щ' || k === 'Щ') { e.preventDefault(); e.stopPropagation(); overview(false); return }
  if (k === 'Tab') return;
  e.stopPropagation(); // остальное не листает слайды под обзором
}

/* ---------- справка ---------- */
let helpEl = null, helpFocus = null;
const KEYS = [
  [tr('→ · Пробел · PgDn'), tr('дальше: шаг или слайд')], ['← · PgUp', tr('назад')], ['Home · End', tr('первый · последний слайд')],
  [tr('цифры + Enter'), tr('перейти к слайду по номеру')], ['Backspace', tr('вернуться туда, откуда пришли по ссылке')],
  ['O · Esc', tr('обзор всех слайдов')], ['N', tr('заметки-стикер')], ['P', tr('окно докладчика')],
  ['D', tr('перо (C — стереть, E — ластик, Z — отменить)')], ['L', tr('лазерная указка')], ['B · .', tr('чёрный экран')],
  ['F', tr('полный экран')], ['?', tr('эта справка')], [tr('свайп'), tr('листать на сенсорном экране')],
];
function help(on) {
  on = !!on; if (on === st.help) return;
  if (on && !helpEl) {
    const list = h('dl', { class: 'dcu-keys' }); for (const [k, d] of KEYS) list.append(h('dt', {}, ...k.split(' · ').flatMap((x, j) => j ? [' ', h('kbd', {}, x)] : [h('kbd', {}, x)])), h('dd', {}, d));
    helpEl = h('div', { class: 'dcu-help', role: 'dialog', 'aria-modal': 'true', 'aria-label': tr('Клавиши'), hidden: true },
      h('div', { class: 'dcu-help-card' }, h('div', { class: 'dcu-help-head' }, h('h2', {}, tr('Клавиши показа')), btn('×', tr('Закрыть справку (Esc)'), () => help(false), 'dcu-x')), list,
        h('p', { class: 'dcu-help-foot' }, tr('Клик по объекту с рамкой — переход по ссылке; наведение — подсказка. Буквы работают и в русской раскладке.'))));
    helpEl.addEventListener('click', e => { if (e.target === helpEl) help(false) });
    V.append(helpEl);
  }
  st.help = on;
  if (on) { helpFocus = document.activeElement; helpEl.hidden = false; void helpEl.offsetWidth; helpEl.classList.add('dcu-show'); helpEl.querySelector('.dcu-x').focus({ preventScroll: true }) }
  else if (helpEl) { helpEl.classList.remove('dcu-show'); helpEl.hidden = true; if (helpFocus && helpFocus.focus && document.contains(helpFocus)) try { helpFocus.focus({ preventScroll: true }) } catch (e) { } }
}

/* ---------- печать / PDF ---------- */
function inkImage(i) { // рисунок пера поверх страницы печати
  const a = ink.strokes[i]; if (!a || !a.length) return null;
  const c0 = h('canvas', { width: 1600, height: 900 }), g = c0.getContext('2d');
  for (const s of a) {
    const p = s.p; g.save(); g.globalCompositeOperation = s.e ? 'destination-out' : 'source-over';
    g.strokeStyle = s.c; g.lineWidth = s.w; g.lineCap = g.lineJoin = 'round'; g.beginPath(); g.moveTo(p[0], p[1]);
    for (let k = 2; k < p.length; k += 2) g.lineTo(p[k], p[k + 1]);
    if (p.length === 2) g.lineTo(p[0] + .01, p[1]);
    g.stroke(); g.restore();
  }
  return h('img', { src: c0.toDataURL('image/png'), alt: '' });
}
function printPrepare() {
  if (document.getElementById('dcu-print')) return;
  const box = h('div', { id: 'dcu-print', 'aria-hidden': 'true' });
  for (let i = 0; i < N; i++) {
    const s = DC.renderStatic(i); s.removeAttribute('style'); s.setAttribute('width', '1600'); s.setAttribute('height', '900');
    box.append(h('section', { class: 'dcu-page' }, s, inkImage(i)));
    const nt = D.slides[i].notes;
    if (OPT.printNotes && nt) box.append(h('section', { class: 'dcu-page dcu-npage' }, h('div', { class: 'dcu-np-n' }, `${pad2(i + 1)} · ${title(i)}`), h('div', { class: 'dcu-np-t' }, nt)));
  }
  document.body.append(box);
}
function printDone() { const b = document.getElementById('dcu-print'); b && b.remove() }
function printDeck() { printPrepare(); setTimeout(() => { try { window.print() } catch (e) { } }, 40) }
addEventListener('beforeprint', printPrepare);
addEventListener('afterprint', printDone);
try { const mq = matchMedia('print'); const f = e => { if (e.matches) printPrepare() }; mq.addEventListener ? mq.addEventListener('change', f) : mq.addListener(f) } catch (e) { }
Object.assign(UI, { printPrepare, printDone });

/* ---------- связь окон: показ ↔ докладчик ---------- */
const CH = 'deckcraft:' + location.pathname + '|' + (D.title || '');
const SRC = (PRESENTER ? 'p' : 'm') + Math.random().toString(36).slice(2, 9);
let bc = null, seq = 0, presWin = null;
const seen = new Set();
try { bc = new BroadcastChannel(CH) } catch (e) { bc = null }
function send(m) {
  m.ch = CH; m.src = SRC; m.id = SRC + ':' + (++seq);
  try { bc && bc.postMessage(m) } catch (e) { }
  try { if (presWin && !presWin.closed) presWin.postMessage(m, '*') } catch (e) { }
  try { if (window.opener && !window.opener.closed) window.opener.postMessage(m, '*') } catch (e) { }
}
function sendInk(i) { if (!remote) send({ t: 'ink', i, s: ink.strokes[i] || [] }) }
function syncTo(i, k) {
  const n = stepsOf(i);
  if (DC.cur !== i) DC.go(i, k >= n && n > 0 && i < DC.cur ? { steps: 'all' } : {});
  const sl = D.slides[i]; let guard = 64;
  while (sl.stepT.length < Math.min(k, n) && guard--) DC.next();
  while (sl.stepT.length > k && guard--) DC.prev();
}
function recv(m) {
  if (!m || m.ch !== CH || m.src === SRC || seen.has(m.id)) return;
  seen.add(m.id); if (seen.size > 400) seen.clear();
  remote = true;
  try {
    if (m.t === 'pos') { quiet = false; syncTo(m.i, m.k) }
    else if (m.t === 'hello' && !PRESENTER) { send({ t: 'pos', i: DC.cur, k: stepsDone(DC.cur) }); send({ t: 'state', s: Object.assign({}, DC.state) }); send({ t: 'inkAll', s: ink.strokes }); if (st.black) send({ t: 'black', on: true }) }
    else if (m.t === 'state') { for (const k in m.s) if (DC.state[k] !== m.s[k]) (DC.setState ? DC.setState(k, m.s[k]) : (DC.state[k] = m.s[k])) }
    else if (m.t === 'ink') { ink.strokes[m.i] = m.s; if (m.i === DC.cur) redrawInk() }
    else if (m.t === 'inkAll') { ink.strokes = m.s || {}; redrawInk() }
    else if (m.t === 'black') black(m.on);
  } catch (e) { console.error(e) } finally { remote = false }
}
if (bc) bc.onmessage = e => recv(e.data);
addEventListener('message', e => { if (e.data && e.data.ch === CH) recv(e.data) });
function openPresenter() {
  if (PRESENTER || OPT.presenter === false) return;
  if (presWin && !presWin.closed) { presWin.focus(); return }
  const u = new URL(location.href); u.hash = '#s' + (DC.cur + 1); u.searchParams.set('presenter', '1');
  try { presWin = window.open(u.href, 'dcu-presenter', 'popup,width=1280,height=780') } catch (e) { presWin = null }
  toast(presWin ? tr('Окно докладчика открыто — листать можно из любого окна') : tr('Браузер не дал открыть окно: разрешите всплывающие окна для этой страницы'));
}
UI.openPresenter = openPresenter;

/* ---------- окно докладчика (?presenter) ---------- */
let pres = null;
function buildPresenter() {
  document.body.classList.add('dcu-presenter');
  document.title = tr('Докладчик · ') + (D.title || document.title);
  const tEl = h('b', { class: 'dcu-pv-time' }, '0:00'), clock = h('span', { class: 'dcu-pv-clock' }, '');
  let t0 = performance.now(), acc = 0, run = true;
  const elapsed = () => acc + (run ? performance.now() - t0 : 0);
  const bPause = btn(tr('Пауза'), tr('Пауза / продолжить таймер'), () => { if (run) { acc += performance.now() - t0; run = false } else { t0 = performance.now(); run = true } bPause.textContent = run ? tr('Пауза') : tr('Дальше'); bPause.setAttribute('aria-pressed', String(!run)); tick() }, '', { 'aria-pressed': 'false' });
  const bReset = btn(tr('Сброс'), tr('Сбросить таймер'), () => { acc = 0; t0 = performance.now(); tick() });
  const where = h('div', { class: 'dcu-pv-where' }), count = h('div', { class: 'dcu-pv-count' });
  const curBox = h('div', { class: 'dcu-pv-cur', 'aria-label': tr('Текущий слайд') });
  const nextBox = h('div', { class: 'dcu-pv-next' }), nextCap = h('div', { class: 'dcu-pv-cap' });
  const notes = h('div', { class: 'dcu-pv-notes-t' });
  let fs = 30; try { fs = +localStorage.getItem('dcu-pv-fs') || 30 } catch (e) { }
  const setFs = v => { fs = Math.max(16, Math.min(64, v)); notes.style.fontSize = fs + 'px'; try { localStorage.setItem('dcu-pv-fs', fs) } catch (e) { } };
  setFs(fs);
  const stepInfo = h('div', { class: 'dcu-pv-step' });
  const bBlack = btn(tr('Чёрный экран'), tr('Чёрный экран в окне показа (B)'), () => black(!st.black), '', { 'aria-pressed': 'false' });
  const pv = h('div', { id: 'dcu-pv' },
    h('header', { class: 'dcu-pv-top' }, h('div', { class: 'dcu-pv-deck' }, D.title || tr('Презентация')), where, count,
      h('div', { class: 'dcu-pv-timer', role: 'timer', 'aria-label': tr('Время доклада') }, tEl, bPause, bReset), clock),
    curBox,
    h('section', { class: 'dcu-pv-side', 'aria-label': tr('Следующий слайд') }, h('div', { class: 'dcu-pv-lbl' }, tr('Далее')), nextBox, nextCap),
    h('section', { class: 'dcu-pv-notes', 'aria-label': tr('Заметки') }, h('div', { class: 'dcu-pv-lbl' }, tr('Заметки'), h('span', { class: 'dcu-pv-fs' }, btn('A−', tr('Мельче'), () => setFs(fs - 2)), btn('A+', tr('Крупнее'), () => setFs(fs + 2)))), notes),
    h('section', { class: 'dcu-pv-ctrl', 'aria-label': tr('Управление') }, btn('←', tr('Назад (←)'), () => DC.prev(), 'dcu-big'), btn('→', tr('Вперёд (→)'), () => DC.next(), 'dcu-big'), stepInfo,
      btn(tr('Обзор'), tr('Обзор слайдов (O)'), () => overview(true)), btn(tr('Перо'), tr('Перо (D) — рисунок появится и в окне показа'), () => pen(!st.pen)), bBlack));
  document.body.append(pv);
  function tick() {
    const s = Math.floor(elapsed() / 1000), hh = Math.floor(s / 3600), mm = Math.floor(s / 60) % 60, ss = s % 60;
    tEl.textContent = (hh ? hh + ':' + pad2(mm) : mm) + ':' + pad2(ss); tEl.classList.toggle('dcu-paused', !run);
    const d = new Date(); clock.textContent = pad2(d.getHours()) + ':' + pad2(d.getMinutes()) + ':' + pad2(d.getSeconds());
  }
  setInterval(tick, 250); tick();
  function layout() {
    const r = curBox.getBoundingClientRect(), k = Math.min(r.width / 1600, r.height / 900);
    root.style.setProperty('--dcu-ps', k.toFixed(5));
    root.style.setProperty('--dcu-px', (r.left + (r.width - 1600 * k) / 2).toFixed(1) + 'px');
    root.style.setProperty('--dcu-py', (r.top + (r.height - 900 * k) / 2).toFixed(1) + 'px');
  }
  addEventListener('resize', layout); layout(); requestAnimationFrame(layout);
  const cache = {};
  const still = i => { const sig = i + '|' + JSON.stringify(DC.state); if (!cache[sig]) cache[sig] = thumb(i); return cache[sig] };
  return {
    update(i) {
      const k = secOf(i), n = stepsOf(i), d = stepsDone(i);
      where.replaceChildren(k >= 0 ? h('span', {}, SECS[k].title) : '', k >= 0 ? ' · ' : '', h('b', {}, title(i)));
      count.replaceChildren(h('b', {}, String(i + 1)), ` / ${N}`);
      stepInfo.textContent = n ? tr('шаг {0} из {1}', d, n) : '';
      if (d < n) { nextBox.replaceChildren(still(i)); nextCap.textContent = tr('Этот же слайд, шаг {0} из {1}', d + 1, n) }
      else if (i + 1 < N) { nextBox.replaceChildren(still(i + 1)); nextCap.textContent = `${i + 2}. ${title(i + 1)}` }
      else { nextBox.replaceChildren(h('div', { class: 'dcu-pv-end' }, tr('Конец'))); nextCap.textContent = tr('Последний слайд') }
      const t = D.slides[i].notes || '';
      notes.textContent = t || tr('— к этому слайду заметок нет —'); notes.classList.toggle('dcu-empty', !t); notes.scrollTop = 0;
    },
    layout,
    black(on) { bBlack.setAttribute('aria-pressed', String(on)) },
  };
}
if (PRESENTER) pres = buildPresenter();

/* ---------- события ядра ---------- */
DC.on('slide', (i, from) => {
  cur = i;
  menu && menu.update(i); hud && hud.update(i); prog && prog.update(i); pres && pres.update(i);
  updBack(); notesUpd(i); hideTip(); hideLhl(); cancelGoto();
  L.classList.toggle('dcu-dark', OPT.theme === 'dark' || (OPT.theme !== 'light' && isDark(i)));
  if (!ires && Object.keys(ink.strokes).length) sizeInk(); redrawInk();
  if (st.ov) ovMark(i, false);
  sr.textContent = tr('Слайд {0} из {1}. {2}', i + 1, N, title(i));
  if (!remote && !quiet) send({ t: 'pos', i, k: stepsDone(i) });
  void from;
});
DC.on('step', (i, n) => { hud && hud.steps(i); pres && pres.update(i); if (!remote && !quiet) send({ t: 'pos', i, k: n }) });
DC.on('state', s => { if (!remote) send({ t: 'state', s: Object.assign({}, s) }); if (lhlNode) showLhl(lhlNode); ovSig = '' });
addEventListener('resize', () => { menu && menu.relayout && menu.relayout(); if (ires) { ires = 0; sizeInk() } });
if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => menu && menu.relayout && menu.relayout());
if (st.notes) setTimeout(() => toggleNotes(true), 0);
if (PRESENTER) DC.on('ready', () => setTimeout(() => { send({ t: 'hello' }); setTimeout(() => { quiet = false }, 1200) }, 0));

/* ---------- клавиши ---------- */
function onEsc() {
  if (st.help) return help(false);
  if (st.goto) return cancelGoto();
  if (st.pen) return pen(false);
  if (st.laser) return laser(false);
  if (st.black) return black(false);
  overview(true);
}
const K = (list, fn) => { for (const k of list) DC.keys[k] = fn };
K(['o', 'O', 'щ', 'Щ'], () => overview(!st.ov));
K(['Escape'], onEsc);
K(['n', 'N', 'т', 'Т'], () => toggleNotes());
K(['f', 'F', 'а', 'А'], fullscreen);
K(['p', 'P', 'з', 'З'], openPresenter);
K(['d', 'D', 'в', 'В'], () => pen(!st.pen));
K(['l', 'L', 'д', 'Д'], () => laser(!st.laser));
K(['c', 'C', 'с', 'С'], clearInk);
K(['e', 'E', 'у', 'У'], () => { if (st.pen) setEraser(!ink.eraser) });
K(['z', 'Z', 'я', 'Я'], () => { if (st.pen || (ink.strokes[DC.cur] || []).length) undoInk() });
K(['b', 'B', 'и', 'И', '.', 'ю', 'Ю'], () => black(!st.black));
K(['?', 'h', 'H', 'р', 'Р', 'F1'], () => help(!st.help));
for (let d = 0; d <= 9; d++) DC.keys[String(d)] = () => gotoDigit(d);
addEventListener('keydown', e => {
  const t = e.target, k = e.key;
  if (t && t.closest && t.closest('input,textarea,select,[contenteditable]')) return;
  if (e.ctrlKey || e.metaKey || e.altKey) {
    if ((e.ctrlKey || e.metaKey) && !e.altKey && (k === 'z' || k === 'я') && (ink.strokes[DC.cur] || []).length) { e.preventDefault(); e.stopPropagation(); undoInk(); return }
    if (k.length === 1) e.stopPropagation(); // Ctrl+P, Ctrl+R … — браузеру, а не клавишам показа
    return;
  }
  if (st.help) { e.stopPropagation(); if (k === 'Escape' || k === '?' || e.code === 'KeyH') { e.preventDefault(); help(false) } else if (k === 'Enter' || k === ' ') return; else if (k !== 'Tab') e.preventDefault(); return }
  if (st.ov) return ovKey(e);
  if (st.goto) {
    if (k === 'Enter') { e.preventDefault(); e.stopPropagation(); commitGoto(); return }
    if (k === 'Backspace') { e.preventDefault(); e.stopPropagation(); st.goto = st.goto.slice(0, -1); st.goto ? showGoto() : cancelGoto(); return }
    if (k === 'Escape') { e.preventDefault(); e.stopPropagation(); cancelGoto(); return }
  }
  if ((k === 'Enter' || k === ' ') && t && t.closest) {
    const lk = t.closest('.dc-link');
    if (lk) { e.preventDefault(); e.stopPropagation(); lk.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })); return }
    if (t.closest('button, a[href], summary')) { e.stopPropagation(); return } // кнопка нажимается сама, слайд не листается
  }
}, true);

Object.assign(UI, { overview, help, notes: toggleNotes, pen, laser, black, fullscreen, goto: n => DC.go(n - 1), clearInk, undoInk, state: st, sections: SECS });
})();
