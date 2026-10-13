"""Комбинирование выбора из опроса: несколько вариантов в каждой категории → варианты презентации A/B/C, узор переходов
между разделами, пул языков движения внутри раздела.

    from morphkit.combine import plan_variants, transition_pattern, motion_schedule
    choice = {"palettes": ["neuro", "ink"], "motifs": ["neural"], "navigation": ["counter", "agenda"],
              "transition": {"main": "camera", "accents": ["cube", "curtains"]},
              "sections": {"Текст": ["fragments", "dots"], ...}, "variants": 3}
    for v in plan_variants(choice):  v["label"], v["palette"], v["navigation"], v["sections"]

Правила (pptx-design/references/structure.md) сохраняются внутри каждого варианта: одна навигация, один тип
перехода на ВСЕХ границах разделов (акцент — система, не разовая вставка), язык движения повторяется внутри
раздела. Разнообразие — между вариантами, а не в хаосе внутри одной презентации.
"""

from __future__ import annotations

from itertools import product

AXES = ("palette", "motif", "navigation")
LABELS = "ABCDEF"

# Нативные переходы PowerPoint для границ глав (Morph остаётся основным внутри разделов)
ACCENTS = {
    "cube": ("Поворот куба", "новый раздел — грань куба поворачивается", "chapter"),
    "rotate": ("Поворот", "смена угла зрения на ту же тему", "chapter"),
    "fly_through": ("Пролёт насквозь", "камера пролетает в следующий мир", "chapter"),
    "gallery": ("Галерея", "лента примеров или кейсов", "chapter"),
    "pan": ("Панорама", "соседний участок одной карты", "chapter"),
    "zoom": ("Наезд", "приближение к детали — кульминация", "climax"),
    "ripple": ("Круги на воде", "волна от главного вывода", "climax"),
    "vortex": ("Воронка", "«сломали»: ошибка, антипример", "error"),
    "shred": ("Шредер", "отказ от старого решения", "error"),
    "page_curl": ("Перелистывание", "документы, редакции, нормативы", "chapter"),
    "origami": ("Оригами", "сложили итог в одну форму", "finale"),
    "curtains": ("Занавес", "финал доклада", "finale"),
}


def _combos(choice: dict) -> list[dict]:
    lists = {"palette": choice.get("palettes") or [], "motif": choice.get("motifs") or [],
             "navigation": choice.get("navigation") or []}
    lists = {k: (v if isinstance(v, list) else [v]) or [None] for k, v in lists.items()}
    return [dict(zip(AXES, c)) for c in product(*(lists[a] for a in AXES))]


def _dist(a: dict, b: dict) -> int:
    return sum(a[k] != b[k] for k in AXES)


def plan_variants(choice: dict, n: int | None = None) -> list[dict]:
    """Варианты презентации из отмеченного: перебор комбинаций палитра × мотив × навигация, жадный выбор максимально
    непохожих (первая комбинация — из первых отмеченных, т. е. «главный» выбор пользователя). Языки движения
    разделов у варианта k — пул раздела, сдвинутый на k: у A ведёт первый язык, у B — второй…"""
    n = n or int(choice.get("variants") or 1)
    combos = _combos(choice)
    picked = [combos[0]]
    while len(picked) < min(n, len(combos)):
        rest = [c for c in combos if c not in picked]
        used = {(a, p[a]) for p in picked for a in AXES}
        # самая далёкая от уже выбранных → больше ещё не показанных значений → раньше в списке (приоритет)
        picked.append(max(rest, key=lambda c: (min(_dist(c, p) for p in picked), sum(_dist(c, p) for p in picked),
                                               sum((a, c[a]) not in used for a in AXES), -combos.index(c))))
    tr = choice.get("transition") or {}
    out = []
    for k, c in enumerate(picked):
        sections = {}
        for name, pool in (choice.get("sections") or {}).items():
            pool = pool if isinstance(pool, list) else [pool]
            sections[name] = pool[k % len(pool):] + pool[:k % len(pool)] if pool else []
        accents = list(tr.get("accents") or [])
        bnd = [a for a in accents if ACCENTS.get(a, ("", "", "chapter"))[2] != "finale"]
        fin = [a for a in accents if a not in bnd][:1]
        if n > 1 and len(bnd) > 1:  # каждый вариант пробует свой тип границы разделов — так их можно сравнить
            accents = [bnd[k % len(bnd)]] + fin
        diff = [a for a in AXES if k and c[a] != picked[0][a]]
        out.append({"label": LABELS[k], **c, "transition": {"main": tr.get("main"), "accents": accents},
                    "sections": sections, "differs": diff})
    if n > len(combos) and n > 1:  # осей мало — варианты различаются порядком языков движения и акцентов
        base = out[0]
        for k in range(len(out), n):
            v = {**base, "label": LABELS[k], "differs": ["motion"]}
            v["sections"] = {s: p[k % len(p):] + p[:k % len(p)] if p else [] for s, p in
                             (choice.get("sections") or {}).items()}
            acc = list(tr.get("accents") or [])
            bnd = [a for a in acc if ACCENTS.get(a, ("", "", "chapter"))[2] != "finale"]
            fin = [a for a in acc if a not in bnd][:1]
            v["transition"] = {"main": tr.get("main"), "accents": ([bnd[k % len(bnd)]] if bnd else []) + fin}
            out.append(v)
    return out


def transition_pattern(n_sections: int, main: str, accents: list[str] | None = None, **_ignored) -> list[str]:
    """Переходы на границах разделов (длина n_sections − 1; граница i — вход в раздел i + 1, последняя — в финал).
    Акцент — это СИСТЕМА, а не разовая вставка (отзыв: «куб/занавес один раз посреди презентации — не к месту»):
    первый не-финальный акцент стоит на ВСЕХ границах разделов; акцент вида «finale» (занавес, оригами) —
    только на входе в финал и только вместе с основным, иначе финал получает тот же переход, что и остальные.
    Без акцентов — везде основной (Morph-приём). Внутри разделов всегда Morph."""
    nb = max(n_sections - 1, 0)
    accents = list(accents or [])
    kind = lambda a: ACCENTS.get(a, ("", "", "chapter"))[2]  # noqa: E731
    boundary = next((a for a in accents if kind(a) != "finale"), None)
    finale = next((a for a in accents if kind(a) == "finale"), None)
    if boundary is None:  # только «финальный» акцент: разовая вставка запрещена — система из него же
        boundary, finale = finale, None
    pat = [boundary or main] * nb
    if nb and finale:
        pat[-1] = finale
    return pat


def motion_schedule(n_slides: int, pool: list[str]) -> list[str]:
    """Язык движения для каждого слайда раздела: ведущий язык — на первом и большинстве шагов, остальные языки
    пула — вставками (не два одинаковых «гостя» подряд). Ведущий держит раздел узнаваемым."""
    if not pool:
        return [""] * n_slides
    lead, guests = pool[0], pool[1:]
    out = []
    for j in range(n_slides):
        out.append(guests[(j // 2) % len(guests)] if guests and j % 2 == 1 else lead)
    return out


__all__ = ["ACCENTS", "plan_variants", "transition_pattern", "motion_schedule"]
