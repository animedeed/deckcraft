"""Демо /deck-build: колода с нуля по брифу «Как нейросеть находит опечатку в тексте» (лекция, 10 мин).

    python examples/demo_deck.py OUT_DIR [--no-render]

Бриф (auto_brief + правка смыслом, см. demo_storyboard.md): палитра «Нейросеть», мотив «нейросеть и токены»,
навигация «метка блока + счётчик», между разделами — сеть переезжает (камера), у разделов свой язык движения:
1 фрагменты (фраза → фишки → векторы), 2 сигнал по связям (волна по слоям, нейрон по спирали), 3 лупа (дуги
внимания, сканер), 4 рост (вероятности, softmax), 5 фон (сеть под выводами). Носитель — одни и те же 7 фишек.
Сцены — формы лаборатории lab/f_neural.py; здесь только сборка колоды, навигация, заметки и проверка.
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
from morphkit.recipes import block_counter  # noqa: E402

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


def build(out: Path, render_png: bool = True) -> dict:
    theme = next(p.theme for p in CATALOG if p.theme.name == "neuro")
    scenes = {"seq": N.seq_neural(theme).slides, "zoom": N.neuron_zoom(theme).slides,
              "prob": N.prob_bars(theme).slides, "soft": N.softmax_fix(theme).slides,
              "back": N.net_backdrop(theme).slides}
    total = len(PLAN)
    slides = []
    for page, (blk, (src, k), layout, tech, notes) in enumerate(PLAN, start=1):
        s = scenes[src][k]
        objs = [o for o in s.objs if o.name != "!!kick"]  # метка раздела — у навигации, а не у сцены
        if blk is not None:
            objs = [o.copy(y=max(o.y, 0.62)) if o.name == "!!ttl" else o for o in objs]
            objs += block_counter("nav", f"Блок {blk + 1} — {BLOCKS[blk]}", page, total, y=0.18)
        slides.append(replace(s, objs=fit_text(objs, theme), layout=layout, technique=tech, notes=notes,
                              title=f"{page:02d} {BLOCKS[blk] if blk is not None else 'обложка/финал'}"))
    out.mkdir(parents=True, exist_ok=True)
    prof = DeckProfile(name="demo-neural", concept="одна фраза проходит через сеть", theme=theme.name,
                       motion="technical")
    prof.save(out / "deck_profile.json")
    issues = lint(slides, theme, profile=prof)
    errors = [i for i in issues if i["level"] == "error"]
    print_issues(errors)
    mlint = motion_lint(slides, theme)
    print_issues(mlint)
    r = build_pptx(slides, theme, out / "demo_neural.pptx", title="Как нейросеть находит опечатку", profile=prof)
    report = {"pptx": str(r["path"]), "slides": len(slides), "lint_errors": len(errors),
              "lint_warnings": len([i for i in issues if i["level"] == "warn"]), "motion_lint": len(mlint),
              "xsd": len(xsd_check(r["path"])) if xsd_available() else "пропущена (нет схем)"}
    eff = lo_effects_check(r["path"])
    report["effects"] = {k: eff.get(k) for k in ("pptx", "odp", "custom_paths", "ok")}
    if render_png:
        pngs = render(r["path"], out / "png")
        contact_sheet(pngs, out / "sheet.png", titles=[s.title for s in slides], cols=4)
        report["sheet"] = str(out / "sheet.png")
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(json.dumps(report, ensure_ascii=False))
    report["passed"] = (report["lint_errors"] == 0 and report["motion_lint"] == 0 and report["xsd"] in (0, "пропущена (нет схем)")
                        and eff.get("ok") is not False)
    return {"slides": slides, "theme": theme, "report": report}


if __name__ == "__main__":
    res = build(Path(sys.argv[1]), render_png="--no-render" not in sys.argv)
    sys.exit(0 if res["report"]["passed"] else 1)
