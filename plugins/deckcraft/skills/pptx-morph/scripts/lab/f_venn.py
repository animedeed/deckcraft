"""Семейство venn: 2–5 кругов/эллипсов и их фрагменты — разлёт и сборка, выделение области, области -> карточки,
вращение разобранного набора, вложенный Венн, Венн как навигация, изометрия «чем больше совпадений, тем выше».
"""

from __future__ import annotations

import math

from morphkit import Cam, O, Slide
from morphkit import vector as V
from morphkit.presets import Fx
from morphkit.theme import contrast, mix

from lab import Variant
from lab._a_util import at_centroid, head, iso, label, orbit, put, sub, sweep

N = 160  # точек на фрагмент (для перелива)


def on(theme, fill: str) -> str:
    """Цвет текста поверх заливки: тушь или фон — что контрастнее."""
    f = theme.c(fill)
    a, b = theme.c("ink"), theme.c("bg")
    return a if contrast(a, f) >= contrast(b, f) else b


def venn3(cx, cy, r, d, a0=-90.0):
    cs = [V.circle(cx + d * math.cos(math.radians(a0 + 120 * k)), cy + d * math.sin(math.radians(a0 + 120 * k)), r)
          for k in range(3)]
    fr = []
    for g in V.fragment(*cs):
        p = g.representative_point()
        m = tuple(c.contains(p) for c in cs)
        fr.append((m, g))
    order = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (0, 1, 1), (1, 0, 1), (1, 1, 1)]
    fr.sort(key=lambda t: order.index(tuple(int(x) for x in t[0])))
    return cs, [(tuple(int(x) for x in m), g) for m, g in fr]


def vcol(theme, m) -> str:
    ink, bg = theme.c("ink"), theme.c("bg")
    n = sum(m)
    if n == 3:
        return theme.c("accent")
    if n == 2:
        return mix(ink, bg, 0.22 + 0.08 * [(1, 1, 0), (0, 1, 1), (1, 0, 1)].index(tuple(m)))
    return mix(ink, bg, 0.50 + 0.07 * [(1, 0, 0), (0, 1, 0), (0, 0, 1)].index(tuple(m)))


SETS = ["Данные", "Модель", "Люди"]
PAIRS = {(1, 1, 0): "Обучение", (0, 1, 1): "Интерфейс", (1, 0, 1): "Разметка", (1, 1, 1): "Продукт"}


def _set_labels(cx, cy, r, d, dist=1.0, prefix="!!sl", a0=-90.0, spread=0.0):
    out = []
    for k, t in enumerate(SETS):
        a = math.radians(a0 + 120 * k)
        rr = (d + r + 0.38) * dist + spread * d
        out.append(label(f"{prefix}{k}", t, cx + rr * math.cos(a), cy + rr * math.sin(a), w=1.7, sz=16, col="ink2"))
    return out


# ----------------------------------------------------------------------------- варианты

def v_explode_lift(theme):
    cx, cy, r, d = 8.6, 3.9, 1.5, 0.92
    _, fr = venn3(cx, cy, r, d)

    def st(spread, lift=False):
        out = []
        for k, (m, g) in enumerate(fr):
            c = g.centroid
            dx, dy = (c.x - cx) * spread, (c.y - cy) * spread
            col = vcol(theme, m)
            if lift:
                if sum(m) == 3:
                    out.append(put("!!vs", g, 0.0, 0.0, fill=theme.c("bg"), fa=0.6, z=20))
                    out.append(put(f"!!v{k}", g, 0.15, -0.36, s=1.6, fill=col, ln=theme.c("bg"), lw=2, z=40))
                    continue
                out.append(put(f"!!v{k}", g, fill=col, fa=0.32, ln=theme.c("bg"), lw=1.5, z=10 + k))
            else:
                out.append(put(f"!!v{k}", g, dx, dy, fill=col, ln=theme.c("bg"), lw=1.5, z=10 + k))
                if sum(m) == 3:
                    out.append(put("!!vs", g, dx, dy, fill=theme.c("bg"), fa=0.0, z=9))
        return out

    s0 = Slide([head("Три области задачи")] + st(0.0) + _set_labels(cx, cy, r, d), dur=800)
    s1 = Slide([head("Семь частей")] + st(0.62) + _set_labels(cx, cy, r, d, dist=1.32, spread=0.3), dur=850)
    lab_ = label("tz", "Наша зона", 10.95, 2.25, w=2.2, sz=20, col="accent", b=True)
    s2 = Slide([head("Что общее у всех трёх"), lab_] + st(0.0, lift=True) + _set_labels(cx, cy, r, d), dur=850,
               fx=[Fx("entrance_fade", "tz", start="at", delay=0.15, dur=0.4)])
    return Variant("venn", "explode_lift", "Разлёт и подъём центра",
                   "Три круга распадаются на семь частей, затем собираются, а общее ядро поднимается над схемой "
                   "с тенью и вдвое крупнее. Роль: переход от «что есть» к «где наш фокус» в начале раздела.",
                   [s0, s1, s2], tags=["fragment", "venn", "explode", "emphasis", "3d"], score=4)


def v_orbit_piece(theme):
    cx, cy, r, d = 4.3, 4.0, 1.35, 0.82
    _, fr = venn3(cx, cy, r, d)
    R_orb = 3.1
    idx = 0  # область «только Данные» (верхняя)
    piece = V.resample(fr[idx][1], N)
    big = 9.5  # радиус рамки на оси (панель должна лежать внутри рамки)

    def ring_line():
        return [V.shape("!!orb", V.subtract(V.circle(cx, cy, R_orb + 0.012), V.circle(cx, cy, R_orb - 0.012)),
                        fill="line", z=4)]

    def venn(skip=None, ghost=False):
        out = []
        for k, (m, g) in enumerate(fr):
            if k == skip:
                if ghost:
                    out.append(put("!!ghost", g, fill=None, ln=theme.c("muted"), lw=1.25, dash="dash", z=8))
                continue
            out.append(put(f"!!v{k}", g, fill=vcol(theme, m), ln=theme.c("bg"), lw=1.5, z=10 + k))
        return out

    th = 90.0  # поворот по орбите
    tgt = (cx + R_orb * math.cos(math.radians(-90 + th)), cy + R_orb * math.sin(math.radians(-90 + th)))
    # до поворота кусок стоит в точке, которую поворот на th приведёт в tgt
    pre = V.rotate(at_centroid(piece, tgt[0] + 0.35, tgt[1], 1.45), -th, origin=(cx, cy))
    pre_panel = V.rotate(V.resample(V.rect(8.0, 2.2, 4.4, 3.4, r=0.35), N), -th, origin=(cx, cy))
    p0 = orbit("!!pc", piece, (cx, cy), big, 0.0, fill=theme.c("accent"), ln=theme.c("bg"), lw=1.5, z=30)
    p1 = orbit("!!pc", pre, (cx, cy), big, th, fill=theme.c("accent"), z=30)
    p2 = orbit("!!pc", pre_panel, (cx, cy), big, th, fill=theme.c("accent"), z=30)  # цвет тот же — без грязного перехода
    s0 = Slide([head("Данные — лишь часть")] + venn() + ring_line() + [p0], dur=800)
    s1 = Slide([head("Выносим часть на орбиту")] + venn(idx, ghost=True) + ring_line() + [p1], dur=900)
    txt = [O("pt", "text", 8.35, 2.45, 3.8, 0.6, txt="Данные", sz=26, b=True, col="on_accent", z=40),
           O("pb", "text", 8.35, 3.15, 3.8, 1.9, txt=["Что собираем", "и кто размечает", "до обучения"], sz=17,
             col="on_accent", z=40)]
    s2 = Slide([head("Часть становится темой")] + venn(idx, ghost=True) + ring_line() + [p2] + txt, dur=800,
               fx=[Fx("entrance_fade", "pt", start="at", delay=0.12, dur=0.35),
                   Fx("entrance_fade", "pb", start="with", delay=0.1, dur=0.35)])
    return Variant("venn", "orbit_piece", "Кусок уходит по орбите",
                   "Область одного круга отделяется и едет по дуге орбиты, вырастая, а затем переливается в панель "
                   "темы; на месте остаётся пунктирный след. Роль: вход в подраздел, «берём одну часть крупно».",
                   [s0, s1, s2], tags=["fragment", "orbit", "venn", "navigation", "shape-morph"], score=5)


def v_lens_card(theme):
    cy = 3.7
    a, b = V.circle(5.4, cy, 1.7), V.circle(7.9, cy, 1.7)
    ca, cb, ln_ = V.resample(V.subtract(a, b), N), V.resample(V.subtract(b, a), N), V.resample(V.intersect(a, b), N)
    ga, gb = mix(theme.c("ink"), theme.c("bg"), 0.55), mix(theme.c("ink"), theme.c("bg"), 0.4)
    labs = lambda xa, xb: [label("!!la", "Бизнес", xa, cy, w=1.6, sz=19, col=on(theme, ga), b=True),  # noqa: E731
                           label("!!lb", "Технологии", xb, cy, w=1.9, sz=19, col=on(theme, gb), b=True)]
    s0 = Slide([head("Две стороны"),
                V.shape("!!ca", ca, fill=ga, z=10), V.shape("!!cb", cb, fill=gb, z=10),
                V.shape("!!ln", ln_, fill="accent", z=12)] + labs(4.75, 8.55), dur=800)
    card = V.resample(V.rect(4.9, 4.55, 3.5, 1.45, r=0.3), N)
    s1 = Slide([head("Общее — отдельно"),
                V.shape("!!ca", V.move(ca, -1.1, -0.6), fill=ga, z=10), V.shape("!!cb", V.move(cb, 1.1, -0.6), fill=gb, z=10),
                V.shape("!!ln", card, fill="accent", z=12),
                O("lc", "text", 4.9, 4.55, 3.5, 1.45, txt="Общие цели", sz=22, b=True, col="on_accent", al="c", va="m", z=20)]
               + labs(3.65, 9.65), dur=850, fx=[Fx("entrance_fade", "lc", start="at", delay=0.12, dur=0.3)])
    s2 = Slide([head("Каждая сторона — целое"),
                V.shape("!!ca", V.resample(V.circle(4.0, 2.9, 1.25), N), fill=ga, z=10),
                V.shape("!!cb", V.resample(V.circle(9.3, 2.9, 1.25), N), fill=gb, z=10),
                V.shape("!!ln", V.resample(V.rect(5.45, 4.75, 2.4, 1.1, r=0.3), N), fill="accent", z=12),
                O("lc2", "text", 5.45, 4.75, 2.4, 1.1, txt="Договор", sz=22, b=True, col="on_accent", al="c", va="m", z=20),
                V.shape("tie_a", V.polygon([(5.0, 3.75), (5.55, 4.85), (5.6, 4.8), (5.06, 3.7)]), fill="line", z=5),
                V.shape("tie_b", V.polygon([(8.3, 3.75), (7.75, 4.85), (7.7, 4.8), (8.24, 3.7)]), fill="line", z=5)]
               + labs(4.0, 9.3), dur=850, fx=[Fx("entrance_fade", "lc2", start="at", delay=0.1, dur=0.3)])
    return Variant("venn", "lens_card", "Линза становится карточкой",
                   "Пересечение двух кругов выпадает вниз и переливается в карточку «Общие цели», круги расходятся "
                   "и затягивают «укус», становясь целыми. Роль: переговоры, партнёрство, «что нас связывает».",
                   [s0, s1, s2], tags=["venn", "shape-morph", "card", "fragment"], score=4)


def v_to_cards(theme):
    cx, cy, r, d = 8.7, 3.9, 1.45, 0.88
    _, fr = venn3(cx, cy, r, d)
    parts = [(m, V.resample(g, N)) for m, g in fr]
    # сетка карточек: 3 одиночные сверху, 3 пары снизу, центр — большая справа
    cw, ch = 2.35, 1.2
    slots = [(0.75 + k * (cw + 0.25), 2.25) for k in range(3)] + [(0.75 + k * (cw + 0.25), 3.75) for k in range(3)]
    texts = SETS + [PAIRS[(1, 1, 0)], PAIRS[(0, 1, 1)], PAIRS[(1, 0, 1)]]

    def st(mode):
        out = []
        for k, (m, g) in enumerate(parts):
            col = vcol(theme, m)
            if mode == 0:
                out.append(V.shape(f"!!v{k}", g, fill=col, ln=theme.c("bg"), lw=1.5, z=10 + k))
            elif mode == 1:
                c = g.centroid
                out.append(V.shape(f"!!v{k}", V.move(g, (c.x - cx) * 0.55, (c.y - cy) * 0.55), fill=col, ln=theme.c("bg"),
                                   lw=1.5, z=10 + k))
            else:
                if k < 6:
                    x, y = slots[k]
                    out.append(V.shape(f"!!v{k}", V.resample(V.rect(x, y, cw, ch, r=0.18), N), fill=col, z=10 + k))
                    out.append(O(f"ct{k}", "text", x, y, cw, ch, txt=texts[k], sz=18, b=True, col=on(theme, col),
                                 al="c", va="m", z=30))
                else:
                    out.append(V.shape(f"!!v{k}", V.resample(V.rect(8.6, 2.25, 3.9, 2.7, r=0.25), N), fill=col, z=16))
                    out.append(O("ct6", "text", 8.6, 2.25, 3.9, 2.7, txt="Продукт", sz=30, b=True, col="on_accent",
                                 al="c", va="m", z=30))
        return out

    fx = [Fx("entrance_fade", f"ct{k}", start="at", delay=0.1 + 0.05 * k, dur=0.3) for k in range(7)]
    return Variant("venn", "to_cards", "Части становятся карточками",
                   "Диаграмма разбирается, и каждый фрагмент переливается в подписанную карточку сетки; ядро — "
                   "крупная акцентная карточка. Роль: от схемы к оглавлению раздела, план работ по зонам.",
                   [Slide([head("Три области")] + st(0), dur=800),
                    Slide([head("Семь частей")] + st(1), dur=800),
                    Slide([head("Семь задач")] + st(2), dur=900, fx=fx)],
                   tags=["venn", "shape-morph", "card", "navigation"], score=4)


def v_spin_explode(theme):
    cx, cy, r, d = 8.6, 3.9, 1.5, 0.92
    _, fr = venn3(cx, cy, r, d)
    R = 4.3

    def st(spread, rot, lit=False):
        out = []
        for k, (m, g) in enumerate(fr):
            c = g.centroid
            g2 = V.move(g, (c.x - cx) * spread, (c.y - cy) * spread)
            col = vcol(theme, m)
            out.append(orbit(f"!!v{k}", g2, (cx, cy), R, rot, fill=col, ln=theme.c("bg"), lw=1.5,
                             fa=1.0 if (not lit or sum(m) >= 2) else 0.35, z=10 + k))
        return out

    return Variant("venn", "spin_explode", "Разобранный набор поворачивается",
                   "Фрагменты разлетаются по спирали и проворачиваются вокруг общего центра, затем собираются "
                   "с поворотом на треть оборота: тот же предмет с другой стороны. Роль: смена точки зрения, "
                   "«посмотрим иначе», переход между частями доклада.",
                   [Slide([head("Одна картина")] + st(0, 0), dur=800),
                    Slide([head("Разбираем")] + st(0.7, 60), dur=900),
                    Slide([head("Другой ракурс")] + st(0.0, 120, lit=True), dur=900)],
                   tags=["venn", "rotate", "explode", "space"], score=4)


def v_nested(theme):
    # мир: большой Венн из двух кругов; внутри линзы — маленький Венн из трёх
    a, b = V.circle(5.6, 3.8, 2.1), V.circle(8.2, 3.8, 2.1)
    lens = V.intersect(a, b)
    lc = (6.9, 3.8)
    _, fr = venn3(lc[0], lc[1], 0.34, 0.2)
    ga, gb = mix(theme.c("ink"), theme.c("bg"), 0.6), mix(theme.c("ink"), theme.c("bg"), 0.45)

    def world(k_inner_lit=False, dim=1.0):
        out = [V.shape("!!a", V.subtract(a, b), fill=ga, fa=dim, z=5, world=True),
               V.shape("!!b", V.subtract(b, a), fill=gb, fa=dim, z=5, world=True),
               V.shape("!!l", lens, fill=mix(theme.c("accent"), theme.c("bg"), 0.78), fa=0.85, z=6, world=True)]
        for k, (m, g) in enumerate(fr):
            col = vcol(theme, m) if (k_inner_lit or sum(m) < 3) else mix(theme.c("ink"), theme.c("bg"), 0.15)
            out.append(V.shape(f"!!n{k}", g, fill=col, ln=theme.c("bg"), lw=0.6, z=10 + k, world=True))
        return out

    s0 = Slide([head("Пересечение двух"), label("oa", "Наука", 4.6, 3.8, w=1.6, sz=19, col=on(theme, ga), b=True),
                label("ob", "Рынок", 9.2, 3.8, w=1.6, sz=19, col=on(theme, gb), b=True)] + world(), cam=Cam(), dur=800)
    cam = Cam(lc[0], lc[1] + 0.03, 4.6)
    inner = [label(f"in{k}", t, *p, w=2.0, sz=19, col="ink", b=True)
             for k, (t, p) in enumerate(zip(["Патенты", "Стартапы", "Кадры"], [(6.9, 0.85), (10.9, 5.6), (2.9, 5.6)]))]
    s1 = Slide([head("Внутри — своё пересечение")] + world(dim=0.3) + inner, cam=cam, dur=900,
               fx=[Fx("entrance_fade", f"in{k}", start="at", delay=0.1 + 0.06 * k, dur=0.3) for k in range(3)])
    s2 = Slide([head("И своё ядро"), label("core", "Трансфер", 11.2, 3.75, w=2.4, sz=24, col="accent", b=True),
                O("corel", "line", 7.3, 3.75, 2.6, 0.0, ln="accent", lw=1.5, z=40)]
               + world(True, dim=0.3) + inner, cam=cam, dur=700,
               fx=[Fx("entrance_wipe", "corel", start="at", delay=0.1, dur=0.3, options={"direction": "left"}),
                   Fx("entrance_fade", "core", start="after", dur=0.3)])
    return Variant("venn", "nested", "Венн внутри Венна",
                   "Камера ныряет в линзу двух больших кругов, и внутри открывается свой Венн из трёх кругов "
                   "со своим ядром. Роль: «внутри пересечения — целая область», переход общий план → деталь.",
                   [s0, s1, s2], tags=["venn", "camera", "zoom", "space", "nested"], score=4)


def v_nav(theme):
    cx, cy, r, d = 3.6, 3.9, 1.3, 0.8
    _, fr = venn3(cx, cy, r, d)
    regions = {m: V.resample(g, N) for m, g in fr}

    def base():
        out = []
        for k, (m, g) in enumerate(fr):
            out.append(V.shape(f"!!v{k}", g, fill=vcol(theme, m) if sum(m) < 3 else mix(theme.c("ink"), theme.c("bg"), 0.1),
                               ln=theme.c("bg"), lw=1.5, z=10 + k))
        return out

    def marker(m):
        return [V.shape("!!mk", regions[m], fill="accent", fa=0.85, ln="accent", lw=2.5, z=30)]

    def panel(n, t, body, key):
        return [O(f"pn{key}", "text", 7.3, 2.0, 1.2, 1.0, txt=f"{n:02d}", sz=40, b=True, col="accent", z=40),
                O(f"pt{key}", "text", 7.3, 3.0, 5.2, 0.7, txt=t, sz=30, b=True, col="ink", z=40),
                O(f"pb{key}", "text", 7.3, 3.8, 5.2, 1.5, txt=body, sz=18, col="ink2", z=40)]

    def fx(key):
        return [Fx("entrance_fade", f"pn{key}", start="at", delay=0.1, dur=0.3),
                Fx("entrance_fade", f"pt{key}", start="with", delay=0.05, dur=0.3),
                Fx("entrance_fade", f"pb{key}", start="with", delay=0.08, dur=0.3)]

    s0 = Slide([head("Три раздела доклада")] + base() + marker((1, 0, 0)) + panel(1, "Данные", ["Откуда берём и сколько"], "a"),
               dur=800, fx=fx("a"))
    s1 = Slide([head("Три раздела доклада")] + base() + marker((1, 1, 0)) + panel(2, "Обучение", ["Данные встречают модель"], "b"),
               dur=800, fx=fx("b"))
    s2 = Slide([head("Три раздела доклада")] + base() + marker((1, 1, 1)) + panel(3, "Продукт", ["Где сходится всё"], "c"),
               dur=800, fx=fx("c"))
    return Variant("venn", "nav", "Маркер перетекает по областям",
                   "Венн стоит на месте как карта доклада; акцентный маркер переливается из области в соседнюю "
                   "(одиночная → пара → ядро), справа меняется раздел. Роль: навигация по разделам без смены стиля.",
                   [s0, s1, s2], tags=["venn", "navigation", "shape-morph", "marker"], score=4)


def v_merge(theme):
    cy = 3.9
    pos_apart = [(3.2, cy), (6.7, cy), (10.2, cy)]
    pos_join = [(6.0, 3.35), (7.3, 3.35), (6.65, 4.5)]
    cols = [mix(theme.c("ink"), theme.c("bg"), t) for t in (0.3, 0.45, 0.6)]
    names = ["Опыт", "Данные", "Интуиция"]

    def st(pos, rr, lp):
        out = []
        for k, (p, c) in enumerate(zip(pos, cols)):
            out.append(O(f"!!c{k}", "oval", p[0] - rr, p[1] - rr, 2 * rr, 2 * rr, fill=c, fa=0.55, z=10 + k))
        for k, p in enumerate(lp):
            out.append(label(f"!!t{k}", names[k], p[0], p[1], w=1.8, sz=18, col="ink", b=True))
        return out

    s0 = Slide([head("Три источника решения")] + st(pos_apart, 1.25, pos_apart), dur=800)
    lp = [(4.25, 2.6), (9.05, 2.6), (6.65, 6.35)]
    s1 = Slide([head("Они пересекаются")] + st(pos_join, 1.4, lp), dur=900)
    cs = [V.circle(p[0], p[1], 1.4) for p in pos_join]
    core = V.intersect(V.intersect(cs[0], cs[1]), cs[2])
    s2 = Slide([head("Решение — в общем")] + st(pos_join, 1.4, lp) +
               [V.shape("core", core, fill="accent", z=20), label("ct", "Решение", 10.4, 3.85, w=2.2, sz=22, col="accent", b=True),
                O("cl", "line", 7.6, 3.85, 1.65, 0.0, ln="accent", lw=1.5, z=19)], dur=600,
               fx=[Fx("entrance_faded_zoom", "core", start="at", delay=0.1, dur=0.4),
                   Fx("entrance_wipe", "cl", start="after", dur=0.3, options={"direction": "left"}),
                   Fx("entrance_fade", "ct", start="after", dur=0.3)])
    return Variant("venn", "merge", "Круги сходятся, ядро вспыхивает",
                   "Три полупрозрачных круга-источника съезжаются в Венн, затем их общее ядро проявляется акцентом "
                   "с выноской. Роль: вывод из нескольких источников, тезис «решение — на пересечении».",
                   [s0, s1, s2], tags=["venn", "merge", "emphasis"], score=3)


def v_five(theme):
    cx, cy = 8.7, 3.85
    cs = [V.circle(cx + 0.95 * math.cos(math.radians(-90 + 72 * k)), cy + 0.95 * math.sin(math.radians(-90 + 72 * k)), 1.35)
          for k in range(5)]
    fr = []
    for g in V.fragment(*cs):
        p = g.representative_point()
        fr.append((sum(c.contains(p) for c in cs), g))
    fr.sort(key=lambda t: (t[0], round(math.atan2(t[1].centroid.y - cy, t[1].centroid.x - cx), 3)))
    ink, bg = theme.c("ink"), theme.c("bg")
    tone = {1: mix(ink, bg, 0.62), 2: mix(ink, bg, 0.4), 3: mix(ink, bg, 0.18), 4: mix(ink, bg, 0.05), 5: theme.c("accent")}
    R = 5.0

    def st(spread, rot, only=None):
        out = []
        for k, (n, g) in enumerate(fr):
            c = g.centroid
            g2 = V.move(g, (c.x - cx) * spread, (c.y - cy) * spread)
            fa = 1.0 if only is None or n in only else 0.18
            out.append(orbit(f"!!f{k}", g2, (cx, cy), R, rot, fill=tone[min(n, 5)], fa=fa, ln=bg, lw=1.2, z=10 + n * 3))
        return out

    return Variant("venn", "five", "Пять кругов — звезда-мандала",
                   f"Пять направлений режут друг друга на {len(fr)} частей; части расходятся звездой с поворотом на "
                   "36°, затем подсвечены только стыки соседей. Роль: заставка раздела «экосистема», фон под вывод.",
                   [Slide([head("Пять направлений")] + st(0, 0), dur=800),
                    Slide([head("Все стыки")] + st(0.55, 36), dur=900),
                    Slide([head("Стыки соседей"), sub("Здесь рождаются задачи", y=1.3)] + st(0.55, 72, only={2, 5}), dur=800)],
                   tags=["venn", "mandala", "explode", "rotate", "background"], score=4)


def v_regions_rank(theme):
    cx, cy = 4.2, 3.85
    es = [V.rotate(V.ellipse(cx + dx, cy + dy, 2.0, 1.05), a, origin=(cx + dx, cy + dy))
          for dx, dy, a in ((-0.55, 0.25, 45), (0.55, 0.25, -45), (-0.15, -0.35, 45), (0.15, -0.35, -45))]
    fr = []
    for g in V.fragment(*es):
        p = g.representative_point()
        fr.append((sum(e.contains(p) for e in es), g))
    fr.sort(key=lambda t: -t[1].area)
    ink, bg = theme.c("ink"), theme.c("bg")
    tone = {1: mix(ink, bg, 0.6), 2: mix(ink, bg, 0.4), 3: mix(ink, bg, 0.2), 4: theme.c("accent")}
    top = fr[:8]
    total = sum(g.area for _, g in fr)

    def st(mode):
        out = []
        x = 1.0
        for k, (n, g) in enumerate(fr):
            if mode == 0:
                out.append(put(f"!!r{k}", g, fill=tone[n], ln=bg, lw=1.2, z=10 + k))
            elif mode == 1:
                c = g.centroid
                out.append(put(f"!!r{k}", g, (c.x - cx) * 0.5, (c.y - cy) * 0.5, fill=tone[n], ln=bg, lw=1.2, z=10 + k))
            else:
                if k < len(top):
                    b = g.bounds
                    s = 0.85
                    w = (b[2] - b[0]) * s
                    out.append(put(f"!!r{k}", g, x + w / 2 - (b[0] + b[2]) / 2, 4.6 - (b[3] - (b[3] - b[1]) * (1 - s) / 2) - 0.0,
                                   s=s, fill=tone[n], ln=bg, lw=1.2, z=10 + k))
                    out.append(label(f"rv{k}", f"{round(100 * g.area / total)}%", x + w / 2, 5.0, w=1.0, sz=15, col="ink2", b=True))
                    x += w + 0.22
                else:
                    out.append(put(f"!!r{k}", g, 0, 0, s=0.01, fill=tone[n], fa=0.0, z=5))
        return out

    fx = [Fx("entrance_fade", f"rv{k}", start="at", delay=0.1 + 0.05 * k, dur=0.25) for k in range(len(top))]
    return Variant("venn", "regions_rank", "Области выстраиваются по размеру",
                   "Четырёхэллипсный Венн разбирается, и восемь крупнейших областей встают в ряд по убыванию "
                   "с долями под ними; мелкие стягиваются в точку. Роль: данные — «какие сегменты самые большие».",
                   [Slide([head("Четыре признака")] + st(0), dur=800),
                    Slide([head("Пятнадцать сегментов")] + st(1), dur=800),
                    Slide([head("Крупнейшие сегменты")] + st(2), dur=900, fx=fx)],
                   tags=["venn", "data", "sort", "fragment"], score=3)


def v_iso_tower(theme):
    cx, cy, r, d = 6.9, 3.6, 1.6, 0.98
    _, fr = venn3(cx, cy, r, d)
    origin = (cx, cy + 0.6)
    ink, bg = theme.c("ink"), theme.c("bg")
    H = {1: 0.25, 2: 0.75, 3: 1.45}
    order = sorted(range(len(fr)), key=lambda k: fr[k][1].centroid.y)  # художник: дальние раньше

    def st(mode):
        out = []
        for zi, k in enumerate(order):
            m, g = fr[k]
            col = vcol(theme, m)
            side = mix(col, bg, 0.45) if sum(m) < 3 else mix(theme.c("accent"), bg, 0.45)
            if mode == 0:
                top_g, side_g = g, g
            else:
                gi = iso(g, origin, tilt=0.48, turn=0.0)
                h = H[sum(m)] if mode == 2 else 0.0
                top_g, side_g = V.move(gi, 0, -h), sweep(gi, h)
            out.append(V.shape(f"!!w{k}", V.resample(side_g, N), fill=side, z=10 + 2 * zi))
            out.append(V.shape(f"!!t{k}", V.resample(top_g, N), fill=col, ln=bg, lw=1.0, z=11 + 2 * zi))
        return out

    leg = [label("l1", "одна область", 1.9, 5.2, w=2.4, sz=15, col="muted", al="l"),
           label("l2", "две", 1.9, 4.6, w=2.4, sz=15, col="ink2", al="l"),
           label("l3", "все три", 1.9, 4.0, w=2.4, sz=15, col="accent", al="l", b=True)]
    return Variant("venn", "iso_tower", "Венн в изометрии: башня совпадений",
                   "Плоский Венн наклоняется в изометрию, и каждая часть вырастает призмой: чем больше кругов её "
                   "покрывает, тем выше. Имитация 3D из 2D. Роль: кульминация раздела, «где совпадает всё».",
                   [Slide([head("Три круга")] + st(0), dur=800),
                    Slide([head("Кладём на плоскость")] + st(1), dur=900),
                    Slide([head("Высота — число совпадений")] + st(2) + leg, dur=900,
                          fx=[Fx("entrance_fade", n, start="at", delay=0.1 + 0.06 * i, dur=0.3) for i, n in enumerate(("l1", "l2", "l3"))])],
                   tags=["venn", "3d", "iso", "space", "data"], score=5)


def v_pop(theme):
    cx, cy, r, d = 7.4, 3.95, 1.5, 0.92
    _, fr = venn3(cx, cy, r, d)
    bg = theme.c("bg")

    def st(lift_m=None):
        out = []
        for k, (m, g) in enumerate(fr):
            col = vcol(theme, m)
            if m == lift_m:
                out.append(put(f"!!sh{k}", g, 0.0, 0.0, fill=mix(bg, theme.c("ink"), 0.08), fa=1.0, z=30))
                out.append(put(f"!!v{k}", g, 0.12, -0.42, s=1.18, fill=col, ln="accent", lw=2.5, z=31))
            else:
                out.append(put(f"!!sh{k}", g, 0.0, 0.0, fill=mix(bg, theme.c("ink"), 0.08), fa=0.0, z=9))
                out.append(put(f"!!v{k}", g, fill=col, ln=bg, lw=1.5, z=10 + k, fa=1.0 if lift_m is None else 0.55))
        return out

    callout = lambda n, t, x, y, k: [label(f"ca{k}", n, x, y, w=3.4, sz=22, col="accent", b=True, al="l"),  # noqa: E731
                                     label(f"cb{k}", t, x, y + 0.5, w=3.4, sz=16, col="ink2", al="l")]
    s0 = Slide([head("Где искать идеи")] + st(), dur=800)
    s1 = Slide([head("Где искать идеи")] + st((1, 1, 0)) + callout("Обучение", "данные встречают модель", 9.65, 1.9, 1),
               dur=750, fx=[Fx("entrance_fade", "ca1", start="at", delay=0.1, dur=0.3), Fx("entrance_fade", "cb1", start="with", delay=0.05, dur=0.3)])
    s2 = Slide([head("Где искать идеи")] + st((0, 1, 1)) + callout("Интерфейс", "модель встречает людей", 9.65, 5.4, 2),
               dur=750, fx=[Fx("entrance_fade", "ca2", start="at", delay=0.1, dur=0.3), Fx("entrance_fade", "cb2", start="with", delay=0.05, dur=0.3)])
    return Variant("venn", "pop", "Область приподнимается",
                   "Выбранная область пересечения приподнимается над схемой (тень остаётся на месте, контур "
                   "акцента), остальные приглушаются; на следующем шаге поднимается соседняя. Роль: выделение "
                   "по шагам рассказа вместо перекраски.",
                   [s0, s1, s2], tags=["venn", "emphasis", "3d", "highlight"], score=4)


def v_split(theme):
    cy = 3.9
    col = [mix(theme.c("ink"), theme.c("bg"), t) for t in (0.3, 0.45, 0.6)]
    names = ["Скорость", "Качество", "Цена"]

    def st(pos, rr, fa, labs=None):
        out = [O(f"!!c{k}", "oval", p[0] - rr, p[1] - rr, 2 * rr, 2 * rr, fill=col[k], fa=fa, z=10 + k) for k, p in enumerate(pos)]
        for k, p in enumerate(labs or []):
            out.append(label(f"!!n{k}", names[k], p[0], p[1], w=1.9, sz=18, col="ink", b=True))
        return out

    one = [(6.65, cy)] * 3
    tri = [(6.65 + 0.85 * math.cos(math.radians(-90 + 120 * k)), cy + 0.85 * math.sin(math.radians(-90 + 120 * k))) for k in range(3)]
    far = [(6.65 + 3.2 * math.cos(math.radians(-90 + 120 * k)) * 1.25, cy + 2.0 * math.sin(math.radians(-90 + 120 * k)) * 1.0 + 0.4)
           for k in range(3)]
    return Variant("venn", "split", "Одна задача делится на три",
                   "Один круг расслаивается на три, которые сначала перекрываются, а потом расходятся в "
                   "самостоятельные направления с подписями. Роль: декомпозиция задачи, вступление к трём частям.",
                   [Slide([head("Одна задача")] + st(one, 1.6, 0.9), dur=800),
                    Slide([head("Три стороны")] + st(tri, 1.45, 0.6), dur=850),
                    Slide([head("Три направления")] + st(far, 1.05, 0.85, far), dur=900)],
                   tags=["venn", "split", "decompose"], score=3)


# ----------------------------------------------------------------------------- живые последовательности

def _piece_set(cx, cy, r, d):
    """Фрагменты Венна + область «только A», заранее разрезанная на 3 дольки (они станут тремя карточками)."""
    from lab._a_util import cut
    _, fr = venn3(cx, cy, r, d)
    ga = fr[0][1]
    b = ga.bounds
    w = b[2] - b[0]
    sl = cut(ga, [[(b[0] + w * k / 3, b[1] - 1), (b[0] + w * k / 3, b[3] + 1)] for k in (1, 2)])
    sl.sort(key=lambda g: g.centroid.x)
    pieces = [(f"a{k}", (1, 0, 0), g) for k, g in enumerate(sl)] + [(f"p{k}", m, g) for k, (m, g) in enumerate(fr[1:])]
    return pieces


def v_seq_story(theme):
    """Один Венн живёт через 9 состояний: собран → разобран → часть уходит в панель → панель делится на карточки →
    карточки возвращаются, маркер идёт по областям → Венн уходит в фон под тезис → части становятся столбиками →
    финальная сборка."""
    n = 120
    bg, ink = theme.c("bg"), theme.c("ink")
    r, d = 1.5, 0.92
    C0 = (8.6, 3.95)
    CL = (3.4, 4.05)
    base = _piece_set(C0[0], C0[1], r, d)
    names = [nm for nm, _, _ in base]
    geo0 = {nm: V.resample(g, n) for nm, _, g in base}
    mem = {nm: m for nm, m, _ in base}
    col = {nm: vcol(theme, m) for nm, m, _ in base}

    def mv(nm, dx, dy):
        return V.move(geo0[nm], dx, dy)

    def venn_at(c, spread=0.0, group_a=True):
        out = {}
        acen = V.union(*[geo0[f"a{k}"] for k in range(3)]).centroid
        for nm in names:
            g = geo0[nm]
            cc = acen if (group_a and nm.startswith("a")) else g.centroid
            dx = c[0] - C0[0] + (cc.x - C0[0]) * spread
            dy = c[1] - C0[1] + (cc.y - C0[1]) * spread
            if nm.startswith("a") and spread:
                dx += (g.centroid.x - acen.x) * 0.25
            out[nm] = V.move(g, dx, dy)
        return out

    def objs(geo, fills=None, fa=None, lw=1.5, z0=10):
        out = []
        for i, nm in enumerate(names):
            f = (fills or {}).get(nm, col[nm])
            out.append(V.shape(f"!!q{nm}", geo[nm], fill=f, fa=(fa or {}).get(nm, 1.0), ln=bg, lw=lw, z=z0 + i))
        return out

    def setlabels(c, k=1.0, show=(0, 1, 2)):
        out = []
        for j in show:
            a = math.radians(-90 + 120 * j)
            rr = (d + r + 0.4) * k
            out.append(label(f"!!sl{j}", SETS[j], c[0] + rr * math.cos(a), c[1] + rr * math.sin(a), w=1.7, sz=16, col="ink2"))
        return out

    slides = []
    # 0 собран
    slides.append(Slide([head("Три силы проекта")] + objs(venn_at(C0)) + setlabels(C0), dur=800))
    # 1 разобран
    slides.append(Slide([head("Из чего он состоит")] + objs(venn_at(C0, 0.55)) + setlabels(C0, 1.35), dur=850))
    # 2 часть «Данные» уходит в панель справа (три дольки = три колонки одной панели)
    g2 = venn_at(CL)
    px, py, pw, ph = 6.9, 2.0, 5.7, 3.7
    for k in range(3):
        g2[f"a{k}"] = V.resample(V.rect(px + pw * k / 3, py, pw / 3 + 0.01, ph, r=0.04), n)
    ghost = put("!!ghost", V.move(fr_only_a := V.union(*[geo0[f"a{k}"] for k in range(3)]), CL[0] - C0[0], CL[1] - C0[1]),
                fill=None, ln=theme.c("muted"), lw=1.25, dash="dash", z=8)
    acc = {f"a{k}": theme.c("accent") for k in range(3)}
    pt = O("p2t", "text", px + 0.35, py + 0.3, pw - 0.7, 0.7, txt="Данные", sz=32, b=True, col="on_accent", z=50)
    pb = O("p2b", "text", px + 0.35, py + 1.1, pw - 0.7, 1.4, txt=["Откуда берём и как проверяем"], sz=19, col="on_accent", z=50)
    slides.append(Slide([head("Начнём с данных"), ghost, pt, pb] + objs(g2, acc, lw=0) + setlabels(CL, show=(1, 2)), dur=900,
                        fx=[Fx("entrance_fade", "p2t", start="at", delay=0.1, dur=0.3), Fx("entrance_fade", "p2b", start="with", delay=0.05, dur=0.3)]))
    # 3 панель делится на три карточки
    g3 = dict(g2)
    cw = (pw - 0.5) / 3
    cards = ["Логи", "Опросы", "Разметка"]
    txt3 = []
    for k in range(3):
        x = px + k * (cw + 0.25)
        g3[f"a{k}"] = V.resample(V.rect(x, py + 0.35 * (k % 2), cw, ph - 0.35, r=0.18), n)
        txt3.append(O(f"c3{k}", "text", x + 0.15, py + 0.35 * (k % 2) + 0.25, cw - 0.3, 0.6, txt=cards[k], sz=22, b=True,
                      col="on_accent", z=50))
        txt3.append(O(f"c3n{k}", "text", x + 0.15, py + 0.35 * (k % 2) + ph - 1.1, cw - 0.3, 0.6, txt=f"0{k + 1}", sz=26,
                      col="on_accent", z=50))
    slides.append(Slide([head("Три источника"), ghost] + txt3 + objs(g3, acc, lw=0) + setlabels(CL, show=(1, 2)), dur=850,
                        fx=[Fx("entrance_fade", t.name, start="at", delay=0.1 + 0.05 * i, dur=0.3) for i, t in enumerate(txt3)]))
    # 4–5 карточки вернулись, маркер идёт по областям
    g4 = venn_at(CL)
    regs = {"ab": V.resample(V.move(dict((m, g) for nm, m, g in base if not nm.startswith("a"))[(1, 1, 0)], CL[0] - C0[0], CL[1] - C0[1]), n),
            "bc": V.resample(V.move(dict((m, g) for nm, m, g in base if not nm.startswith("a"))[(0, 1, 1)], CL[0] - C0[0], CL[1] - C0[1]), n)}

    def step(key, num, t, body):
        return [V.shape("!!mk", regs[key], fill="accent", fa=0.9, ln="accent", lw=2.5, z=40),
                O(f"n{key}", "text", 7.3, 2.1, 1.4, 0.9, txt=num, sz=40, b=True, col="accent", z=50),
                O(f"t{key}", "text", 7.3, 3.05, 5.2, 0.7, txt=t, sz=30, b=True, col="ink", z=50),
                O(f"b{key}", "text", 7.3, 3.85, 5.2, 1.0, txt=body, sz=18, col="ink2", z=50)]

    def sfx(key):
        return [Fx("entrance_fade", f"n{key}", start="at", delay=0.1, dur=0.3), Fx("entrance_fade", f"t{key}", start="with", delay=0.05, dur=0.3),
                Fx("entrance_fade", f"b{key}", start="with", delay=0.05, dur=0.3)]

    slides.append(Slide([head("Где сходятся двое")] + objs(g4) + setlabels(CL) + step("ab", "02", "Обучение", "Данные встречают модель"),
                        dur=850, fx=sfx("ab")))
    slides.append(Slide([head("Где сходятся двое")] + objs(g4) + setlabels(CL) + step("bc", "03", "Интерфейс", "Модель встречает людей"),
                        dur=800, fx=sfx("bc")))
    # 6 Венн уходит в фон: крупно, наклонно, прозрачно; поверх — тезис
    g6 = {nm: V.rotate(V.scale(g, 2.3, origin=(CL[0], CL[1])), 20, origin=(CL[0], CL[1])) for nm, g in g4.items()}
    g6 = {nm: V.move(g, 6.0, 0.3) for nm, g in g6.items()}
    slides.append(Slide([O("q6", "text", 0.8, 2.5, 7.4, 2.4, txt=["Ценность —", "на пересечениях"], sz=48, b=True, col="ink", z=60)]
                        + objs(g6, fa={nm: 0.16 for nm in names}, lw=0, z0=-50), dur=900,
                        fx=[Fx("entrance_fade", "q6", start="at", delay=0.1, dur=0.4)]))
    # 7 части становятся столбиками (три дольки «Данных» — один составной столбик)
    vals = {"a": 2.2, (0, 1, 0): 1.6, (0, 0, 1): 1.2, (1, 1, 0): 2.6, (0, 1, 1): 2.1, (1, 0, 1): 1.4, (1, 1, 1): 3.4}
    order = ["a", (0, 1, 0), (0, 0, 1), (1, 1, 0), (0, 1, 1), (1, 0, 1), (1, 1, 1)]
    bnames = ["Данные", "Модель", "Люди", "Обучение", "Интерфейс", "Разметка", "Продукт"]
    base_y, bw, x0 = 6.0, 1.15, 1.6
    g7, labs7 = {}, []
    for i, key in enumerate(order):
        x = x0 + i * (bw + 0.5)
        hgt = vals[key]
        if key == "a":
            for k in range(3):
                g7[f"a{k}"] = V.resample(V.rect(x, base_y - hgt * (k + 1) / 3, bw, hgt / 3, r=0.02), n)
        else:
            nm = next(nm for nm in names if not nm.startswith("a") and mem[nm] == key)
            g7[nm] = V.resample(V.rect(x, base_y - hgt, bw, hgt, r=0.04), n)
        labs7.append(label(f"bl{i}", bnames[i], x + bw / 2, base_y + 0.3, w=1.6, sz=14, col="ink2"))
    slides.append(Slide([head("Вклад каждой части")] + objs(g7, lw=1.0) + labs7, dur=900,
                        fx=[Fx("entrance_fade", l.name, start="at", delay=0.1 + 0.04 * i, dur=0.25) for i, l in enumerate(labs7)]))
    # 8 сборка
    slides.append(Slide([head("Всё сходится в продукте"), label("fin", "Продукт", 11.6, 3.95, w=1.9, sz=22, col="accent", b=True),
                         O("finl", "line", 9.05, 3.95, 1.55, 0.0, ln="accent", lw=1.5, z=40)] + objs(venn_at(C0)) + setlabels(C0), dur=900,
                        fx=[Fx("entrance_wipe", "finl", start="at", delay=0.1, dur=0.3, options={"direction": "left"}),
                            Fx("entrance_fade", "fin", start="after", dur=0.3)]))
    return Variant("venn", "seq_story", "Венн через весь доклад",
                   "Один Венн из 9 частей проходит 9 состояний: собран, разобран, доля «Данные» уезжает и становится "
                   "панелью, панель делится на три карточки, они возвращаются, маркер идёт по пересечениям, Венн уходит "
                   "в фон под тезис, части становятся столбиками, финальная сборка. Роль: сквозной мотив доклада.",
                   slides, tags=["seq", "venn", "fragment", "card", "navigation", "data", "background"], score=5)


def v_seq_depth(theme):
    """Венн уходит в глубину: два круга → третий въезжает → части → наклон → башня → ядро взлетает панелью →
    башня отходит на фон → плоская сборка."""
    n = 120
    bg, ink = theme.c("bg"), theme.c("ink")
    cx, cy, r, d = 7.6, 3.9, 1.8, 1.08
    cs, fr = venn3(cx, cy, r, d)
    cols3 = [mix(ink, bg, t) for t in (0.5, 0.57, 0.64)]
    names2 = ["Наука", "Рынок", "Люди"]
    origin = (cx, cy + 0.5)
    H = {1: 0.25, 2: 0.7, 3: 1.35}
    order = sorted(range(len(fr)), key=lambda k: fr[k][1].centroid.y)

    def circles(pos, fa=0.6):
        return [O(f"!!o{k}", "oval", p[0] - r, p[1] - r, 2 * r, 2 * r, fill=cols3[k], fa=fa, z=10 + k) for k, p in enumerate(pos)]

    cpos = [(c.centroid.x, c.centroid.y) for c in cs]
    park = [cpos[0], cpos[1], (cpos[2][0] - 0.3, 9.6)]
    two = [(cx - 1.2, cy), (cx + 1.2, cy), park[2]]
    lab2 = lambda pos, show=3: [label(f"!!cn{k}", names2[k], p[0] + (-1.9 if k == 0 else 1.9 if k == 1 else -2.2), p[1] + (0 if k < 2 else 0.9),  # noqa: E731
                                      w=1.6, sz=17, col="ink2", b=True) for k, p in enumerate(pos[:show])]

    def tower(mode, shift=(0.0, 0.0), k=1.0, fa=1.0, lift_core=None):
        out = []
        for zi, j in enumerate(order):
            m, g = fr[j]
            c = vcol(theme, m)
            side = mix(c, bg, 0.45)
            if mode == "flat":
                top_g = side_g = g
            else:
                gi = iso(g, origin, tilt=0.48, turn=0.0)
                h = H[sum(m)] if mode == "tower" else 0.0
                top_g, side_g = V.move(gi, 0, -h), sweep(gi, h)
            top_g = V.move(V.scale(top_g, k, origin=origin), *shift)
            side_g = V.move(V.scale(side_g, k, origin=origin), *shift)
            if lift_core is not None and sum(m) == 3:
                top_g = lift_core
                side_g = V.move(V.scale(iso(g, origin, tilt=0.48, turn=0.0), k, origin=origin), *shift)
                side = theme.c("surface2")
            out.append(V.shape(f"!!w{j}", V.resample(side_g, n), fill=side, fa=fa, z=20 + 2 * zi))
            out.append(V.shape(f"!!t{j}", V.resample(top_g, n), fill=c, fa=fa, ln=bg, lw=1.0, z=21 + 2 * zi))
        return out

    S = []
    S.append(Slide([head("Наука и рынок")] + circles(two) + lab2(two, 2), dur=800))
    S.append(Slide([head("Третий участник")] + circles(cpos) + lab2(cpos), dur=850))
    S.append(Slide([head("Семь зон")] + tower("flat"), dur=700))
    S.append(Slide([head("Кладём на стол")] + tower("iso"), dur=850))
    leg = [label("lg3", "все трое", 1.4, 3.2, w=2.4, sz=16, col="accent", b=True, al="l"),
           label("lg2", "двое", 1.4, 3.75, w=2.4, sz=16, col="ink2", al="l"),
           label("lg1", "один", 1.4, 4.3, w=2.4, sz=16, col="muted", al="l")]
    S.append(Slide([head("Высота — число участников")] + tower("tower") + leg, dur=900,
                   fx=[Fx("entrance_fade", l.name, start="at", delay=0.1 + 0.06 * i, dur=0.3) for i, l in enumerate(leg)]))
    panel = V.resample(V.rect(7.6, 1.6, 5.0, 3.0, r=0.3), n)
    S.append(Slide([head("Ядро — отдельная команда"),
                    O("pc1", "text", 7.95, 1.9, 4.3, 0.7, txt="Общая команда", sz=28, b=True, col="on_accent", z=80),
                    O("pc2", "text", 7.95, 2.7, 4.3, 1.5, txt=["Учёные, продукт", "и пользователи вместе"], sz=19, col="on_accent", z=80)]
                   + tower("tower", shift=(-3.6, 0.9), k=0.75, lift_core=panel), dur=900,
                   fx=[Fx("entrance_fade", "pc1", start="at", delay=0.1, dur=0.3), Fx("entrance_fade", "pc2", start="with", delay=0.05, dur=0.3)]))
    S.append(Slide([O("q", "text", 6.0, 2.6, 6.6, 2.0, txt=["Совпадение —", "редкость и ценность"], sz=40, b=True, col="ink", z=80)]
                   + tower("tower", shift=(-4.6, 1.2), k=1.35, fa=0.18), dur=900,
                   fx=[Fx("entrance_fade", "q", start="at", delay=0.1, dur=0.35)]))
    S.append(Slide([head("Снова плоско и вместе")] + tower("flat"), dur=900))
    return Variant("venn", "seq_depth", "Венн уходит в глубину",
                   "Сквозная фигура в 8 состояниях: два круга, третий въезжает снизу, круги режутся на семь зон, "
                   "плоскость наклоняется, зоны растут призмами, ядро взлетает панелью «Общая команда», башня отходит "
                   "на фон под тезис, и всё складывается обратно в плоский Венн. Роль: «наш путь к совместной работе».",
                   S, tags=["seq", "venn", "3d", "iso", "shape-morph", "background"], score=4)


def variants(theme) -> list[Variant]:
    return [f(theme) for f in (v_seq_story, v_seq_depth, v_explode_lift, v_orbit_piece, v_lens_card, v_to_cards, v_spin_explode, v_nested, v_nav,
                               v_merge, v_five, v_regions_rank, v_iso_tower, v_pop, v_split)]
