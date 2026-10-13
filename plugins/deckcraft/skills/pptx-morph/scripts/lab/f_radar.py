"""Семейство «Радар и полярные диаграммы»: сонар с лучом-петлёй и «кругами на воде», луч открывает столбики
(вход «Колесо» синхронно с лучом), радиальные столбики, санбёрст с проваливанием в сектор, хордовая диаграмма
из лент, профиль-«паутина», роза Найтингейл, мишень приоритетов, тепловой циферблат недели, линия -> полярная
площадь, захват цели.
"""

from __future__ import annotations

import math
import random

from morphkit import Loop, O, Slide
from morphkit import vector as V
from morphkit.presets import Fx
from morphkit.theme import mix

from lab import Variant
from lab._b_util import (arc_band, arc_pieces, arc_pieces_ax, arc_pts, ax, axis, head, pol, shade, text, thin)

FAM = "radar"
C = (9.0, 4.0)


def grid(theme, id, c, R, rings=4, spokes=12, fa=1.0, xf=None):
    """Сетка радара: кольца-контуры и лучи (тонкие формы в общей рамке — переживают наклон)."""
    out = []
    for k in range(1, rings + 1):
        r = R * k / rings
        g = V.resample(V.circle(c[0], c[1], r, seg=16), 64)
        if xf:
            g = V.Polygon([xf(x, y) for x, y in list(g.exterior.coords)[:-1]])
        out.append(ax(f"!!{id}r{k}", g, 0.0, pivot=c, fill=None, ln="line", lw=1.0, la=fa, z=3))
    for j in range(spokes):
        p, q = c, pol(*c, R, -90 + 360 * j / spokes)
        if xf:
            p, q = xf(*p), xf(*q)
        out.append(ax(f"!!{id}s{j}", thin(p, q, 0.012), 0.0, pivot=c, fill="line", fa=fa, z=3))
    return out


def beam(theme, id, c, R, rot=-90.0, span=48, k=8):
    """Луч сонара: k тонких секторов с убывающей непрозрачностью позади ведущей кромки (все на одной оси)."""
    out = []
    for j in range(k):
        a1 = -span * j / k
        a0 = -span * (j + 1) / k
        g = V.sector(c[0], c[1], R, a0, a1 + 0.3, steps=8)
        out.append(axis(f"{id}{j}", g, c, R * 1.001, rot=rot, fill="accent", fa=0.42 * (1 - j / k) ** 1.6 + 0.03, z=5))
    return out


# ----------------------------------------------------------------------------- 1. сонар

def v_sonar(theme) -> Variant:
    R = 2.6
    rnd = random.Random(2)
    blips = [(rnd.uniform(0.7, 2.3), rnd.uniform(0, 360)) for _ in range(6)]
    names = ["Конкурент А", "Новый игрок", "Партнёр", "Ниша", "Регулятор", "Сделка"]

    def state(s, sub):
        objs = head("Сонар рынка", sub)
        objs += grid(theme, "sg", C, R)
        loops = []
        bm = beam(theme, "sb", C, R)
        objs += bm
        loops += [Loop("spin", target=o.name, period=3.2, name="swp") for o in bm]
        for i, (r, a) in enumerate(blips):
            x, y = pol(*C, r, a)
            vis = s >= 1
            hot = s == 2 and i == 1
            d = 0.2 if not hot else 0.3
            objs.append(O(f"!!bp{i}", "oval", x - d / 2, y - d / 2, d, d, fill="accent" if hot else "ink",
                          fa=1.0 if vis else 0.0, z=8))
            if s == 1:
                loops.append(Loop("ripple", target=f"!!bp{i}", period=2.0 + 0.3 * i, scale=2.4, color="accent",
                                  name="blp", start=0.2 * i))
            if hot:
                objs.append(O("lock", "oval", x - 0.45, y - 0.45, 0.9, 0.9, fill=None, ln="accent", lw=2.5, z=9))
                objs.append(text("lockt", x + 0.55, y - 0.25, 2.2, 0.5, names[i], sz=18, b=True, col="accent", va="m"))
        return objs, loops

    sl = []
    for s, (sub, d) in enumerate([("Луч ищет", 700), ("Шесть сигналов", 600), ("Цель — новый игрок", 700)]):
        o, lp = state(s, sub)
        fx = [Fx("entrance_faded_zoom", "lock", start="at", delay=0.1, dur=0.4)] if s == 2 else []
        sl.append(Slide(o, dur=d, loops=lp, fx=fx))
    return Variant(FAM, "sonar", "Сонар: луч, сигналы, захват",
                   "Луч сонара из восьми секторов с убывающей прозрачностью крутится петлёй; появляются сигналы "
                   "с «кругами на воде», один захватывается кольцом и подписывается. Роль: обзор рынка/рисков.",
                   sl, tags=["radar", "loop", "spin", "ripple"], score=4)


# ----------------------------------------------------------------------------- 2. луч открывает столбики

def v_reveal(theme) -> Variant:
    R0, n = 0.8, 24
    rnd = random.Random(6)
    vals = [0.3 + 0.7 * abs(math.sin(i * 0.37 + 0.5)) * rnd.uniform(0.7, 1.0) for i in range(n)]
    P = 3.0

    def state(s, sub):
        objs = head("Луч открывает данные", sub)
        objs += grid(theme, "rg", C, 2.7, rings=3, spokes=0)
        bars = []
        for i in range(n):
            a = -90 + 360 * i / n
            g = arc_band(C[0], C[1], R0, R0 + 1.85 * vals[i], 1.5, 360 / n - 1.5, 8)
            nm = f"rb{i}" if s == 1 else f"!!rb{i}"
            objs.append(axis(nm, g, C, 2.75, rot=a, fill="accent" if vals[i] > 0.85 else shade(theme, "ink", 0.35),
                             fa=1.0 if s == 1 else 0.0, z=6))
            bars.append(nm)
        loops, fx = [], []
        if s == 1:
            bm = beam(theme, "rbm", C, 2.75, rot=-90)
            objs += bm
            loops = [Loop("spin", target=o.name, period=P, name="rsw") for o in bm]
            fx = [Fx("entrance_wheel", nm, start="at", delay=0.0, dur=P, options={"amount": "1"}) for nm in bars]
            objs.append(text("rtx", 0.7, 3.3, 4.0, 1.0, ["Каждый луч —", "час суток"], sz=18, col="ink2"))
        return objs, loops, fx

    sl = []
    for s, (sub, d) in enumerate([("Пусто", 600), ("Луч проходит — данные проявляются", 600)]):
        o, lp, fx = state(s, sub)
        sl.append(Slide(o, dur=d, loops=lp, fx=fx))
    return Variant(FAM, "reveal", "Луч радара открывает столбики",
                   "Столбики на оси центра получают вход «Колесо» длительностью ровно в один оборот луча — каждый "
                   "проявляется в тот момент, когда над ним проходит луч-петля. Роль: эффектное появление "
                   "радиальной диаграммы внутри слайда (без служебных слайдов).",
                   sl, tags=["radar", "reveal", "wheel", "loop", "data"], score=4)


# ----------------------------------------------------------------------------- 3. радиальные столбики

def v_radial(theme) -> Variant:
    mn = ["Я", "Ф", "М", "А", "М", "И", "И", "А", "С", "О", "Н", "Д"]
    d = [[0.4, 0.45, 0.6, 0.7, 0.8, 0.95, 1.0, 0.9, 0.7, 0.55, 0.45, 0.5],
         [0.55, 0.6, 0.7, 0.8, 0.85, 0.8, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]]
    R0 = 0.9

    def state(s, sub):
        objs = head("Радиальные столбики", sub)
        objs += grid(theme, "qg", C, 2.75, rings=3, spokes=0)
        v = d[min(s, 1)]
        for i in range(12):
            g = arc_band(C[0], C[1], R0, R0 + 1.8 * v[i], 3, 27, 10)
            top = v[i] >= max(v) - 1e-9
            objs.append(axis(f"!!qb{i}", g, C, 2.75, rot=-90 + 30 * i, fill="accent" if top or s == 2 else
                             shade(theme, "ink", 0.35), z=6))
            x, y = pol(*C, R0 - 0.25, -90 + 30 * i + 15)
            objs.append(text(f"!!qm{i}", x - 0.2, y - 0.16, 0.4, 0.32, mn[i], sz=12, col="muted", al="c", va="m"))
        objs.append(text(f"qy{min(s, 1)}", 0.7, 3.3, 3.5, 0.8, ["2024", "2025"][min(s, 1)], sz=40, b=True, col="ink",
                         font="head"))
        return objs

    return Variant(FAM, "radial", "Радиальные столбики двух лет",
                   "Двенадцать месяцев лучами; при смене года столбики перерастают по радиусу (перелив только по "
                   "радиусу — точный), максимум подсвечен. Роль: сезонность, сравнение лет.",
                   [Slide(state(0, "Пик — июль"), dur=800), Slide(state(1, "Пик сместился в декабрь"), dur=850),
                    Slide(state(2, "Ровный рост весь год"), dur=600)],
                   tags=["radar", "radial-bars", "data"], score=3)


# ----------------------------------------------------------------------------- 4. санбёрст: проваливание в сектор

SUN = [("Продукт", 40, [("Ядро", 22), ("Мобайл", 12), ("API", 6)]),
       ("Продажи", 30, [("B2B", 18), ("B2C", 12)]),
       ("Сервис", 18, [("Поддержка", 10), ("Внедрение", 8)]),
       ("Прочее", 12, [("HR", 7), ("Офис", 5)])]


def sunburst(theme, id, c, focus=None, xf=None, fa=1.0, r=(0.75, 1.65, 1.75, 2.6), lift=None):
    out = []
    tot = sum(v for _, v, _ in SUN)
    a = -90.0
    cols = ["accent", "ink2", "accent3", "muted"]
    for i, (nm, v, kids) in enumerate(SUN):
        if focus is None:
            span = 360 * v / tot
        else:
            span = 359.0 if i == focus else 0.25
        col = cols[i]
        out += arc_pieces_ax(f"!!{id}c{i}_", c, r[0], r[1], a + 0.6, a + span - 0.6, k=6, xf=xf, fill=col, fa=fa, z=8)
        kt = sum(kv for _, kv in kids)
        b = a
        for j, (kn, kv) in enumerate(kids):
            ks = span * kv / kt
            kc = mix(theme.c(col), theme.c("bg"), 0.25 + 0.2 * j)
            out += arc_pieces_ax(f"!!{id}k{i}_{j}_", c, r[2], r[3], b + 0.6, b + ks - 0.6, k=4, xf=xf, fill=kc, fa=fa,
                                 z=8)
            b += ks
        a += span
    return out


def v_sunburst(theme) -> Variant:
    def labels(focus):
        out = []
        tot = sum(v for _, v, _ in SUN)
        if focus is None:
            a = -90.0
            for i, (nm, v, _) in enumerate(SUN):
                span = 360 * v / tot
                x, y = pol(*C, 3.05, a + span / 2)
                out.append(text(f"!!ul{i}", x - 0.8, y - 0.2, 1.6, 0.4, nm, sz=14, col="ink2", al="c", va="m"))
                a += span
        else:
            nm, v, kids = SUN[focus]
            kt = sum(kv for _, kv in kids)
            b = -90.0
            for j, (kn, kv) in enumerate(kids):
                ks = 359 * kv / kt
                x, y = pol(*C, 3.05, b + ks / 2)
                out.append(text(f"uk{j}", x - 0.9, y - 0.2, 1.8, 0.4, f"{kn} · {kv}%", sz=14, col="ink", al="c", va="m"))
                b += ks
            out.append(text("uc", C[0] - 0.7, C[1] - 0.25, 1.4, 0.5, nm, sz=16, b=True, col="ink", al="c", va="m"))
        return out

    return Variant(FAM, "sunburst", "Санбёрст: проваливаемся в сектор",
                   "Два кольца (направления и их части); выбранное направление разворачивается на весь круг, его "
                   "части — на внешнее кольцо, остальные схлопываются. Кусочки дуг едут по окружности, без клиньев. "
                   "Роль: структура бюджета/выручки с переходом к детали.",
                   [Slide(head("Структура затрат", "Направления и их части") + sunburst(theme, "sb", C) + labels(None),
                          dur=800),
                    Slide(head("Внутри продукта", "40% затрат") + sunburst(theme, "sb", C, focus=0) + labels(0), dur=900),
                    Slide(head("Структура затрат", "Назад к целому") + sunburst(theme, "sb", C) + labels(None),
                          dur=900)],
                   tags=["radar", "sunburst", "drill-down", "data"], score=4)


# ----------------------------------------------------------------------------- 5. хордовая диаграмма

def ribbon_chord(c, R, a0, a1, b0, b1, n=14, m=18):
    """Лента между дугами [a0,a1] и [b0,b1] круга R: дуга, квадратичная кривая через центр, дуга, кривая назад."""
    def bez(p, q):
        return [((1 - t) ** 2 * p[0] + 2 * (1 - t) * t * c[0] + t * t * q[0],
                 (1 - t) ** 2 * p[1] + 2 * (1 - t) * t * c[1] + t * t * q[1]) for t in [k / (m - 1) for k in range(m)]]
    A = arc_pts(c[0], c[1], R, a0, a1, n)
    B = arc_pts(c[0], c[1], R, b0, b1, n)
    pts = A + bez(A[-1], B[0])[1:-1] + B + bez(B[-1], A[0])[1:-1]
    return V.Polygon(pts)


def v_chord(theme) -> Variant:
    names = ["Сайт", "Магазин", "Маркетплейс", "Соцсети", "Партнёры"]
    cols = ["accent", "ink2", "accent3", "muted", "ink"]
    mats = [[[0, 5, 3, 2, 1], [5, 0, 2, 1, 2], [3, 2, 0, 4, 1], [2, 1, 4, 0, 1], [1, 2, 1, 1, 0]],
            [[0, 3, 6, 4, 1], [3, 0, 2, 1, 1], [6, 2, 0, 5, 2], [4, 1, 5, 0, 1], [1, 1, 2, 1, 0]]]
    R, gap = 2.45, 3.0

    def state(s, sub):
        mat = mats[0 if s == 0 else 1]
        objs = head("Потоки клиентов", sub)
        tot = sum(sum(r) for r in mat)
        avail = 360 - gap * 5
        a = -90.0
        start = {}
        for i in range(5):
            span = avail * sum(mat[i]) / tot
            objs += arc_pieces(f"!!cg{i}_", C, R, R + 0.22, a, a + span, k=5, R=R + 0.25, fill=cols[i], z=8)
            x, y = pol(*C, R + 0.6, a + span / 2)
            al = "l" if x > C[0] + 0.3 else ("r" if x < C[0] - 0.3 else "c")
            bx = x if al == "l" else (x - 2.0 if al == "r" else x - 1.0)
            objs.append(text(f"!!cn{i}", bx, y - 0.2, 2.0, 0.4, names[i], sz=14, col="ink2", al=al, va="m"))
            start[i] = a
            a += span + gap
        cur = dict(start)
        seg = {}
        for i in range(5):
            for j in range(5):
                if i == j:
                    continue
                w = avail * mat[i][j] / tot
                seg[(i, j)] = (cur[i], cur[i] + w)
                cur[i] += w
        k = 0
        for i in range(5):
            for j in range(i + 1, 5):
                a0, a1 = seg[(i, j)]
                b0, b1 = seg[(j, i)]
                hl = s == 2 and 2 in (i, j)
                fa = 0.55 if s < 2 else (0.75 if hl else 0.12)
                g = ribbon_chord(C, R - 0.02, a0, a1, b0, b1)
                objs.append(ax(f"!!cr{k}", g, 0.0, pivot=C, fill=cols[i] if not hl else "accent", fa=fa, z=6))
                k += 1
        return objs

    return Variant(FAM, "chord", "Хордовая диаграмма: ленты потоков",
                   "Пять каналов на круге, ленты между ними — переходы клиентов (ширина = поток). При смене года "
                   "дуги и ленты перетекают, затем подсвечиваются связи одного канала. Роль: откуда и куда идут "
                   "клиенты, омниканальность.",
                   [Slide(state(0, "Прошлый год"), dur=800), Slide(state(1, "Этот год"), dur=900),
                    Slide(state(2, "Всё идёт через маркетплейс"), dur=600)],
                   tags=["radar", "chord", "ribbons", "data"], score=4)


# ----------------------------------------------------------------------------- 6. профиль-паутина

def spider_poly(c, R, vals, per=4):
    n = len(vals)
    pts = []
    for i in range(n):
        p = pol(*c, R * vals[i], -90 + 360 * i / n)
        q = pol(*c, R * vals[(i + 1) % n], -90 + 360 * (i + 1) / n)
        pts += [(p[0] + (q[0] - p[0]) * k / per, p[1] + (q[1] - p[1]) * k / per) for k in range(per)]
    return V.Polygon(pts)


def v_spider(theme) -> Variant:
    axes = ["Цена", "Скорость", "Качество", "Сервис", "Бренд", "Охват"]
    us = [0.6, 0.9, 0.8, 0.85, 0.5, 0.45]
    them = [0.85, 0.5, 0.6, 0.4, 0.9, 0.8]
    R = 2.5

    def state(s, sub):
        objs = head("Профиль против рынка", sub)
        objs += grid(theme, "pg", C, R, rings=4, spokes=6)
        A = us if s != 1 else them
        objs.append(ax("!!pa", spider_poly(C, R, A), 0.0, pivot=C, fill="accent" if s != 1 else "ink2", fa=0.35,
                       ln="accent" if s != 1 else "ink2", lw=2.0, z=8))
        if s == 2:
            objs.append(ax("pb", spider_poly(C, R, them), 0.0, pivot=C, fill=None, ln="ink2", lw=1.5, z=7))
        for i, nm in enumerate(axes):
            x, y = pol(*C, R + 0.45, -90 + 60 * i)
            objs.append(text(f"!!pl{i}", x - 0.8, y - 0.2, 1.6, 0.4, nm, sz=14, col="ink2", al="c", va="m"))
        objs.append(text(f"pw{s}", 0.7, 3.3, 3.9, 0.9, ["Мы", "Лидер рынка", "Мы и лидер"][s], sz=26, b=True,
                         col="accent" if s != 1 else "ink", font="head"))
        return objs

    return Variant(FAM, "spider", "Профиль-«паутина» перетекает",
                   "Многоугольник профиля на шести осях переливается из «мы» в «лидер рынка» и обратно, на третьем "
                   "шаге — оба контура. Роль: сравнение с конкурентом, оценка команды.",
                   [Slide(state(0, "Наши сильные стороны"), dur=800), Slide(state(1, "Лидер — в цене и бренде"), dur=850),
                    Slide(state(2, "Где мы впереди"), dur=800)],
                   tags=["radar", "spider", "shape-morph", "data"], score=4)


# ----------------------------------------------------------------------------- 7. роза Найтингейл

def v_coxcomb(theme) -> Variant:
    mn = ["Я", "Ф", "М", "А", "М", "И", "И", "А", "С", "О", "Н", "Д"]
    v1 = [0.5, 0.45, 0.6, 0.75, 0.9, 1.0, 0.95, 0.85, 0.7, 0.6, 0.55, 0.65]
    v2 = [0.7, 0.75, 0.8, 0.7, 0.6, 0.55, 0.5, 0.6, 0.8, 0.9, 1.0, 0.95]

    def state(s, sub):
        objs = head("Роза ветров продаж", sub)
        v = v1 if s == 0 else v2
        for i in range(12):
            r = 0.4 + 2.2 * math.sqrt(v[i])
            g = V.sector(C[0], C[1], r, 0.8, 29.2, steps=14)
            g = V.Polygon(list(g.exterior.coords)[:-1])
            col = mix(theme.c("accent"), theme.c("surface2"), 1 - v[i])
            objs.append(axis(f"!!xc{i}", V.resample(g, 40, start=0), C, 2.65, rot=-90 + 30 * i, fill=col, ln="bg",
                             lw=1.0, z=6))
            x, y = pol(*C, 2.95, -90 + 30 * i + 15)
            objs.append(text(f"!!xm{i}", x - 0.2, y - 0.16, 0.4, 0.32, mn[i], sz=12, col="muted", al="c", va="m"))
        return objs

    return Variant(FAM, "coxcomb", "Роза Найтингейл: сектора-месяцы",
                   "Площадь сектора — продажи месяца; при смене продукта сектора перерастают и перекрашиваются, "
                   "летний «парус» сменяется зимним. Роль: сезонность двух продуктов.",
                   [Slide(state(0, "Летний продукт"), dur=800), Slide(state(1, "Зимний продукт"), dur=900)],
                   tags=["radar", "coxcomb", "data"], score=3)


# ----------------------------------------------------------------------------- 8. мишень приоритетов

def v_target(theme) -> Variant:
    rnd = random.Random(12)
    items = [(rnd.choice([1, 2, 3, 4]), rnd.uniform(0, 360)) for _ in range(16)]
    new = [max(1, p - 2) if k in (2, 5, 11) else min(4, p + 1) if k % 3 == 0 else p for k, (p, _) in enumerate(items)]
    R = 2.6

    def state(s, sub):
        objs = head("Мишень приоритетов", sub)
        for k in range(4, 0, -1):
            r = R * k / 4
            objs.append(O(f"!!tr{k}", "oval", C[0] - r, C[1] - r, 2 * r, 2 * r, fill=shade(theme, "ink", 0.9 - 0.06 * (4 - k)),
                          ln="line", lw=1.0, z=3 + (4 - k)))
        for k, (p, a) in enumerate(items):
            pr = p if s == 0 else new[k]
            r = R * (pr - 0.5) / 4
            x, y = pol(*C, r, a)
            hot = s >= 1 and k in (2, 5, 11)
            objs.append(O(f"!!ti{k}", "oval", x - 0.12, y - 0.12, 0.24, 0.24, fill="accent" if hot else "ink2", z=10))
        objs.append(text("!!tl", 0.7, 3.3, 4.0, 1.0, ["Центр — делаем сейчас", "Край — потом"], sz=15, col="ink2"))
        return objs

    return Variant(FAM, "target", "Мишень: приоритеты едут к центру",
                   "16 инициатив на кольцах приоритета; после пересмотра три подсвеченные съезжают к центру, "
                   "часть уходит к краю (движение строго по радиусу). Роль: пересмотр планов, фокус квартала.",
                   [Slide(state(0, "Было"), dur=800), Slide(state(1, "Стало: три — в фокус"), dur=900)],
                   tags=["radar", "target", "priority"], score=3)


# ----------------------------------------------------------------------------- 9. тепловой циферблат недели

def v_heatclock(theme) -> Variant:
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    def val(d, h, s):
        base = math.exp(-((h - (13 if s == 0 else 19)) / 4.0) ** 2)
        wk = 1.0 if d < 5 else (0.4 if s == 0 else 1.2)
        return min(1.0, base * wk + 0.08 * ((d * 7 + h * 3) % 5) / 5)

    def state(s, sub):
        objs = head("Неделя по часам", sub)
        for d in range(7):
            r0 = 0.85 + d * 0.27
            for h in range(24):
                g = arc_band(C[0], C[1], r0, r0 + 0.24, 0.6, 14.4, 4)
                col = mix(theme.c("surface2"), theme.c("accent"), val(d, h, s))
                objs.append(axis(f"!!hc{d}_{h}", g, C, 2.8, rot=-90 + 15 * h, fill=col, z=6))
        for h in (0, 6, 12, 18):
            x, y = pol(*C, 3.1, -90 + 15 * h)
            objs.append(text(f"!!hh{h}", x - 0.35, y - 0.17, 0.7, 0.34, f"{h:02d}:00", sz=12, col="muted", al="c",
                             va="m"))
        objs.append(text("!!hd", 0.7, 3.3, 4.2, 0.9, ["Кольцо — день недели", "(Пн внутри, Вс снаружи)"], sz=14,
                         col="ink2"))
        return objs

    return Variant(FAM, "heatclock", "Тепловой циферблат недели",
                   "168 ячеек: кольцо — день, сектор — час, цвет — нагрузка; при смене периода пятно смещается "
                   "с обеда на вечер и на выходные. Роль: расписание, нагрузка поддержки, «когда звонят».",
                   [Slide(state(0, "До запуска: днём, в будни"), dur=800),
                    Slide(state(1, "После: вечером и в выходные"), dur=900)],
                   tags=["radar", "heatmap", "time", "data"], score=3)


# ----------------------------------------------------------------------------- 10. линия -> полярная площадь

def v_wrap(theme) -> Variant:
    n = 24
    vals = [0.2 + 0.8 * math.exp(-((h - 19) / 3.5) ** 2) + 0.25 * math.exp(-((h - 9) / 2.0) ** 2) for h in range(n)]
    x0, x1, yb = 1.2, 12.2, 6.2
    r0, k = 0.7, 1.9

    def pts(s):
        top, base = [], []
        for h in range(n + 1):
            v = vals[h % n]
            if s == 0:
                x = x0 + (x1 - x0) * h / n
                top.append((x, yb - 3.0 * v))
                base.append((x, yb))
            else:
                a = -90 + 360 * h / n
                top.append(pol(*C, r0 + k * v, a))
                base.append(pol(*C, r0, a))
        return top, base

    def state(s, sub):
        objs = head("День по кругу", sub)
        top, base = pts(s)
        objs.append(ax("!!wa", V.Polygon(top + base[::-1]), 0.0, pivot=C, fill="accent", fa=0.3, ln="accent", lw=2.0,
                       z=6))
        for h in range(0, n, 6):
            x, y = (x0 + (x1 - x0) * h / n, yb + 0.15) if s == 0 else pol(*C, r0 + k * 1.1 + 0.25, -90 + 15 * h)
            objs.append(text(f"!!wh{h}", x - 0.4, y - (0 if s == 0 else 0.17), 0.8, 0.34, f"{h:02d}:00", sz=12,
                             col="muted", al="c", va="t" if s == 0 else "m"))
        return objs

    return Variant(FAM, "wrap", "Линия суток сворачивается в круг",
                   "Площадь под графиком нагрузки за сутки сворачивается в полярную: полночь встречается с "
                   "полночью, видно, что вечерний пик переходит в ночной хвост. Роль: цикличные данные — сутки, неделя, год.",
                   [Slide(state(0, "Сутки по прямой"), dur=800), Slide(state(1, "Сутки по кругу"), dur=900)],
                   tags=["radar", "wrap", "shape-morph", "data"], score=3)


# ----------------------------------------------------------------------------- ЖИВАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ 1: радар возможностей

def seq_radar(theme) -> Variant:
    """8 состояний: луч ищет -> сигналы -> захват -> сигнал раскрывается в панель -> сигналы становятся
    радиальными столбиками -> столбики встают в рейтинг -> башни на наклонённом диске -> всё уходит на фон."""
    c, R = (9.0, 4.0), 2.6
    rnd = random.Random(21)
    opp = [("Экспорт", 0.9), ("B2B", 0.75), ("Подписка", 0.6), ("Маркетплейс", 0.85), ("Офлайн", 0.3),
           ("Партнёры", 0.5), ("API", 0.65), ("Франшиза", 0.25)]
    pos = [(rnd.uniform(1.0, 2.3), -90 + 45 * i + rnd.uniform(-12, 12)) for i in range(8)]
    order = sorted(range(8), key=lambda i: -opp[i][1])
    K = 0.4
    hot = 3

    def xf_for(st):
        if st == 6:
            return lambda x, y: (x, c[1] + 0.4 + (y - c[1]) * K)
        if st == 7:
            return lambda x, y: (c[0] + 1.6 + (x - c[0]) * 0.65, c[1] - 1.0 + (y - c[1]) * K * 0.65)
        return None

    heads = [("Радар возможностей", "Луч ищет"), ("Восемь сигналов", "Где есть спрос"), ("Захват", "Цель найдена"),
             ("Маркетплейс крупно", "Сигнал раскрывается"), ("Сила сигнала", "Точки стали лучами"),
             ("Рейтинг", "Лучи выстроились"), ("Карта в объёме", "Башни на диске"), ("Решение", "Радар уходит на фон")]
    slides = []
    for st in range(8):
        xf = xf_for(st)
        f = xf or (lambda x, y: (x, y))
        objs = head(*heads[st])
        gfa = 0.0 if st == 5 else (0.4 if st == 7 else 1.0)
        objs += grid(theme, "zg", c, R, rings=4, spokes=8, fa=gfa, xf=xf)
        loops, fx = [], []
        if st in (0, 1, 2):
            bm = beam(theme, "zb", c, R)
            objs += bm
            loops += [Loop("spin", target=o.name, period=3.2, name="zsw") for o in bm]
        for i, ((nm, v), (r, a)) in enumerate(zip(opp, pos)):
            x, y = pol(*c, r, a)
            col = "accent" if (i == hot and st >= 2) else "ink"
            fa = 0.0 if st == 0 else 1.0
            if st in (0, 1, 2):
                g = V.resample(V.circle(x, y, 0.1 if not (st == 2 and i == hot) else 0.15, seg=8), 24)
            elif st == 3:
                if i == hot:
                    g, col = V.resample(V.rect(0.7, 2.45, 4.4, 3.4), 24), "surface"
                else:
                    g, col = V.resample(V.circle(x, y, 0.1, seg=8), 24), shade(theme, "ink", 0.5)
            elif st == 4:
                p0, p1 = pol(*c, 0.45, a), pol(*c, 0.45 + 2.1 * v, a)
                g = V.resample(thin(p0, p1, 0.2), 24, start=a + 180)
            elif st == 5:
                k = order.index(i)
                h = 3.2 * v
                g = V.resample(V.rect(4.4 + k * 1.0, 6.2 - h, 0.6, h), 24, start=90)
            else:
                bx, by = f(*pol(*c, r, a))
                h = 1.8 * v * (1.0 if st == 6 else 0.65)
                w = 0.32 * (1.0 if st == 6 else 0.65)
                g = V.resample(V.rect(bx - w / 2, by - h, w, h), 24, start=90)
                fa = 1.0 if st == 6 else 0.5
            zz = 10
            if st in (6, 7):
                zz = 10 + int(10 * (math.sin(math.radians(a)) + 1))
            objs.append(ax(f"!!zp{i}", g, 0.0, pivot=c, fill=col, fa=fa, ln="accent" if (st == 3 and i == hot) else None,
                           lw=2.0 if (st == 3 and i == hot) else 0, z=30 if (st == 3 and i == hot) else zz))
            if st == 1:
                loops.append(Loop("ripple", target=f"!!zp{i}", period=2.2 + 0.25 * i, scale=2.6, color="accent",
                                  name="zrp", start=0.12 * i))
            if st == 5:
                k = order.index(i)
                objs.append(text(f"zl{i}", 4.4 + k * 1.0 - 0.5, 6.25 + (k % 2) * 0.3, 1.6, 0.3, nm, sz=12,
                                 col="accent" if i == hot else "ink2", al="c"))
        if st == 2:
            x, y = pol(*c, *pos[hot])
            objs.append(O("zlock", "oval", x - 0.45, y - 0.45, 0.9, 0.9, fill=None, ln="accent", lw=2.5, z=12))
            objs.append(text("zlt", x + 0.55, y - 0.25, 2.6, 0.5, opp[hot][0], sz=18, b=True, col="accent", va="m"))
            fx = [Fx("entrance_faded_zoom", "zlock", start="at", delay=0.1, dur=0.35)]
        if st == 3:
            objs.append(text("zp1", 1.0, 2.75, 3.9, 0.7, "Маркетплейс", sz=28, b=True, col="accent", font="head"))
            objs.append(text("zp2", 1.0, 3.6, 3.9, 1.6, ["Спрос растёт 40% в год", "Вход — 2 месяца", "Риск — комиссия"],
                             sz=16, col="ink"))
            fx = [Fx("entrance_fade", "zp1", start="at", delay=0.1, dur=0.3), Fx("entrance_fade", "zp2", start="after",
                                                                                   dur=0.3)]
        if st == 7:
            objs.append(text("zfin", 0.7, 4.3, 6.4, 1.5, ["Идём в экспорт", "и маркетплейс"], sz=38, b=True, col="ink",
                             font="head"))
        slides.append(Slide(objs, dur=[700, 700, 700, 850, 900, 900, 900, 850][st], loops=loops, fx=fx))
    return Variant(FAM, "seq_radar", "Живой радар возможностей (8 состояний)",
                   "Луч-петля ищет, появляются сигналы с кругами на воде, один захватывается и раскрывается в панель "
                   "с фактами, затем все сигналы становятся лучами-столбиками по силе, выстраиваются в рейтинг, встают "
                   "башнями на наклонённом диске радара и уходят на фон под решение. Роль: разведка рынка в разделе.",
                   slides, tags=["seq", "radar", "loop", "magnifier", "chart", "3d", "background"], score=5)


# ----------------------------------------------------------------------------- ЖИВАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ 2: санбёрст бюджета

def seq_budget(theme) -> Variant:
    """7 состояний: внутреннее кольцо -> вырастает внешнее -> провал в «Продукт» -> лупа на «Ядро» -> лупа едет к
    «Мобайл» -> назад к целому и наклон в объём (ступени колец) -> уходит на фон."""
    c = (9.0, 4.0)
    K = 0.45
    heads = [("Бюджет", "Четыре направления"), ("Бюджет", "И их части"), ("Внутри продукта", "40% бюджета"),
             ("Ядро", "Больше половины продукта"), ("Мобайл", "Растёт быстрее всех"), ("Снова целое", "Назад к бюджету"), ("Бюджет в объёме", "Слои"),
             ("Бюджет-2026", "Структура уходит на фон")]
    kids0 = SUN[0][2]
    kt = sum(v for _, v in kids0)
    slides = []
    for st in range(8):
        objs = head(*heads[st])
        focus = 0 if st in (2, 3, 4) else None
        xf = None
        if st == 6:
            xf = lambda x, y: (x, c[1] + (y - c[1]) * K)  # noqa: E731
        if st == 7:
            xf = lambda x, y: (c[0] + 1.6 + (x - c[0]) * 0.6, c[1] - 1.0 + (y - c[1]) * K * 0.6)  # noqa: E731
        r = (0.75, 1.65, 1.75, 2.6) if st else (0.75, 1.65, 1.66, 1.67)
        fa = 0.4 if st == 7 else 1.0
        parts = sunburst(theme, "bb", c, focus=focus, xf=xf, fa=fa, r=r)
        if st in (6, 7):  # внешнее кольцо — ступенькой ниже
            dy = 0.32 if st == 6 else 0.2
            parts = [o if "k" not in o.name[4:6] else o for o in parts]
            parts2 = []
            for o in parts:
                if o.name.startswith("!!bbk"):
                    parts2.append(o.copy(y=o.y + dy))
                else:
                    parts2.append(o)
            parts = parts2
        objs += parts
        if st in (3, 4):
            j = 0 if st == 3 else 1
            b = -90 + 359 * sum(v for _, v in kids0[:j]) / kt
            ks = 359 * kids0[j][1] / kt
            g = arc_band(c[0], c[1], 1.6, 2.85, b - 1.5, b + ks + 1.5, 24)
            objs.append(ax("!!blens", g, b, pivot=c, fill=None, ln="accent", lw=3.0, z=20))
            x, y = pol(*c, 3.3, b + ks / 2)
            objs.append(text(f"bv{st}", x - 1.0, y - 0.3, 2.0, 0.6, f"{kids0[j][1]}% бюджета", sz=18, b=True,
                             col="accent", al="c", va="m"))
        if st == 7:
            objs.append(text("bfin", 0.7, 4.3, 6.2, 1.5, ["Продукт — 40%,", "из них ядро — 22%"], sz=34, b=True,
                             col="ink", font="head"))
        fx = []
        if st == 0:
            fx = [Fx("entrance_wheel", o.name, start="at", delay=0.1, dur=0.8, options={"amount": "1"})
                  for o in objs if o.name.startswith("!!bbc")][:24]
        slides.append(Slide(objs, dur=[800, 850, 900, 800, 850, 900, 900, 850][st], fx=fx))
    return Variant(FAM, "seq_budget", "Живой санбёрст бюджета (8 состояний)",
                   "Внутреннее кольцо направлений, из него вырастает внешнее кольцо частей, выбранное направление "
                   "разворачивается на весь круг, лупа-дуга встаёт на часть и едет к следующей, затем круг "
                   "возвращается к целому, ложится ступенчатым объёмом и уходит на фон под вывод. "
                   "Роль: разбор бюджета через несколько слайдов одной фигурой.",
                   slides, tags=["seq", "radar", "sunburst", "drill-down", "magnifier", "3d"], score=4)


def variants(theme) -> list[Variant]:
    return [v_sonar(theme), v_reveal(theme), v_radial(theme), v_sunburst(theme), v_chord(theme), v_spider(theme),
            v_coxcomb(theme), v_target(theme), v_heatclock(theme), v_wrap(theme), seq_radar(theme),
            seq_budget(theme)]
