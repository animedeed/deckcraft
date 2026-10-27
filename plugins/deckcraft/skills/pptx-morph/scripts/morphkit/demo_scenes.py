"""Демо живых сцен (morphkit/web/scenes.js + morphkit/scenes.py): все сцены в трёх характерах, бокалы lab.f_wine.

    python3 -m morphkit.demo_scenes OUT_DIR [--no-shots] [--no-fps]      # из папки scripts

Собирает OUT_DIR/scenes.html (тема «Лаборатория»), снимает кадры через 0,3 / 1 / 2 / 4 с после перехода к каждому
слайду (OUT_DIR/sNN_t.png + sheet.png), меряет FPS на самом тяжёлом слайде (6000 точек) и пишет OUT_DIR/report.json.
Колонки на слайдах: спокойно (calm) · живо (lively) · драматично (dramatic).
"""

from __future__ import annotations

import asyncio
import json
import math
import sys
from pathlib import Path

from morphkit import O, Slide
from morphkit import scenes as SC
from morphkit import vector as V
from morphkit.html import web
from morphkit.palette import CATALOG
from morphkit.theme import mix

from lab._d_util import dark, light, line, vs
from lab.f_wine import Glass, _bottle, wine_cols

T = next(p.theme for p in CATALOG if p.theme.name == "lab")
RED, WHITE = wine_cols(T)
BOTTLE = mix(T.c("accent2"), "1E2B12", 0.35)
CH = SC.CHARACTERS
CH_RU = {"calm": "спокойно", "lively": "живо", "dramatic": "драматично"}
X0 = [1.25 + 4.0 * k for k in range(3)]  # левые края колонок; ширина колонки 3,8 дюйма
CW = 3.8


# ------------------------------------------------------------------------------ оформление
def head(n: int, kicker: str, title: str, sub: str = "") -> list[O]:
    out = [O(f"h{n}k", "text", 0.6, 0.32, 9, 0.3, txt=kicker, sz=11, b=True, caps=True, tracking=1.2, col="accent", z=90),
           O(f"h{n}t", "text", 0.6, 0.6, 12.2, 0.6, txt=title, sz=28, b=True, font="head", col="ink", z=90)]
    if sub:
        out.append(O(f"h{n}s", "text", 0.6, 1.18, 12.2, 0.35, txt=sub, sz=13, col="muted", z=90))
    return out


def cols(n: int, y: float = 1.6, notes: tuple[str, str, str] | None = None) -> list[O]:
    out = []
    for k, c in enumerate(CH):
        out.append(O(f"c{n}_{k}", "text", X0[k], y, CW, 0.3, txt=f"{CH_RU[c]} · {c}", sz=12, b=True, caps=True,
                     tracking=0.8, col="accent" if c == "lively" else "ink2", z=90, meta={"inset": 0.0}))
        if notes:
            out.append(O(f"c{n}_{k}n", "text", X0[k], y + 0.28, CW, 0.3, txt=notes[k], sz=11, col="muted", z=90,
                         meta={"inset": 0.0}))
    return out


def row_label(n: int, i: int, y: float, text: str) -> O:
    return O(f"r{n}_{i}", "text", 0.3, y, 0.95, 0.3, txt=text, sz=11, b=True, col="ink2", z=90, meta={"inset": 0.0})


def bottle(name: str, piv, theta: float, k: float = 0.45) -> list[O]:
    bot = _bottle(piv[0], piv[1] + 1.4 * k / 0.7, k)
    return [vs(name, bot, 0, pivot=piv, rot=theta % 360, fill=BOTTLE, fa=0.95, z=30),
            vs(name + "_lab", V.rect(piv[0] - 0.3 * k / 0.45, piv[1] + 0.1, 0.6 * k / 0.45, 0.45), 0, pivot=piv,
               rot=theta % 360, fill=T.c("surface"), ln=T.c("line"), lw=0.75, z=31)]


S = Slide


def mk(objs, title, scenes, dur=800, **kw) -> Slide:
    s = S(objs, dur=dur, title=title)
    return web(s, scenes=scenes, **kw)


# ------------------------------------------------------------------------------ слайды
def s_cover() -> Slide:
    g = Glass("cv", R=0.95, Hb=1.8, stem=1.15)
    objs = head(0, "deckcraft 0.3.0 · web", "Живые сцены", "вино в бокале, струя, частицы, сигнал, счётчики, часы, шкала, "
                "терминал, искры, фактура, графики — в трёх характерах")
    objs += g.objs(T, (10.4, 6.7), s=1.2, level=0.55, z=20)
    objs += [O("cv_l", "text", 0.6, 2.2, 7.2, 3.6, sz=16, col="ink2", z=90,
               txt=["liquid · pour · bubbles · drip · stain", "particles (до 6000 точек) · signal", "counter · clock · gauge · terminal",
                    "sparks · confetti · ripple", "grain · halftone · chart-draw · bars-grow", "",
                    "характер: {a:calm} · {a:lively} · {a:dramatic}"]),
             O("cv_n", "text", 0.6, 6.4, 7.5, 0.4, txt="Слайды ниже: колонки — спокойно / живо / драматично", sz=12,
               col="muted", z=90)]
    return mk(objs, "обложка", [SC.grain(amount=0.55, mode="paper", character="calm"),
                                SC.liquid("!!cv", character="lively"),
                                SC.sparks("!!cv_srf", delay=0.6, repeat=2.2, count=4, cone=(-90, 140), power=2.6,
                                          character="calm")], tr="fade")


def s_liquid() -> Slide:
    objs = head(1, "1 · liquid", "Вино живое: уровень, волна, пузырьки, блик",
                "level 0,25 → 0,72 за 1,6 с; поверхность колышется после перехода и налива")
    objs += cols(1, notes=("тихая рябь, редкие пузырьки", "заметное колыхание", "плеск, пена, много пузырьков"))
    sc = []
    for k, c in enumerate(CH):
        g = Glass(f"l{k}", R=0.95, Hb=1.8, stem=1.15)
        objs += g.objs(T, (X0[k] + CW / 2, 6.75), s=1.25, level=0.25, z=20)
        sc.append(SC.liquid(f"!!l{k}", 0.25, 0.72, delay=0.25, dur=1.6, character=c, seed=k + 1))
    return mk(objs, "liquid", sc)


def s_pour() -> Slide:
    objs = head(2, "2 · pour", "Струя: из бутылки и из наклонённого бокала",
                "pour_into(): уровень растёт, пока струя бьёт в поверхность; капли, брызги, круги")
    objs += cols(2)
    sc = []
    for k, c in enumerate(CH):
        x0 = X0[k]
        g = Glass(f"p{k}", R=0.95, Hb=1.8, stem=1.15)
        objs += g.objs(T, (x0 + 2.75, 6.85), s=0.78, level=0.08, z=20)
        if k < 2:
            objs += bottle(f"!!pb{k}", (x0 + 0.85, 2.85), 112, 0.42)
            sc += SC.pour_into(f"!!p{k}", from_obj=f"!!pb{k}", level_from=0.08, level_to=0.6, delay=0.2, dur=2.2,
                               character=c, seed=k + 3)
        else:  # источник — наклонённый бокал: его вино убывает, поверхность остаётся горизонтальной
            src = Glass(f"ps{k}", R=0.95, Hb=1.8, stem=1.15)
            objs += src.objs(T, (x0 + 0.55, 3.55), s=0.62, tilt=95, level=0.5, z=24, rock=False)
            sc += SC.pour_into(f"!!p{k}", from_obj=f"!!ps{k}", level_from=0.08, level_to=0.55, delay=0.2, dur=2.2,
                               character=c, seed=k + 3)
            sc.append(SC.liquid(f"!!ps{k}", 0.5, 0.2, delay=0.2, dur=2.4, character=c, seed=9))
    return mk(objs, "pour", sc)


def s_small() -> Slide:
    objs = head(3, "3 · bubbles · drip · stain", "Пузырьки, капли с края, пятно растекается и подсыхает")
    objs += cols(3, y=1.45)
    objs += [row_label(3, 0, 2.6, "bubbles"), row_label(3, 1, 4.3, "drip"), row_label(3, 2, 6.2, "stain")]
    sc = []
    for k, c in enumerate(CH):
        x0, cx = X0[k], X0[k] + CW / 2
        g = Glass(f"b{k}", R=0.95, Hb=1.8, stem=1.15)
        objs += g.objs(T, (cx - 0.9, 3.75), s=0.62, level=0.62, z=20)
        objs.append(O(f"bx{k}", "rrect", cx + 0.2, 1.95, 1.3, 1.75, fill=light(T.c("accent3"), 0.55), ln="line", lw=0.75,
                      radius=0.12, z=10))
        sc += [SC.bubbles(obj=f"!!b{k}", character=c, seed=k + 1),
               SC.bubbles((cx + 0.25, 2.0, 1.2, 1.65), n=14, color="#ffffff", character=c, seed=k + 5)]
        objs.append(O(f"sh{k}", "rect", x0 + 0.3, 3.95, CW - 0.6, 0.14, fill="ink2", z=12))
        objs.append(line(f"fl{k}", (x0 + 0.2, 5.25), (x0 + CW - 0.2, 5.25), ln="line", lw=1.0, z=5))
        sc.append(SC.drip(obj=f"sh{k}", n=3, period=1.4, floor=5.25, character=c, seed=k + 2))
        objs.append(line(f"tb{k}", (x0 + 0.2, 6.75), (x0 + CW - 0.2, 6.75), ln="line", lw=1.0, z=5))
        sc.append(SC.stain((cx, 6.3), 0.62, squash=0.42, delay=0.2, dur=1.3, dry=2.0, character=c, seed=k + 7))
    return mk(objs, "мелкие сцены", sc)


def s_particles() -> Slide:
    objs = head(4, "4 · particles", "6000 точек: облако → сетка → группы → столбики",
                "3 × 2000 точек, доли 1 599 / 4 898 (красное / белое); одна canvas на поле")
    objs += cols(4)
    sc = []
    for k, c in enumerate(CH):
        sc.append(SC.particles(2000, (X0[k], 2.1, CW, 4.5),
                               [SC.phase("cloud", 0.0), SC.phase("grid", 0.45, 0.9), SC.phase("groups", 1.35, 1.0),
                                SC.phase("bars", 2.45, 1.0)],
                               shares=[1599, 4898], colors=["red_wine", "white_wine"], labels=["красное", "белое"],
                               character=c, seed=k + 1))
    return mk(objs, "particles", sc)


def s_into() -> Slide:
    objs = head(5, "4 · particles → бокалы", "Точки стекают в бокал, вино поднимается",
                "раскладка into: link_to=бокал; уровень — liquid с задержкой")
    objs += cols(5)
    sc = []
    for k, c in enumerate(CH):
        x0, cx = X0[k], X0[k] + CW / 2
        g = Glass(f"i{k}", R=0.95, Hb=1.8, stem=1.15)
        objs += g.objs(T, (cx, 6.95), s=0.8, level=0.05, z=20)
        sc.append(SC.particles(700, (x0 + 0.1, 2.05, CW - 0.2, 1.7),
                               [("cloud", 0.0), ("clusters", 0.6, 0.8), ("into", 1.5, 1.1)], shares=[0.7, 0.3],
                               colors=["red_wine", "white_wine"], link_to=[f"!!i{k}"], character=c, seed=k + 11))
        sc.append(SC.liquid(f"!!i{k}", 0.05, 0.62, delay=1.9, dur=1.8, character=c, seed=k + 1))
    return mk(objs, "particles into", sc)


def s_signal() -> Slide:
    objs = head(6, "5 · signal", "Сигнал по сети: импульсы по слоям, выход растёт",
                "рёбра — линии слайда между узлами; повтор каждые 2,4 с; столбики и число на выходе")
    objs += cols(6)
    sc = []
    for k, c in enumerate(CH):
        x0 = X0[k]
        L = [[(x0 + 0.45, 2.45 + i * 0.62) for i in range(4)], [(x0 + 1.75, 2.25 + i * 0.5) for i in range(6)],
             [(x0 + 3.05, 2.85 + i * 0.95) for i in range(2)]]
        names = [[f"!!n{k}_{l}_{i}" for i in range(len(L[l]))] for l in range(3)]
        for l in range(2):
            for i, (xa, ya) in enumerate(L[l]):
                for j, (xb, yb) in enumerate(L[l + 1]):
                    objs.append(line(f"e{k}_{l}_{i}_{j}", (xa, ya), (xb, yb), ln="line", lw=0.75, z=3))
        for l in range(3):
            r = 0.13 if l != 1 else 0.1
            for i, (x, y) in enumerate(L[l]):
                objs.append(O(names[l][i], "oval", x - r, y - r, 2 * r, 2 * r, fill=RED if l == 0 else ("ink2" if l == 1 else "accent"),
                              z=8))
        objs.append(O(f"!!n{k}v", "text", x0 + 3.25, 2.6, 0.6, 0.35, txt="0,72", sz=14, b=True, col="accent", z=60,
                      meta={"inset": 0.0}))
        sc.append(SC.signal(names, hop=0.5, repeat=2.4, out=[("хорошее", 0.72), ("плохое", 0.28, "muted")],
                            out_box=(x0 + 0.2, 5.3, 3.3, 1.0), out_decimals=2, out_text=f"!!n{k}v", out_value=0.72,
                            delay=0.2, character=c, seed=k + 1))
    return mk(objs, "signal", sc)


def s_counter() -> Slide:
    objs = head(7, "6 · counter", "Числа растут в своих текстах",
                "формат из текста: разряды, запятая, типографский минус, проценты")
    objs += cols(7)
    sc = []
    vals = [("6 497", "образцов"), ("0,541", "MAE сети на test"), ("−0,035", "к Ridge, интервал ниже нуля"),
            ("76 %", "train — баллы 5 и 6")]
    for k, c in enumerate(CH):
        for i, (v, lab) in enumerate(vals):
            y = 2.15 + i * 1.18
            objs += [O(f"!!cn{k}_{i}", "text", X0[k], y, CW, 0.7, txt=v, sz=36, b=True, font="head", col="accent", z=60,
                       meta={"inset": 0.0}),
                     O(f"cl{k}_{i}", "text", X0[k], y + 0.66, CW, 0.3, txt=lab, sz=12, col="ink2", z=60, meta={"inset": 0.0})]
            sc.append(SC.counter(f"!!cn{k}_{i}", delay=0.15 + 0.2 * i, dur=1.4, character=c, seed=i + 1))
    return mk(objs, "counter", sc)


def s_gauge() -> Slide:
    objs = head(8, "8 · gauge", "Шкала: стрелка доезжает с перелётом пружины",
                "центр — счётчик без перелёта; полоса — интервал, жирная метка — ноль")
    objs += cols(8)
    sc = [SC.gauge((X0[0] + CW / 2, 3.95), 0.62, r=1.25, pct=True, suffix=" %", label="доля train", delay=0.2,
                   character="calm"),
          SC.gauge((X0[1] + CW / 2, 3.95), 0.94, r=1.25, pct=True, suffix=" %", label="прогнозов совпало",
                   zones=[(0.6, "bad"), (0.85, "warn"), (1.0, "good")], delay=0.2, character="lively"),
          SC.gauge(None, -0.035, box=(X0[2] + 0.4, 2.45, 3.0, 3.0), vmin=-0.06, vmax=0.02, zero=0.0, band=(-0.058, -0.012),
                   fmt="−0,035", label="сеть − Ridge, MAE", delay=0.2, character="dramatic")]
    return mk(objs, "gauge", sc)


def s_clock() -> Slide:
    objs = head(9, "7 · clock", "Часы и журнал: записи появляются, когда стрелка проходит их час",
                "сутки за 4 с; метка на циферблате закрашивается и даёт круг")
    objs += cols(9)
    ent = [(3, "агент собрал отчёт"), (9, "проверка данных", "good"), (14, "переобучение", "warn"),
           (19, "прогноз отправлен", "accent")]
    sc = [SC.clock((X0[k] + 1.2, 3.25), 1.0, entries=ent, log_at=(X0[k] + 0.05, 4.65), log_dy=0.34, delay=0.2,
                   dur=4.0, character=c) for k, c in enumerate(CH)]
    return mk(objs, "clock", sc)


def s_terminal() -> Slide:
    objs = head(10, "9 · terminal", "Терминал: команды печатаются, вывод — строками",
                "курсор мигает, лишние строки уезжают вверх, цвета вывода — роли темы")
    objs += cols(10)
    lines = [("$ python src/predict.py \\", None), ("    --input new_rows.csv", None), ("прогнозов: 8 · код 0", "good"),
             ("$ cmp out/my.csv reports/ex…", None), ("совпадает с эталоном", "good"),
             ("$ predict --input bad.csv", None), ("wine_type вне области: rose", "bad"), ("код 2", "bad"),
             ("$ ", None)]
    sc = []
    for k, c in enumerate(CH):
        if k == 1:  # готовый прямоугольник слайда как экран
            objs.append(O("!!term1", "rrect", X0[k], 2.2, CW, 3.3, fill="ink", radius=0.1, z=40))
            sc.append(SC.terminal(lines, obj="!!term1", size=11, delay=0.2, character=c, seed=k + 1))
        else:
            sc.append(SC.terminal(lines, box=(X0[k], 2.2, CW, 3.3), size=11, chrome=True, delay=0.2, character=c,
                                  seed=k + 1))
    return mk(objs, "terminal", sc)


def s_burst() -> Slide:
    objs = head(11, "10 · sparks · confetti · ripple", "Вау-моменты: искры у числа, конфетти, круги")
    objs += cols(11, y=1.45)
    objs += [row_label(11, 0, 2.3, "sparks"), row_label(11, 1, 4.1, "confetti"), row_label(11, 2, 6.0, "ripple")]
    sc = []
    for k, c in enumerate(CH):
        x0, cx = X0[k], X0[k] + CW / 2
        objs.append(O(f"!!bn{k}", "text", x0, 2.05, CW, 0.75, txt="94 %", sz=40, b=True, font="head", col="accent", al="c",
                      z=60, meta={"inset": 0.0}))
        sc.append(SC.sparks(f"!!bn{k}", delay=0.3, repeat=1.5, count=6, character=c, seed=k + 1))
        sc.append(SC.confetti((cx, 5.15), delay=0.3, character=c, seed=k + 2))
        objs.append(O(f"bd{k}", "oval", cx - 0.09, 6.1 - 0.09, 0.18, 0.18, fill="accent", z=30))
        sc.append(SC.ripple((cx, 6.1), rings=3, period=1.8, r_max=1.0, squash=0.38, delay=0.2, character=c, seed=k))
    return mk(objs, "burst", sc)


def s_texture() -> Slide:
    objs = head(12, "11 · grain · halftone", "Фактура и растр",
                "зерно обновляется 8–12 к/с; растр проявляется волной и дышит")
    objs += cols(12, y=1.45)
    objs += [row_label(12, 0, 2.7, "grain"), row_label(12, 1, 5.3, "halftone")]
    sc = []
    modes = ["paper", "paper", "film"]
    for k, c in enumerate(CH):
        x0 = X0[k]
        objs.append(O(f"gr{k}", "rect", x0, 1.85, CW, 2.05, fill="surface", z=5))
        objs.append(O(f"grt{k}", "text", x0 + 0.2, 2.65, CW - 0.4, 0.5, txt=f"{modes[k]}", sz=22, b=True, font="head",
                      col="ink2", al="c", z=20))
        sc.append(SC.grain(amount=0.9, mode=modes[k], area=(x0, 1.85, CW, 2.05), character=c, seed=k + 3))
        sc.append(SC.halftone((x0, 4.2, CW, 2.6), cell=0.085, color="accent" if k != 1 else "red_wine",
                              field=["radial", "ring", "wave"][k], delay=0.1, dur=1.4, character=c, seed=k))
    objs += [O(f"hf{k}", "text", X0[k], 6.85, CW, 0.3, txt=["radial", "ring", "wave"][k], sz=11, col="muted", z=20,
               meta={"inset": 0.0}) for k in range(3)]
    return mk(objs, "texture", sc)


HIST = [0.598, 0.590, 0.586, 0.583, 0.581, 0.579, 0.577, 0.576, 0.575, 0.574, 0.573, 0.571, 0.570, 0.569, 0.569,
        0.567, 0.566, 0.566, 0.565, 0.564, 0.564, 0.563, 0.563, 0.562, 0.562, 0.561, 0.561, 0.560, 0.560, 0.560,
        0.559, 0.560, 0.560, 0.561, 0.560, 0.561, 0.561]


def s_chart() -> Slide:
    objs = head(13, "12 · chart-draw", "Кривая обучения рисуется по данным",
                "MAE на val по эпохам; бегущая точка с подписью, лучшая эпоха вспыхивает")
    objs += cols(13)
    sc = [SC.chart_draw((X0[k] + 0.15, 2.4, CW - 0.4, 3.4), HIST, y_range=(0.554, 0.602), marks=[(30, "эпоха 31")],
                        decimals=3, delay=0.2, dur=2.2, character=c, seed=k) for k, c in enumerate(CH)]
    return mk(objs, "chart", sc)


def s_bars() -> Slide:
    objs = head(14, "12 · bars-grow", "Столбики растут с пружиной и счётчиками",
                "сверху — свои столбики сцены; снизу — прямоугольники слайда (режим objs)")
    objs += cols(14)
    sc = []
    vals = [("Dummy", 0.643, "muted"), ("Ridge", 0.576, "ink2"), ("сеть", 0.541, "accent")]
    for k, c in enumerate(CH):
        x0 = X0[k]
        sc.append(SC.bars_grow((x0, 2.15, CW - 0.2, 1.7), vals, vmax=0.7, highlight=2, decimals=3, label_w=0.85,
                               delay=0.2, character=c, seed=k))
        names, texts = [], []
        for i, (lab, v, col) in enumerate(vals):
            h = v / 0.7 * 2.0
            bx = x0 + 0.45 + i * 1.1
            objs += [O(f"!!vb{k}_{i}", "rect", bx, 6.6 - h, 0.7, h, fill=col, z=20),
                     O(f"!!vt{k}_{i}", "text", bx - 0.2, 6.6 - h - 0.42, 1.1, 0.35, txt=f"{v:.3f}".replace(".", ","), sz=13,
                       b=True, col="ink2", al="c", z=30, meta={"inset": 0.0}),
                     O(f"vl{k}_{i}", "text", bx - 0.2, 6.65, 1.1, 0.3, txt=lab, sz=11, col="muted", al="c", z=30,
                       meta={"inset": 0.0})]
            names.append(f"!!vb{k}_{i}")
            texts.append(f"!!vt{k}_{i}")
        sc.append(SC.bars_grow(objs=names, texts=texts, orient="v", decimals=3, delay=0.5, character=c, seed=k))
    return mk(objs, "bars", sc)


def _hero(level: float, base, s: float) -> list[O]:
    return Glass("hero", R=0.95, Hb=1.8, stem=1.15).objs(T, base, s=s, level=level, z=20)


def s_morph_a() -> Slide:
    objs = head(15, "Morph · живой бокал", "Бокал живёт на слайде…", "liquid lively: волна после перехода, пузырьки, блик")
    objs += _hero(0.3, (3.0, 6.85), 1.25)
    objs.append(O("!!hv", "text", 5.4, 3.2, 3.5, 0.9, txt="30 %", sz=48, b=True, font="head", col="accent", z=60,
                  meta={"inset": 0.0}))
    return mk(objs, "morph A", [SC.liquid("!!hero", character="lively"), SC.counter("!!hv", delay=0.1, character="lively")])


def s_morph_b() -> Slide:
    objs = head(16, "Morph · живой бокал", "…и переезжает с наливом через Morph",
                "Morph двигает бокал и меняет уровень 30 → 62 %; затем dramatic: плеск, круги по поверхности")
    objs += _hero(0.62, (9.7, 6.9), 1.5)
    objs.append(O("!!hv", "text", 1.2, 3.2, 3.5, 0.9, txt="62 %", sz=48, b=True, font="head", col="accent", z=60,
                  meta={"inset": 0.0}))
    return mk(objs, "morph B", [SC.liquid("!!hero", character="dramatic", kick=1.6),
                                SC.ripple("!!hero", rings=2, period=1.4, count=4, delay=0.3, character="dramatic"),
                                SC.counter("!!hv", start=30, delay=0.0, character="dramatic")], dur=1000)


def slides() -> list[Slide]:
    return [s_cover(), s_liquid(), s_pour(), s_small(), s_particles(), s_into(), s_signal(), s_counter(), s_gauge(),
            s_clock(), s_terminal(), s_burst(), s_texture(), s_chart(), s_bars(), s_morph_a(), s_morph_b()]


HEAVY = 4  # индекс слайда «6000 точек»


# ------------------------------------------------------------------------------ замер FPS
async def _fps(path: Path, slide: int, secs: float = 2.0) -> dict:
    from playwright.async_api import async_playwright
    from morphkit.webdemo import launch_kw
    async with async_playwright() as p:
        b = await p.chromium.launch(**launch_kw())
        pg = await b.new_page(viewport={"width": 1600, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(path.resolve().as_uri())
        await pg.wait_for_timeout(300)
        await pg.evaluate(f"DC.go({slide}, {{instant: true}})")
        await pg.wait_for_timeout(600)
        js = """(secs) => new Promise(res => { let n = 0, worst = 0, last = performance.now(); const t0 = last;
          const tick = now => { n++; worst = Math.max(worst, now - last); last = now;
            if (now - t0 < secs * 1000) requestAnimationFrame(tick); else res({frames: n, fps: n / ((now - t0) / 1000), worst_ms: worst}) };
          requestAnimationFrame(tick) })"""
        r = await pg.evaluate(js, secs)
        r["slide"] = slide
        r["errors"] = errs
        await b.close()
        return r


def measure_fps(path, slide: int = HEAVY, secs: float = 2.0) -> dict:
    return asyncio.run(_fps(Path(path), slide, secs))


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    from morphkit.webdemo import build, shots
    sl = slides()
    path = build(sl, out / "scenes.html", title="Живые сцены deckcraft")
    rep = {"html": str(path), "slides": len(sl)}
    if "--no-shots" not in argv:
        r = shots(path, out, times=[0.3, 1.0, 2.0, 4.0])
        rep.update(errors=r["errors"], sheet=r["sheet"], shots=len(r["files"]))
        print("ошибок консоли:", len(r["errors"]))
        for e in r["errors"][:20]:
            print("  ", e)
    if "--no-fps" not in argv:
        rep["fps"] = measure_fps(path)
        print("FPS на самом тяжёлом слайде:", rep["fps"])
    (out / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items() if k != "errors"}, ensure_ascii=False))
    return 0 if not rep.get("errors") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
