---
name: deck-build
description: "Builds a .pptx with Morph (and/or one interactive HTML file with the same slides) from the brief: a morphkit generator (motif in roles, navigation, motion language per section, process loops) plus full QA — lint, motion check, XSD, effects import, render and thumbnails, GIFs of key transitions; several variants and a comparison page. English or Russian. / Сборка .pptx с Morph (и/или интерактивной HTML-презентации из тех же слайдов) по brief.json и раскадровке из /deck-brief: генератор презентации на morphkit (мотив в ролях, навигация, язык движения раздела, петли процессов), затем полная проверка с замерами — lint, проверка движения (ничего не пролетает по тексту), XSD, распознавание эффектов, рендер и лист миниатюр, GIF ключевых переходов. Итог — .pptx, отчёт и список того, что посмотреть в PowerPoint."
argument-hint: "[brief.json]"
---

# /deck-build — building from the brief

No brief — run /deck-brief first. Paths are relative to the skill's base; engine `../pptx-morph/scripts`.
Before writing code, read `../pptx-morph/SKILL.md` (profile rules, Morph, building §12, checks §15) and
`../pptx-design/references/structure.md`.


## Language
The language of the survey, pages, captions and the presentation itself is the language of the user's material or request: `ru` or `en`.
Pass it everywhere: `auto_brief(..., lang=)`, `brief_page.py --lang`, `python -m lab.previews OUT --lang`
(English GIFs go in their own folder), `compare_page.py --lang`, and in the generator — `morphkit.i18n.set_lang(lang)` and
`localize(slides)`. Always answer the user in the user's language.

## 1. Generator
Write `out/decks/<slug>/build_deck.py` (do not edit XML by hand): `sys.path` → `../pptx-morph/scripts`.
- Theme: `next(p.theme for p in morphkit.palette.CATALOG if p.theme.name == brief["palette"]["key"])`.
- Profile: `DeckProfile.load(out/decks/<slug>/deck_profile.json)`.
- Motif: ready-made helpers — `morphkit.motif` (Flower, Orbit, `MotifTrack.at(...)` with roles hero / pointer /
  backdrop / data / progress) and the lab families (`lab/f_wine.py` Bunch, Glass; `lab/f_iso.py` platform;
  `lab/f_energy.py`, `lab/f_docs.py`, `lab/f_neural.py`, … — each item has a preview in `morphkit.catalog.MOTIFS[*].preview`).
  Take shape functions from them, not whole slides; use your own name prefix so names do not collide.
- Navigation: `recipes.agenda` (talk map → header), `recipes.menu_bar`, `recipes.block_counter` or a motif at the edge
  (`MotifTrack` pointer with ticks). One per presentation.
- Section motion language → tools: dots — `process.Carrier`, `recipes.dots`; fragments — `ops.explode/gather`;
  circle — `recipes.magnify`, rings; depth — `ops.tilt3d/recede`, camera; flow — `recipes.flow_along`, flow loops;
  growth — `components.Kit.bars`, `recipes.curve`; lens — `recipes.magnify`, `recipes.spotlight`; fold — `ops.fold/peel`.
- Every slide: `layout=`, `technique=`, `title=`, summary speaker notes. Texts go through `fit_text`.
- Numbers come only from the project files; no source — do not write the number.

## 1b. Several variants (survey choice with `variants` > 1)
- `plan_variants(choice)` → list of variants; the presentation generator takes a variant (palette, motif, navigation,
  `transition.accents`, pools of section languages) — like `examples/demo_deck.py --variant JSON --gifs`.
- The default section change is a Morph technique (camera, pointer, map); native accents only if they were chosen
  in the survey (they often cheapen a presentation).
- Transition pattern: `transition_pattern(n_sections + 1, "morph", accents, climax=…, roles={i: "error"})` — the accent
  goes on the entry into a section (the finale as the last chapter); the pool of languages within a section — `motion_schedule(n_slides, pool)`.
- Each variant gets its own folder: .pptx, `report.json` (variant, checks, `gifs` of the same moments, `pattern`),
  `sheet.png`. The §2 checks — for each one.
- The comparison — **only after building** the variants from the saved survey choice (do not publish without a survey):
  `python3 scripts/compare_page.py OUT VAR_A VAR_B VAR_C --topic "…" --brief-url <link to the survey> --lang <lang> --alt-topic "<topic in the other language>"`
  (the page has an RU/EN switch; the GIFs are those of the built presentation) → publish as an artifact
  (`files` from publish.json, `capabilities: {"db": {}}`, `icon: "compare"`). The decision — ArtifactData `get`
  `compare`/`choice`: `best` (A/B/C or "mix"), `from` (axis → variant), `result` (final palette, navigation,
  motif, transitions), `notes`. The final presentation — the generator with `result`, then §2–3.

## 1c. HTML (`format` = html or both)
The same generator: slides → `morphkit.html.export_html(slides, theme, out/deck.html, sections=…, ui={"menu": …,
"hud": True}, lang=lang)`, the `.pptx` twin — `build_pptx(for_pptx(slides), …)`. A web layer on top (`web(slide, …)`):
every section gets its own title entrance; metrics link to evidence slides with “back”; switches (`link set` +
`alt`/`when`) wherever there is a comparison; live scenes (`liquid`, `particles`, `signal`, `gauge` …) where there is a
process; `morphkit.draw` annotations (circle, arrow, handwriting) on code and tables. Reference —
`../pptx-morph/references/web.md`, example — `../pptx-morph/scripts/examples/demo_web.py`.

## 2. Checks (all before showing the user)
```
issues = lint(slides, theme, profile=prof)           # 0 errors
motion_lint(slides, theme)                            # 0: shapes do not fly across text
r = build_pptx(slides, theme, out, title=..., profile=prof)
xsd_check(r["path"])                                  # 0
lo_effects_check(r["path"])["ok"]                     # True
pngs = render(r["path"], out_dir); contact_sheet(pngs, sheet)
morphkit.motion.preview(slides, theme, out_dir/"motion", which=[key transitions])
# HTML: snapshots of every slide and console errors (0), motion variety
r = morphkit.webdemo.shots(html, out_dir/"web", times=[.5, 3.5]); assert not r["errors"]
morphkit.variety.report(slides)["deck"]              # still_transitions ≤ 0.35, verbs per slide ≥ 3
```
Look at the thumbnail sheet and the motion strips yourself (checklist `../pptx-design/SKILL.md` §5). Found a problem — find
the cause by measurement and fix the generator; re-check. No more than three rounds: then show it as it is and name what remains.

## 3. Answer
.pptx (SendUserFile, attach), the HTML (SendUserFile, display "render") if built, the thumbnail sheet and 1–3 GIFs of key transitions (render). Briefly: which techniques on which
transitions, where the loops are, what LibreOffice does not check (freeform Morph, z-order during a transition, 3D) —
ask the user to run the slideshow in PowerPoint 2019+/365. Commit the generator and the brief.

_Russian original: SKILL.ru.md_
