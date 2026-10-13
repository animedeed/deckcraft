"""Операторы движения: любое состояние (список O) -> новое состояние с теми же именами. Morph переводит одно
в другое, поэтому оператор = анимация, применимая к ЛЮБОЙ форме (лепесткам, точкам, карточкам, ягодам).

    from morphkit import ops as P
    a = shapes                                   # исходное состояние
    b = P.explode(a, center, 0.6)                # разлёт
    c = P.tilt3d(P.to_vec(a), center, pitch=62)  # наклон «в стол» (настоящая проекция контуров)
    d = P.recede(c, vanish=(6.7, 2.0), depth=0.5, fade=0.4)   # уход в глубину
    e = P.orbit(a, center, 40)                   # поворот всей системы вокруг центра
    f = P.swirl(a, center, 90)                   # вихрь: внешние части поворачиваются сильнее

Операторы компонуются: P.recede(P.tilt3d(P.explode(a, c, .3), c, 55), v, .4). Псевдо-3D работает на контурах
(`to_vec`): у каждой фигуры фиксированное число точек, поэтому наклон, поворот в пространстве и уход в глубину
переливаются плавно. Фигуры с текстом не превращаются в контуры — у них двигается рамка.
"""

from __future__ import annotations

import math
import random
from typing import Callable, Sequence

from .model import O

Pt = tuple[float, float]
Sel = Callable[[O], bool] | None


def _sel(o: O, select: Sel) -> bool:
    return select is None or select(o)


def _center(o: O) -> Pt:
    return o.x + o.w / 2, o.y + o.h / 2


def _place(o: O, cx: float, cy: float, **kw) -> O:
    w, h = kw.pop("w", o.w), kw.pop("h", o.h)
    return o.copy(x=cx - w / 2, y=cy - h / 2, w=w, h=h, **kw)


# ----------------------------------------------------------------------------- контуры

def to_vec(objs: Sequence[O], n: int = 64) -> list[O]:
    """Фигуры без текста -> свободные формы с n точками на контур (поворот «запечён» в точки). Нужна для
    псевдо-3D и перелива между разными формами. Линии и текст не меняются."""
    from .motion import _local_polys
    out = []
    for o in objs:
        if o.lines or o.kind in ("line", "arrow", "text", "img"):
            out.append(o)
            continue
        rings = _local_polys(o, n_ellipse=n) if o.kind != "vec" else _local_polys(o)
        rings = [r for r in rings if len(r) >= 3]
        if rings:  # внешний контур — по часовой, с самой верхней точки (как V.resample): переливы без перекрута
            from shapely.geometry import Polygon
            from .vector import resample as _rs
            g = Polygon(rings[0])
            if not g.is_valid:
                g = g.buffer(0)
            outer = list(_rs(g, n).exterior.coords)[:-1] if g.area > 1e-6 else _resample_ring(rings[0], n)
            rings = [outer] + [_resample_ring(r, n) for r in rings[1:]]
        if not rings:
            out.append(o)
            continue
        out.append(_from_rings(o, rings))
    return out


def _resample_ring(ring: Sequence[Pt], n: int) -> list[Pt]:
    pts = list(ring) + [ring[0]]
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    L = sum(seg) or 1.0
    out, k, acc = [], 0, 0.0
    for i in range(n):
        d = L * i / n
        while k < len(seg) - 1 and acc + seg[k] < d:
            acc += seg[k]
            k += 1
        f = (d - acc) / (seg[k] or 1.0)
        a, b = pts[k], pts[k + 1]
        out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    return out


def _rings_of(o: O) -> list[list[Pt]]:
    return [[(o.x + px * o.w, o.y + py * o.h) for px, py in r] for r in o.meta.get("vec", [])]


def _from_rings(o: O, rings: list[list[Pt]]) -> O:
    xs = [p[0] for r in rings for p in r]
    ys = [p[1] for r in rings for p in r]
    x0, y0 = min(xs), min(ys)
    w, h = max(max(xs) - x0, 1e-4), max(max(ys) - y0, 1e-4)
    norm = [[((px - x0) / w, (py - y0) / h) for px, py in r] for r in rings]
    meta = dict(o.meta, vec=norm, bbox=(0, 0, 1, 1))
    if o.rot and meta.get("grad"):  # поворот «запекается» в точки — градиент поворачивается вместе с ним
        meta["grad"] = dict(meta["grad"], angle=meta["grad"].get("angle", 90) + o.rot)
    return o.copy(kind="vec", x=x0, y=y0, w=w, h=h, rot=0.0, meta=meta, radius=None)


def map_points(objs: Sequence[O], f: Callable[[Pt], Pt], select: Sel = None) -> list[O]:
    """Произвольное преобразование точек контуров (для vec) и центров (для остальных)."""
    out = []
    for o in objs:
        if not _sel(o, select):
            out.append(o)
        elif o.kind == "vec":
            out.append(_from_rings(o, [[f(p) for p in r] for r in _rings_of(o)]))
        else:
            cx, cy = f(_center(o))
            out.append(_place(o, cx, cy))
    return out


# ----------------------------------------------------------------------------- положение

def explode(objs: Sequence[O], center: Pt, k: float = 0.5, select: Sel = None) -> list[O]:
    """Разлёт от центра: каждая часть отходит на k своего расстояния до центра (контур не искажается)."""
    out = []
    for o in objs:
        if not _sel(o, select):
            out.append(o)
            continue
        cx, cy = _center(o)
        out.append(o.copy(x=o.x + (cx - center[0]) * k, y=o.y + (cy - center[1]) * k))
    return out


def gather(objs: Sequence[O], point: Pt, scale: float = 0.2, select: Sel = None) -> list[O]:
    """Сбор в точку с уменьшением (части «втягиваются»)."""
    return [o.copy(x=point[0] + (o.x - point[0]) * scale, y=point[1] + (o.y - point[1]) * scale, w=o.w * scale,
                   h=o.h * scale, sz=o.sz * scale) if _sel(o, select) else o for o in objs]


def scatter(objs: Sequence[O], box: tuple[float, float, float, float], seed: int = 1, spin: float = 0.0,
            select: Sel = None) -> list[O]:
    """Рассыпать по рамке (случайно, но воспроизводимо); spin — случайный поворот до ±spin°."""
    rnd = random.Random(seed)
    bx, by, bw, bh = box
    out = []
    for o in objs:
        if not _sel(o, select):
            out.append(o)
            continue
        out.append(_place(o, bx + rnd.random() * bw, by + rnd.random() * bh, rot=o.rot + rnd.uniform(-spin, spin)))
    return out


def orbit(objs: Sequence[O], center: Pt, deg: float, spin_self: bool = True, select: Sel = None) -> list[O]:
    """Поворот системы вокруг центра на deg (по часовой). spin_self — фигуры поворачиваются вместе с системой."""
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    out = []
    for o in objs:
        if not _sel(o, select):
            out.append(o)
            continue
        if o.kind == "vec" and spin_self:
            out.append(map_points([o], lambda p: (center[0] + (p[0] - center[0]) * ca - (p[1] - center[1]) * sa,
                                                  center[1] + (p[0] - center[0]) * sa + (p[1] - center[1]) * ca))[0])
            continue
        cx, cy = _center(o)
        nx = center[0] + (cx - center[0]) * ca - (cy - center[1]) * sa
        ny = center[1] + (cx - center[0]) * sa + (cy - center[1]) * ca
        out.append(_place(o, nx, ny, rot=o.rot + (deg if spin_self and not o.lines else 0)))
    return out


def swirl(objs: Sequence[O], center: Pt, max_deg: float = 90, radius: float = 3.0, select: Sel = None) -> list[O]:
    """Вихрь: точка на расстоянии r поворачивается на max_deg·min(r/radius, 1) — внешние части «закручиваются»."""
    def f(p):
        r = math.dist(p, center)
        a = math.radians(max_deg * min(r / radius, 1.0))
        dx, dy = p[0] - center[0], p[1] - center[1]
        return center[0] + dx * math.cos(a) - dy * math.sin(a), center[1] + dx * math.sin(a) + dy * math.cos(a)
    return map_points(objs, f, select)


def wave(objs: Sequence[O], amp: float = 0.3, length: float = 4.0, phase: float = 0.0, axis: str = "y",
         select: Sel = None) -> list[O]:
    """Волна: смещение по оси axis = amp·sin(2π·x/length + phase). Серия состояний с ростом phase — бегущая волна."""
    def f(p):
        s = amp * math.sin(2 * math.pi * (p[0] if axis == "y" else p[1]) / length + phase)
        return (p[0], p[1] + s) if axis == "y" else (p[0] + s, p[1])
    return map_points(objs, f, select)


def along(objs: Sequence[O], path: Sequence[Pt], start: float = 0.0, end: float = 1.0, rotate: bool = False,
          select: Sel = None) -> list[O]:
    """Расставить объекты вдоль ломаной (равномерно по длине), rotate — по касательной."""
    chosen = [o for o in objs if _sel(o, select)]
    seg = [math.dist(a, b) for a, b in zip(path, path[1:])]
    L = sum(seg) or 1.0
    pos = {}
    for i, o in enumerate(chosen):
        d = L * (start + (end - start) * (i / max(len(chosen) - 1, 1)))
        k, acc = 0, 0.0
        while k < len(seg) - 1 and acc + seg[k] < d:
            acc += seg[k]
            k += 1
        f = (d - acc) / (seg[k] or 1.0)
        a, b = path[k], path[k + 1]
        ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        pos[o.name] = ((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), ang)
    out = []
    for o in objs:
        if o.name in pos:
            (x, y), ang = pos[o.name]
            out.append(_place(o, x, y, rot=ang if rotate else o.rot))
        else:
            out.append(o)
    return out


def fan(objs: Sequence[O], pivot: Pt, spread: float = 60.0, select: Sel = None) -> list[O]:
    """Веер: i-й объект поворачивается вокруг pivot на угол от −spread/2 до +spread/2 (карты, листы)."""
    chosen = [o for o in objs if _sel(o, select)]
    n = len(chosen)
    angles = {o.name: (-spread / 2 + spread * i / max(n - 1, 1)) for i, o in enumerate(chosen)}
    out = []
    for o in objs:
        out.append(orbit([o], pivot, angles[o.name])[0] if o.name in angles else o)
    return out


def peel(objs: Sequence[O], step: tuple[float, float] = (0.35, -0.25), order: Sequence[str] | None = None) -> list[O]:
    """Отслаивание: i-й слой (по order или по z) сдвигается на i·step — стопка раскрывается лесенкой."""
    names = list(order) if order else [o.name for o in sorted(objs, key=lambda o: o.z)]
    idx = {n: i for i, n in enumerate(names)}
    return [o.copy(x=o.x + step[0] * idx[o.name], y=o.y + step[1] * idx[o.name]) if o.name in idx else o for o in objs]


def lift(objs: Sequence[O], names: Sequence[str], scale: float = 1.35, dy: float = -0.25, shadow: bool = True,
         theme_bg: str = "bg") -> list[O]:
    """Выдвинуть часть «к зрителю»: увеличение, подъём и тень под ней (тень — отдельный объект !!shadow_*)."""
    out = []
    for o in objs:
        if o.name not in names:
            out.append(o)
            continue
        cx, cy = _center(o)
        big = o.copy(x=cx - o.w * scale / 2, y=cy - o.h * scale / 2 + dy, w=o.w * scale, h=o.h * scale,
                     z=o.z + 200, sz=o.sz * scale)
        if shadow:
            out.append(O(f"!!shadow_{o.name.lstrip('!')}", "oval", cx - o.w * scale * 0.45, cy + o.h * scale * 0.42,
                         o.w * scale * 0.9, o.h * 0.18, fill="ink", fa=0.18, z=o.z + 199, meta={"decor": True}))
        out.append(big)
    return out


# ----------------------------------------------------------------------------- пространство (2D -> 3D)

def tilt3d(objs: Sequence[O], center: Pt, pitch: float = 60.0, yaw: float = 0.0, dist: float = 14.0,
           select: Sel = None) -> list[O]:
    """Наклон плоскости в пространстве: pitch — «положить на стол» (вокруг горизонтальной оси), yaw — поворот
    вокруг вертикальной; перспектива с камерой на расстоянии dist (дюймы). Работает на контурах vec — вызывайте
    после to_vec, иначе двигаются только центры."""
    pc, ps = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    yc, ys = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))

    def f(p):
        x, y, z = p[0] - center[0], p[1] - center[1], 0.0
        x, z = x * yc + z * ys, -x * ys + z * yc
        y, z = y * pc - z * ps, y * ps + z * pc
        k = dist / (dist + z)
        return center[0] + x * k, center[1] + y * k
    return map_points(objs, f, select)


def recede(objs: Sequence[O], vanish: Pt, depth: float = 0.5, fade: float = 0.0, select: Sel = None) -> list[O]:
    """Уход в глубину к точке схода: масштаб (1 − depth) к vanish, затухание fade (0..1) заливки и линий."""
    k = 1 - depth
    out = []
    for o in objs:
        if not _sel(o, select):
            out.append(o)
            continue
        q = o.copy(x=vanish[0] + (o.x - vanish[0]) * k, y=vanish[1] + (o.y - vanish[1]) * k, w=o.w * k, h=o.h * k,
                   sz=o.sz * k, lw=o.lw * k, fa=o.fa * (1 - fade), la=o.la * (1 - fade))
        out.append(q)
    return out


def squash(objs: Sequence[O], center: Pt, sx: float = 1.0, sy: float = 0.35, select: Sel = None) -> list[O]:
    """Сплющивание относительно центра (дешёвая «перспектива сверху»; кольцо -> эллипс-орбита)."""
    return map_points(objs, lambda p: (center[0] + (p[0] - center[0]) * sx, center[1] + (p[1] - center[1]) * sy),
                      select)


def shear(objs: Sequence[O], center: Pt, kx: float = 0.4, select: Sel = None) -> list[O]:
    """Сдвиг (наклон) — грань «бокового» вида, курсив формы."""
    return map_points(objs, lambda p: (p[0] + (p[1] - center[1]) * kx, p[1]), select)


def fold(objs: Sequence[O], axis_x: float, angle: float = 70.0, select: Sel = None) -> list[O]:
    """Сгиб листа по вертикали x = axis_x: правая половина складывается к зрителю (cos-сжатие + перспектива)."""
    c = math.cos(math.radians(angle))
    return map_points(objs, lambda p: (axis_x + (p[0] - axis_x) * c, p[1]) if p[0] > axis_x else p, select)


# ----------------------------------------------------------------------------- цвет и ритм

def colorwave(objs: Sequence[O], origin: Pt, colors: Sequence[str], step: float = 1.0, phase: int = 0,
              select: Sel = None) -> list[O]:
    """Волна цвета от origin: цвет по кольцу расстояний (полоса шириной step); серия состояний с phase+1 —
    волна бежит."""
    out = []
    for o in objs:
        if not _sel(o, select) or o.fill is None:
            out.append(o)
            continue
        band = int(math.dist(_center(o), origin) / step) - phase
        out.append(o.copy(fill=colors[band % len(colors)]))
    return out


def cascade(objs: Sequence[O], origin: Pt, effect: str = "entrance_faded_zoom", speed: float = 0.12,
            delay: float = 0.15, dur: float = 0.35, select: Sel = None, options: dict | None = None) -> list:
    """Каскад появления по расстоянию от origin (волна от точки): список Fx для Slide.fx."""
    from .presets import Fx
    out = []
    for o in objs:
        if _sel(o, select) and o.name.startswith("!!"):
            out.append(Fx(effect, o.name, start="at", delay=delay + speed * math.dist(_center(o), origin), dur=dur,
                          options=dict(options or {})))
    return out


def stagger_by(objs: Sequence[O], key: Callable[[O], float], effect: str = "entrance_rise_up", delay: float = 0.15,
               step: float = 0.06, dur: float = 0.35, select: Sel = None) -> list:
    """Появление по порядку ключа (слева направо, по углу, по значению)."""
    from .presets import Fx
    chosen = sorted([o for o in objs if _sel(o, select) and o.name.startswith("!!")], key=key)
    return [Fx(effect, o.name, start="at", delay=delay + step * i, dur=dur) for i, o in enumerate(chosen)]


OPERATORS = {
    "explode": explode, "gather": gather, "scatter": scatter, "orbit": orbit, "swirl": swirl, "wave": wave,
    "along": along, "fan": fan, "peel": peel, "lift": lift, "tilt3d": tilt3d, "recede": recede, "squash": squash,
    "shear": shear, "fold": fold, "colorwave": colorwave,
}

__all__ = list(OPERATORS) + ["to_vec", "map_points", "cascade", "stagger_by", "OPERATORS"]
