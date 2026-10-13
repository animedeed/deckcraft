"""Сквозной мотив колоды: один объект-герой проходит через всю презентацию в разных РОЛЯХ.

Мотив — не картинка на обложке. Это набор фигур с постоянными именами; меняется только состояние (центр, масштаб,
поворот, прозрачность, размеры частей, подсветка), поэтому Morph переводит мотив из роли в роль:

  hero      — крупно, главный герой (обложка, финал);
  pointer   — наполовину за краем экрана, часть k смотрит на тему раздела (указатель темы);
  backdrop  — огромный и бледный под содержимым, медленно дрейфует от слайда к слайду (фон);
  progress  — раскрыто k частей из n (где мы в докладе);
  data      — размеры частей = значения, у кончиков — подписи (мотив становится диаграммой);
  portal    — центр мотива раздувается на весь экран (полёт «внутрь» к новому разделу);
  seed      — мотив свёрнут в точку (пауза, вопрос, переход к контрасту).

    track = MotifTrack(Flower(petals=8), theme)
    slide.objs += track.at("hero")
    slide.objs += track.at("pointer", k=2)            # раздел 3
    slide.objs += track.at("backdrop", t=5)           # фон 5-го слайда раздела
    slide.objs += track.at("data", values=[...], labels=[...])

MotifTrack помнит прошлый поворот и выбирает равный ему по модулю 360° ближайший угол: Morph крутит по кратчайшему
пути, поэтому шаг всегда < 180° и мотив не «крутится назад». Мотивы: Flower (многослойные лепестки), Orbit (орбиты
и тела). Новый мотив = класс с методом `objs(theme, **state)` и постоянными именами частей.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

from . import vector as V
from .model import O
from .theme import SLIDE_H, SLIDE_W, Theme, mix

DECOR = {"bleed": True, "decor": True}


def _fills(theme: Theme, layers: int) -> list[tuple[str, str]]:
    """Полосы лепестка из цветов темы: светлая и серая чередуются (как вырезанная бумага)."""
    ink, bg = theme.c("ink"), theme.c("bg")
    out = []
    for j in range(layers - 1):
        a = 0.08 + 0.34 * (j % 2) + 0.06 * (j // 2)
        out.append((mix(ink, bg, a), mix(ink, bg, a + 0.18)))
    return out


@dataclass
class Flower:
    """Цветок из многослойных лепестков (эталон — видео пользователя) + центральный диск поверх лепестков.
    Диск — «портал»: в роли portal он закрывает экран цветом фона."""
    id: str = "fl"
    petals: int = 8
    layers: int = 5
    length: float = 3.0
    width: float = 1.15
    disc: float = 0.16  # радиус диска в долях length
    n: int = 0  # >0 — каждая часть ресемплится до n точек (перелив в карточки/столбики), рамка на оси сохраняется

    def step(self) -> float:
        return 360.0 / self.petals

    def facing(self, k: int, angle: float = 0.0) -> float:
        """Поворот цветка, при котором лепесток k смотрит по направлению angle (0° — вправо, 90° — вниз)."""
        return angle + 90.0 - k * self.step()

    def objs(self, theme: Theme, center=(SLIDE_W * 0.7, SLIDE_H / 2), scale: float = 1.0, turn: float = 0.0,
             alpha: float = 1.0, sizes: Sequence[float] | None = None, focus: int | None = None,
             disc_scale: float = 1.0, fill_bands: dict | None = None, z: int = 6, **_) -> list[O]:
        """fill_bands = {лепесток: доля 0..1} — прогресс внутри раздела: полосы лепестка заливаются акцентом
        от ядра наружу (4 полосы: 25 % — одна, 50 % — две…)."""
        cx, cy = center
        fills = _fills(theme, self.layers)
        nb = self.layers - 1
        bg, acc = theme.c("bg"), theme.c("accent")
        out = []
        for k in range(self.petals):
            m = 1.0 if sizes is None else max(float(sizes[k]), 0.02)
            parts = V.bud((cx, cy), self.length * scale * m, self.width * scale * m, layers=self.layers, angle=-90,
                          n=self.n)
            for j, g in enumerate(parts):
                core = j == len(parts) - 1
                if core:
                    fill, grad = bg, None
                else:
                    a, b = fills[j % len(fills)]
                    done = (fill_bands or {}).get(k)
                    if done is not None:
                        n_fill = math.ceil(round(done * nb, 6))
                        if j >= nb - n_fill:  # полоса j считается от внешней (0) к внутренней (nb-1)
                            a, b = mix(acc, bg, 0.05 + 0.12 * (nb - 1 - j)), mix(acc, bg, 0.3 + 0.08 * (nb - 1 - j))
                        elif j == 0:
                            a, b = mix(acc, bg, 0.55), mix(acc, bg, 0.75)
                    elif focus == k and j == 0:
                        a, b = acc, mix(acc, bg, 0.35)
                    grad = V.gradient([(0, a, alpha), (1, b, alpha)], angle=90)
                    fill = a
                out.append(V.shape(f"!!{self.id}{k}_{j}", g, pivot=(cx, cy), rot=(turn + k * self.step()) % 360,
                                   fill=fill, fa=alpha, grad=grad, ln=bg if j == 0 else None, lw=1.0 if j == 0 else 0,
                                   z=z + k * self.layers + j, meta=dict(DECOR)))
        r = self.length * self.disc * scale * disc_scale
        out.append(O(f"!!{self.id}_disc", "oval", cx - r, cy - r, 2 * r, 2 * r, fill="bg",
                     ln=None if disc_scale > 3 else "accent", lw=1.5 * min(scale, 1.5), la=alpha,
                     z=z + self.petals * self.layers + 1, meta=dict(DECOR)))
        return out

    def tip(self, center, scale: float, turn: float, k: int, size: float = 1.0, pad: float = 0.25):
        """Кончик лепестка k (для подписей роли data)."""
        a = math.radians(-90 + turn + k * self.step())
        r = self.length * scale * size + pad
        return center[0] + r * math.cos(a), center[1] + r * math.sin(a), a


@dataclass
class Orbit:
    """Орбиты и тела: кольца-орбиты, на каждой — тело; солнце в центре — «портал»."""
    id: str = "or"
    rings: int = 5
    r0: float = 0.75  # радиус первой орбиты
    gap: float = 0.55  # шаг орбит
    body: float = 0.22  # диаметр тела
    sun: float = 0.42  # радиус солнца
    spread: Sequence[float] = field(default_factory=lambda: [200, 320, 60, 150, 260, 20, 110, 230, 340, 80])

    def step(self) -> float:
        return 360.0 / self.rings

    def facing(self, k: int, angle: float = 0.0) -> float:
        """Поворот системы, при котором тело k смотрит по направлению angle."""
        return angle - self.spread[k % len(self.spread)]

    def objs(self, theme: Theme, center=(SLIDE_W * 0.7, SLIDE_H / 2), scale: float = 1.0, turn: float = 0.0,
             alpha: float = 1.0, sizes: Sequence[float] | None = None, focus: int | None = None,
             disc_scale: float = 1.0, align: Sequence[int] = (), z: int = 6, **_) -> list[O]:
        """align — тела, выстроенные на линию указателя (прогресс: «планеты на одной оси»)."""
        cx, cy = center
        out = []
        for i in range(self.rings):
            r = (self.r0 + i * self.gap) * scale
            out.append(O(f"!!{self.id}_ring{i}", "oval", cx - r, cy - r, 2 * r, 2 * r, fill=None, ln="line",
                         lw=1.25, la=alpha, z=z + i, meta=dict(DECOR)))
        for i in range(self.rings):
            r = (self.r0 + i * self.gap) * scale
            m = 1.0 if sizes is None else max(float(sizes[i]), 0.05)
            d = self.body * scale * m * (1.5 if focus == i else 1.0)
            ang = (turn + self.spread[i % len(self.spread)]) if i not in align else (turn + self.spread[focus or 0])
            g = V.circle(cx + r, cy, d / 2)
            col = "accent" if focus == i else ("ink2" if i in align else "muted")
            out.append(V.shape(f"!!{self.id}_b{i}", g, pivot=(cx, cy), rot=ang % 360, fill=col, fa=alpha,
                               z=z + self.rings + i, meta=dict(DECOR)))
        rs = self.sun * scale * disc_scale
        out.append(O(f"!!{self.id}_disc", "oval", cx - rs, cy - rs, 2 * rs, 2 * rs, fill="bg" if disc_scale > 3 else "accent",
                     fa=1.0 if disc_scale > 3 else alpha, z=z + 2 * self.rings + 1, meta=dict(DECOR)))
        return out

    def tip(self, center, scale: float, turn: float, k: int, size: float = 1.0, pad: float = 0.3):
        a = math.radians(turn + self.spread[k % len(self.spread)])
        r = (self.r0 + k * self.gap) * scale + pad
        return center[0] + r * math.cos(a), center[1] + r * math.sin(a), a


# ----------------------------------------------------------------------------- роли

EDGE = (-0.35, SLIDE_H / 2)  # центр мотива-указателя: за левым краем


@dataclass
class MotifTrack:
    """Мотив на протяжении колоды: роли -> состояния, непрерывный поворот (шаг < 180°)."""
    motif: Flower | Orbit
    theme: Theme
    turn: float = 0.0
    log: list = field(default_factory=list)

    def _turn_near(self, target: float) -> float:
        best = target + 360 * round((self.turn - target) / 360)
        self.turn = best
        return best

    def at(self, role: str, **kw) -> list[O]:
        m, th = self.motif, self.theme
        n = m.petals if isinstance(m, Flower) else m.rings
        if role == "hero":
            st = dict(center=kw.get("center", (SLIDE_W * 0.7, SLIDE_H / 2)), scale=kw.get("scale", 1.0),
                      turn=self._turn_near(kw.get("turn", self.turn)), focus=kw.get("focus"))
        elif role == "pointer":
            k = kw["k"]
            center, scale = kw.get("center", EDGE), kw.get("scale", 0.86)
            if isinstance(m, Orbit) and "center" not in kw:  # тело раздела встаёт у x = reach, система — за краем
                scale = kw.get("scale", 1.6)
                center = (kw.get("reach", 2.4) - (m.r0 + k * m.gap) * scale, SLIDE_H / 2)
            st = dict(center=center, scale=scale, turn=self._turn_near(m.facing(k, kw.get("angle", 0.0))), focus=k)
            if "part" in kw:  # прогресс внутри раздела: kw part = доля пройденных тем (0..1)
                st["fill_bands"] = {k: kw["part"]}
        elif role == "backdrop":
            t = kw.get("t", 0)
            # next_k: фон заранее повёрнут так, что лепесток следующего раздела смотрит вправо — возвращение
            # в указатель = только сдвиг и уменьшение, без вращения (иначе «странно»: крутится, едет и сжимается)
            base = m.facing(kw["next_k"]) if "next_k" in kw else kw.get("base", 0.0)
            st = dict(center=kw.get("center", (SLIDE_W * 0.42, SLIDE_H * 0.55)), scale=kw.get("scale", 1.9),
                      turn=self._turn_near(base + t * kw.get("drift", 0.0 if "next_k" in kw else 7.0)),
                      alpha=kw.get("alpha", 0.10), focus=None, z=kw.get("z", -400))  # фон — под всем
        elif role == "progress":
            # маленький навигатор в углу: раскрыто k+1 частей из n, первая — сверху, по часовой стрелке
            k = kw["k"]
            sizes = [1.0 if i <= k else kw.get("closed", 0.38) for i in range(n)]
            st = dict(center=kw.get("center", (0.95, SLIDE_H - 0.95)), scale=kw.get("scale", 0.24),
                      turn=self._turn_near(kw.get("turn", 0.0)), focus=k, sizes=sizes, align=list(range(k + 1)))
        elif role == "data":
            vals = list(kw["values"])
            top = max(vals) or 1.0
            sizes = [kw.get("floor", 0.18) + (1 - kw.get("floor", 0.18)) * v / top for v in vals]
            st = dict(center=kw.get("center", (SLIDE_W * 0.67, SLIDE_H * 0.59)), scale=kw.get("scale", 0.9),
                      turn=self._turn_near(kw.get("turn", 0.0)), sizes=sizes, focus=kw.get("focus"),
                      disc_scale=kw.get("disc", 0.55))  # диск меньше самого короткого лепестка
        elif role == "portal":
            st = dict(center=kw.get("center", (SLIDE_W / 2, SLIDE_H / 2)), scale=kw.get("scale", 1.2),
                      turn=self._turn_near(self.turn + kw.get("spin", 30)), disc_scale=kw.get("disc", 30.0))
        elif role == "seed":
            st = dict(center=kw.get("center", (SLIDE_W / 2, SLIDE_H / 2)), scale=kw.get("scale", 0.04),
                      turn=self._turn_near(self.turn), alpha=kw.get("alpha", 1.0))
        else:
            raise ValueError(f"нет роли {role!r}")
        st.update({k: v for k, v in kw.items() if k in ("alpha", "z")})
        objs = m.objs(th, **st)
        if role == "data" and kw.get("labels"):
            objs += self._labels(st, kw["labels"], kw.get("label_sz", 13), kw.get("label_names"),
                                 kw.get("value_text"), kw.get("label_w", 1.9), kw.get("label_ring", 0.7))
        self.log.append((role, round(st["turn"], 1)))
        return objs

    def _labels(self, st, labels, sz, names=None, values=None, w: float = 1.9, ring: float = 0.7) -> list[O]:
        """Подписи у кончиков частей. names — имена объектов подписей (например, подписи фишек носителя: тогда
        фишки «перелетают» к лепесткам); values — вторая строка-значение отдельным объектом (текст подписи
        не меняется, поэтому Morph её переносит, а не гасит)."""
        m = self.motif
        out = []
        for k, text in enumerate(labels):
            size = max(st.get("sizes", [1.0] * len(labels))[k], ring)  # короткие части — подписи на общем кольце
            x, y, a = m.tip(st["center"], st["scale"], st["turn"], k, size=size)
            h = 0.32
            al = "l" if math.cos(a) > 0.3 else ("r" if math.cos(a) < -0.3 else "c")
            bx = x if al == "l" else (x - w if al == "r" else x - w / 2)
            up = math.sin(a) < -0.6
            by = y - (0.62 if up else (0.0 if math.sin(a) > 0.6 else 0.28))
            name = names[k] if names else f"!!{m.id}_lbl{k}"
            out.append(O(name, "text", bx, by, w, h, txt=text, sz=sz, col="ink", al=al, va="t", z=80,
                         meta={"inset": 0.0}))
            if values:
                out.append(O(f"!!{m.id}_val{k}", "text", bx, by + h - 0.02, w, 0.28, txt=values[k], sz=sz - 1,
                             col="accent" if st.get("focus") == k else "muted", al=al, va="t", z=80,
                             meta={"inset": 0.0}))
        return out


__all__ = ["Flower", "Orbit", "MotifTrack", "EDGE"]
