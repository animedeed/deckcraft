/* deckcraft web — листы-переходы (sheets.js, 0.3.0).
 * DC.sheets[k] = (p, A, B, ctx): A — <svg>-снимок прежнего кадра (поверх), B — живой <svg> нового слайда (под ним).
 * Лист меняет только style у A и B (transform, clip-path, opacity, filter, z-index, 3D — у #dc-stage есть perspective);
 * если нужны временные элементы (вторая половина листа, тень загиба, кольцо диафрагмы, створки), они кладутся в
 * #dc-stage и убираются сами, как только ядро удалит A (события frame / slide). Ядро после листа удаляет A и
 * сбрасывает B.style — это не трогаем.
 * Обратный ход (ctx.to < ctx.from или opt.rev = true) — то же движение, проигранное назад с переменой ролей A и B
 * (лист «уезжает обратно»); dissolve, glitch и shutter симметричны и не разворачиваются.
 * Параметры — из opt (Python: web(s, sheet={"k": "iris", "dur": 900, "x": .3, "y": .5})); координаты x, y — доли
 * сцены (0..1) или px; без них iris/diamond/ink/zoomThrough берут центр объекта-ссылки, по которой перешли, иначе
 * центр сцены. Всё детерминировано (DC.u.rng), цвета — роли DC.data.colors или #hex. */
'use strict';
(function () {
const DC = window.DC;
if (!DC || !DC.sheets) return;
const S = DC.sheets, W = 1600, H = 900, NS = 'http://www.w3.org/2000/svg';
const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const lerp = (a, b, t) => a + (b - a) * t;
const sstep = (a, b, x) => { const t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t) };
const ez = k => (k && DC.ease[k]) || DC.ease.inOut;
const color = (v, d) => { const C = DC.data.colors || {}; return v ? (C[v] || v) : d };
const f1 = v => (+v).toFixed(1), f3 = v => (+v).toFixed(3);
const poly = pts => pts.length >= 3 ? 'polygon(' + pts.map(p => f1(p[0]) + 'px ' + f1(p[1]) + 'px').join(',') + ')' : 'polygon(0 0,0 0,0 0)';
const pathOf = pts => pts.length >= 3 ? 'M' + pts.map(p => f1(p[0]) + ' ' + f1(p[1])).join('L') + 'Z' : '';
const frac = (v, L) => Math.abs(v) <= 1 ? v * L : v;
let gid = 0;
function el(tag, a, p) { const e = document.createElementNS(NS, tag); for (const k in a) e.setAttribute(k, a[k]); p && p.appendChild(e); return e }

/* ---------- точка начала (iris, diamond, ink, zoomThrough): opt.x/y → объект-ссылка → центр ---------- */
let lastPt = null;
DC.on('link', (lk, o) => { if (o && o.w !== undefined) lastPt = { x: o.x + o.w / 2, y: o.y + o.h / 2, t: performance.now() } });
DC.sheetPoint = (x, y) => { lastPt = { x, y, t: performance.now() } }; // интерфейс: клик по меню → лист из этой точки

/* ---------- состояние одного перехода (ключ — снимок A) и уборка временных элементов ---------- */
const live = new Map();
function sweep() { if (!live.size) return; for (const [A, s] of live) if (!A.isConnected) { for (const e of s.extra) e.remove(); live.delete(A) } }
DC.on('frame', sweep);
DC.on('slide', sweep);
function state(A, ctx) {
  let s = live.get(A);
  if (s) return s;
  const o = ctx.opt || {};
  const back = o.rev !== undefined ? !!o.rev : (ctx.from !== null && ctx.from !== undefined && ctx.to < ctx.from);
  let pt = null;
  if (o.x !== undefined || o.y !== undefined) pt = { x: frac(o.x ?? .5, W), y: frac(o.y ?? .5, H) };
  else if (lastPt && performance.now() - lastPt.t < 900) pt = { x: lastPt.x, y: lastPt.y };
  s = { A, back, pt: pt || { x: W / 2, y: H / 2 }, extra: [], stage: ctx.stage, mem: {} };
  live.set(A, s);
  return s;
}
function extra(s, tag, css) { // временный элемент поверх сцены; удаляется вместе с A
  const e = tag === 'svg' ? document.createElementNS(NS, 'svg') : document.createElement(tag);
  if (tag === 'svg') { e.setAttribute('viewBox', `0 0 ${W} ${H}`); e.setAttribute('width', W); e.setAttribute('height', H) }
  e.setAttribute('aria-hidden', 'true'); e.classList.add('dcs-x');
  e.style.cssText = 'position:absolute;left:0;top:0;width:1600px;height:900px;pointer-events:none;' + (css || '');
  s.stage.appendChild(e); s.extra.push(e); return e;
}
function copyOf(s, X) { // вторая половина листа: копия снимка (у живого svg — DC.snapshot с собственными id)
  const c = X.id === 'dc-svg' ? DC.snapshot() : X.cloneNode(true);
  c.removeAttribute('id'); c.classList.add('dc-snap', 'dcs-x'); c.style.cssText = ''; c.setAttribute('aria-hidden', 'true');
  s.stage.appendChild(c); s.extra.push(c); return c;
}
const zi = (top, bottom) => { top.style.zIndex = 3; bottom.style.zIndex = 1 };
const DIRS = { left: [-1, 0], right: [1, 0], up: [0, -1], down: [0, 1], l: [-1, 0], r: [1, 0], u: [0, -1], d: [0, 1] };
const dirOf = o => DIRS[o.dir] || DIRS.left; // куда движется содержимое: left — новый лист приходит справа

/* def(имя, кривая по умолчанию, fn(q, A, B, opt, s, ctx), sym): fn пишет прямой ход (A уходит, B приходит) */
function def(name, ease, fn, sym) {
  const f = (p, A, B, ctx) => {
    const o = ctx.opt || {}, s = state(A, ctx), raw = ctx.raw ?? p, rev = s.back && !sym;
    const q = ez(o.ease || ease)(rev ? 1 - raw : raw);
    if (rev) fn(q, B, A, o, s, ctx); else fn(q, A, B, o, s, ctx);
  };
  f.ease = ease; f.sym = !!sym; S[name] = f;
}

/* ---------- листы: въезд и сдвиг ---------- */
def('sheetIn', 'out', (q, A, B, o) => { // как в «Зин»: лист въезжает справа с поворотом и тенью
  const k = 1 - q, rot = o.rot ?? 6, dy = o.dy ?? 60;
  zi(B, A);
  B.style.transform = `translate(${f3(k * 104)}%, ${f1(k * dy)}px) rotate(${f3(k * rot)}deg)`;
  B.style.boxShadow = `0 26px 60px rgba(0,0,0,${o.shadow ?? .45})`;
  A.style.filter = `brightness(${f3(1 - .18 * q)})`;
});
def('sheetUp', 'out', (q, A, B, o) => { // как в «Чертеже»: лист снизу
  const k = 1 - q;
  zi(B, A);
  B.style.transform = `translateY(${f3(k * 103)}%) rotate(${f3(k * (o.rot ?? 0))}deg)`;
  B.style.boxShadow = `0 -18px 60px rgba(0,0,0,${o.shadow ?? .4})`;
  A.style.filter = `brightness(${f3(1 - .16 * q)})`;
});
def('sheetDown', 'out', (q, A, B, o) => {
  const k = 1 - q;
  zi(B, A);
  B.style.transform = `translateY(${f3(-k * 103)}%) rotate(${f3(k * (o.rot ?? 0))}deg)`;
  B.style.boxShadow = `0 18px 60px rgba(0,0,0,${o.shadow ?? .4})`;
  A.style.filter = `brightness(${f3(1 - .16 * q)})`;
});
def('push', 'inOut', (q, A, B, o) => { // A уезжает медленнее (parallax: 1 — классический толчок), B накрывает с тенью
  const [mx, my] = dirOf(o), par = o.parallax ?? .35;
  zi(B, A);
  B.style.transform = `translate(${f3(-mx * (1 - q) * 100)}%, ${f3(-my * (1 - q) * 100)}%)`;
  B.style.boxShadow = `${mx * 26}px ${my * 26}px 70px rgba(0,0,0,${f3(.42 * (1 - q * .5))})`;
  A.style.transform = `translate(${f3(mx * q * par * 100)}%, ${f3(my * q * par * 100)}%)`;
  A.style.filter = `brightness(${f3(1 - .32 * q * (1 - par))})`;
});
def('cover', 'out', (q, A, B, o) => { // B наезжает поверх неподвижного A
  const [mx, my] = dirOf(o);
  zi(B, A);
  B.style.transform = `translate(${f3(-mx * (1 - q) * 100)}%, ${f3(-my * (1 - q) * 100)}%)`;
  B.style.boxShadow = `${mx * 24}px ${my * 24}px 64px rgba(0,0,0,${o.shadow ?? .45})`;
  A.style.transform = `scale(${f3(1 - .035 * q)})`;
  A.style.filter = `brightness(${f3(1 - .26 * q)})`;
});
def('uncover', 'inOut', (q, A, B, o) => { // A уезжает и открывает B
  const [mx, my] = dirOf(o);
  zi(A, B);
  A.style.transform = `translate(${f3(mx * q * 100)}%, ${f3(my * q * 100)}%)`;
  A.style.boxShadow = `${-mx * 24}px ${-my * 24}px 64px rgba(0,0,0,${o.shadow ?? .45})`;
  B.style.transform = `scale(${f3(.965 + .035 * q)})`;
  B.style.filter = `brightness(${f3(.74 + .26 * q)})`;
});

/* ---------- 3D ---------- */
def('fold', 'inOut', (q, A, B, o, s) => { // A складывается по средней линии (две половины уходят вглубь, rotateY)
  const R = s.mem.fold || (s.mem.fold = copyOf(s, A)), th = (o.angle ?? 90) * q, z = -(o.depth ?? 260) * q;
  A.style.zIndex = R.style.zIndex = 3; B.style.zIndex = 1;
  if (o.axis === 'x') {
    A.style.clipPath = 'inset(0 0 50% 0)'; R.style.clipPath = 'inset(50% 0 0 0)';
    A.style.transform = `translateZ(${f1(z)}px) rotateX(${f3(th)}deg)`; R.style.transform = `translateZ(${f1(z)}px) rotateX(${f3(-th)}deg)`;
  } else {
    A.style.clipPath = 'inset(0 50% 0 0)'; R.style.clipPath = 'inset(0 0 0 50%)';
    A.style.transform = `translateZ(${f1(z)}px) rotateY(${f3(-th)}deg)`; R.style.transform = `translateZ(${f1(z)}px) rotateY(${f3(th)}deg)`;
  }
  A.style.filter = `brightness(${f3(1 - .55 * q)})`; R.style.filter = `brightness(${f3(1 - .32 * q)})`;
  A.style.opacity = R.style.opacity = f3(1 - sstep(.72, 1, q)); // ребро «призмы» под конец тает
  B.style.transform = `scale(${f3(.92 + .08 * q)})`; B.style.filter = `brightness(${f3(.68 + .32 * q)})`;
});
def('flip', 'inOut', (q, A, B, o) => { // карточка переворачивается (обратная сторона скрыта backface-visibility)
  const ax = o.axis === 'x' ? 'X' : 'Y', k = 1 - (o.depth ?? .16) * Math.sin(Math.PI * q);
  A.style.zIndex = 2; B.style.zIndex = 3;
  A.style.transform = `scale(${f3(k)}) rotate${ax}(${f3(-180 * q)}deg)`;
  B.style.transform = `scale(${f3(k)}) rotate${ax}(${f3(180 - 180 * q)}deg)`;
  A.style.filter = `brightness(${f3(1 - .45 * clamp(q * 2))})`;
  B.style.filter = `brightness(${f3(.55 + .45 * clamp(q * 2 - 1))})`;
});
def('cube', 'inOut', (q, A, B, o) => { // грани куба: A уходит влево, B приходит справа (axis "x" — вверх)
  const ax = o.axis === 'x' ? 'X' : 'Y', d = ax === 'Y' ? W / 2 : H / 2, sg = ax === 'Y' ? 1 : -1;
  const pull = (o.pull ?? 220) * Math.sin(Math.PI * q);
  A.style.zIndex = 2; B.style.zIndex = 3;
  A.style.transform = `translateZ(${f1(-d - pull)}px) rotate${ax}(${f3(-90 * q * sg)}deg) translateZ(${d}px)`;
  B.style.transform = `translateZ(${f1(-d - pull)}px) rotate${ax}(${f3((90 - 90 * q) * sg)}deg) translateZ(${d}px)`;
  A.style.filter = `brightness(${f3(1 - .5 * q)})`; B.style.filter = `brightness(${f3(.5 + .5 * q)})`;
});

/* ---------- формы: круг, ромб, жалюзи, занавес, пятно ---------- */
const farR = (x, y) => Math.max(Math.hypot(x, y), Math.hypot(W - x, y), Math.hypot(x, H - y), Math.hypot(W - x, H - y)) + 4;
function ring(s, o, shape) { // тонкое кольцо по краю круга/ромба (opt.ring = false — без него)
  if (o.ring === false) return null;
  if (!s.mem.ring) { const sv = extra(s, 'svg', 'z-index:4'); s.mem.ring = el(shape, { fill: 'none', stroke: color(o.color, color('accent', '#ffffff')), 'stroke-width': o.ringW ?? 5, 'stroke-linejoin': 'round' }, sv) }
  return s.mem.ring;
}
def('iris', 'inOut', (q, A, B, o, s) => { // круг из точки opt.x, opt.y
  const { x, y } = s.pt, r = farR(x, y) * q;
  zi(B, A);
  B.style.clipPath = `circle(${f1(r)}px at ${f1(x)}px ${f1(y)}px)`;
  A.style.filter = `brightness(${f3(1 - .22 * q)})`;
  const g = ring(s, o, 'circle');
  if (g) { g.setAttribute('cx', f1(x)); g.setAttribute('cy', f1(y)); g.setAttribute('r', f1(r)); g.setAttribute('stroke-opacity', f3(sstep(0, .05, q) * (1 - sstep(.62, .98, q)))) }
});
def('diamond', 'inOut', (q, A, B, o, s) => {
  const { x, y } = s.pt, R = Math.max(x + y, W - x + y, x + H - y, W - x + H - y) + 4, r = R * q;
  const pts = [[x, y - r], [x + r, y], [x, y + r], [x - r, y]];
  zi(B, A);
  B.style.clipPath = poly(pts);
  A.style.filter = `brightness(${f3(1 - .22 * q)})`;
  const g = ring(s, o, 'path');
  if (g) { g.setAttribute('d', pathOf(pts)); g.setAttribute('stroke-opacity', f3(sstep(0, .05, q) * (1 - sstep(.62, .98, q)))) }
});
def('blinds', 'linear', (q, A, B, o) => { // жалюзи: полосы раскрываются от середины каждой ламели, с запаздыванием
  const n = Math.max(2, o.n ?? 10), vert = o.dir === 'v', L = vert ? W : H, M = vert ? H : W, hh = L / n, sg = o.stagger ?? .45;
  const pts = [];
  for (let i = 0; i < n; i++) {
    const e = DC.ease.inOut(clamp(q * (1 + sg) - sg * i / (n - 1)));
    if (e <= 0) continue;
    const c = (i + .5) * hh, a = c - hh / 2 * e - (e > .98 ? 1 : 0), b = c + hh / 2 * e + (e > .98 ? 1 : 0);
    if (vert) pts.push([a, 0], [a, M], [b, M], [b, 0]); else pts.push([0, a], [M, a], [M, b], [0, b]);
  }
  zi(B, A);
  B.style.clipPath = poly(pts);
  A.style.filter = `brightness(${f3(1 - .2 * q)})`;
});
def('curtain', 'inOut', (q, A, B, o, s) => { // A раздвигается из центра двумя полотнищами, они уходят вглубь
  const R = s.mem.cur || (s.mem.cur = copyOf(s, A)), sw = o.swing ?? 24, k = (o.open ?? 54) * q;
  A.style.zIndex = R.style.zIndex = 3; B.style.zIndex = 1;
  A.style.clipPath = 'inset(0 50% 0 0)'; R.style.clipPath = 'inset(0 0 0 50%)';
  A.style.transformOrigin = '0% 50%'; R.style.transformOrigin = '100% 50%';
  A.style.transform = `translateX(${f3(-k)}%) rotateY(${f3(sw * q)}deg)`;
  R.style.transform = `translateX(${f3(k)}%) rotateY(${f3(-sw * q)}deg)`;
  A.style.filter = R.style.filter = `brightness(${f3(1 - .32 * q)})`;
  B.style.transform = `scale(${f3(.95 + .05 * q)})`;
});
function blob(x, y, r, amp, harm, q, n) {
  let d = '';
  for (let i = 0; i < n; i++) {
    const th = i / n * 2 * Math.PI; let v = 0;
    for (const h of harm) v += h.a * Math.sin(h.k * th + h.ph + h.w * q * 3);
    const rr = Math.max(0, r * (1 + amp * v));
    d += (i ? 'L' : 'M') + f1(x + rr * Math.cos(th)) + ' ' + f1(y + rr * Math.sin(th));
  }
  return d + 'Z';
}
def('ink', 'inOut', (q, A, B, o, s) => { // B проступает чернильным пятном с неровным краем и брызгами
  let m = s.mem.ink;
  if (!m) {
    const rnd = DC.u.rng(o.seed ?? 11), { x, y } = s.pt;
    const harm = [3, 5, 8, 13, 21].map((k, i) => ({ k, a: [.42, .27, .16, .1, .06][i] * (.7 + .6 * rnd()), ph: rnd() * 6.283, w: rnd() - .5 }));
    const drops = Array.from({ length: o.drops ?? 7 }, () => { const th = rnd() * 6.283, d = .22 + .5 * rnd(); return { th, d, r: .035 + .06 * rnd(), t0: .04 + .3 * rnd(), harm: harm.map(h => ({ k: h.k, a: h.a, ph: rnd() * 6.283, w: h.w })) } });
    m = s.mem.ink = { x, y, R: farR(x, y), harm, drops };
  }
  const { x, y, R, harm, drops } = m, rr = R * 1.16 * q, amp = .28 * (1 - q) + .035;
  let d = rr > .5 ? blob(x, y, rr, amp, harm, q, 120) : '';
  for (const dp of drops) {
    const g = sstep(dp.t0, dp.t0 + .16, q); if (g <= 0) continue;
    const D = R * dp.d; if (D + R * dp.r < rr * (1 - amp)) continue; // уже поглощена основным пятном
    d += blob(x + D * Math.cos(dp.th), y + D * Math.sin(dp.th), R * dp.r * g, .3, dp.harm, q, 28);
  }
  zi(B, A);
  B.style.clipPath = d ? `path("${d}")` : 'polygon(0 0,0 0,0 0)';
  A.style.filter = `brightness(${f3(1 - .16 * q)})`;
});

/* ---------- фактура: зум сквозь, зерно, глитч, загиб, створки ---------- */
def('zoomThrough', 'inOut', (q, A, B, o, s) => { // A растёт с размытием и тает, B выходит из малого
  const { x, y } = s.pt, org = `${f1(x)}px ${f1(y)}px`;
  A.style.zIndex = 3; B.style.zIndex = 1;
  A.style.transformOrigin = B.style.transformOrigin = org;
  A.style.transform = `scale(${f3(1 + (o.zoom ?? 2.4) * q)})`;
  A.style.opacity = f3(1 - sstep(.08, .7, q));
  A.style.filter = `blur(${f1(q * (o.blur ?? 18))}px)`;
  const e = DC.ease.out(sstep(.1, 1, q));
  B.style.transform = `scale(${f3(lerp(o.from ?? .55, 1, e))})`;
  B.style.opacity = f3(sstep(.04, .5, q));
  B.style.filter = e < .999 ? `blur(${f1((1 - e) * 8)}px)` : '';
});
def('dissolve', 'inOut', (q, A, B, o, s) => { // зерно: клетки A выпадают по случайному порогу, слипаясь в пятна
  let m = s.mem.dis;
  if (!m) {
    const c = o.cell ?? 30, nx = Math.ceil(W / c), ny = Math.ceil(H / c), rnd = DC.u.rng(o.seed ?? 17), g = o.grain ?? 5;
    const gx = Math.ceil(nx / g) + 2, gy = Math.ceil(ny / g) + 2, grid = Array.from({ length: gx * gy }, rnd);
    const vn = (i, j) => { const X = i / g, Y = j / g, a = Math.floor(X), b = Math.floor(Y), fx = X - a, fy = Y - b, sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
      return lerp(lerp(grid[b * gx + a], grid[b * gx + a + 1], sx), lerp(grid[(b + 1) * gx + a], grid[(b + 1) * gx + a + 1], sx), sy) };
    const mix = o.clump ?? .45, cells = [];
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) cells.push([i * c, j * c, (1 - mix) * rnd() + mix * vn(i, j)]);
    cells.sort((a, b) => a[2] - b[2]);
    m = s.mem.dis = { cells, c, n: 0, d: '' };
  }
  const want = Math.round(q * m.cells.length);
  if (want < m.n) { m.n = 0; m.d = '' }
  for (; m.n < want; m.n++) { const [x, y] = m.cells[m.n]; m.d += `M${x} ${y}h${m.c}v${m.c}h${-m.c}z` }
  A.style.zIndex = 3; B.style.zIndex = 1;
  A.style.clipPath = m.n ? `path(evenodd, "M0 0H${W}V${H}H0Z${m.d}")` : '';
}, true);
def('glitch', 'linear', (q, A, B, o, s) => { // полосы со сдвигом и расслоением каналов; ступени детерминированы
  let m = s.mem.gl;
  if (!m) {
    const id = 'dcsg' + (++gid), defs = A.querySelector('defs') || A.insertBefore(el('defs', {}), A.firstChild);
    const f = el('filter', { id, x: 0, y: 0, width: 1, height: 1, filterUnits: 'objectBoundingBox', 'color-interpolation-filters': 'sRGB' }, defs);
    m = s.mem.gl = { url: `url(#${id})`, k: -1 };
    m.turb = el('feTurbulence', { type: 'fractalNoise', baseFrequency: '0 0.04', numOctaves: 1, seed: 1, result: 'n' }, f);
    const ct = el('feComponentTransfer', { in: 'n', result: 'b' }, f);
    m.fr = el('feFuncR', { type: 'discrete', tableValues: '.5' }, ct);
    el('feFuncG', { type: 'table', tableValues: '.5 .5' }, ct); el('feFuncA', { type: 'table', tableValues: '1 1' }, ct);
    m.dm = el('feDisplacementMap', { in: 'SourceGraphic', in2: 'b', scale: 0, xChannelSelector: 'R', yChannelSelector: 'G', result: 'd' }, f);
    el('feColorMatrix', { in: 'd', type: 'matrix', values: '1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0', result: 'r' }, f);
    m.o1 = el('feOffset', { in: 'r', dx: 0, dy: 0, result: 'ro' }, f);
    el('feColorMatrix', { in: 'd', type: 'matrix', values: '0 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0', result: 'gb' }, f);
    m.o2 = el('feOffset', { in: 'gb', dx: 0, dy: 0, result: 'go' }, f);
    el('feBlend', { in: 'ro', in2: 'go', mode: 'screen' }, f);
  }
  const steps = o.steps ?? 16, k = Math.min(steps - 1, Math.floor(q * steps)), I = Math.pow(Math.sin(Math.PI * q), .7);
  if (k !== m.k) {
    m.k = k; const rnd = DC.u.rng((o.seed ?? 5) * 997 + k * 131 + 1);
    m.turb.setAttribute('seed', 1 + (k * 7) % 97); m.turb.setAttribute('baseFrequency', `0 ${f3(.006 + .05 * rnd())}`);
    const tv = []; for (let j = 0; j < 16; j++) tv.push(rnd() < .38 ? f3(rnd()) : '.5'); m.fr.setAttribute('tableValues', tv.join(' '));
    m.amt = .4 + .6 * rnd(); m.ch = 6 + 16 * rnd(); m.flick = rnd() < .3; m.jx = (rnd() - .5) * 2;
  }
  m.dm.setAttribute('scale', f1(I * (o.amount ?? 150) * m.amt));
  m.o1.setAttribute('dx', f1(I * m.ch)); m.o2.setAttribute('dx', f1(-I * m.ch));
  const showA = (q < .5) !== (m.flick && I > .35), tx = `translateX(${f1(m.jx * 14 * I)}px)`;
  A.style.zIndex = 3; B.style.zIndex = 1;
  if (showA) { A.style.opacity = 1; A.style.filter = m.url; A.style.transform = tx; B.style.filter = ''; B.style.transform = '' }
  else { A.style.opacity = 0; A.style.filter = ''; A.style.transform = ''; B.style.filter = m.url; B.style.transform = tx }
}, true);
function clipHalf(pts, C, u, s, keepFar) { // полуплоскость (P−C)·u ≥ s (keepFar) или < s — Сазерленд–Ходжман
  const f = P => ((P[0] - C[0]) * u[0] + (P[1] - C[1]) * u[1] - s) * (keepFar ? 1 : -1), out = [];
  for (let i = 0; i < pts.length; i++) {
    const P = pts[i], Q = pts[(i + 1) % pts.length], fp = f(P), fq = f(Q);
    if (fp >= 0) out.push(P);
    if ((fp >= 0) !== (fq >= 0)) { const t = fp / (fp - fq); out.push([P[0] + (Q[0] - P[0]) * t, P[1] + (Q[1] - P[1]) * t]) }
  }
  return out;
}
def('pageCurl', 'inOut', (q, A, B, o, s) => { // A сворачивается углом: срез по линии сгиба + отогнутый клапан с тенью
  let m = s.mem.curl;
  if (!m) {
    const cn = o.corner || 'br', a = (o.angle ?? 22) * Math.PI / 180;
    const C = [cn[1] === 'l' ? 0 : W, cn[0] === 't' ? 0 : H], u = [(cn[1] === 'l' ? 1 : -1) * Math.cos(a), (cn[0] === 't' ? 1 : -1) * Math.sin(a)];
    const send = Math.max(...[[0, 0], [W, 0], [W, H], [0, H]].map(P => (P[0] - C[0]) * u[0] + (P[1] - C[1]) * u[1]));
    const sv = extra(s, 'svg', 'z-index:4'), defs = el('defs', {}, sv), id = 'dcsc' + (++gid);
    const back = color(o.back, '#f4f1ea');
    const gs = el('linearGradient', { id: id + 's', gradientUnits: 'userSpaceOnUse' }, defs);
    el('stop', { offset: 0, 'stop-color': '#000', 'stop-opacity': .45 }, gs); el('stop', { offset: 1, 'stop-color': '#000', 'stop-opacity': 0 }, gs);
    const gf = el('linearGradient', { id: id + 'f', gradientUnits: 'userSpaceOnUse' }, defs);
    [[0, '#9d978b'], [.1, '#d8d3c8'], [.55, back], [.86, '#ffffff'], [1, '#e2ddd2']].forEach(([of, c]) => el('stop', { offset: of, 'stop-color': c }, gf));
    const sh = el('path', { fill: `url(#${id}s)` }, sv);
    const fl = el('path', { fill: `url(#${id}f)`, style: 'filter:drop-shadow(0 0 16px rgba(0,0,0,.38))' }, sv);
    m = s.mem.curl = { C, u, send, gs, gf, sh, fl };
  }
  const { C, u, send } = m, sd = Math.max(.01, q * send * 1.02), rect = [[0, 0], [W, 0], [W, H], [0, H]];
  const keep = clipHalf(rect, C, u, sd, true), gone = clipHalf(rect, C, u, sd, false);
  const refl = P => { const d = (P[0] - C[0]) * u[0] + (P[1] - C[1]) * u[1] - sd; return [P[0] - 2 * d * u[0], P[1] - 2 * d * u[1]] };
  A.style.zIndex = 3; B.style.zIndex = 1;
  A.style.clipPath = poly(keep);
  m.fl.setAttribute('d', pathOf(gone.map(refl))); m.sh.setAttribute('d', pathOf(gone));
  const at = k => [C[0] + u[0] * k, C[1] + u[1] * k], F = at(sd), T = at(2 * sd), Sh = at(sd - Math.min(sd, 180));
  const set = (g, a, b) => { g.setAttribute('x1', f1(a[0])); g.setAttribute('y1', f1(a[1])); g.setAttribute('x2', f1(b[0])); g.setAttribute('y2', f1(b[1])) };
  set(m.gf, F, T); set(m.gs, F, Sh);
  m.sh.setAttribute('opacity', f3(1 - sstep(.82, 1, q)));
  B.style.filter = `brightness(${f3(.86 + .14 * q)})`;
});
def('shutter', 'linear', (q, A, B, o, s) => { // две створки смыкаются над A и расходятся над B
  let m = s.mem.sh;
  if (!m) {
    const c = color(o.color, color('ink', '#16171b')), lip = color(o.lip, color('accent', '#8e1f33')), v = o.dir !== 'h';
    const base = `z-index:4;background:${c};background-image:linear-gradient(${v ? '0deg' : '90deg'},rgba(255,255,255,.07),rgba(255,255,255,0) 40%);box-shadow:0 0 40px rgba(0,0,0,.45);`;
    const a = extra(s, 'div', base + (v ? `height:450px;border-bottom:6px solid ${lip};box-sizing:border-box;` : `width:800px;border-right:6px solid ${lip};box-sizing:border-box;`));
    const b = extra(s, 'div', base + (v ? `top:450px;height:450px;border-top:6px solid ${lip};box-sizing:border-box;` : `left:800px;width:800px;border-left:6px solid ${lip};box-sizing:border-box;`));
    m = s.mem.sh = { a, b, v };
  }
  const c = q < .45 ? DC.ease.inOut(q / .45) : q > .55 ? DC.ease.inOut((1 - q) / .45) : 1, k = f3((1 - c) * 104);
  m.a.style.transform = m.v ? `translateY(-${k}%)` : `translateX(-${k}%)`;
  m.b.style.transform = m.v ? `translateY(${k}%)` : `translateX(${k}%)`;
  A.style.opacity = q < .5 ? 1 : 0;
  B.style.transform = q > .5 ? `scale(${f3(1 + .045 * (1 - sstep(.5, 1, q)))})` : '';
}, true);

DC.sheetNames = Object.keys(S).filter(k => S[k].ease !== undefined);
})();
