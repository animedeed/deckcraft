"""Документы: стопка листов (объём сдвигом и тенью), веер, маркер-выделение строк, печать с «высотой» (тень),
листы влетают в папки (передний клапан папки выше листов по слою), документ делится на пункты и пункты
связываются ссылками (дуги + поток по ним), загиб страницы, закладки-указатели, лупа над строкой.

Тема для прогона — registry («Реестр»). Строки текста на листах — полоски (не текст), поэтому листы свободно
летают, поворачиваются и масштабируются без «каши букв».
"""

from __future__ import annotations

import math
import random

from morphkit import Fx, Loop, O
from morphkit import vector as V
from morphkit.recipes import doc_sheet
from morphkit.theme import SLIDE_H, SLIDE_W, mix

from lab import Variant
from lab._d_util import (DEC, S, bezier, body, dark, flow, head, kicker, label, light, line, ribbon, raw, rot_pt, stroke,
                         vs)

FAM = "docs"
W, H = SLIDE_W, SLIDE_H


def _v(key, title, idea, slides, tags, score) -> Variant:
    return Variant(FAM, key, title, idea, slides, tags=tags, score=score)


def page(theme, id: str, cx: float, cy: float, w: float, h: float, rot: float = 0.0, nl: int = 6, z: int = 10,
         alpha: float = 1.0, edge: str = "line", fill: str = "FFFFFF", hl: dict | None = None, lines_col: str = "line",
         shadow: float = 0.0, seed: int = 0) -> list[O]:
    """Лист с загнутым углом и nl строками-полосками; всё поворачивается вокруг центра листа.
    hl — {номер строки: цвет} перекраска строк; shadow — смещение тени (высота листа над столом)."""
    rnd = random.Random(seed)
    out = []
    if shadow > 0:
        sx, sy = cx + shadow, cy + shadow * 1.3
        out.append(O(f"{id}_sh", "rect", sx - w / 2, sy - h / 2, w, h, fill="ink", fa=0.10 * alpha, rot=rot, z=z - 1))
    out.append(doc_sheet(id, cx - w / 2, cy - h / 2, w, h, fill=fill, ln=edge, lw=1.0, rot=rot, z=z,
                         fa=alpha, la=alpha, meta=dict(DEC)))
    for i in range(nl):
        lw_ = w * (0.74 if i % 3 != 2 else 0.5) * (0.92 + 0.08 * rnd.random()) if i else w * 0.45
        lh = max(h * 0.035, 0.025)
        x0 = cx - w / 2 + w * 0.12
        y0 = cy - h / 2 + h * (0.14 + 0.74 * i / max(nl - 1, 1))
        c0 = (x0 + lw_ / 2, y0 + lh / 2)
        px, py = rot_pt(c0, rot, (cx, cy))
        col = (hl or {}).get(i, lines_col if i else "ink2")
        out.append(O(f"{id}_l{i}", "rect", px - lw_ / 2, py - lh / 2, lw_, lh * (1.0 if i else 1.4), fill=col, fa=alpha,
                     rot=rot, z=z + 1))
    return out


# ============================================================================= варианты

def stack_fan(theme) -> Variant:
    n = 7
    sl = []
    for st in range(3):
        o = [head(["Пакет документов", "Веер редакций", "Все листы рядом"][st], w=7)]
        for i in range(n):
            if st == 0:
                cx, cy, rot, s = 8.8 + i * 0.07, 4.3 - i * 0.07, -3 + i * 0.8, 1.0
            elif st == 1:
                t = (i - (n - 1) / 2) / ((n - 1) / 2)
                cx, cy, rot, s = 8.2 + t * 3.6, 4.6 + 0.6 * t * t, t * 16, 1.0
            else:
                cx, cy, rot, s = 1.6 + i * 1.72, 4.4, 0.0, 0.78
            on = st == 2 and i == 4
            o += page(theme, f"!!pg{i}", cx, cy, 1.9 * s, 2.6 * s, rot, nl=7, z=10 + 3 * i, edge="accent" if on else "line",
                      shadow=0.06 if st == 0 else 0.03, seed=i)
            if st == 2:
                o.append(label(f"pl{i}", cx, 6.0, f"ред. {i + 1}", w=1.4, sz=13, b=on, col="accent" if on else "ink2"))
        sl.append(S(o, 800, fx=[Fx("entrance_fade", f"pl{i}", start="at", delay=0.15 + 0.04 * i) for i in range(n)] if st == 2 else []))
    return _v("stack_fan", "Стопка → веер → ряд редакций",
              "Носитель «документ»: стопка из 7 листов (сдвиг и тень дают толщину), раскрывается веером по дуге, "
              "затем листы выстраиваются в ряд редакций, нужная — с контуром акцента. Строки-полоски едут вместе с листом.",
              sl, ["docs", "fan", "carrier", "3d"], 4)


def highlighter(theme) -> Variant:
    cx, cy, w, h = 4.0, 4.1, 4.4, 5.6
    nl = 11
    marks = [3, 7]
    hcol = mix(theme.c("accent3"), "FFE45C", 0.6)
    def ly(i):
        return cy - h / 2 + h * (0.14 + 0.74 * i / (nl - 1))
    sl = []
    # 1 лист
    o1 = page(theme, "!!pg", cx, cy, w, h, nl=nl, seed=3) + [head("Договор", x=7.2, w=5), body("!!b", 7.2, 1.4, 5, 0.4, "11 строк, 2 важные", sz=16, col="muted")]
    sl.append(S(o1, 700))
    # 2 маркер проводит по двум строкам
    o2 = page(theme, "!!pg", cx, cy, w, h, nl=nl, seed=3)
    for k, i in enumerate(marks):
        o2.append(O(f"!!hm{k}", "rect", cx - w / 2 + w * 0.09, ly(i) - 0.1, w * 0.8, 0.26, fill=hcol, fa=0.55, z=14))
    o2 += [head("Маркер", x=7.2, w=5), body("!!b", 7.2, 1.4, 5, 0.4, "срок и штраф", sz=16, col="muted")]
    sl.append(S(o2, 600, fx=[Fx("entrance_wipe", f"!!hm{k}", start="at", delay=0.15 + 0.45 * k, dur=0.4,
                                options={"direction": "left"}) for k in range(2)]))
    # 3 выделенные строки отрываются карточками
    o3 = page(theme, "!!pg", cx, cy, w, h, nl=nl, seed=3, hl={i: "muted" for i in marks})
    o3 += [head("Пункты отдельно", x=7.2, w=5.5)]
    for k, (i, t) in enumerate(zip(marks, ["Срок: 30 дней", "Штраф: 0,1 % в день"])):
        y = 2.4 + k * 1.6
        o3.append(O(f"!!hm{k}", "rect", 7.2, y, 5.2, 1.2, fill=hcol, fa=0.55, z=14))
        o3.append(body(f"hc{k}", 7.45, y + 0.35, 4.8, 0.5, t, sz=20, col="ink", b=True))
        o3.append(line(f"hk{k}", (cx + w * 0.41, ly(i)), (7.2, y + 0.6), ln="accent", lw=1.25, z=8, dash="dash"))
    sl.append(S(o3, 900, fx=[Fx("entrance_fade", f"hc{k}", start="at", delay=0.2 + 0.1 * k) for k in range(2)]))
    return _v("highlighter", "Маркер выделяет, строки отрываются",
              "Выделение строк маркером (вход «вытирание» слева направо — как рука), затем полосы маркера перетекают "
              "в карточки пунктов справа, к строкам тянутся пунктирные выноски. Для разбора договора или требования.",
              sl, ["docs", "highlight", "callout"], 4)


def _seal(cx, cy, r):
    """Печать тремя формами (у каждой не больше одной дырки — Morph переносит их как целые)."""
    ring = V.subtract(V.circle(cx, cy, r), V.circle(cx, cy, r * 0.86))
    ring2 = V.subtract(V.circle(cx, cy, r * 0.74), V.circle(cx, cy, r * 0.69))
    star = V.star(cx, cy - r * 0.38, r * 0.17, r * 0.07, 5)
    return [ring, ring2, star]


def seal_objs(c, r, rot, alpha, z, name="!!seal"):
    return [vs(name if k == 0 else f"{name}{k}", g, pivot=c, rot=rot % 360, fill="accent", fa=alpha, z=z + k)
            for k, g in enumerate(_seal(c[0], c[1], r))]


def stamp(theme) -> Variant:
    pc = (6.0, 4.1)
    sl = []
    for st in range(3):
        o = page(theme, "!!pg", pc[0], pc[1], 4.0, 5.4, nl=10, seed=8) + [head(["На подпись", "Удар печати", "Решение есть"][st], x=8.8, w=4.2)]
        if st == 0:
            c, r, rot, alpha, sh = (10.6, 4.4), 1.25, 18, 1.0, 0.0
        elif st == 1:
            c, r, rot, alpha, sh = (7.2, 5.0), 1.3, 6, 1.0, 0.45
        else:
            c, r, rot, alpha, sh = (7.0, 5.4), 0.95, -12, 0.85, 0.0
        if sh:
            o.append(vs("!!sealsh", V.circle(c[0] + sh, c[1] + sh * 1.2, r * 0.95), fill="ink", fa=0.12, z=30))
        else:
            o.append(vs("!!sealsh", V.circle(c[0], c[1], r * 0.9), fill="ink", fa=0.0, z=30))
        o += seal_objs(c, r, rot, alpha, 31)
        o.append(O("!!sealt", "text", c[0] - r * 0.7, c[1] + r * 0.02, r * 1.4, r * 0.4, txt="ПРИНЯТО", sz=14 * r / 0.95,
                   b=True, col="accent", al="c", rot=rot, z=32, meta={"inset": 0.0, "decor": True, "overlap_ok": True}))
        loops = [Loop("ripple", target="!!seal", period=2.2, scale=1.25, color="accent", name="rip")] if st == 2 else []
        sl.append(S(o, 600 if st == 2 else 800, loops=loops))
    return _v("stamp", "Печать с высоты опускается на лист",
              "Высота из 2D: печать над листом крупнее и отбрасывает смещённую тень; при «ударе» тень сливается с "
              "печатью, она уменьшается, поворачивается и становится полупрозрачной, как оттиск; круги на воде — момент "
              "решения. Финал раздела «согласование».",
              sl, ["docs", "3d", "shadow", "accent"], 4)


def _folder(theme, id, cx, cy, w, h, col, z=20, front_alpha=1.0, open_=0.0):
    back = V.union(V.rect(cx - w / 2, cy - h / 2, w, h, r=0.06), V.rect(cx - w / 2, cy - h / 2 - 0.22, w * 0.4, 0.3, r=0.06))
    front = V.polygon([(cx - w / 2 - open_ * 0.15, cy - h / 2 + 0.35 + open_ * 0.2), (cx + w / 2 + open_ * 0.15, cy - h / 2 + 0.35 + open_ * 0.2),
                       (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)])
    return [vs(f"!!{id}b", back, fill=dark(col, 0.15), z=z, meta=dict(DEC)),
            vs(f"!!{id}f", front, 0, fill=col, fa=front_alpha, z=z + 20, grad=V.gradient([(0, light(col, 0.15), front_alpha), (1, col, front_alpha)], 90),
               meta=dict(DEC))]


def pages_folders(theme) -> Variant:
    n = 9
    cols = [theme.c("accent"), theme.c("accent2"), theme.c("accent3")]
    fx_ = [2.6, 6.6, 10.6]
    names = ["Договоры", "Акты", "Письма"]
    sl = []
    for st in range(3):
        o = [head(["Пачка входящих", "Раскладываем", "Разложено"][st], w=6)]
        for j in range(3):
            o += _folder(theme, f"fd{j}", fx_[j], 5.4, 2.8, 2.0, cols[j], z=20 + 0 * j, open_=1.0 if st == 1 else 0.0)
            o.append(label(f"!!fl{j}", fx_[j], 6.55, names[j], w=2.4, sz=15, b=True, col="ink"))
        for i in range(n):
            j = i % 3
            k = i // 3
            if st == 0:
                cx, cy, rot, s = 6.6 + (i - 4) * 0.06, 2.7 - i * 0.03, -4 + i, 0.9
            elif st == 1:
                cx, cy, rot, s = fx_[j] - 0.5 + k * 0.5, 3.6 - k * 0.15, -8 + k * 8, 0.75
            else:
                cx, cy, rot, s = fx_[j] - 0.5 + k * 0.5, 4.75, -4 + k * 4, 0.75
            o += page(theme, f"!!pg{i}", cx, cy, 1.3 * s, 1.75 * s, rot, nl=5, z=30 + i, seed=i)
        sl.append(S(o, 900))
    return _v("pages_folders", "Листы влетают в папки",
              "Глубина слоями: у папки задняя стенка ниже листов, передний клапан — выше (z 40 против 30), поэтому "
              "листы «входят внутрь». Пачка → листы веером над открытыми папками → опускаются, торчат только верхушки.",
              sl, ["docs", "3d", "layers", "sort"], 4)


CLAUSES = ["1. Предмет", "2. Сроки", "3. Оплата", "4. Ответственность", "5. Расторжение"]
LINKS = [(1, 3, "см. п. 4"), (2, 3, "пени"), (0, 4, "основания")]


def clauses(theme) -> Variant:
    pc = (3.4, 4.1)
    pw, ph = 4.0, 5.6
    sl = []
    def blocks(st):
        out = []
        for i in range(5):
            if st == 0:
                y = pc[1] - ph / 2 + 0.45 + i * 1.0
                out.append(O(f"!!cb{i}", "rect", pc[0] - pw / 2 + 0.35, y, pw - 0.7, 0.72, fill="surface2", z=12))
            else:
                y = 1.55 + i * 1.05
                out.append(O(f"!!cb{i}", "rrect", 7.0, y, 4.6, 0.8, fill="surface", ln="accent2" if st == 2 and any(i in l[:2] for l in LINKS) else "line",
                             lw=1.25, radius=0.1, z=12))
                out.append(body(f"!!ct{i}", 7.2, y + 0.18, 4.2, 0.45, CLAUSES[i], sz=17, col="ink", b=True, z=20))
        return out
    o1 = page(theme, "!!pg", pc[0], pc[1], pw, ph, nl=0, seed=1) + blocks(0) + [head("Договор", x=7.0, w=5)]
    o2 = page(theme, "!!pg", pc[0] - 0.6, pc[1], pw * 0.8, ph * 0.8, nl=0, alpha=0.35, seed=1) + blocks(1) + [head("Пять пунктов", x=7.0, w=5)]
    o3 = page(theme, "!!pg", pc[0] - 0.6, pc[1], pw * 0.8, ph * 0.8, nl=0, alpha=0.35, seed=1) + blocks(2) + [head("Ссылки", x=0.7, w=6)]
    loops = []
    for k, (a, b, t) in enumerate(LINKS):
        ya, yb = 1.55 + a * 1.05 + 0.4, 1.55 + b * 1.05 + 0.4
        bend = [0.55, 0.95, 1.45][k]
        pts = bezier((11.6, ya), (11.6 + bend, ya), (11.6 + bend, yb), (11.6, yb), 40)
        o3.append(raw(f"lk{k}", ribbon(pts, 0.04, 60), fill="accent", z=8))
        o3.append(label(f"lt{k}", 11.68 + bend * 0.75, [3.55, 5.25, 1.25][k], t, w=1.5, al="l", sz=12, col="accent"))
        loops.append(flow(pts, n=2, period=2.2 + 0.3 * k, size=0.1, name=f"ref_{k}", color="accent", z=8.5))
    o3[1:1] = []
    sl = [S(o1, 700), S(o2, 900), S(o3, 800, loops=loops,
                                     fx=[Fx("entrance_wipe", f"lk{k}", start="at", delay=0.15 + 0.25 * k, dur=0.35,
                                            options={"direction": "down"}) for k in range(3)])]
    return _v("clauses", "Документ делится на пункты-ссылки",
              "Абзацы-блоки листа выходят из него карточками пунктов (лист бледнеет и отъезжает), затем между "
              "пунктами появляются дуги-ссылки, по дугам бегут точки (поток строго по форме дуги). Разбор структуры "
              "документа, перекрёстных ссылок.",
              sl, ["docs", "split", "relate", "flow"], 4)


def _curl_page(x, y, w, h, c, n=30):
    """Лист с загибом правого края: c = 0 — плоский; c = 1 — правый край «перевёрнут» почти к центру.
    Контур из явных точек (верх, правый край-дуга, низ, левый край) — пары переливаются точка в точку."""
    top = [(x + w * i / n * (1 - 0.45 * c * (i / n) ** 2), y - 0.25 * c * math.sin(math.pi * i / n * 0.5) * (i / n)) for i in range(n + 1)]
    xr = x + w * (1 - 0.45 * c)
    right = [(xr - 0.35 * c * math.sin(math.pi * i / n), y + h * i / n) for i in range(1, n + 1)]
    bot = [(x + w * (n - i) / n * (1 - 0.45 * c * ((n - i) / n) ** 2), y + h + 0.1 * c * ((n - i) / n)) for i in range(1, n + 1)]
    left = [(x, y + h * (n - i) / n) for i in range(1, n)]
    return V.polygon(top + right + bot + left)


def page_curl(theme) -> Variant:
    x, y, w, h = 6.4, 1.0, 4.2, 5.7
    sl = []
    for st, c in enumerate([0.0, 0.75, 1.0]):
        o = [head(["Страница 12", "Переворачиваем", "Страница 13"][st], w=5)]
        o += page(theme, "under", x + w / 2, y + h / 2, w, h, nl=9, seed=13, z=5)
        g = _curl_page(x, y, w, h, c)
        shade = V.gradient([(0, "FFFFFF"), (0.7, "F3EFE6"), (1, dark(theme.c("surface2"), 0.12 + 0.2 * c))], angle=0)
        o.append(raw("!!curl", g, fill="FFFFFF", grad=shade, ln="line", lw=1.0, z=20, fa=1.0 if st < 2 else 0.0, la=1.0 if st < 2 else 0.0))
        if st < 2:
            for i in range(9):
                lw_ = w * (0.7 if i % 3 != 2 else 0.45) * (1 - 0.5 * c)
                o.append(O(f"!!cl{i}", "rect", x + w * 0.12, y + h * (0.14 + 0.74 * i / 8), lw_, 0.05, fill="line", z=21,
                           fa=1.0 - 0.6 * c))
        sl.append(S(o, 800))
    return _v("page_curl", "Загиб страницы: лист переворачивается",
              "3D из 2D: контур листа из явных точек — правый край выгибается дугой и уходит к корешку, градиент "
              "темнеет к сгибу, строки сжимаются; под ним уже лежит следующая страница. Переход «к следующему документу».",
              sl, ["docs", "3d", "shape-morph", "gradient"], 3)


def tabs_pointer(theme) -> Variant:
    secs = ["Заявка", "Проверка", "Решение", "Архив"]
    cols = [theme.c("accent"), theme.c("accent2"), theme.c("accent3"), theme.c("muted")]
    sl = []
    for k in range(3):
        o = [vs("!!binder", V.rect(11.2, 0.5, 3.0, 6.5, r=0.12), fill="surface2", ln="line", lw=1.0, z=10, meta=dict(DEC))]
        for i in range(4):
            out_ = 0.95 if i == k else 0.45
            y = 1.0 + i * 1.45
            o.append(vs(f"!!tab{i}", V.rect(11.2 - out_, y, out_ + 0.4, 1.2, r=0.12), fill=cols[i] if i <= k else light(cols[i], 0.55),
                        z=5 if i != k else 15, meta=dict(DEC)))
            o.append(O(f"!!tt{i}", "text", 11.2 - out_ - 1.6, y + 0.43, 1.5, 0.35, txt=secs[i], sz=13, b=i == k,
                       col="accent" if i == k else "muted", al="r", z=30, meta={"inset": 0.0}))
        o += [kicker(f"раздел {k + 1}"), head(["Приём заявки", "Проверка полноты", "Решение по делу"][k], w=7), body("!!txt", 0.7, 1.5, 7, 1.2,
                                                              [["кто подал", "какие документы"], ["полнота", "сроки"], ["кто решает", "основания"]][k], sz=20)]
        sl.append(S(o, 700))
    return _v("tabs_pointer", "Закладки папки у края — разделы",
              "Навигация: папка-регистратор срезана правым краем, закладки — разделы; текущая выдвигается дальше и "
              "ложится поверх, пройденные — насыщенные, будущие — бледные. Подпись закладки — слева от неё.",
              sl, ["docs", "pointer", "navigation"], 3)


def doc_steps(theme) -> Variant:
    pc = (9.6, 4.0)
    topics = ["Стороны", "Предмет", "Сроки", "Оплата"]
    sl = []
    for k in range(3):
        o = page(theme, "!!pg", pc[0], pc[1], 3.6, 5.2, nl=0, seed=2)
        for i in range(4):
            y = pc[1] - 2.6 + 0.6 + i * 1.15
            done = i <= k
            o.append(O(f"!!pb{i}", "rect", pc[0] - 1.45, y, 2.6, 0.75, fill="surface2" if not done else light(theme.c("accent"), 0.8), z=12))
            o.append(O(f"!!pm{i}", "rect", pc[0] - 1.6, y, 0.08, 0.75, fill="accent" if done else "line", z=13))
            o.append(label(f"!!pt{i}", pc[0] - 1.3, y + 0.2, topics[i], w=2.3, al="l", sz=14, b=i == k, col="ink" if done else "muted"))
        o += [kicker("раздел 1 · проверка договора"), head(f"Шаг {k + 1} из 4", w=6),
              body("!!b", 0.7, 1.45, 6.5, 0.4, f"проверено {(k + 1) * 25} %", sz=16, col="accent")]
        sl.append(S(o, 600))
    return _v("doc_steps", "Абзацы листа закрашиваются по шагам",
              "Прогресс внутри раздела: лист справа из 4 абзацев-тем, проверенные получают метку на полях и тон "
              "акцента — 25 → 50 → 75 %. Лист на месте, меняются только цвета (минимум движения, читается сразу).",
              sl, ["docs", "progress"], 3)


def doc_backdrop(theme) -> Variant:
    sl = []
    for st in range(2):
        o = []
        for i in range(5):
            o += page(theme, f"!!bk{i}", 9.0 + i * 0.35 + st * 0.6, 4.1 - i * 0.25, 5.0, 7.0, rot=-8 + i * 5 + st * 6, nl=10,
                      z=-300 + 12 * i, alpha=0.18, seed=i)
        o += [head(["Что меняется с 1 марта", "Кого это касается"][st], w=8),
              body("!!txt", 0.7, 1.5, 6.5, 2.5, [["новый порядок подачи", "электронная подпись", "сроки — 10 дней"],
                                                 ["заявителей", "проверяющих", "архив"]][st], sz=22, col="ink")]
        o = [ob.copy(meta={**ob.meta, "decor": True}) if ob.name.startswith("!!bk") else ob for ob in o]
        sl.append(S(o, 800))
    return _v("doc_backdrop", "Бледная стопка под текстом",
              "Фон: стопка листов в 2,5 раза больше, прозрачность ~18 %, веером под содержимым; от слайда к слайду "
              "листы чуть поворачиваются и сдвигаются — колода «дышит», текст поверх читается (контроль контраста).",
              sl, ["docs", "backdrop"], 3)


def magnifier(theme) -> Variant:
    pc, pw, ph = (4.6, 4.0), 5.6, 5.8
    nl = 12
    err = 7
    rows = []
    rnd = random.Random(4)
    for i in range(nl):
        y = pc[1] - ph / 2 + 0.5 + i * 0.42
        words, x = [], pc[0] - pw / 2 + 0.5
        while x < pc[0] + pw / 2 - 0.9:
            wl = rnd.uniform(0.25, 0.75)
            words.append((x, y, wl))
            x += wl + 0.12
        rows.append(words)
    def page_objs():
        o = [doc_sheet("!!pg", pc[0] - pw / 2, pc[1] - ph / 2, pw, ph, fill="FFFFFF", ln="line", z=5)]
        for i, words in enumerate(rows):
            for j, (x, y, wl) in enumerate(words):
                bad = i == err and j == 2
                o.append(O(f"w{i}_{j}", "rect", x, y, wl, 0.07, fill="accent" if bad else "line", z=6))
        return o
    def lens(c, r, k=2.6, found=False):
        # увеличенный кусок: слова в круге, растянутые в k раз от центра линзы, и обрезанные кругом
        disc = V.circle(c[0], c[1], r)
        parts = []
        bad_parts = []
        for i, words in enumerate(rows):
            for j, (x, y, wl) in enumerate(words):
                g = V.rect(x, y, wl, 0.07)
                g = V.scale(g, k, k, origin=c)
                q = g.intersection(disc)
                if not q.is_empty:
                    (bad_parts if (i == err and j == 2) else parts).append(q)
        o = [O("!!lensbg", "oval", c[0] - r, c[1] - r, 2 * r, 2 * r, fill="FFFFFF", z=40, meta=dict(DEC))]
        if parts:
            o.append(vs("lensw", V.union(*parts), fill="muted", z=41))
        if bad_parts:
            o.append(vs("lensbad", V.union(*bad_parts), fill="accent", z=42))
        o.append(vs("!!lensr", V.subtract(V.circle(c[0], c[1], r + 0.09), disc), fill="ink2", z=43))
        a = math.radians(45)
        hp = [(c[0] + (r + 0.05) * math.cos(a), c[1] + (r + 0.05) * math.sin(a)), (c[0] + (r + 1.1) * math.cos(a), c[1] + (r + 1.1) * math.sin(a))]
        o.append(vs("!!lensh", stroke(hp, 0.2), fill="ink2", z=43))
        if found:
            o.append(O("!!ring", "oval", c[0] - r * 0.55, c[1] - r * 0.3, r * 1.1, r * 0.6, fill=None, ln="accent", lw=2.0, z=44))
        return o
    sl = []
    rows_y = [r_[0][1] for r_ in rows]
    targets = [(3.2, rows_y[2]), (5.2, rows_y[4]), (rows[err][2][0] + rows[err][2][2] / 2, rows_y[err])]
    for st, (c, t) in enumerate(zip(targets, ["Строка 3", "Строка 5", "Ошибка: строка 8"])):
        o = page_objs() + lens(c, 1.0, found=st == 2) + [head(t, x=8.1, w=5.1)]
        loops = [Loop("ripple", target="!!ring", period=1.8, scale=1.3, color="accent", name="rip")] if st == 2 else []
        sl.append(S(o, 800, loops=loops))
    return _v("magnifier", "Лупа ведёт по строкам и находит слово",
              "Увеличенная часть движется по объекту: внутри линзы — тот же текст-полоски, растянутые в 2,6 раза от "
              "центра линзы и обрезанные кругом (пересечение форм на каждом слайде). Линза переезжает по строкам и "
              "останавливается на слове-ошибке (акцент + круги). Вычитка, поиск, аудит.",
              sl, ["docs", "zoom", "boolean", "flag"], 4)


def seq_docs(theme) -> Variant:
    """Пачка листов через колоду: стопка → веер → один лист крупно (остальные — лента-навигация внизу) → маркер →
    пункты-карточки → ссылки → карточки в папки → папки-закладки у края → печать."""
    n = 6
    cols = [theme.c("accent"), theme.c("accent2"), theme.c("accent3")]
    hcol = mix(theme.c("accent3"), "FFE45C", 0.6)
    S_ = []
    def pages(states, big=None, hl=None):
        o = []
        for i, (cx, cy, rot, s) in enumerate(states):
            o += page(theme, f"!!pg{i}", cx, cy, 1.9 * s, 2.6 * s, rot, nl=7, z=10 + 3 * i, seed=i, shadow=0.05,
                      edge="accent" if big == i else "line", hl=hl if big == i else None)
        return o
    stack = [(9.0 + i * 0.07, 4.2 - i * 0.07, -3 + i, 1.0) for i in range(n)]
    fan = [(8.4 + (i - 2.5) / 2.5 * 3.4, 4.5 + 0.6 * ((i - 2.5) / 2.5) ** 2, (i - 2.5) / 2.5 * 15, 1.0) for i in range(n)]
    strip = [(1.1 + i * 0.75, 6.45, 0, 0.3) for i in range(n)]
    S_.append(S(pages(stack) + [kicker("документооборот"), O("!!cov", "text", 0.7, 1.0, 5.6, 1.7, txt=["Путь", "документа"], sz=48, b=True,
                                                             font="head", col="ink", spacing=0.95, z=90)], 700))
    S_.append(S(pages(fan) + [head("Шесть входящих", w=6)], 900))
    # 3: лист 3 крупно, остальные — лента внизу (навигация по документам)
    st3 = list(strip)
    st3[3] = (8.6, 3.9, 0, 2.0)
    S_.append(S(pages(st3, big=3) + [head("Договор поставки", w=5.5), body("!!b", 0.7, 1.4, 5, 0.4, "лист 4 из 6", sz=15, col="muted")], 900))
    # 4: маркер на строках 2 и 5
    o4 = pages(st3, big=3)
    big_c, bw, bh = (8.6, 3.9), 3.8, 5.2
    lyy = lambda i: big_c[1] - bh / 2 + bh * (0.14 + 0.74 * i / 6)  # noqa: E731
    for k, i in enumerate([2, 5]):
        o4.append(O(f"!!hm{k}", "rect", big_c[0] - bw / 2 + bw * 0.09, lyy(i) - 0.12, bw * 0.8, 0.3, fill=hcol, fa=0.6, z=40))
    S_.append(S(o4 + [head("Важное — маркером", w=6)], 600,
                fx=[Fx("entrance_wipe", f"!!hm{k}", start="at", delay=0.15 + 0.4 * k, dur=0.4, options={"direction": "left"}) for k in range(2)]))
    # 5: полосы маркера -> карточки пунктов; лист уходит влево и бледнеет
    st5 = list(strip)
    st5[3] = (2.6, 4.0, -4, 1.4)
    o5 = pages(st5, big=3)
    for k, t in enumerate(["Срок поставки", "Неустойка"]):
        o5 += [O(f"!!hm{k}", "rect", 5.6, 2.0 + k * 2.0, 4.6, 1.3, fill=hcol, fa=0.6, z=40),
               body(f"!!ht{k}", 5.85, 2.4 + k * 2.0, 4.2, 0.5, t, sz=20, b=True, col="ink")]
    S_.append(S(o5 + [head("Два пункта", w=6)], 900))
    # 6: ссылка между пунктами (дуга + поток)
    pts = bezier((10.2, 2.65), (11.6, 2.65), (11.6, 4.65), (10.2, 4.65), 40)
    o6 = pages(st5, big=3) + [raw("lk", ribbon(pts, 0.045, 60), fill="accent", z=8),
                               label("lkt", 11.15, 3.5, "пени за срок", w=1.9, al="l", sz=13, col="accent")]
    for k, t in enumerate(["Срок поставки", "Неустойка"]):
        o6 += [O(f"!!hm{k}", "rect", 5.6, 2.0 + k * 2.0, 4.6, 1.3, fill=hcol, fa=0.6, z=40),
               body(f"!!ht{k}", 5.85, 2.4 + k * 2.0, 4.2, 0.5, t, sz=20, b=True, col="ink")]
    S_.append(S(o6 + [head("Пункты связаны", w=6)], 700, loops=[flow(pts, n=2, period=2.0, size=0.1, name="ref", color="accent")],
                fx=[Fx("entrance_wipe", "lk", start="at", delay=0.15, dur=0.4, options={"direction": "down"})]))
    # 7: всё раскладывается по папкам; папки потом станут закладками
    fxs = [2.6, 6.6, 10.6]
    names = ["Договоры", "Акты", "Письма"]
    o7 = [head("По папкам", w=6)]
    st7 = []
    for i in range(n):
        j = i % 3
        st7.append((fxs[j] - 0.3 + (i // 3) * 0.6, 4.75, -4 + 6 * (i // 3), 0.6))
    o7 += pages(st7)
    for j in range(3):
        o7 += _folder(theme, f"fd{j}", fxs[j], 5.4, 2.8, 2.0, cols[j], z=20)
        o7.append(label(f"!!fl{j}", fxs[j], 6.55, names[j], w=2.4, sz=15, b=True, col="ink"))
    for k in range(2):
        o7.append(O(f"!!hm{k}", "rect", fxs[0] - 0.3 + k * 0.6 - 0.3, 4.4, 0.6, 0.15, fill=hcol, fa=0.0, z=9))
    S_.append(S(o7, 900))
    # 8: папки — закладки у правого края (навигация); раздел «Акты»
    o8 = [kicker("раздел 2"), head("Приёмка работ", w=6), body("!!txt", 0.7, 1.5, 7, 1.0, ["приёмка, расхождения", "подписи сторон"], sz=20)]
    for j in range(3):
        y = 1.2 + j * 1.9
        out_ = 1.4 if j == 1 else 0.7
        o8 += _folder(theme, f"fd{j}", 13.6 - out_ + 1.4, y + 0.8, 2.8, 1.5, cols[j], z=20 + (10 if j == 1 else 0))
        o8.append(label(f"!!fl{j}", 13.6 - out_ - 0.15, y + 0.6, names[j], w=2.0, al="r", sz=15, b=j == 1, col="ink" if j == 1 else "muted"))
    st8 = [(13.6 - (1.4 if i % 3 == 1 else 0.7) + 1.4 + (i // 3) * 0.3, 1.2 + (i % 3) * 1.9 + 0.55, 0, 0.4) for i in range(n)]
    o8 += pages(st8)
    S_.append(S(o8, 900))
    # 9: печать
    o9 = pages(stack) + [O("!!fin", "text", 0.7, 1.2, 5.6, 1.6, txt=["Принято", "и подшито"], sz=44, b=True, font="head", col="ink",
                           spacing=0.95, z=90)]
    c, r = (9.8, 4.4), 1.1
    o9 += seal_objs(c, r, 348, 0.85, 60)
    S_.append(S(o9, 900, fx=[Fx("entrance_zoom", n_, start="at", delay=0.2, dur=0.35) for n_ in ("!!seal", "!!seal1", "!!seal2")]))
    return _v("seq_docs", "Пачка документов через колоду",
              "9 состояний одних и тех же 6 листов: стопка (обложка) → веер → лист 4 крупно, остальные — лента-"
              "навигация внизу → маркер по двум строкам → полосы маркера становятся карточками пунктов → дуга-ссылка с "
              "потоком → листы в папки → папки становятся закладками у правого края (раздел) → стопка и печать.",
              S_, ["seq", "docs", "carrier", "pointer", "highlight", "relate", "3d"], 4)


def variants(theme) -> list[Variant]:
    return [seq_docs(theme), stack_fan(theme), highlighter(theme), stamp(theme), pages_folders(theme), clauses(theme),
            page_curl(theme), tabs_pointer(theme), doc_steps(theme), doc_backdrop(theme), magnifier(theme)]
