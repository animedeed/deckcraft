"""Векторная графика: булевы операции над фигурами, радиальные сборки, морфинг форм, градиенты, 3D.

Геометрия строится в shapely (координаты — дюймы слайда или мира, ось y вниз) и превращается в объект
O(kind="vec"): свободная форма a:custGeom, вписанная в рамку. Это то же самое, что «Объединение фигур»
в PowerPoint (Union / Combine / Fragment / Intersect / Subtract), только программно и воспроизводимо.

    from morphkit import vector as V
    petal = V.lens((0, -1.2), r=1.0, gap=1.1)            # лепесток = пересечение двух кругов
    ring = V.subtract(V.circle(0, 0, 2.2), V.circle(0, 0, 1.6))
    objs = [V.shape(f"!!p{i}", petal, pivot=(0, 0), rot=36 * i, fill="accent") for i in range(10)]

Приём «рамка на оси» (pivot): рамка объекта — квадрат с центром в точке pivot, а форма нарисована внутри
неё со смещением. PowerPoint вращает объект вокруг центра рамки, поэтому поворот (rot) и его морфинг
вращают форму вокруг pivot: колесо, циферблат, лепестки цветка, орбита. Вход «Вертушка» (Spinner)
и выделение «Вращение» тоже крутят такой объект вокруг pivot.

Морфинг форм: у обеих форм одинаковое число точек, одно направление обхода и одна стартовая точка
(resample). Morph честно переливает одну свободную форму в другую только при этих условиях; не больше
одной дырки у формы.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence

from .model import O

try:
    from shapely import affinity
    from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
    from shapely.geometry.polygon import orient
    from shapely.ops import polygonize, unary_union
except ImportError as exc:  # pragma: no cover
    raise ImportError("morphkit.vector требует shapely: pip install shapely") from exc

SEG = 48  # отрезков на четверть окружности (192 на круг)
RESAMPLE_MIN = 120  # меньше — на крупных формах видны грани и срезанные кончики (отзыв пользователя)


# ----------------------------------------------------------------------------- примитивы

def circle(cx: float, cy: float, r: float, seg: int = SEG) -> Polygon:
    return Point(cx, cy).buffer(r, quad_segs=seg)


def ellipse(cx: float, cy: float, rx: float, ry: float, seg: int = SEG) -> Polygon:
    return affinity.translate(affinity.scale(circle(0, 0, 1, seg), rx, ry, origin=(0, 0)), cx, cy)


def rect(x: float, y: float, w: float, h: float, r: float = 0.0) -> Polygon:
    g = box(x, y, x + w, y + h)
    return g if r <= 0 else g.buffer(-r, join_style="mitre").buffer(r, quad_segs=SEG // 2)


def polygon(points: Sequence[tuple[float, float]]) -> Polygon:
    return Polygon(points)


def regular(cx: float, cy: float, r: float, n: int, start: float = -90.0) -> Polygon:
    """Правильный n-угольник; start — угол первой вершины (−90° — вершина сверху)."""
    return Polygon([(cx + r * math.cos(math.radians(start + 360 * k / n)),
                     cy + r * math.sin(math.radians(start + 360 * k / n))) for k in range(n)])


def star(cx: float, cy: float, r_out: float, r_in: float, n: int = 5, start: float = -90.0) -> Polygon:
    pts = []
    for k in range(2 * n):
        r = r_out if k % 2 == 0 else r_in
        a = math.radians(start + 180 * k / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return Polygon(pts)


def sector(cx: float, cy: float, r_out: float, a0: float, a1: float, r_in: float = 0.0, steps: int | None = None) -> Polygon:
    """Сектор или сегмент кольца от угла a0 до a1 (градусы, 0 — вправо, по часовой стрелке на экране)."""
    steps = steps or max(8, int(abs(a1 - a0) / 2))
    outer = [(cx + r_out * math.cos(math.radians(a0 + (a1 - a0) * t / steps)),
              cy + r_out * math.sin(math.radians(a0 + (a1 - a0) * t / steps))) for t in range(steps + 1)]
    if r_in <= 0:
        return Polygon([(cx, cy)] + outer)
    inner = [(cx + r_in * math.cos(math.radians(a1 - (a1 - a0) * t / steps)),
              cy + r_in * math.sin(math.radians(a1 - (a1 - a0) * t / steps))) for t in range(steps + 1)]
    return Polygon(outer + inner)


def lens(center: tuple[float, float], r: float, gap: float, angle: float = 90.0) -> Polygon:
    """Лепесток-линза: пересечение двух кругов радиуса r, центры которых разнесены на gap поперёк оси.
    angle — направление оси лепестка (90° — вертикально). Чем ближе gap к 2r, тем тоньше лепесток."""
    cx, cy = center
    nx, ny = math.cos(math.radians(angle + 90)), math.sin(math.radians(angle + 90))
    a = circle(cx + nx * gap / 2, cy + ny * gap / 2, r)
    b = circle(cx - nx * gap / 2, cy - ny * gap / 2, r)
    return a.intersection(b)


def petal(pivot: tuple[float, float], r_in: float, r_out: float, width: float, angle: float = -90.0) -> Polygon:
    """Лепесток от радиуса r_in до r_out вокруг pivot, ось по углу angle (−90° — вверх). width — наибольшая ширина."""
    length = r_out - r_in
    # линза длины L и ширины W: радиус дуги R = (L² + W²) / (4W), разнос центров 2R − W
    R = (length ** 2 + width ** 2) / (4 * width)
    mid = (r_in + r_out) / 2
    c = (pivot[0] + mid * math.cos(math.radians(angle)), pivot[1] + mid * math.sin(math.radians(angle)))
    return lens(c, R, 2 * R - width, angle)


def lens_from_base(base: tuple[float, float], length: float, width: float, angle: float = -90.0) -> Polygon:
    """Линза, одна вершина которой в точке base, другая — на расстоянии length по углу angle."""
    return petal(base, 0.0, length, width, angle)


def bud(base: tuple[float, float], length: float, width: float, layers: int = 5, h_ratio: float = 0.80,
        w_ratio: float = 0.84, angle: float = -90.0, n: int = 0, nested: bool = True) -> list[Polygon]:
    """Многослойный «бутон» как в эталонном видео: вложенные линзы с общей вершиной в base (каждая следующая
    короче и уже) -> фрагменты: полосы-полумесяцы снаружи внутрь + ядро. Возвращает [полоса0, …, ядро].
    n > 0 — каждая часть ресемплится до n точек (для перелива формы)."""
    lenses = [lens_from_base(base, length * h_ratio ** k, width * w_ratio ** k, angle) for k in range(layers)]
    # nested: целые линзы стопкой (внутренняя поверх внешней) — видимая полоса та же, но стыков-щелей между
    # соседними частями нет (отзыв: «прорывы» между слоями цветка). False — полосы-полумесяцы (для разлёта на части)
    parts = list(lenses) if nested else [lenses[k].difference(lenses[k + 1]) for k in range(layers - 1)] + [lenses[-1]]
    out = []
    for g in parts:
        if isinstance(g, MultiPolygon):
            g = max(g.geoms, key=lambda q: q.area)
        out.append(resample(g, n) if n else g)
    return out


# ----------------------------------------------------------------------------- булевы операции (Merge Shapes)

def union(*gs) -> Polygon | MultiPolygon:
    return unary_union(list(_flat(gs)))


def intersect(a, b):
    return a.intersection(b)


def subtract(a, *bs):
    for b in bs:
        a = a.difference(b)
    return a


def combine(a, b):
    """«Объединение с исключением» (Combine): части, покрытые ровно одной из фигур."""
    return a.symmetric_difference(b)


def fragment(*gs) -> list[Polygon]:
    """«Фрагментация» (Fragment): все кусочки, на которые фигуры режут друг друга."""
    gs = list(_flat(gs))
    lines = unary_union([g.boundary for g in gs])
    whole = unary_union(gs)
    return [p for p in polygonize(lines) if whole.contains(p.representative_point())]


def slices(g, n: int, pivot: tuple[float, float] | None = None, start: float = -90.0) -> list[Polygon]:
    """Режет фигуру на n равных секторов вокруг pivot (по умолчанию — центр фигуры)."""
    cx, cy = pivot or (g.centroid.x, g.centroid.y)
    big = max(g.bounds[2] - g.bounds[0], g.bounds[3] - g.bounds[1]) * 2
    out = []
    for k in range(n):
        s = sector(cx, cy, big, start + 360 * k / n, start + 360 * (k + 1) / n)
        part = g.intersection(s)
        if not part.is_empty:
            out.append(part)
    return out


def _flat(gs) -> Iterable:
    for g in gs:
        if isinstance(g, (list, tuple)):
            yield from _flat(g)
        else:
            yield g


# ----------------------------------------------------------------------------- преобразования

def rotate(g, deg: float, origin: tuple[float, float] | str = "center"):
    return affinity.rotate(g, deg, origin=origin)


def move(g, dx: float, dy: float):
    return affinity.translate(g, dx, dy)


def scale(g, k: float, ky: float | None = None, origin: tuple[float, float] | str = "center"):
    return affinity.scale(g, k, k if ky is None else ky, origin=origin)


def radial(g, n: int, pivot: tuple[float, float], step: float | None = None) -> list:
    """n копий фигуры, повёрнутых вокруг pivot с шагом 360/n (или step) — сама геометрия поворачивается."""
    step = 360.0 / n if step is None else step
    return [affinity.rotate(g, step * k, origin=pivot) for k in range(n)]


def _corners(pts: list[tuple[float, float]], deg: float = 28.0) -> list[int]:
    """Индексы острых вершин замкнутой ломаной: поворот направления больше deg градусов."""
    out, m = [], len(pts)
    for k in range(m):
        ax, ay = pts[k - 1]
        bx, by = pts[k]
        cx, cy = pts[(k + 1) % m]
        a1, a2 = math.atan2(by - ay, bx - ax), math.atan2(cy - by, cx - bx)
        turn = abs((math.degrees(a2 - a1) + 180) % 360 - 180)
        if turn > deg:
            out.append(k)
    return out


def resample(g, n: int = 160, start: str | float = "top", keep_corners: bool = True) -> Polygon:
    """Внешний контур ровно из n точек, обход по часовой стрелке на экране, первая точка — самая верхняя
    (start='top') или ближайшая к углу start (градусы вокруг центра). Готовит пары форм к морфингу.
    keep_corners: острые вершины (кончик лепестка, угол клёпки) остаются точками контура, остальные точки
    распределяются по дугам между ними пропорционально длине — без этого равномерный шаг срезает углы."""
    n = max(int(n), RESAMPLE_MIN)
    poly = max(g.geoms, key=lambda p: p.area) if isinstance(g, MultiPolygon) else g
    ring = LineString(orient(Polygon(poly.exterior), sign=1.0).exterior.coords)  # против ч. с. в осях y-вверх
    src = list(ring.coords)[:-1]
    corners = _corners(src) if keep_corners else []
    if len(corners) > n // 3:  # слишком много «углов» (мелкая ломаная) — обычный равномерный шаг
        corners = []
    L = ring.length
    if not corners:
        pts = [ring.interpolate(L * k / n) for k in range(n)]
        pts = [(q.x, q.y) for q in pts]
    else:
        # длины дуг между соседними углами и доля точек на каждую (угол — сама точка)
        dist = [ring.project(Point(src[c])) for c in corners]
        arcs = [((dist[(i + 1) % len(dist)] - dist[i]) % L) or L for i in range(len(dist))]
        free = n - len(corners)
        share = [a / L * free for a in arcs]
        cnt = [int(x) for x in share]
        for i in sorted(range(len(cnt)), key=lambda i: -(share[i] - cnt[i]))[:free - sum(cnt)]:
            cnt[i] += 1
        pts = []
        for i, d0 in enumerate(dist):
            pts.append(src[corners[i]])
            for j in range(1, cnt[i] + 1):
                q = ring.interpolate((d0 + arcs[i] * j / (cnt[i] + 1)) % L)
                pts.append((q.x, q.y))
    cx, cy = poly.centroid.x, poly.centroid.y
    if start == "top":
        k0 = min(range(n), key=lambda k: (round(pts[k][1], 6), abs(pts[k][0] - cx)))
    else:
        ang = math.radians(float(start))
        tx, ty = cx + math.cos(ang) * 1e3, cy + math.sin(ang) * 1e3
        k0 = min(range(n), key=lambda k: (pts[k][0] - tx) ** 2 + (pts[k][1] - ty) ** 2)
    pts = pts[k0:] + pts[:k0]
    holes = [list(h.coords)[:-1] for h in poly.interiors]
    return Polygon(pts, holes)


# ----------------------------------------------------------------------------- геометрия -> объект O

def _rings(g) -> list[list[tuple[float, float]]]:
    """Контуры для пути: внешние — по часовой стрелке на экране, дырки — против (заливка верна при любом правиле)."""
    polys = list(g.geoms) if isinstance(g, MultiPolygon) else [g]
    out = []
    for p in polys:
        if p.is_empty:
            continue
        q = orient(p, sign=1.0)  # контур после resample уже так ориентирован: стартовая точка сохраняется
        out.append(list(q.exterior.coords)[:-1])
        out += [list(h.coords)[:-1] for h in q.interiors]
    return out


SMOOTH_TARGET = 240  # точек на контур после сглаживания (не больше ×4 к исходному)


def smooth_ring(ring: list[tuple[float, float]], corner_deg: float = 35.0) -> list[tuple[float, float]]:
    """Гладкий контур без изменения формы: каждая грань делится на k частей кубическим сплайном Эрмита через
    исходные точки (касательная Катмулла–Рома в гладкой вершине, нулевая — в угле: прямые остаются прямыми,
    углы — острыми). k зависит только от числа точек, поэтому у пары Morph с равным числом точек оно одинаково."""
    m = len(ring)
    if m < 3 or m >= SMOOTH_TARGET:
        return ring
    k = max(1, min(4, -(-SMOOTH_TARGET // m)))
    if k == 1:
        return ring
    P = ring

    def turn(i):
        a, b, c = P[i - 1], P[i], P[(i + 1) % m]
        t = math.degrees(math.atan2(c[1] - b[1], c[0] - b[0]) - math.atan2(b[1] - a[1], b[0] - a[0]))
        return abs((t + 180) % 360 - 180)

    tan = []
    for i in range(m):
        if turn(i) > corner_deg:
            tan.append((0.0, 0.0))
        else:
            a, c = P[i - 1], P[(i + 1) % m]
            tan.append(((c[0] - a[0]) / 2, (c[1] - a[1]) / 2))
    out = []
    for i in range(m):
        (x0, y0), (x1, y1) = P[i], P[(i + 1) % m]
        (tx0, ty0), (tx1, ty1) = tan[i], tan[(i + 1) % m]
        out.append((x0, y0))
        for j in range(1, k):
            t = j / k
            h00, h10, h01, h11 = 2 * t**3 - 3 * t**2 + 1, t**3 - 2 * t**2 + t, -2 * t**3 + 3 * t**2, t**3 - t**2
            out.append((h00 * x0 + h10 * tx0 + h01 * x1 + h11 * tx1, h00 * y0 + h10 * ty0 + h01 * y1 + h11 * ty1))
    return out


def smooth_rings(rings, w: float = 1.0, h: float = 1.0):
    """smooth_ring для нормированных контуров рамки w × h (углы считаются в настоящих пропорциях)."""
    w, h = max(w, 1e-6), max(h, 1e-6)
    return [[(x / w, y / h) for x, y in smooth_ring([(px * w, py * h) for px, py in r])] for r in rings]


def shape(name: str, g, pivot: tuple[float, float] | None = None, rot: float = 0.0, frame=None,
          fill: str | None = "accent", ln: str | None = None, lw: float = 0.0, z: int = 6, world: bool = False,
          grad: dict | None = None, d3: dict | None = None, **kw) -> O:
    """Объект-свободная форма. pivot — ось вращения (рамка-квадрат с центром в pivot);
    frame — явная рамка (x, y, w, h); по умолчанию рамка = габарит формы.
    grad — градиент (см. gradient()); d3 — 3D (см. rot3d()). Остальные поля O — через kw."""
    rings = _rings(g)
    xs = [x for r in rings for x, _ in r]
    ys = [y for r in rings for _, y in r]
    minx, miny, maxx, maxy = min(xs), min(ys), max(xs), max(ys)
    if frame is not None:
        fx, fy, fw, fh = frame
    elif pivot is not None:
        px, py = pivot
        R = max(math.hypot(x - px, y - py) for ring in rings for x, y in ring) * 1.0001
        fx, fy, fw, fh = px - R, py - R, 2 * R, 2 * R
    else:
        fx, fy, fw, fh = minx, miny, max(maxx - minx, 1e-4), max(maxy - miny, 1e-4)
    norm = [[((x - fx) / fw, (y - fy) / fh) for x, y in ring] for ring in rings]
    bbox = ((minx - fx) / fw, (miny - fy) / fh, (maxx - fx) / fw, (maxy - fy) / fh)
    meta = dict(kw.pop("meta", {}))
    meta.update({"vec": norm, "bbox": bbox})
    if grad:
        meta["grad"] = _fit_grad(grad, bbox) if grad.get("fit", True) and grad.get("kind", "linear") == "linear" else grad
    if d3:
        meta["d3"] = d3
    return O(name, "vec", fx, fy, fw, fh, fill=fill, ln=ln, lw=lw, rot=rot, z=z, world=world, meta=meta, **kw)


# ----------------------------------------------------------------------------- заливки и 3D

def gradient(stops: Sequence[tuple[float, str] | tuple[float, str, float]], angle: float = 90.0,
             kind: str = "linear", fit: bool = True) -> dict:
    """Градиент: stops — [(позиция 0..1, роль или hex[, непрозрачность])], angle — направление (90° — сверху вниз),
    kind — 'linear' | 'radial' (из центра) | 'rect'. Передаётся в shape(grad=…) или O(meta={'grad': …}).
    Градиент вращается вместе с фигурой. fit=True: у формы в большой рамке (pivot) растягивается по самой форме."""
    return {"stops": [tuple(s) for s in stops], "angle": angle, "kind": kind, "fit": fit}


def _fit_grad(grad: dict, bbox) -> dict:
    """Переносит позиции стопов из [0, 1] формы в координаты рамки вдоль направления градиента."""
    a = math.radians(grad.get("angle", 90))
    d = (math.cos(a), math.sin(a))
    proj = lambda pts: [x * d[0] + y * d[1] for x, y in pts]  # noqa: E731
    pf = proj([(0, 0), (1, 0), (0, 1), (1, 1)])
    l, t, r, b = bbox
    pb = proj([(l, t), (r, t), (l, b), (r, b)])
    f0, f1, q0, q1 = min(pf), max(pf), min(pb), max(pb)
    stops = []
    for st in grad["stops"]:
        pos = (q0 + st[0] * (q1 - q0) - f0) / (f1 - f0)
        stops.append((min(max(pos, 0.0), 1.0),) + tuple(st[1:]))
    return {**grad, "stops": stops}


def rot3d(x: float = 0.0, y: float = 0.0, z: float = 0.0, depth: float = 0.0, depth_color: str | None = None,
          bevel: float = 0.0, camera: str = "perspectiveFront", fov: float = 45.0, light: str = "threePt",
          material: str | None = None) -> dict:
    """3D-поворот фигуры (как «Формат фигуры → Поворот объёмной фигуры»): x, y, z — градусы по осям X, Y, Z;
    depth — глубина выдавливания, pt; bevel — фаска сверху, pt. Morph плавно меняет 3D-поворот между слайдами."""
    return {"x": x, "y": y, "z": z, "depth": depth, "depth_color": depth_color, "bevel": bevel, "camera": camera,
            "fov": fov, "light": light, "material": material}


# ----------------------------------------------------------------------------- XML (используется build)

def custgeom_xml(rings: list[list[tuple[float, float]]], W: int = 100000, H: int = 100000) -> str:
    A = "http://schemas.openxmlformats.org/drawingml/2006/main"
    parts = []
    for ring in rings:
        if len(ring) < 3:
            continue
        x0, y0 = ring[0]
        cmds = [f'<a:moveTo><a:pt x="{round(x0 * W)}" y="{round(y0 * H)}"/></a:moveTo>']
        cmds += [f'<a:lnTo><a:pt x="{round(x * W)}" y="{round(y * H)}"/></a:lnTo>' for x, y in ring[1:]]
        parts.append("".join(cmds) + "<a:close/>")
    return (f'<a:custGeom xmlns:a="{A}"><a:avLst/><a:gdLst/><a:ahLst/><a:cxnLst/><a:rect l="l" t="t" r="r" b="b"/>'
            f'<a:pathLst><a:path w="{W}" h="{H}">{"".join(parts)}</a:path></a:pathLst></a:custGeom>')


def bbox_on_slide(o: O) -> tuple[float, float, float, float]:
    """Настоящий габарит формы на слайде (рамка pivot может быть много больше формы). Поворот не учитывается."""
    if o.kind != "vec" or "bbox" not in o.meta:
        return o.x, o.y, o.w, o.h
    l, t, r, b = o.meta["bbox"]
    if o.rot:
        cx, cy = o.x + o.w / 2, o.y + o.h / 2
        pts = [(o.x + u * o.w, o.y + v * o.h) for ring in o.meta["vec"] for u, v in ring]
        a = math.radians(o.rot)
        rp = [(cx + (x - cx) * math.cos(a) - (y - cy) * math.sin(a), cy + (x - cx) * math.sin(a) + (y - cy) * math.cos(a))
              for x, y in pts]
        xs, ys = [p[0] for p in rp], [p[1] for p in rp]
        return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
    return o.x + l * o.w, o.y + t * o.h, (r - l) * o.w, (b - t) * o.h


def point_in_vec(o: O, px: float, py: float) -> bool:
    """Лежит ли точка слайда внутри формы объекта vec (с учётом поворота рамки; правило чёт-нечет)."""
    cx, cy = o.x + o.w / 2, o.y + o.h / 2
    a = math.radians(-o.rot)
    qx = cx + (px - cx) * math.cos(a) - (py - cy) * math.sin(a)
    qy = cy + (px - cx) * math.sin(a) + (py - cy) * math.cos(a)
    u, v = (qx - o.x) / o.w, (qy - o.y) / o.h
    inside = False
    for ring in o.meta.get("vec", []):
        n = len(ring)
        for i in range(n):
            (x1, y1), (x2, y2) = ring[i], ring[(i + 1) % n]
            if (y1 > v) != (y2 > v) and u < (x2 - x1) * (v - y1) / (y2 - y1) + x1:
                inside = not inside
    return inside
