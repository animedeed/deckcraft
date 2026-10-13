"""Компоненты технических и учебных колод. Каждый метод возвращает список O.

Имена строятся от id: одинаковый id на соседних слайдах -> пара Morph. Пример:
    k = Kit(theme)
    objs = k.label("ПРАКТИКА 1") + k.title("Паспорт данных") + k.node("raw", 1, 3, 2, 1, "data/raw")
"""

from __future__ import annotations

import keyword
import re
from dataclasses import dataclass

from .model import Loop, O, Run
from .theme import SLIDE_H, SLIDE_W, Theme

PY_BUILTINS = {"print", "len", "range", "float", "int", "str", "list", "dict", "set", "open", "sum", "min", "max",
               "abs", "zip", "enumerate", "sorted", "isinstance", "super", "True", "False", "None"}
_TOKEN = re.compile(r"(#.*$)|(\"[^\"]*\"|'[^']*')|(\b\d+(?:\.\d+)?(?:e-?\d+)?\b)|([A-Za-z_][A-Za-z0-9_]*)|(\s+)|(.)")


def highlight_python(line: str) -> list[Run]:
    """Простая подсветка Python: ключевые слова, строки, числа, комментарии. Цвета — роли темы code_*."""
    runs: list[Run] = []
    for m in _TOKEN.finditer(line):
        com, string, num, ident, space, other = m.groups()
        if com:
            runs.append(Run(com, color="code_com"))
        elif string:
            runs.append(Run(string, color="code_str"))
        elif num:
            runs.append(Run(num, color="code_num"))
        elif ident:
            runs.append(Run(ident, color="code_kw" if keyword.iskeyword(ident) or ident in PY_BUILTINS else None))
        else:
            runs.append(Run(space or other))
    merged: list[Run] = []
    for r in runs:  # склеиваем соседние прогоны одного цвета — меньше XML
        if merged and merged[-1].color == r.color:
            merged[-1] = Run(merged[-1].text + r.text, color=r.color)
        else:
            merged.append(r)
    return merged or [Run("")]


@dataclass
class Kit:
    t: Theme

    def fit(self, lines: list[str], w: float, sz: float, font: str = "body", bold: bool = False,
            floor: float | None = None, step: float = 0.94) -> float:
        """Наибольший кегль <= sz, при котором каждая строка помещается в ширину w (метрики шрифта-заменителя)."""
        from .qa import line_width_in
        floor = floor or self.t.density.min_any_pt
        size = sz
        while size > floor:
            probe = O("probe", "text", 0, 0, w, 1, txt=lines, sz=size, font=font, b=bold)
            if all(line_width_in(self.t, probe, l) <= w * 0.97 for l in lines):
                return round(size, 1)
            size *= step
        return floor

    # ------------------------------------------------------------------ типографика
    def label(self, text: str, id: str = "sec", x: float | None = None, y: float | None = None,
              color: str = "accent", w: float = 8.0) -> list[O]:
        g = self.t.grid
        return [O(f"!!{id}", "text", g.margin_x if x is None else x, g.margin_top if y is None else y, w, 0.3,
                  txt=text, sz=self.t.scale.label, col=color, b=True, caps=True, tracking=1.5, z=20)]

    def folio(self, n: int, total: int, id: str = "folio") -> list[O]:
        g = self.t.grid
        return [O(f"!!{id}", "text", SLIDE_W - g.margin_x - 1.4, SLIDE_H - g.margin_bottom - 0.12, 1.4, 0.3,
                  txt=f"{n:02d} / {total:02d}", sz=self.t.scale.label, col="muted", al="r", font="mono", z=20)]

    def title(self, text: str, id: str = "ttl", x: float | None = None, y: float = 0.95, w: float | None = None,
              size: str = "h1", color: str = "ink") -> list[O]:
        g = self.t.grid
        lines = text.split("\n")
        ww = g.content_w if w is None else w
        sz = self.fit(lines, ww, getattr(self.t.scale, size), font="head", bold=self.t.head_bold)
        h = len(lines) * sz * 1.12 / 72 + 0.05
        return [O(f"!!{id}", "text", g.margin_x if x is None else x, y, ww, h, txt=lines,
                  sz=sz, col=color, font="head", b=self.t.head_bold, spacing=0.95, z=20)]

    def text(self, id: str, x: float, y: float, w: float, txt: str, size: str = "body", color: str = "ink2",
             bullets: bool = False, al: str = "l", b: bool = False, h: float | None = None, font: str = "body",
             gap: float = 4) -> list[O]:
        sz = getattr(self.t.scale, size) if isinstance(size, str) else size
        lines = txt.split("\n")
        sz = self.fit(lines, w - (0.25 if bullets else 0), sz, font=font, bold=b)
        hh = h if h is not None else len(lines) * sz * 1.2 * self.t.scale.line / 72 + max(len(lines) - 1, 0) * gap / 72 + 0.05
        return [O(id, "text", x, y, w, hh, txt=lines, sz=sz, col=color, bullets=bullets, al=al, b=b, font=font,
                  spacing=self.t.scale.line, para_gap=gap, z=20)]

    # ------------------------------------------------------------------ блоки
    def card(self, id: str, x: float, y: float, w: float, h: float, title: str | None = None, body: str | None = None,
             fill: str = "surface", title_color: str = "ink", body_color: str = "ink2", kicker: str | None = None,
             kicker_color: str = "accent", line: str | None = None, body_size: str = "small", z: int = 8) -> list[O]:
        pad = 0.22
        out = [O(f"!!{id}", "rrect", x, y, w, h, fill=fill, ln=line, lw=1.0 if line else 0, z=z)]
        cy = y + pad
        if kicker:
            out.append(O(f"!!{id}_k", "text", x + pad, cy, w - 2 * pad, 0.28, txt=kicker, sz=self.t.scale.label,
                         col=kicker_color, b=True, caps=True, tracking=1.2, z=z + 2))
            cy += 0.34
        if title:
            tl = title.split("\n")
            th = len(tl) * self.t.scale.lead * 1.15 / 72 + 0.04
            out.append(O(f"!!{id}_t", "text", x + pad, cy, w - 2 * pad, th, txt=tl, sz=self.t.scale.lead,
                         col=title_color, font="head", b=True, z=z + 2))
            cy += th + 0.08
        if body:
            bl = body.split("\n")
            bsz = self.fit(bl, w - 2 * pad, getattr(self.t.scale, body_size))
            out.append(O(f"!!{id}_b", "text", x + pad, cy, w - 2 * pad, max(y + h - pad - cy, 0.3), txt=bl, sz=bsz,
                         col=body_color, spacing=self.t.scale.line, para_gap=3, z=z + 2))
        return out

    def stat(self, id: str, x: float, y: float, w: float, value: str, label: str, color: str = "accent",
             size: float | None = None, label_color: str = "ink2") -> list[O]:
        sz = size or self.t.scale.display
        vh = sz * 1.05 / 72
        ll = label.split("\n")
        return [O(f"!!{id}_v", "text", x, y, w, vh, txt=value, sz=sz, col=color, font="head", b=self.t.head_bold, z=20),
                O(f"!!{id}_l", "text", x, y + vh + 0.02, w, len(ll) * self.t.scale.small * 1.25 / 72 + 0.05, txt=ll,
                  sz=self.t.scale.small, col=label_color, z=20)]

    def rail(self, steps: list[str], active: int, id: str = "rail", y: float = 0.45, x0: float | None = None,
             w: float | None = None, done_color: str = "muted") -> list[O]:
        """Таблетки шагов в шапке: текущий шаг раскрыт и выделен, пройденные приглушены."""
        g = self.t.grid
        x0 = g.margin_x if x0 is None else x0
        w = g.content_w if w is None else w
        n = len(steps)
        gap = 0.1
        small_w = (w - gap * (n - 1)) / (n + 1.6)
        big_w = small_w * 2.6
        out, x = [], x0
        for i, s in enumerate(steps):
            ww = big_w if i == active else small_w
            is_active = i == active
            fill = "accent" if is_active else "surface"
            col = "on_accent" if is_active else (done_color if i < active else "ink2")
            out.append(O(f"!!{id}{i}", "rrect", x, y, ww, 0.34, fill=fill, radius=0.17, z=15,
                         txt=s if is_active else f"{i + 1}", sz=self.t.scale.label, col=col, b=True, al="c", va="m",
                         meta={"inset": 0.04}))
            x += ww + gap
        return out

    def progress(self, n: int, active: int, id: str = "s", x: float | None = None, y: float | None = None) -> list[O]:
        g = self.t.grid
        x = g.margin_x if x is None else x
        y = SLIDE_H - g.margin_bottom - 0.02 if y is None else y
        out = []
        for i in range(n):
            d = 0.16 if i == active else 0.09
            out.append(O(f"!!{id}{i}", "oval", x + i * 0.26 + (0.16 - d) / 2, y + (0.16 - d) / 2, d, d,
                         fill="accent" if i == active else "line", z=15))
        return out

    # ------------------------------------------------------------------ схемы
    def node(self, id: str, x: float, y: float, w: float, h: float, label: str, sub: str | None = None,
             fill: str = "surface2", col: str = "ink", sub_col: str = "ink2", line: str | None = None,
             kind: str = "rrect", size: float | None = None, z: int = 10, mono_sub: bool = True) -> list[O]:
        sz = self.fit([label], w - 0.16, size or self.t.scale.small, bold=True)
        sub_sz = self.fit([sub], w - 0.16, self.t.scale.label, font="mono" if mono_sub else "body") if sub else 0
        out = [O(f"!!{id}", kind, x, y, w, h, fill=fill, ln=line, lw=1.25 if line else 0, z=z)]
        if sub:
            out.append(O(f"!!{id}_l", "text", x + 0.08, y + h / 2 - sz * 1.25 / 72 + 0.02, w - 0.16, sz * 1.25 / 72,
                         txt=label, sz=sz, col=col, b=True, al="c", va="b", z=z + 1))
            out.append(O(f"!!{id}_s", "text", x + 0.08, y + h / 2 + 0.04, w - 0.16, sub_sz * 1.3 / 72,
                         txt=sub, sz=sub_sz, col=sub_col, al="c", font="mono" if mono_sub else "body", z=z + 1))
        else:
            out.append(O(f"!!{id}_l", "text", x + 0.08, y, w - 0.16, h, txt=label, sz=sz, col=col, b=True, al="c",
                         va="m", z=z + 1))
        return out

    def marker(self, target: O, id: str = "marker", pad: float = 0.07, color: str = "accent", lw: float = 2.5,
               tint: bool = True, tag: str | None = None) -> list[O]:
        """Переезжающая подсветка активного шага: рамка (+ лёгкая подложка) — пара Morph, которая едет от узла к узлу.
        Вместо перекраски самих узлов: Morph не смешивает далёкие цвета (оранжевый -> синий даёт грязно-коричневый)."""
        out = []
        if tint:
            out.append(O(f"!!{id}_tint", "rect", target.x, target.y, target.w, target.h, fill=color, fa=0.12,
                         z=target.z + 0.5))
        out.append(O(f"!!{id}", "rect", target.x - pad, target.y - pad, target.w + 2 * pad, target.h + 2 * pad, fill=None,
                     ln=color, lw=lw, z=target.z + 0.6))
        if tag:
            out.append(O(f"!!{id}_tag", "text", target.x - pad, target.y - pad - 0.34, target.w + 2 * pad, 0.3, txt=tag,
                         sz=self.t.scale.label, col=color, b=True, caps=True, tracking=1.2, al="c", z=target.z + 0.6))
        return out

    @staticmethod
    def center(o: O) -> tuple[float, float]:
        return o.x + o.w / 2, o.y + o.h / 2

    def link(self, id: str, a: O, b: O, color: str = "line", lw: float = 2.0, head: bool = True, gap: float = 0.06,
             z: int = 4, route: str = "auto") -> tuple[list[O], list[tuple[float, float]]]:
        """Соединитель от края a к краю b и путь для потока — от центра a к центру b (очередь точек скрыта под узлами)."""
        ax, ay = self.center(a)
        bx, by = self.center(b)
        horizontal = route == "h" or (route == "auto" and abs(bx - ax) >= abs(by - ay))
        if horizontal:
            sx = a.x + a.w + gap if bx > ax else a.x - gap
            ex = b.x - gap if bx > ax else b.x + b.w + gap
            sy, ey = ay, by
        else:
            sy = a.y + a.h + gap if by > ay else a.y - gap
            ey = b.y - gap if by > ay else b.y + b.h + gap
            sx, ex = ax, bx
        line = O(f"!!{id}", "line", sx, sy, ex - sx, ey - sy, ln=color, lw=lw, head="triangle" if head else None, z=z)
        return [line], [(ax, ay), (bx, by)]

    def flow(self, points, n: int = 3, period: float = 2.4, color: str = "flow", size: float = 0.13, name: str = "flow",
             z: float = 5, start: float = 0.0) -> Loop:
        return Loop("flow", points=list(points), n=n, period=period, color=color, size=size, name=name, start=start, z=z)

    # ------------------------------------------------------------------ код, терминал, файлы
    def code(self, id: str, x: float, y: float, w: float, code: str, title: str | None = None,
             highlight: list[int] | None = None, size: float | None = None, h: float | None = None,
             z: int = 8) -> list[O]:
        sz = size or self.t.scale.code
        lines = code.rstrip("\n").split("\n")
        lh = sz * 1.2 * 1.05 / 72
        bar = 0.34 if title else 0.0
        hh = h or (bar + 0.2 + len(lines) * lh + 0.2)
        out = [O(f"!!{id}", "rrect", x, y, w, hh, fill="code_bg", z=z)]
        if title:
            out.append(O(f"!!{id}_ttl", "text", x + 0.2, y + 0.1, w - 0.4, 0.26, txt=title, sz=self.t.scale.label,
                         col="code_com", font="mono", z=z + 2))
        for i in highlight or []:
            out.append(O(f"!!{id}_hl{i}", "rect", x + 0.06, y + bar + 0.2 + i * lh - 0.02, w - 0.12, lh + 0.02,
                         fill="accent", fa=0.22, z=z + 1))
        out.append(O(f"!!{id}_code", "text", x + 0.22, y + bar + 0.2, w - 0.44, len(lines) * lh + 0.05, txt=lines,
                     sz=sz, col="code_ink", font="mono", spacing=1.05, z=z + 2,
                     meta={"runs": [highlight_python(l) for l in lines]}))
        return out

    def terminal(self, id: str, x: float, y: float, w: float, lines: list[str], cursor: bool = True,
                 size: float | None = None, z: int = 8, prompt_color: str = "code_kw") -> tuple[list[O], str | None]:
        sz = size or self.t.scale.code
        lh = sz * 1.2 * 1.05 / 72
        hh = 0.34 + 0.18 + len(lines) * lh + 0.2
        out = [O(f"!!{id}", "rrect", x, y, w, hh, fill="code_bg", z=z)]
        for k, c in enumerate(("bad", "warn", "good")):
            out.append(O(f"!!{id}_dot{k}", "oval", x + 0.2 + k * 0.2, y + 0.13, 0.11, 0.11, fill=c, fa=0.9, z=z + 1))
        runs = []
        for l in lines:
            if l.startswith("$ "):
                runs.append([Run("$ ", color=prompt_color), Run(l[2:], color="code_ink")])
            else:
                runs.append([Run(l, color="code_com" if l.startswith("#") else "code_ink")])
        out.append(O(f"!!{id}_txt", "text", x + 0.22, y + 0.46, w - 0.44, len(lines) * lh + 0.05, txt=lines, sz=sz,
                     col="code_ink", font="mono", spacing=1.05, z=z + 2, meta={"runs": runs}))
        cursor_name = None
        if cursor:
            from .qa import line_width_in
            last = out[-1]
            lw = line_width_in(self.t, last, lines[-1], runs[-1])
            cursor_name = f"{id}_cursor"
            out.append(O(cursor_name, "rect", last.x + lw + 0.04, last.y + (len(lines) - 1) * lh + 0.03, 0.11, lh - 0.06,
                         fill="code_ink", z=z + 3))
        return out, cursor_name

    def tree(self, id: str, x: float, y: float, entries: list[tuple[int, str, str | None, bool]], w: float = 5.5,
             size: float | None = None, z: int = 10) -> list[O]:
        """Дерево файлов: (глубина, имя, пояснение, выделить)."""
        sz = size or self.t.scale.small
        lh = sz * 1.55 / 72
        out = []
        for i, (depth, name, note, hl) in enumerate(entries):
            yy = y + i * lh
            xx = x + depth * 0.32
            if depth:
                out.append(O(f"!!{id}_g{i}", "line", xx - 0.2, yy + lh / 2, 0.14, 0, ln="line", lw=1, z=z))
            runs = [Run(name, color="accent" if hl else "ink", bold=hl, mono=True)]
            if note:
                runs.append(Run("   " + note, color="muted"))
            out.append(O(f"!!{id}_{i}", "text", xx, yy, w - depth * 0.32, lh, txt=name + ("   " + note if note else ""),
                         sz=sz, col="ink", z=z + 1, meta={"runs": [runs]}))
        if any(d for d, *_ in entries):
            out.append(O(f"!!{id}_trunk", "line", x + 0.12, y + lh, 0, (len(entries) - 1.5) * lh, ln="line", lw=1, z=z))
        return out

    # ------------------------------------------------------------------ данные из фигур (морфятся)
    def bars(self, id: str, x: float, y: float, w: float, h: float, values: list[float], labels: list[str],
             vmax: float | None = None, colors: list[str] | None = None, fmt: str = "{:.2f}", zero: bool = False,
             label_w: float = 2.4, size: float | None = None, z: int = 10, value_color: str = "ink2") -> list[O]:
        """Горизонтальные столбики. zero=True — нулевое состояние для анимации «вырастают из нуля»."""
        sz = size or self.t.scale.small
        n = len(values)
        row = h / n
        bh = min(row * 0.62, 0.42)
        vmax = vmax or max(abs(v) for v in values) or 1
        out = []
        for i, (v, lab) in enumerate(zip(values, labels)):
            yy = y + i * row + (row - bh) / 2
            length = 0.0 if zero else max(abs(v) / vmax * (w - label_w - 0.9), 0.0)
            out.append(O(f"!!{id}_lab{i}", "text", x, yy, label_w - 0.15, bh, txt=lab, sz=sz, col="ink2", al="r", va="m", z=z))
            out.append(O(f"!!{id}_bar{i}", "rect", x + label_w, yy, max(length, 0.001), bh,
                         fill=(colors[i] if colors else "accent"), z=z))
            out.append(O(f"!!{id}_val{i}", "text", x + label_w + length + 0.08, yy, 0.9, bh,
                         txt="" if zero else fmt.format(v), sz=sz, col=value_color, va="m", z=z))
        return out

    def columns(self, id: str, x: float, y: float, w: float, h: float, values: list[float], labels: list[str],
                vmax: float | None = None, colors: list[str] | None = None, fmt: str = "{:.0f}", zero: bool = False,
                size: float | None = None, z: int = 10, base_line: bool = True) -> list[O]:
        """Вертикальные столбики от общей базовой линии y+h."""
        sz = size or self.t.scale.caption
        n = len(values)
        slot = w / n
        bw = slot * 0.62
        vmax = vmax or max(values) or 1
        base = y + h - 0.32
        out = []
        if base_line:
            out.append(O(f"!!{id}_base", "line", x, base, w, 0, ln="line", lw=1, z=z))
        for i, (v, lab) in enumerate(zip(values, labels)):
            xx = x + i * slot + (slot - bw) / 2
            hh = 0.0 if zero else v / vmax * (h - 0.75)
            out.append(O(f"!!{id}_c{i}", "rect", xx, base - max(hh, 0.001), bw, max(hh, 0.001),
                         fill=(colors[i] if colors else "accent"), z=z))
            out.append(O(f"!!{id}_v{i}", "text", xx - 0.2, base - hh - 0.3, bw + 0.4, 0.26, txt="" if zero else fmt.format(v),
                         sz=sz, col="ink2", al="c", z=z))
            out.append(O(f"!!{id}_x{i}", "text", xx - 0.2, base + 0.05, bw + 0.4, 0.26, txt=lab, sz=sz, col="muted", al="c", z=z))
        return out

    def table(self, id: str, x: float, y: float, widths: list[float], rows: list[list[str]], header: bool = True,
              size: float | None = None, row_h: float | None = None, highlight: int | None = None,
              aligns: list[str] | None = None, z: int = 10) -> list[O]:
        sz = size or self.t.scale.small
        rh = row_h or sz * 2.0 / 72
        out = []
        total_w = sum(widths)
        for r, row in enumerate(rows):
            yy = y + r * rh
            is_head = header and r == 0
            if highlight is not None and r == highlight:
                out.append(O(f"!!{id}_hl", "rect", x - 0.08, yy, total_w + 0.16, rh, fill="accent", fa=0.14, z=z - 1))
            xx = x
            for c, (cell, cw) in enumerate(zip(row, widths)):
                al = (aligns[c] if aligns else ("l" if c == 0 else "r"))
                out.append(O(f"!!{id}_{r}_{c}", "text", xx, yy, cw - 0.1, rh, txt=cell, sz=sz,
                             col="muted" if is_head else "ink", b=is_head or (highlight == r), al=al, va="m",
                             caps=is_head, tracking=0.6 if is_head else 0, z=z))
                xx += cw
            if is_head or r == len(rows) - 1:
                out.append(O(f"!!{id}_rule{r}", "line", x, yy + rh, total_w, 0, ln="line" if not is_head else "ink2",
                             lw=1.0 if not is_head else 1.25, z=z))
        return out

    # ------------------------------------------------------------------ акценты
    def callout(self, id: str, x: float, y: float, w: float, kicker: str, text: str, tone: str = "warn",
                h: float | None = None, z: int = 12) -> list[O]:
        lines = text.split("\n")
        sz = self.t.scale.small
        hh = h or (0.22 + 0.32 + len(lines) * sz * 1.3 / 72 + 0.22)
        return [O(f"!!{id}", "rrect", x, y, w, hh, fill=tone, fa=0.12, z=z),
                O(f"!!{id}_k", "text", x + 0.22, y + 0.2, w - 0.44, 0.28, txt=kicker, sz=self.t.scale.label, col=tone,
                  b=True, caps=True, tracking=1.2, z=z + 1),
                O(f"!!{id}_t", "text", x + 0.22, y + 0.52, w - 0.44, len(lines) * sz * 1.3 / 72 + 0.05, txt=lines, sz=sz,
                  col="ink", spacing=1.08, z=z + 1)]

    def bg_grid(self, step: float = 0.5, color: str = "line", alpha: float = 0.5, id: str = "grid") -> list[O]:
        """Миллиметровка для темы «Чертёж» (фактура, без пар Morph)."""
        out = []
        k = 0
        x = 0.0
        while x <= SLIDE_W + 1e-6:
            out.append(O(f"{id}_v{k}", "line", x, 0, 0, SLIDE_H, ln=color, lw=0.5, la=alpha, z=-10))
            x += step
            k += 1
        y, k = 0.0, 0
        while y <= SLIDE_H + 1e-6:
            out.append(O(f"{id}_h{k}", "line", 0, y, SLIDE_W, 0, ln=color, lw=0.5, la=alpha, z=-10))
            y += step
            k += 1
        return out
