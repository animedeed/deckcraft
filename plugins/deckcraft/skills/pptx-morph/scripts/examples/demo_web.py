"""Web demo (deckcraft 0.3.0): the /deck-build demo presentation as one interactive HTML file + its .pptx twin.

    python examples/demo_web.py OUT_DIR [--lang ru|en] [--shots]

The same slides as examples/demo_deck.py (one sentence goes through a neural network) get a web layer: the menu is
clickable, every section has its own title entrance, two web-only slides — buttons that switch the state of the
chart (the bars spring to new heights) and hand annotations (circle, arrow, handwriting, stamp) — and confetti on the
finale. The .pptx twin is built from the same slides with the interactivity folded into its default state.
--shots: Playwright snapshots of every slide and the console check (0 errors expected).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE)]

import demo_deck as DD  # noqa: E402
from lab import f_neural as N  # noqa: E402
from morphkit import O, Slide, build_pptx  # noqa: E402
from morphkit import draw as d  # noqa: E402
from morphkit.html import alt, export_html, for_pptx, link, web  # noqa: E402
from morphkit.i18n import localize, tr  # noqa: E402
from morphkit.qa import fit_text, lint, xsd_available, xsd_check  # noqa: E402
from morphkit.variety import report as variety  # noqa: E402

# each section speaks its own motion language: here — how its titles enter
TITLE_FX = {None: ("in.registration", 0.9), 0: ("in.letters", 0.7), 1: ("in.scramble", 0.7), 2: ("in.blur", 0.6),
            3: ("in.wave-letters", 0.75), 4: ("in.rise", 0.55)}
TX = {
    "ru": {"btn_t": "Кнопки и состояния", "btn_sub": "нажмите: до обучения ↔ после — столбики переезжают пружиной",
           "before": "до обучения", "after": "после", "p": "вероятность ошибки", "ann_t": "Пометки от руки",
           "ann_sub": "рисуются по линии: обвести, стрелка, надпись, печать", "stamp": "ИСПРАВЛЕНО · ПРОВЕРЕНО ·", "stamp_c": "OK",
           "note": "согласовать с «мы»", "title": "Как нейросеть находит опечатку", "back": "в начало"},
    "en": {"btn_t": "Buttons and states", "btn_sub": "click: before training ↔ after — the bars spring to new heights",
           "before": "before training", "after": "after", "p": "error probability", "ann_t": "Hand annotations",
           "ann_sub": "drawn along the line: circle, arrow, handwriting, stamp", "stamp": "FIXED · CHECKED · FIXED · CHECKED ·", "stamp_c": "OK",
           "note": "must agree with “kids”", "title": "How a neural network finds a typo", "back": "to the start"},
}


def _title(text: str, sub: str) -> list[O]:
    return [O("!!ttl", "text", 0.7, 0.86, 11.5, 0.75, txt=text, sz=30, b=True, font="head", col="ink", z=90),
            O("!!wsub", "text", 0.7, 1.55, 11.5, 0.4, txt=sub, sz=15, col="muted", z=90)]


def _buttons_slide(theme, L, nav) -> Slide:
    """Chips + bars: two states of the model, switched by buttons (alt: the bars spring; when: the numbers swap)."""
    y = 5.6
    lay = N.chips_layout(theme, N.WORDS, 1.2, y)
    before = [0.31, 0.27, 0.22, 0.30, 0.34, 0.24, 0.28]
    after = [0.03, 0.05, 0.02, 0.06, 0.91, 0.03, 0.04]
    objs = nav + _title(L["btn_t"], L["btn_sub"]) + N.chips(theme, N.WORDS, lay, y, flagged=N.ERR)
    base, top = y - 0.25, 2.3
    for i, (x, w) in enumerate(lay):
        cx, bw = x + w / 2, min(0.7, w * 0.7)
        h0, h1 = (base - top) * before[i], (base - top) * after[i]
        bar = O(f"!!wb{i}", "rrect", cx - bw / 2, base - h0, bw, h0, fill="accent" if i == N.ERR else "ink2", radius=0.06,
                z=30, meta={"tip": [N.WORDS[i], f"{L['p']}: {before[i]:.2f} → {after[i]:.2f}".replace(".", "," if L is TX["ru"] else ".")]})
        objs.append(alt(bar, "model", "before", {"after": bar.copy(y=base - h1, h=h1)}))
        for st, vals in (("before", before), ("after", after)):
            v = f"{vals[i]:.2f}".replace(".", ",") if L is TX["ru"] else f"{vals[i]:.2f}"
            hh = (base - top) * vals[i]
            t = O(f"wv{i}_{st}", "text", cx - 0.5, base - hh - 0.42, 1.0, 0.36, txt=v, sz=13, al="c", col="ink2", z=40,
                  meta={"when": {"key": "model", "is": st, "dflt": "before"}})
            objs.append(t)
    for j, st in enumerate(("before", "after")):
        x0, w = 0.7 + j * 2.45, 2.3
        objs += [link(O(f"wbtn{j}", "rrect", x0, 2.1, w, 0.44, fill="surface2", radius=0.22, z=70), set={"model": st}),
                 link(O(f"wbtn{j}t", "text", x0, 2.1, w, 0.44, txt=L[st], sz=13, al="c", va="m", col="ink2", z=72,
                        meta={"inset": 0.0}), set={"model": st}),
                 O(f"wbtn{j}on", "rrect", x0, 2.1, w, 0.44, fill="accent", radius=0.22, z=71,
                   meta={"when": {"key": "model", "is": st, "dflt": "before"}, "link": {"set": {"model": st}}}),
                 O(f"wbtn{j}ont", "text", x0, 2.1, w, 0.44, txt=L[st], sz=13, b=True, al="c", va="m", col="on_accent", z=73,
                   meta={"inset": 0.0, "when": {"key": "model", "is": st, "dflt": "before"}, "link": {"set": {"model": st}}})]
    s = Slide(fit_text(objs, theme), dur=800, layout="столбики-над-строкой", technique="кнопки: пружина", title="web buttons",
              notes=L["btn_sub"])
    return web(s, sec=3, autoState=[{"at": 1.6, "set": {"model": "after"}, "reset": {"model": "before"}}],
               fx=[{"key": "in.pop", "target": f"wbtn{j}", "delay": 0.2 + 0.1 * j, "dur": 0.35} for j in range(2)])


def _annotations_slide(theme, L, nav) -> Slide:
    y = 3.9
    lay = N.chips_layout(theme, N.WORDS, 1.2, y)
    objs = nav + _title(L["ann_t"], L["ann_sub"]) + N.chips(theme, N.WORDS, lay, y, flagged=N.ERR)
    xe, we = lay[N.ERR]
    xs, ws = lay[1]  # the subject the verb must agree with
    objs += d.encircle("!!wa_c", xe, y, we, 0.62, pad=0.12, style="ink", color="accent", lw=2.4, seed=3, z=60)
    objs += d.arrow("!!wa_a", (xe + we / 2, y + 0.9), (xe + we / 2 + 0.9, y + 1.75), hand=True, bend=0.12, style="ink",
                    color="accent", lw=2.0, z=60)
    objs += d.write("!!wa_w", xe + we / 2 + 1.0, y + 1.6, f"→ {N.FIX}", sz=30, style="ink", color="accent", z=60)
    objs += d.arrow("!!wa_s", (xe + 0.1, y - 0.2), (xs + ws / 2, y - 0.2), bend=-0.35, hand=True, style="ink", color="ink2",
                    lw=1.6, z=60)
    objs += d.write("!!wa_n", xs, y - 1.15, L["note"], sz=20, style="ink", color="ink2", z=60)
    objs += d.stamp("!!wa_st", 11.2, 2.6, 0.75, L["stamp"], L["stamp_c"], "0.3.0", style="ink", color="good", z=60)
    s = Slide(fit_text(objs, theme), dur=800, layout="текст-на-фоне", technique="пометки рисуются", title="web annotations",
              notes=L["ann_sub"])
    order = [("!!wa_c", "in.draw", 0.3, 0.7), ("!!wa_s", "in.draw", 1.0, 0.6), ("!!wa_n", "in.draw-linear", 1.5, 0.9),
             ("!!wa_a", "in.draw", 2.4, 0.5), ("!!wa_w", "in.draw-linear", 2.8, 0.8), ("!!wa_st", "in.draw-stamp", 3.6, 0.5)]
    return web(s, sec=3, fx=[{"key": k, "target": n, "delay": t, "dur": du} for n, k, t, du in order])


def build(out: Path, lang: str = "ru", shots: bool = False) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    base = DD.build(out / "base", render_png=False, variant={"label": "web", "navigation": "menu"}, lang=lang)
    slides, theme, L = base["slides"], base["theme"], TX[lang]
    blocks = [tr(b) for b in DD.BLOCKS]
    for i, s in enumerate(slides):
        blk = DD.PLAN[i][0]
        for o in s.objs:  # the menu is made of buttons
            if o.name.startswith("!!nav") and o.name[5:].isdigit():
                link(o, section=int(o.name[5:]), tip=blocks[int(o.name[5:])])
        fx = []
        if any(o.name == "!!ttl" for o in s.objs):
            k, du = TITLE_FX[blk]
            fx.append({"key": k, "target": "!!ttl", "delay": 0.05, "dur": du})
        web(s, sec=blk if isinstance(blk, int) else (0 if i == 0 else len(blocks) - 1), fx=fx)
    nav = localize([Slide(DD._nav("menu", 3, 0, 0))])[0].objs
    for o in nav:
        if o.name.startswith("!!nav") and o.name[5:].isdigit():
            link(o, section=int(o.name[5:]), tip=blocks[int(o.name[5:])])
    fin = slides[-1]
    k = next(i for i, row in enumerate(DD.PLAN) if row[1] == ("soft", 2)) + 1  # после «исправлено» — в том же разделе
    slides = slides[:k] + [_buttons_slide(theme, L, nav), _annotations_slide(theme, L, [o.copy() for o in nav])] + slides[k:]
    web(fin, scenes=[{"k": "confetti", "at": [6.67, 2.0], "start": 0.6, "character": "calm"}])
    fin.objs.append(link(O("wback", "text", 0.7, 6.75, 3.0, 0.4, txt=f"↺ {L['back']}", sz=13, b=True, col="accent", z=90,
                           meta={"inset": 0.0}), slide=0, tip=L["back"]))
    html = export_html(slides, theme, out / f"demo_web_{lang}.html", title=L["title"], sections=blocks,
                       ui={"menu": "none", "hud": True}, jumpSheet={"k": "iris", "dur": 700}, lang=lang)
    flat = for_pptx(slides)
    errors = [i for i in lint(flat, theme) if i["level"] == "error"]
    r = build_pptx(flat, theme, out / f"demo_web_{lang}.pptx", title=L["title"])
    rep = {"html": str(html), "pptx": str(r["path"]), "slides": len(slides), "lint_errors": errors,
           "xsd": len(xsd_check(r["path"])) if xsd_available() else "skipped", "variety": variety(slides)["deck"]}
    if shots:
        from morphkit.webdemo import shots as take
        s = take(html, out / "shots", times=[0.5, 4.6])
        rep["console_errors"], rep["sheet"] = s["errors"], s["sheet"]
    (out / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k != "variety"}, ensure_ascii=False))
    rep["passed"] = not errors and rep["xsd"] in (0, "skipped") and not rep.get("console_errors")
    return rep


if __name__ == "__main__":
    lang = sys.argv[sys.argv.index("--lang") + 1] if "--lang" in sys.argv else "ru"
    sys.exit(0 if build(Path(sys.argv[1]), lang=lang, shots="--shots" in sys.argv)["passed"] else 1)
