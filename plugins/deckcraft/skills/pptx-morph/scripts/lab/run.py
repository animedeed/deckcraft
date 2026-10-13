"""Прогон лаборатории: сборка .pptx семейства, lint, XSD, кадры движения и листы миниатюр.

    python -m lab.run f_venn OUT [--theme ink] [--fast]     # из папки scripts; семейство или all
Выход: OUT/<семейство>/<семейство>.pptx, sheet.png (последние состояния), motion/<key>_<i>.png (ленты переходов),
report.json (lint, XSD, число вариантов).
"""

from __future__ import annotations

import importlib
import json
import pkgutil
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from morphkit import build_pptx  # noqa: E402
from morphkit.motion import render_transition, strip  # noqa: E402
from morphkit.palette import CATALOG  # noqa: E402
from morphkit.profile import DeckProfile  # noqa: E402
from morphkit.qa import contact_sheet, fit_text, lint, render, xsd_check  # noqa: E402
from morphkit.model import apply_text_policy  # noqa: E402

from lab import caption, isolate  # noqa: E402


def families() -> list[str]:
    return sorted(m.name for m in pkgutil.iter_modules([str(Path(__file__).parent)]) if m.name.startswith("f_"))


def run(fam: str, out: Path, theme_name: str = "ink", fast: bool = False, motion: bool = True) -> dict:
    theme = next(p.theme for p in CATALOG if p.theme.name == theme_name)
    mod = importlib.import_module(f"lab.{fam}")
    vs = mod.variants(theme)
    od = out / fam
    (od / "motion").mkdir(parents=True, exist_ok=True)
    slides, index = [], []
    for v in vs:
        for k, s in enumerate(isolate(v)):
            s2 = replace(s, objs=fit_text(s.objs, theme) + caption(v, k), title=f"{v.key}:{k}")
            slides.append(s2)
            index.append((v, k))
    prof = DeckProfile(name=f"lab-{fam}", concept="лаборатория", theme=theme.name)
    r = build_pptx(slides, theme, od / f"{fam}.pptx", title=f"lab {fam}", profile=prof)
    issues = lint(slides, theme, profile=prof)
    errs = [i for i in issues if i["level"] == "error"]
    xsd = xsd_check(r["path"])
    rep = {"family": fam, "variants": len(vs), "slides": len(slides), "lint_errors": [f"{i['slide']}: {i['msg']}" for i in errs],
           "lint_warn": len(issues) - len(errs), "xsd": xsd[:5],
           "list": [{"key": v.key, "title": v.title, "idea": v.idea, "tags": v.tags, "score": v.score} for v in vs]}
    pngs = render(r["path"], od / "png", dpi=40 if fast else 55)
    last = [pngs[i] for i, (v, k) in enumerate(index) if k == len(v.slides) - 1]
    contact_sheet(last, od / "sheet.png", titles=[f"{v.key}" for v in vs], cols=4)
    if motion:
        pol = apply_text_policy(slides, prof.text_policy)
        for i, (v, k) in enumerate(index):
            if k == 0:
                continue
            fr = render_transition(pol[i - 1], pol[i], theme, fps=8 if fast else 10, w_px=520 if fast else 640)
            strip(fr, 6, od / "motion" / f"{v.key}_{k}.png", label=f"{v.key} {k}→{k + 1}: {v.title}")
    (od / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    return rep


def main() -> None:
    fam, out = sys.argv[1], Path(sys.argv[2])
    theme = sys.argv[sys.argv.index("--theme") + 1] if "--theme" in sys.argv else "ink"
    fams = families() if fam == "all" else [fam]
    for f in fams:
        rep = run(f, out, theme, fast="--fast" in sys.argv, motion="--no-motion" not in sys.argv)
        print(f, rep["variants"], "вариантов; lint ошибок", len(rep["lint_errors"]), "; XSD", len(rep["xsd"]))
        for e in rep["lint_errors"][:10]:
            print("   ", e)


if __name__ == "__main__":
    main()
