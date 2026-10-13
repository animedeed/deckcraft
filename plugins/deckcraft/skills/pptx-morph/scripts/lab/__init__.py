"""Лаборатория форм и движения: семейства вариантов (2–3 состояния слайда) для отбора лучших приёмов.

Каждое семейство — модуль f_<имя>.py с функцией `variants(theme) -> list[Variant]`. Прогон и отбор —
`python -m lab.run <семейство|all> OUT_DIR [--theme ink] [--fast]` (из папки scripts).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from morphkit import O, Slide


@dataclass
class Variant:
    family: str  # семейство (имя модуля без f_)
    key: str  # короткий ключ латиницей, уникален в семействе
    title: str  # название по-русски (видно в подписи слайда)
    idea: str  # одна-две фразы: что показывает и где использовать в колоде (роль: фон, навигация, данные, акцент…)
    slides: list[Slide]  # 2–3 состояния; соседние связаны парами !! — Morph и эффекты после перехода
    tags: list[str] = field(default_factory=list)  # fragment, orbit, 3d, wine, data, background, navigation, text …
    score: int = 0  # самооценка автора 1–5 (после просмотра кадров движения)


def caption(v: Variant, step: int) -> list[O]:
    """Подпись варианта в углу слайда (не участвует в Morph)."""
    return [O(f"lab_cap{step}", "text", 0.35, 7.02, 12.6, 0.36, txt=f"{v.family} · {v.key} — {v.title}  [{step + 1}/{len(v.slides)}]",
              sz=12, col="muted", z=999, meta={"overlap_ok": True})]


def isolate(v: Variant, tag: str | None = None) -> list[Slide]:
    """Состояния варианта с уникальными именами пар Morph (префикс варианта): соседние варианты в одной колоде
    (лаборатория, витрина) не переливаются друг в друга. Цели эффектов и петель переименовываются тоже."""
    from dataclasses import replace
    tag = tag or "".join(ch for ch in f"{v.family}{v.key}" if ch.isalnum())[:24]
    ren = lambda n: f"!!{tag}_{n[2:]}" if isinstance(n, str) and n.startswith("!!") else n  # noqa: E731
    out = []
    for s in v.slides:
        objs = [o.copy(name=ren(o.name)) for o in s.objs]
        fx = [replace(f, target=ren(f.target)) for f in s.fx]
        loops = [replace(lp, target=ren(lp.target)) for lp in s.loops]
        out.append(replace(s, objs=objs, fx=fx, loops=loops, anims=[ren(a) for a in s.anims]))
    return out
