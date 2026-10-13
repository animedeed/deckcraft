"""Данные: одни и те же именованные метки переходят между типами диаграмм — столбики ↔ секторы ↔ кольцо ↔
100 %-полоса ↔ treemap ↔ объёмный пирог; единицы-квадратики ↔ вафля ↔ точки; полоса точек ↔ beeswarm ↔
гистограмма; санкей-ленты ↔ полоса; одна диаграмма ↔ малые множители; столбики ↔ радиальные столбики;
наклонный график рангов.

Числа условные, по форме открытого набора UCI Wine Quality: баллы экспертов в train (5 — 1490, 6 — 2010, 7 — 760, прочие — 288),
разбиение 4548/975/974, train по типу 1100/3448, важность признаков (без чисел на слайде). Тема прогона — ledger.
"""

from __future__ import annotations

import math
import random

from morphkit import Fx, O
from morphkit import vector as V
from morphkit.theme import SLIDE_H, SLIDE_W, mix

from lab import Variant
from lab._d_util import (DEC, S, bezier, body, cyl_grad, dark, head, kicker, label, light, line, raw, ribbon, vs)
from lab.f_wine import importance

FAM = "data"
W, H = SLIDE_W, SLIDE_H
CATS = [("6 баллов", 2010), ("5 баллов", 1490), ("7 баллов", 760), ("3, 4, 8, 9", 288)]
TOT = sum(v for _, v in CATS)
N = 160
ST = 225  # стартовая точка контура — к верхнему левому углу (одинаково у прямоугольника и сектора)


def _v(key, title, idea, slides, tags, score) -> Variant:
    return Variant(FAM, key, title, idea, slides, tags=tags, score=score)


def ccols(theme):
    return [theme.c("accent"), theme.c("accent2"), theme.c("accent3"), theme.c("muted")]


def fmt(v: int) -> str:
    return f"{v:,}".replace(",", " ")


def mark(name, g, col, z=10, **kw):
    """Метка категории: контур уже из согласованных точек (rect_q / sector_q) — без ресемпла."""
    return raw(name, g, fill=col, z=z, ln="bg", lw=1.5, **kw)


NQ = 40  # точек на сторону


def rect_q(x, y, w, h, n=NQ):
    """Прямоугольник из 4n точек: верх (слева направо), правый край, низ (справа налево), левый край."""
    top = [(x + w * i / n, y) for i in range(n)]
    right = [(x + w, y + h * i / n) for i in range(n)]
    bot = [(x + w - w * i / n, y + h) for i in range(n)]
    left = [(x, y + h - h * i / n) for i in range(n)]
    return V.Polygon(top + right + bot + left)


def sector_q(cx, cy, ro, ri, a0, a1, n=NQ, sy=1.0):
    """Сектор кольца из 4n точек в том же порядке, что rect_q: внешняя дуга ↔ верх, край a1 ↔ правый край,
    внутренняя дуга ↔ низ, край a0 ↔ левый. Столбик «сгибается» в сектор без перекручивания."""
    P = lambda r, a: (cx + r * math.cos(math.radians(a)), cy + sy * r * math.sin(math.radians(a)))  # noqa: E731
    outer = [P(ro, a0 + (a1 - a0) * i / n) for i in range(n)]
    right = [P(ro + (ri - ro) * i / n, a1) for i in range(n)]
    inner = [P(ri, a1 - (a1 - a0) * i / n) for i in range(n)]
    left = [P(ri + (ro - ri) * i / n, a0) for i in range(n)]
    return V.Polygon(outer + right + inner + left)


# ----------------------------------------------------------------------------- формы-раскладки

def bars_geo(x0=3.2, y0=1.9, w=8.0, row=1.05, bh=0.62):
    top = max(v for _, v in CATS)
    return [rect_q(x0, y0 + i * row, max(w * v / top, 0.05), bh) for i, (_, v) in enumerate(CATS)]


def pie_geo(c, r, r_in=0.0, a0=-90, sy=1.0, gap=0.0):
    out, a = [], a0
    for _, v in CATS:
        da = 360 * v / TOT
        g = sector_q(c[0], c[1], r, r_in, a, a + da, sy=sy)
        if gap:
            am = math.radians(a + da / 2)
            g = V.move(g, gap * math.cos(am), gap * math.sin(am) * sy)
        out.append(g)
        a += da
    return out


def stack_geo(x0=1.0, y0=3.4, w=11.3, h=1.2):
    out, x = [], x0
    for _, v in CATS:
        ww = w * v / TOT
        out.append(rect_q(x, y0, ww, h))
        x += ww
    return out


def treemap_geo(x0=4.0, y0=1.7, w=8.6, h=4.9):
    """Простая «полосами» раскладка (slice-and-dice в 2 уровня): первая категория — левая колонка, остальные справа."""
    v = [c[1] for c in CATS]
    w0 = w * v[0] / TOT
    out = [rect_q(x0, y0, w0, h)]
    rest = sum(v[1:])
    y = y0
    for k in (1, 2, 3):
        hh = h * v[k] / rest
        out.append(rect_q(x0 + w0, y, w - w0, hh))
        y += hh
    return out


def bars_pie(theme) -> Variant:
    cols = ccols(theme)
    sl = []
    bg = bars_geo()
    o = [head("Баллы экспертов: train", w=8)]
    for i, (g, (nm, v)) in enumerate(zip(bg, CATS)):
        o += [mark(f"!!m{i}", g, cols[i]), label(f"!!ml{i}", 3.0, 1.9 + i * 1.05 + 0.15, nm, w=2.2, al="r", sz=15, b=True),
              label(f"!!mv{i}", 3.3 + 8.0 * v / 2010, 1.9 + i * 1.05 + 0.15, fmt(v), w=1.2, al="l", sz=15, col="ink2")]
    sl.append(S(o, 800))
    pc = (8.6, 4.1)
    o = [head("Доли", w=6)]
    a = -90
    for i, (g, (nm, v)) in enumerate(zip(pie_geo(pc, 2.4), CATS)):
        am = math.radians(a + 180 * v / TOT)
        a += 360 * v / TOT
        lx, ly = pc[0] + 2.75 * math.cos(am), pc[1] + 2.75 * math.sin(am)
        o += [mark(f"!!m{i}", g, cols[i]),
              label(f"!!ml{i}", lx, ly - 0.17, nm, w=1.9, al="l" if math.cos(am) > 0.2 else ("r" if math.cos(am) < -0.2 else "c"), sz=15, b=True),
              label(f"!!mp{i}", lx, ly + 0.17, f"{round(100 * v / TOT)} %", w=1.9, al="l" if math.cos(am) > 0.2 else ("r" if math.cos(am) < -0.2 else "c"),
                    sz=14, col="ink2")]
    sl.append(S(o, 900))
    o = [head("100 % одной полосой", w=8)]
    x = 1.0
    for i, (g, (nm, v)) in enumerate(zip(stack_geo(), CATS)):
        ww = 11.3 * v / TOT
        o += [mark(f"!!m{i}", g, cols[i]), label(f"!!ml{i}", x + ww / 2, 2.85, nm if ww > 1.2 else "прочие", w=max(ww, 1.0), sz=14, b=True),
              label(f"!!mp{i}", x + ww / 2, 4.75, f"{round(100 * v / TOT)} %", w=max(ww, 0.9), sz=14, col="ink2")]
        x += ww
    sl.append(S(o, 900))
    return _v("bars_pie", "Столбики → секторы → полоса 100 %",
              "Четыре метки с постоянными именами переливаются между типами диаграмм (контур 96 точек, старт в одном "
              "углу): столбики со значениями → секторы пирога с долями → одна полоса 100 %. Подписи категорий едут за "
              "своими метками, числа — новые объекты. Реальные баллы train.",
              sl, ["data", "shape-morph", "chart-morph"], 4)


def waffle(theme) -> Variant:
    cols = ccols(theme)
    units = []
    for k, (_, v) in enumerate(CATS):
        units += [k] * round(100 * v / TOT)
    units = units[:100] + [3] * (100 - len(units))
    sl = []
    s = 0.36
    # 1: столбцы из квадратиков (по 5 в ряд, снизу вверх)
    o = [head("100 квадратиков = train", w=8), body("!!b", 0.7, 1.4, 6, 0.4, "один квадратик ≈ 46 образцов", sz=15, col="muted")]
    cnt = [0] * 4
    for i, k in enumerate(units):
        j = cnt[k]
        cnt[k] += 1
        x = 2.0 + k * 2.6 + (j % 5) * s
        y = 6.4 - (j // 5) * s
        o.append(O(f"!!u{i}", "rect", x, y - s + 0.04, s - 0.05, s - 0.05, fill=cols[k], z=10))
    o += [label(f"!!ul{k}", 2.0 + k * 2.6 + 0.9, 6.45, CATS[k][0], w=2.2, sz=13, b=True) for k in range(4)]
    sl.append(S(o, 800))
    # 2: вафля 10×10
    o = [head("Вафля 10 × 10", w=8), body("!!b", 0.7, 1.4, 6, 0.4, "доли видны сразу", sz=15, col="muted")]
    for i, k in enumerate(units):
        x = 6.8 + (i % 10) * 0.48
        y = 1.6 + (i // 10) * 0.48
        o.append(O(f"!!u{i}", "rect", x, y, 0.42, 0.42, fill=cols[k], z=10))
    o += [label(f"!!ul{k}", 6.6, 2.0 + k * 0.6, CATS[k][0], w=2.4, al="r", sz=13, b=True, col=["accent", "accent2", "accent3", "muted"][k])
          for k in range(4)]
    sl.append(S(o, 900))
    # 3: точки на оси — квадратики становятся кружками-точками в рядах категорий
    o = [head("Те же единицы — точками", w=8)]
    cnt = [0] * 4
    rnd = random.Random(2)
    for i, k in enumerate(units):
        j = cnt[k]
        cnt[k] += 1
        x = 3.2 + j * 0.2 + rnd.uniform(-0.03, 0.03)
        y = 2.2 + k * 1.15 + ((j % 3) - 1) * 0.16
        o.append(O(f"!!u{i}", "oval", x, y, 0.16, 0.16, fill=cols[k], z=10))
    o += [label(f"!!ul{k}", 3.0, 2.12 + k * 1.15, CATS[k][0], w=2.2, al="r", sz=13, b=True) for k in range(4)]
    sl.append(S(o, 900))
    return _v("waffle", "Квадратики: столбцы → вафля → точки",
              "Единичные метки (100 штук ≈ по 46 образцов): столбцы-штабели → вафля 10×10 → ряды точек. Каждая "
              "единица — свой объект, поэтому Morph перекладывает их поштучно — видно, что это те же данные.",
              sl, ["data", "units", "waffle", "carrier"], 4)


def beeswarm(theme) -> Variant:
    rnd = random.Random(11)
    vals = sorted(rnd.gauss(0, 1) for _ in range(64))
    x0, x1 = 1.6, 11.8
    def X(v):
        return x0 + (v + 3) / 6 * (x1 - x0)
    sl = []
    # 1 полоса
    o = [head("Ошибки прогноза: полоса", w=8), line("ax", (x0, 4.4), (x1, 4.4), ln="line", lw=1.0)]
    for i, v in enumerate(vals):
        o.append(O(f"!!p{i}", "oval", X(v) - 0.09, 4.31, 0.18, 0.18, fill="accent", fa=0.55, z=10))
    sl.append(S(o, 700))
    # 2 beeswarm — раздвинуть по вертикали без наложений
    placed = []
    pos = []
    for v in vals:
        x = X(v)
        k = 0
        while True:
            y = 4.4 + ((k + 1) // 2) * 0.2 * (1 if k % 2 else -1)
            if all(math.hypot(x - px, y - py) >= 0.19 for px, py in placed):
                break
            k += 1
        placed.append((x, y))
        pos.append((x, y))
    o = [head("Рой: плотность видна", w=8), line("ax", (x0, 4.4), (x1, 4.4), ln="line", lw=1.0)]
    for i, (x, y) in enumerate(pos):
        o.append(O(f"!!p{i}", "oval", x - 0.09, y - 0.09, 0.18, 0.18, fill="accent", z=10))
    sl.append(S(o, 900))
    # 3 гистограмма-штабели
    o = [head("Гистограмма из тех же точек", w=8), line("ax", (x0, 6.3), (x1, 6.3), ln="line", lw=1.0)]
    cnt = {}
    for i, v in enumerate(vals):
        b = int((v + 3) // 0.5)
        c = cnt.get(b, 0)
        cnt[b] = c + 1
        x = x0 + (b + 0.5) * 0.5 / 6 * (x1 - x0)
        o.append(O(f"!!p{i}", "oval", x - 0.09 + (c % 2) * 0.2 - 0.1, 6.3 - 0.2 - (c // 2) * 0.2, 0.18, 0.18, fill="accent", z=10))
    sl.append(S(o, 900))
    return _v("beeswarm", "Полоса точек → рой → гистограмма",
              "64 наблюдения (условное распределение ошибок): точки на одной линии слипаются, рой раздвигает их без "
              "наложений, затем они складываются в штабели-гистограмму. Объяснение «что такое распределение».",
              sl, ["data", "dots", "distribution"], 4)


def _band(p0a, p0b, p1a, p1b, n=40):  # 40 — как у полосы на шаге 3 (пара Morph)
    """Лента санкея между вертикальными отрезками (p0a..p0b) и (p1a..p1b): верх и низ — кривые Безье, явные точки."""
    mx = (p0a[0] + p1a[0]) / 2
    top = bezier(p0a, (mx, p0a[1]), (mx, p1a[1]), p1a, n)
    bot = bezier(p0b, (mx, p0b[1]), (mx, p1b[1]), p1b, n)
    return V.Polygon(top + bot[::-1])


def sankey(theme) -> Variant:
    cols = [theme.c("accent"), theme.c("accent2"), theme.c("accent3")]
    k = 4.6 / 6497
    sl = []
    split = [("train", 4548), ("val", 975), ("test", 974)]
    # узлы
    def nodes(st):
        o = [O("!!src", "rect", 1.2, 1.6, 0.35, 6497 * k, fill="ink2", z=12), label("!!srcl", 1.0, 1.6 + 6497 * k / 2 - 0.3, "6497", w=1.0, al="r", sz=16, b=True),
             label("!!srcm", 1.0, 1.6 + 6497 * k / 2 + 0.0, "образцов", w=1.3, al="r", sz=13, col="ink2")]
        y = 1.6
        for i, (nm, v) in enumerate(split):
            hh = v * k
            o.append(O(f"!!t{i}", "rect", 6.4, y + i * 0.35, 0.35, hh, fill=cols[i], z=12))
            o.append(label(f"!!tl{i}", 6.95, y + i * 0.35 + hh / 2 - 0.17 if i == 0 else y + i * 0.35 + hh / 2 - 0.17, f"{nm} {v}", w=1.9, al="l", sz=14, b=True))
            y += hh
        return o
    def bands(st):
        o, ys, yt = [], 1.6, 1.6
        for i, (nm, v) in enumerate(split):
            hh = v * k
            g = _band((1.55, ys), (1.55, ys + hh), (6.4, yt + i * 0.35), (6.4, yt + i * 0.35 + hh))
            o.append(raw(f"!!b{i}", g, fill=cols[i], fa=0.45, z=8))
            ys += hh
            yt += hh
        return o
    sl.append(S(nodes(0) + bands(0) + [head("Разбиение", x=8.4, w=4.6)], 800,
                fx=[Fx("entrance_wipe", f"!!b{i}", start="at", delay=0.15 + 0.15 * i, dur=0.45, options={"direction": "left"}) for i in range(3)]))
    # 2: train делится по типу (условно 1100 / 3448)
    o = nodes(1) + bands(1) + [head("Train по типу", x=9.6, w=3.6)]
    by = [("красные", 1100), ("белые", 3448)]
    yt, ys = 1.4, 1.6
    tc = [mix(theme.c("accent"), "8E1F33", 0.6), mix(theme.c("accent3"), "B8860B", 0.5)]
    for i, (nm, v) in enumerate(by):
        hh = v * k
        g = _band((6.75, ys), (6.75, ys + hh), (11.0, yt + i * 0.5), (11.0, yt + i * 0.5 + hh))
        o.append(raw(f"tb{i}", g, fill=tc[i], fa=0.5, z=8))
        o.append(O(f"tn{i}", "rect", 11.0, yt + i * 0.5, 0.35, hh, fill=tc[i], z=12))
        o.append(label(f"tnl{i}", 11.45, yt + i * 0.5 + hh / 2 - 0.17, f"{nm} {v}", w=1.8, al="l", sz=14, b=True))
        ys += hh
        yt += hh
    o = [ob for ob in o if ob.name != "!!tl0"] + [label("!!tl0", 6.3, 1.25, "train 4548", w=1.9, al="r", sz=14, b=True)]
    sl.append(S(o, 800, fx=[Fx("entrance_wipe", f"tb{i}", start="at", delay=0.15 + 0.2 * i, dur=0.45, options={"direction": "left"}) for i in range(2)]))
    # 3: ленты сжимаются в 100 %-полосу
    o = [head("Те же ленты — полосой", w=8)]
    x = 1.2
    for i, (nm, v) in enumerate(split):
        ww = 11.0 * v / 6497
        g = V.Polygon([(x + ww * j / 40, 3.4) for j in range(41)] + [(x + ww * (40 - j) / 40, 4.6) for j in range(41)])
        o.append(raw(f"!!b{i}", g, fill=cols[i], fa=0.9, z=8))
        o.append(label(f"!!tl{i}", x + ww / 2, 4.75, f"{nm} {v}", w=max(ww, 1.5), sz=14, b=True))
        x += ww
    sl.append(S(o, 900))
    return _v("sankey", "Санкей: ленты делятся и сжимаются в полосу",
              "Потоки — ленты с явными точками (верх и низ — кривые Безье по 41 точке): 6497 → train/val/test "
              "(условные числа), затем train по типу 1100/3448 (новые ленты вытираются слева), затем те же три ленты "
              "выпрямляются в полосу 100 %.",
              sl, ["data", "sankey", "shape-morph", "flow"], 4)


def small_multiples(theme) -> Variant:
    cols = [theme.c("accent"), theme.c("accent2"), theme.c("accent3")]
    rnd = random.Random(4)
    series = []
    for s in range(3):
        v, pts = 0.5, []
        for t in range(30):
            v += rnd.uniform(-0.12, 0.12) + 0.02 * (s - 1)
            v = min(max(v, 0.05), 0.95)
            pts.append((t / 29, v))
        series.append(pts)
    names = ["Север", "Центр", "Юг"]
    def place(pts, box):
        x, y, w, h = box
        return [(x + px * w, y + h - py * h) for px, py in pts]
    sl = []
    big = (1.4, 1.7, 10.6, 4.7)
    o = [head("Три ряда на одном графике", w=8), O("!!frame0", "rect", *big, fill=None, ln="line", lw=1.0, z=2)]
    for s in range(3):
        o.append(raw(f"!!s{s}", ribbon(place(series[s], big), 0.045, 80), fill=cols[s], z=10))
        o.append(label(f"!!sl{s}", 12.1, place(series[s], big)[-1][1] - 0.15, names[s], w=1.1, al="l", sz=13, b=True, col=cols[s]))
    sl.append(S(o, 700))
    o = [head("Малые множители", w=8)]
    for s in range(3):
        box = (0.9 + s * 4.15, 2.2, 3.7, 3.6)
        o.append(O(f"!!frame{s}", "rect", *box, fill=None, ln="line", lw=1.0, z=2))
        o.append(raw(f"!!s{s}", ribbon(place(series[s], box), 0.045, 80), fill=cols[s], z=10))
        o.append(label(f"!!sl{s}", box[0] + box[2] / 2, box[1] - 0.45, names[s], w=2.0, sz=15, b=True, col=cols[s]))
    sl.append(S(o, 900))
    o = [head("Одна шкала — друг под другом", w=8)]
    for s in range(3):
        box = (2.4, 1.6 + s * 1.75, 9.6, 1.45)
        o.append(O(f"!!frame{s}", "rect", *box, fill=None, ln="line", lw=1.0, z=2))
        o.append(raw(f"!!s{s}", ribbon(place(series[s], box), 0.045, 80), fill=cols[s], z=10))
        o.append(label(f"!!sl{s}", 2.2, box[1] + 0.55, names[s], w=1.5, al="r", sz=15, b=True, col=cols[s]))
    sl.append(S(o, 900))
    return _v("small_multiples", "Один график → малые множители",
              "Три ряда-ленты (согласованные точки) уходят каждый в свою рамку — сравнение без путаницы цветов; затем "
              "рамки встают столбиком на общей шкале времени. Рамка первого графика становится рамкой первого множителя.",
              sl, ["data", "small-multiples", "shape-morph"], 4)


def scatter_bars(theme) -> Variant:
    cols = ccols(theme)
    rnd = random.Random(8)
    pts = []
    for k, (_, v) in enumerate(CATS):
        for j in range(round(40 * v / TOT)):
            pts.append((k, rnd.uniform(1.8, 6.2), rnd.uniform(0.6, 12.4)))
    sl = []
    o = [head("Облако образцов", w=6)]
    for i, (k, y, x) in enumerate(pts):
        o.append(O(f"!!d{i}", "oval", x - 0.12, y - 0.12, 0.24, 0.24, fill=cols[k], z=10))
    sl.append(S(o, 700))
    o = [head("Счёт по баллам", w=6), line("ax", (1.5, 6.4), (11.8, 6.4), ln="line", lw=1.0)]
    cnt = [0] * 4
    for i, (k, y, x) in enumerate(pts):
        j = cnt[k]
        cnt[k] += 1
        xx = 2.4 + k * 2.6 + (j % 3) * 0.3
        yy = 6.25 - (j // 3) * 0.3
        o.append(O(f"!!d{i}", "oval", xx - 0.12, yy - 0.12, 0.24, 0.24, fill=cols[k], z=10))
    o += [label(f"!!cl{k}", 2.7 + k * 2.6, 6.5, CATS[k][0], w=2.2, sz=13, b=True) for k in range(4)]
    sl.append(S(o, 900))
    o = [head("Столбики из точек", w=6), line("ax", (1.5, 6.4), (11.8, 6.4), ln="line", lw=1.0)]
    cnt = [0] * 4
    tot = [sum(1 for p in pts if p[0] == k) for k in range(4)]
    for i, (k, y, x) in enumerate(pts):
        j = cnt[k]
        cnt[k] += 1
        hgt = 0.3 * math.ceil(tot[k] / 3)
        o.append(O(f"!!d{i}", "rect", 2.28 + k * 2.6, 6.4 - hgt * (j + 1) / tot[k], 0.84, hgt / tot[k] + 0.005, fill=cols[k], z=10))
    o += [label(f"!!cl{k}", 2.7 + k * 2.6, 6.5, CATS[k][0], w=2.2, sz=13, b=True) for k in range(4)]
    o += [label(f"cv{k}", 2.7 + k * 2.6, 6.4 - 0.3 * math.ceil(tot[k] / 3) - 0.4, fmt(CATS[k][1]), w=1.6, sz=14, col="ink2") for k in range(4)]
    sl.append(S(o, 800, fx=[Fx("entrance_fade", f"cv{k}", start="at", delay=0.2 + 0.08 * k) for k in range(4)]))
    return _v("scatter_bars", "Облако точек оседает в столбики",
              "Агрегация на глазах: 40 точек (цвет — балл) разбросаны → оседают в штабели по категориям → каждая "
              "точка становится ломтиком столбика (овал → прямоугольник), появляются числа train (условные).",
              sl, ["data", "aggregate", "dots", "bars"], 4)


def pie3d(theme) -> Variant:
    cols = ccols(theme)
    c = (8.6, 3.9)
    R = 2.6
    depth = 0.55
    sl = []
    for st, (sy, dep, gap) in enumerate([(0.45, depth, 0.0), (0.45, depth, 0.35), (1.0, 0.0, 0.0)]):
        o = [head(["Объёмный пирог", "Секторы выдвинуты", "Вид сверху"][st], w=5)]
        a = -90
        for i, (nm, v) in enumerate(CATS):
            da = 360 * v / TOT
            am = math.radians(a + da / 2)
            dx, dy = gap * math.cos(am), gap * math.sin(am) * sy
            top = V.move(sector_q(c[0], c[1], R, 0.0, a, a + da, sy=sy), dx, dy)
            # боковая стенка: внешняя дуга сектора, опущенная на глубину (видна только передняя половина)
            arc = [(c[0] + dx + R * math.cos(math.radians(a + da * t / 30)), c[1] + dy + R * sy * math.sin(math.radians(a + da * t / 30))) for t in range(31)]
            wall = V.Polygon(arc + [(x, y + max(dep, 0.002)) for x, y in arc[::-1]])
            o.append(vs(f"!!w{i}", wall, N, start=ST, fill=dark(cols[i], 0.3), fa=1.0 if dep > 0 else 0.0, z=5,
                        grad=V.gradient([(0, dark(cols[i], 0.15)), (1, dark(cols[i], 0.45))], 0) if dep > 0 else None))
            o.append(mark(f"!!m{i}", top, cols[i], z=10 + i))
            lx = c[0] + dx * 1.2 + (R + 0.45) * math.cos(am)
            ly = c[1] + dy * 1.2 + (R * sy + 0.3) * math.sin(am) + (dep + 0.15 if math.sin(am) > 0 else 0.0)
            o.append(label(f"!!ml{i}", lx, ly - 0.17, nm, w=1.9, al="l" if math.cos(am) > 0.2 else ("r" if math.cos(am) < -0.2 else "c"), sz=14, b=True))
            a += da
        sl.append(S(o, 900))
    return _v("pie3d", "Объёмный пирог → разлёт → вид сверху",
              "3D из 2D без 3D-поворота: верх пирога — сжатые по вертикали секторы, стенки — дуги, опущенные на глубину "
              "(тёмный градиент); секторы выдвигаются от центра вместе со стенками; затем «камера» поднимается — пирог "
              "разжимается в плоский, стенки исчезают.",
              sl, ["data", "3d", "pie", "fragment"], 4)


def radial_bars(theme) -> Variant:
    imp = importance()[:8]
    top = imp[0][1]
    sl = []
    o = [head("Важность входов", w=8)]
    for i, (nm, v) in enumerate(imp):
        y = 1.6 + i * 0.6
        L = 0.2 + v / top * 7.0
        o += [raw(f"!!r{i}", rect_q(3.4, y, L, 0.42), fill="accent" if i < 3 else "accent2", z=10),
              label(f"!!rl{i}", 3.25, y + 0.05, nm, w=2.4, al="r", sz=14, b=i < 3)]
    sl.append(S(o, 700))
    c = (8.6, 4.1)
    o = [head("Те же столбики — по кругу", w=6)]
    for i, (nm, v) in enumerate(imp):
        r_in = 0.6 + i * 0.36
        sweep = 20 + 300 * v / top
        o += [raw(f"!!r{i}", sector_q(c[0], c[1], r_in + 0.3, r_in, -90, -90 + sweep), fill="accent" if i < 3 else "accent2", z=10),
              label(f"!!rl{i}", c[0] - 0.12, c[1] - r_in - 0.33, nm, w=2.4, al="r", sz=12, b=i < 3)]
    sl.append(S(o, 900))
    return _v("radial_bars", "Столбики сгибаются в кольца",
              "Горизонтальные столбики важности (условные данные, без чисел) переливаются в радиальные — дуги разной длины на "
              "вложенных кольцах. Длина сохраняет порядок; круг — для обложки раздела или «колеса» показателей.",
              sl, ["data", "radial", "shape-morph"], 4)


def slope_ranks(theme) -> Variant:
    from lab.f_wine import importance
    nn = importance("importance")
    feats = [f for f, _ in nn]
    vals = dict(nn)
    rank_r = {f: k for k, (f, _) in enumerate(importance("importance_ridge"))}
    top = max(vals.values())
    sl = []
    o = [head("Важность для сети", w=8)]
    for i, f in enumerate(feats):
        y = 1.5 + i * 0.44
        o += [O(f"!!k{i}", "rect", 3.4, y, 0.15 + vals[f] / top * 6.5, 0.32, fill="accent2", z=10), label(f"!!kl{i}", 3.25, y - 0.01, f, w=2.4, al="r", sz=13)]
    sl.append(S(o, 700))
    o = [head("Сеть и Ridge: ранги", w=8), label("hn", 4.4, 0.95, "сеть", w=1.5, sz=14, b=True), label("hr", 9.4, 0.95, "Ridge", w=1.5, sz=14, b=True)]
    for i, f in enumerate(feats):
        y0, y1 = 1.6 + i * 0.44, 1.6 + rank_r[f] * 0.44
        moved = abs(rank_r[f] - i) >= 3
        o += [O(f"!!k{i}", "oval", 4.4 - 0.12, y0 - 0.12 + 0.16, 0.24, 0.24, fill="accent2", z=10), label(f"!!kl{i}", 4.15, y0 - 0.01, f, w=2.4, al="r", sz=13,
                                                                                                    b=moved),
              O(f"kr{i}", "oval", 9.4 - 0.12, y1 + 0.04, 0.24, 0.24, fill="accent" if moved else "accent2", z=10),
              line(f"ks{i}", (4.4, y0 + 0.16), (9.4, y1 + 0.16), ln="accent" if moved else "line", lw=2.0 if moved else 1.0, z=5)]
    sl.append(S(o, 900, fx=[Fx("entrance_fade", f"ks{i}", start="at", delay=0.15 + 0.03 * i, dur=0.35) for i in range(len(feats))]))
    return _v("slope_ranks", "Столбики сжимаются в наклонный график",
              "Столбики важности для сети сжимаются в точки левой колонки; справа — ранги тех же признаков у Ridge, "
              "линии наклона вытираются слева; признаки, сдвинувшиеся на 3+ места, — акцентом (условные данные).",
              sl, ["data", "slope", "rank"], 4)


def data_steps(theme) -> Variant:
    topics = ["Источник", "Очистка", "Признаки", "Модель"]
    cols = [theme.c("accent"), theme.c("accent2"), theme.c("accent3"), theme.c("muted")]
    sl = []
    for k in range(3):
        o = [kicker("раздел 2 · конвейер данных"), head(f"Шаг {k + 1}: {topics[k].lower()}", w=7),
             body("!!b", 0.7, 1.45, 5, 0.4, f"{(k + 1) * 25} % раздела", sz=16, col="accent")]
        for i in range(4):
            for j in range(9):
                on = i <= k
                x = 8.4 + (j % 3) * 0.42 + (i % 2) * 1.5
                y = 2.0 + (j // 3) * 0.42 + (i // 2) * 1.5
                o.append(O(f"!!q{i}_{j}", "rect", x, y, 0.36, 0.36, fill=cols[i] if on else "surface2", z=10))
            o.append(label(f"!!ql{i}", 8.4 + (i % 2) * 1.5 + 0.6, 3.27 + (i // 2) * 1.5, topics[i], w=1.4, sz=12, b=i == k,
                           col="ink" if i <= k else "muted"))
        sl.append(S(o, 600, fx=[Fx("entrance_zoom", f"!!q{k}_{j}", start="at", delay=0.1 + 0.03 * j, dur=0.2) for j in range(9)] if False else []))
    return _v("data_steps", "Вафля-квартал: шаги раздела",
              "Прогресс внутри раздела: вафля из 4 кварталов по 9 клеток = 4 темы; пройденные кварталы окрашены, "
              "25 → 50 → 75 %. Тихий навигатор в углу содержательного слайда.",
              sl, ["data", "progress", "waffle"], 3)


def seq_data(theme) -> Variant:
    """Четыре метки через презентацию: кольцо-обложка → столбики с числами → 100 %-полоса → treemap → объёмный пирог →
    кольцо у края (навигация) → огромное бледное кольцо под текстом → столбики-итог."""
    cols = ccols(theme)
    S_ = []
    def marks(geos, alpha=1.0, z=10, extra=None):
        return [mark(f"!!m{i}", g, cols[i], z=z + i, fa=alpha, meta=dict(DEC)) for i, g in enumerate(geos)]
    # 1 кольцо
    S_.append(S(marks(pie_geo((9.3, 3.9), 2.6, r_in=1.4)) + [kicker("данные проекта"), O("!!cov", "text", 0.7, 1.0, 5.4, 1.7,
                                                                                    txt=["Одни данные —", "много форм"], sz=44, b=True, font="head",
                                                                                    col="ink", spacing=0.95, z=90),
                                                            body("!!csub", 0.7, 2.9, 5, 0.5, "баллы экспертов, train: 4548", sz=18)], 700))
    # 2 столбики
    o = marks(bars_geo()) + [head("Баллы: сколько образцов", w=8)]
    for i, (nm, v) in enumerate(CATS):
        o += [label(f"!!ml{i}", 3.0, 1.9 + i * 1.05 + 0.15, nm, w=2.2, al="r", sz=15, b=True),
              label(f"mv{i}", 3.3 + 8.0 * v / 2010, 1.9 + i * 1.05 + 0.15, fmt(v), w=1.2, al="l", sz=15, col="ink2")]
    S_.append(S(o, 900, fx=[Fx("entrance_fade", f"mv{i}", start="at", delay=0.2 + 0.08 * i) for i in range(4)]))
    # 3 полоса 100 %
    o = marks(stack_geo()) + [head("Доли одной полосой", w=8)]
    x = 1.0
    for i, (nm, v) in enumerate(CATS):
        ww = 11.3 * v / TOT
        o += [label(f"!!ml{i}", x + ww / 2, 2.85, nm if ww > 1.2 else "прочие", w=max(ww, 1.0), sz=14, b=True),
              label(f"mp{i}", x + ww / 2, 4.75, f"{round(100 * v / TOT)} %", w=max(ww, 0.9), sz=14, col="ink2")]
        x += ww
    S_.append(S(o, 900))
    # 4 treemap
    tg = treemap_geo()
    o = marks(tg) + [head("Площадь = доля", w=3.2), body("!!b", 0.7, 1.45, 3.0, 0.8, ["treemap из", "тех же меток"], sz=16)]
    for i, g in enumerate(tg):
        cx_, cy_ = g.centroid.x, g.centroid.y
        o.append(label(f"!!ml{i}", cx_, cy_ - 0.17, CATS[i][0], w=2.0, sz=14, b=True, col="bg"))
    S_.append(S(o, 900))
    # 5 объёмный пирог
    c = (8.6, 3.8)
    o = [head("Пирог в объёме", w=5)]
    a = -90
    for i, (nm, v) in enumerate(CATS):
        da = 360 * v / TOT
        top = sector_q(c[0], c[1], 2.6, 0.0, a, a + da, sy=0.45)
        arc = [(c[0] + 2.6 * math.cos(math.radians(a + da * t / 30)), c[1] + 2.6 * 0.45 * math.sin(math.radians(a + da * t / 30))) for t in range(31)]
        o.append(vs(f"w{i}", V.Polygon(arc + [(x_, y_ + 0.5) for x_, y_ in arc[::-1]]), fill=dark(cols[i], 0.35), z=5))
        o.append(mark(f"!!m{i}", top, cols[i], z=10 + i))
        am = math.radians(a + da / 2)
        o.append(label(f"!!ml{i}", c[0] + 3.05 * math.cos(am), c[1] + 1.47 * math.sin(am) + (0.65 if math.sin(am) > 0 else 0) - 0.17, nm, w=1.9,
                       al="l" if math.cos(am) > 0.2 else ("r" if math.cos(am) < -0.2 else "c"), sz=14, b=True))
        a += da
    S_.append(S(o, 900))
    # 6 кольцо у левого края — навигация; сектор раздела выдвинут
    secs = ["6 баллов", "5 баллов", "7 баллов", "Прочие"]
    cc = (-0.4, 3.75)
    a0 = -360 * (CATS[0][1] + CATS[1][1] + CATS[2][1] / 2) / TOT  # сектор раздела (балл 7) смотрит вправо
    geos = pie_geo(cc, 2.6, r_in=1.4, a0=a0)
    a = a0
    o = []
    for i, g in enumerate(geos):
        da = 360 * CATS[i][1] / TOT
        if i == 2:
            am = math.radians(a + da / 2)
            g = V.move(g, 0.35 * math.cos(am), 0.35 * math.sin(am))
        o.append(mark(f"!!m{i}", g, cols[i] if i == 2 else light(cols[i], 0.55), z=10 + i, meta=dict(DEC)))
        a += da
    o += [label(f"!!ml{i}", 2.75, 2.4 + i * 0.5, f"0{i + 1} {s}", w=2.2, al="l", sz=13, b=i == 2, col="accent3" if i == 2 else "muted") for i, s in enumerate(secs)]
    o += [kicker("раздел 3", x=5.6), head("Хорошие вина", x=5.6, w=7), body("!!txt", 5.6, 1.5, 7, 1.0, ["балл 7: 760 образцов", "реже, чем 5 и 6"], sz=20)]
    S_.append(S(o, 900))
    # 7 фон: огромное бледное кольцо под текстом
    o = marks(pie_geo((9.5, 4.6), 5.2, r_in=2.9), alpha=0.12, z=-300)
    o += [ml.copy(fa=0) for ml in []]
    o += [head("Почему модели трудно", w=8), body("!!txt", 0.7, 1.5, 6.5, 2.2, ["баллы 5 и 6 — 77 % train", "крайние баллы редки", "MAE 0,55 на test"], sz=22, col="ink")]
    S_.append(S(o, 900))
    # 8 итог — снова столбики
    o = marks(bars_geo()) + [head("Итог: форма под вопрос", w=8)]
    for i, (nm, v) in enumerate(CATS):
        o += [label(f"!!ml{i}", 3.0, 1.9 + i * 1.05 + 0.15, nm, w=2.2, al="r", sz=15, b=True)]
    S_.append(S(o, 900))
    return _v("seq_data", "Четыре метки через презентацию",
              "8 состояний одних и тех же 4 меток: кольцо (обложка) → столбики с числами (условными) → полоса 100 % → "
              "treemap → объёмный пирог (стенки) → кольцо у левого края, сектор раздела выдвинут (навигация) → огромное "
              "бледное кольцо под выводами → снова столбики. Подписи категорий едут за метками.",
              S_, ["seq", "data", "chart-morph", "pointer", "backdrop", "3d"], 4)


def variants(theme) -> list[Variant]:
    return [seq_data(theme), bars_pie(theme), waffle(theme), beeswarm(theme), sankey(theme), small_multiples(theme), scatter_bars(theme),
            pie3d(theme), radial_bars(theme), slope_ranks(theme), data_steps(theme)]
