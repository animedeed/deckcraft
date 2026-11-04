"""Энергетика: опоры ЛЭП в перспективе, провода-цепные линии с током (поток точек строго по проводу), три фазы
(синусоиды со сдвигом → векторы), подстанции-узлы сети, трансформатор, разрез кабеля, профиль нагрузки.

Тема по умолчанию для прогона — grid («Диспетчерская»). Числа на слайдах — только условные подписи без величин.
"""

from __future__ import annotations

import math

from shapely.geometry import LineString

from morphkit import Cam, Fx, Loop, O
from morphkit import vector as V
from morphkit.theme import SLIDE_H, SLIDE_W, mix

from lab import Variant
from lab._d_util import (DEC, S, raw, ribbon, arc_pts, biggest, body, catenary, dark, flow, head, kicker, label, light, line, stroke,
                         vs, wave)

FAM = "energy"
W, H = SLIDE_W, SLIDE_H


def _v(key, title, idea, slides, tags, score) -> Variant:
    return Variant(FAM, key, title, idea, slides, tags=tags, score=score)


def phase_cols(theme):
    return [theme.c("accent"), theme.c("accent2"), theme.c("accent3")]


# ============================================================================= опора ЛЭП

def pylon(x: float, yb: float, h: float):
    """Решётчатая опора одной формой (объединение штрихов). -> (геометрия, [3 точки подвеса фаз], вершина)."""
    lw = max(0.012 * h, 0.012)
    wb, wt = 0.36 * h, 0.09 * h
    yt = yb - 0.86 * h
    L0, L1 = (x - wb / 2, yb), (x - wt / 2, yt)
    R0, R1 = (x + wb / 2, yb), (x + wt / 2, yt)
    parts = [stroke([L0, L1], lw * 1.4), stroke([R0, R1], lw * 1.4), stroke([L1, (x, yb - h), R1], lw)]
    # перекрёстные связи
    lv = 6
    for k in range(lv):
        t0, t1 = k / lv, (k + 1) / lv
        a = (L0[0] + (L1[0] - L0[0]) * t0, yb + (yt - yb) * t0)
        b = (R0[0] + (R1[0] - R0[0]) * t1, yb + (yt - yb) * t1)
        c = (R0[0] + (R1[0] - R0[0]) * t0, yb + (yt - yb) * t0)
        d = (L0[0] + (L1[0] - L0[0]) * t1, yb + (yt - yb) * t1)
        parts += [stroke([a, b], lw * 0.7), stroke([c, d], lw * 0.7)]
    ya, yb2 = yb - 0.66 * h, yb - 0.82 * h
    arm_lo, arm_hi = 0.34 * h, 0.24 * h
    parts += [stroke([(x - arm_lo, ya), (x + arm_lo, ya)], lw * 1.2), stroke([(x - arm_hi, yb2), (x + arm_hi, yb2)], lw * 1.2),
              stroke([(x - arm_lo, ya), (x - wt, ya - 0.08 * h)], lw * 0.7), stroke([(x + arm_lo, ya), (x + wt, ya - 0.08 * h)], lw * 0.7)]
    ins = 0.07 * h
    att = [(x - arm_lo + 0.02 * h, ya + ins), (x + arm_lo - 0.02 * h, ya + ins), (x + arm_hi - 0.02 * h, yb2 + ins)]
    for (ax, ay) in att:
        parts.append(stroke([(ax, ay - ins), (ax, ay)], lw * 1.6))
    g = biggest(V.union(*parts).buffer(0))
    return g, att, (x, yb - h)


def perspective(n: int, x0: float, x1: float, yb0: float, yb1: float, h0: float, h1: float, k: float = 1.8):
    """Ряд опор в перспективе: шаг и высота убывают по геометрической прогрессии (k — сила перспективы)."""
    ts = [(1 - math.exp(-k * i / (n - 1))) / (1 - math.exp(-k)) for i in range(n)]
    return [(x0 + (x1 - x0) * t, yb0 + (yb1 - yb0) * t, h0 + (h1 - h0) * t) for t in ts]


def line_row(theme, row, alpha=1.0, wire_col="ink2", lw_wire=0.03, z=10, names="py"):
    objs, wires = [], [[] for _ in range(3)]
    atts = []
    for i, (x, yb, h) in enumerate(row):
        g, att, _ = pylon(x, yb, h)
        objs.append(vs(f"!!{names}{i}", g, fill=mix(theme.c("ink2"), theme.c("bg"), 0.15), fa=alpha, z=z + i, meta=dict(DEC)))
        atts.append(att)
    for f in range(3):
        pts = []
        for i in range(len(row) - 1):
            seg = catenary(atts[i][f], atts[i + 1][f], sag=0.06 * row[i][2], n=24)
            pts += seg if not pts else seg[1:]
        wires[f] = pts
    return objs, wires


# ============================================================================= варианты

def pylons_row(theme) -> Variant:
    cols = phase_cols(theme)
    big = [(8.6, 7.4, 6.4)]
    row = perspective(6, 2.2, 12.6, 6.9, 4.1, 4.6, 0.7, k=2.2)
    sl = []
    o1, _ = line_row(theme, big)
    sl.append(S(o1 + [kicker("сеть 110 кВ"), head("Одна опора", w=5)], 700))
    o2, wires = line_row(theme, [row[0]] + row[1:])
    o2 = [o.copy(name="!!py0") if o.name == "!!py0" else o for o in o2]
    wobj = [vs(f"!!w{f}", stroke(wires[f], 0.03), 220, fill="ink2", fa=0.9, z=30, meta=dict(DEC)) for f in range(3)]
    sl.append(S(o2 + wobj + [kicker("сеть 110 кВ"), head("Линия уходит вдаль", w=6)], 900,
                fx=[Fx("entrance_fade", f"!!py{i}", start="at", delay=0.1 + 0.08 * i) for i in range(1, 6)] +
                   [Fx("entrance_wipe", f"!!w{f}", start="at", delay=0.5, dur=0.6, options={"direction": "left"}) for f in range(3)]))
    o3, wires = line_row(theme, row)
    wobj = [vs(f"!!w{f}", stroke(wires[f], 0.03), 220, fill=cols[f], z=30, meta=dict(DEC)) for f in range(3)]
    loops = [flow(wires[f], n=3, period=2.6 + 0.4 * f, size=0.12, name=f"cur_{f}", color=cols[f], z=31) for f in range(3)]
    sl.append(S(o3 + wobj + [kicker("сеть 110 кВ"), head("Ток по фазам", w=6),
                             body("!!b", 0.7, 1.45, 5, 0.4, "точки бегут строго по проводам", sz=14, col="muted")], 700, loops=loops))
    return _v("pylons_row", "Опора → линия в перспективе",
              "Глубина из 2D: одна крупная опора становится первой в ряду, остальные — меньше и теснее к горизонту "
              "(геометрическая перспектива); провода — цепные линии; затем фазы окрашиваются и по ним бежит ток "
              "(петля flow по точкам провода). Обложка энергетической презентации.",
              sl, ["energy", "3d", "perspective", "flow", "hero"], 4)


def _wave_ribbon(x0, x1, y, amp, periods, phase, w=0.05, n=120):
    return stroke(wave(x0, x1, y, amp, periods, phase, n), w)


def _arrow(cx, cy, L, ang, w=0.07):
    a = math.radians(ang)
    tip = (cx + L * math.cos(a), cy + L * math.sin(a))
    shaft = stroke([(cx, cy), (cx + (L - 0.25) * math.cos(a), cy + (L - 0.25) * math.sin(a))], w)
    nx, ny = -math.sin(a), math.cos(a)
    bx, by = cx + (L - 0.32) * math.cos(a), cy + (L - 0.32) * math.sin(a)
    head_ = V.polygon([tip, (bx + nx * 0.14, by + ny * 0.14), (bx - nx * 0.14, by - ny * 0.14)])
    return biggest(V.union(shaft, head_))


NR = 90  # точек на край ленты


def shaft(c, L, w=0.07):
    """Стрелка вдоль 0° от центра c (поворот — рамкой на оси): лента-древко и наконечник отдельно."""
    return ribbon([(c[0], c[1]), (c[0] + L - 0.28, c[1])], w, NR), V.polygon([(c[0] + L, c[1]), (c[0] + L - 0.34, c[1] - 0.15),
                                                                           (c[0] + L - 0.34, c[1] + 0.15)])


def three_phase(theme) -> Variant:
    cols = phase_cols(theme)
    names = ["A", "B", "C"]
    sl = []
    # 1: три отдельные синусоиды
    o = [head("Три фазы"), body("!!b", 0.7, 1.4, 5, 0.4, "каждая — своя синусоида", sz=15, col="muted")]
    for f in range(3):
        o.append(raw(f"!!ph{f}", ribbon(wave(3.0, 12.4, 2.6 + f * 1.55, 0.5, 2, 0, 160), 0.05, NR), pivot=(8.6, 4.1), fill=cols[f], z=10))
        o.append(label(f"!!pl{f}", 2.6, 2.6 + f * 1.55 - 0.18, names[f], w=0.5, al="r", sz=18, b=True, col=cols[f]))
    sl.append(S(o, 700))
    # 2: на одной оси, сдвиг 120°
    o = [head("Сдвиг на 120°"), body("!!b", 0.7, 1.4, 5, 0.4, "сумма трёх токов — ноль", sz=15, col="muted"),
         line("axis", (3.0, 4.1), (12.4, 4.1), ln="line", lw=1.0)]
    for f in range(3):
        o.append(raw(f"!!ph{f}", ribbon(wave(3.0, 12.4, 4.1, 1.3, 2, -2 * math.pi * f / 3, 160), 0.05, NR), pivot=(8.6, 4.1),
                     fill=cols[f], z=10 + f))
        o.append(label(f"!!pl{f}", 2.6, 4.1 - 0.18 + (f - 1) * 0.42, names[f], w=0.5, al="r", sz=18, b=True, col=cols[f]))
    sl.append(S(o, 900))
    # 3: синусоиды сворачиваются в векторы
    c = (8.6, 4.1)
    o = [head("Векторы фаз"), body("!!b", 0.7, 1.4, 5, 0.4, "звезда: три стрелки по 120°", sz=15, col="muted"),
         O("circ", "oval", c[0] - 2.2, c[1] - 2.2, 4.4, 4.4, fill=None, ln="line", lw=1.0, z=3)]
    for f in range(3):
        ang = -90 + 120 * f
        sh_, hd = shaft(c, 2.2)
        o.append(raw(f"!!ph{f}", sh_, pivot=c, rot=ang % 360, fill=cols[f], z=10 + f))
        o.append(raw(f"!!phh{f}", hd, pivot=c, rot=ang % 360, fill=cols[f], z=10 + f))
        tx, ty = c[0] + 2.55 * math.cos(math.radians(ang)), c[1] + 2.55 * math.sin(math.radians(ang))
        o.append(label(f"!!pl{f}", tx, ty - 0.18, names[f], w=0.5, sz=18, b=True, col=cols[f]))
    sl.append(S(o, 900, loops=[Loop("spin", target="circ", period=4.0, name="spin")]))
    return _v("three_phase", "Три синусоиды → звезда векторов",
              "Перелив формы со смыслом: три ленты-синусоиды (по 240 точек) сходятся на одну ось со сдвигом 120°, затем "
              "каждая сворачивается в стрелку вектора — «векторная диаграмма» из тех же объектов. Подписи фаз едут следом.",
              sl, ["energy", "shape-morph", "wave", "data"], 4)


NODES = {"ГЭС": (1.6, 2.4), "ПС-1": (4.4, 1.9), "ПС-2": (4.0, 4.6), "ПС-3": (7.2, 3.3), "ПС-4": (7.6, 5.9),
         "ПС-5": (10.2, 2.2), "Город": (11.6, 4.6)}
EDGES = [("ГЭС", "ПС-1"), ("ГЭС", "ПС-2"), ("ПС-1", "ПС-3"), ("ПС-2", "ПС-3"), ("ПС-2", "ПС-4"), ("ПС-3", "ПС-5"),
         ("ПС-4", "Город"), ("ПС-5", "Город"), ("ПС-3", "Город")]


def _hexnode(name, c, r, fill, ln, z=20, fa=1.0):
    return vs(name, V.regular(c[0], c[1], r, 6, start=0), fill=fill, ln=ln, lw=1.5, fa=fa, la=fa, z=z)


def _net(theme, broken=None, reserve=False, focus=None, shift=(0, 0), alpha=1.0, scale=1.0, labels=True, z=10):
    out, loops = [], []
    pos = {k: (shift[0] + v[0] * scale, shift[1] + v[1] * scale) for k, v in NODES.items()}
    edges = list(EDGES) + ([("ПС-1", "ПС-5")] if reserve else [])
    for e, (a, b) in enumerate(edges):
        pa, pb = pos[a], pos[b]
        bad = broken == e
        nm = f"!!e{e}"
        out.append(line(nm, pa, pb, ln="bad" if bad else ("accent2" if not bad else "line"), lw=2.0 * scale, z=z,
                        dash="dash" if bad else None, la=alpha))
        if not bad and alpha > 0.5:
            loops.append(flow([pa, pb], n=2, period=2.0 + 0.15 * (e % 4), size=0.1, name=f"cur_{e}", color="accent", z=z + 0.5))
    for k, (nm, p) in enumerate(pos.items()):
        on = focus == nm
        out.append(_hexnode(f"!!n{k}", p, 0.32 * scale, fill=theme.c("surface2") if not on else theme.c("accent"),
                            ln="accent2" if not on else "accent", z=z + 5, fa=alpha))
        if labels:
            out.append(label(f"!!nl{k}", p[0], p[1] + 0.38 * scale, nm, w=1.4, sz=13, col="ink2", b=on))
    return out, loops


def grid_fault(theme) -> Variant:
    o1, l1 = _net(theme)
    o2, l2 = _net(theme, broken=5)
    mid = [(a + b) / 2 for a, b in zip(NODES["ПС-3"], NODES["ПС-5"])]
    o2 += [O("fault", "oval", mid[0] - 0.14, mid[1] - 0.14, 0.28, 0.28, fill="bad", z=30)]
    o3, l3 = _net(theme, broken=5, reserve=True)
    o3 += [O("fault", "oval", mid[0] - 0.14, mid[1] - 0.14, 0.28, 0.28, fill="bad", z=30)]
    return _v("grid_fault", "Сеть: обрыв и обход",
              "Мнемосхема: подстанции-шестиугольники, по рёбрам бежит ток (петли строго по линиям). Обрыв: ребро "
              "становится красным пунктиром, ток по нему останавливается, у места — круги на воде. Затем резервная "
              "связь вырастает (вытирание), поток идёт в обход.",
              [S(o1 + [head("Сеть в норме", w=6)], 700, loops=l1),
               S(o2 + [head("Обрыв ПС-3 — ПС-5", w=7)], 700, loops=l2 + [Loop("ripple", target="fault", period=1.6, scale=2.4,
                                                                                 color="bad", name="rip")]),
               S(o3 + [head("Резерв ПС-1 — ПС-5", w=7)], 800, loops=l3 + [Loop("ripple", target="fault", period=1.6, scale=2.4,
                                                                                  color="bad", name="rip")],
                 fx=[Fx("entrance_wipe", f"!!e{len(EDGES)}", start="at", delay=0.1, dur=0.5, options={"direction": "left"})])],
              ["energy", "network", "flow", "ripple"], 4)


def _coil(cx, y0, y1, r, turns, front=True, w=0.06, n=160):
    """Обмотка-спираль в проекции: передние полувитки (front=True) или задние."""
    out = []
    for k in range(turns):
        ya, yb_ = y0 + (y1 - y0) * k / turns, y0 + (y1 - y0) * (k + 1) / turns
        pts = []
        for i in range(25):
            t = i / 24
            a = math.pi * t if front else math.pi * (1 + t)
            pts.append((cx - r * math.cos(a), ya + (yb_ - ya) * t + 0.12 * math.sin(a)))
        out.append(stroke(pts, w))
    return V.union(*out) if out else None


def transformer(theme) -> Variant:
    cu = mix(theme.c("accent"), "B06A2A", 0.4)
    core = theme.c("surface2")
    def tr(cx=8.2, cy=3.9, s=1.0, waves=False, focus=False):
        o = []
        frame = V.subtract(V.rect(cx - 2.0 * s, cy - 1.9 * s, 4.0 * s, 3.8 * s, r=0.1),
                           V.rect(cx - 1.2 * s, cy - 1.3 * s, 2.4 * s, 2.6 * s, r=0.05))
        o.append(vs("!!core", frame, fill=core, ln="line", lw=1.0, z=10))
        for side, x in enumerate([cx - 1.6 * s, cx + 1.6 * s]):
            turns = 7 if side == 0 else 4
            back = _coil(x, cy - 1.4 * s, cy + 1.4 * s, 0.42 * s, turns, front=False, w=0.05 * s)
            front = _coil(x, cy - 1.4 * s, cy + 1.4 * s, 0.42 * s, turns, front=True, w=0.07 * s)
            o.append(vs(f"!!cb{side}", back, fill=dark(cu, 0.45), z=9))
            o.append(vs(f"!!cf{side}", front, fill=cu, z=12, grad=V.gradient([(0, light(cu, 0.3)), (1, dark(cu, 0.2))], 0)))
        return o
    o1 = tr() + [head("Трансформатор"), body("!!b", 0.7, 1.4, 4.5, 0.8, ["7 витков слева,", "4 справа"], sz=16)]
    o2 = tr()
    pw = stroke(wave(0.6, 5.6, 6.3, 0.45, 3, 0), 0.05)
    sw = stroke(wave(10.8, 12.9, 6.3, 0.26, 1.3, 0), 0.05)
    o2 += [head("Напряжение падает"), vs("w_in", pw, fill="accent", z=20), vs("w_out", sw, fill="accent2", z=20),
           label("li", 3.1, 6.85 - 0.35, "вход: больше", w=2.4, sz=13), label("lo", 11.85, 6.85 - 0.35, "выход: меньше", w=2.2, sz=13)]
    loops = [flow(wave(0.6, 5.6, 6.3, 0.45, 3, 0, 60), n=2, period=2.4, color="accent", name="win"),
             flow(wave(10.8, 12.9, 6.3, 0.26, 1.3, 0, 30), n=1, period=2.4, color="accent2", name="wout")]
    o3 = tr(s=1.0)
    o3 = [o.copy(fa=0.25, la=0.25) if o.name.startswith("!!c") and o.name != "!!core" else o for o in o3]
    o3 += [head("Обмотки — 3D из 2D"), body("!!b", 0.7, 1.4, 5, 1.2, ["передние полувитки ярче,", "задние — темнее и ниже"], sz=16)]
    o3 = [o.copy(fa=1.0) if o.name in ("!!cf0", "!!cf1") else o for o in o3]
    return _v("transformer", "Трансформатор: витки спереди и сзади",
              "Объём из 2D: обмотка — передние полувитки (светлый градиент, выше по слою) и задние (тёмные, под "
              "сердечником) — читается как спираль вокруг стержня. Затем вход/выход синусоидами с током по ним.",
              [S(o1, 700), S(o2, 800, loops=loops,
                             fx=[Fx("entrance_wipe", "w_in", start="at", delay=0.1, dur=0.5, options={"direction": "left"}),
                                 Fx("entrance_wipe", "w_out", start="at", delay=0.4, dur=0.4, options={"direction": "left"})]),
               S(o3, 700)], ["energy", "3d", "wave", "flow"], 3)


def pylon_pointer(theme) -> Variant:
    secs = ["Генерация", "Передача", "Распределение", "Потребление"]
    sl = []
    x0, yb0, h0 = 0.0, 9.4, 9.6
    g, att, top = pylon(x0, yb0, h0)
    # уровни-разделы снизу вверх: правая нога (2 точки), правый конец нижней траверсы, верхней траверсы
    leg = lambda t: (x0 + 0.18 * h0 + (0.045 * h0 - 0.18 * h0) * t, yb0 - 0.86 * h0 * t)  # noqa: E731
    levels = [leg(0.33), leg(0.58), att[1], att[2]]
    for k in range(3):
        o = [vs("!!pyl", g, fill=mix(theme.c("ink2"), theme.c("bg"), 0.55), z=5, meta=dict(DEC))]
        for i, (x, y) in enumerate(levels):
            on = i == k
            o.append(O(f"!!ins{i}", "oval", x - 0.16, y - 0.16, 0.32, 0.32, fill="accent" if on else "surface2",
                       ln="accent" if on else "line", lw=1.5, z=20))
            o.append(label(f"!!il{i}", x + 0.3, y - 0.17, f"0{i + 1} {secs[i]}", w=2.3, al="l", sz=13, b=on,
                           col="accent" if on else "muted"))
        o += [kicker(f"раздел {k + 1}", x=5.6), head(secs[k], x=5.6, w=7),
              body("!!txt", 5.6, 1.5, 7, 1.0, ["станции и блоки", "линии высокого напряжения", "подстанции и фидеры"][k], sz=18)]
        sl.append(S(o, 800, loops=[Loop("ripple", target=f"!!ins{k}", period=2.0, scale=1.9, color="accent", name="rip")]))
    return _v("pylon_pointer", "Опора у края: изоляторы-разделы",
              "Навигация: огромная опора срезана левым краем, на её ярусах — «изоляторы»-разделы с подписями; текущий "
              "горит акцентом и даёт круги на воде. Смена раздела — перекраска и переезд пульса, опора неподвижна.",
              sl, ["energy", "pointer", "navigation", "ripple"], 3)


def wave_steps(theme) -> Variant:
    """Прогресс внутри раздела: синусоида из 4 периодов, пройденные периоды светятся, точка бежит по пройденному."""
    x0, x1, y = 1.2, 12.2, 4.6
    topics = ["Измерение", "Фильтр", "Прогноз", "Решение"]
    sl = []
    for k in range(3):
        o = [kicker("раздел 3 · диспетчер"), head(f"Шаг {k + 1}: {topics[k].lower()}", w=6), body("!!b", 0.7, 1.4, 5, 0.4, f"{(k + 1) * 25} % раздела",
                                                                         sz=14, col="muted")]
        done = []
        for p in range(4):
            pts = wave(x0 + (x1 - x0) * p / 4, x0 + (x1 - x0) * (p + 1) / 4, y, 0.9, 1, 0, 40)
            on = p <= k
            o.append(vs(f"!!wp{p}", stroke(pts, 0.07 if on else 0.04), 90, start=180, fill="accent" if on else "line", z=10))
            o.append(label(f"!!wt{p}", (x0 + (x1 - x0) * (p + 0.5) / 4), y + 1.25, topics[p], w=2.4, sz=14, b=p == k,
                           col="accent" if p == k else ("ink2" if on else "muted")))
            if on:
                done += pts if not done else pts[1:]
        sl.append(S(o, 700, loops=[flow(done, n=2, period=1.6 + 0.7 * k, size=0.14, name="cur", color="ink")]))
    return _v("wave_steps", "Синусоида раздела: периоды = шаги",
              "Прогресс внутри раздела: 4 периода волны = 4 темы; пройденные периоды толще и янтарные, по пройденному "
              "участку бежит точка тока (её путь — тот же контур). 25 → 50 → 75 %.",
              sl, ["energy", "progress", "flow"], 4)


def load_curve(theme) -> Variant:
    xs = [1.2 + 11.0 * i / 48 for i in range(49)]
    def prof(kind):
        out = []
        for i, x in enumerate(xs):
            hr = i / 2
            if kind == 0:
                v = 0.35 + 0.25 * math.exp(-((hr - 9) / 2.2) ** 2) + 0.4 * math.exp(-((hr - 19.5) / 2.5) ** 2)
            else:
                v = 0.3 + 0.18 * math.exp(-((hr - 13) / 4) ** 2) + 0.2 * math.exp(-((hr - 20) / 2.5) ** 2)
            out.append((x, 6.4 - v * 4.2))
        return out
    sl = []
    for k, (t, kind) in enumerate([("Будний день", 0), ("Выходной", 1)]):
        pts = prof(kind)
        area = V.polygon([(xs[0], 6.4)] + pts + [(xs[-1], 6.4)])
        o = [head("Профиль нагрузки", w=6), body("!!b", 0.7, 1.4, 5, 0.4, t, sz=16, col="accent"),
             line("base", (1.2, 6.4), (12.2, 6.4), ln="line", lw=1.0)]
        o.append(vs("!!area", area, 160, start=90, fill="accent2", fa=0.35, z=8))
        o.append(vs("!!edge", stroke(pts, 0.05), 200, start=180, fill="accent2", z=9))
        pk = min(pts, key=lambda p: p[1])
        o.append(O("!!peak", "oval", pk[0] - 0.12, pk[1] - 0.12, 0.24, 0.24, fill="accent", z=12))
        o.append(label("!!pkl", pk[0], pk[1] - 0.5, "пик", w=1.0, sz=13, b=True, col="accent"))
        o += [label(f"h{j}", 1.2 + 11 * j / 4, 6.5, f"{6 * j}:00", w=1.0, sz=12, col="muted") for j in range(5)]
        sl.append(S(o, 800))
    return _v("load_curve", "Профиль нагрузки переливается",
              "Данные: площадь и контур суточного профиля — свободные формы с равным числом точек; будний день "
              "переливается в выходной, маркер пика переезжает с подписью. Форма условная (без величин).",
              sl, ["energy", "data", "shape-morph", "area"], 3)


def cable(theme) -> Variant:
    c = (8.6, 3.9)
    layers = [("оболочка", 2.3, "surface2"), ("броня", 2.0, "ink2"), ("экран", 1.75, "accent3"), ("изоляция", 1.55, "surface")]
    cols = phase_cols(theme)
    sl = []
    for st in range(3):
        o = [head(["Кабель в разрезе", "Слои расходятся", "Три жилы"][st], w=6)]
        for i, (nm, r, colr) in enumerate(layers):
            r_in = layers[i + 1][1] if i + 1 < len(layers) else 0
            if st == 0:
                g = V.subtract(V.circle(*c, r), V.circle(*c, r_in)) if r_in else V.circle(*c, r)
                o.append(vs(f"!!cl{i}", g, 0, fill=colr, ln="bg", lw=1.0, z=10 + i))
            else:
                # слои — кольца-эллипсы, разъехавшиеся влево по оси кабеля (телескоп)
                dx = -(3 - i) * 1.25 if st == 1 else -(3 - i) * 1.25 - 0.5
                g = V.subtract(V.ellipse(c[0] + dx, c[1], r * 0.45, r), V.ellipse(c[0] + dx, c[1], r_in * 0.45, r_in)) if r_in \
                    else V.ellipse(c[0] + dx, c[1], r * 0.45, r)
                o.append(vs(f"!!cl{i}", g, 0, fill=colr, ln="bg", lw=1.0, z=10 + i))
                o.append(label(f"!!cn{i}", c[0] + dx, c[1] + r + 0.12, nm, w=1.5, sz=13))
        for f in range(3):
            a = math.radians(-90 + 120 * f)
            g = V.sector(c[0], c[1], 0.95, -90 + 120 * f - 52, -90 + 120 * f + 52, r_in=0.12)
            if st == 1:
                g = V.move(g, 0.5, 0)
            elif st == 2:
                g = V.move(g, 2.1 + 0.75 * math.cos(a), 0.75 * math.sin(a))
            o.append(vs(f"!!cj{f}", g, 60, fill=cols[f], ln="bg", lw=1.0, z=30 + f))
            if st == 2:
                gc = g.centroid
                o.append(label(f"cjl{f}", gc.x + 0.75 * math.cos(a), gc.y + 0.75 * math.sin(a) - 0.17, "ABC"[f], w=0.5,
                               sz=16, b=True, col=cols[f]))
        sl.append(S(o, 800))
    return _v("cable", "Разрез кабеля: слои-телескоп",
              "Разлёт частей с объёмом: кольца разреза (оболочка, броня, экран, изоляция) становятся эллипсами и "
              "разъезжаются по оси — как трубы телескопа (вид сбоку из вида торцом); три жилы-сектора выходят вперёд. "
              "Для раздела «из чего состоит».",
              sl, ["energy", "fragment", "3d", "structure"], 3)


def substation_zoom(theme) -> Variant:
    objs = []
    net, loops = _net(theme, labels=True)
    w_objs = [o.copy(world=True) for o in net]
    c = NODES["ПС-3"]
    # внутри шестиугольника ПС-3 — мини-схема: шины и трансформаторы (мелко, в мировых координатах)
    inner = []
    for k in range(3):
        y = c[1] - 0.12 + k * 0.12
        inner.append(O(f"!!bus{k}", "line", c[0] - 0.18, y, 0.36, 0, ln="accent2", lw=1.2, world=True, z=40))
    for k in range(2):
        x = c[0] - 0.08 + k * 0.16
        inner += [O(f"!!tr{k}a", "oval", x - 0.035, c[1] + 0.12, 0.07, 0.07, fill=None, ln="accent", lw=0.8, world=True, z=41),
                  O(f"!!tr{k}b", "oval", x - 0.035, c[1] + 0.17, 0.07, 0.07, fill=None, ln="accent", lw=0.8, world=True, z=41)]
    s1 = S([head("Сеть", w=4)] + w_objs + inner, 700, cam=Cam(W / 2, H / 2, 1.0), loops=loops)
    zcam = Cam(c[0] - 0.22, c[1] + 0.02, 9.0)
    w2 = [o for o in w_objs if not o.name.startswith("!!nl")]
    s2 = S([head("ПС-3 изнутри", w=5), body("!!b", 0.7, 1.4, 4, 0.8, ["три шины,", "два трансформатора"], sz=16)] + w2 + inner,
           900, cam=zcam)
    return _v("substation_zoom", "Камера ныряет в подстанцию",
              "Мир-холст: сеть подстанций в мировых координатах; камера приближается ×9 к узлу ПС-3, внутри "
              "шестиугольника видна заранее нарисованная мелкая схема (шины, трансформаторы). Переход общий план → деталь.",
              [s1, s2], ["energy", "camera", "zoom", "network"], 3)


def grid_backdrop(theme) -> Variant:
    sl = []
    for st in range(2):
        net, _ = _net(theme, alpha=0.12, scale=1.5, shift=(-1.5 + 0.8 * st, -1.6 + 0.3 * st), labels=False, z=-300)
        net = [o.copy(meta={**o.meta, **DEC}) for o in net]
        o = net + [head(["Итоги года", "Что дальше"][st], w=7),
                   body("!!b", 0.7, 1.5, 7.5, 2.0, [["меньше отключений", "резервные связи", "быстрее ремонт"],
                                                    ["цифровые подстанции", "прогноз нагрузки", "учёт в реальном времени"]][st],
                        sz=22, col="ink")]
        sl.append(S(o, 800))
    return _v("grid_backdrop", "Сеть уходит в фон",
              "Фон: та же схема подстанций в 1,5 раза крупнее и с прозрачностью 12 % лежит под текстом; между "
              "слайдами медленно смещается (параллакс без камеры). Текст читается, мир не пропадает.",
              sl, ["energy", "backdrop", "network"], 3)


def seq_energy(theme) -> Variant:
    """Живая линия через презентацию: опора → ряд в перспективе → ток → провода распрямляются в три синусоиды → векторы →
    узлы сети у края (навигация) → бледный фон под графиком → снова опора."""
    cols = phase_cols(theme)
    row = perspective(6, 2.2, 12.6, 6.9, 4.1, 4.6, 0.7, k=2.2)
    big = [(8.6, 7.4, 6.4)]
    S_ = []
    # опоры как объекты !!py0..5 во всех состояниях (лишние — припаркованы за краем/крошечные)
    def pyl(states):
        out = []
        for i, (x, yb, h, a) in enumerate(states):
            g, _, _ = pylon(x, yb, h)
            out.append(vs(f"!!py{i}", g, fill=mix(theme.c("ink2"), theme.c("bg"), 0.15), fa=a, z=10 + i, meta=dict(DEC)))
        return out
    _, wires = line_row(theme, row)
    PC = (8.8, 4.0)
    def wire(f, g, rot=0.0, piv=PC, **kw):
        return raw(f"!!w{f}", g, pivot=piv, rot=rot % 360, meta=dict(DEC), z=30, **kw)
    def whead(f, hd, rot, piv, **kw):
        return raw(f"!!wh{f}", hd, pivot=piv, rot=rot % 360, meta=dict(DEC), z=30, **kw)
    park = [(15 + i, 6.9, 0.7, 1.0) for i in range(6)]
    # 1 герой
    st1 = [(8.6, 7.4, 6.4, 1.0)] + [(row[i][0] + 6, row[i][1], row[i][2], 0.0) for i in range(1, 6)]
    hide_w = [wire(f, ribbon([(7.2, 2.2 + 0.4 * f), (7.3, 2.2 + 0.4 * f)], 0.02, NR), fill="ink2", fa=0.0) for f in range(3)]
    S_.append(S(pyl(st1) + hide_w + [kicker("энергосистема"), O("!!cov", "text", 0.7, 1.0, 5.4, 1.6, txt=["Как течёт", "электричество"],
                                                                 sz=44, b=True, font="head", col="ink", spacing=0.95, z=90)], 700))
    # 2 ряд в перспективе
    st2 = [(x, yb, h, 1.0) for x, yb, h in row]
    S_.append(S(pyl(st2) + [wire(f, ribbon(wires[f], 0.03, NR), fill="ink2") for f in range(3)] + [head("Линия до горизонта", w=7)], 900))
    # 3 ток по фазам
    loops = [flow(wires[f], n=3, period=2.6 + 0.4 * f, size=0.12, name=f"cur_{f}", color=cols[f], z=31) for f in range(3)]
    S_.append(S(pyl(st2) + [wire(f, ribbon(wires[f], 0.035, NR), fill=cols[f]) for f in range(3)] + [head("Ток по трём фазам", w=7)],
                700, loops=loops))
    # 4 провода распрямляются в синусоиды; опоры уходят вниз
    st4 = [(x, yb + 4.5, h, 0.0) for x, yb, h in row]
    waves = [wave(1.2, 12.4, 4.2, 1.2, 2, -2 * math.pi * f / 3, 120) for f in range(3)]
    S_.append(S(pyl(st4) + [wire(f, ribbon(waves[f], 0.05, NR), fill=cols[f]) for f in range(3)] +
                [head("Сдвиг фаз 120°", w=6), line("ax", (1.2, 4.2), (12.4, 4.2), ln="line", lw=1.0, z=2)], 900,
                loops=[flow(waves[f][::3], n=2, period=3.0, size=0.12, name=f"cur_{f}", color=cols[f], z=31) for f in range(1)]))
    # 5 векторы
    c = (8.8, 4.0)
    arrows = []
    for f in range(3):
        sh_, hd = shaft(c, 2.2)
        arrows += [wire(f, sh_, rot=-90 + 120 * f, piv=c, fill=cols[f]), whead(f, hd, -90 + 120 * f, c, fill=cols[f])]
    S_.append(S(pyl(st4) + arrows +
                [head("Векторы фаз", w=6), body("!!b", 0.7, 1.4, 4.5, 0.8, ["сумма трёх токов —", "ноль"], sz=18),
                 O("circ", "oval", c[0] - 2.2, c[1] - 2.2, 4.4, 4.4, fill=None, ln="line", lw=1.0, z=3)], 900))
    # 6–7 навигация: три стрелки сжимаются в «звезду» у левого края; разделы — лучи
    secs = ["Генерация", "Передача", "Распределение"]
    def nav(k, title, text):
        cc = (-0.3, 3.75)
        o = pyl(st4)
        o.append(O("navc", "oval", cc[0] - 2.4, cc[1] - 2.4, 4.8, 4.8, fill=None, ln="line", lw=1.0, z=3, meta=dict(DEC)))
        for f in range(3):
            ang = 120 * (f - k)  # луч раздела k смотрит вправо, на заголовок
            sh_, hd = shaft(cc, 2.9 if f == k else 2.3, w=0.1 if f == k else 0.06)
            o += [wire(f, sh_, rot=ang, piv=cc, fill=cols[f], fa=1.0 if f == k else 0.5),
                  whead(f, hd, ang, cc, fill=cols[f], fa=1.0 if f == k else 0.5)]
        o += [label(f"!!sc{i}", 2.9, 4.6 + i * 0.45, f"0{i + 1} {s}", w=2.4, al="l", sz=13, b=i == k,
                    col="accent" if i == k else "muted") for i, s in enumerate(secs)]
        o += [kicker(f"раздел {k + 1}", x=5.6), head(title, x=5.6, w=7), body("!!txt", 5.6, 1.5, 7, 1.2, text, sz=18)]
        return o
    S_.append(S(nav(0, "Генерация", ["ГЭС, ТЭС и ветер", "синхронная частота"]), 900))
    S_.append(S(nav(1, "Передача", ["линии 110–500 кВ", "меньше ток — меньше потерь"]), 800))
    # 8 фон: ряд опор бледно под профилем нагрузки
    xs = [1.2 + 11.0 * i / 48 for i in range(49)]
    prof = [(x, 6.4 - 4.0 * (0.35 + 0.25 * math.exp(-((i / 2 - 9) / 2.2) ** 2) + 0.4 * math.exp(-((i / 2 - 19.5) / 2.5) ** 2)))
            for i, x in enumerate(xs)]
    st8 = [(x, yb, h * 1.2, 0.12) for x, yb, h in row]
    o8 = pyl(st8) + [wire(f, ribbon(wires[f], 0.03, NR), fill="ink2", fa=0.12) for f in range(3)]
    o8 += [head("Нагрузка за сутки", w=7), vs("!!area", V.polygon([(1.2, 6.4)] + prof + [(12.2, 6.4)]), fill="accent", fa=0.5, z=40),
           label("pk", 9.5, 1.35, "вечерний пик", w=2.2, sz=14, b=True, col="accent")]
    S_.append(S(o8, 900, fx=[Fx("entrance_wipe", "!!area", start="at", delay=0.1, dur=0.6, options={"direction": "left"})]))
    # 9 финал
    S_.append(S(pyl(st1) + hide_w + [O("!!fin", "text", 0.7, 1.2, 5.6, 1.6, txt=["Сеть — один", "организм"], sz=40, b=True,
                                       font="head", col="ink", spacing=0.95, z=90)], 900))
    return _v("seq_energy", "Линия живёт через презентацию",
              "9 состояний одной линии: опора-герой → ряд в перспективе → ток бежит по фазам (по проводам) → провода "
              "распрямляются в три синусоиды со сдвигом → синусоиды сворачиваются в векторы → векторы у левого края — "
              "навигация (луч раздела длиннее) → бледный ряд опор под профилем нагрузки → снова одна опора.",
              S_, ["seq", "energy", "shape-morph", "flow", "pointer", "backdrop", "3d"], 4)


def variants(theme) -> list[Variant]:
    return [seq_energy(theme), pylons_row(theme), three_phase(theme), grid_fault(theme), transformer(theme),
            pylon_pointer(theme), wave_steps(theme), load_curve(theme), cable(theme), substation_zoom(theme), grid_backdrop(theme)]
