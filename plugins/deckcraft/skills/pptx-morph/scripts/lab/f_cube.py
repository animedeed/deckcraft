"""Семейство «Куб и призма»: поворот тел перетеканием спроецированных граней.

Приём «барабан со схлопыванием»: боковые грани призмы — четырёхугольники с общими вершинами; у скрытой грани все
вершины прилипают к ребру ближайшей видимой вершины (нулевая площадь). При повороте на одну грань вершины едут
линейно, соседние грани делят вершины — сетка не рвётся, грани не наползают друг на друга, а силуэт стоит.
Текст на гранях — отдельные объекты, которые гаснут/проявляются (не переливаются).
Развёртка куба: вершины каждой грани поворачиваются вокруг шарнира; порядок отрисовки один и тот же во всех
состояниях (дно, задние, передние, крышка), поэтому от z-порядка Morph ничего не зависит.
"""

from __future__ import annotations

import math

from morphkit import O, Slide
from morphkit.theme import mix

from lab import Variant
from lab._c_util import Cam3, boxes, face, face_col, fitcam, head, ink_on, iso, label, poly, prism_side, ring_pts

FAM = "cube"


def _pal(theme):
    ink2, bg = theme.c("ink2"), theme.c("bg")
    return {"grey": mix(ink2, bg, 0.45), "grey2": mix(ink2, bg, 0.62), "grey3": mix(ink2, bg, 0.30),
            "acc": theme.c("accent"), "acc3": theme.c("accent3"), "acc2": theme.c("accent2"), "bg": bg,
            "floor": mix(theme.c("surface2"), ink2, 0.10), "shadow": mix(theme.c("surface2"), "000000", 0.45)}


def _rot(p, axis_p, axis_d, ang):
    """Поворот точки p вокруг оси (точка axis_p, направление axis_d — единичное) на ang градусов (Родриг)."""
    a = math.radians(ang)
    px, py, pz = (p[i] - axis_p[i] for i in range(3))
    kx, ky, kz = axis_d
    c, s = math.cos(a), math.sin(a)
    dot = kx * px + ky * py + kz * pz
    cx, cy, cz = ky * pz - kz * py, kz * px - kx * pz, kx * py - ky * px
    r = (px * c + cx * s + kx * dot * (1 - c), py * c + cy * s + ky * dot * (1 - c), pz * c + cz * s + kz * dot * (1 - c))
    return tuple(r[i] + axis_p[i] for i in range(3))


# ----------------------------------------------------------------------------- барабан: горизонтальная призма

def drum(prefix, cam, n, phase, L, r, cols, z=10, edge=None, hot=None):
    """Призма с осью x длиной L, радиусом r; phase — поворот (градусы). Грань i: от вершины i к i+1.
    -> (объекты, {i: центр грани на слайде, ширина, высота})."""
    lo = ring_pts(-L / 2, 0, 0, r, n, phase, axis="x")
    hi = ring_pts(L / 2, 0, 0, r, n, phase, axis="x")
    # для призмы вдоль x: «нижнее» кольцо — левый торец; обход граней: lo_i, lo_i+1, hi_i+1, hi_i
    # ориентация: нормаль наружу при обходе lo_i -> hi_i -> hi_i+1 -> lo_i+1; prism_side ждёт [lo_i, lo_i+1, hi_i+1, hi_i]
    # поэтому меняем роли колец местами
    objs, shown = prism_side(prefix, cam, hi, lo, cols, z=z, edge=edge)
    info = {}
    for i in shown:
        q = [hi[i], hi[(i + 1) % n], lo[(i + 1) % n], lo[i]]
        pts = [cam.p(p) for p in q]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        info[i] = ((sum(xs) / 4, sum(ys) / 4), max(xs) - min(xs), max(ys) - min(ys), cam.facing(q))
    return objs, info


def _front_face(info):
    return max(info, key=lambda i: info[i][3] * info[i][2])


def v_drum4(theme):
    pal = _pal(theme)
    topics = ["Рынок", "Продукт", "Команда", "Деньги"]
    cam = Cam3(8.3, 4.1, 1.0, yaw=0, pitch=16, dist=14)
    n = 4

    def make(k):
        cols = [pal["acc"] if i == (k % n) else pal["grey"] for i in range(n)]
        cols = [pal["grey"]] * n
        objs, info = drum("!!dr", cam, n, 45 - 90 * k + 0, 6.2, 1.9, cols, edge=pal["bg"])
        f = _front_face(info)
        (cx, cy), w, h, _ = info[f]
        fill = face_col(cam, [(0, -1, -1), (0, -1, 1), (1, -1, 1), (1, -1, -1)], pal["grey"])
        objs.append(label(f"tp{k}", cx - w / 2 + 0.3, cy - 0.45, w - 0.6, topics[(f - 3) % n], sz=36, b=True,
                          al="c", col=ink_on(theme, [o for o in objs if o.name == f"!!dr{f}"][0].fill), z=80))
        objs.append(O("!!drsh", "oval", 8.3 - 3.4, 6.35, 6.8, 0.42, fill=pal["shadow"], fa=0.8, z=2))
        return objs

    slides = [Slide(head(f"Тема {k + 1} из 4", "барабан поворачивается") + make(k), dur=800) for k in range(3)]
    return Variant(FAM, "drum4", "Барабан тем (куб на оси)",
                   "Горизонтальный куб-барабан с перспективой: клик поворачивает его на грань, новая тема приходит снизу; "
                   "надпись — отдельный объект, гаснет и проявляется. Роль: навигация по 3–4 разделам, оглавление.",
                   slides, tags=["cube", "rotate", "navigation", "3d"], score=4)


def v_drum6(theme):
    pal = _pal(theme)
    topics = ["Идея", "Прототип", "Пилот", "Запуск", "Рост", "Масштаб"]
    cam = Cam3(8.4, 4.0, 1.0, yaw=0, pitch=10, dist=16)
    n = 6

    def make(k):
        cols = [pal["acc"] if i % n == (k + 5) % n else pal["grey"] for i in range(n)]
        objs, info = drum("!!hx", cam, n, 30 - 60 * k, 7.0, 2.1, cols, edge=pal["bg"])
        f = _front_face(info)
        (cx, cy), w, h, _ = info[f]
        objs.append(label(f"tp{k}", cx - w / 2 + 0.3, cy - 0.4, w - 0.6, topics[(f - 5) % n], sz=32, b=True, al="c",
                          col=ink_on(theme, [o for o in objs if o.name == f"!!hx{f}"][0].fill), z=80))
        for i in info:
            if i == f:
                continue
            (cx2, cy2), w2, h2, _ = info[i]
            if h2 > 0.55:
                objs.append(label(f"ts{k}_{i}", cx2 - w2 / 2 + 0.3, cy2 - 0.2, w2 - 0.6, topics[(i - 5) % n], sz=16,
                                  al="c", col=ink_on(theme, [o for o in objs if o.name == f"!!hx{i}"][0].fill), z=80))
        return objs

    slides = [Slide(head(f"Этап {k + 1}", "шестигранный барабан") + make(k), dur=800) for k in range(3)]
    return Variant(FAM, "drum6", "Шестигранный барабан этапов",
                   "Шестигранная призма с перспективой: на передней грани текущий этап, на соседних — прошлый и "
                   "следующий мелко; поворот на 60° за клик. Роль: дорожная карта 5–8 этапов, сквозной навигатор.",
                   slides, tags=["prism", "rotate", "navigation", "roadmap"], score=4)


# ----------------------------------------------------------------------------- вертикальная восьмигранная карусель

def v_octo(theme):
    pal = _pal(theme)
    topics = ["Продажи", "Склад", "Логистика", "Сервис", "Финансы", "Кадры", "ИТ", "Право"]
    cam = Cam3(8.6, 4.1, 1.0, yaw=0, pitch=14, dist=18)
    n = 8

    def make(k):
        ph = 22.5 + 45 * k
        lo = ring_pts(0, 0, -1.7, 2.4, n, ph)
        hi = ring_pts(0, 0, 1.7, 2.4, n, ph)
        cols = [pal["acc"] if i == (7 - k) % n else pal["grey"] for i in range(n)]
        objs, shown = prism_side("!!oc", cam, lo, hi, cols, edge=pal["bg"])
        cap = [cam.p(p) for p in hi]
        objs.append(poly("!!cap", cap, fill=face_col(cam, [(0, 0, 1), (1, 0, 1), (1, 1, 1)], pal["grey2"]),
                         ln=pal["bg"], lw=0.75, z=30))
        f = (7 - k) % n
        q = [lo[f], lo[(f + 1) % n], hi[(f + 1) % n], hi[f]]
        pts = [cam.p(p) for p in q]
        cx, cy = sum(p[0] for p in pts) / 4, sum(p[1] for p in pts) / 4
        objs.append(label(f"tp{k}", cx - 1.5, cy - 0.3, 3.0, topics[(7 - f) % n], sz=26, b=True, al="c",
                          col=ink_on(theme, pal["acc"]), z=80))
        objs.append(O("!!sh", "oval", 8.6 - 3.0, 6.25, 6.0, 0.5, fill=pal["shadow"], fa=0.8, z=2))
        return objs

    slides = [Slide(head(["Восемь служб", "Вторая служба", "Третья служба"][k], "карусель отделов") + make(k), dur=850)
              for k in range(3)]
    return Variant(FAM, "octo_carousel", "Восьмигранная карусель",
                   "Вертикальная восьмигранная призма с крышкой поворачивается на 45°: активная грань выходит к зрителю. "
                   "Роль: оргструктура, обзор 6–8 направлений; поворот виден, силуэт стоит на месте.",
                   slides, tags=["prism", "rotate", "carousel", "3d"], score=4)


# ----------------------------------------------------------------------------- развёртка → куб

NET = ["Цель", "Аудитория", "Канал", "Бюджет", "Сроки", "Риски"]


def _outward(pts3, c=(0.95, 0.95, 0.95)):
    """Обход грани так, чтобы нормаль смотрела от центра куба (для освещения сложенной развёртки)."""
    from lab._c_util import newell
    n = newell(pts3)
    fc = [sum(p[i] for p in pts3) / len(pts3) - c[i] for i in range(3)]
    return pts3 if sum(n[i] * fc[i] for i in range(3)) >= 0 else pts3[::-1]


def net_faces(theta: float):
    """Грани развёртки-креста при угле сгиба theta (0 — плоско, 90 — куб). -> {имя: 4 точки}."""
    B = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    F = [_rot(p, (0, 0, 0), (1, 0, 0), -theta) for p in [(0, -1, 0), (1, -1, 0), (1, 0, 0), (0, 0, 0)]]
    K = [_rot(p, (0, 1, 0), (1, 0, 0), theta) for p in [(0, 1, 0), (1, 1, 0), (1, 2, 0), (0, 2, 0)]]
    Lf = [_rot(p, (0, 0, 0), (0, 1, 0), theta) for p in [(-1, 0, 0), (0, 0, 0), (0, 1, 0), (-1, 1, 0)]]
    R = [_rot(p, (1, 0, 0), (0, 1, 0), -theta) for p in [(1, 0, 0), (2, 0, 0), (2, 1, 0), (1, 1, 0)]]
    # крышка — на дальнем краю задней грани: сначала сгиб относительно задней, потом вместе с ней
    T0 = [(0, 2, 0), (1, 2, 0), (1, 3, 0), (0, 3, 0)]
    T1 = [_rot(p, (0, 2, 0), (1, 0, 0), theta) for p in T0]
    T = [_rot(p, (0, 1, 0), (1, 0, 0), theta) for p in T1]
    return {"B": B, "K": K, "R": R, "F": F, "L": Lf, "T": T}


def v_net(theme):
    pal = _pal(theme)
    order = ["B", "K", "R", "F", "L", "T"]  # дно, задние, передние, крышка — z одинаков во всех состояниях

    def make(cam, k):
        th = [0, 90, 90][k]
        fs = net_faces(th)
        objs = []
        for zi, nm in enumerate(order):
            pts3 = [(x * 1.9, y * 1.9, z * 1.9) for x, y, z in fs[nm]]
            hot = k == 2 and nm == "F"
            base = pal["acc"] if hot else (pal["grey"] if nm in ("F", "L", "T", "B") else pal["grey2"])
            if k == 0:
                col = face_col(cam, [(0, 0, 0), (1, 0, 0), (1, 1, 0)], base)
                col = mix(col, pal["bg"], 0.0 if nm != "B" else 0.15)
            else:
                col = face_col(cam, _outward(pts3), base)
            objs.append(face(f"!!nf{nm}", cam, pts3, base, z=10 + zi, col=col, edge=pal["bg"], ew=1.25))
            if k == 0:
                c = [sum(p[i] for p in pts3) / 4 for i in range(3)]
                px, py = cam.p(tuple(c))
                objs.append(label(f"!!nl{nm}", px - 0.9, py - 0.17, 1.8, NET[order.index(nm)], sz=14, b=True, al="c",
                                  col=ink_on(theme, col)))
        if k >= 1:
            names = {"T": NET[5], "F": NET[3], "L": NET[4]}
            anchors = {"T": (0.95, 0.95, 1.9), "F": (0.95, 0.0, 0.95), "L": (0.0, 0.95, 0.95)}
            for nm, (ax, ay, az) in anchors.items():
                px, py = cam.p((ax * 1.9 / 0.95 / 2 * 0.95 * 2 / 1.9 * 1.9 / 1.9, ay, az))
                px, py = cam.p((ax * 2, ay * 2, az))
                side = 1 if nm == "F" else -1
                tx = px + side * 1.4
                objs.append(O(f"ln{nm}{k}", "line", min(px, tx) if side > 0 else tx, py, 1.2, 0, ln="line", lw=1, z=60))
                objs.append(label(f"nt{nm}{k}", tx + (0.1 if side > 0 else -2.1), py - 0.2, 2.0, names[nm], sz=15,
                                  al="l" if side > 0 else "r", b=(k == 2 and nm == "F"),
                                  col="accent" if (k == 2 and nm == "F") else "ink2"))
        return objs

    cam0 = fitcam(iso(0, 0, 1, yaw=40, pitch=30), make, [0], (5.6, 1.2, 6.6, 5.4))
    cam1 = fitcam(iso(0, 0, 1, yaw=40, pitch=30), make, [1, 2], (6.9, 1.5, 3.9, 4.8))
    heads = [head("Шесть вопросов", "развёртка плана"), head("План собран", "грани сходятся в куб"),
             head("Главное — бюджет", "передняя грань")]
    return Variant(FAM, "net_fold", "Развёртка складывается в куб",
                   "Крест из шести плиток-вопросов лежит на полу, затем грани поднимаются на шарнирах и складываются в "
                   "куб; подписи уходят к видимым граням. Роль: «из частей — целое», чек-лист плана → готовый продукт.",
                   [Slide(heads[k] + make(cam0 if k == 0 else cam1, k), dur=900) for k in range(3)],
                   tags=["cube", "fold", "net", "3d"],
                   score=5)


# ----------------------------------------------------------------------------- коробка открывается

def v_box_open(theme):
    pal = _pal(theme)
    W, D, H = 3.0, 2.4, 1.6

    def make(cam, k):
        objs = []
        # внутренность: задняя и правая стенки изнутри, дно
        inner = [("ib", [(0, D, 0), (W, D, 0), (W, D, H), (0, D, H)]),
                 ("ir", [(W, 0, 0), (W, D, 0), (W, D, H), (W, 0, H)]),
                 ("if", [(0, 0, 0), (W, 0, 0), (W, D, 0), (0, D, 0)])]
        for zi, (nm, q) in enumerate(inner):
            objs.append(face(f"!!bx{nm}", cam, q, pal["grey3"], z=10 + zi, col=shade(pal["grey3"], -0.45 + 0.2 * zi),
                             edge=pal["bg"]))
        # содержимое: три кубика поднимаются и встают в ряд
        items = ["Ключ", "Карта", "Код"]
        for j in range(3):
            if k == 0:
                x, y, z0 = 0.3 + j * 0.9, 0.7, 0.0
            elif k == 1:
                x, y, z0 = 0.3 + j * 0.9, 0.7, H + 0.9
            else:
                x, y, z0 = -1.6 + j * 2.4, -2.6, 0.0
            objs += boxes(cam, [dict(n=f"!!it{j}", x=x, y=y, z=z0, w=0.75, d=0.75, h=0.75,
                                     col=pal["acc"] if j == 0 else pal["acc3"])], z0=20 + j * 3)
            if k == 2:
                px, py = cam.p((x + 0.37, y, 0))
                objs.append(label(f"itl{j}", px - 0.8, py + 0.1, 1.6, items[j], sz=15, al="c", col="ink"))
        # внешние передние стенки
        outer = [("om", [(0, 0, 0), (W, 0, 0), (W, 0, H), (0, 0, H)]), ("ox", [(0, D, 0), (0, 0, 0), (0, 0, H), (0, D, H)])]
        for zi, (nm, q) in enumerate(outer):
            objs.append(face(f"!!bx{nm}", cam, q, pal["grey"], z=40 + zi, edge=pal["bg"]))
        # крышка на шарнире по заднему верхнему ребру
        ang = [0, -115, -115][k]
        lid = [(0, 0, H), (W, 0, H), (W, D, H), (0, D, H)]
        lid = [_rot(p, (0, D, H), (1, 0, 0), ang) for p in lid]
        f = cam.facing(lid)
        col = face_col(cam, lid, pal["grey2"]) if f > 0 else shade(pal["grey3"], -0.2)
        objs.append(poly("!!lid", [cam.p(p) for p in lid], fill=col, ln=pal["bg"], lw=0.75, z=50 if k == 0 else 9))
        return objs

    from lab._c_util import shade
    cam = fitcam(iso(0, 0, 1, yaw=38, pitch=30), make, [0, 1, 2], (5.4, 1.1, 7.2, 5.6))
    heads = [head("Что внутри", "набор для старта"), head("Открываем", "три вещи"), head("Набор новичка", "по порядку")]
    return Variant(FAM, "box_open", "Коробка открывается",
                   "Изометрическая коробка: крышка откидывается на шарнире, из неё поднимаются три кубика, затем они "
                   "встают в ряд с подписями. Роль: «что входит в пакет», онбординг, комплектация тарифа.",
                   [Slide(heads[k] + make(cam, k), dur=850) for k in range(3)], tags=["cube", "hinge", "reveal", "3d"],
                   score=4)


# ----------------------------------------------------------------------------- жалюзи: ламели поворачиваются и открывают текст

def v_blinds(theme):
    pal = _pal(theme)
    cam = Cam3(8.6, 3.9, 1.0, yaw=0, pitch=6, dist=20)
    n, Wd, Hs = 8, 6.8, 0.62

    def make(k):
        objs = []
        ang = [0, 78, 0][k]
        for i in range(n):
            zc = (n / 2 - i - 0.5) * Hs
            q = [(-Wd / 2, 0, zc - Hs / 2), (Wd / 2, 0, zc - Hs / 2), (Wd / 2, 0, zc + Hs / 2), (-Wd / 2, 0, zc + Hs / 2)]
            q = [_rot(p, (0, 0, zc), (1, 0, 0), ang) for p in q]
            base = pal["acc"] if k == 2 else pal["grey"]
            col = face_col(cam, q, base)
            objs.append(poly(f"!!sl{i}", [cam.p(p) for p in q], fill=col, ln=pal["bg"], lw=0.75, z=40 + i))
        if k == 0:
            objs.append(label("bt0", 8.6 - 3.0, 3.55, 6.0, "Итоги года", sz=40, b=True, al="c",
                              col=ink_on(theme, face_col(cam, [(0, 0, 0), (1, 0, 0), (1, 0, 1)], pal["grey"])), z=80))
        if k == 1:
            lines = ["+18% выручки", "3 новых рынка", "NPS 64"]
            for j, t in enumerate(lines):
                objs.append(label(f"bt1_{j}", 8.6 - 3.0, 2.3 + j * 0.85, 6.0, t, sz=30, b=j == 0, al="c",
                                  col="accent" if j == 0 else "ink", z=20))
        if k == 2:
            objs.append(label("bt2", 8.6 - 3.0, 3.55, 6.0, "План на 2027", sz=40, b=True, al="c",
                              col=ink_on(theme, face_col(cam, [(0, 0, 0), (1, 0, 0), (1, 0, 1)], pal["acc"])), z=80))
        return objs

    heads = [head("Отчёт", "закрытые жалюзи"), head("Цифры за шторкой"), head("Дальше", "новая сторона ламелей")]
    return Variant(FAM, "blinds", "Жалюзи открывают цифры",
                   "Панель из восьми ламелей: они поворачиваются ребром (с перспективой), за ними видны итоговые цифры; "
                   "затем закрываются другой стороной. Роль: «приоткрыть» результат, переход итоги → план.",
                   [Slide(heads[k] + make(k), dur=850) for k in range(3)], tags=["slats", "rotate", "reveal", "3d"],
                   score=4)


# ----------------------------------------------------------------------------- матрёшка: куб в кубе

def v_nested(theme):
    """Три вложенных куба: видимые грани внешнего отъезжают по нормалям и тускнеют — открывается следующий."""
    pal = _pal(theme)
    from lab._c_util import BOX_FACES
    sizes = [4.0, 2.6, 1.3]
    cols = [pal["grey2"], pal["grey"], pal["acc"]]
    names = ["Компания", "Отдел", "Команда"]

    def make(cam, k):
        objs = []
        for lv, sz in enumerate(sizes):
            o = -sz / 2
            opened = k > lv  # этот куб уже «раскрыт»
            push = 1.4 * (sizes[lv] / 4.0) if opened else 0.0
            for fi, f in enumerate(("ym", "xm", "top")):
                pts3 = BOX_FACES[f](o, o, o + 2.0, sz, sz, sz)
                nx, ny, nz = {"ym": (0, -1, 0), "xm": (-1, 0, 0), "top": (0, 0, 1)}[f]
                pts3 = [(x + nx * push, y + ny * push, z + nz * push) for x, y, z in pts3]
                objs.append(face(f"!!nc{lv}{f}", cam, pts3, cols[lv], z=10 + (2 - lv) * 10 + fi, fa=0.22 if opened else 1.0,
                                 edge=pal["bg"]))
            if k == lv:
                px, py = cam.p((sz / 2, -sz / 2, 2.0 - sz / 2 + sz * 0.5))
                objs.append(label(f"nl{k}", px + 0.35, py - 0.22, 2.6, names[lv], sz=20, b=True,
                                  col="accent" if lv == 2 else "ink", z=90))
        return objs

    cam = fitcam(iso(0, 0, 1, yaw=40, pitch=30), make, [0, 1, 2], (5.4, 1.1, 6.0, 5.6))
    heads = [head("Снаружи", "вся компания"), head("Внутри", "грани расходятся"), head("Ядро", "команда продукта")]
    return Variant(FAM, "nested", "Матрёшка: куб в кубе",
                   "Видимые грани внешнего куба отъезжают по своим нормалям и становятся прозрачными — внутри следующий "
                   "куб, затем ядро. Роль: уровни вложенности (компания → отдел → команда), «заглянуть внутрь».",
                   [Slide(heads[k] + make(cam, k), dur=850) for k in range(3)], tags=["cube", "nested", "explode", "3d"],
                   score=4)


# ----------------------------------------------------------------------------- цилиндр-барабан с полосами

def v_cylinder(theme):
    pal = _pal(theme)
    cam = Cam3(8.5, 4.0, 1.0, yaw=0, pitch=14, dist=18)
    n = 24

    def make(k):
        ph = 7.5 + 30 * k
        lo = ring_pts(0, 0, -1.9, 1.9, n, ph)
        hi = ring_pts(0, 0, 1.9, 1.9, n, ph)
        cols = [[pal["acc"], pal["grey"], pal["acc3"], pal["grey3"]][i // 6] for i in range(n)]
        objs, shown = prism_side("!!cy", cam, lo, hi, cols, ew=0.4)
        objs.append(poly("!!cyc", [cam.p(p) for p in hi], fill=face_col(cam, [(0, 0, 1), (1, 0, 1), (1, 1, 1)], pal["grey2"]),
                         z=40))
        return objs

    heads = [head("Неделя 1", "полоса-метка уходит"), head("Неделя 2"), head("Неделя 3")]
    return Variant(FAM, "cylinder", "Цилиндр с меткой поворачивается",
                   "24-гранный цилиндр с акцентной полосой: поворот на 30° за клик, метка уезжает за край, оттенки граней "
                   "меняются по свету. Роль: «время идёт», цикл, вращение без цифр.",
                   [Slide(heads[k] + make(k), dur=800) for k in range(3)], tags=["cylinder", "rotate", "cycle"], score=3)


# ----------------------------------------------------------------------------- куб в изометрии кувыркается

def v_die(theme):
    """Кубик в изометрии поворачивается на 90° вокруг вертикали (боковые грани со схлопыванием, крышка честная)."""
    pal = _pal(theme)
    topics = ["Цена", "Качество", "Скорость", "Сервис"]

    def make(cam, k):
        n = 4
        ph = 90 * k
        lo = ring_pts(0, 0, 0, 1.414, n, ph)
        hi = ring_pts(0, 0, 2.0, 1.414, n, ph)
        cols = [pal["acc"] if i == (k + 3) % 4 else pal["grey"] for i in range(n)]
        cols = [pal["grey"]] * 4
        objs, shown = prism_side("!!dc", cam, lo, hi, cols, edge=pal["bg"])
        objs.append(poly("!!dct", [cam.p(p) for p in hi], fill=face_col(cam, [(0, 0, 1), (1, 0, 1), (1, 1, 1)], pal["grey2"]),
                         ln=pal["bg"], lw=0.75, z=40))
        for i in shown:
            q = [lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]]
            pts = [cam.p(p) for p in q]
            cx, cy = sum(p[0] for p in pts) / 4, sum(p[1] for p in pts) / 4
            o = [x for x in objs if x.name == f"!!dc{i}"][0]
            objs.append(label(f"dt{k}_{i}", cx - 1.1, cy - 0.22, 2.2, topics[i], sz=20, b=True, al="c",
                              col=ink_on(theme, o.fill), z=80))
        return objs

    cam = fitcam(Cam3(0, 0, 1, yaw=0, pitch=24), make, [0, 1, 2], (6.0, 1.3, 5.8, 5.4))
    heads = [head("Четыре довода"), head("Поворот", "следующая пара"), head("И снова", "по кругу")]
    return Variant(FAM, "cube_turn", "Куб поворачивается гранью",
                   "Куб на столе поворачивается на 90° вокруг вертикали: две видимые грани с доводами сменяются. "
                   "Крышка при повороте чуть «дышит» (середина хорды). Роль: пары аргументов, сравнение «двух сторон».",
                   [Slide(heads[k] + make(cam, k), dur=850) for k in range(3)], tags=["cube", "rotate", "3d"], score=3)


# ----------------------------------------------------------------------------- карточки-ламели разворачиваются к зрителю

def v_cards_turn(theme):
    pal = _pal(theme)
    cam = Cam3(6.67, 4.2, 1.0, yaw=0, pitch=8, dist=18)
    titles = ["Сбор", "Анализ", "Решение", "Действие"]

    def make(k):
        objs = []
        for i in range(4):
            cx = (i - 1.5) * 2.9
            ang = [80, 0, 0][k] if k < 2 else (0 if i != 2 else 0)
            q = [(cx - 1.25, 0, -1.6), (cx + 1.25, 0, -1.6), (cx + 1.25, 0, 1.6), (cx - 1.25, 0, 1.6)]
            q = [_rot(p, (cx, 0, 0), (0, 0, 1), ang) for p in q]
            dy = -1.2 if (k == 2 and i == 2) else 0
            q = [(x, y + dy, z) for x, y, z in q]
            base = pal["acc"] if (k == 2 and i == 2) else pal["grey"]
            col = face_col(cam, q, base)
            objs.append(poly(f"!!cd{i}", [cam.p(p) for p in q], fill=col, ln=pal["bg"], lw=0.75, z=20 + i))
            if k >= 1:
                pc = cam.p((cx, dy, 0))
                objs.append(label(f"ct{k}_{i}", pc[0] - 1.1, pc[1] - 0.25, 2.2, titles[i], sz=20, b=True, al="c",
                                  col=ink_on(theme, col), z=60))
        return objs

    heads = [head("Четыре шага", "ребром к нам"), head("Шаги процесса"), head("Ключевой — решение")]
    return Variant(FAM, "cards_turn", "Карточки разворачиваются к зрителю",
                   "Четыре карточки стоят ребром (видны тонкими полосками) и одновременно поворачиваются лицом, затем "
                   "одна выходит вперёд с перспективой. Роль: раскрытие ряда шагов, «показать все сразу».",
                   [Slide(heads[k] + make(k), dur=850) for k in range(3)], tags=["cards", "rotate", "reveal"], score=4)


# ----------------------------------------------------------------------------- SEQ 1. кубик-план: развёртка → куб → повороты → снова развёртка

def v_seq_die(theme):
    pal = _pal(theme)
    order = ["B", "K", "R", "F", "L", "T"]
    TOP = ["Цель", "Аудитория", "Канал", "Бюджет", "Сроки", "Риски"]  # по order

    def faces_state(cam, theta, hot=None, lift=0.0, spread=0.0, labels=False):
        fs = net_faces(theta)
        objs = []
        for zi, nm in enumerate(order):
            pts3 = [(x * 1.9, y * 1.9, z * 1.9 + lift) for x, y, z in fs[nm]]
            if spread:
                c = [sum(p[i] for p in pts3) / 4 for i in range(3)]
                cc = (0.95, 0.95, 0.95 + lift)
                pts3 = [(x + (c[0] - cc[0]) * spread, y + (c[1] - cc[1]) * spread, z + (c[2] - cc[2]) * spread)
                        for x, y, z in pts3]
            base = pal["acc"] if nm == hot else (pal["grey"] if nm in ("F", "L", "T", "B") else pal["grey2"])
            col = (face_col(cam, [(0, 0, 0), (1, 0, 0), (1, 1, 0)], base) if theta == 0 else
                   face_col(cam, _outward(pts3), base))
            objs.append(face(f"!!nf{nm}", cam, pts3, base, z=10 + zi, col=col, edge=pal["bg"], ew=1.25))
            if labels:
                c = [sum(p[i] for p in pts3) / 4 for i in range(3)]
                px, py = cam.p(tuple(c))
                objs.append(label(f"!!nl{nm}", px - 0.9, py - 0.17, 1.8, TOP[zi], sz=14, b=True, al="c",
                                  col=ink_on(theme, col)))
        return objs

    def side_labels(cam, items, k, hot=None):
        out = []
        for j, (nm, anchor, side) in enumerate(items):
            px, py = cam.p(anchor)
            tx = px + side * 1.3
            out.append(O(f"ln{k}_{j}", "line", min(px, tx), py, 1.3, 0, ln="line", lw=1, z=60))
            out.append(label(f"nt{k}_{j}", tx + (0.1 if side > 0 else -2.1), py - 0.2, 2.0, nm, sz=15,
                             al="l" if side > 0 else "r", b=nm == hot, col="accent" if nm == hot else "ink2"))
        return out

    base = iso(0, 0, 1, yaw=40, pitch=30)
    camn = fitcam(base, lambda c, k: faces_state(c, 0), [0], (5.6, 1.2, 6.6, 5.4))
    cam = fitcam(base, lambda c, k: faces_state(c, 90, lift=0.5 * k), [0, 1], (6.9, 1.4, 3.9, 5.0))
    cam_c = fitcam(base, lambda c, k: faces_state(c, 90, spread=0.8), [0], (5.6, 1.2, 6.6, 5.4))
    slides = []
    # 1 развёртка
    slides.append(Slide(head("Шесть вопросов", "план кампании") + faces_state(camn, 0, labels=True), dur=900))
    # 2 сложили
    slides.append(Slide(head("План собран", "один предмет") + faces_state(cam, 90) +
                        side_labels(cam, [("Бюджет", (1.9, 0, 0.95), 1), ("Сроки", (0, 1.9, 0.95), -1),
                                          ("Риски", (0, 1.9, 1.9), -1)], 1), dur=900))
    # 3 подсветили бюджет и куб приподнялся
    slides.append(Slide(head("Сначала деньги", "грань горит") + faces_state(cam, 90, hot="F", lift=0.5) +
                        side_labels(cam, [("Бюджет", (1.9, 0, 1.45), 1)], 2, hot="Бюджет"), dur=800))
    # 4 куб раскрылся в объёме: грани отошли от центра — видно, что внутри
    slides.append(Slide(head("Разберём", "грани отходят") + faces_state(cam_c, 90, hot="F", spread=0.8), dur=900))
    # 5 снова плотный куб, подсветка сроков
    slides.append(Slide(head("Потом время", "вторая грань") + faces_state(cam, 90, hot="L", lift=0.5) +
                        side_labels(cam, [("Сроки", (0, 1.9, 1.45), -1)], 4, hot="Сроки"), dur=800))
    # 6 развернули обратно: итоговая развёртка с двумя отметками
    slides.append(Slide(head("Итог", "развёртка с решениями") + faces_state(camn, 0, labels=True, hot="F"), dur=900))
    return Variant(FAM, "seq_die", "Кубик-план: сборка и разбор",
                   "Один куб живёт 6 слайдов: развёртка из шести вопросов → складывается в куб с выносками → "
                   "куб приподнимается, горит «бюджет» → грани отходят от центра (взрыв-схема) → снова куб, горят "
                   "«сроки» → разворачивается обратно в плоскую развёртку-итог. Роль: план/чек-лист как предмет.",
                   slides, tags=["cube", "seq", "fold", "explode"], score=4)


# ----------------------------------------------------------------------------- SEQ 2. барабан-навигатор: поворот → грань-панель → обратно

def v_seq_drum(theme):
    pal = _pal(theme)
    topics = ["Идея", "Рынок", "Продукт", "Команда", "Деньги", "План"]
    n = 6
    cam = Cam3(8.4, 4.0, 1.0, yaw=0, pitch=10, dist=16)
    cam_side = Cam3(10.8, 3.9, 0.5, yaw=0, pitch=10, dist=16)

    def drum_state(c, k, hot=None):
        cols = [pal["acc"] if (hot is not None and i == hot) else pal["grey"] for i in range(n)]
        objs, info = drum("!!hx", c, n, 30 - 60 * k, 7.0, 2.1, cols, edge=pal["bg"])
        return objs, info

    def front_label(objs, info, k, sz=30, tag=""):
        f = _front_face(info)
        (cx, cy), w, h, _ = info[f]
        o = [x for x in objs if x.name == f"!!hx{f}"][0]
        return [label(f"tp{tag}{k}", cx - w / 2 + 0.2, cy - sz / 72 * 0.65, w - 0.4, topics[(f - 5) % n], sz=sz, b=True,
                      al="c", col=ink_on(theme, o.fill), z=80)], f

    slides = []
    for step, k in enumerate([0, 1]):
        objs, info = drum_state(cam, k)
        lab, f = front_label(objs, info, k)
        slides.append(Slide(head(f"Раздел {k + 1}", "барабан тем") + objs + lab, dur=800))
    # 3: барабан отъезжает вправо и уменьшается, передняя грань «отрывается» панелью к зрителю
    objs, info = drum_state(cam_side, 1)
    f = _front_face(info)
    panel = [o for o in objs if o.name == f"!!hx{f}"][0]
    objs = [o for o in objs if o.name != f"!!hx{f}"]
    pts = [(0.75, 2.0), (7.6, 2.0), (7.6, 6.5), (0.75, 6.5)]
    # вершины панели в том же порядке, что у грани (лево-верх, право-верх ... по исходной грани)
    src = panel.meta["vec"][0]
    srcp = [(panel.x + u * panel.w, panel.y + v * panel.h) for u, v in src]
    order = sorted(range(4), key=lambda i: (srcp[i][1], srcp[i][0]))  # два верхних, потом два нижних
    tl, tr = sorted(order[:2], key=lambda i: srcp[i][0])
    bl, br = sorted(order[2:], key=lambda i: srcp[i][0])
    tgt = [None] * 4
    tgt[tl], tgt[tr], tgt[br], tgt[bl] = pts[0], pts[1], pts[2], pts[3]
    objs.append(poly(f"!!hx{f}", tgt, fill=pal["grey3"], ln=pal["bg"], lw=0.75, z=50))
    body = ["Сегмент: малый бизнес", "Объём: 40 млрд ₽", "Рост: 12% в год"]
    objs.append(label("pnt", 1.15, 2.3, 6.0, topics[(f - 5) % n], sz=30, b=True, col=ink_on(theme, pal["grey3"]), z=80))
    for j, t in enumerate(body):
        objs.append(label(f"pnb{j}", 1.15, 3.3 + j * 0.62, 6.0, t, sz=20, col=ink_on(theme, pal["grey3"]), z=80))
    slides.append(Slide(head("Рынок крупно", "грань стала панелью") + objs, dur=900))
    # 4: панель возвращается, барабан поворачивается дальше
    for k in (2, 3):
        objs, info = drum_state(cam, k)
        lab, f2 = front_label(objs, info, k)
        slides.append(Slide(head(f"Раздел {k + 1}", "барабан тем") + objs + lab, dur=850))
    # 6: барабан ложится — камера сверху, видны все шесть граней рядом (развёртка призмы в ленту)
    objs = []
    for i in range(n):
        x0 = 0.9 + i * 2.0
        hot = i == 2
        o_pts = [(x0 + 1.85, 5.6), (x0 + 1.85, 2.6), (x0, 2.6), (x0, 5.6)]  # обход грани барабана: НП, ВП, ВЛ, НЛ
        objs.append(poly(f"!!hx{i}", o_pts, fill=pal["acc"] if hot else pal["grey"], ln=pal["bg"], lw=0.75, z=20))
        objs.append(label(f"ls{i}", x0 + 0.02, 3.85, 1.81, topics[(i - 5) % n], sz=19, b=True, al="c",
                          col=ink_on(theme, pal["acc"] if hot else pal["grey"]), z=80))
    slides.append(Slide(head("Все шесть разделов", "барабан развернулся лентой") + objs, dur=900))
    # 7: обратно барабан, финальная грань «План» акцентом
    objs, info = drum_state(cam, 5, hot=4)
    lab, f = front_label(objs, info, 5)
    slides.append(Slide(head("Итог", "последняя грань") + objs + lab, dur=900))
    return Variant(FAM, "seq_drum", "Барабан-навигатор презентации",
                   "Шестигранный барабан ведёт 7 слайдов: поворот на раздел → передняя грань отрывается и становится "
                   "плоской панелью с текстом (барабан отъезжает) → возвращается, поворот дальше → барабан разворачивается "
                   "в ленту всех шести разделов (оглавление) → снова барабан, финальная грань. Роль: сквозное оглавление.",
                   slides, tags=["prism", "seq", "navigation", "panel"], score=4)


def variants(theme) -> list[Variant]:
    from lab._c_util import ensure_contrast
    return ensure_contrast(theme, [f(theme) for f in (v_drum4, v_drum6, v_octo, v_net, v_box_open, v_blinds, v_nested, v_cylinder, v_die,
                               v_cards_turn, v_seq_die, v_seq_drum)])
