"""Библиотека нативных анимаций PowerPoint (203 эффекта: входы, выделения, пути, выходы) и переходов (53).

Анимации берутся из реестра data/pptx_animation_presets.json — XML-строки, снятые с файлов PowerPoint 16
(проект PPT Master, MIT; см. data/NOTICE.md). Строка пресета перенацеливается на фигуру: задержка, тип узла,
длительность (пропорционально), повтор, новые id узлов, spid цели, параметры (направление, угол, масштаб, цвет).

    Fx("entrance_spinner", "!!flower", dur=0.9)                         # «Вертушка» сразу после перехода
    Fx("emphasis_spin", "gear", dur=3, repeat=True)                     # вращение до конца слайда
    Fx("emphasis_spin", "gear", options={"amount": 90}, start="after")  # поворот на 90° после предыдущего
    Fx("path_circle", "dot", dur=4, repeat=True, path_size=(2, 2))      # круг диаметром 2 дюйма
    Fx("path_custom", "dot", path=[(1, 1), (4, 1), (4, 3)])             # своя ломаная в дюймах слайда
    Fx("entrance_fly", "!!card", options={"direction": "left"})

Старт как в панели анимации PowerPoint: 'with' — вместе с предыдущим Fx (+delay), 'after' — после окончания
всех предыдущих неповторяющихся Fx (+delay), 'at' — от начала шкалы слайда (+delay). Первый Fx стартует в 0.
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from lxml import etree

from .theme import SLIDE_H, SLIDE_W

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_DATA = Path(__file__).with_name("data") / "pptx_animation_presets.json"


@lru_cache(maxsize=1)
def registry() -> dict[str, dict]:
    data = json.loads(_DATA.read_text(encoding="utf-8"))
    return {e["key"]: e for e in data["effects"]}


@lru_cache(maxsize=1)
def model3d_only() -> frozenset[str]:
    """Эффекты 3D-моделей (анимируют атрибуты 3d.*): на обычных фигурах не играют, LibreOffice их отбрасывает."""
    return frozenset(k for k, e in registry().items() if "<p:attrName>3d." in e["row_xml"])


def keys(category: str | None = None, shapes: bool = True) -> list[str]:
    """Ключи пресетов; shapes=True — без эффектов 3D-моделей (198 из 203 работают на фигурах)."""
    return [k for k, e in registry().items() if (category is None or e["category"] == category)
            and not (shapes and k in model3d_only())]


def describe(key: str) -> dict:
    e = registry()[key]
    return {"key": key, "name": e["name"], "category": e["category"], "preset_id": e["preset_id"],
            "default_ms": e["default_duration_ms"], "model3d_only": key in model3d_only(), "options": {k: list(v.get("values", {}))
                                                               for k, v in e.get("effect_options", {}).items()}}


@dataclass
class Fx:
    """Один эффект на шкале слайда.

    key: ключ реестра (keys('entrance') …) или 'path_custom' (путь задаётся в path).
    target: имя объекта на слайде. dur: секунды (None — длительность пресета). repeat: до конца слайда.
    rev: туда-обратно (autoRev). path: ломаная в дюймах слайда [(x, y), …] — объект смещается на (p − p0),
    или готовая строка пути animMotion. path_size: (ширина, высота) готового пути в дюймах — пресеты путей заданы в долях слайда.
    options: параметры пресета (direction, amount — градусы/доля, size — %, color — роль темы или hex, font_name).
    """
    key: str
    target: str
    delay: float = 0.0
    dur: float | None = None
    start: str = "with"
    repeat: bool = False
    rev: bool = False
    options: dict = field(default_factory=dict)
    path: list[tuple[float, float]] | str | None = None
    path_size: tuple[float, float] | None = None

    @property
    def category(self) -> str:
        return "path" if self.key == "path_custom" else registry()[self.key]["category"]


def _q(tag: str) -> str:
    return f"{{{P}}}{tag}"


A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _row(key: str, options: dict) -> etree._Element:
    e = registry()["path_right" if key == "path_custom" else key]
    xml = e["row_xml"]
    numeric = {}
    for opt, value in options.items():
        spec = e.get("effect_options", {}).get(opt)
        if spec is None:
            raise KeyError(f"{key}: нет параметра {opt}; есть {list(e.get('effect_options', {}))}")
        values = spec.get("values")
        if values:
            v = value if value in values else str(value)
            if v not in values:
                raise KeyError(f"{key}.{opt}: нет значения {value!r}; есть {list(values)}")
            xml = values[v]
        else:
            numeric[opt] = value
    row = etree.fromstring(xml.encode())
    for opt, value in numeric.items():
        _apply_value(row, key, opt, value)
    return row


def _apply_value(row: etree._Element, key: str, opt: str, value) -> None:
    """Числовые, цветовые и строковые параметры: угол поворота, масштаб, прозрачность, цвет, шрифт."""
    if opt == "amount" and key == "emphasis_spin":
        for rot in row.iter(_q("animRot")):
            rot.set("by", str(int(round(float(value) * 60000))))
    elif opt == "amount" and key == "emphasis_transparency":
        for to in row.iter(_q("to")):
            sv = to.find(_q("strVal"))
            if sv is not None:
                sv.set("val", f"{float(value):g}")
        for ef in row.iter(_q("animEffect")):
            ef.set("prLst", f"opacity: {float(value):g}")
    elif opt == "size":
        for by in row.iter(_q("by")):
            k = str(int(round(float(value) * 1000)))
            by.set("x", k)
            by.set("y", k)
    elif opt == "color":  # value — hex RRGGBB (роль темы переводит build)
        for clr in row.iter(_q("animClr")):
            to = clr.find(_q("to"))
            for child in list(to):
                to.remove(child)
            etree.SubElement(to, f"{{{A_NS}}}srgbClr").set("val", str(value).lstrip("#").upper())
    elif opt == "font_name":
        for to in row.iter(_q("to")):
            sv = to.find(_q("strVal"))
            if sv is not None:
                sv.set("val", str(value))
    elif opt == "relative":
        pass  # пути и так относительные (pathEditMode="relative")
    else:
        raise KeyError(f"{key}: параметр {opt} не поддерживается движком")


_NUM = re.compile(r"-?\d+(?:\.\d+)?(?:[eE]-?\d+)?|[A-Za-z]")


def _path_scale(path: str, size: tuple[float, float]) -> str:
    """Масштабирует путь animMotion так, чтобы его габарит был size дюймов (пары чисел — x, y)."""
    toks = _NUM.findall(path)
    nums = [float(t) for t in toks if not t.isalpha()]
    xs, ys = nums[0::2], nums[1::2]
    bw, bh = (max(xs) - min(xs)) or 1e-9, (max(ys) - min(ys)) or 1e-9
    kx, ky = size[0] / SLIDE_W / bw, size[1] / SLIDE_H / bh
    out, i = [], 0
    for t in toks:
        if t.isalpha():
            out.append(t)
        else:
            out.append(f"{float(t) * (kx if i % 2 == 0 else ky):.5f}")
            i += 1
    return " ".join(out)


def custom_path(points: list[tuple[float, float]]) -> str:
    """Ломаная в дюймах (смещения от исходного положения объекта; первая точка — (0, 0)) -> путь animMotion."""
    x0, y0 = points[0]
    return " ".join(["M 0 0"] + [f"L {(x - x0) / SLIDE_W:.5f} {(y - y0) / SLIDE_H:.5f}" for x, y in points[1:]]) + " E"


def _prepare(fx: Fx) -> etree._Element:
    if fx.key != "path_custom" and fx.key not in registry():
        raise KeyError(f"нет эффекта {fx.key!r}; см. presets.keys()")
    row = copy.deepcopy(_row(fx.key, fx.options))
    e = registry()["path_right" if fx.key == "path_custom" else fx.key]
    base = e["default_duration_ms"] or effective_ms(row) or 500
    if fx.dur is not None and e.get("duration_scalable", True):
        _scale(row, fx.dur * 1000 / base)
    if fx.key == "path_custom" and fx.path is None:
        raise ValueError("path_custom: нужен path")
    if fx.path is not None or fx.path_size is not None:
        motion = next(row.iter(_q("animMotion")), None)
        if motion is None:
            raise ValueError(f"{fx.key}: path/path_size только для эффектов-путей")
        path = fx.path if isinstance(fx.path, str) else custom_path(fx.path) if fx.path else motion.get("path")
        if fx.path_size is not None:
            path = _path_scale(path, fx.path_size)
        motion.set("path", path)
    return row


def effective_ms(row: etree._Element) -> int:
    end = 0
    for ctn in row.iter(_q("cTn")):
        if ctn is row:
            continue
        d = ctn.get("dur")
        if d and d.isdigit():
            delay = 0
            st = ctn.find(_q("stCondLst"))
            if st is not None:
                for c in st.findall(_q("cond")):
                    if (c.get("delay") or "").isdigit():
                        delay = int(c.get("delay"))
            end = max(end, delay + int(d))
    return end


def duration_ms(fx: Fx) -> int:
    """Длительность одного цикла эффекта после масштабирования, мс."""
    return effective_ms(_prepare(fx))


def _scale(row: etree._Element, ratio: float) -> None:
    for ctn in row.iter(_q("cTn")):
        if ctn is row:
            continue
        d = ctn.get("dur")
        if d and d.isdigit() and d != "1":
            ctn.set("dur", str(max(1, round(int(d) * ratio))))
        st = ctn.find(_q("stCondLst"))
        if st is not None:
            for c in st.findall(_q("cond")):
                if (c.get("delay") or "").isdigit():
                    c.set("delay", str(round(int(c.get("delay")) * ratio)))


def instantiate(fx: Fx, spid: int, delay_ms: int, next_id: int) -> tuple[str, int, int, str]:
    """-> (xml узла <p:par> с эффектом, следующий свободный id, длительность цикла мс, категория)."""
    row = _prepare(fx)
    row.set("nodeType", "withEffect")
    st = row.find(_q("stCondLst"))
    for c in st.findall(_q("cond")):
        st.remove(c)
    etree.SubElement(st, _q("cond")).set("delay", str(delay_ms))
    if fx.repeat:
        row.set("repeatCount", "indefinite")
    if fx.rev:
        row.set("autoRev", "1")
    if row.get("grpId") is None:
        row.set("grpId", "0")
    row.set("id", str(next_id))
    nid = next_id + 1
    for ctn in row.iter(_q("cTn")):
        if ctn is row:
            continue
        ctn.set("id", str(nid))
        nid += 1
    for tgt in row.iter(_q("spTgt")):
        tgt.set("spid", str(spid))
    dur = effective_ms(row)
    par = etree.Element(_q("par"), nsmap={"p": P})
    par.append(row)
    xml = etree.tostring(par, encoding="unicode")
    return xml, nid, dur, fx.category


# ----------------------------------------------------------------------------- нативные переходы

# имя -> (префикс пространства имён или "", элемент, атрибуты). Факты OOXML; список совпадает с галереей PowerPoint.
TRANSITIONS = {
    # без префикса — элементы PresentationML (проверяются XSD)
    "fade": ("", "fade", {}), "push": ("", "push", {"dir": "r"}), "wipe": ("", "wipe", {"dir": "r"}),
    "split": ("", "split", {"orient": "horz", "dir": "out"}), "cover": ("", "cover", {"dir": "r"}),
    "random": ("", "random", {}), "blinds": ("", "blinds", {"dir": "vert"}), "checkerboard": ("", "checker", {"dir": "horz"}),
    "comb": ("", "comb", {"dir": "horz"}), "cut": ("", "cut", {"thruBlk": "0"}), "dissolve": ("", "dissolve", {}),
    "random_bars": ("", "randomBar", {"dir": "vert"}), "shape": ("", "circle", {}), "uncover": ("", "pull", {"dir": "r"}),
    "clock": ("", "wheel", {"spokes": "1"}), "wheel": ("", "wheel", {"spokes": "4"}), "box": ("", "zoom", {}),
    "wedge": ("", "wedge", {}), "plus": ("", "plus", {}), "diamond": ("", "diamond", {}), "strips": ("", "strips", {"dir": "ru"}),
    # p14 — PowerPoint 2010+
    "zoom": ("p14", "warp", {"dir": "in"}), "reveal": ("p14", "reveal", {"dir": "r"}), "flash": ("p14", "flash", {}),
    "ripple": ("p14", "ripple", {}), "honeycomb": ("p14", "honeycomb", {}), "glitter": ("p14", "glitter", {}),
    "vortex": ("p14", "vortex", {"dir": "r"}), "shred": ("p14", "shred", {"dir": "out"}),
    "switch": ("p14", "switch", {"dir": "r"}), "flip": ("p14", "flip", {"dir": "r"}), "gallery": ("p14", "gallery", {"dir": "r"}),
    "cube": ("p14", "prism", {"dir": "r"}), "doors": ("p14", "doors", {"dir": "vert"}), "pan": ("p14", "pan", {"dir": "r"}),
    "ferris_wheel": ("p14", "ferris", {"dir": "r"}), "conveyor": ("p14", "conveyor", {"dir": "r"}),
    "rotate": ("p14", "prism", {"dir": "r", "isContent": "1"}), "window": ("p14", "window", {}),
    "orbit": ("p14", "prism", {"dir": "r", "isContent": "1", "isInverted": "1"}), "fly_through": ("p14", "flythrough", {}),
    # p15 — PowerPoint 2013+
    "fall_over": ("p15", "prstTrans", {"prst": "fallOver", "invX": "1"}), "drape": ("p15", "prstTrans", {"prst": "drape", "invX": "1"}),
    "curtains": ("p15", "prstTrans", {"prst": "curtains"}), "wind": ("p15", "prstTrans", {"prst": "wind"}),
    "prestige": ("p15", "prstTrans", {"prst": "prestige"}), "fracture": ("p15", "prstTrans", {"prst": "fracture"}),
    "crush": ("p15", "prstTrans", {"prst": "crush"}), "peel_off": ("p15", "prstTrans", {"prst": "peelOff", "invX": "1"}),
    "page_curl": ("p15", "prstTrans", {"prst": "pageCurlSingle", "invX": "1"}), "airplane": ("p15", "prstTrans", {"prst": "airplane"}),
    "origami": ("p15", "prstTrans", {"prst": "origami"}),
    # p159 — PowerPoint 2019/365
    "morph": ("p159", "morph", {"option": "byObject"}),
}
NS_URI = {"p14": "http://schemas.microsoft.com/office/powerpoint/2010/main",
          "p15": "http://schemas.microsoft.com/office/powerpoint/2012/main",
          "p159": "http://schemas.microsoft.com/office/powerpoint/2015/09/main"}
