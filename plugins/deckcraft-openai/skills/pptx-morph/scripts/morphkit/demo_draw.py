"""Демо элементов рисования (morphkit.draw + web/draw.js): все виды, все 5 стилей, эффекты рисования и Morph.

    cd scripts && python3 -m morphkit.demo_draw OUT_DIR

Собирает OUT_DIR/draw.html (тема «lab»), снимки Playwright (OUT_DIR/sheet.png, ошибок консоли — 0) и OUT_DIR/draw.pptx
из тех же слайдов (запасные формы vec) с проверкой XSD.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from . import draw as d
from .html import web
from .model import O, Slide

FX: list = []


def T(name, x, y, w, h, txt, sz=18, col="ink", **kw):
    return O(name, "text", x, y, w, h, txt=txt, sz=sz, col=col, z=kw.pop("z", 60), meta={"inset": 0.0, **kw.pop("meta", {})}, **kw)


def title(name, txt, col="ink", sub=None, sub_col="muted"):
    out = [T(name, 0.8, 0.32, 9.0, 0.6, txt, sz=28, col=col, b=True, font="head")]
    if sub:
        out.append(T(name + "s", 0.8, 0.86, 9.0, 0.35, sub, sz=13, col=sub_col))
    return out


def fx(name, delay, dur=1.0, key="in.draw", **opt):
    e = {"key": key, "target": name, "delay": round(delay, 3), "dur": dur}
    if opt:
        e["options"] = opt
    return e


def hole(name, cx, cy, r, **kw):
    import math
    return d.line(name, [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in range(-90, 270, 45)],
                  curve=True, closed=True, **kw)


# ----------------------------------------------------------------------------- 1–2. чертёж (blueprint)
def blueprint(wide: bool) -> Slide:
    d.default(style="blueprint")
    W = 5.0 if wide else 4.0
    x0, y0, x1, y1 = 1.6, 1.9, 1.6 + W, 4.4
    sx = x1 + 0.8  # сечение
    o: list = []
    o += title("!!t1", f"Пластина {1500 if wide else 1200} × 750", col="code_ink",
               sub="рабочий чертёж · стиль blueprint · размеры, прибор и часы переливаются при Morph", sub_col="code_com")
    o += d.gost("!!gost", title="Пластина\nопорная", code="ДК.030.001" if not wide else "ДК.030.002", org="deckcraft",
                material="Сталь 45 ГОСТ 1050", lit="О", mass="12,4" if not wide else "15,5", scale="1:10", sheet=1 if not wide else 2,
                sheets=2, rows=[("Кулак", "10.26"), ("Петров", "10.26"), ("", ""), ("", ""), ("Иванов", "10.26")], z=5)
    o += d.line("!!plate", [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], closed=True, lw=1.8)
    o += hole("!!h1", x0 + 0.8, 3.15, 0.3)
    o += hole("!!h2", x1 - 0.8, 3.15, 0.3)
    o += d.line("!!axis", [(x0 - 0.2, 3.15), (x1 + 0.2, 3.15)], dash="dash", color="code_com", lw=0.8)
    o += d.hatch("!!sec", sx, y0, 0.45, y1 - y0, pattern="hatch", step=0.12)
    o += d.dim_h("!!dimW", x0, x1, 1.4, base=y0, value=1500 if wide else 1200, sz=12)
    o += d.dim_v("!!dimH", y0, y1, 1.1, base=x0, value=750, sz=12)
    o += d.dim_h("!!dimS", sx, sx + 0.45, 1.4, base=y0, value=40, sz=11)
    o += d.brace("!!br", (sx + 0.6, y0), (sx + 0.6, y1), side=1, label="сечение\nА–А", sz=12)
    o += d.arrow("!!arA", (x1 + 0.1, 2.25), (sx - 0.08, 2.25), bend=0.35, head="open")
    o += d.balloon("!!b1", (x0 + 0.8 + 0.21, 3.36), (x0 + 0.5, 5.05), 1)
    o += d.balloon("!!b2", (x0 + W / 2, y1 - 0.05), (x0 + W / 2 + 0.3, 5.05), 2)
    o += d.balloon("!!b3", (sx + 0.22, 3.9), (sx + 0.3, 5.05), 3)
    o += d.leader("!!ld", (x1 - 0.8 + 0.21, 3.36), (x1 - 0.3, 5.45), "2 отв. ⌀ 60 H12", sz=12)
    o += d.ruler("!!rul", x0, 5.95, W, v0=0, v1=1500 if wide else 1200, major=300, minor=3, unit="мм", sz=9)
    o += d.gauge("!!spd", 10.35, 2.45, 1.0, 82 if wide else 35, zones=[(80, 100, "bad"), (60, 80, "warn")], label="нагрузка, %")
    o += d.clock("!!clk", 12.3, 2.45, 0.78, 14 if wide else 10, 45 if wide else 10, s=20)
    o += d.write("!!note", 9.0, 4.15, "Неуказанные предельные отклонения:\nH14, h14, ±IT14/2", sz=13, font="mono")
    s = Slide(o, bg="code_bg", dur=900, title="Чертёж" + (" (Morph)" if wide else ""))
    d.default(style="ink")
    if not wide:
        names = ["!!gost", "!!plate", "!!h1", "!!h2", "!!axis", "!!sec", "!!dimW", "!!dimH", "!!dimS", "!!br", "!!arA", "!!b1",
                 "!!b2", "!!b3", "!!ld", "!!rul", "!!spd", "!!clk"]
        web(s, fx=[fx(n, 0.05 + 0.1 * i, 1.6 if n in ("!!gost", "!!spd", "!!clk") else 1.0) for i, n in enumerate(names)]
            + [fx("!!note", 1.8, 1.4, "in.draw-linear")])
    else:
        web(s, fx=[fx("!!spd", 0.2, 1.2, "em.draw-needle", amp=4), fx("!!clk", 0.1, 2.4, "em.draw-run", minutes=50)])
    return s


# ----------------------------------------------------------------------------- 3–4. пометки (ink + marker)
def _tw(s: str, sz: float, bold: bool = False) -> float:
    """Ширина строки Carlito (как в браузере) в дюймах."""
    try:
        from PIL import ImageFont
        f = ImageFont.truetype("/usr/share/fonts/truetype/crosextra/Carlito-%s.ttf" % ("Bold" if bold else "Regular"), int(sz * 120 / 72 * 4))
        return f.getlength(s) / 4 / 120
    except Exception:
        return len(s) * sz / 72 * 0.48


def notes(after: bool) -> Slide:
    o: list = []
    o += title("!!t3", "Пометки на полях", sub="стили ink и marker · стикер падает и прилипает · печать рывками")
    lines = ["Модель угадывает следующий токен —", "остальное обвязка: контекст, RAG,", "инструменты и память агента."]
    sz, lh, px, py = 22, 22 / 72 * 1.2, 0.9, 1.45
    for i, ln in enumerate(lines):
        o.append(T(f"!!p{i}", px, py + i * lh, 7.0, lh, ln, sz=sz, col="ink2", z=50))
    a = _tw("Модель угадывает ", sz)
    b = _tw("следующий токен", sz)
    if after:
        o += d.highlight("!!hl", px + a - 0.05, py + 0.02, b + 0.1, lh - 0.04, style="marker", passes=2)
    else:
        o += d.highlight("!!hl", px + a - 0.05, py + 0.02, _tw("следующий", sz) + 0.1, lh - 0.04, style="marker", passes=2)
    c0 = _tw("остальное обвязка: ", sz)
    o += d.scribble("!!sc", px + c0, px + c0 + _tw("контекст, RAG", sz), py + 2 * lh - 0.02, amp=0.045, form="wave", color="accent")
    e0 = _tw("инструменты и ", sz)
    o += d.encircle("!!en", px + e0, py + 2 * lh + 0.03, _tw("память", sz), lh - 0.08, pad=0.1, style="marker", color="accent2")
    for i, (mk, lab) in enumerate((("check", "галочка"), ("cross", "крест"), ("asterisk", "звёздочка"), ("star", "звезда"))):
        o += d.mark(f"!!m{i}", 1.2 + 1.15 * i, 3.35, 0.42, mark=mk, color="accent" if mk in ("check", "star") else "ink")
        o.append(T(f"!!ml{i}", 0.75 + 1.15 * i, 3.68, 0.9, 0.3, lab, sz=12, col="muted", al="c"))
    o += d.arrow("!!ah", (6.4, 2.75), (8.45, 2.55) if not after else (8.85, 2.85), hand=True, bend=0.12)
    o += d.sticker("!!st", 8.6 if not after else 9.0, 1.05 if not after else 1.35, 2.7, 2.0, "Не забыть:\nпроверить допуски\nи даты", tape=True,
                   rot=-3 if not after else 4, sz=18)
    o.append(O("!!photo", "rect", 11.75, 1.25, 1.3, 1.7, fill="surface2", ln="line", lw=0.75, rot=5, z=30))
    o += d.tape("!!tp", 11.8, 1.05, 1.15, 0.3, rot=-9, z=45)
    o += d.write("!!w1", 0.9, 4.25, "Спросить про MCP!", sz=34, color="accent")
    o += d.scribble("!!sc2", 0.95, 4.6, 4.95, amp=0.05, form="double", color="accent")
    o += d.arrow("!!am", (4.6, 4.5), (5.55, 5.15), bend=-0.25, style="marker", color="accent3")
    o += d.gauge("!!g3", 6.55, 5.55, 0.95, 70 if after else 30, label="уверенность, %", zones=[(0, 30, "bad")])
    o += d.clock("!!c3", 9.05, 5.55, 0.82, 12 if after else 10, 40 if after else 10, numerals="roman", fill="surface")
    o += d.stamp("!!stp", 11.75, 5.45, 0.92, "ОТДЕЛ ТЕХНИЧЕСКОГО КОНТРОЛЯ • ПРИНЯТО • ", "ОТК\nПРИНЯТО", "23.10.2026",
                 style="ink", color="accent")
    s = Slide(o, dur=850, title="Пометки" + (" (Morph)" if after else ""))
    if not after:
        seq = ["!!hl", "!!sc", "!!en", "!!m0", "!!m1", "!!m2", "!!m3", "!!ah", "!!tp", "!!sc2", "!!am", "!!g3", "!!c3"]
        web(s, fx=[fx(n, 0.1 + 0.16 * i, 0.9 if n.startswith("!!m") else 1.2) for i, n in enumerate(seq)]
            + [fx("!!st", 1.0, 1.1, "in.draw-drop"), fx("!!w1", 1.6, 1.6, "in.draw-linear"), fx("!!stp", 2.6, 0.5, "in.draw-stamp")])
    else:
        web(s, fx=[fx("!!g3", 0.1, 1.4, "em.draw-needle", amp=6), fx("!!c3", 0.2, 2.0, "em.draw-run", minutes=35),
                   fx("!!m3", 0.3, 1.2, "em.draw-redraw")])
    return s


# ----------------------------------------------------------------------------- 5. ризограф
def riso() -> Slide:
    d.default(style="riso", c2="accent")
    o: list = []
    o += d.write("rt", 0.8, 0.3, "Процесс согласования", sz=28, font="head", wt=800, color="ink")
    o.append(T("rts", 0.8, 0.95, 9, 0.35, "стиль riso: надпечатка второй краской, multiply · блок-схема · растр · штамп", sz=13, col="muted"))
    B = [("f1", 0.9, 1.5, 2.3, 0.7, "Заявка", "terminator", "accent3/35"), ("f2", 0.9, 2.65, 2.3, 0.85, "Ввод\nданных", "data", None),
         ("f3", 0.9, 3.95, 2.3, 0.8, "Проверка", "process", "surface"), ("f4", 3.95, 3.75, 2.1, 1.2, "Всё\nверно?", "decision", None),
         ("f5", 6.8, 3.95, 2.3, 0.8, "Согласование", "predef", "surface"), ("f6", 6.8, 5.35, 2.3, 0.95, "Протокол", "document", "accent3/35")]
    for n, x, y, w, h, t, f, fill in B:
        o += d.block(n, x, y, w, h, t, form=f, fill=fill, sz=15, color="accent2" if f == "decision" else None)
    o += d.arrow("a12", (2.05, 2.2), (2.05, 2.63))
    o += d.arrow("a23", (2.05, 3.5), (2.05, 3.93))
    o += d.arrow("a34", (3.2, 4.35), (3.93, 4.35))
    o += d.arrow("a45", (6.05, 4.35), (6.78, 4.35))
    o += d.arrow("a56", (7.95, 4.75), (7.95, 5.33))
    o += d.arrow("a42", (5.0, 3.75), (3.0, 3.07), via=[(5.0, 3.07)], color="accent")
    o.append(T("yes", 6.1, 3.98, 0.6, 0.3, "да", sz=13, col="accent2", b=True))
    o.append(T("no", 5.1, 3.25, 0.6, 0.3, "нет", sz=13, col="accent", b=True))
    o += d.brace("bf", (6.8, 3.75), (9.1, 3.75), side=1, depth=0.2, label="ветка «да»", sz=13)
    o += d.stamp("sr", 11.0, 2.05, form="rect", w=2.7, h=0.95, center="СОГЛАСОВАНО", sub="23.10.2026 · подпись", rot=-8,
                 style="riso", color="accent", c2="accent3")
    import math
    circ = [(11.0 + 1.0 * math.cos(math.radians(a)), 4.55 + 1.0 * math.sin(math.radians(a))) for a in range(0, 360, 10)]
    o += d.hatch("hd", 10, 3.55, 2, 2, pts=circ, pattern="dots", step=0.1, color="accent", outline=False)
    o += d.hatch("hh", 11.3, 4.5, 1.3, 1.1, pattern="cross", step=0.16, color="accent2")
    o += d.ruler("rr", 0.9, 6.8, 5.2, v0=0, v1=10, major=2, minor=4, unit="дн.", sz=10)
    o += d.line("lc", [(9.6, 6.75), (10.3, 6.2), (11.0, 6.45), (11.7, 5.95), (12.6, 6.1)], curve=True, end="dot", color="accent2")
    o += d.tape("tp5", 9.95, 1.35, 1.0, 0.3, rot=-20)
    s = Slide(o, dur=800, title="Ризограф")
    seq = ["f1", "a12", "f2", "a23", "f3", "a34", "f4", "a45", "f5", "a56", "f6", "a42", "bf", "rr", "lc", "hh", "tp5"]
    web(s, fx=[fx("rt", 0.0, 0.9, "in.draw-reg")] + [fx(n, 0.15 + 0.13 * i, 0.8) for i, n in enumerate(seq)]
        + [fx("hd", 0.6, 1.4, "in.draw-reg"), fx("sr", 2.4, 0.5, "in.draw-stamp")])
    d.default(style="ink", c2=None)
    return s


# ----------------------------------------------------------------------------- 6. матрица: виды × стили
def matrix() -> Slide:
    o: list = []
    o += title("mt", "Все виды × 5 стилей", sub="blueprint · ink · marker · riso · chalk — одна и та же спецификация, разный «почерк»")
    styles = ["blueprint", "ink", "marker", "riso", "chalk"]
    top, rh = 1.45, 1.17
    fxs = []
    for r, st in enumerate(styles):
        y = top + r * rh
        dark = st in ("blueprint", "chalk")
        if dark:
            o.append(O(f"bg{r}", "rect", 0.25, y - 0.08, 12.83, rh - 0.04, fill="code_bg", z=1))
        kw = {"style": st}
        if dark:
            kw["color"] = "code_ink"
        lab_col = "code_ink" if dark else "ink"
        o.append(T(f"rl{r}", 0.35, y + 0.4, 1.0, 0.3, st, sz=13, col=lab_col, b=True, font="mono"))
        cols = 11
        X = [1.45 + 1.06 * i for i in range(cols)]
        cy = y + rh / 2 - 0.06
        n = f"m{r}_"
        items = []
        items += d.line(n + "ln", [(X[0], cy + 0.25), (X[0] + 0.3, cy - 0.3), (X[0] + 0.6, cy + 0.15), (X[0] + 0.85, cy - 0.25)], curve=True, end="dot", **kw)
        items += d.arrow(n + "ar", (X[1], cy + 0.3), (X[1] + 0.85, cy - 0.25), hand=True, double=r % 2 == 1, head="tri" if r % 2 == 0 else "open", **kw)
        items += d.dim_h(n + "dm", X[2], X[2] + 0.85, cy - 0.05, base=cy + 0.35, value=850, sz=10, ends="tick" if st == "blueprint" else "arrow", **kw)
        items += d.balloon(n + "bl", (X[3] + 0.15, cy + 0.35), (X[3] + 0.55, cy - 0.15), r + 1, r=0.2, **kw)
        items += d.brace(n + "br", (X[4], cy + 0.15), (X[4] + 0.85, cy + 0.15), side=1, depth=0.18, label="скобка", sz=10, form="square" if r % 2 else "curly", **kw)
        items += d.block(n + "bk", X[5], cy - 0.3, 0.9, 0.6, "Решение", form="decision", sz=10, **kw)
        items += d.mark(n + "mk", X[6] + 0.22, cy, 0.38, mark=["check", "cross", "asterisk", "star", "check"][r], **kw)
        items += d.encircle(n + "en", X[6] + 0.55, cy - 0.12, 0.3, 0.24, pad=0.06, **kw)
        items += d.scribble(n + "sc", X[7], X[7] + 0.85, cy + 0.05, amp=0.07, form=["wave", "zigzag", "loops", "double", "wave"][r], **kw)
        items += d.gauge(n + "ga", X[8] + 0.45, cy + 0.12, 0.42, 25 + 15 * r, sz=6, **kw)
        items += d.clock(n + "cl", X[9] + 0.45, cy, 0.42, 3 + r * 2, 10 * r, numerals=False, **kw)
        items += d.hatch(n + "ht", X[10], cy - 0.32, 0.8, 0.64, pattern=["hatch", "cross", "grid", "dots", "hatch"][r], step=0.1, **kw)
        o += items
        for k, ob in enumerate(x for x in items if "~" not in x.name):
            fxs.append(fx(ob.name, 0.1 + 0.09 * k + 0.12 * r, 1.0))
        if st == "chalk":
            fxs.append({"key": "em.draw-boil", "target": n + "ln", "delay": 2.6, "dur": 1.6, "repeat": True, "options": {"n": 8}})
    # колонка-легенда
    heads = ["линия", "стрелка", "размер", "выноска", "скобка", "блок", "пометки", "каракуля", "прибор", "часы", "штриховка"]
    for i, h in enumerate(heads):
        o.append(T(f"ch{i}", 1.45 + 1.06 * i - 0.1, 1.17, 1.06, 0.25, h, sz=11, col="muted", al="c"))
    s = Slide(o, dur=800, title="Матрица видов и стилей")
    web(s, fx=fxs)
    return s


def slides() -> list[Slide]:
    d.default(style="ink", color=None, c2=None)
    return [blueprint(False), blueprint(True), notes(False), notes(True), riso(), matrix()]


def main(out: str) -> dict:
    from .palette import CATALOG
    from .webdemo import build, shots
    from .build import build_pptx
    from .qa import xsd_check
    outp = Path(out)
    outp.mkdir(parents=True, exist_ok=True)
    S = slides()
    html = build(S, outp / "draw.html", sections=["Чертёж", "Пометки", "Ризограф", "Матрица"], title="Элементы рисования")
    import shutil
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="demo_draw_"))
    res = shots(html, tmp, times=[0.7, 1.7, 4.6])  # кадры: 0,7 с (Morph/начало), 1,7 с (рисуется), 4,6 с (готово)
    shutil.copy(res["sheet"], outp / "sheet.png")
    res["sheet"] = str(outp / "sheet.png")
    theme = next(p.theme for p in CATALOG if p.theme.name == "lab")
    S2 = slides()
    pp = build_pptx(S2, theme, outp / "draw.pptx", title="Элементы рисования")
    xsd = xsd_check(outp / "draw.pptx")
    rep = {"html": str(html), "sheet": res["sheet"], "errors": res["errors"], "pptx": pp["path"], "xsd": xsd,
           "objects": [len(s.objs) for s in S]}
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    shutil.rmtree(tmp, ignore_errors=True)
    return rep


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "demo_draw_out")
