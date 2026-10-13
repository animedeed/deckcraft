"""Грамматика процесса: тяжёлый процесс -> шаги-глаголы -> состояния одних и тех же объектов-носителей.

Носитель (Carrier) — элементы, которые проходят через весь процесс: токены фразы, строки таблицы, документы, пары.
У каждого элемента постоянные имена: тело `!!{id}{i}` (без текста) и подпись `!!{id}{i}t`. Глагол возвращает
новое СОСТОЯНИЕ носителя (те же имена, другие места/формы/цвета) — Morph превращает одно состояние в другое,
поэтому процесс читается как одна непрерывная трансформация, а не как набор картинок.

    c = Carrier("tk", [Item("Капремонт"), Item("ВЛ"), Item("не реже"), Item("12 лет", flag=True)])
    s1 = c.row(0.8, 3.0)                              # фраза
    s2 = c.vectors(0.8, 2.4, dims=6)                  # кодирование: тело -> «колонка» эмбеддинга
    s3 = c.row(0.8, 3.0) + c.links([(0, 3, .9), (2, 3, .6)])   # внимание: дуги между токенами
    s4 = c.bars(0.8, 5.6, values=[.1, .2, .3, .95])  # оценка: тело -> столбик
    s5 = c.row(0.8, 3.0, flagged=True)                # найдено: флаг акцентом (+ c.flag_loops())

Глаголы (VERBS) — словарь для раскадровки и опроса плагина: что показывает глагол, какое состояние носителя,
какие эффекты и петли к нему подходят.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

from shapely.geometry import LineString

from . import vector as V
from .model import Loop, O
from .theme import mix

VERBS: dict[str, dict] = {
    "split":     {"ru": "разбить", "shows": "целое делится на части (фраза -> токены, данные -> выборки)",
                  "state": "row/groups", "fx": "entrance_wipe по частям", "loop": None},
    "encode":    {"ru": "закодировать", "shows": "элемент превращается в числа (токен -> вектор)",
                  "state": "vectors", "fx": "ячейки вектора — entrance_fade по очереди", "loop": None},
    "relate":    {"ru": "связать", "shows": "элементы влияют друг на друга (внимание, ссылки, граф)",
                  "state": "links", "fx": "дуги — entrance_wipe от источника", "loop": "flow по дугам"},
    "score":     {"ru": "оценить", "shows": "каждому элементу — число (вероятность, важность, ошибка)",
                  "state": "bars", "fx": "столбики растут entrance_wipe up", "loop": None},
    "flag":      {"ru": "отметить", "shows": "найдено главное (ошибка, аномалия, правка)",
                  "state": "row(flagged)", "fx": "emphasis — смена цвета", "loop": "ripple вокруг флага"},
    "filter":    {"ru": "отсеять", "shows": "лишнее уходит, остаётся след-точка",
                  "state": "filtered", "fx": None, "loop": None},
    "aggregate": {"ru": "свести", "shows": "части собираются в результат",
                  "state": "merged", "fx": "результат — entrance_faded_zoom", "loop": "pulse результата"},
    "compare":   {"ru": "сравнить", "shows": "два состояния рядом, разница подсвечена",
                  "state": "row + row (сдвиг)", "fx": None, "loop": None},
    "cluster":   {"ru": "сгруппировать", "shows": "элементы расходятся по группам",
                  "state": "groups", "fx": None, "loop": None},
    "zoom":      {"ru": "приблизить", "shows": "одна часть крупно, остальное — контекст",
                  "state": "камера мира / spotlight", "fx": None, "loop": None},
    "iterate":   {"ru": "повторить", "shows": "цикл: эпохи, проходы, итерации",
                  "state": "кривая + маркер шага", "fx": "draw_polyline по сегментам", "loop": "spin маркера"},
}


@dataclass
class Item:
    label: str = ""
    value: float = 0.0
    group: int = 0
    flag: bool = False
    vec: Sequence[float] | None = None  # значения 0..1 для vectors()


@dataclass
class Carrier:
    id: str
    items: list[Item]
    h: float = 0.56  # высота фишки
    sz: float = 16
    pad: float = 0.22  # поля текста в фишке
    gap: float = 0.14
    char_w: float = 0.105  # средняя ширина символа при sz=16, дюймы (Calibri)
    z: int = 40
    widths: list[float] = field(default_factory=list)

    def __post_init__(self):
        self.widths = [max(0.5, len(it.label) * self.char_w * self.sz / 16 + 2 * self.pad) for it in self.items]

    # ------------------------------------------------------------------ базовые состояния
    def _chip(self, i: int, x: float, y: float, w: float, h: float, fill="surface", ln="line", kind="rrect",
              fa=1.0, label=True, col="ink", z_off=0) -> list[O]:
        out = [O(f"!!{self.id}{i}", kind, x, y, w, h, fill=fill, fa=fa, ln=ln, lw=1.0 if ln else 0,
                 radius=min(h / 2, 0.14) if kind == "rrect" else None, z=self.z + z_off)]
        if label:
            out.append(O(f"!!{self.id}{i}t", "text", x, y, w, h, txt=self.items[i].label, sz=self.sz, col=col,
                         al="c", va="m", z=self.z + 1 + z_off, meta={"inset": 0.02}))
        return out

    def positions_row(self, x: float, y: float, max_w: float = 11.8, line_gap: float = 0.3):
        out, cx, cy = [], x, y
        for i, w in enumerate(self.widths):
            if cx + w > x + max_w and cx > x:
                cx, cy = x, cy + self.h + line_gap
            out.append((cx, cy))
            cx += w + self.gap
        return out

    def row(self, x: float, y: float, max_w: float = 11.8, flagged: bool = False, dim_others: bool = False,
            fill="surface", ln="line") -> list[O]:
        """Элементы фишками в порядке чтения (с переносом). flagged — флаги акцентом; dim_others — остальное тише."""
        out = []
        for i, (px, py) in enumerate(self.positions_row(x, y, max_w)):
            it = self.items[i]
            if flagged and it.flag:
                out += self._chip(i, px, py, self.widths[i], self.h, fill="accent", ln="accent", col="on_accent")
            else:
                out += self._chip(i, px, py, self.widths[i], self.h, fill=fill, ln=ln,
                                  col="muted" if (flagged and dim_others) else "ink")
        return out

    def dots(self, positions: Sequence[tuple[float, float]], size: float = 0.16, colors=None,
             labels: bool = False) -> list[O]:
        """Элементы точками (подписи гаснут, тела морфятся в круги)."""
        out = []
        for i, (px, py) in enumerate(positions):
            col = colors[i] if colors else ("accent" if self.items[i].flag else "ink2")
            out += self._chip(i, px - size / 2, py - size / 2, size, size, fill=col, ln=None, kind="oval",
                              label=labels)
        return out

    def groups(self, boxes: Sequence[tuple[float, float, float, float]], step: float = 0.3,
               size: float = 0.2, colors: Sequence[str] | None = None) -> list[O]:
        """Расхождение по группам: элемент i уходит в рамку своей группы items[i].group."""
        filled = [0] * len(boxes)
        pos, cols = [], []
        for it in self.items:
            g = it.group
            bx, by, bw, bh = boxes[g]
            per_row = max(1, int(bw // step))
            k = filled[g]
            pos.append((bx + (k % per_row) * step + size / 2, by + (k // per_row) * step + size / 2))
            cols.append(colors[g] if colors else "ink2")
            filled[g] += 1
        return self.dots(pos, size, cols)

    # ------------------------------------------------------------------ глаголы
    def vectors(self, x: float, y: float, dims: int = 6, cell: float = 0.3, low="surface2", high="accent",
                theme=None) -> list[O]:
        """encode: фишка сжимается в «шапку» столбца, под ней — ячейки вектора (цвет = значение)."""
        out = []
        pos = self.positions_row(x, y)
        for i, (px, py) in enumerate(pos):
            w = self.widths[i]
            out += self._chip(i, px, py, w, self.h * 0.8, fill="surface2", ln=None)
            vec = self.items[i].vec or [((i * 7 + j * 3) % 10) / 10 for j in range(dims)]
            cx = px + w / 2 - cell / 2
            for j, v in enumerate(vec[:dims]):
                col = mix(theme.c(low), theme.c(high), float(v)) if theme else (high if v > 0.6 else low)
                out.append(O(f"!!{self.id}{i}v{j}", "rect", cx, py + self.h * 0.8 + 0.08 + j * (cell + 0.04),
                             cell, cell, fill=col, z=self.z - 1, meta={"decor": True}))
        return out

    def bars(self, x: float, base_y: float, values: Sequence[float], max_h: float = 2.2, bar_w: float = 0.36,
             threshold: float | None = None, max_w: float = 11.8, label_y: float | None = None) -> list[O]:
        """score: тело фишки становится столбиком (высота = значение), подпись встаёт под столбик."""
        out = []
        pos = self.positions_row(x, base_y, max_w)
        for i, (px, _) in enumerate(pos):
            w, v = self.widths[i], float(values[i])
            h = max(max_h * v, 0.04)
            hot = threshold is not None and v >= threshold
            out.append(O(f"!!{self.id}{i}", "rect", px + w / 2 - bar_w / 2, base_y - h, bar_w, h,
                         fill="accent" if hot else "ink2", z=self.z))
            out.append(O(f"!!{self.id}{i}t", "text", px, label_y if label_y is not None else base_y + 0.08, w,
                         self.h, txt=self.items[i].label, sz=self.sz, col="ink" if hot else "muted", al="c", va="t",
                         z=self.z + 1, meta={"inset": 0.02}))
        return out

    def links(self, pairs: Sequence[tuple[int, int, float]], x: float, y: float, height: float = 0.9,
              max_w: float = 11.8, color: str = "accent", above: bool = True, width: float = 0.045) -> list[O]:
        """relate: дуги между фишками (толщина и прозрачность = сила связи). Имена !!{id}_l{a}_{b}."""
        pos = self.positions_row(x, y, max_w)
        out = []
        for a, b, wgt in pairs:
            pa = (pos[a][0] + self.widths[a] / 2, pos[a][1] + (0 if above else self.h))
            pb = (pos[b][0] + self.widths[b] / 2, pos[b][1] + (0 if above else self.h))
            lift = height * (0.22 + 0.7 * min(1.0, abs(pb[0] - pa[0]) / 6))  # длинная дуга — выше
            out.append(arc_ribbon(f"!!{self.id}_l{a}_{b}", pa, pb, 2 * lift * (1 if above else -1), width * (0.5 + wgt), color,
                                  alpha=0.35 + 0.65 * wgt, z=self.z - 2))
        return out

    def filtered(self, keep: Sequence[int], positions: Sequence[tuple[float, float]], size: float = 0.2) -> list[O]:
        """filter: оставшиеся — на своих местах, отсеянные сжимаются в точку-след на месте."""
        keep = set(keep)
        out = []
        for i, (px, py) in enumerate(positions):
            s = size if i in keep else 0.0
            out += self._chip(i, px - s / 2, py - s / 2, s, s, fill="accent" if i in keep else "muted", ln=None,
                              kind="oval", label=False)
        return out

    def merged(self, box: tuple[float, float, float, float]) -> list[O]:
        """aggregate: все тела слетаются в рамку результата и гаснут в ней (рамка-результат — отдельный объект)."""
        bx, by, bw, bh = box
        out = []
        for i in range(len(self.items)):
            out += self._chip(i, bx + bw / 2 - 0.05, by + bh / 2 - 0.05, 0.1, 0.1, fill="accent", ln=None,
                              kind="oval", fa=0.0, label=False)
        return out

    def flag_loops(self, period: float = 1.6) -> list[Loop]:
        """Круги на воде вокруг найденных элементов (не больше двух флагов — иначе шум)."""
        return [Loop("ripple", target=f"!!{self.id}{i}", period=period, scale=1.35, color="accent",
                     name=f"{self.id}flag{i}")
                for i, it in enumerate(self.items) if it.flag][:2]


def arc_ribbon(name: str, a: tuple[float, float], b: tuple[float, float], height: float, width: float,
               color: str = "accent", alpha: float = 1.0, z: int = 30, n: int = 40) -> O:
    """Дуга-лента между точками a и b (квадратичная кривая; вершина поднята на height/2 над верхней точкой,
    отрицательный height — вниз)."""
    mx = (a[0] + b[0]) / 2
    my = (min(a[1], b[1]) - height) if height > 0 else (max(a[1], b[1]) - height)
    pts = [((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * mx + t ** 2 * b[0],
            (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * my + t ** 2 * b[1]) for t in (k / n for k in range(n + 1))]
    g = LineString(pts).buffer(width / 2, cap_style=1, join_style=1)
    return V.shape(name, g, fill=color, fa=alpha, z=z, meta={"decor": True})


def plan(verbs: Sequence[str]) -> list[str]:
    """Проверка раскадровки процесса: известные глаголы, без трёх одинаковых подряд, есть кульминация
    (flag/aggregate/compare). Возвращает замечания."""
    notes = []
    for v in verbs:
        if v not in VERBS:
            notes.append(f"неизвестный глагол {v!r}: {', '.join(VERBS)}")
    for k in range(2, len(verbs)):
        if verbs[k] == verbs[k - 1] == verbs[k - 2]:
            notes.append(f"три «{verbs[k]}» подряд (шаги {k - 1}–{k + 1}) — объедините или смените приём")
    if not any(v in ("flag", "aggregate", "compare") for v in verbs):
        notes.append("нет кульминации: добавьте flag (что найдено), aggregate (итог) или compare (было/стало)")
    return notes


__all__ = ["VERBS", "Item", "Carrier", "arc_ribbon", "plan"]
