"""Общие помощники направления C «Псевдо-3D и пространство» (2.5D): проектор, грани с освещением, призмы.

Всё строится как ПЛОСКАЯ геометрия, которую мы проецируем сами (никакого scene3d): Morph переливает проекции,
предпросмотр motion.py показывает их честно.

Главные идеи:
  * Cam3 — ортографическая/перспективная камера (yaw вокруг вертикали, pitch — наклон вниз). Мир: x вправо,
    y вглубь, z вверх. p(pt) -> точка слайда в дюймах.
  * poly() — свободная форма с СОХРАНЁННЫМ порядком вершин и ОБЩЕЙ рамкой (по умолчанию — весь слайд). Общая рамка
    во всех состояниях => Morph двигает вершины строго линейно (x, y, w, h рамки не меняются), без «вздутия».
  * shade() / lit() — цвет грани по нормали и источнику света (свет привязан к зрителю).
  * box() — брусок из видимых граней; prism_side() — боковые грани призмы, у скрытых граней вершины «прилипают»
    к ребру силуэта: соседние грани делят вершины, поэтому при повороте сетка не рвётся и грани не наползают.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from morphkit import O
from morphkit import vector as V
from morphkit.theme import SLIDE_H, SLIDE_W, contrast, mix

FRAME = (0.0, 0.0, SLIDE_W, SLIDE_H)
P3 = tuple[float, float, float]


# ----------------------------------------------------------------------------- камера

@dataclass
class Cam3:
    cx: float = SLIDE_W / 2  # куда на слайде попадает начало мира
    cy: float = SLIDE_H / 2
    s: float = 1.0  # дюймов на единицу мира
    yaw: float = 45.0  # поворот мира вокруг вертикали, градусы
    pitch: float = 35.264  # взгляд сверху вниз (35,264° + yaw 45° = изометрия)
    dist: float | None = None  # перспектива: расстояние до глаза в единицах мира; None — ортография
    light: tuple[float, float, float] = (-0.45, 0.75, 0.50)  # к свету в осях экрана: (вправо, вверх, к зрителю)

    def view(self, p: P3) -> tuple[float, float, float]:
        """-> (x вправо, y вверх на экране, глубина к зрителю)."""
        x, y, z = p
        a, e = math.radians(self.yaw), math.radians(self.pitch)
        xr = x * math.cos(a) - y * math.sin(a)
        yr = x * math.sin(a) + y * math.cos(a)
        up = yr * math.sin(e) + z * math.cos(e)
        dep = -yr * math.cos(e) + z * math.sin(e)
        return xr, up, dep

    def k(self, p: P3) -> float:
        """Масштаб перспективы в точке (1 — ортография)."""
        if self.dist is None:
            return 1.0
        return self.dist / max(self.dist - self.view(p)[2], 1e-3)

    def p(self, p: P3) -> tuple[float, float]:
        x, up, dep = self.view(p)
        f = 1.0 if self.dist is None else self.dist / max(self.dist - dep, 1e-3)
        return self.cx + self.s * x * f, self.cy - self.s * up * f

    def rot_n(self, n: P3) -> tuple[float, float, float]:
        x, y, z = n
        a, e = math.radians(self.yaw), math.radians(self.pitch)
        xr = x * math.cos(a) - y * math.sin(a)
        yr = x * math.sin(a) + y * math.cos(a)
        return xr, yr * math.sin(e) + z * math.cos(e), -yr * math.cos(e) + z * math.sin(e)

    def facing(self, pts: Sequence[P3]) -> float:
        """> 0 — грань смотрит на зрителя (вершины против часовой, если смотреть снаружи). Учитывает перспективу."""
        n = newell(pts)
        if self.dist is None:
            return self.rot_n(n)[2]
        c = [sum(q[i] for q in pts) / len(pts) for i in range(3)]
        cv = self.view(tuple(c))
        eye = (-cv[0], -cv[1], self.dist - cv[2])  # от грани к глазу в осях камеры
        nv = self.rot_n(n)
        return nv[0] * eye[0] + nv[1] * eye[1] + nv[2] * eye[2]

    def lit(self, pts: Sequence[P3]) -> float:
        nx, ny, nz = _unit(self.rot_n(newell(pts)))
        lx, ly, lz = _unit(self.light)
        return nx * lx + ny * ly + nz * lz


def iso(cx: float, cy: float, s: float = 1.0, yaw: float = 45.0, pitch: float = 35.264, dist=None) -> Cam3:
    return Cam3(cx, cy, s, yaw, pitch, dist)


def newell(pts: Sequence[P3]) -> P3:
    nx = ny = nz = 0.0
    m = len(pts)
    for i in range(m):
        x1, y1, z1 = pts[i]
        x2, y2, z2 = pts[(i + 1) % m]
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    return _unit((nx, ny, nz))


def _unit(v):
    L = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / L for c in v)


# ----------------------------------------------------------------------------- цвет

def shade(base: str, t: float, hi: float = 0.38, lo: float = 0.55) -> str:
    """t ∈ [−1, 1]: >0 — к белому (hi), <0 — к чёрному (lo). base — hex."""
    t = max(-1.0, min(1.0, t))
    return mix(base, "FFFFFF", hi * t) if t >= 0 else mix(base, "000000", lo * -t)


def face_col(cam: Cam3, pts: Sequence[P3], base: str, amb: float = 0.15) -> str:
    return shade(base, cam.lit(pts) * 1.1 - 0.35 + amb)


def ink_on(theme, fill_hex: str) -> str:
    """Цвет текста с лучшим контрастом на заливке: ink или bg темы."""
    a, b = theme.c("ink"), theme.c("bg")
    return a if contrast(a, fill_hex) >= contrast(b, fill_hex) else b


# ----------------------------------------------------------------------------- объекты

def poly(name: str, pts: Sequence[tuple[float, float]], fill: str | None = "accent", fa: float = 1.0,
         ln: str | None = None, lw: float = 0.0, la: float = 1.0, z: int = 6, frame=FRAME, grad: dict | None = None,
         world: bool = False, meta: dict | None = None, **kw) -> O:
    """Свободная форма из точек БЕЗ переориентации (порядок вершин = порядок пары Morph). frame=None — своя рамка."""
    pts = [(float(x), float(y)) for x, y in pts]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    if frame is None:
        frame = (min(xs), min(ys), max(max(xs) - min(xs), 1e-3), max(max(ys) - min(ys), 1e-3))
    fx, fy, fw, fh = frame
    norm = [[((x - fx) / fw, (y - fy) / fh) for x, y in pts]]
    bbox = ((min(xs) - fx) / fw, (min(ys) - fy) / fh, (max(xs) - fx) / fw, (max(ys) - fy) / fh)
    m = dict(meta or {})
    m.update({"vec": norm, "bbox": bbox})
    if grad:
        m["grad"] = V._fit_grad(grad, bbox) if grad.get("kind", "linear") == "linear" else grad
    return O(name, "vec", fx, fy, fw, fh, fill=fill, fa=fa, ln=ln, lw=lw, la=la, z=z, world=world, meta=m, **kw)


def gpoly(name: str, g, n: int, **kw) -> O:
    """shapely-фигура -> poly из n точек (resample: один обход, старт сверху)."""
    r = V.resample(g, n)
    return poly(name, list(r.exterior.coords)[:-1], **kw)


def face(name: str, cam: Cam3, pts3: Sequence[P3], base: str, z: int = 6, edge: str | None = None,
         ew: float = 0.75, fa: float = 1.0, col: str | None = None, **kw) -> O:
    pts = [cam.p(q) for q in pts3]
    c = col or face_col(cam, pts3, base)
    kw.setdefault("la", fa)
    return poly(name, pts, fill=c, fa=fa, ln=edge or c, lw=ew, z=z, **kw)


BOX_FACES = {  # вершины против часовой снаружи
    "top": lambda x, y, z, w, d, h: [(x, y, z + h), (x + w, y, z + h), (x + w, y + d, z + h), (x, y + d, z + h)],
    "bot": lambda x, y, z, w, d, h: [(x, y, z), (x, y + d, z), (x + w, y + d, z), (x + w, y, z)],
    "ym": lambda x, y, z, w, d, h: [(x, y, z), (x + w, y, z), (x + w, y, z + h), (x, y, z + h)],
    "yp": lambda x, y, z, w, d, h: [(x + w, y + d, z), (x, y + d, z), (x, y + d, z + h), (x + w, y + d, z + h)],
    "xm": lambda x, y, z, w, d, h: [(x, y + d, z), (x, y, z), (x, y, z + h), (x, y + d, z + h)],
    "xp": lambda x, y, z, w, d, h: [(x + w, y, z), (x + w, y + d, z), (x + w, y + d, z + h), (x + w, y, z + h)],
}


def box(prefix: str, cam: Cam3, x: float, y: float, z0: float, w: float, d: float, h: float, base: str,
        z: int = 10, faces: Sequence[str] = ("ym", "xm", "top"), edge: str | None = None, ew: float = 0.75,
        fa: float = 1.0, top_col: str | None = None, **kw) -> list[O]:
    """Брусок: грани faces (по умолчанию видимые в изометрии yaw 0..90: ym — передняя левая, xm — правая… зависит
    от yaw). Каждая грань — 4 точки; h=0 даёт плоскую плитку (боковые грани нулевой высоты — для роста)."""
    out = []
    for k, f in enumerate(faces):
        pts3 = BOX_FACES[f](x, y, z0, w, d, h)
        col = top_col if (f == "top" and top_col) else None
        if f != "top" and h < 1e-6:  # плоская плитка: свет как у вертикальной грани, чтобы цвет не прыгал
            ref = BOX_FACES[f](x, y, z0, w, d, 1.0)
            col = face_col(cam, ref, base)
        out.append(face(f"{prefix}_{f}", cam, pts3, base, z=z + k, edge=edge, ew=ew, fa=fa, col=col, **kw))
    return out


def iso_faces_for(cam: Cam3) -> tuple[str, ...]:
    """Какие боковые грани бруска видны при данном yaw (вершина — top)."""
    vis = [f for f in ("ym", "yp", "xm", "xp") if cam.facing(BOX_FACES[f](0, 0, 0, 1, 1, 1)) > 1e-6]
    return tuple(vis) + ("top",)


# ----------------------------------------------------------------------------- призма с вращением

def ring_pts(cx: float, cy: float, cz: float, r: float, n: int, phase: float, axis: str = "z") -> list[P3]:
    """n вершин правильного многоугольника вокруг оси (z — вертикаль, x — горизонталь «барабан»)."""
    out = []
    for i in range(n):
        a = math.radians(phase + 360 * i / n)
        if axis == "z":
            out.append((cx + r * math.sin(a), cy - r * math.cos(a), cz))
        else:  # ось x: кольцо в плоскости y-z; угол 0 — к зрителю (−y), растёт вверх
            out.append((cx, cy - r * math.cos(a), cz + r * math.sin(a)))
    return out


def prism_side(prefix: str, cam: Cam3, lo: list[P3], hi: list[P3], base: str | Sequence[str], z: int = 10,
               edge: str | None = None, ew: float = 0.75, cols: Sequence[str] | None = None) -> tuple[list[O], list[int]]:
    """Боковые грани призмы между кольцами lo и hi (одинаковое число вершин, обход согласован).
    Скрытая грань схлопывается в ребро ближайшей видимой вершины: сетка не рвётся при повороте.
    -> (объекты, индексы видимых граней)."""
    n = len(lo)
    quads = [[lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]] for i in range(n)]
    vis = [cam.facing(q) > 1e-6 for q in quads]
    front_v = {i for i in range(n) if vis[i] or vis[i - 1]}
    out, shown = [], []
    for i, q in enumerate(quads):
        b = base if isinstance(base, str) else base[i % len(base)]
        if vis[i]:
            pts = [cam.p(p) for p in q]
            c = cols[i] if cols else face_col(cam, q, b)
            out.append(poly(f"{prefix}{i}", pts, fill=c, ln=edge or c, lw=ew, z=z))
            shown.append(i)
        else:
            # ближайшая видимая вершина по кольцу
            best = None
            for dd in range(1, n):
                for j in (i - dd + 1, i + dd):
                    jj = j % n
                    if jj in front_v:
                        best = jj
                        break
                if best is not None:
                    break
            best = 0 if best is None else best
            a, b2 = cam.p(lo[best]), cam.p(hi[best])
            c = face_col(cam, q, b)
            out.append(poly(f"{prefix}{i}", [a, a, b2, b2], fill=c, ln=c, lw=ew, la=0.0, z=z))
    return out, shown


# ----------------------------------------------------------------------------- линии и ленты

def band(name: str, pts: Sequence[tuple[float, float]], width: float, n: int | None = None, **kw) -> O:
    """Тонкая лента вдоль ломаной (меридиан, орбита): контур = левый край + правый край назад.
    Число точек = 2·len(pts) — одинаково, если в состояниях одинаковое число точек ломаной."""
    L = len(pts)
    left, right = [], []
    for i in range(L):
        x0, y0 = pts[max(i - 1, 0)]
        x1, y1 = pts[min(i + 1, L - 1)]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / ln * width / 2, dx / ln * width / 2
        x, y = pts[i]
        left.append((x + nx, y + ny))
        right.append((x - nx, y - ny))
    return poly(name, left + right[::-1], **kw)


def label(name: str, x: float, y: float, w: float, txt, sz: float = 14, col: str = "ink2", h: float | None = None,
          al: str = "l", b: bool = False, z: int = 60, va: str = "t", font: str = "body", **kw) -> O:
    lines = txt.split("\n") if isinstance(txt, str) else txt
    h = h if h is not None else sz / 72 * 1.25 * len(lines) + 0.08
    return O(name, "text", x, y, w, h, txt=txt, sz=sz, col=col, al=al, b=b, z=z, va=va, font=font, **kw)


def head(t: str, sub: str | None = None, x: float = 0.75, y: float = 0.6, w: float = 6.2) -> list[O]:
    out = [O("!!ttl", "text", x, y, w, 0.62, txt=t, sz=28, b=True, font="head", col="ink", z=70)]
    if sub:
        out.append(O("sub", "text", x, y + 0.68, w, 0.5, txt=sub, sz=15, col="muted", z=70))
    return out


def rgb(theme, role: str) -> str:
    return theme.c(role)


# ----------------------------------------------------------------------------- сцена брусков и кадрирование

def boxes(cam: Cam3, specs: Sequence[dict], z0: int = 10, zstep: int = 4, edge: str | None = None,
          ew: float = 0.75) -> list[O]:
    """Бруски сцены. spec: {n, x, y, z, w, d, h, col, [cam], [zo], [fa], [edge], [top]} — всегда три грани
    ym, xm, top (при yaw 0..90 и pitch 0..90 они не «переворачиваются»: ребром — вырождаются в линию).
    Порядок отрисовки — по глубине центра (zo задаёт явно)."""
    def dep(s):
        c = s.get("cam") or cam
        return c.view((s["x"] + s["w"] / 2, s["y"] + s["d"] / 2, s["z"] + s["h"] / 2))[2]
    order = sorted(range(len(specs)), key=lambda i: dep(specs[i]))
    rank = {i: r for r, i in enumerate(order)}
    out = []
    for i, s in enumerate(specs):
        c = s.get("cam") or cam
        zz = s["zo"] if "zo" in s else z0 + rank[i] * zstep
        out += box(s["n"], c, s["x"], s["y"], s["z"], s["w"], s["d"], s["h"], s["col"], z=zz,
                   edge=s.get("edge", edge), ew=ew, fa=s.get("fa", 1.0), top_col=s.get("top"))
    return out


def vec_bbox(objs: Sequence[O]) -> tuple[float, float, float, float] | None:
    """Габарит всех свободных форм (без подписей и пола с meta nofit)."""
    xs, ys = [], []
    for o in objs:
        if o.kind != "vec" or o.meta.get("nofit") or o.fa < 0.05:
            continue
        for ring in o.meta["vec"]:
            for u, v in ring:
                xs.append(o.x + u * o.w)
                ys.append(o.y + v * o.h)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def fitcam(cam: Cam3, make, ks: Sequence, area: tuple[float, float, float, float]) -> Cam3:
    """Подбирает cx, cy, s камеры так, чтобы формы make(cam, k) всех состояний ks легли в area = (x, y, w, h).
    Одна камера на все состояния — движение не «плавает»."""
    bbs = [vec_bbox(make(cam, k)) for k in ks]
    bbs = [b for b in bbs if b]
    x0, y0 = min(b[0] for b in bbs), min(b[1] for b in bbs)
    x1, y1 = max(b[2] for b in bbs), max(b[3] for b in bbs)
    ax, ay, aw, ah = area
    k = min(aw / max(x1 - x0, 1e-3), ah / max(y1 - y0, 1e-3))
    s1 = cam.s * k
    # X = cx + s*q  =>  q = (X - cx)/s
    qx0, qx1 = (x0 - cam.cx) / cam.s, (x1 - cam.cx) / cam.s
    qy0, qy1 = (y0 - cam.cy) / cam.s, (y1 - cam.cy) / cam.s
    cx1 = ax + aw / 2 - s1 * (qx0 + qx1) / 2
    cy1 = ay + ah / 2 - s1 * (qy0 + qy1) / 2
    return Cam3(cx1, cy1, s1, cam.yaw, cam.pitch, cam.dist, cam.light)


def recam(cam: Cam3, **kw) -> Cam3:
    from dataclasses import replace
    return replace(cam, **kw)


def ensure_contrast(theme, variants):
    """Подписи поверх граней: если цвет текста не проходит контраст к тому, что под ним, — берём ink или bg темы
    (что контрастнее). Те же правила, что у lint (_bg_under). Слайды с камерой мира не трогаем."""
    from dataclasses import replace as _rp
    from morphkit.qa import _bg_under
    for v in variants:
        new = []
        for s in v.slides:
            if s.cam is not None:
                new.append(s)
                continue
            objs = sorted(s.objs, key=lambda o: o.z)  # как в lint: resolve() сортирует по z
            out = []
            for o in s.objs:
                if o.txt is not None and not o.meta.get("texture") and not o.meta.get("decor"):
                    bgc = _bg_under(o, objs, s.bg, theme)
                    need = 3.0 if (o.sz >= 24 or (o.b and o.sz >= 18.5)) else 4.5
                    if contrast(theme.c(o.col), bgc) < need:
                        cands = [theme.c("ink"), theme.c("bg"), "FFFFFF", "000000"]
                        o = o.copy(col=max(cands, key=lambda c: contrast(c, bgc)))
                out.append(o)
            new.append(_rp(s, objs=out))
        v.slides = new
    return variants
