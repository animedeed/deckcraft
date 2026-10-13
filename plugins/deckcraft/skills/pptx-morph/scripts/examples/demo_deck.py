"""Демо /deck-build: презентация с нуля по брифу «Как нейросеть находит опечатку в тексте» (лекция, 10 мин).

    python examples/demo_deck.py OUT_DIR [--no-render]

Бриф (auto_brief + правка смыслом, см. demo_storyboard.md): палитра «Нейросеть», мотив «нейросеть и токены»,
навигация «метка блока + счётчик», между разделами — сеть переезжает (камера), у разделов свой язык движения:
1 фрагменты (фраза → фишки → векторы), 2 сигнал по связям (волна по слоям, нейрон по спирали), 3 лупа (дуги
внимания, сканер), 4 рост (вероятности, softmax), 5 фон (сеть под выводами). Носитель — одни и те же 7 фишек.
Сцены — формы лаборатории lab/f_neural.py; здесь только сборка презентации, навигация, заметки и проверка.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from morphkit import build_pptx  # noqa: E402
from morphkit.palette import CATALOG  # noqa: E402
from morphkit.profile import DeckProfile  # noqa: E402
from morphkit.qa import (contact_sheet, fit_text, lint, lo_effects_check, motion_lint, print_issues, render,  # noqa: E402
                         xsd_available, xsd_check)
from morphkit import O, Slide  # noqa: E402
from morphkit.combine import transition_pattern  # noqa: E402
from morphkit.i18n import localize, set_lang, tr  # noqa: E402
from morphkit.recipes import agenda, block_counter, menu_bar  # noqa: E402

from lab import f_neural as N  # noqa: E402

BLOCKS = ["Текст", "Слои", "Внимание", "Исправление", "Итог"]

# (блок или None для обложки, сцена, макет, приём на переходе К слайду, заметки)
PLAN = [
    (None, ("seq", 0), "обложка-носитель", "", "Фраза с ошибкой согласования: «Вчера мы с братом пошёл в кино». "
     "Эти семь слов пройдут через всю лекцию."),
    (0, ("seq", 1), "носитель-столбцы", "фишки → векторы", "Сеть не читает буквы: каждое слово становится "
     "вектором — столбиком чисел. Оттенок ячейки — значение."),
    (1, ("seq", 2), "схема-сеть", "векторы → входы (камера)", "Векторы сжимаются во входы сети."),
    (1, ("seq", 3), "схема-сеть", "волна по слоям (серия)", "Сигнал идёт слой за слоем — прямой проход."),
    (1, ("zoom", 0), "схема-деталь", "сеть отъезжает влево", "Посмотрим на один нейрон второго слоя."),
    (1, ("zoom", 1), "схема-деталь", "нейрон по спирали (серия)", "Нейрон — взвешенная сумма входов: "
     "толщина входа — вес."),
    (1, ("zoom", 2), "схема-деталь", "активация (серия)", "Затем плавный порог — активация."),
    (2, ("seq", 4), "дуги-над-строкой", "входы → строка (камера)", "Механизм внимания: слово «пошёл» смотрит "
     "на все слова фразы; толщина дуги — вес связи."),
    (2, ("seq", 5), "дуги-над-строкой", "сканер и красная дуга (серия)", "Подлежащее «мы» во множественном числе, "
     "глагол — в единственном. Связь «пошёл → мы» краснеет: ошибка найдена."),
    (3, ("prob", 1), "столбики-над-строкой", "столбики вероятности", "Сеть оценивает каждое слово: у «пошёл» "
     "вероятность ошибки высокая. Значения условные — важна форма."),
    (3, ("soft", 0), "кандидаты", "строка опускается, кандидаты", "Кандидаты на замену."),
    (3, ("soft", 1), "кандидаты", "softmax (серия)", "Softmax превращает оценки в вероятности."),
    (3, ("soft", 2), "кандидаты", "победитель встаёт в строку (серия)", "Победитель встаёт на место ошибки, "
     "соседние слова раздвигаются."),
    (4, ("back", 0), "текст-на-фоне", "сеть уходит в фон (камера)", "Где это помогает редактору."),
    (4, ("back", 1), "текст-на-фоне", "волна в фоне (серия)", "Что остаётся человеку."),
    (None, ("seq", 7), "финал-носитель", "фраза возвращается", "Сеть видит связи между словами, решение — за "
     "человеком."),
]


DEFAULT_VARIANT = {"label": "A", "palette": "neuro", "motif": "neural", "navigation": "counter", "transition": {"main": "morph", "accents": []}}


def _nav(nav: str, blk: int, page: int, total: int) -> list:
    """Навигация варианта на слайде раздела blk. Одна система на презентацию (structure.md)."""
    if nav == "menu":
        return menu_bar("nav", BLOCKS, blk, y=0.16, sz=12)
    if nav == "agenda":
        return agenda("ag", BLOCKS, state="bar", k=blk)
    return block_counter("nav", f"{tr('Блок')} {blk + 1} — {tr(BLOCKS[blk])}", page, total, y=0.18)


def build(out: Path, render_png: bool = True, variant: dict | None = None, gifs: bool = False,
          lang: str = "ru") -> dict:
    set_lang(lang)
    N.use_lang(lang)
    """variant — один вариант из morphkit.combine.plan_variants: palette, navigation, transition{main, accents}."""
    v = {**DEFAULT_VARIANT, **(variant or {})}
    theme = next(p.theme for p in CATALOG if p.theme.name == v["palette"])
    scenes = {"seq": N.seq_neural(theme).slides, "zoom": N.neuron_zoom(theme).slides,
              "prob": N.prob_bars(theme).slides, "soft": N.softmax_fix(theme).slides,
              "back": N.net_backdrop(theme).slides}
    plan = list(PLAN)
    if v["navigation"] == "agenda":  # карта доклада после обложки и перед финалом (все разделы пройдены)
        plan.insert(1, ("map", 0, "карта-доклада", "фраза уходит, карта", "План лекции: пять блоков."))
        plan.insert(len(plan) - 1, ("map", len(BLOCKS), "карта-доклада", "все блоки пройдены", "Всё, что мы прошли."))
    total = len(plan)
    # узор переходов: граница = вход в следующий блок; финал считается последней «главой»
    starts = [n for n, row in enumerate(plan) if n and row[0] not in (None, "map") and plan[n - 1][0] != row[0]
              and isinstance(row[0], int)] + [len(plan) - 1]
    pattern = transition_pattern(len(starts) + 1, "morph", v["transition"].get("accents") or [])
    trans_at = dict(zip(starts, pattern))
    slides = []
    for page, (blk, src_k, layout, tech, notes) in enumerate(plan, start=1):
        if blk == "map":
            s = Slide(agenda("ag", BLOCKS, state="map", k=src_k, y=2.4, h=2.2, sz=20)
                      + [O("!!ttl", "text", 0.7, 0.62, 8, 0.75, txt=tr("План лекции" if src_k == 0 else "Что мы прошли"),
                           sz=30, b=True, font="head", col="ink", z=90)], dur=800)
            blk_title = "карта"
        else:
            src, k = src_k
            s = scenes[src][k]
            blk_title = tr(BLOCKS[blk]) if blk is not None else tr("обложка/финал")
        objs = [o for o in s.objs if o.name != "!!kick"]  # метка раздела — у навигации, а не у сцены
        if isinstance(blk, int):
            top = 0.86 if v["navigation"] in ("menu", "agenda") else 0.62
            objs = [o.copy(y=max(o.y, top)) if o.name == "!!ttl" else o for o in objs]
            objs += _nav(v["navigation"], blk, page, total)
        t = trans_at.get(page - 1, "morph")
        objs = localize([replace(s, objs=objs)])[0].objs  # надписи сцен — на языке презентации
        slides.append(replace(s, objs=fit_text(objs, theme), layout=layout, notes=tr(notes),
                              technique=tr(tech) if t == "morph" else f"{tr(tech)} · {t}",
                              transition=t, dur=s.dur if t == "morph" else 600,
                              title=f"{page:02d} {blk_title}"))
    out.mkdir(parents=True, exist_ok=True)
    prof = DeckProfile(name=f"demo-neural-{v['label']}", concept="одна фраза проходит через сеть", theme=theme.name,
                       motion="technical")
    prof.save(out / "deck_profile.json")
    issues = lint(slides, theme, profile=prof)
    errors = [i for i in issues if i["level"] == "error"]
    print_issues(errors)
    mlint = motion_lint(slides, theme)
    print_issues(mlint)
    r = build_pptx(slides, theme, out / f"demo_neural_{v['label']}.pptx", title=tr("Как нейросеть находит опечатку"), profile=prof)
    report = {"variant": v, "pptx": str(r["path"]), "slides": len(slides), "lint_errors": len(errors),
              "lint_warnings": len([i for i in issues if i["level"] == "warn"]), "motion_lint": len(mlint),
              "xsd": len(xsd_check(r["path"])) if xsd_available() else "пропущена (нет схем)"}
    eff = lo_effects_check(r["path"])
    report["effects"] = {k: eff.get(k) for k in ("pptx", "odp", "custom_paths", "ok")}
    if render_png:
        pngs = render(r["path"], out / "png")
        contact_sheet(pngs, out / "sheet.png", titles=[s.title for s in slides], cols=4)
        report["sheet"] = str(out / "sheet.png")
    if gifs:  # одни и те же моменты у всех вариантов — для страницы сравнения
        from morphkit.model import apply_text_policy
        from morphkit.motion import render_transition, save_gif
        pol = apply_text_policy(slides, prof.text_policy)
        first = {}
        for n, sl in enumerate(slides):
            first.setdefault(sl.title.split(" ", 1)[1], n)
        moments = {"layers": first.get(tr("Слои")), "attention": first.get(tr("Внимание"), 0) + 1, "finale": len(slides) - 1}
        (out / "gif").mkdir(exist_ok=True)
        report["gifs"] = {}
        for name, n in moments.items():
            if n:
                fr = render_transition(pol[n - 1], pol[n], theme, fps=10, w_px=560)
                save_gif(fr, out / "gif" / f"{name}.gif", fps=10, w=480)
                report["gifs"][name] = f"gif/{name}.gif"
        report["pattern"] = [sl.transition for sl in slides]
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(json.dumps(report, ensure_ascii=False))
    report["passed"] = (report["lint_errors"] == 0 and report["motion_lint"] == 0 and report["xsd"] in (0, "пропущена (нет схем)")
                        and eff.get("ok") is not False)
    return {"slides": slides, "theme": theme, "report": report}


if __name__ == "__main__":
    # python examples/demo_deck.py OUT [--no-render] [--gifs] [--variant '{"palette": "ink", "navigation": "menu", ...}']
    var = json.loads(sys.argv[sys.argv.index("--variant") + 1]) if "--variant" in sys.argv else None
    lang = sys.argv[sys.argv.index("--lang") + 1] if "--lang" in sys.argv else "ru"
    res = build(Path(sys.argv[1]), render_png="--no-render" not in sys.argv, variant=var, gifs="--gifs" in sys.argv,
                lang=lang)
    sys.exit(0 if res["report"]["passed"] else 1)
