"""Семейство «Кольца»: сегменты с зазорами, лупа-сегмент, прогресс по кругу без клина, вложенные кольца,
кольцо-категории, разворот кольца в полосу, разлёт сегментов, наклон кольца в 3D, сбор точек по кругу.

Ключ к движению по кругу — рамка на оси (lab._b_util.axis): сегмент или точка вращаются вокруг центра кольца.
Длина дуги меняется не переливом (хорды режут кольцо — «клин»), а поворотом кусочков (arc_pieces).
"""

from __future__ import annotations

import math
import random

from morphkit import O, Slide
from morphkit import vector as V
from morphkit.presets import Fx
from morphkit.theme import mix

from lab import Variant
from lab._b_util import (arc_band, arc_pieces, arc_pts, ax, axis, bar_band, ellipse_pts, head, move_scale, orbit_dot,
                         pol, rect_band, ring_track, shade, squash, text)
from morphkit import Loop

C = (9.0, 3.95)
FAM = "rings"


def _seg_ring(theme, id, c, r_in, r_out, n, gap, rot0=0.0, fills=None, z=6, R=None, nn=64):
    """Кольцо из n сегментов с зазорами gap (градусы); каждый сегмент — форма на оси, повернута на rot0 + i·360/n."""
    step = 360 / n
    g = arc_band(c[0], c[1], r_in, r_out, gap / 2, step - gap / 2, nn)
    out = []
    for i in range(n):
        f = fills[i] if fills else shade(theme, "ink", 0.55)
        out.append(axis(f"!!{id}{i}", g, c, R or r_out * 1.001, rot=rot0 + i * step, fill=f, z=z))
    return out


# ----------------------------------------------------------------------------- 1. лупа идёт по кольцу

def v_magnifier(theme) -> Variant:
    vals = [62, 70, 81, 77, 90, 104, 118, 111, 96, 88, 74, 69]
    months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь",
              "Ноябрь", "Декабрь"]
    vmax = max(vals)
    fills = [shade(theme, "ink", 0.82 - 0.55 * (v - 55) / (vmax - 55)) for v in vals]

    def state(k, sub):
        a0 = -90 + 30 * k
        objs = head("Лупа по кольцу", sub)
        objs += _seg_ring(theme, "seg", C, 1.85, 2.3, 12, 3.0, rot0=-90, fills=fills)
        lens = arc_band(C[0], C[1], 1.62, 2.72, 0.6, 29.4, 30)
        shadow = arc_band(C[0], C[1], 1.66, 2.8, 2.0, 31.0, 30)
        objs.append(axis("!!lens_sh", shadow, C, 2.85, rot=a0, fill="bg", fa=0.55, z=19))
        objs.append(axis("!!lens", lens, C, 2.85, rot=a0, fill="accent", ln="bg", lw=1.5, z=20))
        lx, ly = pol(*C, 3.25, a0 + 15)
        objs.append(text(f"mon{k}", lx - 0.8, ly - 0.22, 1.6, 0.44, months[k], sz=16, col="ink", al="c", va="m", b=True))
        objs.append(text("!!cap", C[0] - 1.2, C[1] - 0.62, 2.4, 0.36, "заказов за месяц", sz=13, col="muted", al="c"))
        objs.append(text(f"val{k}", C[0] - 1.2, C[1] - 0.25, 2.4, 0.8, str(vals[k]), sz=48, col="ink", al="c", b=True,
                         font="head"))
        return objs

    return Variant(FAM, "magnifier", "Лупа-сегмент обходит кольцо",
                   "Кусок кольца, увеличенный и поднятый, едет по кругу к нужному месяцу; в центре — его значение. "
                   "Роль: разбор годового цикла по месяцам, сезонность, «где мы сейчас» в цикле.",
                   [Slide(state(1, "Февраль — низкий сезон"), dur=800),
                    Slide(state(5, "Июнь — рост"), dur=850),
                    Slide(state(9, "Октябрь — спад"), dur=850)],
                   tags=["ring", "magnifier", "orbit", "data", "navigation"], score=4)


# ----------------------------------------------------------------------------- 2. прогресс по кольцу

def v_progress(theme) -> Variant:
    r_in, r_out = 1.75, 2.25
    th = r_out - r_in
    rm = (r_in + r_out) / 2

    def state(frac, label, sub):
        a1 = -90 + 360 * frac
        objs = head("Прогресс по кругу", sub)
        objs.append(ring_track("!!trk", C, r_in, r_out, fill="surface2"))
        objs += arc_pieces("!!pr", C, r_in, r_out, -90, a1, k=12, fill="accent", z=8)
        objs.append(orbit_dot("!!cap0", C, rm, -90, th, R=r_out * 1.001, fill="accent", z=9))
        objs.append(orbit_dot("!!cap1", C, rm, a1, th, R=r_out * 1.001, fill="accent", z=9))
        objs.append(orbit_dot("!!knob", C, rm, a1, th * 0.45, R=r_out * 1.001, fill="bg", z=10))
        objs.append(text(f"pc{int(frac * 100)}", C[0] - 1.3, C[1] - 0.55, 2.6, 0.9, label, sz=54, b=True, col="ink",
                         al="c", font="head"))
        objs.append(text("!!pcap", C[0] - 1.3, C[1] + 0.42, 2.6, 0.36, "плана выполнено", sz=13, col="muted", al="c"))
        return objs

    return Variant(FAM, "progress", "Прогресс растёт строго по кольцу",
                   "Дуга прогресса из 12 кусочков на оси: при росте кусочки поворачиваются по кругу, конец с круглой "
                   "заглушкой едет по кольцу — без «клина» blockArc. Роль: KPI, доля плана, этап проекта.",
                   [Slide(state(0.25, "25%", "Первый квартал"), dur=800),
                    Slide(state(0.6, "60%", "Полугодие"), dur=850),
                    Slide(state(0.86, "86%", "К концу года"), dur=800)],
                   tags=["ring", "progress", "data", "kpi"], score=4)


# ----------------------------------------------------------------------------- 3. вложенные кольца с разной скоростью

def v_nested(theme) -> Variant:
    rings = [  # (r_in, r_out, n, gap, цвет)
        (2.05, 2.4, 8, 6.0, shade(theme, "ink", 0.35)),
        (1.55, 1.9, 6, 7.0, shade(theme, "ink", 0.55)),
        (1.05, 1.4, 4, 9.0, shade(theme, "ink", 0.7)),
    ]
    names = ["Стратегия · год", "Команды · квартал", "Задачи · неделя"]
    starts = [[-70, 10, -90], [-130, 60, -90], [-20, -170 + 360, -90]]  # углы активного сегмента в 3 состояниях

    def state(s, sub):
        objs = head("Три ритма", sub)
        for j, (ri, ro, n, gap, col) in enumerate(rings):
            step = 360 / n
            rot0 = starts[j][s] - step / 2
            fills = [("accent" if s == 2 else mix(theme.c("accent"), theme.c("bg"), 0.35)) if i == 0 else col
                     for i in range(n)]
            objs += _seg_ring(theme, f"n{j}_", C, ri, ro, n, gap, rot0=rot0, fills=fills, z=6 + j)
        objs.append(O("!!core", "oval", C[0] - 0.55, C[1] - 0.55, 1.1, 1.1, fill="surface2", z=5))
        for j, nm in enumerate(names):
            objs.append(text(f"!!lg{j}", 0.7, 3.0 + j * 0.55, 3.6, 0.4, nm, sz=15, col=["ink", "ink2", "muted"][j]))
        if s == 2:
            objs.append(O("beam", "rect", C[0] - 0.02, C[1] - 2.75, 0.04, 0.35, fill="accent", z=12))
        return objs

    return Variant(FAM, "nested", "Вложенные кольца сходятся",
                   "Три сегментных кольца крутятся с разной скоростью и в разные стороны, на третьем шаге "
                   "активные сегменты выстраиваются в луч наверху. Роль: синхронизация уровней планирования.",
                   [Slide(state(0, "Каждый уровень живёт в своём темпе"), dur=800),
                    Slide(state(1, "Темпы расходятся"), dur=850),
                    Slide(state(2, "Точка синхронизации"), dur=900)],
                   tags=["ring", "nested", "rotation", "metaphor"], score=4)


# ----------------------------------------------------------------------------- 4. сегменты = категории

PAL5 = ["accent", "accent2", "ink2", "muted", "accent3"]


def _donut_cats(theme, id, c, r_in, r_out, shares, gap=2.0, pop=None, k=5):
    out, a = [], -90.0
    tot = sum(shares)
    for i, s in enumerate(shares):
        span = 360 * s / tot
        ri, ro = (r_in + 0.12, r_out + 0.35) if pop == i else (r_in, r_out)
        out += arc_pieces(f"!!{id}{i}_", c, ri, ro, a + gap / 2, a + span - gap / 2, k=k, R=(r_out + 0.36) * 1.001,
                          fill=PAL5[i], z=8)
        out.append((a + span / 2, i))
        a += span
    objs = [o for o in out if isinstance(o, O)]
    mids = [m for m in out if not isinstance(m, O)]
    return objs, mids


def v_categories(theme) -> Variant:
    cats = ["Розница", "Онлайн", "Опт", "Экспорт", "Сервис"]
    years = [("2023", [44, 18, 22, 9, 7]), ("2025", [30, 34, 16, 12, 8]), ("2025", [30, 34, 16, 12, 8])]

    def state(s, sub):
        yr, sh = years[s]
        objs = head("Структура выручки", sub)
        donut, mids = _donut_cats(theme, "cat", C, 1.5, 2.25, sh, pop=1 if s == 2 else None)
        objs += donut
        for a, i in mids:
            rr = 2.95 if (s == 2 and i == 1) else 2.7
            x, y = pol(*C, rr, a)
            objs.append(text(f"pc{s}_{i}", x - 0.45, y - 0.2, 0.9, 0.4, f"{sh[i]}%", sz=15, b=True,
                             col="ink" if not (s == 2 and i == 1) else "accent", al="c", va="m"))
        for i, nm in enumerate(cats):
            objs.append(O(f"!!lgs{i}", "rect", 0.75, 3.05 + i * 0.5, 0.22, 0.22, fill=PAL5[i], z=6))
            objs.append(text(f"!!lgt{i}", 1.1, 2.97 + i * 0.5, 2.6, 0.4, nm, sz=15, col="ink2"))
        objs.append(text(f"yr{s}", C[0] - 1.0, C[1] - 0.4, 2.0, 0.8, yr, sz=40, b=True, col="ink", al="c", font="head"))
        return objs

    return Variant(FAM, "categories", "Доли перетекают по кругу",
                   "Кольцо-пончик из форм: доли меняются, а границы сегментов едут по окружности (кусочки на оси), "
                   "затем растущая доля выдвигается. Роль: структура до/после, сдвиг каналов.",
                   [Slide(state(0, "Два года назад"), dur=800),
                    Slide(state(1, "Сейчас: онлайн вырос"), dur=900),
                    Slide(state(2, "Онлайн — каждый третий рубль"), dur=600)],
                   tags=["ring", "donut", "data", "shares"], score=4)


# ----------------------------------------------------------------------------- 5. кольцо разворачивается в полосу и столбики

def v_unroll(theme) -> Variant:
    cats = ["Розница", "Онлайн", "Опт", "Экспорт", "Сервис"]
    sh = [30, 34, 16, 12, 8]
    tot = sum(sh)
    n = 40
    r_in, r_out = 1.65, 2.15
    x0, L, yb, th = 1.4, 10.6, 3.9, 0.5

    def state(s, sub):
        objs = head("Из кольца — в линейку", sub)
        a, x = -90.0, x0
        order = sorted(range(5), key=lambda i: -sh[i])
        for i, v in enumerate(sh):
            span = 360 * v / tot
            ln = L * v / tot
            flip = 0 < ((a + span / 2) % 360) < 180  # нижняя половина: внешний край ляжет низом полосы
            if s == 0:
                g = arc_band(C[0], C[1], r_in, r_out, a + 0.8, a + span - 0.8, n)
            elif s == 1:
                g = bar_band(x + 0.03, yb, ln - 0.06, th, n)
            else:
                rk = order.index(i)
                g = bar_band(3.2, 2.35 + rk * 0.85, 8.2 * v / max(sh), 0.5, n)
            if s > 0 and flip:
                pts = list(g.exterior.coords)[:-1]
                g = V.Polygon(pts[n:] + pts[:n])
            objs.append(V.shape(f"!!u{i}", g, fill=PAL5[i], z=8))
            if s == 1:
                objs.append(text(f"ul{i}", x, yb + th + 0.12, max(ln, 0.9), 0.4, f"{v}%", sz=14, b=True, col="ink"))
            if s == 2:
                rk = order.index(i)
                objs.append(text(f"!!un{i}", 0.7, 2.37 + rk * 0.85, 2.35, 0.46, cats[i], sz=15, col="ink2", al="r",
                                 va="m"))
                objs.append(text(f"uv{i}", 3.3 + 8.2 * v / max(sh), 2.37 + rk * 0.85, 0.9, 0.46, f"{v}%", sz=15,
                                 b=True, col="ink", va="m"))
            a += span
            x += ln
        return objs

    return Variant(FAM, "unroll", "Кольцо разворачивается в полосу",
                   "Сегменты пончика переливаются в одну полосу 100% (разрез сверху), полоса распадается на "
                   "отсортированные столбики. Роль: от «общей картины» к точному сравнению долей.",
                   [Slide(state(0, "Доли каналов"), dur=800),
                    Slide(state(1, "Разрезаем кольцо"), dur=900),
                    Slide(state(2, "И сравниваем"), dur=800)],
                   tags=["ring", "unroll", "shape-morph", "data"], score=3)


# ----------------------------------------------------------------------------- 6. части кольца расходятся

def v_explode(theme) -> Variant:
    parts = ["Сбор", "Очистка", "Разметка", "Обучение", "Проверка", "Запуск", "Мониторинг", "Обратная связь"]
    n = len(parts)
    step = 360 / n
    r_in, r_out = 1.45, 2.2

    def state(s, sub):
        objs = head("Из чего состоит цикл", sub)
        for i in range(n):
            a0 = -90 + i * step + 1.5
            a1 = -90 + (i + 1) * step - 1.5
            g = arc_band(C[0], C[1], r_in, r_out, a0, a1, 24)
            mid = (a0 + a1) / 2
            col = shade(theme, "ink", 0.3 + 0.4 * (i % 2))
            if s >= 1:
                dx, dy = pol(0, 0, 0.45, mid)
                g = V.move(g, dx, dy)
            if s == 2 and i == 3:
                cg = g.centroid
                g = V.move(V.scale(g, 1.25, origin=(cg.x, cg.y)), 0, 0)
                col = "accent"
            elif s == 2:
                col = shade(theme, "ink", 0.72)
            objs.append(V.shape(f"!!ex{i}", g, fill=col, z=8))
            if s >= 1:
                x, y = pol(*C, 3.05, mid)
                w = 1.7
                al = "l" if x > C[0] + 0.3 else ("r" if x < C[0] - 0.3 else "c")
                bx = x if al == "l" else (x - w if al == "r" else x - w / 2)
                objs.append(text(f"!!el{i}", bx, y - 0.2, w, 0.4, parts[i], sz=14,
                                 col="accent" if (s == 2 and i == 3) else "ink2", al=al, va="m",
                                 b=(s == 2 and i == 3)))
        return objs

    fx = [Fx("entrance_fade", f"!!el{i}", start="at", delay=0.1 + 0.05 * i, dur=0.35) for i in range(n)]
    return Variant(FAM, "explode", "Сегменты расходятся и подписываются",
                   "Цельное кольцо процесса раскрывается: сегменты отходят от центра, у каждого появляется имя, "
                   "затем один выдвигается и подсвечивается. Роль: состав цикла, «где у нас узкое место».",
                   [Slide(state(0, "Восемь этапов"), dur=800),
                    Slide(state(1, "Раскрываем этапы"), dur=850, fx=fx),
                    Slide(state(2, "Узкое место — обучение"), dur=800)],
                   tags=["ring", "fragment", "explode", "process"], score=4)


# ----------------------------------------------------------------------------- 7. кольцо наклоняется в 3D (из 2D)

def v_ring3d(theme) -> Variant:
    cats = ["Розница", "Онлайн", "Опт", "Экспорт", "Сервис"]
    sh = [30, 34, 16, 12, 8]
    tot = sum(sh)
    c = (8.9, 3.7)
    r_in, r_out = 1.25, 2.35
    nE = 40

    def sq(pts, k, dz):
        return [(x, c[1] + (y - c[1]) * k + dz) for x, y in pts]

    def state(s, sub):
        k = 1.0 if s == 0 else 0.42
        depth = 0.003 if s == 0 else 0.42
        objs = head("Кольцо в объёме", sub)
        a = -90.0
        for i, v in enumerate(sh):
            span = 360 * v / tot
            a0, a1 = a + 1.0, a + span - 1.0
            lift = -0.5 if (s == 2 and i == 1) else 0.0
            top = arc_band(c[0], c[1], r_in, r_out, a0, a1, nE)
            topp = V.Polygon(sq(list(top.exterior.coords)[:-1], k, lift))
            col = theme.c(PAL5[i])
            # внешняя стенка — видна спереди (углы 0…180)
            w0, w1 = max(a0, 0.0), min(a1, 180.0)
            if a1 > 360:
                w0, w1 = max(a0, 360.0), min(a1, 540.0)
            if w1 > w0:
                arc = [pol(*c, r_out, w0 + (w1 - w0) * j / 23) for j in range(24)]
                up = sq(arc, k, lift)
                dn = sq(arc, k, lift + depth)
                objs.append(V.shape(f"!!wo{i}", V.Polygon(up + dn[::-1]), fill=mix(col, theme.c("bg"), 0.45), z=7 + (
                    10 if (s == 2 and i == 1) else 0)))
            # внутренняя стенка — видна сзади (углы 180…360)
            w0, w1 = max(a0, 180.0), min(a1, 360.0)
            if w1 > w0:
                arc = [pol(*c, r_in, w0 + (w1 - w0) * j / 23) for j in range(24)]
                objs.append(V.shape(f"!!wi{i}", V.Polygon(sq(arc, k, lift) + sq(arc, k, lift + depth)[::-1]),
                                    fill=mix(col, theme.c("bg"), 0.6), z=6))
            objs.append(V.shape(f"!!tp{i}", topp, fill=col, z=8 + (10 if (s == 2 and i == 1) else 0)))
            a += span
        for i, nm in enumerate(cats):
            objs.append(O(f"!!lgs{i}", "rect", 0.75, 3.05 + i * 0.5, 0.22, 0.22, fill=PAL5[i], z=6))
            objs.append(text(f"!!lgt{i}", 1.1, 2.97 + i * 0.5, 2.6, 0.4, nm, sz=15, col="ink2"))
        if s == 2:
            objs.append(text("lift", 9.3, 6.0, 3.6, 0.5, "Онлайн — 34%", sz=20, b=True, col="accent"))
        return objs

    return Variant(FAM, "ring3d", "Кольцо наклоняется в объём",
                   "Плоский пончик (вид сверху) наклоняется: верх сжимается по вертикали, вырастают стенки — "
                   "получается 3D-диск без 3D; затем один сегмент поднимается над остальными. "
                   "Роль: «вау» на слайде со структурой, акцент на одной доле.",
                   [Slide(state(0, "Вид сверху"), dur=800),
                    Slide(state(1, "Наклоняем"), dur=900),
                    Slide(state(2, "Поднимаем главное"), dur=700)],
                   tags=["ring", "3d", "pseudo-3d", "data"], score=4)


# ----------------------------------------------------------------------------- 8. 100 точек собираются по кругу

def v_dots100(theme) -> Variant:
    n, on = 100, 37
    rnd = random.Random(5)
    flags = [1] * on + [0] * (n - on)
    rnd.shuffle(flags)
    r = 2.1
    # исходно: точка i на угле i·3.6; цель: «включённые» — подряд сверху, порядок по кругу сохраняется
    hot = [i for i in range(n) if flags[i]]
    cold = [i for i in range(n) if not flags[i]]
    best = None
    for off in range(n):
        tgt = {}
        for k, i in enumerate(hot):
            tgt[i] = (off + k) % n
        for k, i in enumerate(cold):
            tgt[i] = (off + on + k) % n
        dev = max(abs(((tgt[i] - i) * 3.6 + 180) % 360 - 180) for i in range(n))
        if best is None or dev < best[0]:
            best = (dev, off, tgt)
    _, off, tgt = best
    shift = -off * 3.6  # поворот всей картинки, чтобы собранная дуга начиналась сверху

    def state(s, sub):
        objs = head("37 из 100", sub)
        for i in range(n):
            if s == 0:
                a = -90 + i * 3.6
            else:
                a = -90 + i * 3.6 + (((tgt[i] - i) * 3.6 + 180) % 360 - 180) + shift
            hotc = flags[i]
            d = 0.17 if not (s == 2 and hotc) else 0.24
            col = "accent" if hotc else shade(theme, "ink", 0.7)
            if s == 2 and not hotc:
                col = shade(theme, "ink", 0.82)
            objs.append(orbit_dot(f"!!d{i}", C, r, a, d, R=r + 0.13, fill=col, z=8))
        objs.append(text("!!big", C[0] - 1.3, C[1] - 0.6, 2.6, 1.0, "37%", sz=54, b=True, col="ink", al="c",
                         font="head"))
        objs.append(text("!!bcap", C[0] - 1.3, C[1] + 0.45, 2.6, 0.36, "клиентов вернулись", sz=13, col="muted",
                         al="c"))
        return objs

    return Variant(FAM, "dots100", "Точки собираются в дугу",
                   "Сто точек по кругу, 37 подсвечены вразброс; затем они скользят по кольцу и собираются в одну "
                   "дугу — доля становится видимой. Роль: доля, «каждый третий», переход от хаоса к выводу.",
                   [Slide(state(0, "Вразброс — не видно"), dur=800),
                    Slide(state(1, "Собираем по кругу"), dur=900),
                    Slide(state(2, "Больше трети"), dur=600)],
                   tags=["ring", "dots", "orbit", "data", "sorting"], score=4)


# ----------------------------------------------------------------------------- 9. кольцо-навигация под неподвижной лупой

def v_nav(theme) -> Variant:
    secs = ["Рынок", "Продукт", "Команда", "Финансы", "План"]
    n = 5
    step = 72
    r_in, r_out = 1.7, 2.3

    def state(k, sub):
        objs = head("Навигация по кольцу", sub)
        rot0 = -90 - step / 2 - k * step
        for i in range(n):
            g = arc_band(C[0], C[1], r_in, r_out, 2, step - 2, 36)
            objs.append(axis(f"!!sg{i}", g, C, 3.0, rot=rot0 + i * step, fill=shade(theme, "ink", 0.35 + 0.1 * i), z=6))
            for j in range(i + 1):
                ang = step / 2 + (j - i / 2) * 5.5
                objs.append(orbit_dot(f"!!sd{i}_{j}", C, (r_in + r_out) / 2, rot0 + i * step + ang, 0.12, R=3.0,
                                      fill="bg", z=7))
        win = arc_band(C[0], C[1], r_in - 0.22, r_out + 0.3, -90 - step / 2 + 1, -90 + step / 2 - 1, 36)
        objs.append(V.shape("!!win", win, fill=None, ln="accent", lw=3.0, z=12))
        objs.append(text(f"nm{k}", C[0] - 1.4, C[1] - 0.5, 2.8, 0.7, secs[k], sz=34, b=True, col="ink", al="c",
                         font="head"))
        objs.append(text(f"no{k}", C[0] - 1.4, C[1] + 0.22, 2.8, 0.4, f"раздел {k + 1} из 5", sz=14, col="muted",
                         al="c"))
        return objs

    return Variant(FAM, "nav", "Кольцо разделов под лупой",
                   "Кольцо из пяти разделов вращается на месте, текущий раздел въезжает под неподвижное окно сверху; "
                   "в центре — его имя. Роль: оглавление и переходы между разделами вместо «колеса в угол».",
                   [Slide(state(0, "Начинаем"), dur=800),
                    Slide(state(1, "Следующий раздел"), dur=800),
                    Slide(state(2, "Дальше по кругу"), dur=800)],
                   tags=["ring", "navigation", "rotation"], score=4)


# ----------------------------------------------------------------------------- 10. кольцо раскрывается в скобки

def v_brackets(theme) -> Variant:
    n = 64

    def state(s):
        objs = []
        if s == 0:
            gl = arc_band(C[0], C[1], 1.75, 2.15, 92, 268, n)
            gr = arc_band(C[0], C[1], 1.75, 2.15, -88, 88, n)
            objs += head("Две половины", "Один круг — две позиции")
        else:
            R, ang = 5.0, 34
            cl = (4.6 + R, 3.95)
            cr = (12.0 - R + 0.4, 3.95)
            gl = arc_band(cl[0], cl[1], R - 0.2, R, 180 - ang, 180 + ang, n)
            gr = arc_band(cr[0], cr[1], R - 0.2, R, -ang, ang, n)
            gl = V.Polygon(list(gl.exterior.coords)[:-1][::-1][n:] + list(gl.exterior.coords)[:-1][::-1][:n])
            gl = arc_band(cl[0], cl[1], R - 0.2, R, 180 + ang, 180 - ang, n)
            gl = arc_band(cl[0], cl[1], R - 0.2, R, 180 - ang, 180 + ang, n)
            objs += head("Две половины", "Между ними — договорённость")
        objs.append(V.shape("!!bl", gl, fill="ink", z=8))
        objs.append(V.shape("!!br", gr, fill="accent", z=8))
        if s == 1:
            objs.append(text("st", 5.35, 3.2, 5.4, 1.5, ["Общий стандарт", "данных к марту"], sz=30, b=True, col="ink",
                             al="c", va="m", font="head"))
        return objs

    return Variant(FAM, "brackets", "Кольцо раскрывается в скобки",
                   "Две половины кольца расходятся и выпрямляются в скобки, между ними появляется тезис. "
                   "Роль: «две стороны пришли к соглашению», цитата, главный вывод раздела.",
                   [Slide(state(0), dur=800),
                    Slide(state(1), dur=900, fx=[Fx("entrance_fade", "st", start="at", delay=0.1, dur=0.4)])],
                   tags=["ring", "shape-morph", "text-frame"], score=3)


# ----------------------------------------------------------------------------- 11. линза-«рыбий глаз» на шкале

def v_fisheye(theme) -> Variant:
    n = 60
    r0 = 2.0
    hours = ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"]

    def state(k, sub, label, val):
        objs = head("Пик нагрузки", sub)
        for i in range(n):
            g = arc_band(C[0], C[1], r0, r0 + (0.32 if i % 5 == 0 else 0.18), -0.45, 0.45, 2)
            objs.append(axis(f"!!tk{i}", g, C, 3.0, rot=-90 + i * 6, fill=shade(theme, "ink", 0.6), z=6))
        cen = -90 + k * 6
        for j in range(-5, 6):
            bump = math.exp(-(j / 2.6) ** 2)
            g = arc_band(C[0], C[1], r0 - 0.05 - 0.25 * bump, r0 + 0.35 + 0.6 * bump, -0.9 - 0.6 * bump,
                         0.9 + 0.6 * bump, 2)
            objs.append(axis(f"!!ln{j}", g, C, 3.0, rot=cen + j * 6,
                             fill=mix(theme.c("accent"), theme.c("bg"), 0.75 * (1 - bump)), z=10))
        for h in range(6):
            x, y = pol(*C, 2.75, -90 + h * 60)
            objs.append(text(f"!!h{h}", x - 0.45, y - 0.18, 0.9, 0.36, hours[h], sz=12, col="muted", al="c", va="m"))
        objs.append(text(f"lb{k}", C[0] - 1.2, C[1] - 0.55, 2.4, 0.8, label, sz=40, b=True, col="ink", al="c",
                         font="head"))
        objs.append(text(f"vl{k}", C[0] - 1.2, C[1] + 0.25, 2.4, 0.4, val, sz=14, col="muted", al="c"))
        return objs

    return Variant(FAM, "fisheye", "Линза-«рыбий глаз» на циферблате",
                   "Шкала суток из 60 рисок; группа удлинённых акцентных рисок (линза) едет по кругу к пику, "
                   "как увеличительное стекло. Роль: время пика, «когда это происходит», расписание.",
                   [Slide(state(14, "Утро", "09:20", "первый пик"), dur=800),
                    Slide(state(35, "День", "14:00", "максимум за сутки"), dur=850),
                    Slide(state(52, "Вечер", "20:40", "второй пик"), dur=850)],
                   tags=["ring", "magnifier", "time", "data"], score=4)


# ----------------------------------------------------------------------------- 12. кольцо-столбики: выше/ниже плана

def v_diverge(theme) -> Variant:
    n = 12
    r0 = 1.85
    plan = [[4, 7, 3, -2, -5, 2, 6, 9, 5, -3, 1, 8], [-3, -6, -2, 4, 7, 5, -1, 2, 6, 8, 3, -2]]
    mn = ["Я", "Ф", "М", "А", "М", "И", "И", "А", "С", "О", "Н", "Д"]

    def state(s, sub):
        objs = head("Выше и ниже плана", sub)
        objs.append(O("!!base", "oval", C[0] - r0, C[1] - r0, 2 * r0, 2 * r0, fill=None, ln="ink2", lw=1.25, z=7))
        vals = plan[min(s, 1)]
        for i in range(n):
            v = vals[i]
            a0, a1 = 3, 27
            if v >= 0:
                g = arc_band(C[0], C[1], r0 + 0.03, r0 + 0.03 + 0.09 * v, a0, a1, 14)
            else:
                g = arc_band(C[0], C[1], r0 - 0.03 + 0.09 * v, r0 - 0.03, a0, a1, 14)
            col = "accent" if v >= 0 else shade(theme, "ink", 0.5)
            if s == 2 and v < 0:
                col = shade(theme, "ink", 0.78)
            objs.append(axis(f"!!b{i}", g, C, 2.95, rot=-90 + i * 30, fill=col, z=8))
            x, y = pol(*C, 3.2, -90 + i * 30 + 15)
            objs.append(text(f"!!m{i}", x - 0.25, y - 0.18, 0.5, 0.36, mn[i], sz=12, col="muted", al="c", va="m"))
        objs.append(text(f"yr{min(s, 1)}", C[0] - 0.9, C[1] - 0.4, 1.8, 0.8, ["2024", "2025"][min(s, 1)], sz=34,
                         b=True, col="ink", al="c", font="head"))
        return objs

    return Variant(FAM, "diverge", "Кольцо-столбики «выше/ниже плана»",
                   "Месяцы по кругу: столбик наружу — выше плана, внутрь — ниже; при смене года столбики "
                   "перерастают на месте. Роль: сезонность отклонений, сравнение двух лет на одной фигуре.",
                   [Slide(state(0, "Прошлый год"), dur=800),
                    Slide(state(1, "Этот год: весна выросла"), dur=850),
                    Slide(state(2, "Провалы — только зимой"), dur=600)],
                   tags=["ring", "radial-bars", "data"], score=3)


# ----------------------------------------------------------------------------- ЖИВАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ 1: кольцо тем

def seq_ring(theme) -> Variant:
    """Одна фигура на 8 состояний: кольцо тем -> лупа на теме 1 -> лупа разворачивается в панель -> лупа на теме 2 ->
    кольцо наклоняется в 3D -> уходит на фон за итоговые числа -> сегменты становятся колонками -> снова кольцо."""
    c = (9.3, 4.0)
    topics = ["Рынок", "Продукт", "Команда", "Финансы", "План"]
    vals = [42, 64, 35, 51, 28]
    r_in, r_out, n = 1.55, 2.15, 32
    cols = [shade(theme, "ink", 0.3 + 0.1 * i) for i in range(5)]
    seg_a = [(-90 + 72 * i + 1.5, -90 + 72 * (i + 1) - 1.5) for i in range(5)]
    mid = [(a0 + a1) / 2 for a0, a1 in seg_a]
    K, DEPTH = 0.42, 0.42
    bars = [(2.3 + i * 2.05, 1.25) for i in range(5)]
    base_y, hmax = 6.25, 3.3

    def col_box(i):
        x, w = bars[i]
        h = hmax * vals[i] / max(vals)
        return x, base_y - h, w, h

    def topface(i, st):
        g = arc_band(c[0], c[1], r_in, r_out, *seg_a[i], n)
        if st in (4, 5):
            g = squash(g, c, K, -0.25)
        if st == 5:
            g = move_scale(g, (c[0], c[1]), 0.55, 0.9, -1.3)
        if st == 6:
            g = rect_band(*col_box(i), n=n, vertical=True)
        return g

    def wall(i, st, a0, a1, r, outer=True):
        arc = arc_pts(c[0], c[1], r, a0, a1, 16)
        if st in (4, 5):
            up = [(x, c[1] + (y - c[1]) * K - 0.25) for x, y in arc]
            dn = [(x, y + DEPTH) for x, y in up]
            if st == 5:
                up = [(c[0] + (x - c[0]) * 0.55 + 0.9, c[1] + (y - c[1]) * 0.55 - 1.3) for x, y in up]
                dn = [(c[0] + (x - c[0]) * 0.55 + 0.9, c[1] + (y - c[1]) * 0.55 - 1.3) for x, y in dn]
        elif st == 6:
            x, y, w, h = col_box(i)
            up = [(x + w * k / 15, base_y) for k in range(16)]
            dn = [(x + w * k / 15, base_y + 0.001) for k in range(16)]
        else:
            up = arc
            dn = [(px + 0.0005, py + 0.0005) for px, py in arc]
        return V.Polygon(up + dn[::-1])

    walls_out = {1: (0.0, seg_a[1][1]), 2: seg_a[2], 3: (seg_a[3][0], 180.0)}
    walls_in = {0: seg_a[0], 3: (180.0, seg_a[3][1]), 4: seg_a[4]}
    mag_on = [0, 0, 0, 1, 1, 1, 1, 1]

    def mag_abs(st):
        k = mag_on[st]
        if st == 0:
            return arc_band(c[0], c[1], r_in, r_out, *seg_a[0], n)
        if st == 2:
            return rect_band(0.7, 2.35, 4.6, 3.9, n=n)
        g = arc_band(c[0], c[1], r_in - 0.22, r_out + 0.42, seg_a[k][0] - 1.2, seg_a[k][1] + 1.2, n)
        if st in (4, 5):
            g = squash(g, c, K, -0.25 - 0.4)
        if st == 5:
            g = move_scale(g, c, 0.55, 0.9, -1.3)
        if st == 6:
            x, y, w, h = col_box(k)
            g = rect_band(x - 0.08, y - 0.08, w + 0.16, h + 0.08, n=n, vertical=True)
        return g

    heads = [("Пять тем", "План доклада по кругу"), ("01 · Рынок", "Лупа на первой теме"),
             ("01 · Рынок", "Лупа раскрывается в панель"), ("02 · Продукт", "Следующая тема"),
             ("Темы связаны", "Кольцо наклоняется — видно целое"), ("Итоги года", "Кольцо уходит на фон"),
             ("Темы в цифрах", "Сегменты стали колонками"), ("Главное — продукт", "Снова целое")]
    slides = []
    for st in range(8):
        objs = head(*heads[st])
        fa = 0.22 if st == 5 else 1.0
        for i in range(5):
            objs.append(ax(f"!!rs{i}", topface(i, st), 0.0, pivot=c, fill=cols[i], fa=fa, z=8))
            if i in walls_out:
                objs.append(ax(f"!!rw{i}", wall(i, st, *walls_out[i], r_out), 0.0, pivot=c,
                               fill=mix(cols[i], theme.c("bg"), 0.5), fa=fa, z=7))
            if i in walls_in:
                objs.append(ax(f"!!rv{i}", wall(i, st, *walls_in[i], r_in), 0.0, pivot=c,
                               fill=mix(cols[i], theme.c("bg"), 0.65), fa=fa, z=6))
        mag_rot = mid[mag_on[st]] + 90 if st != 2 else mid[0] + 90
        mcol = cols[0] if st == 0 else "accent"
        objs.append(ax("!!rmag", mag_abs(st), mag_rot, pivot=c, fill=mcol if st != 2 else "surface",
                       ln="accent" if st == 2 else None, lw=2.0 if st == 2 else 0, fa=0.3 if st == 5 else 1.0,
                       z=20 if st != 2 else 30))
        if st in (0, 1, 3, 7):
            for i in range(5):
                x, y = pol(*c, r_out + 0.55, mid[i])
                al = "l" if x > c[0] + 0.4 else ("r" if x < c[0] - 0.4 else "c")
                w = 1.7
                bx = x if al == "l" else (x - w if al == "r" else x - w / 2)
                on = i == mag_on[st] and st > 0
                objs.append(text(f"!!rl{i}", bx, y - 0.2, w, 0.4, topics[i], sz=15, b=on,
                                 col="accent" if on else "ink2", al=al, va="m"))
        if st in (0, 1, 3, 7):
            txt = ["2025", "+12%", "", "3 новых", "", "", "", "64"][st]
            objs.append(text(f"rc{st}", c[0] - 1.25, c[1] - 0.4, 2.5, 0.8, txt, sz=32, b=True, col="ink", al="c",
                             font="head"))
        fx, loops = [], []
        if st == 0:
            fx = [Fx("entrance_spinner", f"!!rs{i}", start="at", delay=0.05 + 0.07 * i, dur=0.6) for i in range(5)]
        if st == 2:
            lines = ["Рынок растёт на 12% в год", "Три сильных конкурента", "Ниша: малый бизнес"]
            for j, t in enumerate(lines):
                objs.append(text(f"rp{j}", 1.05, 2.7 + j * 1.15, 4.0, 0.9, t, sz=20, col="ink" if j else "accent",
                                 b=j == 0, va="m"))
            fx = [Fx("entrance_fade", f"rp{j}", start="at", delay=0.1 + 0.12 * j, dur=0.35) for j in range(3)]
        if st == 4:
            pts = ellipse_pts(c[0], c[1] - 0.25, (r_in + r_out) / 2, (r_in + r_out) / 2 * K, 72)
            loops = [Loop("flow", points=pts, n=4, period=3.6, size=0.12, color="accent", name="rflow", z=9)]
        if st == 5:
            nums = [("12%", "рост рынка"), ("3", "новых продукта"), ("+40", "человек в команде")]
            for j, (a, b) in enumerate(nums):
                objs.append(text(f"rn{j}", 0.9 + j * 4.1, 4.3, 3.6, 1.1, a, sz=60, b=True, col="ink", font="head"))
                objs.append(text(f"rm{j}", 0.9 + j * 4.1, 5.45, 3.6, 0.45, b, sz=16, col="muted"))
            fx = [Fx("entrance_fade", f"rn{j}", start="at", delay=0.1 + 0.1 * j, dur=0.4) for j in range(3)]
        if st == 6:
            for i in range(5):
                x, y, w, h = col_box(i)
                objs.append(text(f"!!rl{i}", x - 0.3, base_y + 0.12, w + 0.6, 0.4, topics[i], sz=15,
                                 col="accent" if i == 1 else "ink2", al="c", b=i == 1))
                objs.append(text(f"rv{i}", x - 0.3, y - 0.55, w + 0.6, 0.45, str(vals[i]), sz=18, b=True,
                                 col="ink", al="c"))
        slides.append(Slide(objs, dur=[800, 700, 850, 850, 900, 850, 900, 900][st], fx=fx, loops=loops))
    return Variant(FAM, "seq_ring", "Живое кольцо тем (8 состояний)",
                   "Одна фигура ведёт доклад: кольцо из пяти тем, увеличенная лупа-сегмент встаёт на тему, "
                   "раскрывается в панель с фактами, сворачивается и едет к следующей теме, кольцо наклоняется в "
                   "объём и уходит на фон за итоговые числа, сегменты становятся колонками и снова собираются. "
                   "Роль: сквозной мотив-навигатор всей презентации.",
                   slides, tags=["seq", "ring", "magnifier", "3d", "background", "chart", "navigation"], score=5)


# ----------------------------------------------------------------------------- ЖИВАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ 2: сто точек

def seq_dots(theme) -> Variant:
    """100 точек на 8 состояний: поле -> кольцо -> подсветка -> сбор дугой по кругу -> дуга отделяется в поле ->
    поле делится на группы -> группы возвращаются на кольцо цветом -> кольцо в перспективе уходит назад."""
    c = (9.2, 4.0)
    n, on, r = 100, 37, 2.1
    rnd = random.Random(11)
    flags = [1] * on + [0] * (n - on)
    rnd.shuffle(flags)
    hot = [i for i in range(n) if flags[i]]
    cold = [i for i in range(n) if not flags[i]]
    ang0 = {i: -90 + 3.6 * i for i in range(n)}
    best = None
    for off in range(n):
        tgt = {i: (off + k) % n for k, i in enumerate(hot)}
        tgt.update({i: (off + on + k) % n for k, i in enumerate(cold)})
        dev = max(abs(((tgt[i] - i) * 3.6 + 180) % 360 - 180) for i in range(n))
        if best is None or dev < best[0]:
            best = (dev, off, tgt)
    _, off, tgt = best
    ang3 = {i: ang0[i] + (((tgt[i] - i) * 3.6 + 180) % 360 - 180) - off * 3.6 for i in range(n)}
    rank = {i: k for k, i in enumerate(sorted(hot, key=lambda i: ang3[i]))}
    gsz = [18, 12, 7]
    grp = {i: (0 if rank[i] < 18 else (1 if rank[i] < 30 else 2)) for i in hot}
    gcol = ["accent", "accent3", "ink2"]
    gnames = ["Малый бизнес", "Средний", "Крупный"]
    dim = shade(theme, "ink", 0.72)

    def pos(i, st):
        if st == 0:
            return c[0] - 1.71 + (i % 10) * 0.38, c[1] - 1.71 + (i // 10) * 0.38, ang3[i]
        if st in (1, 2):
            return (*pol(*c, r, ang0[i]), ang0[i])
        if st in (3, 6) or not flags[i]:
            x, y = pol(*c, r, ang3[i])
            return x, y, ang3[i]
        if st == 4:
            k = rank[i]
            return 1.0 + (k % 9) * 0.42, 3.0 + (k // 9) * 0.42, ang3[i]
        if st == 5:
            k, g = rank[i], grp[i]
            k -= sum(gsz[:g])
            return 1.0 + g * 1.85 + (k % 3) * 0.4, 3.0 + (k // 3) * 0.4, ang3[i]
        x, y = pol(*c, r, ang3[i])
        return x, y, ang3[i]

    heads = [("100 клиентов", "Каждый — точка"), ("100 клиентов", "Выстраиваем по кругу"),
             ("37 вернулись", "Пока вразброс"), ("37 вернулись", "Собираем по кругу — больше трети"),
             ("Кто они", "Дуга выходит из кольца"), ("Три группы", "Делим по размеру бизнеса"),
             ("Группы на кольце", "Доля каждой группы"), ("Каждый третий", "Кольцо уходит в глубину")]
    slides = []
    for st in range(8):
        objs = head(*heads[st])
        for i in range(n):
            x, y, a = pos(i, st)
            d = 0.17
            col = dim if st < 2 else ("accent" if flags[i] else dim)
            if st >= 6 and flags[i]:
                col = gcol[grp[i]]
            fa = 1.0
            if st == 7:
                depth = (math.sin(math.radians(ang3[i])) + 1) / 2
                y = c[1] - 0.6 + (y - c[1]) * 0.36
                x = c[0] + (x - c[0]) * 1.1
                d = 0.1 + 0.12 * depth
                fa = 0.35 + 0.5 * depth
            g = V.circle(x, y, d / 2, seg=10)
            objs.append(ax(f"!!pd{i}", g, a, pivot=c, fill=col, fa=fa, z=8 + (1 if flags[i] else 0)))
        fx = []
        if st == 3:
            objs.append(text("pk3", c[0] - 1.2, c[1] - 0.5, 2.4, 1.0, "37%", sz=54, b=True, col="ink", al="c",
                             font="head"))
        if st == 4:
            objs.append(text("pk4", 1.0, 2.2, 4.0, 0.5, "37 компаний", sz=18, b=True, col="accent"))
        if st == 5:
            for g in range(3):
                objs.append(text(f"pg{g}", 0.85 + g * 1.85, 5.3, 1.8, 0.8, [gnames[g], str(gsz[g])], sz=13,
                                 col="ink2"))
            fx = [Fx("entrance_fade", f"pg{g}", start="at", delay=0.1 + 0.1 * g, dur=0.3) for g in range(3)]
        if st == 6:
            for g in range(3):
                objs.append(O(f"pq{g}", "oval", 0.8, 2.6 + g * 0.55, 0.2, 0.2, fill=gcol[g], z=6))
                objs.append(text(f"pt{g}", 1.15, 2.5 + g * 0.55, 3.4, 0.4, f"{gnames[g]} · {gsz[g]}", sz=15,
                                 col="ink2"))
        if st == 7:
            objs.append(text("pf", 0.7, 4.9, 7.5, 1.2, "Удержание — главный рычаг роста", sz=30, b=True,
                             col="ink", font="head"))
        slides.append(Slide(objs, dur=[800, 900, 600, 900, 850, 800, 850, 900][st], fx=fx))
    return Variant(FAM, "seq_dots", "Сто точек: поле, кольцо, группы (8 состояний)",
                   "Поле из ста точек выстраивается в кольцо, подсвеченные скользят по кругу в дугу-долю, дуга "
                   "выходит из кольца в поле, делится на группы, группы возвращаются на свои места цветом, кольцо "
                   "наклоняется в перспективу и уходит назад под вывод. Роль: сквозной разбор одной доли.",
                   slides, tags=["seq", "ring", "dots", "groups", "3d", "data"], score=4)


def variants(theme) -> list[Variant]:
    return [v_magnifier(theme), v_progress(theme), v_nested(theme), v_categories(theme), v_unroll(theme),
            v_explode(theme), v_ring3d(theme), v_dots100(theme), v_nav(theme), v_brackets(theme), v_fisheye(theme),
            v_diverge(theme), seq_ring(theme), seq_dots(theme)]
