"""Стилевые превью «покажи, а не рассказывай»: один и тот же бриф в нескольких направлениях.

Для каждого направления собирается мини-колода (титул -> содержательный слайд со схемой и потоком -> тот же
слайд после Morph), рендерится в PNG и складывается в общий лист сравнения. Пользователь выбирает глазами.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw

from .build import build_pptx
from .components import Kit
from .model import Loop, O, Slide
from .qa import contact_sheet, font_obj, lint, render, xsd_check
from .theme import SLIDE_H, SLIDE_W, Theme


@dataclass
class Brief:
    label: str
    title: str
    lead: str
    meta: str
    stages: list[tuple[str, str]]  # (подпись узла, моно-подпись)
    cards: list[tuple[str, str, str]]  # (kicker, title, body)
    content_title: str
    spectrum: list[tuple[str, float]] = field(default_factory=list)  # (признак, сила связи 0..1)


# ----------------------------------------------------------------------------- мотивы направлений

def motif_lab(k: Kit, brief: Brief, stage: str) -> list[O]:
    """Лаборатория: «спектр» признаков — тонкие линейки разной длины, самый сильный — цвет вина."""
    if stage != "title" or not brief.spectrum:
        return []
    out = []
    x0, y0, w = 8.55, 1.55, 3.95
    top = max(v for _, v in brief.spectrum)
    out.append(O("lab_cap", "text", x0, y0 - 0.5, w, 0.3, txt="связь признака с баллом, |ρ| на train", sz=12,
                 col="muted", z=3))
    for i, (name, v) in enumerate(brief.spectrum):
        y = y0 + i * 0.4
        strong = v == top
        out.append(O(f"!!spec_l{i}", "text", x0, y, 1.7, 0.3, txt=name, sz=12, col="ink" if strong else "ink2",
                     b=strong, al="r", va="m", z=3))
        out.append(O(f"!!spec_b{i}", "rect", x0 + 1.85, y + 0.12, max(v / top * (w - 1.95), 0.02), 0.06,
                     fill="accent" if strong else "ink2", fa=1.0 if strong else 0.55, z=3))
    return out


def motif_cellar(k: Kit, brief: Brief, stage: str) -> list[O]:
    """Погреб: крупное кольцо-«бокал» с дугой прогресса и тихое поле точек."""
    out = []
    for i in range(70):  # поле точек — фактура, детерминированное
        x = (i * 3.71) % SLIDE_W
        y = (i * 2.17 + (i // 9) * 0.61) % SLIDE_H
        out.append(O(f"dust{i}", "oval", x, y, 0.035, 0.035, fill="ink2", fa=0.18, z=-5))
    if stage == "title":
        cx, cy, r = 10.4, 3.85, 2.05
        out.append(O("!!glass", "oval", cx - r, cy - r, 2 * r, 2 * r, fill=None, ln="line", lw=2.0, z=2))
        out.append(O("!!glass_arc", "arc", cx - r, cy - r, 2 * r, 2 * r, fill="accent", rot=270,
                     adj={"adj1": 0, "adj2": int(45 * 60000), "adj3": 2500}, z=3))
        out.append(O("!!glass_core", "oval", cx - 0.5, cy - 0.5, 1.0, 1.0, fill="accent", fa=0.9, z=4))
        out.append(O("!!glass_num", "text", cx - 1.2, cy + 0.65, 2.4, 0.4, txt="1 из 8", sz=16, col="ink2", al="c", z=4))
    return out


def motif_blueprint(k: Kit, brief: Brief, stage: str) -> list[O]:
    """Чертёж: миллиметровка, размерная линия и штамп листа."""
    out = k.bg_grid(0.5, "line", 0.55)
    if stage == "title":
        g = k.t.grid
        y_dim = 5.55
        out.append(O("dim_tick_l", "line", g.margin_x, y_dim - 0.18, 0, 0.36, ln="accent", lw=1.0, z=3))
        out.append(O("dim_tick_r", "line", g.margin_x + 7.6, y_dim - 0.18, 0, 0.36, ln="accent", lw=1.0, z=3))
        out.append(O("dim_l", "line", g.margin_x + 3.8, y_dim, -3.78, 0, ln="accent", lw=1.0, head="triangle", z=3))
        out.append(O("dim_r", "line", g.margin_x + 3.8, y_dim, 3.78, 0, ln="accent", lw=1.0, head="triangle", z=3))
        out.append(O("dim_t", "text", g.margin_x + 2.75, y_dim - 0.16, 2.1, 0.32, txt="поле текста 7,6 in", sz=12,
                     col="accent", al="c", va="m", font="mono", fill="bg", z=4))
        sx, sy = 9.35, 5.65
        out.append(O("stamp", "rect", sx, sy, 3.33, 1.2, fill="bg", ln="ink2", lw=1.0, z=3))
        for j, (a, b) in enumerate([("ЛИСТ", "01"), ("ПРОЕКТ", "А"), ("МАСШТАБ", "1:1")]):
            out.append(O(f"stamp_k{j}", "text", sx + 0.15, sy + 0.12 + j * 0.34, 1.4, 0.3, txt=a, sz=12, col="muted",
                         font="mono", z=4))
            out.append(O(f"stamp_v{j}", "text", sx + 1.6, sy + 0.12 + j * 0.34, 1.6, 0.3, txt=b, sz=12, col="ink",
                         font="mono", z=4))
    return out


MOTIFS = {"lab": motif_lab, "cellar": motif_cellar, "blueprint": motif_blueprint}


# ----------------------------------------------------------------------------- мини-колода

def mini_deck(theme: Theme, brief: Brief) -> list[Slide]:
    k = Kit(theme)
    g = theme.grid
    motif = MOTIFS.get(theme.name, lambda *_: [])

    title = (k.label(brief.label, y=0.75) +
             k.title(brief.title, y=1.25, w=7.6, size="display") +
             k.text("!!lead", g.margin_x, 3.55, 7.6, brief.lead, size="lead", color="ink2") +
             k.text("!!meta", g.margin_x, 6.05, 7.6, brief.meta, size="small", color="muted") +
             k.folio(1, 3) + motif(k, brief, "title"))
    s1 = Slide(title, title="титул", layout="cover", notes="Титул: тема, место в курсе, данные.")

    def content(active: int, zoom: bool) -> list[O]:
        objs = k.label(brief.label) + k.title(brief.content_title, y=0.9, size="h1") + k.folio(2 + int(zoom), 3)
        n = len(brief.stages)
        y = 2.55
        w_node, gap = 2.17, 0.29
        total = n * w_node + (n - 1) * gap
        x0 = (SLIDE_W - total) / 2
        nodes = []
        for i, (lab, sub) in enumerate(brief.stages):
            is_active = i == active
            nd = k.node(f"st{i}", x0 + i * (w_node + gap), y, w_node, 1.05, lab, sub,
                        fill="accent" if is_active else "surface2", col="on_accent" if is_active else "ink",
                        sub_col="on_accent" if is_active else "muted")
            nodes.append(nd[0])
            objs += nd
        loops = []
        for i in range(n - 1):
            line, pts = k.link(f"ln{i}", nodes[i], nodes[i + 1], color="line")
            objs += line
            if i in (active - 1, active):
                loops.append(k.flow(pts, n=3, period=2.2, name=f"f{i}"))
        cw = (g.content_w - 2 * 0.3) / 3
        for j, (kick, ttl, body) in enumerate(brief.cards):
            objs += k.card(f"card{j}", g.margin_x + j * (cw + 0.3), 4.2, cw, 2.35, title=ttl, body=body, kicker=kick,
                           fill="surface")
        objs += motif(k, brief, "content")
        return objs, loops

    c1, l1 = content(active=1, zoom=False)
    c2, l2 = content(active=3, zoom=True)
    s2 = Slide(c1, loops=l1, title="схема: шаг 2", layout="pipeline", technique="камера/смена состояния", dur=1400,
               notes="Поток данных по шагам; активный шаг выделен, по соседним связям бегут точки.")
    s3 = Slide(c2, loops=l2, title="схема: шаг 4", layout="pipeline+", technique="смена состояния узла", dur=1200,
               notes="Morph переносит выделение на следующий шаг; петли переезжают вместе со схемой.")
    return [s1, s2, s3]


def build_previews(brief: Brief, themes: list[Theme], out_dir: str | Path) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {}
    rows = []
    for theme in themes:
        slides = mini_deck(theme, brief)
        issues = lint(slides, theme)
        path = out_dir / f"preview_{theme.name}.pptx"
        build_pptx(slides, theme, path, title=f"Превью: {theme.title}")
        xsd = xsd_check(path)
        pngs = render(path, out_dir / "png", dpi=72)
        result[theme.name] = {"pptx": str(path), "issues": issues, "xsd_errors": xsd, "pngs": [str(p) for p in pngs]}
        rows.append((theme, pngs))
    # лист сравнения: строка на направление, титул и содержательный слайд рядом
    tw, th = 760, int(760 * SLIDE_H / SLIDE_W)
    head = 64
    sheet = Image.new("RGB", (2 * tw + 3 * 24, len(rows) * (th + head + 24) + 24), (244, 243, 240))
    draw = ImageDraw.Draw(sheet)
    f_big, f_small = font_obj("DejaVu Sans", True, 26), font_obj("DejaVu Sans", False, 17)
    for r, (theme, pngs) in enumerate(rows):
        y = 24 + r * (th + head + 24)
        draw.text((24, y), f"{chr(65 + r)}. {theme.title}", fill=(20, 20, 20), font=f_big)
        draw.text((24, y + 32), theme.thesis, fill=(80, 80, 80), font=f_small)
        for c, png in enumerate(pngs[:2]):
            im = Image.open(png).convert("RGB").resize((tw, th))
            sheet.paste(im, (24 + c * (tw + 24), y + head))
    sheet_path = out_dir / "style_previews.png"
    sheet.save(sheet_path)
    result["sheet"] = str(sheet_path)
    return result
