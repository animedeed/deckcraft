"""Измеритель однообразия презентации (прототип 0.3.0): числа вместо «кажется скучным».

    from morphkit.variety import report
    r = report(slides)        # {"deck": {...}, "slides": [...]} — см. поля ниже

Что считается (для каждого перехода i−1 → i и для презентации в целом):
  * energy — «сколько мира поменялось»: по парам Morph (одинаковое имя !!…) сумма площади × величины изменения
    (сдвиг центра в долях диагонали слайда, изменение размера, поворота, формы, цвета), в долях площади слайда;
  * static — доля площади слайда под парами, которые не изменились вовсе (неподвижная «рамка»: навигация, шапка);
  * cut — доля площади новых непарных объектов (смена картинки «склейкой», без движения);
  * layout_sim — сходство раскладки с предыдущим слайдом: Жаккар занятых ячеек сетки 16×9 (без неподвижных пар);
  * verbs — словарь движения слайда: семейства эффектов входа/выделения, виды петель, глаголы Morph
    (move / scale / rotate / reshape / recolor / tilt);
  * words — слов текста на слайде.
Сводка: средние, доля переходов с energy < 0,02 («ничего не сдвинулось»), длина самой длинной серии похожих раскладок
(layout_sim > 0,6), число разных глаголов на презентацию и монотонность = 1 − (разных глаголов / возможных).
"""

from __future__ import annotations

import math
from collections import Counter

from .model import Slide, apply_text_policy, resolve
from .theme import SLIDE_H, SLIDE_W

AREA = SLIDE_W * SLIDE_H
DIAG = math.hypot(SLIDE_W, SLIDE_H)
GRID = (16, 9)


def _area(o) -> float:
    return max(0.0, min(abs(o.w * o.h), AREA)) if o.kind not in ("line", "arrow") else abs(o.w + o.h) * 0.02


def _visible(o) -> bool:
    x0, x1 = sorted((o.x, o.x + o.w))
    y0, y1 = sorted((o.y, o.y + o.h))
    return x1 > 0 and y1 > 0 and x0 < SLIDE_W and y0 < SLIDE_H and (o.fa > 0.01 or o.ln or o.lines)


def _cells(o) -> set[tuple[int, int]]:
    x0, x1 = sorted((o.x, o.x + o.w))
    y0, y1 = sorted((o.y, o.y + o.h))
    gx, gy = GRID
    out = set()
    for i in range(max(0, int(x0 / SLIDE_W * gx)), min(gx, int(math.ceil(x1 / SLIDE_W * gx)))):
        for j in range(max(0, int(y0 / SLIDE_H * gy)), min(gy, int(math.ceil(y1 / SLIDE_H * gy)))):
            out.add((i, j))
    return out


def _change(a, b) -> tuple[float, set[str]]:
    verbs = set()
    ca, cb = (a.x + a.w / 2, a.y + a.h / 2), (b.x + b.w / 2, b.y + b.h / 2)
    mv = math.dist(ca, cb) / DIAG
    sc = abs(math.log(max(abs(b.w * b.h), 1e-4) / max(abs(a.w * a.h), 1e-4))) / 3
    rt = abs(((b.rot - a.rot + 180) % 360) - 180) / 180
    sh = 0.0
    if a.kind == b.kind == "vec":
        ra, rb = a.meta.get("vec", []), b.meta.get("vec", [])
        if ra and rb and len(ra[0]) == len(rb[0]):
            sh = sum(math.dist(p, q) for p, q in zip(ra[0], rb[0])) / len(ra[0])
    col = 0.0 if (a.fill == b.fill and a.fa == b.fa) else 0.15
    if mv > 0.01:
        verbs.add("move")
    if sc > 0.03:
        verbs.add("scale")
    if rt > 0.02:
        verbs.add("tilt" if rt < 0.5 else "rotate")
    if sh > 0.02:
        verbs.add("reshape")
    if col:
        verbs.add("recolor")
    return min(1.0, mv * 3 + sc + rt + sh * 2 + col), verbs


def report(slides: list[Slide]) -> dict:
    webs = [getattr(s, "web", None) or {} for s in slides]  # apply_text_policy копирует слайды без поля web
    slides = apply_text_policy(slides)
    res, prev, prev_all, prev_cells = [], None, [], set()
    all_verbs: Counter = Counter()
    for i, s in enumerate(slides):
        all_objs = resolve(s)
        objs = [o for o in all_objs if _visible(o)]  # «запаркованные» за краем объекты не считаются в раскладке
        by = {o.name: o for o in objs}
        energy = static = cut = 0.0
        verbs: set[str] = set()
        moving = []
        if prev is not None:
            pb = {o.name: o for o in prev_all}
            pv = {o.name for o in prev}
            for o in all_objs:
                a = pb.get(o.name) if o.name.startswith("!!") else None
                if not _visible(o) and (a is None or a.name not in pv):
                    continue  # не виден ни до, ни после
                ar = max(_area(o), 0.05) / AREA  # мелкие носители (ягоды, точки) тоже двигают мир
                if a is None:
                    cut += ar
                    moving.append(o)
                    continue
                ch, vb = _change(a, o)
                if ch < 1e-3:
                    static += ar
                else:
                    energy += ar * ch
                    verbs |= vb
                    moving.append(o)
        else:
            moving = list(objs)
        fams = {f.key.split("_")[0] + ":" + f.key.split("_", 1)[1].split("_")[0] for f in s.fx}
        w = webs[i]
        verbs |= {f"fx:{f}" for f in fams} | {f"loop:{lp.kind}" for lp in s.loops}
        verbs |= {f"web:{f['key']}" for f in w.get("fx", [])} | {f"scene:{sc.get('k')}" for sc in w.get("scenes", [])}
        if w.get("sheet"):
            verbs.add("sheet:" + (w["sheet"] if isinstance(w["sheet"], str) else w["sheet"].get("k", "")))
        if any(("alt" in o.meta) or ("when" in o.meta) for o in all_objs):
            verbs.add("interactive:state")
        if any("link" in o.meta for o in all_objs if not o.name.startswith("!!mn")):
            verbs.add("interactive:link")
        cells = set().union(*[_cells(o) for o in moving if o.kind != "text" and _area(o) > 0.02]) if moving else set()
        sim = len(cells & prev_cells) / max(1, len(cells | prev_cells)) if prev is not None else 0.0
        words = sum(len(" ".join(o.lines).split()) for o in objs if o.lines)
        res.append({"slide": i + 1, "title": s.title, "energy": round(energy, 3), "static": round(min(static, 1), 3),
                    "cut": round(min(cut, 1), 3), "layout_sim": round(sim, 2), "verbs": sorted(verbs), "words": words})
        all_verbs.update(verbs)
        prev, prev_all, prev_cells = objs, all_objs, cells
    tr = res[1:] or res
    runs, run = 0, 0
    for r in tr:
        run = run + 1 if r["layout_sim"] > 0.6 else 0
        runs = max(runs, run)
    n_possible = len(all_verbs) or 1
    per_slide = [len(r["verbs"]) for r in res]
    deck = {"slides": len(res), "energy_mean": round(sum(r["energy"] for r in tr) / len(tr), 3),
            "static_mean": round(sum(r["static"] for r in tr) / len(tr), 3),
            "cut_mean": round(sum(r["cut"] for r in tr) / len(tr), 3),
            "still_transitions": round(sum(r["energy"] < 0.02 for r in tr) / len(tr), 2),
            "layout_sim_mean": round(sum(r["layout_sim"] for r in tr) / len(tr), 2),
            "longest_same_layout_run": runs, "distinct_verbs": len(all_verbs),
            "verbs_per_slide": round(sum(per_slide) / len(per_slide), 1),
            "top_verbs": all_verbs.most_common(6),
            "words_mean": round(sum(r["words"] for r in res) / len(res))}
    return {"deck": deck, "slides": res}
