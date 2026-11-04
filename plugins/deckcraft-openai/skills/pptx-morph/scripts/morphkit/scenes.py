"""Живые сцены web-движка deckcraft 0.3.0: конструкторы словарей для `web(slide, scenes=[...])`.

    from morphkit.html import web
    from morphkit import scenes as SC
    web(slide, scenes=[SC.liquid("!!q0", level_to=0.7, character="lively"),
                       SC.pour(from_obj="!!bot", to_obj="!!q0", delay=0.3),
                       SC.counter("!!big", character="dramatic")])

Каждая функция проверяет параметры (ValueError с объяснением по-русски) и возвращает dict `{"k": вид, ...}`, который
исполняет `morphkit/web/scenes.js` (`DC.scenes[вид]`). Сцены — только для HTML: в .pptx их нет (там остаётся
статичный слайд — финальный или исходный кадр, см. описание каждой сцены).

Единицы: координаты и размеры — в **дюймах** слайда 13,333 × 7,5 (как у O), в словарь уходят px (1 дюйм = 120 px,
`"units": "px"`); кегль — в pt; время — в секундах после конца перехода к слайду (как `Fx.delay`: отсчёт от
`FX_START`). Цвета — роли темы (`"accent"`, `"red_wine"`, …) или `#hex`/`hex`: роли переводит `html.py`
(и запасной путь — сам JS).

Общие параметры всех сцен:
    character — "calm" | "lively" | "dramatic": скорость, амплитуда, плотность и перелёт (спокойно / живо / драматично);
    delay     — задержка старта, с;   step — номер клика (steps слайда), с которого сцена начинается;
    seed      — зерно случайности (всё детерминировано);   layer — "over" (поверх объектов) | "under" (под ними).

Объекты слайда задаются именами (`"!!q0"`): бокал Glass — по корню имени (`"!!q0"` → `!!q0_body`, `!!q0_lq0`, …,
`!!q0_srf`, `!!q0_hl`). Текстовые пары с изменённым текстом политика текста переименовывает в `!!x~k` — сцены находят
их по исходному имени сами.

Совместимость: JS понимает и сырые словари (сгенерированные вручную в генераторе презентации) — `start` вместо `delay`, координаты в
дюймах (распознаются, если все числа точек и рамок ≤ 14), синонимы `layout`/`groups`/`targets` у particles,
`min`/`max`/`band`/`zero`/`fmt`-образец у gauge, `opacity` у grain.
"""

from __future__ import annotations

import math
import re
from typing import Iterable, Sequence

PX = 120.0  # px на дюйм (сцена 1600 × 900 = 13,333 × 7,5 дюйма)
PT = 120.0 / 72.0  # px на pt
CHARACTERS = ("calm", "lively", "dramatic")
LAYERS = ("over", "under")
EASES = ("linear", "inOut", "out", "in", "back", "elastic", "spring", "bounce")
LAYOUTS = ("cloud", "clusters", "grid", "groups", "bars", "into")
FIELDS = ("radial", "linear", "wave", "ring")
MAX_PARTICLES = 6000

__all__ = ["liquid", "pour", "pour_into", "bubbles", "drip", "stain", "particles", "phase", "signal", "counter", "clock",
           "gauge", "terminal", "sparks", "confetti", "ripple", "grain", "halftone", "chart_draw", "bars_grow",
           "CHARACTERS", "SCENES"]


# ------------------------------------------------------------------------------ проверки и перевод единиц
def _err(kind: str, msg: str):
    raise ValueError(f"сцена {kind}: {msg}")


def _num(kind, name, v, lo=None, hi=None, allow_none=False):
    if v is None:
        if allow_none:
            return None
        _err(kind, f"{name} обязателен")
    if isinstance(v, bool) or not isinstance(v, (int, float)) or math.isnan(v):
        _err(kind, f"{name} должен быть числом, получено {v!r}")
    if lo is not None and v < lo:
        _err(kind, f"{name} = {v} меньше допустимого {lo}")
    if hi is not None and v > hi:
        _err(kind, f"{name} = {v} больше допустимого {hi}")
    return float(v)


def _r(v: float, nd: int = 2) -> float:
    return round(float(v), nd)


def _pt(kind, name, p, allow_name=True):
    """Точка (x, y) в дюймах → [px, px]; строка — имя объекта (если разрешено)."""
    if isinstance(p, str):
        if not allow_name:
            _err(kind, f"{name}: нужна точка (x, y) в дюймах, а не имя")
        return _name(kind, name, p)
    if not isinstance(p, (list, tuple)) or len(p) != 2:
        _err(kind, f"{name}: нужна точка (x, y) в дюймах или имя объекта, получено {p!r}")
    x, y = (_num(kind, name, v) for v in p)
    if not (-3 <= x <= 16.5 and -3 <= y <= 10.5):
        _err(kind, f"{name} = {p!r} далеко за слайдом 13,333 × 7,5 дюйма (координаты — в дюймах)")
    return [_r(x * PX, 1), _r(y * PX, 1)]


def _box(kind, name, b, allow_name=False):
    if isinstance(b, str) and allow_name:
        return _name(kind, name, b)
    if not isinstance(b, (list, tuple)) or len(b) != 4:
        _err(kind, f"{name}: нужна рамка (x, y, w, h) в дюймах, получено {b!r}")
    x, y, w, h = (_num(kind, name, v) for v in b)
    if w <= 0 or h <= 0:
        _err(kind, f"{name}: ширина и высота должны быть > 0")
    return [_r(x * PX, 1), _r(y * PX, 1), _r(w * PX, 1), _r(h * PX, 1)]


def _name(kind, name, v):
    if not isinstance(v, str) or not v:
        _err(kind, f"{name}: нужно имя объекта слайда, получено {v!r}")
    return v


def _color(kind, name, c):
    if c is None:
        return None
    if not isinstance(c, str) or not c:
        _err(kind, f"{name}: цвет — роль темы или hex, получено {c!r}")
    if re.fullmatch(r"[0-9a-fA-F]{6}", c):
        return "#" + c
    if c.startswith("#") and not re.fullmatch(r"#[0-9a-fA-F]{6}", c):
        _err(kind, f"{name}: неверный hex {c!r}")
    return c


def _colors(kind, name, cs):
    if cs is None:
        return None
    if isinstance(cs, str):
        cs = [cs]
    return [_color(kind, name, c) for c in cs]


def _choice(kind, name, v, options):
    if v not in options:
        _err(kind, f"{name} = {v!r}; допустимо: {', '.join(map(str, options))}")
    return v


def _base(kind: str, character: str, delay: float, seed: int, step: int | None, layer: str, **extra) -> dict:
    d = {"k": kind, "units": "px", "character": _choice(kind, "character", character, CHARACTERS),
         "delay": _r(_num(kind, "delay", delay, 0, 600), 3), "seed": int(seed), "layer": _choice(kind, "layer", layer, LAYERS)}
    if step is not None:
        if not isinstance(step, int) or step < 0:
            _err(kind, f"step — номер клика ≥ 0, получено {step!r}")
        d["step"] = step
    for k, v in extra.items():
        if v is not None:
            d[k] = v
    return d


def _gid(kind, glass):
    g = _name(kind, "glass", glass)
    return g if g.startswith("!!") else "!!" + g


# ------------------------------------------------------------------------------ 1. вино, струя, пузырьки, капли, пятно
def liquid(glass: str, level_from: float | None = None, level_to: float | None = None, *, delay: float = 0.0,
           dur: float = 1.2, ease: str = "inOut", character: str = "lively", waves: bool = True, bubbles: bool = True,
           shimmer: bool = True, foam: bool = True, n_bubbles: int | None = None, kick: float = 1.0, amp: float = 1.0,
           layer_index: int | None = None, bubble_color: str | None = None, seed: int = 1, step: int | None = None,
           layer: str = "over") -> dict:
    """Живое вино в бокале Glass: поверхность колышется (синус с затуханием после перехода и после налива, мелкая
    рябь всегда), пузырьки поднимаются со дна и лопаются у поверхности, блик `_hl` дрожит, на поверхности бегает
    искра; при изменении уровня — пена. Контур верхнего слоя `!!{glass}_lq{i}` пересчитывается каждый кадр по
    горизонтальному срезу чаши (ниже статичной поверхности — по слоям вина, выше — по силуэту `_body` минус стенка),
    эллипс `_srf` едет с поверхностью и наклоняется с волной; наклонённый бокал тоже работает (поверхность
    горизонтальна).

    level_from / level_to — доли объёма чаши 0..1 (как Glass(level=…)); None — статичный уровень слайда.
    **Статичный уровень бокала на слайде должен равняться level_from** — тогда приход Morph и начало сцены совпадают
    (ядро во время Morph модификаторы не применяет). dur/ease — налив; kick — сила «толчка» после перехода (0 — без);
    amp — общий множитель волн; layer_index — какой слой вина менять (по умолчанию верхний ненулевой).
    character: calm — тихая рябь и редкие пузырьки; lively — заметное колыхание; dramatic — сильный плеск, много пены.
    """
    k = "liquid"
    for nm, v in (("level_from", level_from), ("level_to", level_to)):
        if v is not None:
            _num(k, nm, v, 0.0, 1.0)
    return _base(k, character, delay, seed, step, layer, glass=_gid(k, glass),
                 level_from=None if level_from is None else _r(level_from, 4),
                 level_to=None if level_to is None else _r(level_to, 4),
                 dur=_r(_num(k, "dur", dur, 0.05, 60), 3), ease=_choice(k, "ease", ease, EASES), waves=bool(waves),
                 bubbles=bool(bubbles), shimmer=bool(shimmer), foam=bool(foam),
                 n_bubbles=None if n_bubbles is None else int(_num(k, "n_bubbles", n_bubbles, 0, 80)),
                 kick=_r(_num(k, "kick", kick, 0, 5), 3), amp=_r(_num(k, "amp", amp, 0, 5), 3),
                 layer_index=None if layer_index is None else int(_num(k, "layer_index", layer_index, 0, 40)),
                 bubble_color=_color(k, "bubble_color", bubble_color))


def pour(src: Sequence[float] | None = None, dst: Sequence[float] | None = None, *, from_obj: str | None = None,
         to_obj: str | None = None, delay: float = 0.0, dur: float = 1.6, width: float = 0.07, color: str = "red_wine",
         bend: float = 1.0, drops: bool = True, splash: bool = True, character: str = "lively", seed: int = 1,
         step: int | None = None, layer: str = "over") -> dict:
    """Струя из точки A в точку B: голова падает с ускорением, толщина колышется бегущей волной (струя сужается
    к низу), по краям отрываются капли, у поверхности — брызги по параболам и круги; после dur хвост отрывается
    от источника и падает, следом — последние капли.

    src/dst — точки (x, y) в дюймах; from_obj — объект-источник (бутылка, наклонённый бокал: край — верх контура
    в рамке объекта, самая низкая точка после поворота); to_obj — бокал (`"!!q0"`: струя бьёт в поверхность вина и
    следует за ней, если на бокале есть liquid; поверхность получает рябь от удара) или любой объект.
    width — толщина у источника, дюймы; bend — насколько струя «вылетает» вбок (0 — сразу вниз).
    Статичный слайд струи не содержит: в .pptx можно оставить ленту-штрих с входом «вытирание».
    """
    k = "pour"
    if src is None and from_obj is None:
        _err(k, "нужен src (точка) или from_obj (имя)")
    if dst is None and to_obj is None:
        _err(k, "нужен dst (точка) или to_obj (имя)")
    return _base(k, character, delay, seed, step, layer,
                 **{"from": None if src is None else _pt(k, "src", src, False),
                    "to": None if dst is None else _pt(k, "dst", dst, False)},
                 from_obj=None if from_obj is None else _name(k, "from_obj", from_obj),
                 to_obj=None if to_obj is None else _name(k, "to_obj", to_obj),
                 dur=_r(_num(k, "dur", dur, 0.2, 60), 3), width=_r(_num(k, "width", width, 0.01, 0.6) * PX, 2),
                 color=_color(k, "color", color), bend=_r(_num(k, "bend", bend, 0, 1.2), 3), drops=bool(drops),
                 splash=bool(splash))


def pour_into(glass: str, *, from_obj: str | None = None, src: Sequence[float] | None = None,
              level_from: float | None = None, level_to: float, delay: float = 0.0, dur: float = 1.6,
              character: str = "lively", color: str | None = None, width: float = 0.07, seed: int = 1,
              step: int | None = None) -> list[dict]:
    """Налить бокал: струя (pour) + подъём уровня (liquid) с согласованным временем — уровень начинает расти,
    когда струя долетела, и останавливается, когда она оборвалась. Возвращает список из двух сцен:
    `web(s, scenes=pour_into("!!q0", from_obj="!!bot", level_from=0.1, level_to=0.6))`."""
    g = _gid("pour_into", glass)
    lead = 0.3
    return [pour(src, None, from_obj=from_obj, to_obj=g, delay=delay, dur=dur, width=width,
                 color=color or "red_wine", character=character, seed=seed, step=step),
            liquid(g, level_from, level_to, delay=delay + lead, dur=max(0.2, dur), ease="inOut", character=character,
                   seed=seed + 1, step=step)]


def bubbles(area: Sequence[float] | None = None, *, obj: str | None = None, n: int | None = None, size: float = 1.0,
            speed: float = 1.0, color: str = "#ffffff", clip: bool = True, delay: float = 0.0,
            character: str = "lively", seed: int = 1, step: int | None = None, layer: str = "over") -> dict:
    """Пузырьки поднимаются в области (рамка в дюймах) или внутри объекта: obj — бокал (`"!!q0"`: обрезка по вину,
    верх — живая поверхность) или фигура (обрезка по её контуру при clip=True). n — число (по умолчанию по площади),
    size/speed — множители. calm — редкие и медленные, dramatic — густые и быстрые."""
    k = "bubbles"
    if area is None and obj is None:
        _err(k, "нужна area (x, y, w, h) или obj (имя)")
    return _base(k, character, delay, seed, step, layer, area=None if area is None else _box(k, "area", area),
                 obj=None if obj is None else _name(k, "obj", obj),
                 n=None if n is None else int(_num(k, "n", n, 1, 300)), size=_r(_num(k, "size", size, 0.2, 5), 3),
                 speed=_r(_num(k, "speed", speed, 0.1, 5), 3), color=_color(k, "color", color), clip=bool(clip))


def drip(at: Sequence | None = None, *, obj: str | None = None, n: int = 1, period: float = 1.8, size: float = 0.045,
         floor: float | None = None, color: str = "red_wine", delay: float = 0.0, character: str = "lively",
         seed: int = 1, step: int | None = None, layer: str = "over") -> dict:
    """Капли с края: капля набухает и вытягивается, отрывается (остаётся хвостик), падает с ускорением и
    растягивается, на полу — клякса и мелкие брызги; цикл повторяется с периодом period (у источников — сдвиг фазы).
    at — точка или список точек (дюймы); obj — объект, капли с нижнего края (n штук вдоль края).
    floor — высота пола, дюймы (по умолчанию на 1,33 дюйма ниже края); size — радиус капли, дюймы."""
    k = "drip"
    if at is None and obj is None:
        _err(k, "нужна точка at или объект obj")
    pts = None
    if at is not None:
        pts = [_pt(k, "at", q, False) for q in at] if at and isinstance(at[0], (list, tuple)) else _pt(k, "at", at, False)
    return _base(k, character, delay, seed, step, layer, at=pts, obj=None if obj is None else _name(k, "obj", obj),
                 n=int(_num(k, "n", n, 1, 12)), period=_r(_num(k, "period", period, 0.4, 20), 3),
                 size=_r(_num(k, "size", size, 0.01, 0.3) * PX, 2),
                 floor=None if floor is None else _r(_num(k, "floor", floor, 0, 7.5) * PX, 1),
                 color=_color(k, "color", color))


def stain(at: Sequence[float] | None = None, r: float = 0.45, *, obj: str | None = None, color: str = "red_wine",
          delay: float = 0.0, dur: float = 1.4, dry: float | None = None, squash: float = 1.0,
          character: str = "lively", seed: int = 1, step: int | None = None, layer: str = "under") -> dict:
    """Пятно растекается (неровный край из гармоник, растекание замедляется, край «ползёт») и подсыхает: середина
    бледнеет, по краю проступает тёмное кольцо (эффект кофейного кольца). dramatic — с брызгами-спутниками.
    at, r — центр и радиус, дюймы; dry — начало подсыхания, с (по умолчанию dur + 1,2); squash — сжатие по вертикали
    (0,4 — пятно на столе в перспективе). obj — растекается сам объект слайда (например Stain `!!st` и `!!st_in`):
    растёт от центра и бледнеет."""
    k = "stain"
    if at is None and obj is None:
        _err(k, "нужна точка at или объект obj")
    return _base(k, character, delay, seed, step, layer, at=None if at is None else _pt(k, "at", at, False),
                 r=_r(_num(k, "r", r, 0.02, 6) * PX, 1), obj=None if obj is None else _name(k, "obj", obj),
                 color=_color(k, "color", color), dur=_r(_num(k, "dur", dur, 0.1, 30), 3),
                 dry=None if dry is None else _r(_num(k, "dry", dry, 0, 120), 3),
                 squash=_r(_num(k, "squash", squash, 0.1, 1.5), 3))


# ------------------------------------------------------------------------------ 4. поле частиц
def phase(kind: str, at: float, dur: float = 1.0, stagger: float | None = None, ease: str = "inOut") -> dict:
    """Раскладка поля частиц в момент at (с): cloud (облако), clusters (облака по группам), grid (сетка-«вафля»,
    группы подряд), groups (диски-группы, площадь ∝ доле), bars (столбики гистограммы из точек), into (точки
    «стекают» в объекты link_to — бокалы — и исчезают у поверхности). dur — длительность перехода каждой точки,
    stagger — разброс старта (очередь), с."""
    k = "particles"
    d = {"kind": _choice(k, "phase.kind", kind, LAYOUTS), "at": _r(_num(k, "phase.at", at, 0, 600), 3),
         "dur": _r(_num(k, "phase.dur", dur, 0.05, 30), 3), "ease": _choice(k, "phase.ease", ease, EASES)}
    if stagger is not None:
        d["stagger"] = _r(_num(k, "phase.stagger", stagger, 0, 30), 3)
    return d


def particles(n: int, area: Sequence[float], layouts: Iterable, *, shares: Sequence[float] | None = None,
              colors: Sequence[str] | None = None, link_to: Sequence[str] | None = None, labels: Sequence[str] | None = None,
              counts: bool = True, size: float | None = None, delay: float = 0.0, character: str = "lively", seed: int = 1,
              step: int | None = None, layer: str = "over") -> dict:
    """Поле из n точек (до 6000, canvas) в рамке area, переходящее между раскладками. layouts — список phase(...),
    кортежей (kind, at[, dur]) или строк (тогда смена каждые 1,45 с). shares — доли групп (цвета colors по порядку);
    link_to — бокалы/объекты для раскладки into (группа i стекает в link_to[i % len]); labels — подписи групп
    (в groups и bars; под подписью — значение доли, если counts=True: счёт, если shares даны счётом
    (1599, 4898), иначе процент); size — радиус точки, дюймы (по умолчанию по плотности).
    Переход: каждая точка летит по дуге со своим изгибом; очередь — calm: случайно, lively: слева направо,
    dramatic: от центра; в покое точки слегка дышат."""
    k = "particles"
    nn = int(_num(k, "n", n, 1, MAX_PARTICLES))
    ph = []
    for i, q in enumerate(layouts):
        if isinstance(q, str):
            ph.append(phase(q, i * 1.45))
        elif isinstance(q, dict):
            ph.append(phase(**q))
        elif isinstance(q, (list, tuple)):
            ph.append(phase(*q))
        else:
            _err(k, f"раскладка {q!r}: phase(...), (kind, at) или строка")
    if not ph:
        _err(k, "нужна хотя бы одна раскладка")
    if any(q["kind"] == "into" for q in ph) and not link_to:
        _err(k, "раскладка into требует link_to (бокалы или объекты)")
    sh = None
    if shares is not None:
        sh = [_r(_num(k, "shares", v, 0), 5) for v in shares]
        if not sum(sh):
            _err(k, "сумма shares должна быть > 0")
    if labels is not None and sh is not None and len(labels) != len(sh):
        _err(k, "labels — по одной подписи на группу shares")
    return _base(k, character, delay, seed, step, layer, n=nn, area=_box(k, "area", area), layouts=ph, shares=sh,
                 colors=_colors(k, "colors", colors), link_to=[_name(k, "link_to", v) for v in link_to] if link_to else None,
                 labels=[{"t": str(t)} for t in labels] if labels else None, counts=bool(counts),
                 size=None if size is None else _r(_num(k, "size", size, 0.003, 0.1) * PX, 2))


# ------------------------------------------------------------------------------ 5–6. сигнал, счётчик
def signal(layers: Sequence[Sequence], *, edges="auto", hop: float = 0.55, repeat: float | None = None,
           color: str = "accent", active: str | None = None, out: Sequence | None = None,
           out_box: Sequence[float] | None = None, out_decimals: int | None = None, out_suffix: str = "",
           out_text: str | None = None, out_value: float | None = None, max_edges: int = 140, delay: float = 0.0,
           character: str = "lively", seed: int = 1, step: int | None = None, layer: str = "over") -> dict:
    """Сигнал по сети: импульсы с хвостом бегут по рёбрам слой за слоем (у каждого ребра свой небольшой сдвиг),
    узел вспыхивает при приходе импульса (подсветка цветом active, рост, свечение), активный слой подсвечен полосой;
    когда импульс доходит до выхода — растут столбики out и/или число в тексте out_text.

    layers — слои узлов: имена объектов или точки (x, y) в дюймах. edges: "auto" — линии слайда, соединяющие узлы
    соседних слоёв (например, линии `nl{a}_{b}`), иначе полный граф с ограничением max_edges; "full"; или список пар имён.
    hop — время перехода между слоями, с; repeat — период повтора импульсов, с (None — один проход).
    out — столбики у выхода: [(подпись, значение[, цвет]), …] в рамке out_box (дюймы)."""
    k = "signal"
    if len(layers) < 2:
        _err(k, "нужно не меньше двух слоёв узлов")
    L = [[(_pt(k, "layers", n, False) if not isinstance(n, str) else _name(k, "layers", n)) for n in lay] for lay in layers]
    if any(not lay for lay in L):
        _err(k, "пустой слой")
    if isinstance(edges, str):
        _choice(k, "edges", edges, ("auto", "full"))
        e = edges
    else:
        e = [[_name(k, "edges", a), _name(k, "edges", b)] for a, b in edges]
    o = None
    if out:
        if out_box is None:
            _err(k, "для out нужна рамка out_box")
        items = []
        for it in out:
            lab, v = it[0], _num(k, "out", it[1])
            items.append({"label": str(lab), "v": _r(v, 6), **({"c": _color(k, "out", it[2])} if len(it) > 2 else {})})
        fmt = {"suf": out_suffix}
        if out_decimals is not None:
            fmt["dec"] = int(out_decimals)
        o = {"box": _box(k, "out_box", out_box), "items": items, "fmt": fmt}
    return _base(k, character, delay, seed, step, layer, layers=L, edges=e, hop=_r(_num(k, "hop", hop, 0.1, 10), 3),
                 repeat=None if repeat is None else _r(_num(k, "repeat", repeat, 0.5, 120), 3),
                 color=_color(k, "color", color), active=_color(k, "active", active), out=o,
                 out_text=None if out_text is None else _name(k, "out_text", out_text),
                 out_value=None if out_value is None else _num(k, "out_value", out_value),
                 max_edges=int(_num(k, "max_edges", max_edges, 1, 2000)))


def counter(target: str, to: float | None = None, *, start: float = 0.0, delay: float = 0.0, dur: float = 1.2,
            decimals: int | None = None, ease: str | None = None, line: int | None = None, character: str = "lively",
            seed: int = 1, step: int | None = None) -> dict:
    """Число в текстовом объекте растёт от start до to (по умолчанию — число, написанное в объекте). Формат берётся
    из текста: «6 497» (разряды пробелом), «0,541» (запятая, знаки после неё), «−0,035» (типографский минус),
    «76 %» (всё вокруг числа сохраняется). Подменяется только первый числовой фрагмент (или в строке line).
    calm — плавно (inOut), lively — быстро к концу и короткий «щелчок» масштаба, dramatic — младшие разряды
    «перебираются» по пути, в конце — щелчок со свечением. Статичный слайд показывает итоговое число."""
    k = "counter"
    d = _base(k, character, delay, seed, step, "over", target=_name(k, "target", target),
              to=None if to is None else _num(k, "to", to), dur=_r(_num(k, "dur", dur, 0.05, 60), 3),
              decimals=None if decimals is None else int(_num(k, "decimals", decimals, 0, 8)),
              ease=None if ease is None else _choice(k, "ease", ease, EASES),
              line=None if line is None else int(_num(k, "line", line, 0, 100)))
    d["from"] = _num(k, "start", start)
    return d


# ------------------------------------------------------------------------------ 7–9. часы, шкала, терминал
def clock(at: Sequence[float], r: float = 0.95, *, hours: Sequence[float] = (0, 24), entries: Sequence = (),
          log_at: Sequence[float] | None = None, log_dy: float = 0.3, log_size: float = 13, mode: int = 24,
          delay: float = 0.0, dur: float = 4.0, color: str = "accent", face: str = "surface",
          character: str = "lively", seed: int = 1, step: int | None = None, layer: str = "over") -> dict:
    """Часы со стрелкой и журналом: стрелка идёт от hours[0] до hours[1] за dur секунд, за ней заливается
    сектор прошедшего времени, внизу цифровое время; записи журнала entries — (час, текст[, цвет]) — появляются,
    когда стрелка проходит их час (метка на циферблате закрашивается и даёт круг). mode — 24 или 12 часов.
    log_at — левый верх журнала (дюймы; по умолчанию справа от часов), log_dy — шаг строк, дюймы; log_size — pt.
    calm — плавный ход, lively — равномерный с подрагиванием, dramatic — разгон."""
    k = "clock"
    h0, h1 = (_num(k, "hours", v, 0, 48) for v in hours)
    if h1 <= h0:
        _err(k, "hours: конец должен быть позже начала")
    ent = []
    for e in entries:
        h = _num(k, "entries.час", e[0], h0, h1)
        ent.append({"h": _r(h, 4), "t": str(e[1]), **({"c": _color(k, "entries.цвет", e[2])} if len(e) > 2 else {})})
    log = {"dy": _r(log_dy * PX, 1), "size": _r(log_size * PT, 1)}
    if log_at is not None:
        log["at"] = _pt(k, "log_at", log_at, False)
    return _base(k, character, delay, seed, step, layer, at=_pt(k, "at", at, False), r=_r(_num(k, "r", r, 0.2, 4) * PX, 1),
                 hours=[h0, h1], entries=ent, log=log, mode=int(_choice(k, "mode", mode, (12, 24))),
                 dur=_r(_num(k, "dur", dur, 0.3, 120), 3), color=_color(k, "color", color), face=_color(k, "face", face))


def gauge(at: Sequence[float] | None = None, value: float = 0.5, *, box: Sequence[float] | None = None, r: float = 1.0,
          vmin: float = 0.0, vmax: float = 1.0, sweep: float = 240, zero: float | None = None,
          band: Sequence[float] | None = None, zones: Sequence | None = None, fmt: str | None = None,
          decimals: int | None = None, suffix: str = "", pct: bool = False, label: str | None = None,
          follow: bool = False, color: str = "accent", delay: float = 0.0, character: str = "lively", seed: int = 1,
          step: int | None = None, layer: str = "over") -> dict:
    """Дуговая шкала (по умолчанию 240°, разрыв внизу): стрелка доезжает до value с перелётом пружины
    (calm — почти без перелёта, lively — заметный, dramatic — сильный и дрожь в покое), за ней — заливка дуги от
    нуля (zero) или от vmin; в центре — число (монотонно, без перелёта; follow=True — показывает положение стрелки).
    at + r — центр и радиус (дюймы) или box — рамка (x, y, w, h). band — интервал (например 95 % ДИ) полосой у
    шкалы; zones — [(до_значения, цвет), …] тонкие дуги снаружи. Формат числа: fmt — образец («−0,035», «76 %»)
    или decimals + suffix; pct=True — доли показываются в процентах."""
    k = "gauge"
    if at is None and box is None:
        _err(k, "нужен центр at (+ r) или рамка box")
    lo, hi = _num(k, "vmin", vmin), _num(k, "vmax", vmax)
    if hi <= lo:
        _err(k, "vmax должен быть больше vmin")
    v = _num(k, "value", value)
    if not lo <= v <= hi:
        _err(k, f"value = {v} вне шкалы [{lo}; {hi}]")
    f = None
    if fmt is None:
        f = {"suf": suffix}
        if decimals is not None:
            f["dec"] = int(_num(k, "decimals", decimals, 0, 8))
    elif not isinstance(fmt, str) or not re.search(r"\d", fmt):
        _err(k, "fmt — строка-образец с числом, например «−0,035» или «76 %»")
    z = None
    if zones:
        z = [{"to": _num(k, "zones", q[0], lo, hi), "c": _color(k, "zones", q[1])} for q in zones]
    return _base(k, character, delay, seed, step, layer, at=None if at is None else _pt(k, "at", at, False),
                 box=None if box is None else _box(k, "box", box), r=_r(_num(k, "r", r, 0.2, 4) * PX, 1),
                 value=v, vmin=lo, vmax=hi, sweep=_num(k, "sweep", sweep, 60, 330),
                 zero=None if zero is None else _num(k, "zero", zero, lo, hi),
                 band=None if band is None else [_num(k, "band", band[0], lo, hi), _num(k, "band", band[1], lo, hi)],
                 zones=z, fmt=fmt if fmt is not None else f, pct=bool(pct) or None, label=label,
                 follow=bool(follow) or None, color=_color(k, "color", color))


def terminal(lines: Sequence, *, box: Sequence[float] | None = None, obj: str | None = None, fill: bool = False,
             delay: float = 0.0, cps: float = 34, size: float = 11, line_height: float = 1.5, chrome: bool = False,
             bg: str = "code_bg", ink: str = "code_ink", prompt: str = "accent2", character: str = "lively",
             seed: int = 1, step: int | None = None, layer: str = "over") -> dict:
    """Терминал: команды (строки, начинающиеся с «$ », «> », «# » или kind="cmd") печатаются посимвольно со
    скоростью cps знаков/с (lively — с человеческим разбросом и паузами на пробелах), вывод появляется строками;
    курсор-блок мигает; лишние строки уезжают вверх плавной прокруткой. lines — строки или (текст, цвет[, kind]) /
    {"t", "c", "kind", "pause"}; цвет — роль темы (на тёмном фоне тёмные роли автоматически осветляются).
    box — рамка в дюймах (рисуется свой фон bg) или obj — готовый прямоугольник слайда (фон его, fill=True — поверх
    свой). size — кегль, pt; chrome — три точки окна. dramatic — быстрее, строки вывода «вспыхивают» с помехой."""
    k = "terminal"
    if box is None and obj is None:
        _err(k, "нужна рамка box или объект obj")
    L = []
    for ln in lines:
        if isinstance(ln, str):
            L.append({"t": ln})
        elif isinstance(ln, dict):
            if "t" not in ln:
                _err(k, "строка-словарь должна иметь ключ t")
            L.append({kk: (_color(k, "c", vv) if kk == "c" else vv) for kk, vv in ln.items()})
        else:
            d = {"t": str(ln[0])}
            if len(ln) > 1 and ln[1]:
                d["c"] = _color(k, "c", ln[1])
            if len(ln) > 2:
                d["kind"] = _choice(k, "kind", ln[2], ("cmd", "out"))
            L.append(d)
    if not L:
        _err(k, "нет строк")
    return _base(k, character, delay, seed, step, layer, lines=L, box=None if box is None else _box(k, "box", box),
                 obj=None if obj is None else _name(k, "obj", obj), fill=bool(fill) or None,
                 cps=_r(_num(k, "cps", cps, 2, 400), 2), size=_r(_num(k, "size", size, 6, 40) * PT, 2),
                 lh=_r(_num(k, "line_height", line_height, 1, 3), 3), chrome=bool(chrome) or None,
                 bg=_color(k, "bg", bg), ink=_color(k, "ink", ink), prompt=_color(k, "prompt", prompt))


# ------------------------------------------------------------------------------ 10. искры, конфетти, круги
def sparks(at: Sequence[float] | str | None = None, *, n: int | None = None, colors: Sequence[str] | None = None,
           power: float = 3.5, life: float = 0.9, gravity: float = 4.3, cone: Sequence[float] | None = None,
           repeat: float | None = None, count: int | None = None, delay: float = 0.0, character: str = "lively",
           seed: int = 1, step: int | None = None, layer: str = "over") -> dict:
    """Вспышка искр у точки или объекта («вау»-момент): искры-штрихи разлетаются с сопротивлением воздуха и
    гравитацией, гаснут; у lively/dramatic — вспышка-ореол в центре. at — точка (дюймы) или имя объекта (центр).
    power — скорость, дюйм/с; gravity — дюйм/с²; cone — (направление°, ширина°), например (-90, 120) — вверх;
    repeat — период повтора, с (count — сколько раз)."""
    k = "sparks"
    if at is None:
        _err(k, "нужна точка или имя объекта at")
    return _base(k, character, delay, seed, step, layer, at=_pt(k, "at", at),
                 n=None if n is None else int(_num(k, "n", n, 1, 400)), colors=_colors(k, "colors", colors),
                 power=_r(_num(k, "power", power, 0.1, 30) * PX, 1), life=_r(_num(k, "life", life, 0.1, 10), 3),
                 gravity=_r(_num(k, "gravity", gravity, 0, 60) * PX, 1),
                 cone=None if cone is None else [_num(k, "cone", cone[0]), _num(k, "cone", cone[1], 1, 360)],
                 repeat=None if repeat is None else _r(_num(k, "repeat", repeat, 0.2, 60), 3),
                 count=None if count is None else int(_num(k, "count", count, 1, 100)))


def confetti(at: Sequence[float] | str | None = None, *, area: Sequence[float] | None = None, n: int | None = None,
             colors: Sequence[str] | None = None, power: float = 4.3, life: float = 3.2, delay: float = 0.0,
             character: str = "lively", seed: int = 1, step: int | None = None, layer: str = "over") -> dict:
    """Конфетти: залп из точки/объекта at (вверх веером, затем медленное падение с качанием и переворотами) или
    дождь в рамке area. power — скорость залпа, дюйм/с; life — время жизни, с."""
    k = "confetti"
    if at is None and area is None:
        _err(k, "нужна точка/объект at или рамка area")
    return _base(k, character, delay, seed, step, layer, at=None if at is None else _pt(k, "at", at),
                 area=None if area is None else _box(k, "area", area),
                 n=None if n is None else int(_num(k, "n", n, 1, 600)), colors=_colors(k, "colors", colors),
                 power=_r(_num(k, "power", power, 0.2, 30) * PX, 1), life=_r(_num(k, "life", life, 0.3, 20), 3))


def ripple(at: Sequence[float] | str | None = None, *, rings: int = 3, period: float = 1.6, count: int | None = None,
           r_max: float | None = None, squash: float | None = None, color: str = "accent", width: float = 2.2,
           delay: float = 0.0, character: str = "lively", seed: int = 1, step: int | None = None,
           layer: str = "over") -> dict:
    """Круги от точки: rings кругов одновременно, каждый расширяется с замедлением и гаснет за period. at — точка
    (дюймы) или объект; если at — бокал (`"!!q0"`), круги идут по поверхности вина (эллипсы, squash 0,2, радиус —
    по ширине поверхности). count — сколько кругов всего (None — до конца слайда); width — толщина, px."""
    k = "ripple"
    if at is None:
        _err(k, "нужна точка или имя объекта at")
    pt = _pt(k, "at", at)
    d = _base(k, character, delay, seed, step, layer, rings=int(_num(k, "rings", rings, 1, 12)),
              period=_r(_num(k, "period", period, 0.2, 30), 3),
              count=None if count is None else int(_num(k, "count", count, 1, 500)),
              r_max=None if r_max is None else _r(_num(k, "r_max", r_max, 0.02, 8) * PX, 1),
              squash=None if squash is None else _r(_num(k, "squash", squash, 0.05, 1), 3),
              color=_color(k, "color", color), width=_r(_num(k, "width", width, 0.3, 20), 2))
    if isinstance(pt, str):
        d["obj"] = pt
    else:
        d["at"] = pt
    return d


# ------------------------------------------------------------------------------ 11. фактура и растр
def grain(*, amount: float = 0.5, mode: str = "paper", area: Sequence[float] | None = None, fps: float | None = None,
          size: float = 1.0, color: str = "ink", character: str = "lively", seed: int = 3, layer: str = "over") -> dict:
    """Фактура на весь слайд (или в рамке area): шум бумаги (mode="paper": зерно + мягкие волокна) или плёнки
    ("film": плотное зерно, пылинки, царапины, мерцание, виньетка). Обновляется 8–12 к/с (fps; calm 8, lively 10,
    dramatic 12), между обновлениями не тратит кадры. amount — сила 0..2; size — размер зерна, px."""
    k = "grain"
    return _base(k, character, 0.0, seed, None, layer, amount=_r(_num(k, "amount", amount, 0, 2), 3),
                 mode=_choice(k, "mode", mode, ("paper", "film")), area=None if area is None else _box(k, "area", area),
                 fps=None if fps is None else _r(_num(k, "fps", fps, 6, 12), 2), size=_r(_num(k, "size", size, 0.5, 4), 2),
                 color=_color(k, "color", color))


def halftone(area: Sequence[float] | None = None, *, obj: str | None = None, cell: float = 0.08,
             color: str = "accent", angle: float = 45, field: str = "radial", center: Sequence[float] | None = None,
             rmax: float | None = None, speed: float = 1.0, delay: float = 0.0, dur: float = 1.2,
             character: str = "lively", seed: int = 1, step: int | None = None, layer: str = "over") -> dict:
    """Растр точками внутри области (рамка area или фигура obj — обрезка по её контуру): сетка под углом angle,
    радиус точки задаёт поле field — radial (от center к краям, пульсирует), ring (бегущие кольца), wave (волны),
    linear (градиент по направлению angle). Растр «проявляется» волной за dur, потом поле медленно движется
    (speed). cell — шаг сетки, дюймы; rmax — наибольший радиус точки, дюймы (по умолчанию половина шага)."""
    k = "halftone"
    if area is None and obj is None:
        _err(k, "нужна рамка area или фигура obj")
    return _base(k, character, delay, seed, step, layer, area=None if area is None else _box(k, "area", area),
                 obj=None if obj is None else _name(k, "obj", obj), cell=_r(_num(k, "cell", cell, 0.03, 1) * PX, 2),
                 color=_color(k, "color", color), angle=_num(k, "angle", angle, -360, 360),
                 field=_choice(k, "field", field, FIELDS), center=None if center is None else _pt(k, "center", center, False),
                 rmax=None if rmax is None else _r(_num(k, "rmax", rmax, 0.005, 1) * PX, 2),
                 speed=_r(_num(k, "speed", speed, 0, 10), 3), dur=_r(_num(k, "dur", dur, 0.05, 30), 3))


# ------------------------------------------------------------------------------ 12. график и столбики
def chart_draw(box: Sequence[float], data: Sequence, *, x_range: Sequence[float] | None = None,
               y_range: Sequence[float] | None = None, color: str = "accent", width: float = 3.0, fill: float = 0.1,
               dot: bool = True, label: bool = True, decimals: int = 3, suffix: str = "", marks: Sequence | None = None,
               axis: bool = True, size: float = 11, ease: str = "inOut", delay: float = 0.0, dur: float = 1.8,
               character: str = "lively", seed: int = 1, step: int | None = None, layer: str = "over") -> dict:
    """График, который рисуется по точкам данных: линия растёт за dur, за ней — заливка (fill — прозрачность, 0 —
    без), по голове бежит точка с пульсирующим ореолом и подписью текущего значения (decimals, suffix). data —
    значения y или пары (x, y); x_range/y_range — пределы осей (по умолчанию по данным с полями). marks —
    [(индекс, подпись[, цвет]), …]: метка вспыхивает, когда линия до неё дошла (лучшая эпоха). box — рамка
    в дюймах; width — толщина линии, px; size — кегль подписей, pt. dramatic — разгон и «комета» у головы."""
    k = "chart-draw"
    if len(data) < 2:
        _err(k, "нужно не меньше двух точек")
    pts = []
    for i, q in enumerate(data):
        if isinstance(q, (list, tuple)):
            pts.append([_num(k, "data", q[0]), _num(k, "data", q[1])])
        else:
            pts.append([float(i), _num(k, "data", q)])
    mk = None
    if marks:
        mk = []
        for m in marks:
            i = int(_num(k, "marks.индекс", m[0], 0, len(pts) - 1))
            mk.append({"i": i, "t": str(m[1]), **({"c": _color(k, "marks.цвет", m[2])} if len(m) > 2 else {})})
    rng = lambda v, nm: None if v is None else [_num(k, nm, v[0]), _num(k, nm, v[1])]  # noqa: E731
    return _base(k, character, delay, seed, step, layer, box=_box(k, "box", box), data=pts, x_range=rng(x_range, "x_range"),
                 y_range=rng(y_range, "y_range"), color=_color(k, "color", color), width=_r(_num(k, "width", width, 0.5, 20), 2),
                 fill=_r(_num(k, "fill", fill, 0, 1), 3) or None, dot=bool(dot), label=bool(label),
                 fmt={"dec": int(_num(k, "decimals", decimals, 0, 8)), "suf": suffix}, marks=mk, axis=bool(axis),
                 size=_r(_num(k, "size", size, 6, 40) * PT, 2), ease=_choice(k, "ease", ease, EASES),
                 dur=_r(_num(k, "dur", dur, 0.2, 60), 3))


def bars_grow(box: Sequence[float] | None = None, values: Sequence | None = None, *, objs: Sequence[str] | None = None,
              texts: Sequence[str] | None = None, orient: str = "h", vmax: float | None = None, color: str = "accent",
              highlight: int | None = None, decimals: int | None = None, suffix: str = "", size: float = 12,
              label_w: float | None = None, stagger: float = 0.16, delay: float = 0.0, character: str = "lively",
              seed: int = 1, step: int | None = None, layer: str = "over") -> dict:
    """Столбики растут с пружиной (calm — без перелёта, lively — заметный, dramatic — сильный), очередью stagger, у
    кончика — счётчик значения (монотонно). Два режима:
      * свои столбики: box (дюймы) + values — [(подпись, значение[, цвет]), …]; orient "h" (полосы) | "v" (колонки);
        highlight — индекс выделенного (значение его цветом); label_w — ширина колонки подписей, дюймы;
      * объекты слайда: objs — имена прямоугольников (растут от левого края / низа), texts — их тексты-числа
        (считают до написанного). Статичный слайд показывает итог."""
    k = "bars-grow"
    _choice(k, "orient", orient, ("h", "v"))
    if objs:
        return _base(k, character, delay, seed, step, layer, objs=[_name(k, "objs", n) for n in objs],
                     texts=[_name(k, "texts", n) for n in texts] if texts else None, orient=orient,
                     stagger=_r(_num(k, "stagger", stagger, 0, 10), 3),
                     decimals=None if decimals is None else int(_num(k, "decimals", decimals, 0, 8)))
    if box is None or not values:
        _err(k, "нужны box и values (или objs)")
    items = []
    for it in values:
        d = {"label": str(it[0]), "v": _num(k, "values", it[1])}
        if len(it) > 2:
            d["c"] = _color(k, "values.цвет", it[2])
        items.append(d)
    fmt = {"suf": suffix}
    if decimals is not None:
        fmt["dec"] = int(_num(k, "decimals", decimals, 0, 8))
    return _base(k, character, delay, seed, step, layer, box=_box(k, "box", box), values=items, orient=orient,
                 vmax=None if vmax is None else _num(k, "vmax", vmax, 1e-12), color=_color(k, "color", color),
                 hl=None if highlight is None else int(_num(k, "highlight", highlight, 0, len(items) - 1)), fmt=fmt,
                 size=_r(_num(k, "size", size, 6, 40) * PT, 2),
                 label_w=None if label_w is None else _r(_num(k, "label_w", label_w, 0, 13) * PX, 1),
                 stagger=_r(_num(k, "stagger", stagger, 0, 10), 3))


SCENES = {"liquid": liquid, "pour": pour, "bubbles": bubbles, "drip": drip, "stain": stain, "particles": particles,
          "signal": signal, "counter": counter, "clock": clock, "gauge": gauge, "terminal": terminal, "sparks": sparks,
          "confetti": confetti, "ripple": ripple, "grain": grain, "halftone": halftone, "chart-draw": chart_draw,
          "bars-grow": bars_grow}
