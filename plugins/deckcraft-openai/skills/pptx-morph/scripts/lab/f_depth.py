"""Семейство «Глубина»: параллакс, полёт камеры сквозь слои, пол с точкой схода, тоннель, уход вдаль.

Перспектива считается вручную: точка (x вправо, y вглубь, z вверх) -> экран через «глаз» E и фокус f:
X = cx + f·(x − Ex)/(y − Ey), Y = cy − f·(z − Ez)/(y − Ey). Полёт камеры = другой глаз E на соседнем слайде;
все формы (рамки, плитки пола, карточки) — свободные формы из спроецированных вершин, поэтому Morph ведёт их как
одну сцену. То, что «проехали», уходит за край крупным и гаснет; то, что далеко, темнеет к цвету фона (туман).
Параллакс — штатный мир-холст morphkit (world=True, Slide.cam, meta parallax).
"""

from __future__ import annotations

import math
import random

from morphkit import Cam, O, Slide
from morphkit import vector as V
from morphkit.theme import SLIDE_H, SLIDE_W, mix

from lab import Variant
from lab._c_util import Cam3, boxes, face_col, fitcam, head, ink_on, label, poly

FAM = "depth"


def _pal(theme):
    ink2, bg = theme.c("ink2"), theme.c("bg")
    return {"grey": mix(ink2, bg, 0.45), "grey2": mix(ink2, bg, 0.62), "grey3": mix(ink2, bg, 0.30),
            "acc": theme.c("accent"), "acc3": theme.c("accent3"), "acc2": theme.c("accent2"), "bg": bg,
            "ink": theme.c("ink"), "line": theme.c("line"), "floor": mix(theme.c("surface2"), ink2, 0.10)}


class Eye:
    """Глаз перспективы: положение (ex, ey, ez), фокус f (дюймы), центр схода (cx, cy)."""

    def __init__(self, ex=0.0, ey=0.0, ez=0.0, f=6.0, cx=SLIDE_W / 2, cy=SLIDE_H / 2, near=0.35):
        self.ex, self.ey, self.ez, self.f, self.cx, self.cy, self.near = ex, ey, ez, f, cx, cy, near

    def d(self, p):
        return p[1] - self.ey

    def p(self, p):
        d = max(p[1] - self.ey, self.near)
        return self.cx + self.f * (p[0] - self.ex) / d, self.cy - self.f * (p[2] - self.ez) / d

    def k(self, y):
        return self.f / max(y - self.ey, self.near)

    def place(self, sx, sy, y):
        """Мировые (x, z) точки, которая на глубине y попадёт в точку экрана (sx, sy)."""
        d = max(y - self.ey, self.near)
        return self.ex + (sx - self.cx) * d / self.f, self.ez + (self.cy - sy) * d / self.f


def fog(col, bg, d, d0=3.0, d1=16.0, mx=0.85):
    t = min(mx, max(0.0, (d - d0) / (d1 - d0)) * mx)
    return mix(col, bg, t)


def frame_poly(name, eye, x, y, z, w, h, t, col, fa=1.0, zz=10, **kw):
    """Рамка (прямоугольник с одной дыркой) в плоскости y=const: центр (x, z), ширина w, высота h, толщина t."""
    o = [eye.p((x - w / 2, y, z + h / 2)), eye.p((x + w / 2, y, z + h / 2)), eye.p((x + w / 2, y, z - h / 2)),
         eye.p((x - w / 2, y, z - h / 2))]
    i = [eye.p((x - w / 2 + t, y, z + h / 2 - t)), eye.p((x + w / 2 - t, y, z + h / 2 - t)),
         eye.p((x + w / 2 - t, y, z - h / 2 + t)), eye.p((x - w / 2 + t, y, z - h / 2 + t))]
    g = V.Polygon(o, [i])
    return V.shape(name, g, frame=(-2.0, -2.0, SLIDE_W + 4.0, SLIDE_H + 4.0), fill=col, fa=fa, z=zz,
                   meta={"bleed": True, **kw.pop("meta", {})}, **kw)


def quad(name, eye, pts3, col, fa=1.0, zz=10, **kw):
    return poly(name, [eye.p(p) for p in pts3], fill=col, fa=fa, z=zz, meta={"bleed": True}, **kw)


def tlabel(name, eye, x, y, z, txt, sz0, col="ink", al="l", w0=3.0, b=True, zz=60, alpha_hidden=False):
    """Подпись в плоскости сцены: кегль и рамка масштабируются с глубиной; мелкая — текстура (не текст)."""
    k = 5.0 / max(y - eye.ey, eye.near)  # 1 на глубине 5
    sz = sz0 * k
    px, py = eye.p((x, y, z))
    w = w0 * k
    meta = {"texture": True} if sz < 13 else {}
    return O(name, "text", px if al == "l" else px - w / 2, py, w, sz / 72 * 1.3, txt=txt, sz=max(sz, 1.0), b=b, col=col,
             al=al, z=zz, meta={**meta, "bleed": True, "overlap_ok": sz < 13})


# ----------------------------------------------------------------------------- 1. полёт сквозь рамки

LEVELS = ["Рынок", "Компания", "Отдел", "Команда", "Человек"]


def dive_scene(theme, pal, eye, cur, prefix="fr", labels=True):
    objs = []
    for i, t in enumerate(LEVELS):
        y = 5.0 + i * 3.0
        d = eye.d((0, y, 0))
        if d < 2.5:  # проехали: рамка разлетается за край и гаснет
            e2 = Eye(eye.ex, y - 0.6, eye.ez, eye.f, eye.cx, eye.cy)
            objs.append(frame_poly(f"!!{prefix}{i}", e2, 0, y, 0, 7.0, 4.2, 0.3, pal["grey"], fa=0.0, zz=100 - i))
            continue
        hot = i == cur
        col = fog(pal["acc"] if hot else pal["grey"], pal["bg"], d, 3.5, 18)
        objs.append(frame_poly(f"!!{prefix}{i}", eye, 0, y, 0, 7.0, 4.2, 0.3, col, zz=100 - i))
        if labels and 3.0 < d < 10:
            tc = "accent" if hot else "ink2"
            objs.append(tlabel(f"!!{prefix}t{i}", eye, -3.25, y, 1.75, t, 30, col=tc, zz=150 - i))
    return objs


def v_dive(theme):
    pal = _pal(theme)
    slides = []
    subs = ["самый широкий план", "внутри рынка", "ещё глубже", "где решают"]
    for k in range(4):
        eye = Eye(0, k * 3.0, 0, f=6.0, cx=SLIDE_W / 2 + 0.9, cy=SLIDE_H / 2 + 0.45)
        objs = dive_scene(theme, pal, eye, cur=k)
        slides.append(Slide(head(f"Уровень {k + 1}", subs[k], y=0.35) + objs, dur=900))
    return Variant(FAM, "dive_frames", "Полёт сквозь рамки уровней",
                   "Рамки уровней стоят друг за другом в перспективе; клик — камера пролетает сквозь ближнюю рамку "
                   "(она уходит за края крупной и гаснет), следующая выходит вперёд и загорается. Роль: «ныряем глубже» — "
                   "от рынка к человеку, уровни детализации.",
                   slides[:3], tags=["depth", "camera", "dive", "levels"], score=5)


# ----------------------------------------------------------------------------- 2. параллакс: три плана (мир-холст)

def v_parallax(theme):
    pal = _pal(theme)
    rnd = random.Random(3)
    far, mid, near = [], [], []
    for i in range(40):  # дальний план: россыпь точек
        x, y, s = rnd.uniform(-2, 30), rnd.uniform(0.5, 7), rnd.uniform(0.05, 0.14)
        far.append(O(f"!!pf{i}", "oval", x, y, s, s, fill=pal["grey2"], fa=0.8, world=True, z=1, meta={"parallax": 0.25}))
    ridge = [(-4, 7.6)] + [(x * 0.8 - 4, 5.2 + 0.9 * math.sin(x * 0.7) + 0.4 * math.sin(x * 1.9)) for x in range(46)] + [
        (32.8, 7.6)]
    mid.append(poly("!!ridge", ridge, fill=pal["grey3"], fa=0.55, frame=None, world=True, z=2,
                    meta={"parallax": 0.55, "bleed": True}))
    years = ["2022", "2023", "2024", "2025", "2026"]
    facts = ["старт", "первый клиент", "100 клиентов", "выход на рынок", "сеть партнёров"]
    for i, (yy, ft) in enumerate(zip(years, facts)):
        x = 2.0 + i * 5.5
        near.append(O(f"!!pn{i}", "oval", x - 0.18, 4.42, 0.36, 0.36, fill="accent", world=True, z=20))
        near.append(O(f"!!pyr{i}", "text", x - 1.2, 3.2, 2.4, 0.9, txt=yy, sz=40, b=True, col="ink", al="c", world=True,
                      z=21))
        near.append(O(f"!!pft{i}", "text", x - 1.4, 4.95, 2.8, 0.5, txt=ft, sz=18, col="ink2", al="c", world=True, z=21))
    near.append(O("!!axis", "line", -2, 4.6, 34, 0, ln="line", lw=1.5, world=True, z=10))
    objs = far + mid + near
    cams = [Cam(5.0, 3.75, 1.0), Cam(12.5, 3.75, 1.0), Cam(21.0, 3.75, 1.0)]
    heads = [head("Как мы росли", "первые два года"), head("Середина пути", "сотня клиентов"), head("Сейчас", "рынок и партнёры")]
    hh = [[o.copy(z=80) for o in h] for h in heads]
    return Variant(FAM, "parallax_time", "Параллакс: лента времени",
                   "Мир-холст с тремя планами: дальняя россыпь точек (parallax 0,25), гряда (0,55) и лента лет "
                   "(1,0). Камера едет вправо — планы сдвигаются с разной скоростью, появляется глубина. Роль: история, "
                   "таймлайн, «путь».", [Slide(hh[k] + objs, cam=cams[k], dur=900) for k in range(3)],
                   tags=["depth", "parallax", "world", "timeline"], score=4)


# ----------------------------------------------------------------------------- 3. пол с точкой схода, камера едет вперёд

def floor_grid(pal, eye, prefix="gr", n=9, depth=(2.0, 30.0), x0=-8, x1=8, step=2.0, floor_z=-1.6, lw=0.025):
    out = []
    for j in range(n):  # продольные линии к точке схода
        x = x0 + j * (x1 - x0) / (n - 1)
        a, b = eye.p((x, max(depth[0], eye.ey + 0.6), floor_z)), eye.p((x, depth[1], floor_z))
        out.append(_seg(f"!!{prefix}v{j}", a, b, lw * 2.2, pal["line"], 0.8))
    m = int((depth[1] - depth[0]) / step)
    for i in range(m):  # поперечные: «едут» навстречу при движении камеры
        y = depth[0] + i * step
        d = y - eye.ey
        fa = 0.0 if d < 0.6 else min(0.8, max(0.15, 1.0 - d / (depth[1] - depth[0] + 2)))
        yy = max(y, eye.ey + 0.6)
        a, b = eye.p((x0, yy, floor_z)), eye.p((x1, yy, floor_z))
        out.append(_seg(f"!!{prefix}h{i}", a, b, lw * 2.2, pal["line"], fa))
    return out


def _seg(name, a, b, w, col, fa, z=3):
    (x0, y0), (x1, y1) = a, b
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1e-3
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    return poly(name, [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], fill=col, fa=fa, z=z,
                frame=(-2.0, -2.0, SLIDE_W + 4.0, SLIDE_H + 4.0), meta={"bleed": True, "decor": True})


def v_floor(theme):
    pal = _pal(theme)
    items = [("Идея", 5.0, -2.2), ("Прототип", 9.0, 2.6), ("Пилот", 13.0, -2.6), ("Запуск", 17.0, 2.2),
             ("Рост", 21.0, -1.8)]

    def scene(eye, cur):
        objs = floor_grid(pal, eye)
        for i, (t, y, x) in enumerate(items):
            d = y - eye.ey
            hot = i == cur
            base = pal["acc"] if hot else pal["grey"]
            col = fog(base, pal["bg"], d, 3, 20)
            fa = 0.0 if d < 0.8 else 1.0
            yy = max(y, eye.ey + 0.8)
            # стоячая карточка 2.4 × 1.6 на полу
            pts = [(x - 1.2, yy, 0.0), (x + 1.2, yy, 0.0), (x + 1.2, yy, -1.6), (x - 1.2, yy, -1.6)]
            objs.append(quad(f"!!cd{i}", eye, pts, col, fa=fa, zz=40 - i))
            sh = [(x - 1.2, yy, -1.6), (x + 1.2, yy, -1.6), (x + 1.5, yy + 0.8, -1.6), (x - 0.9, yy + 0.8, -1.6)]
            objs.append(quad(f"!!cs{i}", eye, sh, mix(pal["floor"], "000000", 0.3), fa=fa * 0.8, zz=20 - i))
            if fa > 0 and d < 12:
                lab = tlabel(f"!!ct{i}", eye, x, yy, -0.55, t, 26, col=ink_on(theme, col),
                             al="c", w0=2.3, zz=60 - i)
                objs.append(lab)
        return objs

    slides = []
    hs = [head("Путь продукта", "пять вех"), head("Шаг второй", "проезжаем идею"), head("Шаг третий", "ближе к рынку")]
    for k in range(3):
        eye = Eye(0, k * 4.0, 0.9, f=5.2, cx=SLIDE_W / 2, cy=2.7)
        slides.append(Slide(hs[k] + scene(eye, k), dur=900))
    return Variant(FAM, "floor_road", "Дорога вех на полу с точкой схода",
                   "Перспективный пол с сеткой к точке схода, на нём стоят карточки-вехи. Клик — камера едет вперёд: "
                   "поперечные линии бегут навстречу, ближняя веха уходит за край, следующая растёт и горит. "
                   "Роль: дорожная карта «в пространстве», продвижение по плану.",
                   slides, tags=["depth", "floor", "perspective", "roadmap"], score=4)


# ----------------------------------------------------------------------------- 4. тоннель колец

def v_tunnel(theme):
    pal = _pal(theme)
    stages = ["Запрос", "Очередь", "Обработка", "Ответ"]

    def scene(eye, cur):
        objs = []
        for i in range(10):
            y = 3.0 + i * 2.2
            d = y - eye.ey
            hot = (i % 3 == 0) and (i // 3 == cur)
            col = fog(pal["acc"] if hot else pal["grey"], pal["bg"], d, 2.5, 22, 0.9)
            fa = 0.0 if d < 0.7 else 1.0
            yy = max(y, eye.ey + 0.7)
            k = eye.k(yy)
            cx, cy = eye.p((0, yy, 0))
            r = 2.6 * k
            g = V.subtract(V.circle(cx, cy, r, 24), V.circle(cx, cy, r * 0.9, 24))
            objs.append(V.shape(f"!!tr{i}", g, frame=(-2.0, -2.0, SLIDE_W + 4.0, SLIDE_H + 4.0), fill=col, fa=fa,
                                z=50 - i, meta={"bleed": True}))
            if i % 3 == 0 and fa > 0:
                j = i // 3
                objs.append(tlabel(f"!!tt{j}", eye, 0, yy, 2.6 * 0.62, stages[j], 15, al="c", w0=2.4,
                                   col="accent" if j == cur else ("ink2" if d < 10 else "muted"), zz=70 - i))
        # пакет летит по оси тоннеля к следующему кольцу
        px, py = eye.p((0, eye.ey + 2.4, -0.2))
        objs.append(O("!!pk", "oval", px - 0.22, py - 0.22, 0.44, 0.44, fill="accent", z=90))
        return objs

    slides = []
    for k in range(3):
        eye = Eye(0, k * 6.6, 0, f=3.6, cx=SLIDE_W / 2 + 1.4, cy=SLIDE_H / 2 + 0.2)
        slides.append(Slide(head(["Путь запроса", "Дальше по тоннелю", "Внутри системы"][k], f"этап {k + 1} из 4") + scene(eye, k),
                            dur=900))
    return Variant(FAM, "tunnel", "Тоннель колец",
                   "Кольца уходят в точку схода; камера летит по тоннелю на три кольца за клик, кольца-этапы с "
                   "подписями проходят мимо, акцентное кольцо — текущий этап. Роль: путь запроса, конвейер, «внутрь системы».",
                   slides, tags=["depth", "tunnel", "camera", "process"], score=4)


# ----------------------------------------------------------------------------- 5. очередь уходит вдаль

def v_recede(theme):
    pal = _pal(theme)
    weeks = ["Неделя 1", "Неделя 2", "Неделя 3", "Неделя 4", "Неделя 5", "Неделя 6"]

    def scene(cur):
        objs = []
        eye = Eye(0, 0, 0.0, f=5.0, cx=6.6, cy=3.8)
        for i, t in enumerate(weeks):
            rel = cur - i  # 0 — текущая (впереди), >0 — прошлые (вдали), <0 — будущие (ещё не пришли)
            if rel < 0:  # будущая: ждёт слева-спереди, прозрачная
                y, fa = 3.0, 0.0
                x, zc = eye.place(2.2, 4.6, y)
            else:
                y, fa = 4.0 + rel * 3.0, 1.0
                x, zc = eye.place(5.0 + rel * 1.55, 4.3 - rel * 0.62, y)
            col = fog(pal["acc"] if rel == 0 else pal["grey"], pal["bg"], y, 3.5, 20)
            pts = [(x - 1.6, y, zc + 1.0), (x + 1.6, y, zc + 1.0), (x + 1.6, y, zc - 1.0), (x - 1.6, y, zc - 1.0)]
            objs.append(quad(f"!!wk{i}", eye, pts, col, fa=fa, zz=60 - max(rel, 0) * 5))
            if fa > 0:
                if rel < 2:
                    objs.append(tlabel(f"!!wt{i}", eye, x, y, zc + 0.35, t, 24, al="c", w0=3.0, zz=61 - max(rel, 0) * 5,
                                       col=ink_on(theme, col)))
        return objs

    slides = [Slide(head(["Спринты", "Неделя вперёд", "Ещё одна"][k], "прошлое уходит вдаль") + scene(k + 2),
                    dur=850) for k in range(3)]
    return Variant(FAM, "recede", "Прошлое уходит вдаль",
                   "Текущая карточка спереди; при клике она отступает в глубину по диагонали (меньше и темнее) к прошлым, "
                   "новая выходит вперёд. Роль: спринты, хроника, лента событий — время как глубина.",
                   slides, tags=["depth", "queue", "time"], score=4)


# ----------------------------------------------------------------------------- 6. взрыв слоёв интерфейса

UI = [("Фон", 0), ("Панель", 1), ("Карточки", 2), ("Кнопка", 3)]


def ui_layers(theme, pal, cam: Cam3, spread: float, hot=None, prefix="ui", labels=True):
    """Слои макета экрана в плоскости x-z (фронтально), разнесённые по глубине y на spread."""
    objs = []
    rects = {0: [(-3.2, -2.0, 6.4, 4.0)], 1: [(-3.0, 1.2, 6.0, 0.6)],
             2: [(-2.8, -1.4, 1.7, 2.2), (-0.85, -1.4, 1.7, 2.2), (1.1, -1.4, 1.7, 2.2)], 3: [(1.3, -1.85, 1.5, 0.35)]}
    cols = {0: pal["grey3"], 1: pal["grey"], 2: pal["grey2"], 3: pal["acc"]}
    for lv, rs in rects.items():
        y = (3 - lv) * spread
        for j, (x, z, w, h) in enumerate(rs):
            pts = [(x, -y, z + h), (x + w, -y, z + h), (x + w, -y, z), (x, -y, z)]
            col = cols[lv] if hot in (None, lv) else mix(cols[lv], pal["bg"], 0.55)
            if hot == lv:
                col = pal["acc"] if lv != 3 else pal["acc3"]
            objs.append(poly(f"!!{prefix}{lv}_{j}", [cam.p(p) for p in pts], fill=col, ln=pal["bg"], lw=0.75,
                             z=10 + lv * 5 + j))
        if labels and spread > 0.3:
            corner = {0: (3.2, 2.0), 1: (3.0, 1.8), 2: (2.8, 0.8), 3: (2.8, -1.5)}[lv]
            px, py = cam.p((corner[0], -y, corner[1]))
            objs.append(label(f"!!{prefix}t{lv}", px + 0.12, py - 0.4, 1.8, UI[lv][0], sz=19, b=True,
                              col="accent" if hot == lv else "ink2", z=80))
    return objs


def v_ui(theme):
    pal = _pal(theme)
    flat = Cam3(8.6, 3.9, 0.9, yaw=0, pitch=0.01)
    tilt = fitcam(Cam3(0, 0, 1, yaw=38, pitch=24, dist=22), lambda c, k: ui_layers(theme, pal, c, 1.6, labels=False), [0],
                  (5.4, 1.4, 5.6, 5.3))
    slides = [Slide(head("Экран заказа", "как видит клиент") + ui_layers(theme, pal, flat, 0.0), dur=850),
              Slide(head("Четыре слоя", "разносим по глубине") + ui_layers(theme, pal, tilt, 1.6), dur=900),
              Slide(head("Слой карточек", "здесь вся логика") + ui_layers(theme, pal, tilt, 1.6, hot=2), dur=700)]
    return Variant(FAM, "ui_explode", "Экран раскладывается на слои",
                   "Плоский макет экрана поворачивается в перспективу и расслаивается по глубине: фон, панель, карточки, "
                   "кнопка; затем один слой подсвечен. Роль: устройство интерфейса, «из чего собран экран», дизайн-ревью.",
                   slides, tags=["depth", "layers", "ui", "explode", "camera"], score=5)


# ----------------------------------------------------------------------------- 7. сцена с прожектором

def v_stage(theme):
    pal = _pal(theme)
    eye = Eye(0, 0, 1.5, f=5.0, cx=SLIDE_W / 2 + 0.6, cy=2.6)
    who = ["Аналитик", "Дизайнер", "Инженер"]

    def scene(cur):
        objs = []
        fl = [(-6, 3.5, -1.5), (6, 3.5, -1.5), (6, 12, -1.5), (-6, 12, -1.5)]
        objs.append(quad("!!stage", eye, fl, pal["floor"], fa=0.85, zz=2))
        wall = [(-6, 12, -1.5), (6, 12, -1.5), (6, 12, 3.5), (-6, 12, 3.5)]
        objs.append(quad("!!wall", eye, wall, mix(pal["floor"], pal["bg"], 0.5), zz=1))
        for i, t in enumerate(who):
            x = -3.4 + i * 3.4
            y = 7.0
            col = pal["acc"] if i == cur else pal["grey"]
            body = [(x - 0.8, y, -1.5), (x + 0.8, y, -1.5), (x + 0.8, y, 0.6), (x - 0.8, y, 0.6)]
            objs.append(quad(f"!!pp{i}", eye, body, col if i == cur else fog(col, pal["bg"], 9, 3, 20), zz=20 + i))
            hx, hy = eye.p((x, y, 1.15))
            r = 0.5 * eye.k(y)
            objs.append(O(f"!!ph{i}", "oval", hx - r, hy - r, 2 * r, 2 * r, fill=col if i == cur else fog(col, pal["bg"], 9, 3, 20),
                          z=20 + i))
            lx, ly = eye.p((x, 4.2, -1.5))
            objs.append(label(f"!!pl{i}", lx - 1.0, ly + 0.08, 2.0, t, sz=16, b=i == cur, al="c",
                              col="accent" if i == cur else "ink2"))
        # луч прожектора: трапеция от верха к пятну на полу
        x = -3.4 + cur * 3.4
        top = [eye.p((x - 0.25, 7.0, 5.5)), eye.p((x + 0.25, 7.0, 5.5))]
        spot = [eye.p((x + 1.4, 7.0, -1.5)), eye.p((x - 1.4, 7.0, -1.5))]
        objs.append(poly("!!beam", top + spot, fill=pal["acc"], fa=0.16, z=15, meta={"decor": True, "bleed": True}))
        ell = V.ellipse((spot[0][0] + spot[1][0]) / 2, spot[0][1], abs(spot[0][0] - spot[1][0]) / 2, 0.28, 12)
        objs.append(V.shape("!!pool", ell, fill=pal["acc"], fa=0.28, z=16, meta={"decor": True}))
        return objs

    slides = [Slide(head(["Команда проекта", "Дизайн", "Разработка"][k], "кто ведёт этап", x=0.75) + scene(k), dur=800)
              for k in range(3)]
    return Variant(FAM, "stage_spot", "Сцена: прожектор на участнике",
                   "Перспективная сцена с задником; луч прожектора и пятно на полу переезжают от одной фигуры к другой, "
                   "фигура в луче загорается. Роль: представление команды, «кто отвечает за этап», роли.",
                   slides, tags=["depth", "spotlight", "stage", "people"], score=4)


# ----------------------------------------------------------------------------- 8. презентация карт в глубину

def v_deck(theme):
    pal = _pal(theme)
    cards = ["Цель", "Метрика", "Гипотеза", "Опыт", "Вывод", "Решение"]

    def scene(cur):
        eye = Eye(0, 0, 0.0, f=6.0, cx=8.4, cy=3.9)
        objs = []
        for i, t in enumerate(cards):
            rel = i - cur
            if rel < 0:  # сыгранная: улетает влево-вперёд крупной и гаснет
                y, fa = 2.6, 0.0
                x, z = eye.place(1.0, 4.4, y)
            else:
                y, fa = 5.0 + rel * 1.4, 1.0
                x, z = eye.place(8.4 + rel * 0.62, 3.9 - rel * 0.42, y)
            col = fog(pal["acc"] if rel == 0 else pal["grey"], pal["bg"], y, 4.5, 16)
            pts = [(x - 2.0, y, z + 1.3), (x + 2.0, y, z + 1.3), (x + 2.0, y, z - 1.3), (x - 2.0, y, z - 1.3)]
            objs.append(quad(f"!!dk{i}", eye, pts, col, fa=fa, zz=60 - max(rel, -1) * 4, ln=pal["bg"], lw=1.0))
            if rel == 0:
                objs.append(tlabel(f"dt{cur}", eye, x, y, z + 0.3, t, 34, al="c", w0=3.6, col=ink_on(theme, col), zz=80))
        return objs

    slides = [Slide(head(f"Карта {k + 1}", "презентация в глубину") + scene(k), dur=850) for k in range(3)]
    return Variant(FAM, "deck_depth", "Презентация карт в глубину",
                   "Карты стоят друг за другом в перспективе со сдвигом; верхняя улетает влево-вперёд и гаснет, вся "
                   "презентация делает шаг к зрителю. Роль: последовательный разбор (цель → метрика → гипотеза), пошаговый метод.",
                   slides, tags=["depth", "cards", "queue", "carousel"], score=4)


# ----------------------------------------------------------------------------- 9. проезд вдоль столбцов

def v_flyby(theme):
    pal = _pal(theme)
    vals = [2.0, 3.2, 2.6, 4.4, 3.8, 5.6, 4.9, 6.4]
    months = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг"]

    def scene(k):
        cam = Cam3(6.4 - k * 3.6, 6.2, 0.85, yaw=24, pitch=18, dist=16)
        specs = []
        for i, v in enumerate(vals):
            hot = i == 2 + 2 * k + 1
            specs.append(dict(n=f"!!fb{i}", x=i * 2.2, y=0, z=0, w=1.2, d=1.2, h=v * 0.72,
                              col=pal["acc"] if hot else pal["grey"]))
        objs = boxes(cam, specs, edge=pal["bg"])
        for i, m in enumerate(months):
            px, py = cam.p((i * 2.2 + 0.6, -0.4, 0))
            objs.append(label(f"!!fm{i}", px - 0.6, py + 0.05, 1.2, m, sz=14, al="c", col="ink2", meta={"bleed": True}))
        return objs

    slides = [Slide(head(["Весна", "Лето", "Конец лета"][k], "проезд вдоль месяцев") + scene(k), dur=900) for k in range(3)]
    return Variant(FAM, "flyby_bars", "Проезд камеры вдоль столбцов",
                   "Столбики-бруски в перспективе; камера скользит вдоль ряда (сдвиг сцены, перспектива пересчитана), "
                   "акцентный месяц меняется. Роль: длинный ряд данных, который не помещается целиком, «экскурсия по году».",
                   slides, tags=["depth", "camera", "data", "perspective"], score=3)


# ----------------------------------------------------------------------------- 10. коридор с дверями-разделами

def v_corridor(theme):
    pal = _pal(theme)
    doors = [("Продажи", -1, 5.0), ("Склад", 1, 8.0), ("Финансы", -1, 11.0), ("Кадры", 1, 14.0)]

    def scene(k):
        eye = Eye(0, k * 3.0, 0.2, f=4.6, cx=SLIDE_W / 2 + 0.8, cy=SLIDE_H / 2 + 0.2, near=0.5)
        objs = []
        Wd, Hc = 3.0, 2.4
        far = 30.0
        for nm, pts in {"fl": [(-Wd, 0, -1.4), (Wd, 0, -1.4), (Wd, far, -1.4), (-Wd, far, -1.4)],
                        "lw": [(-Wd, 0, -1.4), (-Wd, far, -1.4), (-Wd, far, Hc), (-Wd, 0, Hc)],
                        "rw": [(Wd, 0, -1.4), (Wd, 0, Hc), (Wd, far, Hc), (Wd, far, -1.4)],
                        "cl": [(-Wd, 0, Hc), (-Wd, far, Hc), (Wd, far, Hc), (Wd, 0, Hc)]}.items():
            col = {"fl": pal["floor"], "lw": mix(pal["grey3"], pal["bg"], 0.55), "rw": mix(pal["grey3"], pal["bg"], 0.7),
                   "cl": mix(pal["floor"], pal["bg"], 0.6)}[nm]
            ptsc = [(x, max(y, eye.ey + 0.5), z) for x, y, z in pts]
            objs.append(quad(f"!!cr{nm}", eye, ptsc, col, fa=0.85, zz=1))
        for i, (t, side, y) in enumerate(doors):
            d = y - eye.ey
            hot = i == k
            fa = 0.0 if d < 0.9 else 1.0
            yy = max(y, eye.ey + 0.9)
            x = side * Wd
            pts = [(x, yy, -1.4), (x, yy + 1.4, -1.4), (x, yy + 1.4, 1.0), (x, yy, 1.0)]
            col = fog(pal["acc"] if hot else pal["grey"], pal["bg"], d, 2.5, 16)
            objs.append(quad(f"!!dr{i}", eye, pts, col, fa=fa, zz=10 + (10 - i)))
            if fa and d > 2.4:
                tx = x - side * 0.15
                objs.append(tlabel(f"!!dt{i}", eye, tx if side > 0 else tx, yy + 0.7, 1.55, t, 22,
                                   al="r" if side > 0 else "l", w0=2.4, col="accent" if hot else "ink2", zz=40 + (10 - i)))
        return objs

    slides = [Slide(head(["Офис изнутри", "Вторая дверь", "Третья дверь"][k], "идём по коридору", y=0.35) + scene(k), dur=900)
              for k in range(3)]
    return Variant(FAM, "corridor", "Коридор с дверями-разделами",
                   "Коридор в одноточечной перспективе (пол, стены, потолок), двери-разделы по сторонам. Клик — шаг "
                   "вперёд: пройденная дверь уходит за край, следующая загорается. Роль: навигация по разделам, «экскурсия».",
                   slides, tags=["depth", "corridor", "navigation", "perspective"], score=3)


# ----------------------------------------------------------------------------- SEQ 1. погружение: 7 уровней и обратно

def v_seq_dive(theme):
    pal = _pal(theme)
    rnd = random.Random(8)
    stars = [(rnd.uniform(-14, 14), rnd.uniform(4, 40), rnd.uniform(-8, 8)) for _ in range(36)]
    notes = {0: ("Пять уровней", "от рынка к человеку"), 1: ("Уровень 1", "рынок: 40 млрд ₽"),
             2: ("Уровень 2", "компания: доля 6%"), 3: ("Уровень 3", "отдел: 12 человек"),
             4: ("Уровень 4", "команда: трое"), 5: ("Уровень 5", "один человек решает"), 6: ("Обратно", "весь путь сразу")}

    def scene(k):
        if k == 0:
            eye = Eye(0, -4.0, 0, f=5.0, cx=9.0, cy=3.9)
        elif k == 6:
            eye = Eye(0, -7.0, 0, f=6.0, cx=9.0, cy=3.9)
        else:
            eye = Eye(0, (k - 1) * 3.0, 0, f=6.0, cx=SLIDE_W / 2 + 0.9, cy=SLIDE_H / 2 + 0.45)
        cur = max(0, min(k - 1, 4)) if k not in (0, 6) else (-1 if k == 0 else 4)
        objs = dive_scene(theme, pal, eye, cur=cur, labels=k != 0)
        for i, (x, y, z) in enumerate(stars):  # пылинки: мимо пролетают быстрее ближние — объём
            d = y - eye.ey
            if d < 1.5:
                fa, yy = 0.0, max(y, eye.ey + 0.6)
            else:
                fa, yy = min(0.9, 4.0 / d), y
            px, py = eye.p((x, yy, z))
            r = max(0.025, 0.09 * eye.k(yy) / 3)
            objs.append(O(f"!!st{i}", "oval", px - r, py - r, 2 * r, 2 * r, fill=pal["grey2"], fa=fa, z=0,
                          meta={"bleed": True, "decor": True}))
        if k in (5, 6):  # человек в последней рамке: на общем плане — маленький
            e5 = eye
            y5 = 5.0 + 4 * 3.0
            hx, hy = e5.p((0, y5, 0.45))
            r = 0.42 * e5.k(y5) / 1.2
            objs.append(O("!!who", "oval", hx - r, hy - r, 2 * r, 2 * r, fill="accent", z=200))
            bx, by = e5.p((0, y5, -0.15))
            objs.append(O("!!who_b", "rrect", bx - 1.7 * r, by, 3.4 * r, 2.6 * r, fill="accent", radius=r * 1.2, z=200))
        return objs

    slides = []
    for k in range(7):
        t, sub = notes[k]
        slides.append(Slide(head(t, sub, y=0.35) + scene(k), dur=900))
    return Variant(FAM, "seq_dive", "Погружение: пять рамок и обратно",
                   "Семь слайдов одной сцены: рамки-уровни стоят коридором (общий план с выноса) → камера влетает и "
                   "проходит рамку за рамкой (рынок → компания → отдел → команда → человек), пылинки пролетают мимо, "
                   "проеханное уходит за края → в центре последней рамки появляется человек → камера отъезжает назад и "
                   "вбок, весь коридор виден сразу. Роль: сквозной сюжет «от общего к частному» на всю презентацию.",
                   slides, tags=["depth", "seq", "camera", "dive", "levels"], score=4)


# ----------------------------------------------------------------------------- SEQ 2. экран: плоско → слои → карточки на полу → график → снова экран

def v_seq_ui(theme):
    pal = _pal(theme)
    flat = Cam3(8.6, 3.9, 0.9, yaw=0, pitch=0.01)
    tilt = fitcam(Cam3(0, 0, 1, yaw=38, pitch=24, dist=22), lambda c, k: ui_layers(theme, pal, c, 1.6, labels=False), [0],
                  (5.4, 1.4, 5.6, 5.3))
    vals = [0.62, 0.9, 0.38]
    cname = ["Каталог", "Корзина", "Оплата"]

    def cards_state(mode):
        """Слой карточек отдельно: mode 'front' — крупно лицом, 'floor' — легли на пол, 'bars' — встали столбиками."""
        objs = ui_layers(theme, pal, tilt, 1.6, hot=2, labels=False)
        objs = [o for o in objs if not o.name.startswith("!!ui2_")]
        # остальной экран — тихим фоном
        objs = [o.copy(fa=0.25, la=0.25, meta={**o.meta, "decor": True}) for o in objs]
        cam_f = Cam3(8.7, 4.2, 1.0, yaw=0, pitch=0.01)
        cam_fl = Cam3(9.2, 4.2, 0.9, yaw=20, pitch=55, dist=20)
        cam_b = Cam3(9.2, 5.9, 0.9, yaw=20, pitch=18, dist=20)
        for j in range(3):
            if mode == "front":
                x, z, w, h = -3.2 + j * 2.25, -1.6, 2.0, 3.0
                pts = [(x, 0, z + h), (x + w, 0, z + h), (x + w, 0, z), (x, 0, z)]
                pp = [cam_f.p(p) for p in pts]
            elif mode == "floor":
                x = -3.2 + j * 2.25
                pts = [(x, 2.0, 0), (x + 2.0, 2.0, 0), (x + 2.0, 0.0, 0), (x, 0.0, 0)]
                pp = [cam_fl.p(p) for p in pts]
            else:
                x = -3.2 + j * 2.25
                h = vals[j] * 4.0
                pts = [(x, 0, h), (x + 2.0, 0, h), (x + 2.0, 0, 0), (x, 0, 0)]
                pp = [cam_b.p(p) for p in pts]
            col = pal["acc"] if (mode == "bars" and j == 1) else pal["grey"]
            objs.append(poly(f"!!ui2_{j}", pp, fill=col, ln=pal["bg"], lw=0.75, z=40 + j))
            cx = sum(p[0] for p in pp) / 4
            cy = sum(p[1] for p in pp) / 4
            if mode == "front":
                objs.append(label(f"cf{j}", cx - 0.95, cy - 0.25, 1.9, cname[j], sz=19, b=True, al="c",
                                  col=ink_on(theme, pal["grey"]), z=90))
            if mode == "bars":
                top = min(p[1] for p in pp)
                objs.append(label(f"cb{j}", cx - 0.9, top - 0.5, 1.8, f"{round(vals[j] * 100)}%", sz=18, b=True,
                                  al="c", col="accent" if j == 1 else "ink", z=90))
                objs.append(label(f"cn{j}", cx - 0.95, max(p[1] for p in pp) + 0.08, 1.9, cname[j], sz=14, al="c",
                                  col="ink2", z=90))
        return objs

    slides = [Slide(head("Экран заказа", "как видит клиент") + ui_layers(theme, pal, flat, 0.0), dur=850),
              Slide(head("Четыре слоя", "разносим по глубине") + ui_layers(theme, pal, tilt, 1.6), dur=900),
              Slide(head("Слой карточек", "три шага покупки") + ui_layers(theme, pal, tilt, 1.6, hot=2), dur=700),
              Slide(head("Крупно", "карточки выходят к нам") + cards_state("front"), dur=900),
              Slide(head("Путь клиента", "карточки легли на пол") + cards_state("floor"), dur=900),
              Slide(head("Доходят до шага", "доля посетителей") + cards_state("bars"), dur=900),
              Slide(head("Снова экран", "корзину переделали") + ui_layers(theme, pal, flat, 0.0, hot=2), dur=900)]
    return Variant(FAM, "seq_ui", "Экран: слои, карточки, график, экран",
                   "Один макет экрана живёт 7 слайдов: плоский экран → расслаивается в перспективе → горит слой карточек → "
                   "карточки отделяются и встают лицом к зрителю (остальное — тихий фон) → ложатся на пол «путём "
                   "клиента» → встают столбиками конверсии → схлопываются обратно в плоский экран. Роль: продуктовая "
                   "презентация «экран → метрика → решение».", slides, tags=["depth", "seq", "ui", "layers", "data"], score=4)


def variants(theme) -> list[Variant]:
    from lab._c_util import ensure_contrast
    return ensure_contrast(theme, [f(theme) for f in (v_dive, v_parallax, v_floor, v_tunnel, v_recede, v_ui, v_stage, v_deck, v_flyby,
                               v_corridor, v_seq_dive, v_seq_ui)])
