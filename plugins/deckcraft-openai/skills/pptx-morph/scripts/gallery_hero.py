"""Галерея «геройских» трансформаций (фаза 3): цветок-указатель темы за краем экрана, лепесток → панель,
документы → узлы графа, фрагменты → карточки, «жидкая» смена раздела. Тема «Тушь».

    python gallery_hero.py OUT_DIR [--check]

В заметках каждого слайда — что проверить при показе в PowerPoint.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from morphkit import INK, SLIDE_W, Fx, O, Slide, build_pptx, contrast, mix  # noqa: E402
from morphkit import recipes as R  # noqa: E402
from morphkit import vector as V  # noqa: E402
from morphkit.components import Kit  # noqa: E402

T, K = INK, Kit(INK)
C = T.colors
PETALS, LENGTH, WIDTH = 10, 3.55, 1.38
EDGE = (-0.35, 3.75)  # центр цветка-указателя: половина цветка за левым краем
TOPICS = [("01", "Проблема", "Нормы меняются постоянно: 15 документов изменили ПП 937 за 8 лет"),
          ("02", "Что уже есть", "Части задачи решены, вместе — нет"),
          ("03", "Метод", "Граф + тип правки + один шаг"),
          ("04", "Пример", "Пункт 538 ПТЭ: капремонт ВЛ раз в 12 лет → 10"),
          ("05", "Результаты", "Находим 9 из 10 затронутых документов")]


def turn_for(topic: int) -> float:
    """Поворот цветка, при котором лепесток topic смотрит вправо (0°): ось бутона при turn=0 — вверх (−90°)."""
    return (90 - topic * 360 / PETALS) % 360


def topic_label(t: int, x: float = 3.6) -> list[O]:
    num, name, _ = TOPICS[t]
    return [O("!!tnum", "text", x, 2.95, 2.2, 1.0, txt=num, sz=60, b=True, font="head", col="accent", z=70,
              meta={"morph_text": False}),
            O("!!tname", "text", x + 2.15, 3.18, 6.0, 0.7, txt=name, sz=30, b=True, font="head", col="ink", z=70)]


def cover() -> Slide:
    center = (9.55, 3.75)
    objs = R.mandala("m", center, PETALS, LENGTH, WIDTH, turn=turn_for(0), scale=0.82)
    objs += [O("!!ctx", "text", 0.75, 1.3, 5.5, 0.35, txt="morphkit · галерея", sz=13, b=True, caps=True, tracking=1.5,
               col="accent", z=70),
             O("!!ttl", "text", 0.75, 1.75, 5.6, 2.2, txt=["Геройские", "трансформации"], sz=48, b=True, font="head",
               col="ink", spacing=0.95, z=70),
             O("!!sub", "text", 0.75, 3.95, 5.4, 1.4, sz=17, col="ink2", z=70,
               txt=["Цветок-указатель темы за краем экрана,", "лепесток → панель, документы → узлы графа,",
                    "фрагменты → карточки, «жидкая» смена раздела"])]
    return Slide(objs, transition="fade", dur=500, fx=R.mandala_spin_in("m", PETALS, delay=0.1, step=0.06),
                 title="титул", layout="cover",
                 notes="Что проверить: лепестки по очереди раскручиваются из центра цветка (вход «Вертушка»), "
                       "каждый лепесток — многослойный, как в эталонном видео.")


def indicator(t: int, note: str, panel: bool = False, technique: str = "") -> Slide:
    center, scale = (EDGE, 1.0) if not panel else ((-1.25, 3.75), 0.86)
    objs = R.mandala("m", center, PETALS, LENGTH, WIDTH, turn=turn_for(t), scale=scale)
    if not panel:
        objs += R.pointer_lens("ptr", center, LENGTH * scale, WIDTH * scale, angle=0, color="accent", z=60)
        objs += topic_label(t)
        objs.append(O("!!tsub", "text", 3.62, 4.05, 9.0, 0.5, txt=TOPICS[t][2], sz=17, col="ink2", z=70))
    else:
        objs += R.panel_from_lens("ptr", 3.9, 0.85, 8.75, 5.8, r=0.3, color="accent", fill="surface", z=60)
        objs += [O("!!tnum", "text", 4.35, 1.15, 2.2, 1.0, txt=TOPICS[t][0], sz=60, b=True, font="head", col="accent",
                   z=70),
                 O("!!tname", "text", 6.5, 1.38, 6.0, 0.7, txt=TOPICS[t][1], sz=30, b=True, font="head", col="ink", z=70),
                 O("anim_p1", "text", 4.4, 2.6, 7.8, 2.6, sz=18, col="ink2", z=70,
                   txt=["Лепесток-указатель раскрылся в панель темы:", "внутри — содержимое раздела.",
                        "", "Цветок отъехал дальше за край и уменьшился,", "освобождая место."])]
    return Slide(objs, dur=900, title=f"указатель {t}{' панель' if panel else ''}", layout="flower-indicator",
                 technique=technique, notes=note)


def docs_to_graph() -> list[Slide]:
    n = 8
    s = []
    sheet = mix(C["accent2"], C["accent3"], 0.25)
    arc = R.doc_arc("!!doc", n, 1.2, 4.3, 11.0, sheet_w=0.82, sheet_h=1.12, spread=12, sag=0.4, fill=sheet, ln="bg")
    objs = arc + [O("!!dt", "text", 0.75, 1.2, 11, 0.8, txt="Внутренние документы", sz=34, b=True, font="head",
                    col="ink", z=70),
                  O("!!ds", "text", 0.75, 2.05, 11, 0.5, txt="формы, инструкции, чек-листы, регламенты", sz=18,
                    col="ink2", z=70)]
    s.append(Slide(objs, transition="fade", dur=500, title="документы", layout="doc-units",
                   fx=R.reveal([o.name for o in arc], "entrance_rise_up", delay=0.15, stagger=0.06, dur=0.4),
                   notes="Что проверить: листы входят по очереди слева направо (нет служебного слайда)."))
    cx, cy, r = 8.6, 3.95, 2.45
    objs = []
    for i in range(n):
        a = math.radians(-90 + i * 360 / n)
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        objs.append(R.doc_sheet(f"!!doc{i}", x - 0.21, y - 0.28, 0.42, 0.56, fill=mix(C["accent2"], C["accent3"], 0.25),
                                ln="accent" if i == n - 1 else "bg", lw=2.0 if i == n - 1 else 1.0, z=10 + i))
        objs.append(O(f"!!edge{i}", "line", cx, cy, (x - cx) * 0.83, (y - cy) * 0.83, ln="line", lw=1.25, z=4))
    objs.append(O("!!hub", "oval", cx - 0.22, cy - 0.22, 0.44, 0.44, fill="accent", z=12))
    objs += [O("!!dt", "text", 0.75, 1.2, 5.6, 1.6, txt=["Каждый документ —", "узел графа"], sz=34, b=True, font="head",
               col="ink", spacing=0.95, z=70),
             O("!!ds2", "text", 0.75, 2.95, 5.4, 1.2, sz=18, col="ink2", z=70,
               txt=["Листы сжались и разошлись по кругу:", "те же объекты, теперь — узлы связей", "с пунктом НД"])]
    s.append(Slide(objs, dur=900, title="документы → граф", layout="network", technique="носители непрерывности",
                   loops=[R.flow_along(objs[2 * (n - 1) + 1], n=3, period=1.6, color="accent", name="sig", trim=0.25)],
                   notes="Что проверить: каждый лист сам летит в свой узел и уменьшается; рёбра вырастают из центра; "
                         "по ребру к выделенному документу бежит сигнал — строго по линии."))
    s[-1].objs = [o if not o.name.startswith("!!edge") else o for o in s[-1].objs]
    return s


def fragments_to_cards() -> list[Slide]:
    a, b, c3 = V.circle(3.3, 4.3, 1.45), V.circle(5.3, 4.3, 1.45), V.circle(4.3, 2.75, 1.25)
    parts = sorted(V.fragment(a, b, c3), key=lambda p: (round(p.centroid.y, 1), p.centroid.x))
    def label(p):  # подпись по тому, каким кругам принадлежит кусочек
        inside = [n for g, n in ((a, "граф"), (b, "diff"), (c3, "модель")) if g.contains(p.representative_point())]
        return "все три" if len(inside) == 3 else " + ".join(inside)
    names = [label(p) for p in parts]
    shades = [mix(C["accent2"], C["accent3"], k / 6 * 0.85) for k in range(len(parts))]
    center_idx = max(range(len(parts)), key=lambda k: sum(1 for g in (a, b, c3) if g.contains(parts[k].representative_point())))
    s = []
    objs = [V.shape(f"!!fr{k}", V.resample(p, 120), fill="accent" if k == center_idx else shades[k], ln="bg", lw=1.5, z=10)
            for k, p in enumerate(parts)]
    objs += [O("!!ft", "text", 7.4, 2.0, 5.4, 1.6, txt=["Три подхода", "пересекаются"], sz=34, b=True, font="head",
               col="ink", spacing=0.95, z=70)]
    s.append(Slide(objs, transition="fade", dur=500, title="фрагменты", layout="venn",
                   notes="Фрагменты трёх кругов — свободные формы по 120 точек."))
    objs = []
    for k, p in enumerate(parts):
        col, row = k % 4, k // 4
        x, y = 0.75 + col * 3.1, 2.1 + row * 2.45
        objs.append(V.shape(f"!!fr{k}", V.resample(V.rect(x, y, 2.85, 2.15, r=0.2), 120),
                            fill="accent" if k == center_idx else shades[k], ln="bg", lw=1.5, z=10))
        fill = C["accent"] if k == center_idx else shades[k]
        tcol = "on_accent" if contrast(C["on_accent"], fill) >= contrast(C["ink"], fill) else "ink"
        objs.append(O(f"anim_fl{k}", "text", x + 0.2, y + 1.5, 2.5, 0.45, txt=names[k] if k < len(names) else "",
                      sz=16, b=True, col=tcol, z=20))
    objs += [O("!!ft", "text", 0.75, 0.85, 11, 0.9, txt="Каждая область — своя карточка", sz=30, b=True, font="head",
               col="ink", z=70)]
    s.append(Slide(objs, dur=900, title="фрагменты → карточки", layout="bento", technique="перелив форм (фрагменты)",
                   notes="Что проверить: каждый кусочек диаграммы переливается в свою карточку (форма меняется, "
                         "без самопересечений), центральный (все три) — янтарный."))
    return s


def blob(cx: float, cy: float, r: float, seed: int, n: int = 200) -> object:
    pts = []
    for k in range(n):
        t = 2 * math.pi * k / n
        rr = r * (1 + 0.10 * math.sin(3 * t + seed) + 0.06 * math.sin(5 * t + 2 * seed) + 0.04 * math.cos(7 * t + seed))
        pts.append((cx + rr * math.cos(t), cy + rr * math.sin(t)))
    return V.resample(V.polygon(pts), 200)


def liquid() -> list[Slide]:
    s = []
    for k, (cx, cy, r, seed, title) in enumerate([(2.2, 5.6, 2.1, 1, "Раздел 4: пример на графе"),
                                                  (9.4, 3.6, 4.4, 4, "Раздел 5: результаты")]):
        objs = [V.shape("!!blob", blob(cx, cy, r, seed), fill="surface2", z=2, meta={"bleed": True, "decor": True}),
                V.shape("!!blob2", blob(cx + 0.6, cy - 0.4, r * 0.55, seed + 2), fill="accent", fa=0.9, z=3,
                        meta={"bleed": True, "decor": True}),
                O("!!lt", "text", 0.75, 1.0, 7, 0.9, txt=title, sz=32, b=True, font="head", col="ink", z=70)]
        s.append(Slide(objs, transition="fade" if k == 0 else "morph", dur=500 if k == 0 else 900,
                       title=f"жидкий раздел {k}", layout="section-blob", technique="перелив форм (фон)" if k else "",
                       notes="Что проверить: «капли» перетекают и растут, задавая новый раздел без смены стиля; "
                             "текст заголовка меняется затуханием (политика текста)."))
    return s


def deck() -> list[Slide]:
    slides = [cover()]
    slides.append(indicator(0, "Что проверить: цветок переезжает к левому краю и растёт, половина уходит за экран; "
                               "янтарный указатель смотрит вправо на тему.", technique="указатель"))
    slides.append(indicator(1, "Что проверить: цветок поворачивается на один лепесток (36°) вокруг своего центра "
                               "по дуге; номер и название темы сменяются затуханием.", technique="указатель (серия)"))
    slides.append(indicator(1, "Что проверить: указатель-линза переливается в панель темы; цветок отъезжает дальше "
                               "и уменьшается.", panel=True, technique="лепесток → панель"))
    slides.append(indicator(2, "Что проверить: панель сворачивается обратно в указатель, цветок возвращается и "
                               "поворачивается к теме 3.", technique="указатель (серия)"))
    slides += docs_to_graph() + fragments_to_cards() + liquid()
    return slides


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    slides = deck()
    r = build_pptx(slides, T, out / "hero_gallery.pptx", title="Геройские трансформации")
    print(r["path"], len(slides), "слайдов")
    if "--check" in sys.argv:
        from morphkit.qa import lint, print_issues, xsd_check
        from morphkit.profile import DeckProfile
        print_issues(lint(slides, T, profile=DeckProfile(banned_techniques=[])))
        errs = xsd_check(r["path"])
        print("XSD:", len(errs), *errs[:5])


if __name__ == "__main__":
    main()
