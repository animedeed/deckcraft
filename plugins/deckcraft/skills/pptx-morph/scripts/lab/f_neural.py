"""Нейросеть ищет ошибку в тексте — визуальный язык (не лекция): слои нейронов с волной активации, дуги внимания
между токенами (толщина = вес, перелив при смене запроса), фишки-токены → векторы-столбцы → точки пространства,
«сканер» — светлая полоса идёт по строке и отмечает ошибку волнистой чертой, нейрон улетает по спирали и
раскрывается во взвешенную сумму, softmax выбирает исправление.

Пример фразы с ошибкой согласования: «Вчера мы с братом пошёл в кино» (пошёл → пошли). Тема прогона — neuro.
"""

from __future__ import annotations

import math
import random

from morphkit import Fx, Loop, O
from morphkit import vector as V
from morphkit.qa import line_width_in
from morphkit.theme import SLIDE_H, SLIDE_W, mix

from lab import Variant
from lab._d_util import (DEC, S, bezier, body, dark, flow, head, kicker, label, light, line, raw, ribbon, spiral_pivot, stroke,
                         taper, vs, wave)

FAM = "neural"
W, H = SLIDE_W, SLIDE_H
# Пример по языку: 7 токенов, ошибка согласования в токене 4 с подлежащим в токене 1 (дуга «hot»).
# Английский — своя фраза, а не перевод: у «kids» есть отвлекающее «door» в единственном числе.
PHRASE = {
    "ru": dict(words=["Вчера", "мы", "с", "братом", "пошёл", "в", "кино"], fix="пошли",
               cands=["пошли", "пошла", "ушли", "шли"],
               lines=(["Сегодня", "утром", "шёл", "дождь."], ["Фильм", "оказался", "смешным."])),
    "en": dict(words=["The", "kids", "next", "door", "was", "at", "home"], fix="were",
               cands=["were", "are", "is", "be"],
               lines=(["It", "was", "raining", "today."], ["The", "film", "was", "funny."])),
}
WORDS = PHRASE["ru"]["words"]
ERR = 4
FIX = PHRASE["ru"]["fix"]
CANDS = PHRASE["ru"]["cands"]
LINES = PHRASE["ru"]["lines"]


def use_lang(lang: str | None = None) -> None:
    """Переключить пример фразы на язык (ru/en); надписи — через morphkit.i18n."""
    global WORDS, FIX, CANDS, LINES
    from morphkit.i18n import get_lang, register
    d = PHRASE["en" if (lang or get_lang()) == "en" else "ru"]
    WORDS, FIX, CANDS, LINES = d["words"], d["fix"], d["cands"], d["lines"]
    register({  # подписи, где названы слова фразы
        "«мы … пошёл» — ошибка": "“kids … was” — error", "«мы … пошёл»: число не совпало": "“kids … was”: number mismatch",
        "«пошёл → мы» краснеет, по ней бежит точка: ошибка согласования найдена.":
            "“was → kids” turns red and a dot runs along it: the agreement error is found.",
        "«пошёл» далеко от «мы» и «братом»": "“was” sits far from “kids”", "Внимание «пошёл»": "Attention from “was”",
        "Внимание: «мы»": "Attention: “kids”", "Внимание: «пошёл»": "Attention: “was”", "выход сети предлагает «пошли»":
            "the output suggests “were”", "слово смотрит на подлежащее": "the word looks at its subject"})
ATT = {4: [0.10, 0.62, 0.05, 0.35, 0.0, 0.04, 0.12], 6: [0.05, 0.08, 0.02, 0.06, 0.40, 0.45, 0.0],
       1: [0.10, 0.0, 0.18, 0.30, 0.55, 0.03, 0.04]}


def _v(key, title, idea, slides, tags, score) -> Variant:
    return Variant(FAM, key, title, idea, slides, tags=tags, score=score)


def chips_layout(theme, words, x0, y, sz=22, gap=0.22, pad=0.22):
    """-> [(x, w)] для фишек слов по метрикам шрифта."""
    out, x = [], x0
    probe = O("p", "text", 0, 0, 1, 1, sz=sz, b=True)
    for wd in words:
        w = line_width_in(theme, probe, wd) + 2 * pad
        out.append((x, w))
        x += w + gap
    return out


def chips(theme, words, lay, y, h=0.62, sz=22, cols=None, flagged=None, id="tk", z=20, text=True, alpha=1.0):
    out = []
    for i, (wd, (x, w)) in enumerate(zip(words, lay)):
        bad = flagged == i
        fill = (cols or {}).get(i, "surface2")
        out.append(O(f"!!{id}{i}", "rrect", x, y, w, h, fill="bad" if bad else fill, fa=alpha, ln="bad" if bad else "line",
                     lw=1.25, radius=0.14, z=z))
        if text:
            out.append(O(f"!!{id}{i}t", "text", x, y, w, h, txt=wd, sz=sz, b=True, col="bg" if (bad or fill != "surface2") else "ink", al="c", va="m",
                         z=z + 1, meta={"inset": 0.0}))
    return out


def arc_ribbon(x0, x1, y, hgt, w, n=50):
    pts = bezier((x0, y), (x0, y - hgt), (x1, y - hgt), (x1, y), 40)
    return ribbon(pts, max(w, 0.012), n), pts


# ----------------------------------------------------------------------------- сеть

LAYERS = [5, 7, 7, 3]


def net_pos(x0=4.6, x1=12.0, cy=4.0, gap=0.72, scale=1.0, xs=None):
    xs = xs or [x0 + (x1 - x0) * k / (len(LAYERS) - 1) for k in range(len(LAYERS))]
    return [[(xs[k], cy + (i - (n - 1) / 2) * gap * scale) for i in range(n)] for k, n in enumerate(LAYERS)]


def net_objs(theme, pos, active=None, alpha=1.0, r=0.2, z=10, edges=True, focus=None):
    out, loops = [], []
    for k in range(len(LAYERS) - 1):
        for i, a in enumerate(pos[k]):
            for j, b in enumerate(pos[k + 1]):
                on = active is not None and k == active - 1
                if edges:
                    out.append(line(f"!!e{k}_{i}_{j}", a, b, ln="accent" if on else "line", lw=1.25 if on else 0.75, la=alpha, z=z))
                if on and (i + j) % 3 == 0 and alpha > 0.5:
                    loops.append(flow([a, b], n=1, period=1.4 + 0.1 * ((i * 7 + j) % 5), size=0.09, name=f"act_{k}{i}{j}",
                                      color="accent2", z=z + 0.5))
    for k, layer in enumerate(pos):
        for i, (x, y) in enumerate(layer):
            on = active == k
            fc = focus == (k, i)
            rr = r * (1.35 if on else 1.0)
            out.append(O(f"!!n{k}_{i}", "oval", x - rr, y - rr, 2 * rr, 2 * rr, fill="accent2" if on else ("accent" if fc else "surface2"),
                         ln="accent2" if on else "muted", lw=1.25, fa=alpha, la=alpha, z=z + 5))
    return out, loops


def layers_wave(theme) -> Variant:
    pos = net_pos()
    names = ["вход", "скрытый 1", "скрытый 2", "выход"]
    sl = []
    for st, act in enumerate([0, 1, 3]):
        o, loops = net_objs(theme, pos, active=act)
        o += [label(f"!!ll{k}", pos[k][0][0], 6.75 - 0.0, names[k], w=1.8, sz=13, b=k == act, col="accent2" if k == act else "muted")
              for k in range(4)]
        o += [head(["Сигнал на входе", "Волна по слоям", "Ответ сети"][st], w=4), body("!!b", 0.7, 1.4, 3.6, 0.9,
                                                                                    ["активный слой", "светится"], sz=16)]
        sl.append(S(o, 700, loops=loops))
    return _v("layers_wave", "Волна активации по слоям",
              "Слои нейронов (5–7–7–3): активный слой крупнее и светится, его входящие связи окрашены, по части связей "
              "бегут точки (строго по линиям). Переходы сдвигают волну слой за слоем — «прямой проход».",
              sl, ["neural", "network", "flow", "wave"], 4)


def attention(theme) -> Variant:
    y = 4.8
    lay = chips_layout(theme, WORDS, 1.2, y)
    cx = [x + w / 2 for x, w in lay]
    sl = []
    for st, q in enumerate([1, 4, 4]):
        o = chips(theme, WORDS, lay, y, cols={q: "accent"} if st < 2 else {q: "accent", 1: "surface2"}, flagged=ERR if st == 2 else None)
        loops = []
        for j in range(len(WORDS)):
            wgt = ATT[q][j]
            if j == q:
                wgt = 0.0
            g, pts = arc_ribbon(cx[q], cx[j], y - 0.05, 0.5 + 0.38 * abs(j - q), 0.02 + 0.13 * wgt)
            hot = st == 2 and j == 1
            o.append(raw(f"!!a{j}", g, fill="bad" if hot else "accent", fa=0.25 + 0.75 * wgt if j != q else 0.0, z=10))
            if hot:
                loops.append(flow(pts, n=2, period=1.8, size=0.11, name="att", color="bad", z=11))
        o += [head(["Внимание: «мы»", "Внимание: «пошёл»", "Не согласовано"][st], w=8),
              body("!!b", 0.7, 1.4, 9, 0.45, ["толщина дуги — вес связи", "слово смотрит на подлежащее", "«мы … пошёл»: число не совпало"][st],
                   sz=16, col="muted" if st < 2 else "bad")]
        sl.append(S(o, 800, loops=loops))
    return _v("attention", "Дуги внимания переливаются",
              "Дуги от слова-запроса ко всем словам: толщина и прозрачность = вес внимания (свободные формы-ленты с "
              "согласованными точками). Смена запроса — дуги перетекают от нового центра; затем сильнейшая дуга "
              "«пошёл → мы» краснеет, по ней бежит точка: ошибка согласования найдена.",
              sl, ["neural", "attention", "shape-morph", "flag"], 4)


def _vec_vals(i, d=8):
    rnd = random.Random(i * 13 + 1)
    return [rnd.uniform(-1, 1) for _ in range(d)]


def token_vectors(theme) -> Variant:
    y = 2.2
    lay = chips_layout(theme, WORDS, 1.0, y)
    sl = []
    # 1 фишки
    sl.append(S(chips(theme, WORDS, lay, y) + [head("Токены", w=5)], 700))
    # 2 фишка -> столбец вектора (8 ячеек)
    o = [head("Каждый токен — вектор", w=8)]
    d = 8
    cell = 0.36
    for i, (x, w) in enumerate(lay):
        cxi = x + w / 2
        o.append(O(f"!!tk{i}", "rrect", cxi - 0.24, y + 0.8, 0.48, d * cell + 0.12, fill="surface", ln="line", lw=1.0, radius=0.08, z=20))
        o.append(O(f"!!tk{i}t", "text", x, y, w, 0.62, txt=WORDS[i], sz=22, b=True, col="ink", al="c", va="m", z=21, meta={"inset": 0.0}))
        for k, v in enumerate(_vec_vals(i, d)):
            c = mix(theme.c("accent2"), theme.c("accent"), (v + 1) / 2)
            o.append(O(f"v{i}_{k}", "rect", cxi - 0.18, y + 0.86 + k * cell, 0.36, cell - 0.06, fill=c, fa=0.35 + 0.65 * abs(v), z=22))
    fx = [Fx("entrance_fade", f"v{i}_{k}", start="at", delay=0.15 + 0.02 * (i * d + k), dur=0.2) for i in range(len(WORDS)) for k in range(d)]
    sl.append(S(o, 900, fx=fx[:56]))
    # 3 векторы -> точки пространства; «пошёл» — выброс
    pts = {0: (3.0, 5.2), 1: (6.0, 3.0), 2: (4.4, 5.9), 3: (6.9, 3.6), 4: (10.6, 2.4), 5: (4.0, 6.3), 6: (7.6, 5.6)}
    o = [head("Пространство смыслов", w=8), body("!!b", 0.7, 1.4, 6, 0.4, "«пошёл» далеко от «мы» и «братом»", sz=16, col="muted"),
         O("cl", "oval", 5.3, 2.5, 2.4, 1.6, fill="accent2", fa=0.12, ln="accent2", lw=1.0, la=0.6, z=5)]
    for i in range(len(WORDS)):
        x, yy = pts[i]
        bad = i == ERR
        o.append(O(f"!!tk{i}", "oval", x - 0.14, yy - 0.14, 0.28, 0.28, fill="bad" if bad else "accent2", z=20))
        o.append(O(f"!!tk{i}t", "text", x + 0.2, yy - 0.2, 1.5, 0.4, txt=WORDS[i], sz=16, b=bad, col="bad" if bad else "ink", z=21,
                   meta={"inset": 0.0}))
    sl.append(S(o, 900, loops=[Loop("ripple", target="!!tk4", period=1.8, scale=2.6, color="bad", name="rip")]))
    return _v("token_vectors", "Фишка → вектор → точка",
              "Носитель «токен»: фишка вытягивается в столбец вектора (8 ячеек, оттенок = значение, появляются по "
              "очереди), затем столбец схлопывается в точку пространства; слово-ошибка — выброс от своей группы, "
              "вокруг него — круги. Подпись едет вместе с телом токена.",
              sl, ["neural", "carrier", "encode", "scatter"], 4)


def _wavy(x0, x1, y, n=60):
    return stroke(wave(x0, x1, y, 0.05, (x1 - x0) / 0.22, 0, n), 0.03)


def scanner(theme) -> Variant:
    lines_ = [LINES[0], WORDS, LINES[1]]
    ys = [2.4, 3.5, 4.6]
    lays = [chips_layout(theme, ln, 1.2, y, sz=24, gap=0.12, pad=0.06) for ln, y in zip(lines_, ys)]
    def text_objs(flag=False):
        o = []
        for r, (ln, lay, y) in enumerate(zip(lines_, lays, ys)):
            for i, (wd, (x, w)) in enumerate(zip(ln, lay)):
                bad = flag and r == 1 and i == ERR
                o.append(O(f"!!w{r}_{i}", "text", x, y, w, 0.5, txt=wd, sz=24, col="bad" if bad else "ink", b=bad, al="c", z=30,
                           meta={"inset": 0.0}))
        return o
    def bar(x, hgt=3.4):
        g = V.rect(x - 0.35, 2.0, 0.7, hgt)
        return vs("!!scan", g, fill="accent", fa=0.22, z=10, grad=V.gradient([(0, "accent", 0.0), (0.5, "accent", 0.45), (1, "accent", 0.0)], 0),
                  meta=dict(DEC))
    sl = []
    xs = [1.4, 5.6, lays[1][ERR][0] + lays[1][ERR][1] / 2]
    for st in range(3):
        o = text_objs(flag=st == 2) + [bar(xs[st]), O("!!scl", "line", xs[st], 1.9, 0, 3.6, ln="accent", lw=2.0, z=11),
                                       head(["Сканер читает", "Идёт по строкам", "Нашёл ошибку"][st], w=6)]
        loops = []
        if st == 2:
            x, w = lays[1][ERR]
            o.append(vs("err", _wavy(x, x + w, ys[1] + 0.52), fill="bad", z=31))
            o.append(label("fix", x + w / 2, ys[1] + 0.75, f"→ {FIX}", w=1.6, sz=18, b=True, col="accent2"))
            loops = [Loop("ripple", target="err", period=1.8, scale=1.3, color="bad", name="rip")]
        sl.append(S(o, 800, loops=loops, fx=[Fx("entrance_wipe", "err", start="at", delay=0.15, dur=0.4, options={"direction": "left"}),
                                             Fx("entrance_fade", "fix", start="at", delay=0.5)] if st == 2 else []))
    return _v("scanner", "Сканер идёт по тексту и ставит черту",
              "Светлая полоса (градиент с прозрачными краями) и линия-курсор переезжают по тексту; на ошибке слово "
              "краснеет, под ним вытирается волнистая черта (как в редакторе), рядом — исправление. Текст стоит, едет "
              "только сканер — внимание идёт за ним.",
              sl, ["neural", "flag", "text", "scanner"], 4)


def prob_bars(theme) -> Variant:
    y = 5.4
    lay = chips_layout(theme, WORDS, 1.2, y)
    probs = [0.03, 0.05, 0.02, 0.06, 0.91, 0.03, 0.04]
    sl = []
    for st in range(2):
        o = chips(theme, WORDS, lay, y, flagged=ERR if st == 1 else None)
        for i, (x, w) in enumerate(lay):
            hgt = 0.02 if st == 0 else 3.4 * probs[i] + 0.04
            bad = i == ERR and st == 1
            o.append(O(f"!!pb{i}", "rect", x + w / 2 - 0.25, y - 0.15 - hgt, 0.5, hgt, fill="bad" if bad else "muted", z=15))
        o += [head(["Оценка каждого слова", "Вероятность ошибки"][st], w=8)]
        if st == 1:
            o.append(label("pv", lay[ERR][0] + lay[ERR][1] / 2, y - 0.15 - 3.4 * probs[ERR] - 0.45, "высокая", w=1.6, sz=15, b=True, col="bad"))
        sl.append(S(o, 800))
    return _v("prob_bars", "Столбики вероятности над словами",
              "Глагол «оценить»: над каждой фишкой вырастает столбик вероятности ошибки (условные значения), столбик "
              "слова-ошибки высокий и красный, фишка перекрашивается. Числа не нужны — видна форма.",
              sl, ["neural", "score", "bars"], 3)


def neuron_zoom(theme) -> Variant:
    pos = net_pos(x0=1.6, x1=5.6, gap=0.55)
    k0, i0 = 1, 3
    g0 = pos[k0][i0]
    r0 = 0.2
    T, R = (9.4, 4.0), 2.1
    s = R / r0
    th = 140.0
    p = spiral_pivot(g0, T, s, th)
    sl = []
    for st in range(3):
        o, loops = net_objs(theme, pos, alpha=1.0 if st == 0 else 0.35, focus=(k0, i0), r=r0)
        o = [ob for ob in o if ob.name != f"!!n{k0}_{i0}"]
        g = V.circle(g0[0], g0[1], r0)
        if st == 0:
            o.append(vs("!!big", g, pivot=p, rot=0, fill="accent", z=40))
        else:
            o.append(vs("!!big", V.scale(g, s, s, origin=p), pivot=p, rot=th, fill="surface2", ln="accent", lw=2.5, z=40))
        if st >= 1:
            # входы и сумма внутри
            for j in range(5):
                a = math.radians(160 + 10 * j)
                x0_, y0_ = T[0] + (R + 1.2) * math.cos(a), T[1] + (R + 1.2) * math.sin(a) * 0.9
                o.append(line(f"in{j}", (x0_, y0_), (T[0] - 0.9, T[1]), ln="accent2", lw=1.0 + 0.6 * j, z=41))
            o.append(O("sig", "text", T[0] - 0.9, T[1] - 0.45, 0.9, 0.9, txt="Σ", sz=40, b=True, col="ink", al="c", va="m", z=45,
                       meta={"inset": 0.0}))
        if st == 2:
            curve = [(T[0] + 0.1 + 1.6 * i / 40, T[1] + 0.7 - 1.4 / (1 + math.exp(-(i / 40 * 12 - 6)))) for i in range(41)]
            o.append(vs("sigm", stroke(curve, 0.06), fill="accent", z=46))
            o.append(label("sl", T[0] + 0.9, T[1] + 0.95, "активация", w=1.8, sz=14, col="accent"))
        o += [head(["Один нейрон", "Взвешенная сумма", "Затем — активация"][st], w=5.5),
              body("!!b", 0.7, 1.4, 5, 0.4, ["скрытый слой 1", "толщина входа — вес", "плавный порог"][st], sz=16, col="muted")]
        sl.append(S(o, 900 if st == 1 else 700, fx=[Fx("entrance_wipe", "sigm", start="at", delay=0.1, dur=0.5, options={"direction": "left"})]
                    if st == 2 else []))
    return _v("neuron_zoom", "Нейрон летит по спирали и раскрывается",
              "Часть мотива увеличивается по дуге: нейрон из слоя улетает по спирали (центр спирального подобия, поворот "
              "140°, рост ×10) и становится большим кругом, внутри — входы разной толщины, Σ, затем кривая активации "
              "вытирается слева направо. Сеть остаётся бледным контекстом.",
              sl, ["neural", "zoom", "spiral", "network"], 4)


def net_pointer(theme) -> Variant:
    secs = ["Токены", "Векторы", "Внимание", "Ошибка"]
    pos = net_pos(xs=[-0.6, 0.35, 1.3, 2.25], gap=0.95)
    sl = []
    for k in range(3):
        o, loops = net_objs(theme, pos, active=k, r=0.17)
        o = [ob.copy(meta={**ob.meta, **DEC}) for ob in o]
        o += [label(f"!!sc{i}", 3.2, 2.6 + i * 0.55, f"0{i + 1} {s}", w=2.2, al="l", sz=13, b=i == k, col="accent2" if i == k else "muted")
              for i, s in enumerate(secs)]
        o += [kicker(f"раздел {k + 1}", x=5.8), head(secs[k], x=5.8, w=7),
              body("!!txt", 5.8, 1.5, 7, 1.0, ["слово → номер в словаре", "номер → 768 чисел", "кто на кого смотрит"][k], sz=20)]
        sl.append(S(o, 700, loops=loops))
    return _v("net_pointer", "Сеть у края: слой = раздел",
              "Навигация: сеть срезана левым краем, слой раздела светится и по входящим связям бежит сигнал; смена "
              "раздела — волна сдвигается на слой. Подписи разделов — столбиком рядом с сетью.",
              sl, ["neural", "pointer", "navigation", "flow"], 3)


def act_steps(theme) -> Variant:
    topics = ["Токенизация", "Словарь", "Позиции", "Маска"]
    sl = []
    for k in range(3):
        o = [kicker("раздел 1 · подготовка текста"), head(f"Шаг {k + 1}: {topics[k].lower()}", w=7)]
        for i in range(4):
            x, y = 9.6, 1.9 + i * 1.2
            on = i <= k
            r = 0.36 if i == k else 0.28
            o.append(O(f"!!sn{i}", "oval", x - r, y - r, 2 * r, 2 * r, fill="accent2" if on else "surface2", ln="accent2" if on else "muted",
                       lw=1.5, z=10))
            o.append(label(f"!!st{i}", x + 0.55, y - 0.17, topics[i], w=2.4, al="l", sz=15, b=i == k,
                           col="ink" if on else "muted"))
            if i < 3:
                o.append(line(f"!!sl{i}", (x, y + r), (x, y + 1.2 - 0.3), ln="accent2" if i < k else "line", lw=2.0, z=5))
        o.append(body("!!b", 0.7, 1.45, 6, 0.4, f"{(k + 1) * 25} % раздела", sz=16, col="accent2"))
        loops = [Loop("pulse", target=f"!!sn{k}", period=1.6, scale=1.12, name="p")]
        sl.append(S(o, 600, loops=loops))
    return _v("act_steps", "Нейроны-шаги загораются",
              "Прогресс внутри раздела: столбик из 4 нейронов = 4 темы; пройденные светятся, текущий крупнее и «дышит» "
              "(pulse), связь до него окрашена. 25 → 50 → 75 %.",
              sl, ["neural", "progress", "pulse"], 3)


def net_backdrop(theme) -> Variant:
    sl = []
    for st in range(2):
        pos = net_pos(x0=3.0 + st * 0.8, x1=15.5 + st * 0.8, cy=4.4, gap=1.35)
        o, _ = net_objs(theme, pos, active=1 + st, alpha=0.13, r=0.3, z=-300)
        o = [ob.copy(meta={**ob.meta, **DEC}) for ob in o]
        o += [head(["Зачем это редактору", "Что остаётся человеку"][st], w=8),
              body("!!txt", 0.7, 1.5, 7, 2.2, [["ошибки согласования", "пропущенные запятые", "опечатки в именах"],
                                               ["стиль и тон", "факты", "последнее слово"]][st], sz=22, col="ink")]
        sl.append(S(o, 800))
    return _v("net_backdrop", "Бледная сеть под текстом",
              "Фон: та же сеть крупно, прозрачность 13 %, под текстом; между слайдами сдвигается и волна активации "
              "переходит на следующий слой — фон живой, но не спорит с содержанием.",
              sl, ["neural", "backdrop"], 3)


def softmax_fix(theme) -> Variant:
    y = 5.6
    cands = CANDS
    logits = [0.82, 0.12, 0.04, 0.02]
    sl = []
    lay = chips_layout(theme, WORDS, 1.2, y)
    for st in range(3):
        words = list(WORDS)
        if st == 2:
            words[ERR] = FIX
        lay2 = chips_layout(theme, words, 1.2, y)
        o = []
        for i, (wd, (x, w)) in enumerate(zip(words, lay2)):
            if i == ERR:
                continue
            o.append(O(f"!!tk{i}", "rrect", x, y, w, 0.62, fill="surface2", ln="line", lw=1.25, radius=0.14, z=20))
            o.append(O(f"!!tk{i}t", "text", x, y, w, 0.62, txt=wd, sz=22, b=True, col="ink", al="c", va="m", z=21, meta={"inset": 0.0}))
        xe, we = lay2[ERR]
        if st < 2:
            o.append(O("!!tkE", "rrect", xe, y, we, 0.62, fill="bad", radius=0.14, z=20))
            o.append(O("tkEt", "text", xe, y, we, 0.62, txt=WORDS[ERR], sz=22, b=True, col="bg", al="c", va="m", z=21, meta={"inset": 0.0}))
        for j, (c, v) in enumerate(zip(cands, logits)):
            yy = 2.0 + j * 0.75
            L = 0.05 if st == 0 else 5.0 * v
            top = j == 0
            if st == 2 and top:
                o.append(O("!!cand0", "rrect", xe, y, lay2[ERR][1], 0.62, fill="accent2", radius=0.14, z=22))
                o.append(O("!!cand0t", "text", xe, y, lay2[ERR][1], 0.62, txt=c, sz=22, b=True, col="bg", al="c", va="m", z=23,
                           meta={"inset": 0.0}))
                continue
            o.append(O(f"!!cand{j}", "rrect", 6.0, yy, 1.6, 0.55, fill="accent2" if top and st else "surface2", radius=0.12, z=22))
            o.append(O(f"!!cand{j}t", "text", 6.0, yy, 1.6, 0.55, txt=c, sz=18, b=True, col="bg" if top and st else "ink", al="c", va="m",
                       z=23, meta={"inset": 0.0}))
            o.append(O(f"!!cb{j}", "rect", 7.8, yy + 0.1, L, 0.35, fill="accent2" if top else "muted", z=22))
        o += [head(["Кандидаты", "Softmax", "Исправлено"][st], w=5)]
        sl.append(S(o, 800))
    return _v("softmax_fix", "Softmax выбирает, фишка встаёт в строку",
              "Кандидаты на место ошибки — фишки со столбиками (условные вероятности растут из нуля), победитель "
              "перелетает в строку на место красной фишки, соседние фишки раздвигаются под новую ширину слова.",
              sl, ["neural", "score", "carrier", "fix"], 4)


def seq_neural(theme) -> Variant:
    """Фраза через презентацию: фишки (обложка) → векторы → векторы сжимаются во входы сети → волна по слоям → выход
    возвращается в строку дугами внимания → сканер находит ошибку → сеть у края (навигация) + исправление → финал."""
    y = 4.8
    lay = chips_layout(theme, WORDS, 1.2, y)
    cx = [x + w / 2 for x, w in lay]
    n = len(WORDS)
    S_ = []
    pos = net_pos(x0=4.2, x1=12.0, gap=0.7)
    inputs = [(2.6, 4.0 + (i - 3) * 0.62) for i in range(n)]
    def toks(states, flagged=None, text=True, cols=None):
        o = []
        for i, (x, yy, w, h, kind) in enumerate(states):
            bad = flagged == i
            o.append(O(f"!!tk{i}", kind, x, yy, w, h, fill="bad" if bad else (cols or {}).get(i, "surface2"), ln="bad" if bad else "line",
                       lw=1.25, radius=0.14 if kind == "rrect" else None, z=20))
            if text:
                o.append(O(f"!!tk{i}t", "text", x if kind == "rrect" else x - 1.7, yy if kind == "rrect" else yy - 0.08, w if kind == "rrect" else 1.6,
                           h if kind == "rrect" else 0.4, txt=WORDS[i], sz=22 if kind == "rrect" else 14, b=True,
                           col="bg" if (bad or (cols or {}).get(i)) and kind == "rrect" else "ink", al="c" if kind == "rrect" else "r", va="m", z=21, meta={"inset": 0.0}))
        return o
    row = [(x, y, w, 0.62, "rrect") for x, w in lay]
    # 1 обложка
    S_.append(S(toks(row) + [kicker("нейросеть и текст"), O("!!cov", "text", 0.7, 1.0, 9, 1.7, txt=["Как сеть находит", "ошибку в тексте"],
                                                            sz=44, b=True, font="head", col="ink", spacing=0.95, z=90)], 700))
    # 2 векторы
    vcol = [(c - 0.24, y - 3.0, 0.48, 3.4, "rrect") for c in cx]
    o2 = toks(vcol, text=False) + [O(f"!!tk{i}t", "text", lay[i][0], y + 0.5, lay[i][1], 0.5, txt=WORDS[i], sz=18, b=True, col="ink", al="c",
                                     z=21, meta={"inset": 0.0}) for i in range(n)]
    for i in range(n):
        for k, v in enumerate(_vec_vals(i)):
            c = mix(theme.c("accent2"), theme.c("accent"), (v + 1) / 2)
            o2.append(O(f"v{i}_{k}", "rect", cx[i] - 0.18, y - 2.94 + k * 0.415, 0.36, 0.36, fill=c, fa=0.35 + 0.65 * abs(v), z=22))
    S_.append(S(o2 + [head("Слова → векторы", w=7)], 900,
                fx=[Fx("entrance_fade", f"v{i}_{k}", start="at", delay=0.15 + 0.012 * (i * 8 + k), dur=0.2) for i in range(n) for k in range(8)][:56]))
    # 3–4 векторы сжимаются во входы; волна по слоям
    inp = [(x - 0.16, yy - 0.16, 0.32, 0.32, "oval") for x, yy in inputs]
    # 3 входы сети: векторы сжались во входы, загорается первый слой
    o, loops = net_objs(theme, pos, active=0)
    o += toks(inp)
    o += [line(f"in{i}", inputs[i], pos[0][min(i * 5 // n, 4)], ln="accent2", lw=1.0, z=9) for i in range(n)]
    loops = [flow([inputs[i], pos[0][min(i * 5 // n, 4)]], n=1, period=1.5, size=0.09, name=f"in_{i}", color="accent2")
             for i in range(0, n, 2)]
    S_.append(S(o + [head("Входы сети", w=6)], 900, loops=loops))
    # 4 волна по слоям — на одном слайде, без скачка: слои загораются по очереди (связи k−1 → k, затем узлы k),
    # сигнал бежит непрерывно от входа через все слои к выходу — связь каждого слоя со следующим видна
    o, _ = net_objs(theme, pos, active=0)
    o += toks(inp)
    o += [line(f"in{i}", inputs[i], pos[0][min(i * 5 // n, 4)], ln="accent2", lw=1.0, z=9) for i in range(n)]
    fx = []
    for k in range(1, len(LAYERS)):
        edges = V.union(*[stroke([a, b], 0.018) for a in pos[k - 1] for b in pos[k]])
        o.append(vs(f"wave_e{k}", edges, fill="accent", fa=0.8, z=9, meta=dict(DEC)))
        o.append(vs(f"wave_n{k}", V.union(*[V.circle(x, yy, 0.27) for x, yy in pos[k]]), fill="accent2", z=16,
                    meta=dict(DEC)))
        d = 0.15 + 0.6 * (k - 1)
        fx += [Fx("entrance_fade", f"wave_e{k}", start="at", delay=d, dur=0.35),
               Fx("entrance_fade", f"wave_n{k}", start="at", delay=d + 0.3, dur=0.3)]
    loops = []
    for r, (i, j0, j1, j2, j3) in enumerate([(0, 0, 1, 2, 0), (3, 2, 3, 3, 1), (6, 4, 6, 5, 2)]):
        path = [inputs[i], pos[0][j0], pos[1][j1], pos[2][j2], pos[3][j3]]
        loops.append(flow(path, n=1, period=2.4, size=0.1, name=f"wave_{r}", color="accent2", z=17, start=1.9 + 0.4 * r))
    S_.append(S(o + [head("Волна по слоям", w=6)], 700, loops=loops, fx=fx))
    # 5 ответ возвращается в строку: дуги внимания от «пошёл»
    o5 = toks(row, cols={ERR: "accent"})
    loops = []
    for j in range(n):
        wgt = 0.0 if j == ERR else ATT[ERR][j]
        g, pts = arc_ribbon(cx[ERR], cx[j], y - 0.05, 0.5 + 0.38 * abs(j - ERR), 0.02 + 0.13 * wgt)
        o5.append(raw(f"!!a{j}", g, fill="accent", fa=0.25 + 0.75 * wgt if j != ERR else 0.0, z=10))
    S_.append(S(o5 + [head("Внимание «пошёл»", w=7)], 900))
    # 6 сканер находит
    o6 = toks(row, flagged=ERR)
    for j in range(n):
        wgt = 0.0 if j == ERR else ATT[ERR][j]
        g, pts = arc_ribbon(cx[ERR], cx[j], y - 0.05, 0.5 + 0.38 * abs(j - ERR), 0.02 + 0.13 * wgt)
        hot = j == 1
        o6.append(raw(f"!!a{j}", g, fill="bad" if hot else "accent", fa=(0.25 + 0.75 * wgt) * (1 if hot else 0.4) if j != ERR else 0.0, z=10))
        if hot:
            loops = [flow(pts, n=2, period=1.8, size=0.11, name="att", color="bad", z=11)]
    xe, we = lay[ERR]
    # найденное слово: мягкий ореол из вложенных овалов (свет без краёв и обрыва) и волнистая черта, как в редакторе;
    # без пульсации — внимание держит красная дуга «пошёл → мы» с бегущей точкой
    cxe, cye = xe + we / 2, y + 0.31
    for j in range(4):
        o6.append(vs(f"glow{j}", V.ellipse(cxe, cye, we / 2 + 0.22 + 0.32 * j, 0.5 + 0.26 * j), fill="bad",
                     fa=0.13 - 0.028 * j, z=7 - j, meta=dict(DEC)))
    o6 += [vs("err_ul", _wavy(xe + 0.1, xe + we - 0.1, y + 0.74), fill="bad", z=22),
           head("«мы … пошёл» — ошибка", w=8)]
    S_.append(S(o6, 800, loops=loops, fx=[Fx("entrance_fade", f"glow{j}", start="with" if j else "at", delay=0.1, dur=0.6)
                                          for j in range(4)]
                + [Fx("entrance_wipe", "err_ul", start="at", delay=0.2, dur=0.45, options={"direction": "left"})]))
    # 7 сеть у края — навигация; фраза исправлена
    words = list(WORDS)
    words[ERR] = FIX
    lay2 = chips_layout(theme, words, 4.4, 4.2)
    pos7 = net_pos(xs=[-0.6, 0.35, 1.3, 2.25], gap=0.95)
    o7, loops = net_objs(theme, pos7, active=3, r=0.17)
    o7 = [ob.copy(meta={**ob.meta, **DEC}) for ob in o7]
    for i, (x, w) in enumerate(lay2):
        fix = i == ERR
        o7.append(O(f"!!tk{i}", "rrect", x, 4.2, w, 0.62, fill="accent2" if fix else "surface2", ln="line", lw=1.25, radius=0.14, z=20))
        o7.append(O(f"!!tk{i}t" if not fix else "fixt", "text", x, 4.2, w, 0.62, txt=words[i], sz=22, b=True, col="bg" if fix else "ink",
                    al="c", va="m", z=21, meta={"inset": 0.0}))
    o7 += [kicker("раздел 4 · исправление", x=4.4), head("Исправлено", x=4.4, w=7),
           body("!!b", 4.4, 1.5, 7, 1.0, ["выход сети предлагает «пошли»", "человек принимает правку"], sz=18)]
    S_.append(S(o7, 900, loops=loops))
    # 8 финал: фраза крупно, сеть — бледный фон
    lay3 = chips_layout(theme, words, 1.2, 4.6, sz=22)
    pos8 = net_pos(x0=2.0, x1=12.5, cy=4.0, gap=1.0)
    o8, _ = net_objs(theme, pos8, active=None, alpha=0.12, r=0.26, z=-300)
    o8 = [ob.copy(meta={**ob.meta, **DEC}) for ob in o8]
    for i, (x, w) in enumerate(lay3):
        fix = i == ERR
        o8.append(O(f"!!tk{i}", "rrect", x, 4.6, w, 0.62, fill="accent2" if fix else "surface2", ln="line", lw=1.25, radius=0.14, z=20))
        o8.append(O(f"!!tk{i}t" if not fix else "fixt", "text", x, 4.6, w, 0.62, txt=words[i], sz=22, b=True, col="bg" if fix else "ink",
                    al="c", va="m", z=21, meta={"inset": 0.0}))
    o8 += [O("!!fin", "text", 0.7, 1.2, 9, 1.6, txt=["Сеть видит связи,", "человек решает"], sz=40, b=True, font="head", col="ink",
             spacing=0.95, z=90)]
    S_.append(S(o8, 900))
    return _v("seq_neural", "Фраза проходит через сеть",
              "8 состояний одних и тех же 7 токенов: фишки (обложка) → столбцы-векторы → векторы сжимаются во входы "
              "сети, волна по слоям → токены возвращаются в строку, дуги внимания от «пошёл» → сканер и красная дуга "
              "к «мы»: ошибка → сеть уходит к левому краю (навигация), фишка-исправление → финал на бледной сети.",
              S_, ["seq", "neural", "carrier", "attention", "flag", "pointer", "backdrop"], 4)


def variants(theme) -> list[Variant]:
    use_lang()
    return [seq_neural(theme), layers_wave(theme), attention(theme), token_vectors(theme), scanner(theme), prob_bars(theme),
            neuron_zoom(theme), net_pointer(theme), act_steps(theme), net_backdrop(theme), softmax_fix(theme)]
