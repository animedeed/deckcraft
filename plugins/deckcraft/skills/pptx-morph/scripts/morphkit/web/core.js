/* deckcraft web runtime — ядро (0.3.0).
 * Контракт модулей — CONTRACT.md (EN) и CONTRACT.ru.md рядом. Ядро не зависит от модулей: без них работают Morph, эффекты PowerPoint,
 * петли flow/pulse/ripple/spin/blink, шаги, ссылки, лист «fade» и простая навигация.
 * Координаты: сцена 1600×900 px, 1 дюйм = 120 px; в состояниях эффектов (st.dx, st.dy, st.clip) — дюймы, как в
 * morphkit.motion, чтобы Python-превью и браузер считали одинаково. */
'use strict';
(function () {
const DC = window.DC = window.DC || {};
const D = DC.data = JSON.parse(document.getElementById('dc-data').textContent);
const NS = 'http://www.w3.org/2000/svg';
Object.assign(DC, {
  NS, PX: 120, W: 1600, H: 900, REDUCED: matchMedia('(prefers-reduced-motion: reduce)').matches,
  fx: DC.fx || {}, textFx: DC.textFx || {}, loops: DC.loops || {}, scenes: DC.scenes || {}, sheets: DC.sheets || {}, draw: DC.draw || {},
  textMorph: DC.textMorph || null, keys: DC.keys || {}, hooks: DC.hooks || {}, state: {}, stateT: {}, statePrev: {},
});
DC.on = (ev, fn) => (DC.hooks[ev] || (DC.hooks[ev] = [])).push(fn);
DC.emit = (ev, ...a) => (DC.hooks[ev] || []).forEach(f => { try { f(...a) } catch (e) { console.error(e) } });

/* ---------- утилиты ---------- */
const U = DC.u = {
  lerp: (a, b, t) => a + (b - a) * t,
  clamp: (v, a = 0, b = 1) => Math.max(a, Math.min(b, v)),
  hx: c => [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)],
  el(tag, a, p) { const e = document.createElementNS(NS, tag); for (const k in a) if (a[k] !== undefined && a[k] !== null) e.setAttribute(k, a[k]); p && p.appendChild(e); return e },
  rng(seed) { let s = seed >>> 0 || 1; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296) },
  color: name => (D.colors && D.colors[name]) || name,
};
U.lc = (a, b, t) => { if (!a || !b || a[0] !== '#' || b[0] !== '#') return t < .5 ? (a || b) : (b || a); const p = U.hx(a), q = U.hx(b); return '#' + p.map((v, i) => Math.round(U.lerp(v, q[i], t)).toString(16).padStart(2, '0')).join('') };
DC.ease = Object.assign({
  linear: t => t,
  inOut: t => t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2,
  out: t => 1 - Math.pow(1 - t, 3),
  in: t => t * t * t,
  back: t => { const c = 1.70158, c3 = c + 1; return 1 + c3 * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2) },
  elastic: t => t === 0 || t === 1 ? t : Math.pow(2, -10 * t) * Math.sin((t * 10 - .75) * 2 * Math.PI / 3) + 1,
  spring: t => 1 - Math.exp(-6.5 * t) * Math.cos(t * 9.5),
  bounce: t => { const n = 7.5625, d = 2.75; if (t < 1 / d) return n * t * t; if (t < 2 / d) return n * (t -= 1.5 / d) * t + .75; if (t < 2.5 / d) return n * (t -= 2.25 / d) * t + .9375; return n * (t -= 2.625 / d) * t + .984375 },
}, DC.ease || {});
const ease = DC.ease.inOut;

/* ---------- данные: пул контуров, разделы ---------- */
D.slides.forEach((s, i) => { s.i = i; s.byName = {}; s.objs.forEach(o => { if (o.rp !== undefined) o.rings = D.pool[o.rp]; s.byName[o.n] = o }) });
D.sections = D.sections || [];

/* ---------- поверхность: список {key, o, st} → SVG ---------- */
let gid = 0;
const uid = p => p + (++gid);
const CIRCLE = []; for (let i = 0; i < 48; i++) { const a = i / 48 * 2 * Math.PI; CIRCLE.push(.5 + .5 * Math.cos(a), .5 + .5 * Math.sin(a)) }
DC.CIRCLE = CIRCLE;

function pathD(o) { const out = []; for (const r of o.rings || []) { for (let i = 0; i < r.length; i += 2) out.push((i ? 'L' : 'M') + (o.x + r[i] * o.w).toFixed(1) + ' ' + (o.y + r[i + 1] * o.h).toFixed(1)); out.push('Z') } return out.join('') }
DC.pathD = pathD;

class Surface {
  constructor(svg) { this.svg = svg; this.root = svg.querySelector('.dc-root'); this.defs = svg.querySelector('defs'); this.live = new Map(); this.order = '' }
  grad(node, o) {
    const g = o.grad; let gd = node.gd;
    if (!gd) { gd = U.el(g.kind === 'radial' ? 'radialGradient' : 'linearGradient', { id: uid('g'), gradientUnits: 'userSpaceOnUse' }, this.defs); node.gd = gd }
    gd.setAttribute('gradientTransform', `matrix(${o.w} 0 0 ${o.h} ${o.x} ${o.y})`);
    if (g.kind === 'radial') { gd.setAttribute('cx', g.cx ?? .5); gd.setAttribute('cy', g.cy ?? .5); gd.setAttribute('r', g.r ?? .5) }
    else { const a = g.a * Math.PI / 180, ux = Math.cos(a), uy = Math.sin(a), s = Math.abs(ux) + Math.abs(uy);
      gd.setAttribute('x1', .5 - .5 * ux * s); gd.setAttribute('y1', .5 - .5 * uy * s); gd.setAttribute('x2', .5 + .5 * ux * s); gd.setAttribute('y2', .5 + .5 * uy * s) }
    const sig = JSON.stringify(g.stops) + o.fa;
    if (gd.sig !== sig) { gd.innerHTML = ''; for (const [p, c, al] of g.stops) U.el('stop', { offset: p, 'stop-color': c, 'stop-opacity': al * o.fa }, gd); gd.sig = sig }
    return `url(#${gd.id})`;
  }
  text(node, o, st) {
    const t = o.t, k = 120 / 72;
    const chars = st.chars === undefined ? -1 : Math.floor(st.chars);
    const sig = JSON.stringify(t.lines) + '|' + (st.col || t.col) + '|' + chars + '|' + t.al + t.va;
    const anchor = (oo) => { const tt = oo.t, ins = tt.inset * 120, lh = tt.sz * tt.lh * tt.sp * k, total = lh * tt.lines.length + Math.max(0, tt.lines.length - 1) * tt.pg * k;
      return [tt.al === 'c' ? oo.x + oo.w / 2 : tt.al === 'r' ? oo.x + oo.w - ins : oo.x + ins,
        tt.va === 'm' ? oo.y + (oo.h - total) / 2 : tt.va === 'b' ? oo.y + oo.h - ins - total : oo.y + ins] };
    if (node.tsig !== sig) {
      node.tg.innerHTML = ''; node.tsig = sig; node.tref = { x: o.x, y: o.y, w: o.w, h: o.h, t };
      const size = t.sz * k, lh = t.sz * t.lh * t.sp * k, pg = t.pg * k;
      const [ax, ay] = anchor(o); let y = ay;
      const ta = t.al === 'c' ? 'middle' : t.al === 'r' ? 'end' : 'start';
      const tx = U.el('text', { 'xml:space': 'preserve', style: 'white-space:pre', 'text-anchor': ta, 'font-family': t.font, 'font-size': size.toFixed(2), fill: st.col || t.col, 'letter-spacing': t.tr ? t.tr * k : 0, 'font-weight': t.b ? 700 : 400 }, node.tg);
      let left = chars;
      for (const runs of t.lines) {
        const base = y + (lh - size * 1.15) / 2 + size * .93; let first = true;
        for (const [s, c, b, m] of runs) {
          if (left === 0) break;
          let txt = s; if (left > 0) { txt = s.slice(0, left); left -= txt.length }
          if (!txt) continue;
          const sp = U.el('tspan', {}, tx);
          if (first) { sp.setAttribute('x', ax.toFixed(1)); sp.setAttribute('y', base.toFixed(1)); first = false }
          if (c) sp.setAttribute('fill', c); if (b !== null && b !== undefined) sp.setAttribute('font-weight', b ? 700 : 400); if (m) sp.setAttribute('font-family', t.mono);
          sp.textContent = txt;
        }
        if (first) { const sp = U.el('tspan', { x: ax.toFixed(1), y: base.toFixed(1) }, tx); sp.textContent = ' ' }
        y += lh + pg;
      }
    }
    const ref = node.tref, s = t.sz / ref.t.sz, [ax, ay] = anchor(o), [rx, ry] = anchor({ x: ref.x, y: ref.y, w: ref.w, h: ref.h, t: ref.t });
    node.tg.setAttribute('transform', `translate(${ax.toFixed(1)} ${ay.toFixed(1)}) scale(${s.toFixed(4)}) translate(${-rx.toFixed(1)} ${-ry.toFixed(1)})`);
  }
  draw(items) {
    const seen = new Set();
    items.sort((a, b) => (a.o.z + (a.st.dz || 0)) - (b.o.z + (b.st.dz || 0)));
    const order = [];
    for (const it of items) {
      let o = it.o; const st = it.st, key = it.key || o.n; if (seen.has(key)) continue; seen.add(key); order.push(key);
      if (st.t) o = Object.assign({}, o, { t: st.t }); // эффект/сцена подменяет текст (счётчики, печать)
      let node = this.live.get(key);
      if (!node) { node = { wrap: U.el('g', {}), g: null }; node.g = U.el('g', {}, node.wrap); this.live.set(key, node) }
      node.wrap.dcObj = o; // узел → объект (подсветка ссылок, подписи для диктора)
      // взаимодействие
      if (o.link && !node.linked) { node.wrap.classList.add('dc-link'); node.wrap.addEventListener('click', e => { e.stopPropagation(); DC.follow(o.link, o) }); node.linked = true }
      if (o.tip && !node.tipped) { node.wrap.classList.add('dc-tip'); node.wrap.addEventListener('pointerenter', e => DC.emit('tip', o, e, true)); node.wrap.addEventListener('pointerleave', e => DC.emit('tip', o, e, false)); node.tipped = true }
      const sc = st.scale ?? 1, sx = (st.sx ?? 1) * sc, sy = (st.sy ?? 1) * sc, cx = o.x + o.w / 2, cy = o.y + o.h / 2;
      const ox = (st.dx || 0) * 120 + (st.tx || 0), oy = (st.dy || 0) * 120 + (st.ty || 0);
      const tf = `translate(${(ox + cx).toFixed(2)} ${(oy + cy).toFixed(2)}) rotate(${(o.r + (st.drot || 0)).toFixed(2)})${st.skewX ? ` skewX(${st.skewX})` : ''} scale(${sx.toFixed(4)} ${sy.toFixed(4)}) translate(${-cx.toFixed(2)} ${-cy.toFixed(2)})`;
      if (node.tf !== tf) { node.g.setAttribute('transform', tf); node.tf = tf } // атрибуты — только при изменении
      const op = U.clamp(st.alpha ?? 1).toFixed(3); if (node.op !== op) { node.wrap.setAttribute('opacity', op); node.op = op }
      const f = [];
      if (st.blur) f.push(`blur(${st.blur.toFixed(2)}px)`); if (st.bright !== undefined) f.push(`brightness(${st.bright})`);
      if (st.sat !== undefined) f.push(`saturate(${st.sat})`); if (st.hue) f.push(`hue-rotate(${st.hue}deg)`);
      if (st.glow) f.push(`drop-shadow(0 0 ${st.glowR || 8}px ${st.glow})`); if (st.shadow) f.push(`drop-shadow(${st.shadow})`);
      const fl = f.join(' '); if (node.fl !== fl) { node.wrap.style.filter = fl; node.fl = fl }
      if (st.clip) {
        let cp = node.clip; if (!cp) { cp = U.el('clipPath', { id: uid('c'), clipPathUnits: 'userSpaceOnUse' }, this.defs); node.cr = U.el('rect', {}, cp); node.clip = cp }
        const [x0, y0, x1, y1] = st.clip.map(v => v * 120);
        node.cr.setAttribute('x', Math.min(x0, x1)); node.cr.setAttribute('y', Math.min(y0, y1)); node.cr.setAttribute('width', Math.abs(x1 - x0)); node.cr.setAttribute('height', Math.abs(y1 - y0));
        node.wrap.setAttribute('clip-path', `url(#${node.clip.id})`);
      } else node.wrap.removeAttribute('clip-path');
      const drawSpec = o.draw && DC.draw[o.draw.kind];
      const sig = (drawSpec ? 'draw:' + o.draw.kind : o.k) + (o.t ? '|t' : '');
      if (node.sig !== sig) {
        node.g.innerHTML = ''; node.sig = sig; node.shape = null; node.tg = null; node.tsig = null; node.dstate = null;
        if (drawSpec) node.dg = U.el('g', {}, node.g);
        else if (o.k === 'path') node.shape = U.el('path', { 'fill-rule': 'evenodd' }, node.g);
        else if (o.k === 'line') node.shape = U.el('line', { 'stroke-linecap': 'round' }, node.g);
        else if (o.k === 'img' && o.img) node.shape = U.el('image', { href: D.imgs[o.img], preserveAspectRatio: 'none' }, node.g);
        if (o.t && !drawSpec) node.tg = U.el('g', {}, node.g); // у элементов рисования текст рисует модуль
        if (o.tip && !DC.ui) { const ti = U.el('title', {}, node.g); ti.textContent = Array.isArray(o.tip) ? o.tip.join('\n') : o.tip } // запасная системная подсказка
      }
      const s = node.shape;
      if (drawSpec) DC.draw[o.draw.kind](node, o, st, this);
      else if (o.k === 'path' && s) {
        s.setAttribute('d', pathD(o));
        s.setAttribute('fill', st.fill || (o.f ? (o.grad ? this.grad(node, o) : o.f) : 'none')); s.setAttribute('fill-opacity', o.grad ? 1 : o.fa);
        if ((o.s && o.sw > 0) || st.outline) { s.setAttribute('stroke', st.outline || o.s); s.setAttribute('stroke-width', o.sw || 2); s.setAttribute('stroke-opacity', o.la); s.setAttribute('stroke-linejoin', 'round') } else s.removeAttribute('stroke');
        if (st.drawP !== undefined && st.drawP < 1) { s.setAttribute('pathLength', 1); s.setAttribute('stroke-dasharray', `${st.drawP.toFixed(4)} 1`); if (!o.s) { s.setAttribute('stroke', o.f || '#000'); s.setAttribute('stroke-width', 2.5) } s.setAttribute('fill-opacity', (o.grad ? 1 : o.fa) * Math.pow(st.drawP, 3)) }
        else { s.removeAttribute('pathLength'); s.removeAttribute('stroke-dasharray') }
      } else if (o.k === 'line' && s) {
        s.setAttribute('x1', o.x); s.setAttribute('y1', o.y); s.setAttribute('x2', o.x + o.w); s.setAttribute('y2', o.y + o.h);
        s.setAttribute('stroke', st.fill || o.s || 'none'); s.setAttribute('stroke-width', Math.max(o.sw, 1)); s.setAttribute('stroke-opacity', o.la);
        if (o.dash) s.setAttribute('stroke-dasharray', o.dash === 'dot' ? '1 6' : '10 7');
        if (st.drawP !== undefined && st.drawP < 1) { s.setAttribute('pathLength', 1); s.setAttribute('stroke-dasharray', `${st.drawP.toFixed(4)} 1`) } else if (!o.dash) s.removeAttribute('stroke-dasharray');
        if (o.head) s.setAttribute('marker-end', `url(#${DC.marker(o.s || '#000')})`);
      } else if (o.k === 'img' && s) { s.setAttribute('x', o.x); s.setAttribute('y', o.y); s.setAttribute('width', o.w); s.setAttribute('height', o.h) }
      if (o.t && node.tg && !drawSpec) { const tr = st.textFx && DC.textFx[st.textFx.k]; if (tr) tr(node, o, st, this); else { if (node.tfx) { node.tg.innerHTML = ''; node.tsig = null; node.tfx = false } this.text(node, o, st) } }
    }
    const ord = order.join('\u0001');
    if (ord !== this.order) { for (const k of order) this.root.appendChild(this.live.get(k).wrap); this.order = ord }
    for (const [k, n] of this.live) if (!seen.has(k)) { n.wrap.remove(); n.clip && n.clip.remove(); n.gd && n.gd.remove(); this.live.delete(k) }
  }
  clear() { this.draw([]) }
}
DC.Surface = Surface;
const markers = {};
DC.marker = c => { if (markers[c]) return markers[c]; const id = uid('mk'); const m = U.el('marker', { id, viewBox: '0 0 10 10', refX: 8, refY: 5, markerWidth: 5, markerHeight: 5, orient: 'auto-start-reverse' }, document.querySelector('#dc-svg defs')); U.el('path', { d: 'M0 0L10 5L0 10z', fill: c }, m); return (markers[c] = id) };

/* ---------- Morph: пары и выравнивание контуров разной длины ---------- */
function resample(r, n) {
  const pts = []; for (let i = 0; i < r.length; i += 2) pts.push([r[i], r[i + 1]]);
  pts.push(pts[0]); const seg = []; let L = 0; for (let i = 1; i < pts.length; i++) { const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); seg.push(d); L += d }
  const out = []; let k = 0, acc = 0;
  for (let j = 0; j < n; j++) { const target = L * j / n; while (k < seg.length - 1 && acc + seg[k] < target) { acc += seg[k]; k++ }
    const f = seg[k] ? (target - acc) / seg[k] : 0; out.push(U.lerp(pts[k][0], pts[k + 1][0], f), U.lerp(pts[k][1], pts[k + 1][1], f)) }
  return out;
}
function align(a, b, ax, bx) { // a, b — нормированные кольца одной длины; сдвиг b, при котором точки ближе всего (в координатах сцены)
  const n = a.length / 2, step = Math.max(1, Math.floor(n / 64)); let best = 0, bd = Infinity;
  for (let s = 0; s < n; s += step) { let d = 0; for (let i = 0; i < n; i += step) { const j = ((i + s) % n) * 2; d += Math.abs(ax.x + a[2 * i] * ax.w - (bx.x + b[j] * bx.w)) + Math.abs(ax.y + a[2 * i + 1] * ax.h - (bx.y + b[j + 1] * bx.h)) } if (d < bd) { bd = d; best = s } }
  if (!best) return b; return b.slice(best * 2).concat(b.slice(0, best * 2));
}
const pairCache = new Map();
const pairLive = new WeakMap(); // контуры, изменённые сценами (уровень вина): кэш по самим массивам
function pairRings(a, b) {
  const pooled = a.rings === D.pool[a.rp] && b.rings === D.pool[b.rp];
  const key = a.n + '|' + a.rp + '|' + b.rp + '|' + a.rings.length + '|' + b.rings.length;
  let m = null;
  if (pooled) { if (pairCache.has(key)) return pairCache.get(key) }
  else { m = pairLive.get(a.rings); if (!m) pairLive.set(a.rings, m = new WeakMap()); if (m.has(b.rings)) return m.get(b.rings) }
  let res = null;
  if (a.rings.length === b.rings.length) {
    res = a.rings.map((ra, i) => { const rb = b.rings[i]; if (ra.length === rb.length) return [ra, rb];
      const n = Math.max(ra.length, rb.length) / 2 | 0, A = resample(ra, n), B = resample(rb, n); return [A, align(A, B, a, b)] });
  }
  if (pooled) pairCache.set(key, res); else m.set(b.rings, res);
  return res;
}
function interp(a, b, t) {
  const o = Object.assign({}, b); for (const k of ['x', 'y', 'w', 'h', 'fa', 'la', 'sw']) o[k] = U.lerp(a[k], b[k], t);
  o.r = a.r + ((((b.r - a.r) + 180) % 360 + 360) % 360 - 180) * t; o.f = U.lc(a.f, b.f, t); o.s = U.lc(a.s, b.s, t);
  if (!a.f && b.f) o.fa = b.fa * t; if (a.f && !b.f) { o.f = a.f; o.fa = a.fa * (1 - t) }
  const keepA = () => Object.assign({}, a, { x: o.x, y: o.y, w: o.w, h: o.h, r: o.r });
  const textDiff = a.t && b.t && JSON.stringify(a.t.lines) !== JSON.stringify(b.t.lines);
  if (a.t && b.t && !textDiff) o.t = Object.assign({}, b.t, { sz: U.lerp(a.t.sz, b.t.sz, t), col: U.lc(a.t.col, b.t.col, t) });
  if (textDiff && a.k === 'text' && b.k === 'text') // текст: перелив модуля или «старый уходит, затем приходит новый»
    return DC.textMorph ? DC.textMorph(a, b, t, o) : [[keepA(), U.clamp(1 - 2 * t)], [o, U.clamp(2 * t - 1)]];
  let shape;
  if (a.k === 'path' && b.k === 'path' && !a.draw && !b.draw) {
    const pr = pairRings(a, b);
    if (pr) { o.rings = pr.map(([ra, rb]) => ra.map((v, j) => U.lerp(v, rb[j], t))); if (a.grad && b.grad && t < .5) o.grad = a.grad; shape = [[o, 1]] }
    else shape = [[keepA(), 1 - t], [o, t]];
  } else if (a.k !== b.k || (a.draw || b.draw) && !(a.draw && b.draw && a.draw.kind === b.draw.kind)) shape = [[keepA(), 1 - t], [o, t]];
  else { if (a.draw && b.draw) o.draw = DC.draw._interp ? DC.draw._interp(a.draw, b.draw, t) : b.draw; shape = [[o, 1]] }
  if (!textDiff) return shape;
  // фигура с подписью: контур переливается без текста, подпись — отдельно, как текстовый объект
  const bare = shape.map(([x, al]) => [Object.assign({}, x, { t: null }), al]);
  const only = x => Object.assign({}, x, { k: 'text', f: null, s: null, rings: null, rp: undefined, grad: null, draw: null, link: null, tip: null });
  const ta = only(a), tb = only(b), to = only(o);
  return bare.concat(DC.textMorph ? DC.textMorph(ta, tb, t, to) : [[Object.assign({}, ta, { x: o.x, y: o.y, w: o.w, h: o.h, r: o.r }), U.clamp(1 - 2 * t)], [to, U.clamp(2 * t - 1)]]);
}
DC.interp = interp;

/* ---------- эффекты ---------- */
function legacy(key, o, e, p, opt) { // пресеты PowerPoint — как morphkit.motion._fx_state
  if (key.includes('wipe')) {
    const d = (opt && opt.direction) || 'down'; let pts = [];
    if (o.k === 'path' && o.rings) { const rad = o.r * Math.PI / 180, c = Math.cos(rad), s = Math.sin(rad), cx = o.x + o.w / 2, cy = o.y + o.h / 2;
      for (const r of o.rings) for (let i = 0; i < r.length; i += 2) { const px = o.x + r[i] * o.w - cx, py = o.y + r[i + 1] * o.h - cy; pts.push([cx + px * c - py * s, cy + px * s + py * c]) } }
    if (!pts.length) pts = [[o.x, o.y], [o.x + o.w, o.y + o.h]];
    const xs = pts.map(q => q[0] / 120), ys = pts.map(q => q[1] / 120);
    let x0 = Math.min(...xs) - .05, x1 = Math.max(...xs) + .05, y0 = Math.min(...ys) - .05, y1 = Math.max(...ys) + .05;
    if (d === 'left') x1 = x0 + (x1 - x0) * e; else if (d === 'right') x0 = x1 - (x1 - x0) * e; else if (d === 'up') y0 = y1 - (y1 - y0) * e; else y1 = y0 + (y1 - y0) * e;
    return { clip: [x0, y0, x1, y1] };
  }
  if (key.includes('fly')) { const d = (opt && opt.direction) || 'down', X = o.x / 120, Y = o.y / 120; const off = { left: [-(X + o.w / 120), 0], right: [13.333 - X, 0], up: [0, -(Y + o.h / 120)], down: [0, 7.5 - Y] }[d] || [0, 7.5 - Y]; return { dx: off[0] * (1 - e), dy: off[1] * (1 - e) } }
  if (key.includes('rise') || key.includes('ascend')) return { dy: .35 * (1 - e), alpha: e };
  if (key.includes('descend')) return { dy: -.35 * (1 - e), alpha: e };
  if (key.includes('spinner') || key.includes('pinwheel')) return { drot: -90 * (1 - e), scale: .2 + .8 * e, alpha: e };
  if (key.includes('zoom') || key.includes('grow') || key.includes('expand')) return { scale: .3 + .7 * e, alpha: e };
  if (key.includes('float')) return { dy: .5 * (1 - e), alpha: e };
  if (key.includes('swivel') || key.includes('flip')) return { sx: Math.max(.02, e), alpha: e };
  if (key.includes('bounce')) return { dy: -1.2 * (1 - DC.ease.bounce(p)), alpha: Math.min(1, p * 3) };
  if (key.includes('appear')) return {};
  return { alpha: e };
}
function emphasis(key, o, e, p, opt) {
  if (key.includes('spin')) return { drot: (opt.amount || 360) * e };
  if (key.includes('grow_shrink')) return { scale: 1 + ((opt.size || 150) / 100 - 1) * Math.sin(Math.PI * p) };
  if (key.includes('teeter')) return { drot: 6 * Math.sin(p * Math.PI * 4) * (1 - p) };
  if (key.includes('transparency')) return { alpha: 1 - .5 * Math.sin(Math.PI * p) };
  if (key.includes('pulse') || key.includes('flash')) return { scale: 1 + .08 * Math.sin(Math.PI * p) };
  if (key.includes('wave')) return { dy: -.08 * Math.sin(Math.PI * p) };
  return {};
}
function merge(a, b) {
  if (!b) return a;
  for (const k in b) {
    if (k === 'alpha' || k === 'scale' || k === 'sx' || k === 'sy') a[k] = (a[k] ?? 1) * b[k];
    else if (k === 'dx' || k === 'dy' || k === 'drot' || k === 'tx' || k === 'ty') a[k] = (a[k] || 0) + b[k];
    else a[k] = b[k];
  }
  return a;
}
DC.mergeState = merge;
function fxState(o, list, t, sl) { // null — объект ещё/уже не виден
  if (!list) return {};
  const st = {};
  for (const [key, start0, dur, opt, step, cat] of list) {
    let start = start0;
    if (step !== null && step !== undefined) { const s0 = sl.stepT[step]; if (s0 === undefined) { if (cat === 'entrance') return null; continue } start += s0 }
    let p = (t - start) / Math.max(dur, 1e-6); // без движения: входы видны сразу (кроме шагов-кликов), выделения — в финале
    if (DC.REDUCED && cat !== 'exit' && (cat === 'entrance' || p > 0)) p = Math.max(p, 1);
    const pc = U.clamp(p), e = (DC.ease[opt.ease] || ease)(pc);
    const h = DC.fx[key]; if (opt._dur === undefined) opt._dur = dur;
    if (cat === 'entrance') { if (p <= 0) return null; if (p < 1) merge(st, h ? h(o, e, pc, opt, sl) : legacy(key, o, e, pc, opt)); else if (h && h.hold) merge(st, h(o, 1, 1, opt, sl)) }
    else if (cat === 'exit') { if (p >= 1) return null; if (p > 0) merge(st, h ? h(o, e, pc, opt, sl) : legacy(key, o, 1 - e, 1 - pc, opt)) }
    else if (cat === 'emphasis') { if ((p > 0 && p < 1) || (opt.repeat && p > 0)) merge(st, h ? h(o, e, opt.repeat ? p % 1 : pc, opt, sl) : emphasis(key, o, e, pc, opt)); else if (p >= 1 && h && h.hold) merge(st, h(o, 1, 1, opt, sl)) }
    else if (cat === 'path' && opt.path && p > 0) { const P = opt.path, n = P.length - 1, q = Math.min(pc * n, n - 1e-6), i = Math.floor(q), f = q - i, a = P[i], b = P[i + 1] || a; merge(st, { dx: U.lerp(a[0], b[0], e === pc ? f : f) - P[0][0], dy: U.lerp(a[1], b[1], f) - P[0][1] }) }
  }
  return st;
}
DC.fxState = fxState;

/* ---------- петли ---------- */
function loopItems(sl, t) {
  const out = [], by = sl.byName;
  sl.loops.forEach((lp, li) => {
    const tt = t - D.fxStart - lp.start; if (tt < 0) return;
    const h = DC.loops[lp.k]; if (h) { const r = h(lp, by, tt, sl, li); r && out.push(...r); return }
    if (lp.k === 'flow' && lp.pts) {
      const pts = lp.rev ? lp.pts.slice().reverse() : lp.pts, seg = pts.slice(1).map((q, i) => Math.hypot(q[0] - pts[i][0], q[1] - pts[i][1])), L = seg.reduce((a, b) => a + b, 0) || 1;
      for (let i = 0; i < lp.n; i++) { let dd = ((tt / lp.period + i / lp.n) % 1) * L, k = 0; while (k < seg.length - 1 && dd > seg[k]) { dd -= seg[k]; k++ }
        const a = pts[k], b = pts[k + 1], f = dd / (seg[k] || 1), x = U.lerp(a[0], b[0], f), y = U.lerp(a[1], b[1], f), r = lp.size / 2;
        out.push({ key: `lp${li}_${i}`, o: { n: '', k: 'path', x: x - r, y: y - r, w: 2 * r, h: 2 * r, r: 0, z: lp.z, f: lp.color, fa: 1, rings: [CIRCLE] }, st: {} }) }
    } else if (by[lp.target]) {
      const tg = by[lp.target], ph = (tt % lp.period) / lp.period;
      if (lp.k === 'ripple') out.push({ key: `lp${li}`, o: Object.assign({}, tg, { k: 'path', rings: [CIRCLE], f: null, s: lp.color, sw: 2.6, la: 1 - ph, t: null, draw: null, link: null, z: tg.z + .5 }), st: { scale: 1 + (lp.scale - 1) * ph } });
      else if (lp.k === 'pulse') out.push({ replace: lp.target, st: { scale: 1 + (lp.scale - 1) * Math.sin(Math.PI * ph) } });
      else if (lp.k === 'spin') out.push({ replace: lp.target, st: { drot: (lp.rev ? -360 : 360) * ph } });
      else if (lp.k === 'blink') out.push({ replace: lp.target, st: { alpha: .25 + .75 * Math.abs(Math.cos(Math.PI * ph)) } });
    }
  });
  return out;
}

/* ---------- сцены ---------- */
let mounted = [];
function sceneCtx(sl, sc) {
  const layerName = sc.layer || 'over', host = document.querySelector(layerName === 'under' ? '#dc-under' : '#dc-over');
  const g = U.el('g', { class: 'dc-scene' }, host);
  const ctx = { sl, surface: main, layer: g, D, T: D.colors, reduced: DC.REDUCED, u: U, mods: {},
    obj: n => { const o = sl.byName[n]; return o && o.alt ? applyAlt(o, performance.now()) : o }, mod(name, fn) { this.mods[name] = fn },
    canvas() { const fo = U.el('foreignObject', { x: 0, y: 0, width: 1600, height: 900 }, g); const c = document.createElement('canvas'); const dpr = Math.min(2, devicePixelRatio || 1); c.width = 1600 * dpr; c.height = 900 * dpr; c.style.width = '1600px'; c.style.height = '900px'; fo.appendChild(c); const x = c.getContext('2d'); x.setTransform(dpr, 0, 0, dpr, 0, 0); return x } };
  return ctx;
}
function mountScenes(sl) {
  unmountScenes();
  for (const sc of sl.scenes || []) { const S = DC.scenes[sc.k]; if (!S) { console.warn('нет сцены', sc.k); continue }
    const ctx = sceneCtx(sl, sc); try { const inst = S.mount(ctx, sc); mounted.push({ sc, ctx, inst }) } catch (e) { console.error(e) } }
}
function unmountScenes() { for (const m of mounted) { try { m.inst && m.inst.unmount && m.inst.unmount() } catch (e) { console.error(e) } m.ctx.layer.remove() } mounted = [] }

/* ---------- слайд в момент t → элементы ---------- */
function vis(o, now) { // объекты с условием состояния: {"when": "ab", "is": "A"}
  if (!o.when) return 1;
  const k = o.when.key, is = String(o.when.is), S = v => String(v ?? o.when.dflt ?? '');
  const on = S(DC.state[k]) === is, was = S(DC.statePrev[k]) === is, t0 = DC.stateT[k];
  if (t0 === undefined) return on ? 1 : 0; const p = U.clamp((now - t0) / 350); // гаснет только бывший, зажигается только новый
  return on ? (was ? 1 : p) : (was ? 1 - p : 0);
}
function applyAlt(o, now) { // состояния объекта: по клику объект переезжает/перекрашивается/меняет форму
  const A = o.alt, key = A.key, v = String(DC.state[key] ?? A.dflt), pv = String(DC.statePrev[key] ?? A.dflt), t0 = DC.stateT[key];
  const get = val => A.values[val] || {};
  const p = t0 === undefined ? 1 : (DC.ease[A.ease] || DC.ease.spring)(U.clamp((now - t0) / (A.dur || 650)));
  const a = Object.assign({}, o, get(pv)), b = Object.assign({}, o, get(v));
  if (a.rp !== undefined) a.rings = D.pool[a.rp]; if (b.rp !== undefined) b.rings = D.pool[b.rp];
  if (p >= 1) return b;
  return interp(a, b, p)[0][0];
}
function slideItems(sl, t, now, opts = {}) {
  const items = [], tt = opts.static ? 1e6 : t;
  const lps = opts.static || DC.REDUCED ? [] : loopItems(sl, tt), repl = {};
  lps.filter(l => l.replace).forEach(l => repl[l.replace] = merge(repl[l.replace] || {}, l.st));
  const mods = opts.static ? {} : sceneMods(), last = {};
  for (const o0 of sl.objs) {
    last[o0.n] = null;
    let o = o0.alt ? applyAlt(o0, now) : o0, st = fxState(o, sl.fx[o.n], tt - D.fxStart, sl); if (st === null) continue;
    st = merge(Object.assign({}, st), repl[o.n]);
    const v = vis(o, now); if (v <= 0) continue; if (v < 1) st.alpha = (st.alpha ?? 1) * v;
    if (mods[o.n]) { const r = runMods(mods[o.n], o, st, tt); if (!r) continue; [o, st] = r }
    last[o0.n] = o; items.push({ o, st });
  }
  if (!opts.static) sl.last = last; // последний кадр: с него начнётся Morph ухода (уровень вина, состояние alt, скрытое)
  lps.filter(l => !l.replace).forEach(l => items.push(l));
  return items;
}
function sceneMods() { // модификаторы всех сцен слайда: цепочка на имя, одинаковые функции — один раз
  const out = {};
  for (const m of mounted) for (const n in m.ctx.mods) { const f = m.ctx.mods[n], L = out[n] || (out[n] = []); if (f && !L.includes(f)) L.push(f) }
  return out;
}
function runMods(L, o, st, t) { for (const f of L) { const r = f(o, st, t); if (!r) return null; [o, st] = r } return [o, st] }
DC.slideItems = slideItems;

/* ---------- переход и шкала ---------- */
const svg = document.getElementById('dc-svg'), main = new Surface(svg);
DC.main = main;
let cur = -1, prevI = null, t0 = 0, raf = 0, trans = null;
const backStack = [];
function lagOf(o, sl) { // каскад: Morph одних объектов начинается позже других
  if (o.lag) return o.lag;
  const c = sl.cascade; if (!c) return 0;
  const cx = (o.x + o.w / 2) / 1600, cy = (o.y + o.h / 2) / 900;
  const f = c.by === 'y' ? cy : c.by === 'radial' ? Math.hypot(cx - .5, cy - .5) / .71 : c.by === '-x' ? 1 - cx : cx;
  return (c.amount ?? .35) * f;
}
function frame(now) {
  const sl = D.slides[cur]; let t = Math.max(0, (now - t0) / 1000);
  document.getElementById('dc-bg').setAttribute('fill', sl.bg || D.colors.bg);
  if (trans && t < trans.total) {
    renderTransition(sl, t, now);
    for (const m of mounted) { try { m.inst.frame && m.inst.frame(t - trans.total, m.ctx) } catch (e) { console.error(e) } } // стартовый кадр сцен
    raf = requestAnimationFrame(frame); return }
  if (trans) { endTransition() }
  const tt = t - (trans0 || 0);
  for (const a of sl.autoState || []) if (!a.done && tt >= a.at) { a.done = true; for (const k in a.set) DC.setState(k, a.set[k]) }
  main.draw(slideItems(sl, tt, now));
  for (const m of mounted) { try { m.inst.frame && m.inst.frame(tt, m.ctx) } catch (e) { console.error(e) } }
  DC.emit('frame', tt, sl);
  raf = requestAnimationFrame(frame);
}
let trans0 = 0;
function renderTransition(sl, t, now) {
  const A = D.slides[trans.from];
  if (trans.kind === 'morph') {
    const items = [], byA = A.byName, plan = sl.fx, lastA = A.last || {}, mods = sceneMods(), tn = t - trans.total;
    for (const a0 of A.objs) {
      const gone = lastA[a0.n] === null, a = lastA[a0.n] || (a0.alt ? applyAlt(a0, now) : a0); // кадр, на котором ушли
      let b = sl.byName[a0.n];
      if (b && a0.n.startsWith('!!')) {
        if (b.alt) b = applyAlt(b, now);
        if (mods[b.n]) { const r = runMods(mods[b.n], b, {}, tn); if (r) b = r[0] } // цель — стартовый кадр сцены
        const lag = Math.min(lagOf(b, sl), trans.base * .8), q = (DC.ease[b.ease] || ease)(U.clamp((t - lag) / trans.base));
        const hid = plan[a0.n] && plan[a0.n].some(f => f[5] === 'entrance');
        const v = vis(b, now), k0 = gone ? q : 1; // скрытый на уходе — проявляется по ходу
        interp(a, b, q).forEach(([o, al, st0], j) => items.push({ key: a0.n + (j ? '#' + j : ''), o,
          st: Object.assign({}, st0, { alpha: (st0 && st0.alpha !== undefined ? st0.alpha : 1) * al * k0 * (hid ? 1 - q : 1) * (v < 1 ? U.lerp(1, v, q) : 1) }) }));
      } else if (!gone) items.push({ key: a0.n + '#prev', o: a, st: { alpha: 1 - ease(U.clamp(t / (a.t ? trans.base * .5 : trans.dur))) } });
    }
    const pin = ease(U.clamp(t / trans.dur));
    const pinT = ease(U.clamp((t - trans.base * .5) / (trans.base * .5)));
    for (const b of sl.objs) { if (byA[b.n] && b.n.startsWith('!!')) continue; if (plan[b.n] && plan[b.n].some(f => f[5] === 'entrance')) continue; if (vis(b, now) <= 0) continue; items.push({ o: b, st: { alpha: b.t ? pinT : pin } }) }
    main.draw(items);
  } else {
    const p = (DC.ease[trans.ease] || ease)(U.clamp(t / trans.dur));
    main.draw(slideItems(sl, Math.min(-1e-3, t - trans.total), now).filter(it => it.st !== null));
    const S = DC.sheets[trans.kind] || DC.sheets.fade;
    S(p, trans.A, svg, { dur: trans.dur, opt: trans.opt || {}, stage: document.getElementById('dc-stage'), from: trans.from, to: cur, u: U, raw: U.clamp(t / trans.dur) });
  }
}
DC.sheets.fade = DC.sheets.fade || ((p, A, B) => { A.style.opacity = 1 - p; B.style.opacity = 1 });
function snapshot() { // копия текущего кадра с собственными id (живые defs меняются дальше)
  const A = svg.cloneNode(true); A.removeAttribute('id'); A.classList.add('dc-snap');
  const cs = svg.querySelectorAll('canvas'), cd = A.querySelectorAll('canvas');
  cs.forEach((c, i) => { const fo = cd[i] && cd[i].closest('foreignObject'); if (!fo) return;
    try { const im = U.el('image', { x: fo.getAttribute('x'), y: fo.getAttribute('y'), width: fo.getAttribute('width'), height: fo.getAttribute('height'), href: c.toDataURL() }); fo.replaceWith(im) } catch (e) { fo.remove() } });
  const map = {}; A.querySelectorAll('[id]').forEach(e => { const n = e.id + '_s' + gid; map[e.id] = n; e.id = n });
  A.querySelectorAll('*').forEach(e => { for (const at of ['fill', 'stroke', 'clip-path', 'marker-start', 'marker-mid', 'marker-end', 'mask', 'filter', 'href']) { const v = e.getAttribute(at); if (v && v.includes('#')) { const m = v.match(/#([^)'"\s]+)/); if (m && map[m[1]]) e.setAttribute(at, v.replace('#' + m[1], '#' + map[m[1]])) } } });
  gid++; return A;
}
DC.snapshot = snapshot;
function pairedCount(A, B) { let n = 0; for (const o of A.objs) if (o.n.startsWith('!!') && B.byName[o.n]) n++; return n }
function startTransition(from, to, jump) {
  const sl = D.slides[to];
  if (from === null || DC.REDUCED || (sl.tr === 'none' && !jump)) { trans = null; trans0 = 0; return }
  let sheet = sl.sheet || (sl.tr !== 'morph' ? 'fade' : null);
  if (jump) sheet = pairedCount(D.slides[from], sl) >= 5 && sl.tr === 'morph' ? null : (sl.jumpSheet || D.jumpSheet || 'fade');
  if (sheet) {
    const A = snapshot();
    document.getElementById('dc-stage').appendChild(A);
    const k = typeof sheet === 'string' ? sheet : sheet.k, dur = ((typeof sheet === 'object' && sheet.dur) || sl.dur || 800) / 1000;
    trans = { kind: k, A, from, dur, base: dur, opt: typeof sheet === 'object' ? sheet : {}, ease: typeof sheet === 'object' ? sheet.ease : null, total: dur };
  } else {
    const base = sl.dur / 1000; let maxLag = 0;
    for (const o of sl.objs) if (o.n.startsWith('!!')) maxLag = Math.max(maxLag, Math.min(lagOf(o, sl), base * .8));
    trans = { kind: 'morph', from, base, dur: base + maxLag, total: base + maxLag };
  }
  trans0 = trans.total; DC.emit('trans', trans.kind, true, trans);
}
function endTransition() {
  if (!trans) return; const k = trans.kind;
  if (trans.A) { trans.A.remove(); svg.style.cssText = '' }
  trans = null; DC.emit('trans', k, false);
}
function go(i, opts = {}) {
  i = U.clamp(i, 0, D.slides.length - 1); if (i === cur && !opts.force) return;
  const from = cur < 0 ? null : cur, adjacent = from !== null && Math.abs(i - from) === 1;
  if (trans) endTransition();
  if (opts.push && from !== null) backStack.push(from);
  prevI = from; cur = i; t0 = performance.now();
  const sl = D.slides[i]; sl.stepT = [];
  for (const a of sl.autoState || []) { a.done = false; for (const k in a.reset || {}) { DC.state[k] = a.reset[k]; delete DC.stateT[k] } }
  if (opts.steps === 'all') (sl.steps || []).forEach((_, k) => sl.stepT[k] = -10);
  startTransition(opts.instant ? null : from, i, !adjacent);
  mountScenes(sl);
  cancelAnimationFrame(raf); raf = requestAnimationFrame(frame);
  try { history.replaceState(null, '', '#s' + (i + 1)) } catch (e) { }
  DC.cur = cur; DC.emit('slide', i, from, opts);
}
function next() {
  const sl = D.slides[cur], steps = sl.steps || [];
  if (sl.stepT.length < steps.length) { const t = (performance.now() - t0) / 1000 - (trans0 || 0) - D.fxStart; sl.stepT.push(t); DC.emit('step', cur, sl.stepT.length); return }
  go(cur + 1);
}
function prev() {
  const sl = D.slides[cur];
  if (sl.stepT && sl.stepT.length) { sl.stepT.pop(); DC.emit('step', cur, sl.stepT.length); return }
  go(cur - 1, { steps: 'all' });
}
DC.follow = (link, o) => {
  DC.emit('link', link, o);
  if (link.slide !== undefined) go(link.slide, { push: true });
  else if (link.section !== undefined) { const s = D.sections[link.section]; s && go(s.start, { push: true }) }
  else if (link.back) DC.back();
  else if (link.href) window.open(link.href, '_blank', 'noopener');
  else if (link.set) { for (const k in link.set) DC.setState(k, link.set[k]) }
  else if (link.toggle) { const k = link.toggle, vals = link.values || [true, false]; const i = vals.indexOf(DC.state[k] ?? vals[0]); DC.setState(k, vals[(i + 1) % vals.length]) }
  else if (link.step) next();
};
DC.setState = (k, v) => { const now = performance.now(); if (DC.state[k] === v) return;
  // переключение во время анимации: начинаем от текущего значения по умолчанию (без скачка назад)
  DC.statePrev[k] = DC.state[k]; DC.state[k] = v; DC.stateT[k] = now; DC.emit('state', DC.state) };
DC.back = () => { if (backStack.length) go(backStack.pop()); };
Object.assign(DC, { go, next, prev, backStack, cur: -1 });
Object.defineProperty(DC, 't0', { get: () => t0, configurable: true }); // геттер, а не копия значения

/* ---------- статичный кадр слайда (обзор, печать, миниатюры) ---------- */
DC.renderStatic = (i, target) => {
  const s = target || svg.cloneNode(false);
  if (!target) { s.removeAttribute('id'); s.innerHTML = '<defs></defs><rect width="1600" height="900"/><g class="dc-root"></g>' }
  s.querySelector('rect').setAttribute('fill', D.slides[i].bg || D.colors.bg);
  const sf = new Surface(s); const sl = D.slides[i], keep = sl.stepT; sl.stepT = (sl.steps || []).map(() => -10);
  sf.draw(slideItems(sl, 1e6, performance.now(), { static: true })); sl.stepT = keep; return s;
};

/* ---------- клавиши, клик, свайп, масштаб ---------- */
Object.assign(DC.keys, {
  ArrowRight: next, PageDown: next, ' ': next, Enter: next, ArrowLeft: prev, PageUp: prev,
  Home: () => go(0), End: () => go(D.slides.length - 1), Backspace: () => DC.back(),
}, Object.assign({}, DC.keys));
addEventListener('keydown', e => { // сочетания с модификаторами и кнопки в фокусе — браузеру и интерфейсу
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if (e.target.closest && e.target.closest('input,textarea,select,[contenteditable]')) return;
  if ((e.key === 'Enter' || e.key === ' ') && e.target.closest && e.target.closest('button,[role=button],a[href]')) return; // нажатие кнопки, а не листание
  const f = DC.keys[e.key]; if (f) { e.preventDefault(); f(e) } });
document.getElementById('dc-stage').addEventListener('click', e => { if (DC.clickAdvance !== false) next() });
let tx0 = null; addEventListener('touchstart', e => tx0 = e.touches[0].clientX, { passive: true });
addEventListener('touchend', e => { if (tx0 === null) return; const dx = e.changedTouches[0].clientX - tx0; if (Math.abs(dx) > 40) (dx < 0 ? next : prev)(); tx0 = null });
function fit() { const s = Math.min(innerWidth / 1600, innerHeight / 900); document.getElementById('dc-stage').style.setProperty('--s', s); DC.scale = s }
addEventListener('resize', fit); fit();
DC.start = () => { DC.emit('ready'); const m = location.hash.match(/s(\d+)/); go(m ? +m[1] - 1 : 0) };
})();
