---
name: deck-build
description: "Build and verify PowerPoint Morph/native animations and standalone interactive HTML from the same morphkit scene model and an agreed brief."
---

# Deckcraft build in Codex / ChatGPT Work
Read `../../RUNTIME.md`, `../pptx-morph/SKILL.md` and `../pptx-design/references/structure.md`.
Use the agreed brief and storyboard; obtain material missing choices with `deck-brief`. Paths below are relative to the installed skill.

## Build
Keep `build_deck.py`, `brief.json` and `deck_profile.json` in the task work folder. Add the resolved `../pptx-morph/scripts` path to the generator's import path. Reuse morphkit helpers and original reference assets. The same scene model must drive PPTX and HTML. Preserve matched object names for Morph, native effects, notes, motif roles and navigation. Apply `fit_text` and the requested language with `morphkit.i18n.set_lang`/`localize`.

For HTML, use `morphkit.html.export_html(slides, theme, path, sections=..., ui=..., lang=...)`; use `web()` and `link()` for interactive layers. Pass `ui=brief.get("show_ui", {})` directly to the HTML exporter; do not discard selected toolbar buttons. Missing choices mean the full panel with section navigation, slide paging, notes, overview, presenter view, pen/annotations, laser pointer, print/PDF, full screen and help. Keep `ui.js` included; it is required for HTML presentations. Include useful per-slide speaker notes. `toolbar` changes the panel buttons, not keyboard access. PDF uses browser print (one page per slide), with optional `printNotes`. The PPTX twin uses `build_pptx(for_pptx(slides), ...)`. Do not promise that HTML-only live effects run in PowerPoint.

For variants use `morphkit.combine.plan_variants`, `transition_pattern` and `motion_schedule`. Write each variant and `report.json` in its own folder. Build `scripts/compare_page.py` from real variant reports and preview files, with the topic and brief link. Its “Save decision” downloads `deckcraft-compare-choice.json`. Read that file or pasted JSON, validate variant labels and chosen axes, rebuild the selected result, and rerun checks.

## Verify
- Run `lint(slides, theme, profile=profile)` and `motion_lint`; fix errors. Inspect thumbnail sheets and key motion strips using `morphkit.motion.preview`.
- Build PPTX; run `xsd_check(path, required=True)` when `xsd_available()`. Record absent schemas as skipped. XSD checks the supported fallback content, not actual Morph playback.
- Run `lo_effects_check` when LibreOffice is available; record its `skipped` reason otherwise. Render through LibreOffice or the supplied native PowerPoint renderer. Do not change the final deck during QA.
- For HTML, run `morphkit.webdemo.shots` in a real browser, require zero errors, and test navigation, buttons/state switches, overview, presenter view, notes, pen, laser and PDF; verify the chosen panel buttons match `show_ui`. Check `morphkit.variety.report`; use visual inspection to judge motion and fit.
- When adapting reference decks, compare the result with original frames, including the requested artwork and interactivity. Retain artwork explicitly requested by the user; do not substitute generic assets for supplied references.
- Record passed, failed and skipped separately in `report.json`; repair at most three rounds before explaining unresolved defects. Real Morph/native-effect playback requires a PowerPoint slideshow check.

Deliver the requested PPTX/HTML and useful previews via file links/inline images. Keep complete asset folders for non-standalone pages. Do not commit or publish unless separately authorized.
