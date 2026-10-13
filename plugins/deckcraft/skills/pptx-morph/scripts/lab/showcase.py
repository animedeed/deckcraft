"""Витрина: лучшие варианты лаборатории в одной презентации + GIF каждого приёма (для опроса плагина).

    python -m lab.showcase OUT_DIR SELECTION.json [--theme ink]
SELECTION.json: [{"family": "f_venn", "key": "explode", "group": "Фрагменты"}, ...] — порядок = порядок в презентации.
Перед каждой группой — титульный слайд группы; у каждого варианта внизу подпись «что это и где применять».
"""

from __future__ import annotations

import importlib
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from morphkit import O, Slide, build_pptx  # noqa: E402
from morphkit.model import apply_text_policy  # noqa: E402
from morphkit.motion import render_transition, save_gif  # noqa: E402
from morphkit.palette import CATALOG  # noqa: E402
from morphkit.profile import DeckProfile  # noqa: E402
from morphkit.qa import fit_text, lint, motion_lint, print_issues, xsd_check  # noqa: E402

from lab import isolate  # noqa: E402


def group_slide(title: str, sub: str, n: int) -> Slide:
    return Slide([O("sc_gnum", "text", 0.9, 2.4, 11.5, 0.6, txt=f"{n:02d}", sz=20, b=True, col="accent", z=90),
                  O("sc_gttl", "text", 0.9, 2.95, 11.5, 1.0, txt=title, sz=40, b=True, font="head", col="ink", z=90),
                  O("sc_gsub", "text", 0.9, 4.05, 11.0, 0.9, txt=sub, sz=18, col="ink2", z=90)],
                 transition="fade", dur=500, layout="section", title=title)


def build(selection: list[dict], out: Path, theme_name: str = "ink", gifs: bool = True) -> Path:
    theme = next(p.theme for p in CATALOG if p.theme.name == theme_name)
    cache, gif_jobs = {}, []
    slides = [Slide([O("sc_t1", "text", 0.9, 2.3, 11.5, 1.3, txt="Лаборатория форм и движения", sz=44, b=True, font="head",
                       col="ink", z=90),
                     O("sc_t2", "text", 0.9, 3.65, 11.0, 1.2, sz=18, col="ink2", z=90,
                       txt=["Отбор из 309 вариантов: 25 семейств фигур, ~110 операторов движения,",
                            "41 живая последовательность. Каждый приём — с подсказкой, где он работает в презентации."])],
                    transition="fade", dur=500, layout="cover", title="витрина")]
    group, gi = None, 0
    for item in selection:
        fam = item["family"]
        if fam not in cache:
            cache[fam] = {v.key: v for v in importlib.import_module(f"lab.{fam}").variants(theme)}
        v = cache[fam][item["key"]]
        if item.get("group") != group:
            group, gi = item.get("group"), gi + 1
            gs = group_slide(group, item.get("group_sub", ""), gi)
            slides.append(replace(gs, objs=fit_text(gs.objs, theme)))
        start = len(slides)
        for k, s in enumerate(isolate(v)):
            cap = O(f"sc_cap_{fam}_{v.key}_{k}", "text", 0.5, 6.7, 12.3, 0.78, txt=f"{v.title} — {v.idea}", sz=12,
                    col="muted", z=999, meta={"overlap_ok": True})
            slides.append(replace(s, objs=fit_text(s.objs + [cap], theme), title=f"{fam}:{v.key}:{k}",
                                  notes=f"{v.title}. {v.idea}"))
        gif_jobs.append((fam, v.key, start, len(v.slides)))
    out.mkdir(parents=True, exist_ok=True)
    prof = DeckProfile(name="showcase", concept="витрина лаборатории форм", theme=theme.name)
    r = build_pptx(slides, theme, out / "showcase.pptx", title="Лаборатория форм и движения", profile=prof)
    issues = lint(slides, theme, profile=prof)
    print_issues([i for i in issues if i["level"] == "error"])
    print_issues(motion_lint(slides, theme))
    print("XSD:", len(xsd_check(r["path"])))
    if gifs:
        pol = apply_text_policy(slides, prof.text_policy)
        (out / "gif").mkdir(exist_ok=True)
        for fam, key, start, n in gif_jobs:
            frames = []
            for i in range(start, start + n):
                frames += render_transition(pol[i - 1] if i > start else None, pol[i], theme, fps=12, w_px=640)
            save_gif(frames, out / "gif" / f"{fam}_{key}.gif", fps=12, w=560)
    return r["path"]


def main() -> None:
    out, sel = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text())
    theme = sys.argv[sys.argv.index("--theme") + 1] if "--theme" in sys.argv else "ink"
    print(build(sel, out, theme, gifs="--no-gif" not in sys.argv))


if __name__ == "__main__":
    main()
