"""Страница-витрина брифа: рекомендация auto_brief + каталог с GIF, выбор сохраняется в db артефакта (doc brief/choice).

    python brief_page.py ASSETS_DIR --brief brief.json
    python brief_page.py ASSETS_DIR --topic "Тема доклада" --sections "Данные|Модель|Результаты" [--audience ...] [--minutes 10]

ASSETS_DIR — выход `python -m lab.previews ASSETS_DIR` (gif/, palette/, index.json). Пишет ASSETS_DIR/index.html,
ASSETS_DIR/brief.json (если бриф собран из --topic) и ASSETS_DIR/publish.json — карта файлов для Artifact(files=...).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "pptx-morph" / "scripts"))

from morphkit.catalog import MOTIFS, MOTION, NAVIGATION, TRANSITIONS, auto_brief  # noqa: E402


def _items(choices, gifs: dict) -> list[dict]:
    out = []
    for c in choices:
        img = gifs.get(f"{c.preview[0]}:{c.preview[1]}") if c.preview else None
        out.append({"key": c.key, "title": c.title, "why": c.why[0].upper() + c.why[1:], "img": img})
    return out


def build(assets: Path, brief: dict) -> dict:
    index = json.loads((assets / "index.json").read_text())
    gifs = index["gifs"]
    data = {"id": brief.get("id") or brief["topic"], "brief": brief,
            "palettes": [{"key": p["key"], "title": p["title"], "why": p["why"][0].upper() + p["why"][1:], "img": p["png"]} for p in index["palettes"]],
            "motifs": _items(MOTIFS, gifs), "navigation": _items(NAVIGATION, gifs), "motion": _items(MOTION, gifs),
            "transitions": _items(TRANSITIONS, gifs)}
    tpl = (HERE / "brief_page.html").read_text()
    html = tpl.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    (assets / "index.html").write_text(html)
    used = sorted({it["img"] for k in ("palettes", "motifs", "navigation", "motion", "transitions")
                   for it in data[k] if it.get("img")})
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
    a = ap.parse_args()
    if a.brief:
        brief = json.loads(a.brief.read_text())
    else:
        brief = auto_brief(a.topic, [s.strip() for s in a.sections.split("|") if s.strip()], a.audience, a.minutes)
        (a.assets / "brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=1))
    m = build(a.assets, brief)
    print(json.dumps({k: v for k, v in m.items() if k != "files"} | {"n_files": len(m["files"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
