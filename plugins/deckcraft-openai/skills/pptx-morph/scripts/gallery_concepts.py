"""Галерея концептов: роли сквозного мотива (цветок, орбита) и глаголы процесса (носитель через трансформации).

    python gallery_concepts.py OUT_DIR [theme] [--check]     # theme — имя из каталога палитр (ink, lab, neuro …)

Слайды 1–8 — цветок проходит все роли; 9–13 — фраза проходит процесс «как модель находит ошибку» (пример
грамматики, не готовая лекция); 14–16 — орбита: указатель, прогресс, портал.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from morphkit import Fx, O, Slide, build_pptx  # noqa: E402
from morphkit import recipes as R  # noqa: E402
from morphkit.motif import Flower, MotifTrack, Orbit  # noqa: E402
from morphkit.palette import CATALOG  # noqa: E402
from morphkit.process import Carrier, Item  # noqa: E402
from morphkit.profile import DeckProfile  # noqa: E402


def T(txt, x, y, w, h, sz=18, name=None, **kw) -> O:
    return O(name or f"!!t{abs(hash((txt if isinstance(txt, str) else ''.join(txt), x, y))) % 10**6}", "text", x, y, w,
             h, txt=txt, sz=sz, z=90, **kw)


def head(label: str, title: str, x: float = 3.1) -> list[O]:
    return [O("!!lbl", "text", x, 0.55, 9.5, 0.35, txt=label, sz=12, b=True, caps=True, tracking=1.2, col="accent", z=90),
            O(f"!!ttl", "text", x, 0.9, 9.8, 0.7, txt=title, sz=28, b=True, font="head", col="ink", z=90)]


def deck(theme) -> list:
    fl = MotifTrack(Flower("fl", petals=8, length=2.9, width=1.12), theme)
    S = []
    # 1. hero
    S.append(Slide(fl.at("hero", center=(9.3, 3.75)) + [
        O("!!ttl", "text", 0.8, 2.3, 6.2, 1.6, txt=["Сквозной мотив", "в шести ролях"], sz=40, b=True, font="head",
          col="ink", z=90),
        O("!!sub", "text", 0.8, 4.0, 6.0, 0.9, txt="Один и тот же цветок ведёт всю презентацию: обложка, указатель, фон, "
          "диаграмма, портал, прогресс", sz=17, col="ink2", z=90)],
        transition="fade", dur=500, fx=R.mandala_spin_in("fl", 8, delay=0.1, step=0.05),
        layout="cover", title="hero"))
    # 2. pointer
    for k, (lbl, ttl) in enumerate([("01 · указатель", "Лепесток раздела смотрит на тему"),
                                    ("02 · указатель", "Следующий раздел — поворот на один лепесток")]):
        S.append(Slide(fl.at("pointer", k=k) + head(lbl, ttl) + [
            T("Цветок наполовину за краем: он не мешает тексту и показывает, где мы. Поворот всегда < 180° — "
              "Morph не крутит назад.", 3.1, 1.9, 8.5, 1.0, sz=17, col="ink2", name="!!body")],
            dur=900, layout="section", technique="указатель", title=f"pointer {k}"))
    # 3. data
    vals = [0.142, 0.093, 0.054, 0.047, 0.041, 0.034, 0.028, 0.021]
    labs = ["плотность", "сахар", "летуч. кисл.", "спирт", "тип вина", "общ. SO₂", "сульфаты", "своб. SO₂"]
    labs = [f"{n}  +{v:.3f}".replace(".", ",") for n, v in zip(labs, vals)]
    S.append(Slide(fl.at("data", values=vals, labels=labs, focus=0, center=(9.0, 4.6), scale=0.82) +
                   head("данные", "Лепестки = значения: цветок становится диаграммой", x=0.8) +
                   [T(["Длина лепестка — рост ошибки", "при перемешивании признака"], 0.8, 1.9, 4.0, 1.0, sz=16,
                      col="ink2", name="!!body")],
                   dur=900, layout="chart-radial", technique="мотив → диаграмма", title="data"))
    # 4. backdrop
    for t in range(2):
        S.append(Slide(fl.at("backdrop", t=t) + head("фон", "Мотив под содержимым: бледный и медленный", x=0.8) + [
            O(f"!!card{t}", "rrect", 0.8, 2.0, 5.6, 3.6, fill="surface", ln="line", lw=1, radius=0.14, z=60),
            T(["Фон дрейфует на 7° за слайд —", "презентация «дышит», а текст", "читается: прозрачность 10 %"],
              1.1, 2.3, 5.0, 2.0, sz=18, col="ink", name=f"!!cardt{t}")],
            dur=800, layout="panel", technique="фон-дрейф", title=f"backdrop {t}"))
    # 5. portal
    S.append(Slide(fl.at("portal") + [T("Полёт внутрь", 0.8, 3.2, 12, 1.0, sz=40, b=True, font="head", col="ink",
                                         name="!!portal_t", al="c")],
                   dur=1100, layout="portal", technique="портал", title="portal"))
    # 6. progress
    S.append(Slide(fl.at("progress", k=3) + head("прогресс", "Раскрыто 4 лепестка из 8 — четвёртый раздел", x=0.8) +
                   [T("Навигатор в углу: закрытые лепестки — бутоны, видно, сколько осталось", 0.8, 1.9, 8.5, 0.6,
                      sz=17, col="ink2", name="!!body")],
                   dur=900, layout="section", technique="прогресс", title="progress"))
    # 7. seed
    S.append(Slide(fl.at("seed", center=(6.67, 4.6)) + [T(["Пауза: мотив свернулся", "в точку"], 0.8, 2.4, 11.7, 1.5,
                                                            sz=34, b=True, font="head", col="ink", al="c",
                                                            name="!!seed_t")],
                   dur=900, layout="statement", technique="свёртка", title="seed"))
    # 8. hero again (bloom)
    S.append(Slide(fl.at("hero", center=(6.67, 3.9), scale=0.95) + [
        T("Рифма начала и конца", 0.8, 0.5, 11.7, 0.7, sz=28, b=True, font="head", col="ink", al="c", name="!!fin")],
        dur=1000, layout="recap", technique="раскрытие", title="bloom"))

    # 9–13. процесс: носитель = токены фразы
    words = ["Капремонт", "ВЛ", "проводится", "не", "реже", "1", "раза", "в", "12", "лет"]
    c = Carrier("tk", [Item(w, flag=(w == "12")) for w in words], sz=20)
    X, Y = 0.9, 3.0
    S.append(Slide(head("процесс · split", "Фраза → токены", x=0.9) + c.row(X, Y),
                   dur=800, layout="process", technique="разбиение", title="split",
                   fx=[Fx("entrance_wipe", f"!!tk{i}", start="at", delay=0.15 + 0.05 * i, dur=0.3,
                          options={"direction": "left"}) for i in range(len(words))]))
    S.append(Slide(head("процесс · encode", "Каждый токен → вектор чисел", x=0.9) + c.vectors(X, 2.2, dims=6,
                                                                                               theme=theme),
                   dur=900, layout="process", technique="кодирование", title="encode"))
    pairs = [(0, 8, 0.5), (2, 8, 0.9), (4, 8, 0.7), (8, 9, 1.0), (3, 4, 0.6)]
    S.append(Slide(head("процесс · relate", "Внимание: какие слова смотрят на «12»", x=0.9) + c.row(X, Y) +
                   c.links(pairs, X, Y, height=1.0),
                   dur=900, layout="process", technique="дуги", title="relate",
                   fx=[Fx("entrance_wipe", f"!!tk_l{a}_{b}", start="at", delay=0.2 + 0.1 * k, dur=0.35,
                          options={"direction": "up"}) for k, (a, b, _) in enumerate(pairs)]))
    probs = [0.05, 0.08, 0.04, 0.22, 0.18, 0.12, 0.06, 0.03, 0.93, 0.31]
    S.append(Slide(head("процесс · score", "Оценка: вероятность ошибки для каждого токена", x=0.9) +
                   c.bars(X, 5.4, probs, max_h=2.6, threshold=0.5),
                   dur=900, layout="process", technique="столбики", title="score"))
    S.append(Slide(head("процесс · flag", "Найдено: «12» расходится с новой редакцией", x=0.9) +
                   c.row(X, Y, flagged=True, dim_others=True),
                   dur=800, layout="process", technique="флаг", title="flag", loops=c.flag_loops()))

    # 14–16. орбита
    orb = MotifTrack(Orbit("or", rings=5), theme)
    S.append(Slide(orb.at("pointer", k=1) + head("орбита · указатель",
                                                                                 "Тело раздела выходит на ось"),
                   dur=900, layout="section", technique="указатель-орбита", title="orbit pointer"))
    S.append(Slide(orb.at("pointer", k=3) + head("орбита · прогресс",
                                                                                  "Следующий раздел — система сдвигается к краю"),
                   dur=900, layout="section", technique="орбита-сдвиг", title="orbit pointer 2"))
    S.append(Slide(orb.at("portal", center=(6.67, 3.75), scale=1.0) + [T("Внутрь солнца", 0.8, 3.2, 11.7, 1.0, sz=40,
                                                                          b=True, font="head", col="ink", al="c",
                                                                          name="!!or_t")],
                   dur=1100, layout="portal", technique="портал-орбита", title="orbit portal"))
    return S


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    name = next((a for a in sys.argv[2:] if not a.startswith("--")), "ink")
    theme = next(p.theme for p in CATALOG if p.theme.name == name)
    from morphkit.qa import fit_text
    slides = [replace(sl, objs=fit_text(sl.objs, theme)) for sl in deck(theme)]
    prof = DeckProfile(name="concepts", concept="галерея ролей мотива и глаголов процесса", theme=theme.name)
    r = build_pptx(slides, theme, out / f"concepts_{name}.pptx", title="Концепты: мотив и процесс", profile=prof)
    print(r["path"], len(slides))
    if "--check" in sys.argv:
        from morphkit.qa import lint, print_issues, xsd_check
        print_issues(lint(slides, theme, profile=prof))
        errs = xsd_check(r["path"])
        print("XSD:", len(errs), *errs[:5])


if __name__ == "__main__":
    main()
