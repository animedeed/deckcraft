"""Страница-витрина брифа: рекомендация auto_brief + каталог с GIF, выбор сохраняется в db артефакта (doc brief/choice).

    python brief_page.py ASSETS_DIR --brief brief.json
    python brief_page.py ASSETS_DIR --topic "Тема доклада" --sections "Данные|Модель|Результаты" [--audience ...] [--minutes 10]

ASSETS_DIR — выход `python -m lab.previews ASSETS_DIR` (gif/, palette/, index.json); --assets-other DIR — те же
превью на втором языке (`--lang en`), страница переключается кнопкой RU/EN. Пишет ASSETS_DIR/index.html,
ASSETS_DIR/brief.json (если бриф собран из --topic) и ASSETS_DIR/publish.json — карта файлов для Artifact(files=...).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "pptx-morph" / "scripts"))

from morphkit.catalog import MOTIFS, MOTION, NAVIGATION, TRANSITIONS, auto_brief, localize_brief  # noqa: E402
from morphkit.i18n import set_lang, tr  # noqa: E402
from morphkit.combine import ACCENTS  # noqa: E402

KIND = {"chapter": "новая глава", "climax": "кульминация", "error": "ошибка", "finale": "финал"}


def _items(choices, gifs: dict, lang: str) -> list[dict]:
    out = []
    for c in choices:
        img = gifs.get(f"{c.preview[0]}:{c.preview[1]}") if c.preview else None
        why = tr(c.why, lang)
        out.append({"key": c.key, "title": tr(c.title, lang), "why": why[0].upper() + why[1:], "img": img})
    return out


def _page_data(index: dict, brief: dict, lang: str, prefix: str = "", page_id: str = "") -> dict:
    """Данные страницы на одном языке. prefix — подпапка с картинками этого языка (en/), если они есть."""
    gifs = {k: prefix + v for k, v in index["gifs"].items()}
    cap = lambda t: t[0].upper() + t[1:]  # noqa: E731
    return {"id": page_id or brief.get("id") or brief["topic"], "brief": brief, "lang": lang,
            "palettes": [{"key": p["key"], "title": tr(p["title"], lang), "why": cap(tr(p["why"], lang)),
                          "img": prefix + p["png"]} for p in index["palettes"]],
            "motifs": _items(MOTIFS, gifs, lang), "navigation": _items(NAVIGATION, gifs, lang),
            "motion": _items(MOTION, gifs, lang), "transitions": _items(TRANSITIONS, gifs, lang),
            "accents": [{"key": k, "title": tr(t, lang), "why": cap(tr(w, lang)), "kind": kd, "kind_title": tr(KIND[kd], lang),
                         "img": gifs.get(f"f_nav:x_{k}")} for k, (t, w, kd) in ACCENTS.items()]}


def build(assets: Path, brief: dict, lang: str = "ru", assets_other: Path | None = None) -> dict:
    """Страница на двух языках с переключателем RU/EN; lang — язык, который показывается первым.

    assets — превью на языке lang; assets_other — превью на втором языке (выход `lab.previews --lang ...`),
    копируются в assets/<язык>/. Без него второй язык показывает те же картинки с переведёнными подписями."""
    lang = "en" if str(lang).lower().startswith("en") else "ru"
    other = "ru" if lang == "en" else "en"
    set_lang(lang)
    index = json.loads((assets / "index.json").read_text())
    prefix, index_o = "", index
    if assets_other:
        index_o = json.loads((assets_other / "index.json").read_text())
        prefix = f"{other}/"
        for rel in list(index_o["gifs"].values()) + [p["png"] for p in index_o["palettes"]]:
            dst = assets / prefix / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(assets_other / rel, dst)
    pid = brief.get("id") or brief["topic"]  # one id for both languages: the draft and the choice are shared
    pack = {"lang": lang, lang: _page_data(index, brief, lang, page_id=pid),
            other: _page_data(index_o, localize_brief(brief, other), other, prefix, page_id=pid)}
    tpl = (HERE / "brief_page.html").read_text()
    ui_en = json.loads((HERE.parents[1] / "pptx-morph" / "scripts" / "morphkit" / "data" / "ui_en.json").read_text())
    html = tpl.replace("/*DATA*/null", json.dumps(pack, ensure_ascii=False).replace("</", "<\\/")).replace(
        "/*UI_EN*/{}", json.dumps(ui_en, ensure_ascii=False).replace("</", "<\\/"))
    (assets / "index.html").write_text(html)
    used = sorted({it["img"] for d in (pack["ru"], pack["en"])
                   for k in ("palettes", "motifs", "navigation", "motion", "transitions", "accents")
                   for it in d[k] if it.get("img")})
    files = {p: str((assets / p).resolve()) for p in used if (assets / p).exists()}
    missing = [p for p in used if p not in files]
    manifest = {"page": str((assets / "index.html").resolve()), "files": files,
                "size_mb": round(sum((assets / p).stat().st_size for p in files) / 2**20, 1), "missing": missing}
    (assets / "publish.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("assets", type=Path)
    ap.add_argument("--brief", type=Path)
    ap.add_argument("--topic")
    ap.add_argument("--sections", help="разделы через |")
    ap.add_argument("--audience", default="")
    ap.add_argument("--minutes", type=int, default=10)
    ap.add_argument("--lang", default="ru", help="ru | en — язык, который страница показывает первым")
    ap.add_argument("--assets-other", type=Path, help="превью на втором языке (lab.previews --lang ...)")
    ap.add_argument("--alt-topic", help="тема на втором языке (для переключателя RU/EN)")
    ap.add_argument("--alt-sections", help="разделы на втором языке через |, в том же порядке")
    ap.add_argument("--alt-audience", help="аудитория на втором языке")
    a = ap.parse_args()
    if a.brief:
        brief = json.loads(a.brief.read_text())
    else:
        brief = auto_brief(a.topic, [s.strip() for s in a.sections.split("|") if s.strip()], a.audience, a.minutes,
                           lang=a.lang)
        (a.assets / "brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=1))
    if a.alt_topic or a.alt_sections or a.alt_audience:
        other = "ru" if str(a.lang).startswith("en") else "en"
        brief.setdefault("alt", {})[other] = {k: v for k, v in {
            "topic": a.alt_topic, "audience": a.alt_audience,
            "sections": [x.strip() for x in a.alt_sections.split("|")] if a.alt_sections else None}.items() if v}
        if not a.brief:
            (a.assets / "brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=1))
    m = build(a.assets, brief, a.lang, a.assets_other)
    print(json.dumps({k: v for k, v in m.items() if k != "files"} | {"n_files": len(m["files"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
