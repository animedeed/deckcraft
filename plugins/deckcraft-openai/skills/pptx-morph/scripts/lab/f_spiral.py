"""Семейство «Спирали»: подсолнух (филлотаксис), спиральная лента времени и её разворот в прямую, путь по спирали
(маркер точно на кривой: в рамке на оси меняются и угол, и радиус), золотая спираль с бесконечным зумом, закрутка
галактики, воронка-водоворот, раковина-наутилус, спиральный календарь, двойная спираль ДНК в псевдо-3D.
"""

from __future__ import annotations

import math
import random

from morphkit import Loop, O, Slide
from morphkit import vector as V
from morphkit.presets import Fx
from morphkit.theme import mix

from lab import Variant
from lab._b_util import (arc_band, ax, axis, dashes, head, orbit_dot, pol, ribbon, shade, text)

FAM = "spiral"
GOLD = 137.50776
PHI = (1 + 5 ** 0.5) / 2
C = (9.1, 4.0)


def _phyllo(n, c, scale):
    return [pol(c[0], c[1], scale * math.sqrt(k + 0.5), k * GOLD) for k in range(n)]


def _dots(id, pts, d, cols, fa=1.0, z=10):
    out = []
    for i, (x, y) in enumerate(pts):
        dd = d[i] if isinstance(d, (list, tuple)) else d
        out.append(O(f"!!{id}{i}", "oval", x - dd / 2, y - dd / 2, dd, dd, fill=cols[i] if isinstance(cols, list) else cols,
                     fa=fa[i] if isinstance(fa, list) else fa, z=z))
    return out


def _beads(id, c, a, b, th_end, R, k=60, d=0.09, fill="accent", xf=None, z=6, fa=1.0, rot_override=None):
    """След из k бусин по архимедовой спирали до угла th_end: бусина i на (r(θi), θi) в рамке на оси —
    при смене th_end каждая бусина едет РОВНО по спирали (угол и радиус меняются вместе)."""
    from lab._b_util import ax as _ax
    out = []
    for i in range(k):
        th = th_end * i / (k - 1)
        r = a + b * math.radians(th)
        x, y = pol(c[0], c[1], r, th)
        if xf:
            x, y = xf(i, x, y)
        rot = th if rot_override is None else rot_override(i, th)
        out.append(_ax(f"!!{id}{i}", V.circle(x, y, d / 2, seg=8), rot, pivot=c, R=R, fill=fill, fa=fa, z=z))
    return out


# ----------------------------------------------------------------------------- 1. подсолнух из поля точек

def v_sunflower(theme) -> Variant:
    n = 220
    grid = [(C[0] - 2.6 + (i % 20) * 0.274, C[1] - 1.5 + (i // 20) * 0.274) for i in range(n)]
    sun = _phyllo(n, C, 0.17)
    cats = [0.5, 0.3, 0.2]
    cols3 = ["accent", "ink2", "muted"]

    def state(s, sub):
        objs = head("Подсолнух", sub)
        if s == 0:
            pts, d, cols = grid, 0.13, [shade(theme, "ink", 0.5)] * n
        elif s == 1:
            pts = sun
            d = [0.07 + 0.11 * math.sqrt(k / n) for k in range(n)]
            cols = [shade(theme, "ink", 0.2 + 0.5 * (1 - k / n)) for k in range(n)]
        else:
            # тот же подсолнух, раскрашенный по секторам-долям (порядок по углу сохранён)
            pts = sun
            d = [0.07 + 0.11 * math.sqrt(k / n) for k in range(n)]
            cols = []
            for k in range(n):
                a = (k * GOLD + 90) % 360 / 360
                cols.append(cols3[0] if a < cats[0] else (cols3[1] if a < cats[0] + cats[1] else cols3[2]))
        objs += _dots("sf", pts, d, cols)
        if s == 2:
            for j, (nm, v) in enumerate([("Новые", "50%"), ("Вернулись", "30%"), ("Ушли", "20%")]):
                objs.append(O(f"sq{j}", "oval", 0.75, 3.1 + j * 0.55, 0.22, 0.22, fill=cols3[j], z=6))
                objs.append(text(f"st{j}", 1.1, 3.0 + j * 0.55, 3.0, 0.4, f"{nm} · {v}", sz=15, col="ink2"))
        return objs

    return Variant(FAM, "sunflower", "Поле точек сворачивается в подсолнух",
                   "Сетка из 220 точек сворачивается в филлотаксис (золотой угол), размер растёт от центра; затем "
                   "семена окрашиваются секторами-долями. Роль: «все клиенты» → естественная структура → доли.",
                   [Slide(state(0, "220 клиентов"), dur=800), Slide(state(1, "Естественный порядок"), dur=900),
                    Slide(state(2, "Три типа"), dur=600)],
                   tags=["spiral", "phyllotaxis", "dots", "data"], score=4)


# ----------------------------------------------------------------------------- 2. спиральная лента времени разворачивается

def _arch(c, a, b, th0, th1, n):
    return [pol(c[0], c[1], a + b * math.radians(th0 + (th1 - th0) * k / (n - 1)), th0 + (th1 - th0) * k / (n - 1))
            for k in range(n)]


def _arclen(pts):
    out = [0.0]
    for p, q in zip(pts, pts[1:]):
        out.append(out[-1] + math.dist(p, q))
    return out


def v_timeline(theme) -> Variant:
    c = (8.6, 4.05)
    n = 160
    a, b = 0.35, 0.19
    th0, th1 = -90, -90 + 360 * 2.6
    sp = _arch(c, a, b, th0, th1, n)
    L = _arclen(sp)
    x0, x1, yl = 1.2, 12.3, 4.4
    line = [(x0 + (x1 - x0) * l / L[-1], yl) for l in L]
    events = [(10, "2017", "идея"), (45, "2019", "первый клиент"), (80, "2021", "100 клиентов"), (115, "2023", "выход в СНГ"),
              (152, "2025", "1000 клиентов")]

    def state(s, sub):
        objs = head("Лента времени", sub)
        pts = sp if s == 0 else line
        objs += dashes("tl", pts, 64, w=0.05, fill="ink2", duty=0.75, z=5)
        for j, (k, yr, nm) in enumerate(events):
            x, y = pts[k]
            d = 0.22 if j < 4 else 0.32
            objs.append(O(f"!!te{j}", "oval", x - d / 2, y - d / 2, d, d, fill="accent", z=8))
            if s == 1:
                up = j % 2 == 0
                objs.append(text(f"ty{j}", x - 1.0, y - 1.05 if up else y + 0.3, 2.0, 0.45, yr, sz=20, b=True,
                                 col="ink", al="c"))
                objs.append(text(f"tn{j}", x - 1.1, y - 0.62 if up else y + 0.72, 2.2, 0.4, nm, sz=14, col="ink2",
                                 al="c"))
        if s == 0:
            objs.append(text("tc", 0.7, 3.2, 3.6, 0.8, ["Девять лет", "по спирали"], sz=18, col="ink2"))
        return objs

    fx = [Fx("entrance_fade", f"ty{j}", start="at", delay=0.1 + 0.08 * j, dur=0.3) for j in range(5)] + \
         [Fx("entrance_fade", f"tn{j}", start="at", delay=0.14 + 0.08 * j, dur=0.3) for j in range(5)]
    return Variant(FAM, "timeline", "Спираль времени разворачивается в прямую",
                   "История компании свёрнута в архимедову спираль (прошлое в центре), затем лента разворачивается "
                   "в прямую — точки событий едут вместе с ней, появляются подписи. Роль: история, «как мы росли».",
                   [Slide(state(0, "Свёрнутая история"), dur=800), Slide(state(1, "Разворачиваем"), dur=900, fx=fx)],
                   tags=["spiral", "timeline", "unroll", "shape-morph"], score=4)


# ----------------------------------------------------------------------------- 3. путь точно по спирали

def v_path(theme) -> Variant:
    c = (8.9, 4.0)
    a, b = 0.25, 0.27
    turns = 2.4
    th1 = 360 * turns
    n = 200
    sp = _arch(c, a, b, 0, th1, n)
    stops = [(80, "Идея"), (300, "Прототип"), (465, "Пилот"), (630, "Рынок"), (795, "Масштаб")]
    R = a + b * math.radians(th1) + 0.3

    def state(k, sub):
        objs = head("Путь по спирали", sub)
        objs.append(V.shape("!!sp", ribbon(sp, 0.04), fill="line", z=4))
        # пройденный участок — та же спираль толще, до текущей вехи
        th = stops[k][0]
        objs += _beads("spb", c, a, b, th, R, 60, fill="accent")
        for j, (t, nm) in enumerate(stops):
            r = a + b * math.radians(t)
            x, y = pol(*c, r, t)
            on = j <= k
            objs.append(O(f"!!ss{j}", "oval", x - 0.1, y - 0.1, 0.2, 0.2, fill="accent" if on else "bg",
                          ln="accent" if on else "ink2", lw=1.25, z=8))
        r = a + b * math.radians(th)
        objs.append(orbit_dot("!!sm", c, r, th % 360, 0.36, R=R, fill="accent", ln="bg", lw=2.0, z=12))
        objs.append(text(f"sn{k}", 0.7, 3.4, 4.0, 0.7, stops[k][1], sz=34, b=True, col="ink", font="head"))
        objs.append(text(f"sk{k}", 0.7, 4.15, 4.0, 0.4, f"этап {k + 1} из 5", sz=15, col="muted"))
        return objs

    return Variant(FAM, "path", "Маркер едет точно по спирали",
                   "Маркер в рамке на оси меняет угол и радиус одновременно — у архимедовой спирали r линеен по углу, "
                   "поэтому он едет ровно по кривой; за ним тянется след из бусин, каждая тоже едет по спирали. Роль: этапы роста, «каждый круг "
                   "— шире предыдущего».",
                   [Slide(state(1, "Виток за витком"), dur=800), Slide(state(2, "Шире круг"), dur=850),
                    Slide(state(3, "Выход на рынок"), dur=850)],
                   tags=["spiral", "spiral-move", "roadmap", "progress"], score=4)


# ----------------------------------------------------------------------------- 4. золотая спираль: бесконечный зум

def _golden(n, x, y, w):
    h = w / PHI
    rx, ry, rw, rh = x, y, w, h
    sq, arcs = [], []
    for k in range(n):
        m = k % 4
        if m == 0:
            s = (rx, ry, rh, rh); cen, a0 = (rx + rh, ry + rh), 180; rx, rw = rx + rh, rw - rh
        elif m == 1:
            s = (rx, ry, rw, rw); cen, a0 = (rx, ry + rw), 270; ry, rh = ry + rw, rh - rw
        elif m == 2:
            s = (rx + rw - rh, ry, rh, rh); cen, a0 = (rx + rw - rh, ry), 0; rw = rw - rh
        else:
            s = (rx, ry + rh - rw, rw, rw); cen, a0 = (rx + rw, ry + rh - rw), 90; rh = rh - rw
        sq.append(s)
        arcs.append((cen, s[2], a0))
    eye = (rx + rw / 2, ry + rh / 2)
    return sq, arcs, eye


def v_golden(theme) -> Variant:
    sq, arcs, eye = _golden(16, 0.0, 0.0, 7.2)
    levels = ["Компания", "Направление", "Команда", "Человек"]
    # подобие T: квадрат k -> k+1 (масштаб 1/φ, поворот ±90° вокруг глаза)
    c0 = (sq[0][0] + sq[0][2] / 2, sq[0][1] + sq[0][3] / 2)
    c1 = (sq[1][0] + sq[1][2] / 2, sq[1][1] + sq[1][3] / 2)
    ang = math.degrees(math.atan2(c1[1] - eye[1], c1[0] - eye[0]) - math.atan2(c0[1] - eye[1], c0[0] - eye[0]))
    ang = (ang + 180) % 360 - 180
    target = (9.8, 4.5)

    def tf(g, s):
        g = V.scale(g, PHI ** s, origin=eye)
        g = V.move(g, target[0] - eye[0], target[1] - eye[1])
        return g

    def state(s, sub):
        objs = head("Ближе и ближе", sub)
        rot = -ang * s
        for k, (x, y, w, h) in enumerate(sq):
            g = V.rotate(tf(V.resample(V.rect(x, y, w, h), 4, start=-135), s), rot, origin=target)
            col = shade(theme, "ink", 0.86 - 0.05 * (k % 3)) if k != s + 2 else shade(theme, "accent", 0.55)
            objs.append(ax(f"!!gq{k}", g, rot, pivot=target, R=40, fill=col, fa=0.45, ln="line", lw=1.0, z=4 + k))
            (cx, cy), r, a0 = arcs[k]
            arc = arc_band(cx, cy, r - 0.03 / PHI ** (k / 2), r + 0.03 / PHI ** (k / 2), a0, a0 + 90, 16)
            arc = V.rotate(tf(arc, s), rot, origin=target)
            objs.append(ax(f"!!ga{k}", arc, rot, pivot=target, R=40, fill="accent", z=30 + k))
        objs.append(text(f"gl{s}", 0.7, 6.1, 3.8, 0.6, levels[s + 1], sz=26, b=True, col="accent", font="head"))
        return objs

    return Variant(FAM, "golden", "Золотая спираль: зум в глубину",
                   "Золотые прямоугольники и спираль: каждый шаг — масштаб ×φ и поворот на 90° вокруг «глаза» "
                   "спирали, поэтому картинка повторяет себя уровнем глубже (бесконечный зум без камеры). "
                   "Роль: переход от общего к частному, «из компании — в команду — в человека».",
                   [Slide(state(0, "Уровень за уровнем"), dur=850), Slide(state(1, "Шаг вглубь"), dur=900),
                    Slide(state(2, "Ещё глубже"), dur=900)],
                   tags=["spiral", "zoom", "self-similar", "rotation"], score=4)


# ----------------------------------------------------------------------------- 5. закрутка галактики

def v_galaxy(theme) -> Variant:
    rings = [(0.55, 10), (0.95, 16), (1.35, 22), (1.75, 28), (2.15, 34), (2.55, 40)]
    pts = [(r, 360 * i / m + (j % 2) * 180 / m, j) for j, (r, m) in enumerate(rings) for i in range(m)]

    def state(s, sub):
        objs = head("Закрутка", sub)
        twist = [0, 130, 260][s]
        for i, (r, a, j) in enumerate(pts):
            rot = a + twist * (r / 2.55) ** 1.0
            arm = ((a + 90 + 360) % 90) < 22
            col = "accent" if arm else shade(theme, "ink", 0.35 + 0.08 * j)
            d = 0.15 if arm else 0.11
            objs.append(orbit_dot(f"!!gx{i}", C, r, rot, d, R=2.75, fill=col, z=8))
        objs.append(O("!!gcore", "oval", C[0] - 0.22, C[1] - 0.22, 0.44, 0.44, fill="accent", z=9))
        return objs

    return Variant(FAM, "galaxy", "Кольца закручиваются в галактику",
                   "Концентрические кольца точек; каждая точка поворачивается на угол, растущий с радиусом, — "
                   "кольца закручиваются в рукава (все движения — по дугам). Роль: «из порядка — в движение», "
                   "рост сообщества вокруг ядра.",
                   [Slide(state(0, "Четыре луча"), dur=800), Slide(state(1, "Закручиваем"), dur=900),
                    Slide(state(2, "Рукава роста"), dur=900)],
                   tags=["spiral", "twist", "orbit", "dots"], score=3)


# ----------------------------------------------------------------------------- 6. воронка-водоворот

def v_vortex(theme) -> Variant:
    rnd = random.Random(3)
    n = 120
    base = [(1.0 + 1.6 * math.sqrt(rnd.random()), rnd.uniform(0, 360)) for _ in range(n)]
    order = sorted(range(n), key=lambda i: base[i][0])
    keep1 = set(order[:40])
    keep2 = set(order[:12])
    stages = [("Посетители", "12 000"), ("Заявки", "4 000"), ("Покупки", "1 200")]

    def state(s, sub):
        objs = head("Воронка-водоворот", sub)
        for i, (r, a) in enumerate(base):
            if s == 0:
                rr, aa, d, fa = 0.5 + r, a, 0.12, 1.0
            elif s == 1:
                alive = i in keep1
                rr = 0.35 + r * 0.55 if alive else 0.15
                aa, d, fa = a + 120, (0.13 if alive else 0.04), (1.0 if alive else 0.0)
            else:
                alive = i in keep2
                rr = 0.25 + r * 0.25 if alive else 0.1
                aa, d, fa = a + 240, (0.16 if alive else 0.03), (1.0 if alive else 0.0)
            col = "accent" if (s == 2 and i in keep2) else shade(theme, "ink", 0.35)
            objs.append(orbit_dot(f"!!vx{i}", C, rr, aa, d, R=3.2, fill=col, fa=fa, z=8))
        objs.append(text(f"vt{s}", 0.7, 3.3, 4.0, 1.4, [stages[s][1], stages[s][0]], sz=30, b=True, col="ink",
                         font="head"))
        return objs

    return Variant(FAM, "vortex", "Воронка как водоворот",
                   "Точки-клиенты закручиваются по спиралям к центру (в рамке на оси меняются угол и радиус), "
                   "отсеянные гаснут по пути; к концу остаётся ядро. Роль: воронка продаж без трапеций.",
                   [Slide(state(0, "Широкий вход"), dur=800), Slide(state(1, "Закручиваем"), dur=900),
                    Slide(state(2, "На выходе"), dur=900)],
                   tags=["spiral", "funnel", "spiral-move", "dots", "data"], score=3)


# ----------------------------------------------------------------------------- 7. наутилус: камеры роста

def _nautilus(c, n=12, a=0.8, k=0.18, t0=200.0, step=30.0, per=24):
    """Логарифмическая спираль r = a·e^(kθ); камера j — между витками θ−360° и θ на угловом отрезке j."""
    out = []
    for j in range(n):
        t1, t2 = t0 + j * step, t0 + (j + 1) * step
        f = lambda t: a * math.exp(k * math.radians(t - t0))  # noqa: E731
        outer = [pol(c[0], c[1], f(t1 + (t2 - t1) * q / (per - 1)), t1 + (t2 - t1) * q / (per - 1)) for q in range(per)]
        inner = [pol(c[0], c[1], f(t2 - 360 - (t2 - t1) * q / (per - 1)), t2 - (t2 - t1) * q / (per - 1))
                 for q in range(per)]
        out.append(V.Polygon(outer + inner))
    return out


def v_nautilus(theme) -> Variant:
    c = (8.0, 4.2)
    ch = _nautilus(c)
    names = {7: "Лид", 8: "Команда", 9: "Отдел", 10: "Направление", 11: "Партнёр"}

    def state(s, sub):
        objs = head("Наутилус роста", sub)
        for j, g in enumerate(ch):
            cg = g.centroid
            gg = g
            if s == 1:
                gg = V.move(g, (cg.x - c[0]) * 0.12, (cg.y - c[1]) * 0.12)
            col = shade(theme, "ink", 0.85 - 0.05 * j)
            if s == 2:
                col = "accent" if j == 9 else shade(theme, "ink", 0.85 - 0.04 * j)
            objs.append(V.shape(f"!!nc{j}", V.resample(gg, 64), fill=col, ln="bg", lw=1.5, z=6 + j))
            if s >= 1 and j in names:
                ang = math.degrees(math.atan2(cg.y - c[1], cg.x - c[0]))
                rr = math.hypot(cg.x - c[0], cg.y - c[1]) * 1.12
                x, y = pol(c[0], c[1], rr + 1.0, ang)
                al = "l" if x > c[0] + 0.5 else ("r" if x < c[0] - 0.5 else "c")
                bx = x - 0.9 if al == "c" else (x - 0.3 if al == "l" else x - 1.5)
                on = s == 2 and j == 9
                objs.append(text(f"!!nl{j}", bx, y - 0.2, 1.8, 0.4, names[j], sz=15, b=on,
                                 col="accent" if on else "ink2", al=al, va="m"))
        return objs

    return Variant(FAM, "nautilus", "Раковина-наутилус: камеры роста",
                   "Логарифмическая спираль, разбитая на камеры, каждая больше предыдущей; камеры чуть расходятся "
                   "и получают имена, одна подсвечивается. Роль: карьерная лестница, этапы зрелости.",
                   [Slide(state(0, "Каждая камера больше прежней"), dur=800),
                    Slide(state(1, "Ступени"), dur=850), Slide(state(2, "Вы здесь"), dur=600)],
                   tags=["spiral", "fragment", "growth"], score=3)


# ----------------------------------------------------------------------------- 8. спиральный календарь -> кольца лет

def v_calendar(theme) -> Variant:
    c = (8.9, 4.0)
    rnd = random.Random(8)
    vals = [[0.3 + 0.6 * (0.5 + 0.5 * math.sin(math.radians(30 * m - 60))) * (0.7 + 0.15 * y) + rnd.uniform(-0.08, 0.08)
             for m in range(12)] for y in range(3)]
    years = ["2023", "2024", "2025"]
    w = 0.42

    def state(s, sub):
        objs = head("Календарь-спираль", sub)
        for y in range(3):
            for m in range(12):
                t = y + m / 12
                a0 = -90 + 30 * m + 1
                a1 = a0 + 28
                if s == 0:
                    r0 = 1.0 + 0.55 * t
                    r1 = 1.0 + 0.55 * (t + 1 / 12)
                    out = [pol(*c, r0 + (r1 - r0) * q / 11 + w, a0 + 28 * q / 11) for q in range(12)]
                    inn = [pol(*c, r1 - (r1 - r0) * q / 11, a1 - 28 * q / 11) for q in range(12)]
                    g = V.Polygon(out + inn)
                else:
                    r0 = 1.0 + 0.6 * y
                    g = arc_band(c[0], c[1], r0, r0 + w, a0, a1, 12)
                v = min(max(vals[y][m], 0), 1)
                col = mix(theme.c("surface2"), theme.c("accent"), v)
                objs.append(V.shape(f"!!cm{y}_{m}", g, fill=col, z=6))
            if s >= 1:
                objs.append(text(f"!!cy{y}", c[0] - 0.65, c[1] - 1.0 - 0.6 * y - w / 2 - 0.2 + 0.03, 1.3, 0.4, years[y],
                                 sz=12, col="ink" if s == 1 else ("accent" if y == 2 else "muted"), al="c", va="m",
                                 b=True, z=40))
        objs.append(text("!!cleg", 0.7, 3.2, 4.0, 0.8, ["Цвет — продажи", "за месяц"], sz=15, col="muted"))
        return objs

    return Variant(FAM, "calendar", "Спиральный календарь → кольца лет",
                   "Три года продаж по спирали (виток = год, месяц = сегмент, цвет = объём); спираль "
                   "раскладывается в три кольца — месяцы разных лет встают друг под другом. Роль: сезонность за "
                   "несколько лет на одной фигуре.",
                   [Slide(state(0, "Три года подряд"), dur=800), Slide(state(1, "Год под годом"), dur=900),
                    Slide(state(2, "Лето всё сильнее"), dur=600)],
                   tags=["spiral", "calendar", "heatmap", "data"], score=3)


# ----------------------------------------------------------------------------- 9. ДНК: двойная спираль в псевдо-3D

def v_dna(theme) -> Variant:
    n = 22
    x0, x1, yc, amp = 3.4, 12.2, 4.3, 1.0

    def state(s, sub):
        objs = head("Двойная спираль", sub)
        ph = [0, 40, 80][s] if s < 2 else 80
        flat = s == 2
        for i in range(n):
            x = x0 + (x1 - x0) * i / (n - 1)
            a = math.radians(i * 32 + ph)
            ya, yb = yc - amp * math.sin(a), yc + amp * math.sin(a)
            da, db = math.cos(a), -math.cos(a)  # глубина: +1 — ближе
            if flat:
                ya, yb, da, db = yc - 0.9, yc + 0.9, 0.5, 0.5
            for nm, y, d, col in ((f"!!da{i}", ya, da, "accent"), (f"!!db{i}", yb, db, "ink")):
                sz = 0.16 + 0.12 * (d + 1) / 2
                objs.append(O(nm, "oval", x - sz / 2, y - sz / 2, sz, sz, fill=col, fa=0.45 + 0.55 * (d + 1) / 2,
                              z=10 + int(5 * d) + 5))
            top, bot = min(ya, yb), max(ya, yb)
            objs.append(O(f"!!dr{i}", "rect", x - 0.015, top, 0.03, max(bot - top, 0.01), fill="line", z=6))
        if flat:
            objs.append(text("dtx", 0.7, 3.4, 2.5, 1.2, ["Две цепочки", "— одна", "система"], sz=16, col="ink2"))
        return objs

    return Variant(FAM, "dna", "ДНК вращается и раскладывается",
                   "Две цепочки точек на синусоидах со сдвигом фазы: размер и прозрачность по глубине дают объём, "
                   "сдвиг фазы — вращение; затем спираль раскладывается в плоскую лестницу. "
                   "Роль: две связанные линии (продукт и данные), «ДНК компании».",
                   [Slide(state(0, "Две цепочки"), dur=800), Slide(state(1, "Вращение"), dur=800),
                    Slide(state(2, "Раскладываем"), dur=800)],
                   tags=["spiral", "helix", "pseudo-3d", "metaphor"], score=3)


# ----------------------------------------------------------------------------- ЖИВАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ 1: спираль развития

def seq_growth(theme) -> Variant:
    """8 состояний: спираль -> маркер к вехе 1 со следом -> лупа на вехе с деталью -> маркер и лупа к вехе 3 по спирали ->
    спираль разворачивается в прямую ленту -> бусины следа ссыпаются в столбики по годам -> снова спираль до конца ->
    спираль ложится в перспективу и уходит назад."""
    c = (9.0, 4.0)
    a, b = 0.25, 0.27
    th_max = 800
    sp = _arch(c, a, b, 0, th_max, 220)
    L = _arclen(sp)
    x0, x1, yl = 1.0, 12.4, 4.6
    line = [(x0 + (x1 - x0) * l / L[-1], yl) for l in L]
    stops = [(150, "2018", "Идея"), (310, "2020", "Прототип"), (470, "2022", "Пилот"), (630, "2024", "Рынок"),
             (790, "2025", "Масштаб")]
    R = 9.6
    K = 60
    years_cnt = [4, 8, 12, 16, 20]
    K2 = sum(years_cnt)

    def th_at(th):
        return a + b * math.radians(th)

    def line_pos(th):
        k = min(int(th / th_max * 219), 219)
        return line[k]

    def sq(x, y, st):
        if st == 7:
            return c[0] + 1.3 + (x - c[0]) * 0.75, c[1] - 0.8 + (y - c[1]) * 0.3
        return x, y

    th_marker = {0: 0, 1: 150, 2: 150, 3: 310, 4: 470, 5: 470, 6: 630, 7: 790}
    heads = [("Девять лет", "Путь по спирали"), ("2018 · Идея", "Маркер на первой вехе"),
             ("2018 · Идея", "Лупа на вехе"), ("2020 · Прототип", "Лупа едет по спирали"),
             ("Прямая линия", "Спираль разворачивается"), ("Клиенты по годам", "След ссыпается в столбики"),
             ("2024 · Рынок", "Снова по спирали"), ("Каждый виток шире", "Спираль уходит в глубину")]
    slides = []
    for st in range(8):
        objs = head(*heads[st])
        pts = line if st in (4, 5) else [sq(x, y, st) for x, y in sp]
        objs += dashes("gsp", pts, 90, w=0.035, fill="line", duty=0.7, z=4, fa=0.6 if st == 7 else 1.0)
        thm = th_marker[st]
        # след: K2 бусин
        for i in range(K2):
            th = thm * i / (K2 - 1)
            x, y = pol(*c, th_at(th), th)
            rot = th
            if st in (4, 5):
                x, y = line_pos(th)
            if st == 5:
                yr = next(j for j in range(5) if i < sum(years_cnt[:j + 1]))
                kk = i - sum(years_cnt[:yr])
                xs = line_pos(stops[yr][0])[0]
                x, y = xs + (kk % 2) * 0.17 - 0.085, yl - 0.25 - (kk // 2) * 0.17
            x, y = sq(x, y, st)
            objs.append(ax(f"!!gb{i}", V.circle(x, y, 0.06, seg=8), rot, pivot=c, R=R, fill="accent",
                           fa=(0.5 if st == 7 else 1.0) if thm > 0 else 0.0, z=6))
        for j, (th, yr, nm) in enumerate(stops):
            x, y = pol(*c, th_at(th), th)
            if st in (4, 5):
                x, y = line_pos(th)
            x, y = sq(x, y, st)
            on = th <= thm
            objs.append(ax(f"!!gm{j}", V.circle(x, y, 0.11, seg=10), th, pivot=c, R=R, fill="accent" if on else "bg",
                           ln="accent" if on else "ink2", lw=1.25, z=8))
            if st in (4, 5):
                objs.append(text(f"gy{j}", x - 0.6, yl + 0.25, 1.2, 0.4, yr, sz=15, b=True, col="ink", al="c"))
            if st == 5:
                objs.append(text(f"gc{j}", x - 0.6, yl - 0.32 - (years_cnt[j] // 2) * 0.17 - 0.45, 1.2, 0.4,
                                 f"{years_cnt[j] * 25}", sz=14, col="ink2", al="c"))
        r = th_at(thm)
        mx, my = pol(*c, r, thm)
        if st in (4, 5):
            mx, my = line_pos(thm)
        mx, my = sq(mx, my, st)
        objs.append(ax("!!gmk", V.circle(mx, my, 0.19, seg=12), thm, pivot=c, R=R, fill="accent", ln="bg", lw=2.0,
                       z=12))
        if st in (2, 3):
            rr = th_at(thm)
            lens = arc_band(c[0], c[1], rr - 0.3, rr + 0.3, thm - 22, thm + 22, 20)
            objs.append(ax("!!glens", lens, thm, pivot=c, R=R, fill="accent", fa=0.15, ln="accent", lw=2.0, z=14))
            tx = ["Команда из трёх человек", "Первые 10 клиентов"][st - 2]
            objs.append(text(f"gd{st}", 0.7, 3.4, 4.3, 0.9, tx, sz=22, b=True, col="accent", font="head"))
        if st == 7:
            objs.append(text("gfin", 0.7, 4.6, 6.2, 1.4, ["1000 клиентов", "к 2025 году"], sz=36, b=True, col="ink",
                             font="head"))
        fx = [Fx("entrance_fade", f"gd{st}", start="at", delay=0.1, dur=0.35)] if st in (2, 3) else []
        if st == 5:
            fx = [Fx("entrance_fade", f"gc{j}", start="at", delay=0.1 + 0.06 * j, dur=0.3) for j in range(5)]
        slides.append(Slide(objs, dur=[800, 850, 600, 850, 900, 850, 900, 900][st], fx=fx))
    return Variant(FAM, "seq_growth", "Живая спираль развития (8 состояний)",
                   "Маркер и след из бусин идут точно по спирали от вехи к вехе, лупа встречает веху и едет дальше "
                   "вместе с маркером; затем спираль разворачивается в прямую ленту, бусины следа ссыпаются в "
                   "столбики по годам, снова сворачиваются в спираль и уходят в перспективу под вывод. "
                   "Роль: история компании через весь доклад.",
                   slides, tags=["seq", "spiral", "spiral-move", "unroll", "chart", "magnifier", "3d"], score=4)


# ----------------------------------------------------------------------------- ЖИВАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ 2: подсолнух

def seq_sunflower(theme) -> Variant:
    """7 состояний: поле -> подсолнух -> подсвечен рукав -> рукав выходит в ряд -> секторы-доли расходятся ->
    каждый сектор собирается в свой подсолнух -> всё вместе в перспективе уходит назад."""
    n = 210
    c = (9.0, 4.05)
    sc = 0.165
    sun = _phyllo(n, c, sc)
    arm = [k for k in range(n) if k % 21 == 5]
    shares = [0.5, 0.3, 0.2]
    gcol = ["accent", "ink2", "accent3"]
    gname = ["Новые", "Вернулись", "Ушли"]

    def cat(k):
        a = (k * GOLD + 90) % 360 / 360
        return 0 if a < shares[0] else (1 if a < shares[0] + shares[1] else 2)

    cats = [cat(k) for k in range(n)]
    members = [[k for k in range(n) if cats[k] == g] for g in range(3)]
    centers = [(4.0, 4.3), (7.6, 4.3), (10.7, 4.3)]
    heads = [("210 клиентов", "Поле"), ("Естественный порядок", "Золотой угол"), ("Один рукав", "Клиенты одного года"),
             ("Рукав в ряд", "Десять ключевых"), ("Три доли", "Секторы расходятся"), ("Три сегмента", "Каждый — своим кругом"),
             ("Половина — новые", "Картина уходит на фон")]
    slides = []
    for st in range(7):
        objs = head(*heads[st])
        for k in range(n):
            x, y = sun[k]
            d = 0.07 + 0.1 * math.sqrt(k / n)
            col = shade(theme, "ink", 0.2 + 0.45 * (1 - k / n))
            fa = 1.0
            if st == 0:
                x, y, d = c[0] - 2.6 + (k % 21) * 0.26, c[1] - 1.3 + (k // 21) * 0.26, 0.12
                col = shade(theme, "ink", 0.5)
            if st in (2, 3) and k in arm:
                col, d = "accent", d * 1.4
            if st == 3:
                if k in arm:
                    j = arm.index(k)
                    x, y, d = 0.95 + j * 0.42, 3.4, 0.24
                else:
                    col = shade(theme, "ink", 0.75)
            if st >= 4:
                col = gcol[cats[k]]
            if st == 4:
                a = math.degrees(math.atan2(y - c[1], x - c[0]))
                mid = {0: -90 + 90, 1: 90 + 54, 2: 270 - 36}[cats[k]]
                dx, dy = pol(0, 0, 0.45, mid)
                x, y = x + dx, y + dy
            if st == 5:
                g = cats[k]
                j = members[g].index(k)
                x, y = pol(*centers[g], 0.19 * math.sqrt(j + 0.5), j * GOLD)
                d = 0.11
            if st == 6:
                x, y = c[0] + 1.6 + (x - c[0]) * 0.8, c[1] - 1.0 + (y - c[1]) * 0.8 * 0.36
                depth = (y - (c[1] - 1.0)) / (2.7 * 0.36) * 0.5 + 0.5
                d, fa = d * (0.6 + 0.6 * depth), 0.35 + 0.4 * depth
            objs.append(O(f"!!sf{k}", "oval", x - d / 2, y - d / 2, d, d, fill=col, fa=fa, z=10))
        if st == 3:
            objs.append(text("sfa", 0.85, 2.5, 4.6, 0.5, "Клиенты 2024 года", sz=18, b=True, col="accent"))
        if st == 4:
            for g, (lx, ly) in enumerate([(12.0, 4.6), (6.0, 5.9), (6.0, 2.2)]):
                objs.append(text(f"sfl{g}", lx - 0.6, ly - 0.2, 1.6, 0.4, f"{int(shares[g] * 100)}%", sz=18, b=True,
                                 col="ink", al="c"))
        if st == 5:
            for g in range(3):
                objs.append(text(f"sfn{g}", centers[g][0] - 1.3, 6.25, 2.6, 0.4,
                                 f"{gname[g]} · {len(members[g])}", sz=15, col="ink2", al="c"))
        if st == 6:
            objs.append(text("sffin", 0.7, 4.6, 6.4, 1.4, ["105 из 210 —", "новые клиенты"], sz=36, b=True, col="ink",
                             font="head"))
        slides.append(Slide(objs, dur=[800, 900, 600, 850, 850, 900, 900][st]))
    return Variant(FAM, "seq_sunflower", "Живой подсолнух (7 состояний)",
                   "Поле точек сворачивается в подсолнух, один рукав спирали подсвечивается и выходит в ряд, "
                   "семена окрашиваются по долям и секторы расходятся, каждый сектор собирается в свой маленький "
                   "подсолнух, затем всё ложится в перспективу и уходит на фон под вывод. Роль: сквозная база клиентов.",
                   slides, tags=["seq", "spiral", "phyllotaxis", "dots", "groups", "3d"], score=4)


def variants(theme) -> list[Variant]:
    return [v_sunflower(theme), v_timeline(theme), v_path(theme), v_golden(theme), v_galaxy(theme), v_vortex(theme),
            v_nautilus(theme), v_calendar(theme), v_dna(theme), seq_growth(theme), seq_sunflower(theme)]
