"""Демо модуля «эффекты и текст» (morphkit/web/fx.js): витрины входов, выделений, выходов и перелив текста и чисел.

    python3 -m morphkit.demo_fx OUT_DIR [--all] [--no-shots]

Собирает OUT_DIR/demo_fx.html (тема «Лаборатория»), снимает кадры через несколько моментов после перехода
(OUT_DIR/s??_*.png и лист OUT_DIR/sheet.png) и печатает ошибки консоли — их должно быть 0.
По умолчанию в страницу входят только core.js и fx.js (проверка модуля в изоляции); --all — все модули папки web.
Каждый эффект подписан своим ключом и запущен со ступенчатой задержкой: web(slide, fx=[{"key", "target", "delay",
"dur", "options"}]). Перелив: одинаковые имена '!!…' на соседних слайдах с разным текстом (meta["morph_text"]=True,
иначе политика текста экспорта разрывает пару).
"""

from __future__ import annotations

import sys
from pathlib import Path

from .html import web
from .model import O, Slide

W, H = 13.333, 7.5
X0, Y0, X1, Y1, GAP = 0.6, 1.55, W - 0.6, 7.15, 0.18

# короткие подписи (полные — DC.fxInfo в fx.js)
DESC = {
    "in.stamp": "рывками, как печать", "in.registration": "сдвиг краски", "in.write": "пишется по строкам",
    "in.type": "печать с курсором", "in.scramble": "расшифровка", "in.count": "счётчик",
    "in.highlight": "маркер-подложка", "in.ink": "растекание туши", "in.blur": "из размытия",
    "in.glitch": "сбой сигнала", "in.reveal-r": "шторка вправо", "in.iris": "кругом из центра",
    "in.elastic": "пружина", "in.back": "с перелётом", "in.bounce": "мячиком", "in.drop": "падает сверху",
    "in.pop": "выскакивает", "in.flip": "переворот sx", "in.unfold": "раскрытие sy", "in.zoom": "из малого",
    "in.zoom-out": "из большого", "in.spin": "вкручивается", "in.swing": "на петле сверху", "in.fade": "проявление",
    "in.slide-l": "едет влево", "in.slide-r": "едет вправо", "in.slide-u": "едет вверх", "in.slide-d": "едет вниз",
    "in.rise": "всплывает", "in.reveal-l": "шторка влево", "in.reveal-u": "шторка вверх",
    "in.reveal-d": "шторка вниз", "in.letters": "буквы по одной", "in.wave-letters": "волна букв",
    "in.split-letters": "буквы слетаются", "in.words": "слова по одному", "in.rain-letters": "буквы падают",
    "in.pop-letters": "буквы выскакивают",
    "em.pulse": "пульс", "em.shake": "дрожь", "em.wobble": "вихляние", "em.jello": "желе", "em.heartbeat": "сердце",
    "em.glow": "свечение accent", "em.flash": "вспышка", "em.tada": "та-дам", "em.float": "парение, повтор",
    "em.color": "перекрасить и оставить", "em.swing": "качание", "em.rubber": "резинка", "em.dim": "приглушить",
    "em.wave": "волна по буквам, повтор", "em.grow": "увеличить и оставить", "em.spin": "оборот",
    "em.reg": "краска отходит", "em.glitch": "короткий сбой", "em.mark": "маркер и оставить", "em.jump": "подскок",
    "out.fade": "растворение", "out.zoom": "на зрителя", "out.drop": "падает", "out.slide-l": "уезжает влево",
    "out.slide-r": "уезжает вправо", "out.slide-u": "уезжает вверх", "out.slide-d": "уезжает вниз",
    "out.blur": "в размытие", "out.shrink": "в точку", "out.burn": "выгорание", "out.flip": "переворот",
    "out.fold": "складывается", "out.spin": "выкручивается", "out.erase-l": "стирание влево",
    "out.erase-r": "стирание вправо", "out.erase-u": "стирание вверх", "out.erase-d": "стирание вниз",
    "out.type": "забой с курсором", "out.glitch": "уходит сбоем", "out.ink": "тушь в воде",
    "out.words": "слова уходят", "out.letters": "буквы падают", "out.scatter-letters": "буквы разлетаются",
}


def sample(kind: str, n: str, x: float, y: float, w: float, h: float, txt: str = "", **kw) -> list[O]:
    """Образец в ячейке: текст разного кегля или фигура с подписью (всё по центру ячейки)."""
    cx, cy = x + w / 2, y + h / 2
    if kind in ("word", "big", "acc", "bad"):
        return [O(n, "text", x, y, w, h, txt=txt, sz=32 if kind == "big" else 26, b=True, font="head", al="c",
                  va="m", col={"acc": "accent", "bad": "bad"}.get(kind, "ink"), **kw)]
    if kind == "para":
        return [O(n, "text", x, y, w, h, txt=txt, sz=18, al="c", va="m", **kw)]
    if kind == "line":
        return [O(n, "text", x, y, w, h, txt=txt, sz=19, al="l", va="m", **kw)]
    if kind == "mono":
        return [O(n, "text", x, y, w, h, txt=txt, sz=17, font="mono", al="l", va="m", **kw)]
    if kind == "card":
        cw, ch = min(w, 2.1), min(h, 0.72)
        return [O(n, "rrect", cx - cw / 2, cy - ch / 2, cw, ch, fill="accent", txt=txt, sz=19, b=True, col="on_accent",
                  al="c", va="m", radius=0.12, **kw)]
    if kind == "disc":
        d = min(h, 0.95)
        return [O(n, "oval", cx - d / 2, cy - d / 2, d, d, fill="accent2", txt=txt, sz=18, b=True, col="on_accent",
                  al="c", va="m", **kw)]
    if kind == "tile":
        d = min(h, 1.0)
        return [O(n, "rrect", cx - d / 2, cy - d / 2, d, d, fill="accent3", txt=txt, sz=17, b=True,
                  col="on_accent", al="c", va="m", radius=0.14, **kw)]
    if kind == "stamp":
        return [O(n, "rrect", cx - 1.0, cy - 0.36, 2.0, 0.72, ln="accent", lw=3, txt=txt, sz=24, b=True, col="accent",
                  al="c", va="m", caps=True, tracking=2, rot=-6, radius=0.1, **kw)]
    if kind == "sign":
        return [O(n, "rrect", cx - 0.95, cy - 0.32, 1.9, 0.64, fill="surface2", ln="ink2", lw=1.5, txt=txt, sz=17,
                  b=True, col="ink", al="c", va="m", caps=True, tracking=1.5, radius=0.08, **kw)]
    if kind == "bar":
        return [O(n, "rect", x + w * 0.08, cy - 0.22, w * 0.84, 0.44, fill="accent", **kw)]
    raise ValueError(kind)


def header(k: int, total: int, kicker: str, title: str) -> list[O]:
    morph = {"morph_text": True}
    return [O("!!kick", "text", X0, 0.38, 8.0, 0.3, txt=kicker, sz=12, b=True, col="accent", caps=True, tracking=1.2,
              meta=morph),
            O("!!ttl", "text", X0, 0.62, 10.0, 0.75, txt=title, sz=30, b=True, font="head", meta=morph),
            O("!!pg", "text", W - 2.6, 0.4, 2.0, 0.4, txt=f"{k:02d} / {total}", sz=14, font="mono", col="muted",
              al="r", meta=morph),
            O("!!rule", "line", X0, 1.38, W - 2 * X0, 0.0, ln="line", lw=1)]


def grid(cells: list, cols: int, rows: int, kind: str = "in", step: float = 0.3, start: float = 0.2,
         dur: float = 0.9) -> tuple[list[O], list[dict]]:
    """cells: [(ключ, вид образца, текст, opts | None, dur | None, repeat)] → объекты витрины и план эффектов."""
    cw = (X1 - X0 - GAP * (cols - 1)) / cols
    ch = (Y1 - Y0 - GAP * (rows - 1)) / rows
    objs, fx = [], []
    for k, cell in enumerate(cells):
        key, sk, txt, opts, d, rep = (list(cell) + [None, None, False])[:6]
        x, y = X0 + (k % cols) * (cw + GAP), Y0 + (k // cols) * (ch + GAP)
        objs.append(O(f"c{k}", "rect", x, y, cw, ch, fill="surface", fa=0.65, ln="line", lw=0.75, z=-5))
        objs.append(O(f"l{k}", "text", x + 0.14, y + 0.08, cw - 0.28, 0.3,
                      txt=f"{{a:{key}}}  {{m:{DESC.get(key, '')}}}", sz=11, font="mono", z=2))
        delay = start + step * k
        sx, sy, sw, sh = x + 0.15, y + 0.42, cw - 0.3, ch - 0.55
        if sk == "nums":  # четыре числа разного формата в одной ячейке
            for j, v in enumerate(["6 497", "0,541", "−0,035", "76 %"]):
                n = f"s{k}_{j}"
                objs += sample("word", n, sx + (j % 2) * sw / 2, sy + (j // 2) * sh / 2, sw / 2, sh / 2, v, z=3)
                fx.append({"key": key, "target": n, "delay": delay + 0.06 * j, "dur": d or 1.4, "options": opts or {}})
            continue
        objs += sample(sk, f"s{k}", sx, sy, sw, sh, txt, z=3)
        f = {"key": key, "target": f"s{k}", "delay": delay, "dur": d or dur, "options": opts or {}}
        if rep:
            f["repeat"] = True
        fx.append(f)
    return objs, fx


IN1 = [("in.stamp", "stamp", "Принято", None, 0.5), ("in.registration", "big", "Краска"),
       ("in.write", "para", "Текст пишется\nстрока за строкой", None, 1.4), ("in.type", "mono", "> обучение модели…", None, 1.5),
       ("in.scramble", "acc", "РАСШИФРОВКА", None, 1.4), ("in.count", "nums", ""),
       ("in.highlight", "para", "главное —\nвыделено маркером", None, 1.2), ("in.ink", "big", "Тушь", None, 1.1),
       ("in.blur", "big", "Фокус"), ("in.glitch", "acc", "СБОЙ СИГНАЛА", None, 1.0),
       ("in.reveal-r", "word", "Шторка вправо"), ("in.iris", "big", "Из центра", None, 1.0)]
IN2 = [("in.elastic", "card", "Готово", None, 1.1), ("in.back", "card", "С перелётом"), ("in.bounce", "disc", "мяч", None, 1.1),
       ("in.drop", "card", "Падение", {"amount": 1.1}, 1.0), ("in.pop", "disc", "+1", None, 0.6),
       ("in.flip", "card", "Карточка"), ("in.unfold", "card", "Свиток"), ("in.zoom", "word", "Ближе"),
       ("in.zoom-out", "word", "Из большого"), ("in.spin", "tile", "винт", None, 1.0),
       ("in.swing", "sign", "Открыто", None, 1.6), ("in.fade", "word", "Проявление")]
IN3 = [("in.slide-l", "card", "← влево"), ("in.slide-r", "card", "вправо →"), ("in.slide-u", "card", "↑ вверх"),
       ("in.slide-d", "card", "↓ вниз"), ("in.rise", "word", "Всплытие"), ("in.reveal-l", "word", "← Шторка"),
       ("in.reveal-u", "word", "Шторка вверх"), ("in.reveal-d", "word", "Шторка вниз"),
       ("in.reveal-r", "bar", "", None, 1.0), ("in.iris", "disc", "круг"),
       ("in.write", "line", "Подпись от руки", None, 0.9), ("in.type", "mono", "печать блоком", {"cursor": "▌"}, 1.2)]
IN4 = [("in.letters", "big", "Буквы встают по одной", None, 1.4), ("in.wave-letters", "big", "Волна проходит по буквам", None, 1.5),
       ("in.split-letters", "big", "Буквы слетаются", None, 1.4), ("in.words", "big", "Слова приходят по одному", None, 1.5),
       ("in.rain-letters", "big", "Капли букв", None, 1.4), ("in.pop-letters", "big", "Каждая выскакивает", None, 1.3)]
EM1 = [("em.pulse", "card", "Пульс"), ("em.shake", "bad", "Ошибка!", None, 0.7), ("em.wobble", "card", "Вихляние", None, 1.0),
       ("em.jello", "disc", "желе", None, 1.0), ("em.heartbeat", "disc", "76", None, 1.3), ("em.glow", "card", "Свет", None, 1.2),
       ("em.flash", "acc", "Внимание", None, 1.0), ("em.tada", "card", "Победа", None, 1.0),
       ("em.float", "disc", "∞", None, 2.0, True), ("em.swing", "sign", "Качели", None, 1.0),
       ("em.rubber", "card", "Резинка", None, 1.0), ("em.jump", "disc", "прыг", None, 0.8)]
EM2 = [("em.color", "word", "Перекрасить"), ("em.dim", "word", "Приглушить"),
       ("em.wave", "word", "Волна по буквам", {"color": "accent"}, 1.3, True), ("em.grow", "card", "Крупнее"),
       ("em.spin", "tile", "оборот", None, 1.0), ("em.reg", "big", "Краска", None, 0.8),
       ("em.glitch", "acc", "ПОМЕХИ", None, 0.8), ("em.mark", "para", "это — главное\nна слайде", None, 0.9)]
OUT1 = [("out.fade", "word", "Растворение"), ("out.zoom", "word", "На зрителя"), ("out.drop", "card", "Падение", None, 1.0),
        ("out.slide-l", "card", "← влево"), ("out.slide-r", "card", "вправо →"), ("out.slide-u", "card", "↑ вверх"),
        ("out.slide-d", "card", "↓ вниз"), ("out.blur", "big", "Размытие"), ("out.shrink", "disc", "точка"),
        ("out.burn", "big", "Выгорание", None, 1.1), ("out.flip", "card", "Переворот"), ("out.fold", "card", "Складка")]
OUT2 = [("out.spin", "tile", "винт"), ("out.erase-l", "word", "← Стирание"), ("out.erase-r", "word", "Стирание →"),
        ("out.erase-u", "word", "Стирание ↑"), ("out.erase-d", "word", "Стирание ↓"), ("out.type", "mono", "> удалить строку", None, 1.2),
        ("out.glitch", "acc", "СБОЙ", None, 0.9), ("out.ink", "big", "Тушь"), ("out.words", "word", "Слова уходят", None, 1.3),
        ("out.letters", "word", "Буквы падают", None, 1.3), ("out.scatter-letters", "word", "Разлёт букв", None, 1.2),
        ("out.erase-r", "bar", "")]

# перелив: одно и то же имя — разный текст на соседних слайдах
MORPH = [  # (имя, x, y, w, h, кегль, жирный, тексты по слайдам, подпись)
    ("!!mw1", 0.6, 1.9, 6.0, 0.8, 40, True, ["Нейросеть", "Сеть нейронов", "Нейроны в сети"], "буквы: общие едут"),
    ("!!mw2", 0.6, 3.15, 6.0, 0.7, 30, False, ["морфинг текста", "текст морфинга", "морфинг ткани"], "перестановка слов"),
    ("!!mw3", 0.6, 4.3, 6.0, 0.95, 22, False, ["Данные → модель\nмодель → ответ", "Модель → ответ\nответ → решение",
                                              "Решение → данные\nданные → модель"], "две строки: буквы между строк"),
    ("!!mp", 0.6, 5.65, 6.0, 1.3, 15, False,
     ["Длинный абзац уходит целиком: сначала старый\nтекст растворяется, затем приходит новый —\nбез каши из сотни летящих букв.",
      "Другой абзац о другом. Когда общих букв мало\nили строк больше четырёх, перелив идёт\nпоочерёдным растворением.",
      "Третий вариант абзаца: снова поочерёдно,\nкаждая строка на своём месте."], "абзац: поочерёдно"),
    ("!!mn1", 7.4, 1.9, 2.6, 0.8, 40, True, ["6 497", "7 210", "12 480"], "целое с разрядами"),
    ("!!mn2", 10.2, 1.9, 2.6, 0.8, 40, True, ["0,541", "0,612", "0,598"], "дробь, 3 знака"),
    ("!!mn3", 7.4, 3.15, 2.6, 0.8, 40, True, ["−0,035", "+0,012", "−0,004"], "знак меняется"),
    ("!!mn4", 10.2, 3.15, 2.6, 0.8, 40, True, ["76 %", "91 %", "64 %"], "проценты"),
    ("!!mn5", 7.4, 4.4, 5.4, 0.8, 30, False, ["Точность 76 % · MAE 0,58", "Точность 91 % · MAE 0,41",
                                               "Точность 64 % · MAE 0,73"], "числа внутри фразы"),
    ("!!mn6", 7.4, 5.65, 5.4, 0.8, 30, False, ["шаг 03 из 12", "шаг 07 из 12", "шаг 12 из 12"], "ведущие нули"),
]


def morph_slide(i: int) -> list[O]:
    objs = []
    for n, x, y, w, h, sz, b, texts, cap in MORPH:
        objs.append(O(n, "text", x, y, w, h, txt=texts[i], sz=sz, b=b, font="head", va="m",
                      col="accent" if n.startswith("!!mn") and n != "!!mn5" and n != "!!mn6" else "ink",
                      meta={"morph_text": True}))
        objs.append(O(n.replace("!!", "cap_"), "text", x, y - 0.3, w, 0.28, txt=cap, sz=11, font="mono", col="muted"))
    return objs


def slides() -> tuple[list[Slide], list[str]]:
    total = 12
    out: list[Slide] = []

    def show(k, kicker, title, cells, cols, rows, sec=1, **kw):
        objs, fx = grid(cells, cols, rows, **kw)
        s = Slide(header(k, total, kicker, title) + objs, title=title, dur=600)
        web(s, sec=sec, fx=fx)
        return s

    # 1 — обложка
    n_fx = len({c[0] for c in IN1 + IN2 + IN3 + IN4 + EM1 + EM2 + OUT1 + OUT2})
    cover = header(1, total, "deckcraft 0.3.0 · web", "Эффекты и текст") + [
        O("!!big", "text", X0, 2.0, 9.0, 1.4, txt="Сдвиг краски, печать,\nсчётчики и перелив", sz=44, b=True, font="head"),
        O("sub", "text", X0, 3.9, 8.5, 0.5, txt="> fx.js: входы, выделения, выходы и побуквенные рендеры", sz=18,
          font="mono", col="ink2"),
        O("num", "text", X0, 4.8, 3.2, 1.0, txt=f"{n_fx}", sz=60, b=True, font="head", col="accent"),
        O("numc", "text", X0 + 2.0, 5.05, 4.0, 0.6, txt="эффектов в витрине", sz=18, col="muted"),
        O("stamp", "rrect", 9.6, 2.2, 2.6, 0.9, ln="accent", lw=3, txt="ГОТОВО", sz=30, b=True, col="accent", al="c",
          va="m", tracking=3, rot=-7, radius=0.1),
        O("mark", "text", 8.9, 4.75, 4.0, 1.0, txt="каждый эффект подписан\nсвоим ключом", sz=20, al="l", va="m"),
    ]
    s = Slide(cover, title="Эффекты и текст", dur=600)
    web(s, sec=0, fx=[{"key": "in.registration", "target": "!!big", "delay": 0.1, "dur": 0.9},
                      {"key": "in.type", "target": "sub", "delay": 0.6, "dur": 1.4},
                      {"key": "in.count", "target": "num", "delay": 0.9, "dur": 1.3},
                      {"key": "in.fade", "target": "numc", "delay": 1.4, "dur": 0.5},
                      {"key": "in.stamp", "target": "stamp", "delay": 1.8, "dur": 0.45},
                      {"key": "in.highlight", "target": "mark", "delay": 2.3, "dur": 1.0}])
    out.append(s)
    out.append(show(2, "входы · 1 / 4", "Бумага и печать", IN1, 4, 3))
    out.append(show(3, "входы · 2 / 4", "Пружины и физика", IN2, 4, 3))
    out.append(show(4, "входы · 3 / 4", "Сдвиги и шторки", IN3, 4, 3))
    out.append(show(5, "входы · 4 / 4", "Побуквенно", IN4, 2, 3, step=0.45, dur=1.3))
    out.append(show(6, "выделения · 1 / 2", "Движение", EM1, 4, 3, sec=2))
    out.append(show(7, "выделения · 2 / 2", "Цвет и текст", EM2, 4, 2, sec=2, step=0.35))
    for i in range(3):
        objs = header(8 + i, total, f"перелив · {['было', 'стало', 'ещё раз'][i]}", ["Перелив текста и чисел",
                      "Перелив чисел и текста", "Перелив: третий шаг"][i]) + morph_slide(i)
        s = Slide(objs, title=f"перелив {i + 1}", dur=1600)
        web(s, sec=3)
        out.append(s)
    out.append(show(11, "выходы · 1 / 2", "Уход со сцены", OUT1, 4, 3, sec=4))
    out.append(show(12, "выходы · 2 / 2", "Стирание и разлёт", OUT2, 4, 3, sec=4))
    return out, ["Обложка", "Входы", "Выделения", "Перелив", "Выходы"]


def main(argv: list[str]) -> int:
    from .webdemo import build, shots
    args = [a for a in argv if not a.startswith("--")]
    out = Path(args[0] if args else "demo_fx")
    out.mkdir(parents=True, exist_ok=True)
    ss, secs = slides()
    kw = {} if "--all" in argv else {"modules": ["fx"]}
    path = build(ss, out / "demo_fx.html", sections=secs, title="deckcraft · эффекты и текст", **kw)
    print("html:", path)
    if "--no-shots" in argv:
        return 0
    r = shots(path, out, times=[0.6, 1.4, 2.4, 3.6, 6.5])
    print("кадров:", len(r["files"]), "лист:", r["sheet"])
    print("ошибок консоли:", len(r["errors"]))
    for e in r["errors"]:
        print("  ", e)
    return 1 if r["errors"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
