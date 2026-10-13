"""Проверки презентации до показа: «сначала измерь, потом чини».

lint()          — текст помещается (по метрикам шрифтов-заменителей), кегль, контраст, границы, пары Morph,
                  разнообразие макетов и приёмов, петли, плотность, антишаблоны.
xsd_check()     — строгая проверка слайдов по ISO/IEC 29500 pml.xsd (mc:AlternateContent -> Fallback).
render()        — LibreOffice -> PDF -> PNG; contact_sheet() — лист миниатюр всей презентации.
"""

from __future__ import annotations

import functools
import math

import re
import subprocess
import sys
import zipfile
from functools import lru_cache
from pathlib import Path

from lxml import etree
from PIL import Image, ImageDraw, ImageFont

from .model import O, Slide, apply_text_policy, parse_line, plain, resolve
from .profile import DEFAULT, DeckProfile, camera_like


def bbox_on_slide(o: O):
    if o.kind == "vec":
        from .vector import bbox_on_slide as vb
        return vb(o)
    return o.x, o.y, o.w, o.h
from .theme import APPROX_FONTS, SAFE_FONTS, SLIDE_H, SLIDE_W, Theme, contrast

FONT_FILES = {
    "Carlito": ("/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf", "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf"),
    "Liberation Sans": ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    "Liberation Serif": ("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"),
    "Liberation Mono": ("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf"),
    "DejaVu Sans": ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    "DejaVu Serif": ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"),
    "DejaVu Sans Mono": ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"),
}
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿\U0001F000-\U0001F2FF]")
LINE_HEIGHT = 1.2  # высота строки в долях кегля при межстрочном 100% (Calibri/Carlito ≈ 1,22)


# Замены с теми же метриками на macOS/Windows (Calibri ↔ Carlito, Arial ↔ Liberation Sans, …)
FONT_ALIASES = {
    "Carlito": [("Carlito-Regular.ttf", "Carlito-Bold.ttf"), ("calibri.ttf", "calibrib.ttf"), ("Calibri.ttf", "Calibri Bold.ttf")],
    "Liberation Sans": [("LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf"), ("arial.ttf", "arialbd.ttf"),
                        ("Arial.ttf", "Arial Bold.ttf")],
    "Liberation Serif": [("LiberationSerif-Regular.ttf", "LiberationSerif-Bold.ttf"), ("times.ttf", "timesbd.ttf"),
                         ("Times New Roman.ttf", "Times New Roman Bold.ttf")],
    "Liberation Mono": [("LiberationMono-Regular.ttf", "LiberationMono-Bold.ttf"), ("cour.ttf", "courbd.ttf"),
                        ("Courier New.ttf", "Courier New Bold.ttf")],
    "DejaVu Sans": [("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"), ("arial.ttf", "arialbd.ttf"), ("Arial.ttf", "Arial Bold.ttf")],
}
FONT_DIRS = [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), Path.home() / ".fonts",
             Path.home() / ".local/share/fonts", Path("/Library/Fonts"), Path("/System/Library/Fonts"),
             Path("/System/Library/Fonts/Supplemental"), Path.home() / "Library/Fonts",
             Path("C:/Windows/Fonts"), Path.home() / "AppData/Local/Microsoft/Windows/Fonts"]


@lru_cache(maxsize=64)
def _find_font_file(qa_font: str, bold: bool) -> str:
    """Файл шрифта для замеров: известный путь Linux → fc-match → поиск метрической замены в папках шрифтов ОС.
    Ничего не нашлось — пустая строка (font_obj возьмёт встроенный шрифт PIL, замеры станут приблизительными)."""
    files = FONT_FILES.get(qa_font)
    if files and Path(files[1 if bold else 0]).exists():
        return files[1 if bold else 0]
    import shutil
    if shutil.which("fc-match"):
        out = subprocess.run(["fc-match", "-f", "%{file}", f"{qa_font}:{'bold' if bold else 'regular'}"],
                             capture_output=True, text=True).stdout.strip()
        if out and Path(out).exists():
            return out
    for pair in FONT_ALIASES.get(qa_font, []):
        want = pair[1 if bold else 0]
        for d in FONT_DIRS:
            if d.exists():
                hit = next(iter(d.rglob(want)), None)
                if hit:
                    return str(hit)
    print(f"morphkit: шрифт {qa_font!r} не найден — замеры текста приблизительные (установите {qa_font})",
          file=sys.stderr)
    return ""


@lru_cache(maxsize=256)
def font_obj(qa_font: str, bold: bool, size_tenths: int) -> ImageFont.FreeTypeFont:
    path = _find_font_file(qa_font, bold)
    if not path:
        return ImageFont.load_default(size=max(size_tenths, 1))
    return ImageFont.truetype(path, size=max(size_tenths, 1))


def line_width_in(theme: Theme, o: O, line: str, runs=None) -> float:
    """Ширина строки в дюймах по метрикам шрифта-заменителя (кегль в pt, 72 pt = 1 дюйм)."""
    total = 0.0
    for run in (runs if runs is not None else parse_line(line)):
        face = theme.font("mono" if run.mono else o.font)
        bold = o.b if run.bold is None else run.bold
        text = run.text.upper() if o.caps else run.text
        f = font_obj(theme.qa_font(face), bold, int(o.sz * 10))
        total += f.getlength(text) / 10 / 72 + max(len(text) - 1, 0) * o.tracking / 72
    if o.bullets and line.strip():
        total += 0.25
    return total


def fit_text(objs: list[O], theme: Theme, margin: float = 0.97) -> list[O]:
    """Переносит строки текста по ширине рамки (метрики шрифта-заменителя, как в lint): абзац, который не
    помещается, делится по словам. Явные переносы (список строк) сохраняются как абзацы."""
    out = []
    for o in objs:
        if o.txt is None or not o.lines:
            out.append(o)
            continue
        inset = o.meta.get("inset", 0.0 if o.kind == "text" else 0.12)
        avail = (o.w - 2 * inset - (0.2 if o.kind != "text" else 0.0)) * margin
        lines = []
        for para in o.lines:
            if line_width_in(theme, o, para) <= avail or " " not in para.strip():
                lines.append(para)
                continue
            cur = ""
            for word in para.split(" "):
                cand = f"{cur} {word}" if cur else word
                if cur and line_width_in(theme, o, cand) > avail:
                    lines.append(cur)
                    cur = word
                else:
                    cur = cand
            lines.append(cur)
        out.append(o if len(lines) == len(o.lines) else o.copy(txt=lines))
    return out


def _text_extent(theme: Theme, o: O) -> tuple[float, float, float, float]:
    """Прямоугольник, который реально занимает текст (по метрикам и выравниванию), дюймы слайда."""
    inset = o.meta.get("inset", 0.0 if o.kind == "text" else 0.12)
    prepared = o.meta.get("runs")
    w = max(line_width_in(theme, o, ln, prepared[k] if prepared else None) for k, ln in enumerate(o.lines))
    w = min(w, o.w - 2 * inset)
    h = min(text_height_in(o), o.h)
    x = {"l": o.x + inset, "c": o.x + (o.w - w) / 2, "r": o.x + o.w - inset - w}.get(o.al, o.x + inset)
    y = {"t": o.y + inset, "m": o.y + (o.h - h) / 2, "b": o.y + o.h - inset - h}.get(o.va, o.y + inset)
    return x, y, w, h


def text_height_in(o: O) -> float:
    n = max(len(o.lines), 1)
    if o.meta.get("line_pts"):
        return n * o.meta["line_pts"] / 72 + max(n - 1, 0) * o.para_gap / 72
    return n * o.sz * LINE_HEIGHT * o.spacing / 72 + max(n - 1, 0) * o.para_gap / 72


def _bg_under(o: O, objs: list[O], slide_bg: str, theme: Theme) -> str:
    cx, cy = o.x + o.w / 2, o.y + o.h / 2
    best = theme.c(slide_bg)
    for other in objs:
        if other is o or other.z > o.z or other.fill is None or other.fa < 0.9 or other.kind in ("line", "arrow", "text", "arc", "donut"):
            continue
        if other.kind == "vec":
            from .vector import point_in_vec
            hit = point_in_vec(other, cx, cy)
        else:
            hit = other.x <= cx <= other.x + other.w and other.y <= cy <= other.y + other.h
        if hit:
            grad = other.meta.get("grad")
            best = theme.c(grad["stops"][len(grad["stops"]) // 2][1]) if grad else theme.c(other.fill)
    if o.fill is not None and o.fa >= 0.9:
        best = theme.c(o.fill)
    return best


def lint(slides: list[Slide], theme: Theme, strict: bool = False, profile: DeckProfile | None = None) -> list[dict]:
    issues = []
    profile = profile or DEFAULT
    slides = apply_text_policy(slides, profile.text_policy)

    def add(level, i, msg):
        issues.append({"level": level, "slide": i + 1, "msg": msg})

    _profile_checks(slides, profile, add)

    resolved = []
    for i, s in enumerate(slides):
        try:
            resolved.append(resolve(s))
        except ValueError as exc:
            add("error", i, str(exc))
            resolved.append(s.objs)
    dens = theme.density
    for i, (s, objs) in enumerate(zip(slides, resolved)):
        words = 0
        for o in objs:
            bx, by, bw, bh = bbox_on_slide(o)
            visible = not (bx + bw <= 0 or bx >= SLIDE_W or by + bh <= 0 or by >= SLIDE_H)
            partly_out = visible and (bx < -0.01 or by < -0.01 or bx + bw > SLIDE_W + 0.01 or by + bh > SLIDE_H + 0.01)
            if partly_out and not o.meta.get("bleed") and o.kind not in ("line", "arrow"):
                add("warn", i, f"{o.name}: частично за краем слайда (если это намеренный вылет — meta bleed=True)")
            if not o.lines or not visible:
                continue
            txt_all = " ".join(o.lines if o.meta.get("runs") else [plain(l) for l in o.lines])
            if not o.meta.get("texture"):
                words += len(txt_all.split())
            if EMOJI.search(txt_all):
                add("error", i, f"{o.name}: эмодзи в тексте")
            if o.sz < dens.min_any_pt - 1e-6 and not o.meta.get("texture"):
                add("error", i, f"{o.name}: кегль {o.sz} < {dens.min_any_pt} pt")
            inset = o.meta.get("inset", 0.0 if o.kind == "text" else 0.12)
            avail_w, avail_h = o.w - 2 * inset, o.h - 2 * inset
            approx = theme.font(o.font) in APPROX_FONTS
            slack = 0.90 if approx else 0.985
            prepared = o.meta.get("runs")
            for li, line in enumerate(o.lines):
                wl = line_width_in(theme, o, line, prepared[li] if prepared else None)
                if wl > avail_w * slack:
                    add("error", i, f"{o.name}: строка не помещается ({wl:.2f}\" > {avail_w * slack:.2f}\"): «{plain(line)[:50]}»")
            th = text_height_in(o)
            if th > avail_h + 0.02:
                add("error", i, f"{o.name}: текст выше рамки ({th:.2f}\" > {avail_h:.2f}\")")
            bg = _bg_under(o, objs, s.bg, theme)
            prepared = o.meta.get("runs")
            run_colors = ({r.color or o.col for line in prepared for r in line} if prepared
                          else {r.color or o.col for line in o.lines for r in parse_line(line)})
            for run in run_colors:
                ratio = contrast(theme.c(run), bg)
                need = 3.0 if (o.sz >= 24 or (o.b and o.sz >= 18.5)) else 4.5
                if ratio < need and not o.meta.get("decor"):
                    add("error", i, f"{o.name}: контраст {run} на {bg} = {ratio:.2f} < {need}")
        if words > dens.max_words_per_slide:
            add("warn", i, f"слов на слайде {words} > {dens.max_words_per_slide} (режим {dens.name}) — разделить слайд")
        # антишаблоны
        for o in objs:
            if o.kind == "rect" and o.h < 0.12 and o.w > 0.8 * SLIDE_W and not o.meta.get("allow_bar"):
                add("warn", i, f"{o.name}: полоса во всю ширину — шаблонный приём, лучше убрать")
            if o.kind in ("rect", "line") and o.h <= 0.06 and o.w < 4 and not o.meta.get("allow_bar"):
                above = [t for t in objs if t.lines and t.sz >= 28 and 0 < o.y - (t.y + text_height_in(t)) < 0.35
                         and abs(t.x - o.x) < 0.2]
                if above:
                    add("warn", i, f"{o.name}: акцентная черта под заголовком — шаблонный приём")
        loop_systems = len({lp.name.split("_")[0] for lp in s.loops})  # «sig_a», «sig_b» — одна система
        if loop_systems > profile.max_loop_systems:
            add("warn", i, f"{loop_systems} систем петель на слайде — больше двух отвлекает")
        for lp in s.loops:
            if not 1.0 <= lp.period <= 4.5:
                add("warn", i, f"петля {lp.kind}: период {lp.period} c вне спокойного диапазона 1–4,5 с")
    # эффекты библиотеки Fx и их стык с Morph: пара берёт геометрию статичного слайда, итог анимаций не учитывается
    for i, (s, objs) in enumerate(zip(slides, resolved)):
        names = {o.name for o in objs}
        prev = {o.name for o in resolved[i - 1] if o.is_morph} if i > 0 and s.transition == "morph" else set()
        nxt = ({o.name for o in resolved[i + 1] if o.is_morph}
               if i + 1 < len(slides) and slides[i + 1].transition == "morph" else set())
        for f in s.fx:
            try:
                cat = f.category
            except KeyError:
                add("error", i, f"Fx {f.key}: нет такого эффекта (presets.keys())")
                continue
            if f.target not in names:
                add("error", i, f"Fx {f.key}: нет объекта {f.target}")
                continue
            from .presets import model3d_only
            if f.key in model3d_only():
                add("error", i, f"Fx {f.key}: эффект 3D-модели, на фигуре не играет — взять 3D-поворот фигуры через Morph")
            if cat == "entrance" and f.target in prev:
                add("warn", i, f"Fx {f.key} на {f.target}: у объекта есть пара Morph на прошлом слайде — "
                               "во время перехода он скрыт и «проявится» второй раз; вход давать новым объектам")
            if cat in ("exit", "path") and f.target in nxt and not f.rev:
                add("warn", i, f"Fx {f.key} на {f.target}: пара Morph на следующем слайде стартует из статичного "
                               "положения — объект прыгнет назад; двигать объект лучше самим Morph")
            if f.dur is not None and not 0.2 <= f.dur <= 6 and not f.repeat:
                add("warn", i, f"Fx {f.key}: длительность {f.dur} c вне диапазона 0,2–6 с")
        moments = len({(round(f.delay, 2), f.start) for f in s.fx})  # слои одного лепестка стартуют вместе
        if moments > 24:
            add("warn", i, f"{moments} отдельных моментов анимации на слайде — дробить на шаги-слайды Morph")
    # гладкость кривых: длинная грань на изгибе видна как «рубленый» край (отзыв: цветок и бочка с обрезанными углами)
    for i, objs in enumerate(resolved):
        for o in objs:
            if o.kind != "vec" or o.meta.get("texture") or max(o.w, o.h) < 0.6:
                continue
            worst = 0.0
            from .vector import smooth_rings
            for ring in smooth_rings(o.meta["vec"], o.w, o.h):  # так форма уйдёт в pptx
                pts = [(x * o.w, y * o.h) for x, y in ring]
                m = len(pts)
                if m < 3:
                    continue
                L = [math.hypot(pts[(k + 1) % m][0] - pts[k][0], pts[(k + 1) % m][1] - pts[k][1]) for k in range(m)]
                ang = [math.atan2(pts[(k + 1) % m][1] - pts[k][1], pts[(k + 1) % m][0] - pts[k][0]) for k in range(m)]
                T = [abs((math.degrees(ang[k] - ang[k - 1]) + 180) % 360 - 180) for k in range(m)]  # поворот в вершине k
                for k in range(m):
                    # кусок дискретизованной кривой: 3 грани подряд похожей длины, повороты малые и одного порядка;
                    # длинные грани многоугольников (куб, изометрия, опоры) и намеренные углы сюда не попадают
                    seg = L[k]
                    if not (0.14 < seg < 0.9):
                        continue
                    nb = (L[k - 1], L[(k + 1) % m])
                    tt = (T[k], T[(k + 1) % m])
                    if all(0.6 < x / seg < 1.6 for x in nb) and all(5 < t < 35 for t in tt) and abs(tt[0] - tt[1]) < 8:
                        worst = max(worst, seg)
            if worst > 0.14:
                add("warn", i, f"{o.name}: грубый контур — грань {worst:.2f}\" на изгибе; больше точек "
                               "(vector.resample(g, n) с n ≥ 120) или полный контур без ресемпла")
    # пары свободных форм: Morph переливает форму честно при равном числе точек и не больше одной дырки
    for i in range(1, len(resolved)):
        if slides[i].transition != "morph":
            continue
        prev = {o.name: o for o in resolved[i - 1] if o.is_morph and o.kind == "vec"}
        for o in resolved[i]:
            p = prev.get(o.name)
            if p is None or o.kind != "vec":
                continue
            if [len(r) for r in p.meta["vec"]] != [len(r) for r in o.meta["vec"]] and p.meta["vec"] != o.meta["vec"]:
                add("warn", i, f"{o.name}: формы пары с разным числом точек — перелив непредсказуем, "
                               "подготовь обе через vector.resample(g, n)")
            if len(o.meta["vec"]) > 2:
                add("warn", i, f"{o.name}: больше одной дырки или частей — Morph заменит перелив затуханием")
    # пары Morph
    for i in range(1, len(resolved)):
        prev = {o.name for o in resolved[i - 1] if o.is_morph}
        cur = {o.name for o in resolved[i] if o.is_morph}
        if slides[i].transition == "morph" and not (prev & cur):
            add("warn", i, "Morph без единой пары !! с предыдущим слайдом — переход будет простым затуханием")
    # разнообразие
    scenes = []  # серия слайдов одного макета подряд (шаги Morph) — одна сцена
    for i, s in enumerate(slides):
        if s.layout and (not scenes or scenes[-1][1] != s.layout):
            scenes.append((i, s.layout))
    for k in range(0, max(len(scenes) - 7, 1)):
        window = scenes[k:k + 8]
        need = 4 if profile.allowed_layouts else 6  # замок стиля: набор макетов задан заранее и повторяется
        if len(window) == 8 and len({l for _, l in window}) < need:
            add("warn", window[0][0], f"на сценах со слайда {window[0][0] + 1} по {window[-1][0] + 1} всего "
                                      f"{len({l for _, l in window})} разных макетов из 8 (нужно ≥ {need})")
    for i, objs in enumerate(resolved):  # тексты не должны налезать друг на друга (подпись на заголовок и т.п.)
        boxes = [(o, _text_extent(theme, o)) for o in objs if o.lines and not o.meta.get("texture")
                 and not o.meta.get("overlap_ok")]
        boxes = [(o, b) for o, b in boxes if b[2] > 0 and -0.5 < b[0] < SLIDE_W and -0.5 < b[1] < SLIDE_H]
        for a in range(len(boxes)):
            for b in range(a + 1, len(boxes)):
                (oa, ba), (ob, bb) = boxes[a], boxes[b]
                ix = min(ba[0] + ba[2], bb[0] + bb[2]) - max(ba[0], bb[0])
                iy = min(ba[1] + ba[3], bb[1] + bb[3]) - max(ba[1], bb[1])
                if ix > 0.04 and iy > 0.04:
                    add("error", i, f"тексты накладываются: {oa.name} и {ob.name} ({ix:.2f}\" × {iy:.2f}\")")
    techs = [(i, s.technique) for i, s in enumerate(slides) if s.technique]
    for (i1, t1), (i2, t2) in zip(techs, techs[1:]):
        if t1 == t2 and i2 == i1 + 1 and "серия" not in t1:
            add("warn", i2, f"приём «{t1}» повторяется на двух переходах подряд")
    return issues


def print_issues(issues: list[dict]) -> None:
    for it in issues:
        print(f"[{it['level']:5}] слайд {it['slide']:>2}: {it['msg']}")
    errors = sum(1 for it in issues if it["level"] == "error")
    print(f"итого: ошибок {errors}, предупреждений {len(issues) - errors}")


# ----------------------------------------------------------------------------- XSD и рендер

SKILL_PPTX = Path("/mnt/skills/public/pptx")
# Схемы ECMA/ISO и обёртка soffice берутся из скилла pptx от Anthropic, если он установлен; сами схемы плагин не везёт.
# Рекомендуемая установка:  claude plugin marketplace add anthropics/skills
#                           claude plugin install document-skills@anthropic-agent-skills
PPTX_SKILL_BASES = [Path.home() / ".claude/skills/synced", Path.home() / ".claude/plugins/cache/anthropic-agent-skills",
                    Path.home() / ".claude/plugins/marketplaces/anthropic-agent-skills", Path.home() / ".claude/skills",
                    SKILL_PPTX.parent]
XSD_HINT = ("XSD-проверка пропущена: нет схем OOXML. Для полной проверки установите скилл pptx от Anthropic: "
            "claude plugin marketplace add anthropics/skills && "
            "claude plugin install document-skills@anthropic-agent-skills")


@functools.lru_cache(maxsize=1)
def _schema_dir() -> Path | None:
    for base in PPTX_SKILL_BASES:
        hits = sorted(base.glob("**/ISO-IEC29500-4_2016/pml.xsd")) if base.exists() else []
        if hits:
            return hits[0].parent
    return None


def xsd_available() -> bool:
    return _schema_dir() is not None


def xsd_check(pptx: str | Path, required: bool = False) -> list[str]:
    """Строгая проверка слайдов и заметок по pml.xsd. Нет схем — предупреждение в stderr и [] (или ошибка при required)."""
    d = _schema_dir()
    if d is None:
        if required:
            raise FileNotFoundError(XSD_HINT)
        print(XSD_HINT, file=sys.stderr)
        return []
    schema = etree.XMLSchema(etree.parse(str(d / "pml.xsd")))
    mc = "http://schemas.openxmlformats.org/markup-compatibility/2006"
    errors = []
    with zipfile.ZipFile(pptx) as z:
        for name in sorted(n for n in z.namelist() if n.startswith(("ppt/slides/slide", "ppt/notesSlides/")) and n.endswith(".xml")):
            root = etree.fromstring(z.read(name))
            for ac in list(root.iter(f"{{{mc}}}AlternateContent")):
                fb = ac.find(f"{{{mc}}}Fallback")
                parent = ac.getparent()
                pos = list(parent).index(ac)
                parent.remove(ac)
                if fb is not None:
                    for k, child in enumerate(list(fb)):
                        parent.insert(pos + k, child)
            clean = etree.fromstring(etree.tostring(root))
            if not schema.validate(clean):
                errors += [f"{name}:{e.line}: {e.message}" for e in schema.error_log]
    return errors


def _soffice() -> list[str]:
    for base in PPTX_SKILL_BASES:
        hits = sorted(base.glob("**/pptx/scripts/office/soffice.py")) if base.exists() else []
        if hits:
            return [sys.executable, str(hits[0])]
    return ["soffice"]


def render(pptx: str | Path, out_dir: str | Path, dpi: int = 60) -> list[Path]:
    pptx, out_dir = Path(pptx), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(_soffice() + ["--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(pptx)],
                   capture_output=True, check=True)
    pdf = out_dir / (pptx.stem + ".pdf")
    prefix = out_dir / pptx.stem
    for old in out_dir.glob(pptx.stem + "-*.png"):
        old.unlink()
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), str(pdf), str(prefix)], check=True)
    return sorted(out_dir.glob(pptx.stem + "-*.png"))


def contact_sheet(pngs: list[Path], out: str | Path, titles: list[str] | None = None, cols: int = 4,
                  thumb_w: int = 480) -> Path:
    thumbs = [Image.open(p).convert("RGB") for p in pngs]
    th = int(thumb_w * SLIDE_H / SLIDE_W)
    label_h = 28
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (thumb_w + 16) + 16, rows * (th + label_h + 16) + 16), (235, 235, 235))
    draw = ImageDraw.Draw(sheet)
    font = font_obj("DejaVu Sans", False, 15)
    for k, im in enumerate(thumbs):
        r, c = divmod(k, cols)
        x, y = 16 + c * (thumb_w + 16), 16 + r * (th + label_h + 16)
        sheet.paste(im.resize((thumb_w, th)), (x, y + label_h))
        label = f"{k + 1}. {titles[k] if titles and k < len(titles) else ''}"[:60]
        draw.text((x, y + 4), label, fill=(30, 30, 30), font=font)
    out = Path(out)
    sheet.save(out)
    return out


def _profile_checks(slides: list[Slide], profile: DeckProfile, add) -> None:
    """Правила профиля презентации (выводы из записей показа): навигация, режимы текста, скорость, замок стиля, дубли."""
    for i, s in enumerate(slides):
        if s.auto is not None and not profile.allow_auto:
            add("error", i, "служебный автослайд: при листании назад показ снова уводит вперёд — рост из нуля "
                            "делать эффектами внутри слайда (recipes.reveal / ring)")
        texts = [o for o in s.objs if o.lines and not o.meta.get("texture")]
        if s.mode in ("byWord", "byChar") and len(texts) > 1 and not profile.allow_char_modes:
            add("error", i, f"режим {s.mode} действует на все {len(texts)} текста слайда — буквы улетят в соседние "
                            "надписи; показать правку зачёркиванием и появлением нового значения")
        if i > 0 and s.transition == "morph":
            limit = profile.max_camera_ms if camera_like(s.technique) else profile.max_morph_ms
            if s.dur > limit:
                add("warn", i, f"Morph {s.dur} мс > {limit} мс профиля — медленно")
        if i > 0 and s.transition not in ("morph", "none") and s.dur > profile.max_fade_ms:
            add("warn", i, f"переход {s.transition} {s.dur} мс > {profile.max_fade_ms} мс профиля")
        tech = s.technique.lower().replace("(серия)", "").strip()
        if tech:
            for b in profile.banned_techniques:
                if b in tech:
                    add("error", i, f"приём «{s.technique}» отвергнут профилем (см. techniques.md, «Отвергнутые»)")
            if profile.allowed_techniques and not any(a in tech for a in profile.allowed_techniques):
                add("error", i, f"приём «{s.technique}» не входит в профиль презентации — замок стиля")
        if profile.allowed_layouts and s.layout and s.layout not in profile.allowed_layouts:
            add("error", i, f"макет «{s.layout}» не входит в профиль презентации — новый стиль посреди презентации")
        if s.bg not in profile.backgrounds:
            add("error", i, f"фон «{s.bg}» не входит в профиль ({', '.join(profile.backgrounds)}) — смена стиля посреди презентации")
        seen = {}
        for o in texts:
            t = " ".join(plain(l) for l in o.lines).strip().lower()
            if len(t) > 3:
                if t in seen:
                    add("error", i, f"текст «{t[:40]}» на слайде дважды ({seen[t]} и {o.name})")
                seen[t] = o.name
    for i in range(1, len(slides)):  # линии, которые перевернутся при Morph
        if slides[i].transition != "morph":
            continue
        prev = {o.name: o for o in slides[i - 1].objs if o.is_morph and o.kind in ("line", "arrow")}
        for o in slides[i].objs:
            p = prev.get(o.name)
            if p is not None and o.kind in ("line", "arrow") and ((p.w < 0) != (o.w < 0) or (p.h < 0) != (o.h < 0)):
                add("warn", i, f"{o.name}: направление линии меняется — при Morph она перевернётся через ноль")


def lo_effects_check(pptx: str | Path, workdir: str | Path | None = None) -> dict:
    """Импорт в LibreOffice: каждый эффект PowerPoint (cTn с presetClass) должен стать пресетом ooo-…
    (`presentation:preset-id`). Возвращает {'pptx': n, 'odp': n, 'unknown': [...]}. Расхождение — эффект,
    который другие программы не узнают (часто — ошибка в XML эффекта)."""
    import re as _re
    import subprocess
    import tempfile
    import zipfile as _zip
    pptx = Path(pptx)
    n_pptx = n_custom = 0
    with _zip.ZipFile(pptx) as z:
        for name in z.namelist():
            if _re.match(r"ppt/slides/slide\d+\.xml$", name):
                x = z.read(name).decode("utf8")
                n_pptx += len(_re.findall(r'presetClass="(?:entr|emph|exit|path)"', x))
                n_custom += len(_re.findall(r'presetID="0" presetClass="path"', x))  # свои траектории: без preset-id
    import shutil
    if not shutil.which("soffice"):
        return {"pptx": n_pptx - n_custom, "odp": None, "custom_paths": n_custom, "odp_motions": None, "ok": None,
                "unknown": [], "skipped": "нет LibreOffice (soffice) — распознавание эффектов не проверялось"}
    out = Path(workdir or tempfile.mkdtemp())
    subprocess.run(["soffice", "--headless", "--convert-to", "odp", "--outdir", str(out), str(pptx)],
                   capture_output=True, timeout=300)
    odp = out / (pptx.stem + ".odp")
    with _zip.ZipFile(odp) as z:
        content = z.read("content.xml").decode("utf8")
    ids = _re.findall(r'presentation:preset-id="([^"]+)"', content)
    motions = len(_re.findall(r"<anim:animateMotion", content))
    return {"pptx": n_pptx - n_custom, "odp": len(ids), "custom_paths": n_custom, "odp_motions": motions,
            "ok": len(ids) == n_pptx - n_custom and motions >= n_custom,
            "unknown": sorted({i for i in ids if not i.startswith("ooo-")})}


def motion_lint(slides: list[Slide], theme: Theme, samples: tuple = (0.35, 0.5, 0.65),
                min_move: float = 0.4) -> list[dict]:
    """Ошибки движения на переходах Morph: фигура, которая ЛЕТИТ (сдвиг > min_move) поверх текста, стоящего на
    обоих слайдах (или появляющегося на новом), — «точки улетают перед текстом». Проверка по промежуточным
    состояниям (как в предпросмотре motion.py)."""
    from .model import apply_text_policy
    from .motion import _interp
    out = []
    slides = apply_text_policy(slides, "fade")
    for i in range(1, len(slides)):
        hx = lambda o: o.copy(fill=theme.c(o.fill), ln=theme.c(o.ln), col=theme.c(o.col))  # noqa: E731
        a, b = [hx(o) for o in resolve(slides[i - 1])], [hx(o) for o in resolve(slides[i])]
        if slides[i].transition != "morph":
            continue
        by_a = {o.name: o for o in a}
        texts = [o for o in b if o.lines and o.name in by_a and not o.meta.get("overlap_ok")]
        boxes = [(o, _text_extent(theme, o)) for o in texts]
        hits = set()
        for o in b:
            if o.lines or o.name not in by_a or not o.name.startswith("!!") or o.meta.get("decor_ok"):
                continue
            p = by_a[o.name]
            if math.dist((p.x + p.w / 2, p.y + p.h / 2), (o.x + o.w / 2, o.y + o.h / 2)) < min_move:
                continue
            for t in samples:
                q = _interp(p, o, t)[0][0]
                for tx, (bx, by, bw, bh) in boxes:
                    if q.z <= tx.z:
                        continue
                    if q.x < bx + bw and bx < q.x + q.w and q.y < by + bh and by < q.y + q.h:
                        hits.add((o.name, tx.name))
        for on, tn in sorted(hits)[:12]:
            out.append({"level": "warn", "slide": i + 1, "msg": f"{on} пролетает поверх текста {tn} на переходе"})
    return out
