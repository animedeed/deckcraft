"""Семейство «Изометрия»: бруски и призмы из трёх затенённых граней (верх светлее, бока темнее).

Всё — плоские проекции, посчитанные нами (Cam3), поэтому Morph и предпросмотр совпадают. Грани — свободные формы
по 4 точки в общей рамке слайда: вершины едут линейно, брусок растёт, едет, раскладывается без «вздутия».
Смена камеры (вид сверху → изометрия, изометрия → вид спереди) — тоже просто другие проекции тех же граней:
у бруска всегда три грани ym, xm, top; при yaw 0..90 и pitch 0..90 они не переворачиваются, а ребром вырождаются.
"""

from __future__ import annotations

import math
import random

from morphkit import O, Slide
from morphkit.theme import mix

from lab import Variant
from lab._c_util import Cam3, boxes, face_col, fitcam, head, ink_on, iso, label, poly, recam

FAM = "iso"
AREA = (5.4, 1.15, 7.4, 5.55)  # кадр для сцены справа от шапки
TOP = [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]


def _pal(theme):
    ink2, bg = theme.c("ink2"), theme.c("bg")
    return {
        "grey": mix(ink2, bg, 0.45), "grey2": mix(ink2, bg, 0.62), "grey3": mix(ink2, bg, 0.30),
        "acc": theme.c("accent"), "acc3": theme.c("accent3"), "acc2": theme.c("accent2"),
        "floor": mix(theme.c("surface2"), ink2, 0.10), "bg": bg,
        "shadow": mix(theme.c("surface2"), "000000", 0.45),
    }


def _shadow(name, cam, x, y, w, d, h, col, fa=0.55, z=3, k=(0.30, -0.55)):
    """Тень бруска на полу: 6 вершин всегда (при h=0 — сам след)."""
    a, b = k[0] * h, k[1] * h
    pts3 = [(x, y + d, 0), (x, y, 0), (x + a, y + b, 0), (x + w + a, y + b, 0), (x + w + a, y + d + b, 0), (x + w, y + d, 0)]
    return poly(name, [cam.p(p) for p in pts3], fill=col, fa=fa, z=z, meta={"nofit": True})


def _floor(name, cam, x, y, w, d, col, z=1, fa=1.0):
    pts3 = [(x, y, 0), (x + w, y, 0), (x + w, y + d, 0), (x, y + d, 0)]
    return poly(name, [cam.p(p) for p in pts3], fill=col, fa=fa, z=z)


def _top_text_col(theme, cam, base):
    return ink_on(theme, face_col(cam, TOP, base))


def _seq(fam, key, title, idea, heads, make, cam, ks, dur=850, tags=(), score=3, area=AREA):
    cam = fitcam(cam, make, ks, area)
    return Variant(fam, key, title, idea, [Slide(heads[i] + make(cam, k), dur=dur) for i, k in enumerate(ks)],
                   tags=list(tags), score=score)


# ----------------------------------------------------------------------------- 1. план → объём (столбики)

def v_bars(theme):
    pal = _pal(theme)
    cats = ["Север", "Центр", "Юг", "Восток", "Запад"]
    vals = [3.0, 5.4, 2.2, 4.1, 6.3]

    def make(cam, k):
        objs = [_floor("!!fl", cam, -0.6, -0.6, 10.2, 2.4, pal["floor"])]
        specs = []
        for i, v in enumerate(vals):
            h = 0.0 if k == 0 else v * 0.8
            specs.append(dict(n=f"!!b{i}", x=i * 2.0, y=0, z=0, w=1.2, d=1.2, h=h,
                              col=pal["acc"] if (k == 2 and i == 4) else pal["grey"]))
            objs.append(_shadow(f"!!b{i}_sh", cam, i * 2.0, 0, 1.2, 1.2, h, pal["shadow"]))
        objs += boxes(cam, specs)
        for i, c in enumerate(cats):
            px, py = cam.p((i * 2.0 + 0.6, -0.6, 0))
            objs.append(label(f"!!cat{i}", px - 0.8, py + 0.08, 1.6, c, sz=13, col="ink2", al="c"))
            if k >= 1:
                tx, ty = cam.p((i * 2.0 + 0.6, 0.6, vals[i] * 0.8))
                col = "accent" if (k == 2 and i == 4) else "ink"
                objs.append(label(f"val{i}", tx - 0.6, ty - 0.5, 1.2, f"{vals[i]:.1f}", sz=16, b=True, col=col, al="c"))
        return objs

    heads = [head("Пять регионов", "плоский план"), head("Объём продаж", "млн ₽ за квартал"),
             head("Лидер — Запад", "рост вдвое за год")]
    return _seq(FAM, "bars_grow", "План вырастает в столбики",
                "Плитки регионов на полу поднимаются брусками высотой «значение» (с тенью); третий шаг перекрашивает "
                "лидера. Роль: данные — 3–7 величин, когда нужен «вес» и пространство вместо плоских столбиков.",
                heads, make, iso(0, 0, 1), [0, 1, 2], tags=["iso", "data", "grow", "3d"], score=4)


# ----------------------------------------------------------------------------- 2. стопка слоёв архитектуры раздвигается

LAYERS = ["Интерфейс", "API-шлюз", "Сервисы", "Данные", "Инфраструктура"]


def v_stack(theme):
    pal = _pal(theme)
    n = len(LAYERS)

    def make(cam, k):
        objs, specs = [], []
        gap = [0.0, 0.55, 0.55][k]
        th = 0.32
        for i in range(n):
            j = n - 1 - i
            zb = j * (th + gap)
            hot = k == 2 and i == 2
            dx = -2.6 if hot else 0.0  # выезжает к зрителю влево (−x), подписи справа остаются открытыми
            specs.append(dict(n=f"!!ly{i}", x=dx, y=0, z=zb, w=3.0, d=3.0, h=th, zo=10 + j * 4 + (40 if hot else 0),
                              col=pal["acc"] if hot else mix(pal["grey"], pal["bg"], 0.12 * (i % 2))))
            if k >= 1:
                px, py = cam.p((3.0, 0.0, zb + th / 2))
                objs.append(O(f"!!ll{i}", "line", px + 0.1, py, 0.7, 0, ln="line", lw=1.0, z=90))
                objs.append(label(f"!!lt{i}", px + 0.9, py - 0.17, 2.6, LAYERS[i], sz=15,
                                  col="accent" if hot else "ink2", b=hot))
        return objs + boxes(cam, specs)

    heads = [head("Платформа", "одна стопка"), head("Пять слоёв", "снизу вверх"), head("Слой сервисов", "здесь меняем")]
    return _seq(FAM, "stack_explode", "Стопка слоёв раздвигается",
                "Плотный брусок платформы расслаивается на слои с подписями; третий шаг выдвигает один слой к зрителю. "
                "Роль: архитектура, состав системы, «где мы меняем» — вместо плоской схемы слоёв.",
                heads, make, iso(0, 0, 1), [0, 1, 2], tags=["iso", "layers", "explode", "architecture"], score=4,
                area=(5.2, 1.0, 5.2, 5.8))


# ----------------------------------------------------------------------------- 3. хаос → сетка → город

def v_grid(theme):
    pal = _pal(theme)
    rnd = random.Random(4)
    N = 16
    hs = [1.0 + 3.0 * abs(math.sin(i * 1.7 + 0.4)) for i in range(N)]
    scatter = [(rnd.uniform(-1, 7.5), rnd.uniform(-1, 7.5)) for _ in range(N)]

    def make(cam, k):
        objs = [_floor("!!fl", cam, -1.4, -1.4, 10.4, 10.4, pal["floor"])]
        specs = []
        for i in range(N):
            x, y = scatter[i] if k == 0 else ((i % 4) * 2.0, (i // 4) * 2.0)
            h = 0.6 if k < 2 else hs[i]
            hot = k == 2 and hs[i] > 3.4
            specs.append(dict(n=f"!!g{i}", x=x, y=y, z=0, w=1.1, d=1.1, h=h, col=pal["acc"] if hot else pal["grey"]))
            objs.append(_shadow(f"!!g{i}_sh", cam, x, y, 1.1, 1.1, h, pal["shadow"]))
        return objs + boxes(cam, specs)

    heads = [head("Шестнадцать команд", "без общей схемы"), head("Общая сетка", "одна платформа"),
             head("Нагрузка", "выше — больше запросов")]
    return _seq(FAM, "grid_city", "Хаос → сетка → город данных",
                "Разбросанные кубики съезжаются в сетку, затем вырастают башнями по значению. "
                "Роль: «наводим порядок», переход от инвентаризации к метрике; лучший кадр — третий.",
                heads, make, iso(0, 0, 1), [0, 1, 2], dur=900, tags=["iso", "grid", "data", "city"], score=4)


# ----------------------------------------------------------------------------- 4. вид сверху → изометрия (камера наклоняется)

ROOMS = [(0, 0, 3.0, 2.0, 1.2, "Склад"), (3.2, 0, 2.0, 2.0, 2.2, "Сборка"), (5.4, 0, 2.6, 2.0, 0.8, "Упаковка"),
         (0, 2.2, 4.0, 1.6, 0.6, "Приёмка"), (4.2, 2.2, 3.8, 1.6, 1.6, "Отгрузка")]


def v_tilt(theme):
    pal = _pal(theme)

    def scene(cam, k):
        objs = [_floor("!!fl", cam, -0.4, -0.4, 8.8, 4.6, pal["floor"])]
        specs = []
        for i, (x, y, w, d, h, _) in enumerate(ROOMS):
            specs.append(dict(n=f"!!r{i}", x=x, y=y, z=0, w=w, d=d, h=0.0 if k == 0 else h,
                              col=pal["acc"] if (k == 2 and i == 1) else pal["grey"]))
        objs += boxes(cam, specs, edge=pal["bg"])
        for i, (x, y, w, d, h, t) in enumerate(ROOMS):
            px, py = cam.p((x + w / 2, y + d / 2, 0.0 if k == 0 else h))
            base = pal["acc"] if (k == 2 and i == 1) else pal["grey"]
            objs.append(label(f"!!rt{i}", px - 0.8, py - 0.16, 1.6, t, sz=13, b=True,
                              col=_top_text_col(theme, cam, base), al="c"))
        return objs

    c_top = fitcam(Cam3(0, 0, 1, yaw=0, pitch=89.9), scene, [0], (6.0, 1.2, 6.6, 5.2))
    c_iso = fitcam(iso(0, 0, 1, yaw=35, pitch=38), scene, [1, 2], (5.4, 1.0, 7.4, 5.8))
    heads = [head("План цеха", "вид сверху"), head("Объём участков", "высота — загрузка"),
             head("Узкое место", "участок сборки")]
    return Variant(FAM, "plan_tilt", "План наклоняется в макет",
                   "Тот же план цеха, другая камера: вид сверху наклоняется в изометрию, стены участков поднимаются. "
                   "Роль: «смотрим глубже» — от карты процесса к нагрузке; вход в раздел про узкие места.",
                   [Slide(heads[0] + scene(c_top, 0), dur=900), Slide(heads[1] + scene(c_iso, 1), dur=900),
                    Slide(heads[2] + scene(c_iso, 2), dur=700)], tags=["iso", "camera", "plan", "3d"], score=5)


# ----------------------------------------------------------------------------- 5. куб распадается на кубики

def v_split(theme):
    pal = _pal(theme)

    def make(cam, k):
        specs = []
        n, s = 3, 1.0
        gap = [0.0, 0.3, 0.8][k]
        for ix in range(n):
            for iy in range(n):
                for iz in range(n):
                    hot = k == 2 and (ix, iy, iz) == (0, 0, 2)
                    base = pal["acc"] if hot else (pal["grey"] if (ix + iy + iz) % 2 == 0 else pal["grey2"])
                    specs.append(dict(n=f"!!c{ix}{iy}{iz}", x=ix * (s + gap), y=iy * (s + gap), z=iz * (s + gap),
                                      w=s, d=s, h=s, col=base))
        return boxes(cam, specs, zstep=3, edge=pal["bg"])

    heads = [head("Продукт целиком"), head("27 модулей", "каждый заменяем"), head("Начнём с одного", "угловой модуль")]
    return _seq(FAM, "cube_split", "Куб распадается на модули",
                "Монолитный куб раскалывается на 3×3×3 модуля, модули расходятся в пространстве, один горит. "
                "Роль: «из чего состоит», модульность, декомпозиция задачи — части отделяются в 3D.",
                heads, make, iso(0, 0, 1), [0, 1, 2], tags=["iso", "fragment", "explode", "3d"], score=4)


# ----------------------------------------------------------------------------- 6. лестница роста + шарик

def v_stairs(theme):
    pal = _pal(theme)
    steps = ["Пилот", "Отдел", "Филиал", "Страна", "Рынок"]

    def make(cam, k):
        objs, specs = [], []
        cur = [1, 3, 4][k]
        for i in range(5):
            h = 0.6 + i * 0.75
            specs.append(dict(n=f"!!st{i}", x=i * 1.6, y=0, z=0, w=1.6, d=2.2, h=h,
                              col=pal["acc3"] if i <= cur else pal["grey"]))
        objs += boxes(cam, specs)
        hx, hy = cam.p((cur * 1.6 + 0.8, 1.1, 0.6 + cur * 0.75))
        r = 0.32 * cam.s / 0.7 * 0.7
        objs.append(O("!!ball", "oval", hx - r, hy - 2 * r - 0.05, 2 * r, 2 * r, fill="accent", z=200))
        objs.append(O("!!ballsh", "oval", hx - r * 1.1, hy - r * 0.35, r * 2.2, r * 0.7, fill=pal["shadow"], fa=0.8, z=199))
        for i, t in enumerate(steps):
            px, py = cam.p((i * 1.6 + 1.6, 0.0, 0))
            objs.append(label(f"!!sl{i}", px - 0.2, py - 0.02, 1.4, t, sz=13, col="ink" if i == cur else "ink2",
                              b=i == cur))
        return objs

    heads = [head("Шаг 2 из 5", "пилот пройден"), head("Шаг 4 из 5", "выход в страну"), head("Весь рынок", "финиш")]
    return _seq(FAM, "stairs", "Лестница этапов и шарик",
                "Изометрическая лестница этапов; шарик-маркер переезжает на ступень выше, пройденные ступени окрашены. "
                "Роль: дорожная карта, прогресс по этапам; сквозной прогресс между разделами.",
                heads, make, iso(0, 0, 1, yaw=30), [0, 1, 2], tags=["iso", "progress", "navigation"], score=3)


# ----------------------------------------------------------------------------- 7. список → стопка (камера + толщина)

def v_list_stack(theme):
    pal = _pal(theme)
    items = ["Сбор данных", "Очистка", "Признаки", "Обучение", "Проверка"]
    front = Cam3(5.0, 1.7, 1.0, yaw=0, pitch=0.01)

    def make(cam, k):
        objs, specs = [], []
        for i, t in enumerate(items):
            hot = k == 2 and i == 3
            if k == 0:
                c = front
                x, y, zb, w, d, h = 0, 0, -i * 1.05, 4.6, 0.01, 0.82
            else:
                c = cam
                x, y, zb, w, d, h = 0, 0, (4 - i) * (0.42 if k == 1 else 0.85), 3.4, 3.4, 0.3
            specs.append(dict(n=f"!!pl{i}", x=x, y=y, z=zb, w=w, d=d, h=h, cam=c, zo=10 + (4 - i) * 4,
                              col=pal["acc"] if hot else pal["grey"]))
            if k == 0:
                px, py = c.p((0.25, 0, zb + h / 2))
                objs.append(label(f"!!pt{i}", px, py - 0.22, 4.0, f"{i + 1}. {t}", sz=19, b=True,
                                  col=ink_on(theme, face_col(c, [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)], pal["grey"]))))
            else:
                px, py = c.p((3.4, 0.0, zb + 0.15))
                objs.append(label(f"!!pt{i}", px + 0.3, py - 0.2, 3.2, f"{i + 1}. {t}", sz=15,
                                  col="accent" if hot else "ink2", b=hot))
        return objs + boxes(cam, specs, edge=pal["bg"])

    cam = fitcam(iso(0, 0, 1, yaw=40, pitch=32), lambda c, k: [o for o in make(c, k)], [1, 2], (5.0, 1.0, 4.4, 5.8))
    heads = [head("Конвейер модели", "пять шагов"), head("Слои конвейера"), head("Слой обучения", "дольше всего")]
    heads[0] = [o.copy(x=o.x) for o in heads[0]]
    return Variant(FAM, "list_to_stack", "Список ложится в стопку",
                   "Плоский список шагов (вид спереди) поворачивается камерой и ложится изометрической стопкой; затем "
                   "стопка раздвигается и выделяет слой. Роль: «список → архитектура» теми же объектами.",
                   [Slide(heads[k] + make(cam, k), dur=900) for k in range(3)],
                   tags=["iso", "camera", "list", "layers"], score=4)


# ----------------------------------------------------------------------------- 8. конвейер: бруски едут по станциям

def v_conveyor(theme):
    pal = _pal(theme)
    st_names = ["Заявка", "Проверка", "Сборка", "Отправка"]

    def make(cam, k):
        objs = [_floor("!!belt", cam, -0.6, 0.0, 12.6, 1.6, pal["floor"])]
        specs = []
        for s in range(4):
            specs.append(dict(n=f"!!stn{s}", x=s * 3.6 + 0.2, y=1.9, z=0, w=1.2, d=0.8, h=2.2,
                              col=pal["acc3"] if s == k + 1 else pal["grey2"]))
        for j in range(4):
            pos = j + k
            x = (pos - 1) * 3.6 + 0.45 if pos <= 4 else 15.0
            x = -3.4 if pos == 0 else x
            specs.append(dict(n=f"!!pk{j}", x=min(x, 12.0), y=0.35, z=0, w=0.8, d=0.8, h=0.7,
                              col=pal["acc"] if j == 0 else pal["grey"], fa=1.0 if -1 < x < 12 else 0.0))
        objs += boxes(cam, specs)
        for s, t in enumerate(st_names):
            px, py = cam.p((s * 3.6 + 0.8, 2.7, 2.2))
            objs.append(label(f"!!sn{s}", px - 0.8, py - 0.42, 1.6, t, sz=13, col="ink" if s == k + 1 else "ink2",
                              al="c", b=s == k + 1))
        return objs

    heads = [head("Заказ принят"), head("Шаг вперёд"), head("К отправке")]
    return _seq(FAM, "conveyor", "Посылки едут по станциям",
                "Изометрическая лента со станциями; клик продвигает поток посылок на одну станцию, активная станция "
                "подсвечена. Роль: процесс, очередь, «где сейчас заказ».",
                heads, make, iso(0, 0, 1, yaw=50), [0, 1, 2], tags=["iso", "process", "flow"], score=3,
                area=(4.6, 1.4, 8.3, 5.4))


# ----------------------------------------------------------------------------- 9. пирамида уровней

def v_pyramid(theme):
    pal = _pal(theme)
    lv = ["Миссия", "Цели", "Проекты", "Задачи"]

    def make(cam, k):
        objs, specs = [], []
        for i in range(4):
            j = 3 - i
            s = 1.2 + j * 1.0
            zb = j * (0.45 + [0, 0.5, 0.5][k])
            off = (4.2 - s) / 2
            hot = k == 2 and i == 0
            specs.append(dict(n=f"!!py{i}", x=off, y=off, z=zb, w=s, d=s, h=0.45, zo=10 + j * 4,
                              col=pal["acc"] if hot else mix(pal["grey"], pal["bg"], 0.1 * i)))
            if k >= 1:
                px, py = cam.p((off + s, off, zb + 0.22))
                objs.append(label(f"!!pt{i}", px + 0.35, py - 0.2, 2.4, lv[i], sz=15, b=hot,
                                  col="accent" if hot else "ink2"))
        return objs + boxes(cam, specs, edge=pal["bg"])

    heads = [head("Ступенчатая пирамида"), head("Четыре уровня"), head("Всё ради миссии")]
    return _seq(FAM, "pyramid", "Пирамида уровней расслаивается",
                "Ступенчатая пирамида из плит раздвигается по высоте, подписи встают у каждого уровня; вершина горит. "
                "Роль: иерархия целей, уровни зрелости — объёмная замена плоского треугольника.",
                heads, make, iso(0, 0, 1), [0, 1, 2], tags=["iso", "hierarchy", "layers"], score=3,
                area=(5.0, 1.2, 5.0, 5.5))


# ----------------------------------------------------------------------------- 10. шкаф с ящиками

def v_drawers(theme):
    pal = _pal(theme)
    names = ["Договоры", "Счета", "Акты", "Отчёты"]

    def make(cam, k):
        objs = []
        specs = [dict(n="!!cab", x=0, y=0, z=0, w=3.2, d=3.0, h=4.4, col=pal["grey2"], zo=10)]
        for i in range(4):
            out = 2.2 if ((k == 1 and i == 1) or (k == 2 and i == 3)) else 0.0
            zb = 3.3 - i * 1.08
            specs.append(dict(n=f"!!dr{i}", x=0.15, y=-0.02 - out, z=zb, w=2.9, d=0.4 + out, h=0.9, zo=20 + i * 4,
                              col=pal["acc"] if out else pal["grey"]))
            px, py = cam.p((3.05, -0.02 - out, zb + 0.45))
            objs.append(label(f"!!dl{i}", px + 0.25, py - 0.2, 2.0, names[i], sz=14, col="accent" if out else "ink2",
                              b=bool(out)))
        return objs + boxes(cam, specs, edge=pal["bg"])

    heads = [head("Архив документов"), head("Ищем счёт"), head("Теперь — отчёт")]
    return _seq(FAM, "drawers", "Шкаф: выдвигается ящик",
                "Изометрический шкаф; нужный ящик выезжает вперёд и загорается, прошлый задвигается. "
                "Роль: навигация по разделам-хранилищам (архив, база знаний), «где лежит».",
                heads, make, iso(0, 0, 1, yaw=35, pitch=30), [0, 1, 2], tags=["iso", "navigation", "storage"], score=3,
                area=(5.2, 1.1, 4.6, 5.7))


# ----------------------------------------------------------------------------- 11. матрица: клетки поднимаются рельефом

def v_matrix(theme):
    pal = _pal(theme)
    N = 7
    vals = [[(math.sin(i * 0.9 + j * 0.5) + math.cos(j * 1.3 - i * 0.4)) for j in range(N)] for i in range(N)]

    def make(cam, k):
        objs = [_floor("!!fl", cam, -0.5, -0.5, N * 1.3 + 0.3, N * 1.3 + 0.3, pal["floor"])]
        specs = []
        for i in range(N):
            for j in range(N):
                v = vals[i][j]
                hot = k == 2 and v > 1.2
                h = 0.15 if k == 0 or (k == 2 and not hot) else max(0.15, (v + 2) * 0.75)
                specs.append(dict(n=f"!!m{i}_{j}", x=i * 1.3, y=j * 1.3, z=0, w=1.1, d=1.1, h=h,
                                  col=pal["acc"] if hot else (pal["grey"] if k else pal["grey2"])))
        return objs + boxes(cam, specs, edge=pal["bg"], zstep=3)

    heads = [head("49 магазинов"), head("Выручка", "высота клетки"), head("Лучшие клетки", "остальные опущены")]
    return _seq(FAM, "matrix_lift", "Матрица поднимается рельефом",
                "Плоская сетка клеток становится рельефом значений, затем поднятыми остаются только лучшие. "
                "Роль: тепловая карта с объёмом, отбор «лучших из многих»; читается и без чисел.",
                heads, make, iso(0, 0, 1), [0, 1, 2], dur=900, tags=["iso", "heatmap", "data", "filter"], score=4)


# ----------------------------------------------------------------------------- 12. башни было/стало

def v_compare(theme):
    pal = _pal(theme)
    parts = [1.6, 1.2, 1.4]

    def make(cam, k):
        objs = [_floor("!!fl", cam, -1, -1, 9, 4, pal["floor"])]
        specs = [dict(n="!!ta0", x=0, y=0, z=0, w=2, d=2, h=parts[0], col=pal["grey2"], zo=10),
                 dict(n="!!ta1", x=0, y=0, z=parts[0], w=2, d=2, h=parts[1], col=pal["grey"], zo=14)]
        if k < 2:
            specs.append(dict(n="!!ta2", x=0, y=0, z=parts[0] + parts[1], w=2, d=2, h=parts[2], col=pal["acc3"], zo=18))
        else:
            specs.append(dict(n="!!ta2", x=2.6, y=-0.6, z=0, w=2, d=2, h=0.0, col=pal["acc3"], zo=8, fa=0.6))
        specs.append(dict(n="!!tb", x=5.0, y=0, z=0, w=2, d=2, h=0.0 if k == 0 else 1.6, col=pal["acc"], zo=22))
        objs += boxes(cam, specs, edge=pal["bg"])
        px, py = cam.p((1, -1, 0))
        objs.append(label("!!la", px - 1.2, py + 0.1, 2.4, "Было: 42 дня", sz=15, col="ink2", al="c"))
        if k >= 1:
            px, py = cam.p((6, -1, 0))
            objs.append(label("!!lb", px - 1.2, py + 0.1, 2.4, "Стало: 16 дней", sz=15, b=True, col="accent", al="c"))
        if k == 2:
            px, py = cam.p((3.6, -0.6, 0))
            objs.append(label("lc", px + 0.2, py + 0.25, 2.6, "лишние согласования", sz=13, col="ink2"))
        return objs

    heads = [head("Срок запуска"), head("После перестройки"), head("Что убрали")]
    return _seq(FAM, "towers_compare", "Башни «было/стало»",
                "Башня старого срока сложена из частей; рядом вырастает новая, затем лишняя часть съезжает и ложится "
                "плиткой на пол. Роль: было/стало с объяснением разницы — части башни = причины.",
                heads, make, iso(0, 0, 1, yaw=40), [0, 1, 2], tags=["iso", "compare", "data"], score=4)


# ----------------------------------------------------------------------------- SEQ 1. платформа: живая стопка через всю презентацию

def v_seq_platform(theme):
    """Одна стопка слоёв проходит 8 ролей: монолит → слои → слой-панель к зрителю → обратно → камера к слою данных →
    слой делится на базы → стопка ложится плоскими полосами (бюджет) → снова объём, финал."""
    pal = _pal(theme)
    th = 0.36
    budget = [0.9, 0.6, 1.0, 0.75, 0.45]  # доли бюджета по слоям (длина полос)
    bullets = ["12 сервисов", "общая шина событий", "релиз раз в день"]

    def state(k, cam, front):
        objs, specs = [], []
        n = len(LAYERS)
        for i in range(n):
            j = n - 1 - i
            gap = {0: 0.0, 1: 0.5}.get(k, 0.5)
            zb = j * (th + gap) + (0.7 if (k == 4 and j >= 2) else 0.0)
            col = pal["grey"] if i % 2 == 0 else pal["grey3"]
            sp = dict(n=f"!!L{i}", x=0, y=0, z=zb, w=3.2, d=3.2, h=th, col=col, zo=10 + j * 5)
            if k == 2 and i == 2:  # слой выезжает и разворачивается к зрителю панелью
                sp.update(cam=front, x=0, y=0, z=0, w=5.4, d=0.05, h=3.2, col=pal["grey3"], zo=200)
            if k == 3 and i == 2:
                sp.update(col=pal["acc"])
            if k in (3, 4) and i == 3:
                sp.update(col=pal["acc3"] if k == 4 else col)
            if k == 4 and i == 3:  # слой данных раскалывается на 4 базы и расходится в своей плоскости
                sp = None
                for q in range(4):
                    qx, qy = (q % 2) * 2.0 - 0.4, (q // 2) * 2.0 - 0.4
                    specs.append(dict(n=f"!!D{q}", x=qx, y=qy, z=zb, w=1.6, d=1.6, h=th, col=pal["acc3"],
                                      zo=10 + j * 5 - 1 + (q % 2) + (1 - q // 2) * 2))
            elif i == 3:
                for q in range(4):
                    qx, qy = (q % 2) * 1.6, (q // 2) * 1.6
                    if k in (5, 6):
                        specs.append(dict(n=f"!!D{q}", x=qx, y=qy, z=zb, w=1.6, d=1.6, h=th, col=col, zo=5, fa=0.0))
                    else:
                        specs.append(dict(n=f"!!D{q}", x=qx, y=qy, z=zb, w=1.6, d=1.6, h=th, col=col, zo=10 + j * 5 - 1,
                                          fa=0.0))
            if k == 5 and sp:  # плоские полосы бюджета: вид спереди
                sp.update(cam=front, x=0, y=0, z=-i * 0.95, w=budget[i] * 7.0, d=0.02, h=0.7,
                          col=pal["acc"] if i == 2 else pal["grey"], zo=100 + i)
            if k == 6 and sp:  # полосы встают изометрическими столбиками по бюджету
                sp.update(x=i * 1.5, y=0, z=0, w=1.0, d=1.0, h=budget[i] * 4.2, zo=10 + (n - i),
                          col=pal["acc"] if i == 2 else pal["grey"])
            if k == 7 and sp:
                sp.update(col=pal["acc"] if i == 2 else (pal["acc3"] if i == 3 else col))
            if sp:
                specs.append(sp)
        objs += boxes(cam, specs, edge=pal["bg"])
        # подписи
        if k in (1, 3, 4, 7):
            for i in range(n):
                j = n - 1 - i
                zb = j * (th + 0.5) + (0.7 if (k == 4 and j >= 2) else 0.0)
                if k == 4 and i == 3:
                    continue
                px, py = cam.p((3.2, 0.0, zb + th / 2))
                hot = (k == 3 and i == 2) or (k == 7 and i in (2, 3))
                objs.append(label(f"!!lt{i}", px + 0.35, py - 0.18, 2.6, LAYERS[i], sz=15, b=hot,
                                  col="accent" if (hot and i == 2) else ("ink" if hot else "ink2")))
        if k == 2:
            x0, y0 = front.p((0, 0, 3.2))
            objs.append(label("pn_t", x0 + 0.35, y0 + 0.3, 4.8, "Слой сервисов", sz=24, b=True,
                              col=ink_on(theme, face_col(front, [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)], pal["grey3"])),
                              z=260))
            for b, t in enumerate(bullets):
                objs.append(label(f"pn_b{b}", x0 + 0.35, y0 + 1.05 + b * 0.5, 4.8, "— " + t, sz=18, z=260,
                                  col=ink_on(theme, face_col(front, [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)], pal["grey3"]))))
        if k == 4:
            zb = 1 * (th + 0.5)
            px, py = cam.p((3.6, -0.4, zb + th / 2))
            objs.append(label("db", px + 0.3, py - 0.3, 2.4, ["Заказы · Клиенты", "Склад · Журнал"], sz=15, col="ink"))
        if k == 5:
            for i in range(n):
                px, py = front.p((budget[i] * 7.0, 0, -i * 0.95 + 0.35))
                objs.append(label(f"bv{i}", px + 0.2, py - 0.2, 1.4, f"{round(budget[i] * 40)}%", sz=15, b=True,
                                  col="accent" if i == 2 else "ink2"))
                lx, ly = front.p((0, 0, -i * 0.95 + 0.35))
                objs.append(label(f"bl{i}", lx - 2.9, ly - 0.2, 2.7, LAYERS[i], sz=15, al="r", col="ink2"))
        if k == 6:
            for i in range(n):
                px, py = cam.p((i * 1.5 + 0.5, 0.5, budget[i] * 4.2))
                objs.append(label(f"cl{i}", px - 0.6, py - 0.48, 1.2, f"{round(budget[i] * 40)}%", sz=15, b=True,
                                  al="c", col="accent" if i == 2 else "ink"))
        return objs

    base = iso(0, 0, 1, yaw=42, pitch=33)
    probe = lambda c, k: state(k, c, Cam3(9.0, 4.0, 1, yaw=0, pitch=0.01))  # noqa: E731
    cam = fitcam(base, probe, [1], (5.6, 1.0, 5.0, 5.7))
    cam_far = fitcam(base, probe, [0], (6.6, 1.6, 4.0, 4.6))
    cam_data = fitcam(base, probe, [4], (5.0, 1.0, 5.6, 5.8))
    cam_bars = fitcam(recam(base, yaw=25, pitch=28), probe, [6], (6.0, 1.6, 6.0, 4.8))
    front = Cam3(3.6, 5.3, 1.0, yaw=0, pitch=0.01)
    front_bars = Cam3(4.2, 2.4, 1.0, yaw=0, pitch=0.01)
    plan = [(0, cam_far, front, head("Платформа", "одним блоком")),
            (1, cam, front, head("Пять слоёв", "из чего она состоит")),
            (2, cam, Cam3(0.75, 5.7, 1.0, yaw=0, pitch=0.01), head("Крупно", "слой выходит к нам")),
            (3, cam, front, head("На место", "сервисы в стопке")),
            (4, cam_data, front, head("Слой данных", "четыре базы")),
            (5, cam, front_bars, head("Бюджет по слоям", "доля в годовом плане")),
            (6, cam_bars, front, head("Тот же бюджет", "объёмом")),
            (7, cam, front, head("Платформа 2.0", "два слоя меняем"))]
    slides = [Slide(h + state(k, c, f), dur=900) for k, c, f, h in plan]
    return Variant(FAM, "seq_platform", "Платформа: стопка через всю презентацию",
                   "Одна стопка живёт 8 слайдов: монолит → слои с подписями → слой сервисов выходит к зрителю панелью "
                   "с текстом → возвращается → камера приближает слой данных, он раскалывается на 4 базы → стопка "
                   "ложится плоскими полосами бюджета → полосы встают объёмными столбиками → финал. Роль: хребет "
                   "технической презентации об архитектуре.", slides, tags=["iso", "seq", "camera", "layers", "data"], score=4)


# ----------------------------------------------------------------------------- SEQ 2. город данных

PORT = 0
DISTRICTS = ["Порт", "Центр", "Север", "Юг"]  # порт — ближний к зрителю район


def v_seq_city(theme):
    """План районов → объём → камера в район → дом расслаивается на этажи → этажи встают в ряд полосами →
    дом собирается, камера отъезжает → город снова план, но с выделенным районом."""
    pal = _pal(theme)
    rnd = random.Random(11)
    # 4 района по 3×3 дома
    houses = []
    for d in range(4):
        ox, oy = (d % 2) * 4.4, (d // 2) * 4.4
        for q in range(9):
            hx, hy = ox + (q % 3) * 1.3, oy + (q // 3) * 1.3
            houses.append((d, hx, hy, 0.6 + rnd.random() * (1.4 if d == PORT else 2.0)))
    hero = 0  # ближний дом порта — самый высокий
    houses[0] = (PORT, houses[0][1], houses[0][2], 3.4)
    floors = 5
    loads = [0.9, 0.55, 0.75, 0.35, 0.6]
    fnames = ["Причал", "Склады", "Таможня", "Офис", "Терминал"]

    def state(k, cam, front):
        objs = []
        for d in range(4):
            ox, oy = (d % 2) * 4.4, (d // 2) * 4.4
            hot = d == PORT and k in (2, 3, 6)
            objs.append(_floor(f"!!dst{d}", cam, ox - 0.25, oy - 0.25, 3.9, 3.9,
                               mix(pal["floor"], pal["acc"], 0.35) if hot else pal["floor"]))
        specs = []
        for i, (d, hx, hy, h) in enumerate(houses):
            hh = 0.0 if k in (0, 6) else h
            col = pal["grey"]
            if d == PORT and k in (2, 3, 4):
                col = pal["acc3"]
            if i == hero and k in (3, 4, 5):
                continue
            specs.append(dict(n=f"!!h{i}", x=hx, y=hy, z=0, w=1.0, d=1.0, h=hh, col=col,
                              fa=(0.04 if k == 5 else 0.10) if (k in (4, 5) and d != PORT) else (0.04 if k == 5 else 1.0)))
        d, hx, hy, h = houses[hero]
        for f in range(floors):
            fh = h / floors
            if k in (3, 4):
                gap = 0.35 if k == 4 else 0.0
                specs.append(dict(n=f"!!fl{f}", x=hx, y=hy, z=f * (fh + gap), w=1.0, d=1.0, h=fh,
                                  col=pal["acc"] if (k == 4 and f == 0) else pal["acc3"]))
            elif k == 5:
                specs.append(dict(n=f"!!fl{f}", cam=front, x=0, y=0, z=-f * 0.9, w=loads[f] * 5.0, d=0.02, h=0.62,
                                  col=pal["acc"] if f == 0 else pal["grey"], zo=300 + f))
            else:
                specs.append(dict(n=f"!!fl{f}", x=hx, y=hy, z=f * fh if k not in (0, 6) else 0, w=1.0, d=1.0,
                                  h=fh if k not in (0, 6) else 0.0, col=pal["acc"] if k == 7 else pal["grey"]))
        objs += boxes(cam, specs, zstep=4)
        if k in (0, 6):
            for d in range(4):
                ox, oy = (d % 2) * 4.4, (d // 2) * 4.4
                px, py = cam.p((ox + 1.7, oy - 0.25 if d < 2 else oy + 3.65, 0))
                objs.append(label(f"!!dn{d}", px - 0.9, py + 0.06 if d < 2 else py - 0.42, 1.8, DISTRICTS[d], sz=15,
                                  b=d == PORT and k == 6, al="c", col="accent" if (d == PORT and k == 6) else "ink2"))
        if k == 4:
            for f in range(floors):
                px, py = cam.p((hx + 1.0, hy, f * (h / floors + 0.35) + h / floors / 2))
                objs.append(label(f"!!fn{f}", px + 0.25, py - 0.18, 2.0, fnames[f], sz=14, b=f == 0,
                                  col="accent" if f == 0 else "ink2"))
        if k == 5:
            for f in range(floors):
                px, py = front.p((0, 0, -f * 0.9 + 0.31))
                objs.append(label(f"!!fn{f}", px - 2.3, py - 0.18, 2.1, fnames[f], sz=14, al="r", b=f == 0,
                                  col="accent" if f == 0 else "ink2"))
                ex, ey = front.p((loads[f] * 5.0, 0, -f * 0.9 + 0.31))
                objs.append(label(f"ld{f}", ex + 0.15, ey - 0.18, 1.2, f"{round(loads[f] * 100)}%", sz=14, b=True,
                                  col="ink"))
        return objs

    base = iso(0, 0, 1, yaw=45, pitch=35.264)
    front = Cam3(7.4, 2.6, 1.0, yaw=0, pitch=0.01)
    probe = lambda c, k: state(k, c, front)  # noqa: E731
    top = fitcam(Cam3(0, 0, 1, yaw=0, pitch=89.9), probe, [0], (6.6, 1.5, 5.1, 4.9))
    cam = fitcam(base, probe, [1], (5.2, 1.0, 7.6, 5.8))
    d, hx, hy, h = houses[hero]
    zx, zy = cam.p((hx + 0.5, hy + 0.5, 1.2))
    zk = 1.6
    cam_zoom = recam(cam, s=cam.s * zk, cx=9.9 - (zx - cam.cx) * zk, cy=4.9 - (zy - cam.cy) * zk)
    cam_zoom2 = recam(cam_zoom, cx=cam_zoom.cx - 0.6)
    plan = [(0, top, head("Город", "четыре района")), (1, cam, head("Город в объёме", "высота — грузопоток")),
            (2, cam, head("Самый загруженный", "район порта")),
            (3, cam_zoom, head("Главный узел", "терминал порта")),
            (4, cam_zoom2, head("Пять этажей", "пять служб")),
            (5, cam_zoom2, head("Загрузка служб", "доля мощности")),
            (6, top, head("Снова план", "порт — в фокусе")),
            (7, cam, head("Город после", "узел усилен"))]
    slides = [Slide(hh + state(k, c, front), dur=900) for k, c, hh in plan]
    return Variant(FAM, "seq_city", "Город данных: от плана к этажу",
                   "Один город живёт 8 слайдов: план районов → дома встают объёмом → район подсвечен → камера ныряет к "
                   "главному дому → дом расслаивается на этажи-службы → этажи разворачиваются плоскими полосами "
                   "загрузки → снова план с районом в фокусе → объём-финал. Роль: сквозная карта презентации про операции.",
                   slides, tags=["iso", "seq", "camera", "city", "data", "explode"], score=3)


def variants(theme) -> list[Variant]:
    from lab._c_util import ensure_contrast
    return ensure_contrast(theme, [f(theme) for f in (v_bars, v_stack, v_grid, v_tilt, v_split, v_stairs, v_list_stack, v_conveyor,
                               v_pyramid, v_drawers, v_matrix, v_compare, v_seq_platform, v_seq_city)])
