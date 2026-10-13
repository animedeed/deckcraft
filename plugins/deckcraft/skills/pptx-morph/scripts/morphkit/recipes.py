"""Сложные приёмы Morph: помощники строят состояния объектов для соседних слайдов.

Каждый помощник возвращает объекты O (или координаты) для ОДНОГО состояния. Слайды получаются вызовом
с разными параметрами: одинаковые id дают пары Morph. Каталог приёмов с рецептами — references/techniques.md.

    from morphkit import recipes as R
    s1 = Slide(... + R.spotlight("spot", (1, 2, 4, 1)))            # окно на первой строке
    s2 = Slide(... + R.spotlight("spot", (1, 3, 4, 1)))            # окно переехало на вторую
    objs, fx = R.ring_fill("acc", 3, 3, 1.2, 0.85)                  # кольцо заполняется по кругу при входе
    s4 = Slide(... + R.dots("d", R.grid(60, 1, 2, 12, 0.3)))       # с s5 = R.dots("d", R.groups(...))
"""

from __future__ import annotations

import math
import random
from typing import Sequence

from . import vector as V
from .model import Cam, Loop, O, apply_camera
from .theme import SLIDE_H, SLIDE_W

# ----------------------------------------------------------------------------- прожектор

def spotlight(id: str, win: tuple[float, float, float, float], color: str = "bg", alpha: float = 0.78,
              radius: float = 0.12, n: int = 96, z: int = 15) -> list[O]:
    """Затемнение всего слайда с одним окном (фигура с одной дыркой — Morph её переливает).
    win = (x, y, w, h). Окно на соседнем слайде в другом месте или другого размера — прожектор переезжает.
    Число точек окна фиксировано (n), поэтому пары всегда совместимы. z=15 — выше содержимого (z 6–12),
    ниже заголовков (z 20): шапка не тускнеет."""
    x, y, w, h = win
    hole = V.resample(V.rect(x, y, w, h, r=min(radius, w / 2.01, h / 2.01)), n)
    outer = [(-0.4, -0.4), (SLIDE_W + 0.4, -0.4), (SLIDE_W + 0.4, SLIDE_H + 0.4), (-0.4, SLIDE_H + 0.4)]
    g = V.Polygon(outer, [list(hole.exterior.coords)])
    return [V.shape(f"!!{id}", g, fill=color, z=z, fa=alpha, meta={"bleed": True, "decor": True})]


def spotlight4(id: str, win: tuple[float, float, float, float], color: str = "bg", alpha: float = 0.78,
               z: int = 15) -> list[O]:
    """Запасной прожектор из четырёх прямоугольников вокруг окна (на случай, если версия PowerPoint
    не переливает фигуру с дыркой)."""
    x, y, w, h = win
    m = 0.4
    parts = [(-m, -m, SLIDE_W + 2 * m, y + m), (-m, y + h, SLIDE_W + 2 * m, SLIDE_H - y - h + m),
             (-m, y, x + m, h), (x + w, y, SLIDE_W - x - w + m, h)]
    return [O(f"!!{id}_{k}", "rect", *r, fill=color, fa=alpha, z=z, meta={"bleed": True, "decor": True})
            for k, r in enumerate(parts)]


# ----------------------------------------------------------------------------- поля точек

def grid(n: int, x: float, y: float, cols: int, step: float) -> list[tuple[float, float]]:
    return [(x + (i % cols) * step, y + (i // cols) * step) for i in range(n)]


def ring(n: int, cx: float, cy: float, r: float, start: float = -90) -> list[tuple[float, float]]:
    return [(cx + r * math.cos(math.radians(start + 360 * i / n)), cy + r * math.sin(math.radians(start + 360 * i / n)))
            for i in range(n)]


def pile(n: int, cx: float, cy: float) -> list[tuple[float, float]]:
    return [(cx, cy)] * n


def scatter(points: Sequence[tuple[float, float]], box: tuple[float, float, float, float],
            xlim: tuple[float, float], ylim: tuple[float, float]) -> list[tuple[float, float]]:
    """Значения -> координаты в рамке box = (x, y, w, h); ось y вверх."""
    bx, by, bw, bh = box
    return [(bx + (px - xlim[0]) / (xlim[1] - xlim[0]) * bw, by + bh - (py - ylim[0]) / (ylim[1] - ylim[0]) * bh)
            for px, py in points]


def groups(sizes: Sequence[int], boxes: Sequence[tuple[float, float, float, float]], step: float) -> list[tuple[float, float]]:
    """Точки по группам: группа g — сетка в своей рамке (x, y, w, h). Порядок точек сохраняется: первые
    sizes[0] точек — в первой группе и т.д. (так поле из сетки «расходится» на train / val / test)."""
    out = []
    for size, (bx, by, bw, bh) in zip(sizes, boxes):
        cols = max(1, int(bw // step))
        out += grid(size, bx, by, cols, step)
    return out


def histogram(values: Sequence[float], bins: Sequence[float], x: float, base_y: float, col_w: float,
              step: float) -> list[tuple[float, float]]:
    """Каждая точка — наблюдение: встаёт в стопку своего интервала (точки растут вверх от base_y)."""
    counts = [0] * (len(bins) - 1)
    out = []
    for v in values:
        b = max(0, min(len(bins) - 2, next((i for i in range(len(bins) - 1) if v < bins[i + 1]), len(bins) - 2)))
        out.append((x + b * col_w + col_w / 2 - step / 2, base_y - (counts[b] + 1) * step))
        counts[b] += 1
    return out


def jitter(points: Sequence[tuple[float, float]], amount: float, seed: int = 7) -> list[tuple[float, float]]:
    rnd = random.Random(seed)
    return [(x + rnd.uniform(-amount, amount), y + rnd.uniform(-amount, amount)) for x, y in points]


def dots(id: str, positions: Sequence[tuple[float, float]], size: float | Sequence[float] = 0.16,
         colors: str | Sequence[str] = "accent", fa: float | Sequence[float] = 1.0, z: int = 12) -> list[O]:
    """Поле точек !!id0…: одинаковый id и число точек на соседних слайдах — точки перелетают в новый
    порядок (сетка → разброс → группы → гистограмма). Размер 0 — точка «схлопнулась» на месте."""
    n = len(positions)
    sizes = [size] * n if isinstance(size, (int, float)) else list(size)
    cols = [colors] * n if isinstance(colors, str) else list(colors)
    alphas = [fa] * n if isinstance(fa, (int, float)) else list(fa)
    out = []
    for i, (px, py) in enumerate(positions):
        s = max(sizes[i], 0.001)
        out.append(O(f"!!{id}{i}", "oval", px - s / 2 + sizes[0] / 2, py - s / 2 + sizes[0] / 2, s, s, fill=cols[i],
                     fa=alphas[i], z=z))
    return out


# ----------------------------------------------------------------------------- рост внутри слайда (без служебных слайдов)

def reveal(names: Sequence[str], effect: str = "entrance_fade", delay: float = 0.15, stagger: float = 0.08,
           dur: float | None = None, options: dict | None = None, start: str = "at") -> list:
    """Эффекты появления по очереди при входе на слайд: столбики — entrance_wipe {direction: left},
    колонки — {direction: down}, точки и подписи — entrance_fade, числа — entrance_faded_zoom.
    Заменяет «нулевой» служебный слайд: показ остаётся одним кликом, назад листается нормально."""
    from .presets import Fx
    return [Fx(effect, n, start=start, delay=delay + k * stagger, dur=dur, options=dict(options or {}))
            for k, n in enumerate(names)]


def ring_fill(id: str, cx: float, cy: float, r: float, frac: float, thickness: float = 0.16,
              color: str = "accent", track: str | None = "surface2", dur: float = 0.9, delay: float = 0.15,
              z: int = 10) -> tuple[list[O], list]:
    """Кольцо-прогресс, которое ЗАПОЛНЯЕТСЯ ПО КРУГУ при входе на слайд: дуга сразу нужной длины (старт на 12 часов,
    по часовой стрелке) + вход «Колесо» с одной спицей. Регулятор дуги не морфится — иначе PowerPoint рисует клин.
    -> (объекты, эффекты)."""
    from .presets import Fx
    t = int(min(max(thickness / (2 * r), 0.01), 0.5) * 100000)
    a0 = 16200000  # 270° в системе фигуры = 12 часов
    a1 = int((270 + min(max(frac, 0.002), 0.9995) * 360) % 360 * 60000)
    objs = []
    if track:
        objs.append(O(f"!!{id}_track", "donut", cx - r, cy - r, 2 * r, 2 * r, fill=track, adj={"adj": t}, z=z))
    objs.append(O(f"{id}_arc", "arc", cx - r, cy - r, 2 * r, 2 * r, fill=color, adj={"adj1": a0, "adj2": a1, "adj3": t},
                  z=z + 1))
    return objs, [Fx("entrance_wheel", f"{id}_arc", start="at", delay=delay, dur=dur, options={"amount": "1"})]


# ----------------------------------------------------------------------------- переходы-«события»

def circle_wipe(id: str, cx: float, cy: float, color: str, grown: bool, z: int = 40) -> list[O]:
    """Граница раздела: круг цвета нового раздела растёт из точки (кнопка, узел) до размеров слайда.
    Слайд A — grown=False (точка), слайд B — grown=True; следующий слайд с фоном color круга уже не держит."""
    if not grown:
        s = 0.05
        return [O(f"!!{id}", "oval", cx - s / 2, cy - s / 2, s, s, fill=color, z=z)]
    R = max(math.hypot(cx - px, cy - py) for px in (0, SLIDE_W) for py in (0, SLIDE_H)) * 1.02
    return [O(f"!!{id}", "oval", cx - R, cy - R, 2 * R, 2 * R, fill=color, z=z, meta={"bleed": True, "decor": True})]


# ----------------------------------------------------------------------------- карусель и сортировка

def carousel(n: int, active: int, cx: float, cy: float, rx: float, ry: float, w: float, h: float,
             back_scale: float = 0.55) -> list[dict]:
    """Места n карточек на эллипсе: активная — спереди внизу, крупно; дальние — меньше, бледнее, ниже по z.
    -> [{'x','y','w','h','z','fa','depth'}] по индексу карточки. Шаг на 1 позицию — Morph по хорде;
    при n ≥ 6 это выглядит как вращение (для n < 6 добавь служебные слайды-полушаги с auto=0)."""
    out = []
    for i in range(n):
        a = math.radians(90 + (i - active) * 360 / n)
        depth = (math.sin(a) + 1) / 2  # 1 — спереди
        k = back_scale + (1 - back_scale) * depth
        px, py = cx + rx * math.cos(a), cy + ry * math.sin(a)
        out.append({"x": px - w * k / 2, "y": py - h * k / 2, "w": w * k, "h": h * k, "z": int(10 + depth * 20),
                    "fa": 0.35 + 0.65 * depth, "depth": depth, "scale": k})
    return out


def ranked_bars(id: str, x: float, y: float, w: float, h: float, items: dict[str, float], order: str = "desc",
                colors: dict[str, str] | None = None, fmt: str = "{:.2f}", label_w: float = 2.4, sz: float = 15,
                vmax: float | None = None, zero: bool = False, z: int = 10) -> list[O]:
    """Горизонтальные столбики с именами по сущности (!!id_<метка>): смена порядка (order='desc'|'asc'|
    'given') на следующем слайде — столбики переезжают на новые места, длины меняются плавно.
    zero=True — нулевое состояние (длина 0, без чисел) для «вырастания»."""
    keys = list(items)
    if order == "desc":
        keys.sort(key=lambda k: -items[k])
    elif order == "asc":
        keys.sort(key=lambda k: items[k])
    n = len(keys)
    row = h / n
    bh = min(row * 0.62, 0.42)
    vmax = vmax or max(abs(v) for v in items.values()) or 1
    out = []
    for i, key in enumerate(keys):
        slug = "".join(ch if ch.isalnum() else "_" for ch in key)
        yy = y + i * row + (row - bh) / 2
        length = 0.001 if zero else max(abs(items[key]) / vmax * (w - label_w - 0.9), 0.001)
        out += [O(f"!!{id}_lab_{slug}", "text", x, yy, label_w - 0.15, bh, txt=key, sz=sz, col="ink2", al="r", va="m", z=z),
                O(f"!!{id}_bar_{slug}", "rect", x + label_w, yy, length, bh,
                  fill=(colors or {}).get(key, "accent"), z=z),
                O(f"!!{id}_val_{slug}", "text", x + label_w + length + 0.08, yy, 0.9, bh,
                  txt="" if zero else fmt.format(items[key]),
                  sz=sz, col="ink2", va="m", z=z)]
    return out


# ----------------------------------------------------------------------------- рисование ломаной

def draw_polyline(id: str, pts: Sequence[tuple[float, float]], color: str = "accent", lw: float = 2.5,
                  seg_dur: float = 0.35, start: str = "after", z: int = 8):
    """Ломаная рисуется по сегментам эффектом «Возникновение» (wipe) по направлению движения.
    -> (объекты, список Fx). Сегменты — обычные линии без пар Morph (вход на них запрещён правилом)."""
    from .presets import Fx
    objs, fx = [], []
    for k, ((x0, y0), (x1, y1)) in enumerate(zip(pts, pts[1:])):
        name = f"{id}_seg{k}"
        objs.append(O(name, "line", x0, y0, x1 - x0, y1 - y0, ln=color, lw=lw, z=z))
        dx, dy = x1 - x0, y1 - y0
        frm = ("left" if dx > 0 else "right") if abs(dx) >= abs(dy) else ("up" if dy > 0 else "down")
        fx.append(Fx("entrance_wipe", name, dur=seg_dur, start=start if k else "at", options={"direction": frm}))
    return objs, fx


def curve(id: str, pts: Sequence[tuple[float, float]], color: str = "accent", lw: float = 2.5, dur: float = 1.2,
          delay: float = 0.2, z: int = 8):
    """Длинная кривая (десятки точек) одной фигурой: лента толщиной lw pt, проявляется «Возникновением» слева
    направо за dur. Для 3–8 отрезков с поворотами — draw_polyline (по сегментам). -> (объекты, список Fx)."""
    from shapely.geometry import LineString
    from .presets import Fx
    g = LineString(pts).buffer(lw / 72 / 2, cap_style=1, join_style=1)
    o = V.shape(id, g, fill=color, z=z)
    return [o], [Fx("entrance_wipe", id, start="at", delay=delay, dur=dur, options={"direction": "left"})]


# ----------------------------------------------------------------------------- 3D и разлёт

ISO_TOP_UP = {"x": 314.7, "y": 324.6, "z": 60.2, "camera": "orthographicFront"}  # пресет «Изометрия: сверху вверх»


def flip_fx(front: str, back: str, delay: float = 0.2, half: float = 0.35) -> list:
    """Переворот карточки ВНУТРИ слайда (без служебных слайдов): лицо уходит выходом «Поворот» по горизонтали,
    оборот (лежит на том же месте, скрыт до старта) входит тем же эффектом. Оба объекта — без пар Morph."""
    from .presets import Fx
    return [Fx("exit_swivel", front, start="at", delay=delay, dur=half, options={"direction": "horizontal"}),
            Fx("entrance_swivel", back, start="after", dur=half, options={"direction": "horizontal"})]


def explode(parts: Sequence, k: float = 0.4, center: tuple[float, float] | None = None) -> list:
    """Сдвигает каждую часть от общего центра на k·расстояние (разлёт после fragment)."""
    if center is None:
        u = V.union(*parts).centroid
        center = (u.x, u.y)
    return [V.move(p, (p.centroid.x - center[0]) * k, (p.centroid.y - center[1]) * k) for p in parts]


# ----------------------------------------------------------------------------- мир уходит на фон, сигнал по линиям

def backdrop(objs: Sequence[O], k: float = 0.3, text_role: str = "line") -> list[O]:
    """Тот же мир, но фоном: заливки и линии в k раз прозрачнее, текст — тихой ролью. Имена сохраняются, поэтому
    Morph не убирает мир, а приглушает его (на «сценах» поверх мира). Обычно вместе с другой камерой (сдвиг/отъезд)."""
    out = []
    for o in objs:
        kw = {"fa": o.fa * k, "la": o.la * k}
        if o.txt is not None:
            kw["col"] = text_role
        out.append(o.copy(**kw, meta={**o.meta, "decor": True}))
    return out


def flow_along(line: O, cam: Cam | None = None, n: int = 3, period: float = 2.0, color: str = "flow",
               size: float = 0.13, name: str = "flow", reverse: bool = False, trim: float = 0.0,
               z: float | None = None) -> Loop:
    """Петля-поток ТОЧНО по линии (её начало → конец), с учётом камеры, если линия в мировых координатах.
    trim — сколько дюймов не доходить до концов (чтобы точка «входила» в узел, а не наезжала на подпись)."""
    o = apply_camera(line, cam) if line.world else line
    x0, y0, x1, y1 = o.x, o.y, o.x + o.w, o.y + o.h
    if trim:
        L = max(math.hypot(x1 - x0, y1 - y0), 1e-6)
        ux, uy = (x1 - x0) / L, (y1 - y0) / L
        x0, y0, x1, y1 = x0 + ux * trim, y0 + uy * trim, x1 - ux * trim, y1 - uy * trim
    return Loop("flow", points=[(x0, y0), (x1, y1)], n=n, period=period, color=color, size=size, name=name,
                reverse=reverse, z=line.z + 0.5 if z is None else z)  # точки — сразу над линией, под узлами и текстом


# ----------------------------------------------------------------------------- документы-листы

def doc_sheet(id: str, x: float, y: float, w: float, h: float, fill: str = "surface2", ln: str = "line",
              lw: float = 1.0, fold: float = 0.18, rot: float = 0.0, z: int = 8, **kw) -> O:
    """Лист документа с загнутым углом (foldedCorner); fold — доля загиба от меньшей стороны."""
    return O(id, "fold", x, y, w, h, fill=fill, ln=ln, lw=lw, rot=rot, z=z, adj={"adj": int(fold * 100000)}, **kw)


def doc_arc(id: str, n: int, x: float, y: float, w: float, sheet_w: float = 0.62, sheet_h: float = 0.88,
            spread: float = 10.0, sag: float = 0.35, highlight: int | None = -1, fill: str = "surface2",
            ln: str = "line", accent: str = "accent", z: int = 8) -> list[O]:
    """Ряд листов дугой (как лента редакций): крайние наклонены на ±spread/2 градусов и ниже на sag.
    highlight — индекс выделенного листа (−1 — последний) с контуром акцента."""
    out = []
    hi = (n + highlight) if highlight is not None and highlight < 0 else highlight
    for i in range(n):
        t = (i / (n - 1)) * 2 - 1 if n > 1 else 0.0  # −1 … 1
        cx = x + (i + 0.5) * w / n
        cy = y + sag * t * t
        on = i == hi
        out.append(doc_sheet(f"{id}{i}", cx - sheet_w / 2, cy, sheet_w, sheet_h, fill=fill,
                             ln=accent if on else ln, lw=2.0 if on else 1.0, rot=t * spread / 2, z=z + i))
    return out


def doc_pictograms(id: str, value: float, x: float, y: float, sheet_w: float = 0.62, sheet_h: float = 0.82,
                   gap: float = 0.16, fill: str = "ink2", z: int = 8) -> list[O]:
    """Значение в листах: целые листы + узкая полоска для дробной части (3,3 = три листа и полоска 0,3)."""
    out = []
    full, part = int(value), value - int(value)
    for i in range(full):
        out.append(doc_sheet(f"{id}{i}", x + i * (sheet_w + gap), y, sheet_w, sheet_h, fill=fill, ln=None, lw=0, z=z))
    if part > 0.04:
        out.append(O(f"{id}p", "rect", x + full * (sheet_w + gap), y, sheet_w * part, sheet_h, fill=fill, z=z))
    return out


# ----------------------------------------------------------------------------- цветок-мандала и указатель темы

LAYER_FILLS = [("F2F2EE", "D4D4CE"), ("B9B9B3", "8E8E89"), ("FFFFFF", "DADAD4"), ("A3A39D", "7A7A75")]


def mandala(id: str, center: tuple[float, float], petals: int = 10, length: float = 3.0, width: float = 1.15,
            layers: int = 5, turn: float = 0.0, scale: float = 1.0, fills: Sequence[tuple[str, str]] = LAYER_FILLS,
            core: str = "0B0B0D", edge: str | None = "0B0B0D", edge_w: float = 1.0, z: int = 6) -> list[O]:
    """Цветок из многослойных лепестков (эталон — видео пользователя): у каждого лепестка полосы чередуют
    светлый и серый градиент, тёмное ядро у центра; каждый лепесток лежит поверх предыдущего целиком (как группа
    в PowerPoint), край внешней полосы — тонкий тёмный кант. Все части — формы в рамке на оси center, поэтому `turn`
    (градусы) и его морфинг вращают цветок как целое, а вход «Вертушка» раскручивает его из центра.
    Имена: !!{id}{лепесток}_{слой}. scale меняет размер вокруг центра (цветок уезжает за край и растёт)."""
    cx, cy = center
    parts = V.bud((cx, cy), length * scale, width * scale, layers=layers, angle=-90)
    out = []
    for k in range(petals):
        for j, g in enumerate(parts):
            last = j == len(parts) - 1
            if last:
                fill, grad = core, None
            else:
                a, b = fills[j % len(fills)]
                grad = V.gradient([(0, a), (1, b)], angle=90)
                fill = a
            out.append(V.shape(f"!!{id}{k}_{j}", g, pivot=(cx, cy), rot=(turn + k * 360 / petals) % 360, fill=fill,
                               grad=grad, ln=edge if j == 0 else None, lw=edge_w if j == 0 else 0,
                               z=z + k * layers + j, meta={"bleed": True, "decor": True}))
    return out


def mandala_spin_in(id: str, petals: int = 10, layers: int = 5, delay: float = 0.1, step: float = 0.06,
                    dur: float = 0.8) -> list:
    """Вход «Вертушка» по лепесткам: каждый лепесток (все его слои) раскручивается из центра цветка."""
    from .presets import Fx
    return [Fx("entrance_spinner", f"!!{id}{k}_{j}", start="at", delay=delay + k * step, dur=dur)
            for k in range(petals) for j in range(layers)]


def pointer_lens(id: str, center: tuple[float, float], length: float, width: float, angle: float = 0.0,
                 color: str = "accent", n: int = 160, z: int = 30) -> list[O]:
    """Неподвижный указатель поверх цветка: контур линзы по направлению angle — лепесток, который сейчас
    «смотрит» на тему, оказывается в нём. Контур ресемплирован (n точек), поэтому его можно перелить
    в панель содержимого (`panel_from_lens`)."""
    g = V.resample(V.petal(center, 0.0, length, width, angle), n)
    return [V.shape(f"!!{id}", g, fill=color, fa=0.16, ln=color, lw=2.25, z=z, meta={"bleed": True, "decor": True})]


def panel_from_lens(id: str, x: float, y: float, w: float, h: float, r: float = 0.25, color: str = "accent",
                    fill: str = "surface", n: int = 160, z: int = 30) -> list[O]:
    """Панель содержимого с тем же числом точек, что у указателя: указатель-линза переливается в панель
    (лепесток «раскрывается» в слайд темы) и обратно."""
    g = V.resample(V.rect(x, y, w, h, r=r), n)
    return [V.shape(f"!!{id}", g, fill=fill, fa=1.0, ln=color, lw=1.5, z=z)]


# ----------------------------------------------------------------------------- карта доклада -> шапка раздела

def agenda(id: str, sections: Sequence[str], state: str = "map", k: int = 0, y: float = 2.6, h: float = 2.3,
           gap: float = 0.3, x0: float = 0.6, x1: float = SLIDE_W - 0.6, header: tuple = (0.45, 0.35, 4.6, 0.72),
           frame: tuple | None = None, fill: str = "surface", ln: str = "line", accent: str = "accent", sz: float = 20,
           z: int = 20) -> list[O]:
    """Приём из защиты ВКР: карточки разделов на «карте доклада»; карточка текущего раздела
    ВЫРАСТАЕТ в шапку раздела (state="header") или в рамку содержимого (state="frame"), остальные паркуются за
    нижним краем по своим колонкам и возвращаются на итоговой карте (state="map", k — пройденные: done-подсветка).
    Подложка карточки и подпись — разные объекты (подпись не переливается, при смене размера гаснет/появляется).
    Имена: !!{id}{i} (подложка), !!{id}{i}t (подпись)."""
    n = len(sections)
    cw = (x1 - x0 - gap * (n - 1)) / n
    out = []
    for i, name in enumerate(sections):
        cx = x0 + i * (cw + gap)
        if state == "map":
            box, lab_sz, lit = (cx, y, cw, h), sz, i < k
        elif i == k:
            box = header if state == "header" else (frame or (0.45, 1.2, SLIDE_W - 0.9, 5.7))
            lab_sz, lit = (sz * 0.8 if state == "header" else sz * 0.7), True
        else:
            box, lab_sz, lit = (cx, SLIDE_H + 0.4, cw, h), sz, False  # парковка под нижним краем
        bx, by, bw, bh = box
        out.append(O(f"!!{id}{i}", "rrect", bx, by, bw, bh, fill=fill, ln=accent if lit else ln, lw=1.5 if lit else 1,
                     radius=0.22, z=z, meta={"bleed": True}))
        tb = (bx, by, bw, bh) if state != "frame" or i != k else (bx + 0.25, by + 0.15, bw - 0.5, 0.6)
        out.append(O(f"!!{id}{i}t{state[0] if i == k and state != 'map' else ''}", "text", *tb, txt=name, sz=lab_sz,
                     b=True, col="accent" if (lit and state != "map") else "ink", al="c" if state == "map" or i != k else "l",
                     va="m" if state == "map" or i != k else "t", z=z + 1,
                     meta={"inset": 0.18, "bleed": True}))
    return out


# ----------------------------------------------------------------------------- лупа: увеличенная деталь в окне

def magnify(objs: Sequence[O], lens: tuple[float, float, float], zoom: float = 2.4, id: str = "mg",
            ring: str = "accent", ring_w: float = 2.0, backdrop: str = "bg", z: int = 300, n: int = 64) -> list[O]:
    """Круглая лупа над содержимым: внутри окна — те же фигуры, увеличенные в zoom раз относительно центра
    линзы и обрезанные по кругу (настоящая геометрия, не картинка). Лупа переезжает между слайдами — окно
    показывает другую деталь (имена копий постоянны: !!{id}_{имя}). Текст в лупу не попадает.
    lens = (cx, cy, r)."""
    from shapely.geometry import Polygon
    from .motion import _local_polys
    cx, cy, r = lens
    disc = V.circle(cx, cy, r, seg=n)
    out = [V.shape(f"!!{id}_bg", V.resample(disc, n), fill=backdrop, z=z)]
    for o in objs:
        if o.lines or o.kind in ("line", "arrow", "text") or o.fill is None:
            continue
        rings = _local_polys(o)
        if not rings or len(rings[0]) < 3:
            continue
        g = Polygon(rings[0], rings[1:] if o.kind == "vec" else None)
        if not g.is_valid:
            g = g.buffer(0)
        g = V.scale(g, zoom, origin=(cx, cy)).intersection(disc)
        if g.is_empty or g.area < 1e-4:
            continue
        nm = o.name.lstrip("!")
        out.append(V.shape(f"!!{id}_{nm}", g, fill=o.fill, fa=o.fa, z=z + 1 + (o.z if isinstance(o.z, int) else 0) * 0))
    out.append(O(f"!!{id}_ring", "oval", cx - r, cy - r, 2 * r, 2 * r, fill=None, ln=ring, lw=ring_w, z=z + 500))
    return out


# ----------------------------------------------------------------------------- навигация: меню сайта, метка + счётчик

def menu_bar(id: str, sections: Sequence[str], current: int, y: float = 0.22, x0: float = 0.6, h: float = 0.42,
             sz: float = 13, gap: float = 0.35, char_w: float = 0.088, pill: str = "accent", z: int = 900) -> list[O]:
    """Навигация как меню сайта (как в колоде-презентации продукта): строка разделов сверху; подложка-«пилюля»
    одна на колоду (!!{id}_pill) и переезжает Morph к текущему разделу. Подписи не меняют текст — не переливаются."""
    out, x = [], x0
    for i, name in enumerate(sections):
        w = len(name) * char_w * sz / 13 + 0.36
        if i == current:
            out.append(O(f"!!{id}_pill", "rrect", x - 0.02, y, w + 0.04, h, fill=pill, radius=h / 2, z=z))
        out.append(O(f"!!{id}{i}", "text", x, y, w, h, txt=name, sz=sz, b=i == current, al="c", va="m",
                     col="on_accent" if i == current else "muted", z=z + 1, meta={"inset": 0.0}))
        x += w + gap
    return out


def block_counter(id: str, block: str, page: int, total: int, x: float = 0.6, y: float = 0.25, sz: float = 12,
                  right: float = 12.75, z: int = 900) -> list[O]:
    """Метка блока и счётчик страниц (строгий технический доклад): «Блок 2 — Данные» слева, «9|27» справа.
    Метка блока меняется затуханием (политика текста), счётчик — отдельный объект на каждый слайд."""
    return [O(f"!!{id}_blk", "text", x, y, 7.0, 0.35, txt=block, sz=sz, b=True, col="accent", caps=True,
              tracking=1.0, z=z, meta={"inset": 0.0}),
            O(f"{id}_cnt{page}", "text", right - 1.4, y, 1.4, 0.35, txt=f"{page}|{total}", sz=sz, col="muted", al="r",
              z=z, meta={"inset": 0.0})]
