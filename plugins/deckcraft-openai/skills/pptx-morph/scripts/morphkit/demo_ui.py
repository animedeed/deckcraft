"""Демо модулей web/sheets.js (листы-переходы) и web/ui.js + ui.css (интерфейс показа) и их проверка браузером.

    cd plugins/deckcraft/skills/pptx-morph/scripts
    python3 -m morphkit.demo_ui OUT_DIR            # сборка index*.html + снимки Playwright + check.json
    python3 -m morphkit.demo_ui OUT_DIR --no-shots # только сборка

22 слайда в 4 разделах: каждый из 19 листов показан на переходе к своему слайду и подписан на нём; объекты-ссылки
(слайд, раздел, «назад»), подсказки, шаги, переключатель A/B (объекты с when + объект с alt). Варианты меню:
index.html — "top", index_tabs.html — "tabs", index_stamp.html — "stamp", index_none.html — "none" (+ HUD).
Проверка: середины переходов каждого листа (и обратный ход), меню, обзор, подсказка, «вернуться», перо, указка,
справка, переход по номеру, заметки, окно докладчика (синхронизация в обе стороны), печать в PDF, reduced-motion.
Ошибок консоли должно быть 0.
"""

from __future__ import annotations

import asyncio
import json
import math
import re
import sys
import textwrap
from pathlib import Path

from .html import alt, link, web
from .model import O, Slide
from .webdemo import build, launch_kw

SECTIONS = ["Въезд", "Сдвиг и 3D", "Формы", "Фактура"]
DUR = 900
# (лист, параметры opt, что делает) — порядок = порядок слайдов 2…20
SHEETS = [
    ("sheetIn", {"rot": 6}, "Лист въезжает справа с поворотом 6° и тенью — как в «Зин»."),
    ("sheetUp", {}, "Лист поднимается снизу — как в «Чертеже»."),
    ("sheetDown", {}, "Лист опускается сверху и ложится на старый."),
    ("push", {"parallax": 0.35}, "Новый лист толкает старый; старый уходит медленнее — параллакс."),
    ("cover", {"dir": "up"}, "Новый лист наезжает поверх неподвижного (dir: up — снизу вверх)."),
    ("uncover", {}, "Старый лист уезжает и открывает новый под собой."),
    ("fold", {}, "Старый лист складывается по средней линии в 3D (rotateY)."),
    ("flip", {}, "Карточка переворачивается: на обороте — новый слайд."),
    ("cube", {}, "Грани куба: старая уходит влево, новая приходит справа."),
    ("iris", {"x": 0.76, "y": 0.47}, "Круг раскрывается из точки opt.x, opt.y — clip-path: circle()."),
    ("diamond", {}, "Ромб из центра (или из центра объекта-ссылки, по которой перешли)."),
    ("blinds", {"n": 9}, "Жалюзи: полосы раскрываются от середины ламели, сверху вниз."),
    ("curtain", {}, "Занавес раздвигается из центра, полотнища уходят вглубь."),
    ("ink", {"seed": 4}, "Новый слайд проступает чернильным пятном с брызгами."),
    ("zoomThrough", {}, "Старый лист растёт с размытием и тает, новый выходит из малого."),
    ("dissolve", {"cell": 30}, "Зерно: клетки старого листа выпадают по случайному порогу."),
    ("glitch", {"steps": 16}, "Полосы со сдвигом и расслоением каналов — детерминированно."),
    ("pageCurl", {"corner": "br"}, "Угол листа отгибается: срез по линии сгиба, клапан с тенью."),
    ("shutter", {}, "Две створки смыкаются над старым листом и расходятся над новым."),
]
SEC_OF = [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3]
DOTS = ["accent", "accent2", "accent3"]


def wrap(s: str, w: float, sz: float) -> str:
    """Ядро не переносит строки — разбиваем сами (≈0,5 кегля на знак)."""
    n = max(8, int(w * 72 / (sz * 0.5)))
    return "\n".join(textwrap.fill(par, n) for par in s.split("\n"))


def T(name, x, y, w, h, s, sz=18, col="ink", b=False, font="body", al="l", va="t", **kw) -> O:
    return O(name, "text", x, y, w, h, txt=wrap(s, w, sz), sz=sz, col=col, b=b, font=font, al=al, va=va, **kw)


def card(name, x, y, w, h, fill, s, sz=18, col="ink", **kw) -> O:
    return O(name, "rrect", x, y, w, h, fill=fill, radius=0.16, txt=s, sz=sz, col=col, al="c", va="m", b=True, **kw)


def dark(i: int) -> bool:
    return i % 2 == 1


def sheet_slide(i: int, k: str, opt: dict, desc: str, n: int) -> Slide:
    dk = dark(i)
    ink, mut, panel = ("code_ink", "A9A49A", "2A2B31") if dk else ("ink", "muted", "surface")
    acc = DOTS[n % 3]
    sec = SEC_OF[i]
    code = json.dumps(dict({"k": k, "dur": DUR}, **opt), ensure_ascii=False)
    objs = [
        T("kick", 0.8, 1.0, 7.4, 0.4, f"РАЗДЕЛ {sec + 1} · {SECTIONS[sec].upper()} · ЛИСТ {n + 1} ИЗ 19", 13, mut, True, tracking=1.5),
        T("name", 0.8, 1.45, 7.6, 1.5, k, 80, ink, True, "head"),
        T("desc", 0.8, 3.05, 6.9, 1.3, desc, 24, ink),
        O("codebg", "rrect", 0.8, 4.55, 7.2, 0.62, fill=panel, radius=0.1),
        T("code", 0.98, 4.62, 7.0, 0.5, "sheet=" + code, 14, ink, font="mono", va="m"),
        T("foot", 0.8, 6.75, 6.0, 0.35, "deckcraft 0.3.0 · листы-переходы · ← → листать, O — обзор", 12, mut),
        O("disc", "oval", 8.55, 1.25, 3.9, 3.9, fill=acc),
        T("num", 8.55, 1.25, 3.9, 3.9, f"{i + 1:02d}", 110, "on_accent", True, "head", al="c", va="m"),
        O("sq", "rect", 11.55, 4.55, 1.05, 1.05, fill="ink" if not dk else "code_ink", rot=12),
    ]
    for t in range(6):  # ряд плиток — видны жалюзи, зерно, глитч
        objs.append(O(f"tile{t}", "rect", 8.55 + t * 0.55, 5.55, 0.42, 0.42,
                      fill=DOTS[(n + t) % 3], fa=1.0 - t * 0.12))
    if k == "iris":
        o = O("dot", "oval", 13.333 * 0.76 - 0.22, 7.5 * 0.47 - 0.22, 0.44, 0.44, fill="white_wine", ln="on_accent", lw=3)
        o.meta["tip"] = ["Точка начала круга", "opt.x = 0.76 · opt.y = 0.47", "доли сцены; можно и в px"]
        objs.append(o)
    if k == "push":
        objs.append(link(card("go_ab", 0.8, 5.55, 3.6, 0.7, "accent", "Переключатель A/B →", 18, "on_accent"),
                         slide=20, tip=["Переход по ссылке", "на слайд 21 — лист iris из этой кнопки",
                                        "назад — кнопкой «вернуться» или Backspace"]))
    s = Slide(objs, bg="code_bg" if dk else "bg", title=f"Лист {k}", dur=DUR, transition="fade",
              notes=f"Переход к этому слайду — лист «{k}». {desc} Параметры: {code}. "
                    "При листании назад тот же лист проигрывается в обратную сторону.")
    return web(s, sec=sec, sheet=dict({"k": k, "dur": DUR}, **opt))


def deck() -> list[Slide]:
    slides: list[Slide] = []
    # 1. Обложка
    s0 = Slide([
        T("kick", 0.8, 1.35, 9, 0.4, "DECKCRAFT 0.3.0 · WEB-ДВИЖОК", 14, "muted", True, tracking=2),
        T("title", 0.8, 1.85, 11.5, 2.4, "Листы-переходы\nи интерфейс показа", 64, "ink", True, "head", spacing=0.95),
        T("sub", 0.8, 4.35, 9.5, 1.0, "19 листов · меню разделов · обзор · окно докладчика · перо и указка · печать в PDF", 22, "ink2"),
        link(card("go_toc", 0.8, 5.5, 3.2, 0.72, "accent", "Содержание →", 20, "on_accent"), slide=1,
             tip=["Ссылка на слайд 2", "клик — переход листом", "Backspace — назад"]),
        T("keys", 4.3, 5.62, 8.0, 0.5, "→ листать · O обзор · P докладчик · D перо · ? клавиши", 16, "muted", va="m"),
        O("disc", "oval", 9.9, 0.9, 2.6, 2.6, fill="accent2", fa=0.9),
        O("disc2", "oval", 11.3, 2.6, 1.4, 1.4, fill="accent3"),
    ], bg="bg", title="Листы и интерфейс", notes="Демо модуля sheets.js и ui.js. Внизу справа — HUD, сверху — меню разделов.")
    slides.append(web(s0, sec=0))
    # 2. Содержание: карточки-разделы
    k0, opt0, d0 = SHEETS[0]
    cards = []
    ranges = ["1–4", "5–10", "11–15", "16–22"]
    sheets_by = [["sheetIn", "sheetUp", "sheetDown"], ["push", "cover", "uncover", "fold", "flip", "cube"],
                 ["iris", "diamond", "blinds", "curtain", "ink"], ["zoomThrough", "dissolve", "glitch", "pageCurl", "shutter"]]
    for j, name in enumerate(SECTIONS):
        x = 0.8 + j * 3.0
        cards.append(link(card(f"sec{j}", x, 2.55, 2.75, 2.5, DOTS[j % 3] if j < 3 else "ink",
                               f"{j + 1}\n{name}", 26, "on_accent" if j < 3 else "bg"),
                          section=j, tip=[f"Раздел {j + 1} · {name}", f"слайды {ranges[j]}", "листы: " + ", ".join(sheets_by[j])]))
    s1 = Slide([
        T("kick", 0.8, 1.0, 9, 0.4, "РАЗДЕЛ 1 · ВЪЕЗД · ЛИСТ 1 ИЗ 19", 13, "A9A49A", True, tracking=1.5),
        T("name", 0.8, 1.35, 11, 1.0, "Содержание — лист sheetIn", 40, "code_ink", True, "head"),
        *cards,
        T("desc", 0.8, 5.35, 11.5, 0.9, d0 + " Карточки — ссылки на разделы (клик → раздел, «вернуться» — назад).", 18, "code_ink"),
        T("foot", 0.8, 6.75, 6.0, 0.35, "наведите на карточку — подсказка", 12, "A9A49A"),
    ], bg="code_bg", title="Содержание", dur=DUR, transition="fade",
        notes="Четыре раздела. Карточки кликабельны; меню сверху делает то же самое.")
    slides.append(web(s1, sec=0, sheet=dict({"k": k0, "dur": DUR}, **opt0)))
    # 3–20. Листы
    for n, (k, opt, desc) in enumerate(SHEETS[1:], start=1):
        slides.append(sheet_slide(n + 1, k, opt, desc, n))
    # 21. Переключатель A/B и шаги
    whenA, whenB = {"key": "ab", "is": "A", "dflt": "A"}, {"key": "ab", "is": "B", "dflt": "A"}
    objs = [
        T("kick", 0.8, 1.0, 9, 0.4, "РАЗДЕЛ 4 · ФАКТУРА · ИНТЕРАКТИВ", 13, "muted", True, tracking=1.5),
        T("name", 0.8, 1.35, 11, 1.0, "Переключатель A/B и шаги", 40, "ink", True, "head"),
        link(O("sw_bg", "rrect", 0.8, 2.6, 2.4, 0.66, fill="surface2", radius=0.33, z=1), toggle="ab", values=["A", "B"],
             tip=["Переключатель", "клик — вариант A ↔ B", "ручка едет состоянием alt"]),
    ]
    knob = link(O("sw_knob", "oval", 0.86, 2.65, 0.56, 0.56, fill="bg", ln="accent", lw=2.5, z=2), toggle="ab", values=["A", "B"])
    objs.append(alt(knob, "ab", "A", {"B": knob.copy(x=2.58, ln="accent2")}))
    objs += [link(T("sw_a", 0.86, 2.6, 0.56, 0.66, "A", 20, "ink", True, al="c", va="m", z=3), toggle="ab", values=["A", "B"]),
             link(T("sw_b", 2.58, 2.6, 0.56, 0.66, "B", 20, "ink", True, al="c", va="m", z=3), toggle="ab", values=["A", "B"])]
    bars_a, bars_b = [2.6, 1.6, 3.4, 2.1], [1.2, 3.5, 2.0, 3.1]
    for j, (ha, hb) in enumerate(zip(bars_a, bars_b)):
        x = 4.2 + j * 1.25
        a = O(f"ba{j}", "rect", x, 6.1 - ha, 0.85, ha, fill="accent")
        a.meta["when"] = whenA
        b = O(f"bb{j}", "rect", x, 6.1 - hb, 0.85, hb, fill="accent2")
        b.meta["when"] = whenB
        objs += [a, b]
    la = T("cap_a", 4.2, 6.2, 5.0, 0.4, "вариант A — до обучения", 16, "accent", True)
    la.meta["when"] = whenA
    lb = T("cap_b", 4.2, 6.2, 5.0, 0.4, "вариант B — после обучения", 16, "accent2", True)
    lb.meta["when"] = whenB
    objs += [la, lb,
             card("st_1", 9.6, 2.6, 3.0, 1.1, "surface", "шаг 1: клик →", 20, "ink"),
             card("st_2", 9.6, 3.9, 3.0, 1.1, "accent3", "шаг 2: ещё клик", 20, "on_accent"),
             link(card("back", 9.6, 5.3, 3.0, 0.72, "ink", "← назад", 18, "bg"), back=True,
                  tip=["Ссылка «назад»", "возвращает на слайд, откуда пришли"]),
             T("foot", 0.8, 6.75, 3.2, 0.35, "шаги — по клику / →", 12, "muted")]
    s20 = Slide(objs, bg="bg", title="Переключатель A/B", dur=DUR, transition="fade",
                notes="Клик по переключателю меняет вариант A/B: столбики — по when, ручка — по alt. Две карточки справа появляются по шагам.")
    slides.append(web(s20, sec=3, sheet={"k": "iris", "dur": DUR}, steps=[["st_1"], ["st_2"]]))
    # 22. Итог: ссылки
    s21 = Slide([
        T("kick", 0.8, 1.0, 9, 0.4, "РАЗДЕЛ 4 · ФАКТУРА · ИТОГ", 13, "A9A49A", True, tracking=1.5),
        T("name", 0.8, 1.35, 11.5, 1.0, "Куда дальше", 44, "code_ink", True, "head"),
        link(card("to_toc", 0.8, 2.8, 3.6, 0.9, "accent", "← к содержанию", 20, "on_accent"), slide=1,
             tip=["Ссылка на слайд 2", "переход листом jumpSheet (iris из кнопки)"]),
        link(card("to_forms", 4.7, 2.8, 3.6, 0.9, "accent2", "раздел «Формы»", 20, "on_accent"), section=2,
             tip=["Ссылка на раздел 3", "первый слайд раздела"]),
        link(card("to_back", 8.6, 2.8, 3.6, 0.9, "surface2", "назад по ссылке", 20, "ink"), back=True,
             tip="Возврат по стеку ссылок (то же — Backspace)"),
        T("desc", 0.8, 4.3, 11.5, 1.6, "Клавиши: O — обзор, P — окно докладчика, D — перо, L — указка, N — заметки, "
          "F — полный экран, цифры + Enter — к слайду, ? — справка. Печать (Ctrl+P или «PDF» в HUD) — страница на слайд.",
          20, "code_ink"),
    ], bg="code_bg", title="Итог", dur=DUR, transition="fade", notes="Последний слайд: ссылки на содержание, раздел и назад.")
    slides.append(web(s21, sec=3, sheet={"k": "cube", "dur": DUR}))
    return slides


def build_all(out: Path) -> dict[str, Path]:
    out.mkdir(parents=True, exist_ok=True)
    common = dict(sections=SECTIONS, title="Листы и интерфейс", jumpSheet={"k": "iris", "dur": 800})
    ui_extra = {"author": "Корнилов", "date": "23.10.26", "code": "ДК"}
    paths = {}
    for name, menu in (("index", "top"), ("index_tabs", "tabs"), ("index_stamp", "stamp"), ("index_none", "none")):
        paths[menu] = build(deck(), out / f"{name}.html", ui=dict({"menu": menu, "hud": True}, **ui_extra), **common)
    return paths


# ------------------------------------------------------------------------------ проверка Playwright
# «заморозка» времени: кадр перехода рисуется в момент __t0 + доля·длительность (__t0 — начало перехода, из события
# slide: DC.t0 ядра не годится — Object.assign скопировал значение геттера, а не сам геттер)
INIT = """(() => { const r = window.requestAnimationFrame.bind(window); window.__fakeT = null; window.__t0 = 0;
  window.requestAnimationFrame = cb => r(ts => cb(window.__fakeT === null ? ts : window.__fakeT));
  addEventListener('DOMContentLoaded', () => window.DC && DC.on && DC.on('slide', () => { window.__t0 = performance.now() })); })()"""


async def _check(paths: dict[str, Path], out: Path) -> dict:
    from playwright.async_api import async_playwright
    from PIL import Image, ImageDraw, ImageFont
    shots = out / "shots"
    shots.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    checks: dict[str, object] = {}
    files: list[str] = []

    def hook(pg, tag):
        pg.on("pageerror", lambda e: errors.append(f"{tag} exception: {e}"))
        pg.on("console", lambda m: errors.append(f"{tag} {m.type}: {m.text}") if m.type in ("error", "warning") else None)

    async def snap(pg, name):
        f = shots / f"{name}.png"
        await pg.screenshot(path=str(f))
        files.append(str(f))
        return f

    async def freeze(pg, frac, dur_ms=DUR):
        await pg.evaluate(f"window.__fakeT = window.__t0 + {frac * dur_ms}")
        await pg.wait_for_timeout(70)

    async def unfreeze(pg):
        await pg.evaluate("window.__fakeT = null")

    async with async_playwright() as p:
        b = await p.chromium.launch(**launch_kw())
        ctx = await b.new_context(viewport={"width": 1600, "height": 900})
        await ctx.add_init_script(INIT)
        pg = await ctx.new_page()
        hook(pg, "main")
        uri = paths["top"].resolve().as_uri()
        await pg.goto(uri)
        await pg.wait_for_timeout(500)
        await pg.mouse.move(900, 500)
        await pg.wait_for_timeout(200)
        await snap(pg, "00_start_menu_hud")
        n = await pg.evaluate("DC.data.slides.length")
        checks["slides"] = n
        checks["sheets_registered"] = await pg.evaluate("DC.sheetNames")
        # --- листы: кадры 30/50/75 % вперёд и 50 % назад
        await pg.mouse.move(1599, 899)
        await pg.wait_for_timeout(2900)  # HUD уходит при бездействии
        seq = []
        for i in range(1, 20):
            k = SHEETS[i - 1][0]
            await pg.evaluate(f"DC.go({i - 1}, {{instant: true}})")
            await pg.wait_for_timeout(90)
            await pg.evaluate(f"DC.go({i})")
            row = []
            for fr in (0.3, 0.5, 0.75):
                await freeze(pg, fr)
                row.append(await snap(pg, f"sheet_{i + 1:02d}_{k}_{int(fr * 100)}"))
            await unfreeze(pg)
            await pg.wait_for_timeout(DUR + 150)
            left = await pg.evaluate("document.querySelectorAll('#dc-stage > .dcs-x, #dc-stage > .dc-snap').length")
            style = await pg.evaluate("document.getElementById('dc-svg').getAttribute('style') || ''")
            if left or style.strip():
                errors.append(f"лист {k}: после перехода осталось {left} врем. элементов, style B = {style!r}")
            seq.append((k, row))
        rev = []
        for i in (1, 4, 7, 9, 10, 13, 18):  # обратный ход: из i+1 в i (лист слайда i назад)
            k = SHEETS[i - 1][0]
            await pg.evaluate(f"DC.go({i + 1}, {{instant: true}})")
            await pg.wait_for_timeout(90)
            await pg.evaluate(f"DC.go({i})")
            await freeze(pg, 0.5)
            rev.append((k, await snap(pg, f"back_{i + 1:02d}_{k}_50")))
            await unfreeze(pg)
            await pg.wait_for_timeout(DUR + 150)
        # --- меню разделов: клик по «Формы» (лист jumpSheet iris из пункта меню)
        await pg.evaluate("DC.go(4, {instant: true})")
        await pg.wait_for_timeout(300)
        await pg.click(".dcu-sec-b >> nth=2")
        await freeze(pg, 0.45, 800)
        await snap(pg, "menu_click_mid")
        await unfreeze(pg)
        await pg.wait_for_timeout(1300)
        checks["menu_click_cur"] = await pg.evaluate("DC.cur")
        checks["menu_click_backStack"] = await pg.evaluate("DC.backStack.slice()")
        await snap(pg, "menu_click_after_back_button")
        pill = await pg.evaluate("(() => { const p = document.querySelector('.dcu-pill'), it = document.querySelector('.dcu-sec.dcu-on'); return [p.style.transform, it.offsetLeft] })()")
        checks["menu_pill"] = pill
        # кнопка «вернуться»
        await pg.click(".dcu-back")
        await pg.wait_for_timeout(1200)
        checks["back_button_cur"] = await pg.evaluate("DC.cur")
        # --- ссылка с подсказкой и возврат
        await pg.evaluate("DC.go(4, {instant: true})")
        await pg.wait_for_timeout(400)
        bx = await pg.evaluate("(() => { const o = DC.data.slides[4].byName['go_ab']; return [o.x + o.w / 2, o.y + o.h / 2] })()")
        await pg.mouse.move(bx[0], bx[1])
        await pg.wait_for_timeout(350)
        await snap(pg, "link_hover_tip")
        await pg.mouse.click(bx[0], bx[1])
        await freeze(pg, 0.5, 800)
        await snap(pg, "link_jump_iris_mid")
        await unfreeze(pg)
        await pg.wait_for_timeout(1200)
        checks["link_cur"] = await pg.evaluate("DC.cur")
        await pg.mouse.move(700, 500)
        await snap(pg, "link_after_back_button")
        # A/B и шаги
        tg = await pg.evaluate("(() => { const o = DC.data.slides[20].byName['sw_bg']; return [o.x + o.w / 2, o.y + o.h / 2] })()")
        await pg.mouse.move(tg[0], tg[1])
        await pg.wait_for_timeout(300)
        await snap(pg, "toggle_hover")
        await pg.mouse.click(tg[0], tg[1])
        await pg.wait_for_timeout(900)
        checks["toggle_state"] = await pg.evaluate("DC.state.ab")
        await pg.keyboard.press("ArrowRight")
        await pg.wait_for_timeout(500)
        await pg.keyboard.press("ArrowRight")
        await pg.wait_for_timeout(700)
        checks["steps_done"] = await pg.evaluate("DC.data.slides[20].stepT.length")
        await pg.mouse.move(800, 600)
        await snap(pg, "toggle_B_steps_hud")
        await pg.keyboard.press("Backspace")
        await pg.wait_for_timeout(1200)
        checks["backspace_cur"] = await pg.evaluate("DC.cur")
        # --- подсказка на объекте без ссылки (iris)
        await pg.evaluate("DC.go(10, {instant: true})")
        await pg.wait_for_timeout(400)
        tp = await pg.evaluate("(() => { const o = DC.data.slides[10].byName['dot']; return [o.x + o.w / 2, o.y + o.h / 2] })()")
        await pg.mouse.move(tp[0] - 3, tp[1] - 3)
        await pg.mouse.move(tp[0], tp[1])
        await pg.wait_for_timeout(350)
        await snap(pg, "tip_lines")
        checks["tip_visible"] = await pg.evaluate("document.querySelector('.dcu-tip').classList.contains('dcu-show')")
        await pg.mouse.move(1500, 120)
        await pg.mouse.move(1560, 200)
        await pg.wait_for_timeout(200)
        # подсказка у края сцены не выходит за край
        await pg.evaluate("DC.go(21, {instant: true})")
        await pg.wait_for_timeout(400)
        e = await pg.evaluate("(() => { const o = DC.data.slides[21].byName['to_back']; return [o.x + o.w - 6, o.y + o.h / 2] })()")
        await pg.mouse.move(e[0] - 2, e[1])
        await pg.mouse.move(e[0], e[1])
        await pg.wait_for_timeout(300)
        rect = await pg.evaluate("(() => { const r = document.querySelector('.dcu-tip').getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom] })()")
        checks["tip_inside_stage"] = rect[0] >= 0 and rect[1] >= 0 and rect[2] <= 1600 and rect[3] <= 900
        await snap(pg, "tip_edge")
        # --- обзор
        await pg.evaluate("DC.go(6, {instant: true})")
        await pg.wait_for_timeout(300)
        await pg.keyboard.press("o")
        await pg.wait_for_timeout(500)
        await snap(pg, "overview")
        for key in ("ArrowRight", "ArrowRight", "ArrowDown"):
            await pg.keyboard.press(key)
            await pg.wait_for_timeout(120)
        await pg.wait_for_timeout(350)
        sel = await pg.evaluate("+document.querySelector('.dcu-th.dcu-sel').dataset.i")
        await snap(pg, "overview_select")
        await pg.keyboard.press("Enter")
        await pg.wait_for_timeout(1200)
        checks["overview_select_open"] = [sel, await pg.evaluate("DC.cur")]
        await pg.keyboard.press("Escape")
        await pg.wait_for_timeout(450)
        checks["esc_opens_overview"] = await pg.evaluate("DC.ui.state.ov")
        await pg.click(".dcu-th >> nth=3")
        await pg.wait_for_timeout(1200)
        checks["overview_click_cur"] = await pg.evaluate("DC.cur")
        # --- перо: рисунок хранится по слайду
        await pg.evaluate("DC.go(2, {instant: true})")
        await pg.wait_for_timeout(300)
        await pg.keyboard.press("d")
        await pg.wait_for_timeout(400)
        checks["pen_clickAdvance"] = await pg.evaluate("DC.clickAdvance")
        for (x0, y0, x1, y1) in ((300, 620, 900, 560), (320, 700, 1180, 690), (1200, 250, 1450, 420)):
            await pg.mouse.move(x0, y0)
            await pg.mouse.down()
            for t in range(1, 25):
                f = t / 24
                await pg.mouse.move(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f - 60 * (f * (1 - f)) * 4)
            await pg.mouse.up()
        await pg.click(".dcu-sw >> nth=1")
        await pg.mouse.move(1000, 300)
        await pg.mouse.down()
        for t in range(1, 30):
            await pg.mouse.move(1000 + 90 * math.cos(t / 29 * 6.28), 300 + 90 * math.sin(t / 29 * 6.28))
        await pg.mouse.up()
        checks["pen_cur_after_clicks"] = await pg.evaluate("DC.cur")
        await snap(pg, "pen")
        await pg.keyboard.press("ArrowRight")
        await pg.wait_for_timeout(1100)
        await pg.keyboard.press("ArrowLeft")
        await pg.wait_for_timeout(1100)
        checks["pen_strokes_restored"] = await pg.evaluate("(DC.ui.ink.strokes[2] || []).length")
        checks["pen_canvas_ink"] = await pg.evaluate("(() => { const c = document.querySelector('.dcu-ink'); const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i]) n++; return n })()")
        await snap(pg, "pen_restored")
        await pg.keyboard.press("Escape")
        await pg.wait_for_timeout(200)
        checks["pen_off_clickAdvance"] = await pg.evaluate("DC.clickAdvance === undefined ? 'undefined' : DC.clickAdvance")
        # --- указка
        await pg.keyboard.press("l")
        for t in range(28):
            await pg.mouse.move(700 + 260 * math.cos(t / 9), 450 + 150 * math.sin(t / 7))
            await pg.wait_for_timeout(12)
        await snap(pg, "laser")
        await pg.keyboard.press("l")
        # --- справка, номер, заметки
        await pg.keyboard.press("?")
        await pg.wait_for_timeout(300)
        await snap(pg, "help")
        await pg.keyboard.press("Escape")
        await pg.wait_for_timeout(200)
        await pg.keyboard.press("1")
        await pg.keyboard.press("5")
        await pg.wait_for_timeout(150)
        await snap(pg, "goto_15")
        await pg.keyboard.press("Enter")
        await pg.wait_for_timeout(1200)
        checks["goto_15_cur"] = await pg.evaluate("DC.cur")
        await pg.keyboard.press("n")
        await pg.mouse.move(820, 300)
        await pg.wait_for_timeout(450)
        await snap(pg, "notes_hud")
        await pg.keyboard.press("n")
        # кнопка в фокусе: Enter нажимает её, а не листает
        cur0 = await pg.evaluate("DC.cur")
        await pg.focus(".dcu-hud .dcu-b[aria-label^='Заметки']")
        await pg.keyboard.press("Enter")
        await pg.wait_for_timeout(300)
        checks["enter_on_button"] = [cur0, await pg.evaluate("DC.cur"), await pg.evaluate("DC.ui.state.notes")]
        await pg.keyboard.press("n")
        await pg.evaluate("document.activeElement && document.activeElement.blur()")
        # --- окно докладчика: вторая страница того же контекста
        await pg.evaluate("DC.go(5, {instant: true})")
        await pg.wait_for_timeout(200)
        pr = await ctx.new_page()
        hook(pr, "presenter")
        await pr.goto(uri + "?presenter#s6")
        await pr.wait_for_timeout(900)
        sync = {"start": [await pg.evaluate("DC.cur"), await pr.evaluate("DC.cur")]}
        await pg.evaluate("DC.go(8)")
        await pg.wait_for_timeout(500)
        sync["main→presenter"] = [8, await pr.evaluate("DC.cur")]
        await pr.evaluate("DC.next()")
        await pg.wait_for_timeout(500)
        sync["presenter→main"] = [9, await pg.evaluate("DC.cur")]
        await pr.keyboard.press("ArrowRight")
        await pg.wait_for_timeout(500)
        sync["presenter key→main"] = [10, await pg.evaluate("DC.cur")]
        await pg.evaluate("DC.go(20)")
        await pg.wait_for_timeout(600)
        await pr.evaluate("DC.next()")
        await pg.wait_for_timeout(400)
        sync["step presenter→main"] = [1, await pg.evaluate("DC.data.slides[20].stepT.length")]
        await pr.evaluate("DC.setState('ab', 'B')")
        await pg.wait_for_timeout(300)
        sync["state presenter→main"] = ["B", await pg.evaluate("DC.state.ab")]
        await pg.evaluate("DC.setState('ab', 'A')")
        await pr.wait_for_timeout(300)
        sync["state main→presenter"] = ["A", await pr.evaluate("DC.state.ab")]
        await pr.keyboard.press("d")
        r = await pr.evaluate("(() => { const r = document.getElementById('dc-stage').getBoundingClientRect(); return [r.left, r.top, r.width, r.height] })()")
        await pr.mouse.move(r[0] + r[2] * 0.15, r[1] + r[3] * 0.85)
        await pr.mouse.down()
        for t in range(1, 20):
            await pr.mouse.move(r[0] + r[2] * (0.15 + 0.03 * t), r[1] + r[3] * (0.85 - 0.01 * t))
        await pr.mouse.up()
        await pg.wait_for_timeout(400)
        sync["ink presenter→main"] = await pg.evaluate("(DC.ui.ink.strokes[20] || []).length")
        await pr.keyboard.press("Escape")
        await pr.wait_for_timeout(1300)
        await pr.screenshot(path=str(shots / "presenter.png"))
        files.append(str(shots / "presenter.png"))
        await pg.wait_for_timeout(200)
        await snap(pg, "presenter_main_side")
        checks["presenter_sync"] = sync
        await pr.close()
        # --- печать: страница на слайд
        await pg.emulate_media(media="print")
        await pg.wait_for_timeout(200)
        checks["print_pages_dom"] = await pg.evaluate("document.querySelectorAll('#dcu-print .dcu-page').length")
        pdf = out / "shots" / "deck_print.pdf"
        await pg.pdf(path=str(pdf), prefer_css_page_size=True, print_background=True)
        data = pdf.read_bytes()
        checks["print_pdf_pages"] = len(re.findall(rb"/Type\s*/Page[^s]", data))
        await pg.emulate_media(media="screen")
        await pg.evaluate("DC.ui.printDone()")
        # --- варианты меню
        for menu, slide in (("tabs", 11), ("stamp", 7), ("none", 4)):
            vp = await ctx.new_page()
            hook(vp, menu)
            await vp.goto(paths[menu].resolve().as_uri() + f"#s{slide + 1}")
            await vp.wait_for_timeout(700)
            await vp.mouse.move(800, 450)
            await vp.wait_for_timeout(200)
            await vp.screenshot(path=str(shots / f"menu_{menu}.png"))
            files.append(str(shots / f"menu_{menu}.png"))
            if menu == "tabs":
                await vp.click(".dcu-tab-b >> nth=3")
                await vp.wait_for_timeout(1300)
                checks["tabs_click_cur"] = await vp.evaluate("DC.cur")
                await vp.screenshot(path=str(shots / "menu_tabs_after.png"))
                files.append(str(shots / "menu_tabs_after.png"))
            if menu == "stamp":
                await vp.click(".dcu-st-sec >> nth=1")
                await vp.wait_for_timeout(1300)
                checks["stamp_click_cur"] = await vp.evaluate("DC.cur")
                await vp.screenshot(path=str(shots / "menu_stamp_after.png"))
                files.append(str(shots / "menu_stamp_after.png"))
            if menu == "none":
                checks["none_has_menu"] = await vp.evaluate("!!document.querySelector('.dcu-menu')")
                await vp.keyboard.press("o")
                await vp.wait_for_timeout(400)
                checks["none_overview"] = await vp.evaluate("DC.ui.state.ov")
                await vp.keyboard.press("Escape")
            await vp.close()
        await ctx.close()
        # --- prefers-reduced-motion
        rc = await b.new_context(viewport={"width": 1600, "height": 900}, reduced_motion="reduce")
        rp = await rc.new_page()
        hook(rp, "reduced")
        await rp.goto(uri)
        await rp.wait_for_timeout(300)
        for _ in range(3):
            await rp.keyboard.press("ArrowRight")
            await rp.wait_for_timeout(60)
        await rp.keyboard.press("o")
        await rp.wait_for_timeout(100)
        checks["reduced"] = [await rp.evaluate("DC.REDUCED"), await rp.evaluate("DC.cur"), await rp.evaluate("DC.ui.state.ov")]
        await rp.screenshot(path=str(shots / "reduced_overview.png"))
        files.append(str(shots / "reduced_overview.png"))
        await rc.close()
        # --- телефон: HUD помещается, свайп листает
        mc = await b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True, device_scale_factor=2)
        mp = await mc.new_page()
        hook(mp, "phone")
        await mp.goto(uri + "#s5")
        await mp.wait_for_timeout(500)
        await mp.touchscreen.tap(195, 422)  # центр сцены: касание листает
        await mp.wait_for_timeout(1100)
        hw = await mp.evaluate("(() => { const r = document.querySelector('.dcu-hud').getBoundingClientRect(); return [r.left, r.right] })()")
        checks["phone_hud_fits"] = hw[0] >= 0 and hw[1] <= 390
        checks["phone_tap_cur"] = await mp.evaluate("DC.cur")
        await mp.screenshot(path=str(shots / "phone.png"))
        files.append(str(shots / "phone.png"))
        await mc.close()
        await b.close()

    # листы контактов: 50 % каждого листа и полные ряды 30/50/75 %
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    w, h_ = 400, 225
    cols = 4
    mids = [(k, row[1]) for k, row in seq] + [(k + " ←", f) for k, f in rev]
    sheet = Image.new("RGB", (w * cols, (h_ + 30) * ((len(mids) + cols - 1) // cols)), "white")
    d = ImageDraw.Draw(sheet)
    for j, (k, f) in enumerate(mids):
        x, y = (j % cols) * w, (j // cols) * (h_ + 30)
        sheet.paste(Image.open(f).convert("RGB").resize((w, h_)), (x, y + 30))
        d.text((x + 8, y + 4), k, fill="black", font=font)
    sheet.save(shots / "sheets_mid.png")
    full = Image.new("RGB", (w * 3, (h_ + 30) * len(seq)), "white")
    d = ImageDraw.Draw(full)
    for j, (k, row) in enumerate(seq):
        d.text((8, j * (h_ + 30) + 4), f"{k}: 30 % · 50 % · 75 %", fill="black", font=font)
        for c, f in enumerate(row):
            full.paste(Image.open(f).convert("RGB").resize((w, h_)), (c * w, j * (h_ + 30) + 30))
    full.save(shots / "sheets_seq.png")
    return {"errors": errors, "checks": checks, "files": files,
            "sheet_mid": str(shots / "sheets_mid.png"), "sheet_seq": str(shots / "sheets_seq.png")}


def check(paths: dict[str, Path], out: Path) -> dict:
    res = asyncio.run(_check(paths, out))
    (out / "check.json").write_text(json.dumps({k: v for k, v in res.items() if k != "files"}, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
    return res


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    out = Path(argv[0])
    paths = build_all(out)
    print("собрано:", ", ".join(str(p) for p in paths.values()))
    if "--no-shots" in argv:
        return 0
    res = check(paths, out)
    print(json.dumps(res["checks"], ensure_ascii=False, indent=1))
    print("ошибок консоли:", len(res["errors"]))
    for e in res["errors"][:30]:
        print("  ", e)
    print("снимки:", out / "shots", "· листы:", res["sheet_mid"])
    return 1 if res["errors"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
