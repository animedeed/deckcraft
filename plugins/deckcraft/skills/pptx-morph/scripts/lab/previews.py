"""Материалы витрины-опроса: GIF каждого пункта каталога (morphkit.catalog) и карточки палитр.

    python -m lab.previews OUT_DIR [--theme ink] [--lang ru|en]
Выход: OUT/gif/<семейство>_<ключ>.gif (360 px, 8 кадров/с), OUT/palette/<тема>.png, OUT/index.json.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from morphkit import O, Slide  # noqa: E402
from morphkit.catalog import MOTIFS, MOTION, NAVIGATION, TRANSITIONS  # noqa: E402
from morphkit.model import apply_text_policy  # noqa: E402
from morphkit.motion import Canvas, render_transition, save_gif  # noqa: E402
from morphkit.palette import CATALOG  # noqa: E402
from morphkit.i18n import localize, tr  # noqa: E402
from morphkit.qa import fit_text  # noqa: E402

from lab import isolate  # noqa: E402


def palette_card(theme, out: Path, lang: str = "ru") -> Path:
    """Мини-слайд в палитре: заголовок, подпись, акцент, карточка, столбики (как увидит зритель)."""
    objs = [O("t", "text", 0.8, 0.8, 8, 0.9, txt=tr(theme.title, lang), sz=40, b=True, font="head", col="ink"),
            O("s", "text", 0.8, 1.8, 7.2, 1.2, txt=tr(theme.thesis, lang), sz=18, col="ink2"),
            O("c", "rrect", 0.8, 3.4, 5.6, 3.0, fill="surface", ln="line", lw=1, radius=0.14),
            O("ct", "text", 1.1, 3.65, 5.0, 0.6, txt=tr("Карточка", lang), sz=20, b=True, col="ink"),
            O("cm", "text", 1.1, 4.3, 5.0, 1.2, txt=tr(["второстепенный текст", "приглушённый"], lang), sz=16, col="muted")]
    for k, (h, col) in enumerate([(2.6, "accent"), (1.9, "accent2"), (1.4, "accent3"), (0.9, "muted")]):
        objs.append(O(f"b{k}", "rect", 7.4 + k * 1.3, 6.4 - h, 0.9, h, fill=col))
    cv = Canvas(theme, "bg", 640)
    for o in fit_text(objs, theme):
        cv.draw(o.copy(fill=theme.c(o.fill), ln=theme.c(o.ln), col=theme.c(o.col)))
    out.parent.mkdir(parents=True, exist_ok=True)
    cv.frame().save(out)
    return out


def variant_gif(fam: str, key: str, theme, out: Path, w: int = 360, fps: int = 8, lang: str = "ru") -> Path:
    v = next(v for v in importlib.import_module(f"lab.{fam}").variants(theme) if v.key == key)
    slides = apply_text_policy([s.__class__(**{**s.__dict__, "objs": fit_text(s.objs, theme)})
                                for s in localize(isolate(v), lang)], "fade")
    frames = []
    for i, s in enumerate(slides):
        frames += render_transition(slides[i - 1] if i else None, s, theme, fps=fps, w_px=480)
    out.parent.mkdir(parents=True, exist_ok=True)
    return save_gif(frames, out, fps=fps, w=w)


def main() -> None:
    out = Path(sys.argv[1])
    tname = sys.argv[sys.argv.index("--theme") + 1] if "--theme" in sys.argv else "ink"
    lang = sys.argv[sys.argv.index("--lang") + 1] if "--lang" in sys.argv else "ru"
    from morphkit.i18n import set_lang
    set_lang(lang)
    theme = next(p.theme for p in CATALOG if p.theme.name == tname)
    index = {"palettes": [], "gifs": {}}
    for p in CATALOG:
        palette_card(p.theme, out / "palette" / f"{p.theme.name}.png", lang)
        index["palettes"].append({"key": p.theme.name, "title": p.title, "why": p.why, "dark": p.dark,
                                  "png": f"palette/{p.theme.name}.png"})
    seen = set()
    for c in MOTIFS + NAVIGATION + MOTION + TRANSITIONS:
        if not c.preview or c.preview in seen:
            continue
        seen.add(c.preview)
        fam, key = c.preview
        name = f"{fam}_{key}.gif"
        # тематические мотивы — в своей палитре (вино в «Лаборатории» и т.д.), остальное — в выбранной теме
        own = {"f_wine": "lab", "f_energy": "grid", "f_docs": "registry", "f_neural": "neuro", "f_nature": "forest",
               "f_data": "ledger"}.get(fam, tname)
        th = next(p.theme for p in CATALOG if p.theme.name == own)
        variant_gif(fam, key, th, out / "gif" / name, lang=lang)
        index["gifs"][f"{fam}:{key}"] = f"gif/{name}"
        print("gif", name, flush=True)
    from morphkit.combine import ACCENTS
    for key in ACCENTS:  # нативные переходы: приближённое превью на нейтральных разделах (семейство f_nav)
        name = f"f_nav_x_{key}.gif"
        variant_gif("f_nav", f"x_{key}", theme, out / "gif" / name, lang=lang)
        index["gifs"][f"f_nav:x_{key}"] = f"gif/{name}"
        print("gif", name, flush=True)
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
