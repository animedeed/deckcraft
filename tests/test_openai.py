"""Run with python tests/test_openai.py; add --browser for local browser/PDF checks."""
from __future__ import annotations

import base64
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/deckcraft-openai"
ENGINE = PLUGIN / "skills/pptx-morph/scripts"
sys.path.insert(0, str(ENGINE))
from morphkit import O, Slide, build_pptx
from morphkit import qa
from morphkit.html import export_html
from morphkit.catalog import auto_brief
from morphkit.palette import CATALOG
from pptx import Presentation

BROWSER = "--browser" in sys.argv
if BROWSER:
    sys.argv.remove("--browser")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OpenAIPackage(unittest.TestCase):
    def test_package_has_no_desktop_requirement(self):
        for relative in ('plugin.json', '.codex-plugin/plugin.json'):
            manifest = json.loads((PLUGIN / relative).read_text(encoding='utf-8'))
            extension = manifest.get('extensions', {}).get('com.openai', manifest)
            self.assertIs(extension['requires_local_executor'], False)
            self.assertEqual(extension['hooks'], [])
        self.assertFalse((PLUGIN / 'mcp.json').exists())
        for skill in (PLUGIN / 'skills').glob('*/SKILL.md'):
            self.assertTrue(skill.read_text(encoding='utf-8').startswith('---\n'))

    def test_missing_and_invalid_optional_tools_are_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with patch.dict(os.environ, {}, clear=True):
                qa._schema_dir.cache_clear()
                self.assertFalse(qa.xsd_available())
                with self.assertRaises(FileNotFoundError):
                    qa.xsd_check(path / "missing.pptx", required=True)
            with patch.dict(os.environ, {"DECKCRAFT_XSD_DIR": str(path)}):
                qa._schema_dir.cache_clear()
                with self.assertRaises(FileNotFoundError):
                    qa.xsd_available()
            fake = path / "soffice.exe"
            fake.touch()
            with patch.dict(os.environ, {"DECKCRAFT_SOFFICE": str(fake)}):
                self.assertEqual(qa._soffice(), [str(fake)])
            with patch.dict(os.environ, {"DECKCRAFT_SOFFICE": str(path / "absent.exe")}):
                with self.assertRaises(FileNotFoundError):
                    qa._soffice()
        qa._schema_dir.cache_clear()

    def test_shared_scenes_preserve_editable_content_and_notes(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            theme = CATALOG[0].theme
            slides = [Slide([O("title", "text", 1, 1, 10, 1, txt=f"Deckcraft {i}", sz=30)],
                            title=f"Slide {i}", notes=f"Speaker note {i}") for i in (1, 2)]
            result = build_pptx(slides, theme, out / "deck.pptx")
            export_html(slides, theme, out / "deck.html", lang="en")
            prs = Presentation(result["path"])
            self.assertEqual(len(prs.slides), 2)
            for i, slide in enumerate(prs.slides, 1):
                self.assertTrue(any(shape.has_text_frame and shape.text == f"Deckcraft {i}" for shape in slide.shapes))
                self.assertIn(f"Speaker note {i}", slide.notes_slide.notes_text_frame.text)
            self.assertIn("Speaker note 2", (out / "deck.html").read_text(encoding="utf-8"))

    @unittest.skipUnless(BROWSER, "add --browser to exercise JSON downloads and UI")
    def test_visual_choice_roundtrip_and_html_controls(self):
        from playwright.sync_api import sync_playwright
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            assets = out / "brief"
            assets.mkdir()
            # A tiny static fixture is sufficient: this checks state exchange, not preview artwork.
            (assets / "pixel.png").write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a6ioAAAAASUVORK5CYII="))
            index = {"gifs": {}, "palettes": [{"key": p.theme.name, "title": p.title, "why": p.why, "dark": p.dark, "png": "pixel.png"} for p in CATALOG]}
            (assets / "index.json").write_text(json.dumps(index), encoding="utf-8")
            brief = auto_brief("Data model", ["Data", "Result"], "colleagues", 10, lang="en")
            brief_page = load_module("deckcraft_brief", PLUGIN / "skills/deck-brief/scripts/brief_page.py")
            brief_page.build(assets, brief, "en")
            compare_page = load_module("deckcraft_compare", PLUGIN / "skills/deck-build/scripts/compare_page.py")
            variants = []
            for label in ("A", "B"):
                d = out / label
                d.mkdir()
                report = {"variant": {"label": label, "palette": CATALOG[0].theme.name, "motif": "bunch", "navigation": "menu"},
                          "slides": 2, "lint_errors": 0, "motion_lint": 0, "xsd": "skipped", "gifs": {}}
                (d / "report.json").write_text(json.dumps(report), encoding="utf-8")
                variants.append(d)
            compare_page.build(out / "compare", variants, topic="Data model", lang="en")
            errors = []
            with sync_playwright() as p:
                launch = {"executable_path": os.environ["DECKCRAFT_CHROME"]} if os.environ.get("DECKCRAFT_CHROME") else {}
                browser = p.chromium.launch(**launch)
                page = browser.new_page(accept_downloads=True, viewport={"width": 1600, "height": 900})
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto((assets / "index.html").as_uri())
                page.wait_for_selector("#show-ui")
                default = json.loads(page.locator("#json").text_content())
                self.assertEqual(len(default["show_ui"]["toolbar"]), 9)
                for key in ("pen", "laser", "presenter", "fullscreen", "help"):
                    page.locator(f'input[data-ui="{key}"]').uncheck()
                page.locator('input[data-ui="printNotes"]').check()
                page.locator("#show-ui-menu").select_option("tabs")
                with page.expect_download() as downloaded:
                    page.locator("#save").click()
                downloaded.value.save_as(out / "choice.json")
                choice = json.loads((out / "choice.json").read_text(encoding="utf-8"))
                self.assertEqual(choice["show_ui"]["toolbar"], ["navigation", "notes", "overview", "print"])
                page.reload()
                self.assertEqual(json.loads(page.locator("#json").text_content())["show_ui"], choice["show_ui"])
                for lang, title in (("ru", "Панель HTML-презентации"), ("en", "HTML presentation controls")):
                    page.locator(f'#langsw button[lang="{lang}"]').click()
                    self.assertEqual(page.locator("#show-ui h2").text_content(), title)
                page.goto((out / "compare/index.html").as_uri())
                page.locator("#notes").fill("Keep original artwork")
                with page.expect_download() as downloaded:
                    page.locator("#save").click()
                downloaded.value.save_as(out / "compare.json")
                self.assertEqual(json.loads((out / "compare.json").read_text(encoding="utf-8"))["notes"], "Keep original artwork")
                slides = [Slide([O("title", "text", 1, 1, 10, 1, txt=f"Slide {i}", sz=30)], notes=f"Note {i}") for i in (1, 2)]
                export_html(slides, CATALOG[0].theme, out / "custom.html", lang="en", ui=choice["show_ui"])
                page.goto((out / "custom.html").as_uri())
                page.wait_for_function("window.DC && DC.ui")
                labels = page.locator(".dcu-hud button").all_text_contents()
                self.assertIn("PDF", labels)
                self.assertNotIn("Pen", labels)
                page.evaluate("DC.ui.notes(true); DC.ui.overview(true)")
                self.assertTrue(page.locator(".dcu-notes").is_visible())
                self.assertTrue(page.locator(".dcu-ov").is_visible())
                page.evaluate("DC.ui.overview(false); DC.ui.printPrepare()")
                self.assertEqual(page.locator("#dcu-print .dcu-page").count(), 4)
                pdf = page.pdf(prefer_css_page_size=True, print_background=True)
                self.assertTrue(pdf.startswith(b"%PDF"))
                export_html(slides, CATALOG[0].theme, out / "full.html", lang="en")
                page.goto((out / "full.html").as_uri())
                page.wait_for_function("window.DC && DC.ui")
                for key, flag in (("d", "pen"), ("l", "laser")):
                    page.keyboard.press(key)
                    self.assertTrue(page.evaluate(f"DC.ui.state.{flag}"))
                    page.keyboard.press(key)
                with page.expect_popup() as popup:
                    page.keyboard.press("p")
                popup.value.wait_for_load_state()
                self.assertIn("presenter", popup.value.url)
                popup.value.close()
                browser.close()
            self.assertFalse(errors, errors)


if __name__ == "__main__":
    unittest.main()
