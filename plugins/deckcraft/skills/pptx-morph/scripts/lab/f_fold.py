"""Семейство «Бумага и складки»: лист складывается, гармошка, загиб страницы, конверт, веер, карта.

Каждая панель бумаги — четырёхугольник в 3D; сгиб = поворот вершин вокруг линии сгиба (Родриг), затем
проекция Cam3. Цвет панели — по свету и по стороне: лицо (front) или изнанка (back), определяется знаком facing.
Вершины всегда в одном порядке, поэтому панель переливается, даже когда поворачивается к нам изнанкой.
Порядок слоёв (z) задан один на все состояния (как стопка бумаги), чтобы не зависеть от z-порядка Morph.
"""

from __future__ import annotations

import math

from morphkit import O, Slide
from morphkit import vector as V
from morphkit.theme import mix

from lab import Variant
from lab._c_util import Cam3, face_col, fitcam, head, ink_on, iso, label, newell, poly, shade

FAM = "fold"


def _pal(theme):
    ink2, bg = theme.c("ink2"), theme.c("bg")
    return {"paper": mix(theme.c("ink"), bg, 0.18), "paper2": mix(theme.c("ink"), bg, 0.32),
            "grey": mix(ink2, bg, 0.45), "grey2": mix(ink2, bg, 0.62), "grey3": mix(ink2, bg, 0.30),
            "acc": theme.c("accent"), "acc3": theme.c("accent3"), "bg": bg, "ink": theme.c("ink"),
            "floor": mix(theme.c("surface2"), ink2, 0.10), "line": theme.c("line")}


def rot(p, a_p, a_d, ang):
    a = math.radians(ang)
    px, py, pz = (p[i] - a_p[i] for i in range(3))
    L = math.sqrt(sum(c * c for c in a_d))
    kx, ky, kz = (c / L for c in a_d)
    c, s = math.cos(a), math.sin(a)
    dot = kx * px + ky * py + kz * pz
    cx, cy, cz = ky * pz - kz * py, kz * px - kx * pz, kx * py - ky * px
    r = (px * c + cx * s + kx * dot * (1 - c), py * c + cy * s + ky * dot * (1 - c), pz * c + cz * s + kz * dot * (1 - c))
    return tuple(r[i] + a_p[i] for i in range(3))


def paper(name, cam, pts3, front, back, z, edge=None, ew=0.6, fa=1.0, meta=None):
    """Панель бумаги: лицо или изнанка — по тому, какой стороной она к зрителю."""
    f = cam.facing(pts3)
    if f >= 0:
        col = face_col(cam, pts3, front)
    else:
        col = face_col(cam, pts3[::-1], back)
    return poly(name, [cam.p(p) for p in pts3], fill=col, ln=edge or col, lw=ew, la=fa, fa=fa, z=z, meta=meta)


# ----------------------------------------------------------------------------- 1. буклет: обложка → стоит → разворот

def v_booklet(theme):
    pal = _pal(theme)
    W, H = 3.0, 4.0

    def make(cam, k):
        ang = [180, 90, 0][k]  # угол правой половины относительно разворота
        left = [(-W, 0, 0), (0, 0, 0), (0, H, 0), (-W, H, 0)]
        right = [(0, 0, 0), (W, 0, 0), (W, H, 0), (0, H, 0)]
        right = [rot(p, (0, 0, 0), (0, 1, 0), -ang) for p in right]
        objs = [paper("!!bl_l", cam, left, pal["paper"], pal["acc"], 10, edge=pal["bg"]),
                paper("!!bl_r", cam, right, pal["paper"], pal["acc"], 11, edge=pal["bg"])]
        if k == 0:
            c = [sum(p[i] for p in right) / 4 for i in range(3)]
            px, py = cam.p(c)
            objs.append(label("bt0", px - 1.4, py - 0.35, 2.8, "Годовой\nотчёт", sz=24, b=True, al="c",
                              col=ink_on(theme, objs[1].fill), z=40))
        if k == 2:
            for side, lines in ((-1, ["Выручка", "+18%"]), (1, ["Клиенты", "12 400"])):
                c = (side * W / 2, H / 2, 0)
                px, py = cam.p(c)
                o = objs[0] if side < 0 else objs[1]
                objs.append(label(f"bt2{side}", px - 1.2, py - 0.5, 2.4, lines, sz=22, b=True, al="c",
                                  col=ink_on(theme, o.fill), z=40))
        return objs

    cam = fitcam(iso(0, 0, 1, yaw=20, pitch=52), make, [0, 1, 2], (5.6, 1.2, 6.8, 5.6))
    heads = [head("Отчёт за год", "закрытая обложка"), head("Открываем", "половина встаёт"),
             head("Разворот", "главные цифры")]
    return Variant(FAM, "booklet", "Буклет раскрывается",
                   "Сложенный буклет лежит обложкой вверх; правая половина поднимается на ребро (изнанка видна в "
                   "перспективе), затем ложится разворотом с цифрами. Роль: «открываем отчёт», переход обложка → содержание.",
                   [Slide(heads[k] + make(cam, k), dur=850) for k in range(3)], tags=["fold", "paper", "reveal", "3d"],
                   score=4)


# ----------------------------------------------------------------------------- 2. гармошка этапов

def v_accordion(theme):
    pal = _pal(theme)
    steps = ["Анализ", "Дизайн", "Код", "Тесты", "Релиз"]
    n, w, h = 5, 1.8, 3.4

    def strip(cam, ang):
        """Зигзаг: панель i наклонена на ±ang вокруг вертикали; ширина в плане w·cos(ang)."""
        objs = []
        x = 0.0
        a = math.radians(ang)
        for i in range(n):
            sgn = 1 if i % 2 == 0 else -1
            x0, y0 = x, 0.0 if i % 2 == 0 else w * math.sin(a)
            x1, y1 = x + w * math.cos(a), w * math.sin(a) if i % 2 == 0 else 0.0
            pts = [(x0, y0, 0), (x1, y1, 0), (x1, y1, h), (x0, y0, h)]
            objs.append(paper(f"!!ac{i}", cam, pts, pal["paper"] if i != 2 else pal["acc"], pal["paper2"], 10 + i,
                              edge=pal["bg"]))
            x = x1
            _ = sgn
        return objs

    def make(cam, k):
        ang = [0, 55, 80][k]
        objs = strip(cam, ang)
        if k == 0:
            for i, t in enumerate(steps):
                px, py = cam.p((i * w + w / 2, 0, h / 2))
                objs.append(label(f"as{i}", px - 0.8, py - 0.2, 1.6, t, sz=17, b=True, al="c",
                                  col=ink_on(theme, objs[i].fill), z=40))
        return objs

    cam = fitcam(Cam3(0, 0, 1, yaw=0, pitch=16, dist=26), make, [0], (5.4, 1.4, 7.4, 5.0))
    heads = [head("Пять этапов", "по 2 недели"), head("Сжимаем", "этапы складываются"),
             head("Шесть недель", "вместо десяти")]
    return Variant(FAM, "accordion", "Гармошка: сроки сжимаются",
                   "Лента из пяти панелей-этапов складывается гармошкой: панели наклоняются попеременно, светлые и "
                   "тёмные, вся лента сжимается к левому краю; ключевой этап — акцентом. Роль: сжатие сроков, "
                   "компактность, «сложили процесс».",
                   [Slide(heads[k] + make(cam, k), dur=850) for k in range(3)], tags=["fold", "accordion", "time"],
                   score=4)


# ----------------------------------------------------------------------------- 3. загиб страницы

def v_curl(theme):
    pal = _pal(theme)
    X0, Y0, W, H = 6.4, 1.2, 5.4, 5.4

    def page(k):
        """Страница с загнутым правым нижним углом; t — насколько далеко линия сгиба."""
        t = [0.0, 1.6, 3.4][k]
        objs = []
        # страница 2 (под низом)
        objs.append(poly("!!pg2", [(X0, Y0), (X0 + W, Y0), (X0 + W, Y0 + H), (X0, Y0 + H)], fill=pal["grey3"], z=5))
        # видимая часть страницы 1: пятиугольник (угол срезан по линии сгиба под 45°)
        a = (X0 + W - t, Y0 + H)  # точка на нижнем крае
        b = (X0 + W, Y0 + H - t)  # точка на правом крае
        objs.append(poly("!!pg1", [(X0, Y0), (X0 + W, Y0), b, a, (X0, Y0 + H)], fill=pal["paper"], z=10))
        # клапан: отражение срезанного треугольника относительно линии a–b
        c = (X0 + W, Y0 + H)
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        cr = (2 * mx - c[0], 2 * my - c[1])
        g = V.gradient([(0, mix(pal["paper"], "FFFFFF", 0.25)), (1, mix(pal["paper"], "000000", 0.35))], angle=45)
        objs.append(poly("!!flap", [a, b, cr], fill=pal["paper2"], grad=g, z=12))
        sh = [(a[0] - 0.12, a[1]), (b[0], b[1] - 0.12), (cr[0] - 0.12, cr[1] - 0.12)]
        objs.append(poly("!!flsh", sh, fill="000000", fa=0.25, z=11))
        objs.append(label("p1t", X0 + 0.5, Y0 + 0.5, 4.4, "Глава 1", sz=30, b=True, col=ink_on(theme, pal["paper"]), z=30))
        objs.append(label("p1b", X0 + 0.5, Y0 + 1.25, 2.2, ["Рынок", "Конкуренты", "Цены"], sz=18,
                          col=ink_on(theme, pal["paper"]), z=30))
        if k == 2:
            objs.append(label("p2t", X0 + W - 2.0, Y0 + H - 0.8, 1.9, "Глава 2", sz=18, b=True,
                              col=ink_on(theme, pal["grey3"]), z=8))
        return objs

    heads = [head("Отчёт", "страница первая"), head("Загиб угла", "что дальше?"), head("Следующая глава", "видна под углом")]
    return Variant(FAM, "page_curl", "Загиб угла страницы",
                   "Угол страницы загибается: видимая часть — пятиугольник, клапан — отражённый треугольник с "
                   "градиентом и тенью; при втором клике загиб растёт и открывает следующую главу. "
                   "Роль: тизер следующего раздела, «перелистнуть».",
                   [Slide(heads[k] + page(k), dur=800) for k in range(3)], tags=["fold", "page", "teaser"], score=3)


# ----------------------------------------------------------------------------- 4. конверт

def envelope(pal, cam, k, x0=0.0, scale=1.0, letter_up=None, flap_open=None, lines=None, fly=None, theme=None):
    """Конверт в 3D (плоскость y=0): задник, клапан, письмо, кармашек. z-порядок постоянный."""
    W, H = 5.0 * scale, 3.2 * scale
    ox = x0
    oz = 0.0
    if fly is not None:
        ox, oz = fly
    objs = []
    P = lambda x, z: (ox + x, 0, oz + z)  # noqa: E731
    back = [P(0, 0), P(W, 0), P(W, H), P(0, H)]
    objs.append(paper("!!evb", cam, back, pal["grey3"], pal["grey3"], 10))
    ang = flap_open if flap_open is not None else 0.0  # 0 — закрыт (вниз), 180 — открыт вверх
    tip = P(W / 2, H * 0.42)
    flap = [P(0, H), P(W, H), tip]
    flap = [rot(p, P(0, H), (1, 0, 0), -ang) for p in flap]
    objs.append(paper("!!evf", cam, flap + [flap[2]], pal["grey"], pal["grey2"], 11, edge=pal["bg"]))
    up = letter_up if letter_up is not None else 0.0
    lw, lh = W * 0.9, H * 0.86
    lx, lz = (W - lw) / 2, 0.12 * scale + up
    letter = [P(lx, lz), P(lx + lw, lz), P(lx + lw, lz + lh), P(lx, lz + lh)]
    objs.append(paper("!!evl", cam, letter, pal["paper"], pal["paper"], 12))
    pocket = [P(0, 0), P(W, 0), P(W, H), P(W / 2, H * 0.42), P(0, H)]
    objs.append(poly("!!evp", [cam.p(p) for p in pocket], fill=pal["grey2"], ln=pal["bg"], lw=0.6, z=13))
    return objs, letter


def v_envelope(theme):
    pal = _pal(theme)
    cam = Cam3(6.6, 6.1, 1.0, yaw=0, pitch=8, dist=30)

    def make(k):
        objs, letter = envelope(pal, cam, k, flap_open=[0, 180, 180][k], letter_up=[0, 0, 2.2][k])
        if k == 2:
            p = cam.p(letter[3])
            objs.append(label("lt", p[0] + 0.35, p[1] + 0.25, 4.0, ["Вы приняты", "в пилот"], sz=26, b=True,
                              col=ink_on(theme, pal["paper"]), z=40))
        return objs

    heads = [head("Ответ пришёл", "конверт закрыт"), head("Открываем", "клапан вверх"), head("Решение", "письмо выходит")]
    return Variant(FAM, "envelope", "Конверт открывается",
                   "Клапан конверта поворачивается на шарнире вверх (в перспективе меняется сторона и свет), затем "
                   "письмо выезжает из кармашка с текстом. Порядок слоёв постоянный — клапан всегда за письмом. "
                   "Роль: новость, результат, приглашение; эмоциональный акцент.",
                   [Slide(heads[k] + make(k), dur=850) for k in range(3)], tags=["fold", "hinge", "reveal", "paper"],
                   score=4)


# ----------------------------------------------------------------------------- 5. веер карточек с перспективой

def v_fan(theme):
    pal = _pal(theme)
    names = ["Сбор", "Разметка", "Обучение", "Оценка", "Запуск"]
    piv = (8.6, 6.4)

    def make(k):
        objs = []
        for i in range(5):
            if k == 0:
                rot_, lift, sc = 0.0, i * 0.04, 1.0
            else:
                rot_ = (i - 2) * 21.0
                lift = 0.0
                sc = 1.0
            hot = k == 2 and i == 2
            w, h = 2.0, 3.0
            x, y = piv[0] - w / 2, piv[1] - h - (0.9 if hot else 0.0) - lift
            g = V.rect(x, y, w, h, r=0.12)
            col = pal["acc"] if hot else shade(pal["grey"], 0.25 - 0.12 * abs(i - 2))
            objs.append(V.shape(f"!!fc{i}", V.resample(g, 40), pivot=piv, rot=rot_, fill=col, ln=pal["bg"], lw=1.0,
                                z=30 if i == 2 else 10 + i))
            if k >= 1:
                a = math.radians(rot_ - 90)
                R = (h * 0.62 + 0.9) if hot else h + 0.32
                tx, ty = piv[0] + R * math.cos(a), piv[1] + R * math.sin(a)
                if k == 2 and not hot:
                    continue
                objs.append(label(f"fn{k}_{i}", tx - (1.0 if hot else 0.58), ty - 0.2, 2.0 if hot else 1.16, names[i],
                                  sz=13 if not hot else 20, b=True,
                                  al="c", col=ink_on(theme, col), z=40))
        return objs

    heads = [head("Пять стадий", "стопкой"), head("Веером", "все стадии"), head("Третья стадия", "вытягиваем одну")]
    return Variant(FAM, "fan_cards", "Веер карточек",
                   "Стопка карточек раскрывается веером вокруг общей оси снизу (рамка на оси — поворот по дуге), затем "
                   "средняя карта выдвигается вверх и загорается. Роль: стадии, варианты, «вытянуть карту».",
                   [Slide(heads[k] + make(k), dur=800) for k in range(3)], tags=["fan", "pivot", "cards"], score=3)


# ----------------------------------------------------------------------------- 6. пирамида из листа

def v_pyramid_sheet(theme):
    pal = _pal(theme)
    roles = ["Клиент", "Продукт", "Деньги", "Команда"]

    def make(cam, k):
        hgt = [0.0, 2.6, 2.6][k]
        sh = [1.0, 0.72, 0.72][k]
        S = 2.6
        corners = [(-S * sh, -S * sh, 0), (S * sh, -S * sh, 0), (S * sh, S * sh, 0), (-S * sh, S * sh, 0)]
        top = (0, 0, hgt)
        order = [2, 3, 1, 0]  # дальние грани раньше (z)
        objs = []
        for zi, i in enumerate(order):
            a, b = corners[i], corners[(i + 1) % 4]
            pts = [a, b, top]
            hot = k == 2 and i == 0
            base = pal["acc"] if hot else pal["paper"]
            col = face_col(cam, pts, base) if k else face_col(cam, [(0, 0, 0), (1, 0, 0), (1, 1, 0)], base)
            objs.append(poly(f"!!pf{i}", [cam.p(p) for p in pts], fill=col, ln=pal["bg"], lw=1.2, z=10 + zi))
            if k == 0:
                c = [(a[j] + b[j] + top[j]) / 3 for j in range(3)]
                px, py = cam.p(c)
                objs.append(label(f"pr{i}", px - 0.8, py - 0.17, 1.6, roles[i], sz=14, b=True, al="c",
                                  col=ink_on(theme, col), z=40))
        if k >= 1:
            px, py = cam.p(top)
            objs.append(label("ptop", px - 1.2, py - 0.65, 2.4, "Стратегия", sz=20, b=True, al="c",
                              col="accent" if k == 2 else "ink", z=40))
        return objs

    cam = fitcam(iso(0, 0, 1, yaw=30, pitch=32), make, [0, 1], (5.6, 1.2, 6.6, 5.5))
    heads = [head("Четыре опоры", "плоский лист"), head("Сходятся в вершину", "лист складывается"),
             head("Начинаем с клиента", "передняя грань")]
    return Variant(FAM, "pyramid_sheet", "Лист складывается в пирамиду",
                   "Квадратный лист из четырёх треугольников-опор: центр поднимается, углы сходятся — получается "
                   "пирамида с вершиной «Стратегия», грани освещены по-разному. Роль: «всё сходится к одной цели».",
                   [Slide(heads[k] + make(cam, k), dur=850) for k in range(3)], tags=["fold", "pyramid", "3d"], score=4)


# ----------------------------------------------------------------------------- 7. бумажный самолётик

def plane_faces(k):
    """Лист 4 панели (левое крыло, левый борт, правый борт, правое крыло). k=0 — лист, 1 — самолётик, 2 — в полёте."""
    if k == 0:
        L, Hh = 4.0, 2.8
        xs = [-Hh, -Hh / 2, 0, Hh / 2, Hh]
        P = [[(xs[i], 0, 0), (xs[i + 1], 0, 0), (xs[i + 1], L, 0), (xs[i], L, 0)] for i in range(4)]
        return P
    nose, tail = (0, 4.2, 0.0), (0, 0, 0.0)
    keel_t, keel_n = (0, 0, -0.9), (0, 3.6, -0.15)
    wl_t, wr_t = (-1.9, 0, 0.15), (1.9, 0, 0.15)
    P = [[wl_t, tail, nose, nose], [tail, keel_t, keel_n, nose], [keel_t, tail, nose, keel_n], [tail, wr_t, nose, nose]]
    return P


def v_plane(theme):
    pal = _pal(theme)

    def make(cam, k):
        objs = []
        fs = plane_faces(min(k, 1))
        off = (0, 0, 0) if k < 2 else (4.6, 4.0, 3.2)
        scl = 1.0 if k < 2 else 0.5
        order = [1, 2, 0, 3] if k else [0, 1, 2, 3]
        for zi, i in enumerate(order):
            pts = [(p[0] * scl + off[0], p[1] * scl + off[1], p[2] * scl + off[2]) for p in fs[i]]
            base = pal["paper"] if i in (0, 3) else pal["paper2"]
            objs.append(paper(f"!!pp{i}", cam, pts, base, pal["grey"], 10 + zi, edge=pal["bg"], ew=1.0))
        if k == 0:
            c = cam.p((0, 2.0, 0))
            objs.append(label("ptx", c[0] - 1.6, c[1] - 0.3, 3.2, "Заявка", sz=26, b=True, al="c",
                              col=ink_on(theme, objs[0].fill), z=40))
        if k == 2:
            a = cam.p((0.6, 1.4, 0.4))
            b = cam.p((4.6, 4.0 + 1.0, 3.2))
            objs.append(O("trail", "line", a[0], a[1], b[0] - a[0] - 0.4, b[1] - a[1] + 0.4, ln="accent", lw=2,
                          dash="dash", z=5))
        return objs

    cam = fitcam(iso(0, 0, 1, yaw=-30 + 60, pitch=30), make, [0, 1, 2], (5.4, 1.2, 7.2, 5.6))
    heads = [head("Заявка готова", "лист"), head("Складываем", "проверка пройдена"), head("Отправлено", "летит к банку")]
    return Variant(FAM, "paper_plane", "Лист → самолётик → полёт",
                   "Лист из четырёх панелей складывается в бумажный самолётик (борта и крылья — свои грани и свет), затем "
                   "он уменьшается и улетает вверх-вправо по пунктиру. Роль: «отправили», запуск, подача заявки.",
                   [Slide(heads[k] + make(cam, k), dur=850) for k in range(3)], tags=["fold", "origami", "flight"],
                   score=4)


# ----------------------------------------------------------------------------- 8. карта: сложена → гармошка → разложена

def map_panels(cols=3, rows=2, pw=2.4, ph=2.2, ang=0.0, stack=False):
    """Карта cols×rows; ang — угол гармошки по x (0 — плоско), stack — совсем сложена."""
    out = []
    a = math.radians(ang)
    for r in range(rows):
        for c in range(cols):
            if stack:
                x0 = 0.0
                z = (c + r * cols) * 0.04
                pts = [(x0, r * 0, z), (x0 + pw, 0, z), (x0 + pw, ph, z), (x0, ph, z)]
            else:
                x0 = c * pw * math.cos(a)
                x1 = (c + 1) * pw * math.cos(a)
                z0 = (0 if c % 2 == 0 else pw * math.sin(a))
                z1 = (pw * math.sin(a) if c % 2 == 0 else 0)
                y0 = r * ph if ang < 89 else 0
                pts = [(x0, y0, z0), (x1, y0, z1), (x1, y0 + ph, z1), (x0, y0 + ph, z0)]
            out.append(pts)
    return out


def v_map(theme):
    pal = _pal(theme)

    def make(cam, k):
        objs = []
        if k == 0:
            ps = map_panels(stack=True)
        elif k == 1:
            ps = map_panels(ang=50)
        else:
            ps = map_panels(ang=0)
        for i, pts in enumerate(ps):
            base = pal["paper"] if (i % 2 == 0) else pal["paper2"]
            objs.append(paper(f"!!mp{i}", cam, pts, base, pal["grey"], 10 + i, edge=pal["bg"]))
        if k == 2:
            route = [(0.5, 0.6), (2.0, 1.6), (3.6, 1.1), (5.0, 3.0), (6.5, 3.6)]
            pr = [cam.p((x, y, 0.02)) for x, y in route]
            for j in range(len(pr) - 1):
                a, b = pr[j], pr[j + 1]
                objs.append(O(f"rt{j}", "line", a[0], a[1], b[0] - a[0], b[1] - a[1], ln="accent", lw=3, z=40))
            for j in (0, len(pr) - 1):
                objs.append(O(f"pin{j}", "oval", pr[j][0] - 0.14, pr[j][1] - 0.14, 0.28, 0.28, fill="accent", z=41))
            objs.append(label("rlab", pr[-1][0] + 0.25, pr[-1][1] - 0.45, 2.0, "Цель", sz=18, b=True,
                              col=ink_on(theme, objs[0].fill), z=42))
        return objs

    cam = fitcam(iso(0, 0, 1, yaw=15, pitch=50), make, [0, 1, 2], (5.6, 1.2, 7.0, 5.6))
    heads = [head("Карта проекта", "сложена"), head("Раскрываем", "гармошкой"), head("Маршрут", "от старта к цели")]
    return Variant(FAM, "map_unfold", "Карта раскладывается",
                   "Сложенная карта раскрывается гармошкой (светлые/тёмные панели по свету), затем ложится плоско, и "
                   "по ней проходит маршрут с метками. Роль: дорожная карта проекта, «план на местности».",
                   [Slide(heads[k] + make(cam, k), dur=900) for k in range(3)], tags=["fold", "map", "roadmap"], score=4)


# ----------------------------------------------------------------------------- 9. ширма из панелей

def v_screen(theme):
    pal = _pal(theme)
    words = ["Быстро", "Просто", "Надёжно", "Честно"]

    def make(cam, k):
        ang = [80, 35, 0][k]
        objs = []
        w, h = 2.0, 3.6
        a = math.radians(ang)
        x = 0.0
        for i in range(4):
            y0 = 0.0 if i % 2 == 0 else w * math.sin(a)
            y1 = w * math.sin(a) if i % 2 == 0 else 0.0
            x1 = x + w * math.cos(a)
            pts = [(x, y0, 0), (x1, y1, 0), (x1, y1, h), (x, y0, h)]
            base = pal["acc"] if (k == 2 and i == 0) else pal["paper"]
            objs.append(paper(f"!!sc{i}", cam, pts, base, pal["paper2"], 10 + i, edge=pal["bg"]))
            if k == 2:
                px, py = cam.p(((x + x1) / 2, 0, h / 2))
                objs.append(label(f"sw{i}", px - 0.9, py - 0.22, 1.8, words[i], sz=19, b=True, al="c",
                                  col=ink_on(theme, objs[-1].fill), z=40))
            x = x1
        return objs

    cam = fitcam(Cam3(0, 0, 1, yaw=0, pitch=12, dist=24), make, [2], (5.6, 1.4, 7.0, 5.2))
    heads = [head("Наши принципы", "ширма сложена"), head("Раскрываем", "панели расходятся"),
             head("Четыре принципа", "первый — главный")]
    return Variant(FAM, "folding_screen", "Ширма раскрывается",
                   "Стоячая ширма из четырёх панелей: сложенная почти ребром, затем зигзагом, затем плоско с "
                   "надписями. Роль: ценности/принципы, раскрытие списка «по одной створке».",
                   [Slide(heads[k] + make(cam, k), dur=850) for k in range(3)], tags=["fold", "zigzag", "reveal"], score=3)


# ----------------------------------------------------------------------------- SEQ 1. письмо клиенту

def v_seq_letter(theme):
    pal = _pal(theme)
    cam = Cam3(6.6, 6.2, 1.0, yaw=0, pitch=8, dist=30)
    flat = Cam3(0, 0, 1, yaw=0, pitch=0.01)

    def letter_panels(cam_, x0, z0, w, h, fold):
        """Письмо втрое: fold=0 — плоско, 1 — сложено (верх и низ на средней трети)."""
        t = h / 3
        mid = [(x0, 0, z0 + t), (x0 + w, 0, z0 + t), (x0 + w, 0, z0 + 2 * t), (x0, 0, z0 + 2 * t)]
        top = [(x0, 0, z0 + 2 * t), (x0 + w, 0, z0 + 2 * t), (x0 + w, 0, z0 + 3 * t), (x0, 0, z0 + 3 * t)]
        bot = [(x0, 0, z0), (x0 + w, 0, z0), (x0 + w, 0, z0 + t), (x0, 0, z0 + t)]
        a = 178 * fold
        top = [rot(p, (x0, 0, z0 + 2 * t), (1, 0, 0), a) for p in top]
        bot = [rot(p, (x0, 0, z0 + t), (1, 0, 0), a) for p in bot]
        return bot, mid, top

    slides = []
    # 1-3: конверт, клапан, письмо (сложенное втрое) выходит
    for k, (fo, up, h1, s1) in enumerate([(0, 0, "Письмо клиенту", "один конверт"), (180, 0, "Открываем", "клапан вверх"),
                                           (180, 2.2, "Внутри", "сложено втрое")]):
        objs, letter = envelope(pal, cam, k, flap_open=fo, letter_up=up)
        objs = [o for o in objs if o.name != "!!evl"]
        lw, lh = 4.5, 2.75
        bot, mid, top = letter_panels(cam, 0.25, 0.12 + up, lw, lh, 1.0)
        for nm, pts, zz in (("b", bot, 12), ("m", mid, 12), ("t", top, 12)):
            objs.append(paper(f"!!lp{nm}", cam, pts, pal["paper"], pal["paper2"], 12 + {"b": 0.1, "m": 0.0, "t": 0.2}[nm],
                              edge=pal["bg"]))
        slides.append(Slide(head(h1, s1) + objs, dur=850))
    # 4: письмо выходит вперёд и раскладывается втрое (конверт уходит вниз и тускнеет)
    env_low, _ = envelope(pal, cam, 3, flap_open=180, letter_up=0, fly=(0.0, -4.4))
    env_low = [o.copy(fa=0.0, la=0.0) for o in env_low if o.name != "!!evl"]
    fcam = Cam3(7.4, 6.4, 1.0, yaw=0, pitch=0.01)
    bot, mid, top = letter_panels(fcam, -2.9, 0.0, 5.8, 5.0, 0.0)
    pan = []
    for nm, pts in (("b", bot), ("m", mid), ("t", top)):
        pan.append(paper(f"!!lp{nm}", fcam, pts, pal["paper"], pal["paper2"], 12 + {"b": 1, "m": 0, "t": 2}[nm],
                         edge=pal["bg"]))
    texts = ["Здравствуйте, Анна!", "Ваш тариф обновлён", "Скидка 20% до мая"]
    tx = [label(f"lt{j}", 4.8, 1.85 + j * 1.67, 5.2, t, sz=22, b=j == 0, col=ink_on(theme, pal["paper"]), z=40)
          for j, t in enumerate(texts)]
    slides.append(Slide(head("Три мысли", "письмо разложено") + env_low + pan + tx, dur=900))
    # 5: трети расходятся карточками в ряд (каждая — отдельная мысль)
    cards = []
    for j, nm in enumerate(("t", "m", "b")):
        x = 0.9 + j * 4.15
        pts = [(x, 5.4), (x + 3.8, 5.4), (x + 3.8, 2.6), (x, 2.6)]  # тот же обход, что у панели письма (НЛ, НП, ВП, ВЛ)
        col = pal["acc"] if j == 2 else pal["paper"]
        cards.append(poly(f"!!lp{nm}", pts, fill=col, ln=pal["bg"], lw=0.6, z=12 + j))
        cards.append(label(f"lc{j}", x + 0.3, 3.6, 3.3, ["Приветствие", "Новость", "Оффер"][j], sz=22, b=True, al="c",
                           col=ink_on(theme, col), z=40))
    slides.append(Slide(head("Каждая треть — роль", "приветствие, новость, оффер") + env_low + cards, dur=900))
    # 6: обратно в письмо и в конверт — отправка (конверт уменьшается и улетает вправо вверх)
    objs, letter = envelope(pal, cam, 5, flap_open=0, letter_up=0, fly=(3.0, 2.2), scale=0.55)
    objs = [o for o in objs if o.name != "!!evl"]
    bot, mid, top = letter_panels(cam, 3.0 + 0.14, 2.2 + 0.07, 4.5 * 0.55, 2.75 * 0.55, 1.0)
    for nm, pts in (("b", bot), ("m", mid), ("t", top)):
        objs.append(paper(f"!!lp{nm}", cam, pts, pal["paper"], pal["paper2"], 12, edge=pal["bg"], fa=0.0))
    objs = [o.copy(x=o.x, y=o.y) for o in objs]
    small = []
    for o in objs:  # уменьшение конверта: масштаб рамки относительно её центра не нужен — меняем точки
        small.append(o)
    slides.append(Slide(head("Отправлено", "сегодня в 10:00") + small, dur=900))
    return Variant(FAM, "seq_letter", "Письмо: конверт → три мысли → отправка",
                   "Один конверт и письмо живут 6 слайдов: закрытый конверт → клапан откидывается → письмо, сложенное "
                   "втрое, выходит → письмо выходит вперёд и раскладывается на три трети с текстом → трети расходятся "
                   "карточками «приветствие / новость / оффер» → письмо снова в конверте, конверт уезжает вверх-вправо "
                   "(отправлено). Роль: CRM-рассылка, коммуникация, «как устроено сообщение».",
                   slides, tags=["fold", "seq", "envelope", "paper"], score=4)


# ----------------------------------------------------------------------------- SEQ 2. карта проекта: сложена → маршрут → объём → снова книжка

def v_seq_map(theme):
    pal = _pal(theme)
    route = [(0.5, 0.6), (2.0, 1.6), (3.6, 1.1), (5.0, 3.0), (6.5, 3.6)]
    names = ["Старт", "Прототип", "Пилот", "Запуск", "Рост"]
    vals = [0.4, 1.0, 1.6, 2.6, 3.6]

    def panels(cam, ps, hot=None):
        out = []
        for i, pts in enumerate(ps):
            base = pal["paper"] if (i % 2 == 0) else pal["paper2"]
            out.append(paper(f"!!mp{i}", cam, pts, base, pal["grey"], 10 + i, edge=pal["bg"]))
        return out

    def route_objs(cam, k, pillars=False, labels=True, upto=5):
        out = []
        pr = [cam.p((x, y, 0.02)) for x, y in route]
        for j in range(4):
            a, b = pr[j], pr[j + 1]
            on = j < upto - 1
            out.append(O(f"!!rt{j}", "line", a[0], a[1], b[0] - a[0], b[1] - a[1], ln="accent", lw=3, z=40,
                         la=1.0 if on else 0.0))
        for j, (x, y) in enumerate(route):
            h = vals[j] if pillars else 0.0
            from lab._c_util import box
            out += box(f"!!pl{j}", cam, x - 0.22, y - 0.22, 0.0, 0.44, 0.44, h, pal["acc"] if j <= upto - 1 else pal["grey"],
                       z=50 + j * 4, edge=pal["bg"], fa=0.0 if upto == 0 else 1.0)
            if labels:
                px, py = cam.p((x + 0.3, y, h))
                out.append(label(f"rn{k}_{j}", px + 0.1, py - 0.38, 1.6, names[j], sz=14, b=j == upto - 1,
                                 col=ink_on(theme, pal["paper"]) if not pillars else "ink", z=70))
        return out

    base = iso(0, 0, 1, yaw=15, pitch=50)
    probe = lambda c, k: panels(c, map_panels(ang=0))  # noqa: E731
    cam = fitcam(base, probe, [0], (5.4, 1.2, 7.2, 5.6))
    cam_iso = fitcam(iso(0, 0, 1, yaw=30, pitch=30), lambda c, k: panels(c, map_panels(ang=0)) + route_objs(c, 0, True, False),
                     [0], (5.2, 1.2, 7.4, 5.6))
    cam_top = fitcam(Cam3(0, 0, 1, yaw=0, pitch=89.9), probe, [0], (5.6, 1.2, 7.0, 5.4))
    slides = [
        Slide(head("Карта проекта", "сложена") + panels(cam, map_panels(stack=True)) + route_objs(cam, 0, labels=False, upto=0),
              dur=900),
        Slide(head("Раскрываем", "гармошкой") + panels(cam, map_panels(ang=50)) + route_objs(cam, 1, labels=False, upto=0),
              dur=900),
        Slide(head("Маршрут", "пять остановок") + panels(cam, map_panels(ang=0)) + route_objs(cam, 2, upto=1), dur=900),
        Slide(head("Мы здесь", "третья остановка") + panels(cam, map_panels(ang=0)) + route_objs(cam, 3, upto=3), dur=800),
        Slide(head("Вложения по этапам", "столбики на карте") + panels(cam_iso, map_panels(ang=0)) +
              route_objs(cam_iso, 4, pillars=True, labels=True, upto=5), dur=900),
        Slide(head("Вид сверху", "весь путь") + panels(cam_top, map_panels(ang=0)) + route_objs(cam_top, 5, upto=5), dur=900),
        Slide(head("Сложили", "до следующего квартала") + panels(cam, map_panels(stack=True)) +
              route_objs(cam, 6, labels=False, upto=0), dur=900),
    ]
    return Variant(FAM, "seq_map", "Карта проекта: от сгиба до объёма",
                   "Одна карта живёт 7 слайдов: сложена → раскрывается гармошкой → ложится плоско, появляется маршрут → "
                   "маршрут прорисован до «мы здесь» → камера наклоняется в изометрию, на остановках вырастают столбики "
                   "вложений → вид строго сверху → карта снова складывается. Роль: сквозная дорожная карта колоды.",
                   slides, tags=["fold", "seq", "map", "camera", "data"], score=4)


def variants(theme) -> list[Variant]:
    from lab._c_util import ensure_contrast
    return ensure_contrast(theme, [f(theme) for f in (v_booklet, v_accordion, v_curl, v_envelope, v_fan, v_pyramid_sheet, v_plane, v_map,
                               v_screen, v_seq_letter, v_seq_map)])
