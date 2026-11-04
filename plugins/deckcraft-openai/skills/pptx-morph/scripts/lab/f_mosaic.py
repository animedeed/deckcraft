"""Семейство mosaic: мозаики Вороного, соты, треугольники, полярная сетка — перестраиваются (хаос → порядок),
раскрывают область, кластеризуются по цвету, приближают ячейку, становятся картой, теплокартой и 3D-столбиками.
Ячейка всегда одна и та же пара Morph: меняются её форма (равное число точек), место, цвет и высота.
"""

from __future__ import annotations

import math
import random

from shapely.geometry import Point, box

from morphkit import Cam, O, Slide
from morphkit import vector as V
from morphkit.presets import Fx
from morphkit.theme import mix

from lab import Variant
from lab._a_util import (arc_band, bar_band, blob, cells_exact, head, hex_cells, iso, label, lloyd, match, put, rand_points, sub,
                         sweep, tri_cells, voronoi_cells)

NC = 24  # точек на ячейку


def heat(theme, t: float) -> str:
    """Тёплая шкала от тихого тона к акценту (t 0..1)."""
    bg, acc = theme.c("bg"), theme.c("accent")  # один тон: от тёмного акцента к яркому (без грязного серо-рыжего)
    return mix(bg, acc, 0.16 + 0.84 * max(0.0, min(1.0, t)) ** 1.1)


def field(x, y, bumps=((9.2, 3.2, 1.3, 1.0), (6.0, 4.9, 1.1, 0.75), (10.6, 5.3, 0.8, 0.55))):
    return min(1.0, sum(a * math.exp(-((x - bx) ** 2 + (y - by) ** 2) / (2 * s * s)) for bx, by, s, a in bumps))


def cells(theme, geos, name="!!c", fills=None, fa=None, lw=1.0, z=10, ln=True):
    bg = theme.c("bg")
    out = []
    for i, g in enumerate(geos):
        out.append(V.shape(f"{name}{i}", g, fill=(fills[i] if fills else mix(theme.c("ink"), bg, 0.5)),
                           fa=(fa[i] if isinstance(fa, list) else (fa if fa is not None else 1.0)), ln=bg if ln else None, lw=lw if ln else 0,
                           z=z + i))
    return out


def on(theme, fill):
    from morphkit.theme import contrast
    f = theme.c(fill)
    a, b = theme.c("ink"), theme.c("bg")
    return a if contrast(a, f) >= contrast(b, f) else b


def R(g, n=NC):
    return V.resample(g, n)


# ----------------------------------------------------------------------------- одиночные

def v_relax(theme):
    reg = box(3.2, 1.7, 12.5, 6.6)
    n = 48
    pts = rand_points(n, reg, seed=4)
    bb = reg.bounds
    c0 = [R(c) for c in voronoi_cells(pts, bb)]
    p1 = lloyd(pts, bb, it=4)
    c1 = [R(c) for c in voronoi_cells(p1, bb)]
    hx = [g for _, g in hex_cells(0, 0, 0.56, cols=8, rows=6, x0=3.95, y0=2.25, gap=0.1)]
    perm = match(c1, hx)
    ink, bg = theme.c("ink"), theme.c("bg")
    rnd = random.Random(3)
    tone = [mix(ink, bg, rnd.uniform(0.35, 0.8)) for _ in range(n)]
    ordered = [mix(ink, bg, 0.75 - 0.5 * ((hx[perm[i]].centroid.x - 3.9) / 8.0)) for i in range(n)]
    return Variant("mosaic", "relax", "Хаос → порядок (Ллойд → соты)",
                   "Случайная мозаика Вороного расслабляется по Ллойду (ячейки выравниваются по размеру), затем каждая "
                   "ячейка переливается в соту, а тон выстраивается градиентом. Роль: «навели порядок в процессах», "
                   "раздел про стандартизацию.",
                   [Slide([head("Как было")] + cells(theme, c0, fills=tone), dur=800),
                    Slide([head("Выравниваем")] + cells(theme, c1, fills=tone), dur=900),
                    Slide([head("Как стало")] + cells(theme, [R(hx[perm[i]]) for i in range(n)], fills=ordered), dur=900)],
                   tags=["mosaic", "voronoi", "hex", "order", "shape-morph"], score=4)


def v_waffle(theme):
    reg = box(0.8, 1.8, 6.6, 6.6)
    n = 60
    pts = lloyd(rand_points(n, reg, seed=9), reg.bounds, it=2)
    vc = [R(c) for c in voronoi_cells(pts, reg.bounds)]
    rnd = random.Random(11)
    cat = [0] * 27 + [1] * 21 + [2] * 12
    rnd.shuffle(cat)
    ink, bg = theme.c("ink"), theme.c("bg")
    cols3 = [theme.c("accent"), mix(ink, bg, 0.25), mix(ink, bg, 0.55)]
    fills = [cols3[c] for c in cat]
    # вафля 10×6, отсортированная по категориям
    order = sorted(range(n), key=lambda i: cat[i])
    s, g0 = 0.42, 0.08
    waffle = [None] * n
    for pos, i in enumerate(order):
        waffle[i] = R(V.rect(7.2 + (pos % 10) * (s + g0) - 0.0, 2.0 + (pos // 10) * (s + g0), s, s, r=0.05))
    # три столбика из клеток
    bars = [None] * n
    cnt = [0, 0, 0]
    for i in order:
        c = cat[i]
        k = cnt[c]
        cnt[c] += 1
        bars[i] = R(V.rect(2.0 + c * 3.3 + (k % 3) * (s + g0), 6.2 - (k // 3 + 1) * (s + g0), s, s, r=0.05))
    names = ["Рост · 27", "Плато · 21", "Спад · 12"]
    labs = [label(f"wl{k}", names[k], 2.67 + k * 3.3, 6.55, w=2.6, sz=17, col="accent" if k == 0 else "ink2", b=k == 0) for k in range(3)]
    return Variant("mosaic", "waffle", "Мозаика → вафля → столбики",
                   "Шестьдесят ячеек-клиентов вперемешку; каждая переливается в клетку вафли, отсортированной по "
                   "категориям, затем клетки собираются в три столбика. Роль: «из пёстрой картины — счёт по группам».",
                   [Slide([head("Шестьдесят клиентов")] + cells(theme, vc, fills=fills), dur=800),
                    Slide([head("Сортируем")] + cells(theme, waffle, fills=fills, ln=False), dur=900),
                    Slide([head("Три группы")] + cells(theme, bars, fills=fills, ln=False) + labs, dur=900,
                          fx=[Fx("entrance_fade", l.name, start="at", delay=0.1 + 0.05 * k, dur=0.3) for k, l in enumerate(labs)])],
                   tags=["mosaic", "voronoi", "waffle", "data", "sort", "shape-morph"], score=5)


def v_hex_reveal(theme):
    hx = hex_cells(0, 0, 0.5, cols=16, rows=9, x0=0.2, y0=0.35, gap=0.06)
    ink, bg = theme.c("ink"), theme.c("bg")
    tone = mix(ink, bg, 0.82)

    def st(cx, cy, rad):
        out = []
        for i, ((x, y), g) in enumerate(hx):
            d = math.hypot(x - cx, y - cy)
            s = 1.0 if d > rad + 0.9 else max(0.02, (d - rad) / 0.9) if d > rad else 0.02
            out.append(put(f"!!h{i}", g, s=s, fill=tone, z=20 + i // 40))
        return out

    t1 = [O("r1", "text", 3.4, 2.9, 5.0, 0.8, txt="Главная мысль", sz=34, b=True, col="accent", al="c", z=1),
          O("r1b", "text", 3.4, 3.7, 5.0, 0.6, txt="прячется под шумом", sz=20, col="ink2", al="c", z=1)]
    t2 = [O("r2", "text", 7.4, 4.3, 4.8, 0.8, txt="Вторая мысль", sz=34, b=True, col="accent", al="c", z=1),
          O("r2b", "text", 7.4, 5.1, 4.8, 0.6, txt="рядом, но не сразу", sz=20, col="ink2", al="c", z=1)]
    return Variant("mosaic", "hex_reveal", "Соты расступаются",
                   "Слайд закрыт сотами; соты в круге сжимаются в точки с мягким краем, открывая мысль под ними, "
                   "затем «окно» переезжает к следующей мысли — прожектор из мозаики. Роль: акцент, раскрытие по шагам.",
                   [Slide(st(-5, -5, 0.0), dur=800),
                    Slide(st(5.9, 3.55, 1.9) + t1, dur=900),
                    Slide(st(9.8, 4.95, 1.9) + t2, dur=900)],
                   tags=["mosaic", "hex", "reveal", "spotlight", "background"], score=4)


def _hexmap(r=0.36):
    shape = blob(8.0, 4.0, 2.75, amps=(0.1, 0.09, 0.05), phase=0.7, sx=1.45, sy=0.95)
    hx = [(c, g) for c, g in hex_cells(0, 0, r, cols=30, rows=16, x0=3.5, y0=0.9, gap=0.06) if shape.contains(Point(c))]
    return hx


def v_heat3d(theme):
    hx = _hexmap()
    ink, bg = theme.c("ink"), theme.c("bg")
    vals = [field(*c) for c, _ in hx]
    org = (8.0, 4.4)
    order = sorted(range(len(hx)), key=lambda i: hx[i][0][1])

    def st(mode):
        out = []
        for zi, i in enumerate(order):
            (c, g) = hx[i]
            v = vals[i]
            col = mix(ink, bg, 0.7) if mode == 0 else heat(theme, v)
            if mode < 2:
                top, side = (g, g) if mode == 0 else (iso(g, org, 0.55, 0), iso(g, org, 0.55, 0))
            else:
                gi = iso(g, org, 0.55, 0)
                h = 1.6 * v
                top, side = V.move(gi, 0, -h), sweep(gi, h)
            out.append(V.shape(f"!!w{i}", R(side), fill=mix(col, bg, 0.45), z=10 + 2 * zi))
            out.append(V.shape(f"!!t{i}", R(top), fill=col, ln=bg, lw=0.6, z=11 + 2 * zi))
        return out

    lab_ = label("hl", "Спрос выше всего на востоке", 10.3, 1.2, w=4.6, sz=18, col="accent", b=True)
    return Variant("mosaic", "heat3d", "Сотовая карта → теплокарта → 3D",
                   f"Карта из {len(hx)} сот: серая → раскрашена по спросу и наклонена → каждая сота вырастает призмой "
                   "высотой со значение. Имитация 3D-карты из 2D. Роль: география данных, кульминация анализа.",
                   [Slide([head("Карта регионов")] + st(0), dur=800),
                    Slide([head("Спрос по регионам")] + st(1), dur=900),
                    Slide([head("Где пики"), lab_] + st(2), dur=900, fx=[Fx("entrance_fade", "hl", start="at", delay=0.15, dur=0.3)])],
                   tags=["mosaic", "hex", "map", "heatmap", "3d", "iso", "data"], score=5)


def v_zoom_cell(theme):
    reg = box(-1.0, -1.0, 14.3, 8.5)
    pts = lloyd(rand_points(70, reg, seed=14), reg.bounds, it=2)
    cs = voronoi_cells(pts, reg.bounds)
    ink, bg = theme.c("ink"), theme.c("bg")
    rnd = random.Random(2)
    tone = [mix(ink, bg, rnd.uniform(0.62, 0.85)) for _ in cs]
    tgt = min(range(len(cs)), key=lambda i: math.dist((cs[i].centroid.x, cs[i].centroid.y), (8.6, 4.2)))
    tc = cs[tgt].centroid
    fills = list(tone)
    fills2 = list(tone)
    fills2[tgt] = theme.c("accent")

    def st(f):  # прозрачность 0,88: мозаика — фон (подписи поверх проверяются по фону слайда)
        return [V.shape(f"!!z{i}", g, fill=f[i], fa=1.0 if i == tgt else 0.88, ln=bg, lw=1.5, z=10 + i, world=True, meta={"bleed": True})
                for i, g in enumerate(cs)]

    t = [O("zt", "text", 4.4, 3.0, 4.6, 0.8, txt="Один клиент", sz=30, b=True, col="on_accent", al="c", z=200),
         O("zb", "text", 4.4, 3.8, 4.6, 0.6, txt="и его история", sz=20, col="on_accent", al="c", z=200)]
    return Variant("mosaic", "zoom_cell", "Камера ныряет в ячейку",
                   "Мозаика из 70 ячеек на весь слайд; одна ячейка загорается акцентом, камера приближается к ней в 5 раз, "
                   "и ячейка становится панелью с текстом, соседи — рамкой вокруг. Роль: от общего к частному, кейс.",
                   [Slide([head("Тысячи клиентов")] + st(fills), cam=Cam(), dur=800),
                    Slide([head("Тысячи клиентов")] + st(fills2), cam=Cam(), dur=500),
                    Slide(st(fills2) + t, cam=Cam(tc.x, tc.y, 4.0), dur=900,
                          fx=[Fx("entrance_fade", "zt", start="at", delay=0.12, dur=0.3), Fx("entrance_fade", "zb", start="with", delay=0.05, dur=0.3)])],
                   tags=["mosaic", "voronoi", "camera", "zoom", "space"], score=4)


def v_tri_arrow(theme):
    s = 0.62
    tri = tri_cells(1.0, 0.8, s, 34, 12, gap=0.05)
    hexagon = V.regular(4.4, 4.0, 2.4, 6, start=0)
    arrow = V.polygon([(6.4, 3.3), (9.8, 3.3), (9.8, 1.9), (12.6, 4.15), (9.8, 6.4), (9.8, 5.0), (6.4, 5.0)])
    A = [g for _, g in tri if hexagon.contains(g.centroid)]
    B = [g for _, g in tri if arrow.contains(g.centroid)]
    n = min(len(A), len(B))
    A, B = A[:n] if len(A) >= n else A, B
    perm = match(A, B[:len(A)]) if len(B) >= len(A) else None
    ink, bg = theme.c("ink"), theme.c("bg")
    rnd = random.Random(1)
    tone = [mix(ink, bg, rnd.uniform(0.25, 0.65)) for _ in A]

    def st(mode):
        out = []
        for i, g in enumerate(A):
            if mode == 0:
                out.append(put(f"!!tr{i}", g, fill=tone[i], z=10 + i))
            else:
                q = B[perm[i]]
                out.append(put(f"!!tr{i}", g, q.centroid.x - g.centroid.x, q.centroid.y - g.centroid.y,
                               rot=0 if abs(q.bounds[1] - g.bounds[1] - (q.centroid.y - g.centroid.y)) < 0.05 else 180 if False else 0,
                               fill=theme.c("accent") if q.centroid.x > 9.9 else tone[i], z=10 + i))
        return out

    def st_arrow():
        from lab._a_util import fit_rot
        out = []
        for i, g in enumerate(A):
            q = B[perm[i]]
            th, dx, dy = fit_rot(g, q, prefer=0.0, step=60.0)
            out.append(put(f"!!tr{i}", g, dx, dy, rot=th, fill=theme.c("accent") if q.centroid.x > 9.9 else tone[i], z=10 + i))
        return out

    extra = [put(f"tx{j}", q, fill=mix(ink, bg, 0.7), z=5) for j, q in enumerate(B) if j not in set(perm)]
    return Variant("mosaic", "tri_arrow", "Треугольники перестраиваются в стрелку",
                   f"{len(A)} треугольников мозаики собраны в шестиугольник «как есть»; каждый перелетает в свою клетку "
                   "той же решётки внутри стрелки (треугольник, смотрящий не туда, доворачивается на 60°), остриё — "
                   "акцентом. Роль: «из того же материала — новое направление», стратегия.",
                   [Slide([head("Ресурсы сейчас")] + st(0), dur=800),
                    Slide([head("Те же ресурсы — в направление")] + st_arrow() + extra, dur=900,
                          fx=[Fx("entrance_fade", e.name, start="at", delay=0.2, dur=0.3) for e in extra])],
                   tags=["mosaic", "triangle", "rebuild", "arrow", "strategy"], score=4)


def v_plates(theme):
    reg = box(0.9, 1.7, 12.4, 6.7)
    n = 64
    pts = lloyd(rand_points(n, reg, seed=17), reg.bounds, it=2)
    cs = [R(c) for c in voronoi_cells(pts, reg.bounds)]
    ink, bg = theme.c("ink"), theme.c("bg")

    def side(p):  # линия разлома — кривая
        x, y = p
        return x - (6.7 + 0.8 * math.sin((y - 1.7) * 1.1))

    sd = [side((c.centroid.x, c.centroid.y)) for c in cs]
    rnd = random.Random(8)
    tone = [mix(ink, bg, rnd.uniform(0.5, 0.75)) for _ in cs]

    def st(d, lit=False):
        out = []
        for i, g in enumerate(cs):
            dx = -d if sd[i] < 0 else d
            f = (theme.c("accent") if (lit and sd[i] >= 0 and rnd.random() < 2) else tone[i]) if lit and sd[i] >= 0 else tone[i]
            if lit and sd[i] >= 0:
                f = heat(theme, 0.35 + 0.65 * (g.centroid.x - 7) / 5.5)
            out.append(put(f"!!p{i}", g, dx, 0.25 * d * (1 if sd[i] < 0 else -1), s=0.96 if d else 1.0, fill=f, ln=bg, lw=1.0, z=10 + i))
        return out

    l1 = [label("pa", "Старый рынок", 2.4, 1.35, w=3.0, sz=17, col="ink2"), label("pb", "Новый рынок", 10.9, 1.35, w=3.0, sz=17, col="accent", b=True)]
    return Variant("mosaic", "plates", "Мозаика раскалывается на два материка",
                   "Сплошная мозаика расходится по кривой линии разлома, как тектонические плиты; правая плита "
                   "раскрашивается теплом. Роль: раскол рынка, «старое и новое», смена эпохи.",
                   [Slide([head("Один рынок")] + st(0), dur=800),
                    Slide([head("Разлом")] + st(0.65), dur=900),
                    Slide([head("Два рынка")] + st(0.65, lit=True) + l1, dur=700,
                          fx=[Fx("entrance_fade", l.name, start="at", delay=0.12, dur=0.3) for l in l1])],
                   tags=["mosaic", "voronoi", "split", "space"], score=3)


def v_bubbles(theme):
    reg = blob(6.2, 4.1, 2.6, amps=(0.12, 0.08, 0.04), phase=1.4, sx=1.3, sy=0.95)
    n = 30
    pts = lloyd(rand_points(n, reg, seed=5), reg.bounds, it=3, clip=reg)
    cs = [c.intersection(reg) for c in voronoi_cells(pts, (0, 0, 13.3, 7.5))]
    cs = [max(getattr(c, "geoms", [c]), key=lambda q: q.area) for c in cs]
    rnd = random.Random(4)
    vals = [rnd.uniform(0.05, 1.0) ** 1.6 for _ in cs]
    ink, bg = theme.c("ink"), theme.c("bg")
    fills = [heat(theme, v) for v in vals]
    rad = [0.12 + 0.48 * math.sqrt(v) for v in vals]
    rank = sorted(range(n), key=lambda i: -vals[i])
    row = [None] * n
    k_fit = min(1.0, 11.4 / sum(2 * rad[i] + 0.12 for i in rank[:12]))
    for i in rank[:12]:
        rad[i] = rad[i]  # размер на карте
    x = 0.9
    rrow = {}
    for pos, i in enumerate(rank[:12]):
        rr = rad[i] * k_fit
        rrow[i] = rr
        row[i] = (x + rr, 5.4 - rr)
        x += 2 * rr + 0.12 * k_fit
    for pos, i in enumerate(rank[12:]):
        row[i] = (0.9 + pos * 0.2 + 0.1, 6.35)

    def st(mode):
        out = []
        for i, c in enumerate(cs):
            if mode == 0:
                g = R(c)
            elif mode == 1:
                g = R(V.circle(c.centroid.x, c.centroid.y, rad[i]))
            else:
                r = rrow[i] if i in rank[:12] else 0.07
                g = R(V.circle(row[i][0], row[i][1], r))
            out.append(V.shape(f"!!b{i}", g, fill=fills[i], ln=bg, lw=1.0, z=10 + i))
        return out

    t = [label("bt", "12 крупнейших", 1.8, 2.3, w=3.0, sz=18, col="accent", b=True, al="l")]
    return Variant("mosaic", "bubbles", "Карта → пузыри → рейтинг",
                   "Районы-ячейки на карте переливаются в круги с площадью по значению (картограмма Дорлинга) на своих "
                   "местах, затем крупнейшие встают в ряд по убыванию, остальные — в тонкую строку. Роль: данные по "
                   "территориям, от карты к рейтингу.",
                   [Slide([head("Тридцать районов")] + st(0), dur=800),
                    Slide([head("Размер — продажи")] + st(1), dur=900),
                    Slide([head("Рейтинг районов")] + st(2) + t, dur=900, fx=[Fx("entrance_fade", "bt", start="at", delay=0.12, dur=0.3)])],
                   tags=["mosaic", "voronoi", "map", "bubbles", "data", "sort"], score=4)


def v_polar_table(theme):
    cx, cy = 8.8, 4.0
    months = ["Я", "Ф", "М", "А", "М", "И", "И", "А", "С", "О", "Н", "Д"]
    rows = 3
    ink, bg = theme.c("ink"), theme.c("bg")
    rnd = random.Random(6)
    vals = [[0.3 + 0.6 * (0.5 + 0.5 * math.sin((m - 2 + r) / 12 * 2 * math.pi)) * rnd.uniform(0.7, 1.0) for m in range(12)] for r in range(rows)]

    def st(mode):
        out = []
        for r in range(rows):
            for m in range(12):
                if mode == 0:
                    ri = 1.0 + r * 0.72
                    g = arc_band(cx, cy, ri, ri + 0.64, -90 + m * 30 + 1.2, -90 + (m + 1) * 30 - 1.2, m=10, cap=2)
                else:
                    g = bar_band(1.4 + m * 0.92, 2.6 + (2 - r) * 0.92, 0.84, 0.84, m=10, cap=2)
                out.append(V.shape(f"!!pc{r}_{m}", g, fill=heat(theme, vals[r][m]), z=10 + r * 12 + m))
        return out

    ml = [label(f"m{m}", months[m], 1.82 + m * 0.92, 5.6, w=0.7, sz=14, col="ink2") for m in range(12)]
    yl = [label(f"y{r}", f"{2022 + r}", 0.75, 2.6 + (2 - r) * 0.92 + 0.42, w=0.9, sz=14, col="ink2", al="l") for r in range(rows)]
    yl = [l.copy(x=0.35) for l in yl]
    return Variant("mosaic", "polar_table", "Кольцевая мозаика → таблица",
                   "Три года по месяцам — кольцевая теплокарта (как часы года); каждая ячейка-дуга распрямляется в "
                   "квадрат календаря. Порядок точек согласован, поэтому дуги «разгибаются», а не переливаются кашей. "
                   "Роль: сезонность, переход от образа к точным данным.",
                   [Slide([head("Сезонность продаж")] + st(0), dur=800),
                    Slide([head("Те же месяцы — таблицей")] + st(1) + ml + yl, dur=900,
                          fx=[Fx("entrance_fade", l.name, start="at", delay=0.15, dur=0.3) for l in ml + yl])],
                   tags=["mosaic", "polar", "unroll", "heatmap", "data"], score=4)


def v_iso_blocks(theme):
    cols, rows, s = 8, 5, 0.62
    x0, y0 = 4.8, 2.0
    ink, bg = theme.c("ink"), theme.c("bg")
    org = (x0 + cols * s / 2, y0 + rows * s / 2)
    rnd = random.Random(12)
    vals = [[max(0.05, field(5 + i * 0.75, 2.5 + j * 0.7, ((9.5, 3.2, 1.4, 1.0), (6.0, 5.2, 1.2, 0.6))) + rnd.uniform(-0.05, 0.05))
             for i in range(cols)] for j in range(rows)]
    order = sorted([(i, j) for i in range(cols) for j in range(rows)], key=lambda t: (t[0] - t[1], t[1]))

    def st(mode):
        out = []
        for zi, (i, j) in enumerate(sorted([(i, j) for i in range(cols) for j in range(rows)], key=lambda t: (t[0] + t[1]))):
            sq = V.rect(x0 + i * s, y0 + j * s, s - 0.06, s - 0.06)
            v = vals[j][i]
            col = mix(ink, bg, 0.6) if mode == 0 else heat(theme, v)
            if mode == 0:
                top = side = sq
            else:
                gi = iso(sq, org, 0.55, 45)
                h = 0.0 if mode == 1 else 2.2 * v
                top, side = V.move(gi, 0, -h), sweep(gi, h)
            out.append(V.shape(f"!!kw{i}_{j}", R(side), fill=mix(col, bg, 0.45), z=10 + 2 * zi))
            out.append(V.shape(f"!!kt{i}_{j}", R(top), fill=col, ln=bg, lw=0.6, z=11 + 2 * zi))
        return out

    return Variant("mosaic", "iso_blocks", "Пиксельная таблица → 3D-столбики",
                   "Таблица 8×5 из квадратов раскрашивается, поворачивается в изометрию на 45° и вырастает столбиками "
                   "высотой со значение — «город» данных. Имитация 3D из 2D. Роль: матрица двух признаков, обложка "
                   "раздела аналитики.",
                   [Slide([head("Матрица 8 × 5")] + st(0), dur=800),
                    Slide([head("Повернём")] + st(1), dur=900),
                    Slide([head("Высота — значение")] + st(2), dur=900)],
                   tags=["mosaic", "grid", "3d", "iso", "data"], score=4)


def v_cluster(theme):
    reg = box(3.0, 1.7, 12.6, 6.6)
    n = 56
    rnd = random.Random(21)
    pts = lloyd(rand_points(n, reg, seed=22), reg.bounds, it=1)
    cat = [i % 4 for i in range(n)]
    rnd.shuffle(cat)
    ink, bg = theme.c("ink"), theme.c("bg")
    cols4 = [theme.c("accent"), mix(ink, bg, 0.15), mix(ink, bg, 0.4), mix(ink, bg, 0.65)]
    c0 = voronoi_cells(pts, reg.bounds)
    # новые затравки: каждая категория — в своём квадранте, точки категории расставлены Ллойдом внутри него
    quads = [box(3.0, 1.7, 7.8, 4.15), box(7.8, 1.7, 12.6, 4.15), box(3.0, 4.15, 7.8, 6.6), box(7.8, 4.15, 12.6, 6.6)]
    pts2 = [None] * n
    for q in range(4):
        idx = [i for i in range(n) if cat[i] == q]
        qp = lloyd(rand_points(len(idx), quads[q], seed=30 + q), quads[q].bounds, it=3)
        m = match([Point(pts[i]).buffer(0.01) for i in idx], [Point(p).buffer(0.01) for p in qp], norm=False)
        for k, i in enumerate(idx):
            pts2[i] = qp[m[k]]
    c1 = voronoi_cells(pts2, reg.bounds)
    fills = [cols4[c] for c in cat]
    labs = [label(f"cq{q}", t, quads[q].centroid.x, quads[q].centroid.y, w=2.6, sz=20, b=True,
                  col=on(theme, cols4[q]))
            for q, t in enumerate(["Сегмент А", "Сегмент Б", "Сегмент В", "Сегмент Г"])]
    return Variant("mosaic", "cluster", "Ячейки сходятся в кластеры",
                   "Пёстрая мозаика, где цвета вперемешку; каждая ячейка меняет форму и место, и мозаика "
                   "перестраивается так, что одинаковые цвета образуют четыре сплошные области. Роль: сегментация, "
                   "«нашли закономерность».",
                   [Slide([head("Все вперемешку")] + cells(theme, [R(c) for c in c0], fills=fills), dur=800),
                    Slide([head("Четыре сегмента")] + cells(theme, [R(c) for c in c1], fills=fills) + labs, dur=900,
                          fx=[Fx("entrance_fade", l.name, start="at", delay=0.15 + 0.05 * k, dur=0.3) for k, l in enumerate(labs)])],
                   tags=["mosaic", "voronoi", "cluster", "data", "shape-morph"], score=4)


# ----------------------------------------------------------------------------- живые последовательности

def v_seq_map(theme):
    """Сотовая карта живёт 8 состояний: серая карта → теплокарта → наклон и призмы → горячие соты взлетают в
    отдельный улей → улей встаёт рейтингом → карта с прожектором региона → карта уходит в фон → соты становятся
    вафельными столбиками → снова карта."""
    hx = _hexmap(0.38)
    n = len(hx)
    ink, bg = theme.c("ink"), theme.c("bg")
    vals = [field(*c) for c, _ in hx]
    org = (8.0, 4.4)
    yorder = sorted(range(n), key=lambda i: hx[i][0][1])
    zrank = {i: k for k, i in enumerate(yorder)}
    hot = sorted(range(n), key=lambda i: -vals[i])[:7]
    cities = ["Казань", "Пермь", "Уфа", "Самара", "Ижевск", "Киров", "Чебоксары"]

    def objs(top, side=None, fills=None, fa=None, lw=0.6, z0=10):
        out = []
        for i in range(n):
            f = fills[i] if fills else mix(ink, bg, 0.7)
            a = fa[i] if isinstance(fa, list) else (fa if fa is not None else 1.0)
            sd = side[i] if side else top[i]
            out.append(V.shape(f"!!w{i}", R(sd), fill=mix(f, bg, 0.45), fa=a if side else 0.0, z=z0 + 2 * zrank[i]))
            out.append(V.shape(f"!!t{i}", R(top[i]), fill=f, fa=a, ln=bg, lw=lw, z=z0 + 1 + 2 * zrank[i]))
        return out

    flat = [g for _, g in hx]
    heatf = [heat(theme, v) for v in vals]
    S = []
    S.append(Slide([head("Сеть: регионы")] + objs(flat), dur=800))
    S.append(Slide([head("Спрос по регионам")] + objs(flat, fills=heatf), dur=700))
    tilt = [iso(g, org, 0.55, 0) for g in flat]
    top3 = [V.move(t, 0, -1.5 * v) for t, v in zip(tilt, vals)]
    side3 = [sweep(t, 1.5 * v) for t, v in zip(tilt, vals)]
    S.append(Slide([head("Где пики")] + objs(top3, side3, fills=heatf), dur=900))
    # 3: горячие соты взлетают в отдельный «улей» справа-сверху, карта плоская и сдвинута влево
    hive = [g for _, g in hex_cells(10.6, 3.6, 0.62, rings=1, gap=0.08)]
    shift = [V.move(V.scale(g, 0.8, origin=(8.0, 4.0)), -2.6, 0.5) for g in flat]
    t4 = list(shift)
    for k, i in enumerate(hot):
        t4[i] = hive[k]
    f4 = [heatf[i] if i in hot else mix(ink, bg, 0.72) for i in range(n)]
    S.append(Slide([head("Семь горячих регионов"), label("hv", "дают 40 % спроса", 10.6, 5.65, w=3.4, sz=18, col="accent", b=True)]
                   + objs(t4, fills=f4), dur=900, fx=[Fx("entrance_fade", "hv", start="at", delay=0.15, dur=0.3)]))
    # 4: улей встаёт рейтингом (соты-значки с названиями)
    t5 = list(shift)
    rk = []
    for k, i in enumerate(hot):
        y = 1.75 + k * 0.72
        t5[i] = V.regular(9.0, y + 0.3, 0.32, 6)
        rk.append(label(f"rk{k}", f"{cities[k]}", 9.55, y + 0.3, w=2.6, sz=17, col="accent" if k == 0 else "ink2", al="l", b=k == 0))
    S.append(Slide([head("Рейтинг регионов")] + objs(t5, fills=f4) + rk, dur=850,
                   fx=[Fx("entrance_fade", l.name, start="at", delay=0.1 + 0.04 * k, dur=0.25) for k, l in enumerate(rk)]))
    # 5: прожектор на регион — карта на месте, остальные приглушены, выбранный обведён
    sel = hot[0]
    nb = [i for i in range(n) if math.dist(hx[i][0], hx[sel][0]) < 1.6]
    fa6 = [1.0 if i in nb else 0.25 for i in range(n)]
    t6 = flat
    mk = V.shape("mk", V.scale(flat[sel], 1.25), fill=None, ln="accent", lw=3, z=400)
    S.append(Slide([head("Казань и соседи"), mk] + objs(t6, fills=heatf, fa=fa6), dur=900,
                   fx=[Fx("entrance_faded_zoom", "mk", start="at", delay=0.15, dur=0.35)]))
    # 6: карта уходит в фон под тезис
    t7 = [V.move(V.scale(g, 1.6, origin=(8.0, 4.0)), 1.6, 0.4) for g in flat]
    S.append(Slide([O("q7", "text", 0.8, 2.6, 7.0, 2.0, txt=["Спрос рождается", "в городах-миллионниках"], sz=40, b=True, col="ink", z=600)]
                   + objs(t7, fills=heatf, fa=0.14, lw=0, z0=-400), dur=900, fx=[Fx("entrance_fade", "q7", start="at", delay=0.12, dur=0.35)]))
    # 7: соты -> вафельные столбики по уровню спроса
    lvl = [0 if v > 0.6 else 1 if v > 0.3 else 2 for v in vals]
    cnt = [0, 0, 0]
    t8 = [None] * n
    for i in sorted(range(n), key=lambda i: -vals[i]):
        L = lvl[i]
        k = cnt[L]
        cnt[L] += 1
        cc = 6
        t8[i] = V.regular(2.2 + L * 3.6 + (k % cc) * 0.42 + (0.21 if (k // cc) % 2 else 0), 6.0 - (k // cc) * 0.37, 0.22, 6)
    names = ["Высокий", "Средний", "Низкий"]
    l8 = [label(f"l8{k}", f"{names[k]} · {cnt[k]}", 3.25 + k * 3.6, 6.55, w=2.8, sz=17, col="accent" if k == 0 else "ink2", b=k == 0)
          for k in range(3)]
    S.append(Slide([head("Сколько регионов какого уровня")] + objs(t8, fills=heatf, lw=0) + l8, dur=900,
                   fx=[Fx("entrance_fade", l.name, start="at", delay=0.12 + 0.05 * k, dur=0.25) for k, l in enumerate(l8)]))
    S.append(Slide([head("Карта целиком")] + objs(flat, fills=heatf), dur=900))
    return Variant("mosaic", "seq_map", "Сотовая карта через весь раздел",
                   "Одна сотовая карта в 9 состояниях: серая, теплокарта, наклон с призмами, горячие соты взлетают "
                   "в отдельный «улей», улей становится рейтингом с названиями, прожектор на регион с соседями, карта "
                   "уходит в фон под тезис, соты ссыпаются в столбики по уровню и возвращаются на карту.",
                   S, tags=["seq", "mosaic", "hex", "map", "3d", "data", "spotlight", "background"], score=5)


def v_seq_team(theme):
    """Мозаика организации: хаос задач → окрашено по командам → кластеры команд → ровные соты →
    одна команда раскрывается в панель → клетки-люди в столбики → снова мозаика."""
    reg = box(3.4, 1.7, 12.6, 6.6)
    n = 48
    ink, bg = theme.c("ink"), theme.c("bg")
    pts = rand_points(n, reg, seed=41)
    c0 = voronoi_cells(pts, reg.bounds)
    cat = [0] * 15 + [1] * 13 + [2] * 11 + [3] * 9
    random.Random(5).shuffle(cat)
    cols4 = [theme.c("accent"), mix(ink, bg, 0.15), mix(ink, bg, 0.4), mix(ink, bg, 0.62)]
    fills = [cols4[c] for c in cat]
    teams = ["Данные", "Продукт", "Продажи", "Сервис"]
    # кластеры: вертикальные полосы-территории по командам (ширина ~ размеру команды)
    widths = [15, 13, 11, 9]
    xs = [3.4]
    for w in widths:
        xs.append(xs[-1] + (12.6 - 3.4) * w / 48)
    pts2 = [None] * n
    for q in range(4):
        idx = [i for i in range(n) if cat[i] == q]
        zone = box(xs[q], 1.7, xs[q + 1], 6.6)
        qp = lloyd(rand_points(len(idx), zone, seed=50 + q), zone.bounds, it=3)
        m = match([Point(pts[i]).buffer(0.01) for i in idx], [Point(p).buffer(0.01) for p in qp], norm=False)
        for k, i in enumerate(idx):
            pts2[i] = qp[m[k]]
    c1 = voronoi_cells(pts2, reg.bounds)
    # соты: те же территории в виде ровной сетки 12×4, столбцы по командам
    hx = [g for _, g in hex_cells(0, 0, 0.47, cols=12, rows=4, x0=4.1, y0=2.6, gap=0.08)]
    hx.sort(key=lambda g: (round(g.centroid.x, 1), g.centroid.y))
    order = sorted(range(n), key=lambda i: (cat[i], pts2[i][0], pts2[i][1]))
    c2 = [None] * n
    for pos, i in enumerate(order):
        c2[i] = hx[pos]
    S = []
    S.append(Slide([head("Сорок восемь задач")] + cells(theme, [R(c) for c in c0]), dur=800))
    S.append(Slide([head("У каждой — своя команда")] + cells(theme, [R(c) for c in c0], fills=fills), dur=700))
    lab1 = [label(f"t{q}", teams[q], (xs[q] + xs[q + 1]) / 2, 1.35, w=2.4, sz=16, b=True, col="accent" if q == 0 else "ink2") for q in range(4)]
    S.append(Slide([head("Команды как территории", x=0.7, w=5.5, sz=26)] + cells(theme, [R(c) for c in c1], fills=fills) + lab1, dur=900,
                   fx=[Fx("entrance_fade", l.name, start="at", delay=0.12 + 0.04 * k, dur=0.25) for k, l in enumerate(lab1)]))
    S.append(Slide([head("Ровная структура")] + cells(theme, [R(c) for c in c2], fills=fills, ln=False), dur=900))
    # 4: команда «Данные» раскрывается в панель из своих клеток
    idx0 = [i for i in range(n) if cat[i] == 0]
    panel = V.rect(0.8, 1.7, 5.6, 4.6, r=0.25)
    pc = cells_exact(panel, len(idx0), seed=7)
    pm = match([c2[i] for i in idx0], pc)
    c3 = list(c2)
    for k, i in enumerate(idx0):
        c3[i] = pc[pm[k]]
    for i in range(n):
        if cat[i] != 0:
            c3[i] = V.move(V.scale(c2[i], 0.75, origin=(8.4, 4.1)), 2.2, 0)
    pt = [O("ta", "text", 1.2, 2.0, 4.8, 0.8, txt="Данные", sz=34, b=True, col="on_accent", z=200),
          O("tb", "text", 1.2, 2.9, 4.8, 1.4, txt=["15 задач", "3 человека"], sz=22, col="on_accent", z=200)]
    S.append(Slide([head("Команда данных", x=7.0, w=5.6)] + cells(theme, [R(c) for c in c3], fills=fills) + pt, dur=900,
                   fx=[Fx("entrance_fade", "ta", start="at", delay=0.12, dur=0.3), Fx("entrance_fade", "tb", start="with", delay=0.05, dur=0.3)]))
    # 5: столбики из клеток по командам
    s = 0.36
    cnt = [0] * 4
    c4 = [None] * n
    for i in order:
        q = cat[i]
        k = cnt[q]
        cnt[q] += 1
        c4[i] = V.rect(2.4 + q * 2.6 + (k % 3) * (s + 0.06), 6.1 - (k // 3 + 1) * (s + 0.06), s, s, r=0.04)
    l5 = [label(f"b{q}", f"{teams[q]} · {cnt[q]}", 3.0 + q * 2.6, 6.45, w=2.4, sz=16, col="accent" if q == 0 else "ink2", b=q == 0) for q in range(4)]
    S.append(Slide([head("Нагрузка команд")] + cells(theme, [R(c) for c in c4], fills=fills, ln=False) + l5, dur=900,
                   fx=[Fx("entrance_fade", l.name, start="at", delay=0.12 + 0.04 * k, dur=0.25) for k, l in enumerate(l5)]))
    S.append(Slide([head("Одна организация")] + cells(theme, [R(c) for c in c1], fills=fills), dur=900))
    return Variant("mosaic", "seq_team", "Мозаика организации",
                   "48 ячеек-задач в 7 состояниях: хаотичная мозаика, окраска по командам, ячейки перестраиваются "
                   "в территории команд, территории выпрямляются в соты, команда «Данные» раскрывается панелью из "
                   "своих клеток, клетки ссыпаются в столбики нагрузки и возвращаются в общую мозаику.",
                   S, tags=["seq", "mosaic", "voronoi", "hex", "cluster", "card", "data"], score=4)


def variants(theme) -> list[Variant]:
    return [f(theme) for f in (v_seq_map, v_seq_team, v_relax, v_waffle, v_hex_reveal, v_heat3d, v_zoom_cell, v_tri_arrow, v_plates,
                               v_bubbles, v_polar_table, v_iso_blocks, v_cluster)]
