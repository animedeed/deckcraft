"""Природа: годичные кольца (рост = новые кольца у коры; спил в перспективе → вид сверху), жилкование листа
(жилки рисуются по очереди и переливаются в дерево-иерархию), ветвящийся рост (новые ветви вырастают из кончиков),
семена одуванчика улетают по дугам и кувыркаются, деление клеток, подсолнух (филлотаксис) из поля точек.

Тема прогона — forest («Лес»).
"""

from __future__ import annotations

import math
import random

from shapely import affinity

from morphkit import Fx, Loop, O
from morphkit import vector as V
from morphkit.theme import SLIDE_H, SLIDE_W, mix

from lab import Variant
from lab._d_util import (DEC, S, bezier, body, cyl_grad, dark, flow, head, kicker, label, light, line, raw, resample_line, ribbon,
                         rot_pt, spiral_pivot, stroke, taper, vs)

FAM = "nature"
W, H = SLIDE_W, SLIDE_H


def _v(key, title, idea, slides, tags, score) -> Variant:
    return Variant(FAM, key, title, idea, slides, tags=tags, score=score)


def wood(theme):
    return mix(theme.c("accent"), "8B5A2B", 0.45)


# ============================================================================= кольца

def ring_poly(c, r_in, r_out, seed=1, sy=1.0, n=120, amp=0.035):
    """Кольцо с явными точками (n снаружи + n внутри): неровность общая для всех колец (одна древесина)."""
    rnd = random.Random(seed)
    harm = [(k, rnd.uniform(0.4, 1.0) * amp / k ** 0.5, rnd.uniform(0, 6.28)) for k in (2, 3, 5)]
    def rr(r, a):
        return r * (1 + sum(h * math.sin(k * a + ph) for k, h, ph in harm))
    outer = [(c[0] + rr(r_out, 2 * math.pi * i / n) * math.cos(2 * math.pi * i / n), c[1] + sy * rr(r_out, 2 * math.pi * i / n) * math.sin(2 * math.pi * i / n)) for i in range(n)]
    inner = [(c[0] + rr(r_in, 2 * math.pi * i / n) * math.cos(2 * math.pi * i / n), c[1] + sy * rr(r_in, 2 * math.pi * i / n) * math.sin(2 * math.pi * i / n)) for i in range(n)]
    return V.Polygon(outer, [inner[::-1]]) if r_in > 0.001 else V.Polygon(outer)


WIDTHS = [0.32, 0.22, 0.26, 0.14, 0.12, 0.2, 0.24, 0.1, 0.16, 0.18]  # условные ширины колец (годы)


def rings_objs(theme, c, k_rings, sy=1.0, scale=1.0, focus=None, alpha=1.0, z=10, side=0.0, bark_w=0.14, id="rg"):
    """k_rings видимых колец; остальные — нулевой толщины у коры (будут «нарастать» снаружи). side > 0 — боковина
    ствола (цилиндр) высотой side под эллипсом спила (перспектива)."""
    wd = wood(theme)
    out = []
    R = sum(WIDTHS[:k_rings]) * scale
    if side > 0:
        g = V.union(V.rect(c[0] - R - bark_w, c[1], 2 * (R + bark_w), side), V.ellipse(c[0], c[1] + side, R + bark_w, sy * (R + bark_w)))
        out.append(vs(f"!!{id}_side", g, 140, start=90, fill=dark(wd, 0.35), grad=cyl_grad(dark(wd, 0.25), alpha, 0.4), fa=alpha, z=z - 2,
                      meta=dict(DEC)))
    else:
        g = V.ellipse(c[0], c[1], R + bark_w, sy * (R + bark_w))
        out.append(vs(f"!!{id}_side", g, 140, start=90, fill=dark(wd, 0.35), fa=0.0, z=z - 2, meta=dict(DEC)))
    r = 0.0
    for i in range(len(WIDTHS)):
        w_ = WIDTHS[i] * scale if i < k_rings else 0.004
        r_in, r_out = r, r + w_
        r = r_out if i < k_rings else r
        col = light(wd, 0.35) if i % 2 == 0 else wd
        if focus == i:
            col = theme.c("accent")
        out.append(raw(f"!!{id}{i}", ring_poly(c, r_in if i < k_rings else R, r_out if i < k_rings else R + 0.004, sy=sy), fill=col,
                       fa=alpha, ln=dark(wd, 0.3), lw=0.5, la=alpha, z=z + i, meta=dict(DEC)))
    out.append(raw(f"!!{id}_bark", ring_poly(c, R, R + bark_w, seed=1, sy=sy), fill=dark(wd, 0.5), fa=alpha, z=z + 20, meta=dict(DEC)))
    return out


def tree_rings(theme) -> Variant:
    c = (8.8, 3.3)
    sl = []
    for st, (k, sy, side) in enumerate([(4, 0.42, 2.4), (8, 0.42, 2.4), (10, 1.0, 0.0)]):
        cc = c if st < 2 else (8.8, 3.9)
        o = rings_objs(theme, cc, k, sy=sy, scale=1.15, side=side)
        o += [head(["Спил: четыре года", "Восемь колец", "Вид сверху"][st], w=6),
              body("!!b", 0.7, 1.4, 5, 0.8, ["кольцо — один год роста", "новые кольца — у коры", "ширина — условный прирост"][st],
                   sz=16, col="muted")]
        sl.append(S(o, 900))
    return _v("tree_rings", "Кольца нарастают у коры, спил разворачивается",
              "Рост = появление колец: новые кольца нарастают снаружи (из нулевой толщины у коры), старые на месте; "
              "спил в перспективе (эллипс + цилиндр ствола с градиентом) разворачивается в вид сверху — 3D → 2D.",
              sl, ["nature", "growth", "3d", "shape-morph"], 4)


def log_pointer(theme) -> Variant:
    secs = ["Почва", "Корни", "Ствол", "Крона"]
    sl = []
    c = (-0.6, 3.75)
    for k in range(3):
        o = rings_objs(theme, c, 10, scale=1.35, focus=None)
        # кольца разделов: группы колец; раздел k — его кольца акцентом
        groups = [(0, 2), (3, 5), (6, 7), (8, 9)]
        o = [ob.copy(fill=theme.c("accent")) if ob.name in {f"!!rg{i}" for i in range(groups[k][0], groups[k][1] + 1)} else ob for ob in o]
        r_acc = 0.0
        for gi, (a, b) in enumerate(groups):
            r_mid = sum(WIDTHS[:a]) * 1.35 + sum(WIDTHS[a:b + 1]) * 1.35 / 2
            y = 3.75 - 0.0
            o.append(label(f"!!sc{gi}", c[0] + sum(WIDTHS) * 1.35 + 0.45, 2.2 + gi * 0.55, f"0{gi + 1} {secs[gi]}", w=2.2, al="l", sz=13,
                           b=gi == k, col="accent" if gi == k else "muted"))
        o += [kicker(f"раздел {k + 1}", x=5.8), head(secs[k], x=5.8, w=7),
              body("!!txt", 5.8, 1.5, 7, 1.0, ["вода и минералы", "сеть, которой не видно", "годы роста в разрезе"][k], sz=20)]
        sl.append(S(o, 700))
    return _v("log_pointer", "Спил у края: кольца = разделы",
              "Навигация: спил срезан левым краем, группы колец от сердцевины к коре — разделы по порядку; текущая "
              "группа подсвечена золотом. Презентация «растёт изнутри наружу».",
              sl, ["nature", "pointer", "navigation"], 3)


# ============================================================================= лист

def leaf_shape(c, L, Wd, angle=-90):
    return V.petal(c, 0.0, L, Wd, angle)


def veins(c, L, nv=4, Wd=None):
    """Срединная жилка + боковые жилки (по nv с каждой стороны): списки точек от основания к кончику.
    Wd — ширина листа: кончики жилок не выходят за край (80 % полуширины на высоте кончика)."""
    from lab._d_util import chord
    leaf = leaf_shape(c, L, Wd or L * 0.52)
    mid = [(c[0], c[1] - L * t) for t in [i / 30 for i in range(31)]]
    side = []
    for k in range(nv):
        t = 0.18 + 0.62 * k / (nv - 1)
        base = (c[0], c[1] - L * t)
        for sgn in (-1, 1):
            ty = c[1] - L * t - L * 0.14
            ch = chord(leaf, ty) or (c[0] - 0.1, c[0] + 0.1)
            tip = (c[0] + sgn * 0.8 * (ch[1] - ch[0]) / 2, ty)
            side.append(bezier(base, (base[0] + sgn * 0.15, base[1] - 0.05), (tip[0] - sgn * 0.1, tip[1] + 0.12), tip, 16))
    return mid, side


def leaf_venation(theme) -> Variant:
    c, L, Wd = (9.0, 6.6), 5.6, 2.9
    green = theme.c("accent2")
    mid, side = veins(c, L, Wd=Wd)
    sl = []
    leaf = vs("!!leaf", leaf_shape(c, L, Wd), 160, fill=dark(green, 0.25), fa=0.85,
              grad=V.gradient([(0, light(green, 0.1)), (1, dark(green, 0.4))], 0), z=5)
    o1 = [leaf, raw("!!mid", ribbon(mid, 0.07, 40), fill="accent", z=10)] + [head("Лист", w=4)]
    for k, s_ in enumerate(side):
        o1.append(raw(f"!!vn{k}", ribbon(s_, 0.04, 40), fill="accent", z=10))
    fx1 = [Fx("entrance_wipe", "!!mid", start="at", delay=0.1, dur=0.5, options={"direction": "up"})]
    fx1 += [Fx("entrance_wipe", f"!!vn{k}", start="at", delay=0.5 + 0.1 * (k // 2), dur=0.3,
               options={"direction": "left" if k % 2 else "right"}) for k in range(len(side))]
    sl.append(S(o1, 700, fx=fx1))
    # 2: лист растворяется, жилки становятся деревом-иерархией (ствол — вертикаль, ветви — ступени)
    o2 = [vs("!!leaf", leaf_shape(c, L, Wd), 160, fill=dark(green, 0.25), fa=0.12, z=5)]
    top = (6.8, 1.6)
    o2.append(raw("!!mid", ribbon([(6.8, 6.4), (6.8, 1.6)], 0.07, 40), fill="accent", z=10))
    labels = ["Сбор", "Очистка", "Признаки", "Модель", "Проверка", "Отчёт", "Внедрение", "Поддержка"]
    for k, s_ in enumerate(side):
        lvl = k // 2
        sgn = -1 if k % 2 == 0 else 1
        y = 5.6 - lvl * 1.15
        pts = [(6.8, y + 0.3), (6.8 + sgn * 0.3, y), (6.8 + sgn * 2.2, y)]
        o2.append(raw(f"!!vn{k}", ribbon(pts, 0.04, 40), fill="accent", z=10))
        o2.append(label(f"vl{k}", 6.8 + sgn * 2.3, y - 0.17, labels[k], w=1.8, al="l" if sgn > 0 else "r", sz=13))
    o2 += [head("Жилки = иерархия", w=5)]
    sl.append(S(o2, 900, fx=[Fx("entrance_fade", f"vl{k}", start="at", delay=0.2 + 0.04 * k) for k in range(len(side))]))
    return _v("leaf_venation", "Жилки листа → дерево-иерархия",
              "Жилки рисуются по очереди (срединная снизу вверх, боковые — от неё наружу), затем лист бледнеет, а те же "
              "ленты-жилки (согласованные точки) выпрямляются в схему-иерархию с подписями. Метафора «структура "
              "растёт из одного стебля».",
              sl, ["nature", "growth", "shape-morph", "hierarchy"], 4)


def leaf_steps(theme) -> Variant:
    c, L, Wd = (10.2, 6.5), 5.0, 2.6
    green = theme.c("accent2")
    leaf = leaf_shape(c, L, Wd)
    topics = ["Свет", "Вода", "CO₂", "Сахар"]
    cuts = [c[1] - L * t for t in (0.0, 0.27, 0.5, 0.73, 1.0)]
    parts = [leaf.intersection(V.box(0, cuts[i + 1], W, cuts[i])) for i in range(4)]
    sl = []
    for k in range(3):
        o = [kicker("раздел 2 · фотосинтез"), head(f"Шаг {k + 1}: {topics[k]}", w=6),
             body("!!b", 0.7, 1.45, 5, 0.4, f"{(k + 1) * 25} % раздела", sz=16, col="accent")]
        for i, g in enumerate(parts):
            on = i <= k
            o.append(vs(f"!!lp{i}", g, fill=green if on else theme.c("surface2"), ln=theme.c("bg"), lw=1.5, z=10 + i,
                        grad=V.gradient([(0, light(green, 0.15)), (1, dark(green, 0.3))], 0) if on else None))
            o.append(label(f"!!lt{i}", c[0] - Wd / 2 - 0.4, (cuts[i] + cuts[i + 1]) / 2 - 0.17, topics[i], w=1.8, al="r", sz=14,
                           b=i == k, col="accent" if i == k else ("ink2" if on else "muted")))
        sl.append(S(o, 600))
    return _v("leaf_steps", "Лист закрашивается долями",
              "Прогресс внутри раздела (как деления лепестка): лист разрезан жилками на 4 доли = 4 темы; доли "
              "зеленеют снизу вверх 25 → 50 → 75 %, подпись текущей — золотом.",
              sl, ["nature", "progress"], 4)


def leaf_backdrop(theme) -> Variant:
    green = theme.c("accent2")
    sl = []
    for st in range(2):
        c, L, Wd = (10.4 + st * 0.5, 9.6), 9.5, 5.0
        ang = -100 + st * 8
        mid, side = veins(c, L, Wd=Wd)
        o = [vs("!!leaf", V.rotate(leaf_shape(c, L, Wd), ang + 90, origin=c), 160, fill=green, fa=0.1, z=-300, meta=dict(DEC)),
             raw("!!mid", V.rotate(ribbon(mid, 0.1, 40), ang + 90, origin=c), fill=green, fa=0.18, z=-299, meta=dict(DEC))]
        o += [raw(f"!!vn{k}", V.rotate(ribbon(s_, 0.06, 40), ang + 90, origin=c), fill=green, fa=0.15, z=-299, meta=dict(DEC))
              for k, s_ in enumerate(side)]
        o += [head(["Лес как система", "Что измеряем"][st], w=7),
              body("!!txt", 0.7, 1.5, 6.5, 2.2, [["почва, вода, свет", "конкуренция деревьев", "прирост по годам"],
                                                 ["диаметр ствола", "высоту и крону", "ширину колец"]][st], sz=22, col="ink")]
        sl.append(S(o, 800))
    return _v("leaf_backdrop", "Огромный бледный лист под текстом",
              "Фон: лист с жилками в 2 раза больше слайда, 10–18 % прозрачности, наклонён; между слайдами "
              "поворачивается на 8° вокруг черешка и чуть смещается.",
              sl, ["nature", "backdrop"], 3)


# ============================================================================= ветвление

def branches(depth, base=(6.6, 6.9), L0=1.7, ang0=-90, spread=24, shrink=0.74, seed=2):
    """Рекурсивное дерево: [(путь, p0, p1, ширина)] — путь ('', 'l', 'lr', …) даёт постоянные имена ветвей."""
    rnd = random.Random(seed)
    out = []
    def rec(path, p0, L, ang, w, d):
        a = math.radians(ang)
        p1 = (p0[0] + L * math.cos(a), p0[1] + L * math.sin(a))
        out.append((path, p0, p1, w))
        if d + 1 < depth:
            j = rnd.uniform(-6, 6)
            rec(path + "l", p1, L * shrink * rnd.uniform(0.92, 1.05), ang - spread + j, w * 0.68, d + 1)
            rec(path + "r", p1, L * shrink * rnd.uniform(0.92, 1.05), ang + spread + j, w * 0.68, d + 1)
    rec("", base, L0, ang0, 0.26, 0)
    return out


def tree_objs(theme, depth, full=7, leaves=False, alpha=1.0, base=(6.6, 6.9), scale=1.0, z=10, leaf_col=None):
    wd = dark(wood(theme), 0.1)
    allb = branches(full, base=base, L0=1.7 * scale)
    tips = {}
    for path, p0, p1, w in allb:
        tips[path] = (p0, p1, w * scale)
    out = []
    for path, (p0, p1, w) in tips.items():
        d = len(path)
        if d < depth:
            g = taper(resample_line([p0, p1], 10), w, w * 0.72)
        else:  # ещё не выросла: нулевая длина в начале ветви (у кончика родителя)
            q = (p0[0] + (p1[0] - p0[0]) * 0.01, p0[1] + (p1[1] - p0[1]) * 0.01)
            g = taper(resample_line([p0, q], 10), w * 0.3, w * 0.2)
        out.append(raw(f"!!b{path or 'o'}", g, fill=wd, fa=alpha if d < depth else 0.0, z=z + d, meta=dict(DEC)))
    if leaves:
        rnd = random.Random(5)
        for path, (p0, p1, w) in tips.items():
            if len(path) == depth - 1:
                r = 0.22 * scale * rnd.uniform(0.8, 1.2)
                out.append(O(f"!!lf{path}", "oval", p1[0] - r, p1[1] - r, 2 * r, 2 * r, fill=leaf_col or theme.c("accent2"), fa=0.85 * alpha,
                             z=z + 30, meta=dict(DEC)))
    return out


def branching(theme) -> Variant:
    sl = []
    for st, d in enumerate([2, 4, 7]):
        o = tree_objs(theme, d, leaves=st == 2) + [head(["Росток", "Ветвится", "Крона"][st], w=4),
                                                   body("!!b", 0.7, 1.4, 4.5, 0.8, [f"уровней: {d}", "каждый кончик делится на два",
                                                                                    "127 ветвей из одного правила"][st], sz=16, col="muted")]
        new = [ob.name for ob in o if ob.name.startswith("!!lf")]
        sl.append(S(o, 900, fx=[Fx("entrance_zoom", n_, start="at", delay=0.3 + 0.01 * k, dur=0.3) for k, n_ in enumerate(new[:40])]))
    return _v("branching", "Ветви вырастают из кончиков",
              "Рекурсивный рост: у каждой ветви постоянное имя-путь (l, lr, lrl…); ещё не выросшие ветви лежат нулевой "
              "длины у кончика родителя, поэтому Morph «выращивает» их из нужной точки. 2 → 4 → 7 уровней, листья "
              "проявляются зумом.",
              sl, ["nature", "growth", "recursion", "tree"], 4)


# ============================================================================= семена

def seed_geom(c, L=0.55):
    """Семя одуванчика: стебелёк + зонтик-хохолок из 7 лучей (одна форма), вершина зонтика вверх."""
    x, y = c
    parts = [stroke([(x, y), (x, y - L)], 0.02), V.ellipse(x, y + 0.06, 0.04, 0.08)]
    for k in range(7):
        a = math.radians(-90 - 60 + 20 * k)
        parts.append(stroke([(x, y - L), (x + 0.32 * math.cos(a), y - L + 0.32 * math.sin(a))], 0.012))
    return V.union(*parts)


def seeds(theme) -> Variant:
    head_c = (4.0, 3.2)
    n = 22
    rnd = random.Random(3)
    stem = [vs("!!stem", stroke(bezier((4.1, 7.6), (4.2, 6.0), (3.9, 4.6), (4.0, 3.3), 30), 0.07), fill=theme.c("accent2"), z=5)]
    sl = []
    homes, angs = [], []
    for i in range(n):
        a = -90 + (i - (n - 1) / 2) * (300 / n)
        angs.append(a)
        homes.append(rot_pt((head_c[0], head_c[1] + 0.05), a + 90, head_c))
    # цели: 3 группы на земле справа (кластеры)
    groups = [(8.0, 6.3), (10.2, 5.9), (12.0, 6.4)]
    targets = []
    for i in range(n):
        g = groups[i % 3]
        targets.append((g[0] + rnd.uniform(-0.6, 0.6), g[1] + rnd.uniform(-0.25, 0.25)))
    flying = [(5.5 + 6.5 * (i / n) + rnd.uniform(-0.5, 0.5), 1.4 + 2.6 * rnd.random()) for i in range(n)]
    for st in range(3):
        o = list(stem) + [O("!!core", "oval", head_c[0] - 0.12, head_c[1] - 0.12, 0.24, 0.24, fill="muted", z=6)]
        for i in range(n):
            g0 = seed_geom((head_c[0], head_c[1]))  # семя у центра головки, лучом вверх
            if st == 0:
                o.append(vs(f"!!sd{i}", g0, pivot=head_c, rot=(angs[i] + 90) % 360, fill="ink2", z=10 + i))
            else:
                t = flying[i] if st == 1 else targets[i]
                rot_t = (angs[i] + 90) + (60 + 25 * (i % 4)) * (1 if st == 1 else 1.0) + (0 if st == 1 else 50)
                rot_t = rot_t if st == 1 else (rot_t - 0)
                # поворот рамки на угол delta вокруг центра спирали p переносит семя по дуге к цели
                delta = 70 + 15 * (i % 5) if st == 1 else 70 + 15 * (i % 5) + 40
                p = spiral_pivot(head_c, t, 1.0, delta)
                g = V.rotate(g0, angs[i] + 90 - delta + (rot_t - (angs[i] + 90)) * 0.0, origin=head_c)
                o.append(vs(f"!!sd{i}", g, pivot=p, rot=delta % 360, fill="ink2" if st == 1 else theme.c("accent"), z=10 + i))
        o += [head(["Одуванчик", "Ветер", "Новые места"][st], w=5),
              body("!!b", 0.7, 1.4, 5, 0.8, ["22 семени на одной головке", "семена кувыркаются по дугам", "три новые колонии"][st],
                   sz=16, col="muted")]
        sl.append(S(o, 900))
    return _v("seeds", "Семена улетают по дугам и кувыркаются",
              "Каждое семя — форма в рамке, центр которой — центр поворота, переносящего семя к цели (спиральное "
              "подобие без роста): Morph ведёт семя по дуге и одновременно переворачивает его. Головка → полёт → три "
              "колонии на земле (кластеры). Разброс, распространение, «данные разлетаются».",
              sl, ["nature", "arc", "pivot", "cluster", "fragment"], 4)


# ============================================================================= клетки

def cells(theme) -> Variant:
    green = theme.c("accent2")
    sl = []
    base = (8.6, 4.0)
    def cell(name, c, r, sx=1.0, sy=1.0, seed=1, fa=1.0):
        mem = V.resample(affinity.scale(V.circle(c[0], c[1], r), sx, sy, origin=c), 120)
        nuc = V.resample(affinity.scale(V.circle(c[0], c[1], r * 0.36), sx ** 0.5, sy ** 0.5, origin=c), 60)
        return [vs(f"!!{name}", mem, fill=green, fa=0.28 * fa, ln=green, lw=2.0, la=fa, z=10),
                vs(f"!!{name}n", nuc, fill=theme.c("accent"), fa=0.85 * fa, z=12)]
    states = [
        [(base, 1.6, 1, 1)] * 4,
        [((base[0] - 0.9, base[1]), 1.15, 1.25, 0.9)] * 2 + [((base[0] + 0.9, base[1]), 1.15, 1.25, 0.9)] * 2,
        [((base[0] - 1.25, base[1] - 1.2), 1.05, 1, 1), ((base[0] - 1.35, base[1] + 1.2), 1.05, 1, 1),
         ((base[0] + 1.3, base[1] - 1.15), 1.05, 1, 1), ((base[0] + 1.25, base[1] + 1.25), 1.05, 1, 1)],
    ]
    for st, cs in enumerate(states):
        o = [head(["Одна клетка", "Деление", "Четыре клетки"][st], w=5), body("!!b", 0.7, 1.4, 5, 0.4, ["1", "1 → 2", "2 → 4"][st], sz=20, col="accent")]
        for i, (c, r, sx, sy) in enumerate(cs):
            o += cell(f"c{i}", c, r, sx, sy, fa=1.0 if (st > 0 or i == 0) else 0.0)
        sl.append(S(o, 900))
    return _v("cells", "Клетка делится: 1 → 2 → 4",
              "Четыре клетки с самого начала лежат одна в другой (видна одна), на делении расходятся парами с "
              "вытянутой мембраной, затем — на четыре. Ядра делятся вместе с клетками. Масштабирование, рост команды, "
              "«одна идея → много решений».",
              sl, ["nature", "split", "growth"], 3)


def phyllotaxis(theme) -> Variant:
    n = 144
    c = (8.8, 3.95)
    ga = math.radians(137.508)
    grid_ = [(4.4 + (i % 16) * 0.55, 1.6 + (i // 16) * 0.56) for i in range(n)]
    spiral = [(c[0] + 0.24 * math.sqrt(i + 1) * math.cos(i * ga), c[1] + 0.24 * math.sqrt(i + 1) * math.sin(i * ga)) for i in range(n)]
    sl = []
    for st in range(3):
        o = [head(["144 точки данных", "Золотой угол", "Подсолнух"][st], w=5),
             body("!!b", 0.7, 1.4, 4, 0.8, ["таблицей", "каждая следующая — на 137,5°", "размер — от центра"][st], sz=16, col="muted")]
        for i in range(n):
            x, y = grid_[i] if st == 0 else spiral[i]
            r = 0.09 if st < 2 else 0.05 + 0.1 * math.sqrt(i / n)
            col = theme.c("accent") if st < 2 or i % 8 else theme.c("accent3")
            o.append(O(f"!!d{i}", "oval", x - r, y - r, 2 * r, 2 * r, fill=col, z=10 + (n - i)))
        sl.append(S(o, 900))
    return _v("phyllotaxis", "Поле точек складывается в подсолнух",
              "Перестановка носителя: 144 точки из таблицы перелетают на спираль золотого угла (филлотаксис), затем "
              "размер растёт от центра к краю. Красивый способ показать «много однотипных объектов» и порядок в них.",
              sl, ["nature", "dots", "layout", "data"], 4)


def seq_nature(theme) -> Variant:
    """Одно дерево через презентацию: росток → ветвится → крона → ствол становится спилом (перспектива) → вид сверху,
    кольца = прирост → спил у края — навигация → лист-фон под текстом → крона, листья опадают золотом."""
    S_ = []
    base = (6.6, 6.9)
    def trunk_as_log(c, R, side, sy, alpha=1.0):
        return rings_objs(theme, c, 10, sy=sy, scale=R / sum(WIDTHS), side=side, alpha=alpha)
    def log_hidden(c=(6.6, 6.0)):
        o = rings_objs(theme, c, 10, sy=0.4, scale=0.05, side=0.01, alpha=0.0)
        return o
    S_.append(S(tree_objs(theme, 2) + log_hidden() + [kicker("лес и данные"), O("!!cov", "text", 0.7, 1.0, 5.6, 1.7, txt=["Как растёт", "дерево"],
                                                                                  sz=48, b=True, font="head", col="ink", spacing=0.95, z=90)], 700))
    S_.append(S(tree_objs(theme, 4) + log_hidden() + [head("Каждый год — ветви", w=6)], 900))
    S_.append(S(tree_objs(theme, 7, leaves=True) + log_hidden() + [head("Крона", w=6)], 900))
    # 4: дерево уходит вверх и бледнеет; из основания ствола — спил в перспективе
    o4 = tree_objs(theme, 7, leaves=True, alpha=0.15, base=(6.6, 3.2), scale=0.6) + trunk_as_log((6.6, 4.6), 1.9, 1.6, 0.4)
    S_.append(S(o4 + [head("Спил ствола", w=5)], 900))
    # 5: вид сверху — кольца = прирост по годам
    o5 = tree_objs(theme, 7, leaves=True, alpha=0.0, base=(6.6, -1.0), scale=0.5) + trunk_as_log((8.6, 4.0), 2.6, 0.0, 1.0)
    o5 += [head("Десять колец", w=5), body("!!b", 0.7, 1.4, 4.5, 0.8, ["узкое кольцо —", "сухой год"], sz=18)]
    S_.append(S(o5, 900))
    # 6: спил у левого края — навигация; группа колец раздела — золото
    secs = ["Почва", "Корни", "Ствол", "Крона"]
    groups = [(0, 2), (3, 5), (6, 7), (8, 9)]
    o6 = tree_objs(theme, 7, leaves=True, alpha=0.0, base=(6.6, -1.0), scale=0.5) + trunk_as_log((-0.6, 3.75), 2.4, 0.0, 1.0)
    o6 = [ob.copy(fill=theme.c("accent")) if ob.name in {f"!!rg{i}" for i in range(6, 8)} else ob for ob in o6]
    o6 += [label(f"!!sc{gi}", 2.3, 2.2 + gi * 0.55, f"0{gi + 1} {s}", w=2.2, al="l", sz=13, b=gi == 2, col="accent" if gi == 2 else "muted")
           for gi, s in enumerate(secs)]
    o6 += [kicker("раздел 3", x=5.8), head("Ствол", x=5.8, w=7), body("!!txt", 5.8, 1.5, 7, 1.0, ["годы роста в разрезе", "ширина = погода года"], sz=20)]
    S_.append(S(o6, 900))
    # 7: крона — бледный фон под текстом, спил уходит
    o7 = tree_objs(theme, 7, leaves=True, alpha=0.14, base=(9.5, 9.0), scale=1.7) + trunk_as_log((-3.6, 3.75), 2.4, 0.0, 1.0, alpha=0.0)
    o7 = [ob.copy(z=ob.z - 400, meta={**ob.meta, **DEC}) if ob.name.startswith(("!!b", "!!lf")) else ob for ob in o7]
    o7 += [head("Что измеряют лесники", w=8), body("!!txt", 0.7, 1.5, 6.5, 2.2, ["диаметр на высоте груди", "высоту и крону", "ширину колец"], sz=22, col="ink")]
    S_.append(S(o7, 900))
    # 8: финал — дерево снова целиком, листья золотые (осень)
    o8 = tree_objs(theme, 7, leaves=True, leaf_col=theme.c("accent"), base=(9.3, 6.9)) + log_hidden()
    o8 += [O("!!fin", "text", 0.7, 1.2, 5.6, 1.6, txt=["Рост виден", "в каждом кольце"], sz=40, b=True, font="head", col="ink", spacing=0.95, z=90)]
    S_.append(S(o8, 900))
    return _v("seq_nature", "Дерево живёт через презентацию",
              "8 состояний одного дерева: росток → ветвится → крона → дерево уходит вверх, из ствола — спил в "
              "перспективе → вид сверху, 10 колец → спил у левого края — навигация (кольца раздела золотом) → огромная "
              "бледная крона под текстом → финал: снова дерево, листья пожелтели.",
              S_, ["seq", "nature", "growth", "3d", "pointer", "backdrop"], 4)


def variants(theme) -> list[Variant]:
    return [seq_nature(theme), tree_rings(theme), log_pointer(theme), leaf_venation(theme), leaf_steps(theme), leaf_backdrop(theme),
            branching(theme), seeds(theme), cells(theme), phyllotaxis(theme)]
