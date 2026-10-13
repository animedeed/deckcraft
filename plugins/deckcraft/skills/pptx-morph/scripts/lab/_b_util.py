"""Общие помощники направления B «Круги и движение по кругу» (кольца, орбиты, спирали, шестерни, линии, радар).

Главные приёмы:
  * axis()       — форма в квадратной рамке на оси: rot и его морфинг ведут её по дуге вокруг оси;
  * arc_pieces() — дуга кольца из k кусочков на оси: при смене длины дуги кусочки ПОВОРАЧИВАЮТСЯ вдоль круга,
                   а не переливаются по хордам — прогресс растёт строго по кольцу, без «клина»;
  * arc_band()/bar_band() — сегмент кольца и прямая полоса с одинаковым числом и порядком точек:
                   кольцо «разворачивается» в столбик переливом формы;
  * orbit_dot()/comet() — спутник и хвост кометы из убывающих точек на оси;
  * spiral_move — форма в рамке на оси меняет и угол, и радиус: путь — спираль (переход с орбиты на орбиту);
  * gear()       — шестерня из shapely с трапециевидными зубцами (контур с постоянным числом точек).
"""

from __future__ import annotations

import math
from typing import Sequence

from morphkit import O
from morphkit import vector as V
from morphkit.theme import mix

SW, SH = 13.333, 7.5


# ----------------------------------------------------------------------------- точки

def pol(cx: float, cy: float, r: float, a: float) -> tuple[float, float]:
    """Точка на окружности; угол a в градусах, 0 — вправо, по часовой стрелке на экране (ось y вниз)."""
    return cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))


def arc_pts(cx, cy, r, a0, a1, n) -> list[tuple[float, float]]:
    return [pol(cx, cy, r, a0 + (a1 - a0) * k / (n - 1)) for k in range(n)]


def ellipse_pts(cx, cy, rx, ry, n=96, tilt=0.0, a0=0.0, closed=True) -> list[tuple[float, float]]:
    """Точки эллипса (для пути петли flow). tilt — поворот эллипса в градусах. closed — последняя = первая."""
    out = []
    ct, st = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    m = n + 1 if closed else n
    for k in range(m):
        a = math.radians(a0 + 360 * k / n)
        x, y = rx * math.cos(a), ry * math.sin(a)
        out.append((cx + x * ct - y * st, cy + x * st + y * ct))
    return out


# ----------------------------------------------------------------------------- формы с управляемым порядком точек

def arc_band(cx, cy, r_in, r_out, a0, a1, n=48) -> V.Polygon:
    """Сегмент кольца: внешняя дуга a0→a1 (n точек), затем внутренняя a1→a0 (n точек). Всегда 2n точек."""
    return V.Polygon(arc_pts(cx, cy, r_out, a0, a1, n) + arc_pts(cx, cy, r_in, a1, a0, n))


def bar_band(x, y, length, thick, n=48) -> V.Polygon:
    """Прямая полоса с тем же порядком точек, что у arc_band: верх слева направо, низ справа налево."""
    length = max(length, 1e-3)
    top = [(x + length * k / (n - 1), y) for k in range(n)]
    bot = [(x + length * (n - 1 - k) / (n - 1), y + thick) for k in range(n)]
    return V.Polygon(top + bot)


def ribbon(pts: Sequence[tuple[float, float]], w: float) -> V.Polygon:
    """Лента вдоль ломаной толщиной w (дюймы): левый край вперёд, правый назад — 2·len(pts) точек."""
    left, right = [], []
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[max(i - 1, 0)]
        x1, y1 = pts[min(i + 1, n - 1)]
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy) or 1e-9
        nx, ny = -dy / L * w / 2, dx / L * w / 2
        left.append((pts[i][0] + nx, pts[i][1] + ny))
        right.append((pts[i][0] - nx, pts[i][1] - ny))
    return V.Polygon(left + right[::-1])


def thin(p, q, w=0.02) -> V.Polygon:
    """Тонкая линия-четырёхугольник (морфится по точкам, без переворотов коннектора)."""
    return ribbon([p, q], w)


def gear(cx, cy, r_root, r_tip, teeth, phase=0.0, tooth=0.5, top=0.55, per=6, hole=0.0) -> V.Polygon:
    """Шестерня: teeth зубцов (зубец 0 смотрит на угол phase); tooth — доля шага под зубцом у основания,
    top — ширина вершины от ширины основания. per — точек на вершину и на впадину: всего 2·per·teeth точек.
    hole — радиус отверстия (одна дырка — форма ещё морфится)."""
    step = 360.0 / teeth
    wb = step * tooth
    wt = wb * top
    pts = []
    for k in range(teeth):
        a = phase + k * step
        pts += [pol(cx, cy, r_tip, a - wt / 2 + wt * j / (per - 1)) for j in range(per)]
        pts += [pol(cx, cy, r_root, a + wb / 2 + (step - wb) * j / (per - 1)) for j in range(per)]
    if hole > 0:
        return V.Polygon(pts, [list(V.circle(cx, cy, hole, seg=12).exterior.coords)[::-1]])
    return V.Polygon(pts)


# ----------------------------------------------------------------------------- объекты

def axis(name: str, g, pivot: tuple[float, float], R: float, rot: float = 0.0, **kw) -> O:
    """Форма в квадратной рамке радиуса R с центром на оси pivot: rot вращает её вокруг pivot (по дуге)."""
    px, py = pivot
    kw.setdefault("z", 6)
    return V.shape(name, g, frame=(px - R, py - R, 2 * R, 2 * R), rot=rot % 360, **kw)


def arc_pieces(id: str, c: tuple[float, float], r_in: float, r_out: float, a0: float, a1: float, k: int = 10,
               R: float | None = None, overlap: float = 0.35, n: int = 10, **kw) -> list[O]:
    """Дуга кольца из k кусочков на оси c. Кусочек j нарисован от 0° до span (+перекрытие) и повёрнут на
    a0 + j·span. При смене a0/a1 на соседнем слайде кусочки вращаются по кругу — дуга растёт строго по кольцу.
    Шаг поворота последнего кусочка (k−1)/k·Δ должен быть < 180°."""
    span = (a1 - a0) / k
    R = R or r_out * 1.001
    out = []
    for j in range(k):
        g = arc_band(c[0], c[1], r_in, r_out, 0.0, max(span, 0.01) + (overlap if j < k - 1 else 0.0), n)
        out.append(axis(f"{id}{j}", g, c, R, rot=a0 + j * span, **kw))
    return out


def orbit_dot(name: str, pivot, r: float, ang: float, d: float, R: float | None = None, **kw) -> O:
    """Круг-спутник диаметра d на радиусе r вокруг pivot, угол ang (рамка на оси)."""
    g = V.circle(pivot[0] + r, pivot[1], d / 2, seg=12)
    return axis(name, g, pivot, R or (r + d / 2) * 1.001, rot=ang, **kw)


def comet(id: str, pivot, r: float, ang: float, d: float = 0.3, n: int = 8, gap: float = 0.2, fill="accent",
          bg="0B0B0D", z: int = 12, cw: bool = True, fade: float = 0.85) -> list[O]:
    """Голова кометы (угол ang) и хвост из n убывающих точек позади по дуге. gap — шаг хвоста по дуге (дюймы),
    шаг растёт к концу хвоста. cw — движение по часовой: хвост «сзади» = меньшие углы."""
    out = [orbit_dot(f"!!{id}h", pivot, r, ang, d, fill=fill, z=z + n)]
    s = 0.0
    for k in range(1, n + 1):
        t = k / (n + 1)
        s += gap * (1 + 0.6 * t)
        a = ang - math.degrees(s / r) * (1 if cw else -1)
        out.append(orbit_dot(f"!!{id}t{k}", pivot, r, a, d * (1 - 0.75 * t), R=(r + d / 2) * 1.001,
                             fill=mix(fill, bg, fade * t), z=z + n - k))
    return out


def text(name, x, y, w, h, txt, sz=14, col="ink2", al="l", va="t", b=False, font="body", z=30, **kw) -> O:
    return O(name, "text", x, y, w, h, txt=txt, sz=sz, col=col, al=al, va=va, b=b, font=font, z=z, **kw)


def head(title: str, sub: str | None = None, x: float = 0.7, y: float = 0.55, w: float = 5.6) -> list[O]:
    out = [O("!!ttl", "text", x, y, w, 0.7, txt=title, sz=30, b=True, font="head", col="ink", z=50)]
    if sub:
        out.append(O("!!sub", "text", x, y + 0.78, w, 0.9, txt=sub, sz=16, col="muted", z=50))
    return out


def ring_track(name, c, r_in, r_out, fill="surface2", z=4, **kw) -> O:
    g = V.subtract(V.circle(c[0], c[1], r_out), V.circle(c[0], c[1], r_in))
    return V.shape(name, g, fill=fill, z=z, **kw)


def outline_circle(name, c, r, ln="line", lw=1.0, z=3, **kw) -> O:
    return O(name, "oval", c[0] - r, c[1] - r, 2 * r, 2 * r, fill=None, ln=ln, lw=lw, z=z, **kw)


def shade(theme, role: str, t: float, to: str = "bg") -> str:
    """Роль цвета, смешанная с фоном (t=0 — чистый цвет, t=1 — фон)."""
    return mix(theme.c(role), theme.c(to), t)


def shortest(a: float, b: float) -> float:
    """b, приведённый к a так, чтобы |b − a| ≤ 180 (для явного контроля направления)."""
    return a + ((b - a + 180) % 360) - 180


def ax(name: str, g_abs, rot: float, pivot=(9.0, 3.95), R: float = 9.6, **kw) -> O:
    """Сквозная форма живой последовательности: ОДНА рамка (ось pivot, радиус R) во всех состояниях.
    g_abs — где форма должна оказаться на слайде; rot — угол рамки. Внутри рамки хранится g_abs, повёрнутая на −rot,
    поэтому смена rot ведёт форму по дуге вокруг оси, а смена g_abs — линейный перелив точек в координатах слайда.
    Так одна и та же фигура может ехать по кругу, разворачиваться в панель, наклоняться и уходить на фон."""
    local = V.rotate(g_abs, -rot, origin=pivot)
    meta = dict(kw.pop("meta", {}))
    meta.setdefault("bleed", True)
    return axis(name, local, pivot, R, rot=rot, meta=meta, **kw)


def rect_band(x, y, w, h, n=48, vertical=False) -> V.Polygon:
    """Прямоугольник с порядком точек arc_band (2n точек). vertical=False: верх слева направо (n), низ справа налево;
    vertical=True: левая сторона снизу вверх (n), правая сверху вниз — для колонок из сегментов кольца."""
    if not vertical:
        return bar_band(x, y, w, h, n)
    left = [(x, y + h - h * k / (n - 1)) for k in range(n)]
    right = [(x + w, y + h * k / (n - 1)) for k in range(n)]
    return V.Polygon(left + right)


def squash(g, c, k, dy=0.0) -> V.Polygon:
    """Сжатие по вертикали к центру c (наклон плоскости «к зрителю») и сдвиг по y: линейно, морфится точно."""
    pts = [(x, c[1] + (y - c[1]) * k + dy) for x, y in list(g.exterior.coords)[:-1]]
    return V.Polygon(pts)


def move_scale(g, c, k, dx=0.0, dy=0.0) -> V.Polygon:
    pts = [(c[0] + (x - c[0]) * k + dx, c[1] + (y - c[1]) * k + dy) for x, y in list(g.exterior.coords)[:-1]]
    return V.Polygon(pts)


def comet_ax(id: str, c, r: float, ang: float, d: float = 0.3, n: int = 7, gap: float = 0.16, fill="F5A300",
             bg="0B0B0D", z: int = 12, R: float = 9.6, xf=None, fa: float = 1.0, size_k=None) -> list[O]:
    """Комета в общей рамке живой последовательности (ось c, радиус рамки R): голова на (r, ang), хвост позади.
    xf(x, y) -> (x, y) — преобразование плоскости (наклон, уход на фон); size_k(x, y) -> множитель размера (глубина)."""
    xf = xf or (lambda x, y: (x, y))
    out, s = [], 0.0
    for k in range(n + 1):
        t = k / (n + 1)
        if k:
            s += gap * (1 + 0.6 * t)
        a = ang - math.degrees(s / r)
        x, y = xf(*pol(c[0], c[1], r, a))
        dd = d * (1 - 0.75 * t) * (size_k(x, y) if size_k else 1.0)
        nm = f"!!{id}h" if k == 0 else f"!!{id}t{k}"
        out.append(ax(nm, V.circle(x, y, dd / 2, seg=10), a, pivot=c, R=R, fill=mix(fill, bg, 0.85 * t), fa=fa,
                      z=z + n - k))
    return out


def dashes(id: str, pts, n: int, w: float = 0.04, fill="line", duty: float = 0.7, z: int = 4, **kw) -> list[O]:
    """Кривая как цепочка из n коротких штрихов вдоль точек pts. Для перелива «кривая -> другая кривая» (спираль ->
    прямая) это надёжнее одной ленты: у ленты промежуточная линия самопересекается и петли заливаются."""
    out = []
    m = len(pts) - 1
    for k in range(n):
        i0 = int(m * k / n)
        i1 = max(i0 + 1, int(m * (k + duty) / n))
        seg = pts[i0:i1 + 1]
        out.append(V.shape(f"!!{id}{k}", ribbon(seg, w), fill=fill, z=z, **kw))
    return out


def arc_pieces_ax(id: str, c, r_in: float, r_out: float, a0: float, a1: float, k: int = 6, xf=None, n: int = 8,
                  R: float = 9.6, overlap: float = 0.35, **kw) -> list[O]:
    """Как arc_pieces, но в общей рамке живой последовательности: кусочки едут по кругу при смене углов, а xf
    (наклон, уход на фон) применяется к их точкам — дуга может и расти по кольцу, и ложиться в перспективу."""
    span = (a1 - a0) / k
    out = []
    for j in range(k):
        s0 = a0 + j * span
        g = arc_band(c[0], c[1], r_in, r_out, s0, s0 + max(span, 0.01) + (overlap if j < k - 1 else 0.0), n)
        if xf:
            g = V.Polygon([xf(x, y) for x, y in list(g.exterior.coords)[:-1]])
        out.append(ax(f"{id}{j}", g, s0, pivot=c, R=R, **kw))
    return out
