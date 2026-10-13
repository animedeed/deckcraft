"""Предпросмотр движения: Morph, эффекты после перехода и петли — кадрами (PNG-лента, GIF, MP4).

LibreOffice не проигрывает Morph, поэтому движение проверяется здесь: та же модель слайдов, что у сборки
(политика текста, камера), пары по именам, интерполяция как у PowerPoint (положение, размер, поворот по кратчайшему
пути, цвет, прозрачность; перелив свободных форм с одинаковым числом точек, иначе — растворение).

    from morphkit.motion import preview
    preview(slides, theme, "out/motion", which=[3, 4], gif=True, strip=True)   # переходы К слайдам 3 и 4

Это приближение, а не PowerPoint: точные кривые ускорения и некоторые эффекты отличаются. Его задача — увидеть
ошибки движения: что летит поверх текста, что крутится не туда, что исчезает и появляется вместо перелёта.
"""

from __future__ import annotations

import math
import subprocess
from dataclasses import replace
from pathlib import Path

from PIL import Image, ImageDraw

from .model import O, Slide, apply_text_policy, parse_line, resolve
from .presets import duration_ms
from .qa import LINE_HEIGHT, font_obj
from .theme import SLIDE_H, SLIDE_W, Theme

W_PX = 960
SS = 2  # суперсэмплинг


def _ease(t: float) -> float:
    return t * t * (3 - 2 * t)


def _hex(c: str) -> tuple[int, int, int]:
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _lerp(a, b, t):
    return a + (b - a) * t


def _lerp_col(a: str | None, b: str | None, t: float) -> str | None:
    if a is None or b is None:
        return b if t > 0.5 else a
    ca, cb = _hex(a), _hex(b)
    return "".join(f"{round(_lerp(x, y, t)):02X}" for x, y in zip(ca, cb))


# ----------------------------------------------------------------------------- геометрия объекта

def _local_polys(o: O, n_ellipse: int = 72) -> list[list[tuple[float, float]]]:
    """Контуры объекта в дюймах слайда (с учётом поворота)."""
    x, y, w, h = o.x, o.y, o.w, o.h
    k = o.kind
    if k == "vec":
        from .vector import smooth_rings
        rings = [[(x + px * w, y + py * h) for px, py in ring] for ring in smooth_rings(o.meta.get("vec", []), w, h)]
    elif k == "oval":
        rings = [[(x + w / 2 + w / 2 * math.cos(2 * math.pi * i / n_ellipse),
                   y + h / 2 + h / 2 * math.sin(2 * math.pi * i / n_ellipse)) for i in range(n_ellipse)]]
    elif k == "rrect":
        r = min(o.radius if o.radius is not None else min(w, h) * 0.16, w / 2, h / 2)
        pts = []
        for cx, cy, a0 in ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90), (x + r, y + r, 180)):
            for i in range(9):
                a = math.radians(a0 + 90 * i / 8)
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        rings = [pts]
    elif k == "tri":
        rings = [[(x + w / 2, y), (x + w, y + h), (x, y + h)]]
    elif k == "chevron":
        d = min(w, h) * 0.5
        rings = [[(x, y), (x + w - d, y), (x + w, y + h / 2), (x + w - d, y + h), (x, y + h), (x + d, y + h / 2)]]
    else:
        rings = [[(x, y), (x + w, y), (x + w, y + h), (x, y + h)]]
    if o.rot and k != "line":
        cx, cy = x + w / 2, y + h / 2
        a = math.radians(o.rot)
        ca, sa = math.cos(a), math.sin(a)
        rings = [[(cx + (px - cx) * ca - (py - cy) * sa, cy + (px - cx) * sa + (py - cy) * ca) for px, py in ring]
                 for ring in rings]
    return rings


# ----------------------------------------------------------------------------- отрисовка

class Canvas:
    def __init__(self, theme: Theme, bg: str = "bg", w_px: int = W_PX):
        self.theme = theme
        self.w = w_px * SS
        self.h = round(w_px * SLIDE_H / SLIDE_W) * SS
        self.k = self.w / SLIDE_W
        self.img = Image.new("RGBA", (self.w, self.h), _hex(theme.c(bg)) + (255,))

    def px(self, p):
        return p[0] * self.k, p[1] * self.k

    def draw(self, o: O, alpha: float = 1.0, clip: tuple[float, float, float, float] | None = None,
             dx: float = 0.0, dy: float = 0.0, scale: float = 1.0, drot: float = 0.0) -> None:
        if alpha <= 0.003:
            return
        if scale != 1.0 or dx or dy or drot:
            cx, cy = o.x + o.w / 2, o.y + o.h / 2
            o = o.copy(x=cx - o.w * scale / 2 + dx, y=cy - o.h * scale / 2 + dy, w=o.w * scale, h=o.h * scale,
                       sz=o.sz * scale, rot=o.rot + drot)
        th = self.theme
        k = self.k
        rings = [] if o.kind in ("line", "arrow") else _local_polys(o)
        pts_all = [p_ for r in rings for p_ in r] + [(o.x, o.y), (o.x + o.w, o.y + o.h)]
        pad = max(o.lw / 72, 0.02) + 0.02
        bx0 = max(0, math.floor((min(p_[0] for p_ in pts_all) - pad) * k))
        by0 = max(0, math.floor((min(p_[1] for p_ in pts_all) - pad) * k))
        bx1 = min(self.w, math.ceil((max(p_[0] for p_ in pts_all) + pad) * k))
        by1 = min(self.h, math.ceil((max(p_[1] for p_ in pts_all) + pad) * k))
        if bx1 - bx0 < 1 or by1 - by0 < 1:
            return
        W, H = bx1 - bx0, by1 - by0
        loc = lambda p_: (p_[0] * k - bx0, p_[1] * k - by0)  # noqa: E731
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        if o.kind in ("line", "arrow"):
            if o.ln and o.lw > 0:
                d.line([loc((o.x, o.y)), loc((o.x + o.w, o.y + o.h))],
                       fill=_hex(th.c(o.ln)) + (round(255 * o.la),), width=max(1, round(o.lw / 72 * k)))
        else:
            if o.fill is not None and rings and o.kind != "text":
                mask = Image.new("L", (W, H), 0)
                md = ImageDraw.Draw(mask)
                for ri, ring in enumerate(rings):
                    if len(ring) >= 3:
                        md.polygon([loc(p_) for p_ in ring], fill=255 if ri == 0 or o.kind != "vec" else 0)
                grad = o.meta.get("grad")
                if grad:
                    fill_img = self._gradient(o, grad, bx0, by0, W, H)
                else:
                    fill_img = Image.new("RGBA", (W, H), _hex(th.c(o.fill)) + (round(255 * o.fa),))
                layer.paste(fill_img, (0, 0), mask)
            if o.ln and o.lw > 0 and rings and o.kind != "text":
                for ring in rings:
                    pts = [loc(p_) for p_ in ring]
                    d.line(pts + [pts[0]], fill=_hex(th.c(o.ln)) + (round(255 * o.la),),
                           width=max(1, round(o.lw / 72 * k)), joint="curve")
            if o.lines:
                self._text(d, o, bx0, by0)
        if clip is not None:
            cx0, cy0, cx1, cy1 = (v * k for v in clip)
            cx0, cx1 = min(cx0, cx1), max(cx0, cx1)  # линия с отрицательной шириной/высотой
            cy0, cy1 = min(cy0, cy1), max(cy0, cy1)
            m = Image.new("L", (W, H), 0)
            ImageDraw.Draw(m).rectangle([cx0 - bx0, cy0 - by0, cx1 - bx0, cy1 - by0], fill=255)
            a = layer.getchannel("A")
            layer.putalpha(Image.composite(a, Image.new("L", a.size, 0), m))
        if alpha < 1.0:
            layer.putalpha(layer.getchannel("A").point(lambda v: round(v * alpha)))
        self.img.alpha_composite(layer, dest=(bx0, by0))

    def _gradient(self, o: O, grad: dict, bx0: int, by0: int, W: int, H: int) -> Image.Image:
        """Линейный градиент по рамке объекта (с поворотом) сразу в размере локального слоя (numpy)."""
        import numpy as np
        th = self.theme
        stops = grad["stops"]
        ang = math.radians(grad.get("angle", 90) + o.rot)
        ux, uy = math.cos(ang), math.sin(ang)
        fx0, fy0 = o.x * self.k - bx0, o.y * self.k - by0
        fw, fh = max(o.w * self.k, 1e-6), max(o.h * self.k, 1e-6)
        xs = (np.arange(W) + 0.5 - fx0) / fw - 0.5
        ys = (np.arange(H) + 0.5 - fy0) / fh - 0.5
        X, Y = np.meshgrid(xs, ys)
        t = np.clip((X * ux + Y * uy) / (abs(ux) + abs(uy)) + 0.5, 0, 1)
        pos = [st[0] for st in stops]
        cols = [_hex(th.c(st[1])) for st in stops]
        alph = [(st[2] if len(st) > 2 else 1.0) * o.fa for st in stops]
        arr = np.zeros((H, W, 4), dtype=np.uint8)
        for c in range(3):
            arr[..., c] = np.interp(t, pos, [col[c] for col in cols]).astype(np.uint8)
        arr[..., 3] = (np.interp(t, pos, alph) * 255).astype(np.uint8)
        return Image.fromarray(arr, "RGBA")

    def _text(self, d: ImageDraw.ImageDraw, o: O, ox: float = 0.0, oy: float = 0.0) -> None:
        th = self.theme
        inset = o.meta.get("inset", 0.0 if o.kind == "text" else 0.12)
        size_px = o.sz / 72 * self.k
        line_h = o.sz * LINE_HEIGHT * o.spacing / 72 * self.k
        lines = o.lines
        total_h = line_h * len(lines) + (len(lines) - 1) * o.para_gap / 72 * self.k
        bx, by, bw, bh = o.x * self.k - ox, o.y * self.k - oy, o.w * self.k, o.h * self.k
        ins = inset * self.k
        y = {"t": by + ins, "m": by + (bh - total_h) / 2, "b": by + bh - ins - total_h}.get(o.va, by + ins)
        for line in lines:
            runs = parse_line(line)
            widths, fonts = [], []
            for r in runs:
                face = th.font("mono" if r.mono else o.font)
                f = font_obj(th.qa_font(face), o.b if r.bold is None else r.bold, max(1, round(size_px)))
                fonts.append(f)
                widths.append(f.getlength(r.text.upper() if o.caps else r.text))
            lw = sum(widths)
            x = {"l": bx + ins, "c": bx + (bw - lw) / 2, "r": bx + bw - ins - lw}.get(o.al, bx + ins)
            for r, f, wdt in zip(runs, fonts, widths):
                col = th.c(r.color or o.col)
                d.text((x, y + (line_h - size_px * 1.15) / 2), r.text.upper() if o.caps else r.text, font=f,
                       fill=_hex(col) + (255,))
                x += wdt
            y += line_h + o.para_gap / 72 * self.k

    def frame(self) -> Image.Image:
        return self.img.resize((self.w // SS, self.h // SS), Image.LANCZOS).convert("RGB")


# ----------------------------------------------------------------------------- состояния

def _interp(a: O, b: O, t: float) -> list[tuple[O, float]]:
    """Пара Morph в момент t: один объект (перелив) или два с растворением (несовместимая геометрия)."""
    d_rot = ((b.rot - a.rot + 180) % 360) - 180
    base = dict(x=_lerp(a.x, b.x, t), y=_lerp(a.y, b.y, t), w=_lerp(a.w, b.w, t), h=_lerp(a.h, b.h, t),
                rot=a.rot + d_rot * t, fa=_lerp(a.fa, b.fa, t), la=_lerp(a.la, b.la, t), lw=_lerp(a.lw, b.lw, t),
                sz=_lerp(a.sz, b.sz, t), fill=_lerp_col(a.fill, b.fill, t) if a.fill and b.fill else (b.fill or a.fill),
                ln=_lerp_col(a.ln, b.ln, t) if a.ln and b.ln else (b.ln or a.ln))
    if a.fill is None and b.fill is not None:
        base["fa"] = b.fa * t
    if a.fill is not None and b.fill is None:
        base["fa"] = a.fa * (1 - t)
    if a.kind == b.kind == "vec":
        ra, rb = a.meta.get("vec", []), b.meta.get("vec", [])
        if [len(r) for r in ra] == [len(r) for r in rb]:
            rings = [[(_lerp(p[0], q[0], t), _lerp(p[1], q[1], t)) for p, q in zip(r1, r2)] for r1, r2 in zip(ra, rb)]
            meta = dict(b.meta, vec=rings)
            if a.meta.get("grad") and b.meta.get("grad"):
                meta["grad"] = b.meta["grad"] if t > 0.5 else a.meta["grad"]
            return [(b.copy(**base, meta=meta), 1.0)]
        return [(a.copy(**base), 1 - t), (b.copy(**base), t)]
    if a.kind != b.kind:
        return [(a.copy(**base), 1 - t), (b.copy(**base), t)]
    return [(b.copy(**base, meta=b.meta if t > 0.5 else a.meta), 1.0)]


FX_START = 0.15  # шкала слайда стартует после перехода


def _fx_plan(slide: Slide) -> dict[str, tuple[str, float, float, dict]]:
    """Имя -> (ключ эффекта, старт с, длительность с, опции) по правилам старта with/after/at."""
    plan, prev, end = {}, 0.0, 0.0
    for f in slide.fx:
        dur = duration_ms(f) / 1000
        lag = f.delay
        start = {"with": prev + lag, "after": end + lag, "at": lag}.get(f.start, lag)
        plan.setdefault(f.target, (f.key, start, dur, dict(f.options)))
        prev = start
        if not getattr(f, "repeat", None):
            end = max(end, start + dur)
    return plan


def _fx_state(o: O, fx: tuple | None, t: float) -> dict | None:
    """Параметры отрисовки объекта с эффектом в момент t (с после конца перехода). None — не виден."""
    if fx is None:
        return {}
    key, start, dur, opt = fx
    p = (t - start) / max(dur, 1e-6)
    entrance = key.startswith("entrance")
    if entrance and p <= 0:
        return None
    if not entrance:
        return {}
    p = min(max(p, 0.0), 1.0)
    e = _ease(p)
    if "wipe" in key:
        dirn = opt.get("direction", "down")
        lx0, lx1 = sorted((o.x, o.x + o.w))
        ly0, ly1 = sorted((o.y, o.y + o.h))
        x0, y0, x1, y1 = lx0 - 0.05, ly0 - 0.05, lx1 + 0.05, ly1 + 0.05
        if dirn == "left":
            x1 = x0 + (x1 - x0) * e
        elif dirn == "right":
            x0 = x1 - (x1 - x0) * e
        elif dirn == "up":
            y0 = y1 - (y1 - y0) * e
        else:
            y1 = y0 + (y1 - y0) * e
        if o.rot or o.kind == "vec":  # повёрнутая форма: рамка поворота шире — клип по габариту контура
            pts = [p_ for r in _local_polys(o) for p_ in r] or [(o.x, o.y)]
            minx, maxx = min(p_[0] for p_ in pts), max(p_[0] for p_ in pts)
            miny, maxy = min(p_[1] for p_ in pts), max(p_[1] for p_ in pts)
            if dirn == "left":
                x0, x1 = minx - 0.05, minx + (maxx - minx + 0.1) * e
            elif dirn == "right":
                x0, x1 = maxx - (maxx - minx + 0.1) * e, maxx + 0.05
            elif dirn == "up":
                y0, y1 = maxy - (maxy - miny + 0.1) * e, maxy + 0.05
            else:
                y0, y1 = miny - 0.05, miny + (maxy - miny + 0.1) * e
        return {"clip": (x0, y0, x1, y1)}
    if "fly" in key:
        dirn = opt.get("direction", "down")
        off = {"left": (-(o.x + o.w), 0), "right": (SLIDE_W - o.x, 0), "up": (0, -(o.y + o.h)),
               "down": (0, SLIDE_H - o.y)}.get(dirn, (0, SLIDE_H - o.y))
        return {"dx": off[0] * (1 - e), "dy": off[1] * (1 - e)}
    if "rise" in key:
        return {"dy": 0.35 * (1 - e), "alpha": e}
    if "spinner" in key or "pinwheel" in key:
        return {"drot": -90 * (1 - e), "scale": 0.2 + 0.8 * e, "alpha": e}
    if "zoom" in key or "grow" in key or "expand" in key:
        return {"scale": 0.3 + 0.7 * e, "alpha": e}
    if "appear" in key:
        return {}
    return {"alpha": e}


def _loop_objs(slide: Slide, objs: list[O], t: float, theme: Theme) -> list[tuple[O, dict]]:
    by = {o.name: o for o in objs}
    out = []
    for lp in slide.loops:
        tt = t - FX_START - lp.start
        if tt < 0:
            continue
        if lp.kind == "flow" and lp.points:
            pts = list(reversed(lp.points)) if lp.reverse else list(lp.points)
            seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
            L = sum(seg) or 1
            for i in range(lp.n):
                ph = (tt / lp.period + i / lp.n) % 1.0
                dd, k = ph * L, 0
                while k < len(seg) - 1 and dd > seg[k]:
                    dd -= seg[k]
                    k += 1
                a, b = pts[k], pts[k + 1]
                f = dd / (seg[k] or 1)
                x, y = _lerp(a[0], b[0], f), _lerp(a[1], b[1], f)
                out.append((O(f"loopdot{i}", "oval", x - lp.size / 2, y - lp.size / 2, lp.size, lp.size,
                              fill=lp.color, z=lp.z), {}))
        elif lp.target in by:
            tg = by[lp.target]
            ph = (tt % lp.period) / lp.period
            if lp.kind == "ripple":
                s = 1 + (lp.scale - 1) * ph
                out.append((tg.copy(name="rip", fill=None, ln=lp.color, lw=2.0, la=1 - ph, txt=None, kind="oval"),
                            {"scale": s}))
            elif lp.kind == "pulse":
                out.append((tg, {"scale": 1 + (lp.scale - 1) * math.sin(math.pi * ph), "_replace": True}))
            elif lp.kind == "spin":
                out.append((tg, {"drot": (-360 if lp.reverse else 360) * ph, "_replace": True}))
            elif lp.kind == "blink":
                out.append((tg, {"alpha": 0.25 + 0.75 * abs(math.cos(math.pi * ph)), "_replace": True}))
    return out


# ----------------------------------------------------------------------------- кадры перехода и слайда

NATIVE = {"zoom", "cube", "rotate", "fly_through", "gallery", "pan", "push", "ripple", "vortex", "shred", "page_curl",
          "origami", "curtains", "cover", "uncover", "wipe", "fade"}


def _native_frame(a: Image.Image, b: Image.Image, kind: str, t: float, bg) -> Image.Image:
    """Приближение нативного перехода PowerPoint из двух статичных кадров (для превью и GIF, не точная копия)."""
    W, H = a.size
    out = Image.new("RGB", (W, H), bg)

    def scaled(img, k, alpha=1.0, cx=0.5, cy=0.5):
        w, h = max(1, int(W * k)), max(1, int(H * k))
        im = img.resize((w, h), Image.BILINEAR)
        x, y = int(W * cx - w / 2), int(H * cy - h / 2)
        if alpha >= 1:
            out.paste(im, (x, y))
        else:
            base = out.crop((x, y, x + w, y + h)) if x >= 0 and y >= 0 else None
            if base is None:
                out.paste(Image.blend(Image.new("RGB", (w, h), bg), im, alpha), (x, y))
            else:
                out.paste(Image.blend(base, im, alpha), (x, y))

    if kind == "zoom":  # новый слайд вырастает из центра, старый растёт и тает
        scaled(a, 1 + 0.25 * t, 1 - t)
        scaled(b, 0.35 + 0.65 * t, min(1, t * 1.6))
    elif kind == "fly_through":  # камера пролетает сквозь старый слайд
        scaled(b, 0.7 + 0.3 * t, min(1, t * 1.3))
        if t < 0.85:
            scaled(a, 1 + 1.2 * t, max(0.0, 1 - t / 0.85))
    elif kind in ("cube", "rotate"):  # грань уходит влево, новая разворачивается справа
        wa, wb = max(1, int(W * (1 - t))), max(1, int(W * t))
        ia = a.resize((wa, H), Image.BILINEAR)
        ib = b.resize((wb, H), Image.BILINEAR)
        shade = Image.new("RGB", (wa, H), (0, 0, 0))
        out.paste(Image.blend(ia, shade, 0.35 * t), (0, 0))
        out.paste(Image.blend(ib, Image.new("RGB", (wb, H), (0, 0, 0)), 0.35 * (1 - t)), (W - wb, 0))
    elif kind in ("push", "pan", "gallery"):
        dx = int(W * t)
        out.paste(a, (-dx, 0)); out.paste(b, (W - dx, 0))
    elif kind == "cover":
        out.paste(a, (0, 0)); out.paste(b, (int(W * (1 - t)), 0))
    elif kind == "uncover":
        out.paste(b, (0, 0)); out.paste(a, (-int(W * t), 0))
    elif kind == "curtains":  # половины старого слайда расходятся
        out.paste(b, (0, 0))
        dx = int(W / 2 * t)
        out.paste(a.crop((0, 0, W // 2, H)), (-dx, 0)); out.paste(a.crop((W // 2, 0, W, H)), (W // 2 + dx, 0))
    elif kind == "ripple":  # круг нового слайда расходится из центра
        out.paste(a, (0, 0))
        m = Image.new("L", (W, H), 0)
        r = int(math.hypot(W, H) / 2 * t)
        ImageDraw.Draw(m).ellipse((W // 2 - r, H // 2 - r, W // 2 + r, H // 2 + r), fill=255)
        out.paste(b, (0, 0), m)
    elif kind == "vortex":
        out.paste(b, (0, 0))
        if t < 0.9:
            k = 1 - t / 0.9
            im = a.rotate(-300 * t, resample=Image.BILINEAR, fillcolor=bg).resize((max(1, int(W * k)), max(1, int(H * k))))
            out.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
    elif kind == "shred":
        out.paste(b, (0, 0))
        n = 12
        for i in range(n):
            x0, x1 = W * i // n, W * (i + 1) // n
            dy = int(H * max(0.0, t * 1.6 - 0.5 * i / n) ** 2)
            if dy < H:
                out.paste(a.crop((x0, 0, x1, H)), (x0, dy))
    elif kind in ("page_curl", "origami"):  # лист складывается к левому краю
        out.paste(b, (0, 0))
        w = max(1, int(W * (1 - t)))
        im = a.resize((w, H), Image.BILINEAR)
        out.paste(Image.blend(im, Image.new("RGB", (w, H), (255, 255, 255)), 0.25 * t), (0, 0))
    elif kind == "wipe":
        out.paste(a, (0, 0)); x = int(W * t)
        out.paste(b.crop((0, 0, max(1, x), H)), (0, 0))
    else:
        out = Image.blend(a, b, t)
    return out


def render_transition(prev: Slide | None, cur: Slide, theme: Theme, fps: int = 15, hold: float | None = None,
                      w_px: int = W_PX) -> list[Image.Image]:
    """Кадры: переход prev -> cur (Morph или растворение), затем шкала эффектов и петли cur."""
    hexify = lambda o: o.copy(fill=theme.c(o.fill), ln=theme.c(o.ln), col=theme.c(o.col))  # noqa: E731
    a_objs = [hexify(o) for o in resolve(prev)] if prev else []
    b_objs = [hexify(o) for o in resolve(cur)]
    frames = []
    dur = cur.dur / 1000 if cur.transition not in ("none",) else 0.0
    n_tr = max(1, round(dur * fps)) if prev else 0
    by_a = {o.name: o for o in a_objs}
    by_b = {o.name: o for o in b_objs}
    plan = _fx_plan(cur)
    morph = cur.transition == "morph"
    native = prev is not None and not morph and cur.transition in NATIVE and cur.transition != "fade"
    if native:  # нативный переход: статичный конец prev и начало cur, сведённые приближением
        def still(objs, skip_entr=False):
            cv = Canvas(theme, (prev if not skip_entr else cur).bg, w_px)
            for o in sorted(objs, key=lambda o: o.z):
                if skip_entr and plan.get(o.name) and plan[o.name][0].startswith("entrance"):
                    continue
                cv.draw(o, 1.0)
            return cv.frame().convert("RGB")
        ia, ib = still(a_objs), still(b_objs, True)
        bgc = tuple(int(theme.c(cur.bg)[i:i + 2], 16) for i in (0, 2, 4))
        for k in range(n_tr):
            frames.append(_native_frame(ia, ib, cur.transition, _ease((k + 1) / n_tr), bgc))
        n_tr = 0
    for k in range(n_tr):
        t = _ease((k + 1) / n_tr)
        cv = Canvas(theme, cur.bg, w_px)
        items = []
        if morph:
            for o in a_objs:
                if o.name in by_b and o.name.startswith("!!"):
                    for oo, al in _interp(o, by_b[o.name], t):
                        hidden_in_b = plan.get(o.name) and plan[o.name][0].startswith("entrance")
                        items.append((oo.z, oo, al * ((1 - t) if hidden_in_b else 1.0)))
                else:
                    items.append((o.z, o, 1 - t))
            for o in b_objs:
                if not (o.name in by_a and o.name.startswith("!!")):
                    if plan.get(o.name) and plan[o.name][0].startswith("entrance"):
                        continue  # появится эффектом после перехода
                    items.append((o.z, o, t))
        else:
            items = [(o.z, o, 1 - t) for o in a_objs] + [(o.z, o, t) for o in b_objs
                                                          if not (plan.get(o.name) and plan[o.name][0].startswith("entrance"))]
        for _, o, al in sorted(items, key=lambda it: it[0]):
            cv.draw(o, al)
        frames.append(cv.frame())
    span = max([s + d for _, s, d, _ in plan.values()] + [0.0]) + FX_START
    hold = hold if hold is not None else (max(span + 0.6, 1.2) if (plan or cur.loops) else 0.6)
    for k in range(max(1, round(hold * fps))):
        t = k / fps
        cv = Canvas(theme, cur.bg, w_px)
        loops = _loop_objs(cur, b_objs, t, theme)
        repl = {o.name: st for o, st in loops if st.get("_replace")}
        extra = [(o, st) for o, st in loops if not st.get("_replace")]
        draw_list = []
        for o in b_objs:
            st = _fx_state(o, plan.get(o.name), t - FX_START)
            if st is None:
                continue
            st = dict(st)
            st.update({k2: v for k2, v in repl.get(o.name, {}).items() if k2 != "_replace"})
            draw_list.append((o.z, o, st))
        for o, st in extra:
            draw_list.append((o.z, o, st))
        for _, o, st in sorted(draw_list, key=lambda it: it[0]):
            cv.draw(o, st.get("alpha", 1.0), st.get("clip"), st.get("dx", 0), st.get("dy", 0), st.get("scale", 1.0),
                    st.get("drot", 0.0))
        frames.append(cv.frame())
    return frames


def strip(frames: list[Image.Image], n: int = 6, out: str | Path | None = None, label: str = "") -> Image.Image:
    """Лента из n равномерно взятых кадров (для проверки глазами)."""
    idx = [round(i * (len(frames) - 1) / max(n - 1, 1)) for i in range(n)]
    w, h = frames[0].size
    sw = w // 2
    sh = h // 2
    img = Image.new("RGB", (sw * n + 4 * (n - 1), sh + (22 if label else 0)), (235, 235, 235))
    d = ImageDraw.Draw(img)
    if label:
        d.text((4, 3), label, fill=(30, 30, 30), font=font_obj("DejaVu Sans", True, 14))
    for k, i in enumerate(idx):
        img.paste(frames[i].resize((sw, sh)), (k * (sw + 4), 22 if label else 0))
    if out:
        img.save(out)
    return img


def save_gif(frames: list[Image.Image], out: str | Path, fps: int = 15, w: int = 640) -> Path:
    out = Path(out)
    small = [f.resize((w, round(w * f.size[1] / f.size[0]))) for f in frames]
    small[0].save(out, save_all=True, append_images=small[1:], duration=round(1000 / fps), loop=0, optimize=True)
    return out


def save_mp4(frames: list[Image.Image], out: str | Path, fps: int = 15) -> Path:
    out = Path(out)
    tmp = out.with_suffix("")
    tmp.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(frames):
        f.save(tmp / f"f{i:04d}.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(tmp / "f%04d.png"),
                    "-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", str(out)], check=True)
    for p in tmp.glob("*.png"):
        p.unlink()
    tmp.rmdir()
    return out


def preview(slides: list[Slide], theme: Theme, out_dir: str | Path, which: list[int] | None = None,
            gif: bool = True, strip_n: int = 6, mp4: bool = False, fps: int = 15, policy: str = "fade",
            w_px: int = W_PX) -> list[Path]:
    """Переходы К слайдам which (номера с 1; по умолчанию все): ленты кадров и GIF. Возвращает пути лент."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slides = apply_text_policy(slides, policy)
    which = which or list(range(1, len(slides) + 1))
    paths, all_frames = [], []
    for i in which:
        prev = slides[i - 2] if i > 1 else None
        fr = render_transition(prev, slides[i - 1], theme, fps=fps, w_px=w_px)
        all_frames += fr
        p = out_dir / f"t{i:02d}.png"
        strip(fr, strip_n, p, label=f"→ {i}: {slides[i - 1].title} · {slides[i - 1].technique}")
        paths.append(p)
        if gif:
            save_gif(fr, out_dir / f"t{i:02d}.gif", fps=fps)
    if mp4 and all_frames:
        save_mp4(all_frames, out_dir / "deck.mp4", fps=fps)
    return paths


__all__ = ["preview", "render_transition", "strip", "save_gif", "save_mp4", "Canvas"]
