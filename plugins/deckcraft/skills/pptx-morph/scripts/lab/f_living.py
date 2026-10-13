"""Живые последовательности: одна сложная фигура проходит всю «колоду» в разных ролях (ответ на отзыв
«лепестки красивые, но используются мало — эффектно только первое появление»).

seq_flower (10 состояний): распускается → карта доклада (разделы у лепестков, по кольцу едет увеличенный
сегмент) → указатель раздела за краем (деление лепестка залито) → полосы лепестка расходятся в 4 карточки тем →
карточки возвращаются, лепесток залит → сегмент едет к следующему разделу → цветок ложится в 3D и уходит в глубину
за содержимое → лепестки = значения → слои лепестков становятся сегментами столбиков → финал.
"""

from __future__ import annotations

import math

from morphkit import O, Slide
from morphkit import ops as P
from morphkit import vector as V
from morphkit.motif import Flower
from morphkit.theme import mix

from lab import Variant

N = 48  # точек на контур: все состояния одной фигуры переливаются друг в друга
PET, LAY, LEN, WID = 8, 5, 2.6, 1.05
SECTIONS = ["Данные", "Признаки", "Модель", "Итог"]
VALUES = [0.142, 0.093, 0.054, 0.047, 0.041, 0.034, 0.028, 0.021]
VNAMES = ["плотность", "сахар", "летуч. кисл.", "спирт", "тип вина", "общий SO₂", "сульфаты", "своб. SO₂"]


def flower(theme, center, scale=1.0, turn=0.0, sizes=None, focus=None, bands=None, alpha=1.0, z=6,
           bake: bool = False) -> list[O]:
    """Цветок с рамками на оси (поворот между слайдами — вращение, а не перелив точек). bake=True — поворот
    «запечён» в контуры (нужно для проекции в 3D)."""
    f = Flower("fl", petals=PET, layers=LAY, length=LEN, width=WID, n=N)
    objs = f.objs(theme, center=center, scale=scale, turn=turn, sizes=sizes, focus=focus, fill_bands=bands, alpha=alpha,
                  z=z)
    return P.to_vec(objs, n=N) if bake else objs


def ring(theme, center, r, seg_angle, thick=0.05, seg_thick=0.22, seg_span=24, z=80) -> list[O]:
    """Тонкое кольцо + увеличенный сегмент кольца (кусок кольца, «вынесенный» наружу и толще) на угле seg_angle.
    Сегмент построен на 0° и повёрнут вокруг центра (рамка на оси) — между слайдами он едет по кругу."""
    cx, cy = center
    band = V.subtract(V.circle(cx, cy, r + thick / 2, seg=160), V.circle(cx, cy, r - thick / 2, seg=160))
    seg = V.sector(cx, cy, r + seg_thick, -seg_span / 2, seg_span / 2, r_in=r + 0.04)
    return [V.shape("!!rg_band", band, fill="line", z=z),
            V.shape("!!rg_seg", V.resample(seg, N), pivot=(cx, cy), rot=seg_angle % 360, fill="accent", z=z + 1)]


def head(t: str, sub: str | None = None, x: float = 0.6) -> list[O]:
    out = [O("!!ttl", "text", x, 0.5, 6.2, 0.7, txt=t, sz=28, b=True, font="head", col="ink", z=900)]
    if sub:
        out.append(O("!!sub", "text", x, 1.2, 6.2, 0.9, txt=sub, sz=16, col="ink2", z=900))
    return out


def _parts(objs, k):
    return [o for o in objs if o.name.startswith(f"!!fl{k}_")]


def seq_flower(theme) -> Variant:
    S = []
    hero_c, map_c, edge_c = (8.6, 3.85), (6.67, 4.05), (-0.35, 3.75)
    step = 360 / PET
    facing = lambda k: 90 - k * step  # noqa: E731 — лепесток k смотрит вправо

    # 1. распускается
    st = flower(theme, hero_c, 1.05, 0)
    fx = P.stagger_by([o for o in st if o.name.startswith("!!fl") and o.name != "!!fl_disc"],
                      key=lambda o: math.atan2(o.y + o.h / 2 - hero_c[1], o.x + o.w / 2 - hero_c[0]) % (2 * math.pi),
                      effect="entrance_faded_zoom", delay=0.1, step=0.012, dur=0.4)
    S.append(Slide(head("Одна фигура — вся колода", "Цветок проходит все роли: обложка, карта, указатель, карточки, "
                        "фон, данные, график") + st, dur=700, fx=fx, title="распускается"))

    # 2. карта доклада: разделы у лепестков 0,2,4,6; сегмент кольца — на разделе 1
    def mapstate(cur: int, turn: float):
        objs = flower(theme, map_c, 0.82, turn, focus=2 * cur)
        r = LEN * 0.82 + 0.28
        for i, name in enumerate(SECTIONS):
            a = math.radians(-90 + turn + 2 * i * step)
            x, y = map_c[0] + (r + 0.55) * math.cos(a), map_c[1] + (r + 0.42) * math.sin(a)
            objs.append(O(f"!!sec{i}", "text", x - 1.0, y - 0.22, 2.0, 0.44, txt=name, sz=16, b=i == cur,
                          col="accent" if i == cur else "ink2", al="c", va="m", z=900))
        return objs + ring(theme, map_c, r, -90 + turn + 2 * cur * step + 90 - 90)
    S.append(Slide(head("Карта доклада") + mapstate(0, 0), dur=900, title="карта: раздел 1"))

    # 3. указатель раздела 1 у края, четверть лепестка залита
    def pointer(k: int, part: float):
        return flower(theme, edge_c, 0.86, facing(k), focus=k, bands={k: part}) + ring(theme, edge_c, LEN * 0.86 + 0.3, 0)
    S.append(Slide(head("01 · Данные", "Тема 1 из 4: откуда образцы", x=3.3) + pointer(0, 0.25) +
                   [O("!!body", "text", 3.3, 2.4, 8.5, 1.4, txt=["6497 образцов, 1599 красных и 4898 белых.",
                                                               "Деление лепестка = пройденная тема раздела."], sz=18,
                      col="ink", z=900)], dur=900, title="указатель 1/4"))

    # 4. полосы лепестка 0 расходятся в 4 карточки тем
    base = pointer(0, 0.25)
    cards = []
    names = ["Источник", "Качество", "Копии", "Разбиение"]
    for j in range(LAY - 1):
        x = 3.3 + j * 2.4
        g = V.resample(V.rect(x, 2.45, 2.15, 3.1, r=0.16), N)
        src = next(o for o in base if o.name == f"!!fl0_{LAY - 2 - j}")  # от внутренней полосы к внешней
        cards.append(V.shape(src.name, g, fill=mix(theme.c("accent"), theme.c("surface"), [0.0, 0.55, 0.68, 0.8][j]),
                                 z=60 + j))
        cards.append(O(f"!!ct{j}", "text", x + 0.15, 2.65, 1.85, 1.0, txt=[f"{j + 1}", names[j]], sz=18, b=True,
                       col="on_accent" if j == 0 else "ink", z=900))
    rest = [o for o in base if not any(o.name == c.name for c in cards)]
    S.append(Slide(head("01 · Данные", "Лепесток раздела раскрылся в 4 темы", x=3.3) + rest + cards, dur=900,
                   title="лепесток → карточки"))

    # 5. карточки возвращаются в лепесток, раздел пройден целиком
    S.append(Slide(head("01 · Данные", "Раздел пройден: лепесток залит", x=3.3) + pointer(0, 1.0), dur=900,
                   title="указатель 4/4"))

    # 6. карта: сегмент едет по кольцу к разделу 2
    S.append(Slide(head("Карта доклада") + mapstate(1, 0), dur=900, title="карта: раздел 2"))

    # 7. цветок ложится в пространство и уходит в глубину за содержимое
    deep = P.recede(P.tilt3d(flower(theme, map_c, 0.82, 0, focus=2, bake=True), map_c, pitch=64, yaw=18), (10.0, 3.0),
                    0.35, fade=0.55)
    deep = [o.copy(z=o.z - 500) for o in deep]
    S.append(Slide(head("02 · Признаки", "Цветок ушёл в глубину — на первом плане содержимое") + deep +
                   [O("!!card", "rrect", 0.6, 2.4, 6.4, 3.6, fill="surface", ln="line", lw=1, radius=0.16, z=600),
                    O("!!cardt", "text", 0.9, 2.7, 5.8, 3.0, txt=["11 химических показателей", "и тип вина —",
                                                                  "12 входных величин"], sz=22, col="ink", z=900)],
                   dur=900, title="3D: в глубину"))

    # 8. данные: лепестки = важность признаков
    data_c = (8.9, 4.2)
    top = max(VALUES)
    sizes = [0.2 + 0.8 * v / top for v in VALUES]
    fl = flower(theme, data_c, 0.8, 0, sizes=sizes, focus=0)
    labels = []
    for k, (nm, v) in enumerate(zip(VNAMES, VALUES)):
        a = math.radians(-90 + k * step)
        rr = LEN * 0.8 * max(sizes[k], 0.62) + 0.35
        x, y = data_c[0] + rr * math.cos(a), data_c[1] + rr * math.sin(a)
        al = "l" if math.cos(a) > 0.3 else ("r" if math.cos(a) < -0.3 else "c")
        bx = x if al == "l" else (x - 1.9 if al == "r" else x - 0.95)
        labels.append(O(f"!!vl{k}", "text", bx, y - 0.3, 1.9, 0.6, txt=[nm, f"+{v:.3f}".replace(".", ",")], sz=13,
                        col="ink2", al=al, va="m", z=900))
    S.append(Slide(head("Лепестки = значения", "Рост ошибки, если перемешать признак") + fl + labels, dur=900,
                   title="данные"))

    # 9. слои каждого лепестка становятся сегментами столбика (сортировка по значению)
    bars = []
    x0, base_y, bw, gap, H = 0.9, 6.3, 1.05, 0.42, 3.9
    for k in range(PET):
        x = x0 + k * (bw + gap)
        h = H * VALUES[k] / top
        segs = LAY  # 4 полосы + ядро
        for j in range(LAY):
            src = next(o for o in fl if o.name == f"!!fl{k}_{j}")
            sh = h / segs
            y = base_y - h + j * sh
            bars.append(V.shape(src.name, V.resample(V.rect(x, y, bw, max(sh - 0.03, 0.02)), N), fill=src.fill,
                                fa=1.0, z=60 + j, meta={"grad": src.meta.get("grad")} if src.meta.get("grad") else {}))
        bars.append(O(f"!!vl{k}", "text", x - 0.25, base_y + 0.08, bw + 0.5, 0.6,
                      txt=[VNAMES[k], f"+{VALUES[k]:.3f}".replace(".", ",")], sz=13, col="ink2", al="c", va="t",
                      z=900))
    bars.append(O("!!fl_disc", "oval", x0 + 0.3, base_y - 0.05, 0.1, 0.1, fill="bg", fa=0.0, ln=None, z=50))
    S.append(Slide(head("Лепестки → столбики", "Слои лепестка стали сегментами столбика") + bars, dur=900,
                   title="столбики"))

    # 10. финал: цветок собирается, все разделы пройдены
    S.append(Slide(head("Финал", "Все разделы пройдены — лепестки залиты") +
                   flower(theme, hero_c, 1.05, 0, bands={k: 1.0 for k in range(0, PET, 2)}), dur=900, title="финал"))
    return Variant("living", "seq_flower", "Цветок живёт всю колоду (10 состояний)",
                   "Одна сложная фигура проходит роли: обложка, карта доклада с бегущим сегментом, указатель с прогрессом, "
                   "лепесток → карточки тем, 3D-уход в глубину, лепестки = значения, слои → столбики, финал.",
                   S, tags=["sequence", "flower", "navigation", "3d", "data"], score=4)


def variants(theme) -> list[Variant]:
    return [seq_flower(theme)]
