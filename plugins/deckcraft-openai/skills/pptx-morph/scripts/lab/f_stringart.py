"""Семейство «Линии»: таблица умножения на круге (кардиоида -> нефроида), муар колец и вееров, розы-кривые,
гиперболоид из прямых (3D из 2D), огибающая-парабола -> звезда, веер -> вихрь, сеть хорд с сигналами, фигуры
Лиссажу из точек, глобус из меридианов -> карта, волна -> круговая волна.

Каждая хорда — тонкая форма в рамке на оси круга: положение — поворот (по дуге), длина — перелив формы.
"""

from __future__ import annotations

import math
import random

from morphkit import Loop, O, Slide
from morphkit import vector as V
from morphkit.presets import Fx
from morphkit.theme import mix

from lab import Variant
from lab._b_util import (ax, axis, head, pol, shade, text, thin)

FAM = "stringart"
C = (9.0, 4.0)


def chord(name, c, R, a, b, w=0.014, prev_m=None, **kw):
    """Хорда круга между углами a и b как форма на оси: rot = середина, перелив = полуугол.
    prev_m — середина на прошлом слайде: выбираем из двух равных представлений то, что ближе по повороту."""
    m, d = (a + b) / 2, (b - a) / 2
    if prev_m is not None:
        alt = (m + 180, 180 - d)
        if abs(((alt[0] - prev_m + 180) % 360) - 180) < abs(((m - prev_m + 180) % 360) - 180):
            m, d = alt
    x = c[0] + R * math.cos(math.radians(d))
    h = R * math.sin(math.radians(d))
    g = V.Polygon([(x - w / 2, c[1] - h), (x + w / 2, c[1] - h), (x + w / 2, c[1] + h), (x - w / 2, c[1] + h)])
    return axis(name, g, c, R * 1.001, rot=m, **kw), m


# ----------------------------------------------------------------------------- 1. таблица умножения: кардиоида -> нефроида

def v_times(theme) -> Variant:
    N, R = 96, 2.6
    ks = [2, 3, 5]
    prev = [None] * N

    def state(s, sub):
        objs = head("Умножение на круге", sub)
        objs.append(O("!!tc", "oval", C[0] - R, C[1] - R, 2 * R, 2 * R, fill=None, ln="line", lw=1.0, z=3))
        k = ks[s]
        for i in range(N):
            a = 360 * i / N - 90
            b = 360 * i * k / N - 90
            if abs(((b - a) + 180) % 360 - 180) < 0.5:
                b = a + 0.6
            col = mix(theme.c("accent"), theme.c("ink"), i / N)
            o, prev[i] = chord(f"!!tch{i}", C, R, a, b, prev_m=prev[i], fill=col, fa=0.85, z=6)
            objs.append(o)
        objs.append(text(f"tk{s}", 0.7, 3.3, 3.5, 0.9, f"× {k}", sz=44, b=True, col="accent", font="head"))
        return objs

    return Variant(FAM, "times", "Таблица умножения рисует кардиоиду",
                   "96 хорд: точка i соединена с точкой k·i; при смене множителя хорды поворачиваются по кругу и "
                   "меняют длину — кардиоида перетекает в нефроиду и звезду. Роль: «простое правило — сложный "
                   "результат», заставка раздела про алгоритмы.",
                   [Slide(state(0, "Каждая точка — к удвоенной"), dur=800), Slide(state(1, "Утроенной"), dur=900),
                    Slide(state(2, "Пятикратной"), dur=900)],
                   tags=["lines", "string-art", "rotation", "math"], score=5)


# ----------------------------------------------------------------------------- 2. муар колец

def v_moire_rings(theme) -> Variant:
    n, step = 26, 0.11

    def state(s, sub):
        objs = head("Муар", sub)
        off = [0.0, 0.32, 0.65][s]
        for k in range(n):
            r = 0.15 + k * step
            objs.append(O(f"!!ma{k}", "oval", C[0] - off - r, C[1] - r, 2 * r, 2 * r, fill=None, ln="ink2", lw=1.6, z=5))
            objs.append(O(f"!!mb{k}", "oval", C[0] + off - r, C[1] - r, 2 * r, 2 * r, fill=None, ln="accent", lw=1.6,
                          la=0.85, z=6))
        objs.append(text(f"mt{s}", 0.7, 3.4, 4.0, 1.2, [["Два плана совпадают", "Расходятся на шаг", "Видна интерференция"][s]],
                         sz=18, col="ink2"))
        return objs

    return Variant(FAM, "moire_rings", "Муар двух систем колец",
                   "Две системы концентрических колец совпадают, затем расходятся — возникают полосы-интерференции. "
                   "Роль: «две команды/два плана: где совпадаем, где спорим», фон-переход.",
                   [Slide(state(0, "Совпадение"), dur=800), Slide(state(1, "Сдвиг"), dur=900),
                    Slide(state(2, "Узор расхождений"), dur=900)],
                   tags=["lines", "moire", "background"], score=3)


# ----------------------------------------------------------------------------- 3. муар вееров

def v_moire_fan(theme) -> Variant:
    n, R = 90, 2.9

    def fan(id, rot0, col, z):
        out = []
        g = V.Polygon([(C[0] + 0.25, C[1] - 0.008), (C[0] + R, C[1] - 0.01), (C[0] + R, C[1] + 0.01),
                       (C[0] + 0.25, C[1] + 0.008)])
        for i in range(n):
            out.append(axis(f"!!{id}{i}", g, C, R * 1.001, rot=rot0 + 360 * i / n, fill=col, z=z))
        return out

    def state(s, sub):
        objs = head("Розетка муара", sub)
        objs += fan("fa", 0, "ink2", 5)
        objs += fan("fb", [0, 1.6, 3.2][s], "accent", 6)
        return objs

    return Variant(FAM, "moire_fan", "Два веера: поворот на градус рождает розетку",
                   "Два веера по 90 лучей; второй поворачивается на 1,6°, затем на 3,2° — проступают лепестки "
                   "муара. Роль: «маленькое изменение — большой эффект», переход к разделу.",
                   [Slide(state(0, "Лучи совпали"), dur=800), Slide(state(1, "Поворот на 1,6°"), dur=900),
                    Slide(state(2, "На 3,2°"), dur=900)],
                   tags=["lines", "moire", "rotation"], score=3)


# ----------------------------------------------------------------------------- 4. розы-кривые

def lobe(c, R, k, n=64):
    """Один лепесток розы r = R·cos(kθ), θ ∈ [−π/2k, π/2k], ось лепестка — угол 0."""
    pts = []
    for q in range(n):
        t = -math.pi / (2 * k) + math.pi / k * q / (n - 1)
        r = R * math.cos(k * t)
        pts.append((c[0] + r * math.cos(t), c[1] + r * math.sin(t)))
    pts[0] = pts[-1] = c
    return V.Polygon(pts[:-1])


def v_rose(theme) -> Variant:
    ks = [3, 5, 7]
    M = 7
    R = 2.6

    def state(s, sub):
        objs = head("Роза", sub)
        k = ks[s]
        for j in range(M):
            on = j < k
            g = V.resample(lobe(C, R if on else 0.05, k), 64)
            objs.append(axis(f"!!rl{j}", g, C, R * 1.001, rot=-90 + 360 * j / k if on else -90 + 360 * j / M,
                             fill="accent", fa=0.12, ln="accent", lw=1.5, la=1.0 if on else 0.0, z=6))
            g2 = V.resample(lobe(C, R * 0.62 if on else 0.05, k), 64)
            objs.append(axis(f"!!ri{j}", g2, C, R * 1.001, rot=-90 + 180 / k + 360 * j / k if on else -90,
                             fill=None, ln="ink2", lw=1.0, la=1.0 if on else 0.0, z=7))
        objs.append(text(f"rk{s}", 0.7, 3.3, 3.8, 0.9, f"{k} лепестков", sz=30, b=True, col="ink", font="head"))
        return objs

    return Variant(FAM, "rose", "Роза: 3 -> 5 -> 7 лепестков",
                   "Лепестки кривой r = cos(kθ) поворачиваются на новые места и сужаются, лишние вырастают из центра; "
                   "внутренняя роза сдвинута на полшага. Роль: рост числа направлений, «из трёх продуктов — семь».",
                   [Slide(state(0, "Три направления"), dur=800), Slide(state(1, "Пять"), dur=900),
                    Slide(state(2, "Семь"), dur=900)],
                   tags=["lines", "rose", "shape-morph", "rotation"], score=4)


# ----------------------------------------------------------------------------- 5. гиперболоид из прямых

def v_hyper(theme) -> Variant:
    N = 40
    cx, yt, yb, rx, ry = 8.9, 1.85, 6.1, 2.2, 0.42

    def state(s, sub):
        objs = head("Гиперболоид", sub)
        tw = [0, 75, 140][s]
        objs.append(O("!!ht", "oval", cx - rx, yt - ry, 2 * rx, 2 * ry, fill=None, ln="ink2", lw=1.25, z=4))
        objs.append(O("!!hb", "oval", cx - rx, yb - ry, 2 * rx, 2 * ry, fill=None, ln="ink2", lw=1.25, z=4))
        for i in range(N):
            a = math.radians(360 * i / N)
            b = math.radians(360 * i / N + tw)
            p = (cx + rx * math.cos(a), yb + ry * math.sin(a))
            q = (cx + rx * math.cos(b), yt + ry * math.sin(b))
            depth = (math.sin(a) + math.sin(b)) / 2
            col = "accent" if depth > 0 else shade(theme, "ink", 0.55)
            objs.append(ax(f"!!hl{i}", thin(p, q, 0.018), 0.0, pivot=(cx, 4.0), fill=col,
                           fa=0.95 if depth > 0 else 0.6, z=8 if depth > 0 else 5))
        return objs

    return Variant(FAM, "hyper", "Цилиндр из прямых скручивается в гиперболоид",
                   "40 прямых между двумя эллипсами: верхний конец каждой сдвигается по эллипсу — появляется "
                   "«талия», объём из одних прямых (передние линии ярче, задние приглушены). "
                   "Роль: «прямые решения дают кривую форму», переход к стратегии.",
                   [Slide(state(0, "Цилиндр"), dur=800), Slide(state(1, "Поворот"), dur=900),
                    Slide(state(2, "Талия"), dur=900)],
                   tags=["lines", "pseudo-3d", "string-art"], score=5)


# ----------------------------------------------------------------------------- 6. огибающая: кривая роста -> звезда

def v_envelope(theme) -> Variant:
    N = 48
    x0, y0, L = 3.0, 6.3, 4.6  # угол осей (левый нижний)
    sc = (9.0, 4.0)
    S = 2.4

    def state(s, sub):
        objs = head("Кривая из прямых", sub)
        for i in range(N):
            if s == 0:
                t = (i + 1) / (N + 1)
                p, q = (x0, y0 - L * (1 - t)), (x0 + L * t * 1.9, y0)
            else:
                k, j = i // 12, i % 12
                t = (j + 1) / 13
                ang = math.radians(90 * k + (45 if s == 2 else 0))
                ux, uy = math.cos(ang), math.sin(ang)
                vx, vy = -uy, ux
                p = (sc[0] + ux * S * (1 - t), sc[1] + uy * S * (1 - t))
                q = (sc[0] + vx * S * t, sc[1] + vy * S * t)
            col = mix(theme.c("accent"), theme.c("ink2"), (i % 12) / 12 if s else i / N)
            objs.append(ax(f"!!ev{i}", thin(p, q, 0.016), 0.0, pivot=sc, fill=col, z=6))
        if s == 0:
            objs.append(text("evt", 8.4, 2.4, 4.4, 1.0, ["Ни одной кривой —", "только прямые"], sz=18, col="ink2"))
        return objs

    return Variant(FAM, "envelope", "Огибающая: кривая роста из прямых -> звезда",
                   "48 отрезков между двумя осями дают плавную кривую-огибающую; затем те же отрезки "
                   "расходятся на четыре четверти — звезда, и она поворачивается на 45°. "
                   "Роль: «из простых шагов — плавный рост», визуальная пауза.",
                   [Slide(state(0, "Кривая роста"), dur=800), Slide(state(1, "Четыре стороны"), dur=900),
                    Slide(state(2, "Поворот"), dur=800)],
                   tags=["lines", "string-art", "envelope"], score=3)


# ----------------------------------------------------------------------------- 7. веер -> вихрь

def v_vortex(theme) -> Variant:
    n, R = 72, 2.7

    def state(s, sub):
        objs = head("Веер в вихрь", sub)
        rho = [0.0, 0.9, 1.6][s]
        twist = [0, 25, 50][s]
        for i in range(n):
            if rho == 0:
                g = thin((C[0] + 0.3, C[1]), (C[0] + R, C[1]), 0.016)
            else:
                h = math.sqrt(R * R - rho * rho)
                g = thin((C[0] + rho, C[1] - h), (C[0] + rho, C[1] + h), 0.016)
            col = "accent" if i % 6 == 0 else shade(theme, "ink", 0.35)
            objs.append(axis(f"!!vx{i}", g, C, R * 1.001, rot=360 * i / n + twist, fill=col, z=6))
        objs.append(O("!!vc", "oval", C[0] - R, C[1] - R, 2 * R, 2 * R, fill=None, ln="line", lw=1, z=3))
        return objs

    return Variant(FAM, "vortex", "Лучи веера становятся касательными — вихрь",
                   "72 луча из центра сдвигаются в касательные к растущему внутреннему кругу и поворачиваются — "
                   "в середине открывается «глаз» вихря. Роль: фокус внимания, «пустота в центре — место для "
                   "главного».",
                   [Slide(state(0, "Лучи"), dur=800), Slide(state(1, "Сдвиг"), dur=900),
                    Slide(state(2, "Вихрь"), dur=900)],
                   tags=["lines", "rotation", "focus"], score=4)


# ----------------------------------------------------------------------------- 8. сеть хорд с сигналами

def v_network(theme) -> Variant:
    n, R = 12, 2.5
    rnd = random.Random(4)
    edges = set()
    while len(edges) < 22:
        a, b = rnd.sample(range(n), 2)
        if abs(a - b) not in (1, n - 1):
            edges.add((min(a, b), max(a, b)))
    edges = sorted(edges)
    names = ["Склад", "Курьер", "Сайт", "Касса", "CRM", "Банк", "Почта", "Чат", "Отзывы", "Реклама", "Аналитика",
             "Поддержка"]
    pos = [pol(*C, R, -90 + 30 * i) for i in range(n)]

    def state(s, sub):
        hub = [None, 4, 10][s]
        objs = head("Сеть связей", sub)
        loops = []
        for k, (a, b) in enumerate(edges):
            on = hub in (a, b)
            objs.append(V.shape(f"!!ne{k}", thin(pos[a], pos[b], 0.022 if on else 0.014),
                                fill="accent" if on else shade(theme, "ink", 0.6), z=6 if on else 4))
            if on:
                src, dst = (pos[a], pos[b]) if a == hub else (pos[b], pos[a])
                loops.append(Loop("flow", points=[src, dst], n=2, period=2.2, size=0.12, color="accent",
                                  name=f"sig_{k}", z=6.5))
        for i, (x, y) in enumerate(pos):
            on = i == hub
            d = 0.36 if on else 0.24
            objs.append(O(f"!!nn{i}", "oval", x - d / 2, y - d / 2, d, d, fill="accent" if on else "bg",
                          ln="accent" if on else "ink2", lw=1.5, z=10))
            lx, ly = pol(*C, R + 0.55, -90 + 30 * i)
            objs.append(text(f"!!nt{i}", lx - 0.9, ly - 0.2, 1.8, 0.4, names[i], sz=13, b=on,
                             col="accent" if on else "ink2", al="c", va="m"))
        return objs, loops

    sl = []
    for s, (sub, d) in enumerate([("12 сервисов, 22 связи", 800), ("CRM — узел связей", 800), ("Фокус на аналитике", 800)]):
        o, lp = state(s, sub)
        sl.append(Slide(o, dur=d, loops=lp))
    return Variant(FAM, "network", "Сеть хорд: узел и его сигналы",
                   "Сервисы на круге, связи — хорды; выбранный узел подсвечивает свои хорды, по ним бегут сигналы "
                   "строго по линиям; фокус переходит к другому узлу. Роль: интеграции, «кто с кем связан».",
                   sl, tags=["lines", "network", "flow", "loop"], score=4)


# ----------------------------------------------------------------------------- 9. Лиссажу из точек

def v_lissajous(theme) -> Variant:
    n = 160
    A, B = 2.6, 2.3
    ratios = [(1, 2, 90), (3, 2, 45), (5, 4, 60)]

    def state(s, sub):
        a, b, dl = ratios[s]
        objs = head("Ритмы", sub)
        for i in range(n):
            t = 2 * math.pi * i / n
            x = C[0] + A * math.sin(a * t + math.radians(dl))
            y = C[1] + B * math.sin(b * t)
            col = mix(theme.c("accent"), theme.c("ink2"), abs(math.sin(t)))
            objs.append(O(f"!!lj{i}", "oval", x - 0.05, y - 0.05, 0.1, 0.1, fill=col, z=6))
        objs.append(text(f"lr{s}", 0.7, 3.3, 3.6, 0.9, f"{a} : {b}", sz=44, b=True, col="accent", font="head"))
        return objs

    return Variant(FAM, "lissajous", "Фигуры Лиссажу: отношение ритмов",
                   "160 точек на кривой Лиссажу; при смене отношения частот (1:2 -> 3:2 -> 5:4) точки перетекают в "
                   "новый узор. Роль: два ритма (продажи и производство), их согласование.",
                   [Slide(state(0, "Один к двум"), dur=800), Slide(state(1, "Три к двум"), dur=900),
                    Slide(state(2, "Пять к четырём"), dur=900)],
                   tags=["lines", "dots", "math"], score=3)


# ----------------------------------------------------------------------------- 10. глобус из меридианов -> карта

def _mer(name, cx, cy, rx, ry, pivot, **kw):
    """Меридиан — контур эллипса (48 точек) в общей рамке: ширина может падать почти до нуля без искажений."""
    g = V.resample(V.ellipse(cx, cy, max(rx, 0.012), ry, seg=12), 48)
    return ax(name, g, 0.0, pivot=pivot, **kw)


def globe_objs(theme, c, R, phase, flat, n_mer=12, n_par=5, fa=1.0, k_tilt=1.0, prefix="g", hl=None, bars=None):
    """Каркас глобуса: меридианы — эллипсы шириной 2R·|sin λ|; flat=True — развёртка (прямоугольная сетка карты);
    bars — {j: (x, y, w, h, цвет)} — меридиан становится столбиком."""
    out = []
    W, H = min(2 * math.pi * R * 0.62, 7.4), 2 * R
    for j in range(n_mer):
        lam = math.radians(phase + 360 * j / n_mer)
        on = hl is not None and j == hl
        if bars is not None and j in bars:
            x, y, w, h, col = bars[j]
            g = V.resample(V.rect(x, y, w, h), 48)
            out.append(ax(f"!!{prefix}m{j}", g, 0.0, pivot=c, fill=col, ln=None, z=6))
            continue
        if not flat:
            w = 2 * R * abs(math.sin(lam))
            front = math.cos(lam) > 0
            out.append(_mer(f"!!{prefix}m{j}", c[0], c[1], w / 2, R * k_tilt, c, fill=None,
                            ln="accent" if on else ("ink2" if front else "line"), lw=2.0 if on else 1.0, la=fa, z=6))
        else:
            x = c[0] - W / 2 + W * ((phase + 360 * j / n_mer) % 360) / 360
            if bars is not None:
                out.append(_mer(f"!!{prefix}m{j}", x, c[1] + H / 2, 0.0, 0.012, c, fill=None, ln="ink2", lw=1.0, la=0.0,
                                z=6))
                continue
            out.append(_mer(f"!!{prefix}m{j}", x, c[1], 0.0, H / 2, c, fill=None, ln="accent" if on else "ink2",
                            lw=2.0 if on else 1.0, la=fa, z=6))
    for k in range(n_par):
        phi = math.radians(-60 + 120 * k / (n_par - 1))
        y = c[1] + R * math.sin(phi) * k_tilt
        hw = R * math.cos(phi) if not flat else W / 2
        if flat:
            y = c[1] + H / 2 * math.sin(phi) / math.sin(math.radians(60)) * 0.85
        out.append(O(f"!!{prefix}p{k}", "rect", c[0] - hw, y - 0.006, 2 * hw, 0.012, fill="ink2", fa=fa, z=6))
    if not flat:
        out.append(O(f"!!{prefix}o", "oval", c[0] - R, c[1] - R * k_tilt, 2 * R, 2 * R * k_tilt, fill=None, ln="ink",
                     lw=1.5, la=fa, z=7))
    else:
        out.append(O(f"!!{prefix}o", "oval", c[0] - W / 2, c[1] - H / 2, W, H, fill=None, ln="ink", lw=1.5, la=0.0, z=7))
    return out


def v_globe(theme) -> Variant:
    c, R = (8.9, 4.1), 2.25

    def state(s, sub):
        objs = head("Глобус", sub)
        objs += globe_objs(theme, c, R, [0, 14, 14][s], s == 2, hl=3)
        return objs

    return Variant(FAM, "globe", "Глобус из меридианов разворачивается в карту",
                   "Меридианы — овалы, ширина которых зависит от долготы: сдвиг фазы даёт вращение глобуса; затем "
                   "каркас разворачивается в прямоугольную сетку карты, выделенный меридиан едет на своё место. "
                   "Роль: выход на новые рынки, «весь мир -> наша карта».",
                   [Slide(state(0, "Мир"), dur=800), Slide(state(1, "Поворачиваем"), dur=800),
                    Slide(state(2, "Разворачиваем в карту"), dur=900)],
                   tags=["lines", "pseudo-3d", "globe", "unroll"], score=4)


# ----------------------------------------------------------------------------- 11. волна -> круговая волна

def v_wave(theme) -> Variant:
    n = 64
    cc = (9.0, 4.0)
    r0 = 1.3

    def hval(i, s):
        return 0.25 + 1.0 * abs(math.sin(i * 0.31) * math.cos(i * 0.11 + s))

    def state(s, sub):
        objs = head("Сигнал по кругу", sub)
        for i in range(n):
            h = hval(i, 0)
            ang = -90 + 360 * i / n
            if s == 0:
                x = 1.2 + 11.0 * i / (n - 1)
                g = V.Polygon([(x - 0.05, 4.4 - h), (x + 0.05, 4.4 - h), (x + 0.05, 4.4 + h * 0.3), (x - 0.05, 4.4 + h * 0.3)])
                rot = 0.0
            else:
                k = 1.0 if s == 1 else 1.25
                p0 = pol(*cc, r0 - 0.3 * h * k * 0.3, ang)
                p1 = pol(*cc, r0 + h * k, ang)
                g = thin(p0, p1, 0.065)
                rot = 0.0
            col = "accent" if (i % 8 == 0) else shade(theme, "ink", 0.3)
            objs.append(ax(f"!!wv{i}", g, rot, pivot=cc, R=9.6, fill=col, z=6))
        return objs

    return Variant(FAM, "wave", "Волна сворачивается в круговую",
                   "64 столбика-«звуковой волны» по прямой сворачиваются в кольцо (каждый становится лучом), "
                   "затем кольцо «вдыхает». Роль: голос клиента, отзывы, «сигнал со всех сторон».",
                   [Slide(state(0, "Сигнал"), dur=800), Slide(state(1, "По кругу"), dur=900),
                    Slide(state(2, "Громче"), dur=600)],
                   tags=["lines", "wrap", "data"], score=3)


# ----------------------------------------------------------------------------- ЖИВАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ 1: сеть клиентов

def seq_web(theme) -> Variant:
    """8 состояний: узлы на круге -> все связи (толщина = сила) -> узел-хаб с сигналами -> лупа едет к другому
    узлу -> сеть наклоняется в 3D -> уходит на фон -> самые сильные связи выстраиваются в столбики -> снова сеть."""
    c, R, n = (9.0, 4.0), 2.45, 12
    names = ["Склад", "Курьер", "Сайт", "Касса", "CRM", "Банк", "Почта", "Чат", "Отзывы", "Реклама", "Аналитика",
             "Поддержка"]
    rnd = random.Random(9)
    pairs = [(a, b) for a in range(n) for b in range(a + 1, n)]
    wgt = {p: rnd.random() ** 2 for p in pairs}
    for p in [(2, 4), (4, 10), (3, 5), (0, 1), (4, 11), (2, 9), (8, 10)]:
        wgt[p] = 0.8 + 0.2 * rnd.random()
    top = sorted(pairs, key=lambda p: -wgt[p])[:8]
    K = 0.38
    ang = [-90 + 30 * i for i in range(n)]

    def npos(i, st):
        x, y = pol(*c, R, ang[i])
        if st == 4:
            y = c[1] + (y - c[1]) * K
        if st == 5:
            x, y = c[0] + 1.6 + (x - c[0]) * 0.7, c[1] - 1.1 + (y - c[1]) * K * 0.7
        return x, y

    heads = [("Двенадцать сервисов", "Пока без связей"), ("Все связи", "Толщина — объём обмена"),
             ("Узел: CRM", "Сигналы идут по линиям"), ("Узел: аналитика", "Лупа переехала по кругу"),
             ("Сеть в объёме", "Наклоняем"), ("Главное", "Сеть уходит на фон"), ("Сильнейшие связи", "Линии стали столбиками"),
             ("Связано всё", "Снова сеть")]
    hubs = {2: 4, 3: 10}
    slides = []
    for st in range(8):
        objs = head(*heads[st])
        loops = []
        hub = hubs.get(st)
        for k, (a, b) in enumerate(pairs):
            w = wgt[(a, b)]
            pa, pb = npos(a, st), npos(b, st)
            fa = 0.0 if st == 0 else (0.25 + 0.75 * w)
            col = shade(theme, "ink", 0.55 - 0.3 * w)
            if hub is not None and hub in (a, b) and w > 0.3:
                col, fa = "accent", 1.0
            if st == 0:  # линия вырастет из узла a: стартовый отрезок крошечный, но невырожденный
                pb = (pa[0] + (pb[0] - pa[0]) * 0.01, pa[1] + (pb[1] - pa[1]) * 0.01)
            if st == 5:
                fa *= 0.35
            if st == 6:
                if (a, b) in top:
                    j = top.index((a, b))
                    L = 6.5 * wgt[(a, b)]
                    pa, pb = (4.4, 2.55 + j * 0.5), (4.4 + L, 2.55 + j * 0.5)
                    col, fa = ("accent" if j == 0 else shade(theme, "ink", 0.25)), 1.0
                else:
                    pa, pb = (4.4, 6.6), (4.45, 6.6)
                    fa = 0.0
            wd = (0.012 + 0.03 * w) if st != 6 else 0.26
            objs.append(ax(f"!!wl{k}", thin(pa, pb, wd), 0.0, pivot=c, fill=col, fa=fa, z=6 if col == "accent" else 4))
            if hub is not None and col == "accent":
                src, dst = (pa, pb) if a == hub else (pb, pa)
                loops.append(Loop("flow", points=[src, dst], n=2, period=2.4, size=0.12, color="accent",
                                  name=f"ws_{k}", z=6.5))
        for i in range(n):
            x, y = npos(i, st)
            on = i == hub
            d = 0.36 if on else 0.24
            if st == 6:
                x, y, d = 4.4, 6.6, 0.02
            objs.append(O(f"!!wn{i}", "oval", x - d / 2, y - d / 2, d, d, fill="accent" if on else "bg",
                          ln="accent" if on else "ink2", lw=1.5, z=10, fa=1.0, la=0.0 if st == 6 else 1.0))
            if st in (0, 1, 2, 3, 7):
                lx, ly = pol(*c, R + 0.55, ang[i])
                objs.append(text(f"!!wt{i}", lx - 0.9, ly - 0.2, 1.8, 0.4, names[i], sz=13, b=on,
                                 col="accent" if on else "ink2", al="c", va="m"))
        if st in (2, 3):
            lens_a = ang[hub]
            from lab._b_util import arc_band
            g = arc_band(c[0], c[1], R - 0.4, R + 0.95, lens_a - 13, lens_a + 13, 16)
            objs.append(ax("!!wlens", g, lens_a, pivot=c, fill="accent", fa=0.14, ln="accent", lw=2.0, z=8))
        if st == 5:
            objs.append(text("wfin", 0.7, 4.4, 6.4, 1.4, ["CRM связан", "с 9 из 11"], sz=40, b=True, col="ink",
                             font="head"))
        if st == 6:
            for j, (a, b) in enumerate(top):
                objs.append(text(f"wb{j}", 0.7, 2.43 + j * 0.5, 3.55, 0.36, f"{names[a]} — {names[b]}", sz=13,
                                 col="accent" if j == 0 else "ink2", al="r", va="m"))
        fx = []
        if st == 0:
            fx = [Fx("entrance_zoom", f"!!wn{i}", start="at", delay=0.05 + 0.04 * i, dur=0.3) for i in range(n)]
        slides.append(Slide(objs, dur=[800, 900, 700, 850, 900, 850, 900, 900][st], loops=loops, fx=fx))
    return Variant(FAM, "seq_web", "Живая сеть сервисов (8 состояний)",
                   "Сервисы на круге соединяются всеми связями (толщина — объём), хаб подсвечивает свои линии и "
                   "шлёт по ним сигналы, лупа-дуга переезжает по кругу к другому хабу, сеть наклоняется в объём и "
                   "уходит на фон, сильнейшие связи выпрямляются в столбики рейтинга и снова становятся сетью. "
                   "Роль: интеграции и зависимости через раздел.",
                   slides, tags=["seq", "lines", "network", "flow", "magnifier", "3d", "chart"], score=4)


# ----------------------------------------------------------------------------- ЖИВАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ 2: глобус -> рынки

def seq_world(theme) -> Variant:
    """7 состояний: глобус -> поворот к нашему региону -> спутник облетает -> развёртка в карту -> меридианы
    становятся столбиками по регионам -> обратно в глобус -> глобус уходит на фон."""
    c, R = (9.0, 4.1), 2.25
    regions = ["Европа", "Азия", "Африка", "Америка", "Океания", "Ближний Восток"]
    vals = [0.55, 0.9, 0.25, 0.7, 0.15, 0.4]
    heads = [("Мир", "Где наши клиенты"), ("Наш регион", "Поворачиваем глобус"), ("Облёт", "Спутник ищет рынки"),
             ("Карта", "Глобус разворачивается"), ("Рынки по выручке", "Меридианы стали столбиками"),
             ("Снова карта", "Столбики ложатся в сетку"), ("Снова мир", "Сворачиваем"), ("Азия — главный рынок", "Глобус уходит на фон")]
    slides = []
    for st in range(8):
        objs = head(*heads[st])
        phase = [0, 30, 30, 30, 30, 30, 60, 60][st]
        flat = st in (3, 4, 5)
        cc = (c[0] + 1.7, c[1] - 1.0) if st == 7 else c
        RR = R * (0.62 if st == 7 else 1.0)
        W, H = min(2 * math.pi * R * 0.62, 7.4), 2 * R
        bars = None
        if st == 4:
            bars = {}
            for j in range(6):
                h = 0.4 + 3.0 * vals[j]
                bars[j] = (c[0] - W / 2 + 0.2 + j * (W / 6), c[1] + H / 2 - h, 0.55, h, "accent" if j == 1 else "ink2")
        g = globe_objs(theme, cc, RR, phase, flat, hl=1 if st >= 1 else None, fa=0.35 if st == 7 else 1.0, prefix="w",
                       bars=bars)
        if st == 4:
            g = [o.copy(fa=0.0) if (o.name.startswith("!!wp") and not o.name.endswith("4")) else o for o in g]
            for j in range(6):
                x = c[0] - W / 2 + 0.2 + j * (W / 6)
                objs.append(text(f"wr{j}", x - 0.35, c[1] + H / 2 + 0.12, 1.25, 0.6, regions[j], sz=12, col="ink2",
                                 al="c"))
        objs += g
        if st == 2:
            from lab._b_util import comet
            objs += comet("wsat", c, R + 0.45, 200, d=0.22, n=7, gap=0.13, fill=theme.c("accent"), bg=theme.c("bg"), z=20)
        if st in (1, 3, 5):
            objs += [o.copy(fa=0.0, la=0.0) for o in []]
        if st == 7:
            objs.append(text("wfin", 0.7, 4.4, 6.0, 1.4, ["38% выручки —", "из Азии"], sz=40, b=True, col="ink",
                             font="head"))
        if st == 1:
            from lab._b_util import comet
            objs += comet("wsat", c, R + 0.45, 40, d=0.22, n=7, gap=0.13, fill=theme.c("accent"), bg=theme.c("bg"), z=20)
        slides.append(Slide(objs, dur=[800, 850, 900, 900, 900, 800, 900, 850][st]))
    return Variant(FAM, "seq_world", "Глобус -> карта -> рынки (8 состояний)",
                   "Каркасный глобус поворачивается к региону, вокруг него по дуге облетает спутник-комета, глобус "
                   "разворачивается в прямоугольную карту, меридианы карты вырастают в столбики выручки по "
                   "регионам, затем всё сворачивается обратно в глобус и уходит на фон под вывод. Роль: география "
                   "бизнеса в одном сквозном объекте.",
                   slides, tags=["seq", "lines", "globe", "unroll", "chart", "orbit", "background"], score=4)


def variants(theme) -> list[Variant]:
    return [v_times(theme), v_moire_rings(theme), v_moire_fan(theme), v_rose(theme), v_hyper(theme),
            v_envelope(theme), v_vortex(theme), v_network(theme), v_lissajous(theme), v_globe(theme), v_wave(theme), seq_web(theme), seq_world(theme)]
