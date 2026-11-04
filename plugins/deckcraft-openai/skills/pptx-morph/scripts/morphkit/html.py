"""deckcraft 0.3.0: слайды morphkit → один самодостаточный HTML (web-движок morphkit/web/*.js).

    from morphkit.html import export_html, web, link
    web(slide, sec=1, sheet="sheetIn", scenes=[...], steps=[["!!a"], ["!!b"]], fx=[...], cascade={"by": "x"})
    link(obj, slide=12)            # объект — кнопка: переход (со стеком «назад»), раздел, состояние, ссылка
    export_html(slides, theme, "deck.html", title="…", sections=["Задача", "Данные", …])

Python разрешает то, что знает только движок: камеру, политику текста, роли цветов, контуры (нормированные точки
свободных форм — те же, что уходят в custGeom), сглаживание, градиенты, план эффектов и петли. Всё, что только для HTML,
хранится в `slide.web` (dict) и в `o.meta` (link, tip, ease, lag, draw, when) — сборка .pptx эти поля не читает.
Модули проигрывателя — morphkit/web/*.js и *.css; порядок: core.js, затем draw, fx, scenes, sheets, ui, остальные.
Контракт модулей — morphkit/web/CONTRACT.md (EN) и CONTRACT.ru.md.
"""

from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path

from .model import O, Slide, apply_text_policy, parse_line, resolve
from .motion import FX_START, _local_polys
from .presets import duration_ms, registry
from .qa import LINE_HEIGHT
from .theme import SLIDE_H, SLIDE_W, Theme
from .vector import smooth_rings

PX = 1600 / SLIDE_W  # пикселей на дюйм
WEB = Path(__file__).with_name("web")
ORDER = ["core.js", "draw.js", "fx.js", "scenes.js", "sheets.js", "ui.js"]
FALLBACK = {"Calibri": "Calibri, Carlito, 'Segoe UI', Arial, sans-serif",
            "Arial": "Arial, 'Liberation Sans', Helvetica, sans-serif",
            "Courier New": "'Courier New', 'Liberation Mono', 'IBM Plex Mono', monospace"}
META_KEYS = ("link", "tip", "ease", "lag", "draw", "when", "web")  # + "alt" (состояния) — ниже
WEB_CAT = {"in": "entrance", "em": "emphasis", "out": "exit", "path": "path"}


# ------------------------------------------------------------------------------ API для генераторов
def web(slide: Slide, **kw) -> Slide:
    """Поля только для HTML: autoState ([{"at": с, "set": {ключ: значение}, "reset": {ключ: значение при входе}}] —
    переключения сами по времени), sec (раздел), sheet (лист-переход: имя или {"k", "dur", ...}), jumpSheet, scenes (список
    {"k": …} для DC.scenes), steps (группы имён по кликам), fx (эффекты web: {"key": "in.stamp", "target", "delay",
    "dur", "options", "step"}), cascade ({"by": "x"|"y"|"radial"|"-x", "amount": с}), loops (доп. петли web)."""
    d = dict(getattr(slide, "web", None) or {})
    for k, v in kw.items():
        if k in ("scenes", "fx", "loops") and k in d:
            d[k] = list(d[k]) + list(v)
        else:
            d[k] = v
    slide.web = d
    return slide


def alt(o: O, key: str, dflt, values: dict) -> O:
    """Состояния объекта для переключателей: values = {значение: вариант O (та же форма, другое место/размер/цвет/
    контур с тем же числом точек)}. Объект o — вид при значении по умолчанию dflt. По клику (link set/toggle) объект
    плавно переходит к варианту (пружина 0,65 с)."""
    vals = dict(values)
    vals.setdefault(dflt, o.copy())
    o.meta = dict(o.meta, alt={"key": key, "dflt": dflt, "values": vals})
    return o


def link(o: O, **target) -> O:
    """Сделать объект кнопкой: slide=i | section=k | back=True | href=url | set={...} | toggle=key (values=[...]) |
    step=True. tip=… — подсказка при наведении."""
    tip = target.pop("tip", None)
    o.meta = dict(o.meta, link=target)
    if tip:
        o.meta["tip"] = tip
    return o


def for_pptx(slides: list[Slide], state: dict | None = None) -> list[Slide]:
    """Копии слайдов для .pptx-двойника web-презентации: интерактив сворачивается в один кадр. Объекты `when` остаются
    только для значения по умолчанию (или из state), объекты с `alt` — в виде этого значения; обычный текст, накрытый
    видимым `when`-двойником с тем же текстом в той же рамке (подложка кнопки), убирается; эффекты и петли без цели —
    тоже."""
    import copy
    state = state or {}
    out = []
    for s in slides:
        objs = []
        for o in s.objs:
            w = o.meta.get("when")
            if w and str(state.get(w["key"], w.get("dflt"))) != str(w["is"]):
                continue
            a = o.meta.get("alt")
            if a and str(state.get(a["key"], a["dflt"])) != str(a["dflt"]):
                v = a["values"].get(state[a["key"]])
                if v is not None:
                    o = o.copy(x=v.x, y=v.y, w=v.w, h=v.h, rot=v.rot, fill=v.fill, fa=v.fa, meta=dict(o.meta, vec=v.meta.get("vec", o.meta.get("vec"))))
            objs.append(o)

        def sig(o):
            return tuple(o.lines), round(o.x, 2), round(o.y, 2), round(o.w, 2), round(o.h, 2)
        cover = {sig(o) for o in objs if "when" in o.meta and o.lines}
        objs = [o for o in objs if "when" in o.meta or not o.lines or sig(o) not in cover]
        names = {o.name for o in objs}
        c = copy.copy(s)
        c.objs = objs
        c.fx = [f for f in s.fx if getattr(f, "target", None) in (None, *names)]
        c.loops = [lp for lp in s.loops if lp.target is None or lp.target in names]
        c.anims = [n for n in s.anims if n in names]
        out.append(c)
    return out


# ------------------------------------------------------------------------------ сериализация
def _hex(theme: Theme, c: str | None) -> str | None:
    if c is None:
        return None
    v = theme.c(c)
    return "#" + v if v and not v.startswith("#") else v


def _rings(o: O) -> list[list[float]]:
    if o.kind == "vec":
        rings = smooth_rings(o.meta.get("vec", []), o.w, o.h)
    else:
        oo = o.copy(rot=0.0)
        w, h = max(o.w, 1e-6), max(o.h, 1e-6)
        rings = [[((x - o.x) / w, (y - o.y) / h) for x, y in r] for r in _local_polys(oo)]
    return [[round(v, 4) for p in r for v in p] for r in rings if len(r) >= 3]


def _text(o: O, theme: Theme) -> dict:
    lines = [[[r.text.upper() if o.caps else r.text, _hex(theme, r.color) if r.color else None, r.bold, bool(r.mono)]
              for r in parse_line(line)] for line in o.lines]
    inset = o.meta.get("inset", 0.0 if o.kind == "text" else 0.12)
    return {"lines": lines, "sz": o.sz, "col": _hex(theme, o.col), "b": o.b,
            "font": FALLBACK.get(theme.font(o.font), f"'{theme.font(o.font)}', sans-serif"),
            "mono": FALLBACK.get(theme.font("mono")), "al": o.al, "va": o.va, "sp": o.spacing, "pg": o.para_gap,
            "tr": o.tracking, "inset": inset, "lh": LINE_HEIGHT}


def _img(path: str) -> str:
    p = Path(path)
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


class _Pool:
    def __init__(self):
        self.items, self.index = [], {}

    def add(self, rings) -> int:
        key = json.dumps(rings, separators=(",", ":"))
        if key not in self.index:
            self.index[key] = len(self.items)
            self.items.append(rings)
        return self.index[key]


def _resolve_colors(v, theme):
    """Цвета в meta/web: роли темы → hex (строки вида 'accent', 'ink2' …), рекурсивно."""
    if isinstance(v, str) and v in theme.colors:
        return _hex(theme, v)
    if isinstance(v, dict):
        return {k: (_resolve_colors(x, theme) if k in ("color", "c", "fill", "ink", "stroke", "col", "colors", "bg")
                    or isinstance(x, (dict, list)) else x) for k, x in v.items()}
    if isinstance(v, list):
        return [_resolve_colors(x, theme) for x in v]
    return v


def _obj(o: O, theme: Theme, imgs: dict, pool: _Pool) -> dict:
    d = {"n": o.name, "k": o.kind, "x": round(o.x * PX, 2), "y": round(o.y * PX, 2), "w": round(o.w * PX, 2),
         "h": round(o.h * PX, 2), "r": round(o.rot, 3), "z": o.z, "f": _hex(theme, o.fill), "fa": o.fa,
         "s": _hex(theme, o.ln), "sw": round(o.lw * PX / 72, 3), "la": o.la}
    if o.dash:
        d["dash"] = o.dash
    if o.kind in ("line", "arrow"):
        d["k"] = "line"
        if o.head or o.kind == "arrow":
            d["head"] = o.head or "triangle"
    elif o.kind == "img" and o.img:
        imgs.setdefault(o.img, _img(o.img))
        d["img"] = o.img
    elif o.kind != "text":
        d["k"] = "path"
        if not o.meta.get("draw"):  # элемент рисования строит модуль draw — запасной контур только для .pptx
            d["rp"] = pool.add(_rings(o))
        g = o.meta.get("grad")
        if g and g.get("stops"):
            d["grad"] = {"a": g.get("angle", 90), "kind": g.get("kind", "linear"),
                         "stops": [[st[0], _hex(theme, st[1]), st[2] if len(st) > 2 else 1.0] for st in g["stops"]]}
    if o.lines:
        d["t"] = _text(o, theme)
    for k in META_KEYS:
        if k in o.meta:
            d[k] = _resolve_colors(o.meta[k], theme)
    if "alt" in o.meta:  # варианты объекта по состоянию: {"key", "dflt", "values": {значение: O}} → поля в px
        a = o.meta["alt"]
        vals = {}
        for val, oo in a["values"].items():
            x = _obj(oo.copy(name=o.name, meta={k: v for k, v in oo.meta.items() if k != "alt"}), theme, imgs, pool)
            vals[str(val)] = {k: x[k] for k in ("x", "y", "w", "h", "r", "f", "fa", "s", "sw", "la", "rp") if k in x}
        d["alt"] = {"key": a["key"], "dflt": str(a["dflt"]), "values": vals, "dur": a.get("dur", 650),
                    "ease": a.get("ease", "spring")}
    return d


def _cat(key: str) -> str:
    if "." in key:
        return WEB_CAT.get(key.split(".", 1)[0], "entrance")
    if key == "path_custom":
        return "path"
    return registry()[key]["category"]


def _plan(s: Slide, w: dict, theme: Theme | None = None) -> dict:
    """Все эффекты слайда: имя → [[ключ, старт с, длительность с, опции, шаг, категория], …] (правила with/after/at)."""
    steps = {n: k for k, names in enumerate(w.get("steps", [])) for n in names}
    entries = [(f.key, f.target, f.delay, duration_ms(f) / 1000, f.start, dict(f.options),
                [list(p) for p in f.path] if isinstance(f.path, list) else None, f.repeat) for f in s.fx]
    for f in w.get("fx", []):
        entries.append((f["key"], f["target"], f.get("delay", 0.0), f.get("dur", 0.6), f.get("start", "at"),
                        dict(f.get("options", {})), None, f.get("repeat", False), f.get("step")))
    plan, prev, end = {}, 0.0, 0.0
    for e in entries:
        key, target, lag, dur, start, opt, path, rep = e[:8]
        st = {"with": prev + lag, "after": end + lag, "at": lag}.get(start, lag)
        if theme is not None:
            opt = _resolve_colors(opt, theme)
        if path:
            p0 = path[0]
            opt["path"] = [[x - p0[0] + p0[0], y - p0[1] + p0[1]] for x, y in path]
        if rep:
            opt["repeat"] = True
        step = e[8] if len(e) > 8 and e[8] is not None else steps.get(target)
        plan.setdefault(target, []).append([key, round(st, 3), round(dur, 3), opt, step, _cat(key)])
        prev = st
        if not rep:
            end = max(end, st + dur)
    for n, k in steps.items():  # объект в шаге без своего эффекта — проявляется по клику
        if not any(x[5] == "entrance" for x in plan.get(n, [])):
            plan.setdefault(n, []).append(["entrance_fade", 0.0, 0.4, {}, k, "entrance"])
    return plan


def _loops(loops, theme: Theme) -> list[dict]:
    out = []
    for lp in loops:
        if isinstance(lp, dict):
            out.append(_resolve_colors(dict({"start": 0.0, "z": 5}, **lp), theme))
            continue
        d = {"k": lp.kind, "target": lp.target, "period": lp.period, "n": lp.n, "size": lp.size * PX,
             "color": _hex(theme, lp.color), "scale": lp.scale, "start": lp.start, "rev": lp.reverse, "z": lp.z}
        if lp.points:
            d["pts"] = [[round(x * PX, 2), round(y * PX, 2)] for x, y in lp.points]
        out.append(d)
    return out


def scene(slides: list[Slide], theme: Theme, sections: list[str] | None = None, text_policy: str = "fade",
          **deck) -> dict:
    """text_policy: "fade" — пары !!… с изменённым текстом рвутся (правило профиля: текст не переливается; кроме
    meta morph_text=True), "morph" — пары сохраняются, текст переливает DC.textMorph (числа считают, буквы съезжаются)."""
    webs = [dict(getattr(s, "web", None) or {}) for s in slides]
    if text_policy != "morph":
        slides = apply_text_policy(slides)
    imgs: dict = {}
    pool = _Pool()
    data, sec_start = [], {}
    for i, (s, w) in enumerate(zip(slides, webs)):
        objs = [_obj(o, theme, imgs, pool) for o in resolve(s)
                if (o.meta.get("draw") or {}).get("kind") != "pptx"]  # части только для .pptx в HTML не нужны
        sec = w.get("sec")
        if sec is not None:
            sec_start.setdefault(sec, i)
        d = {"title": s.title or f"слайд {i + 1}", "notes": s.notes or "", "dur": s.dur,
             "tr": s.transition if i else "none", "bg": _hex(theme, s.bg), "objs": objs, "fx": _plan(s, w, theme),
             "loops": _loops(list(s.loops) + list(w.get("loops", [])), theme),
             "scenes": _resolve_colors(w.get("scenes", []), theme), "steps": w.get("steps", []), "sec": sec}
        for k in ("sheet", "jumpSheet", "cascade", "label", "nav", "autoState"):
            if k in w:
                d[k] = _resolve_colors(w[k], theme)
        data.append(d)
    secs = [{"title": t, "start": sec_start.get(k, 0)} for k, t in enumerate(sections or [])]
    if "lang" not in deck:  # язык интерфейса показа и форматов чисел — язык презентации (morphkit.i18n)
        from .i18n import get_lang
        deck["lang"] = get_lang()
    colors = {k: _hex(theme, k) for k in theme.colors}
    return {"w": 1600, "h": round(1600 * SLIDE_H / SLIDE_W), "fxStart": FX_START, "slides": data, "imgs": imgs,
            "pool": pool.items, "colors": colors, "sections": secs,
            "fonts": {r: FALLBACK.get(theme.font(r), theme.font(r)) for r in ("head", "body", "mono")}, **deck}


def _assets(modules: list[str] | None = None) -> tuple[str, str]:
    js = [p for p in sorted(WEB.glob("*.js"))]
    js.sort(key=lambda p: (ORDER.index(p.name) if p.name in ORDER else len(ORDER), p.name))
    if modules is not None:
        js = [p for p in js if p.name == "core.js" or p.stem in modules]
    css = sorted(WEB.glob("*.css"), key=lambda p: (p.name != "base.css", p.name))
    return ("\n".join(p.read_text(encoding="utf-8") for p in css),
            "\n".join(f"/* ---- {p.name} ---- */\n" + p.read_text(encoding="utf-8") for p in js))


def export_html(slides: list[Slide], theme: Theme, path: str | Path, title: str = "Презентация",
                sections: list[str] | None = None, modules: list[str] | None = None, **deck) -> Path:
    path = Path(path)
    sc = scene(slides, theme, sections, title=title, **deck)
    data = json.dumps(sc, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    css, js = _assets(modules)
    html = (TEMPLATE.replace("__LANG__", sc.get("lang", "ru")).replace("__TITLE__", title).replace("__CSS__", css).replace("__DATA__", data)
            .replace("__JS__", js))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


TEMPLATE = """<!doctype html><html lang="__LANG__"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>__CSS__</style></head><body>
<div id="dc-stage" role="region" aria-roledescription="презентация" aria-label="__TITLE__">
<svg id="dc-svg" viewBox="0 0 1600 900" xmlns="http://www.w3.org/2000/svg"><defs></defs><rect id="dc-bg" width="1600" height="900"/>
<g id="dc-under"></g><g class="dc-root" id="dc-root"></g><g id="dc-over"></g></svg>
<div class="dc-overlay" id="dc-overlay"></div></div>
<script type="application/json" id="dc-data">__DATA__</script>
<script>__JS__
DC.start();</script></body></html>"""
