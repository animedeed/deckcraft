"""Семейство «Орбиты»: комета с хвостом, парад планет, наклон системы в 3D, переход с орбиты на орбиту по спирали,
спутники-навигация, орбита с читаемыми подписями, атом с электронами по эллипсам, вытянутая орбита с кометой-петлёй,
планета распадается на луны, затмение, двойная система, путь по орбите с вехами.

Движение по окружности — рамка на оси (поворот), по эллипсу — петля flow точно по нарисованному эллипсу.
"""

from __future__ import annotations

import math

from morphkit import Loop, O, Slide
from morphkit import vector as V
from morphkit.presets import Fx
from morphkit.theme import mix

from lab import Variant
from lab._b_util import (arc_pieces, ax, axis, comet, ellipse_pts, head, orbit_dot, outline_circle, pol, shade, text,
                         thin, comet_ax, arc_band, squash, move_scale)

FAM = "orbit"
P = (9.0, 4.0)


def _sun(theme, name="!!sun", c=P, r=0.55, col="accent"):
    g = V.circle(c[0], c[1], r)
    return V.shape(name, g, fill=col, z=20, grad=V.gradient([(0, mix(theme.c(col), "FFFFFF", 0.35)), (1, theme.c(col))],
                                                             angle=60))


def _orbit(name, c, rx, ry=None, ln="line", lw=1.0, z=3, rot=0.0, **kw):
    ry = rx if ry is None else ry
    return O(name, "oval", c[0] - rx, c[1] - ry, 2 * rx, 2 * ry, fill=None, ln=ln, lw=lw, z=z, rot=rot, **kw)


# ----------------------------------------------------------------------------- 1. комета по станциям

def v_comet(theme) -> Variant:
    r = 2.35
    st_ang = [-90, 30, 150]
    names = ["Заявка", "Сборка", "Доставка"]
    bg = theme.c("bg")

    def state(k, sub):
        objs = head("Комета по этапам", sub)
        objs.append(_orbit("!!orb", P, r, lw=1.25))
        objs.append(_sun(theme, "!!csun", r=0.42, col="ink2"))
        for j, a in enumerate(st_ang):
            x, y = pol(*P, r, a)
            on = j == k
            objs.append(O(f"!!st{j}", "oval", x - 0.17, y - 0.17, 0.34, 0.34, fill="bg", ln="accent" if on else "ink2",
                          lw=2.0, z=8))
            lx, ly = pol(*P, r + 0.62, a)
            objs.append(text(f"!!sl{j}", lx - 0.9, ly - 0.2, 1.8, 0.4, names[j], sz=16, b=on,
                             col="accent" if on else "ink2", al="c", va="m"))
        objs += comet("cm", P, r, st_ang[k], d=0.3, n=9, gap=0.17, fill=theme.c("accent"), bg=bg, z=12)
        return objs

    return Variant(FAM, "comet", "Комета обходит этапы",
                   "Голова кометы с хвостом из убывающих точек едет по орбите от этапа к этапу (поворот на оси, "
                   "хвост тянется по дуге), станция под ней подсвечивается. Роль: этапы цикла, «где сейчас заказ».",
                   [Slide(state(0, "Старт"), dur=800), Slide(state(1, "Второй этап"), dur=850),
                    Slide(state(2, "Третий этап"), dur=850)],
                   tags=["orbit", "comet", "process", "navigation"], score=4)


# ----------------------------------------------------------------------------- 2. парад планет

def v_align(theme) -> Variant:
    c = (6.4, 4.2)
    radii = [0.95, 1.45, 1.95, 2.45, 2.95]
    sizes = [0.22, 0.3, 0.26, 0.36, 0.3]
    a1 = [150, -60, 70, -130, 20]
    goals = ["Продажи", "Продукт", "Найм", "Финансы", "Бренд"]

    def state(s, sub):
        objs = head("Парад планет", sub)
        objs.append(_sun(theme, "!!asun", c=c, r=0.35))
        for i, (r, d) in enumerate(zip(radii, sizes)):
            objs.append(_orbit(f"!!ao{i}", c, r, lw=0.9))
            a = a1[i] if s == 0 else -12
            objs.append(orbit_dot(f"!!ap{i}", c, r, a, d, R=3.3, fill="ink" if s < 2 else "accent", z=10))
        if s >= 1:
            for i, r in enumerate(radii):
                x, y = pol(*c, r, -12)
                objs.append(text(f"!!al{i}", x - 0.6, y - 0.62 if i % 2 == 0 else y + 0.28, 1.2, 0.34, goals[i], sz=12,
                                 col="ink2", al="c"))
        if s == 2:
            x0, y0 = pol(*c, 0.4, -12)
            x1, y1 = pol(*c, 3.4, -12)
            objs.append(V.shape("abeam", thin((x0, y0), (x1, y1), 0.03), fill="accent", z=6))
            objs.append(text("agoal", 10.0, 2.55, 3.0, 1.0, ["Одна цель", "на год"], sz=24, b=True, col="accent"))
        fx = []
        if s == 1:
            fx = [Fx("entrance_fade", f"!!al{i}", start="at", delay=0.1 + 0.06 * i, dur=0.3) for i in range(5)]
        if s == 2:
            fx = [Fx("entrance_wipe", "abeam", start="at", delay=0.1, dur=0.4, options={"direction": "left"}),
                  Fx("entrance_fade", "agoal", start="after", dur=0.3)]
        return objs, fx

    sl = []
    for s, (sub, d) in enumerate([("Каждое направление — на своей орбите", 800), ("Выстраиваем в линию", 900),
                                  ("Все смотрят в одну сторону", 600)]):
        o, f = state(s, sub)
        sl.append(Slide(o, dur=d, fx=f))
    return Variant(FAM, "align", "Парад планет: цели выстраиваются",
                   "Планеты на разных орбитах в случайных фазах, затем каждая по своей дуге приходит на общий луч, "
                   "луч прорисовывается к цели. Роль: согласование направлений, общая цель года.",
                   sl, tags=["orbit", "alignment", "metaphor"], score=4)


# ----------------------------------------------------------------------------- 3. наклон системы: вид сверху -> 3D

def v_tilt(theme) -> Variant:
    radii = [0.95, 1.5, 2.1, 2.75]
    sizes = [0.24, 0.32, 0.4, 0.3]
    speed = [70, 40, 25, 12]
    base = [200, -40, 100, 10]
    K = 0.34
    names = ["Ядро", "Модули", "Партнёры", "Рынок"]

    def state(s, sub):
        objs = head("Наклон системы", sub)
        k = 1.0 if s == 0 else K
        objs.append(_sun(theme, "!!tsun", r=0.42))
        for i, r in enumerate(radii):
            objs.append(_orbit(f"!!to{i}", P, r, r * k, lw=1.0))
            a = base[i] + (speed[i] if s == 2 else 0)
            x = P[0] + r * math.cos(math.radians(a))
            y = P[1] + r * k * math.sin(math.radians(a))
            depth = (math.sin(math.radians(a)) + 1) / 2 if s else 0.5
            d = sizes[i] * (0.7 + 0.6 * depth) if s else sizes[i]
            zz = 25 if (s and depth > 0.5) else 10
            objs.append(O(f"!!tp{i}", "oval", x - d / 2, y - d / 2, d, d, fill=shade(theme, "ink", 0.15 + 0.35 * (1 - depth)),
                          z=zz))
        if s == 0:
            for i, r in enumerate(radii):
                objs.append(text(f"tn{i}", P[0] + 3.1, P[1] - 1.6 + i * 0.5, 1.8, 0.4, names[i], sz=13, col="muted"))
        return objs

    return Variant(FAM, "tilt", "Вид сверху → наклон в 3D",
                   "Система орбит сверху; затем «камера» наклоняется — окружности сжимаются в эллипсы, планеты "
                   "меняют размер и слой по глубине, потом каждая проходит свой путь с разной скоростью. "
                   "Роль: из схемы — в объём, переход от структуры к динамике.",
                   [Slide(state(0, "Схема: четыре уровня"), dur=800), Slide(state(1, "Наклоняем — появляется глубина"),
                                                                           dur=900),
                    Slide(state(2, "Внутренние круги быстрее"), dur=900)],
                   tags=["orbit", "3d", "pseudo-3d", "depth"], score=3)


# ----------------------------------------------------------------------------- 4. переход по спирали на внешнюю орбиту

def v_transfer(theme) -> Variant:
    r1, r2 = 1.05, 2.6
    a1, a2 = 160, 300
    R = r2 + 0.3
    bg = theme.c("bg")

    def body(r, a, nm="!!tb", d=0.34, **kw):
        g = V.circle(P[0] + r, P[1], d / 2, seg=12)
        return axis(nm, g, P, R, rot=a, **kw)

    def state(s, sub):
        objs = head("Новый уровень", sub)
        objs.append(_sun(theme, "!!xsun", r=0.38, col="ink2"))
        objs.append(_orbit("!!xo1", P, r1, lw=1.0, ln="ink2" if s == 0 else "line"))
        objs.append(_orbit("!!xo2", P, r2, lw=1.25, ln="accent" if s else "line"))
        r = r1 if s == 0 else r2
        a = a1 if s == 0 else (a2 if s == 1 else a2 + 120)
        objs.append(body(r, a, fill="accent", z=12))
        for k in range(1, 7):  # хвост: те же радиус/угол позади
            t = k / 7
            objs.append(body(r - (0 if s != 1 else 0), a - k * (9 if s != 1 else 6), nm=f"!!tt{k}", d=0.34 * (1 - 0.7 * t),
                             fill=mix(theme.c("accent"), bg, 0.85 * t), z=12 - k))
        if s == 1:
            for k in range(14):  # след спирали
                t = (k + 0.5) / 14
                rr, aa = r1 + (r2 - r1) * t, a1 + (a2 - a1) * t
                x, y = pol(*P, rr, aa)
                objs.append(O(f"xs{k}", "oval", x - 0.04, y - 0.04, 0.08, 0.08, fill="muted", z=5))
        labs = [("Клиент", "первая покупка"), ("Постоянный", "вторая покупка"), ("Постоянный", "дальше — по кругу")]
        objs.append(text(f"xl{s}", 0.7, 3.3, 4.6, 1.2, [labs[s][0], labs[s][1]], sz=20, col="ink"))
        return objs

    loops = [Loop("spin", target=nm, period=4.5, name="xsp") for nm in ["!!tb"] + [f"!!tt{k}" for k in range(1, 7)]]
    return Variant(FAM, "transfer", "Переход на внешнюю орбиту по спирали",
                   "Тело в рамке на оси меняет и угол, и радиус — путь получается спиралью с внутренней орбиты на "
                   "внешнюю; на последнем шаге оно продолжает кружить петлёй «Вращение». "
                   "Роль: переход клиента/команды на следующий уровень, апгрейд.",
                   [Slide(state(0, "Внутренняя орбита"), dur=800), Slide(state(1, "Разгон — и выше"), dur=900),
                    Slide(state(2, "Новая орбита — новый ритм"), dur=850, loops=loops)],
                   tags=["orbit", "spiral-move", "loop", "metaphor"], score=4)


# ----------------------------------------------------------------------------- 5. спутники-навигация

def v_nav(theme) -> Variant:
    c = (4.0, 4.55)
    r = 1.95
    secs = [("Рынок", "Кто покупает и почему"), ("Продукт", "Что меняем в этом году"), ("Команда", "Кого нанимаем"),
            ("Деньги", "Сколько стоит план"), ("Сроки", "Когда увидим результат")]

    def state(k, sub):
        objs = head("Спутники разделов", sub)
        objs.append(_orbit("!!no", c, r, lw=1.0))
        objs.append(_sun(theme, "!!nsun", c=c, r=0.6, col="ink2"))
        for i in range(5):
            a = (i - k) * 72
            cur = i == k
            d = 0.7 if cur else 0.42
            objs.append(orbit_dot(f"!!nm{i}", c, r, a, d, R=r + 0.4, fill="accent" if cur else shade(theme, "ink", 0.45),
                                  z=10))
            for j in range(i + 1):
                g = V.circle(c[0] + r, c[1] + (j - i / 2) * 0.1, 0.03, seg=6)
                objs.append(axis(f"!!np{i}_{j}", g, c, r + 0.4, rot=a, fill="bg", z=11))
        x0, y0 = pol(*c, r + 0.4, 0)
        objs.append(O("!!nline", "line", x0, y0, 6.8 - x0, 0, ln="accent", lw=1.5, z=4))
        objs.append(text(f"nt{k}", 7.0, 4.05, 5.8, 0.8, f"0{k + 1} · {secs[k][0]}", sz=34, b=True, col="ink",
                         font="head"))
        objs.append(text(f"nd{k}", 7.0, 4.9, 5.8, 0.5, secs[k][1], sz=18, col="ink2"))
        return objs

    return Variant(FAM, "nav", "Спутники-разделы: текущий на оси",
                   "Пять спутников на орбите; система поворачивается так, что текущий раздел выходит на ось к тексту, "
                   "растёт и подсвечивается. Роль: навигация по разделам, «вы здесь».",
                   [Slide(state(0, "Раздел 1"), dur=800), Slide(state(1, "Раздел 2"), dur=800),
                    Slide(state(2, "Раздел 3"), dur=800)],
                   tags=["orbit", "navigation", "rotation"], score=4)


# ----------------------------------------------------------------------------- 6. орбита с читаемыми подписями

def v_labels(theme) -> Variant:
    c = (8.6, 4.15)
    r = 2.05
    items = ["Банк", "Склад", "Курьеры", "Маркетплейс", "Касса", "CRM", "Поддержка", "Аналитика"]

    def state(k, sub):
        objs = head("Экосистема вокруг", sub)
        objs.append(_orbit("!!lo", c, r, lw=1.0))
        objs.append(O("!!lc", "oval", c[0] - 0.75, c[1] - 0.75, 1.5, 1.5, fill="surface2", z=8))
        objs.append(text("!!lct", c[0] - 0.75, c[1] - 0.25, 1.5, 0.5, "Мы", sz=20, b=True, col="ink", al="c", va="m"))
        for i in range(8):
            a = -90 + (i - k) * 45
            cur = (i - k) % 8 == 2
            objs.append(orbit_dot(f"!!ld{i}", c, r, a, 0.26 if not cur else 0.38, R=r + 0.2,
                                  fill="accent" if cur else "ink2", z=10))
            x, y = pol(*c, r + 0.75, a)
            objs.append(text(f"!!lt{i}", x - 0.95, y - 0.2, 1.9, 0.4, items[i], sz=15 if not cur else 17, b=cur,
                             col="accent" if cur else "ink2", al="c", va="m"))
        return objs

    return Variant(FAM, "labels", "Орбита с горизонтальными подписями",
                   "Восемь партнёров на орбите; система поворачивается на один шаг (45°) — точки едут по дуге, "
                   "подписи остаются горизонтальными и смещаются по хорде (≈0,08 радиуса, незаметно). "
                   "Роль: экосистема, партнёры, «кто справа — тот в фокусе».",
                   [Slide(state(0, "В фокусе — курьеры"), dur=750), Slide(state(1, "Шаг: маркетплейс"), dur=750),
                    Slide(state(2, "Шаг: касса"), dur=750)],
                   tags=["orbit", "labels", "rotation", "ecosystem"], score=4)


# ----------------------------------------------------------------------------- 7. атом: три направления

def v_atom(theme) -> Variant:
    rx, ry = 2.7, 0.85
    tilts = [0, 60, 120]
    names = ["Сервис", "Данные", "Платформа"]

    def state(s, sub):
        objs = head("Атом продукта", sub)
        objs.append(_sun(theme, "!!nuc", r=0.42))
        loops = []
        for j, t in enumerate(tilts):
            if s == 0:
                a, b, rt = 1.7, 1.7, t
            else:
                a, b, rt = rx, ry, t
            hl = s == 2 and j == 1
            objs.append(_orbit(f"!!el{j}", P, a, b, rot=rt, ln="accent" if hl else "ink2", lw=2.0 if hl else 1.1,
                               la=1.0 if (s < 2 or hl) else 0.4))
            pts = ellipse_pts(P[0], P[1], a, b, 80, tilt=rt, a0=90 * j)
            loops.append(Loop("flow", points=pts, n=1 if s == 0 else 2, period=2.6 + 0.4 * j, size=0.16,
                              color="accent" if (s < 2 or hl) else "muted", name=f"el_{j}", z=9))
            if s >= 1:
                ex, ey = pol(*P, rx + 0.45, rt + (180 if j == 1 else 0))
                objs.append(text(f"!!en{j}", ex - 0.9, ey - 0.2, 1.8, 0.4, names[j], sz=15, b=hl,
                                 col="accent" if hl else "ink2", al="c", va="m"))
        return objs, loops

    sl = []
    for s, (sub, d) in enumerate([("Одно ядро", 800), ("Три направления вокруг", 900), ("Главное — данные", 600)]):
        o, lp = state(s, sub)
        sl.append(Slide(o, dur=d, loops=lp))
    return Variant(FAM, "atom", "Атом: электроны по эллипсам",
                   "Ядро и одна круговая орбита раскрываются в три наклонных эллипса; электроны бегут петлёй строго "
                   "по нарисованным эллипсам; одно направление подсвечивается. Роль: ядро + направления, «живая» "
                   "заставка раздела.",
                   sl, tags=["orbit", "ellipse", "loop", "flow", "metaphor"], score=4)


# ----------------------------------------------------------------------------- 8. вытянутая орбита и комета-петля

def v_ellipse(theme) -> Variant:
    sun = (7.4, 4.1)

    def state(s, sub):
        objs = head("Вытянутая орбита", sub)
        objs.append(_sun(theme, "!!esun", c=sun, r=0.45))
        if s == 0:
            cx, rx, ry = sun[0], 2.1, 2.1
        else:
            e = 0.78
            rx = 3.0
            ry = rx * math.sqrt(1 - e * e)
            cx = sun[0] + rx * e  # Солнце — в фокусе
        objs.append(_orbit("!!eo", (cx, sun[1]), rx, ry, lw=1.25))
        objs.append(_orbit("!!ep", sun, 1.3, lw=1.0, la=1.0 if s == 2 else 0.0, ln="ink2"))
        pts = ellipse_pts(cx, sun[1], rx, ry, 96, a0=180)
        loops = []
        for k in range(6):
            loops.append(Loop("flow", points=pts, n=1, period=4.2, size=0.22 * (1 - 0.13 * k), start=0.07 * k,
                              color=mix(theme.c("accent"), theme.c("bg"), 0.14 * k), name=f"cm_{k}", z=12 - k * 0.1))
        if s == 2:
            objs.append(O("meet", "oval", sun[0] - 1.3 - 0.13, sun[1] - 0.13, 0.26, 0.26, fill="bg", ln="accent", lw=2,
                          z=14))
            loops.append(Loop("ripple", target="meet", period=1.8, scale=2.2, color="accent", name="mt"))
            objs.append(text("mtx", 0.7, 4.6, 4.2, 0.9, ["Точка встречи —", "раз в цикл"], sz=18, col="ink2"))
        return objs, loops

    sl = []
    for s, (sub, d) in enumerate([("Круг: равномерно", 800), ("Вытянули: близко и далеко", 900),
                                  ("Пересечение с нашей орбитой", 700)]):
        o, lp = state(s, sub)
        sl.append(Slide(o, dur=d, loops=lp))
    return Variant(FAM, "ellipse", "Комета на вытянутой орбите",
                   "Комета из шести точек-петель с запаздыванием (голова и хвост) бежит строго по орбите; круг "
                   "вытягивается в эллипс с Солнцем в фокусе, затем появляется точка встречи с «кругами на воде». "
                   "Роль: редкие события, сезонный клиент, цикл с пиком.",
                   sl, tags=["orbit", "ellipse", "loop", "comet"], score=3)


# ----------------------------------------------------------------------------- 9. планета распадается на луны

def v_moons(theme) -> Variant:
    r_orb = 2.3
    parts = V.slices(V.circle(P[0], P[1], 1.15), 3, pivot=P, start=-90)
    names = ["Поиск", "Платежи", "Доставка"]
    mang = [-30, 90, 210]

    def state(s, sub):
        objs = head("Из одного — три", sub)
        if s >= 1:
            objs.append(_orbit("!!mo", P, r_orb, lw=1.0))
        objs.append(O("!!mcore", "oval", P[0] - 0.3, P[1] - 0.3, 0.6, 0.6, fill="surface2", z=6))
        for j, g in enumerate(parts):
            rot = mang[j] + (0 if s < 2 else 100)
            if s == 0:
                gg = V.resample(g, 90)
            else:
                gg = V.resample(V.circle(*pol(*P, r_orb, mang[j]), 0.45), 90)
            col = ["accent", "ink", "ink2"][j]
            objs.append(ax(f"!!mn{j}", gg, mang[j], pivot=P, R=3.0, fill=col, ln="bg", lw=2.0, z=10)
                        if s < 2 else axis(f"!!mn{j}", V.rotate(gg, -mang[j], origin=P), P, 3.0, rot=rot, fill=col,
                                           ln="bg", lw=2.0, z=10))
            if s >= 1:
                x, y = pol(*P, r_orb + 0.6 + 0.45 * abs(math.cos(math.radians(rot))), rot)
                objs.append(text(f"!!mt{j}", x - 0.9, y - 0.2, 1.8, 0.4, names[j], sz=15, col="ink2", al="c", va="m"))
        return objs

    return Variant(FAM, "moons", "Планета распадается на луны",
                   "Цельный диск режется на три сектора, они переливаются в круглые луны и уходят на орбиту, затем "
                   "луны идут по кругу. Роль: разделение монолита на сервисы, отделение направлений.",
                   [Slide(state(0, "Монолит"), dur=800), Slide(state(1, "Три сервиса на орбите"), dur=900),
                    Slide(state(2, "Каждый — своим ходом"), dur=850)],
                   tags=["orbit", "fragment", "shape-morph", "split"], score=4)


# ----------------------------------------------------------------------------- 10. затмение

def v_eclipse(theme) -> Variant:
    sc, rs, rm = (8.6, 4.05), 1.6, 1.5

    def state(s, sub):
        objs = head("Затмение", sub)
        mx = [sc[0] - 3.6, sc[0] - 1.35, sc[0]][s]
        moon = V.circle(mx, sc[1], rm)
        sun = V.circle(sc[0], sc[1], rs)
        vis = V.subtract(sun, moon)
        if vis.is_empty or vis.area < 0.05:
            vis = V.subtract(sun, V.circle(sc[0], sc[1], rs - 0.06))
        vis = V.resample(vis if vis.geom_type == "Polygon" else max(vis.geoms, key=lambda q: q.area), 160)
        if s == 2:
            vis = V.resample(V.circle(sc[0] + 1.2, sc[1] - 1.05, 0.06), 160)  # остаток света — «бриллиант» на краю
        objs.append(V.shape("!!esun", vis, fill="accent", z=8))
        objs.append(O("!!emoon", "oval", mx - rm, sc[1] - rm, 2 * rm, 2 * rm, fill="surface", ln="line", lw=1.0, z=9))
        if s == 2:
            objs.append(O("halo", "oval", sc[0] - rs - 0.12, sc[1] - rs - 0.12, 2 * rs + 0.24, 2 * rs + 0.24, fill=None,
                          ln="accent", lw=3.0, z=7))
        labs = ["Наш рынок", "Новый игрок закрывает часть", "Остался только край — пора действовать"]
        objs.append(text(f"etx{s}", 0.7, 5.3, 5.2, 1.0, labs[s], sz=18, col="ink2"))
        return objs

    return Variant(FAM, "eclipse", "Затмение: конкурент закрывает рынок",
                   "Видимая часть «солнца» — вычитание диска луны из диска солнца, перелив серпа на каждом шаге; "
                   "в полной фазе вспыхивает ореол. Роль: угроза, вытеснение, «что остаётся нам».",
                   [Slide(state(0, "Полный свет"), dur=800), Slide(state(1, "Тень наползает"), dur=900),
                    Slide(state(2, "Полная фаза"), dur=900,
                          fx=[Fx("entrance_faded_zoom", "halo", start="at", delay=0.1, dur=0.5)])],
                   tags=["orbit", "boolean", "shape-morph", "metaphor"], score=3)


# ----------------------------------------------------------------------------- 11. двойная система

def v_binary(theme) -> Variant:
    c = P

    def state(s, sub):
        a = [-20, 100, 220][s]
        objs = head("Двойная звезда", sub)
        objs.append(_orbit("!!bo1", c, 0.75, lw=1.0, ln="line"))
        objs.append(_orbit("!!bo2", c, 2.1, lw=1.0, ln="line"))
        tether = V.Polygon([(c[0] - 0.75, c[1] - 0.012), (c[0] + 2.1, c[1] - 0.012), (c[0] + 2.1, c[1] + 0.012),
                            (c[0] - 0.75, c[1] + 0.012)])
        objs.append(axis("!!bt", V.rotate(tether, 180, origin=c), c, 2.6, rot=a, fill="ink2", fa=0.6, z=5))
        objs.append(orbit_dot("!!bA", c, 0.75, a + 180, 0.9, R=2.6, fill="accent", z=10))
        objs.append(orbit_dot("!!bB", c, 2.1, a, 0.45, R=2.6, fill="ink", z=10))
        objs.append(O("!!bc", "oval", c[0] - 0.05, c[1] - 0.05, 0.1, 0.1, fill="ink2", z=11))
        ax_, ay = pol(*c, 0.75, a + 180)
        bx, by = pol(*c, 2.1, a)
        objs.append(text("!!bla", ax_ - 0.9, ay + 0.5, 1.8, 0.4, "Продукт", sz=15, b=True, col="accent", al="c"))
        objs.append(text("!!blb", bx - 0.9, by + 0.3, 1.8, 0.4, "Сервис", sz=15, col="ink2", al="c"))
        return objs

    return Variant(FAM, "binary", "Двойная система вокруг общего центра",
                   "Тяжёлое и лёгкое тело вращаются вокруг общего центра масс, связь — тонкая лента через центр "
                   "на той же оси. Роль: партнёрство, продукт и сервис, взаимозависимость.",
                   [Slide(state(0, "Два тела — один центр"), dur=800), Slide(state(1, "Двигаются вместе"), dur=850),
                    Slide(state(2, "Лёгкое проходит больший путь"), dur=850)],
                   tags=["orbit", "rotation", "metaphor"], score=3)


# ----------------------------------------------------------------------------- 12. путь по орбите с вехами

def v_path(theme) -> Variant:
    r_in, r_out = 2.0, 2.18
    rm = (r_in + r_out) / 2
    marks = [(-90, "Старт"), (-18, "MVP"), (54, "Пилот"), (126, "Релиз"), (198, "Масштаб")]
    bg = theme.c("bg")

    def state(frac, sub):
        a1 = -90 + 360 * frac
        objs = head("Путь по орбите", sub)
        objs.append(_orbit("!!po", P, rm, lw=1.0, ln="line"))
        objs += arc_pieces("!!pp", P, r_in, r_out, -90, a1, k=10, fill="accent", z=7, R=2.5)
        objs += comet("pc", P, rm, a1, d=0.32, n=6, gap=0.14, fill=theme.c("accent"), bg=bg, z=12)
        for j, (a, nm) in enumerate(marks):
            done = a <= a1 + 0.5
            x, y = pol(*P, rm, a)
            objs.append(O(f"!!pm{j}", "oval", x - 0.13, y - 0.13, 0.26, 0.26, fill="accent" if done else "bg",
                          ln="accent" if done else "ink2", lw=1.5, z=9))
            lx, ly = pol(*P, rm + 0.62, a)
            objs.append(text(f"!!pl{j}", lx - 0.8, ly - 0.2, 1.6, 0.4, nm, sz=15, b=done, col="ink" if done else "muted",
                             al="c", va="m"))
        objs.append(text(f"pn{int(frac * 100)}", P[0] - 1.2, P[1] - 0.45, 2.4, 0.9, f"{int(frac * 100)}%", sz=44,
                         b=True, col="ink", al="c", font="head"))
        return objs

    return Variant(FAM, "path", "Путь по орбите: вехи загораются",
                   "Комета идёт по орбите и оставляет за собой след-дугу (кусочки на оси, растут по кругу), "
                   "пройденные вехи заливаются. Роль: дорожная карта проекта в форме цикла.",
                   [Slide(state(0.2, "MVP впереди"), dur=800), Slide(state(0.42, "MVP готов"), dur=850),
                    Slide(state(0.62, "Пилот запущен"), dur=800)],
                   tags=["orbit", "progress", "comet", "roadmap"], score=4)


# ----------------------------------------------------------------------------- ЖИВАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ 1: система продукта

def seq_system(theme) -> Variant:
    """8 состояний одной системы: появление -> планета 1 на оси -> отделяется в крупный диск-панель -> возвращается,
    на оси планета 2 -> наклон в 3D -> планеты сходят с орбит в пузырьковую диаграмму -> возвращаются с размером
    по данным -> система уходит на фон под вывод."""
    c = P
    radii = [1.1, 1.75, 2.4, 3.05]
    names = ["Ядро", "Мобильное", "B2B", "Экспорт"]
    vals = [48, 31, 22, 9]
    a0 = [130, 210, -60, 40]
    speeds = [1.0, 0.75, 0.55, 0.4]
    K = 0.42
    # углы по состояниям: шаг 1 — планета 1 приходит на 0°, шаг 3 — планета 2 приходит на 0°
    ang = {0: a0[:]}
    d1 = (0 - a0[1]) % 360 - 360 if (0 - a0[1]) % 360 > 180 else (0 - a0[1]) % 360  # кратчайший до оси
    ang[1] = [a0[i] + d1 * speeds[i] / speeds[1] for i in range(4)]
    ang[2] = ang[1][:]
    d3 = ((0 - ang[1][2]) + 180) % 360 - 180
    ang[3] = [ang[1][i] + d3 * speeds[i] / speeds[2] for i in range(4)]
    for st in (4, 5, 6, 7):
        ang[st] = ang[3][:]
    sizes = [0.42, 0.36, 0.32, 0.26]

    def planet_geo(i, st):
        a = ang[st][i]
        r = radii[i]
        x, y = pol(*c, r, a)
        d = sizes[i]
        if st in (1, 3) and i == (1 if st == 1 else 2):
            d = 0.62
        if st == 2:
            if i == 1:
                return V.circle(3.4, 4.35, 1.65, seg=16)
            x, y = c[0] + 1.6 + (x - c[0]) * 0.62, c[1] + (y - c[1]) * 0.62
            d *= 0.62
        if st in (4, 6, 7):
            depth = (math.sin(math.radians(a)) + 1) / 2
            y = c[1] + (y - c[1]) * K
            dv = 0.25 + 0.75 * math.sqrt(vals[i] / max(vals)) if st >= 6 else 1.0
            d = (d if st == 4 else 0.75 * dv) * (0.75 + 0.5 * depth)
            if st == 7:
                x, y, d = c[0] + 1.3 + (x - c[0]) * 0.75, c[1] - 0.9 + (y - c[1]) * 0.75, d * 0.75
        if st == 5:
            d = 2.0 * math.sqrt(vals[i] / max(vals))
            x, y = 2.0 + [0, 2.7, 5.1, 7.1][i] + d / 2, 4.6 - d / 2 + 0.9
        return V.circle(x, y, d / 2, seg=16)

    def orbit_obj(i, st):
        r = radii[i]
        cx, cy, rx, ry, la = c[0], c[1], r, r, 1.0
        if st == 2:
            cx, rx, ry = c[0] + 1.6, r * 0.62, r * 0.62
        if st in (4, 6, 7):
            ry = r * K
        if st == 5:
            rx = ry = 0.05
            cx, cy, la = 1.4, 5.0, 0.0
        if st == 7:
            cx, cy, rx, ry, la = c[0] + 1.3, c[1] - 0.9, rx * 0.75, ry * 0.75, 0.35
        return _orbit(f"!!so{i}", (cx, cy), rx, ry, lw=1.0, la=la)

    heads = [("Система продукта", "Четыре направления вокруг ядра"), ("Направление 2", "Выходит на ось"),
             ("Мобильное", "Крупным планом"), ("Направление 3", "Следующее на оси"), ("Взгляд сбоку", "Система в объёме"),
             ("По выручке", "Планеты сходят с орбит"), ("Размер = выручка", "Обратно на орбиты"),
             ("Ядро держит половину", "Система уходит на фон")]
    slides = []
    for st in range(8):
        objs = head(*heads[st])
        sun_r = 0.32
        scx, scy = c
        if st == 2:
            scx, sun_r = c[0] + 1.6, 0.2
        if st == 5:
            scx, scy, sun_r = 1.4, 5.0, 0.06
        if st == 7:
            scx, scy, sun_r = c[0] + 1.3, c[1] - 0.9, 0.24
        objs.append(V.shape("!!ssun", V.circle(scx, scy, sun_r), fill="muted", fa=0.4 if st == 7 else 1.0, z=15))
        for i in range(4):
            objs.append(orbit_obj(i, st))
            hl = (st in (1, 2) and i == 1) or (st == 3 and i == 2) or (st == 7 and i == 0)
            col = "accent" if hl else shade(theme, "ink", 0.15 + 0.15 * i)
            if st == 2 and i == 1:
                col = "surface2"
            zz = 20
            if st in (4, 6, 7) and math.sin(math.radians(ang[st][i])) < 0:
                zz = 10
            objs.append(ax(f"!!sp{i}", planet_geo(i, st), ang[st][i], pivot=c, fill=col,
                           ln="accent" if (st == 2 and i == 1) else None, lw=2.0 if (st == 2 and i == 1) else 0,
                           fa=0.5 if (st == 7 and not hl) else 1.0, z=zz if not (st == 2 and i == 1) else 25))
        fx = []
        if st == 0:
            fx = [Fx("entrance_spinner", f"!!sp{i}", start="at", delay=0.1 + 0.1 * i, dur=0.6) for i in range(4)]
        if st in (1, 3):
            k = 1 if st == 1 else 2
            x, y = pol(*c, radii[k], 0)
            objs.append(text(f"sl{st}", x + 0.45, y - 0.25, 2.4, 0.5, names[k], sz=20, b=True, col="accent", va="m"))
        if st == 2:
            objs.append(text("sd1", 2.1, 3.55, 2.6, 0.9, "31%", sz=48, b=True, col="ink", al="c", font="head"))
            objs.append(text("sd2", 2.1, 4.5, 2.6, 0.8, ["выручки", "+18% за год"], sz=15, col="ink2", al="c"))
            fx = [Fx("entrance_fade", "sd1", start="at", delay=0.15, dur=0.35),
                  Fx("entrance_fade", "sd2", start="after", dur=0.3)]
        if st == 5:
            for i in range(4):
                d = 2.0 * math.sqrt(vals[i] / max(vals))
                x = 2.0 + [0, 2.7, 5.1, 7.1][i] + d / 2
                objs.append(text(f"sb{i}", x - 1.1, 5.65, 2.2, 0.8, [names[i], f"{vals[i]}%"], sz=15, col="ink2",
                                 al="c"))
        if st == 7:
            objs.append(text("sfin", 0.7, 4.4, 6.5, 1.4, ["48% выручки —", "от ядра"], sz=36, b=True, col="ink",
                             font="head"))
        slides.append(Slide(objs, dur=[800, 900, 850, 900, 900, 900, 900, 850][st], fx=fx))
    return Variant(FAM, "seq_system", "Живая система продукта (8 состояний)",
                   "Одна планетная система ведёт раздел: планеты по очереди выходят на ось, одна отделяется в "
                   "крупный диск с цифрой и возвращается, система наклоняется в объём, планеты сходят с орбит в "
                   "пузырьковую диаграмму и возвращаются с размером по данным, затем уходят на фон под вывод.",
                   slides, tags=["seq", "orbit", "3d", "chart", "background", "navigation"], score=3)


# ----------------------------------------------------------------------------- ЖИВАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ 2: путь клиента

def seq_journey(theme) -> Variant:
    """Комета-курсор на 8 состояний: станции на орбите -> комета к станции 1 -> лупа на станции и деталь ->
    к станции 2 (лупа едет вместе) -> спиралью на внешнюю орбиту -> кружит петлёй -> наклон -> уход назад."""
    c = (9.2, 4.0)
    r1, r2 = 1.35, 2.55
    st_a = [-90, 0, 90, 180]
    st_n = ["Реклама", "Сайт", "Покупка", "Доставка"]
    bg, acc = theme.c("bg"), theme.c("accent")
    K = 0.36

    def tilt(st):
        if st == 6:
            return lambda x, y: (x, c[1] + (y - c[1]) * K)
        if st == 7:
            return lambda x, y: (c[0] + 1.0 + (x - c[0]) * 0.7, c[1] - 1.4 + (y - c[1]) * K * 0.7)
        return None

    pos = {0: (r1, -90), 1: (r1, 0), 2: (r1, 0), 3: (r1, 90), 4: (r2, 300), 5: (r2, 300), 6: (r2, 300),
           7: (r2, 300)}
    heads = [("Путь клиента", "Четыре касания"), ("Касание 1 → 2", "Клиент пришёл на сайт"),
             ("Сайт крупно", "Лупа на станции"), ("Касание 3", "Лупа едет вместе с клиентом"),
             ("Повторная покупка", "Выход на внешнюю орбиту"), ("Постоянный клиент", "Новый круг — без рекламы"),
             ("Две орбиты", "Вид сбоку"), ("Треть вернулась", "Система уходит назад")]
    slides = []
    for st in range(8):
        xf = tilt(st)
        f = xf or (lambda x, y: (x, y))
        objs = head(*heads[st])
        for j, r in enumerate((r1, r2)):
            ry = r * (K if st == 6 else (K * 0.7 if st == 7 else 1.0))
            rx = r * (0.7 if st == 7 else 1.0)
            cx, cy = (c[0] + 1.0, c[1] - 1.4) if st == 7 else c
            vis = j == 0 or st >= 4
            objs.append(_orbit(f"!!jo{j}", (cx, cy), rx, ry, lw=1.25 if j == 0 else 1.0,
                               ln="ink2" if j == 0 else "accent", la=(1.0 if vis else 0.0) * (0.5 if st == 7 else 1)))
        for k, a in enumerate(st_a):
            x, y = f(*pol(*c, r1, a))
            passed = (st >= 1 and k <= 1) or (st >= 3 and k <= 2)
            objs.append(O(f"!!js{k}", "oval", x - 0.15, y - 0.15, 0.3, 0.3, fill="accent" if passed else "bg",
                          ln="accent" if passed else "ink2", lw=1.5, z=9, fa=1.0))
            if st < 6:
                lx, ly = pol(*c, r1 - 0.62 if k in (1, 3) else r1 + 0.5, a)
                if k == 0:
                    lx, ly = pol(*c, r1 + 0.42, a)
                objs.append(text(f"!!jl{k}", lx - 0.75, ly - 0.2, 1.5, 0.4, st_n[k], sz=13, col="ink2" if not passed
                                 else "ink", al="c", va="m", b=passed))
        r, a = pos[st]
        sk = (lambda x, y: 0.7 + 0.6 * ((y - c[1]) / (r * K) + 1) / 2) if st == 6 else None
        objs += comet_ax("jc", c, r, a, d=0.3, n=7, gap=0.13, fill=acc, bg=bg, z=14, xf=xf, size_k=sk, R=9.6)
        if st in (2, 3):
            ka = 0 if st == 2 else 90
            lens = arc_band(c[0], c[1], r1 - 0.42, r1 + 0.42, ka - 24, ka + 24, 24)
            objs.append(ax("!!jlens", lens, ka, pivot=c, fill="accent", fa=0.16, ln="accent", lw=2.5, z=16))
            tx = ["Сайт: 3 минуты", "Покупка: 1 из 5"][st - 2]
            objs.append(text(f"jd{st}", 0.7, 3.6, 4.6, 0.6, tx, sz=24, b=True, col="accent", font="head"))
        loops = []
        if st == 7:
            objs.append(text("jfin", 0.7, 4.3, 6.4, 1.5, ["33% покупают", "повторно"], sz=40, b=True, col="ink",
                             font="head"))
        if st == 5:
            loops = [Loop("spin", target=nm, period=4.5, name="jsp") for nm in
                     ["!!jch"] + [f"!!jct{k}" for k in range(1, 8)]]
        slides.append(Slide(objs, dur=[800, 850, 700, 850, 900, 700, 900, 850][st], loops=loops,
                            fx=[Fx("entrance_fade", f"jd{st}", start="at", delay=0.1, dur=0.35)] if st in (2, 3) else []))
    return Variant(FAM, "seq_journey", "Комета-курсор: путь клиента (8 состояний)",
                   "Комета-курсор идёт по станциям орбиты, на станции её встречает лупа-дуга с деталью и едет "
                   "вместе с ней, затем комета по спирали выходит на внешнюю орбиту и кружит петлёй, обе орбиты "
                   "наклоняются в объём и уходят назад под вывод. Роль: воронка/путь клиента через весь раздел.",
                   slides, tags=["seq", "orbit", "comet", "magnifier", "spiral-move", "3d", "loop"], score=4)


def variants(theme) -> list[Variant]:
    return [v_comet(theme), v_align(theme), v_tilt(theme), v_transfer(theme), v_nav(theme), v_labels(theme),
            v_atom(theme), v_ellipse(theme), v_moons(theme), v_eclipse(theme), v_binary(theme), v_path(theme),
            seq_system(theme), seq_journey(theme)]
