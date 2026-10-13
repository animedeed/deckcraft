"""Галереи библиотеки движения: каждый из 53 переходов и каждая из 198 анимаций фигур на своём образце.

    python gallery.py OUT_DIR            # transitions_gallery.pptx и fx_gallery.pptx
    python gallery.py OUT_DIR --check    # + проверка XSD и импорта в LibreOffice

Презентации служат справочником «посмотреть глазами» в PowerPoint и тестом движка: каждый пресет собирается,
перенацеливается и проходит схему.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from morphkit import LAB, SLIDE_H, SLIDE_W, TRANSITIONS, Fx, O, Slide, build_pptx  # noqa: E402
from morphkit.components import Kit  # noqa: E402
from morphkit.presets import describe, keys  # noqa: E402

T, K = LAB, Kit(LAB)
CAT_RU = {"entrance": "Вход", "emphasis": "Выделение", "path": "Путь перемещения", "exit": "Выход"}
TR_GROUP = {"": "ISO, все версии", "p14": "PowerPoint 2010+", "p15": "PowerPoint 2013+", "p159": "PowerPoint 2019 / 365"}


def transitions_deck() -> list[Slide]:
    slides = []
    names = list(TRANSITIONS)
    for i, name in enumerate(names):
        prefix, el, attrs = TRANSITIONS[name]
        bg = "bg" if i % 2 == 0 else "surface"
        tile = "accent" if i % 2 == 0 else "accent2"
        objs = K.label(f"Переход {i + 1:02d} / {len(names)} · {TR_GROUP[prefix]}")
        objs += [O("name", "text", 0.9, 2.2, 11.5, 1.4, txt=name, sz=66, font="head", b=True, col="ink"),
                 O("xml", "text", 0.9, 3.75, 11.5, 0.5, sz=16, font="mono", col="ink2",
                   txt=f"<{prefix + ':' if prefix else 'p:'}{el}" + "".join(f' {k}="{v}"' for k, v in attrs.items()) + "/>"),
                 O("tile", "rrect", 9.6, 4.7, 2.8, 1.9, fill=tile, z=2),
                 O("tile2", "oval", 0.9, 5.2, 1.0, 1.0, fill="ink", z=2)]
        slides.append(Slide(objs, bg=bg, transition=name, dur=1600, title=name))
    return slides


def fx_deck() -> list[Slide]:
    slides = []
    cols, rows = 4, 2
    cw, ch = (SLIDE_W - 1.2) / cols, 2.6
    for cat in ("entrance", "emphasis", "path", "exit"):
        ks = keys(cat)
        pages = [ks[j:j + cols * rows] for j in range(0, len(ks), cols * rows)]
        for pi, page in enumerate(pages):
            objs = K.label(f"{CAT_RU[cat]} · {pi + 1} / {len(pages)}") + K.title(f"{CAT_RU[cat]}: {len(ks)} эффектов", size="h2")
            fx = []
            for j, key in enumerate(page):
                d = describe(key)
                cx, cy = 0.6 + (j % cols) * cw, 2.0 + (j // cols) * ch
                tgt = f"s{j}"
                objs += [O(tgt, "rrect", cx + cw / 2 - 0.6, cy + 0.15, 1.2, 1.2, fill="accent" if j % 2 == 0 else "accent2",
                           txt=str(j + 1), sz=22, b=True, col="bg", al="c", va="m", z=10),
                         O(f"n{j}", "text", cx + 0.1, cy + 1.5, cw - 0.2, 0.35, txt=d["name"], sz=15, b=True, al="c", z=12),
                         O(f"k{j}", "text", cx + 0.1, cy + 1.85, cw - 0.2, 0.3, txt=key, sz=11, font="mono", col="muted",
                           al="c", z=12)]
                kw = {}
                if cat == "path":
                    kw = {"path_size": (1.1, 1.1) if key not in ("path_left", "path_right", "path_up", "path_down") else None,
                          "rev": True}
                    kw = {k: v for k, v in kw.items() if v is not None}
                fx.append(Fx(key, tgt, start="after" if j else "at", delay=0.25 if j else 0.3,
                             dur=None if cat != "emphasis" else 1.0, **kw))
            slides.append(Slide(objs, transition="fade", dur=500, fx=fx, title=f"{cat} {pi + 1}"))
    return slides


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    tr = build_pptx(transitions_deck(), T, out / "transitions_gallery.pptx", title="Галерея переходов")
    fx = build_pptx(fx_deck(), T, out / "fx_gallery.pptx", title="Галерея анимаций")
    print(tr["path"], len(tr["slides"]), "слайдов;", fx["path"], len(fx["slides"]), "слайдов,",
          sum(s["fx"] for s in fx["slides"]), "эффектов")
    if "--check" in sys.argv:
        from morphkit.qa import xsd_check
        for p in (tr["path"], fx["path"]):
            errs = xsd_check(p)
            print(Path(p).name, "XSD:", len(errs), "ошибок", *errs[:5], sep="\n  " if errs else " ")


if __name__ == "__main__":
    main()
