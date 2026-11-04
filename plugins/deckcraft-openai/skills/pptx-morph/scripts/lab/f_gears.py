"""Семейство «Шестерни»: зацепление пары и передачи (углы связаны передаточным числом, Morph сохраняет зацепление,
потому что все углы интерполируются синхронно), петли вращения в разные стороны, планетарная передача, рейка,
шестерня -> значок, разлёт шестерни на части, зубцы как данные, псевдо-3D шестерня, шестерня -> цветок.
"""

from __future__ import annotations

import math

from morphkit import Loop, O, Slide
from morphkit import vector as V
from morphkit.presets import Fx
from morphkit.theme import mix

from lab import Variant
from lab._b_util import (arc_pts, ax, axis, gear, head, pol, shade, squash, text)

FAM = "gears"
M = 0.11  # модуль: дюймов на зуб по делительному диаметру


def rp(n, m=M):
    return m * n / 2


def gear_obj(name, c, n, rot, fill, m=M, hole=0.0, z=8, **kw):
    """Шестерня на своей оси: rot — угол зуба 0. Делительный радиус m·n/2, высота зуба 1.8m."""
    g = gear(c[0], c[1], rp(n, m) - 1.0 * m, rp(n, m) + 0.8 * m, n, phase=0.0, tooth=0.5, top=0.55, per=4, hole=hole)
    return axis(name, g, c, rp(n, m) + 0.85 * m, rot=rot, fill=fill, z=z, **kw)


def mesh(thA, nA, nB, phi):
    """Угол шестерни B, зацеплённой с A по направлению phi (от A к B)."""
    sB = 360 / nB
    return phi + 180 - sB / 2 + (nA / nB) * (phi - thA)


def place(cA, nA, nB, phi, m=M):
    d = rp(nA, m) + rp(nB, m) + 0.02
    return pol(cA[0], cA[1], d, phi)


# ----------------------------------------------------------------------------- 1. пара: вход и выход

def v_pair(theme) -> Variant:
    nA, nB = 36, 18
    cA = (6.6, 4.3)
    phi = -20
    cB = place(cA, nA, nB, phi)

    def state(s, sub):
        thA = 40 * s
        objs = head("Передача ×2", sub)
        objs.append(gear_obj("!!gA", cA, nA, thA, shade(theme, "ink", 0.35), hole=0.35))
        objs.append(gear_obj("!!gB", cB, nB, mesh(thA, nA, nB, phi), "accent", hole=0.2))
        for c, nm, r, k in ((cA, "!!gma", rp(nA), 0), (cB, "!!gmb", rp(nB), 1)):
            g = V.circle(c[0] + r * 0.55, c[1], 0.07, seg=8)
            th = thA if k == 0 else mesh(thA, nA, nB, phi)
            objs.append(axis(nm, g, c, r, rot=th, fill="bg", z=9))
        objs.append(text("!!gla", cA[0] - 1.0, cA[1] + rp(nA) + 0.25, 2.0, 0.4, "Вход: 1 оборот", sz=15, col="ink2",
                         al="c"))
        objs.append(text("!!glb", cB[0] - 1.0, cB[1] - rp(nB) - 0.65, 2.0, 0.4, "Выход: 2 оборота", sz=15, col="accent",
                         al="c", b=True))
        return objs

    return Variant(FAM, "pair", "Пара шестерён в зацеплении",
                   "Большая и малая шестерни: углы связаны передаточным числом, поэтому при Morph зубья не "
                   "проскальзывают; метки на дисках показывают, что малая крутится вдвое быстрее. "
                   "Роль: рычаг, «вложили 1 — получили 2».",
                   [Slide(state(0, "Вложили усилие"), dur=800), Slide(state(1, "Передали"), dur=850),
                    Slide(state(2, "Малая — вдвое быстрее"), dur=850)],
                   tags=["gears", "mesh", "rotation", "metaphor"], score=4)


# ----------------------------------------------------------------------------- 2. передача из четырёх: процесс

def _train(n_list, c0, phis):
    cs = [c0]
    for k in range(1, len(n_list)):
        cs.append(place(cs[-1], n_list[k - 1], n_list[k], phis[k - 1]))
    return cs


def _train_angles(th0, n_list, phis):
    th = [th0]
    for k in range(1, len(n_list)):
        th.append(mesh(th[-1], n_list[k - 1], n_list[k], phis[k - 1]))
    return th


def v_train(theme) -> Variant:
    ns = [24, 16, 28, 14]
    phis = [-25, 30, -35]
    cs = _train(ns, (3.4, 4.3), phis)
    steps = ["Сбор", "Анализ", "Решение", "Действие"]

    def state(k, sub):
        objs = head("Цепочка решений", sub)
        th = _train_angles(30 * k, ns, phis)
        for i, (n, c) in enumerate(zip(ns, cs)):
            objs.append(gear_obj(f"!!tg{i}", c, n, th[i], shade(theme, "ink", 0.3 + 0.12 * (i % 2)), hole=0.15))
            objs.append(text(f"!!tl{i}", c[0] - 1.0, c[1] + rp(n) + 0.25 if i % 2 == 0 else c[1] - rp(n) - 0.65, 2.0,
                             0.4, steps[i], sz=15, b=i == k + 1, col="accent" if i == k + 1 else "ink2", al="c"))
        a = k + 1
        r = rp(ns[a]) + 0.22
        objs.append(O("!!tmark", "oval", cs[a][0] - r, cs[a][1] - r, 2 * r, 2 * r, fill=None, ln="accent", lw=2.5, z=12))
        return objs

    return Variant(FAM, "train", "Передача из четырёх: шаги процесса",
                   "Четыре шестерни — четыре шага; каждый слайд поворачивает всю передачу (зацепление сохраняется), "
                   "а кольцо-маркер переезжает на следующий шаг. Роль: процесс, где каждый шаг крутит следующий.",
                   [Slide(state(0, "Шаг 2"), dur=800), Slide(state(1, "Шаг 3"), dur=850),
                    Slide(state(2, "Шаг 4"), dur=850)],
                   tags=["gears", "process", "mesh", "marker"], score=4)


# ----------------------------------------------------------------------------- 3. живой механизм: вращение петлями

def v_spin(theme) -> Variant:
    ns = [30, 15, 22]
    phis = [10, -40]
    cs = _train(ns, (6.0, 4.0), phis)
    th = _train_angles(0, ns, phis)
    P = 3.0

    def state(s, sub):
        objs = head("Механизм работает", sub)
        for i, (n, c) in enumerate(zip(ns, cs)):
            objs.append(gear_obj(f"gs{i}" if s else f"!!gs{i}", c, n, th[i],
                                 "accent" if i == 1 else shade(theme, "ink", 0.3 + 0.15 * i), hole=0.18))
        return objs

    loops = [Loop("spin", target="gs0", period=P, name="gsp"), Loop("spin", target="gs2", period=P * ns[2] / ns[0],
                                                                       name="gsp")]
    fx = [Fx("emphasis_spin", "gs1", dur=P * ns[1] / ns[0], repeat=True, options={"amount": -360})]
    return Variant(FAM, "spin", "Шестерни крутятся петлями в разные стороны",
                   "Передача из трёх: крайние — петля «Вращение» по часовой, средняя — эффект «Вращение» на −360°; "
                   "периоды пропорциональны числу зубьев, зацепление держится бесконечно. Роль: фон «система "
                   "работает», слайд-пауза. (Обратное вращение предпросмотр не показывает — только PowerPoint.)",
                   [Slide(state(0, "Стоит"), dur=600), Slide(state(1, "Работает"), dur=600, loops=loops, fx=fx)],
                   tags=["gears", "loop", "spin", "background"], score=3)


# ----------------------------------------------------------------------------- 4. шестерня -> значок

def v_icon(theme) -> Variant:
    c = (9.0, 4.0)
    n = 240
    g_gear = V.resample(gear(c[0], c[1], 1.45, 1.85, 12, phase=-90, tooth=0.5, top=0.6, per=6), n)
    from shapely.geometry import LineString
    chk = LineString([(c[0] - 1.1, c[1] + 0.05), (c[0] - 0.3, c[1] + 0.85), (c[0] + 1.25, c[1] - 0.9)]).buffer(
        0.32, cap_style=1, join_style=1)
    g_chk = V.resample(chk, n)
    g_circ = V.resample(V.circle(c[0], c[1], 1.85), n)

    def state(s, sub):
        objs = head("Настроено", sub)
        g = [g_gear, g_circ, g_chk][s]
        objs.append(V.shape("!!ico", g, fill=["ink2", "accent", "accent"][s], z=8))
        if s == 2:
            objs.append(O("ring", "oval", c[0] - 2.0, c[1] - 2.0, 4.0, 4.0, fill=None, ln="accent", lw=3, z=6))
        return objs

    return Variant(FAM, "icon", "Шестерня переливается в галочку",
                   "Контур шестерни (240 точек) переливается в диск, затем в галочку того же числа точек; "
                   "вокруг проявляется кольцо. Роль: «настройка завершена», переход от процесса к результату.",
                   [Slide(state(0, "Идёт настройка"), dur=800), Slide(state(1, "Собираем"), dur=700),
                    Slide(state(2, "Готово"), dur=800, fx=[Fx("entrance_faded_zoom", "ring", start="at", delay=0.1,
                                                              dur=0.4)])],
                   tags=["gears", "shape-morph", "icon"], score=4)


# ----------------------------------------------------------------------------- 5. планетарная передача

def v_planetary(theme) -> Variant:
    c = (8.9, 4.0)
    m = 0.075
    Zs, Zp, Zr = 18, 12, 42
    a = rp(Zs, m) + rp(Zp, m) + 0.01
    ring_hole = gear(c[0], c[1], rp(Zr, m) - 0.8 * m, rp(Zr, m) + 1.0 * m, Zr, phase=0, tooth=0.5, top=0.55, per=4)

    def state(s, sub):
        objs = head("Планетарная передача", sub)
        car = 30 * s
        ths = car * (1 + Zr / Zs)
        objs.append(gear_obj("!!ps", c, Zs, ths, "accent", m=m, hole=0.12, z=9))
        for j in range(3):
            phi = car + 120 * j
            pc = pol(*c, a, phi)
            thp0 = mesh(ths, Zs, Zp, phi)
            objs.append(gear_obj(f"!!pp{j}", pc, Zp, thp0, shade(theme, "ink", 0.3), m=m, hole=0.08, z=9))
        # кольцо с внутренними зубьями: неподвижно, фаза под планету 0 при car=0
        phi0 = 0
        thp = mesh(0, Zs, Zp, phi0)
        delta = ((phi0 - thp) % (360 / Zp))
        ph = phi0 - delta * rp(Zp, m) / rp(Zr, m) + 180 / Zr
        hole = V.rotate(ring_hole, ph, origin=c)
        ringg = V.Polygon(list(V.circle(c[0], c[1], rp(Zr, m) + 0.35).exterior.coords), [list(hole.exterior.coords)])
        objs.append(V.shape("!!pr", ringg, fill=shade(theme, "ink", 0.6), z=7))
        carrier = [pol(*c, a, car + 120 * j) for j in range(3)]
        objs.append(V.shape("!!pcar", V.Polygon(carrier), fill=None, ln="ink", lw=1.5, z=10))
        objs.append(text("!!pl1", 0.7, 3.2, 4.0, 1.2, ["Центр — продукт", "Сателлиты — команды", "Кольцо — рынок"],
                         sz=15, col="ink2"))
        return objs

    return Variant(FAM, "planetary", "Планетарная передача",
                   "Солнце, три сателлита и кольцо с внутренними зубьями: водило поворачивается на 30°, солнце — "
                   "на 100°, сателлиты катятся по кольцу и крутятся в обратную сторону. Роль: сложная система "
                   "с одним центром, роли команд вокруг продукта.",
                   [Slide(state(0, "Три команды вокруг продукта"), dur=800), Slide(state(1, "Всё связано"), dur=850),
                    Slide(state(2, "Обороты разные — система одна"), dur=850)],
                   tags=["gears", "planetary", "mesh", "metaphor"], score=4)


# ----------------------------------------------------------------------------- 6. рейка: вращение -> движение вперёд

def _rack(x0, y, n, pitch, h=0.25, top=0.5, base=0.3):
    pts = []
    for k in range(n):
        x = x0 + k * pitch
        wt, wb = pitch * 0.5 * top, pitch * 0.5
        pts += [(x - wb / 2, y), (x - wt / 2, y - h), (x + wt / 2, y - h), (x + wb / 2, y)]
    pts += [(x0 + (n - 1) * pitch + pitch / 2, y), (x0 + (n - 1) * pitch + pitch / 2, y + base),
            (x0 - pitch / 2, y + base), (x0 - pitch / 2, y)]
    return V.Polygon(pts)


def v_rack(theme) -> Variant:
    n = 16
    c = (6.7, 3.2)
    r = rp(n)
    pitch = 2 * math.pi * r / n
    yr = c[1] + r + 0.02
    qs = ["I кв.", "II кв.", "III кв.", "IV кв.", "2026"]

    def state(s, sub):
        th = 90 * s
        shift = -math.radians(th) * r
        objs = head("Рейка", sub)
        objs.append(gear_obj("!!rg", c, n, th - 90 + 180 / n, "accent", hole=0.18))
        x0 = c[0] - 10 * pitch + shift
        g = _rack(x0, yr + 0.08, 40, pitch, h=1.8 * M)
        objs.append(V.shape("!!rk", g, fill=shade(theme, "ink", 0.35), z=7, meta={"bleed": True}))
        for j, q in enumerate(qs):
            x = c[0] + j * 2 * math.pi * r / 4 + shift
            objs.append(text(f"!!rq{j}", x - 0.7, yr + 0.62, 1.4, 0.4, q, sz=15, b=j == s, col="accent" if j == s
                             else "ink2", al="c"))
        objs.append(O("!!rpt", "rect", c[0] - 0.02, yr + 0.42, 0.04, 0.16, fill="accent", z=12))
        return objs

    return Variant(FAM, "rack", "Шестерня катит рейку-шкалу",
                   "Поворот шестерни на 90° сдвигает зубчатую рейку ровно на четверть окружности; на рейке — "
                   "кварталы, текущий встаёт под указатель. Роль: «каждый оборот — шаг по плану», дорожная карта.",
                   [Slide(state(0, "Начало года"), dur=800), Slide(state(1, "Квартал прошёл"), dur=850),
                    Slide(state(2, "Ещё квартал"), dur=850)],
                   tags=["gears", "rack", "timeline", "rotation"], score=3)


# ----------------------------------------------------------------------------- 7. шестерня разбирается на части

def v_explode(theme) -> Variant:
    c = (8.9, 4.1)
    g = gear(c[0], c[1], 1.6, 2.05, 16, phase=-90, per=4, hole=0.55)
    parts = V.slices(g, 6, pivot=c, start=-90)
    names = ["Люди", "Процессы", "Данные", "Инструменты", "Деньги", "Клиенты"]

    def state(s, sub):
        objs = head("Из чего механизм", sub)
        for j, p in enumerate(parts):
            pp = max(p.geoms, key=lambda q: q.area) if p.geom_type == "MultiPolygon" else p
            mid = -90 + 60 * j + 30
            k = [0, 0.55, 0.55][s]
            dx, dy = pol(0, 0, k, mid)
            col = shade(theme, "ink", 0.3 + 0.08 * (j % 2))
            if s == 2:
                col = "accent" if j == 2 else shade(theme, "ink", 0.65)
            objs.append(V.shape(f"!!ep{j}", V.move(pp, dx, dy), fill=col, z=8))
            if s >= 1:
                x, y = pol(*c, 2.95, mid)
                al = "l" if x > c[0] + 0.3 else ("r" if x < c[0] - 0.3 else "c")
                bx = x - 0.1 if al == "l" else (x - 1.9 if al == "r" else x - 1.0)
                objs.append(text(f"!!en{j}", bx, y - 0.2, 2.0, 0.4, names[j], sz=15, b=(s == 2 and j == 2),
                                 col="accent" if (s == 2 and j == 2) else "ink2", al=al, va="m"))
        return objs

    return Variant(FAM, "explode", "Шестерня разбирается на части",
                   "Шестерня режется на шесть секторов, они расходятся и подписываются, один подсвечивается. "
                   "Роль: из чего состоит «механизм» компании, где поломка.",
                   [Slide(state(0, "Целое"), dur=800), Slide(state(1, "Шесть частей"), dur=850,
                                                            fx=[Fx("entrance_fade", f"!!en{j}", start="at",
                                                                   delay=0.1 + 0.05 * j, dur=0.3) for j in range(6)]),
                    Slide(state(2, "Слабое звено — данные"), dur=600)],
                   tags=["gears", "fragment", "explode"], score=4)


# ----------------------------------------------------------------------------- 8. зубцы как данные

def data_gear(c, vals, r_root, hmax, phase=-90.0, per=4, tooth=0.6, top=0.6):
    n = len(vals)
    step = 360 / n
    wb, wt = step * tooth, step * tooth * top
    pts = []
    for k, v in enumerate(vals):
        a = phase + k * step + step / 2
        rt = r_root + 0.08 + hmax * v
        pts += [pol(c[0], c[1], rt, a - wt / 2 + wt * j / (per - 1)) for j in range(per)]
        pts += [pol(c[0], c[1], r_root, a + wb / 2 + (step - wb) * j / (per - 1)) for j in range(per)]
    return V.Polygon(pts)


def v_datagear(theme) -> Variant:
    c = (8.9, 4.0)
    mn = ["Я", "Ф", "М", "А", "М", "И", "И", "А", "С", "О", "Н", "Д"]
    d1 = [0.3, 0.35, 0.5, 0.6, 0.7, 0.9, 1.0, 0.95, 0.7, 0.55, 0.4, 0.35]
    d2 = [0.45, 0.5, 0.6, 0.75, 0.85, 0.8, 0.9, 1.0, 0.9, 0.8, 0.7, 0.6]

    def state(s, sub):
        objs = head("Зубцы — это месяцы", sub)
        vals = d1 if s == 0 else d2
        g = data_gear(c, vals, 1.5, 0.95)
        objs.append(V.shape("!!dg", g, fill="accent" if s == 2 else shade(theme, "ink", 0.3), z=8))
        objs.append(O("!!dh", "oval", c[0] - 0.75, c[1] - 0.75, 1.5, 1.5, fill="bg", z=9))
        for k in range(12):
            x, y = pol(*c, 2.85, -90 + 30 * k + 15)
            objs.append(text(f"!!dm{k}", x - 0.2, y - 0.17, 0.4, 0.34, mn[k], sz=12, col="muted", al="c", va="m"))
        objs.append(text(f"dy{min(s, 1)}", 0.7, 3.3, 3.5, 0.8, ["2024", "2025"][min(s, 1)], sz=40, b=True, col="ink",
                         font="head"))
        return objs

    return Variant(FAM, "datagear", "Зубцы шестерни — значения по месяцам",
                   "Высота каждого зуба — продажи месяца; при смене года зубья перерастают на месте (меняется только "
                   "радиус — перелив точный). Роль: сезонность в форме «механизма», связка с темой процессов.",
                   [Slide(state(0, "Прошлый год: пик летом"), dur=800), Slide(state(1, "Этот год: ровнее"), dur=850),
                    Slide(state(2, "Механизм крутится весь год"), dur=600)],
                   tags=["gears", "data", "radial-bars"], score=4)


# ----------------------------------------------------------------------------- 9. псевдо-3D: шестерня обретает толщину

def v_gear3d(theme) -> Variant:
    c = (8.9, 3.6)
    nL = 7

    def state(s, sub):
        objs = head("Шестерня в объёме", sub)
        k = 1.0 if s == 0 else 0.45
        dep = 0.0 if s == 0 else 0.07
        ph = [0, 0, 360 / 14][s]
        g = gear(c[0], c[1], 1.55, 1.95, 14, phase=-90 + ph, per=4, hole=0.0)
        top = squash(g, c, k)
        for L in range(nL, 0, -1):
            objs.append(V.shape(f"!!gl{L}", V.move(top, 0, dep * L), fill=mix(theme.c("ink2"), theme.c("bg"),
                                                                                  0.35 + 0.06 * L), z=8 + nL - L))
        objs.append(V.shape("!!gt", top, fill="accent" if s == 2 else shade(theme, "ink", 0.2), z=20))
        hole = squash(V.circle(c[0], c[1], 0.55, seg=24), c, k)
        objs.append(V.shape("!!gh", hole, fill="bg", z=21))
        return objs

    return Variant(FAM, "gear3d", "Плоская шестерня обретает толщину",
                   "Вид сверху -> наклон: контур сжимается по вертикали, под ним вырастают семь слоёв-теней — "
                   "получается выдавленная деталь без 3D-движка; затем она проворачивается на зуб. "
                   "Роль: «вау» на титуле раздела о процессах.",
                   [Slide(state(0, "Чертёж"), dur=800), Slide(state(1, "Деталь"), dur=900),
                    Slide(state(2, "Поворот на зуб"), dur=700)],
                   tags=["gears", "pseudo-3d", "extrude"], score=3)


# ----------------------------------------------------------------------------- 10. шестерня -> цветок

def v_bloom(theme) -> Variant:
    c = (8.9, 4.0)
    n = 300
    g_gear = V.resample(gear(c[0], c[1], 1.5, 2.0, 10, phase=-90, tooth=0.5, top=0.6, per=8), n)
    pet = [V.petal(c, 0.4, 2.3, 0.95, -90 + 36 * k) for k in range(10)]
    g_flower = V.resample(V.union(*pet, V.circle(c[0], c[1], 0.9)), n)
    g_flower2 = V.resample(V.union(*[V.petal(c, 0.4, 2.6, 1.15, -90 + 36 * k + 18) for k in range(10)],
                                   V.circle(c[0], c[1], 0.9)), n)

    def state(s, sub):
        objs = head("Механизм оживает", sub)
        g = [g_gear, g_flower, g_flower2][s]
        objs.append(V.shape("!!bl", g, fill=["ink2", "accent", "accent"][s], z=8))
        objs.append(O("!!bc", "oval", c[0] - 0.55, c[1] - 0.55, 1.1, 1.1, fill="bg", z=9))
        return objs

    return Variant(FAM, "bloom", "Шестерня распускается цветком",
                   "Зубья шестерни переливаются в лепестки (один контур, 300 точек), цветок раскрывается шире. "
                   "Роль: переход от «машины» к «живой системе», культура вместо регламентов.",
                   [Slide(state(0, "Регламенты"), dur=800), Slide(state(1, "Живая система"), dur=900),
                    Slide(state(2, "Растёт"), dur=800)],
                   tags=["gears", "shape-morph", "flower", "metaphor"], score=3)


# ----------------------------------------------------------------------------- ЖИВАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ 1: механизм года

def tooth_piece(c, r_in, r_root, r_tip, a0, step, per=5, tooth=0.5, top=0.55, ov=0.25):
    """Кусок шестерни на угловом отрезке [a0, a0+step]: впадина, зуб, впадина, внутренняя дуга. 4·per точек."""
    wb, wt = step * tooth, step * tooth * top
    am = a0 + step / 2
    pts = [pol(c[0], c[1], r_root, a0 - ov + ((step - wb) / 2 + ov) * j / (per - 1)) for j in range(per)]
    pts += [pol(c[0], c[1], r_tip, am - wt / 2 + wt * j / (per - 1)) for j in range(per)]
    pts += [pol(c[0], c[1], r_root, am + wb / 2 + ((step - wb) / 2 + ov) * j / (per - 1)) for j in range(per)]
    pts += [pol(c[0], c[1], r_in, a0 + step + ov - (step + 2 * ov) * j / (per - 1)) for j in range(per)]
    return V.Polygon(pts)


def col_rect(x, y, w, h, per=5):
    """Прямоугольник в порядке точек tooth_piece: левая сторона вверх, верх, правая вниз, низ назад (без дублей углов)."""
    pts = [(x, y + h - h * j / per) for j in range(per)]
    pts += [(x + w * j / per, y) for j in range(per)]
    pts += [(x + w, y + h * j / per) for j in range(per)]
    pts += [(x + w - w * j / per, y + h) for j in range(per)]
    return V.Polygon(pts)


def seq_machine(theme) -> Variant:
    c = (8.0, 4.15)
    m = 0.275
    nB, nS = 12, 6
    r_in, r_root, r_tip = 0.62, rp(nB, m) - m, rp(nB, m) + 0.8 * m
    cS = place(c, nB, nS, 0, m)
    months = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
    vals = [0.35, 0.4, 0.55, 0.6, 0.7, 0.85, 1.0, 0.9, 0.75, 0.8, 0.6, 0.5]
    K, DEP = 0.45, 0.3
    step = 30.0
    # угол колеса θ: зуб j смотрит на θ + 30j + 15; зуб «Окт» (9) приходит к малой шестерне (0°) на шаге 1
    th = {0: -40.0}
    th[1] = -(30 * 9 + 15)
    th[2] = th[1]
    th[3] = th[1] - 30
    for st in (4, 5, 6, 7):
        th[st] = th[3]
    hl = {0: 9, 1: 9, 2: 9, 3: 10, 4: 10, 5: 10, 6: 10, 7: 10}

    def small_abs(st):
        thS = mesh(th[st] + 15, nB, nS, 0)
        g = gear(cS[0], cS[1], rp(nS, m) - m, rp(nS, m) + 0.8 * m, nS, phase=thS, per=4, hole=0.0)
        if st == 4:
            g = squash(g, c, K)
        if st == 6:
            g = V.Polygon([(x + 4.0, y + 1.2) for x, y in list(g.exterior.coords)[:-1]])
        return g, thS

    heads = [("Механизм года", "12 зубцов — 12 месяцев"), ("Октябрь в работе", "Зуб месяца у передачи"),
             ("Октябрь крупно", "Зуб выходит в панель"), ("Дальше — ноябрь", "Колесо провернулось на зуб"),
             ("Деталь в объёме", "Наклоняем механизм"), ("Зубцы = выручка", "Высота зуба — месяц"),
             ("Год по месяцам", "Колесо разворачивается в столбики"), ("Механизм работает", "Снова целое")]
    slides = []
    for st in range(8):
        objs = head(*heads[st])
        for j in range(nB):
            a0 = th[st] + step * j
            h_t = r_tip if st < 5 else r_root + 0.12 + 0.75 * vals[j]
            if st == 7:
                h_t = r_root + 0.12 + 0.75 * vals[j]
            g = tooth_piece(c, r_in, r_root, h_t, a0, step)
            side = None
            if st == 4:
                g = squash(g, c, K)
                side = V.move(g, 0, DEP)
            if st == 2 and j == hl[st]:
                g = col_rect(0.7, 2.45, 4.3, 3.5)
            if st == 6:
                bh = 0.4 + 2.8 * vals[j]
                g = col_rect(1.1 + j * 0.95, 6.2 - bh, 0.7, bh)
            on = j == hl[st]
            col = "accent" if on else shade(theme, "ink", 0.28 + 0.06 * (j % 2))
            if st == 2 and on:
                col = "surface"
            objs.append(ax(f"!!mt{j}", g, a0, pivot=c, R=9.6, fill=col, ln="accent" if (st == 2 and on) else None,
                           lw=2.0 if (st == 2 and on) else 0, z=30 if (st == 2 and on) else 10))
            sg = side if side is not None else g
            objs.append(ax(f"!!ms{j}", sg, a0, pivot=c, R=9.6,
                           fill=mix(theme.c("accent") if on else theme.c("ink2"), theme.c("bg"), 0.55),
                           fa=1.0 if side is not None else 0.0, z=6))
            if st == 6:
                bh = 0.4 + 2.8 * vals[j]
                objs.append(text(f"mm{j}", 1.1 + j * 0.95 - 0.15, 6.3, 1.0, 0.36, months[j], sz=12,
                                 col="accent" if on else "muted", al="c"))
        gS, thS = small_abs(st)
        objs.append(ax("!!msm", gS, thS, pivot=cS, R=9.6, fill=shade(theme, "ink", 0.5), z=9,
                       fa=0.0 if st == 6 else 1.0))
        hole = V.circle(c[0], c[1], r_in * 0.55, seg=16)
        if st == 4:
            hole = squash(hole, c, K)
        if st == 6:
            hole = V.circle(c[0], 6.2, 0.02, seg=16)
        objs.append(V.shape("!!mh", hole, fill="bg", z=12))
        if st in (1, 3):
            x, y = pol(*c, r_tip + 0.1, 0)
            objs.append(text(f"ml{st}", x - 0.2, y - 1.55, 1.6, 0.45, months[hl[st]], sz=18, b=True, col="accent"))
        if st == 2:
            objs.append(text("mp1", 1.0, 2.8, 3.8, 0.8, "Октябрь", sz=30, b=True, col="accent", font="head"))
            objs.append(text("mp2", 1.0, 3.75, 3.8, 1.4, ["Выручка 80% пика", "Запуск B2B", "Найм: 6 человек"], sz=16,
                             col="ink"))
        fx = []
        if st == 0:
            fx = [Fx("entrance_spinner", f"!!mt{j}", start="at", delay=0.05 + 0.03 * j, dur=0.5) for j in range(nB)]
        if st == 2:
            fx = [Fx("entrance_fade", "mp1", start="at", delay=0.1, dur=0.3), Fx("entrance_fade", "mp2", start="after",
                                                                                   dur=0.3)]
        loops = []
        if st == 7:
            loops = [Loop("spin", target=f"!!mt{j}", period=4.0, name="msp") for j in range(nB)]
            fx = [Fx("emphasis_spin", "!!msm", dur=4.0 * nS / nB, repeat=True, options={"amount": -360})]
        slides.append(Slide(objs, dur=[800, 900, 850, 850, 900, 850, 900, 900][st], fx=fx, loops=loops))
    return Variant(FAM, "seq_machine", "Живой механизм года (8 состояний)",
                   "Шестерня из 12 зубцов-месяцев: колесо подводит зуб месяца к передаче, зуб выходит из колеса и "
                   "раскрывается в панель с фактами, возвращается, колесо проворачивается, наклоняется в объём, "
                   "зубцы вырастают по выручке, колесо разворачивается в столбики и снова собирается и крутится "
                   "петлёй. Роль: сквозной мотив годового отчёта.",
                   slides, tags=["seq", "gears", "magnifier", "3d", "chart", "loop", "data"], score=4)


# ----------------------------------------------------------------------------- ЖИВАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ 2: сборка процесса

def seq_assembly(theme) -> Variant:
    ns = [22, 14, 20, 12]
    phis = [-20, 25, -30]
    cs = _train(ns, (3.6, 4.4), phis)
    names = ["Заявка", "Проверка", "Сборка", "Доставка"]
    parked = [(1.8, 5.6), (5.6, 2.9), (11.6, 2.6), (12.2, 6.0)]
    heads = [("Процесс по частям", "Шаги пока врозь"), ("Собрали цепочку", "Каждый шаг крутит следующий"),
             ("Работает", "Один оборот"), ("Сбой", "Сборка выпала — всё встало"),
             ("Замена", "Новый шаг вместо старого"), ("Снова в работе", "Цепочка крутится")]
    slides = []
    for st in range(6):
        objs = head(*heads[st])
        th = _train_angles([0, 0, 50, 50, 50, 110][st], ns, phis)
        for i, (n, c) in enumerate(zip(ns, cs)):
            cc, rot = c, th[i]
            col = shade(theme, "ink", 0.3 + 0.12 * (i % 2))
            if st == 0:
                cc, rot = parked[i], th[i] - 120
            if st >= 3 and i == 2:
                cc, rot = (c[0] + 1.6, c[1] + 1.1), th[i] + 35
                col = "bad"
                if st >= 4:
                    cc = (c[0] + 1.5, 9.5)
            nm = f"!!ag{i}" if not (st == 5 and i != 2) else f"ag{i}"
            if st == 5 and i == 2:
                nm = "!!ag2"
            objs.append(gear_obj(nm, cc, n, rot, col, hole=0.15, z=8, meta={"bleed": True}))
            if st in (1, 2, 4, 5) and not (st >= 4 and i == 2):
                objs.append(text(f"!!an{i}", c[0] - 1.0, c[1] + rp(n) + 0.25 if i % 2 == 0 else c[1] - rp(n) - 0.65,
                                 2.0, 0.4, names[i], sz=15, col="ink2", al="c"))
        # новая шестерня-замена
        if st >= 4:
            cc = cs[2] if st >= 4 else (14.5, cs[2][1])
            rot = th[2]
            nm = "!!agN" if st == 4 else "agN"
            objs.append(gear_obj(nm, cc, ns[2], rot, "accent", hole=0.15, z=9))
            objs.append(text("!!anN", cs[2][0] - 1.0, cs[2][1] + rp(ns[2]) + 0.25, 2.0, 0.4, "Сборка 2.0", sz=15, b=True,
                             col="accent", al="c"))
        if st == 3:
            objs.append(gear_obj("!!agN", (14.8, cs[2][1]), ns[2], th[2] + 60, "accent", hole=0.15, z=9,
                                 meta={"bleed": True}))
        loops, fx = [], []
        if st == 5:
            P = 3.0
            loops = [Loop("spin", target="ag0", period=P, name="asp"),
                     Loop("spin", target="agN", period=P * ns[2] / ns[0], name="asp")]
            fx = [Fx("emphasis_spin", "ag1", dur=P * ns[1] / ns[0], repeat=True, options={"amount": -360}),
                  Fx("emphasis_spin", "ag3", dur=P * ns[3] / ns[0], repeat=True, options={"amount": -360})]
            objs = [o for o in objs if o.name != "!!ag2"]
        slides.append(Slide(objs, dur=[800, 900, 800, 800, 850, 600][st], loops=loops, fx=fx))
    return Variant(FAM, "seq_assembly", "Сборка, сбой и замена шага (6 состояний)",
                   "Шестерни-шаги влетают из-за краёв и сцепляются в цепочку, проворачиваются вместе; одна "
                   "выпадает (красная, перекос) — цепочка стоит; новая въезжает на её место, и цепочка крутится "
                   "петлями в разные стороны. Роль: история «узкого места» и его замены.",
                   slides, tags=["seq", "gears", "process", "mesh", "loop", "story"], score=3)


def variants(theme) -> list[Variant]:
    return [v_pair(theme), v_train(theme), v_spin(theme), v_icon(theme), v_planetary(theme), v_rack(theme),
            v_explode(theme), v_datagear(theme), v_gear3d(theme), v_bloom(theme), seq_machine(theme),
            seq_assembly(theme)]
