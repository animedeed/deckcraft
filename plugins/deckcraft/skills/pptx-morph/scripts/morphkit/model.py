"""Описание сцены: объекты, слайды, камера и разметка текста.

Колода — поток состояний. Каждый слайд — список объектов O. Объекты с одинаковым именем '!!…' на соседних
слайдах образуют пару Morph. Префиксы имён задают роль объекта:
    !!имя   — участвует в Morph (пара на соседнем слайде);
    anim_…  — проявляется после перехода (по очереди), без пары;
    loop_…  — носитель зацикленной анимации; никогда не делается парой Morph;
    остальное — обычные объекты (без пары: при Morph проявляются или гаснут).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any

from .theme import SLIDE_H, SLIDE_W

# ----------------------------------------------------------------------------- текст

STYLE_TAGS = {"a": "accent", "a2": "accent2", "a3": "accent3", "r": "bad", "g": "good", "w": "warn",
              "m": "muted", "i": "ink", "i2": "ink2"}
_TAG = re.compile(r"\{(a2|a3|i2|[a-z]):([^{}]*)\}")


@dataclass(frozen=True)
class Run:
    text: str
    color: str | None = None  # роль или hex; None — цвет объекта
    bold: bool | None = None
    mono: bool = False
    strike: bool = False


def parse_line(line: str) -> list[Run]:
    """Мини-разметка: обычный {a:акцент} {b:жирный} {m:приглушённый} {c:код} {x:зачёркнутый}.
    Вложенность не поддерживается; каждая строка размечается отдельно."""
    runs, pos = [], 0
    for m in _TAG.finditer(line):
        if m.start() > pos:
            runs.append(Run(line[pos:m.start()]))
        tag, body = m.group(1), m.group(2)
        if tag == "b":
            runs.append(Run(body, bold=True))
        elif tag == "c":
            runs.append(Run(body, mono=True))
        elif tag == "x":
            runs.append(Run(body, strike=True, color="muted"))
        elif tag in STYLE_TAGS:
            runs.append(Run(body, color=STYLE_TAGS[tag]))
        else:
            raise ValueError(f"неизвестный тег {{{tag}:…}} в строке {line!r}")
        pos = m.end()
    if pos < len(line):
        runs.append(Run(line[pos:]))
    return runs or [Run("")]


def plain(line: str) -> str:
    return "".join(r.text for r in parse_line(line))


# ----------------------------------------------------------------------------- объект

@dataclass
class O:
    """Один объект слайда. Координаты — дюймы на слайде 13,333 × 7,5 (или мир, если world=True)."""
    name: str
    kind: str = "rect"  # rect rrect oval text line arrow arc chevron tri pent hex img
    x: float = 0.0
    y: float = 0.0
    w: float = 1.0
    h: float = 1.0
    fill: str | None = None
    fa: float = 1.0  # непрозрачность заливки 0..1
    ln: str | None = None  # цвет линии/обводки
    lw: float = 0.0  # толщина, pt
    la: float = 1.0  # непрозрачность линии
    dash: str | None = None  # 'dash' | 'dot' | 'sysDash' …
    head: str | None = None  # наконечник линии в конце: 'triangle' | 'arrow' | 'oval'
    txt: str | list[str] | None = None
    sz: float = 18
    col: str = "ink"
    b: bool = False
    font: str = "body"  # 'head' | 'body' | 'mono' или имя шрифта
    al: str = "l"  # l c r
    va: str = "t"  # t m b
    spacing: float = 1.0  # множитель межстрочного интервала
    para_gap: float = 0.0  # отступ после абзаца, pt
    bullets: bool = False
    caps: bool = False
    tracking: float = 0.0  # разрядка, pt (spc в сотых pt)
    rot: float = 0.0
    radius: float | None = None  # радиус скругления rrect, дюймы (пересчитывается в adj)
    adj: dict = field(default_factory=dict)  # прямые регуляторы фигуры
    img: str | None = None
    crop: tuple[float, float, float, float] | None = None  # l, t, r, b доли 0..1
    world: bool = False
    shadow: bool = False
    z: int = 0
    meta: dict = field(default_factory=dict)

    def copy(self, **kw: Any) -> "O":
        return replace(self, **kw)

    @property
    def lines(self) -> list[str]:
        if self.txt is None:
            return []
        if isinstance(self.txt, str):
            return self.txt.split("\n")
        return list(self.txt)

    @property
    def is_morph(self) -> bool:
        return self.name.startswith("!!")

    @property
    def is_anim(self) -> bool:
        return self.name.startswith("anim_")

    @property
    def is_loop(self) -> bool:
        return self.name.startswith("loop_")


# ----------------------------------------------------------------------------- зацикленные анимации

@dataclass
class Loop:
    """Анимация, повторяющаяся до конца слайда.

    kind:
      'flow'   — точки бегут по пути points (ломаная в дюймах слайда), n штук со сдвигом фазы;
      'pulse'  — объект target плавно увеличивается и возвращается (scale);
      'ripple' — круг вокруг target расширяется и гаснет («круги на воде»);
      'spin'   — объект target вращается;
      'blink'  — объект target мигает (курсор, индикатор).
    """
    kind: str
    target: str | None = None
    points: list[tuple[float, float]] | None = None
    n: int = 3
    period: float = 2.4  # секунды на один цикл
    size: float = 0.13  # диаметр точки потока, дюймы
    color: str = "flow"
    scale: float = 1.18  # для pulse/ripple
    start: float = 0.0  # задержка старта после перехода, с
    name: str = "loop"
    reverse: bool = False  # для flow: обратное направление
    z: float = 5  # слой точек: ниже узлов (z=10), выше соединителей (z=4) — очередь точек прячется под источником


# ----------------------------------------------------------------------------- слайд и камера

@dataclass
class Cam:
    cx: float = SLIDE_W / 2
    cy: float = SLIDE_H / 2
    z: float = 1.0


@dataclass
class Slide:
    objs: list[O]
    bg: str = "bg"
    cam: Cam | None = None
    dur: int = 800  # длительность Morph в мс (на переходе К этому слайду); быстрые переходы — правило профиля
    mode: str = "byObject"  # byObject | byWord | byChar
    anims: list[str] = field(default_factory=list)  # имена anim_* в порядке появления (по умолчанию — порядок в objs)
    loops: list[Loop] = field(default_factory=list)
    notes: str = ""
    hold: float = 4.0  # пауза в видео-резерве, с
    auto: int | None = None  # advTm, мс: слайд сам переключится дальше (служебные «нулевые» состояния)
    layout: str = ""  # имя архетипа макета (для проверки разнообразия)
    technique: str = ""  # приём Morph на переходе К этому слайду (для проверки разнообразия)
    title: str = ""  # для контактного листа и отчёта
    transition: str = "morph"  # любой ключ presets.TRANSITIONS (morph, fade, push, vortex, curtains …) или none
    trans_opts: dict = field(default_factory=dict)  # атрибуты перехода, например {"dir": "l"}
    fx: list = field(default_factory=list)  # эффекты библиотеки presets.Fx (входы, выделения, пути, выходы)


def apply_camera(o: O, cam: Cam | None, parallax: float | None = None) -> O:
    """Мировые координаты -> слайд: x = (X − cx)·z + W/2. Кегль и толщины масштабируются вместе с z."""
    if not o.world or cam is None:
        return o
    z = cam.z if parallax is None else cam.z ** parallax
    cx = cam.cx if parallax is None else cam.cx * parallax + (SLIDE_W / 2) * (1 - parallax)
    cy = cam.cy if parallax is None else cam.cy * parallax + (SLIDE_H / 2) * (1 - parallax)
    meta = o.meta
    if o.txt is not None:  # внутренние поля текста масштабируются вместе с камерой, иначе мелкий план «съедает» рамку
        meta = dict(o.meta)
        meta["inset"] = o.meta.get("inset", 0.0 if o.kind == "text" else 0.12) * z
    return o.copy(x=(o.x - cx) * z + SLIDE_W / 2, y=(o.y - cy) * z + SLIDE_H / 2, w=o.w * z, h=o.h * z,
                  sz=o.sz * z, lw=o.lw * z, radius=None if o.radius is None else o.radius * z, world=False, meta=meta)


def resolve(slide: Slide) -> list[O]:
    """Применяет камеру и проверяет уникальность имён."""
    out = [apply_camera(o, slide.cam, o.meta.get("parallax")) for o in slide.objs]
    names = [o.name for o in out]
    dup = {n for n in names if names.count(n) > 1}
    if dup:
        raise ValueError(f"повторяющиеся имена на слайде «{slide.title}»: {sorted(dup)}")
    for o in out:
        if o.is_loop and o.is_morph:
            raise ValueError(f"{o.name}: объект петли не может быть парой Morph")
    return sorted(out, key=lambda o: o.z)


# ----------------------------------------------------------------------------- политика текста

def apply_text_policy(slides: list[Slide], policy: str = "fade") -> list[Slide]:
    """policy="fade": если у пары Morph изменился текст, пара разрывается — старый текст гаснет, новый проявляется
    (перелив разного текста выглядит как каша букв). Объекты с meta["morph_text"]=True морфятся всегда.
    Возвращает копии слайдов; исходные не меняются."""
    if policy != "fade":
        return slides
    out, prev_alias, prev_text = [], {}, {}
    for i, s in enumerate(slides):
        objs, alias_now, text_now = [], {}, {}
        for o in s.objs:
            if not o.is_morph or o.txt is None:
                objs.append(o)
                continue
            txt = "\n".join(o.lines)
            alias = prev_alias.get(o.name, o.name)
            if (o.name in prev_text and prev_text[o.name] != txt and not o.meta.get("morph_text")
                    and s.transition == "morph"):
                alias = f"{o.name}~{i}"
            alias_now[o.name], text_now[o.name] = alias, txt
            objs.append(o if alias == o.name else o.copy(name=alias))
        renamed = {k: v for k, v in alias_now.items() if k != v}
        if renamed:  # ссылки эффектов, петель и порядка появления — на новые имена
            fx = [replace(f, target=renamed.get(f.target, f.target)) for f in s.fx]
            loops = [replace(lp, target=renamed.get(lp.target, lp.target)) for lp in s.loops]
            anims = [renamed.get(a, a) for a in s.anims]
            out.append(replace(s, objs=objs, fx=fx, loops=loops, anims=anims))
        else:
            out.append(replace(s, objs=objs))
        prev_alias, prev_text = alias_now, text_now
    return out
