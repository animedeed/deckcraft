"""Семейство peel: слоистые формы (полосы бутона V.bud, луковица из колец, стопка дисков, пятна-горизонтали,
листы) — слои отслаиваются, выезжают по оси, раскрываются веером, открываются створками и снова складываются.
Слой = уровень детализации.
"""

from __future__ import annotations

import math

from morphkit import O, Slide
from morphkit import vector as V
from morphkit.presets import Fx
from morphkit.theme import contrast, mix

from lab import Variant
from lab._a_util import (arrow_poly, arc_band, bar_band, blob, cut, head, iso, label, orbit, put, sub, sweep)

N = 140


def on(theme, fill):
    f = theme.c(fill)
    a, b = theme.c("ink"), theme.c("bg")
    return a if contrast(a, f) >= contrast(b, f) else b


def band_cols(theme, n):
    ink, bg = theme.c("ink"), theme.c("bg")
    return [mix(ink, bg, 0.15 + 0.5 * k / max(n - 1, 1)) for k in range(n)]


def bud_parts(base, length, width, layers=5, angle=0.0):
    return [V.resample(g, N) for g in V.bud(base, length, width, layers=layers, angle=angle, h_ratio=0.8, w_ratio=0.8)]


LEVELS = ["Миссия", "Цели", "Проекты", "Задачи", "Действие"]


# ----------------------------------------------------------------------------- одиночные варианты

def v_bud_slide(theme):
    base = (4.1, 4.1)
    parts = bud_parts(base, 6.2, 2.9, 5, angle=0.0)
    cols = band_cols(theme, 5)[:4] + [theme.c("accent")]
    R = 9.0

    def st(shift, fan):
        out = []
        for j, g in enumerate(parts):
            dx = shift * (4 - j)
            out.append(orbit(f"!!b{j}", V.move(g, dx, 0), base, R, (j - 2) * fan, fill=cols[j], ln=theme.c("bg"), lw=1.2, z=10 + j))
        return out

    def labs(shift, fan, key):
        out = []
        for j, g in enumerate(parts):
            tip = g.bounds[2] + shift * (4 - j)
            L = tip - base[0]
            a = math.radians((j - 2) * fan)
            x, y = base[0] + (L + 0.15) * math.cos(a), base[1] + (L + 0.15) * math.sin(a)
            out.append(label(f"{key}{j}", LEVELS[j], x, y, w=1.8, sz=16, col="accent" if j == 4 else "ink2", al="l",
                             b=j == 4))
        return out

    l1 = labs(0, 0, "la")
    l1 = [l.copy(y=2.0 + 0.0 * j, x=4.6 + 1.25 * j - 0.6 + (0 if j < 4 else 0), w=1.6) for j, l in enumerate(l1)]
    s0 = Slide([head("Один образ — пять слоёв")] + st(0, 0), dur=800)
    s1 = Slide([head("Слои выдвигаются по оси")] + st(0.95, 0), dur=850)
    s2 = Slide([head("Веер уровней")] + st(0, 13) + labs(0, 13, "lf"), dur=900,
               fx=[Fx("entrance_fade", f"lf{j}", start="at", delay=0.1 + 0.05 * j, dur=0.3) for j in range(5)])
    return Variant("peel", "bud_slide", "Бутон: слои выдвигаются и веером",
                   "Многослойный лепесток-бутон лежит на боку; полосы выдвигаются вдоль оси, как подзорная труба, затем "
                   "раскрываются веером вокруг общей вершины, и у каждой — свой уровень. Роль: от миссии к действию.",
                   [s0, s1, s2], tags=["peel", "bud", "fan", "pivot", "levels"], score=3)


def _lock(theme, cx, cy, gaps, rings=5, r0=0.55, t=0.36, gapw=34.0, key="!!r"):
    out = []
    cols = band_cols(theme, rings)
    for k in range(rings):
        ri = r0 + k * (t + 0.08)
        g = arc_band(cx, cy, ri, ri + t, -90 + gapw / 2, 270 - gapw / 2, m=72)
        out.append(orbit(f"{key}{k}", g, (cx, cy), r0 + rings * (t + 0.08) + 0.2, gaps[k], fill=cols[rings - 1 - k], z=10 + k))
    return out


def v_lock_align(theme):
    cx, cy = 8.6, 3.95
    g0 = [40, -70, 120, -150, 80]
    g1 = [90] * 5
    core = O("!!core", "oval", cx - 0.4, cy - 0.4, 0.8, 0.8, fill="accent", z=20)
    arrow = V.shape("thr", arrow_poly(12.4, cy, cx + 0.45, cy), fill="accent", z=30)
    return Variant("peel", "lock_align", "Кольца-замок: дыры совпали",
                   "Пять колец с прорезями вращаются каждое на свой угол, пока прорези не выстроятся в коридор, и "
                   "угроза проходит к ядру (модель «швейцарского сыра»). Роль: риски, «почему случилась авария».",
                   [Slide([head("Пять уровней защиты"), sub("У каждого есть слабое место")] + _lock(theme, cx, cy, g0) + [core], dur=800),
                    Slide([head("Когда дыры совпали"), arrow] + _lock(theme, cx, cy, g1) + [core], dur=900,
                          fx=[Fx("entrance_wipe", "thr", start="at", delay=0.15, dur=0.5, options={"direction": "right"})])],
                   tags=["peel", "rings", "rotate", "pivot", "risk"], score=4)


def v_ring_unroll(theme):
    cx, cy = 4.2, 4.0
    vals = [0.92, 0.74, 0.61, 0.43, 0.28]
    names = ["Узнали", "Попробовали", "Купили", "Вернулись", "Советуют"]
    cols = band_cols(theme, 5)
    t, gap = 0.34, 0.1

    def rings():
        out = []
        for k, v in enumerate(vals):
            ri = 2.25 - k * (t + gap) - t
            out.append(V.shape(f"!!u{k}", arc_band(cx, cy, ri, ri + t, -90, -90 + 360 * v, m=72), fill=cols[k], z=10 + k))
        return out

    def bars():
        out = []
        for k, v in enumerate(vals):
            y = 2.1 + k * 0.72
            out.append(V.shape(f"!!u{k}", bar_band(5.6, y, 6.6 * v, 0.42, m=72), fill=cols[k], z=10 + k))
        return out

    lab_r = [label(f"lr{k}", names[k], 6.95, 2.05 + k * (t + gap), w=2.4, sz=15, col="ink2", al="l") for k in range(5)]
    lab_b = [label(f"lb{k}", f"{names[k]} · {round(v * 100)}%", 2.9, 2.1 + k * 0.72 + 0.21, w=2.6, sz=16, col="ink2", al="l")
             for k, v in enumerate(vals)]
    lab_b = [l.copy(x=2.9) for l in lab_b]
    return Variant("peel", "ring_unroll", "Кольца разворачиваются в полосы",
                   "Вложенные дуги-доли воронки (каждая — свой процент круга) распрямляются в горизонтальные полосы той "
                   "же длины по порядку точек — видно, что это те же величины. Роль: данные, переход «красиво → точно».",
                   [Slide([head("Воронка как кольца")] + rings() + lab_r, dur=800,
                          fx=[Fx("entrance_fade", f"lr{k}", start="at", delay=0.1 + 0.05 * k, dur=0.25) for k in range(5)]),
                    Slide([head("Те же доли — полосами")] + bars() + lab_b, dur=900,
                          fx=[Fx("entrance_fade", f"lb{k}", start="at", delay=0.1 + 0.05 * k, dur=0.25) for k in range(5)])],
                   tags=["peel", "rings", "unroll", "data", "shape-morph"], score=5)


def _disk(theme, name, cx, cy, rx, ry, th, col, z, fa=1.0):
    top = V.resample(V.ellipse(cx, cy, rx, ry), N)
    side = V.resample(sweep(V.ellipse(cx, cy + th, rx, ry), th) if th > 0 else V.ellipse(cx, cy, rx, ry), N)
    return [V.shape(f"{name}s", side, fill=mix(col, theme.c("bg"), 0.5), fa=fa, z=z),
            V.shape(f"{name}t", top, fill=col, fa=fa, ln=theme.c("bg"), lw=1.0, z=z + 1)]


def v_disk_stack(theme):
    cx = 8.6
    cols = band_cols(theme, 5)
    names = ["Интерфейс", "API", "Логика", "Данные", "Железо"]

    def stack(gap, out_k=None):
        out, labs = [], []
        y0 = 4.6 - 2 * gap
        for k in range(5):
            y = y0 + k * gap
            if k == out_k:
                out += _disk(theme, f"!!d{k}", 3.4, 4.0, 1.75, 1.75, 0.0, theme.c("accent"), 80)
                continue
            col = cols[k]
            out += _disk(theme, f"!!d{k}", cx, y, 2.3, 0.62, 0.22, col, 50 - 2 * k)
            labs.append((k, y))
        return out, labs

    s0o, _ = stack(0.32)
    s1o, l1 = stack(0.98)
    lab1 = [label(f"dl{k}", names[k], 11.6, y, w=1.9, sz=16, col="ink2", al="l") for k, y in l1]
    s2o, l2 = stack(0.98, out_k=2)
    lab2 = [label(f"dm{k}", names[k], 11.6, y, w=1.9, sz=16, col="ink2", al="l") for k, y in l2]
    cap = [label("dc", "Логика", 3.4, 3.75, w=2.6, sz=26, col="on_accent", b=True, z=95),
           label("dc2", "правила и расчёты", 3.4, 4.35, w=3.0, sz=16, col="on_accent", z=95)]
    return Variant("peel", "disk_stack", "Стопка дисков: слой выезжает",
                   "Архитектура как стопка объёмных дисков (имитация 3D из эллипсов и «стенок»): стопка раздвигается "
                   "по высоте с подписями, затем один слой выезжает в сторону и поворачивается к зрителю кругом. "
                   "Роль: уровни системы, «а теперь подробно про этот слой».",
                   [Slide([head("Пять слоёв системы")] + s0o, dur=800),
                    Slide([head("Раздвигаем")] + s1o + lab1, dur=900,
                          fx=[Fx("entrance_fade", l.name, start="at", delay=0.1 + 0.04 * i, dur=0.25) for i, l in enumerate(lab1)]),
                    Slide([head("Слой крупно")] + s2o + lab2 + cap, dur=900,
                          fx=[Fx("entrance_fade", "dc", start="at", delay=0.12, dur=0.3), Fx("entrance_fade", "dc2", start="with", delay=0.05, dur=0.3)])],
                   tags=["peel", "3d", "stack", "space", "architecture"], score=4)


def v_topo(theme):
    cx, cy = 8.6, 4.0
    L = 6
    ink, bg = theme.c("ink"), theme.c("bg")
    cols = [mix(ink, bg, 0.82 - 0.13 * k) for k in range(L - 1)] + [theme.c("accent")]
    shapes = [V.resample(blob(cx, cy, 2.6 - 0.4 * k, amps=(0.1, 0.07, 0.05), phase=0.6 * k), N) for k in range(L)]

    def st(vx, vy, lift=0.0):
        out = []
        for k, g in enumerate(shapes):
            s = 1.0 + (lift if k == L - 1 else 0)
            out.append(put(f"!!t{k}", g, vx * k, vy * k - (0.5 if lift and k == L - 1 else 0), s=s, fill=cols[k],
                           ln=bg, lw=1.0, z=10 + k))
        return out

    tag = [label("tg", "Вершина: 4 % клиентов", 11.6, 1.45, w=3.2, sz=18, col="accent", b=True)]
    return Variant("peel", "topo", "Горизонтали поднимаются холмом",
                   "Вложенные пятна-горизонтали смещаются с шагом по глубине — плоская карта становится холмом, "
                   "затем ракурс поворачивается, а вершина приподнимается. Роль: «пирамида» клиентов без пирамиды, фон.",
                   [Slide([head("Карта уровней")] + st(0, 0), dur=800),
                    Slide([head("Это холм")] + st(0.22, -0.2), dur=900),
                    Slide([head("Вид с другой стороны")] + st(-0.24, -0.22, lift=0.2) + tag, dur=900,
                          fx=[Fx("entrance_fade", "tg", start="at", delay=0.12, dur=0.3)])],
                   tags=["peel", "blob", "3d", "parallax", "background"], score=4)


def _flower(theme, cx, cy, active, detach=None, sep=0.0, push=0.0, scale=1.0, dim=1.0, petals=8, layers=4,
            length=2.5, width=1.0, key="!!f"):
    parts = [V.resample(g, N) for g in V.bud((cx, cy), length, width, layers=layers, angle=-90, h_ratio=0.78, w_ratio=0.8)]
    ink, bg = theme.c("ink"), theme.c("bg")
    cols = [mix(ink, bg, 0.12 + 0.18 * j) for j in range(layers - 1)] + [theme.c("accent")]
    R = 8.0
    out = []
    for k in range(petals):
        rot = 270 + (k - active) * 360 / petals
        for j, g in enumerate(parts):
            gg = g
            fa = dim
            if k == detach:
                gg = V.scale(g, scale, origin=(cx, cy))
                gg = V.move(gg, 0, -(push + sep * (layers - 1 - j)))
                fa = 1.0
            out.append(orbit(f"{key}{k}_{j}", gg, (cx, cy), R, rot, fill=cols[j], fa=fa, ln=bg, lw=0.8,
                             z=10 + (40 if k == detach else 0) + k * layers + j))
    return out


def v_petal_detail(theme):
    cx, cy = 10.6, 3.9
    dets = ["Обзор", "Метрики", "Риски", "Решение"]

    def labs(key):
        # лепесток смотрит влево: слои разнесены по оси x
        xs = [3.25, 4.7, 6.05, 7.3]
        return [label(f"{key}{j}", dets[j], xs[j], 5.15, w=1.4, sz=15, col="accent" if j == 3 else "ink2", b=j == 3) for j in range(4)]

    l1 = labs("pd")
    return Variant("peel", "petal_detail", "Лепесток выходит из цветка",
                   "Цветок из многослойных лепестков; лепесток темы выдвигается из цветка по своей оси, вырастает, его "
                   "слои расходятся с подписями (уровни детализации), а цветок уходит в полутень. На следующем шаге "
                   "лепесток возвращается, цветок поворачивается на один шаг. Роль: навигация по темам с раскрытием.",
                   [Slide([head("Восемь тем")] + _flower(theme, cx, cy, 0), dur=800),
                    Slide([head("Тема 1 по слоям")] + _flower(theme, cx, cy, 0, detach=0, sep=0.55, push=2.7, scale=1.45, dim=0.28) + l1,
                          dur=900, fx=[Fx("entrance_fade", f"pd{j}", start="at", delay=0.12 + 0.05 * j, dur=0.25) for j in range(4)]),
                    Slide([head("Тема 2")] + _flower(theme, cx, cy, 1), dur=850)],
                   tags=["peel", "petal", "flower", "pivot", "navigation", "detail"], score=4)


def v_sheet_peel(theme):
    piv = (6.6, 6.2)
    names = ["Черновик", "Ревью", "Правки", "Итог"]
    ink_, bg_ = theme.c("ink"), theme.c("bg")
    cols = [mix(ink_, bg_, t) for t in (0.3, 0.45, 0.58, 0.7)]

    def sheet(k, ang):
        x, y, w, h = piv[0] + 0.14 * k, piv[1] - 3.4 - 0.14 * k, 4.8, 3.4
        g = V.rect(x, y, w, h, r=0.12)
        p = (x, y + h)
        R = math.hypot(w, h) + 0.05
        o = orbit(f"!!sh{k}", g, p, R, ang, fill=cols[k], ln=theme.c("bg"), lw=1.2, z=10 + (4 - k))
        # подпись: центр подписи поворачивается вокруг угла листа, сама надпись — горизонтально по оси листа
        lx, ly = x + w - 2.95, y + h - 0.85  # подпись у правого нижнего угла — открывается, когда лист сверху отогнут
        a = math.radians(ang)
        qx = p[0] + (lx + 1.3 - p[0]) * math.cos(a) - (ly + 0.25 - p[1]) * math.sin(a)
        qy = p[1] + (lx + 1.3 - p[0]) * math.sin(a) + (ly + 0.25 - p[1]) * math.cos(a)
        t = O(f"!!st{k}", "text", qx - 1.3, qy - 0.25, 2.6, 0.5, txt=names[3 - k], sz=20, b=True, al="r",
              col=on(theme, cols[k]), rot=ang, z=10 + (4 - k) + 0.5, meta={"overlap_ok": True})
        return [o, t]

    def st(angs):
        out = []
        for k, a in enumerate(angs):
            out += sheet(k, a)
        return out

    return Variant("peel", "sheet_peel", "Листы отгибаются от угла",
                   "Стопка листов-версий; верхний лист отгибается вокруг нижнего левого угла (рамка на оси), затем "
                   "следующий — открывается история документа слой за слоем. Роль: версии, этапы согласования.",
                   [Slide([head("Четыре версии")] + st([0, 0, 0, 0]), dur=800),
                    Slide([head("Под итогом — правки")] + st([-28, 0, 0, 0]), dur=850),
                    Slide([head("Под правками — ревью")] + st([-44, -22, 0, 0]), dur=850)],
                   tags=["peel", "sheets", "pivot", "versions"], score=3)


def v_shell(theme):
    cx, cy = 8.4, 4.0
    bg = theme.c("bg")
    cols = band_cols(theme, 3)

    def halves(ri, ro, k, ang):
        top = V.resample(V.sector(cx, cy, ro, 180, 360, r_in=ri), N)
        bot = V.resample(V.sector(cx, cy, ro, 0, 180, r_in=ri), N)
        hinge = (cx - ro, cy)
        R = 2 * ro + 0.1
        return [orbit(f"!!h{k}t", top, hinge, R, -ang, fill=cols[k], ln=bg, lw=1.2, z=20 - k),
                orbit(f"!!h{k}b", bot, hinge, R, ang, fill=mix(cols[k], bg, 0.15), ln=bg, lw=1.2, z=20 - k)]

    def st(a0, a1):
        out = halves(1.35, 2.05, 0, a0) + halves(0.8, 1.35, 1, a1)
        out.append(O("!!core", "oval", cx - 0.8, cy - 0.8, 1.6, 1.6, fill="accent", z=5))
        return out

    cap = label("cc", "Ядро", cx, cy, w=1.4, sz=22, col="on_accent", b=True, z=8)
    return Variant("peel", "shell", "Створки открываются",
                   "Шар из двух оболочек раскрывается створками на шарнире: сначала внешняя, затем внутренняя, "
                   "и в глубине — акцентное ядро. Роль: «заглянуть внутрь продукта», раскрытие сути после интриги.",
                   [Slide([head("Что внутри")] + st(0, 0), dur=800),
                    Slide([head("Внешняя оболочка")] + st(28, 0), dur=850),
                    Slide([head("И ещё глубже"), cap] + st(46, 26), dur=850,
                          fx=[Fx("entrance_fade", "cc", start="at", delay=0.15, dur=0.3)])],
                   tags=["peel", "pivot", "open", "reveal"], score=3)


def v_strata(theme):
    ink, bg = theme.c("ink"), theme.c("bg")
    names = ["Почва", "Глина", "Песок", "Известняк", "Гранит"]
    vals = [0.9, 2.1, 1.4, 3.0, 2.3]
    cols = [mix(ink, bg, 0.15 + 0.12 * k) for k in range(5)]
    x0, x1 = 4.2, 12.6

    def wave(y, amp, ph):
        return [(x0 + (x1 - x0) * i / 63, y + amp * math.sin(2 * math.pi * i / 63 * 1.5 + ph)) for i in range(64)]

    bounds = [1.9]
    for v in vals:
        bounds.append(bounds[-1] + v * 0.4 + 0.12)
    layers = []
    for k in range(5):
        top, bot = wave(bounds[k], 0.12, k * 0.7), wave(bounds[k + 1], 0.12, (k + 1) * 0.7)
        layers.append(V.resample(V.polygon(top + bot[::-1]), N))

    def st(mode):
        out = []
        for k, g in enumerate(layers):
            if mode == 0:
                out.append(V.shape(f"!!s{k}", g, fill=cols[k], ln=bg, lw=1.0, z=10 + k))
            elif mode == 1:
                out.append(V.shape(f"!!s{k}", V.move(g, (k % 2) * 0.9 - 0.45, 0.12 * k - 0.2), fill=cols[k], ln=bg, lw=1.0, z=10 + k))
            else:
                y = 1.95 + k * 0.85
                out.append(V.shape(f"!!s{k}", V.resample(V.rect(x0, y, vals[k] * 2.6, 0.58, r=0.05), N), fill=cols[k], z=10 + k))
        return out

    l0 = [label(f"sn{k}", names[k], 2.6, (bounds[k] + bounds[k + 1]) / 2, w=2.4, sz=16, col="ink2", al="l") for k in range(5)]
    l2 = [label(f"sv{k}", f"{names[k]} · {vals[k]:.1f} м".replace(".", ","), 2.0, 1.95 + k * 0.85 + 0.29, w=2.2, sz=16, col="ink2", al="l")
          for k in range(5)]
    return Variant("peel", "strata", "Пласты сдвигаются и выпрямляются",
                   "Геологический разрез из волнистых пластов: пласты расходятся сдвигом, затем выпрямляются в "
                   "полосы, длина которых — толщина пласта. Роль: состав целого, данные «из разреза в график».",
                   [Slide([head("Разрез участка")] + st(0) + l0, dur=800),
                    Slide([head("Пласты по отдельности")] + st(1), dur=850),
                    Slide([head("Толщина пластов")] + st(2) + l2, dur=900,
                          fx=[Fx("entrance_fade", f"sv{k}", start="at", delay=0.1 + 0.05 * k, dur=0.25) for k in range(5)])],
                   tags=["peel", "layers", "data", "shape-morph"], score=4)


def v_lens_fan(theme):
    piv = (8.6, 6.3)
    names = ["Сбор", "Очистка", "Признаки", "Модель", "Проверка", "Запуск"]
    ink, bg = theme.c("ink"), theme.c("bg")
    leaf = V.resample(V.petal(piv, 0.25, 4.3, 0.95), N)
    long_ = V.resample(V.petal(piv, 0.25, 4.9, 1.3), N)
    R = 5.2

    def st(spread, active=None, center=None):
        out = []
        for k in range(6):
            rot = (k - 2.5) * spread - (0 if center is None else (center - 2.5) * spread)
            g = long_ if k == active else leaf
            col = theme.c("accent") if k == active else mix(ink, bg, 0.2 + 0.08 * k)
            out.append(orbit(f"!!lf{k}", g, piv, R, rot, fill=col, ln=bg, lw=1.0, z=10 + k + (20 if k == active else 0)))
        return out

    def labs(spread, center=None, key="ln", skip=None):
        out = []
        for k in range(6):
            if k == skip:
                continue
            rot = (k - 2.5) * spread - (0 if center is None else (center - 2.5) * spread)
            a = math.radians(-90 + rot)
            rr = 4.75
            out.append(label(f"{key}{k}", names[k], piv[0] + rr * math.cos(a), piv[1] + rr * math.sin(a), w=1.5, sz=15, col="ink2"))
        return out

    l1 = labs(24)
    l2 = labs(24, center=3, skip=3)
    act = label("lact", "Модель", piv[0], 0.95, w=2.0, sz=20, col="accent", b=True)
    return Variant("peel", "lens_fan", "Стопка листьев раскрывается веером",
                   "Шесть листьев-линз лежат стопкой, раскрываются веером вокруг общего черенка с подписями этапов, "
                   "затем веер проворачивается, выводя активный этап вверх, и тот вытягивается акцентом. Роль: этапы "
                   "процесса, навигация по шагам.",
                   [Slide([head("Шесть этапов")] + st(0), dur=800),
                    Slide([head("Конвейер данных")] + st(24) + l1, dur=900,
                          fx=[Fx("entrance_fade", l.name, start="at", delay=0.1 + 0.04 * i, dur=0.25) for i, l in enumerate(l1)]),
                    Slide([head("Сейчас — модель")] + st(24, active=3, center=3) + l2 + [act], dur=850,
                          fx=[Fx("entrance_fade", "lact", start="at", delay=0.12, dur=0.3)])],
                   tags=["peel", "petal", "fan", "pivot", "navigation", "process"], score=4)


def v_iso_cake(theme):
    cx, cy = 7.6, 4.2
    radii = [2.6, 2.0, 1.4, 0.8]
    names = ["Все клиенты", "Активные", "Платящие", "Лояльные"]
    ink, bg = theme.c("ink"), theme.c("bg")
    cols = [mix(ink, bg, 0.55 - 0.13 * k) for k in range(3)] + [theme.c("accent")]
    rings = []
    for k, r in enumerate(radii):
        g = V.circle(cx, cy, r)
        if k + 1 < len(radii):
            g = V.subtract(g, V.circle(cx, cy, radii[k + 1]))
        rings.append(g)
    origin = (cx, cy)

    def st(mode):
        out = []
        for k, r in enumerate(radii):
            disk = V.circle(cx, cy, r)  # верх яруса — целый диск (лежит поверх нижнего)
            if mode == 0:
                top = side = disk
            else:
                gi = iso(disk, origin, tilt=0.45, turn=0.0)
                h = 0.0 if mode == 1 else 0.45 * (k + 1)
                top, side = V.move(gi, 0, -h), sweep(gi, h)
            out.append(V.shape(f"!!cs{k}", V.resample(side, N), fill=mix(cols[k], bg, 0.45), z=10 + 2 * k))
            out.append(V.shape(f"!!ct{k}", V.resample(top, N), fill=cols[k], ln=bg, lw=1.0, z=11 + 2 * k))
        return out

    labs = []
    for k, r in enumerate(radii):
        y = cy - 0.45 * (k + 1) * 1.0 - 0.45 * r * 0.0
        labs.append(label(f"ck{k}", names[k], cx + 3.35, cy + 0.3 - 0.62 * (k + 1), w=2.4, sz=16,
                          col="accent" if k == 3 else "ink2", al="l", b=k == 3))
    return Variant("peel", "iso_cake", "Кольца становятся ярусами",
                   "Вложенные круги-сегменты наклоняются в изометрию и поднимаются ярусами торта: чем уже сегмент, тем "
                   "выше ярус. Имитация 3D из 2D. Роль: воронка/пирамида аудитории, кульминация раздела про клиентов.",
                   [Slide([head("Четыре круга клиентов")] + st(0), dur=800),
                    Slide([head("Кладём на стол")] + st(1), dur=850),
                    Slide([head("Ярусы ценности")] + st(2) + labs, dur=900,
                          fx=[Fx("entrance_fade", l.name, start="at", delay=0.1 + 0.05 * i, dur=0.25) for i, l in enumerate(labs)])],
                   tags=["peel", "3d", "iso", "rings", "data"], score=4)


# ----------------------------------------------------------------------------- живые последовательности

def v_seq_bud(theme):
    """Бутон через весь доклад: целый → слои по оси → слой уходит в панель → панель на три карточки →
    маркер по слоям → бутон в изометрии слоями-плитами → фон под тезис → полосы-веса → снова бутон."""
    bg, ink = theme.c("bg"), theme.c("ink")
    base = (8.2, 6.55)
    L, W = 4.7, 3.2
    raw = V.bud(base, L, W, layers=5, angle=-90, h_ratio=0.8, w_ratio=0.8)
    cols = band_cols(theme, 5)[:4] + [theme.c("accent")]
    # слой 1 заранее разрезан на три дольки (станут карточками)
    b1 = raw[1]
    bx = b1.bounds
    sl = cut(b1, [[(bx[0] - 1, bx[1] + (bx[3] - bx[1]) * t), (bx[2] + 1, bx[1] + (bx[3] - bx[1]) * t)] for t in (0.28, 0.52)])
    sl = sorted(sl, key=lambda g: g.centroid.y)[:3]
    pieces = [("l0", raw[0], 0), ("l1a", sl[0], 1), ("l1b", sl[1], 1), ("l1c", sl[2], 1), ("l2", raw[2], 2), ("l3", raw[3], 3),
              ("l4", raw[4], 4)]
    G0 = {nm: V.resample(g, N) for nm, g, _ in pieces}
    lay = {nm: j for nm, _, j in pieces}
    names = [nm for nm, _, _ in pieces]
    LV = ["Рынок", "Клиенты", "Продукт", "Команда", "Ядро"]

    def objs(geo, fa=None, lw=1.2, z0=10, fills=None):
        return [V.shape(f"!!z{nm}", geo[nm], fill=(fills or {}).get(nm, cols[lay[nm]]), fa=(fa or {}).get(nm, 1.0), ln=bg, lw=lw,
                        z=z0 + i) for i, nm in enumerate(names)]

    def slid(k):
        return {nm: V.move(G0[nm], 0, -k * (4 - lay[nm])) for nm in names}

    S = []
    S.append(Slide([head("Компания в одном образе")] + objs(G0), dur=800))
    g1 = slid(0.38)
    labs1 = []
    for j in range(5):
        tip_y = min(g1[nm].bounds[1] for nm in names if lay[nm] == j)
        labs1.append(label(f"bl{j}", LV[j], 10.7, tip_y + 0.12, w=2.0, sz=16, col="accent" if j == 4 else "ink2", al="l", b=j == 4))
    S.append(Slide([head("Пять слоёв")] + objs(g1) + labs1, dur=850,
                   fx=[Fx("entrance_fade", l.name, start="at", delay=0.1 + 0.04 * i, dur=0.25) for i, l in enumerate(labs1)]))
    # 2: слой «Клиенты» (3 дольки) уходит влево и складывается в панель; бутон закрывается правее
    g2 = {nm: V.move(G0[nm], 2.6, 0) for nm in names}
    px, py, pw, ph = 0.8, 1.7, 6.0, 3.9
    for i, nm in enumerate(("l1a", "l1b", "l1c")):
        g2[nm] = V.resample(V.rect(px, py + ph * i / 3, pw, ph / 3 + 0.01, r=0.03), N)
    acc = {nm: theme.c("accent2") if theme.name == "ink" else theme.c("surface2") for nm in ("l1a", "l1b", "l1c")}
    pc = acc["l1a"]
    t2 = [O("p2a", "text", px + 0.35, py + 0.3, 5.0, 0.7, txt="Клиенты", sz=32, b=True, col=on(theme, pc), z=60),
          O("p2b", "text", px + 0.35, py + 1.1, 5.0, 0.6, txt="Кто они и что ценят", sz=19, col=on(theme, pc), z=60)]
    S.append(Slide([head("Слой «Клиенты»", x=7.2, w=5.6)] + objs(g2, fills=acc, lw=0) + t2, dur=900,
                   fx=[Fx("entrance_fade", "p2a", start="at", delay=0.1, dur=0.3), Fx("entrance_fade", "p2b", start="with", delay=0.05, dur=0.3)]))
    # 3: панель делится на три карточки
    g3 = dict(g2)
    segs = ["Малый бизнес", "Сети", "Госзаказ"]
    t3 = []
    for i, nm in enumerate(("l1a", "l1b", "l1c")):
        y = py + i * 1.33
        g3[nm] = V.resample(V.rect(px + 0.35 * i, y, pw - 0.7, 1.13, r=0.15), N)
        t3.append(O(f"c3{i}", "text", px + 0.35 * i + 0.3, y, 4.5, 1.13, txt=segs[i], sz=22, b=True, col=on(theme, pc), va="m", z=60))
    S.append(Slide([head("Три сегмента", x=7.2, w=5.6)] + objs(g3, fills=acc, lw=0) + t3, dur=850,
                   fx=[Fx("entrance_fade", t.name, start="at", delay=0.1 + 0.06 * i, dur=0.25) for i, t in enumerate(t3)]))
    # 4: дольки вернулись; маркер-контур на слое «Команда»
    g4 = {nm: V.move(G0[nm], 2.6, 0) for nm in names}
    mk = V.shape("!!mk", V.resample(V.move(raw[3], 2.6, 0), N), fill=None, ln="accent", lw=3.0, z=40)
    t4 = [O("n4", "text", 0.8, 2.2, 1.6, 0.9, txt="04", sz=40, b=True, col="accent", z=60),
          O("t4", "text", 0.8, 3.1, 5.6, 0.7, txt="Команда", sz=30, b=True, col="ink", z=60),
          O("b4", "text", 0.8, 3.9, 5.6, 1.0, txt="Кто делает продукт", sz=18, col="ink2", z=60)]
    S.append(Slide([head("Сейчас — команда")] + objs(g4) + [mk] + t4, dur=850,
                   fx=[Fx("entrance_fade", t.name, start="at", delay=0.1 + 0.05 * i, dur=0.25) for i, t in enumerate(t4)]))
    # 5: слои становятся этажами — изометрические плиты стопкой (три дольки «Клиентов» — одна плита из трёх частей)
    def diamond(cxp, cyp, w, h):
        return V.polygon([(cxp, cyp - h / 2), (cxp + w / 2, cyp), (cxp, cyp + h / 2), (cxp - w / 2, cyp)])

    g5, walls = {}, []
    for j in range(5):
        cyp = 5.7 - 0.82 * j
        dm = diamond(9.4, cyp, 4.2, 1.3)
        walls.append(V.shape(f"wall{j}", sweep(V.move(dm, 0, 0.2), 0.2), fill=mix(cols[j], bg, 0.5), z=9 + 2 * j))
        if j == 1:
            bb = dm.bounds
            parts3 = cut(dm, [[(bb[0] + (bb[2] - bb[0]) * t, bb[1] - 1), (bb[0] + (bb[2] - bb[0]) * t - 1.0, bb[3] + 1)] for t in (0.4, 0.62)])
            parts3.sort(key=lambda g: g.centroid.x)
            for nm, g in zip(("l1a", "l1b", "l1c"), parts3):
                g5[nm] = V.resample(g, N)
        else:
            nm = [n for n in names if lay[n] == j][0]
            g5[nm] = V.resample(dm, N)
    labs5 = [label(f"il{j}", LV[j], 6.6, 5.7 - 0.82 * j, w=2.2, sz=16, col="accent" if j == 4 else "ink2", al="r") for j in range(5)]
    labs5 = [l.copy(x=4.4) for l in labs5]
    S.append(Slide([head("Слои — этажи")] + objs(g5, lw=1.0, z0=20) + walls + labs5, dur=900,
                   fx=[Fx("entrance_fade", w.name, start="at", delay=0.05, dur=0.3) for w in walls]
                   + [Fx("entrance_fade", l.name, start="at", delay=0.15 + 0.04 * i, dur=0.25) for i, l in enumerate(labs5)]))
    # 6: фон под тезис
    g6 = {nm: V.move(V.scale(G0[nm], 1.7, origin=base), 2.8, 1.6) for nm in names}
    S.append(Slide([O("q6", "text", 0.8, 2.6, 7.6, 2.0, txt=["Сильная компания", "растёт слоями"], sz=46, b=True, col="ink", z=60)]
                   + objs(g6, fa={nm: 0.14 for nm in names}, lw=0, z0=-60), dur=900,
                   fx=[Fx("entrance_fade", "q6", start="at", delay=0.1, dur=0.35)]))
    # 7: слои -> полосы-веса (три дольки «Клиентов» — составная полоса)
    w7 = {0: 4.6, 1: 6.4, 2: 5.2, 3: 3.3, 4: 2.1}
    g7 = {}
    for j in range(5):
        y = 1.8 + j * 0.85
        if j == 1:
            for i, nm in enumerate(("l1a", "l1b", "l1c")):
                g7[nm] = V.resample(V.rect(4.0 + w7[1] * i / 3, y, w7[1] / 3, 0.55, r=0.02), N)
        else:
            nm = [n for n in names if lay[n] == j][0]
            g7[nm] = V.resample(V.rect(4.0, y, w7[j], 0.55, r=0.05), N)
    labs7 = [label(f"wl{j}", LV[j], 2.1, 1.8 + j * 0.85 + 0.27, w=1.8, sz=16, col="accent" if j == 4 else "ink2", al="l") for j in range(5)]
    S.append(Slide([head("Вес каждого слоя")] + objs(g7, lw=0.8) + labs7, dur=900,
                   fx=[Fx("entrance_fade", l.name, start="at", delay=0.1 + 0.04 * i, dur=0.25) for i, l in enumerate(labs7)]))
    S.append(Slide([head("Снова целое")] + objs(G0), dur=900))
    return Variant("peel", "seq_bud", "Бутон через весь доклад",
                   "Один многослойный бутон в 9 состояниях: целый, слои выдвигаются с подписями, слой «Клиенты» уходит "
                   "в панель, панель делится на три сегмента, маркер-контур отмечает текущий слой, бутон ложится "
                   "в изометрию этажами, уходит в фон под тезис, слои становятся полосами и снова собираются.",
                   S, tags=["seq", "peel", "bud", "card", "3d", "data", "background"], score=4)


def v_seq_onion(theme):
    """Луковица-«швейцарский сыр»: уровни защиты → прорези совпали → угроза проходит → кольца разворачиваются в
    полосы → сортировка по ширине прорези → кольца сворачиваются обратно с разнесёнными прорезями (защищено)."""
    cx, cy = 8.4, 4.0
    t, gp = 0.36, 0.1
    rings = 5
    names = ["Сеть", "Доступ", "Код", "Данные", "Люди"]
    holes = [34, 22, 46, 28, 16]  # ширина прорези, градусы
    cols = band_cols(theme, rings)
    R = 6.6  # одна большая рамка на оси: и кольца, и полосы внутри неё

    def ring_g(k):
        ri = 0.55 + (rings - 1 - k) * (t + gp)  # k=0 — внешний
        return arc_band(cx, cy, ri, ri + t, -90 + holes[k] / 2, 270 - holes[k] / 2, m=72)

    def lock(rots, fa=1.0):
        return [orbit(f"!!o{k}", ring_g(k), (cx, cy), R, rots[k], fill=cols[k], fa=fa, z=10 + k) for k in range(rings)]

    core = lambda: O("!!core", "oval", cx - 0.42, cy - 0.42, 0.84, 0.84, fill="accent", z=30)  # noqa: E731

    def bars(order, x0=4.4):
        out, labs = [], []
        for pos, k in enumerate(order):
            y = 1.9 + pos * 0.8
            ri = 0.55 + (rings - 1 - k) * (t + gp)
            arc_len = 2 * math.pi * (ri + t / 2) * (360 - holes[k]) / 360
            L = arc_len * 0.5
            hole = 2 * math.pi * (ri + t / 2) * holes[k] / 360 * 0.5
            # торец полосы — место прорези (полоса короче на ширину прорези)
            out.append(orbit(f"!!o{k}", bar_band(x0 + hole, y, L, 0.45, m=72), (cx, cy), R, 0, fill=cols[k], z=10 + k))
            labs.append((k, y, x0 + hole))
        return out, labs

    rnd = [40, -75, 125, -150, 85]
    S = []
    S.append(Slide([head("Пять уровней защиты"), sub("У каждого — своя брешь")] + lock(rnd) + [core()], dur=800))
    arrow = V.shape("thr", arrow_poly(12.6, cy, cx + 0.5, cy), fill="accent", z=40)
    S.append(Slide([head("Бреши совпали"), arrow] + lock([90] * 5) + [core()], dur=900,
                   fx=[Fx("entrance_wipe", "thr", start="at", delay=0.15, dur=0.5, options={"direction": "right"})]))
    b2, l2 = bars(list(range(5)))
    labs2 = [label(f"bn{k}", names[k], 2.3, y + 0.22, w=1.8, sz=16, col="ink2", al="l") for k, y, _ in l2]
    gapm = [O(f"gm{k}", "rect", 4.4, y, x - 4.4, 0.45, fill=None, ln="accent", lw=1.25, dash="dash", z=8) for k, y, x in l2]
    S.append(Slide([head("Каждый уровень отдельно")] + b2 + [core().copy(x=12.0, y=6.0, w=0.01, h=0.01)] + labs2 + gapm, dur=900,
                   fx=[Fx("entrance_fade", l.name, start="at", delay=0.1 + 0.04 * i, dur=0.25) for i, l in enumerate(labs2)]
                   + [Fx("entrance_fade", g.name, start="at", delay=0.3 + 0.04 * i, dur=0.25) for i, g in enumerate(gapm)]))
    order = sorted(range(5), key=lambda k: -holes[k])
    b3, l3 = bars(order)
    labs3 = [label(f"bs{k}", names[k], 2.3, y + 0.22, w=1.8, sz=16, col="accent" if pos == 0 else "ink2", al="l", b=pos == 0)
             for pos, (k, y, _) in enumerate(l3)]
    gap3 = [O(f"gs{k}", "rect", 4.4, y, x - 4.4, 0.45, fill="accent", fa=0.25, ln="accent", lw=1.25, z=8) for k, y, x in l3]
    S.append(Slide([head("Самая широкая брешь — в коде")] + b3 + [core().copy(x=12.0, y=6.0, w=0.01, h=0.01)] + labs3 + gap3, dur=900,
                   fx=[Fx("entrance_fade", l.name, start="at", delay=0.1 + 0.04 * i, dur=0.25) for i, l in enumerate(labs3)]
                   + [Fx("entrance_wipe", g.name, start="at", delay=0.3, dur=0.35, options={"direction": "left"}) for g in gap3]))
    holes_fixed = list(holes)
    holes_fixed[2] = 14
    safe = [10, 82, 154, 226 - 360, 298 - 360]

    def lock2(rots):
        out = []
        for k in range(rings):
            ri = 0.55 + (rings - 1 - k) * (t + gp)
            g = arc_band(cx, cy, ri, ri + t, -90 + holes_fixed[k] / 2, 270 - holes_fixed[k] / 2, m=72)
            out.append(orbit(f"!!o{k}", g, (cx, cy), R, rots[k], fill=cols[k], z=10 + k))
        return out

    S.append(Slide([head("Сужаем брешь в коде")] + lock2([0] * 5) + [core()], dur=900))
    S.append(Slide([head("Разносим бреши")] + lock2(safe) + [core()], dur=900))
    shield = O("rip", "oval", cx - 2.95, cy - 2.95, 5.9, 5.9, fill=None, ln="accent", lw=2, z=5)
    S.append(Slide([head("Ядро защищено"), label("ok", "Ни одного сквозного пути", 3.0, 6.1, w=4.6, sz=18, col="accent", b=True)]
                   + lock2([s + 40 for s in safe[:3]] + [s + 40 for s in safe[3:]]) + [core(), shield], dur=800,
                   loops=[], fx=[Fx("entrance_faded_zoom", "rip", start="at", delay=0.1, dur=0.4), Fx("entrance_fade", "ok", start="after", dur=0.3)]))
    return Variant("peel", "seq_onion", "Кольца защиты через раздел",
                   "Луковица из колец с брешами живёт 6 состояний: бреши в разных местах, кольца проворачиваются и "
                   "бреши совпадают — угроза идёт к ядру, кольца разворачиваются в полосы (брешь видна как недостающий "
                   "конец), полосы сортируются по ширине бреши, кольца сворачиваются обратно с узкими разнесёнными "
                   "брешами. Роль: раздел про риски и безопасность.",
                   S, tags=["seq", "peel", "rings", "unroll", "rotate", "data", "risk"], score=4)


def variants(theme) -> list[Variant]:
    return [f(theme) for f in (v_seq_bud, v_seq_onion, v_bud_slide, v_lock_align, v_ring_unroll, v_disk_stack, v_topo,
                               v_petal_detail, v_sheet_peel, v_shell, v_strata, v_lens_fan, v_iso_cake)]
