"""Проверка web-модулей: сборка демо-страницы и снимки браузером (Playwright + Chromium: свой из
`python -m playwright install chromium`, путь можно задать переменной DECKCRAFT_CHROME).

    from morphkit.webdemo import build, shots
    path = build(slides, "demo.html", sections=[...])          # тема «Лаборатория» по умолчанию
    res = shots(path, "out_dir", times=[0.3, 1.0, 3.0], slides=None, clicks=0)
    # res = {"errors": [...консоль и исключения...], "files": [...png...], "sheet": "out_dir/sheet.png"}

Снимки: для каждого слайда — кадры через times секунд после перехода (переход Morph/лист входит в отсчёт), затем
лист миниатюр. Ошибки JS собираются — пустой список обязателен для сдачи модуля.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from .html import export_html
from .palette import CATALOG

import os

_PW = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
CHROME = os.environ.get("DECKCRAFT_CHROME") or next((str(p) for p in sorted(_PW.glob("chromium-*/chrome-linux/chrome"))), None)


def launch_kw() -> dict:
    """Параметры chromium.launch: найденный Chromium или браузер Playwright по умолчанию."""
    return {"executable_path": CHROME} if CHROME and Path(CHROME).exists() else {}


def build(slides, path, sections=None, theme_name: str = "lab", title: str = "демо", **kw) -> Path:
    theme = next(p.theme for p in CATALOG if p.theme.name == theme_name)
    return export_html(slides, theme, path, title=title, sections=sections, **kw)


async def _shots(path: Path, out: Path, times, slides, clicks, size):
    from playwright.async_api import async_playwright
    from PIL import Image
    out.mkdir(parents=True, exist_ok=True)
    errors, files = [], []
    async with async_playwright() as p:
        b = await p.chromium.launch(**launch_kw())
        pg = await b.new_page(viewport={"width": 1600, "height": 900})
        pg.on("pageerror", lambda e: errors.append(f"exception: {e}"))
        pg.on("console", lambda m: errors.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
        await pg.goto(path.resolve().as_uri())
        await pg.wait_for_timeout(300)
        n = await pg.evaluate("DC.data.slides.length")
        idx = slides if slides is not None else list(range(n))
        for i in idx:
            await pg.evaluate(f"DC.go({i - 1 if i else 0}, {{instant: true}})")
            await pg.wait_for_timeout(150)
            if i:
                await pg.evaluate(f"DC.go({i})")
            t_prev = 0.0
            for c in range(clicks):
                await pg.wait_for_timeout(1200)
                await pg.evaluate("DC.next()")
            for t in times:
                await pg.wait_for_timeout(int((t - t_prev) * 1000))
                t_prev = t
                f = out / f"s{i + 1:02d}_{t:.1f}.png"
                await pg.screenshot(path=str(f))
                files.append(f)
        await b.close()
    ims = [Image.open(f).resize(size) for f in files]
    cols = len(times)
    sheet = Image.new("RGB", (size[0] * cols, size[1] * ((len(ims) + cols - 1) // cols)), "white")
    for k, im in enumerate(ims):
        sheet.paste(im, ((k % cols) * size[0], (k // cols) * size[1]))
    sp = out / "sheet.png"
    sheet.save(sp)
    return {"errors": errors, "files": [str(f) for f in files], "sheet": str(sp)}


def shots(path, out, times=(0.4, 1.2, 3.0), slides=None, clicks: int = 0, size=(480, 270)) -> dict:
    return asyncio.run(_shots(Path(path), Path(out), list(times), slides, clicks, size))
