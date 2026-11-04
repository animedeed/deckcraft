"""Семейство shatter: крупные числа и слова как КОНТУРЫ глифов (TextPath -> shapely, дырки сохранены),
которые раскалываются на осколки и собираются; число из осколков; осколки перетекают в график, кольцо, точки.
Глиф никогда не переливается в другой глиф — только сборка и разборка.
"""

from __future__ import annotations

import math
import random

from morphkit import O, Slide
from morphkit import vector as V
from morphkit.presets import Fx
from morphkit.theme import mix

from lab import Variant
from lab._a_util import (at_centroid, cells_exact, cut, glyphs, head, label, match, no_holes, orbit, put, ring_cells,
                         shatter, shelf, sub, text_width)
from shapely.ops import unary_union

NP = 28  # точек на осколок (для перелива осколок -> ячейка)


def number(text, x, y, h, n, seed=3, track=-0.04, resample=True):
    g = unary_union(glyphs(text, x, y, h, track=track))
    sh = no_holes(shatter(g, n, seed=seed))
    sh.sort(key=lambda p: (round(p.centroid.x, 1), p.centroid.y))
    return g, ([V.resample(p, NP) for p in sh] if resample else sh)


def centered(text, cx, cy, h, track=-0.04):
    w = text_width(text, h, track=track)
    return cx - w / 2, cy - h / 2


def scatter_pos(k, seed, box=(0.6, 1.6, 12.7, 6.8)):
    rnd = random.Random(seed * 1000 + k)
    return rnd.uniform(box[0], box[2]), rnd.uniform(box[1], box[3]), rnd.uniform(-110, 110)


def shards(theme, pieces, name="!!s", fill="ink", seam=0.75, fa=1.0, z=10, mode="put", **kw):
    bg = theme.c("bg")
    return [put(f"{name}{i}", g, fill=fill if isinstance(fill, str) else fill[i], ln=bg if seam else None, lw=seam, fa=fa, z=z + i)
            for i, g in enumerate(pieces)]


def scattered(theme, pieces, seed=1, name="!!s", fill="ink", fa=0.55, k=1.0, box=(0.6, 1.6, 12.7, 6.8)):
    out = []
    for i, g in enumerate(pieces):
        x, y, r = scatter_pos(i, seed, box)
        c = g.centroid
        x = c.x + (x - c.x) * k
        y = c.y + (y - c.y) * k
        out.append(put(f"{name}{i}", g, x - c.x, y - c.y, rot=r * k, fill=fill if isinstance(fill, str) else fill[i], fa=fa,
                       ln=theme.c("bg"), lw=0.75, z=10 + i))
    return out


# ----------------------------------------------------------------------------- одиночные

def v_assemble(theme):
    x, y = centered("87%", 7.6, 3.9, 3.0)
    g, sh = number("87%", x, y, 3.0, 70, seed=4)
    cap = label("cap", "клиентов вернулись за год", 7.6, 6.0, w=6.0, sz=22, col="ink2")
    return Variant("shatter", "assemble", "Число собирается из осколков",
                   "Осколки разбросаны по слайду и повёрнуты; за один Morph они слетаются в контур числа (швы видны "
                   "тонкими линиями), затем швы исчезают и появляется подпись. Роль: число-герой, начало раздела.",
                   [Slide([head("Что мы узнали")] + scattered(theme, sh, seed=2), dur=800),
                    Slide([head("Что мы узнали")] + shards(theme, sh), dur=900),
                    Slide([head("Что мы узнали"), cap] + shards(theme, sh, seam=0, fill="accent"), dur=600,
                          fx=[Fx("entrance_fade", "cap", start="at", delay=0.12, dur=0.35)])],
                   tags=["shatter", "glyph", "number", "assemble", "hero"], score=4)


def v_to_columns(theme):
    x, y = centered("100%", 6.9, 3.9, 2.3)
    g, sh = number("100%", x, y, 2.3, 70, seed=7)
    # три доли по площади слева направо: 50 / 30 / 20
    tot = sum(p.area for p in sh)
    order = sorted(range(len(sh)), key=lambda i: sh[i].centroid.x)
    grp, acc = [0] * len(sh), 0.0
    for i in order:
        grp[i] = 0 if acc < 0.5 * tot else 1 if acc < 0.8 * tot else 2
        acc += sh[i].area
    ink, bg = theme.c("ink"), theme.c("bg")
    cols3 = [theme.c("accent"), mix(ink, bg, 0.2), mix(ink, bg, 0.5)]
    fills = [cols3[grp[i]] for i in range(len(sh))]
    # колонки: осколки группы укладываются стопкой
    names3, shares = ["Зарплаты", "Аренда", "Прочее"], [50, 30, 20]
    moved = list(sh)
    for gi in range(3):
        idx = [i for i in range(len(sh)) if grp[i] == gi]
        offs = shelf([sh[i] for i in idx], 1.9 + gi * 3.5, 6.1, 3.0, gap=0.03)
        for i, (dx, dy) in zip(idx, offs):
            moved[i] = V.move(sh[i], dx, dy)
    labs = [label(f"cl{k}", f"{names3[k]} · {shares[k]}%", 3.4 + k * 3.5, 6.5, w=3.0, sz=17, col="ink2", b=k == 0) for k in range(3)]
    return Variant("shatter", "to_columns", "100% ссыпается в столбики",
                   "Число «100%» трескается на осколки, осколки окрашиваются в три доли слева направо, затем каждая доля "
                   "ссыпается в свою стопку — высоты стопок и есть доли. Роль: структура бюджета, «из чего 100%».",
                   [Slide([head("Весь бюджет")] + shards(theme, sh), dur=800),
                    Slide([head("Из трёх частей")] + shards(theme, sh, fill=fills), dur=700),
                    Slide([head("Куда уходят деньги")] + shards(theme, moved, fill=fills) + labs, dur=900,
                          fx=[Fx("entrance_fade", l.name, start="at", delay=0.1 + 0.05 * k, dur=0.3) for k, l in enumerate(labs)])],
                   tags=["shatter", "glyph", "data", "pile", "number"], score=3)


def v_cut_slide(theme):
    word = "РИСК"
    h = 2.2
    x, y = centered(word, 6.67, 3.8, h, track=0.02)
    g = unary_union(glyphs(word, x, y, h, track=0.02))
    b = g.bounds
    ang = math.radians(-14)
    cxw, cyw = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    L = 9
    line = [(cxw - L * math.cos(ang), cyw - L * math.sin(ang)), (cxw + L * math.cos(ang), cyw + L * math.sin(ang))]
    parts = cut(g, [line])
    nx, ny = -math.sin(ang), math.cos(ang)  # нормаль к разрезу
    side = lambda p: (p.centroid.x - cxw) * nx + (p.centroid.y - cyw) * ny  # noqa: E731
    up = [p for p in parts if side(p) < 0]
    dn = [p for p in parts if side(p) >= 0]

    def st(d, slide_along=0.0):
        out = []
        ux, uy = math.cos(ang), math.sin(ang)
        for i, p in enumerate(up):
            out.append(put(f"!!u{i}", p, -nx * d - ux * slide_along, -ny * d - uy * slide_along, fill="ink", z=20))
        for i, p in enumerate(dn):
            out.append(put(f"!!d{i}", p, nx * d + ux * slide_along, ny * d + uy * slide_along, fill="ink", z=20))
        return out

    slash = V.shape("sl", V.polygon([line[0], line[1], (line[1][0], line[1][1] + 0.03), (line[0][0], line[0][1] + 0.03)]),
                    fill="accent", z=30)
    msg = O("msg", "text", 2.0, 3.45, 9.3, 0.7, txt="управляем, если разрезать на части", sz=20, col="accent", al="c", rot=-14, z=40)
    return Variant("shatter", "cut_slide", "Слово разрезано по косой",
                   "Крупное слово разрезается одной косой линией; половины расходятся по нормали и сдвигаются вдоль "
                   "разреза, в щели проявляется подпись под тем же углом. Роль: тезис, кинетическая типографика без "
                   "перелива букв.",
                   [Slide([head("Тезис")] + st(0), dur=800),
                    Slide([head("Тезис"), slash] + st(0), dur=500, fx=[Fx("entrance_wipe", "sl", start="at", delay=0.1, dur=0.35, options={"direction": "left"})]),
                    Slide([head("Тезис"), msg] + st(0.6, 0.3), dur=800, fx=[Fx("entrance_fade", "msg", start="at", delay=0.15, dur=0.35)])],
                   tags=["shatter", "glyph", "cut", "typography", "emphasis"], score=3)


def v_kintsugi(theme):
    x, y = centered("2024", 6.67, 3.85, 2.9)
    g, sh = number("2024", x, y, 2.9, 40, seed=11)
    c = g.centroid
    rnd = random.Random(5)
    cracked = []
    for p in sh:
        pc = p.centroid
        cracked.append((V.move(p, (pc.x - c.x) * 0.09 + rnd.uniform(-0.05, 0.05), (pc.y - c.y) * 0.12 + rnd.uniform(-0.05, 0.05)),
                        rnd.uniform(-7, 7)))
    s0 = Slide([head("Тяжёлый год")] + shards(theme, sh, seam=0, fill=mix(theme.c("ink"), theme.c("bg"), 0.1)), dur=800)
    s1 = Slide([head("Тяжёлый год")] + [put(f"!!s{i}", p, rot=r, fill=mix(theme.c("ink"), theme.c("bg"), 0.3), ln=theme.c("bg"), lw=1.0, z=10 + i)
                                         for i, (p, r) in enumerate(cracked)], dur=700)
    s2 = Slide([head("Собрали — крепче"), sub("Швы — наш опыт", y=1.3, col="accent")]
               + shards(theme, sh, seam=2.0, fill=mix(theme.c("ink"), theme.c("bg"), 0.1)) +
               [V.shape("gold", unary_union(sh).boundary.buffer(0.012), fill="accent", z=5)], dur=800)
    for o in s2.objs:
        if o.name.startswith("!!s"):
            o.ln = theme.c("accent")
    return Variant("shatter", "kintsugi", "Кинцуги: трещины и золотые швы",
                   "Число года трескается — осколки чуть расходятся и поворачиваются, затем собираются обратно, но швы "
                   "становятся золотыми линиями. Роль: эмоциональный слайд про кризис и уроки, «стали крепче».",
                   [s0, s1, s2], tags=["shatter", "glyph", "number", "emotion"], score=4)


def v_orbit_in(theme):
    x, y = centered("12", 7.4, 3.9, 3.4)
    g, sh = number("12", x, y, 3.4, 46, seed=9)
    c = g.centroid
    piv = (c.x, c.y)
    R = 9.0
    rnd = random.Random(3)

    def st(k, rot):
        out = []
        for i, p in enumerate(sh):
            pc = p.centroid
            a = math.atan2(pc.y - piv[1], pc.x - piv[0])
            rr = math.hypot(pc.x - piv[0], pc.y - piv[1])
            r2 = rr + k * (2.2 + rnd.uniform(0, 1.2))
            q = at_centroid(p, piv[0] + r2 * math.cos(a), piv[1] + r2 * math.sin(a) * (1 - 0.38 * min(k, 1)))
            out.append(orbit(f"!!s{i}", q, piv, R, rot, fill="ink" if k == 0 else mix(theme.c("ink"), theme.c("bg"), 0.45),
                             ln=theme.c("bg"), lw=0.75, z=10 + i))
        return out

    cap = label("c12", "месяцев до окупаемости", 7.4, 6.2, w=5.0, sz=22, col="ink2")
    return Variant("shatter", "orbit_in", "Осколки по спирали в число",
                   "Осколки кружат вокруг центра на эллиптической орбите и за один Morph по спирали ложатся в контур "
                   "числа (рамка на оси общего центра). Роль: эффектное появление ключевой цифры, финал раздела.",
                   [Slide([head("Срок окупаемости")] + st(1.0, -100), dur=800),
                    Slide([head("Срок окупаемости"), cap] + st(0.0, 0), dur=900, fx=[Fx("entrance_fade", "c12", start="at", delay=0.15, dur=0.35)])],
                   tags=["shatter", "glyph", "orbit", "spiral", "number"], score=4)


def v_to_dots(theme):
    x, y = centered("48", 6.67, 3.9, 3.2)
    g, sh = number("48", x, y, 3.2, 48, seed=6)
    n = len(sh)
    ink, bg = theme.c("ink"), theme.c("bg")
    d = 0.36
    grid = [(3.4 + (i % 12) * 0.56, 2.4 + (i // 12) * 0.56) for i in range(n)]
    dots = [V.resample(V.circle(px, py, d / 2), NP) for px, py in grid]
    perm = match(sh, dots)
    sizes = [24, 16, n - 40]
    boxes = [(1.2, 2.2, 3.4, 3.4), (5.1, 2.2, 3.0, 3.4), (8.8, 2.2, 3.2, 3.4)]
    gpos = []
    for k, sz in enumerate(sizes):
        bx, by, bw, bh = boxes[k]
        cols = 6 if k == 0 else 4
        gpos += [(bx + 0.3 + (j % cols) * 0.5, by + 0.4 + (j // cols) * 0.5) for j in range(sz)]
    cols3 = [theme.c("accent"), mix(ink, bg, 0.2), mix(ink, bg, 0.5)]
    gfill = [cols3[0 if j < 24 else 1 if j < 40 else 2] for j in range(n)]

    def st(mode):
        out = []
        for i, p in enumerate(sh):
            j = perm[i]
            if mode == 0:
                out.append(V.shape(f"!!s{i}", p, fill="ink", ln=bg, lw=0.75, z=10 + i))
            elif mode == 1:
                out.append(V.shape(f"!!s{i}", dots[j], fill=mix(ink, bg, 0.15), z=10 + i))
            else:
                px, py = gpos[j]
                out.append(V.shape(f"!!s{i}", V.resample(V.circle(px, py, d / 2), NP), fill=gfill[j], z=10 + i))
        return out

    labs = [label("g0", "Остались · 24", 2.9, 5.6, w=3.0, sz=17, col="accent", b=True),
            label("g1", "Ушли · 16", 6.25, 5.6, w=2.6, sz=17, col="ink2"),
            label("g2", "Вернулись · 8", 9.75, 5.6, w=2.8, sz=17, col="ink2")]
    return Variant("shatter", "to_dots", "Число рассыпается в точки",
                   "Число «48» раскалывается на 48 осколков, каждый переливается в точку сетки (одна точка — один "
                   "участник), затем точки расходятся на три группы. Мост к любимому приёму «поле точек → группы». "
                   "Роль: число -> состав, данные.",
                   [Slide([head("Участники пилота")] + st(0), dur=800),
                    Slide([head("Каждый осколок — человек")] + st(1), dur=900),
                    Slide([head("Что с ними стало")] + st(2) + labs, dur=900,
                          fx=[Fx("entrance_fade", l.name, start="at", delay=0.12 + 0.06 * k, dur=0.3) for k, l in enumerate(labs)])],
                   tags=["shatter", "glyph", "dots", "groups", "data", "shape-morph"], score=5)


def v_to_ring(theme):
    x, y = centered("64%", 4.0, 3.9, 2.4)
    g, sh = number("64%", x, y, 2.4, 34, seed=8)
    P = len(sh)
    total = round(P / 0.64)
    cx, cy = 9.6, 3.95
    cells = [V.resample(c, NP) for c in ring_cells(cx, cy, 1.55, 2.45, total, gap_deg=1.6)]
    perm = match(sh, cells[:P])
    rest = [V.shape(f"rc{k}", cells[P + k], fill=theme.c("surface2"), z=5) for k in range(total - P)]
    lab_ = [label("rl", "64%", cx, cy - 0.2, w=2.4, h=0.75, sz=40, col="ink", b=True), label("rl2", "автоматизировано", cx, cy + 0.55, w=2.8, sz=15, col="ink2")]
    return Variant("shatter", "to_ring", "Осколки числа становятся кольцом",
                   "Осколки «64%» перелетают в ячейки кольцевой шкалы и заполняют ровно 64% кольца, остальные ячейки "
                   "проявляются серыми. Кольцо собрано из отдельных сегментов, без регулятора дуги. Роль: доля, KPI.",
                   [Slide([head("Доля автоматизации")] + shards(theme, sh, fill="accent"), dur=800),
                    Slide([head("Доля автоматизации")] + [V.shape(f"!!s{i}", cells[perm[i]], fill="accent", z=10 + i) for i in range(P)]
                          + rest + lab_, dur=900,
                          fx=[Fx("entrance_fade", r.name, start="at", delay=0.1 + 0.01 * k, dur=0.2) for k, r in enumerate(rest)]
                          + [Fx("entrance_fade", "rl", start="at", delay=0.2, dur=0.3), Fx("entrance_fade", "rl2", start="with", delay=0.05, dur=0.3)])],
                   tags=["shatter", "glyph", "ring", "data", "shape-morph"], score=5)


def v_cut_lid(theme):
    x, y = centered("3×", 6.67, 3.7, 3.4)
    g = unary_union(glyphs("3×", x, y, 3.4))
    b = g.bounds
    ym = b[1] + (b[3] - b[1]) * 0.48
    parts = cut(g, [[(b[0] - 1, ym), (b[2] + 1, ym)]])
    top = [p for p in parts if p.centroid.y < ym]
    bot = [p for p in parts if p.centroid.y >= ym]

    def st(open_):
        out = []
        for i, p in enumerate(top):
            out.append(put(f"!!t{i}", p, 0, -0.85 * open_, rot=-3 * open_, fill="ink", z=20))
        for i, p in enumerate(bot):
            out.append(put(f"!!b{i}", p, 0, 0.8 * open_, rot=2 * open_, fill="ink", z=20))
        return out

    card = O("crd", "text", 3.2, ym - 0.42 - 0.05, 6.9, 0.85, txt="быстрее проходит проверка", sz=28, b=True, col="accent", al="c", va="m", z=10)
    return Variant("shatter", "cut_lid", "Число открывается крышкой",
                   "Число разрезано по горизонтали; верх поднимается, низ опускается, и в образовавшейся щели "
                   "появляется смысл числа. Роль: раскрытие KPI — сначала цифра, потом «что за ней».",
                   [Slide([head("Главный результат")] + st(0), dur=800),
                    Slide([head("Главный результат"), card] + st(1), dur=800, fx=[Fx("entrance_fade", "crd", start="at", delay=0.12, dur=0.35)])],
                   tags=["shatter", "glyph", "cut", "reveal", "number"], score=3)


def v_strips(theme):
    word = "СМЫСЛ"
    h = 1.75
    x, y = centered(word, 6.67, 3.9, h, track=0.02)
    g = unary_union(glyphs(word, x, y, h, track=0.02))
    b = g.bounds
    k = 11
    w = (b[2] - b[0]) / k
    lines = [[(b[0] + w * i, b[1] - 1), (b[0] + w * i, b[3] + 1)] for i in range(1, k)]
    pieces = cut(g, lines)
    col_of = lambda p: min(k - 1, int((p.centroid.x - b[0]) / w))  # noqa: E731
    order = list(range(k))
    random.Random(4).shuffle(order)
    rnd = random.Random(2)
    dys = [rnd.uniform(-0.7, 0.7) for _ in range(k)]

    def st(mode):
        out = []
        for i, p in enumerate(pieces):
            c = col_of(p)
            if mode == 0:
                dx, dy = (order[c] - c) * w * 1.15 + (order[c] - k / 2) * 0.12, dys[c]
                out.append(put(f"!!p{i}", p, dx, dy, fill=mix(theme.c("ink"), theme.c("bg"), 0.45), z=10 + i))
            else:
                out.append(put(f"!!p{i}", p, 0, 0, fill="ink", z=10 + i))
        return out

    return Variant("shatter", "strips", "Слово из перемешанных полос",
                   "Слово нарезано на вертикальные полосы, полосы перемешаны и сдвинуты — читается шум; за один Morph "
                   "каждая полоса встаёт на место, и слово складывается. Роль: «собираем разрозненное в смысл», тезис.",
                   [Slide([head("Разрозненные данные")] + st(0), dur=800),
                    Slide([head("Складываются в")] + st(1), dur=900)],
                   tags=["shatter", "glyph", "strips", "assemble", "typography"], score=4)


def v_depth(theme):
    text = "5"
    h = 3.6
    x, y = centered(text, 7.2, 3.9, h)
    gl = unary_union(glyphs(text, x, y, h))
    ink, bg = theme.c("ink"), theme.c("bg")
    L = 7
    cols = [mix(ink, bg, 0.75 - 0.08 * k) for k in range(L - 1)] + [theme.c("accent")]

    def st(dx, dy, spread=1.0):
        return [put(f"!!d{k}", gl, dx * k * spread, dy * k * spread, fill=cols[k], ln=bg, lw=0.75, z=10 + k) for k in range(L)]

    return Variant("shatter", "depth", "Цифра выдавлена в объём",
                   "Семь копий контура цифры с шагом по диагонали и тоном от тёмного к акценту — плоская цифра "
                   "становится объёмной, затем слои расходятся в глубину и ракурс меняется. Имитация 3D из 2D. "
                   "Роль: номер раздела, обложка главы.",
                   [Slide([head("Раздел")] + st(0, 0), dur=800),
                    Slide([head("Раздел")] + st(-0.05, -0.04), dur=800),
                    Slide([head("Раздел"), sub("Пять шагов внедрения", y=1.3)] + st(0.16, -0.1, 1.0), dur=900)],
                   tags=["shatter", "glyph", "3d", "depth", "section"], score=4)


# ----------------------------------------------------------------------------- живые последовательности

def v_seq_number(theme):
    """Одно число живёт 8 состояний: осколки → число → три региона → столбики → самый большой столбик → панель
    → доля в кольце → фон под тезис → число с золотыми швами."""
    ink, bg = theme.c("ink"), theme.c("bg")
    txt = "3,2"
    h = 3.4
    x, y = centered(txt, 6.9, 3.9, h)
    g, sh = number(txt, x, y, h, 64, seed=12)
    P = len(sh)
    # регионы — по площади слева направо 46 / 34 / 20
    tot = sum(p.area for p in sh)
    order = sorted(range(P), key=lambda i: sh[i].centroid.x)
    grp, acc = [0] * P, 0.0
    for i in order:
        grp[i] = 0 if acc < 0.46 * tot else 1 if acc < 0.80 * tot else 2
        acc += sh[i].area
    cols3 = [theme.c("accent"), mix(ink, bg, 0.2), mix(ink, bg, 0.5)]
    fills = [cols3[grp[i]] for i in range(P)]
    regs = ["Москва", "Регионы", "СНГ"]
    shares = [46, 34, 20]

    def S(head_t, objs, dur=850, fx=None, extra=()):
        return Slide([head(head_t)] + list(extra) + objs, dur=dur, fx=fx or [])

    slides = []
    slides.append(S("Что мы собрали", scattered(theme, sh, seed=7, fa=0.5), dur=800))
    unit = label("unit", "млн пользователей", 6.9, 6.5, w=4.6, sz=22, col="ink2")
    slides.append(S("Что мы собрали", shards(theme, sh), extra=[unit], dur=900, fx=[Fx("entrance_fade", "unit", start="at", delay=0.12, dur=0.3)]))
    leg = [label(f"lg{k}", f"{regs[k]} · {shares[k]}%", 2.0 + 3.3 * k, 6.2, w=3.0, sz=17, col="accent" if k == 0 else "ink2", b=k == 0) for k in range(3)]
    slides.append(S("Откуда они", shards(theme, sh, fill=fills), extra=leg, dur=700,
                    fx=[Fx("entrance_fade", l.name, start="at", delay=0.1 + 0.05 * k, dur=0.25) for k, l in enumerate(leg)]))
    # 3 столбики: осколки региона ссыпаются стопкой
    col_x = [2.2, 5.6, 9.0]
    moved = list(sh)
    for gi in range(3):
        idx = [i for i in range(P) if grp[i] == gi]
        for i, (dx, dy) in zip(idx, shelf([sh[i] for i in idx], col_x[gi], 6.0, 2.4, gap=0.04)):
            moved[i] = V.move(sh[i], dx, dy)
    leg3 = [label(f"lc{k}", f"{regs[k]} · {shares[k]}%", col_x[k] + 1.2, 6.45, w=3.0, sz=17, col="accent" if k == 0 else "ink2", b=k == 0)
            for k in range(3)]
    slides.append(S("По регионам", shards(theme, moved, fill=fills), extra=leg3, dur=900,
                    fx=[Fx("entrance_fade", l.name, start="at", delay=0.1 + 0.05 * k, dur=0.25) for k, l in enumerate(leg3)]))
    # 4 столбик «Москва» поднимается и складывается в панель из ячеек; остальные отходят вниз-вправо
    idx0 = [i for i in range(P) if grp[i] == 0]
    panel = V.rect(0.8, 1.7, 5.6, 4.2, r=0.2)
    pc = cells_exact(panel, len(idx0), seed=3)
    pm = match([moved[i] for i in idx0], pc)
    st4 = []
    for i in range(P):
        if grp[i] == 0:
            j = idx0.index(i)
            st4.append(V.shape(f"!!s{i}", V.resample(pc[pm[j]], NP), fill=theme.c("accent"), ln=bg, lw=0.5, z=10 + i))
        else:
            st4.append(put(f"!!s{i}", moved[i], 3.2, 0.3, s=0.7, fill=fills[i], fa=0.5, ln=bg, lw=0.5, z=10 + i))
    ptxt = [O("p4a", "text", 1.2, 2.0, 4.8, 0.8, txt="Москва", sz=34, b=True, col="on_accent", z=80),
            O("p4b", "text", 1.2, 2.9, 4.8, 1.6, txt=["1,5 млн", "рост в 2 раза за год"], sz=22, col="on_accent", z=80)]
    slides.append(S("Главный регион", st4, extra=ptxt, dur=900,
                    fx=[Fx("entrance_fade", "p4a", start="at", delay=0.12, dur=0.3), Fx("entrance_fade", "p4b", start="with", delay=0.06, dur=0.3)]))
    # 5 все осколки -> кольцо долей (каждый осколок — ячейка своего региона)
    cx, cy = 8.9, 4.0
    cells = ring_cells(cx, cy, 1.5, 2.4, P, gap_deg=1.2)
    ordered = sorted(range(P), key=lambda i: (grp[i], sh[i].centroid.x))
    st5 = []
    for pos, i in enumerate(ordered):
        st5.append(V.shape(f"!!s{i}", V.resample(cells[pos], NP), fill=fills[i], z=10 + i))
    rl = [label("r5", "46%", cx, cy - 0.2, w=2.0, h=0.75, sz=40, col="accent", b=True), label("r5b", "Москва", cx, cy + 0.55, w=2.0, sz=16, col="ink2")]
    leg5 = [label(f"l5{k}", f"{regs[k]} · {shares[k]}%", 2.6, 2.9 + 0.6 * k, w=3.2, sz=17, col="accent" if k == 0 else "ink2", al="l", b=k == 0)
            for k in range(3)]
    slides.append(S("Доли регионов", st5, extra=rl + leg5, dur=900,
                    fx=[Fx("entrance_fade", t.name, start="at", delay=0.12 + 0.04 * k, dur=0.25) for k, t in enumerate(rl + leg5)]))
    # 6 фон под тезис: число крупно и прозрачно
    big = [put(f"!!s{i}", p, 2.6, 0.6, s=1.0, fill=fills[i], fa=0.12, z=-50 + i) for i, p in enumerate(sh)]
    big = []
    gx = V.scale(g, 1.9, origin=(6.9, 3.9))
    for i, p in enumerate(sh):
        q = V.scale(p, 1.9, origin=(6.9, 3.9))
        big.append(put(f"!!s{i}", V.move(q, 1.4, 0.6), fill=fills[i], fa=0.12, z=-60 + i))
    slides.append(Slide([O("q6", "text", 0.8, 2.6, 7.2, 2.0, txt=["Рост — из регионов,", "а не из столицы"], sz=40, b=True, col="ink", z=60)] + big,
                        dur=900, fx=[Fx("entrance_fade", "q6", start="at", delay=0.12, dur=0.35)]))
    # 7 финал: число с золотыми швами
    fin = [put(f"!!s{i}", p, fill="ink", ln=theme.c("accent"), lw=1.5, z=10 + i) for i, p in enumerate(sh)]
    slides.append(S("3,2 млн — и это начало", fin, dur=900))
    return Variant("shatter", "seq_number", "Число через весь раздел",
                   "Одно число из 60+ осколков в 8 состояниях: разбросано, собирается в «3,2», окрашивается тремя "
                   "регионами, ссыпается в столбики, доля «Москва» становится панелью из ячеек, все осколки "
                   "встают ячейками кольца долей, число уходит крупно в фон под тезис и собирается с золотыми швами.",
                   slides, tags=["seq", "shatter", "glyph", "data", "ring", "pile", "card", "background"], score=5)


def v_seq_word(theme):
    """Слово «РОСТ»: собирается → разрезается, в щели +38% → осколки складываются в стрелку → стрелка
    рассыпается на клетки столбиков по годам → последний год подсвечен → снова слово с акцентом."""
    ink, bg = theme.c("ink"), theme.c("bg")
    word = "РОСТ"
    h = 2.6
    x, y = centered(word, 6.67, 3.9, h, track=0.03)
    g = unary_union(glyphs(word, x, y, h, track=0.03))
    sh = no_holes(shatter(g, 56, seed=21))
    sh = [V.resample(p, NP) for p in sh]
    P = len(sh)
    S = []
    S.append(Slide([head("Итоги года")] + scattered(theme, sh, seed=4, fa=0.5), dur=800))
    S.append(Slide([head("Итоги года")] + shards(theme, sh), dur=900))
    # 2: разрез по косой — осколки по сторонам линии расходятся
    ang = math.radians(-12)
    b = g.bounds
    cxw, cyw = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    nx, ny = -math.sin(ang), math.cos(ang)
    side = [((p.centroid.x - cxw) * nx + (p.centroid.y - cyw) * ny) for p in sh]
    st2 = [put(f"!!s{i}", p, (nx if side[i] >= 0 else -nx) * 0.55, (ny if side[i] >= 0 else -ny) * 0.55, fill="ink", ln=bg, lw=0.75, z=10 + i)
           for i, p in enumerate(sh)]
    msg = O("m2", "text", 2.2, 3.5, 8.9, 0.8, txt="+38 % выручки за год", sz=30, b=True, col="accent", al="c", rot=-12, z=40)
    S.append(Slide([head("Итоги года"), msg] + st2, dur=800, fx=[Fx("entrance_fade", "m2", start="at", delay=0.15, dur=0.35)]))
    # 3: стрелка вверх из тех же осколков (ячейки стрелки)
    arrow = V.polygon([(5.2, 6.4), (5.2, 3.9), (4.1, 3.9), (6.67, 1.4), (9.25, 3.9), (8.15, 3.9), (8.15, 6.4)])
    ac = cells_exact(arrow, P, seed=2)
    am = match(sh, ac)
    S.append(Slide([head("Рост")] + [V.shape(f"!!s{i}", V.resample(ac[am[i]], NP), fill="accent", ln=bg, lw=0.75, z=10 + i) for i in range(P)],
                   dur=900))
    # 4: клетки столбиков по годам (вафельные столбики)
    years = ["2021", "2022", "2023", "2024"]
    ratio = [1.0, 1.35, 1.75, 2.45]
    cnt = [int(P * r / sum(ratio)) for r in ratio[:3]]
    cnt.append(P - sum(cnt))
    hs = [(c + 1) // 2 for c in cnt]
    cell = 0.36
    cols_per_bar = 2
    sq, owner = [], []
    for k, hh in enumerate(hs):
        for j in range(cnt[k]):
            cx_ = 2.4 + k * 2.4 + (j % cols_per_bar) * (cell + 0.06)
            cy_ = 6.1 - (j // cols_per_bar + 1) * (cell + 0.06)
            sq.append(V.rect(cx_, cy_, cell, cell, r=0.04))
            owner.append(k)
    while len(sq) < P:  # лишние осколки — в последний столбик
        j = len([o for o in owner if o == 3])
        sq.append(V.rect(2.4 + 3 * 2.4 + (j % cols_per_bar) * (cell + 0.06), 6.1 - (j // cols_per_bar + 1) * (cell + 0.06), cell, cell, r=0.04))
        owner.append(3)
    sq, owner = sq[:P], owner[:P]
    sm = match([ac[am[i]] for i in range(P)], sq)
    fills4 = [mix(ink, bg, 0.55 - 0.12 * owner[sm[i]]) for i in range(P)]
    labs4 = [label(f"y{k}", years[k], 2.4 + k * 2.4 + 0.4, 6.45, w=1.4, sz=16, col="ink2") for k in range(4)]
    S.append(Slide([head("Год за годом")] + [V.shape(f"!!s{i}", V.resample(sq[sm[i]], NP), fill=fills4[i], z=10 + i) for i in range(P)] + labs4,
                   dur=900, fx=[Fx("entrance_fade", l.name, start="at", delay=0.1 + 0.04 * k, dur=0.25) for k, l in enumerate(labs4)]))
    fills5 = [theme.c("accent") if owner[sm[i]] == 3 else mix(ink, bg, 0.55) for i in range(P)]
    labs5 = [l.copy(name=l.name + "b") for l in labs4]
    S.append(Slide([head("Этот год — рекорд"), label("y5", "+38 %", 2.4 + 3 * 2.4 + 0.4, 1.75, w=1.8, h=0.6, sz=28, col="accent", b=True)]
                   + [V.shape(f"!!s{i}", V.resample(sq[sm[i]], NP), fill=fills5[i], z=10 + i) for i in range(P)] + labs4, dur=700,
                   fx=[Fx("entrance_fade", "y5", start="at", delay=0.12, dur=0.3)]))
    S.append(Slide([head("Итоги года")] + [put(f"!!s{i}", p, fill="ink", ln=theme.c("accent"), lw=1.25, z=10 + i) for i, p in enumerate(sh)],
                   dur=900))
    return Variant("shatter", "seq_word", "Слово «РОСТ» в данные и обратно",
                   "Осколки складываются в слово «РОСТ», слово разрезается косой и в щели появляется «+38 %», осколки "
                   "переливаются в ячейки стрелки вверх, стрелка рассыпается в клетки столбиков по годам, последний год "
                   "подсвечен, и всё собирается обратно в слово со швами-акцентами. 7 состояний одной фигуры.",
                   S, tags=["seq", "shatter", "glyph", "cut", "arrow", "data", "shape-morph"], score=4)


def variants(theme) -> list[Variant]:
    return [f(theme) for f in (v_seq_number, v_seq_word, v_assemble, v_to_columns, v_cut_slide, v_kintsugi, v_orbit_in, v_to_dots,
                               v_to_ring, v_cut_lid, v_strips, v_depth)]
