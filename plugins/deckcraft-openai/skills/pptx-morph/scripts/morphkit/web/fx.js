/* deckcraft web runtime — эффекты и текст (fx.js, 0.3.0).
 *
 * Регистрирует:
 *   DC.fx['in.*' | 'em.*' | 'out.*'] — эффекты входа, выделения и выхода; параметры — opt из Python;
 *   DC.textFx['fx.glyph' | 'fx.wipe' | 'fx.mark'] — свои рендеры текста: буквы по отдельности, маска с мягким
 *       краем, маркер-подложка. Раскладка та же, что у ядра: текст строится функцией ядра Surface.text в скрытом
 *       <svg>, затем меряются позиции букв (getStartPositionOfChar) — побуквенный кадр совпадает с обычным;
 *   DC.textMorph — перелив пар '!!…' с разным текстом: числа считаются как счётчик (до середины — формат старого текста,
 *       после — цели; крайние кадры совпадают со слайдами), общие буквы
 *       едут на новые места (самые длинные общие куски по очереди — слова могут меняться местами; одиночные
 *       буквы — только если почти на месте), лишние гаснут, новые проявляются; непохожие абзацы — поочерёдно;
 *   DC.draw['fx:morph'] — кадр побуквенного перелива (ядро не передаёт st объектам из textMorph — см. отчёт);
 *   DC.fxInfo — подписи эффектов по-русски; DC.fxNum — разбор и формат русских чисел.
 * Единицы: st.dx/dy/clip — дюймы, st.tx/ty — px; opt.amount у сдвигов — дюймы, у размытия/свечения — px.
 * Суффикс -l/-r/-u/-d — направление ДВИЖЕНИЯ: in.slide-u едет вверх (появляется снизу), in.reveal-r открывает
 * слева направо, out.slide-l уезжает влево, out.erase-r стирает слева направо.
 * Всё детерминировано (DC.u.rng, зерно — имя объекта + ключ или opt.seed); DC.REDUCED — сразу финал. */
'use strict';
(function () {
const DC = window.DC;
if (!DC || !DC.u || !DC.fx) return;
const U = DC.u, D = DC.data, NS = DC.NS, IN = 120, K = 120 / 72, EZ = DC.ease;
const clamp = U.clamp, lerp = U.lerp;

/* ---------- кривые и мелочи ---------- */
const outC = p => 1 - Math.pow(1 - p, 3), outQ = p => 1 - Math.pow(1 - p, 5), inC = p => p * p * p;
const outBack = (p, s = 1.70158) => 1 + (s + 1) * Math.pow(p - 1, 3) + s * Math.pow(p - 1, 2);
const inBack = (p, s = 1.70158) => (s + 1) * p * p * p - s * p * p;
const smooth = p => { p = clamp(p); return p * p * (3 - 2 * p) };
const bump = (p, c, w) => { const x = (p - c) / w; return Math.abs(x) >= 1 ? 0 : .5 + .5 * Math.cos(Math.PI * x) };
const ez = (opt, e, p, f) => (opt.ease ? e : f(p)); // своя кривая эффекта, если в Python не задана opt.ease
const C = n => (D.colors && D.colors[n]) || null;
const col = (c, d) => (c ? (c[0] === '#' ? c : C(c) || c) : d);
const ACC = () => C('accent') || '#8e1f33';
const rgba = (c, a) => { if (!c || c[0] !== '#' || c.length < 7) return c; const [r, g, b] = U.hx(c); return `rgba(${r},${g},${b},${a})` };
const lum = c => { if (!c || c[0] !== '#') return 1; const [r, g, b] = U.hx(c); return (.2126 * r + .7152 * g + .0722 * b) / 255 };
const isText = o => !!(o.t && o.k === 'text');
function hash(s) { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) } return h >>> 0 }
const seedOf = (o, key, opt) => ((opt && opt.seed !== undefined ? +opt.seed : hash((o.n || '') + '|' + key)) >>> 0) || 1;
const rnd = (seed, i) => { const r = U.rng((seed ^ Math.imul(i + 1, 2654435761)) >>> 0); r(); return r };
const KF = (p, F) => { // ключевые кадры [[t, v1, v2…]] — гладко между соседними
  if (p <= F[0][0]) return F[0].slice(1);
  for (let i = 1; i < F.length; i++) if (p <= F[i][0]) { const a = F[i - 1], b = F[i], u = smooth((p - a[0]) / (b[0] - a[0] || 1)); return a.slice(1).map((v, j) => lerp(v, b[j + 1], u)) }
  return F[F.length - 1].slice(1);
};
let fid = 0;
const fuid = p => 'dcfx' + p + (++fid);

/* ---------- геометрия ---------- */
function frameBox(o) { // повёрнутая рамка → [x0, y0, x1, y1] px
  const cx = o.x + o.w / 2, cy = o.y + o.h / 2, a = (o.r || 0) * Math.PI / 180, c = Math.abs(Math.cos(a)), s = Math.abs(Math.sin(a));
  const W = Math.abs(o.w), H = Math.abs(o.h), hw = (W * c + H * s) / 2, hh = (W * s + H * c) / 2; // у линий w/h бывают < 0
  return [cx - hw, cy - hh, cx + hw, cy + hh];
}
function inkBox(o) { // рамка ∪ буквы (текст может выходить за рамку)
  const b = frameBox(o);
  if (o.t && !(o.r % 360)) { const L = layout(o); if (L && L.box) return [Math.min(b[0], L.box[0]), Math.min(b[1], L.box[1]), Math.max(b[2], L.box[2]), Math.max(b[3], L.box[3])] }
  return b;
}
function clipWipe(o, d, f, pad = .05) { // прямоугольник clip (дюймы): видимая доля f со стороны, откуда идёт край
  const b = inkBox(o).map(v => v / IN); let [x0, y0, x1, y1] = [b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad];
  if (d === 'r') x1 = lerp(x0, x1, f); else if (d === 'l') x0 = lerp(x1, x0, f); else if (d === 'd') y1 = lerp(y0, y1, f); else y0 = lerp(y1, y0, f);
  return [x0, y0, x1, y1];
}
const DIRV = { l: [-1, 0], r: [1, 0], u: [0, -1], d: [0, 1] };
function pivot(o, th, fy = -.5, fx = 0) { // поворот на th° вокруг точки рамки (доли от центра) → drot + tx/ty
  const a = (o.r || 0) * Math.PI / 180, vx0 = fx * o.w, vy0 = fy * o.h;
  const vx = vx0 * Math.cos(a) - vy0 * Math.sin(a), vy = vx0 * Math.sin(a) + vy0 * Math.cos(a);
  const t = th * Math.PI / 180, c = Math.cos(t), s = Math.sin(t);
  return { drot: th, tx: vx - (vx * c - vy * s), ty: vy - (vx * s + vy * c) };
}

/* ---------- раскладка текста: те же <text>/<tspan>, что у ядра, + позиции букв ---------- */
let MS = null, fontGen = 0;
try { document.fonts && document.fonts.addEventListener('loadingdone', () => { fontGen++ }) } catch (e) { /* без FontFaceSet */ }
function mroot() {
  if (MS && MS.isConnected) return MS;
  MS = document.createElementNS(NS, 'svg');
  MS.setAttribute('aria-hidden', 'true'); MS.setAttribute('width', 1600); MS.setAttribute('height', 900); MS.setAttribute('viewBox', '0 0 1600 900');
  MS.style.cssText = 'position:absolute;left:-12000px;top:0;width:1600px;height:900px;visibility:hidden;pointer-events:none;overflow:hidden';
  document.body.appendChild(MS); return MS;
}
const LAY = new WeakMap(), WSC = /[ \t\n\r]/, SPC = /\s/;
function layout(o) {
  const t = o.t; if (!t || !t.lines) return null;
  let m = LAY.get(t); if (!m) { m = new Map(); LAY.set(t, m) }
  const key = o.x.toFixed(1) + ',' + o.y.toFixed(1) + ',' + o.w.toFixed(1) + ',' + o.h.toFixed(1) + ',' + fontGen;
  let L = m.get(key); if (L) return L;
  L = measure(o); if (m.size > 6) m.clear(); m.set(key, L); return L;
}
function measure(o) {
  const L = { glyphs: [], lines: [], words: 0, size: o.t.sz * K, fill: o.t.col, bad: false, box: null };
  const g = U.el('g', {}, mroot());
  try {
    DC.Surface.prototype.text.call(DC.main, { tg: g }, o, {});
    const te = g.querySelector('text'); if (!te) throw new Error('нет текста');
    L.fill = te.getAttribute('fill'); L.size = +te.getAttribute('font-size');
    const fw0 = te.getAttribute('font-weight'), ff0 = te.getAttribute('font-family');
    let line = -1, word = 0, inWord = false, prevWs = true, cur = null, run = -1;
    for (const sp of te.children) {
      if (sp.hasAttribute('x') || !cur) { line++; if (inWord) { word++; inWord = false } cur = { x0: Infinity, x1: -Infinity, top: Infinity, bot: -Infinity, base: +sp.getAttribute('y'), n: 0 }; L.lines.push(cur) }
      run++;
      const raw = sp.textContent; let s = ''; // свёртка пробелов, как у браузера (подряд, в начале текста, через tspan)
      for (let i = 0; i < raw.length; i++) { const ch = raw[i]; if (WSC.test(ch)) { if (!prevWs) s += ' '; prevWs = true } else { s += ch; prevWs = false } }
      if (s.length !== sp.getNumberOfChars()) { L.bad = true; break }
      const fill = sp.getAttribute('fill'), fw = sp.getAttribute('font-weight') || fw0, ff = sp.getAttribute('font-family') || ff0;
      for (let i = 0; i < s.length; i++) {
        let ch = s[i]; const cc = ch.charCodeAt(0);
        if (cc >= 0xDC00 && cc <= 0xDFFF) continue;
        if (cc >= 0xD800 && cc <= 0xDBFF) ch += s[i + 1] || '';
        if (SPC.test(ch)) { if (inWord) { word++; inWord = false } continue }
        const ps = sp.getStartPositionOfChar(i), ex = sp.getExtentOfChar(i);
        inWord = true;
        L.glyphs.push({ ch, x: ps.x, y: ps.y, w: ex.width, top: ex.y, h: ex.height, line, word, run, fill, fw, ff });
        cur.x0 = Math.min(cur.x0, ps.x); cur.x1 = Math.max(cur.x1, ps.x + ex.width); cur.top = Math.min(cur.top, ex.y); cur.bot = Math.max(cur.bot, ex.y + ex.height); cur.n++;
      }
    }
    L.words = word + (inWord ? 1 : 0);
  } catch (e) { L.bad = true }
  g.remove();
  if (L.glyphs.length) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const q of L.glyphs) { x0 = Math.min(x0, q.x); y0 = Math.min(y0, q.top); x1 = Math.max(x1, q.x + q.w); y1 = Math.max(y1, q.top + q.h) }
    L.box = [x0, y0, x1, y1];
  }
  return L;
}
const okL = o => { const L = o.t && layout(o); return L && !L.bad && L.glyphs.length ? L : null };
const coreText = (node, o, st) => DC.Surface.prototype.text.call(DC.main, node, o, st);
function plainText(node, o, st) { if (node.tfx) { node.tg.innerHTML = ''; node.tsig = null; node.tfx = false } coreText(node, o, st) }
function prep(node, kind) { // свой рендер в node.tg: очистить то, что рисовало ядро
  const tg = node.tg; tg.innerHTML = ''; tg.removeAttribute('transform');
  node.tsig = null; node.tfx = true; node.fxk = kind; node.fxTg = tg; return tg;
}
const mine = (node, kind, L, cache) => node.tfx && node.fxk === kind && node.fxTg === node.tg && cache && cache.L === L;
const R4 = (el, x, y, w, h) => { el.setAttribute('x', x.toFixed(1)); el.setAttribute('y', y.toFixed(1)); el.setAttribute('width', Math.max(0, w).toFixed(1)); el.setAttribute('height', Math.max(0, h).toFixed(1)) };

/* ---------- рендер «буквы по отдельности»: один <text> на букву в её измеренной позиции ---------- */
function glyphNodes(node, L, X) {
  let G = node.fxG;
  if (!mine(node, 'glyph', L, G)) {
    const tg = prep(node, 'glyph'), items = [];
    for (const q of L.glyphs) {
      const w = U.el('g', {}, tg), f0 = q.fill || L.fill;
      const te = U.el('text', { x: q.x.toFixed(2), y: q.y.toFixed(2), 'font-family': q.ff, 'font-size': L.size.toFixed(2), 'font-weight': q.fw, fill: f0 }, w);
      te.textContent = q.ch;
      items.push({ w, te, f0, c: f0, tr: '', op: '1', cx: q.x + q.w / 2, cy: q.top + q.h / 2 });
    }
    G = node.fxG = { L, items, seed: null, R: null };
  }
  if (G.seed !== X.seed) { const r = U.rng(X.seed); r(); G.R = L.glyphs.map(() => [r(), r(), r(), r()]); G.seed = X.seed }
  return G;
}
function setGlyph(n, s) {
  const has = s.x || s.y || s.r || (s.s !== undefined && s.s !== 1);
  const tr = has ? `translate(${(n.cx + (s.x || 0)).toFixed(2)} ${(n.cy + (s.y || 0)).toFixed(2)}) rotate(${(s.r || 0).toFixed(2)}) scale(${Math.max(0, s.s ?? 1).toFixed(4)}) translate(${(-n.cx).toFixed(2)} ${(-n.cy).toFixed(2)})` : '';
  if (tr !== n.tr) { if (tr) n.w.setAttribute('transform', tr); else n.w.removeAttribute('transform'); n.tr = tr }
  const op = s.a === undefined ? '1' : clamp(s.a).toFixed(3);
  if (op !== n.op) { n.w.setAttribute('opacity', op); n.op = op }
  const c = s.c || n.f0;
  if (c !== n.c) { n.te.setAttribute('fill', c); n.c = c }
}
const lq = (i, n, p, span) => clamp((p - (n > 1 ? i / (n - 1) : 0) * (1 - span)) / span); // ступенчатый местный прогресс
const GM = { // (буква, номер, всего, X, случайные[4], раскладка) → {x, y (px), r (°), s, a, c}
  letters: (g, i, n, X, R, L) => { const q = lq(i, n, X.p, X.span), e = outC(q); return { y: (1 - e) * L.size * X.amt, a: clamp(q * 1.8) } },
  wave: (g, i, n, X, R, L) => { const q = lq(i, n, X.p, X.span); return { y: L.size * X.amt * (.5 * (1 - q) - 1.1 * Math.sin(Math.PI * q) * (1 - .35 * q)), s: .7 + .3 * outC(q), a: clamp(q * 3) } },
  split: (g, i, n, X, R, L) => { const q = clamp((X.p - R[3] * .3) / .7), k = 1 - outQ(q), sp = X.amt * IN; return { x: (R[0] * 2 - 1) * sp * k, y: (R[1] * 2 - 1) * sp * .6 * k, r: (R[2] * 2 - 1) * 140 * k, s: 1 + (R[3] * 1.4 - .4) * k, a: clamp(q * 2.2) } },
  words: (g, i, n, X, R, L) => { const q = lq(g.word, L.words, X.p, X.span), e = outC(q); return { y: (1 - e) * L.size * X.amt, s: .92 + .08 * e, a: clamp(q * 1.5) } },
  rain: (g, i, n, X, R, L) => { const q = lq(i, n, X.p, X.span); return { y: -(1 - EZ.bounce(q)) * L.size * X.amt, r: (R[2] * 2 - 1) * 24 * (1 - q), a: clamp(q * 5) } },
  pop: (g, i, n, X, R, L) => { const q = lq(i, n, X.p, X.span); return { s: outBack(q, 2.6), a: clamp(q * 3) } },
  emWave: (g, i, n, X, R, L) => { const q = lq(i, n, X.p, X.span), s = Math.sin(Math.PI * q); return { y: -s * L.size * X.amt, s: 1 + .12 * s, c: X.col && s > .02 ? U.lc(g.fill || L.fill, X.col, s) : undefined } },
  scatter: (g, i, n, X, R, L) => { const q = clamp((X.p - R[3] * .25) / .75), e = outC(q), sp = X.amt * IN; return { x: (R[0] * 2 - 1) * sp * e, y: (R[1] * 2 - 1) * sp * .6 * e + q * q * L.size * 1.2, r: (R[2] * 2 - 1) * 160 * e, s: 1 - .4 * e, a: 1 - smooth(q) } },
  fall: (g, i, n, X, R, L) => { const q = lq(i, n, X.p, X.span); return { y: q * q * L.size * X.amt * 3, r: (R[2] * 2 - 1) * 55 * q, a: 1 - smooth((q - .25) / .75) } },
  outWords: (g, i, n, X, R, L) => { const q = lq(g.word, L.words, X.p, X.span); return { y: -outC(q) * L.size * X.amt, a: 1 - smooth(q) } },
};
DC.textFx['fx.glyph'] = (node, o, st) => {
  const X = st.textFx, L = okL(o);
  if (!L) return plainText(node, o, st);
  const G = glyphNodes(node, L, X), M = GM[X.mode] || GM.letters, n = G.items.length, base = st.col || null;
  for (let i = 0; i < n; i++) { const g = L.glyphs[i], s = M(g, i, n, X, G.R[i], L); if (!s.c && base && !g.fill) s.c = base; setGlyph(G.items[i], s) }
};

/* ---------- рендер «маска с мягким краем»: шторка, письмо по строкам, круг из центра ---------- */
function buildWipe(node, L, X, sig) {
  const tg = prep(node, 'wipe'), id = fuid('w'), defs = U.el('defs', {}, tg), W = { L, sig, parts: [] };
  for (const [k, x1, y1, x2, y2] of [['r', 0, 0, 1, 0], ['l', 1, 0, 0, 0], ['d', 0, 0, 0, 1], ['u', 0, 1, 0, 0]]) {
    const lg = U.el('linearGradient', { id: id + k, x1, y1, x2, y2 }, defs);
    U.el('stop', { offset: 0, 'stop-color': '#fff' }, lg); U.el('stop', { offset: 1, 'stop-color': '#000' }, lg);
  }
  const mk = U.el('mask', { id: id + 'm', maskUnits: 'userSpaceOnUse', x: -3000, y: -3000, width: 7600, height: 6900 }, defs);
  if (X.mode === 'iris') {
    const rg = U.el('radialGradient', { id: id + 'i' }, defs);
    U.el('stop', { offset: 0, 'stop-color': '#fff' }, rg); W.s1 = U.el('stop', { offset: .5, 'stop-color': '#fff' }, rg); U.el('stop', { offset: 1, 'stop-color': '#000' }, rg);
    W.circ = U.el('circle', { fill: `url(#${id}i)` }, mk);
  } else {
    const pad = 3, boxes = X.lines ? L.lines.filter(l => l.n).map(l => [l.x0, l.top, l.x1, l.bot]) : [L.box];
    for (const b of boxes) W.parts.push({ b: [b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad], solid: U.el('rect', { fill: '#fff' }, mk), soft: U.el('rect', { fill: `url(#${id}${X.mode})` }, mk) });
  }
  const wrap = U.el('g', { mask: `url(#${id}m)` }, tg);
  W.sh = U.el('g', {}, wrap); W.tn = { tg: U.el('g', {}, W.sh) }; W.shv = '';
  return W;
}
function wipePart(P, d, f, s) { // видимая доля f: сплошной прямоугольник + полоса мягкого края s px
  const [x0, y0, x1, y1] = P.b;
  if (d === 'r') { const xe = lerp(x0, x1 + s, f); R4(P.solid, x0 - 2, y0, xe - s - x0 + 2, y1 - y0); R4(P.soft, xe - s, y0, s, y1 - y0) }
  else if (d === 'l') { const xe = lerp(x1, x0 - s, f); R4(P.solid, xe + s, y0, x1 + 2 - xe - s, y1 - y0); R4(P.soft, xe, y0, s, y1 - y0) }
  else if (d === 'd') { const ye = lerp(y0, y1 + s, f); R4(P.solid, x0, y0 - 2, x1 - x0, ye - s - y0 + 2); R4(P.soft, x0, ye - s, x1 - x0, s) }
  else { const ye = lerp(y1, y0 - s, f); R4(P.solid, x0, ye + s, x1 - x0, y1 + 2 - ye - s); R4(P.soft, x0, ye, x1 - x0, s) }
}
DC.textFx['fx.wipe'] = (node, o, st) => {
  const X = st.textFx, L = okL(o);
  if (!L) return plainText(node, o, st);
  const sig = X.mode + (X.lines ? 'L' : 'B');
  let W = node.fxW;
  if (!mine(node, 'wipe', L, W) || W.sig !== sig) W = node.fxW = buildWipe(node, L, X, sig);
  coreText(W.tn, o, st);
  const f = clamp(X.q), s = Math.max(1, X.soft || 1);
  if (X.mode === 'iris') {
    const b = L.box, cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2, r = f * (Math.hypot(b[2] - b[0], b[3] - b[1]) / 2 + s);
    W.circ.setAttribute('cx', cx.toFixed(1)); W.circ.setAttribute('cy', cy.toFixed(1)); W.circ.setAttribute('r', r.toFixed(1));
    W.s1.setAttribute('offset', r > s ? (1 - s / r).toFixed(4) : 0);
  } else if (X.lines) { // письмо: строки по очереди, скорость пера постоянна
    const lens = W.parts.map(P => P.b[2] - P.b[0] + s), tot = lens.reduce((a, b) => a + b, 0);
    let c = f * tot;
    W.parts.forEach((P, k) => { wipePart(P, X.mode, clamp(c / lens[k]), s); c -= lens[k] });
  } else wipePart(W.parts[0], X.mode, f, s);
  const v = DIRV[X.mode], sh = X.shift && v ? `translate(${(-v[0] * X.shift * (1 - f)).toFixed(2)} ${(-v[1] * X.shift * (1 - f)).toFixed(2)})` : '';
  if (sh !== W.shv) { if (sh) W.sh.setAttribute('transform', sh); else W.sh.removeAttribute('transform'); W.shv = sh }
};

/* ---------- рендер «маркер»: мазок под строками, текст поверх ---------- */
DC.textFx['fx.mark'] = (node, o, st) => {
  const X = st.textFx, L = okL(o);
  if (!L) return plainText(node, o, st);
  let M = node.fxM;
  if (!mine(node, 'mark', L, M)) {
    const tg = prep(node, 'mark'), mg = U.el('g', {}, tg), tw = U.el('g', {}, tg);
    M = node.fxM = { L, rects: L.lines.filter(l => l.n).map(l => ({ l, r: U.el('rect', {}, mg) })), tw, tn: { tg: U.el('g', {}, tw) }, c: '', ta: '' };
  }
  coreText(M.tn, o, st);
  const S = L.size, padx = S * .14, lens = M.rects.map(R => R.l.x1 - R.l.x0 + 2 * padx), tot = lens.reduce((a, b) => a + b, 0);
  let c = clamp(X.q) * tot;
  M.rects.forEach((R, k) => {
    const fk = clamp(c / lens[k]), l = R.l, x = l.x0 - padx, y = l.base - S * (X.top ?? .7), h = S * (X.hgt ?? .9); c -= lens[k];
    R4(R.r, x, y, lens[k] * fk, h); R.r.setAttribute('rx', (h * .2).toFixed(1));
    R.r.setAttribute('transform', `rotate(${X.tilt ?? -.8} ${x.toFixed(1)} ${(y + h / 2).toFixed(1)})`);
  });
  const ck = X.color + '|' + X.op;
  if (ck !== M.c) { for (const R of M.rects) { R.r.setAttribute('fill', X.color); R.r.setAttribute('fill-opacity', X.op) } M.c = ck }
  const ta = clamp(X.ta ?? 1).toFixed(3);
  if (ta !== M.ta) { M.tw.setAttribute('opacity', ta); M.ta = ta }
};
const markColor = opt => { const dark = lum(C('bg') || '#ffffff') < .45; return { color: col(opt.color, dark ? (C('accent3') || '#b8860b') : '#FFE14D'), op: opt.opacity ?? (dark ? .45 : .9) } };

/* ---------- числа по-русски: «6 497», «0,541», «−0,035», «76 %», «+12», «007» ---------- */
const GRP = /[    ]/g;
const NUMRE = /([+−–-]?)(\d{1,3}(?:[    ]\d{3})+(?!\d)|\d+)(?:([.,])(\d+))?/g;
function parseNums(s) {
  const out = []; let m; NUMRE.lastIndex = 0;
  while ((m = NUMRE.exec(s))) {
    let st = m.index, sign = m[1];
    if (sign && st > 0 && /[\p{L}\p{N}]/u.test(s[st - 1])) { sign = ''; st += 1 } // «2020–2024», «А-1» — не минус
    const digits = m[2].replace(GRP, ''), dp = m[4] || '', grp = (m[2].match(/[    ]/) || [''])[0];
    const neg = !!sign && sign !== '+';
    let v = parseFloat(digits + (dp ? '.' + dp : '')); if (neg) v = -v;
    out.push({ s: st, e: m.index + m[0].length, v, sp: { nd: dp.length, dec: m[3] || ',', grp, minus: neg ? sign : '', plus: sign === '+', pad: digits.length > 1 && digits[0] === '0' ? digits.length : 0 } });
  }
  return out;
}
function fmt(v, sp, minus) {
  let s = Math.abs(v).toFixed(sp.nd); if (+s === 0) v = 0;
  let [ip, fp] = s.split('.');
  if (sp.pad && ip.length < sp.pad) ip = ip.padStart(sp.pad, '0');
  if (sp.grp && ip.length > 3) ip = ip.replace(/\B(?=(\d{3})+(?!\d))/g, sp.grp);
  s = ip + (sp.nd ? sp.dec + fp : '');
  return v < 0 ? (sp.minus || minus || '−') + s : sp.plus ? '+' + s : s;
}
const NUMC = new WeakMap();
function numInfo(t) {
  if (NUMC.has(t)) return NUMC.get(t);
  const nums = [], skel = [];
  t.lines.forEach((line, li) => {
    line.forEach((run, ri) => { const s = run[0] || ''; let pos = 0; for (const k of parseNums(s)) { skel.push(s.slice(pos, k.s), '#'); pos = k.e; nums.push(Object.assign({ li, ri }, k)) } skel.push(s.slice(pos)) });
    skel.push('\n');
  });
  const r = nums.length ? { nums, skel: skel.join('').replace(/\s+/g, ' ').trim() } : null;
  NUMC.set(t, r); return r;
}
function substNums(t, info, vals, minus) {
  const lines = t.lines.map(l => l.map(r => r.slice()));
  for (let i = info.nums.length - 1; i >= 0; i--) { const n = info.nums[i], run = lines[n.li][n.ri]; run[0] = run[0].slice(0, n.s) + fmt(vals[i], n.sp, minus) + run[0].slice(n.e) }
  return lines;
}
DC.fxNum = { parse: parseNums, fmt, info: numInfo, subst: substNums };

/* ---------- печать и расшифровка: подмена строк (st.t) ---------- */
const totalChars = t => t.lines.reduce((a, l) => a + l.reduce((b, r) => b + (r[0] || '').length, 0), 0);
function withCursor(lines, c, cur, color) { // курсор — отдельный фрагмент сразу после c-го символа
  const out = []; let left = c, done = false;
  for (const line of lines) {
    const nl = [];
    for (const r of line) {
      const s = r[0] || '';
      if (!done && left <= s.length) { // без пустых фрагментов: пустой tspan не держит позицию x/y строки
        if (left > 0) nl.push([s.slice(0, left), r[1], r[2], r[3]]);
        nl.push([cur, color, null, false]);
        if (left < s.length) nl.push([s.slice(left), r[1], r[2], r[3]]);
        done = true;
      }
      else { nl.push(r); if (!done) left -= s.length }
    }
    out.push(nl);
  }
  if (!done && out.length) out[out.length - 1].push([cur, color, null, false]);
  return out;
}
const TYPEC = new WeakMap();
function typeCum(t, seed) { // накопленное «время» печати по символам: пробелы и знаки препинания — паузы
  const c0 = TYPEC.get(t); if (c0 && c0.seed === seed) return c0;
  const R = U.rng(seed), cum = []; let acc = 0, prev = '', first = true;
  for (const line of t.lines) { first = true; for (const r of line) for (const ch of (r[0] || '')) {
    let w = .55 + R() * .9; if (ch === ' ') w *= 1.5; if ('.,:;!?…—'.includes(prev)) w *= 2.2; if (first) w *= cum.length ? 2 : 1;
    first = false; prev = ch; acc += w; for (let k = 0; k < ch.length; k++) cum.push(acc);
  } }
  const r = { seed, cum, tot: acc || 1 }; TYPEC.set(t, r); return r;
}
const typedAt = (TC, u) => { const lim = u * TC.tot; let n = 0; while (n < TC.cum.length && TC.cum[n] <= lim + 1e-9) n++; return n };
const POOL = { U: 'АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЭЮЯ', L: 'абвгдежзийклмнопрстуфхцчшщэюя', A: 'ABCDEFGHJKLMNPQRSTUVWXYZ', a: 'abcdefghijkmnopqrstuvwxyz', D: '0123456789', S: '#%&@$*+=<>/?!§' };
const poolOf = ch => /\d/.test(ch) ? POOL.D : /[А-ЯЁ]/.test(ch) ? POOL.U : /[а-яё]/.test(ch) ? POOL.L : /[A-Z]/.test(ch) ? POOL.A : /[a-z]/.test(ch) ? POOL.a : POOL.S;
const SCRC = new WeakMap();
function scrTimes(t, seed) { // момент «расшифровки» каждого символа: слева направо с разбросом
  const c0 = SCRC.get(t); if (c0 && c0.seed === seed) return c0;
  const N = totalChars(t), R = U.rng(seed), at = [];
  for (let i = 0; i < N; i++) at.push(.18 + .62 * (N > 1 ? i / (N - 1) : 0) + R() * .16);
  const r = { seed, at }; SCRC.set(t, r); return r;
}

/* ---------- регистрация ---------- */
const INFO = DC.fxInfo = DC.fxInfo || {};
function reg(key, ru, fn, hold) {
  const cat = key.slice(0, key.indexOf('.'));
  const h = (o, e, p, opt, sl) => {
    opt = opt || {};
    if (DC.REDUCED) { if (cat === 'out') return { alpha: 0 }; if (cat === 'em' && !hold) return {}; e = 1; p = 1 }
    return fn(o, e, p, opt, sl) || {};
  };
  if (hold) h.hold = true;
  DC.fx[key] = h; INFO[key] = ru;
}
const glyphFx = (mode, span, amt, fb) => (o, e, p, opt) => { // побуквенный эффект; без текста — запасной fb
  if (p >= 1 && mode !== 'emWave') return {};
  if (!okL(o)) return fb(o, e, p, opt);
  return { textFx: { k: 'fx.glyph', mode, p: opt.ease ? e : p, span: opt.span ?? span, amt: opt.amount ?? amt, seed: seedOf(o, mode, opt), col: opt.color ? col(opt.color) : null } };
};
const fbIn = (o, e, p) => ({ alpha: outC(p), dy: .25 * (1 - outC(p)) });
const fbOut = (o, e, p) => ({ alpha: 1 - p, scale: 1 - .15 * p });

/* ===== входы ===== */
reg('in.fade', 'проявление', (o, e, p, opt) => ({ alpha: ez(opt, e, p, smooth) }));
reg('in.rise', 'всплывает снизу с проявлением (opt.amount, дюймы)', (o, e, p, opt) => { const q = ez(opt, e, p, outC); return { dy: (opt.amount ?? .35) * (1 - q), alpha: q } });
reg('in.zoom', 'вырастает из малого (opt.from)', (o, e, p, opt) => { const q = ez(opt, e, p, outC); return { scale: lerp(opt.from ?? .3, 1, q), alpha: clamp(q * 1.4) } });
reg('in.stamp', 'рывками, как печать: крупно и бледно → удар (opt.steps, opt.from, opt.rot)', (o, e, p, opt) => {
  if (p >= 1) return {};
  const n = Math.max(2, opt.steps ?? 5), q = Math.min(1, (Math.floor(p * n) + 1) / n);
  const hit = q === 1 && p < 1 - .5 / n ? .965 : 1; // последний шаг — короткая «вдавленность»
  return { scale: lerp(opt.from ?? 1.7, 1, q) * hit, alpha: q, drot: (opt.rot ?? -5) * (1 - q) };
});
reg('in.registration', 'сдвиг краски: тень-копия цвета accent съезжает на место (opt.amount [dx, dy] px, opt.rest — остаток, opt.color)', (o, e, p, opt) => {
  const q = ez(opt, e, p, outC), a = opt.amount ?? [22, 14], r = opt.rest ?? [3, 2];
  const A = Array.isArray(a) ? a : [a, a * .64], B = Array.isArray(r) ? r : [r, r * .66];
  const dx = lerp(A[0], B[0], q), dy = lerp(A[1], B[1], q), st = { alpha: clamp(q * 1.25), tx: -(opt.shift ?? 12) * (1 - q) };
  if (Math.abs(dx) + Math.abs(dy) > .05) st.shadow = `${dx.toFixed(1)}px ${dy.toFixed(1)}px 0 ${rgba(col(opt.color, ACC()), opt.opacity ?? .8)}`;
  return st;
}, true);
reg('in.write', 'пишется слева направо через clip; текст — строка за строкой, мягкий край (opt.soft, дюймы; opt.lines=false — одним блоком)', (o, e, p, opt) => {
  if (p >= 1) return {};
  const q = opt.ease ? e : p, d = opt.direction === 'left' ? 'l' : 'r';
  if (isText(o) && okL(o)) return { textFx: { k: 'fx.wipe', mode: d, q, soft: (opt.soft ?? .08) * IN, lines: opt.lines !== false } };
  return { clip: clipWipe(o, d, q) };
});
reg('in.type', 'печать по символам (st.chars) с курсором-подчёркиванием (opt.cursor: "_" | "▌" | false, opt.color, opt.until)', (o, e, p, opt) => {
  if (!o.t) return { alpha: p };
  if (p >= 1) return {};
  const until = opt.until ?? .86, TC = typeCum(o.t, seedOf(o, 'type', opt)), c = typedAt(TC, clamp((opt.ease ? e : p) / until));
  const cur = opt.cursor === false ? '' : (opt.cursor ?? '_');
  const on = !!cur && (p <= until || Math.floor((p - until) / (1 - until) * 4) % 2 === 0);
  if (!on) return { chars: c };
  return { chars: c + cur.length, t: Object.assign({}, o.t, { lines: withCursor(o.t.lines, c, cur, col(opt.color, ACC())) }) };
});
reg('in.scramble', 'случайные символы «расшифровываются» в текст слева направо (opt.rate — смен за эффект, opt.color — цвет нерасшифрованных)', (o, e, p, opt) => {
  if (!o.t) return { alpha: p };
  if (p >= 1) return {};
  const seed = seedOf(o, 'scramble', opt), at = scrTimes(o.t, seed).at, q = opt.ease ? e : p;
  const tick = Math.floor(q * (opt.rate ?? 26)), R = rnd(seed, tick), cc = col(opt.color, ACC());
  let gi = 0;
  const lines = o.t.lines.map(line => {
    const out = [];
    for (const r of line) {
      let buf = '', bufOk = null;
      const flush = () => { if (buf) out.push([buf, bufOk ? r[1] : cc, r[2], r[3]]); buf = '' };
      for (const ch of (r[0] || '')) {
        const ok = SPC.test(ch) || q >= at[gi]; let c = ch;
        if (!ok) { const P = poolOf(ch); c = P[Math.floor(R() * P.length) % P.length] }
        gi += ch.length;
        if (bufOk !== null && ok !== bufOk) flush();
        bufOk = ok; buf += c;
      }
      flush(); if (!(r[0] || '').length) out.push(r);
    }
    return out;
  });
  return { t: Object.assign({}, o.t, { lines }), alpha: clamp(p * 7) };
});
reg('in.count', 'число растёт от opt.from (0) до значения; «6 497», «0,541», «−0,035», «76 %» — формат сохраняется', (o, e, p, opt) => {
  const info = o.t && numInfo(o.t);
  if (!info) return { alpha: ez(opt, e, p, outC) };
  if (p >= 1) return {};
  const q = ez(opt, e, p, outQ), from = opt.from;
  const vals = info.nums.map((n, i) => lerp(Array.isArray(from) ? (from[i] ?? 0) : (from ?? 0), n.v, q));
  return { t: Object.assign({}, o.t, { lines: substNums(o.t, info, vals) }), alpha: clamp(p * 6) };
});
reg('in.blur', 'из размытия (opt.amount px, opt.scale)', (o, e, p, opt) => { const q = ez(opt, e, p, outC); return { blur: (opt.amount ?? 14) * (1 - q), alpha: q, scale: lerp(opt.scale ?? 1.06, 1, q) } });
reg('in.elastic', 'пружина: масштаб с затухающими колебаниями (opt.axis: both | x | y)', (o, e, p, opt) => {
  const v = Math.max(0, EZ.elastic(p)), ax = opt.axis || 'both', st = { alpha: clamp(p * 5) };
  if (ax === 'x') st.sx = Math.max(.01, v); else if (ax === 'y') st.sy = Math.max(.01, v); else st.scale = Math.max(.01, v);
  return st;
});
reg('in.back', 'въезд с перелётом и возвратом (opt.direction: up | down | left | right, opt.amount дюймы)', (o, e, p, opt) => {
  const v = DIRV[(opt.direction || 'up')[0]] || DIRV.u, k = (opt.amount ?? .7) * (1 - outBack(p, 2.2));
  return { dx: -v[0] * k, dy: -v[1] * k, alpha: clamp(p * 3) };
});
reg('in.bounce', 'мячиком: масштаб с отскоками', (o, e, p) => ({ scale: Math.max(.01, EZ.bounce(p)), alpha: clamp(p * 4) }));
reg('in.drop', 'падает сверху и отскакивает (opt.amount дюймы, opt.rot)', (o, e, p, opt) => ({ dy: -(opt.amount ?? 2) * (1 - EZ.bounce(p)), drot: (opt.rot ?? 0) * (1 - outC(p)), alpha: clamp(p * 5) }));
reg('in.pop', 'выскакивает: масштаб с перелётом и подъёмом (opt.from)', (o, e, p, opt) => ({ scale: Math.max(.01, lerp(opt.from ?? .55, 1, outBack(p, 2.4))), ty: 24 * (1 - outC(p)), alpha: clamp(p * 3) }));
reg('in.flip', 'переворот по горизонтали: sx 0 → 1', (o, e, p, opt) => ({ sx: Math.max(.02, ez(opt, e, p, q => outBack(q, 1.3))), alpha: clamp(p * 3), bright: lerp(1.25, 1, p) }));
reg('in.unfold', 'раскрытие по вертикали: sy 0 → 1', (o, e, p, opt) => ({ sy: Math.max(.02, ez(opt, e, p, q => outBack(q, 1.3))), alpha: clamp(p * 3) }));
for (const [d, ru] of [['l', 'влево (появляется справа)'], ['r', 'вправо (появляется слева)'], ['u', 'вверх (появляется снизу)'], ['d', 'вниз (появляется сверху)']])
  reg('in.slide-' + d, 'въезд ' + ru + ' с проявлением (opt.amount дюймы)', (o, e, p, opt) => { const q = ez(opt, e, p, outC), v = DIRV[d], k = (opt.amount ?? .6) * (1 - q); return { dx: -v[0] * k, dy: -v[1] * k, alpha: q } });
reg('in.zoom-out', 'из большого: масштаб opt.from → 1 с размытием', (o, e, p, opt) => { const q = ez(opt, e, p, outQ); return { scale: lerp(opt.from ?? 2.4, 1, q), alpha: clamp(q * 1.2), blur: (opt.blur ?? 6) * (1 - q) } });
reg('in.spin', 'вкручивается: поворот opt.amount° и рост', (o, e, p, opt) => { const q = ez(opt, e, p, outC); return { drot: -(opt.amount ?? 200) * (1 - q), scale: lerp(.3, 1, q), alpha: clamp(p * 2.5) } });
reg('in.swing', 'качается на петле сверху и успокаивается (opt.amount°)', (o, e, p, opt) => {
  if (p >= 1) return {};
  const th = (opt.amount ?? 70) * Math.pow(1 - p, 1.7) * Math.cos(p * Math.PI * 3);
  return Object.assign(pivot(o, th, -.5), { alpha: clamp(p * 4) });
});
reg('in.ink', 'растекание туши: рост + размытие + проявление (opt.from, opt.amount px)', (o, e, p, opt) => { const q = ez(opt, e, p, outC); return { scale: lerp(opt.from ?? .8, 1, q), blur: (opt.amount ?? 12) * Math.pow(1 - q, 1.3), alpha: clamp(q * 1.35), sat: lerp(.4, 1, q) } });
function glitchSt(o, p, I, opt, key) { // рывки по x, сдвиг оттенка и яркости, цветная тень; кадры — шагами
  const seed = seedOf(o, key, opt), k = Math.floor(p * (opt.steps ?? 18)), R = rnd(seed, k), r = [R(), R(), R(), R(), R(), R()], A = (opt.amount ?? .18) * IN * I;
  const st = { tx: (r[0] * 2 - 1) * A, hue: (r[1] * 2 - 1) * 150 * I, bright: 1 + (r[2] * 2 - 1) * .6 * I };
  if (r[3] > .55) st.skewX = (r[3] - .55) / .45 * 16 * I * (r[0] > .5 ? 1 : -1);
  if (r[4] < .3 * I) st.alpha = .25;
  st.shadow = `${((r[5] > .5 ? 1 : -1) * (3 + 7 * r[5]) * I).toFixed(1)}px 0 0 ${rgba(col(opt.color, C('accent2') || '#2a9d8f'), .8)}`;
  return st;
}
reg('in.glitch', 'сбой сигнала: рывки по x, оттенок и яркость шагами, затем чисто (opt.amount дюймы, opt.steps, opt.color)', (o, e, p, opt) => {
  if (p >= .8) return {};
  const st = glitchSt(o, p, 1 - p / .8 * .55, opt, 'glitch');
  st.alpha = (st.alpha ?? 1) * clamp(.35 + p * 2); return st;
});
for (const [d, ru] of [['l', 'справа налево'], ['r', 'слева направо'], ['u', 'снизу вверх'], ['d', 'сверху вниз']])
  reg('in.reveal-' + d, 'вытирание ' + ru + ' с мягким краем (текст — маска; фигуры — clip) и лёгким сдвигом (opt.soft, opt.shift дюймы)', (o, e, p, opt) => {
    if (p >= 1) return {};
    const q = ez(opt, e, p, outC), sh = (opt.shift ?? .12) * IN, v = DIRV[d];
    if (isText(o) && okL(o)) return { textFx: { k: 'fx.wipe', mode: d, q, soft: (opt.soft ?? .35) * IN, shift: sh } };
    return { clip: clipWipe(o, d, q), tx: -v[0] * sh * (1 - q), ty: -v[1] * sh * (1 - q) };
  });
reg('in.iris', 'появление из центра кругом (текст — круглая маска с мягким краем, фигуры — квадрат clip)', (o, e, p, opt) => {
  if (p >= 1) return {};
  const q = ez(opt, e, p, outC);
  if (isText(o) && okL(o)) return { textFx: { k: 'fx.wipe', mode: 'iris', q, soft: (opt.soft ?? .3) * IN } };
  const b = frameBox(o), cx = (b[0] + b[2]) / 2 / IN, cy = (b[1] + b[3]) / 2 / IN, r = q * (Math.max(b[2] - b[0], b[3] - b[1]) / 2 / IN + .06);
  return { clip: [cx - r, cy - r, cx + r, cy + r], scale: lerp(.94, 1, q) };
});
reg('in.letters', 'буквы по одной поднимаются (opt.span — доля длительности на букву, opt.amount — высота в кеглях)', glyphFx('letters', .35, .6, fbIn));
reg('in.wave-letters', 'буквы приходят волной: снизу, через гребень, на место', glyphFx('wave', .4, .6, fbIn));
reg('in.split-letters', 'буквы слетаются из разброса (opt.amount — разброс, дюймы)', glyphFx('split', .7, 1.4, fbIn));
reg('in.words', 'слова по одному', glyphFx('words', .45, .45, fbIn));
reg('in.rain-letters', 'буквы падают сверху с отскоком, по очереди', glyphFx('rain', .45, 2.2, fbIn));
reg('in.pop-letters', 'буквы выскакивают по одной с перелётом', glyphFx('pop', .3, 1, fbIn));
reg('in.highlight', 'текст проявляется с маркером-подложкой (opt.color — по умолчанию жёлтый, opt.opacity)', (o, e, p, opt) => {
  if (!(isText(o) && okL(o))) return { alpha: ez(opt, e, p, outC) };
  const m = markColor(opt), q = opt.ease ? e : p;
  return { textFx: { k: 'fx.mark', q: outC(clamp(q / .75)), ta: smooth((q - .1) / .6), color: m.color, op: m.op } };
}, true);

/* ===== выделения ===== */
reg('em.pulse', 'пульс: масштаб туда и обратно (opt.amount)', (o, e, p, opt) => ({ scale: 1 + (opt.amount ?? .08) * Math.sin(Math.PI * p) }));
reg('em.shake', 'дрожь по горизонтали (opt.amount дюймы, opt.count)', (o, e, p, opt) => ({ tx: (opt.amount ?? .1) * IN * Math.sin(p * Math.PI * 2 * (opt.count ?? 5)) * (1 - p) }));
reg('em.wobble', 'вихляние: сдвиг с поворотом, затухает (opt.amount дюймы)', (o, e, p, opt) => { const [k, r] = KF(p, [[0, 0, 0], [.15, -1, -5], [.3, .8, 3], [.45, -.6, -3], [.6, .4, 2], [.75, -.2, -1], [1, 0, 0]]); return { tx: k * (opt.amount ?? .25) * IN, drot: r } });
reg('em.jello', 'желе: наклон skewX туда-сюда (opt.amount°)', (o, e, p, opt) => { const [s] = KF(p, [[0, 0], [.111, 0], [.222, -12.5], [.333, 6.25], [.444, -3.125], [.555, 1.5625], [.666, -.78], [.777, .39], [.888, -.2], [1, 0]]); return { skewX: s * (opt.amount ?? 12.5) / 12.5 } });
reg('em.heartbeat', 'сердцебиение: два удара (opt.amount)', (o, e, p, opt) => { const a = opt.amount ?? .15, [s] = KF(p, [[0, 1], [.14, 1 + a], [.28, 1], [.42, 1 + a], [.7, 1], [1, 1]]); return { scale: s } });
reg('em.glow', 'свечение цветом accent (opt.color, opt.amount — радиус px)', (o, e, p, opt) => { const k = Math.sin(Math.PI * p), c = col(opt.color, ACC()), r = (opt.amount ?? 18) * k; return k < .01 ? {} : { glow: c, glowR: r, shadow: `0 0 ${(r * .45).toFixed(1)}px ${c}`, bright: 1 + .08 * k } });
reg('em.flash', 'вспышка: мигнуть opt.count раз (opt.min — нижняя прозрачность)', (o, e, p, opt) => ({ alpha: lerp(1, opt.min ?? .1, (1 - Math.cos(2 * Math.PI * (opt.count ?? 2) * p)) / 2) }));
reg('em.tada', 'та-дам: сжаться, вырасти с покачиванием, вернуться (opt.amount)', (o, e, p, opt) => { const [s, r] = KF(p, [[0, 1, 0], [.1, .9, -3], [.2, .9, -3], [.3, 1.1, 3], [.4, 1.1, -3], [.5, 1.1, 3], [.6, 1.1, -3], [.7, 1.1, 3], [.8, 1.1, -3], [.9, 1.1, 3], [1, 1, 0]]), k = (opt.amount ?? .1) / .1; return { scale: 1 + (s - 1) * k, drot: r } });
reg('em.float', 'парение вверх-вниз (для повтора — "repeat": True; opt.amount дюймы)', (o, e, p, opt) => ({ dy: -(opt.amount ?? .12) * Math.sin(2 * Math.PI * p) }));
reg('em.color', 'перекрасить текст (фигуру — заливку) в opt.color и оставить', (o, e, p, opt) => {
  const q = ez(opt, e, p, smooth), c = col(opt.color, ACC());
  if (o.t && (o.k === 'text' || opt.part === 'text')) {
    const st = { col: U.lc(o.t.col, c, q) };
    if (opt.runs !== false && o.t.lines.some(l => l.some(r => r[1]))) st.t = Object.assign({}, o.t, { lines: o.t.lines.map(l => l.map(r => (r[1] ? [r[0], U.lc(r[1], c, q), r[2], r[3]] : r))) });
    return st;
  }
  return { fill: U.lc(o.k === 'line' ? o.s : o.f, c, q) };
}, true);
reg('em.swing', 'качание на петле сверху (opt.amount°)', (o, e, p, opt) => { const [a] = KF(p, [[0, 0], [.2, 15], [.4, -10], [.6, 5], [.8, -5], [1, 0]]); return pivot(o, a * (opt.amount ?? 15) / 15, -.5) });
reg('em.rubber', 'резинка: растяжение-сжатие по осям', (o, e, p) => { const [sx, sy] = KF(p, [[0, 1, 1], [.3, 1.25, .75], [.4, .75, 1.25], [.5, 1.15, .85], [.65, .95, 1.05], [.75, 1.05, .95], [1, 1, 1]]); return { sx, sy } });
reg('em.dim', 'приглушить (alpha opt.amount = 0,25, opt.sat) и оставить', (o, e, p, opt) => { const q = ez(opt, e, p, smooth); return { alpha: lerp(1, opt.amount ?? .25, q), sat: lerp(1, opt.sat ?? .5, q) } }, true);
reg('em.wave', 'волна по буквам (opt.color — подсветка гребня; для фигур — подскок)', glyphFx('emWave', .35, .35, (o, e, p) => ({ dy: -.1 * Math.sin(Math.PI * p) })));
reg('em.grow', 'увеличить до opt.amount (1,15) и оставить', (o, e, p, opt) => ({ scale: lerp(1, opt.amount ?? 1.15, ez(opt, e, p, q => outBack(q, 2))) }), true);
reg('em.spin', 'оборот на opt.amount° (360)', (o, e, p, opt) => ({ drot: (opt.amount ?? 360) * e }));
reg('em.reg', 'сдвиг краски на миг: тень-копия отходит и возвращается (opt.amount [dx, dy] px)', (o, e, p, opt) => {
  const a = opt.amount ?? [10, 6], A = Array.isArray(a) ? a : [a, a * .6], k = Math.sin(Math.PI * p);
  return k < .01 ? {} : { shadow: `${(A[0] * k).toFixed(1)}px ${(A[1] * k).toFixed(1)}px 0 ${rgba(col(opt.color, ACC()), opt.opacity ?? .8)}`, tx: -3 * k };
});
reg('em.glitch', 'короткий сбой сигнала', (o, e, p, opt) => { const I = Math.sin(Math.PI * p); return I < .05 ? {} : glitchSt(o, p, I, opt, 'emglitch') });
reg('em.mark', 'маркер под текстом прокатывается и остаётся (фигура — обводка цветом)', (o, e, p, opt) => {
  const m = markColor(opt);
  if (!(isText(o) && okL(o))) return { outline: m.color };
  return { textFx: { k: 'fx.mark', q: ez(opt, e, p, outC), ta: 1, color: m.color, op: m.op } };
}, true);
reg('em.jump', 'подскок с приседанием (opt.amount дюймы)', (o, e, p, opt) => {
  const h = clamp((p - .12) / .76), sq = bump(p, .06, .07) + bump(p, .94, .07);
  return { dy: -(opt.amount ?? .3) * 4 * h * (1 - h), sy: 1 - .14 * sq, sx: 1 + .1 * sq };
});

/* ===== выходы (p: 0 → 1 — ход ухода) ===== */
reg('out.fade', 'растворение', (o, e, p, opt) => ({ alpha: 1 - ez(opt, e, p, smooth) }));
reg('out.zoom', 'улетает на зрителя: рост до opt.to (1,6) и растворение', (o, e, p, opt) => { const q = ez(opt, e, p, outC); return { scale: lerp(1, opt.to ?? 1.6, q), alpha: 1 - q, blur: 4 * q } });
reg('out.drop', 'падает вниз с поворотом (opt.amount дюймы, opt.rot)', (o, e, p, opt) => ({ dy: (opt.amount ?? 1.8) * inBack(p, 1.2), drot: (opt.rot ?? 14) * inC(p), alpha: 1 - smooth((p - .45) / .55) }));
for (const [d, ru] of [['l', 'влево'], ['r', 'вправо'], ['u', 'вверх'], ['d', 'вниз']])
  reg('out.slide-' + d, 'уезжает ' + ru + ' с растворением (opt.amount дюймы)', (o, e, p, opt) => { const q = ez(opt, e, p, x => x * x), v = DIRV[d], k = (opt.amount ?? .8) * q; return { dx: v[0] * k, dy: v[1] * k, alpha: 1 - q } });
reg('out.blur', 'в размытие (opt.amount px)', (o, e, p, opt) => { const q = ez(opt, e, p, smooth); return { blur: (opt.amount ?? 14) * q, alpha: 1 - q, scale: 1 + .06 * q } });
reg('out.shrink', 'сжимается в точку (с замахом)', (o, e, p) => ({ scale: Math.max(.001, 1 - inBack(p, 2)), alpha: 1 - smooth((p - .7) / .3) }));
reg('out.burn', 'выгорание: раскаляется (цвет opt.color, яркость, свечение) и гаснет', (o, e, p, opt) => {
  const h = smooth(p / .55), c = col(opt.color, C('warn') || '#e07a1f'), st = { bright: 1 + 1.6 * h, glow: c, glowR: 14 * h, alpha: 1 - smooth((p - .35) / .65) };
  if (o.t && o.k === 'text') st.col = U.lc(o.t.col, c, h); else if (o.f) st.fill = U.lc(o.f, c, h);
  return st;
});
reg('out.flip', 'переворот: sx 1 → 0', (o, e, p, opt) => { const q = ez(opt, e, p, q => inBack(q, 1.3)); return { sx: Math.max(.02, 1 - q), alpha: 1 - smooth((p - .6) / .4) } });
reg('out.fold', 'складывается по вертикали: sy 1 → 0', (o, e, p, opt) => { const q = ez(opt, e, p, q => inBack(q, 1.3)); return { sy: Math.max(.02, 1 - q), alpha: 1 - smooth((p - .6) / .4) } });
reg('out.spin', 'выкручивается: поворот opt.amount° и уменьшение', (o, e, p, opt) => { const q = ez(opt, e, p, x => x * x); return { drot: (opt.amount ?? 200) * q, scale: lerp(1, .2, q), alpha: 1 - q } });
for (const [d, inv, ru] of [['l', 'r', 'справа налево'], ['r', 'l', 'слева направо'], ['u', 'd', 'снизу вверх'], ['d', 'u', 'сверху вниз']])
  reg('out.erase-' + d, 'стирание ' + ru + ' с мягким краем (opt.soft, opt.shift дюймы)', (o, e, p, opt) => {
    const q = ez(opt, e, p, smooth), sh = (opt.shift ?? .12) * IN, v = DIRV[d];
    if (isText(o) && okL(o)) return { textFx: { k: 'fx.wipe', mode: inv, q: 1 - q, soft: (opt.soft ?? .35) * IN, shift: sh } };
    return { clip: clipWipe(o, inv, 1 - q), tx: v[0] * sh * q, ty: v[1] * sh * q };
  });
reg('out.type', 'стирание по символам (забой) с курсором (opt.cursor, opt.color, opt.until)', (o, e, p, opt) => {
  if (!o.t) return { alpha: 1 - p };
  const until = opt.until ?? .8, N = totalChars(o.t), c = Math.round(N * (1 - clamp((opt.ease ? e : p) / until)));
  const cur = opt.cursor === false ? '' : (opt.cursor ?? '_');
  if (!cur) return { chars: c };
  const on = p <= until || Math.floor((p - until) / (1 - until) * 4) % 2 === 0;
  if (!on) return { chars: c };
  return { chars: c + cur.length, t: Object.assign({}, o.t, { lines: withCursor(o.t.lines, c, cur, col(opt.color, ACC())) }) };
});
reg('out.glitch', 'уходит сбоем: рывки нарастают, кадры гаснут', (o, e, p, opt) => { const st = glitchSt(o, p, .45 + .55 * p, opt, 'outglitch'); st.alpha = (st.alpha ?? 1) * (1 - smooth((p - .5) / .5)); return st });
reg('out.ink', 'растворяется, как тушь в воде: размытие, рост, бледнеет', (o, e, p, opt) => { const q = ez(opt, e, p, smooth); return { blur: (opt.amount ?? 12) * q, scale: 1 + .22 * q, alpha: 1 - q, sat: 1 - .6 * q } });
reg('out.words', 'слова уходят вверх по одному', glyphFx('outWords', .45, .45, fbOut));
reg('out.letters', 'буквы по одной падают вниз', glyphFx('fall', .4, 1, fbOut));
reg('out.scatter-letters', 'буквы разлетаются в стороны (opt.amount — разброс, дюймы)', glyphFx('scatter', .75, 1.4, fbOut));

/* ---------- перелив текста ---------- */
const keepA = (a, o) => Object.assign({}, a, { x: o.x, y: o.y, w: o.w, h: o.h, r: o.r });
const dissolve = (a, b, t, o) => [[keepA(a, o), clamp(1 - 2 * t)], [o, clamp(2 * t - 1)]]; // как у ядра: сначала уходит старый
function numMorph(a, b, t, o) { // одинаковые «скелеты» с числами: числа считаются; до середины — формат старого
  const A = numInfo(a.t), B = numInfo(b.t);   // текста (знак «+», разряды, нули, знаки после запятой), после — цели
  if (!A || !B || A.skel !== B.skel || A.nums.length !== B.nums.length) return null;
  if (A.nums.every((n, i) => n.v === B.nums[i].v)) return null; // числа те же — изменился формат: обычный перелив
  const first = t < .5, T = first ? a.t : b.t, I = first ? A : B;
  const minus = ((first ? B : A).nums.find(n => n.sp.minus) || { sp: {} }).sp.minus;
  const vals = B.nums.map((n, i) => lerp(A.nums[i].v, n.v, t));
  const lines = t <= 0 ? a.t.lines : t >= 1 ? b.t.lines : substNums(T, I, vals, minus);
  const tt = Object.assign({}, T, { sz: lerp(a.t.sz, b.t.sz, t), col: U.lc(a.t.col, b.t.col, clamp(t)), lines });
  return [[Object.assign({}, o, { t: tt }), 1]];
}
const MPLAN = new WeakMap();
function morphPlan(a, b) {
  let m = MPLAN.get(a.t); if (!m) { m = new WeakMap(); MPLAN.set(a.t, m) }
  const key = [a.x, a.y, a.w, a.h, b.x, b.y, b.w, b.h, fontGen].map(v => (+v).toFixed(1)).join(',');
  const rec = m.get(b.t); if (rec && rec.key === key) return rec.P;
  const P = buildPlan(a, b); m.set(b.t, { key, P }); return P;
}
function buildPlan(a, b) { // общие куски: самые длинные общие подстроки по очереди (слова могут меняться местами)
  const LA = layout(a), LB = layout(b);
  if (!LA || !LB || LA.bad || LB.bad) return null;
  const A = LA.glyphs, B = LB.glyphs, n = A.length, m = B.length;
  if (n * m > 160000) return null; // очень длинные тексты — поочерёдно
  const ca = [a.x + a.w / 2, a.y + a.h / 2], cb = [b.x + b.w / 2, b.y + b.h / 2], S = Math.max(LA.size, LB.size);
  const RA = A.map(g => [g.x - ca[0], g.y - ca[1]]), RB = B.map(g => [g.x - cb[0], g.y - cb[1]]);
  const dist = (i, j) => Math.hypot(RA[i][0] - RB[j][0], RA[i][1] - RB[j][1]);
  const swA = A.map((g, i) => i > 0 && g.word !== A[i - 1].word), swB = B.map((g, i) => i > 0 && g.word !== B[i - 1].word);
  const ma = new Uint8Array(n), mb = new Uint8Array(m), pair = new Map(), blk = new Map(); // blk: буква A → начало куска в B
  let prev = new Uint16Array(m + 1), cur = new Uint16Array(m + 1);
  for (;;) { // кусок длиной ≥ 2 с одинаковыми границами слов; из равных — ближний
    let best = 0, bi = 0, bj = 0, bd = Infinity;
    prev.fill(0);
    for (let i = 1; i <= n; i++) {
      cur[0] = 0;
      for (let j = 1; j <= m; j++) {
        let L = 0;
        if (!ma[i - 1] && !mb[j - 1] && A[i - 1].ch === B[j - 1].ch) L = prev[j - 1] && swA[i - 1] === swB[j - 1] ? prev[j - 1] + 1 : 1;
        cur[j] = L;
        if (L > 1 && L >= best) { const d = dist(i - L, j - L); if (L > best || d < bd) { best = L; bi = i; bj = j; bd = d } }
      }
      const tmp = prev; prev = cur; cur = tmp;
    }
    if (best < 2) break;
    for (let k = 1; k <= best; k++) { ma[bi - k] = 1; mb[bj - k] = 1; pair.set(bi - k, bj - k); blk.set(bi - k, bj - best) }
  }
  for (let i = 0; i < n; i++) { // одиночные буквы — только если почти на месте
    if (ma[i]) continue;
    let bj = -1, bd = S * .9;
    for (let j = 0; j < m; j++) if (!mb[j] && A[i].ch === B[j].ch) { const d = dist(i, j); if (d < bd) { bd = d; bj = j } }
    if (bj >= 0) { ma[i] = 1; mb[bj] = 1; pair.set(i, bj); blk.set(i, bj) }
  }
  const multi = LA.lines.length > 1 || LB.lines.length > 1;
  if (multi && pair.size < .5 * Math.max(n, m)) return null; // абзацы мало похожи — поочерёдное растворение
  const items = [], lagMax = .16;
  const fa = g => g.fill || LA.fill, fb = g => g.fill || LB.fill;
  for (let k = 0; k < n; k++) {
    const g = A[k];
    if (pair.has(k)) {
      const j2 = pair.get(k), h = B[j2], dx = RB[j2][0] - RA[k][0];
      const arc = Math.abs(dx) > S * .6 ? -Math.sign(dx) * Math.min(Math.abs(dx) * .3, S * .75) : 0; // встречные куски расходятся дугами
      items.push({ kind: 'm', ch: g.ch, ax: RA[k][0], ay: RA[k][1], bx: RB[j2][0], by: RB[j2][1], arc, fa: fa(g), fb: fb(h), fwa: g.fw, fwb: h.fw, ffa: g.ff, ffb: h.ff, lag: lagMax * (m > 1 ? blk.get(k) / (m - 1) : 0) }); // кусок едет целиком
    }
    else items.push({ kind: 'a', ch: g.ch, ax: RA[k][0], ay: RA[k][1], fa: fa(g), fwa: g.fw, ffa: g.ff });
  }
  for (let k = 0; k < m; k++) if (!mb[k]) { const h = B[k]; items.push({ kind: 'b', ch: h.ch, bx: RB[k][0], by: RB[k][1], fb: fb(h), fwb: h.fw, ffb: h.ff, lag: .42 + .18 * (m > 1 ? k / (m - 1) : 0) }) }
  return { items, sa: LA.size, sb: LB.size, lagMax, cover: pair.size / Math.max(n, m, 1) };
}
DC.draw['fx:morph'] = (node, o) => {
  const M = o.draw, P = M.P, q = M.q;
  let R = node.fxMo;
  if (!R || R.P !== P || R.dg !== node.dg) {
    node.dg.innerHTML = '';
    R = node.fxMo = { P, dg: node.dg, items: P.items.map(it => {
      const w = U.el('g', {}, node.dg), size = it.kind === 'b' ? P.sb : P.sa;
      const te = U.el('text', { x: 0, y: 0, 'font-size': size.toFixed(2), 'font-family': it.ffa || it.ffb, 'font-weight': it.fwa || it.fwb, fill: it.fa || it.fb }, w);
      te.textContent = it.ch; return { it, w, te, c: it.fa || it.fb, sw: false, tr: '', op: '' };
    }) };
  }
  const cx = o.x + o.w / 2, cy = o.y + o.h / 2, ks = P.sb / P.sa;
  for (const n of R.items) {
    const it = n.it; let x, y, s = 1, a = 1, c = n.c;
    if (it.kind === 'm') {
      const k = q > 1 ? q : clamp((q - it.lag) / (1 - P.lagMax)), kc = clamp(k); // q > 1 — перелёт кривой back/elastic
      x = cx + lerp(it.ax, it.bx, k); y = cy + lerp(it.ay, it.by, k) + it.arc * Math.sin(Math.PI * kc); s = lerp(1, ks, k); c = U.lc(it.fa, it.fb, kc);
      const sw = kc > .5; if (sw !== n.sw) { n.te.setAttribute('font-weight', sw ? it.fwb : it.fwa); n.te.setAttribute('font-family', sw ? it.ffb : it.ffa); n.sw = sw }
    } else if (it.kind === 'a') { const k = clamp(q / .5); x = cx + it.ax; y = cy + it.ay - k * P.sa * .22; s = 1 - .2 * k; a = 1 - smooth(k) }
    else { const k = clamp((q - it.lag) / (1 - it.lag)); x = cx + it.bx; y = cy + it.by + (1 - outC(k)) * P.sb * .3; s = .8 + .2 * outC(k); a = smooth(k) }
    const tr = `translate(${x.toFixed(2)} ${y.toFixed(2)}) scale(${s.toFixed(4)})`;
    if (tr !== n.tr) { n.w.setAttribute('transform', tr); n.tr = tr }
    const op = clamp(a).toFixed(3); if (op !== n.op) { n.w.setAttribute('opacity', op); n.op = op }
    if (c !== n.c) { n.te.setAttribute('fill', c); n.c = c }
  }
};
/* o.web.textMorph у объекта (из Python: meta["web"] = {"textMorph": …}): "auto" (по умолчанию) | "count" | "letters" |
 * "dissolve". auto: числа с одинаковым скелетом → счётчик; иначе буквы (многострочные — если общих букв ≥ 50 %); иначе
 * поочерёдное растворение (сначала уходит старый текст, затем приходит новый). */
DC.textMorph = (a, b, t, o) => {
  try {
    const mode = (b.web && b.web.textMorph) || (a.web && a.web.textMorph) || 'auto';
    if (mode === 'dissolve' || DC.REDUCED) return dissolve(a, b, t, o);
    if (mode !== 'letters') { const N = numMorph(a, b, t, o); if (N) return N }
    if (mode !== 'count' && a.k === 'text' && b.k === 'text') { const P = morphPlan(a, b); if (P) return [[Object.assign({}, o, { t: null, draw: { kind: 'fx:morph', P, q: t } }), 1]] }
  } catch (e) { console.warn('fx: перелив текста —', e && e.message) }
  return dissolve(a, b, t, o);
};
})();
