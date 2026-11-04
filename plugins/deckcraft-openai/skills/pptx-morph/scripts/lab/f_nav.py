"""Навигация и смена разделов — превью для опроса: метка блока + счётчик, меню сайта, карта разделов → ряд рамок,
поворот указателя-мотива у края, а также нативные переходы PowerPoint между разделами (для сравнения с Morph).

Содержимое слайдов — нейтральные «разделы» (столбики, точки, карточки), чтобы смотреть именно на навигацию.
"""

from __future__ import annotations

from morphkit import O, Slide
from morphkit.motif import Flower, MotifTrack
from morphkit.recipes import agenda, block_counter, menu_bar

from lab import Variant

FAM = "nav"
SECS = ["Данные", "Модель", "Результаты", "Выводы"]
HEADS = ["36 образцов в работе", "Четыре слоя сети", "Лучший — третий", "Три вывода"]


def _v(key, title, idea, slides, tags, score=3) -> Variant:
    return Variant(FAM, key, title, idea, slides, tags=tags, score=score)


def _ttl(text: str, y: float = 0.86) -> O:
    return O("!!ttl", "text", 0.7, y, 8.0, 0.75, txt=text, sz=30, b=True, font="head", col="ink", z=90)


def _content(k: int, x0: float = 0.7) -> list[O]:
    """Тело раздела k: у каждого своя простая картинка (без пар — меняется затуханием)."""
    out = []
    if k == 0:  # точки
        for i in range(36):
            out.append(O(f"c0_{i}", "oval", x0 + 0.3 + (i % 9) * 0.62, 2.6 + (i // 9) * 0.62, 0.3, 0.3,
                         fill="accent" if i % 7 == 0 else "muted", fa=0.85, z=10))
    elif k == 1:  # слои
        for c in range(4):
            for r in range(4 if c in (1, 2) else 3):
                out.append(O(f"c1_{c}_{r}", "oval", x0 + 0.6 + c * 1.6, 2.7 + r * 0.8 + (0.4 if c in (0, 3) else 0),
                             0.42, 0.42, fill="surface2", ln="accent" if c == 1 else "muted", lw=1.5, z=10))
    elif k == 2:  # столбики
        for i, h in enumerate([1.2, 2.0, 2.9, 1.6, 2.4]):
            out.append(O(f"c2_{i}", "rect", x0 + 0.5 + i * 1.05, 5.6 - h, 0.7, h, fill="accent" if i == 2 else "muted", z=10))
    else:  # карточки-выводы
        for i in range(3):
            out.append(O(f"c3_{i}", "rrect", x0 + 0.3 + i * 2.1, 2.7, 1.85, 2.4, fill="surface", ln="line", lw=1,
                         radius=0.14, z=10))
            out.append(O(f"c3_{i}t", "text", x0 + 0.45 + i * 2.1, 2.9, 1.6, 0.5, txt=f"вывод {i + 1}", sz=16, b=True,
                         col="ink", z=11))
    return out


def nav_counter(theme) -> Variant:
    sl = [Slide(block_counter("nv", f"Блок {k + 1} — {s}", k + 2, 9, y=0.18) + [_ttl(HEADS[k], 0.62)] + _content(k), dur=700)
          for k, s in enumerate(SECS[:3])]
    return _v("counter", "Метка блока + счётчик", "Строго и спокойно: метка раздела меняется затуханием, счётчик страниц справа.",
              sl, ["navigation"])


def nav_menu(theme) -> Variant:
    sl = [Slide(menu_bar("nv", SECS, k, y=0.16, sz=13) + [_ttl(HEADS[k])] + _content(k), dur=700) for k, s in enumerate(SECS[:3])]
    return _v("menu", "Меню сайта", "Строка разделов сверху, подсветка-пилюля переезжает к текущему разделу (Morph).",
              sl, ["navigation"])


def nav_agenda(theme) -> Variant:
    sl = [Slide(agenda("ag", SECS, state="map", k=0, y=2.4, h=2.2) + [_ttl("План доклада", 0.62)], dur=700)]
    sl += [Slide(agenda("ag", SECS, state="bar", k=k) + [_ttl(HEADS[k])] + _content(k), dur=800) for k, s in enumerate(SECS[:2])]
    return _v("agenda", "Карта доклада → ряд рамок", "Карточки разделов складываются в ряд рамок наверху; дальше едет "
              "только подсветка текущего раздела.", sl, ["navigation", "transition"])


def trans_pointer(theme) -> Variant:
    tr = MotifTrack(Flower("pt", petals=8, layers=4, length=2.4, width=0.9), theme)
    sl = []
    for k, s in enumerate(SECS[:3]):
        o = tr.at("pointer", k=k)
        o += [_ttl(HEADS[k], 0.62)] + [O(f"pb{k}", "text", 0.7, 1.55, 6.5, 0.9, txt=f"раздел {k + 1}: лепесток смотрит на заголовок",
                                  sz=18, col="ink2", z=90)] + _content(k, x0=3.4)
        sl.append(Slide(o, dur=900))
    return _v("pointer", "Поворот указателя", "Мотив у края поворачивается к следующему разделу — смена раздела "
              "трансформацией, без нативного перехода.", sl, ["navigation", "transition", "motif"])


def _native(kind: str, title: str, idea: str) -> Variant:
    a = Slide([_ttl("Раздел 1 — " + SECS[0], 0.62)] + _content(0), dur=600)
    b = Slide([_ttl("Раздел 2 — " + SECS[2], 0.62)] + _content(2), dur=600, transition=kind)
    return _v(f"x_{kind}", title, idea, [a, b], ["transition", "native"], 2)


NATIVE = [("zoom", "Наезд"), ("cube", "Поворот куба"), ("rotate", "Поворот"), ("fly_through", "Пролёт насквозь"),
          ("gallery", "Галерея"), ("pan", "Панорама"), ("ripple", "Круги на воде"), ("vortex", "Воронка"),
          ("shred", "Шредер"), ("page_curl", "Перелистывание"), ("origami", "Оригами"), ("curtains", "Занавес")]


def variants(theme) -> list[Variant]:
    out = [nav_counter(theme), nav_menu(theme), nav_agenda(theme), trans_pointer(theme)]
    out += [_native(k, t, "Нативный переход PowerPoint между разделами (превью приближённое).") for k, t in NATIVE]
    return out
