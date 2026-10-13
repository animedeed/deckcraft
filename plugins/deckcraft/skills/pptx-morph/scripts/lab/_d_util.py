"""Общие помощники направления D («тематические мотивы»): текст-шапки, штрихи-ленты, кривые, сферы,
неровные кольца, «спиральный центр» (полёт по дуге с ростом), жидкость в сосуде с горизонтальной поверхностью.

Все функции возвращают shapely-геометрию или списки O; имена задаёт вызывающий (пары !! — его забота).
"""

from __future__ import annotations

import cmath
import math
import random
from typing import Sequence

from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Polygon, box

from morphkit import Loop, O, Slide
from morphkit import vector as V
from morphkit.theme import SLIDE_H, SLIDE_W, mix

W, H = SLIDE_W, SLIDE_H
DEC = {"bleed": True, "decor": True}


# ----------------------------------------------------------------------------- цвет

def tc(theme, role: str, fallback: str = "accent") -> str:
    """Роль темы -> hex; если роли нет (red_wine вне темы lab/cellar) — запасная роль."""
    return theme.colors.get(role) or theme.c(fallback)


def dark(c: str, k: float) -> str:
    return mix(c, "000000", k)


def light(c: str, k: float) -> str:
    return mix(c, "FFFFFF", k)


def is_dark(theme) -> bool:
    c = theme.c("bg")
    return sum(int(c[i:i + 2], 16) for i in (0, 2, 4)) < 3 * 110


# ----------------------------------------------------------------------------- текст

def head(text: str, x: float = 0.7, y: float = 0.55, w: float = 6.2, sz: float = 30, name: str = "!!ttl",
         col: str = "ink", h: float = 0.75) -> O:
    return O(name, "text", x, y, w, h, txt=text, sz=sz, b=True, font="head", col=col, z=90)


def kicker(text: str, x: float = 0.7, y: float = 0.3, w: float = 6.0, name: str = "!!kick", col: str = "accent") -> O:
    return O(name, "text", x, y, w, 0.3, txt=text, sz=12, b=True, caps=True, tracking=1.2, col=col, z=90)


def body(name: str, x: float, y: float, w: float, h: float, text, sz: float = 16, col: str = "ink2", **kw) -> O:
    return O(name, "text", x, y, w, h, txt=text, sz=sz, col=col, z=kw.pop("z", 90), **kw)


def label(name: str, x: float, y: float, text: str, w: float = 1.6, sz: float = 13, al: str = "c", col: str = "ink2",
          b: bool = False, h: float = 0.3, **kw) -> O:
    """Подпись с якорем: al='c' — x по центру, 'l' — x слева, 'r' — x справа."""
    bx = x - w / 2 if al == "c" else (x - w if al == "r" else x)
    return O(name, "text", bx, y, w, h, txt=text, sz=sz, col=col, al=al, b=b, z=kw.pop("z", 85),
             meta={"inset": 0.0, **kw.pop("meta", {})}, **kw)


# ----------------------------------------------------------------------------- геометрия

def vs(name: str, g, n: int = 0, start="top", **kw) -> O:
    """Свободная форма; n > 0 — ресемпл контура (для перелива пары); start — стартовая точка контура
    ('top' или угол от центра, 90 — низ: у жидкости дно стабильнее поверхности)."""
    return V.shape(name, V.resample(g, n, start=start) if n else g, **kw)


def biggest(g):
    if isinstance(g, MultiPolygon):
        return max(g.geoms, key=lambda p: p.area)
    return g


def stroke(pts: Sequence[tuple[float, float]], w_in: float, cap: int = 1) -> Polygon:
    """Лента-штрих по ломаной толщиной w_in дюймов (линия как свободная форма — её можно перелить)."""
    return LineString(pts).buffer(w_in / 2, cap_style=cap, join_style=1, quad_segs=6)


def taper(pts: Sequence[tuple[float, float]], w0: float, w1: float) -> Polygon:
    """Сужающаяся лента (ветка, жилка, хвост кометы): ширина от w0 у начала до w1 у конца."""
    left, right = [], []
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        a = pts[min(i + 1, n - 1)]
        b = pts[max(i - 1, 0)]
        dx, dy = a[0] - b[0], a[1] - b[1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        w = (w0 + (w1 - w0) * i / max(n - 1, 1)) / 2
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))
    g = Polygon(left + right[::-1])
    return g if g.is_valid else g.buffer(0)


def bezier(p0, p1, p2, p3, n: int = 40) -> list[tuple[float, float]]:
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def catenary(p0, p1, sag: float, n: int = 28) -> list[tuple[float, float]]:
    """Провисающий провод между p0 и p1 (парабола как приближение цепной линии), sag — провис в середине."""
    return [(p0[0] + (p1[0] - p0[0]) * i / n, p0[1] + (p1[1] - p0[1]) * i / n + 4 * sag * (i / n) * (1 - i / n))
            for i in range(n + 1)]


def wave(x0: float, x1: float, y: float, amp: float, periods: float, phase: float = 0.0, n: int = 80):
    return [(x0 + (x1 - x0) * i / n, y - amp * math.sin(2 * math.pi * periods * i / n + phase)) for i in range(n + 1)]


def arc_pts(cx: float, cy: float, r: float, a0: float, a1: float, n: int = 40):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]


def blob(cx: float, cy: float, r: float, seed: int = 1, amp: float = 0.07, n: int = 160, sx: float = 1.0,
         sy: float = 1.0) -> Polygon:
    """Неровный круг (пятно, клетка, капля): радиус r·(1 + сумма гармоник)."""
    rnd = random.Random(seed)
    harm = [(k, rnd.uniform(0.3, 1.0) * amp / k ** 0.6, rnd.uniform(0, 2 * math.pi)) for k in (2, 3, 5, 7)]
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        rr = r * (1 + sum(h * math.sin(k * a + ph) for k, h, ph in harm))
        pts.append((cx + rr * math.cos(a) * sx, cy + rr * math.sin(a) * sy))
    return Polygon(pts)


def stain_ring(cx: float, cy: float, r: float, th: float, seed: int = 1, amp: float = 0.05, n: int = 160) -> Polygon:
    """Кольцо-след от бокала: неровный внешний край, толщина меняется по кругу (одна дырка — Morph переливает)."""
    rnd = random.Random(seed)
    harm = [(k, rnd.uniform(0.3, 1.0) * amp / k ** 0.5, rnd.uniform(0, 2 * math.pi)) for k in (2, 3, 4, 7, 11)]
    tph = rnd.uniform(0, 2 * math.pi)
    outer, inner = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        ro = r * (1 + sum(h * math.sin(k * a + ph) for k, h, ph in harm))
        t = th * (0.55 + 0.45 * (1 + math.sin(a + tph)) / 2 + 0.25 * math.sin(3 * a + tph) ** 2)
        outer.append((cx + ro * math.cos(a), cy + ro * math.sin(a)))
        inner.append((cx + (ro - t) * math.cos(a), cy + (ro - t) * math.sin(a)))
    return Polygon(outer, [inner[::-1]])


def chord(poly, y: float) -> tuple[float, float] | None:
    """Хорда фигуры на высоте y: (x_left, x_right) или None."""
    minx, _, maxx, _ = poly.bounds
    seg = poly.intersection(LineString([(minx - 1, y), (maxx + 1, y)]))
    if seg.is_empty:
        return None
    xs = [c[0] for c in (seg.coords if hasattr(seg, "coords") else [p for g in seg.geoms for p in g.coords])]
    return min(xs), max(xs)


def level_for_area(poly, area: float, iters: int = 40) -> float:
    """Высота горизонтальной поверхности, при которой часть фигуры ниже неё имеет площадь area (жидкость в сосуде)."""
    _, miny, _, maxy = poly.bounds
    lo, hi = miny, maxy  # y вниз: больше y — ниже
    for _ in range(iters):
        mid = (lo + hi) / 2
        a = poly.intersection(box(-1e3, mid, 1e3, 1e3)).area
        if a > area:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def below(poly, y: float):
    return biggest(poly.intersection(box(-1e3, y, 1e3, 1e3)))


def band(poly, y0: float, y1: float):
    """Слой фигуры между высотами y0 < y1 (y вниз)."""
    return biggest(poly.intersection(box(-1e3, y0, 1e3, y1)))


def spiral_pivot(g: tuple[float, float], t: tuple[float, float], s: float, theta: float) -> tuple[float, float]:
    """Центр спирального подобия: точка p, для которой поворот на theta и растяжение в s раз вокруг p переводит g в t.
    Объект в рамке-квадрате с центром p: Morph размера и поворота рамки ведёт его по спирали от g к t, он растёт."""
    G, T = complex(*g), complex(*t)
    k = s * cmath.exp(1j * math.radians(theta))
    if abs(1 - k) < 1e-9:
        return g
    p = (T - k * G) / (1 - k)
    return p.real, p.imag


def rot_pt(p, deg: float, origin) -> tuple[float, float]:
    a = math.radians(deg)
    dx, dy = p[0] - origin[0], p[1] - origin[1]
    return origin[0] + dx * math.cos(a) - dy * math.sin(a), origin[1] + dx * math.sin(a) + dy * math.cos(a)


def pivot_frame(p: tuple[float, float], R: float) -> tuple[float, float, float, float]:
    return p[0] - R, p[1] - R, 2 * R, 2 * R


# ----------------------------------------------------------------------------- «объём» из 2D

def ball(theme, name: str, cx: float, cy: float, r: float, c: str, z: int = 20, fa: float = 1.0, light_k: float = 0.42,
         dark_k: float = 0.38, hl: bool = True, hl_a: float = 0.75, angle: float = 50.0, ln: str | None = None,
         lw: float = 0.0) -> list[O]:
    """Шар из круга: диагональный градиент (свет сверху слева) + блик. Имена: name и name+'h'."""
    out = [O(name, "oval", cx - r, cy - r, 2 * r, 2 * r, fill=c, fa=fa, ln=ln, lw=lw, z=z,
             meta={"grad": V.gradient([(0, light(c, light_k), fa), (0.55, c, fa), (1, dark(c, dark_k), fa)], angle=angle),
                   **DEC})]
    if hl:
        hr = r * 0.3
        out.append(O(name + "h", "oval", cx - r * 0.52, cy - r * 0.6, hr * 1.25, hr * 0.85, fill="FFFFFF",
                     fa=hl_a * fa, rot=-35, z=z + 1, meta=dict(DEC)))
    return out


def cyl_grad(c: str, fa: float = 1.0, k: float = 0.35) -> dict:
    """Горизонтальный «цилиндрический» градиент: тёмный край — свет левее середины — тёмный край."""
    return V.gradient([(0, dark(c, k), fa), (0.32, light(c, 0.28), fa), (0.6, c, fa), (1, dark(c, k * 1.2), fa)], angle=0)


def vgrad(c: str, fa: float = 1.0, top: float = 0.18, bot: float = 0.3) -> dict:
    return V.gradient([(0, light(c, top), fa), (1, dark(c, bot), fa)], angle=90)


# ----------------------------------------------------------------------------- слайд и петли

def S(objs: list[O], dur: int = 800, **kw) -> Slide:
    return Slide(objs, dur=min(dur, 900), **kw)


def flow(pts, n: int = 3, period: float = 2.2, size: float = 0.11, name: str = "flow", color: str = "flow",
         z: float = 5, start: float = 0.0, reverse: bool = False) -> Loop:
    return Loop("flow", points=[(float(x), float(y)) for x, y in pts], n=n, period=period, size=size, name=name,
                color=color, z=z, start=start, reverse=reverse)


def line(name: str, p0, p1, ln: str = "line", lw: float = 1.25, z: int = 4, **kw) -> O:
    return O(name, "line", p0[0], p0[1], p1[0] - p0[0], p1[1] - p0[1], ln=ln, lw=lw, z=z, **kw)


__all__ = [n for n in dir() if not n.startswith("_")]


def resample_line(pts, n: int) -> list[tuple[float, float]]:
    """Ломаная ровно из n точек, равномерно по длине (для перелива лент-линий одна в другую)."""
    ls = LineString(pts)
    L = ls.length
    return [(p.x, p.y) for p in (ls.interpolate(L * i / (n - 1)) for i in range(n))]


def ribbon(pts, w: float, n: int = 80) -> Polygon:
    """Лента постоянной ширины с явным соответствием точек: левый край вперёд, правый назад (2n точек).
    Две ленты с одинаковым n переливаются «точка в точку»: провод распрямляется в синусоиду, синусоида — в стрелку."""
    return taper(resample_line(pts, n), w, w)


def raw(name: str, g, **kw) -> O:
    """Свободная форма без ресемпла (точки уже согласованы, например у ribbon)."""
    return V.shape(name, g, **kw)
