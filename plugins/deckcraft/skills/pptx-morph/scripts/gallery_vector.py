"""Галерея векторных приёмов: цветок-инфографика (Spinner + вращение колеса Morph-ом), перелив форм,
булевы операции с разлётом кусочков, 3D-переворот карточки, стопка слоёв в изометрии, орбита на оси.

    python gallery_vector.py OUT_DIR [--check]

Колода — тест для записи показа в PowerPoint: в заметках каждого слайда написано, что проверить.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from morphkit import LAB, SLIDE_W, Fx, O, Slide, build_pptx, mix  # noqa: E402
from morphkit import recipes as R  # noqa: E402
from morphkit import vector as V  # noqa: E402
from morphkit.components import Kit  # noqa: E402

T, K = LAB, Kit(LAB)
C = T.colors
STEPS = [("01", "Задача и данные", "цель, источник, паспорт"),
         ("02", "Хранение", "формат и бенчмарк"),
         ("03", "Качество и разбиение", "дубли, train/val/test"),
         ("04", "Базовая модель", "простое правило → линейная"),
         ("05", "Первая сеть", "архитектура и параметры"),
         ("06", "Обучение", "ранняя остановка, сравнение"),
         ("07", "Финальная оценка", "тест и доверительный интервал"),
         ("08", "Защита", "выводы и вопросы")]
N = len(STEPS)
PIV = (4.1, 4.05)
PET = V.resample(V.petal(PIV, 0.62, 2.55, 0.98), 120)       # лепесток вверх; у всех один и тот же контур
PET_ON = V.resample(V.petal(PIV, 0.82, 2.95, 1.12), 120)    # выдвинутый активный лепесток, столько же точек


def petal_color(i: int) -> str:
    return mix(C["accent"], C["accent3"], i / (N - 1))


def flower(active: int | None, turn: int) -> list[O]:
    """turn — на сколько шагов повёрнуто колесо (активный лепесток приходит на 12 часов)."""
    objs = []
    for i in range(N):
        on = active == i
        col = petal_color(i)
        grad = V.gradient([(0, mix(col, "FFFFFF", 0.35)), (1, col)], angle=90)
        objs.append(V.shape(f"!!pet{i}", PET_ON if on else PET, pivot=PIV, rot=(i - turn) * 360 / N,
                            fill=col, grad=grad, z=6))
    objs.append(O("!!core", "oval", PIV[0] - 0.55, PIV[1] - 0.55, 1.1, 1.1, fill="bg", ln="line", lw=1.0, z=8,
                  txt="8", sz=30, b=True, font="head", al="c", va="m", col="ink"))
    import math
    for i in range(N):
        a = math.radians(-90 + (i - turn) * 360 / N)
        r = 3.3 if active == i else 3.0
        x, y = PIV[0] + r * math.cos(a), PIV[1] + r * math.sin(a)
        objs.append(O(f"!!num{i}", "text", x - 0.35, y - 0.2, 0.7, 0.4, txt=STEPS[i][0], sz=16, b=True,
                      col="accent" if active == i else "muted", al="c", va="m", z=12))
    return objs


def step_card(active: int) -> list[O]:
    code, name, sub = STEPS[active]
    x = 8.25
    return [O("!!st_code", "text", x, 2.85, 4.4, 0.9, txt=code, sz=54, b=True, font="head", col="accent", z=20),
            O("!!st_name", "text", x, 3.85, 4.6, 0.6, txt=name, sz=26, b=True, font="head", col="ink", z=20),
            O("!!st_sub", "text", x, 4.55, 4.6, 0.45, txt=sub, sz=17, col="ink2", z=20)]


def head(label: str, title: str) -> list[O]:
    return K.label(label) + K.title(title, size="h2")


def side_head(label: str, title: str) -> list[O]:
    """Заголовок в правой колонке: цветок занимает всю высоту слева, шапка не давит на него сверху."""
    return K.label(label, x=8.25, y=0.75, w=4.6) + K.title(title, x=8.25, y=1.1, w=4.6, size="h2")


def section_flower() -> list[Slide]:
    s = []
    fx = [Fx("entrance_faded_zoom", "!!core", dur=0.5, start="at")]
    for i in range(N):
        fx.append(Fx("entrance_spinner", f"!!pet{i}", dur=0.8, start="at", delay=0.15 + i * 0.09))
    fx += [Fx("entrance_fade", f"!!num{i}", dur=0.3, start="at", delay=1.05 + i * 0.05) for i in range(N)]
    s.append(Slide(side_head("Вектор · цветок", "Лепестки из\nпересечения кругов,\nвход «Вертушка»") + flower(None, 0),
                   fx=fx, transition="fade", dur=600, title="цветок: вход",
                   notes="Что проверить: лепестки по очереди раскручиваются из центра цветка (не из своих центров); "
                         "номера проявляются после лепестков."))
    for k, (active, turn) in enumerate([(0, 0), (1, 1), (2, 2), (5, 5)]):
        s.append(Slide(side_head("Вектор · колесо Morph", "Колесо поворачивается,\nактивный шаг — на 12 часов")
                       + flower(active, turn) + step_card(active), dur=1100 if k else 900,
                       title=f"колесо: {STEPS[active][0]}",
                       notes="Что проверить: колесо вращается вокруг центра по дуге (лепестки не режут хорду); "
                             "шаг на 135° (03 → 06) идёт в ту же сторону, кратчайшим путём; активный лепесток плавно "
                             "выдвигается, прежний — задвигается; номера едут за лепестками."))
    return s


def section_shapes() -> list[Slide]:
    cx, cy = SLIDE_W / 2, 4.15
    forms = [("круг", V.circle(cx, cy, 1.55)),
             ("скруглённый квадрат", V.rect(cx - 1.4, cy - 1.4, 2.8, 2.8, r=0.45)),
             ("звезда", V.star(cx, cy, 1.85, 0.78, 5)),
             ("капля", V.union(V.circle(cx, cy + 0.35, 1.25), V.polygon([(cx - 0.95, cy - 0.45), (cx, cy - 2.0),
                                                                        (cx + 0.95, cy - 0.45)])))]
    s = []
    for k, (name, g) in enumerate(forms):
        col = mix(C["accent"], C["accent3"], k / 3 * 0.6)
        objs = head("Вектор · перелив формы", f"Одна свободная форма: {name}")
        objs.append(V.shape("!!blob", V.resample(g, 160), fill=col, z=6,
                            grad=V.gradient([(0, mix(col, "FFFFFF", 0.3)), (1, col)], angle=60)))
        objs.append(O("!!cap", "text", 0.9, 6.55, 11.5, 0.4, txt=" → ".join(n if i != k else "{a:" + n + "}"
                                                                           for i, (n, _) in enumerate(forms)),
                      sz=16, col="muted", z=20))
        s.append(Slide(objs, dur=1300, title=f"форма: {name}", transition="morph" if k else "fade",
                       notes="Что проверить: форма переливается без самопересечений и «перекрута» — у всех форм "
                             "160 точек, обход по часовой стрелке, старт с верхней точки."))
    return s


def section_boolean() -> list[Slide]:
    a, b = V.circle(5.67, 4.85, 1.45), V.circle(7.67, 4.85, 1.45)
    c3 = V.circle(6.67, 3.35, 1.2)
    parts = V.fragment(a, b, c3)
    parts.sort(key=lambda p: (round(p.centroid.y, 1), p.centroid.x))
    center = V.union(a, b, c3).centroid
    s = []
    base = [V.shape("!!ca", a, fill="accent", fa=0.85), V.shape("!!cb", b, fill="accent2", fa=0.85),
            V.shape("!!cc", c3, fill="accent3", fa=0.85)]
    s.append(Slide(head("Вектор · булевы операции", "Три круга") + base, transition="fade", dur=600,
                   title="три круга", notes="Обычные свободные формы-круги."))
    cols = [mix(C["accent"], C["accent3"], i / max(len(parts) - 1, 1)) for i in range(len(parts))]
    frag = [V.shape(f"!!fr{i}", p, fill=cols[i], ln="bg", lw=1.5) for i, p in enumerate(parts)]
    s.append(Slide(head("Вектор · булевы операции", f"Фрагментация: {len(parts)} частей") + frag, dur=700,
                   title="фрагменты", notes="Круги заменены кусочками на тех же местах: переход почти незаметен."))
    out = []
    for i, p in enumerate(parts):
        dx, dy = p.centroid.x - center.x, p.centroid.y - center.y
        out.append(V.shape(f"!!fr{i}", V.move(p, dx * 0.4, dy * 0.4), fill=cols[i], ln="bg", lw=1.5))
    s.append(Slide(head("Вектор · булевы операции", "Разлёт: каждая часть — свой объект") + out, dur=1200,
                   title="разлёт", notes="Что проверить: кусочки разъезжаются от центра, формы не искажаются."))
    ops = [("объединение", V.union(a, b)), ("пересечение", V.intersect(a, b)), ("вычитание", V.subtract(a, b)),
           ("исключение", V.combine(a, b))]
    objs = head("Вектор · булевы операции", "Объединение, пересечение, вычитание, исключение")
    for k, (name, g) in enumerate(ops):
        g = V.scale(V.move(g, -center.x, -center.y), 0.48, origin=(0, 0))
        cx = 1.95 + k * 3.15
        objs.append(V.shape(f"op{k}", V.move(g, cx, 4.0), fill="accent" if k % 2 == 0 else "accent2"))
        objs.append(O(f"opl{k}", "text", cx - 1.45, 5.55, 2.9, 0.4, txt=name, sz=16, al="c", col="ink2", z=20))
    s.append(Slide(objs, dur=900, title="операции", notes="Статичный справочник Merge Shapes; исключение = две "
                   "части (дырка-линза) — у такой формы Morph заменит перелив затуханием."))
    return s


def section_3d() -> list[Slide]:
    x, y, w, h = 4.4, 2.25, 4.5, 3.6
    front = dict(txt="Вопрос\nПочему MAE?", sz=26, b=True, font="head", col="ink", al="c", va="m", fill="surface",
                 ln="line", lw=1.0, radius=0.2, z=8)
    back = dict(txt="Ответ\nОшибка в баллах", sz=26, b=True, font="head", col="on_accent", al="c", va="m",
                fill="accent", radius=0.2, z=9)
    s = []
    objs = head("Вектор · 3D", "Переворот карточки внутри слайда")
    objs += [O("front", "rrect", x, y, w, h, **front), O("back", "rrect", x, y, w, h, **back)]
    s.append(Slide(objs, dur=600, transition="fade", title="флип", fx=R.flip_fx("front", "back", delay=0.6),
                   notes="Что проверить: лицо поворачивается ребром и исчезает, оборот появляется тем же поворотом — "
                         "без служебных слайдов, назад листается нормально."))
    layers = ["Данные", "Признаки", "Модель", "Прогноз"]
    iso = dict(x=314.7, y=324.6, z=60.2, camera="orthographicFront", depth=8)
    for k, mode in enumerate(("flat", "iso")):
        objs = head("Вектор · 3D", "Слои: список → изометрическая стопка" if mode == "iso" else "Слои конвейера списком")
        for i, name in enumerate(layers):
            col = mix(C["accent"], C["accent3"], i / 3)
            if mode == "flat":
                ox, oy, ow, oh, d3 = 4.65, 2.2 + i * 1.08, 4.0, 0.88, V.rot3d()
            else:
                ox, oy, ow, oh, d3 = 4.85, 4.55 - i * 0.6, 3.6, 2.2, V.rot3d(depth_color=col, **iso)
            objs.append(O(f"!!lay{i}", "rrect", ox, oy, ow, oh, fill=col, txt=name, sz=20, b=True, col="on_accent",
                          al="c", va="m", radius=0.12, z=6 + i, meta={"d3": d3}))
        s.append(Slide(objs, dur=1400, title=f"слои {mode}", transition="morph" if k else "fade",
                       notes="Что проверить: плоские плашки поворачиваются в изометрию и складываются в стопку; "
                             "подписи поворачиваются вместе с плашками."))
    return s


def section_orbit() -> list[Slide]:
    piv = (6.67, 4.1)
    s = []
    for k, turn in enumerate((0, 120, 240)):
        objs = head("Вектор · орбита", "Ось вращения: дуга вместо хорды")
        objs.append(O("orbit", "oval", piv[0] - 2.3, piv[1] - 2.3, 4.6, 4.6, fill=None, ln="line", lw=1.25, dash="dash"))
        objs.append(O("!!sun", "oval", piv[0] - 0.6, piv[1] - 0.6, 1.2, 1.2, fill="accent", z=8))
        for i in range(3):
            g = V.circle(piv[0], piv[1] - 2.3, 0.26)
            objs.append(V.shape(f"!!sat{i}", g, pivot=piv, rot=i * 120 + turn, fill="accent2", z=9))
        import math
        a = math.radians(-90 + 60 + turn)
        cx, cy = piv[0] + 2.3 * math.cos(a), piv[1] + 2.3 * math.sin(a)
        objs.append(O("!!chord", "oval", cx - 0.2, cy - 0.2, 0.4, 0.4, fill="accent3", z=9))
        objs.append(O("!!leg", "text", 0.9, 6.6, 11.5, 0.4, sz=15, col="muted", z=20,
                      txt="{a2:зелёные} — форма в рамке с центром на оси (дуга)   ·   {b:жёлтый} — обычный овал (хорда)"))
        s.append(Slide(objs, dur=1400, title=f"орбита {turn}°", transition="morph" if k else "fade",
                       notes="Что проверить: зелёные спутники идут по пунктирной орбите, жёлтый срезает по прямой; "
                             "шаг 120° — меньше 180°, поэтому направление однозначно."))
    return s


def deck() -> list[Slide]:
    cover = Slide(K.label("morphkit · вектор и 3D") + K.title("Галерея векторных приёмов", y=2.6)
                  + K.text("sub", 0.9, 3.7, 11, "Цветок и колесо · перелив формы · булевы операции · 3D · орбита"),
                  transition="fade", title="обложка")
    slides = [cover] + section_flower() + section_shapes() + section_boolean() + section_3d() + section_orbit()
    for sl in slides:  # скорость профиля по умолчанию: Morph ≤ 0,9 с, затухание ≤ 0,5 с
        sl.dur = min(sl.dur, 500 if sl.transition == "fade" else 900)
    return slides


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    slides = deck()
    r = build_pptx(slides, T, out / "vector_gallery.pptx", title="Галерея векторных приёмов")
    print(r["path"], len(slides), "слайдов")
    if "--check" in sys.argv:
        from morphkit.qa import lint, print_issues, xsd_check
        print_issues(lint(slides, T))
        errs = xsd_check(r["path"])
        print("XSD:", len(errs), *errs[:5])


if __name__ == "__main__":
    main()
