/* deckcraft web runtime — элементы рисования (0.3.0).
 * DC.draw[kind](node, o, st, surface) рисует o.draw (спецификация из morphkit/draw.py) в node.dg.
 *
 * Спецификация: {kind, style, c, c2, tc, lw (pt), seed, _f: [x, y, w, h] — рамка в дюймах при сборке, параметры вида —
 * в дюймах слайда}. Рамка объекта o.x/y/w/h (px) может отличаться от _f (камера, Morph, состояния alt) — геометрия
 * переносится: X = o.x + (u − _f[0])·o.w/_f[2].
 * Стили: blueprint (тонкие светлые линии для тёмного фона), ink (тушь с лёгким дрожанием), marker (толстые полупрозрачные,
 * multiply), riso (толстые + смещённая копия второй краской, надпечатка multiply), chalk (мел: неровная прерывистая).
 * Порядок частей: у каждой части окно [t0, t1] внутри st.drawP (0..1); штрихи рисуются по длине (pathLength=1 +
 * stroke-dasharray), заливки и подписи проявляются / «пишутся» (clip) / выскакивают.
 * Узлы кэшируются в node.dc: на кадре без изменений ничего не трогаем; при изменении спецификации или рамки (Morph)
 * обновляются атрибуты существующих элементов, DOM пересоздаётся, только если меняется число/вид частей.
 * Поля состояния (свои): drawP, drawReg (0..1 — сдвиг надпечатки riso), drawBoil (номер «кипения» линий),
 * drawValue (подмена value/t: стрелка прибора, часы, размер), drawNeedle (доп. угол стрелки, градусы).
 * Эффекты: in.draw, in.draw-linear, in.draw-stamp, in.draw-drop, in.draw-reg, in.draw-pop;
 * em.draw-redraw, em.draw-boil, em.draw-to, em.draw-run, em.draw-needle (в конце файла). */
'use strict';
(function () {
const GOST_EN = { 'Изм.': 'Rev.', 'Лист': 'Sheet', '№ докум.': 'Doc. no.', 'Подп.': 'Sign.', 'Дата': 'Date', 'Разраб.': 'Drawn',
  'Пров.': 'Checked', 'Т.контр.': 'Tech. check', 'Н.контр.': 'Std. check', 'Утв.': 'Approved', 'Лит.': 'Lit.', 'Масса': 'Mass',
  'Масштаб': 'Scale', 'Листов': 'Sheets' };
const gl = s => (String((window.DC && DC.data && DC.data.lang) || 'ru').startsWith('en') && GOST_EN[s]) || s; // графы рамки по языку
const DC = window.DC, U = DC.u, D = DC.data;
const REG = DC.draw;
const RAD = Math.PI / 180, PT = 1 / 72;
const clamp = U.clamp, lerp = U.lerp;
let N = 0;
const uid = p => 'dd' + p + (++N);
const eOut = t => 1 - Math.pow(1 - t, 3);
const eIO = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
const eBack = t => { const c = 2.2, c3 = c + 1; return 1 + c3 * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2) };

/* ---------- цвета, шрифты, числа ---------- */
function col(c, fb) { // роль темы | #hex | hex | "роль/30" (оттенок: 30 % цвета на белом)
  if (c === undefined || c === null || c === '') return fb === undefined ? '#000000' : col(fb);
  if (typeof c !== 'string') return '#000000';
  let s = c.trim(), tint = null;
  const m = /^(.+?)\/(\d+(?:\.\d+)?)$/.exec(s); if (m) { s = m[1]; tint = +m[2] / 100 }
  let h = (D.colors && D.colors[s]) || s;
  if (/^[0-9a-f]{6}$/i.test(h)) h = '#' + h;
  if (tint !== null && /^#[0-9a-f]{6}$/i.test(h)) h = U.lc('#ffffff', h, clamp(tint));
  return h;
}
const HAND = "'Caveat', 'Segoe Print', 'Bradley Hand', 'Noteworthy', 'Comic Sans MS', 'Comic Neue'";
let handOK = null;
function handAvail() { // есть ли рукописный шрифт; нет — тело текста курсивом + дрожание букв
  if (handOK !== null) return handOK;
  try { const x = document.createElement('canvas').getContext('2d'), s = 'Рукопись wmWM 0123';
    x.font = '40px monospace'; const a = x.measureText(s).width; x.font = `40px ${HAND}, monospace`; handOK = Math.abs(x.measureText(s).width - a) > .5 } catch (e) { handOK = false }
  return handOK;
}
const fonts = () => D.fonts || {};
function font(role) { // → [семейство, курсив-замена]
  const F = fonts();
  if (role === 'hand') return handAvail() ? [HAND + ', cursive', false] : [F.body || 'sans-serif', true];
  return [F[role] || role || F.body || 'sans-serif', false];
}
const MC = document.createElement('canvas').getContext('2d'), mcache = new Map();
function textW(s, px, fam, wt, it) {
  const k = s + '|' + px.toFixed(1) + '|' + fam + wt + it; let v = mcache.get(k);
  if (v === undefined) { MC.font = `${it ? 'italic ' : ''}${wt || 400} ${px}px ${fam}`; v = MC.measureText(s).width; if (mcache.size > 5000) mcache.clear(); mcache.set(k, v) }
  return v;
}
function fmtNum(v, dec, fmt) { // 1200 → «1200», 12500 → «12 500», 3.5 → «3,5»
  let s = (+v).toFixed(dec || 0);
  if (Math.abs(+v) >= 10000) { const [a, b] = s.split('.'); s = a.replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + (b ? '.' + b : '') }
  if (String((window.DC && DC.data && DC.data.lang) || 'ru').startsWith('en')) return (fmt || '{v}').replace('{v}', s.replace(/ /g, ',').replace('-', '−')); // en: 12,500 · 3.5
  return (fmt || '{v}').replace('{v}', s.replace('.', ',').replace('-', '−'));
}

/* ---------- стили ---------- */
const STY = {
  blueprint: { c: 'code_ink', lw: 1.1, jit: 0, op: 1, font: 'mono', wt: 400 },
  ink: { c: 'ink', lw: 1.8, jit: 1.05, op: 1, font: 'hand', wt: 600 },
  marker: { c: 'accent', lw: 5.5, jit: .8, op: .62, font: 'hand', wt: 700, blend: 'multiply' },
  riso: { c: 'ink', c2: 'accent', lw: 3.4, jit: .45, op: .95, font: 'head', wt: 700, blend: 'multiply', off: [3.4, 2.6] },
  chalk: { c: 'ink', lw: 2.8, jit: 1.6, op: .9, font: 'hand', wt: 600, chalk: true },
};
REG._styles = STY;

/* ---------- геометрия (дюймы) ---------- */
const G = {
  arc(cx, cy, rx, ry, a0, a1, n) { n = n || Math.max(6, Math.ceil(Math.abs(a1 - a0) / 3)); const o = []; for (let i = 0; i <= n; i++) { const a = (a0 + (a1 - a0) * i / n) * RAD; o.push([cx + rx * Math.cos(a), cy + ry * Math.sin(a)]) } return o },
  quad(p0, c, p1, n = 24) { const o = []; for (let i = 0; i <= n; i++) { const t = i / n, a = (1 - t) * (1 - t), b = 2 * t * (1 - t), d = t * t; o.push([a * p0[0] + b * c[0] + d * p1[0], a * p0[1] + b * c[1] + d * p1[1]]) } return o },
  cubic(p0, p1, p2, p3, n = 28) { const o = []; for (let i = 0; i <= n; i++) { const t = i / n, a = (1 - t) ** 3, b = 3 * t * (1 - t) ** 2, c = 3 * t * t * (1 - t), d = t ** 3; o.push([a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]]) } return o },
  smooth(P, closed, n = 12) { // Катмулл–Ром через точки (кривая Безье через точки)
    if (P.length < 3) return P.map(p => p.slice());
    const pts = closed ? P.concat([P[0]]) : P, m = pts.length, out = [], L = P.length;
    const g = i => closed ? P[((i % L) + L) % L] : pts[Math.max(0, Math.min(m - 1, i))];
    for (let i = 0; i < m - 1; i++) { const p0 = g(i - 1), p1 = pts[i], p2 = pts[i + 1], p3 = g(i + 2);
      for (let j = 0; j < n; j++) { const t = j / n, t2 = t * t, t3 = t2 * t, f = k => .5 * (2 * p1[k] + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2 + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3);
        out.push([f(0), f(1)]) } }
    out.push(pts[m - 1].slice()); return out;
  },
  rect(x, y, w, h) { return [[x, y], [x + w, y], [x + w, y + h], [x, y + h], [x, y]] },
  circ(c, r, n = 24) { const o = []; for (let i = 0; i < n; i++) { const a = i / n * 2 * Math.PI; o.push([c[0] + r * Math.cos(a), c[1] + r * Math.sin(a)]) } return o },
};
function cutStart(P, d) {
  let acc = 0;
  for (let i = 1; i < P.length; i++) { const a = P[i - 1], b = P[i], s = Math.hypot(b[0] - a[0], b[1] - a[1]);
    if (acc + s >= d) { const f = s ? (d - acc) / s : 0; return [[lerp(a[0], b[0], f), lerp(a[1], b[1], f)]].concat(P.slice(i)) } acc += s }
  const e = P[P.length - 1]; return [e.slice(), e.slice()];
}
function trim(P, d0, d1) { let Q = P; if (d0 > 0) Q = cutStart(Q, d0); if (d1 > 0) Q = cutStart(Q.slice().reverse(), d1).reverse(); return Q }
function polyLen(P) { let L = 0; for (let i = 1; i < P.length; i++) L += Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]); return L }

/* ---------- части ---------- */
const S = (pts, win, o) => Object.assign({ t: 's', pts, win }, o);            // штрих
const F = (pts, win, o) => Object.assign({ t: 'f', pts, win }, o);            // заливка
const X = (s, x, y, win, o) => Object.assign({ t: 'x', s: String(s), x, y, win }, o); // подпись
function txt(sp, key, fn) { // строка параметра → части; при Morph разных строк (_interp) — две части с долями 1−t и t
  const s = sp[key], pv = sp['~' + key], t = sp['~t'] ?? 1;
  if (pv !== undefined && pv !== null && pv !== '' && String(pv) !== String(s ?? '')) return fn(String(pv), 1 - t).concat(s === undefined || s === null || s === '' ? [] : fn(String(s), t));
  if (s === undefined || s === null || s === '') return [];
  return fn(String(s), 1);
}
function heads(out, P, a, b, c, win, wk = 1) { // наконечники: tri | dim | open | dot | tick; возвращает укороченный стержень
  const w = c.lw * wk, hl = Math.min(.07 + Math.min(w, .03) * 4, polyLen(P) * .42);
  const one = (type, atEnd) => {
    const Q = atEnd ? P : P.slice().reverse(), tip = Q[Q.length - 1], bk = cutStart(Q.slice().reverse(), hl)[0];
    let ux = tip[0] - bk[0], uy = tip[1] - bk[1]; const L = Math.hypot(ux, uy) || 1; ux /= L; uy /= L; const nx = -uy, ny = ux;
    const at = (s, n) => [tip[0] - ux * s * hl + nx * n * hl, tip[1] - uy * s * hl + ny * n * hl];
    if (type === 'tri' || type === 'dim' || type === 'triangle' || type === 'arrow') { const hw = type === 'dim' ? .22 : .36;
      out.push(F([tip.slice(), at(1, hw), at(.78, 0), at(1, -hw)], win, { reveal: 'pop', pivot: tip.slice() })); return hl * .7 }
    if (type === 'open') { out.push(S([at(1, .42), tip.slice(), at(1, -.42)], win, { wk, jit: .4 })); return 0 }
    if (type === 'dot' || type === 'oval') { const r = Math.min(Math.max(w * 2, .024), .065); out.push(F(G.circ(tip, r, 18), win, { reveal: 'pop', pivot: tip.slice() })); return r * .5 }
    if (type === 'tick') { const vx = (ux + nx) * .7071, vy = (uy + ny) * .7071, s = hl * .55; out.push(S([[tip[0] - vx * s, tip[1] - vy * s], [tip[0] + vx * s, tip[1] + vy * s]], win, { wk: wk * 1.6, jit: 0 })); return 0 }
    return 0;
  };
  const d0 = a ? one(a, false) : 0, d1 = b ? one(b, true) : 0;
  return trim(P, d0, d1);
}

/* ---------- виды ---------- */
const BLD = {};
BLD.line = (sp, c) => { // линия, ломаная, кривая через точки; start/end — наконечники
  let P = (sp.pts || []).map(p => p.slice()); if (P.length < 2) return [];
  if (sp.curve) P = G.smooth(P, sp.closed); else if (sp.closed) P.push(P[0].slice());
  const hd = [], has = !!(sp.start || sp.end), sh = heads(hd, P, sp.start, sp.end, c, [.84, 1]);
  return [S(sh, [0, has ? .86 : 1], { dash: sp.dash })].concat(hd);
};
BLD.arrow = (sp, c) => { // прямая | дуга (bend) | «от руки» (hand) | ломаная (via); одинарная/двойная
  const a = sp.p0, b = sp.p1, dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1, nx = dy / L, ny = -dx / L;
  let P;
  if (sp.via && sp.via.length) P = [a].concat(sp.via, [b]).map(p => p.slice());
  else if (sp.hand) { const r = U.rng((sp.seed ?? 1) * 7 + 3), k1 = (r() - .5) * .2 + (sp.bend || 0) * 1.3, k2 = (r() - .5) * .2 + (sp.bend || 0) * 1.3;
    P = G.cubic(a, [a[0] + dx * .3 + nx * L * k1, a[1] + dy * .3 + ny * L * k1], [a[0] + dx * .7 + nx * L * k2, a[1] + dy * .7 + ny * L * k2], b, 32) }
  else if (sp.bend) P = G.quad(a, [(a[0] + b[0]) / 2 + nx * L * sp.bend * 2, (a[1] + b[1]) / 2 + ny * L * sp.bend * 2], b, 32);
  else P = [a.slice(), b.slice()];
  const hd = [], head = sp.head || 'tri', sh = heads(hd, P, sp.double ? head : null, head, c, [.8, 1]);
  return [S(sh, [0, .82], { jit: sp.hand ? 1.7 : 1 })].concat(hd);
};
BLD.dim = (sp, c) => { // размерная линия: выносные → линия со стрелками (от середины) → подпись
  const v = sp.dir === 'v', a = sp.a, b = sp.b, at = sp.at, over = sp.over ?? .08, gap = .04;
  const base = sp.base ?? (at + (sp.ext ?? .25)), s = Math.sign(at - base) || -1;
  const P = (u, w) => v ? [w, u] : [u, w], mid = (a + b) / 2;
  const parts = [S([P(a, base + s * gap), P(a, at + s * over)], [0, .3], { wk: .7 }), S([P(b, base + s * gap), P(b, at + s * over)], [0, .3], { wk: .7 })];
  const hd = [], e = sp.ends || 'arrow', ht = e === 'arrow' ? 'dim' : e;
  const s1 = heads(hd, [P(mid, at), P(a, at)], null, ht, c, [.66, .8]), s2 = heads(hd, [P(mid, at), P(b, at)], null, ht, c, [.66, .8]);
  parts.push(S(s1, [.28, .7]), S(s2, [.28, .7]), ...hd);
  const sz = sp.sz ?? 12, lab = Object.assign({}, sp);
  if (sp.value !== undefined && sp.value !== null) { lab.label = fmtNum(c.val ?? sp.value, sp.dec, sp.fmt); delete lab['~label'] }
  const tp = v ? [at - gap - sz * PT * .55, mid] : [mid, at - gap - sz * PT * .55];
  return parts.concat(txt(lab, 'label', (s0, al) => [X(s0, tp[0], tp[1], [.74, 1], { sz, anchor: 'middle', va: 'm', rot: v ? -90 : 0, a: al })]));
};
BLD.balloon = (sp, c) => { // выноска-номер: точка → линия → кружок → номер
  const A = sp.anchor, B = sp.at, r = sp.r ?? .2, dx = A[0] - B[0], dy = A[1] - B[1], L = Math.hypot(dx, dy) || 1, ang = Math.atan2(dy, dx) / RAD;
  const att = [B[0] + dx / L * r, B[1] + dy / L * r];
  return [F(G.circ(A, Math.min(Math.max(c.lw * 1.8, .025), .06), 18), [0, .12], { reveal: 'pop', pivot: A.slice() }),
    S([A.slice(), att], [.08, .45], { wk: .8 }), S(G.arc(B[0], B[1], r, r, ang, ang + 360, 72), [.42, .85])]
    .concat(txt(sp, 'num', (s, al) => [X(s, B[0], B[1], [.78, 1], { sz: sp.sz ?? r * 72 * .95, anchor: 'middle', va: 'm', reveal: 'pop', a: al })]));
};
BLD.leader = (sp, c) => { // полка-выноска: метка у точки → линия → полка → подпись над полкой
  const A = sp.anchor, E = sp.elbow, sh = sp.shelf ?? 1, R = [E[0] + sh, E[1]], end = sp.end ?? 'dot', parts = [], hd = [];
  let line = [A.slice(), E.slice()];
  if (end === 'dot') parts.push(F(G.circ(A, Math.min(Math.max(c.lw * 1.8, .025), .06), 18), [0, .1], { reveal: 'pop', pivot: A.slice() }));
  else if (end && end !== 'none') line = heads(hd, [E.slice(), A.slice()], null, end === 'arrow' ? 'tri' : end, c, [0, .14]).reverse();
  parts.push(S(line, [.06, .4], { wk: .85 }), S([E.slice(), R], [.38, .58], { wk: .85 }), ...hd);
  const sz = sp.sz ?? 13, x = E[0] + (sh >= 0 ? .05 : -.05), an = sh >= 0 ? 'start' : 'end';
  return parts.concat(txt(sp, 'text', (s, al) => [X(s, x, E[1] - .05, [.56, .92], { sz, anchor: an, va: 'b', reveal: 'write', a: al })]),
    txt(sp, 'sub', (s, al) => [X(s, x, E[1] + .05, [.8, 1], { sz: sz * .8, anchor: an, va: 't', a: al * .8 })]));
};
BLD.brace = (sp, c) => { // фигурная / квадратная скобка: растёт от середины, затем подпись
  const a = sp.p0, b = sp.p1, dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1, ux = dx / L, uy = dy / L;
  const side = sp.side ?? 1, nx = uy * side, ny = -ux * side, d = sp.depth ?? .22;
  const M = (u, w) => [a[0] + ux * u + nx * w, a[1] + uy * u + ny * w];
  let half;
  if (sp.form === 'square') half = [[L / 2, d], [0, d], [0, 0]];
  else { const r = Math.min(d / 2, L / 4);
    half = G.cubic([L / 2, d], [L / 2, d * .72], [L / 2 - r * .45, d / 2], [L / 2 - r, d / 2], 10).concat([[r, d / 2]], G.cubic([r, d / 2], [r * .45, d / 2], [0, d * .22], [0, 0], 10)) }
  const h1 = half.map(([u, w]) => M(u, w)), h2 = half.map(([u, w]) => M(L - u, w));
  const parts = [S(h1, [0, .7]), S(h2, [0, .7])], sz = sp.sz ?? 13, tip = M(L / 2, d + .07);
  const horiz = Math.abs(nx) > Math.abs(ny);
  const o = horiz ? { anchor: nx > 0 ? 'start' : 'end', va: 'm' } : { anchor: 'middle', va: ny < 0 ? 'b' : 't' };
  return parts.concat(txt(sp, 'label', (s, al) => s.split('\n').map((ln, i, A) => X(ln, tip[0], tip[1] + (horiz ? (i - (A.length - 1) / 2) : ny < 0 ? i - (A.length - 1) : i) * sz * PT * 1.25, [.62 + .3 * i / A.length, .9 + .1 * i / A.length], Object.assign({ sz, reveal: 'write', a: al }, o)))));
};
BLD.hatch = (sp, c) => { // штриховка | клетка | сетка | растр точками внутри прямоугольника или контура
  const poly = sp.pts && sp.pts.length > 2 ? sp.pts.map(p => p.slice()) : G.rect(...sp.box).slice(0, 4);
  const xs = poly.map(p => p[0]), ys = poly.map(p => p[1]), x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const parts = [], pat = sp.pattern || 'hatch', step = Math.max(.03, sp.step || .12), ang = sp.angle ?? 45;
  parts.clips = { k: poly };
  const fams = pat === 'cross' ? [ang, ang + 90] : pat === 'grid' ? [ang % 90 === 45 ? 0 : ang, (ang % 90 === 45 ? 0 : ang) + 90] : pat === 'dots' ? [] : [ang];
  const lines = [];
  for (const th of fams) {
    const ux = Math.cos(th * RAD), uy = Math.sin(th * RAD), nx = -uy, ny = ux, cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    const pr = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]].map(([x, y]) => (x - cx) * nx + (y - cy) * ny), m0 = Math.min(...pr), m1 = Math.max(...pr);
    for (let m = m0 + ((m1 - m0) % step) / 2; m <= m1 + 1e-9; m += step) {
      const px = cx + nx * m, py = cy + ny * m; let t0 = -1e9, t1 = 1e9; // отрезок прямой внутри габарита (Лянг–Барски)
      for (const [p, q] of [[-ux, px - x0], [ux, x1 - px], [-uy, py - y0], [uy, y1 - py]]) { if (Math.abs(p) < 1e-12) { if (q < 0) t1 = -1e9; continue } const r = q / p; if (p < 0) t0 = Math.max(t0, r); else t1 = Math.min(t1, r) }
      if (t1 > t0 + 1e-6) lines.push([[px + ux * t0, py + uy * t0], [px + ux * t1, py + uy * t1]]);
    }
  }
  lines.forEach((ln, i) => { const t0 = .22 + .62 * i / Math.max(1, lines.length); parts.push(S(ln, [t0, Math.min(1, t0 + .16)], { wk: .55, clip: 'k', a: .9 })) });
  if (pat === 'dots') parts.push({ t: 'pat', clip: 'k', box: [x0, y0, x1 - x0, y1 - y0], step, r: sp.r ?? step * .27, win: [.25, 1] });
  if (sp.outline !== false) parts.push(S(poly.concat([poly[0].slice()]), [0, .35]));
  return parts;
};
BLD.highlight = (sp, c) => { // маркер-выделение: 1–3 полупрозрачных мазка с неровным краем (multiply)
  const [x, y, w, h] = sp.box, n = Math.max(1, sp.passes ?? 2), r = U.rng((sp.seed ?? 1) * 13 + 5), parts = [], bw = h / n * 1.3;
  for (let i = 0; i < n; i++) {
    const yy = y + h * (i + .5) / n + (r() - .5) * h * .06, xa = x - .05 + r() * .05, xb = x + w + .04 - r() * .07, tilt = (r() - .5) * h * .1, sl = bw * .28, M = 18;
    const top = [], bot = [];
    for (let j = 0; j <= M; j++) { const t = j / M, xx = lerp(xa, xb, t), yc = yy + tilt * (2 * t - 1);
      top.push([xx + sl * .5, yc - bw / 2 + (r() - .5) * bw * .07]); bot.push([xx - sl * .5, yc + bw / 2 + (r() - .5) * bw * .07]) }
    parts.push(F(top.concat(bot.reverse()), [i / n, (i + 1) / n], { reveal: 'wipe', dir: i % 2 ? '-x' : 'x', aa: sp.a ?? .45, blend: 'multiply', noriso: true }));
  }
  return parts;
};
BLD.scribble = (sp, c) => { // подчёркивание-каракуля: wave | zigzag | loops | double
  const x0 = sp.x0, x1 = sp.x1, y = sp.y, A = sp.amp ?? .06, L = x1 - x0, r = U.rng((sp.seed ?? 1) * 17 + 1), k = sp.form || 'wave';
  let P = [];
  if (k === 'zigzag') { const st = A * 1.4; let i = 0; for (let x = x0; x < x1 + st * .5; x += st * (.8 + r() * .4), i++) P.push([Math.min(x, x1), y + (i % 2 ? A : -A) * (.7 + r() * .35)]) }
  else if (k === 'loops') { const R = A * 1.1, n = Math.max(3, Math.round(L / (R * 2.2))), M = n * 24; for (let j = 0; j <= M; j++) { const t = j / M * n * 2 * Math.PI; P.push([x0 + L * j / M - R * .9 * Math.sin(t), y - R * .8 * Math.cos(t) + R * .4]) } }
  else if (k === 'double') { P = G.quad([x0, y], [(x0 + x1) / 2, y + A * .5], [x1, y - A * .3], 20) }
  else { const n = Math.max(2, L / (A * 3.4)), M = Math.ceil(n * 16), ph = r() * 6; for (let j = 0; j <= M; j++) { const t = j / M; P.push([x0 + L * t, y + A * Math.sin(t * n * 2 * Math.PI + ph) * (.65 + .35 * Math.sin(t * 7 + ph))]) } }
  const parts = [S(P, k === 'double' ? [0, .55] : [0, 1], { wk: 1.15 })];
  if (k === 'double') parts.push(S(G.quad([x0 + L * .05, y + A * 1.6], [(x0 + x1) / 2, y + A * 1.9], [x1 - L * .03, y + A * 1.2], 20), [.45, 1], { wk: 1.15 }));
  return parts;
};
BLD.encircle = (sp, c) => { // обвести от руки: неровный овал с заходом конца за начало
  const [x, y, w, h] = sp.box, pad = sp.pad ?? .12, cx = x + w / 2, cy = y + h / 2, rx = w / 2 + pad, ry = h / 2 + pad * .85;
  const r = U.rng((sp.seed ?? 1) * 19 + 7), turns = sp.turns ?? 1.12, a0 = -160 + (r() - .5) * 30, tilt = (r() - .5) * 7 * RAD;
  const M = Math.ceil(110 * turns), ph = r() * 6, ph2 = r() * 6, P = [];
  for (let j = 0; j <= M; j++) { const t = j / M, a = (a0 + 360 * turns * t) * RAD, k = 1 + .035 * Math.sin(2 * a + ph) + .02 * Math.sin(3 * a + ph2) + .07 * (t - .5);
    const px = rx * k * Math.cos(a), py = ry * k * Math.sin(a); P.push([cx + px * Math.cos(tilt) - py * Math.sin(tilt), cy + px * Math.sin(tilt) + py * Math.cos(tilt)]) }
  return [S(P, [0, 1], { jit: .8, wk: 1.15 })];
};
BLD.mark = (sp, c) => { // галочка | крест | звёздочка-пометка (asterisk) | звезда одним росчерком
  const [cx, cy] = sp.pos, s = sp.size ?? .4, m = sp.mark || 'check', p = (u, v) => [cx + u * s, cy + v * s];
  if (m === 'cross') return [S([p(-.38, -.36), p(.4, .38)], [0, .5], { wk: 1.4 }), S([p(.37, -.4), p(-.38, .4)], [.5, 1], { wk: 1.4 })];
  if (m === 'asterisk') return [90, 30, 150].map((a, i) => { const ux = Math.cos(a * RAD) * .46, uy = Math.sin(a * RAD) * .46; return S([p(-ux, -uy), p(ux, uy)], [i / 3, (i + 1) / 3], { wk: 1.3 }) });
  if (m === 'star') return [S([0, 2, 4, 1, 3, 0].map(k => p(.5 * Math.cos((-90 + 72 * k) * RAD), .5 * Math.sin((-90 + 72 * k) * RAD))), [0, 1], { wk: 1.2 })];
  return [S([p(-.42, -.02), p(-.13, .3)].concat(G.quad(p(-.13, .3), p(.06, -.06), p(.46, -.42), 14).slice(1)), [0, 1], { wk: 1.45 })];
};
BLD.stamp = (sp, c) => { // печать: круглая (кольца + текст по кругу + середина) или прямоугольный штамп в рамке
  const parts = [], hf = { font: 'head', wt: 700 };
  if (sp.form === 'rect') {
    const [x, y, w, h] = sp.box, i = Math.min(w, h) * .09, sz = sp.sz ?? h * 72 * .3;
    parts.push(S(G.rect(x, y, w, h), [0, .3], { wk: 1.7 }), S(G.rect(x + i, y + i, w - 2 * i, h - 2 * i), [.15, .45], { wk: .8 }));
    parts.push(...txt(sp, 'center', (s, al) => [X(s, x + w / 2, y + h / 2 - (sp.sub ? h * .1 : 0), [.45, .85], Object.assign({ sz, anchor: 'middle', va: 'm', a: al, ls: .06 }, hf))]),
      ...txt(sp, 'sub', (s, al) => [X(s, x + w / 2, y + h * .74, [.6, 1], { sz: sz * .42, anchor: 'middle', va: 'm', a: al, font: 'mono' })]));
  } else {
    const [cx, cy] = sp.pos, R = sp.r ?? .8, sz = sp.sz ?? R * 72 * .3;
    parts.push(S(G.arc(cx, cy, R, R, -90, 270, 96), [0, .3], { wk: 1.7 }), S(G.arc(cx, cy, R * .74, R * .74, -90, 270, 80), [.15, .42], { wk: .85 }));
    parts.push(...txt(sp, 'text', (s, al) => [Object.assign({ t: 'tp', s, cx, cy, r: R * .8, sz: sp.tsz ?? R * 72 * .165, win: [.35, .8], a: al, start: 128 }, hf)]));
    parts.push(...txt(sp, 'center', (s, al) => s.split('\n').map((ln, i, A) => X(ln, cx, cy + (i - (A.length - 1) / 2) * sz * PT * 1.1 - (sp.sub ? R * .1 : 0), [.5, .9], Object.assign({ sz, anchor: 'middle', va: 'm', a: al }, hf)))),
      ...txt(sp, 'sub', (s, al) => [X(s, cx, cy + R * .42, [.65, 1], { sz: sz * .42, anchor: 'middle', va: 'm', a: al, font: 'mono' })]));
    parts.push(F(G.circ([cx - R * .87, cy], R * .035, 10), [.3, .4], { reveal: 'pop', pivot: [cx - R * .87, cy] }), F(G.circ([cx + R * .87, cy], R * .035, 10), [.3, .4], { reveal: 'pop', pivot: [cx + R * .87, cy] }));
  }
  parts.forEach(p => { p.blend = 'multiply' });
  parts.wear = sp.wear !== false;
  return parts;
};
BLD.sticker = (sp, c) => { // стикер: лист с тенью (поворот — у объекта), текст пишется
  const [x, y, w, h] = sp.box, cu = Math.min(w, h) * (sp.curl ?? .07), pad = Math.min(w, h) * .1, cxy = [x + w / 2, y + h / 2];
  const paper = [[x, y], [x + w, y], [x + w, y + h - cu * 3]].concat(G.quad([x + w, y + h - cu * 3], [x + w - cu * .3, y + h - cu * .3], [x + w - cu * 3, y + h], 10).slice(1), [[x, y + h]]);
  const parts = [F(paper, [0, .3], { c: col(sp.paper, 'accent3/30'), reveal: 'pop', pivot: cxy, aa: 1, noriso: true, shadow: 'drop-shadow(0 6px 7px rgba(25,20,10,.22))', blend: '' }),
    F([[x + w, y + h - cu * 3], [x + w - cu * 3, y + h], [x + w - cu * 1.3, y + h - cu * 1.3]], [0, .3], { c: '#000000', aa: .07, reveal: 'pop', pivot: cxy, noriso: true, blend: '' })];
  if (sp.tape) { const tw = Math.min(w * .45, 1.1), th = .26, tx = x + w / 2 - tw / 2, ty = y - th * .55, k = -.04;
    parts.push(F([[tx, ty + tw * k * -.5], [tx + tw, ty + tw * k * .5], [tx + tw, ty + th + tw * k * .5], [tx, ty + th - tw * k * .5]], [.25, .4], { c: col(sp.tapeC, 'accent3'), aa: .5, blend: 'multiply', reveal: 'wipe', noriso: true })) }
  const sz = sp.sz ?? 18, lh = sz * PT * 1.22;
  parts.push(...txt(sp, 'text', (s, al) => { const L = s.split('\n'); return L.map((ln, i) => X(ln, x + pad, y + pad + lh * (i + .5), [.35 + .6 * i / L.length, .35 + .6 * (i + 1) / L.length], { sz, anchor: 'start', va: 'm', reveal: 'write', a: al, font: sp.font })) }));
  return parts;
};
BLD.tape = (sp, c) => { // полоска скотча с рваными краями (multiply), разматывается слева направо
  const [x, y, w, h] = sp.box, r = U.rng((sp.seed ?? 1) * 29 + 1), z = Math.min(.05, w * .06), n = 6, P = [[x, y], [x + w, y]];
  for (let i = 1; i < n; i++) P.push([x + w - (i % 2 ? z : 0) - r() * z * .4, y + h * i / n]);
  P.push([x + w, y + h], [x, y + h]);
  for (let i = n - 1; i > 0; i--) P.push([x + (i % 2 ? z : 0) + r() * z * .4, y + h * i / n]);
  return [F(P, [0, 1], { reveal: 'wipe', aa: sp.a ?? .5, blend: 'multiply', noriso: true })];
};
BLD.gost = (sp, c) => { // рамка листа + основная надпись (форма 1, 185×55 условных мм)
  const [x, y, w, h] = sp.box, bw = sp.bw ?? 4.4, u = bw / 185, bx = x + w - bw, by = y + h - 55 * u, parts = [];
  const L = (a, b, cc, d) => [[bx + a * u, by + b * u], [bx + cc * u, by + d * u]];
  parts.push(S(G.rect(x, y, w, h), [0, .38], { wk: 1.5 }));
  const thick = [L(0, 0, 185, 0), L(0, 0, 0, 55), L(65, 0, 65, 55), L(65, 15, 185, 15), L(135, 15, 135, 55), L(0, 25, 65, 25), L(0, 30, 65, 30), L(65, 40, 185, 40), L(135, 20, 185, 20), L(135, 35, 185, 35)];
  const thin = [L(7, 0, 7, 30), L(17, 0, 17, 55), L(40, 0, 40, 55), L(55, 0, 55, 55), L(140, 20, 140, 35), L(145, 20, 145, 35), L(150, 15, 150, 35), L(167, 15, 167, 35), L(155, 35, 155, 40)];
  for (const yy of [5, 10, 15, 20, 35, 40, 45, 50]) thin.push(L(0, yy, 65, yy));
  thick.forEach((ln, i) => parts.push(S(ln, [.3 + .25 * i / thick.length, .42 + .25 * i / thick.length], { wk: 1.25 })));
  thin.forEach((ln, i) => parts.push(S(ln, [.4 + .25 * i / thin.length, .5 + .25 * i / thin.length], { wk: .55 })));
  const ts = [], T = (key, ux, uy, mm, o = {}) => ts.push([key, bx + ux * u, by + uy * u, mm * u * 72 * 1.1, o]);
  ['Изм.', 'Лист', '№ докум.', 'Подп.', 'Дата'].forEach((s, i) => T('=' + gl(s), [3.5, 12, 28.5, 47.5, 60][i], 27.5, 2.6, { anchor: 'middle' }));
  ['Разраб.', 'Пров.', 'Т.контр.', 'Н.контр.', 'Утв.'].forEach((s, i) => T('=' + gl(s), 1, 32.5 + 5 * i, 2.6, { anchor: 'start' }));
  (sp.rows || []).slice(0, 5).forEach((r, i) => { if (r && r[0]) T('=' + r[0], 18, 32.5 + 5 * i, 2.6, { anchor: 'start' }); if (r && r[1]) T('=' + r[1], 60, 32.5 + 5 * i, 2.2, { anchor: 'middle' }) });
  T('code', 125, 7.5, 5.2, { anchor: 'middle', wt: 700 }); T('title', 100, 27.5, 4.4, { anchor: 'middle', wt: 700 }); T('material', 100, 47.5, 3.2, { anchor: 'middle' });
  T('=' + gl('Лит.'), 142.5, 17.5, 2.6, { anchor: 'middle' }); T('=' + gl('Масса'), 158.5, 17.5, 2.6, { anchor: 'middle' }); T('=' + gl('Масштаб'), 176, 17.5, 2.6, { anchor: 'middle' });
  T('lit', 142.5, 27.5, 3.4, { anchor: 'middle' }); T('mass', 158.5, 27.5, 3.4, { anchor: 'middle' }); T('scale', 176, 27.5, 3.4, { anchor: 'middle' });
  T('=' + gl('Лист') + ' ' + (sp.sheet ?? 1), 137, 37.5, 2.6, { anchor: 'start' }); T('=' + gl('Листов') + ' ' + (sp.sheets ?? 1), 157, 37.5, 2.6, { anchor: 'start' }); T('org', 160, 47.5, 3.4, { anchor: 'middle', wt: 700 });
  ts.forEach(([key, tx, ty, sz, o], i) => { const w0 = .6 + .32 * i / ts.length, win = [w0, Math.min(1, w0 + .12)], base = Object.assign({ sz, va: 'm', it: true }, o);
    if (key[0] === '=') parts.push(X(key.slice(1), tx, ty, win, base));
    else parts.push(...txt(sp, key, (s, al) => s.split('\n').map((ln, j, A) => X(ln, tx, ty + (j - (A.length - 1) / 2) * sz * PT * 1.15, win, Object.assign({}, base, { a: al }))))) });
  return parts;
};
BLD.ruler = (sp, c) => { // линейка/шкала с делениями и подписями
  const [x, y] = sp.at, len = sp.len, vert = !!sp.vertical, side = sp.side ?? 1, v0 = sp.v0 ?? 0, v1 = sp.v1 ?? 10;
  const major = sp.major || 1, minor = Math.max(1, Math.round(sp.minor ?? 5)), P = (s, d) => vert ? [x + d * side, y + s] : [x + s, y + d * side];
  const parts = [S([P(0, 0), P(len, 0)], [0, .3])], n = Math.max(1, Math.round((v1 - v0) / major * minor)), sz = sp.sz ?? 10;
  for (let i = 0; i <= n; i++) {
    const val = v0 + (v1 - v0) * i / n, s = len * i / n, maj = i % minor === 0 || i === n, half = minor % 2 === 0 && i % (minor / 2) === 0;
    const tl = maj ? .16 : half ? .11 : .065, w0 = .2 + .45 * i / n;
    parts.push(S([P(s, 0), P(s, tl)], [w0, w0 + .08], { wk: maj ? .9 : .6 }));
    if (maj && sp.labels !== false) { const q = P(s, .16 + .05 + sz * PT * .6), lab = fmtNum(val, sp.dec, null) + (i === n && sp.unit ? ' ' + sp.unit : '');
      parts.push(X(lab, q[0], q[1], [.45 + .45 * i / n, Math.min(1, .55 + .45 * i / n)], { sz, anchor: vert ? (side > 0 ? 'start' : 'end') : 'middle', va: 'm', font: c.sty.font === 'hand' ? 'hand' : 'mono' })) }
  }
  return parts;
};
BLD.gauge = (sp, c) => { // спидометр / дуговая шкала: дуга → зоны → деления → числа → стрелка доезжает до значения
  const [cx, cy] = sp.pos, R = sp.r, vmin = sp.vmin ?? 0, vmax = sp.vmax ?? 100, a0 = sp.a0 ?? 150, sw = sp.sweep ?? 240;
  const val = clamp(c.val ?? sp.value ?? vmin, Math.min(vmin, vmax), Math.max(vmin, vmax)), ang = v => a0 + sw * (v - vmin) / ((vmax - vmin) || 1);
  const parts = [S(G.arc(cx, cy, R, R, a0, a0 + sw, 80), [0, .3], { wk: 1.1 })];
  (sp.zones || []).forEach(([f, t, zc], i) => parts.push(S(G.arc(cx, cy, R * .9, R * .9, ang(f), ang(t), 40), [.2 + .05 * i, .45], { w: R * .07, c: zc, cap: 'butt', aa: .85, noriso: true, jit: 0 })));
  const major = Math.max(1, Math.round(sp.major ?? 5)), minor = Math.max(1, Math.round(sp.minor ?? 4)), n = major * minor, sz = sp.sz ?? R * 72 * .13;
  for (let i = 0; i <= n; i++) { const a = ang(vmin + (vmax - vmin) * i / n) * RAD, maj = i % minor === 0, r1 = R * (maj ? .8 : .87), w0 = .25 + .3 * i / n;
    parts.push(S([[cx + Math.cos(a) * R * .97, cy + Math.sin(a) * R * .97], [cx + Math.cos(a) * r1, cy + Math.sin(a) * r1]], [w0, w0 + .08], { w: Math.min(c.lw * (maj ? .9 : .55), R * (maj ? .035 : .02)), jit: .4 }));
    if (maj) parts.push(X(fmtNum(vmin + (vmax - vmin) * i / n, sp.ldec ?? 0), cx + Math.cos(a) * R * .66, cy + Math.sin(a) * R * .66, [.4 + .25 * i / n, .55 + .25 * i / n], { sz, anchor: 'middle', va: 'm', font: c.sty.font === 'hand' ? 'hand' : 'mono' })) }
  const nc = col(sp.needle, 'accent'), spin = { cx, cy, a0: ang(vmin), a1: ang(val), win: [.62, .95], role: 'needle' };
  parts.push(F([[cx - R * .15, cy - R * .028], [cx + R * .8, cy - R * .007], [cx + R * .83, cy], [cx + R * .8, cy + R * .007], [cx - R * .15, cy + R * .028]], [.58, .63], { c: nc, spin, noriso: false }));
  parts.push(F(G.circ([cx, cy], R * .065, 20), [.6, .66], { c: nc, reveal: 'pop', pivot: [cx, cy] }));
  parts.push(X('', cx, cy + R * .4, [.6, .64], { sz: sp.vsz ?? R * 72 * .22, anchor: 'middle', va: 'm', wt: 700, count: { a: vmin, b: val, dec: sp.dec ?? 0, fmt: sp.fmt, win: [.62, .95] }, s0: fmtNum(val, sp.dec ?? 0, sp.fmt) }));
  return parts.concat(txt(sp, 'label', (s, al) => [X(s, cx, cy + R * .64, [.7, 1], { sz: sz * .95, anchor: 'middle', va: 'm', a: al * .85 })]));
};
const ROMAN = ['XII', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI'];
BLD.clock = (sp, c) => { // циферблат: обод → деления → цифры → часовая, минутная, секундная стрелки
  const [cx, cy] = sp.pos, R = sp.r, t = c.val ?? sp.t ?? 600, parts = [];
  if (sp.fill) parts.push(F(G.circ([cx, cy], R, 64), [0, .3], { c: sp.fill, aa: 1, noriso: true, blend: '' }));
  parts.push(S(G.arc(cx, cy, R, R, -90, 270, 96), [0, .3], { wk: 1.3 }));
  for (let i = 0; i < 60; i++) { const a = (i * 6 - 90) * RAD, h = i % 5 === 0, r1 = R * (h ? .84 : .92), w0 = .15 + .4 * i / 60;
    parts.push(S([[cx + Math.cos(a) * R * .97, cy + Math.sin(a) * R * .97], [cx + Math.cos(a) * r1, cy + Math.sin(a) * r1]], [w0, w0 + .06], { w: Math.min(c.lw * (h ? 1.1 : .45), R * (h ? .035 : .015)), jit: .3 })) }
  if (sp.numerals !== false) for (let i = 0; i < 12; i++) { const a = (i * 30 - 90) * RAD, w0 = .35 + .3 * i / 12;
    parts.push(X(sp.numerals === 'roman' ? ROMAN[i] : String(i || 12), cx + Math.cos(a) * R * .7, cy + Math.sin(a) * R * .7, [w0, w0 + .12], { sz: sp.sz ?? R * 72 * .17, anchor: 'middle', va: 'm' })) }
  const ha = ((t / 60) % 12) * 30 - 90, ma = (t % 60) * 6 - 90;
  const hand = (len, tail, wk, mx, a, role, win, o = {}) => S([[cx - R * tail, cy], [cx + R * len, cy]], win, Object.assign({ w: Math.min(c.lw * wk, R * mx), jit: .2, spin: { cx, cy, a0: a, a1: a, role } }, o));
  parts.push(hand(.5, .1, 2.6, .075, ha, 'hour', [.62, .76]), hand(.76, .12, 1.6, .045, ma, 'min', [.72, .86]));
  if (sp.sec !== undefined && sp.sec !== null) parts.push(hand(.86, .18, .7, .02, sp.sec * 6 - 90 + (t % 1) * 360, 'sec', [.82, .94], { c: col(sp.c2s, 'accent'), noriso: true }));
  parts.push(F(G.circ([cx, cy], R * .045, 16), [.9, 1], { reveal: 'pop', pivot: [cx, cy] }));
  return parts;
};
BLD.write = (sp, c) => { // рукописная надпись: строки «пишутся» слева направо (clip)
  const [x, y] = sp.at, sz = sp.sz ?? 28, lh = sz * PT * (sp.lh ?? 1.15), an = sp.al === 'c' ? 'middle' : sp.al === 'r' ? 'end' : 'start';
  return txt(sp, 'text', (s, al) => { const L = s.split('\n'), tot = L.reduce((q, l) => q + Math.max(1, l.length), 0); let acc = 0;
    return L.map((ln, i) => { const w0 = acc / tot; acc += Math.max(1, ln.length); return X(ln, x, y + lh * (i + .5), [w0, acc / tot], { sz, anchor: an, va: 'm', reveal: 'write', a: al, font: sp.font ?? 'hand', wt: sp.wt }) }) });
};
BLD.block = (sp, c) => { // блок-схема: процесс | терминатор | данные | решение | документ | подпрограмма
  const [x, y, w, h] = sp.box, f = sp.form || 'process'; let P, extra = [];
  if (f === 'terminator') { const r = Math.min(h / 2, w / 2); P = [[x + r, y], [x + w - r, y]].concat(G.arc(x + w - r, y + r, r, h / 2 === r ? r : r, -90, 90, 24).slice(1), [[x + r, y + h]], G.arc(x + r, y + h - r, r, r, 90, 270, 24).slice(1)) }
  else if (f === 'data') { const k = Math.min(h * .35, w * .15); P = [[x + k, y], [x + w, y], [x + w - k, y + h], [x, y + h], [x + k, y]] }
  else if (f === 'decision') P = [[x + w / 2, y], [x + w, y + h / 2], [x + w / 2, y + h], [x, y + h / 2], [x + w / 2, y]];
  else if (f === 'document') { const a = h * .09; P = [[x, y], [x + w, y], [x + w, y + h - a]]; for (let i = 1; i <= 32; i++) { const t = i / 32; P.push([x + w - w * t, y + h - a + a * Math.sin(t * 2 * Math.PI)]) } P.push([x, y]) }
  else { P = G.rect(x, y, w, h); if (f === 'predef') { const k = Math.min(w * .08, .18); extra = [[[x + k, y], [x + k, y + h]], [[x + w - k, y], [x + w - k, y + h]]] } }
  const parts = [];
  if (sp.fill) parts.push(F(P, [.5, .85], { c: sp.fill, aa: sp.fa ?? 1, noriso: true, blend: '' }));
  parts.push(S(P, [0, .7]));
  extra.forEach(e => parts.push(S(e, [.55, .75], { wk: .8 })));
  const sz = sp.sz ?? 14;
  return parts.concat(txt(sp, 'text', (s, al) => { const L = s.split('\n'); return L.map((ln, i) => X(ln, x + w / 2, y + h / 2 + (i - (L.length - 1) / 2) * sz * PT * 1.22 - (f === 'document' ? h * .04 : 0), [.62 + .1 * i / L.length, .95], { sz, anchor: 'middle', va: 'm', a: al })) }));
};

/* ---------- стиль: части → элементы (px) ---------- */
function noise1(r, n) { const k = []; for (let i = 0; i < n + 2; i++) k.push(r() * 2 - 1); return x => { const i = Math.max(0, Math.floor(x)), f = x - i, t = f * f * (3 - 2 * f); return lerp(k[i] ?? 0, k[i + 1] ?? 0, t) } }
function jitter(P, amp, seed) { // дрожание руки: гладкий шум поперёк линии, концы закреплены
  const Q = [P[0]];
  for (let i = 1; i < P.length; i++) { const a = P[i - 1], b = P[i], L = Math.hypot(b[0] - a[0], b[1] - a[1]), n = Math.max(1, Math.ceil(L / 5)); for (let j = 1; j <= n; j++) Q.push([lerp(a[0], b[0], j / n), lerp(a[1], b[1], j / n)]) }
  const m = Q.length; if (m < 3) return Q;
  const s = [0]; for (let i = 1; i < m; i++) s.push(s[i - 1] + Math.hypot(Q[i][0] - Q[i - 1][0], Q[i][1] - Q[i - 1][1]));
  const L = s[m - 1]; if (L < 2) return Q;
  const r = U.rng(seed), n1 = noise1(r, Math.ceil(L / 34) + 2), n2 = noise1(r, Math.ceil(L / 11) + 2), out = [];
  for (let i = 0; i < m; i++) {
    const a = Q[Math.max(0, i - 1)], b = Q[Math.min(m - 1, i + 1)], dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy) || 1;
    const v = (n1(s[i] / 34) + .35 * n2(s[i] / 11)) * amp * Math.min(1, s[i] / 14, (L - s[i]) / 14);
    out.push([Q[i][0] - dy / l * v, Q[i][1] + dx / l * v]);
  }
  return out;
}
function chalkDash(L, w, seed, fine) { // мел: неровные штрихи с разрывами (доли длины пути)
  const r = U.rng(seed), out = []; let acc = 0;
  while (acc < L && out.length < 600) { const d = fine ? 2 + r() * 7 : 12 + r() * 34, g = fine ? 2 + r() * 6 : (r() < .25 ? 3 + r() * 7 : .8 + r() * 2.4) + w * .15; out.push(d / L, g / L); acc += d + g }
  return out.length ? out : null;
}
function dashList(kind, w, L) {
  const d = kind === 'dot' ? .01 : w * 3.2 + 5, g = kind === 'dot' ? w * 2.4 + 3 : w * 2.2 + 4, out = [];
  for (let acc = 0; acc < L && out.length < 800; acc += d + g) out.push(d / L, g / L);
  return out.length ? out : null;
}
function cut(list, q) { // штриховой узор, обрезанный на доле q длины (рисование по длине)
  if (!list) return q.toFixed(4) + ' 2';
  const out = []; let acc = 0;
  for (let i = 0; i < list.length; i++) { const s = list[i];
    if (acc + s >= q) { if (i % 2 === 0) out.push(q - acc, 2); else out.push(2); return out.map(v => +v.toFixed(5)).join(' ') }
    out.push(s); acc += s }
  return list.map(v => +v.toFixed(5)).join(' ');
}
const pathD = P => { let s = ''; for (let i = 0; i < P.length; i++) s += (i ? 'L' : 'M') + P[i][0].toFixed(1) + ' ' + P[i][1].toFixed(1); return s };
function bbox(P) { let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9; for (const [x, y] of P) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y) } return [x0, y0, x1 - x0, y1 - y0] }

function expand(items, pt, idx, cx, M, Sx) {
  const sty = cx.sty, k = Sx / 120, seed = cx.seed * 31 + idx * 101;
  const blend = pt.blend !== undefined ? pt.blend : (sty.blend || '');
  const riso = sty.off && !pt.noriso ? [sty.off[0] * k, sty.off[1] * k] : null;
  const spin = pt.spin ? Object.assign({}, pt.spin, { cx: M([pt.spin.cx, pt.spin.cy])[0], cy: M([pt.spin.cx, pt.spin.cy])[1] }) : null;
  const push = (base, k2 = 1) => { if (riso) items.push(Object.assign({}, base, { c: cx.c2, off: [riso[0] * k2, riso[1] * k2] })); items.push(base) };
  if (pt.t === 's') {
    if (!pt.pts || pt.pts.length < 2) return;
    let P = pt.pts.map(M);
    const w = (pt.w !== undefined ? pt.w : cx.lw * (pt.wk ?? 1)) * Sx, amp = (sty.jit || 0) * (pt.jit ?? 1) * k;
    if (amp > 0) P = jitter(P, amp, seed);
    const L = polyLen(P), a = pt.aa !== undefined ? pt.aa : (pt.a ?? 1) * sty.op;
    let dash = null; if (pt.dash) dash = dashList(pt.dash, w, L); else if (sty.chalk && !pt.solid) dash = chalkDash(L, w, seed);
    const base = { k: 's', d: pathD(P), w, c: pt.c ? col(pt.c) : cx.c, a, cap: pt.cap || 'round', join: pt.join || 'round', dash, win: pt.win, blend, clip: pt.clip, spin };
    push(base);
    if (sty.chalk && !pt.solid && !pt.dash) { const P2 = jitter(pt.pts.map(M), Math.max(amp, .8 * k) * 1.4, seed + 7), L2 = polyLen(P2);
      items.push(Object.assign({}, base, { d: pathD(P2), w: w * .42, a: a * .55, dash: chalkDash(L2, w * .5, seed + 3, true) })) }
  } else if (pt.t === 'f') {
    if (!pt.pts || pt.pts.length < 3) return;
    const P = pt.pts.map(M), bb = bbox(P);
    push({ k: 'f', d: pathD(P) + 'Z', c: pt.c ? col(pt.c) : cx.c, a: pt.aa !== undefined ? pt.aa : (pt.a ?? 1) * sty.op, win: pt.win, reveal: pt.reveal || 'fade', dir: pt.dir || 'x',
      pivot: pt.pivot ? M(pt.pivot) : [bb[0] + bb[2] / 2, bb[1] + bb[3] / 2], bb, shadow: pt.shadow, blend, spin });
  } else if (pt.t === 'x') {
    const role = pt.font ?? sty.font, [fam, itF] = font(role), size = (pt.sz ?? 14) * PT * Sx, wt = pt.wt ?? sty.wt ?? 400, it = itF || !!pt.it;
    const [x, y] = M([pt.x, pt.y]), va = pt.va || 'm', yy = va === 'b' ? y - size * .5 : va === 't' ? y + size * .55 : y;
    const s = pt.s, sw = pt.s0 ?? s;
    push({ k: 'x', s, x, y: yy, size, fam, wt, it, c: pt.c ? col(pt.c) : cx.tc, a: (pt.a ?? 1) * (pt.aa ?? Math.max(sty.op, .85)), anchor: pt.anchor || 'start',
      rot: pt.rot || 0, win: pt.win, reveal: pt.reveal || 'fade', pivot: [x, yy], width: textW(sw, size, fam, wt, it) + (pt.ls ? pt.ls * size * sw.length : 0), count: pt.count, blend,
      ls: pt.ls ? pt.ls * size : 0, hand: role === 'hand', seed, spin }, Math.min(1, size / 64)); // мелкий текст — слабее сдвиг, чтобы читался
  } else if (pt.t === 'tp') {
    const [fam] = font(pt.font || 'head'), [x, y] = M([pt.cx, pt.cy]);
    push({ k: 'tp', s: pt.s, cx: x, cy: y, r: pt.r * Sx, size: (pt.sz ?? 12) * PT * Sx, fam, wt: pt.wt ?? 700, c: pt.c ? col(pt.c) : cx.tc, a: (pt.a ?? 1) * Math.max(sty.op, .85), win: pt.win, reveal: 'fade', start: pt.start ?? 130, blend }, .5);
  } else if (pt.t === 'pat') {
    const [bx, by] = M([pt.box[0], pt.box[1]]);
    items.push({ k: 'pat', bb: [bx, by, pt.box[2] * Sx, pt.box[3] * Sx], step: pt.step * Sx, r: pt.r * Sx, c: pt.c ? col(pt.c) : cx.c, a: (pt.a ?? 1) * sty.op, win: pt.win, clip: pt.clip, blend });
  }
}

/* ---------- DOM: элементы из кэша ---------- */
function make(dc, k) {
  const r = { k };
  if (k === 's') r.el = U.el('path', { fill: 'none', pathLength: 1 });
  else if (k === 'f') r.el = U.el('path', {});
  else if (k === 'x') { r.el = U.el('g', {}); r.t = U.el('text', { 'dominant-baseline': 'central' }, r.el) }
  else if (k === 'tp') { r.el = U.el('text', {}); r.path = U.el('path', { id: uid('t'), fill: 'none' }, dc.defs); r.tp = U.el('textPath', { href: '#' + r.path.id, lengthAdjust: 'spacing' }, r.el) }
  else if (k === 'pat') { const id = uid('p'); r.pat = U.el('pattern', { id, patternUnits: 'userSpaceOnUse' }, dc.defs); r.dot = U.el('circle', {}, r.pat); r.el = U.el('rect', { fill: `url(#${id})` }) }
  return r;
}
function kill(r) { r.el.remove(); r.path && r.path.remove(); r.pat && r.pat.remove(); r.cp && r.cp.remove() }
function clipOf(dc, r, target) { // свой прямоугольник-клип элемента (письмо, разматывание)
  if (!r.cp) { r.cp = U.el('clipPath', { id: uid('c'), clipPathUnits: 'userSpaceOnUse' }, dc.defs); r.cr = U.el('rect', {}, r.cp) }
  target.setAttribute('clip-path', `url(#${r.cp.id})`);
}
function apply(dc, r, it) {
  const e = r.el;
  if (it.k === 's') {
    e.setAttribute('d', it.d); e.setAttribute('stroke', it.c); e.setAttribute('stroke-width', Math.max(.3, it.w).toFixed(2)); e.setAttribute('stroke-opacity', +it.a.toFixed(3));
    e.setAttribute('stroke-linecap', it.cap); e.setAttribute('stroke-linejoin', it.join);
    if (it.clip && dc.clips[it.clip]) e.setAttribute('clip-path', `url(#${dc.clips[it.clip].id})`); else e.removeAttribute('clip-path');
  } else if (it.k === 'f') {
    e.setAttribute('d', it.d); e.setAttribute('fill', it.c); e.style.filter = it.shadow || '';
    if (it.reveal === 'wipe') clipOf(dc, r, e); else e.removeAttribute('clip-path');
  } else if (it.k === 'x') {
    const t = r.t;
    t.setAttribute('x', it.x.toFixed(1)); t.setAttribute('y', it.y.toFixed(1)); t.setAttribute('font-family', it.fam); t.setAttribute('font-size', it.size.toFixed(2));
    t.setAttribute('font-weight', it.wt); t.setAttribute('font-style', it.it ? 'italic' : 'normal'); t.setAttribute('fill', it.c); t.setAttribute('text-anchor', it.anchor);
    if (it.ls) t.setAttribute('letter-spacing', it.ls.toFixed(2)); else t.removeAttribute('letter-spacing');
    if (!it.count) t.textContent = it.s;
    if (it.hand && it.s.length < 160) { const q = U.rng(it.seed); t.setAttribute('rotate', Array.from(it.count ? '0000000000' : it.s, () => ((q() - .5) * 5).toFixed(1)).join(' ')) } else t.removeAttribute('rotate');
    if (it.reveal === 'write') clipOf(dc, r, t); else t.removeAttribute('clip-path');
  } else if (it.k === 'tp') {
    const a = it.start * RAD, x0 = it.cx + it.r * Math.cos(a), y0 = it.cy + it.r * Math.sin(a), x1 = it.cx - it.r * Math.cos(a), y1 = it.cy - it.r * Math.sin(a);
    r.path.setAttribute('d', `M${x0.toFixed(1)} ${y0.toFixed(1)}A${it.r.toFixed(1)} ${it.r.toFixed(1)} 0 1 1 ${x1.toFixed(1)} ${y1.toFixed(1)}A${it.r.toFixed(1)} ${it.r.toFixed(1)} 0 1 1 ${x0.toFixed(1)} ${y0.toFixed(1)}`);
    e.setAttribute('font-family', it.fam); e.setAttribute('font-size', it.size.toFixed(2)); e.setAttribute('font-weight', it.wt); e.setAttribute('fill', it.c);
    r.tp.setAttribute('textLength', (2 * Math.PI * it.r * .97).toFixed(1)); r.tp.textContent = it.s;
  } else if (it.k === 'pat') {
    const st = Math.max(2, it.step); r.pat.setAttribute('width', st.toFixed(2)); r.pat.setAttribute('height', st.toFixed(2));
    r.pat.setAttribute('x', it.bb[0].toFixed(1)); r.pat.setAttribute('y', it.bb[1].toFixed(1));
    r.dot.setAttribute('cx', (st / 2).toFixed(2)); r.dot.setAttribute('cy', (st / 2).toFixed(2)); r.dot.setAttribute('r', it.r.toFixed(2)); r.dot.setAttribute('fill', it.c);
    e.setAttribute('x', it.bb[0].toFixed(1)); e.setAttribute('y', it.bb[1].toFixed(1)); e.setAttribute('height', it.bb[3].toFixed(1));
    if (it.clip && dc.clips[it.clip]) e.setAttribute('clip-path', `url(#${dc.clips[it.clip].id})`);
  }
  e.style.mixBlendMode = blendFor(it.blend);
  r.it = it; r.vis = null; r.dash = null; r.op = null; r.tf = null; r.txt = null; r.cw = null;
}
function sync(dc, items, clips, M) {
  for (const k in dc.clips) if (!clips || !clips[k]) { dc.clips[k].remove(); delete dc.clips[k] }
  if (clips) for (const k in clips) { let cp = dc.clips[k]; if (!cp) { cp = dc.clips[k] = U.el('clipPath', { id: uid('k'), clipPathUnits: 'userSpaceOnUse' }, dc.defs); cp.p = U.el('path', {}, cp) } cp.p.setAttribute('d', pathD(clips[k].map(M)) + 'Z') }
  const recs = dc.recs; let moved = false;
  for (let i = 0; i < items.length; i++) { const it = items[i]; let r = recs[i];
    if (!r || r.k !== it.k) { if (r) kill(r); r = recs[i] = make(dc, it.k); moved = true }
    apply(dc, r, it) }
  for (let i = items.length; i < recs.length; i++) kill(recs[i]);
  recs.length = items.length;
  if (moved) for (const r of recs) dc.g.appendChild(r.el);
}
function bgDark() { // тёмный фон слайда: multiply там гасит краску — берём screen
  const D = DC.data || {}, sl = D.slides && D.slides[DC.cur], c = String((sl && sl.bg) || (D.colors && D.colors.bg) || '#ffffff');
  const m = /^#?([0-9a-f]{6})$/i.exec(c); if (!m) return false;
  const n = parseInt(m[1], 16), r = n >> 16 & 255, g = n >> 8 & 255, b = n & 255;
  return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255 < 0.4;
}
function blendFor(b) { return b === 'multiply' && bgDark() ? 'screen' : (b || '') }
function wear(dc, on, seed, gb) { // «износ» печати: шумовая маска
  if (on && !dc.wf) { const f = dc.wf = U.el('filter', { id: uid('w'), x: '-5%', y: '-5%', width: '110%', height: '110%' }, dc.defs);
    U.el('feTurbulence', { type: 'fractalNoise', baseFrequency: '.55', numOctaves: 2, seed: seed % 97, result: 'n' }, f);
    U.el('feColorMatrix', { in: 'n', type: 'matrix', values: '0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -7 0 0 0 5.3', result: 'm' }, f);
    U.el('feComposite', { in: 'SourceGraphic', in2: 'm', operator: 'in' }, f) }
  if (on) dc.g.setAttribute('filter', `url(#${dc.wf.id})`); else dc.g.removeAttribute('filter');
  dc.g.style.mixBlendMode = blendFor(on ? 'multiply' : gb);
}

/* ---------- кадр ---------- */
function build(dc, sp, o, val) {
  const sty = Object.assign({ name: sp.style }, STY[sp.style] || STY.ink);
  const f = sp._f || [o.x / 120, o.y / 120, Math.max(o.w, 1) / 120, Math.max(o.h, 1) / 120];
  const Sx = o.w / Math.max(f[2], 1e-6), Sy = f[3] > 1e-6 ? o.h / f[3] : Sx;
  const cx = { sty, seed: (sp.seed ?? 1) + dc.boil * 7919, lw: (sp.lw ?? sty.lw) * PT, c: col(sp.c, sty.c), c2: col(sp.c2, sty.c2 || 'accent'), val };
  cx.tc = col(sp.tc ?? sp.c, sty.c);
  let parts = [];
  try { parts = BLD[sp.kind](sp, cx) || [] } catch (e) { console.warn('draw:', sp.kind, e); parts = [] }
  const M = p => [o.x + (p[0] - f[0]) * Sx, o.y + (p[1] - f[1]) * Sy], items = [];
  parts.forEach((pt, i) => expand(items, pt, i, cx, M, Sx));
  // один режим наложения на весь элемент — одна группа multiply вместо сотни (в 2 раза быстрее на программной отрисовке)
  const bl = new Set(items.map(i => i.blend || '')), gb = bl.size === 1 ? [...bl][0] : '';
  if (bl.size === 1) items.forEach(i => { i.blend = '' });
  sync(dc, items, parts.clips, M);
  wear(dc, !!parts.wear, cx.seed, gb);
}
function progress(dc, p, reg, ndl) {
  for (const r of dc.recs) {
    const it = r.it, w = it.win || [0, 1];
    const q = w[1] > w[0] ? clamp((p - w[0]) / (w[1] - w[0])) : (p >= w[0] ? 1 : 0), vis = q > .0005;
    if (r.vis !== vis) { r.el.style.display = vis ? '' : 'none'; r.vis = vis }
    if (!vis) continue;
    let tf = '';
    if (it.off) { const m = 1 + reg * 7; tf += `translate(${(it.off[0] * m).toFixed(2)} ${(it.off[1] * m).toFixed(2)})` }
    if (it.spin) { const s = it.spin, qs = s.win ? clamp((p - s.win[0]) / ((s.win[1] - s.win[0]) || 1e-6)) : 1, a = s.a0 + (s.a1 - s.a0) * eIO(qs) + (s.role === 'needle' ? ndl : 0); tf += ` rotate(${a.toFixed(2)} ${s.cx.toFixed(1)} ${s.cy.toFixed(1)})` }
    if (it.reveal === 'pop' && q < 1) { const sc = Math.max(.001, eBack(q)), [px, py] = it.pivot; tf += ` translate(${px.toFixed(1)} ${py.toFixed(1)}) scale(${sc.toFixed(3)}) translate(${(-px).toFixed(1)} ${(-py).toFixed(1)})` }
    if (it.k === 'x') { if (it.reveal === 'fade' && q < 1) tf = `translate(0 ${((1 - eOut(q)) * it.size * .3).toFixed(2)}) ` + tf; if (it.rot) tf += ` rotate(${it.rot} ${it.x.toFixed(1)} ${it.y.toFixed(1)})` }
    tf = tf.trim();
    if (r.tf !== tf) { if (tf) r.el.setAttribute('transform', tf); else r.el.removeAttribute('transform'); r.tf = tf }
    if (it.k === 's') {
      const ds = q >= 1 ? (it.dash ? it.dash.map(v => +v.toFixed(5)).join(' ') : '') : cut(it.dash, q);
      if (r.dash !== ds) { if (ds) r.el.setAttribute('stroke-dasharray', ds); else r.el.removeAttribute('stroke-dasharray'); r.dash = ds }
      continue;
    }
    const fade = it.reveal === 'fade' ? eOut(q) : it.reveal === 'pop' ? Math.min(1, q * 3) : 1, op = (it.a * fade).toFixed(3);
    if (r.op !== op) { r.el.setAttribute('opacity', op); r.op = op }
    if (it.reveal === 'wipe' && r.cr) { const [bx, by, bw, bh] = it.bb, ww = bw * q + 2, cw = ww.toFixed(1);
      if (r.cw !== cw) { r.cr.setAttribute('x', (it.dir === '-x' ? bx + bw - ww + 1 : bx - 1).toFixed(1)); r.cr.setAttribute('y', (by - 2).toFixed(1)); r.cr.setAttribute('width', cw); r.cr.setAttribute('height', (bh + 4).toFixed(1)); r.cw = cw } }
    if (it.k === 'x') {
      if (it.count) { const c = it.count, qc = clamp((p - c.win[0]) / ((c.win[1] - c.win[0]) || 1e-6)), s = fmtNum(lerp(c.a, c.b, eIO(qc)), c.dec, c.fmt); if (r.txt !== s) { r.t.textContent = s; r.txt = s } }
      if (it.reveal === 'write' && r.cr) { const pad = it.size * .35, left = it.anchor === 'middle' ? it.x - it.width / 2 : it.anchor === 'end' ? it.x - it.width : it.x, cw = (q >= 1 ? it.width + pad * 2 + it.size : it.width * q + pad).toFixed(1);
        if (r.cw !== cw) { r.cr.setAttribute('x', (left - pad).toFixed(1)); r.cr.setAttribute('y', (it.y - it.size * 1.6).toFixed(1)); r.cr.setAttribute('width', cw); r.cr.setAttribute('height', (it.size * 3.2).toFixed(1)); r.cw = cw } }
    }
    if (it.k === 'pat') { const cw = (it.bb[2] * q).toFixed(1); if (r.cw !== cw) { r.el.setAttribute('width', cw); r.cw = cw } }
  }
}
function render(node, o, st) {
  if (node.tg && node.tgh !== node.tg) { node.tg.style.display = 'none'; node.tgh = node.tg } // текст объекта (запасной для .pptx) рисует сам элемент
  const sp = o.draw;
  let dc = node.dc;
  if (!dc || dc.g !== node.dg) dc = node.dc = { g: node.dg, defs: U.el('defs', {}, node.dg), recs: [], clips: {}, boil: 0, ps: null };
  const boil = DC.REDUCED ? 0 : (st.drawBoil | 0), val = DC.REDUCED || st.drawValue === undefined ? undefined : st.drawValue;
  if (dc.spec !== sp || dc.x !== o.x || dc.y !== o.y || dc.w !== o.w || dc.h !== o.h || dc.boil !== boil || dc.val !== val) {
    Object.assign(dc, { spec: sp, x: o.x, y: o.y, w: o.w, h: o.h, boil, val, ps: null });
    build(dc, sp, o, val);
  }
  const p = DC.REDUCED ? 1 : clamp(st.drawP ?? 1), reg = DC.REDUCED ? 0 : (st.drawReg || 0), ndl = DC.REDUCED ? 0 : (st.drawNeedle || 0);
  if (dc.ps !== p || dc.pr !== reg || dc.pn !== ndl) { dc.ps = p; dc.pr = reg; dc.pn = ndl; progress(dc, p, reg, ndl) }
}
for (const k in BLD) REG[k] = render;
REG.pptx = node => { if (node.tg && node.tgh !== node.tg) { node.tg.style.display = 'none'; node.tgh = node.tg } }; // подписи, нужные только .pptx (в HTML их рисует элемент)
REG._kinds = Object.keys(BLD);

/* ---------- Morph: перелив параметров одного вида ---------- */
const ENUM = new Set(['kind', 'style', 'form', 'pattern', 'head', 'ends', 'end', 'start', 'dir', 'mark', 'font', 'al', 'fmt', 'numerals', 'dash']);
const COLK = new Set(['c', 'c2', 'tc', 'paper', 'fill', 'needle', 'tapeC', 'c2s']);
const INT = new Set(['seed', 'dec', 'ldec', 'major', 'minor', 'passes', 'sheet', 'sheets']);
const isPt = v => Array.isArray(v) && v.length === 2 && typeof v[0] === 'number' && typeof v[1] === 'number';
function resamplePts(P, n) {
  if (P.length === n) return P; const L = polyLen(P), out = [];
  for (let i = 0; i < n; i++) { const Q = cutStart(P, L * i / Math.max(1, n - 1)); out.push(Q[0]) } return out;
}
function lerpV(a, b, t, key) {
  if (a === b) return b;
  if (typeof a === 'number' && typeof b === 'number') return INT.has(key) ? (t < .5 ? a : b) : a + (b - a) * t;
  if (typeof a === 'string' && typeof b === 'string') { if (COLK.has(key) || (!ENUM.has(key) && /^#[0-9a-f]{6}$/i.test(col(a)) && /^#[0-9a-f]{6}$/i.test(col(b)) && (D.colors[a] || a[0] === '#') && (D.colors[b] || b[0] === '#'))) return U.lc(col(a), col(b), t); return t < .5 ? a : b }
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length === b.length) return a.map((v, i) => lerpV(v, b[i], t));
    if (a.length > 1 && b.length > 1 && a.every(isPt) && b.every(isPt)) { const n = Math.max(a.length, b.length), A = resamplePts(a, n), B = resamplePts(b, n); return A.map((p, i) => [lerp(p[0], B[i][0], t), lerp(p[1], B[i][1], t)]) }
    return t < .5 ? a : b;
  }
  if (a && b && typeof a === 'object' && typeof b === 'object') return interpObj(a, b, t);
  return t < .5 ? a : b;
}
function interpObj(a, b, t) {
  const o = {};
  for (const k in b) {
    if (k[0] === '~') continue;
    const x = a[k], y = b[k];
    if (x === undefined) { o[k] = y; continue }
    if (typeof x === 'string' && typeof y === 'string' && x !== y && !ENUM.has(k) && !COLK.has(k) && !(D.colors[x] && D.colors[y])) { o[k] = y; o['~' + k] = x; o['~t'] = t; continue }
    o[k] = lerpV(x, y, t, k);
  }
  for (const k in a) if (b[k] === undefined && typeof a[k] === 'string' && k[0] !== '~' && !ENUM.has(k)) { o['~' + k] = a[k]; o['~t'] = t }
  return o;
}
REG._interp = (a, b, t) => {
  if (!a || !b || a.kind !== b.kind || !BLD[b.kind]) return b;
  if (t <= 0) return a; if (t >= 1) return b;
  return interpObj(a, b, t);
};

/* ---------- эффекты рисования ---------- */
const FX = DC.fx;
const R0 = () => DC.REDUCED;
FX['in.draw'] = (o, e) => R0() ? {} : { drawP: e };                                   // рисуется в порядке частей
FX['in.draw-linear'] = (o, e, p) => R0() ? {} : { drawP: p };                         // ровная скорость (рукопись)
FX['in.draw-stamp'] = (o, e, p) => { if (R0()) return {}; const k = Math.min(1, Math.floor(p * 5) / 4); // печать рывками
  return { scale: 1.75 - .75 * k, alpha: Math.min(1, .25 + k * 1.2), drot: 8 * (1 - k), drawP: 1 } };
FX['in.draw-drop'] = (o, e, p, opt) => { if (R0()) return {}; const f = eOut(clamp(p / .55)), land = clamp((p - .5) / .5), from = opt.from ?? .32; // стикер падает и прилипает
  const st = { dy: -(opt.h ?? .7) * (1 - f), drot: (opt.rot ?? 9) * (1 - f), scale: 1 + .07 * (1 - f) - .025 * Math.sin(Math.PI * clamp((p - .5) / .18)), alpha: clamp(p * 5), drawP: from + (1 - from) * eIO(land) };
  if (f < .98) st.shadow = `0 ${(14 * (1 - f)).toFixed(1)}px ${(18 * (1 - f) + 2).toFixed(1)}px rgba(0,0,0,.25)`; return st };
FX['in.draw-reg'] = (o, e, p) => R0() ? {} : { drawP: Math.min(1, e * 1.6), drawReg: 1 - e, tx: -14 * (1 - e), alpha: Math.min(1, p * 3) }; // надпечатка сходится
FX['in.draw-pop'] = (o, e, p) => R0() ? {} : { scale: .35 + .65 * eBack(p), drawP: e, alpha: Math.min(1, p * 3) };
FX['em.draw-redraw'] = (o, e, p) => R0() ? {} : { drawP: p < .3 ? 1 - eIO(p / .3) : eIO((p - .3) / .7) };         // стереть и нарисовать заново
FX['em.draw-boil'] = (o, e, p, opt) => R0() ? {} : { drawBoil: 1 + Math.floor(p * (opt.n || Math.max(2, Math.round((opt._dur || 1.2) * 8)))) }; // «кипящая» линия ~8 к/с (repeat — до конца слайда)
FX['em.draw-to'] = (o, e, p, opt) => { const d = o.draw || {}, v0 = d.value ?? d.t ?? 0, v1 = opt.value ?? opt.to ?? v0; return { drawValue: R0() ? v1 : lerp(v0, v1, e) } }; // стрелка/часы/размер к значению
FX['em.draw-to'].hold = true;
FX['em.draw-run'] = (o, e, p, opt) => { const d = o.draw || {}; return { drawValue: (d.t ?? d.value ?? 0) + (opt.minutes ?? opt.by ?? 60) * (R0() ? 1 : e) } }; // часы идут
FX['em.draw-run'].hold = true;
FX['em.draw-needle'] = (o, e, p, opt) => R0() ? {} : { drawNeedle: (opt.amp ?? 5) * Math.sin(p * Math.PI * (opt.n ?? 7)) * (1 - p) }; // стрелка дрожит
})();
