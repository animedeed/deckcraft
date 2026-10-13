"""Тематические мотивы вина (пример на открытом наборе UCI Wine Quality: 6497 образцов, 11 показателей + тип;
метрики, разбиение и важность признаков — условные, свои числа — через DECKCRAFT_LAB_DATA).

Мотивы выведены из темы проекта, а не из цветка: бокал с жидкостью (уровень = значение, поверхность всегда
горизонтальна — при наклоне бокала жидкость пересчитывается с сохранением объёма), гроздь (ягоды = точки данных и
разделы, отрываются и раскатываются в группы и столбики, «созревают» как прогресс), кольца-следы от бокала (Венн,
мишень ошибки, накопление по ходу доклада), бочка из клёпок (клёпки = столбики), бутылка в разрезе (слои-этапы
расходятся с объёмными торцами), лоза (растёт по сегментам — линия времени), колесо признаков (как «колесо ароматов»).

Мотивы для переноса в motif.py
------------------------------
Предлагаемый API (по образцу Flower/Orbit): класс мотива хранит форму и постоянные имена частей, метод
`objs(theme, **state)` строит одно состояние; роли собирает трек (`WineTrack`, как MotifTrack):

    Glass(id="gl", R=0.95, Hb=1.8, stem=1.15)            # бокал: чаша + ножка + основание одной формой
        .objs(theme, base=(x, y), s=1.0, tilt=0.0, level=0.6, layers=None, colors=None, ticks=None,
              alpha=1.0, z=20)
        части: !!gl_body (силуэт), !!gl_lq{i} (слои жидкости, n точек), !!gl_srf (поверхность-эллипс),
               !!gl_hl (блик), !!gl_tk{i} (деления); level/layers — доли объёма, tilt — наклон вокруг основания.
        роли: hero (крупно, наклон-«покачивание»), pointer (у края, уровень у деления раздела k),
              progress (деления 25/50/75/100 % — уровень по шагам раздела), data (слои = доли выборок,
              несколько бокалов = значения), backdrop (огромный, alpha≈0.08), pour (наклон + струя в другой бокал).
    Bunch(id="gr", r=0.2, rows=(6, 7, 6, 5, 4, 3, 1))     # гроздь: ягоды-шары (градиент + блик), гребень, лист
        .slots(center, s) -> [(x, y)]                    # места ягод в грозди
        .objs(theme, pos, r, colors, alpha, stalk=(center, s) | None, leaf=True, z=30)
        части: !!gr{i}, !!gr{i}h (ягода, блик), !!gr_stalk, !!gr_leaf; ягоды — носитель: pos задаёт любые места
        (поле точек, группы, столбики, внутри бокала).
        роли: hero, data (ягоды = образцы: тип — цвет, выборка — группа), pointer (гроздь за краем, ряд k — раздел),
              progress (в ряду раздела «созревают» 25/50/75/100 % ягод), zoom (ягода летит по спирали и растёт).
    Stain(id="st") .objs(theme, center, r, seed, alpha, rot)   # кольцо-след: неровное, 1 дырка, + бледная середина
        роли: venn (2–3 следа сходятся), data (радиус = значение — мишень ошибки), backdrop (следы копятся
              по разделам: каждый раздел оставляет новый след).
    Barrel(id, staves=12) — клёпки-полосы цилиндра (освещение по углу) + обручи; роль data: клёпка -> столбик
        (рамка поворачивается на 90°, форма переливается в прямоугольник). Сейчас — функция barrel().
    BottleSlices(id, cuts) — силуэт бутылки, разрезанный на слои-этапы; state(e, dy, dx): e — высота торца-эллипса
        (0 — собрана, 0,2–0,3 — разобрана, видны объёмные торцы). Сейчас — bottle_slices().
    Vine(id, path, nodes) — лоза-линия времени: сегменты-ленты (вход «вытирание» по росту), листья узлов, гроздь-итог.
    FeatureWheel(id, groups) — «колесо ароматов»: группы (внутреннее кольцо) и входы (внешнее); роли hero, data
        (длина сектора = важность), pointer (центр за краем, группа раздела смотрит на заголовок). Сейчас — wheel().

    track = WineTrack(Glass(), theme); track.at("pointer", k=2, n=5); track.at("progress", frac=0.5)
    # WineTrack — как MotifTrack: помнит прошлое состояние (поворот, наклон, уровень), выбирает ближайший угол,
    # хранит «парковку» частей (бокалы val/test за правым краем), чтобы пары !! не рвались между ролями.

Правила мотивов: имена частей постоянны во всех ролях; формы с переливом ресемплятся до одного числа точек;
наклон и поворот — через рамку на оси (pivot), шаг < 180°; цвет ягоды меняется только в одной гамме
(зелёная -> винная — «созревание»), жидкость всегда горизонтальна.
"""

from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from shapely import affinity
from shapely.geometry import box

from morphkit import Fx, O, Slide
from morphkit import vector as V
from morphkit.theme import SLIDE_H, SLIDE_W, mix

from lab import Variant
from lab._d_util import (DEC, S, ball, band, below, biggest, body, chord, cyl_grad, dark, flow, head, kicker, label,
                         level_for_area, light, line, spiral_pivot, stain_ring, stroke, taper, tc, vgrad, vs, bezier)

FAM = "wine"
W, H = SLIDE_W, SLIDE_H

# ----------------------------------------------------------------------------- числа (условные; свои — lab_data())

N_ALL, N_RED, N_WHITE = 6497, 1599, 4898
SPLIT = {"train": 4548, "val": 975, "test": 974}
MAE = {"Сеть": 0.55, "Ridge": 0.60, "Dummy": 0.66}
FEAT_RU = {"density": "плотность", "residual_sugar": "сахар", "volatile_acidity": "летучая кисл.",
           "alcohol": "спирт", "wine_type": "тип вина", "total_sulfur_dioxide": "общий SO₂", "sulphates": "сульфаты",
           "free_sulfur_dioxide": "свободный SO₂", "fixed_acidity": "фикс. кисл.", "ph": "pH",
           "citric_acid": "лимонная к.", "chlorides": "хлориды"}
# условная важность признаков (форма убывания, не результат исследования)
_IMP_SAMPLE = [0.15, 0.10, 0.06, 0.05, 0.042, 0.035, 0.029, 0.023, 0.019, 0.014, 0.009, 0.006]
_RIDGE_ORDER = [1, 0, 3, 2, 6, 4, 5, 9, 7, 8, 11, 10]  # условный порядок важности у линейной модели


def lab_data() -> dict:
    """Свои числа для вариантов лаборатории: JSON по пути из DECKCRAFT_LAB_DATA с ключами
    importance / importance_ridge ({признак: значение}), mae, split. Без него — условные значения."""
    import json
    import os
    path = os.environ.get("DECKCRAFT_LAB_DATA")
    try:
        return json.loads(Path(path).read_text()) if path else {}
    except (OSError, ValueError):
        return {}


def importance(which: str = "importance") -> list[tuple[str, float]]:
    """Важность признаков (рост ошибки при перестановке), по убыванию; числа на слайды не выводятся."""
    d = lab_data().get(which)
    if d:
        return sorted(((FEAT_RU.get(k, k), float(v)) for k, v in d.items()), key=lambda kv: -kv[1])
    names = list(FEAT_RU.values())
    if which == "importance_ridge":
        return [(names[i], _IMP_SAMPLE[r]) for r, i in enumerate(_RIDGE_ORDER)]
    return list(zip(names, _IMP_SAMPLE))


QUALITY = {3: 20, 4: 150, 5: 1490, 6: 2010, 7: 760, 8: 110, 9: 8}  # баллы в train (только форма, без чисел)


def ru(v: float, nd: int = 3) -> str:
    return f"{v:.{nd}f}".replace(".", ",")


def wine_cols(theme):
    red = tc(theme, "red_wine", "accent")
    white = tc(theme, "white_wine", "accent3")
    return red, white


# ============================================================================= мотив 1: бокал

@dataclass
class Glass:
    """Бокал-тюльпан: силуэт (чаша + ножка + основание) одной формой, жидкость слоями, эллипс поверхности, блик.
    Геометрия строится в единичном масштабе и масштабируется вокруг основания — число точек одинаково при любом s
    и наклоне, поэтому Morph честно переливает и двигает бокал."""
    id: str = "gl"
    R: float = 0.95
    Hb: float = 1.8
    stem: float = 1.15
    wall: float = 0.05
    n: int = 120

    def _base_geom(self, base):
        bx, by = base
        R, Hb = self.R, self.Hb
        ybb = by - self.stem - 0.08 * R
        Ry = 0.6 * Hb
        bowl = V.ellipse(bx, ybb - Ry, R, Ry, seg=40).intersection(box(bx - 2 * R, ybb - Hb, bx + 2 * R, ybb + 1))
        stem = V.polygon([(bx - 0.07 * R, ybb - 0.05), (bx + 0.07 * R, ybb - 0.05), (bx + 0.035 * R, ybb + 0.25 * self.stem),
                          (bx + 0.035 * R, by - 0.2 * R), (bx + 0.16 * R, by - 0.08 * R),
                          (bx - 0.16 * R, by - 0.08 * R), (bx - 0.035 * R, by - 0.2 * R),
                          (bx - 0.035 * R, ybb + 0.25 * self.stem)])
        foot = V.ellipse(bx, by - 0.07 * R, 0.74 * R, 0.075 * R, seg=24)
        outline = biggest(V.union(bowl, stem, foot).buffer(0))
        interior = bowl.buffer(-self.wall)
        hl = V.petal((bx - 0.6 * R, ybb - 0.22 * Hb), 0.0, 0.5 * Hb, 0.1 * R, angle=-97)
        return outline, interior, hl, ybb - Hb

    def geom(self, base, s: float = 1.0):
        out = []
        for g in self._base_geom(base)[:3]:
            out.append(affinity.scale(g, s, s, origin=base))
        rim = base[1] - (base[1] - self._base_geom(base)[3]) * s
        return out[0], out[1], out[2], rim

    def rim_y(self, base, s: float = 1.0) -> float:
        return self.geom(base, s)[3]

    def objs(self, theme, base=(9.5, 6.4), s: float = 1.0, tilt: float = 0.0, level: float = 0.55,
             layers: Sequence[float] | None = None, colors: Sequence[str] | None = None, ticks: Sequence[float] | None = None,
             tick_on: int | None = None, alpha: float = 1.0, z: int = 20, glass_fill: str | None = None,
             surface: bool = True, nlayers: int | None = None, rock: bool = True) -> list[O]:
        """level — доля объёма чаши (0..1); layers — доли слоёв снизу вверх (в сумме ≤ 1), имеют приоритет над level.
        nlayers — сколько слоёв-объектов держать (лишние — нулевые тонкие у поверхности: пары сохраняются)."""
        red, _ = wine_cols(theme)
        outline, interior, hl, _rim = self.geom(base, s)
        bg = theme.c("bg")
        # ось наклона: на столе — край основания (бокал не «взлетает»), в воздухе (rock=False) — центр основания
        piv = base if (tilt == 0 or not rock) else (base[0] + math.copysign(0.74 * self.R * s, tilt), base[1])
        base_ = base
        base = piv
        gf = glass_fill or mix(bg, theme.c("line"), 0.45)
        out = [vs(f"!!{self.id}_body", outline, pivot=piv, rot=tilt % 360, fill=gf, fa=0.55 * alpha, ln="muted",
                  lw=1.1, la=0.9 * alpha, z=z, meta=dict(DEC))]
        fr = list(layers) if layers is not None else [level]
        nl = nlayers or len(fr)
        fr = fr + [0.0] * (nl - len(fr))
        cols = list(colors) if colors else [red] * nl
        cols = cols + [cols[-1]] * (nl - len(cols))
        wint = affinity.rotate(interior, tilt, origin=base)
        A = interior.area
        cum, ys = 0.0, []
        for f in fr:
            cum += max(f, 0.0)
            ys.append(level_for_area(wint, max(min(cum, 0.97), 0.012) * A))
        y_prev = 1e3
        for i, (y, c) in enumerate(zip(ys, cols)):
            y_top = min(y, y_prev - 0.012)
            g = band(wint, y_top, y_prev)
            if g.is_empty or g.area < 1e-4:
                g = band(wint, y_prev - 0.012, y_prev) if y_prev < 1e2 else below(wint, ys[0])
            loc = affinity.rotate(g, -tilt, origin=piv)
            out.append(vs(f"!!{self.id}_lq{i}", loc, self.n, start=90, pivot=piv, rot=tilt % 360, fill=c, fa=alpha,
                          grad=vgrad(c, alpha, 0.12, 0.28), z=z + 1 + i, meta=dict(DEC)))
            y_prev = y_top
        if surface:
            yt = y_prev
            ch = chord(wint, yt)
            if ch:
                xa, xb = ch
                e = 0.16 * (xb - xa)
                out.append(O(f"!!{self.id}_srf", "oval", xa, yt - e / 2, xb - xa, e, fill=light(cols[len(fr) - 1 - [f > 0 for f in fr][::-1].index(True)] if any(f > 0 for f in fr) else cols[0], 0.22),
                             fa=alpha, z=z + 1 + nl, meta=dict(DEC)))
        out.append(vs(f"!!{self.id}_hl", hl, pivot=piv, rot=tilt % 360, fill="FFFFFF", fa=0.65 * alpha, z=z + 2 + nl,
                      meta=dict(DEC)))
        if ticks:
            for i, f in enumerate(ticks):
                yy = level_for_area(interior, f * A)
                ch = chord(interior, yy)
                if not ch:
                    continue
                on = tick_on is not None and i <= tick_on
                x1 = ch[1] + self.wall * s
                out.append(line(f"!!{self.id}_tk{i}", (x1 - 0.22 * s, yy), (x1 + 0.05, yy), ln="accent" if on else "muted",
                                lw=2.0 if on else 1.0, z=z + 3 + nl))
        return out

    def tick_y(self, base, s: float, f: float) -> tuple[float, float]:
        _o, interior, _h, _r = self.geom(base, s)
        yy = level_for_area(interior, f * interior.area)
        return chord(interior, yy)[1] + self.wall * s, yy

    def mouth(self, base, s: float, tilt: float) -> tuple[float, float]:
        """Точка края чаши (правый край ободка) с учётом наклона — откуда льётся струя."""
        outline, _i, _h, rim = self.geom(base, s)
        ch = chord(outline, rim + 0.01)
        from lab._d_util import rot_pt
        return rot_pt((ch[1], rim), tilt, base)


# ============================================================================= мотив 2: гроздь

def vine_leaf(cx: float, cy: float, size: float, angle: float = 0.0):
    """Лист винограда: пять лопастей-линз из одной точки + сердцевина; angle — поворот листа."""
    base = (cx, cy)
    parts = [V.petal(base, 0.0, size * L, size * L * 0.78, -90 + a) for a, L in
             ((0, 1.0), (-48, 0.86), (48, 0.86), (-105, 0.58), (105, 0.58))]
    g = V.union(*parts, V.circle(cx, cy - size * 0.28, size * 0.36)).buffer(size * 0.04).buffer(-size * 0.04)
    return V.rotate(biggest(g), angle, origin=base)


@dataclass
class Bunch:
    """Гроздь: ягоды по рядам (обратный треугольник), гребень и лист. Ягоды — носитель: их места задаёт вызывающий."""
    id: str = "gr"
    r: float = 0.2
    rows: Sequence[int] = (6, 7, 6, 5, 4, 3, 1)

    @property
    def count(self) -> int:
        return sum(self.rows)

    def slots(self, center=(9.5, 3.9), s: float = 1.0, seed: int = 3) -> list[tuple[float, float]]:
        rnd = random.Random(seed)
        r = self.r * s
        dy = r * 1.62
        top = center[1] - dy * (len(self.rows) - 1) / 2
        out = []
        for i, c in enumerate(self.rows):
            x0 = center[0] - (c - 1) * r * 1.02
            for j in range(c):
                out.append((x0 + j * r * 2.04 + rnd.uniform(-0.06, 0.06) * r, top + i * dy + rnd.uniform(-0.08, 0.08) * r))
        return out

    def row_of(self) -> list[int]:
        return [i for i, c in enumerate(self.rows) for _ in range(c)]

    def stalk(self, center, s: float = 1.0):
        top = self.slots(center, s)[0][1] - self.r * s
        cx = center[0]
        pts = bezier((cx + 0.05 * s, top + 0.5 * s), (cx, top), (cx + 0.1 * s, top - 0.45 * s), (cx + 0.45 * s, top - 0.75 * s), 24)
        return taper(pts, 0.1 * s, 0.05 * s), (cx + 0.45 * s, top - 0.75 * s)

    def objs(self, theme, pos: Sequence[tuple[float, float]], r: float | Sequence[float] | None = None,
             colors: Sequence[str] | str | None = None, alpha: float | Sequence[float] = 1.0,
             stalk: tuple | None = None, leaf: bool = True, z: int = 30, hl: bool = True) -> list[O]:
        red, _ = wine_cols(theme)
        n = len(pos)
        rs = [r or self.r] * n if not isinstance(r, (list, tuple)) else list(r)
        cs = [colors or red] * n if isinstance(colors, str) or colors is None else list(colors)
        fas = [alpha] * n if isinstance(alpha, (int, float)) else list(alpha)
        out = []
        if stalk is not None:
            c, s, a = (stalk + (1.0,))[:3] if len(stalk) == 2 else stalk
            g, tip = self.stalk(c, s)
            brown = mix(theme.c("accent2"), "6B4A2B", 0.6)
            out.append(vs(f"!!{self.id}_stalk", g, 80, fill=brown, fa=a, z=z - 2, meta=dict(DEC)))
            if leaf:
                lf = vine_leaf(tip[0] - 0.05 * s, tip[1] + 0.05 * s, 1.0 * s, angle=55)
                green = theme.c("accent2")
                out.append(vs(f"!!{self.id}_leaf", lf, 160, fill=green, fa=a,
                              grad=V.gradient([(0, light(green, 0.25), a), (1, dark(green, 0.25), a)], angle=60),
                              ln=dark(green, 0.3), lw=0.75, la=a, z=z - 3, meta=dict(DEC)))
        # нижние ряды поверх верхних (ближе к зрителю)
        order = sorted(range(n), key=lambda i: pos[i][1])
        for rank, i in enumerate(order):
            x, y = pos[i]
            out += ball(theme, f"!!{self.id}{i}", x, y, max(rs[i], 0.004), cs[i], z=z + 2 * rank, fa=fas[i],
                        hl=hl and rs[i] > 0.05, hl_a=0.6)
        return out


# ============================================================================= мотив 3: след бокала

@dataclass
class Stain:
    id: str = "st"

    def objs(self, theme, center, r: float, seed: int = 1, alpha: float = 1.0, c: str | None = None, rot: float = 0.0,
             th: float | None = None, z: int = 4, name: str | None = None) -> list[O]:
        c = c or wine_cols(theme)[0]
        nm = name or self.id
        ring = stain_ring(center[0], center[1], r, th or max(0.05, r * 0.07), seed=seed)
        disc = V.resample(ring.exterior.buffer(0) if False else V.polygon(list(ring.exterior.coords)), 160)
        return [vs(f"!!{nm}_in", disc, 0, pivot=center, rot=rot % 360, fill=c, fa=0.07 * alpha, z=z, meta=dict(DEC)),
                V.shape(f"!!{nm}", ring, pivot=center, rot=rot % 360, fill=c, fa=0.5 * alpha, z=z + 1, meta=dict(DEC))]


# ============================================================================= варианты

def _v(key, title, idea, slides, tags, score) -> Variant:
    return Variant(FAM, key, title, idea, slides, tags=tags, score=score)


SECTIONS = ["Данные", "Разбиение", "Модель", "Результаты"]


def seq_bunch(theme) -> Variant:
    """Живая гроздь через всю колоду: обложка -> поле данных -> три группы -> давим в бокалы -> бокал train
    наливает модель -> гроздь у края как навигация с прогрессом -> бокал-фон под графиком -> финал."""
    red, white = wine_cols(theme)
    B = Bunch("gr", r=0.21)
    n = B.count  # 32: 8 красных + 24 белых (1599 / 4898 ≈ 25 %)
    types = [0] * 8 + [1] * 24
    rnd = random.Random(5)
    order = list(range(n))
    rnd.shuffle(order)
    tcol = [red if types[i] == 0 else light(white, 0.15) for i in range(n)]
    hero_c = (9.6, 3.95)
    slots = B.slots(hero_c, 1.25)
    hero_pos = [slots[order[i]] for i in range(n)]
    S_ = []

    # 1. обложка: гроздь собирается
    o1 = B.objs(theme, hero_pos, r=B.r * 1.25, colors=tcol, stalk=(hero_c, 1.25)) + [
        kicker("пример · этапы 1–7"),
        O("!!cov", "text", 0.7, 1.0, 5.6, 1.7, txt=["Качество вина", "по анализу"], sz=44, b=True, font="head",
          col="ink", spacing=0.95, z=90),
        body("!!csub", 0.7, 2.9, 5.2, 0.9, "11 показателей лаборатории → балл экспертов", sz=18)]
    fx1 = [Fx("entrance_zoom", f"!!gr{i}", start="at", delay=0.1 + 0.025 * k, dur=0.35)
           for k, i in enumerate(sorted(range(n), key=lambda i: hero_pos[i][1]))]
    S_.append(S(o1, 800, fx=fx1))

    # 2. ягоды -> поле образцов (красные слева)
    grid = []
    reds = [i for i in range(n) if types[i] == 0]
    whites = [i for i in range(n) if types[i] == 1]
    gpos = {}
    for k, i in enumerate(reds):
        gpos[i] = (1.2 + (k % 2) * 0.62, 2.6 + (k // 2) * 0.62)
    for k, i in enumerate(whites):
        gpos[i] = (3.3 + (k % 6) * 0.62, 2.6 + (k // 6) * 0.62)
    grid = [gpos[i] for i in range(n)]
    o2 = B.objs(theme, grid, r=0.24, colors=tcol, stalk=((11.6, 4.6), 0.9, 0.25)) + [
        head("6497 образцов", y=0.5), body("!!b2", 0.7, 1.3, 7.5, 0.4, "одна ягода ≈ 200 образцов", sz=14, col="muted"),
        label("!!lr", 1.51, 5.15, "1599 красных", w=2.0, al="c", b=True, col="accent"),
        label("!!lw", 4.85, 5.15, "4898 белых", w=2.0, al="c", b=True, col="ink2")]
    S_.append(S(o2, 900))

    # 3. разбиение: три горки над бокалами (22 / 5 / 5)
    groups = [0] * 22 + [1] * 5 + [2] * 5
    gorder = list(range(n))
    random.Random(9).shuffle(gorder)
    grp = {gorder[k]: groups[k] for k in range(n)}
    gx = [3.0, 6.7, 10.4]
    G = [Glass(f"g{j}", R=0.85, Hb=1.6, stem=0.95) for j in range(3)]
    gbase = [(x, 6.55) for x in gx]
    pile = {}
    cnt = [0, 0, 0]
    for i in range(n):
        g = grp[i]
        k = cnt[g]
        cnt[g] += 1
        cols = 6 if g == 0 else 3
        pile[i] = (gx[g] - (cols - 1) * 0.25 + (k % cols) * 0.5, 3.4 - (k // cols) * 0.44)
    p3 = [pile[i] for i in range(n)]
    lab3 = [label(f"!!gl{j}", gx[j], 1.4, t, w=2.6, b=True, col="accent" if j == 0 else "ink2")
            for j, t in enumerate(["train · 4548", "val · 975", "test · 974"])]
    o3 = B.objs(theme, p3, r=0.21, colors=tcol) + [head("Разбиение 70 / 15 / 15")] + lab3
    for j in range(3):
        o3 += G[j].objs(theme, gbase[j], level=0.02, z=10)
    S_.append(S(o3, 900))

    # 4. ягоды «давим» в бокалы: уровень = доля выборки
    shares = [SPLIT["train"] / N_ALL, SPLIT["val"] / N_ALL, SPLIT["test"] / N_ALL]
    p4, r4 = [], []
    for i in range(n):
        g = grp[i]
        _o, _in, _h, rim = G[g].geom(gbase[g])
        y_srf = level_for_area(_in, shares[g] * _in.area)
        p4.append((gx[g] + random.Random(i).uniform(-0.3, 0.3), y_srf))
        r4.append(0.004)
    o4 = B.objs(theme, p4, r=r4, colors=tcol, hl=False, alpha=0.0) + [head("Объём бокала — доля выборки")] + lab3
    for j in range(3):
        o4 += G[j].objs(theme, gbase[j], level=shares[j], z=10, colors=[red])
    S_.append(S(o4, 900))

    # 5. бокал train наклоняется и «наливает» модель 13 → 32 → 1 (сверху вниз, как фильтр)
    tb = (1.0, 3.1)
    tilt = 70
    o5 = B.objs(theme, [(8.1, 6.25)] * n, r=0.004, colors=tcol, hl=False, alpha=0.0) + [
        head("Модель 13 → 32 → 1", x=5.0, w=7.6)]
    o5 += G[0].objs(theme, tb, s=0.95, tilt=tilt, level=shares[0] * 0.8, z=10, rock=False)
    o5 += G[1].objs(theme, (14.6, 6.55), level=shares[1], z=10)  # за правый край
    o5 += G[2].objs(theme, (15.6, 6.55), level=shares[2], z=10)
    mx, my = G[0].mouth(tb, 0.95, tilt)
    ins = [(4.8 + k * 0.55, 3.6) for k in range(13)]
    hid = [(4.3 + k * 0.24, 5.0) for k in range(32)]
    outp = (8.1, 6.25)
    net = []
    for a_, (x, y) in enumerate(ins):
        for b_ in (a_ * 32 // 13, (a_ * 32 // 13 + 11) % 32):
            net.append(line(f"nl{a_}_{b_}", (x, y), hid[b_], ln="line", lw=0.75, z=3))
    for b_, (x, y) in enumerate(hid):
        net.append(line(f"nh{b_}", (x, y), outp, ln="line", lw=0.6, z=3))
    net += [O(f"ni{k}", "oval", x - 0.09, y - 0.09, 0.18, 0.18, fill=red, z=8) for k, (x, y) in enumerate(ins)]
    net += [O(f"nd{k}", "oval", x - 0.05, y - 0.05, 0.1, 0.1, fill="ink2", z=8) for k, (x, y) in enumerate(hid)]
    net += [O("no", "oval", outp[0] - 0.17, outp[1] - 0.17, 0.34, 0.34, fill="accent", z=8)]
    stream = vs("pour", stroke(bezier((mx, my), (mx + 0.5, my - 0.05), (4.55, my + 0.1), (4.75, 3.45), 30), 0.07),
                fill=red, fa=0.85, z=9, meta=dict(DEC))
    loops = [flow([ins[k], hid[k * 32 // 13]], n=2, period=1.8, size=0.09, name=f"sig_{k}") for k in (1, 6, 11)]
    loops += [flow([hid[b_], outp], n=2, period=2.3, size=0.09, name=f"sig_h{b_}", start=0.4) for b_ in (4, 20, 28)]
    S_.append(S(o5 + net + [stream] + [label("!!n5", 11.75, 3.45, "13 входов", w=1.5, al="l"),
                                       label("!!n6", 12.0, 4.85, "32", w=0.9, al="l"),
                                       label("!!n7", 8.45, 6.1, "балл", w=1.2, al="l", b=True, col="accent")],
                900, loops=loops, fx=[Fx("entrance_wipe", "pour", start="at", delay=0.1, dur=0.45,
                                         options={"direction": "left"})]))

    # 6–7. гроздь у левого края — навигация; ряды = разделы, в текущем «созревает» доля ягод
    nav_c = (0.15, 3.75)
    nav = B.slots(nav_c, 1.05)
    rowsec = [0, 0, 1, 1, 2, 3, 3]  # ряд -> раздел
    rows = B.row_of()
    row_y = [nav[rows.index(r_)][1] for r_ in range(len(B.rows))]
    green = mix(theme.c("accent2"), "C8D3A0", 0.45)

    def nav_cols(sec, frac):
        out = []
        sec_idx = [i for i in range(n) if rowsec[rows[i]] == sec]
        lit = set(sec_idx[:round(frac * len(sec_idx))])
        for i in range(n):
            sr = rowsec[rows[i]]
            out.append(red if (sr < sec or i in lit) else (light(red, 0.55) if sr == sec else green))
        return out

    # ягода i бокала -> место i в грозди (ягоды «вырастают» снова)
    def nav_slide(sec, frac, title, text, extra=(), fx=()):
        objs = B.objs(theme, nav, r=B.r * 1.05, colors=nav_cols(sec, frac), stalk=(nav_c, 1.05))
        objs += [kicker(f"раздел {sec + 1} · {SECTIONS[sec]}", x=4.2), head(title, x=4.2, w=8)]
        objs += [body("!!txt", 4.2, 1.6, 7.0, 2.0, text, sz=18)]
        objs += [label(f"!!sec{k}", 2.0, row_y[rowsec.index(k)] - 0.15, f"{k + 1} {SECTIONS[k]}", w=1.9, al="l",
                       col="accent" if k == sec else "muted", b=k == sec, sz=13) for k in range(4)]
        return objs + list(extra)

    o6 = nav_slide(2, 0.5, "Архитектура", ["13 входов: 11 показателей и тип вина", "32 нейрона скрытого слоя",
                                           "1 выход — балл"])
    o6 += G[0].objs(theme, (16.5, 6.2), s=0.95, tilt=0, level=0.3, z=10)
    o6 += G[1].objs(theme, (17.6, 6.55), level=shares[1], z=10)
    o6 += G[2].objs(theme, (18.6, 6.55), level=shares[2], z=10)
    S_.append(S(o6, 900))
    o7 = nav_slide(2, 0.75, "Обучение", ["ранняя остановка по val", "test открыт один раз"])
    o7 += G[0].objs(theme, (16.5, 6.2), s=0.95, tilt=0, level=0.3, z=10)
    o7 += G[1].objs(theme, (17.6, 6.55), level=shares[1], z=10)
    o7 += G[2].objs(theme, (18.6, 6.55), level=shares[2], z=10)
    S_.append(S(o7, 700))

    # 8. результаты: бокал train — огромный бледный фон под столбиками MAE; гроздь — раздел 4
    o8 = nav_slide(3, 0.25, "MAE на test", [])
    o8 = [o for o in o8 if o.name != "!!txt"]
    o8 += G[0].objs(theme, (8.6, 9.6), s=2.9, level=0.45, alpha=0.1, z=-50)
    o8 += G[1].objs(theme, (17.6, 6.55), level=shares[1], z=10)
    o8 += G[2].objs(theme, (18.6, 6.55), level=shares[2], z=10)
    for k, (nm, v) in enumerate(MAE.items()):
        y = 2.3 + k * 1.15
        L = v / 0.66 * 6.2
        o8 += [label(f"!!ml{k}", 3.6, y + 0.1, nm, w=1.3, al="r", b=k == 0, col="ink" if k == 0 else "ink2", sz=16),
               O(f"!!mb{k}", "rect", 3.75, y, L, 0.5, fill="accent" if k == 0 else "muted", z=40),
               label(f"!!mv{k}", 3.85 + L, y + 0.1, ru(v), w=1.0, al="l", b=k == 0, sz=16,
                     col="accent" if k == 0 else "ink2")]
    S_.append(S(o8, 900, fx=[Fx("entrance_wipe", f"!!mb{k}", start="at", delay=0.15 + 0.12 * k, dur=0.4,
                                options={"direction": "left"}) for k in range(3)]))

    # 9. финал: гроздь снова собирается героем, все ягоды «созрели» в свои цвета
    o9 = B.objs(theme, hero_pos, r=B.r * 1.25, colors=tcol, stalk=(hero_c, 1.25)) + [
        O("!!fin", "text", 0.7, 1.4, 5.6, 1.6, txt=["MAE 0,55", "лучше Ridge и Dummy"], sz=36, b=True, font="head",
          col="ink", spacing=0.95, z=90),
        body("!!fsub", 0.7, 3.2, 5.2, 0.9, "6497 образцов · 13 → 32 → 1", sz=18)]
    o9 += G[0].objs(theme, (16.5, 6.2), s=0.95, level=0.3, z=10)
    o9 += G[1].objs(theme, (17.6, 6.55), level=shares[1], z=10)
    o9 += G[2].objs(theme, (18.6, 6.55), level=shares[2], z=10)
    S_.append(S(o9, 900))
    return _v("seq_bunch", "Гроздь живёт через колоду",
              "Одна гроздь проходит 9 состояний: обложка → ягоды-образцы (красные/белые) → три горки train/val/test → "
              "ягоды «давятся» в бокалы, уровень = доля выборки → бокал train наклоняется и наливает модель → гроздь у "
              "края — навигация, в ряду раздела созревают ягоды (прогресс) → бокал — бледный фон под MAE → финал.",
              S_, ["seq", "wine", "carrier", "navigation", "progress", "backdrop", "data"], 5)


# ----------------------------------------------------------------------------- общие мелочи

def rename(objs: list[O], mapping: dict[str, str]) -> list[O]:
    return [o.copy(name=mapping.get(o.name, o.name)) for o in objs]


def drop(objs: list[O], *names: str) -> list[O]:
    return [o for o in objs if o.name not in names]


def table(theme, y: float = 6.62, x0: float = 0.0, x1: float = W, name: str = "!!table") -> list[O]:
    return [line(name, (x0, y), (x1, y), ln="line", lw=1.0, z=2)]


# ============================================================================= бокал: одиночные варианты

def glass_swirl(theme) -> Variant:
    G = Glass("gl", R=1.15, Hb=2.2, stem=1.45)
    base = (9.4, 6.62)
    t = [kicker("пример"), O("!!cov", "text", 0.7, 1.0, 5.4, 1.7, txt=["Качество вина", "до дегустации"],
                                       sz=44, b=True, font="head", col="ink", spacing=0.95, z=90)]
    sh = lambda a: [O("!!shadow", "oval", base[0] - 1.0 - a * 0.02, base[1] - 0.06, 2.0, 0.14, fill="line", fa=0.5, z=2)]  # noqa: E731
    sl = [S(t + sh(0) + table(theme) + G.objs(theme, base, tilt=0, level=0.5), 700),
          S(t + sh(-14) + table(theme) + G.objs(theme, base, tilt=-14, level=0.5) +
            [body("!!b1", 0.7, 3.0, 5.2, 0.9, "жидкость всегда горизонтальна: объём пересчитан при наклоне", sz=16)], 800),
          S(t + sh(12) + table(theme) + G.objs(theme, base, tilt=12, level=0.5) +
            [body("!!b1", 0.7, 3.0, 5.2, 0.9, "жидкость всегда горизонтальна: объём пересчитан при наклоне", sz=16)], 800)]
    return _v("glass_swirl", "Бокал качается, вино горизонтально",
              "Обложка-герой: бокал наклоняется вокруг основания (рамка на оси), слой вина пересчитан с сохранением "
              "объёма — поверхность остаётся горизонтальной, эллипс поверхности даёт объём. Живая обложка без текста-фокусов.",
              sl, ["wine", "hero", "physics", "pivot", "3d"], 4)


def glass_steps(theme) -> Variant:
    """Прогресс внутри раздела: 4 деления бокала = 4 темы раздела; уровень — по шагам 25/50/75/100 %."""
    G = Glass("gp", R=0.95, Hb=1.85, stem=1.2)
    base = (10.4, 6.6)
    topics = ["Пропуски", "Копии строк", "Масштаб", "Утечки"]
    ticks = [0.25, 0.5, 0.75, 1.0 * 0.96]
    sl = []
    for k in range(3):
        objs = G.objs(theme, base, level=ticks[k] * 0.96 + 0.0, ticks=ticks, tick_on=k)
        for i, tp in enumerate(topics):
            x, y = G.tick_y(base, 1.0, ticks[i])
            objs.append(label(f"!!tp{i}", x + 0.15, y - 0.16, tp, w=1.9, al="l", sz=13, b=i == k,
                              col="accent" if i == k else ("ink2" if i < k else "muted")))
        objs += [kicker("раздел 2 · подготовка данных"), head(f"Шаг {k + 1}: {topics[k].lower()}", w=7),
                 body("!!pct", 0.7, 1.4, 4, 0.4, f"{(k + 1) * 25} % раздела", sz=14, col="muted")]
        sl.append(S(objs, 700))
    return _v("glass_steps", "Деления бокала: шаги раздела",
              "Прогресс внутри раздела (идея пользователя): 4 деления = 4 темы раздела, вино поднимается на одно "
              "деление за шаг (25 → 50 → 75 %), текущая метка — акцентом. Небольшой бокал справа на слайдах раздела.",
              sl, ["wine", "progress", "navigation"], 4)


def glass_pointer(theme) -> Variant:
    """Указатель у края: огромный бокал срезан левым краем, деления = разделы, уровень = текущий раздел."""
    G = Glass("gq", R=0.95, Hb=1.85, stem=1.2)
    base = (0.2, 9.0)
    s = 2.35
    secs = ["Данные", "Признаки", "Модель", "Результаты"]
    ticks = [0.2, 0.42, 0.64, 0.86]
    sl = []
    for k in range(3):
        objs = G.objs(theme, base, s=s, level=ticks[k], ticks=ticks, tick_on=k)
        for i, tp in enumerate(secs):
            x, y = G.tick_y(base, s, ticks[i])
            objs.append(label(f"!!sc{i}", x + 0.15, y - 0.17, f"0{i + 1} {tp}", w=2.0, al="l", sz=13, b=i == k,
                              col="accent" if i == k else "muted"))
        objs += [kicker(f"раздел {k + 1}", x=5.6), head(secs[k], x=5.6, w=7),
                 body("!!txt", 5.6, 1.5, 6.8, 1.6, ["6497 образцов: 1599 красных, 4898 белых",
                                                   "11 показателей + тип вина = 13 входов",
                                                   "MLP 13 → 32 → 1"][k], sz=18)]
        sl.append(S(objs, 800))
    return _v("glass_pointer", "Бокал у края: раздел = деление",
              "Навигация: бокал в 2,3 раза больше, срезан левым краем (видна правая половина чаши). Деления — разделы "
              "доклада с подписями; уровень вина поднимается к делению текущего раздела. Рядом — содержание раздела.",
              sl, ["wine", "pointer", "navigation", "bleed"], 4)


def glass_quality(theme) -> Variant:
    """Данные: слои вина по баллам 3…9 -> семь бокалов, уровень = число образцов с этим баллом (train)."""
    red, _ = wine_cols(theme)
    big = Glass("gb", R=1.1, Hb=2.1, stem=1.35)
    base = (9.6, 6.6)
    tot = sum(QUALITY.values())
    qs = list(QUALITY)
    shades = [mix(red, theme.c("bg"), 0.7 - 0.11 * i) for i in range(7)]
    lay = [QUALITY[q] / tot * 0.9 for q in qs]
    o1 = big.objs(theme, base, layers=lay, colors=shades) + [head("Баллы экспертов"),
                                                            body("!!b", 0.7, 1.4, 5.5, 0.8, "train: 4548 образца, баллы 3–9", sz=16)]
    small = [Glass(f"gs{i}", R=0.5, Hb=1.0, stem=0.62) for i in range(7)]
    top = max(QUALITY.values())
    o2 = [head("Баллы экспертов"), body("!!b", 0.7, 1.4, 5.5, 0.8, "train: 4548 образца, баллы 3–9", sz=16)]
    for i, q in enumerate(qs):
        b2 = (1.6 + i * 1.65, 6.4)
        g = small[i].objs(theme, b2, level=max(QUALITY[q] / top * 0.92, 0.015), colors=[shades[i]])
        o2 += rename(g, {f"!!gs{i}_lq0": f"!!gb_lq{i}"})
        o2.append(label(f"q{i}", b2[0], 6.5, str(q), w=0.6, b=True, sz=16))
    o2 = drop(o2) + []
    sl = [S(o1, 800), S(o2, 900, fx=[Fx("entrance_fade", f"q{i}", start="at", delay=0.2 + 0.05 * i) for i in range(7)])]
    return _v("glass_quality", "Слои бокала разливаются по баллам",
              "Роль «данные»: в одном бокале слои по баллам экспертов (3 — светлый … 9 — тёмный), толщина слоя = доля. "
              "Переход: каждый слой перетекает в свой бокал — уровень = число образцов (гистограмма из бокалов).",
              sl, ["wine", "data", "shape-morph", "histogram"], 4)


def glass_layers(theme) -> Variant:
    """Данные: красные/белые слоем -> train/val/test слоями -> три бокала."""
    red, white = wine_cols(theme)
    G = Glass("gl", R=1.15, Hb=2.2, stem=1.4)
    base = (9.4, 6.6)
    full = 0.86
    def labs(fr, names, cols):
        out, cum = [], 0.0
        for i, (f, t) in enumerate(zip(fr, names)):
            _o, inn, _h, _r = G.geom(base)
            y = level_for_area(inn, (cum + f / 2) * inn.area)
            cum += f
            out.append(label(f"!!ly{i}", 10.75, y - 0.15, t, w=2.4, al="l", sz=14, b=True, col=cols[i]))
        return out
    l1 = [full * N_RED / N_ALL, full * N_WHITE / N_ALL * 0.5, full * N_WHITE / N_ALL * 0.5]
    o1 = G.objs(theme, base, layers=l1, colors=[red, light(white, 0.2), light(white, 0.2)]) + \
        labs([l1[0], l1[1] + l1[2]], ["1599 красных", "4898 белых"], ["accent", dark(white, 0.35)]) + [head("6497 образцов")]
    sh = [SPLIT[k] / N_ALL * full for k in ("train", "val", "test")]
    c2 = [red, mix(red, theme.c("bg"), 0.45), mix(red, theme.c("bg"), 0.7)]
    o2 = G.objs(theme, base, layers=sh, colors=c2) + labs(sh, ["train 4548", "val 975", "test 974"],
                                                          ["accent", "ink2", "ink2"]) + [head("Разбиение по группам")]
    o3 = [head("Три бокала — три выборки")]
    gl = [Glass(f"gl{j}", R=0.8, Hb=1.55, stem=0.95) for j in range(3)]
    for j, x in enumerate([2.6, 6.6, 10.6]):
        lv = SPLIT[("train", "val", "test")[j]] / SPLIT["train"] * 0.85
        o = gl[j].objs(theme, (x, 6.6), level=lv, colors=[c2[j]])
        o = rename(o, {f"!!gl{j}_lq0": f"!!gl_lq{j}"} | ({"!!gl0_body": "!!gl_body", "!!gl0_hl": "!!gl_hl", "!!gl0_srf": "!!gl_srf"} if j == 0 else {}))
        o3 += o + [label(f"!!ly{j}", x, 2.25, ["train 4548", "val 975", "test 974"][j], w=2.2, b=True, sz=15,
                         col="accent" if j == 0 else "ink2")]
    return _v("glass_layers", "Слои в бокале = доли выборки",
              "Данные слоями: красные/белые (доли 1599/4898) → те же слои пересекаются заново как train/val/test → "
              "слои перетекают в три бокала (бокал train остаётся тем же объектом). Подходит для раздела «Данные».",
              [S(o1, 800), S(o2, 800), S(o3, 900)], ["wine", "data", "split", "shape-morph"], 4)


# ============================================================================= гроздь: одиночные варианты

def bunch_ripen(theme) -> Variant:
    """Указатель + прогресс: гроздь срезана правым краем; ряды = разделы; в текущем ряду «созревают» ягоды."""
    red, _ = wine_cols(theme)
    green = mix(theme.c("accent2"), "C8D3A0", 0.45)
    B = Bunch("gr", r=0.25, rows=(4, 5, 4, 4, 3, 2))
    c = (12.6, 3.9)
    pos = B.slots(c, 1.2)
    rows = B.row_of()
    secs = ["Данные", "Признаки", "Модель", "Обучение", "Итоги", "Границы"]
    ry = [pos[rows.index(r)][1] for r in range(len(B.rows))]
    rx = [min(p[0] for p, rr in zip(pos, rows) if rr == r) for r in range(len(B.rows))]
    sl = []
    for st, (sec, frac) in enumerate([(1, 1.0), (2, 0.25), (2, 0.75)]):
        cols = []
        for i in range(len(pos)):
            r = rows[i]
            idx = [j for j in range(len(pos)) if rows[j] == r]
            if r < sec:
                cols.append(red)
            elif r == sec:
                cols.append(red if idx.index(i) < round(frac * len(idx)) else light(red, 0.6))
            else:
                cols.append(green)
        objs = B.objs(theme, pos, r=B.r * 1.2, colors=cols, stalk=(c, 1.2))
        objs += [label(f"!!rs{r}", rx[r] - 0.4, ry[r] - 0.16, secs[r], w=1.9, al="r", sz=13, b=r == sec,
                       col="accent" if r == sec else "muted") for r in range(len(B.rows))]
        objs += [kicker(f"раздел {sec + 1} · {secs[sec]}"), head(["Признаки готовы", "Модель: начало", "Модель: три четверти"][st], w=7),
                 body("!!b", 0.7, 1.45, 6.0, 0.4, f"созрело {round(frac * 100)} % ягод раздела", sz=14, col="muted")]
        sl.append(S(objs, 700))
    return _v("bunch_ripen", "Гроздь у края: созревание = прогресс",
              "Навигация и прогресс одной фигурой: гроздь срезана правым краем, ряд = раздел (подписи слева), "
              "пройденные ряды — винные, в текущем ягоды «созревают» долями 25/50/75/100 %, будущие — зелёные.",
              sl, ["wine", "pointer", "progress", "navigation"], 4)


def bunch_columns(theme) -> Variant:
    """Ягоды катятся на стол и встают столбиками train/val/test (с условными числами)."""
    red, white = wine_cols(theme)
    B = Bunch("gr", r=0.21)
    n = B.count
    types = [0] * 8 + [1] * 24
    order = list(range(n))
    random.Random(4).shuffle(order)
    cols = [red if t == 0 else light(white, 0.15) for t in types]
    hc = (9.4, 3.8)
    sl0 = B.slots(hc, 1.2)
    p1 = [sl0[order[i]] for i in range(n)]
    o1 = B.objs(theme, p1, r=0.25, colors=cols, stalk=(hc, 1.2)) + [head("Гроздь данных"),
                                                                   body("!!b", 0.7, 1.4, 5, 0.4, "32 ягоды ≈ 6497 образцов", sz=15, col="muted")]
    # 2: на столе в ряд, по типу
    srt = sorted(range(n), key=lambda i: (types[i], order[i]))
    p2 = [None] * n
    for k, i in enumerate(srt):
        p2[i] = (0.75 + k * 0.38, 6.62 - 0.17)
    o2 = B.objs(theme, p2, r=0.17, colors=cols, stalk=((14.5, 3.8), 1.2, 0.0)) + table(theme) + [
        head("Скатились на стол"), body("!!b", 0.7, 1.4, 6, 0.4, "8 красных + 24 белых — как 1599 / 4898", sz=15, col="muted")]
    # 3: столбики 22 / 5 / 5
    grp = {}
    gorder = list(range(n))
    random.Random(2).shuffle(gorder)
    for k, i in enumerate(gorder):
        grp[i] = 0 if k < 22 else (1 if k < 27 else 2)
    cnt = [0, 0, 0]
    p3 = [None] * n
    xs = [3.0, 6.2, 9.4]
    for i in sorted(range(n), key=lambda i: types[i]):
        g = grp[i]
        k = cnt[g]
        cnt[g] += 1
        p3[i] = (xs[g] - 0.19 + (k % 2) * 0.38, 6.62 - 0.17 - (k // 2) * 0.36)
    o3 = B.objs(theme, p3, r=0.17, colors=cols, stalk=((14.5, 3.8), 1.2, 0.0)) + table(theme) + [head("Столбики выборок")]
    o3 += [label(f"!!c{j}", xs[j], [2.0, 5.0, 5.0][j] - 0.05, t, w=2.2, b=True, sz=15, col="accent" if j == 0 else "ink2")
           for j, t in enumerate(["train 4548", "val 975", "test 974"])]
    return _v("bunch_columns", "Ягоды скатываются в столбики",
              "Роль «данные»: гроздь (ягода ≈ 200 образцов) → ягоды скатываются на линию стола, отсортированные по типу "
              "(8 красных / 24 белых) → встают столбиками train / val / test. Одни и те же 32 объекта.",
              [S(o1, 800), S(o2, 900), S(o3, 900)], ["wine", "data", "carrier", "fragment"], 4)


def bunch_zoom(theme) -> Variant:
    """Ягода улетает по спирали и растёт (спиральное подобие), затем раскрывается на 12 долей-признаков."""
    red, white = wine_cols(theme)
    B = Bunch("gr", r=0.24)
    n = B.count
    hc = (3.4, 4.1)
    pos = B.slots(hc, 1.0)
    k0 = 13
    g0 = pos[k0]
    r0 = B.r
    T, Rbig = (9.6, 4.15), 1.65
    s = Rbig / r0
    th = 160.0
    p = spiral_pivot(g0, T, s, th)
    imp = importance()
    feats = [f for f, _ in imp]
    others = [i for i in range(n) if i != k0]
    base_cols = [light(white, 0.15) if i % 4 else red for i in range(n)]
    def cluster(alpha=1.0, hide=False):
        objs = B.objs(theme, [pos[i] for i in range(n)], r=[0.004 if i == k0 else r0 for i in range(n)],
                      colors=base_cols, stalk=(hc, 1.0, alpha), alpha=[0 if i == k0 else alpha for i in range(n)])
        return objs
    # доли ягоды (12 секторов) в рамке на оси p
    def slices(scale, rot, spread):
        out = []
        for j in range(12):
            a0, a1 = -90 + 30 * j, -90 + 30 * (j + 1)
            am = math.radians((a0 + a1) / 2)
            g = V.sector(g0[0], g0[1], r0 * 0.985, a0 + 1.2, a1 - 1.2)
            g = V.move(g, math.cos(am) * spread * r0, math.sin(am) * spread * r0)
            g = affinity.scale(g, scale, scale, origin=p)
            R = max(math.hypot(x - p[0], y - p[1]) for x, y in g.exterior.coords) * 1.02 if scale > 1 else None
            # освещение: доля смотрит на угол (am + rot) на экране; свет сверху-слева
            scr = am + math.radians(rot)
            litk = 0.5 + 0.5 * math.cos(scr - math.radians(-135))
            c = mix(dark(red, 0.35), light(red, 0.35), litk)
            out.append(V.shape(f"!!sl{j}", V.resample(g, 40), frame=None, pivot=p, rot=rot % 360, fill=c, z=60 + j,
                               ln=theme.c("bg") if spread > 0 else None, lw=0.75, meta=dict(DEC)))
        return out
    o1 = cluster() + slices(1.0, 0.0, 0.0) + [head("Один образец"), body("!!b", 0.7, 1.4, 5, 0.4, "ягода — 1 строка таблицы",
                                                                          sz=15, col="muted")]
    o2 = cluster(0.35) + slices(s, th, 0.0) + [head("Один образец"), body("!!b", 0.7, 1.4, 5, 0.4, "ягода — 1 строка таблицы",
                                                                           sz=15, col="muted")]
    o3 = cluster(0.2) + slices(s, th, 0.16) + [head("12 входов строки"), body("!!b", 0.7, 1.4, 5.4, 0.4,
                                                                            "11 показателей + тип вина", sz=15, col="muted")]
    for j in range(12):
        am = math.radians(-90 + 30 * j + 15)
        # подпись доли j: доля на экране повернута на th
        a = am + math.radians(th)
        x, y = T[0] + (Rbig * 1.16 + 0.5) * math.cos(a), T[1] + (Rbig * 1.16 + 0.3) * math.sin(a)
        al = "l" if math.cos(a) > 0.25 else ("r" if math.cos(a) < -0.25 else "c")
        o3.append(label(f"f{j}", x - (0.0 if al != "c" else 0), y - 0.15, feats[j], w=1.7, al=al, sz=12))
    fx3 = [Fx("entrance_fade", f"f{j}", start="at", delay=0.15 + 0.03 * j, dur=0.3) for j in range(12)]
    return _v("bunch_zoom", "Ягода улетает по спирали и раскрывается",
              "Увеличенная часть мотива движется по дуге: ягода из грозди летит по спирали (рамка с центром спирального "
              "подобия: поворот 160° + рост ×7) и становится крупным шаром из 12 долей; доли расходятся — 11 показателей "
              "и тип. Свет пересчитан под поворот — шар остаётся освещённым сверху. Раздел «Признаки».",
              [S(o1, 700), S(o2, 900), S(o3, 800, fx=fx3)], ["wine", "zoom", "spiral", "fragment", "3d"], 3)


def bunch_backdrop(theme) -> Variant:
    """Фон: огромная бледная гроздь дрейфует под графиком, ряд текущего раздела чуть темнее."""
    red, white = wine_cols(theme)
    B = Bunch("gr", r=0.6)
    imp = importance()
    sl = []
    for st in range(2):
        c = (8.8 + st * 0.6, 3.9 + st * 0.25)
        pos = B.slots(c, 1.0, seed=3)
        pos = [V.rotate(V.Point(x, y), 8 * st, origin=c).coords[0] for x, y in pos]
        objs = B.objs(theme, pos, r=0.6, colors=red, alpha=0.08, stalk=(c, 1.0, 0.08), z=-300, hl=False)
        objs += [head(["Важность показателей", "Важность: тройка лидеров"][st], w=8)]
        top = imp[0][1]
        for i, (nm, v) in enumerate(imp[:8]):
            y = 1.6 + i * 0.62
            L = v / top * 6.5
            hot = st == 1 and i < 3
            objs += [label(f"!!il{i}", 3.1, y + 0.05, nm, w=2.3, al="r", sz=14, col="ink" if hot else "ink2", b=hot),
                     O(f"!!ib{i}", "rect", 3.3, y, L, 0.4, fill="accent" if hot or st == 0 else "muted", z=40)]
        sl.append(S(objs, 800, fx=[Fx("entrance_wipe", f"!!ib{i}", start="at", delay=0.15 + 0.06 * i, dur=0.35,
                                        options={"direction": "left"}) for i in range(8)] if st == 0 else []))
    return _v("bunch_backdrop", "Бледная гроздь под графиком",
              "Фон: гроздь в 3 раза крупнее, прозрачность 8 %, под всем содержимым; между слайдами дрейфует и "
              "поворачивается на 8°. Столбики — важность показателей (рост MAE при перестановке, без чисел).",
              sl, ["wine", "backdrop", "data"], 3)


# ============================================================================= бочка из клёпок

def barrel(theme) -> Variant:
    imp = importance()
    nst = 12
    cx, cy, Hh, a, b = 9.5, 3.9, 2.5, 1.55, 0.42  # центр, полувысота, полуширина у дна, выпуклость
    wood = mix(theme.c("accent3"), "6B4A2B", 0.55)
    def hw(y):
        return a + b * math.cos(math.pi / 2 * (y - cy) / Hh)
    def stave(j, n=34):
        t0, t1 = -90 + 180 * j / nst, -90 + 180 * (j + 1) / nst
        ys = [cy - Hh + 2 * Hh * i / n for i in range(n + 1)]
        L = [(cx + hw(y) * math.sin(math.radians(t0 + 0.6)), y) for y in ys]
        R_ = [(cx + hw(y) * math.sin(math.radians(t1 - 0.6)), y) for y in ys[::-1]]
        return V.polygon(L + R_), (t0 + t1) / 2
    order = list(range(nst))
    sl = []
    for st in range(3):
        objs = []
        for j in range(nst):
            g, tm = stave(j)
            lit = 0.5 + 0.5 * math.cos(math.radians(tm + 25))
            c = mix(dark(wood, 0.45), light(wood, 0.3), lit)
            if st == 0:
                objs.append(vs(f"!!stv{j}", g, 72, fill=c, ln=dark(wood, 0.5), lw=0.5, z=10 + j))
            else:
                # клёпка j -> столбик ранга j (важность), лежит горизонтально: вертикальная форма с поворотом 90°
                nm, v = imp[j]
                L = 0.25 + v / imp[0][1] * 6.2
                yb = 1.55 + j * 0.44
                xb = 3.3 + L / 2
                rect = V.rect(xb - 0.16, yb + 0.17 - L / 2, 0.32, L, r=0.06)
                hot = st == 2 and j < 3
                col = (light(wood, 0.1) if j % 2 else wood) if not hot else tc(theme, "red_wine", "accent")
                objs.append(vs(f"!!stv{j}", rect, 72, rot=90, fill=col, ln=dark(wood, 0.5), lw=0.5, z=10 + j))
                objs.append(label(f"!!sn{j}", 3.15, yb + 0.02, nm, w=2.3, al="r", sz=13, col="ink" if hot else "ink2", b=hot))
        if st == 0:
            for k, yy in enumerate([cy - Hh * 0.82, cy - Hh * 0.45, cy + Hh * 0.45, cy + Hh * 0.82]):
                w_ = hw(yy) + 0.04
                pts_top = [(cx + w_ * math.sin(math.radians(t)), yy + 0.12 * math.cos(math.radians(t)) - 0.06) for t in range(-90, 91, 6)]
                pts_bot = [(x, y + 0.13) for x, y in pts_top[::-1]]
                objs.append(vs(f"hoop{k}", V.polygon(pts_top + pts_bot), fill=theme.c("ink2"), z=40,
                               grad=V.gradient([(0, dark(theme.c("ink2"), 0.3)), (0.4, light(theme.c("ink2"), 0.35)),
                                                (1, dark(theme.c("ink2"), 0.4))], angle=0)))
            objs.append(O("lid", "oval", cx - hw(cy - Hh), cy - Hh - 0.2, 2 * hw(cy - Hh), 0.4, fill=light(wood, 0.2),
                          ln=dark(wood, 0.5), lw=0.75, z=8))
            objs += [head("Бочка из 12 клёпок"), body("!!b", 0.7, 1.4, 5.2, 0.8, "клёпка = вход модели", sz=16)]
        else:
            objs += [head(["Клёпки = важность входов", "Три главные клёпки"][st - 1], w=9),
                     body("!!b2", 0.7, 6.75, 9, 0.3, "рост MAE сети при перестановке признака (итоговая оценка)", sz=12, col="muted")]
        sl.append(S(objs, 900 if st == 1 else 700,
                    fx=[Fx("entrance_fade", f"!!sn{j}", start="at", delay=0.3 + 0.03 * j, dur=0.3) for j in range(nst)]
                    if st == 1 else []))
    return _v("barrel", "Бочка разбирается на клёпки-столбики",
              "Объём из 2D: клёпки бочки — полосы цилиндра в проекции (крайние уже, освещение по углу), обручи "
              "изогнуты. Переход: обручи падают, клёпки разлетаются, поворачиваются на 90° и переливаются в "
              "горизонтальные столбики важности 12 входов (условные данные, без чисел); затем лидеры — винным.",
              sl, ["wine", "data", "fragment", "3d", "shape-morph"], 4)


# ============================================================================= бутылка в разрезе

def _bottle(cx: float, yb: float, k: float = 1.0):
    body = V.rect(cx - 0.78 * k, yb - 3.0 * k, 1.56 * k, 3.0 * k, r=0.16 * k)
    sh = V.ellipse(cx, yb - 3.0 * k, 0.78 * k, 0.62 * k)
    neck = V.rect(cx - 0.22 * k, yb - 4.75 * k, 0.44 * k, 1.5 * k)
    lip = V.rect(cx - 0.27 * k, yb - 4.85 * k, 0.54 * k, 0.24 * k, r=0.05 * k)
    return biggest(V.union(body, sh, neck, lip).buffer(0.02).buffer(-0.02))


def bottle_slices(theme) -> Variant:
    cx, yb = 10.2, 6.3
    bot = _bottle(cx, yb, 1.0)
    cuts = [yb - 4.86, yb - 3.9, yb - 2.95, yb - 1.95, yb - 0.98, yb + 0.01]
    stages = ["Данные", "Признаки", "Модель", "Обучение", "Оценка"]
    gl = mix(theme.c("accent2"), "1E2B12", 0.35)
    def slab(i, e, dy=0.0, dx=0.0):
        y0, y1 = cuts[i], cuts[i + 1]
        part = biggest(bot.intersection(box(0, y0, W, y1)))
        ch0 = chord(bot, y0 + 0.02) or (cx - 0.2, cx + 0.2)
        ch1 = chord(bot, y1 - 0.02) or (cx - 0.2, cx + 0.2)
        w0, w1 = ch0[1] - ch0[0], ch1[1] - ch1[0]
        if e > 0:
            part = biggest(V.union(part, V.ellipse(cx, y1 - 0.02, w1 / 2, e * w1 / 2).intersection(box(0, y1 - 0.02, W, H + 2))))
            part = biggest(part.difference(V.ellipse(cx, y0, w0 / 2, e * w0 / 2)))
        return V.move(part, dx, dy), (cx + dx - w0 / 2, y0 + dy - e * w0 / 2, w0, max(e * w0, 0.002))
    sl = []
    for st in range(3):
        objs = []
        for i in range(5):
            if st == 0:
                g, top = slab(i, 0.0)
            elif st == 1:
                g, top = slab(i, 0.22, dy=(i - 2) * 0.3)
            else:
                xs = [1.5, 4.0, 6.5, 9.0, 11.5]
                y_mid = (cuts[i] + cuts[i + 1]) / 2
                g, top = slab(i, 0.3, dx=xs[i] - cx, dy=4.3 - y_mid)
            objs.append(vs(f"!!bs{i}", g, 140, fill=gl, grad=cyl_grad(gl, 1.0, 0.45), z=10 + 2 * i, meta=dict(DEC)))
            objs.append(O(f"!!bt{i}", "oval", *top, fill=light(gl, 0.35), fa=1.0 if st else 0.0, ln=dark(gl, 0.3),
                          lw=0.75 if st else 0, z=11 + 2 * i, meta=dict(DEC)))
            if st >= 1:
                if st == 1:
                    y_l = (cuts[i] + cuts[i + 1]) / 2 + (i - 2) * 0.3 - 0.15
                    objs.append(label(f"!!bl{i}", cx - 1.2, y_l, f"{i + 1} {stages[i]}", w=2.2, al="r", sz=14,
                                      b=i == 2, col="accent" if i == 2 else "ink2"))
                else:
                    objs.append(label(f"!!bl{i}", [1.5, 4.0, 6.5, 9.0, 11.5][i], 5.75, f"{i + 1} {stages[i]}", w=2.2,
                                      sz=14, b=i == 2, col="accent" if i == 2 else "ink2"))
        objs += [head(["Проект в бутылке", "Разрез: пять этапов", "Этапы в ряд"][st], w=6)]
        sl.append(S(objs, 900))
    return _v("bottle_slices", "Бутылка в разрезе: этапы расходятся",
              "Обложка → структура: бутылка (цилиндрический градиент) режется на 5 слоёв-этапов; слои расходятся по "
              "вертикали, у каждого появляется объёмный торец-эллипс (2D → 3D), затем выстраиваются в ряд конвейера. "
              "Части отделяются, но остаются той же бутылкой — обратный ход собирает её.",
              sl, ["wine", "fragment", "3d", "process", "hero"], 4)


def bottle_pour(theme) -> Variant:
    red, _ = wine_cols(theme)
    gl = mix(theme.c("accent2"), "1E2B12", 0.35)
    piv = (3.4, 3.2)
    bot = _bottle(piv[0], piv[1] + 1.4, 0.7)
    inner = bot.buffer(-0.06)
    A = inner.area
    G = Glass("gg", R=1.0, Hb=1.9, stem=1.2)
    gb = (8.6, 6.6)
    def bottle_objs(theta, vol):
        objs = [vs("!!bot", bot, 0, pivot=piv, rot=theta % 360, fill=gl, grad=cyl_grad(gl, 0.95, 0.45), fa=0.95, z=10,
                   meta=dict(DEC))]
        wi = V.rotate(inner, theta, origin=piv)
        y = level_for_area(wi, vol * A)
        liq = V.rotate(below(wi, y), -theta, origin=piv)
        objs.append(vs("!!bliq", liq, 120, pivot=piv, rot=theta % 360, fill=dark(red, 0.25), fa=0.9, z=11, meta=dict(DEC)))
        lab_ = V.rect(piv[0] - 0.5, piv[1] - 0.2, 1.0, 0.75)
        objs.append(vs("!!blab", lab_, 0, pivot=piv, rot=theta % 360, fill=theme.c("surface"), z=12, ln=theme.c("line"),
                       lw=0.75, meta=dict(DEC)))
        return objs
    th = 118
    wi = V.rotate(inner, th, origin=piv)
    # горлышко после поворота: самая дальняя от оси точка формы
    mouth = max(V.rotate(bot, th, origin=piv).exterior.coords, key=lambda q: math.hypot(q[0] - piv[0], q[1] - piv[1]))
    _o, gin, _h, rim = G.geom(gb)
    y_lq = level_for_area(gin, 0.35 * gin.area)
    stream = vs("pour", stroke(bezier(mouth, (mouth[0] + 0.5, mouth[1] + 0.2), (gb[0] - 0.1, rim - 0.4), (gb[0] - 0.05, y_lq), 30),
                               0.08), fill=red, fa=0.9, z=9, meta=dict(DEC))
    o1 = bottle_objs(0, 0.75) + G.objs(theme, gb, level=0.015) + [head("Данные → модель", x=6.5, w=6),
                                                                  body("!!b", 6.5, 1.35, 6, 0.4, "6497 образцов", sz=16, col="muted")]
    o2 = bottle_objs(th, 0.45) + G.objs(theme, gb, level=0.35) + [stream, head("Данные → модель", x=6.5, w=6),
                                                                   body("!!b", 6.5, 1.35, 6, 0.4, "6497 образцов", sz=16, col="muted")]
    o3 = bottle_objs(0, 0.25) + G.objs(theme, gb, level=0.62) + [head("Готово к обучению", x=6.5, w=6),
                                                                 body("!!b", 6.5, 1.35, 6, 0.4, "train 4548 · val 975 · test 974", sz=16,
                                                                      col="muted")]
    return _v("bottle_pour", "Бутылка наливает бокал",
              "Герой-процесс: бутылка поворачивается на 118° вокруг оси (рамка на оси), вино внутри неё каждый раз "
              "пересчитано горизонтально с убывающим объёмом; струя появляется вытиранием, бокал наполняется. Переход "
              "«данные → модель» или вступление к разделу обучения.",
              [S(o1, 700), S(o2, 900, fx=[Fx("entrance_wipe", "pour", start="at", delay=0.05, dur=0.4,
                                              options={"direction": "left"})]), S(o3, 800)],
              ["wine", "hero", "physics", "pivot", "process"], 4)


# ============================================================================= лоза-линия времени

def vine(theme) -> Variant:
    red, _ = wine_cols(theme)
    green = theme.c("accent2")
    brown = mix(green, "6B4A2B", 0.6)
    pts = bezier((0.4, 5.6), (4.0, 2.4), (8.0, 7.4), (12.9, 3.2), 140)
    nodes = [10, 30, 50, 70, 90, 110, 132]
    names = ["1 Данные", "2 Разведка", "3 Признаки", "4 Восстановление", "5 Тензоры", "6 Обучение", "7 Итог"]
    cuts = [0] + nodes
    segs = []
    for k in range(len(cuts) - 1):
        a, b = cuts[k], cuts[k + 1]
        w0 = 0.2 - 0.12 * a / 140
        w1 = 0.2 - 0.12 * b / 140
        segs.append(taper(pts[a:b + 1], w0, w1))
    def leaf_at(k):
        x, y = pts[nodes[k]]
        up = k % 2 == 0
        a = -35 if up else 145
        tip = (x + 0.55 * math.cos(math.radians(a - 60 if up else a + 60)), y + (-0.5 if up else 0.5))
        lf = vine_leaf(tip[0], tip[1] + (0.0 if up else 0.0), 0.62, angle=(-20 if up else 160))
        pet = taper(bezier((x, y), (x, y - 0.2 if up else y + 0.2), tip, tip, 10), 0.06, 0.03)
        return lf, pet
    sl = []
    for st, upto in enumerate([3, 5, 7]):
        objs = [head(["Лоза проекта", "Растёт по этапам", "Итог: урожай"][st], w=6), kicker("линия времени · этапы 1–7")]
        fx = []
        delay = 0.15
        for k in range(upto):
            nm = f"!!vs{k}"
            objs.append(vs(nm, segs[k], 0, fill=brown, grad=V.gradient([(0, light(brown, 0.2)), (1, dark(brown, 0.25))], 90),
                           z=10, meta=dict(DEC)))
            lf, pet = leaf_at(k)
            cur = k == upto - 1
            objs.append(vs(f"!!vl{k}", lf, 0, fill=red if cur else green, grad=V.gradient([(0, light(red if cur else green, 0.2)),
                                                                                         (1, dark(red if cur else green, 0.25))], 60),
                           ln=dark(green, 0.3), lw=0.6, z=12 + k, meta=dict(DEC)))
            objs.append(vs(f"!!vp{k}", pet, 0, fill=brown, z=11, meta=dict(DEC)))
            x, y = pts[nodes[k]]
            up = k % 2 == 0
            objs.append(label(f"!!vt{k}", x + (0.25 if up else -0.25), y + (-1.75 if up else 1.45), names[k], w=1.9,
                              al="c", sz=13, b=cur, col="accent" if cur else "ink2"))
            new = k >= [0, 3, 5][st]
            if new:
                fx.append(Fx("entrance_wipe", nm, start="at", delay=delay, dur=0.3, options={"direction": "left"}))
                fx.append(Fx("entrance_zoom", f"!!vl{k}", start="at", delay=delay + 0.2, dur=0.35))
                fx.append(Fx("entrance_fade", f"!!vp{k}", start="at", delay=delay + 0.15, dur=0.2))
                fx.append(Fx("entrance_fade", f"!!vt{k}", start="at", delay=delay + 0.3, dur=0.3))
                delay += 0.3
        if st == 2:
            B = Bunch("vg", r=0.16, rows=(4, 5, 4, 3, 2, 1))
            c = (pts[-1][0] - 0.3, pts[-1][1] + 1.2)
            bp = B.slots(c, 1.0)
            objs += B.objs(theme, bp, r=0.17, colors=red, stalk=None)
            fx += [Fx("entrance_zoom", f"!!vg{i}", start="at", delay=delay + 0.02 * i, dur=0.3) for i in range(len(bp))]
        sl.append(S(objs, 800, fx=fx))
    return _v("vine", "Лоза растёт по этапам 1–7",
              "Линия времени проекта: ветвь — сужающиеся сегменты, каждый новый проявляется вытиранием по ходу роста, "
              "лист узла раскрывается, текущий этап — винный лист; на последнем этапе вырастает гроздь-итог. Прогресс по колоде.",
              sl, ["wine", "timeline", "progress", "growth"], 3)


# ============================================================================= колесо признаков

GROUPS = [("Кислотность", ["фикс. кисл.", "летучая кисл.", "лимонная к.", "pH"]),
          ("Сера", ["свободный SO₂", "общий SO₂", "сульфаты"]),
          ("Тело", ["сахар", "плотность", "спирт"]),
          ("Соли", ["хлориды"]),
          ("Тип", ["тип вина"])]


def wheel(theme) -> Variant:
    red, white = wine_cols(theme)
    gc = [red, white, theme.c("accent2"), theme.c("muted"), theme.c("ink2")]
    imp = dict(importance())
    feats = [(gi, f) for gi, (_, fs) in enumerate(GROUPS) for f in fs]
    nF = len(feats)
    step = 360 / nF
    def build(center, scale, turn, data=False, alpha=1.0, focus=None):
        cx, cy = center
        out = []
        r_in, r_mid, r_out = 0.45 * scale, 1.35 * scale, 2.45 * scale
        for j, (gi, f) in enumerate(feats):
            a0, a1 = -90 + j * step, -90 + (j + 1) * step
            ro = r_out if not data else r_mid + 0.15 * scale + (r_out * 1.15 - r_mid) * imp.get(f, 0.01) / max(imp.values())
            g = V.sector(cx, cy, ro, a0 + 0.8, a1 - 0.8, r_in=r_mid + 0.05 * scale, steps=20)
            c = light(gc[gi], 0.35 if focus not in (None, gi) else 0.15)
            out.append(vs(f"!!wf{j}", g, 64, pivot=center, rot=turn % 360, fill=c, fa=alpha, z=10 + j, meta=dict(DEC)))
        j0 = 0
        for gi, (gname, fs) in enumerate(GROUPS):
            a0, a1 = -90 + j0 * step, -90 + (j0 + len(fs)) * step
            g = V.sector(cx, cy, r_mid, a0 + 0.8, a1 - 0.8, r_in=r_in, steps=30)
            out.append(vs(f"!!wg{gi}", g, 96, pivot=center, rot=turn % 360, fill=gc[gi], fa=alpha * (1 if focus in (None, gi) else 0.45),
                          z=30 + gi, meta=dict(DEC)))
            j0 += len(fs)
        return out
    def facing(gi):
        j0 = sum(len(fs) for _, fs in GROUPS[:gi])
        mid = -90 + (j0 + len(GROUPS[gi][1]) / 2) * step
        return -mid  # центр группы смотрит вправо (0°)
    def flabels(center, scale, turn, which=None, data=False, sz=12):
        out = []
        for j, (gi, f) in enumerate(feats):
            if which is not None and gi != which:
                continue
            a = math.radians(-90 + (j + 0.5) * step + turn)
            ro = 2.45 * scale if not data else 1.5 * scale + (2.45 * 1.15 - 1.35) * scale * imp.get(f, 0.01) / max(imp.values())
            r = ro + 0.18
            x, y = center[0] + r * math.cos(a), center[1] + r * math.sin(a)
            al = "l" if math.cos(a) > 0.3 else ("r" if math.cos(a) < -0.3 else "c")
            out.append(label(f"!!wl{j}", x, y - 0.15 + (0.12 if math.sin(a) > 0.6 else (-0.12 if math.sin(a) < -0.6 else 0)), f,
                             w=1.6, al=al, sz=sz))
        return out
    c1 = (9.3, 3.95)
    o1 = build(c1, 1.15, 0) + flabels(c1, 1.15, 0) + [head("Колесо признаков", w=5), body("!!b", 0.7, 1.4, 4.5, 1.2,
                                                                                         ["5 групп,", "11 показателей + тип"], sz=16)]
    o2 = build(c1, 1.15, 0, data=True) + flabels(c1, 1.15, 0, data=True) + [head("Длина = важность", w=5),
                                                                           body("!!b2", 0.7, 1.4, 4.5, 1.2, ["рост MAE при", "перестановке (итоговая оценка)"], sz=16)]
    t3 = facing(2)
    t3 = t3 + 360 * round((0 - t3) / 360)
    c3 = (-0.9, 3.75)
    o3 = build(c3, 1.25, t3, focus=2) + flabels(c3, 1.25, t3, which=2, sz=13) + [kicker("раздел 3", x=3.6), head("Тело вина", x=3.6, w=6),
                                                                            body("!!b3", 3.6, 1.5, 6, 0.9, "сахар, плотность и спирт", sz=18)]
    return _v("wheel", "Колесо признаков: данные → указатель",
              "Как «колесо ароматов» сомелье: внутреннее кольцо — 5 групп, внешнее — 12 входов. Данные: внешние сектора "
              "вытягиваются по важности (перелив секторов). Указатель: колесо уезжает за левый край и поворачивается "
              "так, что группа раздела смотрит на заголовок; остальные группы гаснут.",
              [S(o1, 700), S(o2, 800), S(o3, 900)], ["wine", "data", "pointer", "pivot", "radial"], 4)


# ============================================================================= живая последовательность 2: бокал

def seq_glass(theme) -> Variant:
    """Бокал через колоду: герой → слои красное/белое → слои выборок → слои разливаются в три бокала →
    бокал-указатель у края (уровень = раздел) → шаг внутри раздела → огромный фон под графиком → финал."""
    red, white = wine_cols(theme)
    G = Glass("gl", R=1.15, Hb=2.2, stem=1.4)
    base = (9.6, 6.6)
    full = 0.84
    c_type = [red, light(white, 0.2), light(white, 0.2)]
    c_split = [red, mix(red, theme.c("bg"), 0.45), mix(red, theme.c("bg"), 0.7)]
    sh = [SPLIT[k] / N_ALL * full for k in ("train", "val", "test")]
    def lab_layers(fr, names, cols, x=11.0):
        out, cum = [], 0.0
        _o, inn, _h, _r = G.geom(base)
        for i, (f, t) in enumerate(zip(fr, names)):
            y = level_for_area(inn, (cum + f / 2) * inn.area)
            cum += f
            out.append(label(f"!!ly{i}", x, y - 0.15, t, w=2.2, al="l", sz=14, b=True, col=cols[i]))
        return out
    sm = [Glass(f"gs{j}", R=0.62, Hb=1.2, stem=0.8) for j in (1, 2)]
    park = [(15.0, 6.6), (16.5, 6.6)]
    def smalls(pos, lv, alpha=1.0, merged=True):
        out = []
        for j, g in enumerate(sm):
            o = g.objs(theme, pos[j], level=lv[j], colors=[c_split[j + 1]], alpha=alpha)
            out += rename(o, {f"!!gs{j + 1}_lq0": f"!!gl_lq{j + 1}"}) if merged else o
        return out
    S_ = []
    # 1 герой
    S_.append(S(G.objs(theme, base, level=full, layers=[full, 0.0, 0.0], colors=[red, red, red], tilt=-8) +
                smalls(park, [0.02, 0.02], merged=False) +
                [kicker("пример · этапы 1–7"), O("!!cov", "text", 0.7, 1.0, 5.6, 1.7, txt=["Качество вина", "по анализу"], sz=44,
                                                     b=True, font="head", col="ink", spacing=0.95, z=90)], 700))
    # 2 слои типа
    l1 = [full * N_RED / N_ALL, full * N_WHITE / N_ALL * 0.5, full * N_WHITE / N_ALL * 0.5]
    S_.append(S(G.objs(theme, base, layers=l1, colors=c_type) + smalls(park, [0.02, 0.02], merged=False) +
                lab_layers([l1[0], l1[1] + l1[2]], ["1599 красных", "4898 белых"], ["accent", dark(white, 0.35)]) +
                [head("6497 образцов")], 800))
    # 3 слои выборок
    S_.append(S(G.objs(theme, base, layers=sh, colors=c_split) + smalls(park, [0.02, 0.02], merged=False) +
                lab_layers(sh, ["train 4548", "val 975", "test 974"], ["accent", "ink2", "ink2"]) + [head("Разбиение по группам")], 800))
    # 4 слои val и test перетекают в свои бокалы
    b4 = (4.2, 6.6)
    lv_small = [sh[1] / full * 0.8 * 1.6, sh[2] / full * 0.8 * 1.6]
    o4 = G.objs(theme, b4, layers=[sh[0]], colors=c_split) + smalls([(8.0, 6.6), (11.0, 6.6)], lv_small)
    o4 += [head("Три бокала"), label("!!ly0", 4.2, 1.6, "train 4548", w=2.3, b=True, col="accent", sz=15),
           label("!!ly1", 8.0, 3.0, "val 975", w=2.0, b=True, sz=15), label("!!ly2", 11.0, 3.0, "test 974", w=2.0, b=True, sz=15)]
    S_.append(S(o4, 900))
    # 5–6 указатель у края: деления = разделы; шаг внутри раздела — волнение (уровень между делениями)
    secs = ["Данные", "Признаки", "Модель", "Результаты"]
    ticks = [0.2, 0.42, 0.64, 0.86]
    pb, ps = (0.2, 9.0), 2.35
    def pointer(k, lv, title, text):
        o = G.objs(theme, pb, s=ps, layers=[lv], colors=[red], ticks=ticks, tick_on=k)
        for i, tp in enumerate(secs):
            x, y = G.tick_y(pb, ps, ticks[i])
            o.append(label(f"!!sc{i}", x + 0.15, y - 0.17, f"0{i + 1} {tp}", w=2.0, al="l", sz=13, b=i == k,
                           col="accent" if i == k else "muted"))
        o += smalls(park, lv_small)
        o += [kicker(f"раздел {k + 1} · {secs[k]}", x=5.6), head(title, x=5.6, w=7), body("!!txt", 5.6, 1.5, 6.8, 1.6, text, sz=18)]
        return o
    S_.append(S(pointer(2, 0.53, "Модель", ["MLP 13 → 32 → 1", "13 входов: 11 показателей и тип"]), 900))
    S_.append(S(pointer(2, 0.62, "Обучение", ["ранняя остановка по val", "test открыт один раз"]), 700))
    # 7 фон: огромный бокал под столбиками MAE
    o7 = G.objs(theme, (8.4, 10.4), s=3.2, layers=[0.62], colors=[red], alpha=0.09, z=-60) + smalls(park, lv_small)
    o7 += [kicker("раздел 4 · Результаты"), head("MAE на test")]
    for k, (nm, v) in enumerate(MAE.items()):
        y = 2.3 + k * 1.15
        L = v / 0.66 * 6.2
        o7 += [label(f"!!ml{k}", 3.6, y + 0.1, nm, w=1.3, al="r", b=k == 0, col="ink" if k == 0 else "ink2", sz=16),
               O(f"!!mb{k}", "rect", 3.75, y, L, 0.5, fill="accent" if k == 0 else "muted", z=40),
               label(f"!!mv{k}", 3.85 + L, y + 0.1, ru(v), w=1.0, al="l", b=k == 0, sz=16, col="accent" if k == 0 else "ink2")]
    S_.append(S(o7, 900, fx=[Fx("entrance_wipe", f"!!mb{k}", start="at", delay=0.15 + 0.12 * k, dur=0.4,
                                options={"direction": "left"}) for k in range(3)]))
    # 8 финал
    S_.append(S(G.objs(theme, base, layers=[full], colors=[red], tilt=8) + smalls(park, lv_small) +
                [O("!!fin", "text", 0.7, 1.4, 5.8, 1.6, txt=["MAE 0,55", "лучше Ridge и Dummy"], sz=36, b=True, font="head",
                   col="ink", spacing=0.95, z=90)], 900))
    return _v("seq_glass", "Бокал живёт через колоду",
              "8 состояний одного бокала: герой (наклон) → слои красное/белое → те же слои пересекаются как train/val/test → "
              "слои val и test перетекают в свои бокалы → бокал ×2,3 у левого края — указатель, уровень у деления раздела → "
              "шаг внутри раздела (уровень между делениями) → огромный бледный фон под MAE → финал с обратным наклоном.",
              S_, ["seq", "wine", "data", "pointer", "progress", "backdrop", "hero"], 4)


# ============================================================================= живая последовательность 3: следы на столе

def seq_stain(theme) -> Variant:
    """Бокал ставят на стол трижды (три модели) — остаются следы в перспективе; вид сверху: следы = круги ошибки."""
    red, _ = wine_cols(theme)
    G = Glass("gl", R=0.8, Hb=1.55, stem=1.0)
    ty = 5.6  # линия стола (следы — эллипсы в перспективе)
    spots = [(2.8, ty + 0.55), (6.6, ty + 0.75), (10.4, ty + 0.5)]
    names = list(MAE.items())[::-1]  # Dummy, Ridge, Сеть
    radii = [v * 3.9 for _, v in names]
    seeds = [3, 7, 11]
    def stain(k, center, r, sy, alpha=1.0, rot=0.0, amp=0.05, th=0.08):
        ring = stain_ring(0, 0, r, r * th, seed=seeds[k], amp=amp)
        disc = V.polygon(list(ring.exterior.coords))
        tr = lambda g: affinity.translate(affinity.scale(V.rotate(g, rot, origin=(0, 0)), 1.0, sy, origin=(0, 0)), *center)  # noqa: E731
        return [vs(f"!!sti{k}", V.resample(tr(disc), 160), 0, fill=red, fa=0.07 * alpha, z=3 + 2 * k, meta=dict(DEC)),
                V.shape(f"!!st{k}", tr(ring), fill=red, fa=0.5 * alpha, z=4 + 2 * k, meta=dict(DEC))]
    floor = [O("!!floor", "rect", -0.2, ty, W + 0.4, H - ty + 0.2, fill="surface", z=1, meta=dict(DEC))]
    S_ = []
    for st in range(3):
        objs = list(floor) + [head(f"Попытка {st + 1}: {names[st][0]}", w=7),
                              body("!!b", 0.7, 1.35, 6, 0.4, f"MAE {ru(names[st][1])}", sz=18, col="accent")]
        for k in range(st + 1):
            objs += stain(k, spots[k], 0.62 + 0.25 * k / 2 * 0 + 0.05 * (2 - k), 0.32)
        x, y = spots[st]
        objs += G.objs(theme, (x, y), s=1.0, level=0.45, z=30)
        fx = [Fx("entrance_fade", f"!!st{st}", start="at", delay=0.25, dur=0.4),
              Fx("entrance_fade", f"!!sti{st}", start="at", delay=0.25, dur=0.4)]
        S_.append(S(objs, 800, fx=fx))
    # 4: вид сверху — следы становятся кругами-мишенью, радиус = MAE
    c = (8.2, 4.1)
    objs = [O("!!floor", "rect", -0.2, -0.2, W + 0.4, H + 0.4, fill="surface", fa=0.0, z=1, meta=dict(DEC)),
            head("Вид сверху: пятно ошибки", w=6), body("!!b", 0.7, 1.35, 4.8, 0.8, "радиус следа = MAE: меньше — точнее", sz=16)]
    for k in range(3):
        objs += stain(k, c, radii[k], 1.0, rot=40 * k, amp=0.012, th=0.045)
        dy = (k - 1) * 0.55 - 1.2
        x = c[0] + math.sqrt(max(radii[k] ** 2 - dy ** 2, 0)) + 0.12
        objs.append(label(f"sl{k}", x, c[1] + dy - 0.15, f"{names[k][0]} {ru(names[k][1])}", w=2.0, al="l", sz=13,
                          b=k == 2, col="accent" if k == 2 else "ink2"))
    objs += G.objs(theme, (c[0], -3.0), s=1.0, level=0.45, z=30)
    S_.append(S(objs, 900, fx=[Fx("entrance_fade", f"sl{k}", start="at", delay=0.2 + 0.1 * k) for k in range(3)]))
    # 5: следы уходят в фон — бледные под выводом, лёгкий поворот
    objs = [O("!!floor", "rect", -0.2, -0.2, W + 0.4, H + 0.4, fill="surface", fa=0.0, z=1, meta=dict(DEC)),
            head("Сеть точнее на 0,05", w=7.5), body("!!b", 0.7, 1.35, 6.5, 1.2, ["MAE 0,55 против 0,60 у Ridge", "и 0,66 у Dummy"], sz=18)]
    for k in range(3):
        objs += stain(k, (9.0, 4.6), radii[k] * 1.5, 1.0, alpha=0.3, rot=40 * k + 25, amp=0.012, th=0.045)
    objs += G.objs(theme, (9.0, -3.0), s=1.0, level=0.45, z=30)
    S_.append(S(objs, 900))
    # 6: указатель — следы у правого края, текущий (сеть) — полный цвет
    objs = [O("!!floor", "rect", -0.2, -0.2, W + 0.4, H + 0.4, fill="surface", fa=0.0, z=1, meta=dict(DEC)),
            kicker("раздел 5 · Границы"), head("Где сеть ошибается", w=7),
            body("!!b", 0.7, 1.5, 6.5, 1.2, ["редкие баллы 3 и 9", "сдвиг к середине шкалы"], sz=18)]
    for k in range(3):
        objs += stain(k, (13.0, 1.6 + k * 2.1), 0.85, 1.0, alpha=1.0 if k == 2 else 0.35, rot=40 * k + 50)
    objs += G.objs(theme, (13.0, -3.0), s=1.0, level=0.45, z=30)
    S_.append(S(objs, 900))
    return _v("seq_stain", "Следы бокала: перспектива → мишень",
              "Бокал ставят на стол трижды — три модели (Dummy, Ridge, Сеть); каждый раз остаётся неровное кольцо-след "
              "в перспективе стола (эллипс). Вид сверху: следы разворачиваются в круги, радиус = MAE (мишень ошибки). "
              "Потом следы уходят в бледный фон под выводом и встают у края как указатель.",
              S_, ["seq", "wine", "3d", "data", "backdrop", "pointer", "shape-morph"], 3)


def variants(theme) -> list[Variant]:
    return [seq_bunch(theme), seq_glass(theme), seq_stain(theme), glass_swirl(theme), glass_steps(theme),
            glass_pointer(theme), glass_layers(theme), glass_quality(theme), bunch_ripen(theme), bunch_columns(theme),
            bunch_zoom(theme), bunch_backdrop(theme), barrel(theme), bottle_slices(theme), bottle_pour(theme),
            vine(theme), wheel(theme)]
