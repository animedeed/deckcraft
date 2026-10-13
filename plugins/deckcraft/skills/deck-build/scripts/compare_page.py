"""Страница сравнения вариантов презентации A/B/C: одни и те же моменты (GIF) столбцами, узор переходов, миниатюры,
выбор «лучший целиком» или «собрать из частей»; решение сохраняется в db артефакта (doc compare/choice).

    python compare_page.py OUT_DIR VAR_DIR [VAR_DIR ...] --topic "..." --brief-url https://claude.ai/artifact/...

Сравнение строится только из вариантов, собранных по сохранённому выбору опроса (/deck-brief): тема и ссылка на
опрос показываются в шапке страницы.

VAR_DIR — папка варианта со сборкой: report.json (variant, slides, lint/motion/xsd, gifs, pattern) и sheet.png
(так пишет examples/demo_deck.py с --gifs; свой генератор презентации пишет то же). Выход: OUT_DIR/index.html и
OUT_DIR/publish.json (карта файлов для Artifact(files=...), capabilities {"db": {}}).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "pptx-morph" / "scripts"))

from morphkit.catalog import MOTIFS, NAVIGATION  # noqa: E402
from morphkit.combine import ACCENTS  # noqa: E402
from morphkit.palette import CATALOG  # noqa: E402
from morphkit.i18n import set_lang, tr  # noqa: E402

MOMENTS = [("layers", "Вход в раздел"), ("attention", "Кульминация"), ("finale", "Финал")]


def _title(choices, key, lang) -> str:
    return tr(next((c.title for c in choices if c.key == key), key or "—"), lang)


def _titles(v: dict, lang: str) -> dict:
    """Подписи осей варианта на языке lang (страница переключает языки без пересборки)."""
    acc = (v.get("transition") or {}).get("accents") or []
    accents = ", ".join(tr(ACCENTS.get(a, (a,))[0], lang) for a in acc)
    return {"palette_title": tr(next((p.title for p in CATALOG if p.theme.name == v.get("palette")), v.get("palette")), lang),
            "navigation_title": _title(NAVIGATION, v.get("navigation"), lang),
            "motif_title": _title(MOTIFS, v.get("motif"), lang),
            "accents_title": accents,
            "transition_title": accents or tr("только Morph", lang)}


def build(out: Path, var_dirs: list[Path], topic: str = "", brief_url: str = "", lang: str = "ru") -> dict:
    """lang — язык, который страница показывает первым; второй доступен переключателем RU/EN."""
    lang = "en" if str(lang).lower().startswith("en") else "ru"
    set_lang(lang)
    out.mkdir(parents=True, exist_ok=True)
    common, files = [], {}
    for d in var_dirs:
        r = json.loads((d / "report.json").read_text())
        v = r["variant"]
        lab = v["label"]
        gifs = {}
        for k, rel in (r.get("gifs") or {}).items():
            dst = f"{lab}/{Path(rel).name}"
            (out / lab).mkdir(exist_ok=True)
            shutil.copy(d / rel, out / dst)
            gifs[k] = dst
            files[dst] = str((out / dst).resolve())
        sheet = None
        if (d / "sheet.png").exists():
            sheet = f"{lab}/sheet.png"
            (out / lab).mkdir(exist_ok=True)
            shutil.copy(d / "sheet.png", out / sheet)
            files[sheet] = str((out / sheet).resolve())
        common.append({"label": lab, "variant": v, "slides": r["slides"], "gifs": gifs, "sheet": sheet,
                       "pattern": r.get("pattern") or [],
                       "qa": {"lint": r["lint_errors"], "motion": r["motion_lint"], "xsd": r["xsd"]}})
    pack = {"lang": lang}
    for lg in ("ru", "en"):
        pack[lg] = {"topic": topic, "brief_url": brief_url, "lang": lg,
                    "variants": [{**c, **_titles(c["variant"], lg)} for c in common],
                    "moments": [(k, tr(t, lg)) for k, t in MOMENTS]}
    ui_en = json.loads((HERE.parents[1] / "pptx-morph" / "scripts" / "morphkit" / "data" / "ui_en.json").read_text())
    html = (HERE / "compare_page.html").read_text().replace(
        "/*DATA*/null", json.dumps(pack, ensure_ascii=False).replace("</", "<\\/")).replace(
        "/*UI_EN*/{}", json.dumps(ui_en, ensure_ascii=False).replace("</", "<\\/"))
    (out / "index.html").write_text(html)
    manifest = {"page": str((out / "index.html").resolve()), "files": files,
                "size_mb": round(sum(Path(p).stat().st_size for p in files.values()) / 2**20, 1)}
    (out / "publish.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    return manifest


def main() -> None:
    args = [a for a in sys.argv[1:]]
    opts = {}
    for flag in ("--topic", "--brief-url", "--lang"):
        if flag in args:
            i = args.index(flag)
            opts[flag] = args[i + 1]
            del args[i:i + 2]
    m = build(Path(args[0]), [Path(a) for a in args[1:]], opts.get("--topic", ""), opts.get("--brief-url", ""),
              opts.get("--lang", "ru"))
    print(json.dumps({"page": m["page"], "n_files": len(m["files"]), "size_mb": m["size_mb"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
