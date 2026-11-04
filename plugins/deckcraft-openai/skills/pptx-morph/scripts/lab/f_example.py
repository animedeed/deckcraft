"""Образец семейства: три круга -> фрагменты пересечений; части отделяются и собираются (Morph).

Правила (для всех семейств):
  * у фигуры, которая должна перелететь/перелиться, одно и то же имя «!!…» во всех состояниях;
  * свободная форма, которая должна плавно переливаться, — с одинаковым числом точек (V.resample(g, n));
  * фигура, которая только двигается/масштабируется/поворачивается, может не ресемплироваться;
  * поворот между соседними состояниями < 180° (Morph крутит по кратчайшему пути);
  * Morph ≤ 900 мс (Slide.dur), никаких auto-слайдов; текст не переливается (новый текст — новый объект);
  * не использовать: одометр, полукруглый «спидометр», колесо в угол, круг-границу на весь экран.
"""

from __future__ import annotations

from morphkit import O, Slide
from morphkit import vector as V
from morphkit.theme import mix

from lab import Variant


def _venn(cx: float, cy: float, r: float, d: float) -> list:
    import math
    cs = [V.circle(cx + d * math.cos(math.radians(a)), cy + d * math.sin(math.radians(a)), r) for a in (-90, 30, 150)]
    return sorted(V.fragment(*cs), key=lambda g: (round(g.centroid.y, 2), round(g.centroid.x, 2)))


def _state(theme, parts, cx, cy, spread: float, lit: int | None = None, alpha_others: float = 1.0) -> list[O]:
    out = []
    ink, bg, acc = theme.c("ink"), theme.c("bg"), theme.c("accent")
    for k, g in enumerate(parts):
        c = g.centroid
        dx, dy = (c.x - cx) * spread, (c.y - cy) * spread
        g2 = V.move(g, dx, dy)
        col = acc if lit == k else mix(ink, bg, 0.25 + 0.5 * (k % 3) / 2)
        out.append(V.shape(f"!!vn{k}", g2, fill=col, fa=1.0 if lit in (None, k) else alpha_others, ln=bg, lw=1.5,
                           z=10 + k))
    return out


def variants(theme) -> list[Variant]:
    cx, cy = 8.6, 3.9
    parts = _venn(cx, cy, 1.6, 1.0)
    head = lambda t: [O("!!ttl", "text", 0.8, 0.8, 5.0, 1.2, txt=t, sz=28, b=True, font="head", col="ink", z=50)]  # noqa: E731
    v1 = Variant("example", "venn_explode", "Пересечения разлетаются на части",
                 "Три области задачи и их пересечения: фрагменты отходят от центра — видно, из чего состоит "
                 "«общая зона». Роль: раскрытие структуры, вступление к разделу «что уже есть».",
                 [Slide(head("Три круга") + _state(theme, parts, cx, cy, 0.0), dur=800),
                  Slide(head("Семь частей") + _state(theme, parts, cx, cy, 0.55), dur=900),
                  Slide(head("Наша зона") + _state(theme, parts, cx, cy, 0.0, lit=3, alpha_others=0.35), dur=800)],
                 tags=["fragment", "venn", "structure"], score=3)
    return [v1]
