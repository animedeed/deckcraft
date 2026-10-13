"""Общие помощники направления A «Фрагменты и разрезы» (семейства venn, peel, shatter, mosaic, tangram).

Геометрия — shapely в дюймах слайда (ось y вниз). Здесь:
  * glyphs(text, x, y, h)          — контуры букв/цифр как многоугольники с дырками (TextPath + свой разбор кривых);
  * shatter(g, n, seed)            — осколки: ячейки Вороного, обрезанные по фигуре;
  * cut(g, lines)                  — разрез фигуры набором линий;
  * voronoi_cells / hex_cells / tri_cells / lloyd — мозаики;
  * put / orbit                    — объект-кусок: сдвиг, масштаб, поворот на месте; кусок в рамке на оси;
  * sweep / iso                    — имитация 3D: «выдавливание» силуэта и изометрический наклон плоскости;
  * shelf                          — укладка кусков стопкой (осколки -> столбик);
  * head / sub / label             — короткие русские надписи.
"""

from __future__ import annotations

import math
import random
from typing import Sequence

from shapely import affinity
from shapely.geometry import LineString, MultiPoint, MultiPolygon, Point, Polygon, box
from shapely.ops import polygonize, unary_union, voronoi_diagram

from morphkit import O
from morphkit import vector as V
from morphkit.theme import mix

FONT_BOLD = "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf"


# ----------------------------------------------------------------------------- текст

def head(t: str, x: float = 0.7, y: float = 0.55, w: float = 6.2, sz: float = 30, name: str = "!!ttl") -> O:
    return O(name, "text", x, y, w, 0.75, txt=t, sz=sz, b=True, font="head", col="ink", z=60)


def sub(t: str, x: float = 0.7, y: float = 1.3, w: float = 5.6, name: str = "sub", col: str = "muted", sz: float = 16) -> O:
    return O(name, "text", x, y, w, 0.9, txt=t, sz=sz, col=col, z=60)


def label(name: str, t: str, cx: float, cy: float, w: float = 2.0, h: float = 0.42, sz: float = 15, col: str = "ink",
          b: bool = False, al: str = "c", z: int = 70) -> O:
    x = cx - w / 2 if al == "c" else cx
    return O(name, "text", x, cy - h / 2, w, h, txt=t, sz=sz, col=col, b=b, al=al, va="m", z=z)


def tones(theme, n: int, a: float = 0.08, b: float = 0.62, base: str = "ink") -> list[str]:
    """n оттенков от base к фону (тушь на чёрном / графит на бумаге)."""
    ink, bg = theme.c(base), theme.c("bg")
    return [mix(ink, bg, a + (b - a) * k / max(n - 1, 1)) for k in range(n)]


# ----------------------------------------------------------------------------- глифы

def _flatten(path, steps: int = 10) -> list[list[tuple[float, float]]]:
    """Path matplotlib -> замкнутые контуры (кривые Безье разбиты на отрезки)."""
    rings, cur, last = [], [], None
    for verts, code in path.iter_segments(curves=True, simplify=False):
        if code == 1:  # MOVETO
            if len(cur) > 2:
                rings.append(cur)
            cur = [tuple(verts[-2:])]
        elif code == 2:  # LINETO
            cur.append(tuple(verts[-2:]))
        elif code == 3:  # CURVE3
            (x0, y0), (x1, y1), (x2, y2) = cur[-1], verts[0:2], verts[2:4]
            for k in range(1, steps + 1):
                t = k / steps
                cur.append(((1 - t) ** 2 * x0 + 2 * (1 - t) * t * x1 + t * t * x2,
                            (1 - t) ** 2 * y0 + 2 * (1 - t) * t * y1 + t * t * y2))
        elif code == 4:  # CURVE4
            (x0, y0) = cur[-1]
            x1, y1, x2, y2, x3, y3 = verts
            for k in range(1, steps + 1):
                t = k / steps
                a, b_, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
                cur.append((a * x0 + b_ * x1 + c * x2 + d * x3, a * y0 + b_ * y1 + c * y2 + d * y3))
        elif code == 79:  # CLOSEPOLY
            if len(cur) > 2:
                rings.append(cur)
            cur = []
        last = code
    if len(cur) > 2:
        rings.append(cur)
    return rings


def _nest(rings) -> list[Polygon]:
    """Контуры -> многоугольники с дырками по вложенности (чётная глубина — тело, нечётная — дырка)."""
    polys = [Polygon(r).buffer(0) for r in rings]
    polys = [p if isinstance(p, Polygon) else max(p.geoms, key=lambda q: q.area) for p in polys if p.area > 1e-6]
    polys.sort(key=lambda p: -p.area)
    depth = []
    for i, p in enumerate(polys):
        depth.append(sum(1 for j in range(i) if polys[j].contains(p.representative_point())))
    out = []
    for i, p in enumerate(polys):
        if depth[i] % 2 == 0:
            holes = [polys[j] for j in range(len(polys)) if depth[j] == depth[i] + 1 and p.contains(polys[j].representative_point())]
            g = p
            for h in holes:
                g = g.difference(h)
            out.append(g)
    return out


def glyphs(text: str, x: float, y: float, h: float, bold: bool = True, per_char: bool = False, track: float = 0.0):
    """Контуры текста: высота заглавных/цифр = h дюймов, левый верхний угол в (x, y).
    per_char=False — список многоугольников (с дырками); per_char=True — список [символ -> список многоугольников]."""
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath
    fp = FontProperties(fname=FONT_BOLD if bold else FONT_REG)
    ref = TextPath((0, 0), "0", size=1.0, prop=fp).get_extents()
    k = h / ref.height
    chars, pen = [], 0.0
    for ch in text:
        tp = TextPath((pen, 0), ch, size=1.0, prop=fp)
        chars.append(_nest(_flatten(tp)))
        adv = TextPath((0, 0), ch + "|", size=1.0, prop=fp).get_extents().width - TextPath((0, 0), "|", size=1.0, prop=fp).get_extents().width
        pen += max(adv, 0.3) + track
    top = ref.y1
    out = []
    for polys in chars:
        out.append([affinity.affine_transform(p, [k, 0, 0, -k, x, y + top * k]) for p in polys])
    return out if per_char else [p for c in out for p in c]


def text_width(text: str, h: float, bold: bool = True, track: float = 0.0) -> float:
    gs = glyphs(text, 0, 0, h, bold, track=track)
    return unary_union(gs).bounds[2]


# ----------------------------------------------------------------------------- разрезы и осколки

def parts_of(g) -> list[Polygon]:
    if g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g]
    return [p for p in getattr(g, "geoms", []) if isinstance(p, Polygon) and not p.is_empty]


def shatter(g, n: int, seed: int = 3, min_area: float = 0.004, points: Sequence | None = None) -> list[Polygon]:
    """Осколки: ячейки Вороного случайных точек внутри g, обрезанные по g. Многосвязные куски делятся на части."""
    rnd = random.Random(seed)
    minx, miny, maxx, maxy = g.bounds
    pts = list(points or [])
    tries = 0
    while len(pts) < n and tries < n * 400:
        tries += 1
        p = (rnd.uniform(minx, maxx), rnd.uniform(miny, maxy))
        if g.contains(Point(p)):
            pts.append(p)
    cells = voronoi_cells(pts, (minx - 1, miny - 1, maxx + 1, maxy + 1))
    out = []
    for c in cells:
        for p in parts_of(c.intersection(g)):
            if p.area > min_area:
                out.append(p)
    return out


def cut(g, lines: Sequence[Sequence[tuple[float, float]]], min_area: float = 0.002) -> list[Polygon]:
    """Режет фигуру (можно с дырками) набором ломаных; возвращает куски."""
    ls = [LineString(l) for l in lines]
    edges = unary_union([b for p in parts_of(g) for b in [p.boundary]] + ls)
    out = []
    for p in polygonize(edges):
        if g.contains(p.representative_point()) and p.area > min_area:
            out.append(p)
    return out


def voronoi_cells(pts, bounds) -> list[Polygon]:
    """Ячейки Вороного в порядке точек, обрезанные прямоугольником bounds=(minx, miny, maxx, maxy)."""
    env = box(*bounds)
    vd = voronoi_diagram(MultiPoint(pts), envelope=env)
    cells = [c.intersection(env) for c in vd.geoms]
    order = []
    for p in pts:
        P = Point(p)
        order.append(min(cells, key=lambda c: 0 if c.contains(P) else c.distance(P) + 1))
    return order


def lloyd(pts, bounds, it: int = 1, clip=None) -> list[tuple[float, float]]:
    """Релаксация Ллойда: точки -> центры своих ячеек (хаос -> порядок)."""
    for _ in range(it):
        cells = voronoi_cells(pts, bounds)
        if clip is not None:
            cells = [c.intersection(clip) if not c.intersection(clip).is_empty else c for c in cells]
        pts = [(c.centroid.x, c.centroid.y) for c in cells]
    return pts


def rand_points(n: int, region, seed: int = 1, min_d: float = 0.0) -> list[tuple[float, float]]:
    rnd = random.Random(seed)
    minx, miny, maxx, maxy = region.bounds
    pts, tries = [], 0
    while len(pts) < n and tries < n * 2000:
        tries += 1
        p = (rnd.uniform(minx, maxx), rnd.uniform(miny, maxy))
        if region.contains(Point(p)) and all(math.dist(p, q) >= min_d for q in pts):
            pts.append(p)
    return pts


def hex_cells(cx: float, cy: float, r: float, rings: int | None = None, cols: int = 0, rows: int = 0,
              x0: float = 0, y0: float = 0, gap: float = 0.0, flat: bool = False) -> list[tuple[tuple[float, float], Polygon]]:
    """Соты. rings — шестиугольник из колец вокруг (cx, cy); или прямоугольник cols×rows от (x0, y0).
    Возвращает [(центр, шестиугольник)]. gap — зазор между сотами."""
    out = []
    w, hgt = math.sqrt(3) * r, 1.5 * r  # «острый верх»
    start = -90 if not flat else 0
    if rings is not None:
        for q in range(-rings, rings + 1):
            for s in range(max(-rings, -q - rings), min(rings, -q + rings) + 1):
                x = cx + w * (q + s / 2)
                y = cy + hgt * s
                out.append(((x, y), V.regular(x, y, r - gap / 2, 6, start=start)))
    else:
        for j in range(rows):
            for i in range(cols):
                x = x0 + w * (i + (0.5 if j % 2 else 0))
                y = y0 + hgt * j
                out.append(((x, y), V.regular(x, y, r - gap / 2, 6, start=start)))
    return out


def tri_cells(x0: float, y0: float, s: float, cols: int, rows: int, gap: float = 0.0) -> list[tuple[tuple[int, int], Polygon]]:
    """Треугольная мозаика: ячейки (i, j) со стороной s; чётные — вершиной вверх."""
    hgt = s * math.sqrt(3) / 2
    out = []
    for j in range(rows):
        for i in range(cols):
            xl = x0 + (i - 1) * s / 2 + (s / 2 if j % 2 else 0)
            up = (i + j) % 2 == 0
            ya, yb = y0 + j * hgt, y0 + (j + 1) * hgt
            if up:
                t = Polygon([(xl + s / 2, ya), (xl + s, yb), (xl, yb)])
            else:
                t = Polygon([(xl, ya), (xl + s, ya), (xl + s / 2, yb)])
            if gap:
                t = t.buffer(-gap / 2, join_style="mitre")
            out.append(((i, j), t))
    return out


# ----------------------------------------------------------------------------- куски -> объекты

def put(name: str, g, dx: float = 0.0, dy: float = 0.0, rot: float = 0.0, s: float = 1.0, **kw) -> O:
    """Кусок как жёсткое тело: сдвиг, равномерный масштаб вокруг центра габарита, поворот на месте (rot).
    Нормированные точки формы не меняются, поэтому Morph двигает/крутит/масштабирует рамку без перелива."""
    if s != 1.0:
        b = g.bounds
        g = V.scale(g, s, origin=((b[0] + b[2]) / 2, (b[1] + b[3]) / 2))
    if dx or dy:
        g = V.move(g, dx, dy)
    return V.shape(name, g, rot=rot, **kw)


def orbit(name: str, g, pivot: tuple[float, float], R: float, rot: float = 0.0, **kw) -> O:
    """Кусок в рамке на оси pivot фиксированного радиуса R: rot вращает его по дуге вокруг pivot,
    а смена самой формы (сдвиг, рост) — перелив внутри той же рамки (число точек не меняется)."""
    px, py = pivot
    return V.shape(name, g, frame=(px - R, py - R, 2 * R, 2 * R), rot=rot, **kw)


def at_centroid(g, x: float, y: float, s: float = 1.0):
    """Переносит фигуру центром масс в (x, y), с масштабом s."""
    c = g.centroid
    if s != 1.0:
        g = V.scale(g, s, origin=(c.x, c.y))
    return V.move(g, x - c.x, y - c.y)


def bbox_center(g) -> tuple[float, float]:
    b = g.bounds
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


def iso(g, origin: tuple[float, float], tilt: float = 0.5, turn: float = 45.0):
    """Изометрический наклон плоскости: поворот на turn вокруг origin и сжатие по вертикали в tilt раз."""
    g = V.rotate(g, turn, origin=origin)
    return affinity.scale(g, 1.0, tilt, origin=origin)


def sweep(g, dy: float):
    """Силуэт «выдавливания» фигуры вертикально вверх на dy дюймов (боковая стенка призмы)."""
    if abs(dy) < 1e-6:
        return g
    top = V.move(g, 0, -dy)
    quads = []
    for poly in parts_of(g):
        cs = list(poly.exterior.coords)
        for (x1, y1), (x2, y2) in zip(cs, cs[1:]):
            q = Polygon([(x1, y1), (x2, y2), (x2, y2 - dy), (x1, y1 - dy)])
            if q.is_valid and q.area > 1e-9:
                quads.append(q)
    return unary_union([g, top] + quads)


def shelf(pieces: Sequence, x: float, base: float, w: float, gap: float = 0.03, upward: bool = True) -> list[tuple[float, float]]:
    """Укладка кусков рядами (от base вверх) в колонку шириной w. Возвращает сдвиги (dx, dy) каждого куска."""
    order = sorted(range(len(pieces)), key=lambda i: -(pieces[i].bounds[3] - pieces[i].bounds[1]))
    res = [None] * len(pieces)
    cx, cy, row_h = x, base, 0.0
    for i in order:
        b = pieces[i].bounds
        pw, ph = b[2] - b[0], b[3] - b[1]
        if cx + pw > x + w and cx > x:
            cy = cy - row_h - gap if upward else cy + row_h + gap
            cx, row_h = x, 0.0
        tx = cx - b[0]
        ty = (cy - ph - b[1]) if upward else (cy - b[1])
        res[i] = (tx, ty)
        cx += pw + gap
        row_h = max(row_h, ph)
    return res


def ring_cells(cx: float, cy: float, r_in: float, r_out: float, n: int, a0: float = -90.0, a1: float = 270.0,
               gap_deg: float = 0.0) -> list[Polygon]:
    """Сегменты кольца (кольцевая шкала из отдельных ячеек — не blockArc)."""
    out = []
    for k in range(n):
        s = a0 + (a1 - a0) * k / n + gap_deg / 2
        e = a0 + (a1 - a0) * (k + 1) / n - gap_deg / 2
        out.append(V.sector(cx, cy, r_out, s, e, r_in=r_in, steps=8))
    return out


def blob(cx: float, cy: float, r: float, amps: Sequence[float] = (0.12, 0.08, 0.05), phase: float = 0.0, n: int = 180,
         sx: float = 1.0, sy: float = 1.0) -> Polygon:
    """Органическое пятно: круг с гармониками радиуса."""
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        rr = r * (1 + sum(am * math.sin((i + 2) * a + phase * (i + 1)) for i, am in enumerate(amps)))
        pts.append((cx + rr * math.cos(a) * sx, cy + rr * math.sin(a) * sy))
    return Polygon(pts)


def fit_rot(canon, target, prefer: float = 0.0, step: float = 45.0, tol: float = 0.02) -> tuple[float, float, float] | None:
    """Ищет поворот θ (кратный step) куска canon, при котором он совпадает с target после сдвига.
    Возвращает (θ, dx, dy) для put(name, canon, dx, dy, rot=θ) — θ ближайший к prefer."""
    best = None
    bc = bbox_center(canon)
    for k in range(int(360 / step)):
        th = k * step
        g1 = V.rotate(canon, th, origin=bc)
        c1, ct = g1.centroid, target.centroid
        g2 = V.move(g1, ct.x - c1.x, ct.y - c1.y)
        if g2.symmetric_difference(target).area < tol * target.area:
            # рамка вращается вокруг центра габарита исходного куска: сдвигаем исходный кусок на тот же вектор
            cand = th
            while cand - prefer > 180:
                cand -= 360
            while cand - prefer < -180:
                cand += 360
            d = abs(cand - prefer)
            if best is None or d < best[0]:
                best = (d, cand, ct.x - c1.x, ct.y - c1.y)
    return None if best is None else (best[1], best[2], best[3])


# ----------------------------------------------------------------------------- полосы с согласованными точками

def arc_band(cx: float, cy: float, r_in: float, r_out: float, a0: float, a1: float, m: int = 64, cap: int = 4) -> Polygon:
    """Дуга-полоса (сегмент кольца) с точками в фиксированном порядке: внешняя дуга a0→a1 (m точек), торец,
    внутренняя дуга a1→a0, торец. Пара к bar_band с тем же m и cap: Morph «разворачивает» кольцо в полосу."""
    pts = []
    for k in range(m):
        a = math.radians(a0 + (a1 - a0) * k / (m - 1))
        pts.append((cx + r_out * math.cos(a), cy + r_out * math.sin(a)))
    for k in range(1, cap + 1):
        rr = r_out + (r_in - r_out) * k / (cap + 1)
        a = math.radians(a1)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    for k in range(m):
        a = math.radians(a1 + (a0 - a1) * k / (m - 1))
        pts.append((cx + r_in * math.cos(a), cy + r_in * math.sin(a)))
    for k in range(1, cap + 1):
        rr = r_in + (r_out - r_in) * k / (cap + 1)
        a = math.radians(a0)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return Polygon(pts)


def bar_band(x: float, y: float, L: float, t: float, m: int = 64, cap: int = 4) -> Polygon:
    """Прямая полоса длины L и толщины t с тем же порядком точек, что у arc_band (верх = внешняя дуга)."""
    pts = [(x + L * k / (m - 1), y) for k in range(m)]
    pts += [(x + L, y + t * k / (cap + 1)) for k in range(1, cap + 1)]
    pts += [(x + L - L * k / (m - 1), y + t) for k in range(m)]
    pts += [(x, y + t - t * k / (cap + 1)) for k in range(1, cap + 1)]
    return Polygon(pts)


def vshape(name: str, g, **kw):
    """V.shape без переориентации точек: для пар arc_band/bar_band (порядок точек уже согласован)."""
    return V.shape(name, g, **kw)


def arrow_poly(x0: float, y0: float, x1: float, y1: float, w: float = 0.06, head: float = 0.28) -> Polygon:
    """Стрелка-многоугольник от (x0, y0) к (x1, y1): древко толщиной w, наконечник длиной head."""
    L = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    nx, ny = -uy, ux
    bx, by = x1 - ux * head, y1 - uy * head
    pts = [(x0 + nx * w / 2, y0 + ny * w / 2), (bx + nx * w / 2, by + ny * w / 2), (bx + nx * head * 0.55, by + ny * head * 0.55),
           (x1, y1), (bx - nx * head * 0.55, by - ny * head * 0.55), (bx - nx * w / 2, by - ny * w / 2), (x0 - nx * w / 2, y0 - ny * w / 2)]
    return Polygon(pts)


def no_holes(pieces: Sequence) -> list[Polygon]:
    """Куски с дырками режутся вертикалью через центр дырки (для перелива нужны контуры без дыр)."""
    out = []
    stack = list(pieces)
    while stack:
        p = stack.pop()
        if isinstance(p, Polygon) and len(p.interiors) == 0:
            out.append(p)
            continue
        h = Polygon(p.interiors[0]).centroid
        b = p.bounds
        stack += cut(p, [[(h.x, b[1] - 1), (h.x, b[3] + 1)]])
    return out


def match(src: Sequence, dst: Sequence, norm: bool = True) -> list[int]:
    """Сопоставление кусков src -> места dst (минимум суммарного пути, по центрам; norm — в долях габаритов),
    чтобы перелёт был связным. Возвращает perm: src[i] -> dst[perm[i]]."""
    def cen(gs):
        pts = [(g.centroid.x, g.centroid.y) for g in gs]
        if not norm:
            return pts
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        sx, sy = (max(xs) - min(xs)) or 1, (max(ys) - min(ys)) or 1
        return [((x - min(xs)) / sx, (y - min(ys)) / sy) for x, y in pts]
    a, b = cen(src), cen(dst)
    try:
        from scipy.optimize import linear_sum_assignment
        cost = [[(p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 for q in b] for p in a]
        r, c = linear_sum_assignment(cost)
        perm = [0] * len(a)
        for i, j in zip(r, c):
            perm[i] = j
        return perm
    except ImportError:  # pragma: no cover
        ia = sorted(range(len(a)), key=lambda i: (a[i][0], a[i][1]))
        ib = sorted(range(len(b)), key=lambda i: (b[i][0], b[i][1]))
        perm = [0] * len(a)
        for i, j in zip(ia, ib):
            perm[i] = j
        return perm


def cells_exact(region, n: int, seed: int = 5, relax: int = 2) -> list[Polygon]:
    """Ровно n ячеек Вороного внутри region (по одной на точку; у ячейки берётся самая крупная часть)."""
    pts = rand_points(n, region, seed=seed)
    b = region.bounds
    bb = (b[0] - 1, b[1] - 1, b[2] + 1, b[3] + 1)
    for _ in range(relax):
        cs = voronoi_cells(pts, bb)
        pts = []
        for c in cs:
            q = c.intersection(region)
            q = max(parts_of(q), key=lambda g: g.area) if not q.is_empty else c
            pts.append((q.centroid.x, q.centroid.y))
    out = []
    for c in voronoi_cells(pts, bb):
        q = c.intersection(region)
        ps = parts_of(q)
        out.append(max(ps, key=lambda g: g.area) if ps else c.buffer(-0.3 * math.sqrt(c.area)))
    return out
