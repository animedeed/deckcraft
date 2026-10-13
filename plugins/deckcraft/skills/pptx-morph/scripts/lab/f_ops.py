"""Операторы движения (morphkit.ops) на разных базовых формах: один оператор — анимация для любой формы.

База × оператор (или цепочка операторов) = вариант. Здесь — по 2–3 базы на оператор и цепочки из 2–3 операторов.
"""

from __future__ import annotations

import math

from morphkit import O, Slide
from morphkit import ops as P
from morphkit import recipes as R
from morphkit import vector as V
from morphkit.motif import Flower, MotifTrack, Orbit
from morphkit.theme import mix

from lab import Variant

C = (7.6, 3.95)


def _head(t: str) -> list[O]:
    return [O("!!ttl", "text", 0.6, 0.55, 5.6, 1.4, txt=t, sz=26, b=True, font="head", col="ink", z=900)]


def bases(theme) -> dict:
    fl = MotifTrack(Flower("fl", petals=10, length=2.5, width=1.0), theme)
    flower = P.to_vec(fl.at("hero", center=C, scale=1.0), n=48)
    dots = R.dots("dt", [(x + 0.08, y + 0.08) for x, y in R.grid(120, C[0] - 2.85, C[1] - 1.5, 15, 0.38)], 0.18,
                  colors=["accent" if (i * 7) % 11 == 0 else "ink2" for i in range(120)], z=20)
    cards = []
    for i in range(5):
        x = C[0] - 3.6 + i * 1.5
        cards += [O(f"!!cd{i}", "rrect", x, C[1] - 0.9, 1.3, 1.8, fill=mix(theme.c("surface2"), theme.c("accent"), 0.12 * i),
                    ln="line", lw=1, radius=0.12, z=20 + i)]
    orb = MotifTrack(Orbit("or", rings=5, r0=0.6, gap=0.5), theme).at("hero", center=C, scale=1.0)
    venn = []
    cs = [V.circle(C[0] + 0.95 * math.cos(math.radians(a)), C[1] + 0.95 * math.sin(math.radians(a)), 1.55)
          for a in (-90, 30, 150)]
    for k, g in enumerate(sorted(V.fragment(*cs), key=lambda g: (round(g.centroid.y, 2), g.centroid.x))):
        venn.append(V.shape(f"!!vn{k}", V.resample(g, 64), fill=mix(theme.c("ink"), theme.c("bg"), 0.2 + 0.1 * (k % 4)),
                            ln="bg", lw=1.5, z=10 + k))
    return {"цветок": flower, "точки": dots, "карточки": P.to_vec(cards, 40), "орбита": P.to_vec(orb, 48),
            "пересечения": venn}


def variants(theme) -> list[Variant]:
    B = bases(theme)
    out: list[Variant] = []

    def add(key, title, idea, states, tags, score=3, dur=900):
        out.append(Variant("ops", key, title, idea,
                           [Slide(_head(h) + objs, dur=dur, title=h) for h, objs in states], tags=tags, score=score))

    vanish = (10.6, 2.2)
    for bname, b in B.items():
        tag = {"цветок": "fl", "точки": "dt", "карточки": "cd", "орбита": "or", "пересечения": "vn"}[bname]
        add(f"tilt_{tag}", f"Наклон в пространство: {bname}",
            "Форма ложится «на стол» (поворот плоскости с перспективой) — переход от схемы к фону или к виду сверху.",
            [(bname.capitalize(), b), ("Наклон 62°", P.tilt3d(b, C, pitch=62)),
             ("Поворот в пространстве", P.tilt3d(b, C, pitch=58, yaw=35))], ["3d", "space", tag])
        add(f"depth_{tag}", f"Уход в глубину: {bname}",
            "Наклон и уход к точке схода с затуханием — содержимое следующего слайда выходит на первый план.",
            [(bname.capitalize(), b), ("Ушла в глубину", P.recede(P.tilt3d(b, C, pitch=60), vanish, 0.6, fade=0.45))],
            ["3d", "background", tag])
        add(f"swirl_{tag}", f"Вихрь: {bname}",
            "Внешние части закручиваются сильнее внутренних — «засасывание» в процесс, переход к циклу.",
            [(bname.capitalize(), b), ("Вихрь", P.swirl(b, C, 120, 2.8)), ("Обратно", b)], ["swirl", tag])
        add(f"explode_{tag}", f"Разлёт и сборка: {bname}",
            "Части отходят от центра, видно устройство; затем собираются — «из чего состоит».",
            [(bname.capitalize(), b), ("Разлёт", P.explode(b, C, 0.65)), ("Собрано", b)], ["fragment", tag])
        add(f"wave_{tag}", f"Бегущая волна: {bname}",
            "Волна смещения проходит по форме за 3 шага — «сигнал прошёл через систему».",
            [(bname.capitalize(), b), ("Волна", P.wave(b, 0.35, 3.0, 0.0)), ("Волна дальше", P.wave(b, 0.35, 3.0, 2.1)),
             ("Затихла", b)], ["wave", tag])
    # цепочки
    for bname in ("цветок", "пересечения", "карточки"):
        b = B[bname]
        tag = {"цветок": "fl", "пересечения": "vn", "карточки": "cd"}[bname]
        add(f"chain_explode_tilt_{tag}", f"Разлёт → наклон → глубина: {bname}",
            "Цепочка операторов: устройство формы раскрывается, затем вся конструкция ложится в пространство и уходит "
            "фоном — три смысла за три клика.",
            [(bname.capitalize(), b), ("Части", P.explode(b, C, 0.5)),
             ("В пространстве", P.tilt3d(P.explode(b, C, 0.5), C, pitch=58, yaw=20)),
             ("Фон", P.recede(P.tilt3d(P.explode(b, C, 0.5), C, pitch=58, yaw=20), vanish, 0.55, fade=0.5))],
            ["chain", "3d", tag], score=4)
        add(f"chain_swirl_gather_{tag}", f"Вихрь → сбор в точку → раскрытие: {bname}",
            "Форма закручивается и стягивается в узел, затем раскрывается снова — «сжатие» перед новым разделом.",
            [(bname.capitalize(), b), ("Закрутка", P.swirl(b, C, 90, 2.6)),
             ("Узел", P.gather(P.swirl(b, C, 160, 2.6), C, 0.25)), ("Раскрытие", b)], ["chain", tag])
    # карточки: веер и отслаивание
    cards = B["карточки"]
    add("fan_cards", "Веер карточек", "Карточки разворачиваются веером вокруг нижней точки — выбор из вариантов.",
        [("Ряд", cards), ("Веер", P.fan(P.gather(cards, (C[0], C[1]), 1.0), (C[0], C[1] + 2.6), 70))],
        ["cards", "fan"])
    add("peel_cards", "Стопка → лесенка", "Карточки лежат стопкой и раскрываются лесенкой — слои, версии, этапы.",
        [("Стопка", P.gather(cards, (C[0] - 0.6, C[1] - 0.9), 1.0)),
         ("Лесенка", P.peel(P.gather(cards, (C[0] - 0.6, C[1] - 0.9), 1.0), (0.55, 0.32)))], ["cards", "peel"])
    add("lift_flower", "Лепесток к зрителю", "Один лепесток выдвигается к зрителю с тенью — выбранная тема.",
        [("Цветок", B["цветок"]), ("Тема 3", P.lift(B["цветок"], [o.name for o in B["цветок"] if o.name.startswith("!!fl2_")],
                                                   1.25, -0.2, shadow=False))], ["flower", "lift"])
    return out
