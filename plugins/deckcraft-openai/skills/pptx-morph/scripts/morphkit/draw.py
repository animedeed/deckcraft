"""Элементы рисования deckcraft 0.3.0: линии, стрелки, размеры, выноски, скобки, штриховки, пометки от руки, печати,
стикеры, рамка ГОСТ, шкалы, приборы, часы, рукописный текст, блок-схемы.

    from morphkit import draw as d
    objs += d.dim_h("!!w", 2.0, 6.0, 1.4, base=1.8, value=1200, fmt="{v} мм", style="blueprint")
    objs += d.gauge("!!spd", 10.5, 4.0, 1.6, 72, label="км/ч", zones=[(80, 100, "bad")])
    web(slide, fx=[{"key": "in.draw", "target": "!!w", "delay": .2, "dur": 1.2}])

Каждая функция возвращает **список O**: первый — сам элемент (O с meta["draw"] = {"kind", параметры, "style"}; в HTML
его рисует morphkit/web/draw.js — SVG, рисование по длине штрихов, перелив Morph), остальные — запасные части только
для .pptx (подписи-текстбоксы, вторая краска, заливки другого цвета: meta["draw"] = {"kind": "pptx"}, в HTML скрыты).
Запасная форма самого элемента — свободная форма kind="vec" из лент-штрихов (shapely), поэтому build_pptx собирает те
же слайды. Рамка (x, y, w, h) охватывает элемент; параметры — в дюймах слайда, в спецификации хранится рамка "_f".

Стили: blueprint (тонкие светлые линии — для тёмного фона), ink (тушь с дрожанием), marker (толстые полупрозрачные,
multiply), riso (толстые + смещённая копия второй краски c2), chalk (мел). Цвета — роли темы ("accent", "ink2" …), hex
или оттенок "роль/30" (30 % цвета на белом). Общие параметры всех функций: style, color, c2, tc (цвет текста), lw (pt),
seed, z, rot, world, meta. Стиль по умолчанию — default(style=…) или "ink".
Эффекты web: in.draw (рисование), in.draw-linear, in.draw-stamp, in.draw-drop, in.draw-reg, in.draw-pop; выделения
em.draw-redraw, em.draw-boil, em.draw-to ({"value": …}), em.draw-run ({"minutes": …}), em.draw-needle.
"""

from __future__ import annotations

import math
import zlib
from typing import Sequence

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from . import vector as V
from .model import O

P2 = Sequence[float]
STYLES = {
    "blueprint": {"c": "code_ink", "lw": 1.1, "font": "mono", "a": 1.0, "bold": False},
    "ink": {"c": "ink", "lw": 1.8, "font": "hand", "a": 1.0, "bold": True},
    "marker": {"c": "accent", "lw": 5.5, "font": "hand", "a": 0.62, "bold": True},
    "riso": {"c": "ink", "c2": "accent", "lw": 3.4, "font": "head", "a": 0.95, "bold": True},
    "chalk": {"c": "ink", "lw": 2.8, "font": "hand", "a": 0.9, "bold": True},
}
HAND_FONT = "Segoe Print"  # рукописный шрифт в .pptx (в HTML: 'Caveat', 'Segoe Print', …, запасной — курсив)
_DEF: dict = {"style": "ink"}
RISO_OFF = (0.028, 0.022)  # смещение второй краски, дюймы


def default(**kw) -> dict:
    """Умолчания для следующих вызовов: default(style="blueprint", color="code_ink"). Возвращает текущие умолчания."""
    _DEF.update(kw)
    return dict(_DEF)


# ----------------------------------------------------------------------------- числа, случайность, геометрия
def fmt_num(v: float, dec: int = 0, fmt: str | None = None) -> str:
    """Как в draw.js: 1200 → «1200», 12500 → «12 500», 3.5 → «3,5»."""
    s = f"{float(v):.{int(dec or 0)}f}"
    if abs(float(v)) >= 10000:
        a, _, b = s.partition(".")
        sign = "-" if a.startswith("-") else ""
        a = a.lstrip("-")
        a = " ".join(a[max(0, i - 3):i] for i in range(len(a), 0, -3)[::-1])
        s = sign + a + ("." + b if b else "")
    from .i18n import get_lang
    if get_lang() == "en":  # en: 12,500 · 3.5 · −2
        return (fmt or "{v}").replace("{v}", s.replace(" ", ",").replace("-", "−"))
    return (fmt or "{v}").replace("{v}", s.replace(".", ",").replace("-", "−"))


def _rng(seed: int):
    """Тот же генератор, что DC.u.rng: формы «от руки» в .pptx совпадают с HTML."""
    s = [int(seed) & 0xFFFFFFFF or 1]

    def nxt() -> float:
        s[0] = (s[0] * 1664525 + 1013904223) & 0xFFFFFFFF
        return s[0] / 4294967296
    return nxt


def _arc(cx, cy, rx, ry, a0, a1, n=None):
    n = n or max(6, math.ceil(abs(a1 - a0) / 3))
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]


def _quad(p0, c, p1, n=24):
    return [((1 - t) ** 2 * p0[0] + 2 * t * (1 - t) * c[0] + t * t * p1[0], (1 - t) ** 2 * p0[1] + 2 * t * (1 - t) * c[1] + t * t * p1[1])
            for t in (i / n for i in range(n + 1))]


def _cubic(p0, p1, p2, p3, n=28):
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def _smooth(P, closed=False, n=12):
    """Катмулл–Ром через точки (как G.smooth в draw.js)."""
    P = [tuple(p) for p in P]
    if len(P) < 3:
        return P
    pts = P + [P[0]] if closed else P
    m, L = len(pts), len(P)

    def g(i):
        return P[i % L] if closed else pts[max(0, min(m - 1, i))]
    out = []
    for i in range(m - 1):
        p0, p1, p2, p3 = g(i - 1), pts[i], pts[i + 1], g(i + 2)
        for j in range(n):
            t = j / n
            out.append(tuple(0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t * t
                                    + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t ** 3) for k in (0, 1)))
    out.append(pts[-1])
    return out


def _rect(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]


def _circ(c, r, n=24):
    return [(c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _cut_start(P, d):
    acc = 0.0
    for i in range(1, len(P)):
        a, b = P[i - 1], P[i]
        s = math.hypot(b[0] - a[0], b[1] - a[1])
        if acc + s >= d:
            f = (d - acc) / s if s else 0.0
            return [(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)] + [tuple(p) for p in P[i:]]
        acc += s
    return [tuple(P[-1]), tuple(P[-1])]


def _trim(P, d0, d1):
    Q = [tuple(p) for p in P]
    if d0 > 0:
        Q = _cut_start(Q, d0)
    if d1 > 0:
        Q = _cut_start(Q[::-1], d1)[::-1]
    return Q


def _pl(pts) -> list[list[float]]:
    return [[round(float(p[0]), 4), round(float(p[1]), 4)] for p in pts]


def _col(c: str | None) -> tuple[str | None, float]:
    """'accent3/30' → ('accent3', 0.30): оттенок в .pptx — тот же цвет с прозрачностью."""
    if c and "/" in c:
        base, pct = c.split("/", 1)
        return base, max(0.0, min(1.0, float(pct) / 100))
    return c, 1.0


# ----------------------------------------------------------------------------- сборщик элемента
class _Fig:
    def __init__(self, name: str, kind: str, kw: dict, **defaults):
        for k, v in defaults.items():
            kw.setdefault(k, v)
        style = kw.pop("style", None) or _DEF.get("style", "ink")
        if style not in STYLES:
            raise ValueError(f"стиль {style!r}: есть {sorted(STYLES)}")
        self.name, self.kind, self.style, self.st = name, kind, style, STYLES[style]
        user_c = kw.pop("color", None)
        self.color = user_c or _DEF.get("color") or self.st["c"]
        user_c2 = kw.pop("c2", None)
        self.c2 = user_c2 or _DEF.get("c2") or self.st.get("c2") or "accent"
        self.tc = kw.pop("tc", None)
        lw = kw.pop("lw", None)
        self.lw = (lw if lw is not None else self.st["lw"]) / 72
        seed = kw.pop("seed", None)
        self.seed = int(seed) if seed is not None else zlib.crc32(name.lstrip("!").encode()) % 9973 + 1
        self.z = kw.pop("z", 40)
        self.world = kw.pop("world", False)
        self.rot = kw.pop("rot", 0.0)
        self.meta = dict(kw.pop("meta", {}) or {})
        if kw:
            raise TypeError(f"{kind}: неизвестные параметры {sorted(kw)}")
        self.spec: dict = {"kind": kind, "style": style, "seed": self.seed}
        if user_c or _DEF.get("color"):
            self.spec["c"] = self.color
        for k, v in (("c2", user_c2), ("tc", self.tc), ("lw", lw)):
            if v is not None:
                self.spec[k] = v
        if self.c2 and style == "riso":
            self.spec.setdefault("c2", self.c2)
        self.groups: dict[str, list] = {"main": []}
        self.gstyle: dict[str, tuple] = {"main": (self.color, self.st["a"], 0)}
        self.texts: list[tuple] = []
        self.extra_bounds: list[tuple] = []

    # геометрия запасной формы
    def s(self, pts, wk: float = 1.0, w: float | None = None, group: str = "main", cap: int = 1):
        pts = [tuple(p) for p in pts]
        if len(pts) < 2:
            return
        ww = w if w is not None else self.lw * wk
        self.groups.setdefault(group, []).append(LineString(pts).buffer(max(ww, 0.004) / 2, cap_style=cap, join_style=1 if cap == 1 else 2,
                                                                        quad_segs=2))

    def f(self, poly, group: str = "main", color: str | None = None, alpha: float | None = None, zoff: float = -1):
        g = poly if isinstance(poly, Polygon) else Polygon([tuple(p) for p in poly])
        if not g.is_valid:
            g = g.buffer(0)
        self.groups.setdefault(group, []).append(g)
        if group not in self.gstyle:
            c, tint = _col(color or self.color)
            self.gstyle[group] = (c, tint * (1.0 if alpha is None else alpha), zoff)

    def t(self, x, y, s, sz, anchor="middle", va="m", rot=0.0, bold=None, font=None, col=None):
        if s is None or str(s) == "":
            return
        s = str(s)
        k = sz / 72
        yc = y - k * 0.5 if va == "b" else y + k * 0.55 if va == "t" else y
        w = max(0.2, len(s) * k * 0.58 + 0.12)
        h = k * 1.4
        al = {"start": "l", "end": "r"}.get(anchor, "c")
        bx = x - w / 2 if al == "c" else x if al == "l" else x - w
        if rot:  # подпись повёрнута вокруг своего центра
            cx = bx + w / 2
            self.texts.append((cx - w / 2, yc - h / 2, w, h, s, sz, "c", rot, bold, font, col))
            self.extra_bounds.append((cx - h / 2, yc - w / 2, cx + h / 2, yc + w / 2))
        else:
            self.texts.append((bx, yc - h / 2, w, h, s, sz, al, 0.0, bold, font, col))
            self.extra_bounds.append((bx, yc - h / 2, bx + w, yc + h / 2))

    def heads(self, P, a, b, win_unused=None, wk: float = 1.0):
        """Наконечники (как heads() в draw.js); возвращает укороченный стержень."""
        w = self.lw * wk
        plen = sum(math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]) for i in range(1, len(P)))
        hl = min(0.07 + min(w, 0.03) * 4, plen * 0.42)

        def one(kind, at_end):
            Q = list(P) if at_end else list(P)[::-1]
            tip = tuple(Q[-1])
            bk = _cut_start(Q[::-1], hl)[0]
            ux, uy = tip[0] - bk[0], tip[1] - bk[1]
            L = math.hypot(ux, uy) or 1.0
            ux, uy = ux / L, uy / L
            nx, ny = -uy, ux

            def at(s, n):
                return (tip[0] - ux * s * hl + nx * n * hl, tip[1] - uy * s * hl + ny * n * hl)
            if kind in ("tri", "dim", "triangle", "arrow"):
                hw = 0.22 if kind == "dim" else 0.36
                self.f([tip, at(1, hw), at(0.78, 0), at(1, -hw)], zoff=0)
                return hl * 0.7
            if kind == "open":
                self.s([at(1, 0.42), tip, at(1, -0.42)], wk)
                return 0.0
            if kind in ("dot", "oval"):
                r = min(max(w * 2, 0.024), 0.065)
                self.f(_circ(tip, r, 18), zoff=0)
                return r * 0.5
            if kind == "tick":
                vx, vy, s = (ux + nx) * 0.7071, (uy + ny) * 0.7071, hl * 0.55
                self.s([(tip[0] - vx * s, tip[1] - vy * s), (tip[0] + vx * s, tip[1] + vy * s)], wk * 1.6)
                return 0.0
            return 0.0
        d0 = one(a, False) if a else 0.0
        d1 = one(b, True) if b else 0.0
        return _trim(P, d0, d1)

    def font(self, role: str | None = None) -> str:
        r = role or self.st["font"]
        return HAND_FONT if r == "hand" else r

    def finish(self, main_text: O | None = None) -> list[O]:
        geoms = {k: [g for g in v if not g.is_empty] for k, v in self.groups.items()}
        alls = [g for v in geoms.values() for g in v]
        bounds = [g.bounds for g in alls] + list(self.extra_bounds)
        if not bounds:
            raise ValueError(f"{self.kind} {self.name}: пустой элемент")
        x0, y0 = min(b[0] for b in bounds), min(b[1] for b in bounds)
        x1, y1 = max(b[2] for b in bounds), max(b[3] for b in bounds)
        pad = max(0.04, self.lw)
        fx, fy = x0 - pad, y0 - pad
        fw, fh = max(x1 - x0 + 2 * pad, 0.1), max(y1 - y0 + 2 * pad, 0.1)
        frame = (fx, fy, fw, fh)
        self.spec["_f"] = [round(fx, 4), round(fy, 4), round(fw, 4), round(fh, 4)]
        meta = dict(self.meta, draw=self.spec)
        hidden = {"draw": {"kind": "pptx"}}
        order = [k for k in geoms if geoms[k]]
        out: list[O] = []
        tc = _col(self.tc or self.color)[0]
        if main_text is not None:
            main_text.meta = dict(main_text.meta, **meta)
            main_text.z, main_text.world, main_text.rot = self.z, self.world, self.rot
            out.append(main_text)
        elif not order:
            raise ValueError(f"{self.kind} {self.name}: нет геометрии")
        for i, k in enumerate(order):
            g = unary_union(geoms[k]).simplify(0.0025, preserve_topology=True)
            if g.is_empty:
                continue
            c, a, zoff = self.gstyle.get(k, (self.color, self.st["a"], 0))
            c = _col(c)[0]
            first = main_text is None and not out
            nm = self.name if first else f"{self.name}~g{i}"
            out.append(V.shape(nm, g, frame=frame, fill=c, fa=a, z=self.z + (0 if first else zoff), rot=self.rot,
                               world=self.world, meta=meta if first else dict(hidden)))
            if self.style == "riso" and k == "main":
                from shapely import affinity
                g2 = affinity.translate(g, *RISO_OFF)
                out.append(V.shape(f"{self.name}~r", g2, frame=(fx + RISO_OFF[0], fy + RISO_OFF[1], fw, fh), fill=_col(self.c2)[0],
                                   fa=0.9, z=self.z - 0.5, rot=self.rot, world=self.world, meta=dict(hidden)))
        if out and out[0].name != self.name:  # главным должен быть объект с именем элемента
            out[0] = out[0].copy(name=self.name, meta=meta)
        cx, cy = fx + fw / 2, fy + fh / 2
        a = math.radians(self.rot or 0.0)
        for i, (bx, by, w, h, s, sz, al, rot, bold, font, col) in enumerate(self.texts):
            if self.rot:  # центр подписи поворачивается вместе с рамкой элемента
                tx, ty = bx + w / 2 - cx, by + h / 2 - cy
                nx, ny = cx + tx * math.cos(a) - ty * math.sin(a), cy + tx * math.sin(a) + ty * math.cos(a)
                bx, by = nx - w / 2, ny - h / 2
            out.append(O(f"{self.name}~t{i}", "text", bx, by, w, h, txt=s, sz=sz, col=_col(col)[0] if col else tc, al=al,
                         va="m", b=self.st["bold"] if bold is None else bold, font=self.font(font), rot=(rot or 0.0) + (self.rot or 0.0),
                         z=self.z + 2, world=self.world, meta={"inset": 0.0, **hidden}))
        return out


def _ff(v):
    return round(float(v), 4)


# ----------------------------------------------------------------------------- линии и стрелки
def line(name: str, pts: Sequence[P2], *, curve: bool = False, closed: bool = False, start: str | None = None,
         end: str | None = None, dash: str | None = None, **kw) -> list[O]:
    """Линия, ломаная, кривая через точки (curve=True), замкнутая (closed). start/end — наконечник: tri | open | dot |
    tick. dash — 'dash' | 'dot'."""
    fg = _Fig(name, "line", kw)
    fg.spec.update(pts=_pl(pts), curve=curve, closed=closed, start=start, end=end, dash=dash)
    P = _smooth(pts, closed) if curve else [tuple(p) for p in pts] + ([tuple(pts[0])] if closed else [])
    fg.s(fg.heads(P, start, end))
    return fg.finish()


def arrow(name: str, p0: P2, p1: P2, *, via: Sequence[P2] | None = None, bend: float = 0.0, hand: bool = False,
          double: bool = False, head: str = "tri", **kw) -> list[O]:
    """Стрелка: прямая; дуга (bend — прогиб в долях длины, + влево от направления); «от руки» (hand=True); ломаная (via);
    double — наконечники с двух сторон; head — tri | open | dot | tick."""
    fg = _Fig(name, "arrow", kw)
    fg.spec.update(p0=_pl([p0])[0], p1=_pl([p1])[0], via=_pl(via) if via else None, bend=bend, hand=hand, double=double, head=head)
    a, b = tuple(p0), tuple(p1)
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1.0
    nx, ny = dy / L, -dx / L
    if via:
        P = [a] + [tuple(p) for p in via] + [b]
    elif hand:
        r = _rng(fg.seed * 7 + 3)
        k1 = (r() - 0.5) * 0.2 + bend * 1.3
        k2 = (r() - 0.5) * 0.2 + bend * 1.3
        P = _cubic(a, (a[0] + dx * .3 + nx * L * k1, a[1] + dy * .3 + ny * L * k1), (a[0] + dx * .7 + nx * L * k2, a[1] + dy * .7 + ny * L * k2), b, 32)
    elif bend:
        P = _quad(a, ((a[0] + b[0]) / 2 + nx * L * bend * 2, (a[1] + b[1]) / 2 + ny * L * bend * 2), b, 32)
    else:
        P = [a, b]
    fg.s(fg.heads(P, head if double else None, head))
    return fg.finish()


# ----------------------------------------------------------------------------- размеры и выноски
def _dim(name, dirn, a, b, at, base, label, value, dec, fmt, ends, over, ext, sz, kw):
    fg = _Fig(name, "dim", kw)
    lab = fmt_num(value, dec, fmt) if value is not None else label
    fg.spec.update(dir=dirn, a=_ff(a), b=_ff(b), at=_ff(at), base=None if base is None else _ff(base), ext=ext, over=over,
                   ends=ends, sz=sz, dec=dec, fmt=fmt)
    if value is not None:
        fg.spec["value"] = value
    else:
        fg.spec["label"] = label
    v = dirn == "v"
    base = at + ext if base is None else base
    s = (1 if at > base else -1) if at != base else -1
    gap = 0.04

    def P(u, w):
        return (w, u) if v else (u, w)
    fg.s([P(a, base + s * gap), P(a, at + s * over)], 0.7)
    fg.s([P(b, base + s * gap), P(b, at + s * over)], 0.7)
    mid = (a + b) / 2
    ht = "dim" if ends == "arrow" else ends
    fg.s(fg.heads([P(mid, at), P(a, at)], None, ht))
    fg.s(fg.heads([P(mid, at), P(b, at)], None, ht))
    k = sz / 72
    if v:
        fg.t(at - gap - k * 0.55, mid, lab, sz, "middle", "m", rot=-90)
    else:
        fg.t(mid, at - gap - k * 0.55, lab, sz, "middle", "m")
    return fg.finish()


def dim_h(name: str, x0: float, x1: float, y: float, *, base: float | None = None, label: str | None = None,
          value: float | None = None, dec: int = 0, fmt: str = "{v}", ends: str = "arrow", over: float = 0.08,
          ext: float = 0.25, sz: float = 12, **kw) -> list[O]:
    """Горизонтальная размерная линия от x0 до x1 на высоте y. base — край измеряемого объекта (выносные линии от него);
    value — число (при Morph подпись считает), fmt — '{v} мм', dec — знаков после запятой; label — готовая подпись.
    ends — arrow | tick (засечка) | dot | open."""
    return _dim(name, "h", x0, x1, y, base, label, value, dec, fmt, ends, over, ext, sz, kw)


def dim_v(name: str, y0: float, y1: float, x: float, *, base: float | None = None, label: str | None = None,
          value: float | None = None, dec: int = 0, fmt: str = "{v}", ends: str = "arrow", over: float = 0.08,
          ext: float = 0.25, sz: float = 12, **kw) -> list[O]:
    """Вертикальная размерная линия от y0 до y1 на абсциссе x (подпись повёрнута, слева от линии)."""
    return _dim(name, "v", y0, y1, x, base, label, value, dec, fmt, ends, over, ext, sz, kw)


def balloon(name: str, anchor: P2, at: P2, num, *, r: float = 0.2, sz: float | None = None, **kw) -> list[O]:
    """Выноска с номером: точка на детали anchor → линия → кружок в at → номер."""
    fg = _Fig(name, "balloon", kw)
    fg.spec.update(anchor=_pl([anchor])[0], at=_pl([at])[0], r=r, num=str(num), sz=sz)
    A, B = tuple(anchor), tuple(at)
    dx, dy = A[0] - B[0], A[1] - B[1]
    L = math.hypot(dx, dy) or 1.0
    fg.f(_circ(A, min(max(fg.lw * 1.8, 0.025), 0.06), 18), zoff=0)
    fg.s([A, (B[0] + dx / L * r, B[1] + dy / L * r)], 0.8)
    fg.s(_arc(B[0], B[1], r, r, 0, 360, 72))
    fg.t(B[0], B[1], num, sz or r * 72 * 0.95, "middle", "m")
    return fg.finish()


def leader(name: str, anchor: P2, elbow: P2, text: str, *, shelf: float | None = None, end: str = "dot",
           sub: str | None = None, sz: float = 13, **kw) -> list[O]:
    """Полка-выноска: метка у точки anchor (dot | arrow | open | tick | none) → линия к elbow → полка длиной shelf
    (− влево; по умолчанию — по длине подписи) → подпись над полкой, sub — под полкой."""
    fg = _Fig(name, "leader", kw)
    if shelf is None:
        shelf = len(text) * sz / 72 * 0.56 + 0.15
        if anchor[0] > elbow[0]:
            shelf = -shelf
    fg.spec.update(anchor=_pl([anchor])[0], elbow=_pl([elbow])[0], shelf=_ff(shelf), text=text, sub=sub, end=end, sz=sz)
    A, E = tuple(anchor), tuple(elbow)
    ln = [A, E]
    if end == "dot":
        fg.f(_circ(A, min(max(fg.lw * 1.8, 0.025), 0.06), 18), zoff=0)
    elif end and end != "none":
        ln = fg.heads([E, A], None, "tri" if end == "arrow" else end)[::-1]
    fg.s(ln, 0.85)
    fg.s([E, (E[0] + shelf, E[1])], 0.85)
    x = E[0] + (0.05 if shelf >= 0 else -0.05)
    an = "start" if shelf >= 0 else "end"
    fg.t(x, E[1] - 0.05, text, sz, an, "b")
    if sub:
        fg.t(x, E[1] + 0.05, sub, sz * 0.8, an, "t")
    return fg.finish()


def brace(name: str, p0: P2, p1: P2, *, side: int = 1, depth: float = 0.22, form: str = "curly", label: str | None = None,
          sz: float = 13, **kw) -> list[O]:
    """Фигурная (form='curly') или квадратная ('square') скобка вдоль отрезка p0→p1; side=±1 — в какую сторону носик
    (для p0→p1 слева направо side=1 — вверх); label — подпись у носика (строки через \\n)."""
    fg = _Fig(name, "brace", kw)
    fg.spec.update(p0=_pl([p0])[0], p1=_pl([p1])[0], side=side, depth=depth, form=form, label=label, sz=sz)
    a, b = tuple(p0), tuple(p1)
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    nx, ny = uy * side, -ux * side
    d = depth

    def M(u, w):
        return (a[0] + ux * u + nx * w, a[1] + uy * u + ny * w)
    if form == "square":
        half = [(L / 2, d), (0, d), (0, 0)]
    else:
        r = min(d / 2, L / 4)
        half = _cubic((L / 2, d), (L / 2, d * .72), (L / 2 - r * .45, d / 2), (L / 2 - r, d / 2), 10) + [(r, d / 2)] + \
            _cubic((r, d / 2), (r * .45, d / 2), (0, d * .22), (0, 0), 10)
    fg.s([M(u, w) for u, w in half])
    fg.s([M(L - u, w) for u, w in half])
    if label:
        tip = M(L / 2, d + 0.07)
        horiz = abs(nx) > abs(ny)
        lines = label.split("\n")
        for i, ln in enumerate(lines):
            k = (i - (len(lines) - 1) / 2) if horiz else (i - (len(lines) - 1) if ny < 0 else i)
            y = tip[1] + k * sz / 72 * 1.25
            if horiz:
                fg.t(tip[0], y, ln, sz, "start" if nx > 0 else "end", "m")
            else:
                fg.t(tip[0], y, ln, sz, "middle", "b" if ny < 0 else "t")
    return fg.finish()


# ----------------------------------------------------------------------------- заливки и пометки
def hatch(name: str, x: float, y: float, w: float, h: float, *, pts: Sequence[P2] | None = None, pattern: str = "hatch",
          angle: float = 45, step: float = 0.12, outline: bool = True, r: float | None = None, **kw) -> list[O]:
    """Штриховка (hatch), клетка (cross), сетка (grid) или растр точками (dots) внутри прямоугольника x, y, w, h или
    контура pts; angle — наклон, step — шаг, r — радиус точки растра; outline — контур."""
    fg = _Fig(name, "hatch", kw)
    fg.spec.update(box=[_ff(x), _ff(y), _ff(w), _ff(h)], pts=_pl(pts) if pts else None, pattern=pattern, angle=angle, step=step,
                   outline=outline, r=r)
    poly = [tuple(p) for p in pts] if pts and len(pts) > 2 else _rect(x, y, w, h)[:4]
    shape = Polygon(poly)
    if not shape.is_valid:
        shape = shape.buffer(0)
    x0, y0, x1, y1 = shape.bounds
    step = max(0.03, step)
    if pattern == "dots":
        rr = r if r is not None else step * 0.27
        dots = []
        yy = y0 + step / 2
        while yy < y1:
            xx = x0 + step / 2
            while xx < x1:
                dots.append(Point(xx, yy).buffer(rr, quad_segs=1))
                xx += step
            yy += step
        g = unary_union(dots).intersection(shape)
        if not g.is_empty:
            fg.groups["main"].append(g)
    else:
        fams = [angle, angle + 90] if pattern == "cross" else ([0, 90] if angle % 90 == 45 else [angle, angle + 90]) if pattern == "grid" else [angle]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        D = math.hypot(x1 - x0, y1 - y0)
        for th in fams:
            ux, uy = math.cos(math.radians(th)), math.sin(math.radians(th))
            nx, ny = -uy, ux
            pr = [(px - cx) * nx + (py - cy) * ny for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
            m0, m1 = min(pr), max(pr)
            m = m0 + ((m1 - m0) % step) / 2
            while m <= m1 + 1e-9:
                px, py = cx + nx * m, cy + ny * m
                seg = LineString([(px - ux * D, py - uy * D), (px + ux * D, py + uy * D)]).intersection(shape)
                if not seg.is_empty:
                    fg.groups["main"].append(seg.buffer(fg.lw * 0.55 / 2, cap_style=2, quad_segs=2))
                m += step
    if outline:
        fg.s(poly + [poly[0]])
    return fg.finish()


def highlight(name: str, x: float, y: float, w: float, h: float, *, passes: int = 2, a: float = 0.45, **kw) -> list[O]:
    """Маркер-выделение: полупрозрачные мазки с неровным краем поверх (или под) текста; цвет по умолчанию accent3."""
    fg = _Fig(name, "highlight", kw, color="accent3")
    fg.spec.update(box=[_ff(x), _ff(y), _ff(w), _ff(h)], passes=passes, a=a)
    if "c" not in fg.spec:
        fg.spec["c"] = fg.color
    n = max(1, passes)
    r = _rng(fg.seed * 13 + 5)
    bw = h / n * 1.3
    for i in range(n):
        yy = y + h * (i + .5) / n + (r() - .5) * h * .06
        xa = x - .05 + r() * .05
        xb = x + w + .04 - r() * .07
        tilt = (r() - .5) * h * .1
        sl = bw * .28
        top, bot = [], []
        for j in range(19):
            t = j / 18
            xx = xa + (xb - xa) * t
            yc = yy + tilt * (2 * t - 1)
            top.append((xx + sl * .5, yc - bw / 2 + (r() - .5) * bw * .07))
            bot.append((xx - sl * .5, yc + bw / 2 + (r() - .5) * bw * .07))
        fg.f(top + bot[::-1], group=f"p{i}", color=fg.color, alpha=a, zoff=0)
    del fg.groups["main"]
    return fg.finish()


def scribble(name: str, x0: float, x1: float, y: float, *, amp: float = 0.06, form: str = "wave", **kw) -> list[O]:
    """Подчёркивание-каракуля под текстом: wave | zigzag | loops | double."""
    fg = _Fig(name, "scribble", kw)
    fg.spec.update(x0=_ff(x0), x1=_ff(x1), y=_ff(y), amp=amp, form=form)
    L, A, r = x1 - x0, amp, _rng(fg.seed * 17 + 1)
    P: list = []
    if form == "zigzag":
        st, i, x = A * 1.4, 0, x0
        while x < x1 + st * .5:
            P.append((min(x, x1), y + (A if i % 2 else -A) * (.7 + r() * .35)))
            x += st * (.8 + r() * .4)
            i += 1
    elif form == "loops":
        R = A * 1.1
        n = max(3, round(L / (R * 2.2)))
        M = n * 24
        for j in range(M + 1):
            t = j / M * n * 2 * math.pi
            P.append((x0 + L * j / M - R * .9 * math.sin(t), y - R * .8 * math.cos(t) + R * .4))
    elif form == "double":
        P = _quad((x0, y), ((x0 + x1) / 2, y + A * .5), (x1, y - A * .3), 20)
        fg.s(_quad((x0 + L * .05, y + A * 1.6), ((x0 + x1) / 2, y + A * 1.9), (x1 - L * .03, y + A * 1.2), 20), 1.15)
    else:
        n = max(2, L / (A * 3.4))
        M = math.ceil(n * 16)
        ph = r() * 6
        P = [(x0 + L * j / M, y + A * math.sin(j / M * n * 2 * math.pi + ph) * (.65 + .35 * math.sin(j / M * 7 + ph))) for j in range(M + 1)]
    fg.s(P, 1.15)
    return fg.finish()


def encircle(name: str, x: float, y: float, w: float, h: float, *, pad: float = 0.12, turns: float = 1.12, **kw) -> list[O]:
    """Обвести от руки рамку x, y, w, h: неровный овал, конец заходит за начало."""
    fg = _Fig(name, "encircle", kw)
    fg.spec.update(box=[_ff(x), _ff(y), _ff(w), _ff(h)], pad=pad, turns=turns)
    cx, cy, rx, ry = x + w / 2, y + h / 2, w / 2 + pad, h / 2 + pad * .85
    r = _rng(fg.seed * 19 + 7)
    a0 = -160 + (r() - .5) * 30
    tilt = math.radians((r() - .5) * 7)
    M = math.ceil(110 * turns)
    ph, ph2 = r() * 6, r() * 6
    P = []
    for j in range(M + 1):
        t = j / M
        a = math.radians(a0 + 360 * turns * t)
        k = 1 + .035 * math.sin(2 * a + ph) + .02 * math.sin(3 * a + ph2) + .07 * (t - .5)
        px, py = rx * k * math.cos(a), ry * k * math.sin(a)
        P.append((cx + px * math.cos(tilt) - py * math.sin(tilt), cy + px * math.sin(tilt) + py * math.cos(tilt)))
    fg.s(P, 1.15)
    return fg.finish()


def mark(name: str, cx: float, cy: float, size: float = 0.4, mark: str = "check", **kw) -> list[O]:
    """Пометка от руки в точке cx, cy: check (галочка) | cross (крест) | asterisk (звёздочка-пометка) | star (звезда)."""
    fg = _Fig(name, "mark", kw)
    fg.spec.update(pos=[_ff(cx), _ff(cy)], size=size, mark=mark)
    s = size

    def p(u, v):
        return (cx + u * s, cy + v * s)
    if mark == "cross":
        fg.s([p(-.38, -.36), p(.4, .38)], 1.4)
        fg.s([p(.37, -.4), p(-.38, .4)], 1.4)
    elif mark == "asterisk":
        for a in (90, 30, 150):
            ux, uy = math.cos(math.radians(a)) * .46, math.sin(math.radians(a)) * .46
            fg.s([p(-ux, -uy), p(ux, uy)], 1.3)
    elif mark == "star":
        fg.s([p(.5 * math.cos(math.radians(-90 + 72 * k)), .5 * math.sin(math.radians(-90 + 72 * k))) for k in (0, 2, 4, 1, 3, 0)], 1.2)
    else:
        fg.s([p(-.42, -.02), p(-.13, .3)] + _quad(p(-.13, .3), p(.06, -.06), p(.46, -.42), 14)[1:], 1.45)
    return fg.finish()


def check(name, cx, cy, size=0.4, **kw):
    return mark(name, cx, cy, size, "check", **kw)


def cross(name, cx, cy, size=0.4, **kw):
    return mark(name, cx, cy, size, "cross", **kw)


def asterisk(name, cx, cy, size=0.4, **kw):
    return mark(name, cx, cy, size, "asterisk", **kw)


# ----------------------------------------------------------------------------- печать, стикер, скотч
def stamp(name: str, cx: float, cy: float, r: float = 0.8, text: str = "", center: str = "", sub: str = "", *,
          form: str = "round", w: float | None = None, h: float | None = None, wear: bool = True, sz: float | None = None,
          tsz: float | None = None, **kw) -> list[O]:
    """Печать: form='round' — два кольца, text по кругу, center в середине (строки через \\n), sub — мелко (дата);
    form='rect' — штамп в двойной рамке w × h с центром cx, cy. wear — «износ» краски. rot по умолчанию −12°."""
    fg = _Fig(name, "stamp", kw, color="accent", rot=-12.0)
    fg.spec.update(form=form, text=text, center=center, sub=sub, wear=wear)
    if "c" not in fg.spec:
        fg.spec["c"] = fg.color
    if form == "rect":
        w = w or 2.4
        h = h or 0.9
        x, y = cx - w / 2, cy - h / 2
        i = min(w, h) * .09
        size = sz or h * 72 * .3
        fg.spec.update(box=[_ff(x), _ff(y), _ff(w), _ff(h)], sz=size)
        fg.s(_rect(x, y, w, h), 1.7)
        fg.s(_rect(x + i, y + i, w - 2 * i, h - 2 * i), 0.8)
        fg.t(x + w / 2, y + h / 2 - (h * .1 if sub else 0), center, size, "middle", "m", bold=True, font="head")
        if sub:
            fg.t(x + w / 2, y + h * .74, sub, size * .42, "middle", "m", font="mono")
    else:
        size = sz or r * 72 * .3
        ts = tsz or r * 72 * .165
        fg.spec.update(pos=[_ff(cx), _ff(cy)], r=r, sz=size, tsz=ts)
        fg.s(_arc(cx, cy, r, r, -90, 270, 96), 1.7)
        fg.s(_arc(cx, cy, r * .74, r * .74, -90, 270, 80), 0.85)
        for sx in (-1, 1):
            fg.f(_circ((cx + sx * r * .87, cy), r * .035, 10), zoff=0)
        lines = center.split("\n") if center else []
        for i, ln in enumerate(lines):
            fg.t(cx, cy + (i - (len(lines) - 1) / 2) * size / 72 * 1.1 - (r * .1 if sub else 0), ln, size, "middle", "m", bold=True, font="head")
        if sub:
            fg.t(cx, cy + r * .42, sub, size * .42, "middle", "m", font="mono")
        n = len(text)
        for i, ch in enumerate(text):  # текст по кругу в .pptx — по буквам
            if ch.strip() == "":
                continue
            a = 128 + 360 * .97 * (i + .5) / max(n, 1)
            rr = r * .8 + ts / 72 * .35
            px, py = cx + rr * math.cos(math.radians(a)), cy + rr * math.sin(math.radians(a))
            k = ts / 72
            fg.texts.append((px - k * .45, py - k * .7, k * .9, k * 1.4, ch, ts, "c", a + 90, True, "head", None))
    out = fg.finish()
    for o in out:  # буквы по кругу и мелкая дата — фактура печати, а не текст для чтения (lint: кегль, контраст)
        if o.lines and o is not out[0]:
            o.meta = dict(o.meta, texture=True, decor=True)
    return out


def sticker(name: str, x: float, y: float, w: float, h: float, text: str = "", *, paper: str = "accent3/30",
            sz: float = 18, tape: bool = False, font: str | None = None, curl: float = 0.07, **kw) -> list[O]:
    """Стикер: лист бумаги paper с тенью и загнутым углом, повёрнут на rot (по умолчанию −3°), текст пишется рукой;
    tape=True — полоска скотча сверху. Вход in.draw-drop — «падает и прилипает»."""
    fg = _Fig(name, "sticker", kw, rot=-3.0)
    fg.spec.update(box=[_ff(x), _ff(y), _ff(w), _ff(h)], text=text, paper=paper, sz=sz, tape=tape, font=font, curl=curl)
    cu = min(w, h) * curl
    pad = min(w, h) * .1
    poly = [(x, y), (x + w, y), (x + w, y + h - cu * 3)] + _quad((x + w, y + h - cu * 3), (x + w - cu * .3, y + h - cu * .3), (x + w - cu * 3, y + h), 10)[1:] + [(x, y + h)]
    fg.f(poly, group="paper", color=paper, zoff=-1)
    if tape:
        tw, th = min(w * .45, 1.1), .26
        tx, ty = x + w / 2 - tw / 2, y - th * .55
        fg.f([(tx, ty + tw * .02), (tx + tw, ty - tw * .02), (tx + tw, ty + th - tw * .02), (tx, ty + th + tw * .02)],
             group="tape", color="accent3", alpha=.5, zoff=1)
    lh = sz / 72 * 1.22
    for i, ln in enumerate(text.split("\n") if text else []):
        fg.t(x + pad, y + pad + lh * (i + .5), ln, sz, "start", "m", font=font)
    del fg.groups["main"]
    return fg.finish()


def tape(name: str, x: float, y: float, w: float = 1.3, h: float = 0.34, *, a: float = 0.5, **kw) -> list[O]:
    """Полоска скотча с рваными концами (полупрозрачная, multiply); rot по умолчанию −6°, цвет accent3."""
    fg = _Fig(name, "tape", kw, color="accent3", rot=-6.0)
    fg.spec.update(box=[_ff(x), _ff(y), _ff(w), _ff(h)], a=a)
    if "c" not in fg.spec:
        fg.spec["c"] = fg.color
    r = _rng(fg.seed * 29 + 1)
    z, n = min(.05, w * .06), 6
    P = [(x, y), (x + w, y)]
    for i in range(1, n):
        P.append((x + w - (z if i % 2 else 0) - r() * z * .4, y + h * i / n))
    P += [(x + w, y + h), (x, y + h)]
    for i in range(n - 1, 0, -1):
        P.append((x + (z if i % 2 else 0) + r() * z * .4, y + h * i / n))
    fg.f(P, group="t", color=fg.color, alpha=a, zoff=0)
    del fg.groups["main"]
    return fg.finish()


# ----------------------------------------------------------------------------- лист, шкалы, приборы
GOST_ROWS = ("Разраб.", "Пров.", "Т.контр.", "Н.контр.", "Утв.")
GOST_EN = {"Изм.": "Rev.", "Лист": "Sheet", "№ докум.": "Doc. no.", "Подп.": "Sign.", "Дата": "Date", "Разраб.": "Drawn",
           "Пров.": "Checked", "Т.контр.": "Tech. check", "Н.контр.": "Std. check", "Утв.": "Approved", "Лит.": "Lit.",
           "Масса": "Mass", "Масштаб": "Scale", "Листов": "Sheets"}


def _gl(s: str) -> str:
    """Графа рамки на языке презентации (morphkit.i18n): как в draw.js."""
    from .i18n import get_lang
    return GOST_EN.get(s, s) if get_lang() == "en" else s


def gost(name: str, *, title: str = "", code: str = "", org: str = "", material: str = "", lit: str = "", mass: str = "",
         scale: str = "1:1", sheet: int = 1, sheets: int = 1, rows: Sequence[Sequence[str]] | None = None,
         margins: tuple[float, float, float, float] = (0.5, 0.15, 0.15, 0.15), bw: float = 4.4,
         slide: tuple[float, float] = (13.333, 7.5), **kw) -> list[O]:
    """Рамка листа (поля слева, сверху, справа, снизу) и основная надпись по форме 1 ГОСТ 2.104 шириной bw:
    обозначение code, наименование title, организация org, материал, литера, масса, масштаб, лист/листов;
    rows — [(фамилия, дата)] для граф Разраб., Пров., Т.контр., Н.контр., Утв."""
    fg = _Fig(name, "gost", kw)
    l, t, r_, b = margins
    x, y, w, h = l, t, slide[0] - l - r_, slide[1] - t - b
    rows = [list(rw) + [""] * (2 - len(rw)) for rw in (rows or [])][:5]
    fg.spec.update(box=[_ff(x), _ff(y), _ff(w), _ff(h)], bw=bw, title=title, code=code, org=org, material=material, lit=lit,
                   mass=mass, scale=scale, sheet=sheet, sheets=sheets, rows=rows)
    u = bw / 185
    bx, by = x + w - bw, y + h - 55 * u

    def L(a, b_, c, d):
        return [(bx + a * u, by + b_ * u), (bx + c * u, by + d * u)]
    fg.s(_rect(x, y, w, h), 1.5)
    thick = [L(0, 0, 185, 0), L(0, 0, 0, 55), L(65, 0, 65, 55), L(65, 15, 185, 15), L(135, 15, 135, 55), L(0, 25, 65, 25),
             L(0, 30, 65, 30), L(65, 40, 185, 40), L(135, 20, 185, 20), L(135, 35, 185, 35)]
    thin = [L(7, 0, 7, 30), L(17, 0, 17, 55), L(40, 0, 40, 55), L(55, 0, 55, 55), L(140, 20, 140, 35), L(145, 20, 145, 35),
            L(150, 15, 150, 35), L(167, 15, 167, 35), L(155, 35, 155, 40)] + [L(0, yy, 65, yy) for yy in (5, 10, 15, 20, 35, 40, 45, 50)]
    for ln in thick:
        fg.s(ln, 1.25, cap=2)
    for ln in thin:
        fg.s(ln, 0.55, cap=2)

    def T(s, ux, uy, mm, anchor="middle", bold=False):
        for j, part in enumerate(str(s).split("\n") if s else []):
            n = len(str(s).split("\n"))
            fg.t(bx + ux * u, by + uy * u + (j - (n - 1) / 2) * mm * u * 72 * 1.1 / 72 * 1.15, part, mm * u * 72 * 1.1, anchor, "m", bold=bold)
    for i, s in enumerate(("Изм.", "Лист", "№ докум.", "Подп.", "Дата")):
        T(_gl(s), (3.5, 12, 28.5, 47.5, 60)[i], 27.5, 2.6)
    for i, s in enumerate(GOST_ROWS):
        T(_gl(s), 1, 32.5 + 5 * i, 2.6, "start")
    for i, rw in enumerate(rows):
        T(rw[0], 18, 32.5 + 5 * i, 2.6, "start")
        T(rw[1], 60, 32.5 + 5 * i, 2.2)
    T(code, 125, 7.5, 5.2, bold=True)
    T(title, 100, 27.5, 4.4, bold=True)
    T(material, 100, 47.5, 3.2)
    T(_gl("Лит."), 142.5, 17.5, 2.6)
    T(_gl("Масса"), 158.5, 17.5, 2.6)
    T(_gl("Масштаб"), 176, 17.5, 2.6)
    T(lit, 142.5, 27.5, 3.4)
    T(mass, 158.5, 27.5, 3.4)
    T(scale, 176, 27.5, 3.4)
    T(f"{_gl('Лист')} {sheet}", 137, 37.5, 2.6, "start")
    T(f"{_gl('Листов')} {sheets}", 157, 37.5, 2.6, "start")
    T(org, 160, 47.5, 3.4, bold=True)
    return fg.finish()


def ruler(name: str, x: float, y: float, length: float, *, vertical: bool = False, v0: float = 0, v1: float = 10,
          major: float = 1, minor: int = 5, unit: str = "", dec: int = 0, side: int = 1, labels: bool = True,
          sz: float = 10, **kw) -> list[O]:
    """Линейка/шкала от точки x, y длиной length: значения v0…v1, подписи через major, minor делений между ними;
    side=±1 — сторона делений (вниз/вправо = 1); unit — единица у последней подписи."""
    fg = _Fig(name, "ruler", kw)
    fg.spec.update(at=[_ff(x), _ff(y)], len=_ff(length), vertical=vertical, v0=v0, v1=v1, major=major, minor=minor, unit=unit,
                   dec=dec, side=side, labels=labels, sz=sz)

    def P(s, d):
        return (x + d * side, y + s) if vertical else (x + s, y + d * side)
    fg.s([P(0, 0), P(length, 0)])
    n = max(1, round((v1 - v0) / major * minor))
    for i in range(n + 1):
        val, s = v0 + (v1 - v0) * i / n, length * i / n
        maj = i % minor == 0
        half = minor % 2 == 0 and i % (minor // 2) == 0
        fg.s([P(s, 0), P(s, .16 if maj or i == n else .11 if half else .065)], .9 if maj else .6, cap=2)
        if (maj or i == n) and labels:
            q = P(s, .16 + .05 + sz / 72 * .6)
            lab = fmt_num(val, dec) + (" " + unit if i == n and unit else "")
            fg.t(q[0], q[1], lab, sz, ("start" if side > 0 else "end") if vertical else "middle", "m", bold=False, font="mono")
    return fg.finish()


def gauge(name: str, cx: float, cy: float, r: float, value: float, *, vmin: float = 0, vmax: float = 100, a0: float = 150,
          sweep: float = 240, major: int = 5, minor: int = 4, zones: Sequence | None = None, label: str = "", dec: int = 0,
          fmt: str = "{v}", needle: str = "accent", sz: float | None = None, **kw) -> list[O]:
    """Спидометр / дуговая шкала: центр cx, cy, радиус r, значение value на шкале vmin…vmax (a0 — угол начала, 0° —
    вправо, по часовой; sweep — размах). zones — [(от, до, цвет)]; label — подпись (единица). Morph и em.draw-to
    поворачивают стрелку к новому значению, число считает."""
    fg = _Fig(name, "gauge", kw)
    fg.spec.update(pos=[_ff(cx), _ff(cy)], r=r, value=value, vmin=vmin, vmax=vmax, a0=a0, sweep=sweep, major=major, minor=minor,
                   zones=[list(zz) for zz in zones] if zones else None, label=label, dec=dec, fmt=fmt, needle=needle, sz=sz)

    def ang(v):
        return math.radians(a0 + sweep * (v - vmin) / ((vmax - vmin) or 1))
    fg.s(_arc(cx, cy, r, r, a0, a0 + sweep, 80), 1.1)
    for i, (f0, f1, zc) in enumerate(zones or []):
        fg.groups.setdefault(f"z{i}", [])
        fg.gstyle[f"z{i}"] = (zc, .85, -1)
        a1, a2 = math.degrees(ang(f0)), math.degrees(ang(f1))
        fg.s(_arc(cx, cy, r * .9, r * .9, a1, a2, 40), w=r * .07, group=f"z{i}")
    n = major * minor
    size = sz or r * 72 * .13
    for i in range(n + 1):
        a = ang(vmin + (vmax - vmin) * i / n)
        maj = i % minor == 0
        r1 = r * (.8 if maj else .87)
        fg.s([(cx + math.cos(a) * r * .97, cy + math.sin(a) * r * .97), (cx + math.cos(a) * r1, cy + math.sin(a) * r1)], w=min(fg.lw * (.9 if maj else .55), r * (.035 if maj else .02)), cap=2)
        if maj:
            fg.t(cx + math.cos(a) * r * .66, cy + math.sin(a) * r * .66, fmt_num(vmin + (vmax - vmin) * i / n), size, bold=False, font="mono")
    a = ang(max(min(value, max(vmin, vmax)), min(vmin, vmax)))
    ca, sa = math.cos(a), math.sin(a)
    nd = [(-r * .15, -r * .028), (r * .8, -r * .007), (r * .83, 0), (r * .8, r * .007), (-r * .15, r * .028)]
    fg.f([(cx + u * ca - v * sa, cy + u * sa + v * ca) for u, v in nd], group="needle", color=needle, alpha=1, zoff=1)
    fg.f(_circ((cx, cy), r * .065, 20), group="needle")
    fg.t(cx, cy + r * .4, fmt_num(value, dec, fmt), r * 72 * .22, bold=True)
    if label:
        fg.t(cx, cy + r * .64, label, size * .95, bold=False)
    return fg.finish()


def clock(name: str, cx: float, cy: float, r: float, h: int = 10, m: float = 10, s: float | None = None, *,
          numerals: bool | str = True, fill: str | None = None, sz: float | None = None, **kw) -> list[O]:
    """Циферблат с часовой, минутной и (если s задано) секундной стрелками; numerals — True | 'roman' | False;
    fill — заливка циферблата. Morph переводит стрелки вперёд, em.draw-run({"minutes": 90}) — часы идут."""
    fg = _Fig(name, "clock", kw)
    t = h * 60 + m
    fg.spec.update(pos=[_ff(cx), _ff(cy)], r=r, t=t, sec=s, numerals=numerals, fill=fill, sz=sz)
    if fill:
        fg.f(_circ((cx, cy), r, 64), group="face", color=fill, alpha=1, zoff=-1)
    fg.s(_arc(cx, cy, r, r, -90, 270, 96), 1.3)
    for i in range(60):
        a = math.radians(i * 6 - 90)
        hh = i % 5 == 0
        r1 = r * (.84 if hh else .92)
        fg.s([(cx + math.cos(a) * r * .97, cy + math.sin(a) * r * .97), (cx + math.cos(a) * r1, cy + math.sin(a) * r1)], w=min(fg.lw * (1.1 if hh else .45), r * (.035 if hh else .015)), cap=2)
    roman = ["XII", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]
    if numerals:
        for i in range(12):
            a = math.radians(i * 30 - 90)
            fg.t(cx + math.cos(a) * r * .7, cy + math.sin(a) * r * .7, roman[i] if numerals == "roman" else str(i or 12), sz or r * 72 * .17)

    def hand(length, tail, wk, mx, deg, group="main"):
        a = math.radians(deg)
        fg.s([(cx - math.cos(a) * r * tail, cy - math.sin(a) * r * tail), (cx + math.cos(a) * r * length, cy + math.sin(a) * r * length)],
             w=min(fg.lw * wk, r * mx), group=group)
    hand(.5, .1, 2.6, .075, (t / 60 % 12) * 30 - 90)
    hand(.76, .12, 1.6, .045, (t % 60) * 6 - 90)
    if s is not None:
        fg.gstyle["sec"] = ("accent", 1.0, 1)
        hand(.86, .18, .7, .02, s * 6 - 90, group="sec")
    fg.f(_circ((cx, cy), r * .045, 16), zoff=0)
    return fg.finish()


# ----------------------------------------------------------------------------- текст и блок-схемы
def write(name: str, x: float, y: float, text: str, *, sz: float = 28, al: str = "l", w: float | None = None,
          lh: float = 1.15, font: str = "hand", wt: int | None = None, **kw) -> list[O]:
    """Рукописная надпись в рамке с левым верхним углом x, y (al — l | c | r внутри ширины w): строки «пишутся» слева
    направо. Шрифт 'hand' — 'Caveat', 'Segoe Print', … (нет — курсив основного шрифта); можно 'head' | 'body' | 'mono'."""
    fg = _Fig(name, "write", kw)
    lines = text.split("\n")
    w = w or max(len(ln) for ln in lines) * sz / 72 * .72 + .3  # с запасом: рукописный шрифт шире
    hh = len(lines) * sz / 72 * lh + .1
    ax = x if al == "l" else x + w / 2 if al == "c" else x + w
    fg.spec.update(at=[_ff(ax), _ff(y)], text=text, sz=sz, al=al, lh=lh, font=font, wt=wt)
    fg.extra_bounds.append((x, y, x + w, y + hh))
    main = O(name, "text", x, y, w, hh, txt=text, sz=sz, col=_col(fg.tc or fg.color)[0], al=al, va="t", spacing=lh / 1.2,
             font=fg.font(font), b=True, meta={"inset": 0.0})
    fg.groups = {}
    from .qa import text_height_in
    main.h = max(main.h, text_height_in(main) + 0.04)  # рукописный шрифт выше обычного — рамка .pptx по замеру
    return fg.finish(main_text=main)


def block(name: str, x: float, y: float, w: float, h: float, text: str = "", *, form: str = "process",
          fill: str | None = None, fa: float = 1.0, sz: float = 14, **kw) -> list[O]:
    """Блок-схема: form — process | terminator | data | decision | document | predef; fill — заливка (роль), текст по
    центру (строки через \\n). Контур рисуется, затем проявляется заливка и подпись."""
    fg = _Fig(name, "block", kw)
    fg.spec.update(box=[_ff(x), _ff(y), _ff(w), _ff(h)], form=form, text=text, fill=fill, fa=fa, sz=sz)
    if form == "terminator":
        r = min(h / 2, w / 2)
        P = [(x + r, y), (x + w - r, y)] + _arc(x + w - r, y + r, r, r, -90, 90, 24)[1:] + [(x + r, y + h)] + _arc(x + r, y + h - r, r, r, 90, 270, 24)[1:]
    elif form == "data":
        k = min(h * .35, w * .15)
        P = [(x + k, y), (x + w, y), (x + w - k, y + h), (x, y + h), (x + k, y)]
    elif form == "decision":
        P = [(x + w / 2, y), (x + w, y + h / 2), (x + w / 2, y + h), (x, y + h / 2), (x + w / 2, y)]
    elif form == "document":
        a = h * .09
        P = [(x, y), (x + w, y), (x + w, y + h - a)] + [(x + w - w * i / 32, y + h - a + a * math.sin(i / 32 * 2 * math.pi)) for i in range(1, 33)] + [(x, y)]
    else:
        P = _rect(x, y, w, h)
        if form == "predef":
            k = min(w * .08, .18)
            fg.s([(x + k, y), (x + k, y + h)], .8)
            fg.s([(x + w - k, y), (x + w - k, y + h)], .8)
    if fill:
        fg.f(P, group="fill", color=fill, alpha=fa, zoff=-1)
    fg.s(P)
    lines = text.split("\n") if text else []
    for i, ln in enumerate(lines):
        fg.t(x + w / 2, y + h / 2 + (i - (len(lines) - 1) / 2) * sz / 72 * 1.22 - (h * .04 if form == "document" else 0), ln, sz, bold=False)
    return fg.finish()


KINDS = ("line", "arrow", "dim", "balloon", "leader", "brace", "hatch", "highlight", "scribble", "encircle", "mark", "stamp",
         "sticker", "tape", "gost", "ruler", "gauge", "clock", "write", "block")
