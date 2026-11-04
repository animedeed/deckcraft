/* deckcraft web — живые сцены (0.3.0).
 * Регистрирует DC.scenes[kind] = { mount(ctx, params) => { frame(t, ctx), unmount() } } — см. CONTRACT.md.
 * Сцены: liquid (вино в бокале), pour (струя), bubbles, drip (капли с края), stain (пятно), particles (поле точек
 * с раскладками), signal (сигнал по сети), counter (число в тексте), clock (часы и журнал), gauge (дуговая шкала),
 * terminal, sparks, confetti, ripple, grain (зерно бумаги/плёнки), halftone (растр), chart-draw, bars-grow.
 * Параметры приходят из morphkit/scenes.py уже в px сцены (1 дюйм = 120 px), цвета — роли темы или #hex.
 * Время сцены lt = t − fxStart − delay (как у эффектов); step: k — начало сдвигается на момент k-го клика.
 * character: calm | lively | dramatic — множители скорости (sp), амплитуды (amp), плотности (den), перелёта (ov).
 * Правила: без внешних библиотек; случайность — DC.u.rng(seed) и хеш-шум; узлы кэшируются, на кадре только
 * атрибуты; ctx.reduced — сразу финальный кадр без движения; unmount снимает модификаторы и общие ссылки. */
'use strict';
(function () {
const DC = window.DC;
if (!DC || !DC.u) return;
const U = DC.u, D = DC.data, TAU = Math.PI * 2, PX = 120;
DC.scenes = DC.scenes || {};

/* ================================================================== общее */
const CHAR = {
  calm: { sp: .62, amp: .55, den: .55, ov: .25, jit: .45 },
  lively: { sp: 1, amp: 1, den: 1, ov: .65, jit: 1 },
  dramatic: { sp: 1.45, amp: 1.75, den: 1.7, ov: 1, jit: 1.6 },
};
DC.sceneChar = CHAR;
const clamp = U.clamp, lerp = U.lerp;
const E = n => (n && DC.ease[n]) || DC.ease.inOut;
const sstep = t => t * t * (3 - 2 * t);
const sq = v => v * v;
const f1 = v => (Math.round(v * 10) / 10).toString();
function col(v, d) {
  if (v === undefined || v === null || v === '') return d === undefined ? null : col(d);
  const c = U.color(String(v));
  return /^[0-9a-f]{6}$/i.test(c) ? '#' + c : c;
}
function rgb(c) { c = col(c, '#000000'); return c[0] === '#' && c.length >= 7 ? U.hx(c) : [0, 0, 0] }
function rgba(c, a) { const [r, g, b] = rgb(c); return `rgba(${r},${g},${b},${(+a).toFixed(3)})` }
function mixc(a, b, t) { return U.lc(col(a, '#000000'), col(b, '#ffffff'), clamp(t)) }
function lum(c) { const [r, g, b] = rgb(c); return (.2126 * r + .7152 * g + .0722 * b) / 255 }
function hash(n) { n = (n ^ 61) ^ (n >>> 16); n = (n + (n << 3)) | 0; n ^= n >>> 4; n = Math.imul(n, 0x27d4eb2d); n ^= n >>> 15; return (n >>> 0) / 4294967296 }
function noise(x, seed) { // гладкий шум −1..1
  const i = Math.floor(x), f = x - i, s = (seed | 0) * 668265263;
  return lerp(hash((i * 374761393 + s) | 0), hash(((i + 1) * 374761393 + s) | 0), sstep(f)) * 2 - 1;
}
function spring(t, z, w) { // переходная функция пружины 0 → 1 (z — демпфирование, w — частота)
  if (t <= 0) return 0;
  if (z >= 1) return 1 - (1 + w * t) * Math.exp(-w * t);
  const wd = w * Math.sqrt(1 - z * z);
  return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + z * w / wd * Math.sin(wd * t));
}
const SPRING = { calm: [.92, 7], lively: [.42, 9], dramatic: [.26, 12] };
function springOf(p) { return SPRING[p.character] || SPRING.lively }
const el = (tag, a, parent) => U.el(tag, a, parent);
const font = r => (D.fonts && D.fonts[r]) || 'Calibri, Carlito, Arial, sans-serif';
let uidN = 0;
const uid = p => 'dcs' + p + (++uidN);

/* ---------- числа по-русски: «6 497», «0,541», «−0,035», «76 %» ---------- */
const NUM_RE = /([+−\-–]?)(\d{1,3}(?:[   ]\d{3})+|\d+)(?:([,.])(\d+))?/;
function parseNum(s) {
  const m = NUM_RE.exec(s || ''); if (!m) return null;
  const g = /[   ]/.exec(m[2]), neg = m[1] && m[1] !== '+';
  const val = parseFloat(m[2].replace(/[   ]/g, '') + (m[4] ? '.' + m[4] : '')) * (neg ? -1 : 1);
  return { val, idx: m.index, len: m[0].length, f: { dec: m[4] ? m[4].length : 0, grp: g ? g[0] : '', sep: m[3] || ',', minus: neg ? m[1] : '−', plus: m[1] === '+' } };
}
function fmtNum(v, f) {
  f = f || {}; const dec = f.dec || 0;
  const s = Math.abs(v).toFixed(dec); let [ip, fp] = s.split('.');
  const grp = f.grp === undefined ? ' ' : f.grp;
  if (grp && ip.length >= (f.grpMin || 4)) ip = ip.replace(/\B(?=(\d{3})+(?!\d))/g, grp);
  let out = ip + (fp ? (f.sep || ',') + fp : '');
  if (v < 0 && +s !== 0) out = (f.minus || '−') + out; else if (f.plus && v > 0) out = '+' + out;
  return (f.pre || '') + out + (f.suf || '');
}
DC.fmtNum = DC.fmtNum || fmtNum;

/* ---------- объекты слайда: поиск, контуры в координатах сцены ---------- */
function normId(n) { n = String(n || ''); return n.startsWith('!!') ? n : '!!' + n }
function findObj(ctx, name) { // текстовая политика переименовывает пары с новым текстом: «!!x» → «!!x~5»
  if (!name) return null; const o = ctx.obj(name); if (o) return o;
  const pre = name + '~'; for (const x of ctx.sl.objs) if (x.n.startsWith(pre)) return x; return null;
}
function worldRings(o) {
  const rad = (o.r || 0) * Math.PI / 180, c = Math.cos(rad), s = Math.sin(rad), cx = o.x + o.w / 2, cy = o.y + o.h / 2, out = [];
  const rings = o.rings && o.rings.length ? o.rings : [[0, 0, 1, 0, 1, 1, 0, 1]];
  for (const r of rings) { const q = new Array(r.length); for (let i = 0; i < r.length; i += 2) { const x = o.x + r[i] * o.w - cx, y = o.y + r[i + 1] * o.h - cy; q[i] = cx + x * c - y * s; q[i + 1] = cy + x * s + y * c } out.push(q) }
  return out;
}
function ringsBox(rings) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const r of rings) for (let i = 0; i < r.length; i += 2) { const x = r[i], y = r[i + 1]; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y }
  return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
}
function objBox(o) {
  if (o.k === 'line') return { x: Math.min(o.x, o.x + o.w), y: Math.min(o.y, o.y + o.h), w: Math.abs(o.w), h: Math.abs(o.h) };
  if (o.k === 'path' && o.rings) return ringsBox(worldRings(o));
  if (!o.r) return { x: o.x, y: o.y, w: o.w, h: o.h };
  return ringsBox(worldRings(Object.assign({}, o, { rings: null })));
}
const mid = b => [b.x + b.w / 2, b.y + b.h / 2];
function ringsD(rings) {
  let s = ''; for (const r of rings) { for (let i = 0; i < r.length; i += 2) s += (i ? 'L' : 'M') + f1(r[i]) + ' ' + f1(r[i + 1]); s += 'Z' } return s;
}
function crossX(r, y) {
  const xs = [], n = r.length;
  for (let i = 0; i < n; i += 2) { const j = (i + 2) % n, y0 = r[i + 1], y1 = r[j + 1]; if ((y0 <= y && y1 > y) || (y1 <= y && y0 > y)) xs.push(r[i] + (r[j] - r[i]) * (y - y0) / (y1 - y0)) }
  return xs.sort((a, b) => a - b);
}
function point(env, spec) { // [x, y] px или имя объекта → центр рамки
  if (Array.isArray(spec)) return [+spec[0], +spec[1]];
  const o = env.find(spec); return o ? mid(objBox(o)) : null;
}
function boxOf(env, spec) {
  if (Array.isArray(spec)) return { x: +spec[0], y: +spec[1], w: +spec[2], h: +spec[3] };
  const o = env.find(spec); return o ? objBox(o) : null;
}

/* ---------- модификаторы: цепочка на имя (ядро хранит один fn на имя для всех сцен слайда) ---------- */
const CHAINS = new Map();
function addMod(ctx, name, fn, bag) {
  let ch = CHAINS.get(name);
  if (!ch) { const fns = []; ch = { fns, run: (o, st, t) => { for (let i = 0; i < fns.length; i++) { const r = fns[i](o, st, t); if (!r) return null; o = r[0]; st = r[1] } return [o, st] } }; CHAINS.set(name, ch) }
  ch.fns.push(fn); ctx.mod(name, ch.run); bag.push([name, fn]);
}
function dropMods(bag) {
  for (const [name, fn] of bag) { const ch = CHAINS.get(name); if (!ch) continue; const i = ch.fns.indexOf(fn); if (i >= 0) ch.fns.splice(i, 1); if (!ch.fns.length) CHAINS.delete(name) }
  bag.length = 0;
}

/* ---------- общее состояние сцен одного бокала: поверхность (liquid) и струя (pour) ---------- */
const LIVE = new Map();
function liveSet(id, key, v) { let e = LIVE.get(id); if (!e) { if (v === null) return; e = {}; LIVE.set(id, e) } e[key] = v; if (!e.surf && !e.pour) LIVE.delete(id) }
const liveGet = (id, key) => { const e = LIVE.get(id); return e ? e[key] || null : null };
DC.scenesDebug = () => ({ chains: CHAINS.size, mods: [...CHAINS.values()].reduce((n, c) => n + c.fns.length, 0), live: LIVE.size }); // проверка unmount

/* ---------- canvas на область (меньше пикселей, чем во весь слайд), с учётом DPR и масштаба сцены ---------- */
function areaCanvas(ctx, x, y, w, h) {
  x = Math.max(0, Math.floor(x)); y = Math.max(0, Math.floor(y));
  w = Math.max(1, Math.min(1600 - x, Math.ceil(w))); h = Math.max(1, Math.min(900 - y, Math.ceil(h)));
  const fo = el('foreignObject', { x, y, width: w, height: h }, ctx.layer); fo.style.pointerEvents = 'none';
  const c = document.createElement('canvas'), k = Math.min(2, (devicePixelRatio || 1) * Math.max(1, DC.scale || 1));
  c.width = Math.round(w * k); c.height = Math.round(h * k); c.style.cssText = `width:${w}px;height:${h}px;display:block;pointer-events:none`;
  fo.appendChild(c);
  const g = c.getContext('2d'); g.setTransform(k, 0, 0, k, -x * k, -y * k);
  return { g, c, x, y, w, h, clear() { g.save(); g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, c.width, c.height); g.restore() } };
}

/* ---------- регистрация ---------- */
function makeEnv(ctx, p) {
  const C = CHAR[p.character] || CHAR.lively, delay = +p.delay || 0, bag = [], keys = [];
  return {
    C, p, ctx, rng: U.rng((((p.seed || 1) * 2654435761) >>> 0) || 7),
    get reduced() { // reduced-motion: финальный кадр — но только когда шаг (step) уже наступил
      if (!ctx.reduced) return false;
      return p.step === undefined || p.step === null || !!(ctx.sl.stepT && ctx.sl.stepT[p.step] !== undefined);
    },
    local(t) {
      let s0 = 0;
      if (p.step !== undefined && p.step !== null) { const v = ctx.sl.stepT && ctx.sl.stepT[p.step]; if (v === undefined) return -1e4; s0 = v }
      if (ctx.reduced) return 1e4;
      return t - (D.fxStart || 0) - delay - s0;
    },
    find: n => findObj(ctx, n),
    mod: (name, fn) => addMod(ctx, name, fn, bag),
    live(id, key, v) { liveSet(id, key, v); if (v !== null) keys.push([id, key]) },
    canvas: (x, y, w, h) => areaCanvas(ctx, x, y, w, h),
    cleanup() { dropMods(bag); for (const [id, key] of keys) liveSet(id, key, null); keys.length = 0 },
  };
}
/* Параметры из сырых словарей (без morphkit.scenes): start → delay; координаты в дюймах (все числа точек и рамок
 * ≤ 14) переводятся в px; units: "px" | "in" задаёт явно (scenes.py всегда пишет "px"). Синонимы старых имён. */
const PT_KEYS = ['at', 'from', 'to', 'center'], BOX_KEYS = ['area', 'box'], LEN_KEYS = ['r', 'r_max', 'rmax', 'cell', 'floor'];
function normParams(p0) {
  const p = Object.assign({}, p0 || {});
  if (p.delay === undefined && typeof p.start === 'number') p.delay = p.start;
  let inch = p.units === 'in';
  if (p.units === undefined) {
    const nums = [], add = v => { if (Array.isArray(v)) v.forEach(add); else if (typeof v === 'number') nums.push(v) };
    for (const k of PT_KEYS.concat(BOX_KEYS)) if (Array.isArray(p[k])) add(p[k]);
    if (nums.length && nums.every(v => Math.abs(v) <= 14)) inch = true;
  }
  if (inch) {
    const cv = v => Array.isArray(v) ? v.map(x => typeof x === 'number' ? x * PX : cv(x)) : v;
    for (const k of PT_KEYS.concat(BOX_KEYS)) if (Array.isArray(p[k])) p[k] = cv(p[k]);
    for (const k of LEN_KEYS) if (typeof p[k] === 'number') p[k] *= PX;
    if (p.log && Array.isArray(p.log.at)) p.log = Object.assign({}, p.log, { at: cv(p.log.at) });
    if (p.out && Array.isArray(p.out.box)) p.out = Object.assign({}, p.out, { box: cv(p.out.box) });
  }
  return p;
}
function def(kinds, mount) {
  const S = {
    mount(ctx, p) {
      p = normParams(p); ctx.layer.style.pointerEvents = 'none'; ctx.layer.style.display = 'none';
      const env = makeEnv(ctx, p); let inst;
      try { inst = mount(ctx, p, env) || {} } catch (e) { env.cleanup(); throw e }
      let lastLt = NaN;
      return {
        frame(t, c) {
          const lt = env.local(t); if (env.reduced && lt === lastLt && !inst.always) return; lastLt = lt;
          inst.frame && inst.frame(lt, t, c); if (ctx.layer.style.display) ctx.layer.style.display = '';
        },
        unmount() { try { inst.unmount && inst.unmount() } finally { env.cleanup(); inst = {} } },
      };
    },
  };
  for (const k of kinds.split(' ')) DC.scenes[k] = S;
}
function pool(parent, n, make) { const a = []; for (let i = 0; i < n; i++) a.push(make(i, parent)); return a }
function setA(e, a) { for (const k in a) { const v = a[k]; if (e['_' + k] !== v) { e['_' + k] = v; e.setAttribute(k, v) } } } // без лишних записей в DOM
function show(e, on) { const v = on ? '' : 'none'; if (e._disp !== v) { e._disp = v; e.style.display = v } }

/* ================================================================== 1. liquid — живое вино в бокале */
/* Модель чаши: таблица горизонтальных хорд внутренности бокала в координатах сцены (с учётом наклона).
 * Ниже статичной поверхности — по слоям вина (точно), выше — по силуэту !!id_body минус толщина стенки
 * (калибруется по хорде вина у поверхности). Уровень — доля площади чаши, как у Python Glass(level=…). */
function glassModel(env, id) {
  const lq = []; for (let i = 0; i < 40; i++) { const o = env.find(id + '_lq' + i); if (!o) break; lq.push(o) }
  if (!lq.length) return null;
  const body = env.find(id + '_body'), W = lq.map(o => worldRings(o)[0]), B = W.map(r => ringsBox([r]));
  let top = 0; for (let i = 0; i < lq.length; i++) if (B[i].h > 3) top = i;
  if (env.p.layer_index !== undefined && env.p.layer_index !== null) top = clamp(env.p.layer_index | 0, 0, lq.length - 1);
  const y0 = B[top].y, yBot = Math.max(...B.map(b => b.y + b.h)), lowY = top > 0 ? B[top - 1].y : Infinity;
  const statChord = y => { let a = Infinity, b = -Infinity; for (const r of W) { const xs = crossX(r, y); if (xs.length > 1) { a = Math.min(a, xs[0]); b = Math.max(b, xs[xs.length - 1]) } } return a < b ? [a, b] : null };
  const bodyW = body ? worldRings(body)[0] : null;
  const bodyChord = (y, xm) => { if (!bodyW) return null; const xs = crossX(bodyW, y); let best = null, bd = Infinity; for (let i = 0; i + 1 < xs.length; i += 2) { const a = xs[i], b = xs[i + 1], d = xm < a ? a - xm : xm > b ? xm - b : 0; if (d < bd) { bd = d; best = [a, b] } } return best };
  const c0 = statChord(y0 + 1.2) || [B[top].x, B[top].x + B[top].w];
  let dl = 0, dr = 0; const xm = (c0[0] + c0[1]) / 2;
  const bc0 = bodyChord(y0 + 1.2, xm); if (bc0) { dl = c0[0] - bc0[0]; dr = bc0[1] - c0[1] }
  const wall = Math.max(0, (dl + dr) / 2), rows = [];
  if (bc0) { // вверх от поверхности до ободка
    const up = []; let m = xm, pw = c0[1] - c0[0];
    for (let y = y0 - 2.5; y > 0; y -= 2.5) {
      const bc = bodyChord(y, m); if (!bc) break; const a = bc[0] + dl, b = bc[1] - dr, w = b - a;
      if (w < 2 || w < pw * .6 || Math.abs((a + b) / 2 - m) > .3 * pw) break;
      up.push([y, a, b]); m = (a + b) / 2; pw = w;
    }
    const cut = up.length ? up[up.length - 1][0] + wall : y0;
    for (let k = up.length - 1; k >= 0; k--) if (up[k][0] >= cut) rows.push(up[k]);
  }
  const nB = 64;
  for (let k = 0; k <= nB; k++) { const y = y0 + .3 + (yBot - .6 - y0) * Math.sin(k / nB * Math.PI / 2), c = statChord(y); if (c) rows.push([y, c[0], c[1]]) }
  if (rows.length < 2) return null;
  const last = rows[rows.length - 1]; rows.push([yBot, (last[1] + last[2]) / 2, (last[1] + last[2]) / 2]);
  const AR = new Float64Array(rows.length);
  for (let k = rows.length - 2; k >= 0; k--) AR[k] = AR[k + 1] + ((rows[k][2] - rows[k][1]) + (rows[k + 1][2] - rows[k + 1][1])) / 2 * (rows[k + 1][0] - rows[k][0]);
  const Atot = AR[0] || 1;
  const rowAt = y => {
    const n = rows.length; if (y <= rows[0][0]) return [rows[0][0], rows[0][1], rows[0][2], AR[0]]; if (y >= rows[n - 1][0]) return [y, rows[n - 1][1], rows[n - 1][2], 0];
    let lo = 0, hi = n - 1; while (hi - lo > 1) { const m2 = (lo + hi) >> 1; if (rows[m2][0] <= y) lo = m2; else hi = m2 }
    const a = rows[lo], b = rows[hi], f = (y - a[0]) / ((b[0] - a[0]) || 1); return [y, lerp(a[1], b[1], f), lerp(a[2], b[2], f), lerp(AR[lo], AR[hi], f)];
  };
  const yAt = frac => { // доля площади → высота поверхности
    const A = clamp(frac, 0, 1) * Atot; let lo = 0, hi = rows.length - 1; // AR убывает с индексом
    if (A >= AR[0]) return rows[0][0]; while (hi - lo > 1) { const m2 = (lo + hi) >> 1; if (AR[m2] >= A) lo = m2; else hi = m2 }
    const f = (AR[lo] - A) / ((AR[lo] - AR[hi]) || 1); return lerp(rows[lo][0], rows[hi][0], f);
  };
  const fLow = isFinite(lowY) ? rowAt(lowY)[3] / Atot : 0;
  return { id, lq, top, W, B, y0, yBot, lowY, rows, rowAt, yAt, Atot, f0: rowAt(y0)[3] / Atot, fLow, fMax: .97,
    yTop: rows[0][0], srf: env.find(id + '_srf'), hl: env.find(id + '_hl'), body };
}
function surfacePoly(M, yc, slope, ripple, Ns) {
  const yLim = M.yTop, yLow = Math.min(M.lowY, M.yBot);
  yc = clamp(yc, yLim + 1, yLow - 1.5);
  const c = M.rowAt(yc), xc = (c[1] + c[2]) / 2, hw = Math.max(1, (c[2] - c[1]) / 2);
  const yL = clamp(yc - slope * hw, yLim, yLow - 1), yR = clamp(yc + slope * hw, yLim, yLow - 1);
  const xL = M.rowAt(yL)[1], xR = M.rowAt(yR)[2], pts = [];
  for (let i = 0; i <= Ns; i++) { const x = lerp(xL, xR, i / Ns); pts.push(x, i === 0 ? yL : i === Ns ? yR : yc + slope * (x - xc) + ripple((x - xc) / hw, x)) }
  const rows = M.rows, fin = isFinite(M.lowY);
  for (let k = 0; k < rows.length; k++) { const r = rows[k]; if (r[0] > yR + .6 && (!fin || r[0] < M.lowY - .3)) pts.push(r[2], r[0]) }
  if (fin) { const e = M.rowAt(M.lowY); pts.push(e[2], M.lowY, e[1], M.lowY) }
  for (let k = rows.length - 1; k >= 0; k--) { const r = rows[k]; if (r[0] > yL + .6 && (!fin || r[0] < M.lowY - .3)) pts.push(r[1], r[0]) }
  return { pts, xc, hw, yc, xL, xR, yL, yR };
}
function toLocal(o, pts) { // точки сцены → нормированный контур в рамке объекта (поворот объекта сохраняется)
  const rad = -(o.r || 0) * Math.PI / 180, c = Math.cos(rad), s = Math.sin(rad), cx = o.x + o.w / 2, cy = o.y + o.h / 2, out = new Array(pts.length);
  for (let i = 0; i < pts.length; i += 2) { const x = pts[i] - cx, y = pts[i + 1] - cy; out[i] = +((cx + x * c - y * s - o.x) / o.w).toFixed(5); out[i + 1] = +((cy + x * s + y * c - o.y) / o.h).toFixed(5) }
  return out;
}
def('liquid', (ctx, p, env) => {
  const C = env.C, id = normId(p.glass), M = glassModel(env, id);
  if (!M) { console.warn('liquid: нет слоёв вина', id + '_lq0'); return {} }
  const top = M.lq[M.top], wine = col(top.f, '#8e1f33');
  const clampF = f => clamp(f, Math.max(.012, M.fLow + .004), M.fMax);
  const fFrom = clampF(p.level_from ?? M.f0), fTo = clampF(p.level_to ?? p.level_from ?? M.f0);
  const dur = Math.max(.05, +p.dur || 1.2), ez = E(p.ease || 'inOut'), df = Math.abs(fTo - fFrom);
  const amp = C.amp * (p.amp ?? 1), waves = p.waves !== false, size = clamp(M.rowAt(M.y0)[2] - M.rowAt(M.y0)[1], 20, 600) / 120;
  const kicks = [[0, .05 * (p.kick ?? 1)]]; if (df > .004) kicks.push([dur, .02 + .06 * Math.min(1, df * 3)]);
  const wS = TAU * (.85 + .35 * C.sp), tauD = .9 + .55 * C.amp;
  const kickEnv = lt => { let s = 0, e = 0; for (const [te, a] of kicks) { const tau = lt - te; if (tau <= 0) continue; const en = (1 - Math.exp(-tau / .09)) * Math.exp(-tau / tauD); s += a * en * Math.sin(wS * tau + (te ? 1.2 : 0)); e += en * a / .05 } return [s, e] };
  const levelAt = lt => lt <= 0 ? fFrom : lerp(fFrom, fTo, ez(clamp(lt / dur)));
  const turbAt = lt => df < .004 || lt <= 0 || lt >= dur ? 0 : Math.sin(Math.PI * lt / dur) * clamp(df / dur * 3);
  let G = null, Gt = NaN, seen = false, lastSt = null;
  const geom = t => {
    if (t === Gt && G) return G; Gt = t;
    const lt = env.local(t), still = env.reduced || lt < 0, f = still && lt < 0 ? fFrom : levelAt(lt), yc = M.yAt(f);
    const pr = liveGet(id, 'pour'), pI = pr && pr.on ? pr.I : 0;
    const [ks, ke] = still || !waves ? [0, 0] : kickEnv(lt), turb = still ? 0 : turbAt(lt) + .7 * pI;
    const slope = still || !waves ? 0 : amp * (ks + .004 * Math.sin(1.3 * lt) + .012 * turb * Math.sin(5.1 * lt * C.sp));
    const A = still || !waves ? 0 : amp * (.45 + 2.4 * turb + 2.6 * ke) * Math.min(1.6, size);
    const ph = lt * C.sp, px = pr && pr.on ? pr.x : 0, pw = Math.max(6, M.rowAt(yc)[2] - M.rowAt(yc)[1]) * .18;
    const ripple = (u, x) => { let y = A * (1 - u * u) * (.62 * Math.sin(2.6 * Math.PI * u + 5.1 * ph) + .38 * Math.sin(5.4 * Math.PI * u - 7.7 * ph + 1.3)); if (pI) y += 2.4 * amp * pI * Math.exp(-sq((x - px) / pw)) * Math.sin((x - px) / pw * 2.2 - 17 * ph); return y };
    const S = surfacePoly(M, yc, slope, ripple, 28);
    G = Object.assign(S, { lt, f, slope, A, turb, ke, pI, still, ripple, surfY: x => S.yc + slope * (x - S.xc) + ripple((x - S.xc) / S.hw, x) });
    env.live(id, 'surf', { y: S.yc, xl: S.xL, xr: S.xR, xc: S.xc, hw: S.hw, slope, color: wine });
    return G;
  };
  env.mod(top.n, (o, st, t) => { const g = geom(t); seen = true; lastSt = st; return [Object.assign({}, o, { rings: [toLocal(o, g.pts)] }), st] });
  for (let i = M.top + 1; i < M.lq.length; i++) env.mod(M.lq[i].n, (o, st, t) => Math.abs(geom(t).yc - M.y0) > 1 ? null : [o, st]);
  if (M.srf) env.mod(M.srf.n, (o, st, t) => {
    const g = geom(t), w = g.xR - g.xL, h = .16 * w * (1 + .22 * clamp(g.A / 4) * Math.sin(9 * g.lt * C.sp)), cx = (g.xL + g.xR) / 2, cy = (g.yL + g.yR) / 2;
    return [Object.assign({}, o, { x: cx - w / 2, y: cy - h / 2, w, h, r: Math.atan(g.slope) * 180 / Math.PI }), st];
  });
  const shimmer = p.shimmer !== false && !env.reduced;
  if (M.hl && shimmer) env.mod(M.hl.n, (o, st, t) => {
    const lt = env.local(t), n1 = noise(lt * 2.7 * C.sp, 11), n2 = noise(lt * 3.3 * C.sp, 23);
    return [o, Object.assign({}, st, { alpha: (st.alpha ?? 1) * (.84 + .16 * n1), tx: (st.tx || 0) + .7 * amp * n2, ty: (st.ty || 0) + .5 * amp * n1 })];
  });
  // свой слой: пузырьки (обрезаны контуром вина), пена и блик на поверхности
  const g = el('g', {}, ctx.layer), cid = uid('c'), cp = el('clipPath', { id: cid }, g), cpath = el('path', {}, cp);
  const gb = el('g', { 'clip-path': `url(#${cid})` }, g), gs = el('g', {}, g);
  const nb = p.bubbles === false ? 0 : Math.round((p.n_bubbles ?? 9) * C.den * clamp(size, .5, 2.2)), nx = Math.round(nb * 1.2), rnd = env.rng;
  const bcol = col(p.bubble_color, mixc(wine, '#ffffff', .62));
  const bub = pool(gb, nb + nx, () => ({ e: el('circle', { fill: bcol, 'fill-opacity': .32, stroke: '#ffffff', 'stroke-opacity': .55, 'stroke-width': .8 }, gb), u: rnd() * 1.6 - .8, v: (26 + 30 * rnd()) * C.sp, r: .9 + 1.7 * rnd() * (.7 + .3 * C.amp), ph: rnd(), wf: 2 + 3 * rnd(), wa: (.6 + 1.6 * rnd()) * C.amp }));
  const nf = p.foam === false ? 0 : Math.round(10 * C.den * clamp(size, .6, 2));
  const foam = pool(gs, nf, () => ({ e: el('circle', { fill: '#ffffff', 'fill-opacity': .7, stroke: mixc(wine, '#ffffff', .4), 'stroke-width': .6 }, gs), u: .08 + .84 * rnd(), r: .8 + 1.6 * rnd(), d: rnd() * TAU }));
  const glint = shimmer ? el('ellipse', { fill: '#ffffff' }, gs) : null;
  return {
    frame(lt, t) {
      if (!seen || !G) { show(g, false); return } seen = false; show(g, true);
      const st = lastSt || {}, gg = G;
      setA(g, { opacity: clamp(st.alpha ?? 1).toFixed(3), transform: `translate(${f1((st.dx || 0) * PX + (st.tx || 0))} ${f1((st.dy || 0) * PX + (st.ty || 0))})` });
      if (nb) { setA(cpath, { d: 'M' + gg.pts.map((v, i) => f1(v) + (i % 2 ? (i < gg.pts.length - 1 ? 'L' : '') : ' ')).join('') + 'Z' }) }
      const L = Math.max(4, M.yBot - 5 - gg.yc), time = gg.still ? 0 : gg.lt, extra = clamp(gg.turb * 1.6 + gg.pI);
      for (let i = 0; i < bub.length; i++) {
        const b = bub[i], on = !gg.still && (i < nb || (i - nb) < extra * nx);
        show(b.e, on); if (!on) continue;
        const q = (b.ph + time * b.v / L) % 1, y = M.yBot - 5 - q * L, row = M.rowAt(y), xc = (row[1] + row[2]) / 2, hw = (row[2] - row[1]) / 2;
        const x = xc + b.u * hw * .8 + b.wa * Math.sin(time * b.wf + b.ph * 9), pop = q > .94 ? (q - .94) / .06 : 0;
        setA(b.e, { cx: f1(x), cy: f1(y), r: (b.r * (.7 + .3 * q + .8 * pop)).toFixed(2), opacity: (sstep(clamp(q / .12)) * (1 - pop)).toFixed(2) });
      }
      const fa = gg.still ? 0 : clamp(gg.turb * 1.4 + gg.pI * .8 + (df > .004 ? clamp(1 - (gg.lt - dur) / 1.4) * (gg.lt > dur ? .7 : 0) : 0));
      for (const fo of foam) {
        show(fo.e, fa > .03); if (fa <= .03) continue;
        const x = lerp(gg.xL, gg.xR, fo.u + .02 * Math.sin(time * 1.7 + fo.d));
        setA(fo.e, { cx: f1(x), cy: f1(gg.surfY(x) + .4), r: (fo.r * (.6 + .4 * fa)).toFixed(2), opacity: (fa * (.55 + .45 * Math.sin(time * 3 + fo.d) ** 2)).toFixed(2) });
      }
      if (glint) {
        const x = gg.xc - .36 * gg.hw + .05 * gg.hw * noise(time * 1.3 * C.sp, 5), n = noise(time * 2.6 * C.sp, 9);
        setA(glint, { cx: f1(x), cy: f1(gg.surfY(x) + 1.2), rx: f1(gg.hw * (.13 + .03 * n)), ry: Math.max(.8, gg.hw * .03).toFixed(2), opacity: (.28 + .22 * (n + 1) / 2).toFixed(2), transform: `rotate(${(Math.atan(gg.slope) * 180 / Math.PI).toFixed(2)} ${f1(x)} ${f1(gg.surfY(x))})` });
      }
    },
  };
});

/* ================================================================== 2. pour — струя из A в B */
function lipPoint(env, name, toward) { // край, с которого льётся: верх контура в рамке объекта, самая низкая точка после поворота
  let o = env.find(name); if (!o) o = env.find(normId(name) + '_body'); if (!o) return null;
  if (!(o.k === 'path' && o.rings)) { const b = objBox(o); return [b.x + b.w / 2, b.y] }
  const loc = []; for (const r of o.rings) for (let i = 0; i < r.length; i += 2) loc.push([r[i], r[i + 1]]);
  let y0 = Infinity, y1 = -Infinity; for (const q of loc) { y0 = Math.min(y0, q[1]); y1 = Math.max(y1, q[1]) }
  const sel = loc.filter(q => q[1] <= y0 + .035 * (y1 - y0));
  const w = worldRings(Object.assign({}, o, { rings: [sel.flat()] }))[0];
  let best = null; for (let i = 0; i < w.length; i += 2) { const sc = w[i + 1] + (toward ? -.15 * Math.abs(w[i] - toward[0]) : 0); if (!best || sc > best[2]) best = [w[i], w[i + 1], sc] }
  return [best[0], best[1]];
}
function glassTarget(env, name, from) { // точка падения струи в бокал: поверхность вина, ближе к источнику
  const id = normId(name), s = liveGet(id, 'surf');
  if (s) return [s.xc + clamp((from[0] - s.xc) / Math.max(1, s.hw), -1, 1) * .3 * s.hw, s.y, id];
  const lq = []; for (let i = 0; i < 40; i++) { const o = env.find(id + '_lq' + i); if (!o) break; lq.push(o) }
  if (lq.length) { let best = null; for (const o of lq) { const b = objBox(o); if (b.h > 3 && (!best || b.y < best.y)) best = b } if (best) { const xc = best.x + best.w / 2; return [xc + clamp((from[0] - xc) / (best.w / 2), -1, 1) * .15 * best.w, best.y, id] } }
  const o = env.find(name); if (!o) return null; const b = objBox(o); return [b.x + b.w / 2, b.y + b.h * .25, null];
}
def('pour', (ctx, p, env) => {
  const C = env.C, rnd = env.rng, color = col(p.color, 'red_wine'), W0 = (+p.width || 8.4) * (.85 + .15 * C.amp);
  const A0 = p.from ? [p.from[0], p.from[1]] : p.from_obj ? null : [700, 200];
  const dur = Math.max(.2, +p.dur || 1.6), g = 2600 * (.75 + .25 * C.sp);
  const root = el('g', {}, ctx.layer), rib = el('path', { fill: color, 'fill-opacity': .94 }, root);
  const shine = el('path', { fill: 'none', stroke: '#ffffff', 'stroke-opacity': .38, 'stroke-width': 1.1, 'stroke-linecap': 'round' }, root);
  const nd = p.drops === false ? 0 : Math.round(4 + 6 * C.den), ns = p.splash === false ? 0 : Math.round(6 + 10 * C.den);
  const drops = pool(root, nd, () => ({ e: el('ellipse', { fill: color }, root), off: rnd() * 2 - 1, s: rnd(), r: .25 + .3 * rnd() }));
  const spl = pool(root, ns, () => ({ e: el('circle', { fill: color }, root), a: -Math.PI / 2 + (rnd() - .5) * 2.2, v: (70 + 120 * rnd()) * C.amp, ph: rnd(), r: .9 + 1.6 * rnd() }));
  const rings = pool(root, 2, () => el('ellipse', { fill: 'none', stroke: mixc(color, '#ffffff', .35), 'stroke-width': 1.3 }, root));
  const tail = pool(root, 4, (i) => ({ e: el('circle', { fill: color }, root), k: i }));
  let A = A0, tgt = null;
  const resolve = () => {
    if (p.from_obj) A = lipPoint(env, p.from_obj, p.to || null) || A || [700, 200];
    if (p.to) tgt = [p.to[0], p.to[1], null]; else if (p.to_obj) tgt = glassTarget(env, p.to_obj, A) || [A[0] + 80, A[1] + 260, null]; else tgt = [A[0] + 60, A[1] + 260, null];
  };
  resolve();
  const bez = (P0, P1, P2, u) => { const a = (1 - u) * (1 - u), b = 2 * u * (1 - u), c = u * u; return [a * P0[0] + b * P1[0] + c * P2[0], a * P0[1] + b * P1[1] + c * P2[1]] };
  const bezD = (P0, P1, P2, u) => [2 * (1 - u) * (P1[0] - P0[0]) + 2 * u * (P2[0] - P1[0]), 2 * (1 - u) * (P1[1] - P0[1]) + 2 * u * (P2[1] - P1[1])];
  const hideAll = () => { show(rib, false); show(shine, false); drops.forEach(d => show(d.e, false)); spl.forEach(s => show(s.e, false)); rings.forEach(r => show(r, false)); tail.forEach(d => show(d.e, false)) };
  return {
    always: true,
    frame(lt) {
      if (p.to_obj && !p.to) { const nt = glassTarget(env, p.to_obj, A); if (nt) tgt = nt }
      const B = tgt, dy = Math.max(30, B[1] - A[1]), tf = Math.sqrt(2 * dy / g), bend = p.bend ?? 1;
      const P1 = [A[0] + (B[0] - A[0]) * clamp(.86 * bend, 0, 1), A[1] + (B[1] - A[1]) * .1];
      const L = dur, fin = env.reduced;
      if (fin || lt < 0 || lt > L + tf + 1.4) { hideAll(); if (B[2]) env.live(B[2], 'pour', null); return }
      const u1 = clamp(sq(lt / tf)), u0 = lt < L ? 0 : clamp(sq((lt - L) / tf));
      const on = lt < L + tf * .9 && u1 >= .999, I = on ? clamp(Math.min(lt - tf, L + tf - lt) / .25) * (u0 > .6 ? .4 : 1) : 0;
      if (B[2]) env.live(B[2], 'pour', { x: B[0], on: I > .02, I });
      const ph = lt * C.sp, M = 40, left = [], right = [], mids = [];
      if (u1 - u0 > .002) {
        for (let k = 0; k <= M; k++) {
          const u = lerp(u0, u1, k / M), P = bez(A, P1, B, u), d = bezD(A, P1, B, u), dl = Math.hypot(d[0], d[1]) || 1, nx = -d[1] / dl, ny = d[0] / dl;
          const cap = Math.sqrt(clamp((u1 - u) / .035)) * (u0 > 0 ? Math.sqrt(clamp((u - u0) / .03)) : 1);
          const w = W0 * (1 - .48 * u) * (1 + .16 * C.amp * Math.sin(TAU * (3.4 * u - 2.1 * ph)) + .08 * C.amp * Math.sin(TAU * (7.3 * u - 3.7 * ph) + 1)) * Math.max(.18, cap) / 2;
          left.push(P[0] + nx * w, P[1] + ny * w); right.push(P[0] - nx * w, P[1] - ny * w); mids.push(P[0] + nx * w * .45, P[1] + ny * w * .45);
        }
        let s = 'M'; for (let i = 0; i < left.length; i += 2) s += f1(left[i]) + ' ' + f1(left[i + 1]) + 'L';
        for (let i = right.length - 2; i >= 0; i -= 2) s += f1(right[i]) + ' ' + f1(right[i + 1]) + (i ? 'L' : 'Z');
        setA(rib, { d: s }); show(rib, true);
        let s2 = 'M'; for (let i = 0; i < mids.length; i += 2) s2 += f1(mids[i]) + ' ' + f1(mids[i + 1]) + (i < mids.length - 2 ? 'L' : '');
        setA(shine, { d: s2 }); show(shine, true);
      } else { show(rib, false); show(shine, false) }
      // капли вдоль струи (отрываются от краёв) и последние капли после конца
      for (let i = 0; i < drops.length; i++) {
        const d = drops[i], per = .55 / C.sp, q = ((lt / per) + d.s) % 1, u = sq(q), live = lt > tf && lt < L && u > u0 && u < u1;
        show(d.e, live); if (!live) continue;
        const P = bez(A, P1, B, u), dd = bezD(A, P1, B, u), dl = Math.hypot(dd[0], dd[1]) || 1, off = d.off * W0 * (.9 + 1.4 * u) * C.amp;
        setA(d.e, { cx: f1(P[0] - dd[1] / dl * off), cy: f1(P[1] + dd[0] / dl * off), rx: (W0 * d.r * .5).toFixed(2), ry: (W0 * d.r * (.5 + .6 * u)).toFixed(2), opacity: (.85 * (1 - q * .5)).toFixed(2) });
      }
      for (const d of tail) {
        const t0 = L + tf * .8 + d.k * .2 / C.sp, q = (lt - t0) / tf, live = q > 0 && q < 1 && d.k < 1 + 2 * C.den;
        show(d.e, live); if (!live) continue; const P = bez(A, P1, B, sq(q));
        setA(d.e, { cx: f1(P[0]), cy: f1(P[1]), r: (W0 * (.32 - .05 * d.k)).toFixed(2) });
      }
      // брызги и круги у поверхности
      for (const s of spl) {
        const per = .5 / C.sp, q = ((lt - tf) / per + s.ph) % 1, live = I > .05 && lt > tf;
        show(s.e, live); if (!live) continue; const tt = q * per * 1.1;
        setA(s.e, { cx: f1(B[0] + Math.cos(s.a) * s.v * tt), cy: f1(B[1] + Math.sin(s.a) * s.v * tt + .5 * 900 * tt * tt), r: (s.r * (1 - .5 * q)).toFixed(2), opacity: (I * (1 - q)).toFixed(2) });
      }
      rings.forEach((r, k) => {
        const per = .7 / C.sp, q = ((lt - tf) / per + k * .5) % 1; show(r, I > .05); if (I <= .05) return; const R = 4 + 26 * C.amp * DC.ease.out(q);
        setA(r, { cx: f1(B[0]), cy: f1(B[1] + 1), rx: f1(R), ry: f1(R * .22), 'stroke-opacity': (I * (1 - q) * .8).toFixed(2) });
      });
    },
    unmount() { tgt = null },
  };
});

/* ================================================================== 3a. bubbles — пузырьки в области или объекте */
def('bubbles', (ctx, p, env) => {
  const C = env.C, rnd = env.rng;
  let box = p.area ? boxOf(env, p.area) : null, clipD = null, glass = null;
  if (p.obj) {
    const id = normId(p.obj), lq0 = env.find(id + '_lq0');
    if (lq0) { glass = id; const rs = []; for (let i = 0; i < 40; i++) { const o = env.find(id + '_lq' + i); if (!o) break; rs.push(...worldRings(o)) } box = ringsBox(rs); clipD = ringsD(rs) }
    else { const o = env.find(p.obj); if (o) { const rs = worldRings(o); box = ringsBox(rs); if (p.clip !== false && o.k === 'path') clipD = ringsD(rs) } }
  }
  if (!box) { console.warn('bubbles: нет области'); return {} }
  const root = el('g', {}, ctx.layer); let gb = root;
  if (clipD) { const id = uid('c'), cp = el('clipPath', { id }, root); el('path', { d: clipD }, cp); gb = el('g', { 'clip-path': `url(#${id})` }, root) }
  const n = Math.round((p.n ?? Math.max(6, box.w * box.h / 900)) * C.den), c = col(p.color, '#ffffff'), sz = +p.size || 1;
  const bs = pool(gb, Math.min(n, 300), () => ({ e: el('circle', { fill: c, 'fill-opacity': .22, stroke: c, 'stroke-opacity': .75, 'stroke-width': .9 }, gb), x: rnd(), v: (24 + 36 * rnd()) * C.sp * (+p.speed || 1), r: (1 + 2.6 * rnd()) * sz * (.75 + .25 * C.amp), ph: rnd(), wf: 1.5 + 3 * rnd(), wa: (.8 + 2.2 * rnd()) * C.amp }));
  return {
    frame(lt) {
      const fade = env.reduced ? 1 : clamp(lt / .5), time = env.reduced ? 0 : Math.max(0, lt);
      let top = box.y; if (glass) { const s = liveGet(glass, 'surf'); if (s) top = s.y }
      const L = Math.max(4, box.y + box.h - top);
      for (const b of bs) {
        const q = (b.ph + time * b.v / L) % 1, y = box.y + box.h - q * L, pop = q > .93 ? (q - .93) / .07 : 0;
        setA(b.e, { cx: f1(box.x + b.x * box.w + b.wa * Math.sin(time * b.wf + b.ph * 7)), cy: f1(y), r: (b.r * (.6 + .4 * q + .7 * pop)).toFixed(2), opacity: (fade * sstep(clamp(q / .1)) * (1 - pop)).toFixed(2) });
      }
    },
  };
});

/* ================================================================== 3b. drip — капли с края */
def('drip', (ctx, p, env) => {
  const C = env.C, rnd = env.rng, c = col(p.color, 'red_wine'), R = (+p.size || 5.4) * (.8 + .2 * C.amp);
  let src = [];
  if (Array.isArray(p.at) && Array.isArray(p.at[0])) src = p.at.map(q => [q[0], q[1]]);
  else if (Array.isArray(p.at)) src = [[p.at[0], p.at[1]]];
  else if (p.obj) { const o = env.find(p.obj); if (o) { const rs = worldRings(o), b = ringsBox(rs), n = Math.max(1, p.n || 1); for (let k = 0; k < n; k++) { const x = b.x + b.w * (n === 1 ? .5 : .18 + .64 * k / (n - 1)); let yb = b.y + b.h; for (const r of rs) { const ys = []; for (let i = 0; i < r.length; i += 2) { const j = (i + 2) % r.length; if ((r[i] - x) * (r[j] - x) <= 0 && r[i] !== r[j]) ys.push(r[i + 1] + (r[j + 1] - r[i + 1]) * (x - r[i]) / (r[j] - r[i])) } if (ys.length) yb = Math.max(...ys) } src.push([x, yb]) } } }
  if (!src.length) { console.warn('drip: нет точки'); return {} }
  const floor = p.floor ?? Math.min(890, Math.max(...src.map(s => s[1])) + 160), per = (+p.period || 1.8) / C.sp, g = 1500 * (.8 + .2 * C.sp);
  const root = el('g', {}, ctx.layer);
  const S = src.map((s, k) => ({ s, ph: k * .37 + rnd() * .3, hang: el('path', { fill: c }, root), fall: el('ellipse', { fill: c }, root), splat: el('ellipse', { fill: c }, root), mic: pool(root, 3, () => el('circle', { fill: c }, root)), md: [rnd(), rnd(), rnd()] }));
  const grow = .62;
  return {
    frame(lt) {
      for (const d of S) {
        const [x0, y0] = d.s, tt = env.reduced ? grow * per * .9 : lt + d.ph * per;
        if (lt < 0 && !env.reduced) { show(d.hang, false); show(d.fall, false); show(d.splat, false); d.mic.forEach(m => show(m, false)); continue }
        const q = (tt / per) % 1, cyc = Math.floor(tt / per), wob = 1 + .04 * C.amp * Math.sin(tt * 11);
        // висящая капля: растёт, вытягивается; после отрыва остаётся маленький «хвостик»
        let rr, ext;
        if (q < grow) { const k = DC.ease.out(q / grow); rr = R * (.25 + .75 * k); ext = rr * (.55 + .9 * k * k) } else { const k = clamp((q - grow) / .2); rr = R * .3 * (1 - k) + R * .25 * k; ext = rr * .4 }
        const cy = y0 + ext + rr * .2, nw = Math.min(rr * .55, R * .4);
        setA(d.hang, { d: `M${f1(x0 - nw)} ${f1(y0)}C${f1(x0 - nw)} ${f1(y0 + ext * .5)} ${f1(x0 - rr * wob)} ${f1(cy - rr * .6)} ${f1(x0 - rr * wob)} ${f1(cy)}A${f1(rr * wob)} ${f1(rr)} 0 0 0 ${f1(x0 + rr * wob)} ${f1(cy)}C${f1(x0 + rr * wob)} ${f1(cy - rr * .6)} ${f1(x0 + nw)} ${f1(y0 + ext * .5)} ${f1(x0 + nw)} ${f1(y0)}Z` });
        show(d.hang, true);
        // падение
        const tfall = (q - grow) * per, yS = y0 + R * 1.6, y = yS + .5 * g * tfall * tfall, v = g * tfall, falling = q >= grow && y < floor;
        show(d.fall, falling && !env.reduced);
        if (falling) setA(d.fall, { cx: f1(x0), cy: f1(y), rx: f1(R * (1 - Math.min(.25, v / 4000))), ry: f1(R * (1 + Math.min(.9, v / 1100))) });
        // всплеск на полу
        const tHit = Math.sqrt(2 * Math.max(0, floor - yS) / g), ts = tfall - tHit, splash = q >= grow && ts > 0 && !env.reduced;
        const ts2 = splash ? ts : (q < grow && cyc > 0 ? ts + per : -1), sp = ts2 > 0 ? ts2 / (.9 / C.sp) : -1;
        show(d.splat, sp > 0 && sp < 1);
        if (sp > 0 && sp < 1) setA(d.splat, { cx: f1(x0), cy: f1(floor), rx: f1(R * (.6 + 2.4 * DC.ease.out(sp)) * (.8 + .2 * C.amp)), ry: f1(R * .32 * (1 - .4 * sp)), opacity: (1 - sp).toFixed(2) });
        d.mic.forEach((m, j) => {
          const on = sp > 0 && sp < .7 && j < 1 + C.den * 1.2; show(m, on); if (!on) return;
          const a = -Math.PI / 2 + (d.md[j] - .5) * 2.4, vv = (60 + 90 * d.md[(j + 1) % 3]) * C.amp, tt2 = sp * .9 / C.sp * .7;
          setA(m, { cx: f1(x0 + Math.cos(a) * vv * tt2), cy: f1(floor + Math.sin(a) * vv * tt2 + 450 * tt2 * tt2), r: f1(R * .28), opacity: (1 - sp / .7).toFixed(2) });
        });
      }
    },
  };
});

/* ================================================================== 3c. stain — пятно растекается и подсыхает */
def('stain', (ctx, p, env) => {
  const C = env.C, rnd = env.rng;
  let at = p.at ? [p.at[0], p.at[1]] : null, R = +p.r || 54, c = col(p.color, 'red_wine'), objMode = null;
  if (p.obj) { const o = env.find(p.obj); if (o) { const b = objBox(o); at = mid(b); R = Math.max(b.w, b.h) / 2; c = col(p.color, o.f || o.s || c); objMode = o } }
  if (!at) { console.warn('stain: нет точки'); return {} }
  const dur = Math.max(.2, +p.dur || 1.4) / C.sp, dry = p.dry ?? dur + 1.2, sqz = +p.squash || 1;
  if (objMode) { // режим объекта: растекается и подсыхает сам объект слайда (и его бледная середина «_in»)
    const grow = lt => lt < 0 ? .05 : .05 + .95 * (1 - Math.pow(1 - clamp(lt / dur), 3)) * (1 + .03 * Math.sin(lt * 6) * clamp(1 - lt / dur));
    const mod = (o, st, t) => { const lt = env.local(t), k = grow(lt), d = clamp((lt - dry) / 1.5); return [o, Object.assign({}, st, { scale: (st.scale ?? 1) * k, alpha: (st.alpha ?? 1) * (lt < 0 ? 0 : clamp(lt / .15)) * (1 - .45 * d) })] };
    env.mod(objMode.n, mod); const inn = env.find(objMode.n + '_in'); if (inn) env.mod(inn.n, mod);
    return {};
  }
  const N = 96, H = [2, 3, 5, 7, 11].map(k => [k, (.35 + .65 * rnd()) / Math.pow(k, .7) * .16 * (.6 + .4 * C.amp), rnd() * TAU]);
  const root = el('g', {}, ctx.layer), fill = el('path', { fill: c }, root), ring = el('path', { fill: 'none', stroke: mixc(c, '#000000', .18), 'stroke-linejoin': 'round' }, root);
  const ns = Math.round(C.den > 1 ? 5 * C.den : C.den > .8 ? 3 : 0);
  const sats = pool(root, ns, () => ({ e: el('path', { fill: c }, root), a: rnd() * TAU, d: 1.15 + .55 * rnd(), r: .05 + .08 * rnd(), s: (rnd() * 1e4) | 0 }));
  const blobD = (cx, cy, r, amp, sd) => { let s = ''; for (let i = 0; i < N; i++) { const a = i / N * TAU; let k = 1; for (const [h, A, ph] of H) k += A * amp * Math.sin(h * a + ph + sd); s += (i ? 'L' : 'M') + f1(cx + Math.cos(a) * r * k) + ' ' + f1(cy + Math.sin(a) * r * k * sqz) } return s + 'Z' };
  return {
    frame(lt) {
      if (lt < 0) { show(root, false); return } show(root, true);
      const k = 1 - Math.pow(1 - clamp(lt / dur), 3), creep = 1 + .035 * clamp((lt - dur) / 3), r = R * (.08 + .92 * k) * creep;
      const d = clamp((lt - dry) / 1.5), fa = lerp(.55, .14, d), wob = env.reduced ? 0 : .004 * C.amp * Math.sin(lt * 7) * (1 - k);
      setA(fill, { d: blobD(at[0], at[1], r, .4 + .6 * k + wob * 40, 0), 'fill-opacity': fa.toFixed(3) });
      setA(ring, { d: blobD(at[0], at[1], r * .985, .4 + .6 * k, 0), 'stroke-opacity': (.62 * d).toFixed(3), 'stroke-width': (1 + 1.8 * d).toFixed(2) });
      for (const s of sats) {
        const pk = clamp(lt / .18), rr = R * s.r * (.4 + .6 * pk);
        setA(s.e, { d: blobD(at[0] + Math.cos(s.a) * R * s.d * (.3 + .7 * k), at[1] + Math.sin(s.a) * R * s.d * (.3 + .7 * k) * sqz, rr, .8, s.s), 'fill-opacity': (fa * 1.2).toFixed(3) });
      }
    },
  };
});

/* ================================================================== 4. particles — поле точек и раскладки */
const GA = Math.PI * (3 - Math.sqrt(5));
function particleLayout(kind, P, env) {
  const { N, grp, rank, counts, start, area: a, K } = P, out = new Float32Array(N * 2), rnd = U.rng(((env.p.seed || 1) * 7919 + kind.length * 131) >>> 0);
  const gauss = () => { let u = 0, v = 0; while (u === 0) u = rnd(); v = rnd(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(TAU * v) };
  const meta = { labels: [] };
  if (kind === 'cloud' || kind === 'clusters') {
    const cl = kind === 'clusters';
    for (let i = 0; i < N; i++) {
      const g = grp[i], cx = cl ? a.x + a.w * (g + .5) / K : a.x + a.w / 2, cy = a.y + a.h / 2, sx = cl ? a.w / K * .2 : a.w * .2, sy = a.h * (cl ? .2 : .22);
      out[2 * i] = clamp(cx + gauss() * sx, a.x, a.x + a.w); out[2 * i + 1] = clamp(cy + gauss() * sy, a.y, a.y + a.h);
    }
  } else if (kind === 'grid') {
    const cols = Math.ceil(Math.sqrt(N * a.w / a.h)), rows = Math.ceil(N / cols), cell = Math.min(a.w / cols, a.h / rows), ox = a.x + (a.w - cols * cell) / 2, oy = a.y + (a.h - rows * cell) / 2;
    for (let i = 0; i < N; i++) { const j = start[grp[i]] + rank[i]; out[2 * i] = ox + (j % cols + .5) * cell; out[2 * i + 1] = oy + (Math.floor(j / cols) + .5) * cell }
    meta.cell = cell;
  } else if (kind === 'groups') {
    const rs = counts.map(c => Math.sqrt(Math.max(c, 1))), sum = rs.reduce((s, v) => s + v, 0), gap = a.w * .06;
    const k = Math.min((a.w - gap * (K - 1)) / (2 * sum), a.h * .82 / (2 * Math.max(...rs)));
    let x = a.x + (a.w - (2 * k * sum + gap * (K - 1))) / 2; const cxs = [];
    for (let g = 0; g < K; g++) { cxs.push(x + k * rs[g]); x += 2 * k * rs[g] + gap }
    for (let i = 0; i < N; i++) { const g = grp[i], R = k * rs[g], r = R * Math.sqrt((rank[i] + .5) / counts[g]), th = rank[i] * GA; out[2 * i] = cxs[g] + r * Math.cos(th); out[2 * i + 1] = a.y + a.h * .45 + r * Math.sin(th) }
    for (let g = 0; g < K; g++) meta.labels.push([cxs[g], a.y + a.h * .45 + k * rs[g] + 18]);
  } else if (kind === 'bars') {
    const slot = a.w / K, bw = slot * .7, H = a.h * .86, mx = Math.max(...counts, 1);
    let c = Math.sqrt(bw * H / mx); for (let it = 0; it < 60 && Math.ceil(mx / Math.max(1, Math.floor(bw / c))) * c > H; it++) c *= .97;
    const cb = Math.max(1, Math.floor(bw / c));
    for (let i = 0; i < N; i++) { const g = grp[i], r = rank[i], x0 = a.x + slot * g + (slot - cb * c) / 2; out[2 * i] = x0 + (r % cb + .5) * c; out[2 * i + 1] = a.y + H - (Math.floor(r / cb) + .5) * c }
    for (let g = 0; g < K; g++) meta.labels.push([a.x + slot * (g + .5), a.y + H + 18]);
    meta.cell = c;
  } else if (kind === 'into') { // бокал: горло над вином; объект — место в его рамке (там точка гаснет)
    const T = P.sinks;
    for (let i = 0; i < N; i++) { const s = T[grp[i] % T.length], b = s.box; out[2 * i] = s.glass ? s.rimC : b.x + b.w / 2 + (rnd() - .5) * b.w * .5; out[2 * i + 1] = s.glass ? s.sy + 4 : b.y + b.h * .3 + (rnd() - .5) * b.h * .2 }
  } else return particleLayout('cloud', P, env);
  return { pos: out, meta, kind };
}
function makeStamp(cv, r0, cols, grp) { // сглаженный диск со сдвигом на 1/4 пикселя; смешивание src-over прямо в буфере
  const W = cv.c.width, H = cv.c.height, sk = W / cv.w, img = cv.g.createImageData(W, H), d = img.data, R = r0 * sk, rr = Math.ceil(R + 1), S = 2 * rr + 2, Q = 4, masks = [];
  for (let fy = 0; fy < Q; fy++) for (let fx = 0; fx < Q; fx++) { // разреженная маска: только покрытые пиксели
    const xs = [], ys = [], cs = [];
    for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) { const c = clamp(R + .5 - Math.hypot(x - rr - fx / Q, y - rr - fy / Q)); if (c > 0) { xs.push(x); ys.push(y); cs.push(c) } }
    masks.push({ xs: Int16Array.from(xs), ys: Int16Array.from(ys), cs: Float32Array.from(cs), off: Int32Array.from(xs.map((x, i) => (ys[i] * W + x) * 4)) });
  }
  const rgbs = cols.map(c => c.slice());
  return (cur, alpha) => {
    d.fill(0);
    for (let i = 0, n = alpha.length; i < n; i++) {
      const al = alpha[i]; if (al < .03) continue;
      const px = (cur[2 * i] - cv.x) * sk, py = (cur[2 * i + 1] - cv.y) * sk, ix = Math.floor(px), iy = Math.floor(py), m = masks[(((py - iy) * Q) | 0) * Q + (((px - ix) * Q) | 0)];
      const c = rgbs[grp[i] % rgbs.length], cr = c[0], cg = c[1], cb = c[2], x0 = ix - rr, y0 = iy - rr, cs = m.cs, len = cs.length;
      const inside = x0 >= 0 && y0 >= 0 && x0 + S < W && y0 + S < H, base = (y0 * W + x0) * 4, off = m.off;
      for (let k = 0; k < len; k++) {
        let o;
        if (inside) o = base + off[k]; else { const xx = x0 + m.xs[k], yy = y0 + m.ys[k]; if (xx < 0 || yy < 0 || xx >= W || yy >= H) continue; o = (yy * W + xx) * 4 }
        const a = cs[k] * al;
        if (a >= .995 || d[o + 3] === 0) { d[o] = cr; d[o + 1] = cg; d[o + 2] = cb; d[o + 3] = a * 255; continue }
        const da = d[o + 3] / 255, oa = a + da * (1 - a), k1 = a / oa, k2 = 1 - k1;
        d[o] = cr * k1 + d[o] * k2; d[o + 1] = cg * k1 + d[o + 1] * k2; d[o + 2] = cb * k1 + d[o + 2] * k2; d[o + 3] = oa * 255;
      }
    }
    cv.g.putImageData(img, 0, 0);
  };
}
def('particles', (ctx, p, env) => {
  const C = env.C, N = clamp(p.n | 0 || 1200, 1, 6000), a = p.area ? boxOf(env, p.area) : { x: 80, y: 120, w: 1440, h: 660 };
  const shares = ((p.shares || p.groups || []).length ? (p.shares || p.groups) : [1]).map(Number), K = shares.length, ssum = shares.reduce((s, v) => s + v, 0) || 1;
  const counts = shares.map(s => Math.floor(s / ssum * N)); let rem = N - counts.reduce((s, v) => s + v, 0); for (let g = 0; rem > 0; g = (g + 1) % K, rem--) counts[g]++;
  const start = []; let acc = 0; for (const c of counts) { start.push(acc); acc += c }
  const grp = new Uint16Array(N), rank = new Uint32Array(N); for (let g = 0; g < K; g++) for (let r = 0; r < counts[g]; r++) { grp[start[g] + r] = g; rank[start[g] + r] = r }
  const colors = (p.colors && p.colors.length ? p.colors : ['accent', 'accent3', 'accent2', 'ink2']).map(c => col(c));
  const P = { N, grp, rank, counts, start, area: a, K, sinks: [] };
  // цели «стекания». Бокал: точка летит к горлу (внутри ободка), падает сквозь него в вино и растворяется под
  // поверхностью — над ободом ничего не копится; поверхность — живая (liquid) или статичная. Объект — гаснет в рамке.
  const gcache = new Map();
  const glassStatic = id => {
    if (gcache.has(id)) return gcache.get(id);
    const lqs = []; for (let i = 0; i < 40; i++) { const o = env.find(id + '_lq' + i); if (!o) break; lqs.push(worldRings(o)[0]) }
    let G = null;
    if (lqs.length) {
      const bb = ringsBox(lqs); let y0 = Infinity; for (const r of lqs) { const b = ringsBox([r]); if (b.h > 3) y0 = Math.min(y0, b.y) } if (!isFinite(y0)) y0 = bb.y;
      const yb = bb.y + bb.h, rows = [];
      for (let k = 0; k <= 24; k++) { const y = y0 + .5 + (yb - y0 - 1) * k / 24; let l = Infinity, r = -Infinity; for (const q of lqs) { const xs = crossX(q, y); if (xs.length > 1) { l = Math.min(l, xs[0]); r = Math.max(r, xs[xs.length - 1]) } } if (l < r) rows.push([y, l, r]) }
      const body = env.find(id + '_body'); let rimY = y0 - 30, rl = rows.length ? rows[0][1] : bb.x, rr = rows.length ? rows[0][2] : bb.x + bb.w;
      if (body) { const br = worldRings(body)[0], b2 = ringsBox([br]), xm = (rl + rr) / 2; rimY = b2.y; const xs = crossX(br, rimY + 5); for (let j = 0; j + 1 < xs.length; j += 2) if (xs[j] <= xm && xs[j + 1] >= xm) { rl = xs[j] + 5; rr = xs[j + 1] - 5 } }
      G = { y0, yb, rows, rimY, rimC: (rl + rr) / 2, rimH: Math.max(4, (rr - rl) / 2), box: body ? objBox(body) : bb };
    }
    gcache.set(id, G); return G;
  };
  const sinkOf = n => {
    const id = normId(n), G = glassStatic(id);
    if (G) {
      const s = liveGet(id, 'surf'), R = G.rows;
      const chord = y => { if ((s && y < G.y0) || !R.length) return s ? [s.xl, s.xr] : [G.rimC - G.rimH, G.rimC + G.rimH]; let k = 0; while (k < R.length - 1 && R[k + 1][0] < y) k++; return [R[k][1], R[k][2]] };
      return { glass: true, sy: s ? s.y : G.y0, yb: G.yb, rimY: G.rimY, rimC: G.rimC, rimH: G.rimH, chord, box: G.box };
    }
    const o = env.find(n); return { glass: false, box: o ? objBox(o) : { x: a.x + a.w / 2 - 20, y: a.y + a.h, w: 40, h: 12 } };
  };
  const sinks = () => (p.link_to || p.targets || []).map(sinkOf);
  const LK = { glasses: 'into', targets: 'into', histogram: 'bars', hist: 'bars', waffle: 'grid' };
  const lay0 = p.layouts || (Array.isArray(p.layout) ? p.layout : p.layout ? [p.layout] : null);
  const phases0 = (lay0 && lay0.length ? lay0 : [{ kind: 'cloud', at: 0 }]).map(q => typeof q === 'string' ? { kind: q } : Object.assign({}, q));
  phases0.forEach((q, k) => { q.kind = LK[q.kind] || q.kind; if (q.at === undefined) q.at = k * (+p.every || 1.45) });
  const ph = phases0.sort((x, y) => x.at - y.at);
  if (ph.some(q => q.kind === 'into')) P.sinks = sinks();
  // облако, сетка, группы не заходят на бокалы-цели: низ рамки — над ободками (если остаётся ≥ 40 % высоты)
  const rims = P.sinks.filter(q => q.glass).map(q => q.rimY - 24);
  if (rims.length) { const yb = Math.min(...rims); if (yb < a.y + a.h && yb - a.y >= a.h * .4) P.area = { x: a.x, y: a.y, w: a.w, h: yb - a.y } }
  const lays = ph.map(q => particleLayout(q.kind, P, env));
  const rnd = env.rng, phi = new Float32Array(N), bendK = new Float32Array(N), ordK = new Float32Array(N);
  for (let i = 0; i < N; i++) { phi[i] = rnd() * TAU; bendK[i] = (rnd() - .5) * 2; ordK[i] = rnd() }
  const r0 = p.size ? +p.size : clamp(Math.sqrt(a.w * a.h / N) * .3, .9, 5);
  let cb = { x0: a.x, y0: a.y, x1: a.x + a.w, y1: a.y + a.h + 40 }; // canvas накрывает и цели стекания
  for (const s of P.sinks) { const b = s.box; cb = { x0: Math.min(cb.x0, b.x), y0: Math.min(cb.y0, b.y - 20), x1: Math.max(cb.x1, b.x + b.w), y1: Math.max(cb.y1, b.y + b.h) } }
  const pad = 40, cv = env.canvas(cb.x0 - pad, cb.y0 - pad, cb.x1 - cb.x0 + 2 * pad, cb.y1 - cb.y0 + 2 * pad), g = cv.g;
  const times = Q => { const into = Q.kind === 'into'; return [(Q.dur ?? (into ? 1.1 : 1.0)) / C.sp, (Q.stagger ?? (into ? 1.3 : .55 * (.5 + .5 * C.jit))) / C.sp] };
  const stamp = r0 > 1.6 && N >= 500 && p.stamp !== false ? makeStamp(cv, r0, colors.map(rgb), grp) : null;
  const labels = p.labels || null, lfont = `${Math.round(13 * 120 / 72)}px ${font('body')}`;
  const cur = new Float32Array(N * 2), alpha = new Float32Array(N);
  const order = (i, A, B) => { // очередь сдвига: спокойно — случайно, живо — слева направо, драматично — от центра
    if (env.p.character === 'calm') return ordK[i];
    if (env.p.character === 'dramatic') return clamp(Math.hypot(A[2 * i] - a.x - a.w / 2, A[2 * i + 1] - a.y - a.h / 2) / (Math.hypot(a.w, a.h) / 2)) * .75 + ordK[i] * .25;
    return clamp((A[2 * i] - a.x) / a.w) * .6 + ordK[i] * .4;
  };
  let lastDraw = -1, lastTick = -1;
  return {
    always: true,
    frame(lt) {
      if (env.reduced && lastDraw === 1) return;
      let k = 0; for (let j = 0; j < ph.length; j++) if (lt >= ph[j].at) k = j;
      { const Qk = ph[k], [dk, sk2] = times(Qk), busy = lt < Qk.at + dk + sk2 + .6 || (k + 1 < ph.length && lt > ph[k + 1].at - .1);
        const tick = Math.floor(lt * 30); if (!busy && !env.reduced && tick === lastTick) return; lastTick = tick } // в покое — 30 к/с
      const appear = env.reduced ? 1 : clamp((lt - ph[0].at) / .5);
      if (lt < ph[0].at && !env.reduced) { cv.clear(); lastDraw = 0; return }
      if (env.reduced) k = ph.length - 1;
      const L1 = lays[k], L0 = k > 0 ? lays[k - 1] : L1, Q = ph[k];
      const [d, stag] = times(Q), into = L1.kind === 'into';
      if (into && P.sinks.length) { const ns = sinks(); for (let s = 0; s < ns.length; s++) P.sinks[s] = ns[s] }
      const SK = P.sinks, nS = SK.length;
      const tt = env.reduced ? 1e4 : lt - Q.at, jA = (L1.kind === 'cloud' || L1.kind === 'clusters' ? 2.6 : .7) * C.amp, w1 = 1.1 * C.sp, ezf = E(Q.ease || 'inOut');
      const A = L0.pos, B = L1.pos;
      for (let i = 0; i < N; i++) {
        const o = k > 0 ? order(i, A, B) * stag : 0, e = k > 0 ? clamp((tt - o) / d) : 1;
        let x, y, al = appear;
        if (into && nS && SK[grp[i] % nS].glass) { // сквозь горло в вино, растворение в 10 px под поверхностью
          const S = SK[grp[i] % nS], u = bendK[i], ax = A[2 * i], ay = A[2 * i + 1];
          const xE = S.rimC + u * S.rimH * .5, yE = S.rimY - 8, yB = S.sy + 4 + (phi[i] / TAU) * Math.max(6, (S.yb - S.sy) * .5), ch = S.chord(yB), xB = (ch[0] + ch[1]) / 2 + u * (ch[1] - ch[0]) * .35;
          if (e < .7) { const t = e / .7, q = Math.pow(t, 1.6), dx = xE - ax, dy = yE - ay, dist = Math.hypot(dx, dy) || 1, bend = Math.sin(Math.PI * q) * bendK[(i * 7 + 3) % N] * dist * .16 * C.amp; x = ax + dx * q - dy / dist * bend; y = ay + dy * q + dx / dist * bend } // разгон без торможения у горла — без «пробки» на ободке
          else { const q = (e - .7) / .3; x = lerp(xE, xB, q); y = lerp(yE, yB, q * q) }
          if (y > S.sy) al *= 1 - clamp((y - S.sy) / 10); if (e >= 1) al = 0;
          cur[2 * i] = x; cur[2 * i + 1] = y; alpha[i] = al; continue;
        }
        if (e >= 1) { x = B[2 * i]; y = B[2 * i + 1] }
        else {
          const ax = A[2 * i], ay = A[2 * i + 1], bx = B[2 * i], by = B[2 * i + 1];
          if (into) { const ex = DC.ease.out(e), ey = e * e; x = lerp(ax, bx, ex); y = lerp(ay, by, ey) }
          else { const q = ezf(e), dx = bx - ax, dy = by - ay, dist = Math.hypot(dx, dy) || 1, bend = Math.sin(Math.PI * q) * bendK[i] * dist * .28 * C.amp; x = ax + dx * q - dy / dist * bend; y = ay + dy * q + dx / dist * bend }
        }
        if (into) { const arr = clamp((tt - o - d) / .45); al *= 1 - arr; if (e >= 1) { x = B[2 * i]; y = B[2 * i + 1] + 4 * arr } }
        else if (!env.reduced) { const s = e >= 1 ? 1 : .35; x += s * jA * Math.sin(lt * w1 + phi[i]); y += s * jA * Math.cos(lt * w1 * 1.3 + phi[i] * 1.7) }
        cur[2 * i] = x; cur[2 * i + 1] = y; alpha[i] = al;
      }
      if (stamp) stamp(cur, alpha); // много крупных точек: штампы в ImageData (быстрее arc на программной растеризации)
      else {
        cv.clear();
        for (let gi = 0; gi < K; gi++) {
          g.fillStyle = colors[gi % colors.length];
          for (const [lo, hi, ga] of [[.75, 2, 1], [.35, .75, .55], [.05, .35, .22]]) {
            g.globalAlpha = ga; g.beginPath(); let any = false;
            for (let i = start[gi], e = start[gi] + counts[gi]; i < e; i++) { const al = alpha[i]; if (al < lo || al >= hi) continue; any = true; const x = cur[2 * i], y = cur[2 * i + 1]; if (r0 <= 1.6) g.rect(x - r0, y - r0, 2 * r0, 2 * r0); else { g.moveTo(x + r0, y); g.arc(x, y, r0, 0, TAU) } }
            if (any) g.fill();
          }
        }
        g.globalAlpha = 1;
      }
      if (labels && L1.meta.labels.length) {
        const settle = clamp((tt - stag - d * .8) / .5) * appear;
        if (settle > 0) { g.font = lfont; g.textAlign = 'center'; g.textBaseline = 'top'; g.globalAlpha = settle;
          L1.meta.labels.forEach(([x, y], gi) => { if (!labels[gi]) return; g.fillStyle = col('ink2'); g.fillText(String(labels[gi].t ?? labels[gi]), x, y); if (p.counts !== false) { g.fillStyle = col('muted'); g.fillText(ssum > 1.5 ? fmtNum(shares[gi], { grp: '\u00a0' }) : fmtNum(shares[gi] / ssum * 100, { suf: '\u00a0%' }), x, y + 22) } });
          g.globalAlpha = 1 }
      }
      lastDraw = env.reduced ? 1 : 2;
    },
  };
});

/* ================================================================== 5. signal — сигнал по сети */
function barsView(parent, spec, env) { // горизонтальные/вертикальные столбики с пружиной и счётчиками
  const C = env.C, [zeta, omega] = springOf(env.p), items = spec.items || [], orient = spec.orient || 'h', b = spec.box;
  const vmax = spec.vmax || Math.max(...items.map(i => Math.abs(+i.v || 0)), 1e-9), fs = spec.size || 18, f = spec.fmt || {};
  const labW = orient === 'h' && items.some(i => i.label) ? (spec.labW ?? b.w * .3) : 0, valW = orient === 'h' ? (spec.valW ?? fs * 3.6) : 0;
  const n = items.length, slot = (orient === 'h' ? b.h : b.w) / Math.max(n, 1), th = slot * (spec.thick ?? .62);
  const g = el('g', {}, parent), L = orient === 'h' ? b.w - labW - valW : b.h - (items.some(i => i.label) ? fs * 1.6 : 0) - fs * 1.5;
  const rows = items.map((it, k) => {
    const c = col(it.c || it.color, spec.color || 'accent');
    const r = el('rect', { fill: c, rx: Math.min(4, th / 4) }, g);
    const lt = it.label ? el('text', { 'font-family': font('body'), 'font-size': fs, fill: col(spec.ink, 'ink2'), 'text-anchor': orient === 'h' ? 'end' : 'middle', 'dominant-baseline': orient === 'h' ? 'central' : 'hanging' }, g) : null;
    if (lt) lt.textContent = it.label;
    const vt = el('text', { 'font-family': font('body'), 'font-size': fs, 'font-weight': it.bold ? 700 : 600, fill: col(it.vc || spec.vcol, k === spec.hl ? c : 'ink2'), 'text-anchor': orient === 'h' ? 'start' : 'middle', 'dominant-baseline': orient === 'h' ? 'central' : 'auto' }, g);
    return { it, r, lt, vt, c, k };
  });
  return {
    g,
    update(lt0) {
      for (const R of rows) {
        const lt = lt0 - R.k * (spec.stagger ?? .16) / C.sp, s = env.reduced ? 1 : spring(lt * C.sp, zeta, omega), cnt = env.reduced ? 1 : DC.ease.out(clamp(lt * C.sp / 1.1));
        const v = +R.it.v || 0, len = Math.max(0, L * Math.abs(v) / vmax * s), on = lt > 0 || env.reduced;
        show(R.r, on); show(R.vt, on); if (R.lt) show(R.lt, true);
        if (orient === 'h') {
          const y = b.y + slot * (R.k + .5), x = b.x + labW;
          setA(R.r, { x: f1(x), y: f1(y - th / 2), width: f1(len), height: f1(th) }); if (R.lt) setA(R.lt, { x: f1(x - 10), y: f1(y) });
          setA(R.vt, { x: f1(x + len + 8), y: f1(y) });
        } else {
          const x = b.x + slot * (R.k + .5), y0 = b.y + L + fs * 1.5;
          setA(R.r, { x: f1(x - th / 2), y: f1(y0 - len), width: f1(th), height: f1(len) }); if (R.lt) setA(R.lt, { x: f1(x), y: f1(y0 + 8) });
          setA(R.vt, { x: f1(x), y: f1(y0 - len - 8) });
        }
        const txt = fmtNum(v * cnt, Object.assign({ dec: f.dec ?? (Math.abs(v) < 10 && v % 1 ? 2 : 0) }, f));
        if (R.vt._t !== txt) { R.vt._t = txt; R.vt.textContent = txt }
      }
    },
  };
}
def('signal', (ctx, p, env) => {
  const C = env.C, rnd = env.rng, colr = col(p.color, 'accent'), act = col(p.active, colr);
  const layers = (p.layers || []).map(L => L.map(n => { if (Array.isArray(n)) return { p: [n[0], n[1]], o: null, r: 6 }; const o = env.find(n); if (!o) return null; const b = objBox(o); return { p: mid(b), o, r: Math.max(b.w, b.h) / 2 } }).filter(Boolean)).filter(L => L.length);
  if (layers.length < 2) { console.warn('signal: нужно ≥ 2 слоёв'); return {} }
  const edges = [], idx = new Map();
  layers.forEach((L, l) => L.forEach((nd, i) => { nd.l = l; nd.i = i; if (nd.o) idx.set(nd.o.n, nd) }));
  if (Array.isArray(p.edges)) for (const [a, b] of p.edges) { const A = idx.get((env.find(a) || {}).n), B = idx.get((env.find(b) || {}).n); if (A && B) edges.push([A, B]) }
  else {
    if (p.edges !== 'full') { // рёбра — линии слайда, концы которых у узлов соседних слоёв
      const near = (L, x, y) => { let best = null, bd = Infinity; for (const nd of L) { const d = Math.hypot(nd.p[0] - x, nd.p[1] - y); if (d < bd && d <= nd.r + 5) { bd = d; best = nd } } return best };
      for (const o of ctx.sl.objs) { if (o.k !== 'line') continue; const x1 = o.x, y1 = o.y, x2 = o.x + o.w, y2 = o.y + o.h;
        for (let l = 0; l + 1 < layers.length; l++) { let A = near(layers[l], x1, y1), B = near(layers[l + 1], x2, y2); if (!(A && B)) { A = near(layers[l], x2, y2); B = near(layers[l + 1], x1, y1) } if (A && B) { edges.push([A, B]); break } } }
    }
    if (!edges.length) { const cap = p.max_edges || 140;
      for (let l = 0; l + 1 < layers.length; l++) { const La = layers[l], Lb = layers[l + 1], k = La.length * Lb.length <= cap ? Lb.length : Math.max(1, Math.floor(cap / La.length));
        La.forEach((a, i) => { for (let j = 0; j < k; j++) edges.push([a, Lb[k === Lb.length ? j : Math.floor(i * Lb.length / La.length + j * Lb.length / k) % Lb.length]]) }) } }
  }
  const hop = Math.max(.12, (+p.hop || .55) / C.sp), travel = hop * .85, period = p.repeat ? Math.max(+p.repeat, layers.length * hop + .6) : 0;
  const E2 = edges.map(([a, b]) => ({ a, b, j: rnd() * hop * .4 * C.jit, len: Math.hypot(b.p[0] - a.p[0], b.p[1] - a.p[1]) }));
  const root = el('g', {}, ctx.layer), bands = layers.map(() => el('rect', { fill: act, 'fill-opacity': 0, rx: 14 }, root));
  const lbox = layers.map(L => { let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity; for (const n of L) { x0 = Math.min(x0, n.p[0] - n.r); x1 = Math.max(x1, n.p[0] + n.r); y0 = Math.min(y0, n.p[1] - n.r); y1 = Math.max(y1, n.p[1] + n.r) } return [x0 - 10, y0 - 10, x1 - x0 + 20, y1 - y0 + 20] });
  bands.forEach((b, l) => setA(b, { x: f1(lbox[l][0]), y: f1(lbox[l][1]), width: f1(lbox[l][2]), height: f1(lbox[l][3]) }));
  const pr = 2.6 + 1.4 * C.amp;
  const pulses = E2.map(() => ({ tr: el('line', { stroke: colr, 'stroke-width': pr * .9, 'stroke-linecap': 'round' }, root), c: el('circle', { fill: colr, r: pr }, root) }));
  const arrive = l => l === 0 ? 0 : (l - 1) * hop + travel + hop * .2 * C.jit;
  const cyc = lt => period && lt > period ? lt % period : lt;
  const actv = (l, lt) => { const ta = arrive(l), d = cyc(lt) - ta; return lt < 0 ? 0 : d < -.08 ? 0 : d < 0 ? sstep((d + .08) / .08) : Math.exp(-d / (.32 + .2 / C.sp)) };
  for (const L of layers) for (const nd of L) if (nd.o) env.mod(nd.o.n, (o, st, t) => {
    const lt = env.local(t), a = env.reduced ? 0 : actv(nd.l, lt); if (a < .01) return [o, st];
    const s2 = Object.assign({}, st, { scale: (st.scale ?? 1) * (1 + .3 * C.amp * a), glow: rgba(act, .85 * a), glowR: 4 + 8 * a * C.amp });
    if (o.f) s2.fill = mixc(o.f, act, a); return [o, s2];
  });
  const tOut = arrive(layers.length - 1);
  const out = p.out && p.out.items ? barsView(root, { box: boxOf(env, p.out.box), items: p.out.items, fmt: p.out.fmt, size: p.out.size, color: colr, hl: 0, stagger: .08 }, env) : null;
  if (p.out_text) { const o = env.find(p.out_text); if (o) env.mod(o.n, counterMod(env, o, { to: p.out_value, from0: p.out_from ?? 0, dur: .9, delay: tOut, fmt: p.out_fmt })) }
  return {
    frame(lt) {
      const tc = cyc(lt);
      for (let l = 0; l < layers.length; l++) setA(bands[l], { 'fill-opacity': (env.reduced ? 0 : .07 * actv(l, lt) * (.6 + .4 * C.amp)).toFixed(3) });
      for (let k = 0; k < E2.length; k++) {
        const e = E2[k], P = pulses[k], t0 = e.a.l * hop + e.j, q = (tc - t0) / travel, on = !env.reduced && lt >= 0 && q > 0 && q < 1;
        show(P.c, on); show(P.tr, on); if (!on) continue;
        const qq = DC.ease.inOut(q), x = lerp(e.a.p[0], e.b.p[0], qq), y = lerp(e.a.p[1], e.b.p[1], qq), back = Math.min(qq, 26 * (.6 + .4 * C.amp) / (e.len || 1));
        const xb = lerp(e.a.p[0], e.b.p[0], qq - back), yb = lerp(e.a.p[1], e.b.p[1], qq - back), fade = Math.min(1, q * 6, (1 - q) * 6);
        setA(P.c, { cx: f1(x), cy: f1(y), opacity: fade.toFixed(2) }); setA(P.tr, { x1: f1(xb), y1: f1(yb), x2: f1(x), y2: f1(y), 'stroke-opacity': (.45 * fade).toFixed(2) });
      }
      if (out) out.update(env.reduced ? 1e4 : lt - tOut);
    },
  };
});

/* ================================================================== 6. counter — число в тексте растёт */
function counterMod(env, o, q) {
  const C = env.C, lines = o.t ? o.t.lines : null; if (!lines) return (oo, st) => [oo, st];
  let li = -1, ri = -1, info = null;
  for (let a = 0; a < lines.length && !info; a++) { if (q.line !== undefined && q.line !== null && a !== q.line) continue; for (let b = 0; b < lines[a].length; b++) { const m = parseNum(lines[a][b][0]); if (m) { li = a; ri = b; info = m; break } } }
  if (!info) return (oo, st) => [oo, st];
  const to = q.to ?? info.val, from = q.from0 ?? 0, dur = Math.max(.05, q.dur ?? 1.2) / C.sp, delay = q.delay || 0;
  const f = Object.assign({}, info.f, q.fmt || {}); if (q.decimals !== undefined && q.decimals !== null) f.dec = q.decimals;
  if (!f.grp && Math.abs(to) >= 1e4) f.grp = ' ';
  const ez = E(q.ease || (env.p.character === 'calm' ? 'inOut' : 'out')), drama = env.p.character === 'dramatic', run = lines[li][ri];
  let cacheV = null, cacheT = null;
  return (oo, st, t) => {
    const lt = env.local(t) - delay, p = env.reduced ? 1 : clamp(lt / dur), e = ez(p);
    let v = lerp(from, to, e);
    if (drama && p > 0 && p < .85) { const k = Math.pow(10, -f.dec), j = Math.floor(lt * 30); v += (hash(j * 977 + 13) - .5) * Math.abs(to - from) * .04 * (1 - p); v = Math.round(v / k) * k }
    const s = fmtNum(v, f);
    if (s !== cacheV) { cacheV = s; const nl = lines.slice(); nl[li] = lines[li].slice(); nl[li][ri] = [run[0].slice(0, info.idx) + s + run[0].slice(info.idx + info.len), run[1], run[2], run[3]]; cacheT = Object.assign({}, oo.t, { lines: nl }) }
    const st2 = Object.assign({}, st, { t: cacheT });
    const pop = !env.reduced && p >= 1 ? Math.max(0, 1 - (lt - dur) / .45) : 0;
    if (pop > 0 && env.p.character !== 'calm') { st2.scale = (st.scale ?? 1) * (1 + .07 * C.amp * Math.sin(Math.PI * (1 - pop)) * pop); if (drama) { st2.glow = rgba(oo.t.col || '#8e1f33', .55 * pop); st2.glowR = 10 } }
    return [oo, st2];
  };
}
def('counter', (ctx, p, env) => {
  const o = env.find(p.target); if (!o) { console.warn('counter: нет объекта', p.target); return {} }
  env.mod(o.n, counterMod(env, o, { to: typeof p.to === 'number' ? p.to : undefined, from0: typeof p.from === 'number' ? p.from : 0, dur: p.dur, delay: 0, decimals: p.decimals, ease: p.ease, line: p.line, fmt: p.fmt }));
  return {};
});

/* ================================================================== 7. clock — часы и журнал */
def('clock', (ctx, p, env) => {
  const C = env.C, [cx, cy] = p.at || [800, 450], R = +p.r || 110, mode = p.mode === 12 ? 12 : 24, [h0, h1] = p.hours || [0, 24];
  const dur = Math.max(.3, +p.dur || 4), ez = env.p.character === 'dramatic' ? DC.ease.in : env.p.character === 'calm' ? DC.ease.inOut : (t => t);
  const ink = col(p.ink, 'ink2'), line = col(p.line, 'line'), hand = col(p.color, 'accent'), face = col(p.face, 'surface');
  const root = el('g', {}, ctx.layer), fsz = Math.max(11, R * .13);
  el('circle', { cx, cy, r: R, fill: face, stroke: line, 'stroke-width': 3 }, root);
  el('circle', { cx, cy, r: R - R * .24, fill: 'none', stroke: line, 'stroke-width': 1 }, root);
  const ang = h => (h / mode) * TAU - Math.PI / 2;
  const wedge = el('path', { fill: hand, 'fill-opacity': .1 * C.amp }, root);
  for (let i = 0; i < mode * 2; i++) { const major = i % (mode === 24 ? 12 : 6) === 0, half = i % 2 === 0, a = ang(i / 2), r1 = R - (major ? R * .16 : half ? R * .09 : R * .05);
    el('line', { x1: f1(cx + Math.cos(a) * r1), y1: f1(cy + Math.sin(a) * r1), x2: f1(cx + Math.cos(a) * (R - 2)), y2: f1(cy + Math.sin(a) * (R - 2)), stroke: major ? ink : line, 'stroke-width': major ? 2.4 : 1.2 }, root);
    if (major) { const tx = el('text', { x: f1(cx + Math.cos(a) * (R - R * .32)), y: f1(cy + Math.sin(a) * (R - R * .32)), 'text-anchor': 'middle', 'dominant-baseline': 'central', 'font-family': font('mono'), 'font-size': f1(fsz), fill: ink }, root); tx.textContent = mode === 24 ? String(i / 2).padStart(2, '0') : String(i / 2 || 12) } }
  const entries = (p.entries || []).map((e, k) => ({ e, h: e.h ?? (h0 + (h1 - h0) * (e.at ?? 0) / dur), k }));
  const marks = entries.map(en => { const a = ang(en.h); return { a, dot: el('circle', { cx: f1(cx + Math.cos(a) * R), cy: f1(cy + Math.sin(a) * R), r: Math.max(5, R * .065), fill: face, stroke: hand, 'stroke-width': 2 }, root), ring: el('circle', { cx: f1(cx + Math.cos(a) * R), cy: f1(cy + Math.sin(a) * R), r: 6, fill: 'none', stroke: hand, 'stroke-width': 1.6 }, root) } });
  const hd = el('line', { x1: cx, y1: cy, stroke: hand, 'stroke-width': Math.max(2.5, R * .028), 'stroke-linecap': 'round' }, root);
  el('circle', { cx, cy, r: Math.max(4, R * .055), fill: hand }, root);
  const dig = el('text', { x: cx, y: f1(cy + R * .42), 'text-anchor': 'middle', 'dominant-baseline': 'central', 'font-family': font('head'), 'font-size': f1(R * .2), 'font-weight': 700, fill: col('ink') }, root);
  const lg = p.log || {}, lx = lg.at ? lg.at[0] : cx + R + 30, ly = lg.at ? lg.at[1] : cy - R * .7, dy = lg.dy || 34, lsz = lg.size || 17;
  const rows = entries.map((en, k) => { const g = el('g', { opacity: 0 }, root); el('circle', { cx: lx + 6, cy: ly + k * dy, r: 5, fill: col(en.e.c, hand) }, g);
    const tt = el('text', { x: lx + 20, y: ly + k * dy, 'dominant-baseline': 'central', 'font-family': font('mono'), 'font-size': lsz * .82, fill: col('muted') }, g); const hh = Math.floor(en.h), mm = Math.round((en.h - hh) * 60); tt.textContent = String(hh % 24).padStart(2, '0') + ':' + String(mm).padStart(2, '0');
    const tx = el('text', { x: lx + 20 + lsz * 3.3, y: ly + k * dy, 'dominant-baseline': 'central', 'font-family': font('body'), 'font-size': lsz, fill: col(en.e.ink, 'ink') }, g); tx.textContent = en.e.t || ''; return g });
  return {
    frame(lt) {
      const k = env.reduced ? 1 : clamp(lt / dur), h = h0 + (h1 - h0) * ez(k), a = ang(h), wob = env.reduced || k >= 1 ? 0 : .012 * C.jit * Math.sin(lt * 31) * (env.p.character === 'lively' ? 1 : .3);
      setA(hd, { x2: f1(cx + Math.cos(a + wob) * R * .74), y2: f1(cy + Math.sin(a + wob) * R * .74) });
      const a0 = ang(h0), large = (a - a0) % TAU > Math.PI ? 1 : 0, rr = R * .74;
      setA(wedge, { d: h - h0 < .02 ? '' : (h - h0 >= mode - .01 ? `M${cx - rr} ${cy}a${rr} ${rr} 0 1 0 ${2 * rr} 0a${rr} ${rr} 0 1 0 ${-2 * rr} 0Z` : `M${cx} ${cy}L${f1(cx + Math.cos(a0) * rr)} ${f1(cy + Math.sin(a0) * rr)}A${rr} ${rr} 0 ${large} 1 ${f1(cx + Math.cos(a) * rr)} ${f1(cy + Math.sin(a) * rr)}Z`) });
      const hh = Math.floor(h + 1e-6), mm = Math.floor((h - hh) * 60), s = h >= mode - 1e-6 && h >= h1 - 1e-6 ? String(mode) + ':00' : String(hh % mode).padStart(2, '0') + ':' + String(mm).padStart(2, '0');
      if (dig._t !== s) { dig._t = s; dig.textContent = s }
      entries.forEach((en, i) => {
        const passed = h >= en.h - 1e-6, m = marks[i];
        let tIn = 0; if (passed && !env.reduced) { const kk = clamp((en.h - h0) / ((h1 - h0) || 1)); let lo = 0, hi = 1; for (let it = 0; it < 20; it++) { const md = (lo + hi) / 2; if (ez(md) < kk) lo = md; else hi = md } tIn = lt - lo * dur } else if (passed) tIn = 9;
        setA(m.dot, { fill: passed ? col(en.e.c, hand) : face });
        const rq = clamp(tIn / .7); show(m.ring, passed && rq < 1); if (passed && rq < 1) setA(m.ring, { r: f1(6 + 18 * C.amp * DC.ease.out(rq)), 'stroke-opacity': (1 - rq).toFixed(2) });
        const pin = passed ? DC.ease.out(clamp(tIn / .4)) : 0;
        setA(rows[i], { opacity: pin.toFixed(2), transform: `translate(${f1(-14 * (1 - pin))} 0)` });
      });
    },
  };
});

/* ================================================================== 8. gauge — дуговая шкала со стрелкой-пружиной */
def('gauge', (ctx, p, env) => {
  const C = env.C, bx = p.box ? boxOf(env, p.box) : null;
  const [cx, cy] = bx ? [bx.x + bx.w / 2, bx.y + bx.h * .54] : (p.at || [800, 450]), R = bx ? Math.min(bx.w, bx.h) * .38 : (+p.r || 120);
  const vmin = +(p.vmin ?? p.min ?? 0), vmax = +(p.vmax ?? p.max ?? 1), val = clamp(+(p.value ?? .5), Math.min(vmin, vmax), Math.max(vmin, vmax));
  const zero = p.zero !== undefined && p.zero !== null ? +p.zero : null, base = zero ?? vmin; // стрелка стартует от нуля шкалы
  const sweep = clamp(+p.sweep || 240, 60, 330) * Math.PI / 180, a0 = Math.PI / 2 + (TAU - sweep) / 2, angOf = v => a0 + sweep * (v - vmin) / ((vmax - vmin) || 1);
  const c = col(p.color, 'accent'), line = col(p.track, 'line'), ink = col('ink'), [zeta, omega] = springOf(p);
  const arc = (r, A, B) => { if (B < A) [A, B] = [B, A]; const large = B - A > Math.PI ? 1 : 0; return `M${f1(cx + Math.cos(A) * r)} ${f1(cy + Math.sin(A) * r)}A${f1(r)} ${f1(r)} 0 ${large} 1 ${f1(cx + Math.cos(B) * r)} ${f1(cy + Math.sin(B) * r)}` };
  const root = el('g', {}, ctx.layer), W = R * .1;
  el('path', { d: arc(R, a0, a0 + sweep), fill: 'none', stroke: line, 'stroke-width': W, 'stroke-linecap': 'round', 'stroke-opacity': .7 }, root);
  let zf = vmin; for (const z of p.zones || []) { const zt = clamp(+z.to, vmin, vmax); el('path', { d: arc(R + W * .95, angOf(zf), angOf(zt)), fill: 'none', stroke: col(z.c || z.color, 'muted'), 'stroke-width': W * .32 }, root); zf = zt }
  const band = Array.isArray(p.band) && p.band.length === 2 ? el('path', { d: arc(R + W * 1.05, angOf(+p.band[0]), angOf(+p.band[1])), fill: 'none', stroke: c, 'stroke-width': W * .55, 'stroke-opacity': 0, 'stroke-linecap': 'butt' }, root) : null;
  const fillArc = el('path', { fill: 'none', stroke: c, 'stroke-width': W, 'stroke-linecap': 'round' }, root);
  for (let i = 0; i <= 50; i++) { const major = i % 10 === 0, a = a0 + sweep * i / 50, r1 = R - W * (major ? 1.6 : 1.05), r2 = R - W * .7; el('line', { x1: f1(cx + Math.cos(a) * r1), y1: f1(cy + Math.sin(a) * r1), x2: f1(cx + Math.cos(a) * r2), y2: f1(cy + Math.sin(a) * r2), stroke: major ? col('ink2') : line, 'stroke-width': major ? 1.8 : 1 }, root) }
  if (zero !== null) { const a = angOf(zero), zt = el('text', { x: f1(cx + Math.cos(a) * (R - W * 2.6)), y: f1(cy + Math.sin(a) * (R - W * 2.6)), 'text-anchor': 'middle', 'dominant-baseline': 'central', 'font-family': font('body'), 'font-size': f1(Math.max(11, R * .11)), 'font-weight': 700, fill: ink }, root);
    el('line', { x1: f1(cx + Math.cos(a) * (R - W * 1.8)), y1: f1(cy + Math.sin(a) * (R - W * 1.8)), x2: f1(cx + Math.cos(a) * (R + W * 1.6)), y2: f1(cy + Math.sin(a) * (R + W * 1.6)), stroke: ink, 'stroke-width': 2.2 }, root); zt.textContent = '0' }
  // формат: словарь {dec, suf, pre, grp} или строка-образец «−0,035», «76 %», «6 497»
  let f = { dec: 0 }; if (typeof p.fmt === 'string') { const m = parseNum(p.fmt); if (m) f = Object.assign(m.f, { pre: p.fmt.slice(0, m.idx).replace(/[+−\-–]$/, ''), suf: p.fmt.slice(m.idx + m.len) }) } else if (p.fmt) f = Object.assign(f, p.fmt);
  if (p.decimals !== undefined && p.decimals !== null) f.dec = p.decimals;
  const scale = p.pct ? 100 : 1, span = Math.abs(vmax - vmin) * scale;
  if (typeof p.fmt !== 'string' && (p.decimals === undefined || p.decimals === null) && !(p.fmt && p.fmt.dec !== undefined)) f.dec = span <= 1 ? 2 : span <= 10 ? 1 : 0;
  [[vmin, a0], [vmax, a0 + sweep]].forEach(([v, a]) => { const t = el('text', { x: f1(cx + Math.cos(a) * (R + W * 2)), y: f1(cy + Math.sin(a) * (R + W * 2)), 'text-anchor': 'middle', 'dominant-baseline': 'central', 'font-family': font('body'), 'font-size': f1(Math.max(11, R * .1)), fill: col('muted') }, root); t.textContent = fmtNum(v * scale, Object.assign({}, f, { pre: '', suf: '' })) });
  const nd = el('path', { d: `M${f1(cx - R * .07)} ${f1(cy + R * .025)}L${f1(cx + R * .8)} ${cy}L${f1(cx - R * .07)} ${f1(cy - R * .025)}L${f1(cx - R * .16)} ${cy}Z`, fill: ink }, root);
  el('circle', { cx, cy, r: f1(R * .075), fill: ink }, root); el('circle', { cx, cy, r: f1(R * .03), fill: col('bg') }, root);
  const rd = el('text', { x: cx, y: f1(cy + R * .44), 'text-anchor': 'middle', 'dominant-baseline': 'central', 'font-family': font('head'), 'font-size': f1(R * (p.zero !== undefined ? .3 : .36)), 'font-weight': 700, fill: c }, root);
  if (p.label) { const t = el('text', { x: cx, y: f1(cy + R * .78), 'text-anchor': 'middle', 'dominant-baseline': 'central', 'font-family': font('body'), 'font-size': f1(Math.max(12, R * .12)), fill: col('ink2') }, root); t.textContent = p.label }
  const settle = 4 / (zeta * omega);
  return {
    frame(lt) {
      const tt = env.reduced ? 1e3 : Math.max(0, lt) * C.sp, s = lt < 0 && !env.reduced ? 0 : spring(tt, zeta, omega), jit = env.reduced || tt < settle ? 0 : (env.p.character === 'dramatic' ? .0035 : 0) * noise(lt * 9, 3);
      const v = base + (val - base) * s, a = clamp(angOf(v) + jit * sweep, a0 - .05, a0 + sweep + .05);
      setA(nd, { transform: `rotate(${(a * 180 / Math.PI).toFixed(2)} ${cx} ${cy})` });
      const ab = angOf(base); setA(fillArc, { d: Math.abs(a - ab) > .002 ? arc(R, clamp(ab, a0, a0 + sweep), clamp(a, a0, a0 + sweep)) : '' });
      if (band) setA(band, { 'stroke-opacity': (.32 * (env.reduced ? 1 : clamp((tt - settle * .4) / .5))).toFixed(3) });
      const dv = p.follow ? v : base + (val - base) * DC.ease.out(clamp(tt / settle)), s2 = lt < 0 && !env.reduced ? '' : fmtNum(dv * scale, f);
      if (rd._t !== s2) { rd._t = s2; rd.textContent = s2 }
    },
  };
});

/* ================================================================== 9. terminal — печать команд и вывода */
def('terminal', (ctx, p, env) => {
  const C = env.C, rnd = env.rng;
  let box = p.box ? boxOf(env, p.box) : null, own = true;
  if (p.obj) { const o = env.find(p.obj); if (o) { box = objBox(o); own = !!p.fill } }
  if (!box) box = { x: 800, y: 200, w: 640, h: 360 };
  const fs = +p.size || 18, lh = fs * (p.lh || 1.5), pad = p.pad ?? fs * .9, chrome = p.chrome ? fs * 1.7 : 0;
  const bg = col(p.bg, 'code_bg'), ink = col(p.ink, 'code_ink'), dark = lum(bg) < .45;
  const fixc = c => { c = col(c, ink); if (dark && lum(c) < .5) return mixc(c, '#ffffff', .45); if (!dark && lum(c) > .7) return mixc(c, '#000000', .45); return c };
  const root = el('g', {}, ctx.layer);
  if (own) { el('rect', { x: box.x, y: box.y, width: box.w, height: box.h, rx: 10, fill: bg }, root); if (chrome) ['#e5534b', '#d9a400', '#3fa45b'].forEach((c, i) => el('circle', { cx: box.x + pad + i * fs * .9, cy: box.y + chrome * .55, r: fs * .28, fill: c }, root)) }
  const cid = uid('t'), cp = el('clipPath', { id: cid }, root); el('rect', { x: box.x + 2, y: box.y + chrome + 2, width: box.w - 4, height: box.h - chrome - 4 }, cp);
  const body = el('g', { 'clip-path': `url(#${cid})` }, root), scr = el('g', {}, body);
  const cps = (+p.cps || 34) * C.sp, sched = [], prm = col(p.prompt, 'accent2'); let t = 0;
  const cmdRe = /^(\$|>|#|❯|[\w.-]+[@$]\S*\$)\s/;
  for (const ln of p.lines || []) {
    const s = String(ln.t ?? ln), kind = ln.kind || (cmdRe.test(s) ? 'cmd' : 'out'), times = [];
    if (kind === 'cmd') {
      const pm = cmdRe.exec(s), pl = pm ? pm[0].length : 0; t += .18 / C.sp;
      for (let i = 0; i < s.length; i++) { if (i < pl) { times.push(t); continue } t += (1 / cps) * (1 + C.jit * .9 * (rnd() - .5)) + (s[i] === ' ' ? .04 * C.jit : 0); times.push(t) }
      sched.push({ s, kind, t0: times[0] ?? t, times, pl, c: ln.c }); t += (ln.pause ?? .3) / C.sp;
    } else { t += (ln.pause ?? (.05 + .09 * rnd())) / C.sp; sched.push({ s, kind, t0: t, times: null, pl: 0, c: ln.c }) }
  }
  const rowsVis = Math.max(1, Math.floor((box.h - chrome - 2 * pad) / lh)), y0 = box.y + chrome + pad + lh * .5;
  const els = sched.map((L, k) => { const tx = el('text', { x: box.x + pad, y: f1(y0 + k * lh), 'dominant-baseline': 'central', 'font-family': font('mono'), 'font-size': fs, fill: fixc(L.c || (L.kind === 'cmd' ? ink : 'muted')), 'xml:space': 'preserve' }, scr);
    const a = el('tspan', { fill: prm }, tx), b = el('tspan', {}, tx); show(tx, false); return { tx, a, b, shown: -1 } });
  const meas = el('text', { 'font-family': font('mono'), 'font-size': fs, x: -999, y: -999 }, root); meas.textContent = 'M'.repeat(20);
  let cw = fs * .6; try { const w = meas.getComputedTextLength(); if (w > 0) cw = w / 20 } catch (e) { /* без раскладки */ } meas.remove();
  const cur = el('rect', { width: f1(cw * .95), height: f1(fs * 1.12), fill: ink, 'fill-opacity': .85 }, scr);
  const total = t;
  return {
    frame(lt) {
      const tt = env.reduced ? total + 10 : lt; let last = -1, lastLen = 0, typing = false;
      for (let k = 0; k < sched.length; k++) {
        const L = sched[k], E1 = els[k];
        if (tt < L.t0) { show(E1.tx, false); continue }
        let n = L.s.length; if (L.times) { n = 0; while (n < L.times.length && L.times[n] <= tt) n++; typing = typing || n < L.s.length }
        show(E1.tx, true); last = k; lastLen = n;
        if (E1.shown !== n) { E1.shown = n; E1.a.textContent = L.s.slice(0, Math.min(n, L.pl)); E1.b.textContent = L.s.slice(Math.min(n, L.pl), n) || (n ? '' : ' ') }
        const age = tt - L.t0; if (L.kind === 'out' && env.p.character === 'dramatic' && age < .14 && !env.reduced) setA(E1.tx, { x: f1(box.x + pad + (hash(k * 31 + Math.floor(age * 60)) - .5) * 8), opacity: (.4 + .6 * hash(k * 7 + Math.floor(age * 90))).toFixed(2) });
        else setA(E1.tx, { x: f1(box.x + pad), opacity: 1 });
      }
      // прокрутка: каждая строка сверх видимых сдвигает текст на строку с короткой кривой
      let off = 0; for (let k = rowsVis; k < sched.length; k++) off += lh * DC.ease.out(clamp((tt - sched[k].t0 + .02) / .14));
      setA(scr, { transform: `translate(0 ${f1(-off)})` });
      const nxt = sched[last + 1], waiting = nxt && nxt.kind === 'cmd' && tt < nxt.t0;
      const ci = last < 0 ? 0 : (waiting || (sched[last] && sched[last].kind === 'out') ? last + 1 : last), cl = ci === last ? lastLen : (nxt && nxt.kind === 'cmd' ? 0 : 0);
      const blink = typing || ((tt * 1.9) % 1) < .58;
      show(cur, tt >= 0 && blink && ci < sched.length + 1);
      setA(cur, { x: f1(box.x + pad + cl * cw), y: f1(y0 + ci * lh - fs * .56) });
      if (env.p.character === 'dramatic') setA(cur, { 'fill-opacity': (.6 + .4 * Math.abs(Math.sin(tt * 5))).toFixed(2) });
    },
  };
});

/* ================================================================== 10. sparks / confetti / ripple */
def('sparks', (ctx, p, env) => {
  const C = env.C, at = point(env, p.at || p.obj) || [800, 450];
  if (!at) return {};
  const n = Math.round((p.n ?? 36) * C.den), power = (+p.power || 420) * (.75 + .25 * C.amp), life = (+p.life || .9) * (.85 + .15 * C.amp), grav = p.gravity ?? 520, drag = 2.2;
  const colors = (p.colors && p.colors.length ? p.colors : ['accent', 'accent3', 'warn']).map(c => col(c));
  const cone = p.cone ? [p.cone[0] * Math.PI / 180, p.cone[1] * Math.PI / 180] : [-Math.PI / 2, TAU];
  const reach = power / drag * 1.05 + 40, cv = env.canvas(at[0] - reach, at[1] - reach, 2 * reach, 2 * reach + grav * life * life * .5), g = cv.g;
  const rep = +p.repeat || 0, count = p.count ?? (rep ? 99 : 1);
  const burst = k => { const r = U.rng(((p.seed || 1) * 977 + k * 7919) >>> 0); return Array.from({ length: n }, () => { const a = cone[0] + (r() - .5) * cone[1], v = power * (.35 + .65 * Math.sqrt(r())); return { vx: Math.cos(a) * v, vy: Math.sin(a) * v, l: life * (.55 + .45 * r()), c: colors[(r() * colors.length) | 0], w: 1.4 + 1.6 * r() * C.amp } }) };
  const B = [], pos = (s, t) => { const k = (1 - Math.exp(-drag * t)) / drag; return [at[0] + s.vx * k, at[1] + s.vy * k + .5 * grav * t * t] };
  let drawn = false;
  return {
    always: true,
    frame(lt) {
      if (env.reduced) { if (!drawn) { cv.clear(); drawn = true } return }
      cv.clear(); if (lt < 0) return;
      const k0 = rep ? Math.max(0, Math.floor((lt - life * 1.2) / rep)) : 0, k1 = rep ? Math.min(count - 1, Math.floor(lt / rep)) : 0;
      for (let k = k0; k <= k1; k++) {
        const tb = lt - k * rep; if (tb < 0 || tb > life * 1.3) continue; B[k] = B[k] || burst(k);
        if (tb < .3 && C.amp > .7) { const fr = clamp(tb / .3), gr = g.createRadialGradient(at[0], at[1], 0, at[0], at[1], 46 * C.amp); gr.addColorStop(0, rgba(colors[0], .55 * (1 - fr))); gr.addColorStop(1, rgba(colors[0], 0)); g.fillStyle = gr; g.beginPath(); g.arc(at[0], at[1], 46 * C.amp, 0, TAU); g.fill() }
        for (const s of B[k]) { if (tb > s.l) continue; const q = tb / s.l, [x, y] = pos(s, tb), [xb, yb] = pos(s, Math.max(0, tb - .035 - .03 * C.amp));
          g.strokeStyle = rgba(s.c, 1 - q * q); g.lineWidth = s.w * (1 - .6 * q); g.lineCap = 'round'; g.beginPath(); g.moveTo(xb, yb); g.lineTo(x, y); g.stroke() }
      }
      for (const k in B) if (+k < k0) delete B[k];
    },
  };
});
def('confetti', (ctx, p, env) => {
  const C = env.C, rain = !!p.area && !p.at, a = rain ? boxOf(env, p.area) : null, at = rain ? null : (point(env, p.at || p.obj) || [800, 500]);
  const n = Math.round((p.n ?? 70) * C.den), power = (+p.power || 520) * (.8 + .2 * C.amp), life = (+p.life || 3.2), drag = 2.4;
  const colors = (p.colors && p.colors.length ? p.colors : ['accent', 'accent3', 'accent2', 'warn']).map(c => col(c));
  const r = env.rng, P = Array.from({ length: n }, () => {
    const ang = -Math.PI / 2 + (r() - .5) * 1.9, v = power * (.45 + .55 * r());
    return { x0: rain ? a.x + r() * a.w : at[0], y0: rain ? a.y - r() * 60 : at[1], vx: rain ? 0 : Math.cos(ang) * v, vy: rain ? 0 : Math.sin(ang) * v, t0: rain ? r() * 1.4 : r() * .08,
      vt: (60 + 70 * r()) * (.7 + .3 * C.sp), sw: 10 + 22 * r() * C.amp, sf: 1.5 + 2.5 * r(), ph: r() * TAU, rot: r() * TAU, wr: (r() - .5) * 9 * C.sp, wf: 4 + 8 * r() * C.sp, w: 5 + 5 * r(), h: 3 + 6 * r(), c: colors[(r() * colors.length) | 0] };
  });
  const bx = rain ? { x: a.x - 40, y: a.y - 80, w: a.w + 80, h: a.h + 100 } : { x: at[0] - power * .7, y: at[1] - power / drag - 40, w: power * 1.4, h: power / drag + 40 + 380 };
  const cv = env.canvas(bx.x, bx.y, bx.w, bx.h), g = cv.g, ylim = bx.y + bx.h;
  return {
    always: true,
    frame(lt) {
      cv.clear(); if (lt < 0 && !env.reduced) return; const tt0 = env.reduced ? 1.2 : lt;
      for (const q of P) {
        const t = tt0 - q.t0; if (t < 0) continue; const k = (1 - Math.exp(-drag * t)) / drag;
        const x = q.x0 + q.vx * k + q.sw * Math.sin(t * q.sf + q.ph) * clamp(t / .6), y = q.y0 + q.vy * k + q.vt * (t - k);
        const al = clamp((life - t) / .6) * clamp((ylim - y) / 30); if (al <= 0) continue;
        const flip = Math.cos(t * q.wf + q.ph), rot = q.rot + q.wr * t;
        g.save(); g.translate(x, y); g.rotate(rot); g.scale(1, Math.max(.08, Math.abs(flip))); g.globalAlpha = al; g.fillStyle = flip > 0 ? q.c : mixc(q.c, '#000000', .25); g.fillRect(-q.w / 2, -q.h / 2, q.w, q.h); g.restore();
      }
    },
  };
});
def('ripple', (ctx, p, env) => {
  const C = env.C; let at = p.at ? [p.at[0], p.at[1]] : null, rmax = +p.r_max || 72, sqz = p.squash ?? 1, glass = null;
  if (!at && p.obj) { const id = normId(p.obj); if (env.find(id + '_lq0')) { glass = id; sqz = p.squash ?? .2 } else at = point(env, p.obj) }
  if (!at && !glass) return {};
  const n = Math.max(1, p.rings || 3), per = (+p.period || 1.6) / C.sp, count = p.count ?? 0, c = col(p.color, 'accent'), w = +p.width || 2.2;
  const root = el('g', {}, ctx.layer), E3 = pool(root, n + 1, () => el('ellipse', { fill: 'none', stroke: c }, root));
  return {
    frame(lt) {
      let cx, cy, R = rmax; if (glass) { const s = liveGet(glass, 'surf'); if (s) { cx = s.xc; cy = s.y; R = p.r_max ? rmax : s.hw * .9 } else { const o = env.find(glass + '_srf'); if (!o) return; const b = objBox(o); cx = b.x + b.w / 2; cy = b.y + b.h / 2; R = p.r_max ? rmax : b.w * .45 } } else [cx, cy] = at;
      const gap = per / n, tt = env.reduced ? -1 : lt;
      E3.forEach((e, j) => {
        const kk = Math.floor(tt / gap) - j, age = (tt - kk * gap) / per, on = tt >= 0 && kk >= 0 && age < 1 && (!count || kk < count);
        show(e, on); if (!on) return; const r = R * (.06 + .94 * DC.ease.out(age));
        setA(e, { cx: f1(cx), cy: f1(cy), rx: f1(r), ry: f1(r * sqz), 'stroke-opacity': Math.pow(1 - age, 1.5 * (2 - C.amp * .5)).toFixed(3), 'stroke-width': (w * (1 - .55 * age) * (.8 + .2 * C.amp)).toFixed(2) });
      });
    },
  };
});

/* ================================================================== 11. grain / halftone */
def('grain', (ctx, p, env) => {
  const C = env.C, a = p.area ? boxOf(env, p.area) : { x: 0, y: 0, w: 1600, h: 900 }, film = p.mode === 'film';
  const fps = clamp(+p.fps || (8 + 2 * (C.sp > 1 ? 2 : C.sp < 1 ? 0 : 1)), 6, 12), amount = clamp((p.opacity !== undefined ? +p.opacity / .16 : (+p.amount || .5)) * C.amp, 0, 2), sz = clamp(+p.size || 1, .5, 4);
  const ink = rgb(col(p.color, 'ink')), Tn = 160, K = 5, tiles = [];
  for (let k = 0; k < K; k++) {
    const c = document.createElement('canvas'); c.width = c.height = Tn; const x = c.getContext('2d'), d = x.createImageData(Tn, Tn), r = U.rng(((p.seed || 3) * 131 + k * 7) >>> 0), dens = film ? .3 : .17;
    for (let i = 0; i < d.data.length; i += 4) { const v = r(); if (v < dens) { d.data[i] = ink[0]; d.data[i + 1] = ink[1]; d.data[i + 2] = ink[2]; d.data[i + 3] = 255 * amount * .16 * (.35 + .65 * r()) } else if (v > 1 - dens * .55) { d.data[i] = d.data[i + 1] = d.data[i + 2] = 255; d.data[i + 3] = 255 * amount * .2 * (.4 + .6 * r()) } }
    x.putImageData(d, 0, 0); tiles.push(c);
  }
  let paper = null;
  if (!film) { const c = document.createElement('canvas'); c.width = c.height = 256; const x = c.getContext('2d'), d = x.createImageData(256, 256); for (let j = 0; j < 256; j++) for (let i = 0; i < 256; i++) { const v = (noise(i / 23, 5 + Math.floor(j / 23)) * .5 + noise(i / 7.3 + j / 11, 9) * .5); const o = (j * 256 + i) * 4; d.data[o] = ink[0]; d.data[o + 1] = ink[1]; d.data[o + 2] = ink[2]; d.data[o + 3] = Math.max(0, v) * 255 * .05 * amount } x.putImageData(d, 0, 0); paper = c }
  const cv = env.canvas(a.x, a.y, a.w, a.h), g = cv.g, pats = tiles.map(c => g.createPattern(c, 'repeat')), ppat = paper ? g.createPattern(paper, 'repeat') : null;
  let lastK = null;
  return {
    always: true,
    frame(lt) {
      const k = env.reduced ? 0 : Math.floor(Math.max(0, lt) * fps); if (k === lastK) return; lastK = k;
      cv.clear(); g.save(); g.beginPath(); g.rect(a.x, a.y, a.w, a.h); g.clip();
      const h1 = hash(k * 2654 + 1), pat = pats[Math.floor(h1 * K) % K], ox = hash(k * 31 + 7) * Tn, oy = hash(k * 17 + 3) * Tn;
      if (ppat) { if (ppat.setTransform) ppat.setTransform(new DOMMatrix().translate(a.x, a.y)); g.fillStyle = ppat; g.fillRect(a.x, a.y, a.w, a.h) }
      if (pat.setTransform) pat.setTransform(new DOMMatrix().translate(a.x + ox, a.y + oy).scale(sz)); g.fillStyle = pat; g.fillRect(a.x, a.y, a.w, a.h);
      if (film) {
        const fl = noise(k * .7, 13) * .03 * amount; g.fillStyle = fl > 0 ? `rgba(255,255,255,${fl})` : `rgba(${ink},${-fl})`; g.fillRect(a.x, a.y, a.w, a.h);
        const nd = Math.round(2 + 5 * C.den); g.fillStyle = `rgba(${ink},${.35 * amount})`;
        for (let i = 0; i < nd; i++) { const x = a.x + hash(k * 101 + i * 7) * a.w, y = a.y + hash(k * 103 + i * 11) * a.h, r = .6 + 1.8 * hash(k * 107 + i); g.beginPath(); g.ellipse(x, y, r * 1.6, r, hash(i + k) * 3, 0, TAU); g.fill() }
        if (hash(k * 7 + 5) < .35 * C.den) { const x = a.x + hash(k * 13 + 1) * a.w; g.strokeStyle = `rgba(${ink},${.18 * amount})`; g.lineWidth = .7; g.beginPath(); g.moveTo(x, a.y); g.bezierCurveTo(x + 3, a.y + a.h * .3, x - 3, a.y + a.h * .6, x + 1, a.y + a.h); g.stroke() }
        const vg = g.createRadialGradient(a.x + a.w / 2, a.y + a.h / 2, Math.min(a.w, a.h) * .35, a.x + a.w / 2, a.y + a.h / 2, Math.hypot(a.w, a.h) * .6); vg.addColorStop(0, `rgba(${ink},0)`); vg.addColorStop(1, `rgba(${ink},${.16 * amount})`); g.fillStyle = vg; g.fillRect(a.x, a.y, a.w, a.h);
      }
      g.restore();
    },
  };
});
def('halftone', (ctx, p, env) => {
  const C = env.C; let a = p.area ? boxOf(env, p.area) : null, clip = null;
  if (p.obj) { const o = env.find(p.obj); if (o) { const rs = worldRings(o); a = a || ringsBox(rs); if (o.k === 'path') { clip = new Path2D(); for (const r of rs) { for (let i = 0; i < r.length; i += 2) i ? clip.lineTo(r[i], r[i + 1]) : clip.moveTo(r[i], r[i + 1]); clip.closePath() } } } }
  if (!a) return {};
  const cell = +p.cell || 10, rmax = (p.rmax ?? cell * .5), ang = (p.angle ?? 45) * Math.PI / 180, ca = Math.cos(ang), sa = Math.sin(ang), field = p.field || 'radial';
  const ctr = p.center ? [p.center[0], p.center[1]] : [a.x + a.w * .5, a.y + a.h * .5], c = col(p.color, 'accent'), dur = (+p.dur || 1.2) / C.sp, spd = (+p.speed || 1) * C.sp;
  const dots = [], diag = Math.hypot(a.w, a.h), m = Math.ceil(diag / cell / 2) + 1, cx0 = a.x + a.w / 2, cy0 = a.y + a.h / 2;
  for (let j = -m; j <= m; j++) for (let i = -m; i <= m; i++) { const x = cx0 + (i * ca - j * sa) * cell, y = cy0 + (i * sa + j * ca) * cell; if (x < a.x - cell || x > a.x + a.w + cell || y < a.y - cell || y > a.y + a.h + cell) continue; const d = Math.hypot(x - ctr[0], y - ctr[1]); dots.push(x, y, d, ((x - a.x) * Math.cos(ang) + (y - a.y) * Math.sin(ang))) }
  const R = Math.max(...[[a.x, a.y], [a.x + a.w, a.y], [a.x, a.y + a.h], [a.x + a.w, a.y + a.h]].map(q => Math.hypot(q[0] - ctr[0], q[1] - ctr[1])));
  const cv = env.canvas(a.x - cell, a.y - cell, a.w + 2 * cell, a.h + 2 * cell), g = cv.g; let lastT = -1;
  // штампы: точки сетки неподвижны, радиус квантуется (24 уровня × 4 × 4 сдвига на ¼ пикселя); писать в ImageData
  // быстрее тысяч arc на программной растеризации; точки не перекрываются (r ≤ шаг / 2) — смешивание не нужно
  const W = cv.c.width, H = cv.c.height, sk = W / cv.w, img = g.createImageData(W, H), dd = img.data, Lv = 24, Q = 4, RP = rmax * sk, R0 = Math.ceil(RP + 1), SS = 2 * R0 + 2;
  const masks = [];
  for (let l = 0; l <= Lv; l++) for (let fy = 0; fy < Q; fy++) for (let fx = 0; fx < Q; fx++) { const rr = RP * l / Lv, xs = [], ys = [], cs = [];
    if (l) for (let y = 0; y < SS; y++) for (let x = 0; x < SS; x++) { const cc = clamp(rr + .5 - Math.hypot(x - R0 - fx / Q, y - R0 - fy / Q)); if (cc > 0) { xs.push(x); ys.push(y); cs.push(cc * 255) } }
    masks.push({ xs: Int16Array.from(xs), ys: Int16Array.from(ys), cs: Float32Array.from(cs) }) }
  const nd = dots.length / 4, ix0 = new Int32Array(nd), iy0 = new Int32Array(nd), sub = new Uint8Array(nd);
  for (let k = 0; k < nd; k++) { const px = (dots[4 * k] - cv.x) * sk, py = (dots[4 * k + 1] - cv.y) * sk, ix = Math.floor(px), iy = Math.floor(py); ix0[k] = ix - R0; iy0[k] = iy - R0; sub[k] = (((py - iy) * Q) | 0) * Q + (((px - ix) * Q) | 0) }
  const ax0 = Math.max(0, Math.round((a.x - cv.x) * sk)), ay0 = Math.max(0, Math.round((a.y - cv.y) * sk)), ax1 = Math.min(W, Math.round((a.x + a.w - cv.x) * sk)), ay1 = Math.min(H, Math.round((a.y + a.h - cv.y) * sk));
  const [cr, cg, cb] = rgb(c), span = a.w * Math.abs(Math.cos(ang)) + a.h * Math.abs(Math.sin(ang));
  return {
    always: true,
    frame(lt) {
      const tt = env.reduced ? 1e3 : lt;
      if (env.reduced ? lastT === 1e3 : (lastT >= 0 && Math.abs(tt - lastT) < 1 / 30)) return; // поле движется медленно — 30 к/с
      lastT = tt; if (tt < 0) { cv.clear(); return }
      const ph = env.reduced ? 0 : tt * spd, build = clamp(tt / dur), amp = .12 * C.amp, rr0 = (ph * 90) % (R * 1.2);
      dd.fill(0);
      for (let k = 0; k < nd; k++) {
        const x = dots[4 * k], y = dots[4 * k + 1], d = dots[4 * k + 2], s = dots[4 * k + 3]; let f;
        if (field === 'radial') f = 1 - d / R + amp * Math.sin(ph * 2.4 - d * .045);
        else if (field === 'ring') f = .15 + .85 * Math.exp(-sq((d - rr0) / (R * .16)));
        else if (field === 'wave') f = .5 + .42 * Math.sin(x * .021 + y * .013 - ph * 2.2) * Math.cos(y * .017 - ph * 1.1);
        else f = clamp(s / span) + amp * Math.sin(ph * 2 - s * .03);
        const sweep = field === 'radial' || field === 'ring' ? d / R : s / Math.max(1, a.w), gin = clamp((build * 1.35 - sweep) / .35);
        const lv = Math.round(clamp(f) * DC.ease.out(gin) * Lv); if (lv < 1) continue;
        const m = masks[(lv * Q * Q) + sub[k]], xs = m.xs, ys = m.ys, cs = m.cs, bx = ix0[k], by = iy0[k];
        for (let j = 0, n = cs.length; j < n; j++) { const xx = bx + xs[j], yy = by + ys[j]; if (xx < ax0 || yy < ay0 || xx >= ax1 || yy >= ay1) continue; const o = (yy * W + xx) * 4; if (dd[o + 3] < cs[j]) { dd[o] = cr; dd[o + 1] = cg; dd[o + 2] = cb; dd[o + 3] = cs[j] } }
      }
      g.putImageData(img, 0, 0);
      if (clip) { g.save(); g.globalCompositeOperation = 'destination-in'; g.fillStyle = '#000'; g.fill(clip); g.restore() }
    },
  };
});

/* ================================================================== 12. chart-draw / bars-grow */
def('chart-draw chart_draw', (ctx, p, env) => {
  const C = env.C, b = boxOf(env, p.box || [200, 200, 600, 300]), data = (p.data || []).map((q, i) => Array.isArray(q) ? [+q[0], +q[1]] : [i, +q]);
  if (data.length < 2) return {};
  const xs = data.map(q => q[0]), ys = data.map(q => q[1]), [x0, x1] = p.x_range || [Math.min(...xs), Math.max(...xs)];
  let [y0, y1] = p.y_range || [Math.min(...ys), Math.max(...ys)]; if (!p.y_range) { const pd = (y1 - y0) * .08 || 1; y0 -= pd; y1 += pd }
  const X = x => b.x + (x - x0) / ((x1 - x0) || 1) * b.w, Y = y => b.y + b.h - (y - y0) / ((y1 - y0) || 1) * b.h, P = data.map(q => [X(q[0]), Y(q[1])]);
  const c = col(p.color, 'accent'), lw = +p.width || 3, dur = Math.max(.2, +p.dur || 1.8) / C.sp, drama = p.character === 'dramatic';
  const ez = drama ? (t => t < .5 ? DC.ease.in(t * 2) / 2 : .5 + DC.ease.out(t * 2 - 1) / 2) : E(p.ease || 'inOut');
  const root = el('g', {}, ctx.layer);
  if (p.axis !== false) { el('line', { x1: b.x, y1: b.y + b.h, x2: b.x + b.w, y2: b.y + b.h, stroke: col('line'), 'stroke-width': 1.2 }, root); el('line', { x1: b.x, y1: b.y, x2: b.x, y2: b.y + b.h, stroke: col('line'), 'stroke-width': 1.2 }, root) }
  const area = p.fill ? el('path', { fill: c, 'fill-opacity': +p.fill }, root) : null;
  const path = el('path', { fill: 'none', stroke: c, 'stroke-width': lw, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }, root);
  const comet = drama ? el('path', { fill: 'none', stroke: mixc(c, '#ffffff', .3), 'stroke-width': lw * 1.9, 'stroke-linecap': 'round', 'stroke-opacity': .55 }, root) : null;
  const marks = (p.marks || []).map(m => { const i = clamp(m.i | 0, 0, P.length - 1), g = el('g', { opacity: 0 }, root); el('circle', { cx: f1(P[i][0]), cy: f1(P[i][1]), r: lw * 2.2, fill: col(m.c, c) }, g); const tx = el('text', { x: f1(P[i][0] + (m.dx ?? 0)), y: f1(P[i][1] + (m.dy ?? 22)), 'text-anchor': m.al || 'middle', 'dominant-baseline': 'hanging', 'font-family': font('body'), 'font-size': p.size || 17, 'font-weight': 700, fill: col(m.c, c) }, g); tx.textContent = m.t || ''; return { i, g, ring: el('circle', { cx: f1(P[i][0]), cy: f1(P[i][1]), fill: 'none', stroke: col(m.c, c), 'stroke-width': 1.8 }, root) } });
  const halo = p.dot !== false ? el('circle', { fill: c, 'fill-opacity': .18 }, root) : null, dot = p.dot !== false ? el('circle', { fill: c, r: lw * 1.7, stroke: col('bg'), 'stroke-width': 2 }, root) : null;
  const lab = p.label !== false ? el('text', { 'font-family': font('body'), 'font-size': p.size || 17, 'font-weight': 700, fill: c, 'dominant-baseline': 'central' }, root) : null;
  const f = Object.assign({ dec: p.decimals ?? 3 }, p.fmt || {});
  const partial = s => { const n = Math.floor(s), fr = s - n, pts = P.slice(0, n + 1); if (n < P.length - 1) pts.push([lerp(P[n][0], P[n + 1][0], fr), lerp(P[n][1], P[n + 1][1], fr)]); return pts };
  const dOf = pts => 'M' + pts.map(q => f1(q[0]) + ' ' + f1(q[1])).join('L');
  let lastS = -1;
  return {
    frame(lt) {
      const k = env.reduced ? 1 : clamp(lt / dur), s = ez(k) * (P.length - 1), pts = partial(s), h = pts[pts.length - 1];
      if (s !== lastS) { lastS = s; setA(path, { d: lt <= 0 && !env.reduced ? '' : dOf(pts) }); if (area) setA(area, { d: lt <= 0 && !env.reduced ? '' : dOf(pts) + `L${f1(h[0])} ${f1(b.y + b.h)}L${f1(P[0][0])} ${f1(b.y + b.h)}Z` });
        if (comet) { const tail = partial(Math.max(0, s - (P.length - 1) * .08)).length - 1; setA(comet, { d: k > 0 && k < 1 ? dOf(pts.slice(Math.max(0, tail))) : '' }) } }
      const vis = lt > 0 || env.reduced;
      if (dot) { show(dot, vis); show(halo, vis && !env.reduced); setA(dot, { cx: f1(h[0]), cy: f1(h[1]) }); const pulse = Math.max(0, lt) * 1.6 * C.sp % 1; setA(halo, { cx: f1(h[0]), cy: f1(h[1]), r: f1(lw * (2.5 + 4 * pulse * C.amp)), 'fill-opacity': (.25 * (1 - pulse)).toFixed(2) }) }
      if (lab) { show(lab, vis); const n = Math.floor(s), fr = s - n, v = n < data.length - 1 ? lerp(data[n][1], data[n + 1][1], fr) : data[data.length - 1][1], txt = fmtNum(v, f);
        if (lab._t !== txt) { lab._t = txt; lab.textContent = txt } const right = h[0] > b.x + b.w * .82; setA(lab, { x: f1(h[0] + (right ? -12 : 12)), y: f1(clamp(h[1] - 20, b.y + 8, b.y + b.h - 8)), 'text-anchor': right ? 'end' : 'start' }) }
      for (const m of marks) { const on = s >= m.i - 1e-6, tIn = on ? (env.reduced ? 9 : (k >= 1 ? lt - dur : 0) + .5 * (s - m.i) / Math.max(1, P.length) * dur) : 0, q = clamp(tIn / .45);
        setA(m.g, { opacity: on ? DC.ease.out(clamp(tIn / .3 + .2)).toFixed(2) : 0 }); show(m.ring, on && q < 1 && !env.reduced); if (on && q < 1) setA(m.ring, { r: f1(lw * (2 + 7 * DC.ease.out(q) * C.amp)), 'stroke-opacity': (1 - q).toFixed(2) }) }
    },
  };
});
def('bars-grow bars_grow', (ctx, p, env) => {
  const C = env.C, [zeta, omega] = springOf(p);
  if (p.objs && p.objs.length) { // режим объектов слайда: прямоугольники растут от основания, тексты считают
    const orient = p.orient || 'h';
    const grow = (k, t) => { const lt = env.local(t) - k * (p.stagger ?? .16) / C.sp; return env.reduced ? 1 : lt < 0 ? -1 : Math.max(0, spring(lt * C.sp, zeta, omega)) };
    const bars = p.objs.map(n => env.find(n));
    bars.forEach((o, k) => { if (!o) return; env.mod(o.n, (oo, st, t) => { const s = grow(k, t); if (s < 0) return null;
      return [orient === 'h' ? Object.assign({}, oo, { w: oo.w * s }) : Object.assign({}, oo, { y: oo.y + oo.h * (1 - s), h: oo.h * s }), st] }) });
    (p.texts || []).forEach((n, k) => { const o = env.find(n); if (!o) return; const cm = counterMod(env, o, { delay: k * (p.stagger ?? .16) / C.sp, dur: 1.1, decimals: p.decimals }), b = bars[k];
      env.mod(o.n, (oo, st, t) => { const s = grow(k, t); if (s < 0) return null; const r = cm(oo, st, t), st2 = r[1];
        if (b) { if (orient === 'h') st2.tx = (st2.tx || 0) - b.w * (1 - s); else st2.ty = (st2.ty || 0) + b.h * (1 - s) } st2.alpha = (st2.alpha ?? 1) * clamp(s * 4); return [r[0], st2] }) });
    return {};
  }
  const view = barsView(ctx.layer, { box: boxOf(env, p.box || [200, 200, 600, 300]), items: p.values || [], vmax: p.vmax, orient: p.orient || 'h', fmt: p.fmt, size: p.size, color: p.color, hl: p.hl, stagger: p.stagger, labW: p.label_w }, env);
  return { frame(lt) { view.update(env.reduced ? 1e4 : lt) } };
});
})();
