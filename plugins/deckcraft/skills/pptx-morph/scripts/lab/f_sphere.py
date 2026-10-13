"""Семейство «Сферы»: объём из 2D — слои света, глобус с вращающимися меридианами, орбиты, дольки, лупа.

Сфера = диск + 4 линзы света (пересечения диска со смещёнными к свету кругами) + тень-серп + блик. Все части —
обычные плоские формы со своей рамкой, поэтому сфера едет и масштабируется как одно тело (точки внутри рамок
не меняются), а предпросмотр совпадает с PowerPoint (без radial-градиентов).
Глобус: меридианы и параллели — тонкие ленты с постоянным числом точек; точка, ушедшая за край диска, «прилипает»
к контуру (кромке) — так полоса меридиана плавно уходит за горизонт при повороте, а не исчезает.
"""

from __future__ import annotations

import math
import random

from morphkit import O, Slide
from morphkit import vector as V
from morphkit.theme import SLIDE_W, mix

from lab import Variant
from lab._c_util import band, head, ink_on, label, poly

FAM = "sphere"
LIGHT = (-0.55, -0.62)  # направление к свету на экране (влево-вверх)


def _pal(theme):
    ink2, bg = theme.c("ink2"), theme.c("bg")
    return {"grey": mix(ink2, bg, 0.45), "grey2": mix(ink2, bg, 0.62), "grey3": mix(ink2, bg, 0.30),
            "acc": theme.c("accent"), "acc3": theme.c("accent3"), "acc2": theme.c("accent2"), "bg": bg,
            "ink": theme.c("ink"), "line": theme.c("line"), "night": mix(bg, "000000", 0.2)}


def sphere(prefix, cx, cy, R, base, fa=1.0, z=10, gloss=True, rim=True, light=LIGHT):
    """Шар из слоёв: тёмное основание, 4 светлеющие линзы к свету, тень-серп, блик. Имена частей постоянны."""
    lx, ly = light
    L = math.hypot(lx, ly)
    lx, ly = lx / L, ly / L
    out = [O(f"{prefix}_b", "oval", cx - R, cy - R, 2 * R, 2 * R, fill=mix(base, "000000", 0.42), fa=fa, z=z,
             meta={"bleed": True})]
    disc = V.circle(cx, cy, R, 16)
    for j in range(1, 5):
        off = R * 0.13 * j
        rr = R * (1.0 - 0.17 * j)
        g = V.intersect(disc, V.circle(cx + lx * off, cy + ly * off, rr, 16))
        col = mix(base, "FFFFFF", 0.06 * j) if j > 1 else base
        out.append(V.shape(f"{prefix}_l{j}", V.resample(g, 64), fill=col, fa=fa, z=z + j, meta={"bleed": True}))
    if gloss:
        hx, hy = cx + lx * R * 0.48, cy + ly * R * 0.48
        out.append(O(f"{prefix}_g", "oval", hx - R * 0.2, hy - R * 0.14, R * 0.4, R * 0.28, fill="FFFFFF",
                     fa=0.35 * fa, z=z + 6, rot=-35, meta={"bleed": True, "decor": True}))
    if rim:
        out.append(O(f"{prefix}_r", "oval", cx - R, cy - R, 2 * R, 2 * R, fill=None, ln=mix(base, "FFFFFF", 0.2),
                     lw=0.75, la=0.5 * fa, z=z + 7, meta={"bleed": True, "decor": True}))
    return out


def sph_xyz(lat, lon, R, rot, tilt):
    """Точка на сфере (широта, долгота) -> (x, y, глубина) при повороте rot вокруг оси и наклоне оси tilt."""
    la, lo = math.radians(lat), math.radians(lon + rot)
    x = R * math.cos(la) * math.sin(lo)
    y0 = R * math.sin(la)
    z0 = R * math.cos(la) * math.cos(lo)
    t = math.radians(tilt)
    y = y0 * math.cos(t) - z0 * math.sin(t)
    z = y0 * math.sin(t) + z0 * math.cos(t)
    return x, y, z


def on_disc(cx, cy, R, x, y, d):
    """Экранная точка; задняя (d<0) прижимается к контуру диска."""
    if d < 0:
        L = math.hypot(x, y) or 1e-6
        x, y = x / L * R, y / L * R
    return cx + x, cy - y


def globe(prefix, theme, pal, cx, cy, R, rot, tilt=18, nm=8, lat_lines=(-60, -30, 0, 30, 60), w=0.03, col=None,
          fa=1.0, z=30, cities=None, hot=None):
    col = col or mix(pal["ink"], pal["bg"], 0.35)
    out = []
    for i in range(nm):
        lon = i * 180.0 / nm * 2 % 360
        pts = []
        for s in range(25):
            lat = -90 + s * 7.5
            x, y, d = sph_xyz(lat, lon, R, rot, tilt)
            pts.append(on_disc(cx, cy, R, x, y, d))
        out.append(band(f"{prefix}_m{i}", pts, w, fill=col, fa=fa, z=z, meta={"bleed": True, "decor": True}))
    for j, lat in enumerate(lat_lines):
        pts = []
        for s in range(37):
            x, y, d = sph_xyz(lat, -180 + s * 10, R, 0, tilt)
            pts.append(on_disc(cx, cy, R, x, y, d))
        out.append(band(f"{prefix}_p{j}", pts, w, fill=col, fa=fa, z=z, meta={"bleed": True, "decor": True}))
    for k, (nm_, lat, lon) in enumerate(cities or []):
        x, y, d = sph_xyz(lat, lon, R, rot, tilt)
        vis = d > R * 0.05
        px, py = on_disc(cx, cy, R, x, y, d)
        s = (0.2 if hot == k else 0.12) * (R / 2.2) * (0.4 + 0.6 * max(d, 0) / R)
        out.append(O(f"{prefix}_c{k}", "oval", px - s, py - s, 2 * s, 2 * s, fill="accent" if hot == k else pal["acc3"],
                     fa=fa if vis else 0.0, z=z + 2, meta={"bleed": True}))
    return out


# ----------------------------------------------------------------------------- 1. глобус вращается

CITIES = [("Лиссабон", 39, -9), ("Москва", 56, 38), ("Дубай", 25, 55), ("Сингапур", 1, 104), ("Токио", 36, 140)]


def v_globe(theme):
    pal = _pal(theme)
    cx, cy, R = 8.9, 3.95, 2.55
    rots = [-10, -55, -120]
    hot = [0, 1, 4]

    def make(k):
        objs = sphere("!!gl", cx, cy, R, pal["grey3"], gloss=False)
        objs += globe("!!gl", theme, pal, cx, cy, R, rots[k], cities=CITIES, hot=hot[k])
        nm, lat, lon = CITIES[hot[k]]
        x, y, d = sph_xyz(lat, lon, R, rots[k], 18)
        px, py = on_disc(cx, cy, R, x, y, d)
        objs.append(O(f"cl{k}", "line", px + 0.2, py, 12.4 - px - 0.2 - 1.9, 0, ln="line", lw=1, z=60))
        objs.append(label(f"ct{k}", 12.4 - 1.85, py - 0.22, 1.85, nm, sz=18, b=True, col="accent", z=61))
        return objs

    heads = [head("Наши офисы", "начинали в Европе"), head("Шаг на восток", "главный офис"), head("Азия", "офис в Токио")]
    return Variant(FAM, "globe_spin", "Глобус поворачивается к городу",
                   "Шар со слоями света, меридианы — ленты, которые при повороте сжимаются и уходят за кромку; "
                   "точки городов проезжают по шару, нужный город выходит к зрителю с выноской. Роль: география, "
                   "экспансия, «где мы».", [Slide(heads[k] + make(k), dur=900) for k in range(3)],
                   tags=["sphere", "globe", "rotate", "geo"], score=5)


# ----------------------------------------------------------------------------- 2. фазы планеты (день/ночь)

def phase_shape(cx, cy, R, p, n=96):
    """Освещённая часть диска: дуга кромки справа + терминатор (полуэллипс с полуосью R·cos(πp)). p 0..1."""
    pts = []
    for i in range(n // 2 + 1):
        a = -90 + 180 * i / (n // 2)
        pts.append((cx + R * math.cos(math.radians(a)), cy + R * math.sin(math.radians(a))))
    k = math.cos(math.pi * p)
    for i in range(1, n // 2):
        a = 90 + 180 * i / (n // 2)
        pts.append((cx - k * R * math.cos(math.radians(a)), cy + R * math.sin(math.radians(a))))
    return pts


def v_phase(theme):
    pal = _pal(theme)
    cx, cy, R = 9.0, 3.95, 2.4
    ps = [0.12, 0.5, 0.92]
    labs = ["Исследование", "Половина пути", "Почти готово"]

    def make(k):
        objs = [O("!!pl_b", "oval", cx - R, cy - R, 2 * R, 2 * R, fill=pal["night"], z=10, ln=pal["grey3"], lw=1)]
        pts = phase_shape(cx, cy, R, ps[k])
        g = V.gradient([(0, mix(pal["acc"], "FFFFFF", 0.25)), (1, pal["acc"])], angle=135)
        objs.append(poly("!!pl_lit", pts, fill=pal["acc"], grad=g, z=11, frame=(cx - R, cy - R, 2 * R, 2 * R)))
        objs.append(label(f"pt{k}", cx - 1.6, cy + R + 0.25, 3.2, labs[k], sz=20, b=True, al="c", col="ink", z=40))
        return objs

    heads = [head("Фаза 1", "освещена малая часть"), head("Фаза 2", "ровно половина"), head("Фаза 3", "почти полный диск")]
    return Variant(FAM, "planet_phase", "Фазы планеты: терминатор едет",
                   "Ночной диск и освещённая часть (дуга кромки + полуэллипс терминатора с постоянным числом точек): "
                   "терминатор плавно проходит по диску. Роль: метафора стадии/зрелости без шкалы-индикатора, «свет "
                   "приходит». Не путать с кольцом-прогрессом.", [Slide(heads[k] + make(k), dur=900) for k in range(3)],
                   tags=["sphere", "phase", "shape-morph"], score=4)


# ----------------------------------------------------------------------------- 3. планета и наклонная орбита со спутниками

def orbit_ring(prefix, cx, cy, a, b, w, col, half, z, fa=1.0, n=96):
    """Половина эллипса орбиты лентой: half='back' (верхняя дуга), 'front' (нижняя)."""
    a0, a1 = (180, 360) if half == "back" else (0, 180)
    pts = [(cx + a * math.cos(math.radians(a0 + (a1 - a0) * i / (n - 1))),
            cy + b * math.sin(math.radians(a0 + (a1 - a0) * i / (n - 1)))) for i in range(n)]
    return [band(prefix, pts, w, fill=col, fa=fa, z=z, meta={"bleed": True})]


def moons(prefix, pal, cx, cy, a, b, n, phase, names=None, hot=None, sz=0.36, label_on=True, theme=None):
    out = []
    for i in range(n):
        ang = math.radians(90 + phase + 360 * i / n)  # 90° — ближе всего к зрителю (низ эллипса)
        x, y = cx + a * math.cos(ang), cy + b * math.sin(ang)
        depth = math.sin(ang)  # +1 спереди, −1 сзади
        s = sz * (0.65 + 0.35 * (depth + 1) / 2)
        behind = depth < -0.35 and abs(math.cos(ang)) < 0.55  # за планетой
        col = pal["acc"] if hot == i else mix(pal["grey"], pal["bg"], 0.35 * (1 - depth) / 2)
        out += sphere(f"{prefix}{i}", x, y, s, col, fa=0.0 if behind else 1.0, z=60 + i * 8, gloss=False, rim=False)
        if names and label_on and depth > 0.55:
            out.append(label(f"{prefix}t{i}_{int(phase)}", x - 1.1, y + s + 0.05, 2.2, names[i], sz=16, b=hot == i,
                             al="c", col="accent" if hot == i else "ink2", z=120))
    return out


def v_orbit(theme):
    pal = _pal(theme)
    cx, cy, R = 8.9, 3.9, 1.5
    a, b = 3.6, 1.15
    names = ["Сайт", "Приложение", "Магазины", "Партнёры", "Поддержка"]

    def make(k):
        objs = orbit_ring("!!or_b", cx, cy, a, b, 0.035, pal["grey2"], "back", 5)
        objs += sphere("!!pln", cx, cy, R, pal["grey"])
        objs.append(label("pc", cx - 1.0, cy - 0.2, 2.0, "Клиент", sz=18, b=True, al="c", col=ink_on(theme, pal["grey"]),
                          z=40))
        objs += orbit_ring("!!or_f", cx, cy, a, b, 0.035, pal["grey2"], "front", 50)
        objs += moons("!!mn", pal, cx, cy, a, b, 5, -72 * k, names=names, hot=k)
        return objs

    heads = [head("Каналы вокруг клиента", "сайт ближе всех"), head("Поворот орбиты", "второй канал"),
             head("Ещё шаг", "третий канал")]
    return Variant(FAM, "orbit_moons", "Спутники на наклонной орбите",
                   "Планета-клиент и пять спутников-каналов на наклонной орбите (задняя половина орбиты под планетой, "
                   "передняя — над ней); клик поворачивает орбиту на один спутник, ближний растёт и подписан, "
                   "заходящий за планету гаснет. Роль: экосистема, каналы, «вокруг клиента».",
                   [Slide(heads[k] + make(k), dur=900) for k in range(3)], tags=["sphere", "orbit", "circle-motion"],
                   score=3)


# ----------------------------------------------------------------------------- 3б. круговая орбита на оси (точное движение по дуге)

def v_orbit_pivot(theme):
    """Вид сверху: спутники в рамках на оси планеты — Morph крутит rot, и они идут ровно по окружности."""
    pal = _pal(theme)
    cx, cy, R = 8.9, 3.95, 1.25
    ro = 2.65
    names = ["Найм", "Адаптация", "Обучение", "Рост", "Удержание"]

    def make(k):
        objs = [O("!!orc", "oval", cx - ro, cy - ro, 2 * ro, 2 * ro, fill=None, ln=pal["grey2"], lw=1.2, z=5)]
        objs += sphere("!!pv", cx, cy, R, pal["grey"])
        objs.append(label("pvc", cx - 1.0, cy - 0.2, 2.0, "Сотрудник", sz=16, b=True, al="c", col="ink", z=40))
        for i in range(5):
            ang = -90 + 72 * i - 72 * k  # активный — сверху
            hot = i == k
            r = 0.34 if hot else 0.24
            for j, (rr, cc, ff) in enumerate([(r, mix(pal["acc"] if hot else pal["grey"], "000000", 0.35), 1.0),
                                              (r * 0.78, pal["acc"] if hot else pal["grey"], 1.0),
                                              (r * 0.4, mix(pal["acc"] if hot else pal["grey"], "FFFFFF", 0.3), 1.0)]):
                g = V.circle(cx, cy - ro, rr, 8)
                objs.append(V.shape(f"!!pm{i}_{j}", V.resample(g, 32), pivot=(cx, cy), rot=ang + 90, fill=cc, fa=ff,
                                    z=50 + i * 4 + j))
            if hot:
                objs.append(label(f"pmt{k}", cx + 0.5, cy - ro - 0.22, 2.4, names[i], sz=20, b=True,
                                  col="accent", z=90))
        return objs

    heads = [head("Путь сотрудника", "пять этапов по кругу"), head("Шаг 2", "круг повернулся"), head("Шаг 3", "ещё на 72°")]
    return Variant(FAM, "orbit_pivot", "Спутники по окружности (рамка на оси)",
                   "Объёмная планета и пять спутников в рамках на её оси: Morph поворачивает rot, спутники идут точно по "
                   "окружности (без «срезания» хорды), активный выходит наверх с подписью. Роль: цикл, этапы по кругу.",
                   [Slide(heads[k] + make(k), dur=900) for k in range(3)], tags=["sphere", "orbit", "pivot", "circle-motion"],
                   score=4)


# ----------------------------------------------------------------------------- 4. пузырь делится на сегменты

def v_bubbles(theme):
    pal = _pal(theme)
    segs = [("Новые", 0.34), ("Постоянные", 0.28), ("Ушедшие", 0.16), ("Спящие", 0.22)]
    big = (8.9, 3.95, 2.3)

    def make(k):
        objs = []
        if k == 0:
            pos = [big] * 4
        else:
            pos = [(6.8, 3.0), (10.4, 2.8), (7.6, 5.6), (10.8, 5.4)]
            pos = [(x, y, 2.3 * math.sqrt(v) * (1.0 if k == 1 else 1.0)) for (x, y), (_, v) in zip(pos, segs)]
        for i, ((nm, v), (x, y, r)) in enumerate(zip(segs, pos)):
            base = pal["acc"] if (k == 2 and i == 2) else pal["grey"]
            objs += sphere(f"!!bb{i}", x, y, r, base, z=10 + i * 10)
            if k >= 1:
                objs.append(label(f"bl{i}", x - 1.1, y - 0.36, 2.2, [nm, f"{round(v * 100)}%"], sz=16, b=True, al="c",
                                  col=ink_on(theme, base), z=80))
        if k == 0:
            objs.append(label("ball", big[0] - 1.3, big[1] - 0.25, 2.6, "48 000 клиентов", sz=20, b=True, al="c",
                              col=ink_on(theme, pal["grey"]), z=80))
        return objs

    heads = [head("Вся база", "одним пузырём"), head("Четыре сегмента", "площадь — доля"),
             head("Ушедшие", "вернуть 16%")]
    return Variant(FAM, "bubble_split", "Пузырь делится на сегменты",
                   "Один объёмный пузырь базы делится на четыре пузыря-сегмента (площадь = доля), сегменты расходятся "
                   "в пространстве, нужный загорается. Роль: сегментация аудитории, «части отделяются».",
                   [Slide(heads[k] + make(k), dur=900) for k in range(3)], tags=["sphere", "split", "data"], score=4)


# ----------------------------------------------------------------------------- 5. дольки апельсина — объёмные доли

def lune_poly(cx, cy, R, lon0, lon1, rot, tilt, n=48):
    """Видимая долька между меридианами lon0..lon1 (только передняя полусфера, задние точки прижаты к кромке)."""
    left, right = [], []
    for s in range(n):
        lat = -90 + 180 * s / (n - 1)
        x, y, d = sph_xyz(lat, lon0, R, rot, tilt)
        left.append(on_disc(cx, cy, R, x, y, d))
        x, y, d = sph_xyz(lat, lon1, R, rot, tilt)
        right.append(on_disc(cx, cy, R, x, y, d))
    return left + right[::-1]


def v_lunes(theme):
    pal = _pal(theme)
    cx, cy, R = 8.9, 3.95, 2.45
    shares = [("Зарплаты", 0.38), ("Аренда", 0.18), ("Маркетинг", 0.16), ("ИТ", 0.14), ("Прочее", 0.14)]

    def make(k):
        objs = []
        lon = -90.0
        for i, (nm, v) in enumerate(shares):
            l0, l1 = lon, lon + 180 * v
            lon = l1
            mid = math.radians((l0 + l1) / 2)
            spread = [0, 0.55, 0.3][k]
            dx, dy = math.sin(mid) * spread, 0.0
            if k == 2 and i != 0:
                dx = math.sin(mid) * 0.25
            pts = [(x + dx, y + dy) for x, y in lune_poly(cx, cy, R, l0, l1, 0, 14)]
            lit = 0.5 + 0.5 * math.cos(mid + 0.6)
            base = pal["acc"] if (k == 2 and i == 0) else pal["grey"]
            col = mix(mix(base, "000000", 0.35), mix(base, "FFFFFF", 0.2), lit)
            objs.append(poly(f"!!ln{i}", pts, fill=col, ln=pal["bg"], lw=1.0, z=10 + i))
            if k >= 1:
                x, y, d = sph_xyz(-8 + 16 * (i % 2), (l0 + l1) / 2, R, 0, 14)
                px, py = on_disc(cx, cy, R, x, y, d)
                ty = 6.55 if i % 2 == 0 else 1.05
                objs.append(O(f"lnl{k}_{i}", "line", px + dx, py, 0.001, ty - py + (0.0 if i % 2 == 0 else 0.42), ln="line",
                              lw=0.75, z=50))
                objs.append(label(f"lnt{k}_{i}", px + dx - 0.9, ty if i % 2 == 0 else ty, 1.8, f"{nm} {round(v * 100)}%",
                                  sz=13, al="c", b=(k == 2 and i == 0), col="accent" if (k == 2 and i == 0) else "ink2",
                                  z=51))
        return objs

    heads = [head("Расходы", "один шар"), head("Пять долей", "дольки расходятся"), head("Главная доля", "больше трети")]
    return Variant(FAM, "orange_lunes", "Дольки шара — доли бюджета",
                   "Передняя полусфера разрезана меридианами на дольки по долям; дольки расходятся в стороны "
                   "(объёмный «пирог» без наклона-искажения), главная загорается. Роль: структура целого, бюджет, доли.",
                   [Slide(heads[k] + make(k), dur=900) for k in range(3)], tags=["sphere", "share", "explode", "data"],
                   score=4)


# ----------------------------------------------------------------------------- 6. атом: ядро и три орбиты

def v_atom(theme):
    pal = _pal(theme)
    cx, cy = 8.9, 3.95
    names = ["Данные", "Модели", "Люди"]

    def ell_band(name, a, b, ang, col, z):
        pts = []
        for i in range(73):
            t = math.radians(i * 5)
            x, y = a * math.cos(t), b * math.sin(t)
            r = math.radians(ang)
            pts.append((cx + x * math.cos(r) - y * math.sin(r), cy + x * math.sin(r) + y * math.cos(r)))
        return band(name, pts, 0.035, fill=col, z=z, meta={"bleed": True})

    def make(k):
        objs = []
        angs = [0, 60, 120]
        for j, an in enumerate(angs):
            objs.append(ell_band(f"!!at{j}", 3.1, 1.0, an, pal["grey2"], 5))
        objs += sphere("!!core", cx, cy, 0.9, pal["acc"])
        for j, an in enumerate(angs):
            t = math.radians(90 + 70 * k + j * 40)
            x, y = 3.1 * math.cos(t), 1.0 * math.sin(t)
            r = math.radians(an)
            ex, ey = cx + x * math.cos(r) - y * math.sin(r), cy + x * math.sin(r) + y * math.cos(r)
            objs += sphere(f"!!el{j}", ex, ey, 0.26, pal["acc3"] if j != k else pal["acc"], z=60 + j * 8, gloss=False,
                           rim=False)
            if j == k:
                objs.append(label(f"et{k}", ex + 0.35, ey - 0.2, 1.8, names[j], sz=17, b=True, col="accent", z=90))
        return objs

    heads = [head("Ядро продукта", "три контура вокруг"), head("Контур моделей", "второй виток"),
             head("Контур людей", "третий виток")]
    return Variant(FAM, "atom", "Атом: ядро и три орбиты",
                   "Объёмное ядро и три наклонные орбиты-ленты; «электроны» сдвигаются по своим эллипсам на каждом "
                   "клике, активный контур подписан. Роль: продукт и его контуры, экосистема, движение по кругу.",
                   [Slide(heads[k] + make(k), dur=850) for k in range(3)], tags=["sphere", "orbit", "circle-motion"],
                   score=3)


# ----------------------------------------------------------------------------- 7. стеклянная линза над полем точек

def v_lens(theme):
    pal = _pal(theme)
    rnd = random.Random(5)
    pts = []
    for i in range(14):
        for j in range(8):
            pts.append((5.6 + i * 0.52 + rnd.uniform(-0.05, 0.05), 1.9 + j * 0.62 + rnd.uniform(-0.05, 0.05)))
    special = {i for i, (x, y) in enumerate(pts) if (x - 10.4) ** 2 + (y - 3.0) ** 2 < 0.8}
    lens_c = [(7.0, 4.6), (9.0, 3.6), (10.4, 3.0)]
    LR = 1.25

    def make(k):
        objs = []
        lx, ly = lens_c[k]
        for i, (x, y) in enumerate(pts):
            dx, dy = x - lx, y - ly
            d = math.hypot(dx, dy)
            s = 0.11
            if d < LR:  # «рыбий глаз»: точка отодвигается от центра и растёт
                f = 1.0 + 0.85 * (1 - (d / LR) ** 2)
                x, y = lx + dx * min(f, LR / max(d, 1e-3) * 0.98), ly + dy * min(f, LR / max(d, 1e-3) * 0.98)
                s = 0.11 * (1 + 1.2 * (1 - d / LR))
            col = "accent" if (i in special and k == 2) else pal["grey"]
            objs.append(O(f"!!ld{i}", "oval", x - s, y - s, 2 * s, 2 * s, fill=col, z=10))
        objs.append(O("!!lens", "oval", lx - LR, ly - LR, 2 * LR, 2 * LR, fill=pal["acc2"], fa=0.10, ln=pal["ink"], lw=1.5,
                      la=0.6, z=20, meta={"decor": True}))
        objs.append(O("!!lensg", "oval", lx - LR * 0.62, ly - LR * 0.78, LR * 0.7, LR * 0.32, fill="FFFFFF", fa=0.22,
                      rot=-30, z=21, meta={"decor": True}))
        objs.append(O("!!lensh", "line", lx + LR * 0.7, ly + LR * 0.7, 0.8, 0.8, ln=pal["ink"], lw=5, la=0.7, z=21))
        return objs

    heads = [head("112 магазинов", "ищем аномалию"), head("Ближе к центру", "всё ровно"),
             head("Нашли", "кластер из 4 точек")]
    return Variant(FAM, "glass_lens", "Стеклянная линза над полем точек",
                   "Прозрачная линза ездит по полю точек; точки под ней раздвигаются и растут («рыбий глаз»), на "
                   "последнем шаге найденный кластер окрашен. Роль: поиск в данных, «присмотримся», аудит.",
                   [Slide(heads[k] + make(k), dur=850) for k in range(3)], tags=["sphere", "lens", "dots", "data"], score=4)


# ----------------------------------------------------------------------------- 8. срезы шара раздвигаются

def slice_poly(cx, cy, R, z1, z2, tilt, n=64):
    """Ломоть шара между высотами z1<z2 (доли R): видимый контур = левая кромка вниз, нижний передний полуэллипс,
    правая кромка вверх, верхний эллипс (передняя и задняя дуги — крышка рисуется отдельно)."""
    t = math.radians(tilt)
    pts = []
    def ring(zz, a0, a1, m):
        r = R * math.sqrt(max(0.0, 1 - zz * zz))
        return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / (m - 1))),
                 cy - R * zz * math.cos(t) + r * math.sin(t) * math.sin(math.radians(a0 + (a1 - a0) * i / (m - 1))))
                for i in range(m)]
    top_back = ring(z2, 180, 360, n)       # верхняя крышка: дальняя дуга слева направо
    right = [(cx + R * math.sqrt(max(0, 1 - zz * zz)), cy - R * zz * math.cos(t))
             for zz in [z2 - (z2 - z1) * i / 5 for i in range(6)]]
    bot_front = ring(z1, 0, 180, n)        # нижняя передняя дуга справа налево
    left = [(cx - R * math.sqrt(max(0, 1 - zz * zz)), cy - R * zz * math.cos(t))
            for zz in [z1 + (z2 - z1) * i / 5 for i in range(6)]]
    pts = top_back + right + bot_front + left
    cap = ring(z2, 0, 360, 2 * n)
    return pts, cap


def v_slices(theme):
    pal = _pal(theme)
    cx, cy, R = 8.9, 3.9, 2.2
    cuts = [-1.0, -0.55, -0.05, 0.45, 0.85]
    names = ["Ядро", "Сервисы", "Интеграции", "Интерфейс"]

    def make(k):
        objs = []
        for i in range(4):
            z1, z2 = cuts[i], cuts[i + 1]
            gap = [0.0, 0.35, 0.35][k] * i
            shift = -1.0 if (k == 2 and i == 0) else 0.0
            body, cap = slice_poly(cx + shift * 0, cy - gap + 0.5, R, z1, z2, 24)
            hot = k == 2 and i == 1
            base = pal["acc"] if hot else pal["grey"]
            g = V.gradient([(0, mix(base, "FFFFFF", 0.18)), (1, mix(base, "000000", 0.45))], angle=20)
            objs.append(poly(f"!!sb{i}", body, fill=base, grad=g, z=10 + i * 3, ln=pal["bg"], lw=0.5))
            objs.append(poly(f"!!sc{i}", cap, fill=mix(base, "FFFFFF", 0.22) if k else base, z=11 + i * 3, ln=pal["bg"], lw=0.5,
                             fa=1.0 if (k > 0 or i == 3) else 0.0))
            if k >= 1:
                yy = cy - gap + 0.5 - R * (z1 + z2) / 2 * math.cos(math.radians(24))
                objs.append(label(f"!!st{i}", cx + R + 0.35, yy - 0.2, 2.2, names[i], sz=15, b=hot,
                                  col="accent" if hot else "ink2", z=60))
        return objs

    heads = [head("Платформа", "цельный шар"), head("Четыре среза", "от ядра к интерфейсу"),
             head("Срез сервисов", "здесь работаем")]
    return Variant(FAM, "sphere_slices", "Шар режется на срезы",
                   "Шар (с градиентом объёма) разрезан горизонтально на четыре ломтя; ломти раздвигаются вверх, у "
                   "каждого видна светлая крышка-срез. Роль: слои системы «изнутри», геология, уровни.",
                   [Slide(heads[k] + make(k), dur=900) for k in range(3)], tags=["sphere", "slices", "layers", "explode"],
                   score=4)


# ----------------------------------------------------------------------------- 9. плоская сетка сворачивается в глобус

def grid_lines(cx, cy, R, wrap, rot=-20, tilt=15, w=0.03, nm=12, lats=(-60, -30, 0, 30, 60), flat_box=None):
    """Линии сетки: wrap=0 — плоская карта (равнопромежуточная), 1 — на шаре. Одинаковое число точек."""
    fx, fy, fw, fh = flat_box
    out_m, out_p = [], []
    for i in range(nm):
        lon = -180 + i * 360 / nm
        pts = []
        for s in range(19):
            lat = -90 + s * 10
            if wrap == 0:
                pts.append((fx + (lon + 180) / 360 * fw, fy + (90 - lat) / 180 * fh))
            else:
                x, y, d = sph_xyz(lat, lon, R, rot, tilt)
                pts.append(on_disc(cx, cy, R, x, y, d))
        out_m.append(pts)
    for lat in lats:
        pts = []
        for s in range(37):
            lon = -180 + s * 10
            if wrap == 0:
                pts.append((fx + (lon + 180) / 360 * fw, fy + (90 - lat) / 180 * fh))
            else:
                x, y, d = sph_xyz(lat, lon, R, rot, tilt)
                pts.append(on_disc(cx, cy, R, x, y, d))
        out_p.append(pts)
    return out_m, out_p


def v_wrap(theme):
    pal = _pal(theme)
    cx, cy, R = 8.9, 3.95, 2.45
    box = (5.3, 2.1, 7.2, 3.6)
    col = mix(pal["ink"], pal["bg"], 0.35)

    def make(k):
        wrap = 0 if k == 0 else 1
        rot = [-20, -20, -80][k]
        objs = []
        if wrap:
            objs += sphere("!!wg", cx, cy, R, pal["grey3"], gloss=k == 2)
        else:
            fx, fy, fw, fh = box
            objs.append(O("!!wg_b", "oval", cx - R, cy - R, 2 * R, 2 * R, fill=pal["grey3"], fa=0.0, z=10))
            objs.append(O("!!wg_bg", "rect", fx, fy, fw, fh, fill=pal["grey3"], fa=0.6, z=9))
        ms, ps = grid_lines(cx, cy, R, wrap, rot=rot, flat_box=box)
        for i, pts in enumerate(ms):
            objs.append(band(f"!!wm{i}", pts, 0.03, fill=col, z=30, meta={"bleed": True, "decor": True}))
        for j, pts in enumerate(ps):
            objs.append(band(f"!!wp{j}", pts, 0.03, fill=col, z=30, meta={"bleed": True, "decor": True}))
        # одна «наша» точка
        lat, lon = 56, 38
        if wrap:
            x, y, d = sph_xyz(lat, lon, R, rot, 15)
            px, py = on_disc(cx, cy, R, x, y, d)
        else:
            px, py = box[0] + (lon + 180) / 360 * box[2], box[1] + (90 - lat) / 180 * box[3]
        objs.append(O("!!wc", "oval", px - 0.13, py - 0.13, 0.26, 0.26, fill="accent", z=40))
        return objs

    heads = [head("Карта рынка", "плоская сетка"), head("Сворачиваем", "сетка ложится на шар"),
             head("Поворот к нам", "наш регион")]
    return Variant(FAM, "map_to_globe", "Плоская карта сворачивается в глобус",
                   "Равнопромежуточная сетка (меридианы и параллели — ленты с постоянным числом точек) сворачивается "
                   "на шар: каждая линия переливается из прямой в дугу, обратная сторона уходит на кромку; затем шар "
                   "поворачивается. Роль: «из плоского — в объём», мировой рынок.",
                   [Slide(heads[k] + make(k), dur=900) for k in range(3)], tags=["sphere", "globe", "shape-morph", "wrap"],
                   score=5)


# ----------------------------------------------------------------------------- 10. планеты-масштаб: рядом по размеру

def v_planets(theme):
    pal = _pal(theme)
    items = [("2024", 0.75, pal["grey"]), ("2025", 1.1, pal["grey"]), ("2026", 1.6, pal["acc"])]

    def make(k):
        objs = []
        x = 5.2
        for i, (t, r, c) in enumerate(items):
            rr = r if i <= k else 0.12
            cx = x + rr
            cy = 4.4 - (rr - 0.9) * 0.2
            objs += sphere(f"!!pp{i}", cx, cy, rr, c if i <= k else pal["grey2"], z=10 + i * 10)
            if i <= k:
                objs.append(label(f"ppl{i}", cx - 1.0, cy + rr + 0.15, 2.0, t, sz=18, b=True, al="c",
                                  col="accent" if i == 2 else "ink", z=60))
            x = cx + rr + 0.35
        return objs

    heads = [head("Выручка", "2024 год"), head("Рост", "в полтора раза"), head("План", "вдвое больше")]
    return Variant(FAM, "planet_scale", "Планеты растут по годам",
                   "Ряд объёмных шаров: каждый клик «зажигает» следующий год — шар вырастает из зерна до своего "
                   "размера (площадь = значение), соседи сдвигаются. Роль: сравнение 2–4 величин, рост.",
                   [Slide(heads[k] + make(k), dur=850) for k in range(3)], tags=["sphere", "data", "grow"], score=3)


# ----------------------------------------------------------------------------- SEQ 1. мир: карта → глобус → город → панель → снова глобус

def v_seq_globe(theme):
    pal = _pal(theme)
    cx, cy, R = 8.9, 3.95, 2.45
    box = (5.3, 2.1, 7.2, 3.6)
    col = mix(pal["ink"], pal["bg"], 0.35)

    def world(k, wrap, rot, R_=R, cx_=cx, cy_=cy, fa=1.0, hot=None, gloss=True):
        objs = []
        if wrap:
            objs += sphere("!!wg", cx_, cy_, R_, pal["grey3"], gloss=gloss, fa=fa)
        else:
            objs.append(O("!!wg_b", "oval", cx_ - R_, cy_ - R_, 2 * R_, 2 * R_, fill=pal["grey3"], fa=0.0, z=10))
        ms, ps = grid_lines(cx_, cy_, R_, wrap, rot=rot, flat_box=box)
        for i, pts in enumerate(ms):
            objs.append(band(f"!!wm{i}", pts, 0.03, fill=col, fa=fa, z=30, meta={"bleed": True, "decor": True}))
        for j, pts in enumerate(ps):
            objs.append(band(f"!!wp{j}", pts, 0.03, fill=col, fa=fa, z=30, meta={"bleed": True, "decor": True}))
        for c, (nm, lat, lon) in enumerate(CITIES):
            if wrap:
                x, y, d = sph_xyz(lat, lon, R_, rot, 15)
                px, py = on_disc(cx_, cy_, R_, x, y, d)
                vis = d > 0.05 * R_
            else:
                px, py = box[0] + (lon + 180) / 360 * box[2], box[1] + (90 - lat) / 180 * box[3]
                vis = True
            s = 0.13 * (R_ / R) ** 0.5 if c != hot else 0.2 * (R_ / R) ** 0.5
            objs.append(O(f"!!wc{c}", "oval", px - s, py - s, 2 * s, 2 * s, fill="accent" if c == hot else pal["acc3"],
                          fa=(1.0 if c == hot else fa) if vis else 0.0, z=40, meta={"bleed": True}))
        return objs

    def city_of(rot, c, R_=R, cx_=cx, cy_=cy):
        nm, lat, lon = CITIES[c]
        x, y, d = sph_xyz(lat, lon, R_, rot, 15)
        return on_disc(cx_, cy_, R_, x, y, d)

    slides = []
    slides.append(Slide(head("Пять офисов", "на плоской карте") + world(0, 0, -20), dur=900))
    slides.append(Slide(head("Тот же мир", "сетка ложится на шар") + world(1, 1, -20), dur=900))
    # 3: поворот к Москве + выноска
    o = world(2, 1, -45, hot=1)
    px, py = city_of(-45, 1)
    o += [O("cl", "line", px + 0.25, py, 11.3 - px, 0, ln="line", lw=1, z=60),
          label("ct", 11.6, py - 0.22, 1.6, "Москва", sz=18, b=True, col="accent", z=61)]
    slides.append(Slide(head("Главный офис", "поворот к нам") + o, dur=900))
    # 4: камера ныряет к городу: шар огромный, уходит за край; точка — в центр
    Rz = 9.0
    rot = -45
    px0, py0 = city_of(rot, 1, Rz, 0, 0)
    o = world(3, 1, rot, R_=Rz, cx_=8.6 - px0, cy_=4.2 - py0, fa=0.35, hot=1, gloss=False)
    slides.append(Slide(head("Ближе", "москва крупно") + o, dur=900))
    # 5: точка города раскрывается в панель (круглый диск → панель-круг с цифрами)
    o = world(4, 1, rot, R_=Rz, cx_=8.6 - px0, cy_=4.2 - py0, fa=0.15, hot=None, gloss=False)
    o = [x for x in o if x.name != "!!wc1"]
    o.append(O("!!wc1", "oval", 8.6 - 2.1, 4.2 - 2.1, 4.2, 4.2, fill="accent", z=40))
    o.append(label("pn1", 8.6 - 1.7, 3.3, 3.4, ["320 человек", "40% выручки"], sz=24, b=True, al="c",
                   col=ink_on(theme, theme.c("accent")), z=80))
    slides.append(Slide(head("Москва", "главный офис") + o, dur=900))
    # 6: обратно — глобус, поворот к Токио
    o = world(5, 1, -120, hot=4)
    px, py = city_of(-120, 4)
    o += [O("cl6", "line", px + 0.25, py, 11.3 - px, 0, ln="line", lw=1, z=60),
          label("ct6", 11.6, py - 0.22, 1.6, "Токио", sz=18, b=True, col="accent", z=61)]
    slides.append(Slide(head("Следующий шаг", "офис в Азии") + o, dur=900))
    # 7: глобус уходит в угол маленьким знаком — мотив на фоне
    o = world(6, 1, -150, R_=0.9, cx_=12.0, cy_=6.3, fa=0.6, hot=4, gloss=False)
    o.append(label("fin", 0.75, 3.0, 8.0, ["Пять офисов —", "одна команда"], sz=40, b=True, col="ink", z=80))
    slides.append(Slide(head("Итог", "мир — фоном") + o, dur=900))
    return Variant(FAM, "seq_globe", "Мир: карта → глобус → город → итог",
                   "Одна сетка мира живёт 7 слайдов: плоская карта с офисами → сворачивается в глобус → поворот к "
                   "главному офису с выноской → камера «ныряет»: шар огромный и прозрачный, город в центре → точка "
                   "города раскрывается в круг-панель с цифрами → снова глобус, поворот к Азии → глобус уходит "
                   "маленьким знаком в угол, на первом плане вывод. Роль: хребет презентации о географии бизнеса.",
                   slides, tags=["sphere", "seq", "globe", "camera", "wrap"], score=4)


# ----------------------------------------------------------------------------- SEQ 2. система спутников: орбита → спутник-панель → пузыри-данные → столбики → орбита

def v_seq_orbit(theme):
    pal = _pal(theme)
    cx, cy, R = 8.9, 3.9, 1.5
    a, b = 3.6, 1.15
    names = ["Сайт", "Приложение", "Магазины", "Партнёры", "Поддержка"]
    share = [0.34, 0.27, 0.18, 0.13, 0.08]

    def base_scene(fa=1.0):
        o = orbit_ring("!!or_b", cx, cy, a, b, 0.035, pal["grey2"], "back", 5, fa=fa)
        o += sphere("!!pln", cx, cy, R, pal["grey"], fa=fa)
        o += orbit_ring("!!or_f", cx, cy, a, b, 0.035, pal["grey2"], "front", 50, fa=fa)
        return o

    slides = []
    o = base_scene() + moons("!!mn", pal, cx, cy, a, b, 5, 0, names=names, hot=None)
    o.append(label("pc0", cx - 1.0, cy - 0.2, 2.0, "Клиент", sz=18, b=True, al="c", col=ink_on(theme, pal["grey"]), z=40))
    slides.append(Slide(head("Пять каналов", "вокруг клиента") + o, dur=900))
    o = base_scene() + moons("!!mn", pal, cx, cy, a, b, 5, -72, names=names, hot=1)
    o.append(label("pc1", cx - 1.0, cy - 0.2, 2.0, "Клиент", sz=18, b=True, al="c", col=ink_on(theme, pal["grey"]), z=40))
    slides.append(Slide(head("Второй канал", "ближе всех сейчас") + o, dur=900))
    # 3: ближний спутник растёт в большой шар-панель слева, система уходит вправо и тускнеет
    o = base_scene(fa=0.25)
    o += [x.copy(fa=x.fa * 0.25) for x in moons("!!mn", pal, cx, cy, a, b, 5, -72, hot=None) if not x.name.startswith("!!mn1_")]
    o += sphere("!!mn1", 3.4, 4.3, 2.1, pal["acc"], z=200)
    o.append(label("mp", 3.4 - 1.6, 3.85, 3.2, ["27% заказов", "рост ×2"], sz=24, b=True, al="c",
                   col=ink_on(theme, mix(pal["acc"], "FFFFFF", 0.18)), z=260))
    slides.append(Slide(head("Приложение крупно", "доля и рост") + o, dur=900))
    # 4: все спутники становятся пузырями-долями в ряд (площадь = доля), планета гаснет
    o = base_scene(fa=0.0)
    xs = 5.2
    for i in range(5):
        r = 1.5 * math.sqrt(share[i])
        o += sphere(f"!!mn{i}", xs + r, 4.0, r, pal["acc"] if i == 1 else pal["grey"], z=60 + i * 8, gloss=False, rim=False)
        o.append(label(f"bs{i}", xs + r - 0.8, 4.0 + r + 0.12, 1.6, [names[i], f"{round(share[i] * 100)}%"], sz=14,
                       al="c", b=i == 1, col="accent" if i == 1 else "ink2", z=90))
        xs += 2 * r + 0.25
    slides.append(Slide(head("Доли каналов", "площадь шара") + o, dur=900))
    # 5: пузыри сжимаются в точки-верхушки столбиков (столбики — ленты от оси)
    o = base_scene(fa=0.0)
    for i in range(5):
        x = 6.0 + i * 1.35
        h = share[i] * 11
        o += sphere(f"!!mn{i}", x, 6.2 - h, 0.22, pal["acc"] if i == 1 else pal["grey"], z=60 + i * 8, gloss=False, rim=False)
        o.append(O(f"bar{i}", "rect", x - 0.08, 6.2 - h, 0.16, h, fill=pal["acc"] if i == 1 else pal["grey2"], z=55))
        o.append(label(f"bn{i}", x - 0.66, 6.32, 1.32, names[i], sz=12, al="c", col="ink2", z=90))
    slides.append(Slide(head("Те же доли", "столбиками") + o, dur=900))
    # 6: обратно на орбиту, поворот к магазинам
    o = base_scene() + moons("!!mn", pal, cx, cy, a, b, 5, -144, names=names, hot=2)
    o.append(label("pc6", cx - 1.0, cy - 0.2, 2.0, "Клиент", sz=18, b=True, al="c", col=ink_on(theme, pal["grey"]), z=40))
    slides.append(Slide(head("Следующий канал", "офлайн") + o, dur=900))
    return Variant(FAM, "seq_orbit", "Орбита каналов: панель, доли, столбики",
                   "Одна система спутников живёт 6 слайдов: планета-клиент и 5 каналов на наклонной орбите → поворот, "
                   "ближний подписан → он вырастает в большой шар-панель с цифрами (система уходит тихим фоном) → все "
                   "спутники выстраиваются пузырями-долями → сжимаются в верхушки столбиков → снова орбита, поворот "
                   "к следующему каналу. Роль: сквозной мотив презентации о каналах продаж.",
                   slides, tags=["sphere", "seq", "orbit", "data", "circle-motion"], score=4)


def variants(theme) -> list[Variant]:
    from lab._c_util import ensure_contrast
    return ensure_contrast(theme, [f(theme) for f in (v_globe, v_phase, v_orbit, v_orbit_pivot, v_bubbles, v_lunes, v_atom, v_lens, v_slices, v_wrap,
                               v_planets, v_seq_globe, v_seq_orbit)])
