"""Семейство tangram: семь фигур танграма (и кубики-пиксели) собираются в квадрат, стрелку, ступени роста,
разлетаются в ряд аргументов, поворачиваются, встают недостающим звеном. Кусок — жёсткое тело: Morph двигает
и вращает рамку (поворот всегда < 180°), форма не переливается — кроме сознательного «кусок → панель».
"""

from __future__ import annotations

import math
import random

from shapely.geometry import Polygon

from morphkit import O, Slide
from morphkit import vector as V
from morphkit.presets import Fx
from morphkit.theme import contrast, mix

from lab import Variant
from lab._a_util import bbox_center, fit_rot, head, label, orbit, put, sub, sweep

K = 1 / math.sqrt(2)
SQ = {"T1": [(0, 0), (4, 0), (2, 2)], "T2": [(0, 0), (2, 2), (0, 4)], "M": [(4, 2), (4, 4), (2, 4)], "S1": [(4, 0), (4, 2), (3, 1)],
      "Q": [(2, 2), (3, 1), (4, 2), (3, 3)], "S2": [(2, 2), (3, 3), (1, 3)], "P": [(1, 3), (3, 3), (2, 4), (0, 4)]}
NAMES = ["T1", "T2", "M", "S1", "Q", "S2", "P"]
# стрелка вправо (единица — катет малого треугольника), ось y вниз; ствол зеркален — так сходится хиральность параллелограмма
ARROW = {"T1": [(3, 2), (5, 0), (3, 0)], "T2": [(3, 0), (5, 0), (3, -2)], "S1": [(-1, 0.5), (0, -0.5), (-1, -0.5)],
         "M": [(-1, 0.5), (1, 0.5), (0, -0.5)], "P": [(0, -0.5), (1, 0.5), (2, 0.5), (1, -0.5)], "S2": [(2, 0.5), (1, -0.5), (2, -0.5)],
         "Q": [(2, 0.5), (3, 0.5), (3, -0.5), (2, -0.5)]}
# ступени роста: квадрат (1), прямоугольник 1×2 (M+S1+S2), квадрат 2×2 (T1+T2) и параллелограмм-«стрелка» сверху
STEPS = {"Q": [(0, 2), (1, 2), (1, 3), (0, 3)], "M": [(1.3, 1), (1.3, 3), (2.3, 2)], "S1": [(1.3, 1), (2.3, 1), (2.3, 2)],
         "S2": [(2.3, 2), (2.3, 3), (1.3, 3)], "T1": [(2.6, 1), (4.6, 1), (4.6, 3)], "T2": [(2.6, 1), (4.6, 3), (2.6, 3)],
         "P": [(2.6, 1), (3.6, 1), (4.6, 0), (3.6, 0)]}
STEPS_P_ALT = [(2.6, 0), (3.6, 0), (4.6, 1), (3.6, 1)]


def canon(u: float, x: float, y: float) -> dict:
    """Куски в собранном квадрате (сторона 4·K·u), левый верхний угол в (x, y)."""
    return {n: Polygon([(x + px * K * u, y + py * K * u) for px, py in pts]) for n, pts in SQ.items()}


def target(layout: dict, u: float, x: float, y: float, alt: dict | None = None) -> dict:
    out = {}
    for n, pts in layout.items():
        out[n] = Polygon([(x + px * u, y + py * u) for px, py in pts])
    if alt:
        out.update({n: Polygon([(x + px * u, y + py * u) for px, py in pts]) for n, pts in alt.items()})
    return out


def place(pieces: dict, tgt: dict, prev: dict | None = None, alt: dict | None = None) -> dict:
    """Для каждого куска — (θ, dx, dy), чтобы канонический кусок лёг в цель; θ — ближайший к прошлому повороту."""
    res = {}
    for n, g in pieces.items():
        r = fit_rot(g, tgt[n], prefer=(prev or {}).get(n, (0, 0, 0))[0], step=45.0)
        if r is None and alt and n in alt:
            r = fit_rot(g, alt[n], prefer=(prev or {}).get(n, (0, 0, 0))[0], step=45.0)
        if r is None:
            raise ValueError(f"кусок {n} не ложится в цель")
        res[n] = r
    return res


def pcols(theme):
    ink, bg = theme.c("ink"), theme.c("bg")
    tones = [mix(ink, bg, t) for t in (0.12, 0.3, 0.45, 0.6, 0.22, 0.52, 0.38)]
    return dict(zip(NAMES, tones))


def draw(theme, pieces, pose, key="!!g", fills=None, fa=None, lw=1.5, z=10, hi=None):
    bg = theme.c("bg")
    out = []
    for i, n in enumerate(NAMES):
        th, dx, dy = pose[n]
        f = (fills or pcols(theme))[n]
        if hi == n:
            f = theme.c("accent")
        out.append(put(f"{key}{n}", pieces[n], dx, dy, rot=th, fill=f, fa=(fa or {}).get(n, 1.0), ln=bg, lw=lw, z=z + i))
    return out


def ident(pieces):
    return {n: (0.0, 0.0, 0.0) for n in pieces}


def on(theme, fill):
    f = theme.c(fill)
    a, b = theme.c("ink"), theme.c("bg")
    return a if contrast(a, f) >= contrast(b, f) else b


def row_pose(pieces, x0, y, gap=0.45, prefer=None, angles=None):
    """Куски в ряд по горизонтали (центры габаритов на высоте y), каждый со своим поворотом."""
    out, x = {}, x0
    for n in NAMES:
        g = pieces[n]
        th = (angles or {}).get(n, 0.0)
        gr = V.rotate(g, th, origin=bbox_center(g))
        b = gr.bounds
        w = b[2] - b[0]
        cx = x + w / 2
        c0 = bbox_center(g)
        out[n] = (th, cx - c0[0], y - c0[1])
        x += w + gap
    return out


# ----------------------------------------------------------------------------- одиночные

U = 0.95


def v_square_arrow(theme):
    pc = canon(U * 1.25, 6.67 - 2 * K * U * 1.25, 3.85 - 2 * K * U * 1.25)
    p0 = ident(pc)
    p1 = place(pc, target(ARROW, U * 1.25, 4.2, 3.9))
    return Variant("tangram", "square_arrow", "Квадрат складывается в стрелку",
                   "Семь фигур танграма — собранный квадрат «как есть»; каждая фигура поворачивается (≤ 135°) и "
                   "переезжает, и из того же набора выходит стрелка. Роль: «из тех же ресурсов — направление», стратегия.",
                   [Slide([head("Что у нас есть")] + draw(theme, pc, p0), dur=800),
                    Slide([head("Куда мы идём")] + draw(theme, pc, p1, hi="T1"), dur=900)],
                   tags=["tangram", "assemble", "rotate", "arrow"], score=4)


def v_args(theme):
    s = U * 1.15
    pc = canon(s, 7.4 - 2 * K * s, 3.95 - 2 * K * s)
    p0 = ident(pc)
    p1 = row_pose(pc, 0.9, 3.4, gap=0.42)
    args = {"T1": "Рынок", "T2": "Команда", "M": "Деньги", "S1": "Сроки", "Q": "Опыт", "S2": "Риски", "P": "Партнёры"}
    labs = []
    for n in NAMES:
        th, dx, dy = p1[n]
        c = bbox_center(pc[n])
        labs.append(label(f"al{n}", args[n], c[0] + dx, 5.2, w=1.6, sz=16, col="ink2"))
    p2 = place(pc, target(ARROW, s, 4.6, 4.0), prev=p1)
    return Variant("tangram", "args", "Аргументы складываются в вывод",
                   "Квадрат-решение разбирается на семь фигур, которые встают в ряд с подписями-аргументами, затем "
                   "те же фигуры складываются в стрелку-вывод. Роль: логика доклада, «семь доводов → одно решение».",
                   [Slide([head("Наше решение")] + draw(theme, pc, p0), dur=800),
                    Slide([head("Семь доводов")] + draw(theme, pc, p1) + labs, dur=900,
                          fx=[Fx("entrance_fade", l.name, start="at", delay=0.1 + 0.04 * k, dur=0.25) for k, l in enumerate(labs)]),
                    Slide([head("Один вывод")] + draw(theme, pc, p2, hi="T1"), dur=900)],
                   tags=["tangram", "explode", "argument", "arrow", "list"], score=4)


def v_steps(theme):
    s = U * 1.15
    pc = canon(s, 3.0 - 2 * K * s, 3.95 - 2 * K * s)
    alt = {"P": STEPS_P_ALT}
    tg = target(STEPS, s, 5.4, 2.6)
    p1 = place(pc, tg, alt=target(alt, s, 5.4, 2.6))
    labs = [label("st0", "2023", 5.4 + 0.5 * s, 6.25, w=1.4, sz=16, col="ink2"),
            label("st1", "2024", 5.4 + 1.8 * s, 6.25, w=1.4, sz=16, col="ink2"),
            label("st2", "2025", 5.4 + 3.6 * s, 6.25, w=1.4, sz=16, col="accent", b=True)]
    return Variant("tangram", "steps", "Квадрат → ступени роста",
                   "Квадрат слева разбирается, и фигуры переезжают вправо, складываясь в три ступени (1 → 2 → 3) с "
                   "параллелограммом-стрелкой наверху. Роль: план по годам, «как растём из того, что есть».",
                   [Slide([head("Ресурсы")] + draw(theme, pc, ident(pc)), dur=800),
                    Slide([head("Ступени роста")] + draw(theme, pc, p1, hi="P") + labs, dur=900,
                          fx=[Fx("entrance_fade", l.name, start="at", delay=0.12 + 0.05 * k, dur=0.25) for k, l in enumerate(labs)])],
                   tags=["tangram", "assemble", "data", "steps"], score=4)


def v_missing(theme):
    s = U * 1.35
    x0, y0 = 7.2, 3.9 - 2 * K * s
    pc = canon(s, x0, y0)
    p_in = ident(pc)
    out = dict(p_in)
    c = bbox_center(pc["Q"])
    out["Q"] = (-75.0, 2.0 - c[0], 4.6 - c[1])
    gap = V.shape("gap", pc["Q"], fill=None, ln=theme.c("muted"), lw=1.5, dash="dash", z=5)
    t = [label("mq", "Опыт команды", 2.0, 5.65, w=2.8, sz=18, col="accent", b=True)]
    return Variant("tangram", "missing", "Недостающее звено встаёт на место",
                   "Квадрат собран, кроме одной фигуры — на её месте пунктир, а сама фигура (акцент, с подписью) "
                   "ждёт в стороне, повёрнутая; она проворачивается и входит в паз. Роль: «чего не хватает», "
                   "закрытие разрыва, предложение партнёру.",
                   [Slide([head("Почти готово"), gap] + draw(theme, pc, out, hi="Q") + t, dur=800),
                    Slide([head("Недостающее звено"), gap] + draw(theme, pc, p_in, hi="Q"), dur=900)],
                   tags=["tangram", "puzzle", "rotate", "emphasis"], score=4)


def v_turn_up(theme):
    s = U * 0.95
    pc = canon(s, 3.6 - 2 * K * s, 3.85 - 2 * K * s)
    pr = place(pc, target(ARROW, s, 5.6, 3.9))
    up = {n: [(y, -x) for x, y in pts] for n, pts in ARROW.items()}  # поворот на −90°
    pu = place(pc, target(up, s, 9.9, 6.0), prev=pr)
    return Variant("tangram", "turn_up", "Стрелка поворачивается вверх",
                   "Квадрат складывается в стрелку вправо, затем каждая фигура доворачивается ещё на 90°, и стрелка "
                   "смотрит вверх — «от движения к росту». Роль: смена цели, разворот стратегии.",
                   [Slide([head("Старт")] + draw(theme, pc, ident(pc)), dur=800),
                    Slide([head("Движение")] + draw(theme, pc, pr, hi="T1"), dur=900),
                    Slide([head("Рост")] + draw(theme, pc, pu, hi="T1"), dur=900)],
                   tags=["tangram", "rotate", "arrow", "strategy"], score=4)


def v_lift3d(theme):
    s = U * 1.3
    pc = canon(s, 6.67 - 2 * K * s, 4.3 - 2 * K * s)
    bg = theme.c("bg")
    cols = pcols(theme)
    H = {"T1": 1.4, "T2": 0.4, "M": 0.9, "S1": 0.6, "Q": 1.1, "S2": 0.3, "P": 0.75}
    order = sorted(NAMES, key=lambda n: pc[n].centroid.y)

    from lab._a_util import iso

    def st(k, tilt=True):
        out = []
        for zi, n in enumerate(order):
            g = V.resample(pc[n], 48)
            if tilt:
                g = iso(g, (6.67, 4.3), 0.55, 0)
            h = H[n] * k
            out.append(V.shape(f"!!sd{n}", V.resample(sweep(g, h), 48), fill=mix(cols[n], bg, 0.5), z=10 + 2 * zi))
            out.append(V.shape(f"!!tp{n}", V.resample(V.move(g, 0, -h), 48), fill=cols[n] if n != "T1" else theme.c("accent"),
                               ln=bg, lw=1.0, z=11 + 2 * zi))
        return out

    return Variant("tangram", "lift3d", "Фигуры поднимаются на высоту вклада",
                   "Собранный квадрат ложится в перспективу, и каждая фигура выдавливается вверх призмой на высоту своего "
                   "вклада — плоский пазл становится объёмным рельефом. Имитация 3D из 2D. Роль: «вклад частей в общее решение».",
                   [Slide([head("Из чего решение")] + st(0, tilt=False), dur=800),
                    Slide([head("Кладём на стол")] + st(0), dur=800),
                    Slide([head("Вклад каждой части")] + st(1), dur=900)],
                   tags=["tangram", "3d", "extrude", "iso", "data"], score=3)


def v_orbit_build(theme):
    s = U * 1.3
    cx, cy = 6.67, 3.95
    pc = canon(s, cx - 2 * K * s, cy - 2 * K * s)
    R = 6.0

    def st(k, rot):
        out = []
        cols = pcols(theme)
        for i, n in enumerate(NAMES):
            g = pc[n]
            c = g.centroid
            a = math.atan2(c.y - cy, c.x - cx) if (c.x, c.y) != (cx, cy) else i
            rr = math.hypot(c.x - cx, c.y - cy) + k * (2.0 + 0.25 * i)
            g2 = V.move(g, cx + rr * math.cos(a) * 1.25 - c.x, cy + rr * math.sin(a) * 0.8 - c.y) if k else g
            out.append(orbit(f"!!o{n}", g2, (cx, cy), R, rot, fill=cols[n] if n != "Q" else theme.c("accent"), ln=theme.c("bg"), lw=1.5, z=10 + i))
        return out

    return Variant("tangram", "orbit_build", "Фигуры слетаются по орбите",
                   "Семь фигур кружат вокруг будущего квадрата на эллипсе (рамка на оси центра) и по спирали "
                   "ложатся на места. Роль: «всё сходится», сборка команды или продукта, финал раздела.",
                   [Slide([head("Части в движении")] + st(1.0, -120), dur=800),
                    Slide([head("Всё сходится")] + st(0.0, 0), dur=900)],
                   tags=["tangram", "orbit", "spiral", "assemble"], score=4)


def v_pinwheel(theme):
    cx, cy, a = 8.6, 3.95, 1.5
    ink, bg = theme.c("ink"), theme.c("bg")
    tri = V.polygon([(cx, cy), (cx - a, cy - a), (cx + a, cy - a)])  # верхний треугольник квадрата
    cols = [theme.c("accent"), mix(ink, bg, 0.2), mix(ink, bg, 0.4), mix(ink, bg, 0.6)]
    R = 3.6
    names = ["План", "Делай", "Проверь", "Улучшай"]

    def st(spread, spin, open_):
        out = []
        for k in range(4):
            g = V.rotate(tri, 90 * k, origin=(cx, cy))
            ang = math.radians(-90 + 90 * k)
            g = V.move(g, math.cos(ang) * spread, math.sin(ang) * spread)
            if open_:  # каждый треугольник отклоняется вокруг своей вершины — «лопасть»
                g = V.rotate(g, 25, origin=(cx + math.cos(ang) * spread, cy + math.sin(ang) * spread))
            out.append(orbit(f"!!pw{k}", g, (cx, cy), R, spin, fill=cols[k], ln=bg, lw=1.5, z=10 + k))
        return out

    labs = [label(f"pl{k}", names[k], cx + 2.75 * math.cos(math.radians(-90 + 90 * k + 70)), cy + 2.5 * math.sin(math.radians(-90 + 90 * k + 70)),
                  w=1.8, sz=17, col="accent" if k == 0 else "ink2", b=k == 0) for k in range(4)]
    return Variant("tangram", "pinwheel", "Квадрат раскрывается вертушкой",
                   "Квадрат из четырёх треугольников расходится крестом, каждая часть отклоняется лопастью, и вся "
                   "вертушка проворачивается на 70° — цикл из четырёх шагов. Роль: циклический процесс (PDCA).",
                   [Slide([head("Один цикл")] + st(0, 0, False), dur=800),
                    Slide([head("Четыре шага")] + st(0.35, 0, True), dur=800),
                    Slide([head("Цикл идёт")] + st(0.35, 70, True) + labs, dur=900,
                          fx=[Fx("entrance_fade", l.name, start="at", delay=0.12 + 0.05 * k, dur=0.25) for k, l in enumerate(labs)])],
                   tags=["tangram", "pinwheel", "rotate", "cycle", "pivot"], score=3)


# ----------------------------------------------------------------------------- кубики-пиксели

HOUSE = ["...#...", "..###..", ".#####.", "#######", ".##.##.", ".##.##.", ".#####."]
ARROWPX = ["...#...", "..###..", ".#####.", "#######", "..###..", "..###..", "..###.."]


def px_cells(art, x0, y0, s):
    out = []
    for j, row in enumerate(art):
        for i, ch in enumerate(row):
            if ch == "#":
                out.append((x0 + i * s, y0 + j * s))
    return out


def blocks(theme, pos, s, fills, key="!!k", fa=None, z=10):
    return [put(f"{key}{i}", V.rect(0, 0, s - 0.05, s - 0.05, r=0.05), x, y, fill=fills[i], fa=(fa[i] if fa else 1.0), z=z + i)
            for i, (x, y) in enumerate(pos)]


def _assign(src, dst, n):
    """src, dst — списки (x, y); вернуть dst, переупорядоченный по src (минимальный путь); недостающие — в центр."""
    from lab._a_util import match
    from shapely.geometry import Point
    if len(dst) < n:
        c = (sum(p[0] for p in dst) / len(dst), sum(p[1] for p in dst) / len(dst))
        dst = dst + [c] * (n - len(dst))
    m = match([Point(p).buffer(0.01) for p in src], [Point(p).buffer(0.01) for p in dst[:n]])
    return [dst[m[i]] for i in range(n)], [m[i] >= len(dst) for i in range(n)]


def v_blocks(theme):
    s = 0.5
    house = px_cells(HOUSE, 7.2, 1.9, s)
    n = len(house)
    ink, bg = theme.c("ink"), theme.c("bg")
    rnd = random.Random(3)
    pile = [(rnd.uniform(1.0, 5.0), rnd.uniform(4.6, 6.2)) for _ in range(n)]
    # столбики
    hs = [4, 6, 8, n - 18]
    bars = []
    for k, h in enumerate(hs):
        for j in range(h):
            bars.append((7.0 + k * 1.4 + (j % 2) * s, 6.0 - (j // 2 + 1) * s))
    b_pos, _ = _assign(house, bars, n)
    tone = [mix(ink, bg, 0.25 + 0.3 * ((p[1] - 1.9) / 3.5)) for p in house]
    fills_b = [theme.c("accent") if b_pos[i][0] >= 7.0 + 3 * 1.4 - 0.01 else mix(ink, bg, 0.4) for i in range(n)]
    yl = [label(f"yb{k}", f"{2022 + k}", 7.0 + k * 1.4 + s, 6.3, w=1.2, sz=15, col="accent" if k == 3 else "ink2") for k in range(4)]
    return Variant("tangram", "blocks", "Кубики: куча → дом → столбики",
                   "Одинаковые кубики лежат кучей, собираются в пиктограмму дома (продукт), затем перестраиваются в "
                   "столбики по годам, последний — акцентом. Роль: «из чего сложен продукт и как он рос».",
                   [Slide([head("Кубики")] + blocks(theme, pile, s, tone), dur=800),
                    Slide([head("Продукт")] + blocks(theme, house, s, tone), dur=900),
                    Slide([head("Рост по годам")] + blocks(theme, b_pos, s, fills_b) + yl, dur=900,
                          fx=[Fx("entrance_fade", l.name, start="at", delay=0.12 + 0.04 * k, dur=0.25) for k, l in enumerate(yl)])],
                   tags=["tangram", "blocks", "pixel", "data", "icon"], score=4)


# ----------------------------------------------------------------------------- живые последовательности

def v_seq_argument(theme):
    """Танграм через доклад: квадрат-решение → разбор на 7 доводов → довод «Рынок» раскрывается в панель →
    фигуры складываются в стрелку → маркер на слабом звене → стрелка вверх → ступени роста → фон под тезис →
    квадрат с акцентом."""
    s = U * 1.15
    bg, ink = theme.c("bg"), theme.c("ink")
    pc = canon(s, 7.6 - 2 * K * s, 3.95 - 2 * K * s)
    cols = pcols(theme)
    args = {"T1": "Рынок", "T2": "Команда", "M": "Деньги", "S1": "Сроки", "Q": "Опыт", "S2": "Риски", "P": "Партнёры"}
    S = []
    p0 = ident(pc)
    S.append(Slide([head("Наше решение")] + draw(theme, pc, p0), dur=800))
    p1 = row_pose(pc, 0.9, 3.4, gap=0.42)
    labs = []
    for n in NAMES:
        th, dx, dy = p1[n]
        c = bbox_center(pc[n])
        labs.append(label(f"a1{n}", args[n], c[0] + dx, 5.2, w=1.6, sz=16, col="ink2"))
    S.append(Slide([head("Семь доводов")] + draw(theme, pc, p1) + labs, dur=900,
                   fx=[Fx("entrance_fade", l.name, start="at", delay=0.1 + 0.04 * k, dur=0.25) for k, l in enumerate(labs)]))
    # 2: довод «Рынок» (большой треугольник) переливается в панель; остальные — маленьким рядом сверху справа
    n_pts = 64
    objs2 = []
    small = row_pose({n: V.scale(pc[n], 0.45) for n in NAMES}, 7.6, 1.55, gap=0.2)
    for i, n in enumerate(NAMES):
        if n == "T1":
            continue
        th, dx, dy = small[n]
        g = V.scale(pc[n], 0.45)
        objs2.append(put(f"!!g{n}", g, dx, dy, rot=th, fill=cols[n], ln=bg, lw=1.0, z=10 + i))
    panel = V.resample(V.rect(0.8, 1.7, 6.0, 4.4, r=0.25), n_pts)
    tri = V.resample(pc["T1"], n_pts)
    pt = [O("p2a", "text", 1.2, 2.0, 5.2, 0.8, txt="Рынок", sz=34, b=True, col="on_accent", z=80),
          O("p2b", "text", 1.2, 2.9, 5.2, 1.4, txt=["Спрос растёт на 20 %", "в год три года подряд"], sz=20, col="on_accent", z=80)]
    # «Рынок» живёт как отдельная пара !!gT1v (переливаемый контур), пока квадратная фигура скрыта
    S[0].objs = [o for o in S[0].objs]
    S.append(Slide([head("Довод первый", x=7.6, y=2.4, w=5.0)] + objs2 + [V.shape("!!gT1", panel, fill="accent", z=30)] + pt, dur=900,
                   fx=[Fx("entrance_fade", "p2a", start="at", delay=0.12, dur=0.3), Fx("entrance_fade", "p2b", start="with", delay=0.05, dur=0.3)]))
    # чтобы панель переливалась из треугольника, на слайде 1 треугольник T1 — с тем же числом точек
    th, dx, dy = p1["T1"]
    for o_i, o in enumerate(S[1].objs):
        if o.name == "!!gT1":
            S[1].objs[o_i] = put("!!gT1", tri, dx, dy, rot=th, fill=cols["T1"], ln=bg, lw=1.5, z=10)
    # 3: стрелка
    p3 = place(pc, target(ARROW, s, 4.4, 4.0), prev=p1)

    def drawT(pose, hi=None, fa=None, lw=1.5, z=10, key="!!g"):
        out = draw(theme, pc, pose, hi=hi, fa=fa, lw=lw, z=z, key=key)
        for k, o in enumerate(out):
            if o.name == f"{key}T1":
                t, ddx, ddy = pose["T1"]
                out[k] = put(f"{key}T1", tri, ddx, ddy, rot=t, fill=theme.c("accent") if hi in ("T1", "all") else cols["T1"],
                             fa=(fa or {}).get("T1", 1.0), ln=bg, lw=lw, z=z)
        return out

    S.append(Slide([head("Куда это ведёт")] + drawT(p3, hi="T1"), dur=900))
    # 4: маркер — контур на слабом звене (параллелограмм «Партнёры»)
    th, dx, dy = p3["P"]
    mk = put("mk", pc["P"], dx, dy, s=1.0, rot=th, fill=None, ln=theme.c("accent"), lw=3.5, z=60)
    note = [label("wk", "Слабое звено — партнёры", 4.4 + 1.5 * s, 5.55, w=4.6, sz=18, col="accent", b=True)]
    S.append(Slide([head("Где риск"), mk] + drawT(p3, hi="T1", fa={n: (1.0 if n in ("P", "T1") else 0.4) for n in NAMES}) + note, dur=700,
                   fx=[Fx("entrance_faded_zoom", "mk", start="at", delay=0.1, dur=0.35), Fx("entrance_fade", "wk", start="after", dur=0.3)]))
    # 5: стрелка вверх
    c45, s45 = math.cos(math.radians(-45)), math.sin(math.radians(-45))
    up = {n: [(x * c45 - y * s45, x * s45 + y * c45) for x, y in pts] for n, pts in ARROW.items()}  # стрелка вверх-вправо
    p5 = place(pc, target(up, s, 7.4, 5.4), prev=p3)
    S.append(Slide([head("Рост"), sub("если закрыть риск", y=1.3)] + drawT(p5, hi="T1"), dur=900))
    # 6: ступени
    p6 = place(pc, target(STEPS, s, 5.0, 2.7), prev=p5, alt=target({"P": STEPS_P_ALT}, s, 5.0, 2.7))
    yl = [label("y0", "2025", 5.0 + 0.5 * s, 6.3, w=1.3, sz=16, col="ink2"), label("y1", "2026", 5.0 + 1.8 * s, 6.3, w=1.3, sz=16, col="ink2"),
          label("y2", "2027", 5.0 + 3.6 * s, 6.3, w=1.3, sz=16, col="accent", b=True)]
    S.append(Slide([head("Три ступени")] + drawT(p6, hi="T1") + yl, dur=900,
                   fx=[Fx("entrance_fade", l.name, start="at", delay=0.12 + 0.05 * k, dur=0.25) for k, l in enumerate(yl)]))
    # 7: фон — крупный бледный квадрат справа под тезисом
    big = canon(s * 2.2, 8.0 - 2 * K * s * 2.2 + 2.0, 3.9 - 2 * K * s * 2.2)
    p7 = {}
    for n in NAMES:
        c0, c1 = bbox_center(pc[n]), bbox_center(big[n])
        p7[n] = (0.0, c1[0] - c0[0], c1[1] - c0[1])
    bigobj = []
    for i, n in enumerate(NAMES):
        th, dx, dy = p7[n]
        g = pc[n] if n != "T1" else tri
        bigobj.append(put(f"!!g{n}", g, dx, dy, s=2.2, fill=cols[n] if n != "T1" else theme.c("accent"), fa=0.13, z=-50 + i))
    S.append(Slide([O("q7", "text", 0.8, 2.6, 7.2, 2.0, txt=["Решение складывается", "из тех же частей"], sz=40, b=True, col="ink", z=60)]
                   + bigobj, dur=900, fx=[Fx("entrance_fade", "q7", start="at", delay=0.12, dur=0.35)]))
    S.append(Slide([head("Наше решение")] + drawT(ident(pc), hi="T1"), dur=900))
    # слайд 0 — тот же треугольник T1 с 64 точками
    for o_i, o in enumerate(S[0].objs):
        if o.name == "!!gT1":
            S[0].objs[o_i] = put("!!gT1", tri, fill=cols["T1"], ln=bg, lw=1.5, z=10)
    return Variant("tangram", "seq_argument", "Танграм-аргумент через доклад",
                   "Семь фигур в 9 состояниях: квадрат-решение, ряд из семи доводов с подписями, довод «Рынок» "
                   "переливается в панель, фигуры складываются в стрелку, маркер на слабом звене, стрелка "
                   "поворачивается вверх, ступени роста по годам, крупный бледный квадрат под тезисом, сборка.",
                   S, tags=["seq", "tangram", "argument", "card", "arrow", "data", "background"], score=4)


def v_seq_blocks(theme):
    """Кубики через раздел: куча → дом → дом расслаивается на три уровня → столбики по годам → акцент на последнем
    → стрелка вверх → дом с акцентной дверью."""
    s = 0.5
    ink, bg = theme.c("ink"), theme.c("bg")
    house = px_cells(HOUSE, 7.6, 1.85, s)
    n = len(house)
    rnd = random.Random(8)
    pile = [(rnd.uniform(1.2, 5.5), rnd.uniform(4.4, 6.2)) for _ in range(n)]
    lvl = [0 if y < 1.85 + 2 * s - 0.01 else 1 if y < 1.85 + 4 * s - 0.01 else 2 for _, y in house]
    tone = [mix(ink, bg, [0.2, 0.38, 0.55][l]) for l in lvl]
    split = [(x + 0.0, y - [0.9, 0.45, 0.0][lvl[i]]) for i, (x, y) in enumerate(house)]
    lv_names = ["Крыша: бренд", "Стены: продукт", "Фундамент: данные"]
    lv_y = [1.45, 2.9, 4.6]
    lv_l = [label(f"lv{k}", lv_names[k], 5.4, lv_y[k], w=3.2, sz=17, col="ink2", al="r") for k in range(3)]
    lv_l = [l.copy(x=3.6) for l in lv_l]
    hs = [4, 6, 8, n - 18]
    bars = []
    for k, h in enumerate(hs):
        for j in range(h):
            bars.append((6.6 + k * 1.5 + (j % 2) * s, 6.1 - (j // 2 + 1) * s))
    b_pos, _ = _assign(house, bars, n)
    last_x = 6.6 + 3 * 1.5 - 0.01
    yl = [label(f"yb{k}", f"{2022 + k}", 6.6 + k * 1.5 + s, 6.4, w=1.2, sz=15, col="ink2") for k in range(4)]
    arrow = px_cells(ARROWPX, 7.6, 1.85, s)
    a_pos, hid = _assign(b_pos, arrow, n)
    S = []
    S.append(Slide([head("Из чего строим")] + blocks(theme, pile, s, [mix(ink, bg, 0.45)] * n), dur=800))
    S.append(Slide([head("Продукт")] + blocks(theme, house, s, tone), dur=900))
    S.append(Slide([head("Три уровня")] + blocks(theme, split, s, tone) + lv_l, dur=850,
                   fx=[Fx("entrance_fade", l.name, start="at", delay=0.12 + 0.05 * k, dur=0.25) for k, l in enumerate(lv_l)]))
    S.append(Slide([head("Рост по годам")] + blocks(theme, b_pos, s, tone) + yl, dur=900,
                   fx=[Fx("entrance_fade", l.name, start="at", delay=0.12 + 0.04 * k, dur=0.25) for k, l in enumerate(yl)]))
    f4 = [theme.c("accent") if b_pos[i][0] >= last_x else tone[i] for i in range(n)]
    S.append(Slide([head("2025 — рекорд")] + blocks(theme, b_pos, s, f4) + [l.copy(name=l.name + "c", col="accent" if k == 3 else "ink2")
                                                                           for k, l in enumerate(yl)], dur=600))
    fa5 = [0.0 if hid[i] else 1.0 for i in range(n)]
    S.append(Slide([head("Дальше — вверх")] + blocks(theme, a_pos, s, f4, fa=fa5), dur=900))
    door = [i for i, (x, y) in enumerate(house) if abs(x - (7.6 + 3 * s)) < 0.01 and y > 1.85 + 4 * s]
    f6 = [theme.c("accent") if i in door else tone[i] for i in range(n)]
    S.append(Slide([head("Добро пожаловать")] + blocks(theme, house, s, f6), dur=900))
    return Variant("tangram", "seq_blocks", "Кубики через раздел",
                   "Одинаковые кубики в 7 состояниях: куча, пиктограмма дома, дом расслаивается на три уровня с "
                   "подписями, кубики перестраиваются в столбики по годам, последний год — акцентом, столбики "
                   "складываются в стрелку вверх и возвращаются домом с акцентной дверью.",
                   S, tags=["seq", "tangram", "blocks", "pixel", "icon", "data"], score=4)


def variants(theme) -> list[Variant]:
    return [f(theme) for f in (v_seq_argument, v_seq_blocks, v_square_arrow, v_args, v_steps, v_missing, v_turn_up, v_lift3d,
                               v_orbit_build, v_pinwheel, v_blocks)]
